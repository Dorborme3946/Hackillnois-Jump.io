import cv2
import mediapipe as mp
import os
import subprocess
import numpy as np

mp_pose = mp.solutions.pose
mp_drawing = mp.solutions.drawing_utils


def convert_to_h264(input_path: str) -> str:
    output_path = input_path.rsplit(".", 1)[0] + "_h264.mp4"
    print(f"🔄 Converting to H264...")
    result = subprocess.run([
        "ffmpeg", "-i", input_path,
        "-vcodec", "libx264",
        "-preset", "fast",
        "-crf", "23",
        "-y",
        output_path
    ], capture_output=True, text=True)
    if result.returncode == 0:
        print(f"✅ Converted — size: {os.path.getsize(output_path)} bytes")
        return output_path
    else:
        print(f"❌ ffmpeg error: {result.stderr}")
        return input_path


def resize_keep_aspect(frame, max_width=720, max_height=540):
    h, w = frame.shape[:2]
    scale = min(max_width / w, max_height / h)
    new_w = int(w * scale)
    new_h = int(h * scale)
    return cv2.resize(frame, (new_w, new_h))


def calculate_height_from_hangtime(takeoff_frame: int, landing_frame: int, fps: float):
    hang_time = (landing_frame - takeoff_frame) / fps
    g = 9.81
    height_meters = g * (hang_time ** 2) / 8
    print(f"⏱️  Hang time: {hang_time:.3f}s")
    print(f"📐 Height: {round(height_meters, 3)}m")
    return round(height_meters, 3), round(hang_time, 3)


