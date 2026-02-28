from ultralytics import YOLO
import cv2
import os
import sys
import numpy as np
from collections import deque

# ── Constants ────────────────────────────────────────────────────────────────
G = 9.81
GROUND_CALIBRATION_FRAMES = 30
AIRBORNE_THRESHOLD = 2
SMOOTH_WINDOW = 5

APPROACH_VELOCITY_THRESHOLD = 1.5
TAKEOFF_FRAMES = 6
LANDING_FRAMES = 8

# ── Angle thresholds ─────────────────────────────────────────────────────────
HIP_LOADING       = 100   # below = crouching
KNEE_LOADING      = 100
HIP_EXTENDED      = 160   # above = straight
KNEE_EXTENDED     = 160
HIP_LANDING       = 130   # below (while descending) = absorbing
KNEE_LANDING      = 130

# ── COCO keypoint indices (0-based) ──────────────────────────────────────────
L_SHOULDER, R_SHOULDER = 5, 6
L_HIP,      R_HIP      = 11, 12
L_KNEE,     R_KNEE     = 13, 14
L_ANKLE,    R_ANKLE    = 15, 16

# ── Model & video setup ──────────────────────────────────────────────────────
model = YOLO('yolov8n-pose.pt')

video_path = sys.argv[1] if len(sys.argv) > 1 else 'input.mp4'
cap = cv2.VideoCapture('./input/' + video_path)
if not cap.isOpened():
    print(f"Error: Cannot open video '{video_path}'")
    sys.exit(1)

fps         = cap.get(cv2.CAP_PROP_FPS) or 30
width       = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
height      = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

os.makedirs('output', exist_ok=True)
video_name = os.path.splitext(os.path.basename(video_path))[0]
out_path   = os.path.join('output', f'{video_name}_skeleton.mp4')
fourcc     = cv2.VideoWriter_fourcc(*'mp4v')
out        = cv2.VideoWriter(out_path, fourcc, fps, (width, height))

skeleton_connections = [
    (16, 14), (14, 12), (17, 15), (15, 13), (12, 13),
    (6, 12),  (7, 13),  (6, 7),   (6, 8),   (7, 9), (8, 10), (9, 11)
]

# ── Helpers ──────────────────────────────────────────────────────────────────
def calc_angle(a, b, c):
    """Angle at B formed by A-B-C, in degrees."""
    a, b, c = np.array(a), np.array(b), np.array(c)
    ba, bc  = a - b, c - b
    cosine  = np.dot(ba, bc) / (np.linalg.norm(ba) * np.linalg.norm(bc) + 1e-6)
    return np.degrees(np.arccos(np.clip(cosine, -1.0, 1.0)))

def get_angles(kpts):
    """Return averaged left/right hip and knee angles. None if points missing."""
    def pt(i):
        x, y = kpts[i]
        return (x, y) if x > 0 and y > 0 else None

    angles = {}

    # Hip: shoulder → hip → knee (both sides, average if both visible)
    hip_vals = []
    if all([pt(L_SHOULDER), pt(L_HIP), pt(L_KNEE)]):
        hip_vals.append(calc_angle(pt(L_SHOULDER), pt(L_HIP), pt(L_KNEE)))
    if all([pt(R_SHOULDER), pt(R_HIP), pt(R_KNEE)]):
        hip_vals.append(calc_angle(pt(R_SHOULDER), pt(R_HIP), pt(R_KNEE)))
    angles['hip'] = sum(hip_vals) / len(hip_vals) if hip_vals else None

    # Knee: hip → knee → ankle (both sides)
    knee_vals = []
    if all([pt(L_HIP), pt(L_KNEE), pt(L_ANKLE)]):
        knee_vals.append(calc_angle(pt(L_HIP), pt(L_KNEE), pt(L_ANKLE)))
    if all([pt(R_HIP), pt(R_KNEE), pt(R_ANKLE)]):
        knee_vals.append(calc_angle(pt(R_HIP), pt(R_KNEE), pt(R_ANKLE)))
    angles['knee'] = sum(knee_vals) / len(knee_vals) if knee_vals else None

    return angles

def get_ankle_y(kpts):
    pts = []
    for idx in [L_ANKLE, R_ANKLE]:
        x, y = kpts[idx]
        if x > 0 and y > 0:
            pts.append(y)
    return sum(pts) / len(pts) if pts else None

