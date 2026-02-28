from ultralytics import YOLO
import cv2
import os
import sys
from collections import deque

# ── Constants ────────────────────────────────────────────────────────────────
G = 9.81                        # gravity (m/s²)
GROUND_CALIBRATION_FRAMES = 30  # how many still frames to average for ground_y
AIRBORNE_THRESHOLD = 2         # pixels above ground_y to count as airborne
SMOOTH_WINDOW = 5               # rolling average window for ankle Y smoothing

# ── Model & video setup ──────────────────────────────────────────────────────
model = YOLO('yolov8n-pose.pt')

video_path = sys.argv[1] if len(sys.argv) > 1 else 'input.mp4'
cap = cv2.VideoCapture('./input/' + video_path)
if not cap.isOpened():
    print(f"Error: Cannot open video '{video_path}'")
    sys.exit(1)

fps    = cap.get(cv2.CAP_PROP_FPS) or 30
width  = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

os.makedirs('output', exist_ok=True)
video_name = os.path.splitext(os.path.basename(video_path))[0]
out_path   = os.path.join('output', f'{video_name}_skeleton.mp4')
fourcc     = cv2.VideoWriter_fourcc(*'mp4v')
out        = cv2.VideoWriter(out_path, fourcc, fps, (width, height))

# Define connections for the skeleton (COCO keypoints)
skeleton_connections = [
    (16, 14), (14, 12), (17, 15), (15, 13), (12, 13),  # Legs
    (6, 12), (7, 13), (6, 7), (6, 8), (7, 9), (8, 10), (9, 11)  # Torso/Arms
]

# COCO keypoint indices for ankles
LEFT_ANKLE  = 16  # index 14 (0-based)
RIGHT_ANKLE = 17  # index 15 (0-based)

# ── State tracking ───────────────────────────────────────────────────────────
ground_y         = None          # established ground level (pixels)
calibration_ys   = []            # ankle Y samples during calibration
ankle_y_buffer   = deque(maxlen=SMOOTH_WINDOW)  # smoothing buffer

state            = 'CALIBRATING' # CALIBRATING → STANDING → AIRBORNE
liftoff_frame    = None
jump_results     = []            # list of jump heights (meters)

def get_ankle_y(keypoints):
    """Return average Y of both visible ankles, or None if not detected."""
    pts = []
    for idx in [LEFT_ANKLE - 1, RIGHT_ANKLE - 1]:  # convert to 0-based
        x, y = keypoints[idx]
        if x > 0 and y > 0:
            pts.append(y)
    return sum(pts) / len(pts) if pts else None

def smooth_y(buffer, new_y):
    buffer.append(new_y)
    return sum(buffer) / len(buffer)

# ── Main loop ────────────────────────────────────────────────────────────────
print(f"Processing '{video_path}' ({frame_count} frames) -> '{out_path}'")
processed = 0

while cap.isOpened():
    success, frame = cap.read()
    if not success:
        break

    results = model(frame, conf=0.5, verbose=False)

    ankle_y_raw = None
    if results[0].keypoints is not None and len(results[0].keypoints.xy) > 0:
        # Use the first detected person only
        person_kpts = results[0].keypoints.xy[0].cpu().numpy()
        ankle_y_raw = get_ankle_y(person_kpts)
        
        print(f"print(person_kpts.shape): {person_kpts.shape}", end=' | ')
        
        print(f"ankle_y_raw: {ankle_y_raw:.1f}" if ankle_y_raw is not None else "ankle_y_raw: None", end=' | ')

        # ── Draw skeleton ──────────────────────────────────────────────────
        for connection in skeleton_connections:
            pt1 = person_kpts[connection[0] - 1].astype(int)
            pt2 = person_kpts[connection[1] - 1].astype(int)
            if pt1[0] > 0 and pt1[1] > 0 and pt2[0] > 0 and pt2[1] > 0:
                cv2.line(frame, tuple(pt1), tuple(pt2), (0, 255, 0), 2)

        for person_kpts_all in results[0].keypoints.xy.cpu().numpy():
            for kpt in person_kpts_all:
                x, y = int(kpt[0]), int(kpt[1])
                if x > 0 and y > 0:
                    cv2.circle(frame, (x, y), 5, (0, 0, 255), -1)

    # ── Ground calibration ─────────────────────────────────────────────────
    if state == 'CALIBRATING':
        if ankle_y_raw is not None:
            calibration_ys.append(ankle_y_raw)
            
            
            
        if len(calibration_ys) >= GROUND_CALIBRATION_FRAMES:
            # Add offset to push line down closer to the actual floor
            print(f"\nCalibration complete. Raw ground Y samples: {[f'{y:.1f}' for y in calibration_ys]}")
            print(f"calibration_ys: {calibration_ys} | len: {len(calibration_ys)} | average: {sum(calibration_ys) / len(calibration_ys):.1f}")
            ground_y = sum(calibration_ys) / len(calibration_ys)
            state = 'STANDING'
            print(f"\nGround calibrated at Y={ground_y:.1f}px — now tracking jumps...")

    # ── Jump detection ─────────────────────────────────────────────────────
    elif ankle_y_raw is not None:
        smoothed_y = smooth_y(ankle_y_buffer, ankle_y_raw)
        # In image coords, Y increases downward — so "higher" means smaller Y
        is_airborne = smoothed_y < (ground_y - AIRBORNE_THRESHOLD)

        if state == 'STANDING' and is_airborne:
            state = 'AIRBORNE'
            liftoff_frame = processed
            print(f"\n[Frame {processed}] Liftoff detected!")

        elif state == 'AIRBORNE' and not is_airborne:
            state = 'STANDING'
            air_frames = processed - liftoff_frame
            t = air_frames / fps
            h = G * t**2 / 8
            jump_results.append(h)
            print(f"[Frame {processed}] Landed! Air time: {t:.3f}s → Jump height: {h:.3f}m")
            liftoff_frame = None
            ankle_y_buffer.clear()  # reset smoother after landing

    # ── Overlay on frame ───────────────────────────────────────────────────
    if ground_y is not None:
        # Yellow line (BGR: 0, 255, 255) at ground level
        cv2.line(frame, (0, int(ground_y)), (width, int(ground_y)), (0, 255, 255), 2)

    status_text = f"State: {state}"
    cv2.putText(frame, status_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

    if jump_results:
        last_h = jump_results[-1]
        cv2.putText(frame, f"Last jump: {last_h:.3f}m", (10, 60),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
        cv2.putText(frame, f"Best jump: {max(jump_results):.3f}m", (10, 90),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

    out.write(frame)
    processed += 1
    print(f"\rFrame {processed}/{frame_count}", end='', flush=True)

cap.release()
out.release()

# ── Summary ──────────────────────────────────────────────────────────────────
print(f"\n\nDone! Output saved to '{out_path}'")
if jump_results:
    print(f"Total jumps detected : {len(jump_results)}")
    print(f"Best jump            : {max(jump_results):.3f}m")
    print(f"Average jump         : {sum(jump_results)/len(jump_results):.3f}m")
    for i, h in enumerate(jump_results, 1):
        print(f"  Jump {i}: {h:.3f}m")
else:
    print("No jumps detected.")