def playback(frames, fps, max_height_meters, hang_time, threshold_y):
    idx = 0
    paused = False
    total = len(frames)
    delay = max(1, int(1000 / fps))

    print("\n▶️  Playback controls:")
    print("   SPACE — pause/resume")
    print("   ← →   — rewind / forward 30 frames")
    print("   R     — restart")
    print("   Q     — quit\n")

    while True:
        if idx >= total:
            idx = total - 1
            paused = True

        frame = frames[idx].copy()
        h, w = frame.shape[:2]

        # Draw knee threshold line
        if threshold_y is not None:
            threshold_px = int(threshold_y * h)
            cv2.line(frame, (0, threshold_px), (w, threshold_px), (0, 200, 255), 2)
            cv2.putText(frame, "Knee Baseline", (w - 150, threshold_px - 8),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 200, 255), 1)

        cv2.putText(frame, f"Frame: {idx + 1}/{total}", (20, h - 60),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (200, 200, 200), 1)

        if paused:
            cv2.putText(frame, "PAUSED", (w // 2 - 40, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 200, 255), 2)

        if max_height_meters > 0:
            cv2.putText(frame,
                        f"Max Vert: {max_height_meters}m  |  Hang: {hang_time}s",
                        (20, h - 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 157), 2)

        cv2.imshow("JumpIQ - Analysis", frame)

        key = cv2.waitKey(1 if paused else delay) & 0xFF

        if key == ord('q'):
            break
        elif key == ord(' '):
            paused = not paused
        elif key == ord('r'):
            idx = 0
            paused = False
        elif key == 81 or key == 2:
            idx = max(0, idx - 30)
            paused = True
        elif key == 83 or key == 3:
            idx = min(total - 1, idx + 30)
            paused = True
        elif not paused:
            idx += 1

    cv2.destroyAllWindows()


def analyze_video(video_path: str, user_height_inches: float = 70):
    converted_path = convert_to_h264(video_path)

    cap = cv2.VideoCapture(converted_path)
    print(f"📹 Opened: {cap.isOpened()}")
    print(f"📹 Frame count: {cap.get(cv2.CAP_PROP_FRAME_COUNT)}")

    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0

    pose = mp_pose.Pose(min_detection_confidence=0.5, min_tracking_confidence=0.5)

    frames_with_skeleton = []
    knee_readings = []
    knee_baseline = None
    threshold_y = None
    state = "standing"
    takeoff_frame = None
    landing_frame = None
    max_height_meters = 0.0
    hang_time = 0.0
    frame_count = 0

    BASELINE_FRAMES = 30
    LIFTOFF_THRESHOLD = 0.06   # knees move more than hips so slightly higher threshold

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frame_count += 1
        frame = resize_keep_aspect(frame)
        h, w = frame.shape[:2]
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = pose.process(rgb)

        if results.pose_landmarks:
            landmarks = results.pose_landmarks.landmark

            left_knee_y  = landmarks[mp_pose.PoseLandmark.LEFT_KNEE].y
            right_knee_y = landmarks[mp_pose.PoseLandmark.RIGHT_KNEE].y

            avg_knee_y = (left_knee_y + right_knee_y) / 2

            knee_readings.append(avg_knee_y)

            # Build stable baseline from median of first N frames
            if frame_count <= BASELINE_FRAMES:
                knee_baseline = float(np.median(knee_readings))
                threshold_y = knee_baseline
                print(f"📏 Knee baseline: {knee_baseline:.4f}")

            # Knees rise above baseline = airborne
            knees_above_baseline = (
                knee_baseline is not None and
                avg_knee_y < knee_baseline - LIFTOFF_THRESHOLD
            )

            if frame_count % 10 == 0:
                print(f"Frame {frame_count:4d} | {state:10s} | knee_y: {avg_knee_y:.4f} | baseline: {knee_baseline:.4f} | airborne: {knees_above_baseline}")

            # State machine
            if state == "standing" and knees_above_baseline:
                state = "airborne"
                takeoff_frame = frame_count
                print(f"🚀 TAKEOFF at frame {frame_count}")

            if state == "airborne" and not knees_above_baseline and frame_count > takeoff_frame + 5:
                state = "landing"
                landing_frame = frame_count
                print(f"🛬 LANDING at frame {frame_count}")
                max_height_meters, hang_time = calculate_height_from_hangtime(
                    takeoff_frame, landing_frame, fps
                )

            # Draw skeleton
            mp_drawing.draw_landmarks(
                frame,
                results.pose_landmarks,
                mp_pose.POSE_CONNECTIONS,
                mp_drawing.DrawingSpec(color=(0, 255, 157), thickness=2, circle_radius=3),
                mp_drawing.DrawingSpec(color=(0, 184, 255), thickness=2)
            )

            # Draw knee baseline line
            if threshold_y is not None:
                line_y = int(threshold_y * h)
                cv2.line(frame, (0, line_y), (w, line_y), (0, 200, 255), 2)
                cv2.putText(frame, "Knee Baseline", (w - 150, line_y - 8),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 200, 255), 1)

            # State label
            state_color = (0, 255, 157) if state == "airborne" else (255, 255, 255)
            cv2.putText(frame, f"State: {state.upper()}", (20, 40),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, state_color, 2)

            # Live hang time + current height while airborne
            if state == "airborne" and takeoff_frame:
                live_hang = (frame_count - takeoff_frame) / fps
                g = 9.81
                live_height = g * (live_hang ** 2) / 8
                cv2.putText(frame, f"Hang: {live_hang:.2f}s", (20, 80),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 200, 0), 2)
                cv2.putText(frame, f"Height: {live_height:.2f}m", (20, 115),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 184, 255), 2)

            # Max vert after landing
            if max_height_meters > 0:
                cv2.putText(frame, f"Max Vert: {max_height_meters}m", (20, 150),
                            cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 157), 3)

        frames_with_skeleton.append(frame)

    cap.release()

    print("\n" + "=" * 45)
    print("         JUMPIQ ANALYSIS COMPLETE")
    print("=" * 45)
    print(f"  Max Vertical:  {max_height_meters} m")
    print(f"  Max Vertical:  {round(max_height_meters * 100, 1)} cm")
    print(f"  Max Vertical:  {round(max_height_meters * 39.3701, 1)} inches")
    print(f"  Hang Time:     {hang_time} seconds")
    print(f"  Frames Read:   {frame_count}")
    print(f"  FPS:           {fps}")
    print(f"  Final State:   {state.upper()}")
    print("=" * 45 + "\n")

    playback(frames_with_skeleton, fps, max_height_meters, hang_time, threshold_y)

    if converted_path != video_path and os.path.exists(converted_path):
        os.remove(converted_path)

    return {
        "max_height_meters": max_height_meters,
        "max_height_cm": round(max_height_meters * 100, 1),
        "max_height_inches": round(max_height_meters * 39.3701, 1),
        "hang_time_seconds": hang_time,
        "frames_read": frame_count,
        "fps": fps,
        "final_state": state
    }