def get_ankles_separate(kpts):
    def get_y(idx):
        x, y = kpts[idx]
        return y if x > 0 and y > 0 else None
    return get_y(L_ANKLE), get_y(R_ANKLE)

def smooth_y(buffer, new_y):
    buffer.append(new_y)
    return sum(buffer) / len(buffer)

def classify_phase_by_angles(angles, prev_angles, is_airborne):
    """
    Use joint angles + airborne flag to determine jump phase.
    Falls back gracefully if angles are missing.
    """
    hip   = angles.get('hip')
    knee  = angles.get('knee')
    p_hip  = prev_angles.get('hip')  if prev_angles else None
    p_knee = prev_angles.get('knee') if prev_angles else None

    hip_extending  = (hip  > p_hip)  if (hip  and p_hip)  else False
    knee_extending = (knee > p_knee) if (knee and p_knee) else False

    if is_airborne:
        if hip and knee and hip > HIP_EXTENDED and knee > KNEE_EXTENDED:
            return 'FLIGHT'
        elif hip_extending or knee_extending:
            return 'TAKEOFF'
        else:
            return 'FLIGHT'   # default while airborne

    else:
        if hip and knee:
            if hip < HIP_LOADING and knee < KNEE_LOADING:
                return 'APPROACH'   # deep crouch = loading
            elif hip_extending and knee_extending and hip < HIP_EXTENDED:
                return 'TAKEOFF'    # extending but not yet off ground (just before liftoff)
            elif hip < HIP_LANDING and knee < KNEE_LANDING:
                return 'LANDING'    # flexing on impact
            else:
                return 'STANDING'
        return 'STANDING'

def estimate_camera_drift(prev_frame, curr_frame):
    """Optical flow on background to compensate for camera movement."""
    pg = cv2.cvtColor(prev_frame, cv2.COLOR_BGR2GRAY)
    cg = cv2.cvtColor(curr_frame, cv2.COLOR_BGR2GRAY)
    features = cv2.goodFeaturesToTrack(pg, maxCorners=200, qualityLevel=0.01, minDistance=10)
    if features is None:
        return 0.0
    nxt, status, _ = cv2.calcOpticalFlowPyrLK(pg, cg, features, None)
    good_prev = features[status == 1]
    good_next = nxt[status == 1]
    return float(np.median(good_next[:, 1] - good_prev[:, 1])) if len(good_prev) > 0 else 0.0

# Phase label colors (BGR)
PHASE_COLORS = {
    'CALIBRATING' : (200, 200, 200),
    'STANDING'    : (255, 255, 255),
    'APPROACH'    : (0,   165, 255),  # orange
    'TAKEOFF'     : (0,   255, 255),  # yellow
    'FLIGHT'      : (0,   255, 0),    # green
    'LANDING'     : (255, 100, 100),  # blue-ish
}

# ── State ─────────────────────────────────────────────────────────────────────
ground_y          = None
calibration_ys    = []
ankle_y_buffer    = deque(maxlen=SMOOTH_WINDOW)
prev_frame        = None
prev_angles       = {}

state             = 'CALIBRATING'
angle_phase       = 'STANDING'
liftoff_frame     = None
phase_start_frame = 0
jump_type         = None
jump_results      = []

prev_smoothed_y   = None

# ── Main loop ─────────────────────────────────────────────────────────────────
print(f"Processing '{video_path}' ({frame_count} frames) -> '{out_path}'")
processed = 0

