import argparse
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
import cv2
import time
from pose_extraction import extract_landmarks

# Visualization utilities
import numpy as np
from mediapipe.tasks.python.vision import drawing_utils
from mediapipe.tasks.python.vision import drawing_styles
from mediapipe.tasks.python import vision

def draw_landmarks_on_image(rgb_image, detection_result):
  pose_landmarks_list = detection_result.pose_landmarks
  annotated_image = np.copy(rgb_image)

  pose_landmark_style = drawing_styles.get_default_pose_landmarks_style()
  pose_connection_style = drawing_utils.DrawingSpec(color=(0, 255, 0), thickness=2)

  for pose_landmarks in pose_landmarks_list:
    drawing_utils.draw_landmarks(
        image=annotated_image,
        landmark_list=pose_landmarks,
        connections=vision.PoseLandmarksConnections.POSE_LANDMARKS,
        landmark_drawing_spec=pose_landmark_style,
        connection_drawing_spec=pose_connection_style)
  return annotated_image


# Setting up argparse
parser = argparse.ArgumentParser(description="A testing model for mediapipe")
parser.add_argument("--model", default="pose_landmarker_heavy.task", help="Path to the model file.")
parser.add_argument("--input", default=0, help="Path to the input file.")
args = parser.parse_args()

# Creating a PoseLandmarker object
base_options = python.BaseOptions(model_asset_path = args.model)
options = vision.PoseLandmarkerOptions(
    base_options = base_options, # Use base options from the .task file
    running_mode = vision.RunningMode.VIDEO,
    output_segmentation_masks = True
)
detector = vision.PoseLandmarker.create_from_options(options)

# Load input Frame using openCV
cap = cv2.VideoCapture(args.input)
frame_index = 0
all_landmark_frames = []
fps = cap.get(cv2.CAP_PROP_FPS)
if (fps == 0 or fps == None):
    fps = 30
phase_state = "approach"
prev_avg_hip_flexion = None
loading_min_hip_flexion = None
smallest_loading_min_hip_flexion = None
dramatic_increase_deg = 6.0
rebound_margin_deg = 4.0

# Default Angle Readings
angle_lines = [
        "Right knee flexion: not detected!",
        "Left knee flexion: not detected!",
        "Right hip flexion: not detected!",
        "Left hip flexion: not detected!",
        "Right ankle_angle: not detected!",
        "Left ankle_angle: not detected!",
    ]

while True:
    ret, frame = cap.read()
    if not ret:
        break

    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    mp_frame_rgb = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame_rgb)

    # Detect pose landmarks from input Frame
    timestamp_ms = int(time.monotonic() * 1000)
    detection_results = detector.detect_for_video(mp_frame_rgb, timestamp_ms)

    frame_height, frame_width, _ = frame.shape
    primary_frame_data = None

    # Extract landmark data
    if detection_results.pose_landmarks:
        # pose_landmarks is a list of detected poses for THIS frame.
        # frame_index is a video frame counter, not a pose index.
        for pose_landmarks in detection_results.pose_landmarks:
            frame_data = extract_landmarks(
                frame_index, fps, pose_landmarks, frame_height, frame_width
            )
            all_landmark_frames.append(frame_data)
            if primary_frame_data is None:
                primary_frame_data = frame_data

    frame_index += 1

    # Annotate the detected landmarks on the original Frame
    annotated_frame = draw_landmarks_on_image(frame_rgb, detection_results)
    annotated_frame_BGR = cv2.cvtColor(annotated_frame, cv2.COLOR_RGB2BGR)

    # Default Jump Phase State
    phase_text = "Jump phase: not detected!"
    
    if primary_frame_data is not None:
        angles = primary_frame_data["landmarks"]["angles"]
        right_angles = angles["right"]
        left_angles = angles["left"]

        # Reading the angles
        angle_lines = [
            f"Right knee flexion: {right_angles['knee_flexion']:.1f}" if right_angles["knee_flexion"] is not None else "Right knee flexion: not detected!",
            f"Left knee flexion: {left_angles['knee_flexion']:.1f}" if left_angles["knee_flexion"] is not None else "Left knee flexion: not detected!",
            f"Right hip flexion: {right_angles['hip_flexion']:.1f}" if right_angles["hip_flexion"] is not None else "Right hip flexion: not detected!",
            f"Left hip flexion: {left_angles['hip_flexion']:.1f}" if left_angles["hip_flexion"] is not None else "Left hip flexion: not detected!",
            f"Right ankle_angle: {right_angles['ankle_angle']:.1f}" if right_angles["ankle_angle"] is not None else "Right ankle_angle: not detected!",
            f"Left ankle_angle: {left_angles['ankle_angle']:.1f}" if left_angles["ankle_angle"] is not None else "Left ankle_angle: not detected!",
        ]

        # Phase Segmentation
        hip_flexion_values = [value for value in [right_angles["hip_flexion"], left_angles["hip_flexion"]] if value is not None]
        if hip_flexion_values:
            avg_hip_flexion = sum(hip_flexion_values) / len(hip_flexion_values)

            if prev_avg_hip_flexion is None:
                phase_state = "loading" if avg_hip_flexion <= 90 else "approach"
                if phase_state == "loading":
                    loading_min_hip_flexion = avg_hip_flexion
                    if (
                        smallest_loading_min_hip_flexion is None
                        or loading_min_hip_flexion < smallest_loading_min_hip_flexion
                    ):
                        smallest_loading_min_hip_flexion = loading_min_hip_flexion
            else:
                if phase_state == "approach" and avg_hip_flexion <= 90:
                    phase_state = "loading"
                    loading_min_hip_flexion = avg_hip_flexion
                    if (
                        smallest_loading_min_hip_flexion is None
                        or loading_min_hip_flexion < smallest_loading_min_hip_flexion
                    ):
                        smallest_loading_min_hip_flexion = loading_min_hip_flexion
                elif phase_state == "loading":
                    if loading_min_hip_flexion is None:
                        loading_min_hip_flexion = avg_hip_flexion
                    else:
                        loading_min_hip_flexion = min(loading_min_hip_flexion, avg_hip_flexion)
                    if (
                        smallest_loading_min_hip_flexion is None
                        or loading_min_hip_flexion < smallest_loading_min_hip_flexion
                    ):
                        smallest_loading_min_hip_flexion = loading_min_hip_flexion

                    if (
                        avg_hip_flexion >= loading_min_hip_flexion + rebound_margin_deg
                        and (avg_hip_flexion - prev_avg_hip_flexion) >= dramatic_increase_deg
                    ):
                        phase_state = "takeoff"

            prev_avg_hip_flexion = avg_hip_flexion
            phase_text = f"Jump phase: {phase_state}"

    cv2.putText(
        annotated_frame_BGR,
        phase_text,
        (10, 30),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.8,
        (0, 255, 255),
        2,
        cv2.LINE_AA,
    )

    for idx, text in enumerate(angle_lines):
        cv2.putText(
            annotated_frame_BGR,
            text,
            (10, 60 + idx * 25),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (255, 255, 255),
            2,
            cv2.LINE_AA,
        )
    cv2.imshow("Frames", annotated_frame_BGR)

    if cv2.waitKey(1) == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()

# Debugging: checking minimum hip flexion
if smallest_loading_min_hip_flexion is not None:
    print(f"Smallest loading_min_hip_flexion detected: {smallest_loading_min_hip_flexion:.1f}")
else:
    print("Smallest loading_min_hip_flexion detected: not detected!")