while cap.isOpened():
    success, frame = cap.read()
    if not success:
        break

    # ── Camera drift compensation ──────────────────────────────────────────
    if prev_frame is not None and ground_y is not None:
        drift  = estimate_camera_drift(prev_frame, frame)
        ground_y += drift

    # ── Pose estimation ───────────────────────────────────────────────────
    results     = model(frame, conf=0.5, verbose=False)
    ankle_y_raw = None
    angles      = {}

    if results[0].keypoints is not None and len(results[0].keypoints.xy) > 0:
        person_kpts = results[0].keypoints.xy[0].cpu().numpy()
        ankle_y_raw = get_ankle_y(person_kpts)
        angles      = get_angles(person_kpts)

        # Draw skeleton
        for connection in skeleton_connections:
            pt1 = person_kpts[connection[0] - 1].astype(int)
            pt2 = person_kpts[connection[1] - 1].astype(int)
            if pt1[0] > 0 and pt1[1] > 0 and pt2[0] > 0 and pt2[1] > 0:
                cv2.line(frame, tuple(pt1), tuple(pt2), (0, 255, 0), 2)
        for kpt in person_kpts:
            x, y = int(kpt[0]), int(kpt[1])
            if x > 0 and y > 0:
                cv2.circle(frame, (x, y), 5, (0, 0, 255), -1)

    # ── Calibration ───────────────────────────────────────────────────────
    if state == 'CALIBRATING':
        if ankle_y_raw is not None:
            calibration_ys.append(ankle_y_raw)
        if len(calibration_ys) >= GROUND_CALIBRATION_FRAMES:
            ground_y = sum(calibration_ys) / len(calibration_ys)
            state    = 'STANDING'
            print(f"\nGround calibrated at Y={ground_y:.1f}px")

    # ── Jump tracking + angle phase ───────────────────────────────────────
    elif ankle_y_raw is not None:
        smoothed_y  = smooth_y(ankle_y_buffer, ankle_y_raw)
        is_airborne = smoothed_y < (ground_y - AIRBORNE_THRESHOLD)

        # Ankle-based state machine (source of truth for liftoff/landing)
        left_y, right_y = get_ankles_separate(person_kpts)
        left_air  = left_y  is not None and left_y  < (ground_y - AIRBORNE_THRESHOLD)
        right_air = right_y is not None and right_y < (ground_y - AIRBORNE_THRESHOLD)

        velocity_y = (smoothed_y - prev_smoothed_y) if prev_smoothed_y else 0
        prev_smoothed_y = smoothed_y

        if state == 'STANDING' and velocity_y < -APPROACH_VELOCITY_THRESHOLD:
            state = 'APPROACH'

        elif state == 'APPROACH':
            if is_airborne:
                state         = 'AIRBORNE'
                liftoff_frame = processed
                jump_type     = '2L' if (left_air and right_air) else '1L'
                print(f"\n[Frame {processed}] Liftoff! Type: {jump_type}")
            elif velocity_y >= 0:
                state = 'STANDING'

        elif state == 'AIRBORNE' and not is_airborne:
            state      = 'STANDING'
            air_frames = processed - liftoff_frame
            t          = air_frames / fps
            h          = G * t**2 / 8
            jump_results.append({'height': h, 'type': jump_type, 'frame': processed})
            print(f"[Frame {processed}] Landed! {t:.3f}s → {h:.3f}m ({jump_type})")
            liftoff_frame = None
            ankle_y_buffer.clear()

        # Angle-based phase (runs every frame independently)
        angle_phase = classify_phase_by_angles(angles, prev_angles, is_airborne)

    prev_angles = angles.copy()

    # ── Overlay ───────────────────────────────────────────────────────────
    if ground_y is not None:
        cv2.line(frame, (0, int(ground_y)), (width, int(ground_y)), (0, 255, 255), 2)

    phase_color = PHASE_COLORS.get(angle_phase, (255, 255, 255))
    cv2.putText(frame, f"Phase : {angle_phase}", (10, 30),  cv2.FONT_HERSHEY_SIMPLEX, 0.7, phase_color, 2)
    cv2.putText(frame, f"State : {state}",       (10, 60),  cv2.FONT_HERSHEY_SIMPLEX, 0.7, (200, 200, 200), 2)

    if angles.get('hip'):
        cv2.putText(frame, f"Hip   : {angles['hip']:.1f}°",  (10, 90),  cv2.FONT_HERSHEY_SIMPLEX, 0.65, (180, 255, 180), 2)
    if angles.get('knee'):
        cv2.putText(frame, f"Knee  : {angles['knee']:.1f}°", (10, 115), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (180, 255, 180), 2)

    if jump_results:
        last = jump_results[-1]
        cv2.putText(frame, f"Last  : {last['height']:.3f}m ({last['type']})", (10, 145), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 255, 255), 2)
        cv2.putText(frame, f"Best  : {max(j['height'] for j in jump_results):.3f}m",     (10, 170), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 255, 0),   2)

    out.write(frame)
    prev_frame = frame.copy()
    processed += 1
    print(f"\rFrame {processed}/{frame_count}", end='', flush=True)

cap.release()
out.release()

print(f"\n\nDone! Saved to '{out_path}'")
if jump_results:
    print(f"Total jumps : {len(jump_results)}")
    print(f"Best        : {max(j['height'] for j in jump_results):.3f}m")
    for i, j in enumerate(jump_results, 1):
        print(f"  Jump {i}: {j['height']:.3f}m | {j['type']}")
else:
    print("No jumps detected.")