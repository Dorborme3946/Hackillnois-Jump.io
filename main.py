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
smallest_loading_min_knee_flexion = None
largest_loading_max_knee_flexion = None
largest_loading_max_shoulder_angle = None
loading_max_shoulder_timestamp = None
largest_takeoff_max_shoulder_angle = None
takeoff_max_shoulder_timestamp = None
analysis_side = None
side_locked = False
left_shoulder_valid_count = 0
right_shoulder_valid_count = 0
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
        knee_flexion_values = [value for value in [right_angles["knee_flexion"], left_angles["knee_flexion"]] if value is not None]
        current_left_shoulder_angle = left_angles["shoulder_angle"]
        current_right_shoulder_angle = right_angles["shoulder_angle"]

        if current_left_shoulder_angle is not None:
            left_shoulder_valid_count += 1
        if current_right_shoulder_angle is not None:
            right_shoulder_valid_count += 1

        if not side_locked:
            if current_left_shoulder_angle is not None and current_right_shoulder_angle is None:
                analysis_side = "left"
            elif current_right_shoulder_angle is not None and current_left_shoulder_angle is None:
                analysis_side = "right"
            elif current_left_shoulder_angle is not None and current_right_shoulder_angle is not None:
                analysis_side = "left" if left_shoulder_valid_count >= right_shoulder_valid_count else "right"

        selected_shoulder_angle = None
        if analysis_side == "left":
            selected_shoulder_angle = current_left_shoulder_angle
        elif analysis_side == "right":
            selected_shoulder_angle = current_right_shoulder_angle
        elif current_left_shoulder_angle is not None:
            selected_shoulder_angle = current_left_shoulder_angle
        elif current_right_shoulder_angle is not None:
            selected_shoulder_angle = current_right_shoulder_angle

        if hip_flexion_values:
            avg_hip_flexion = sum(hip_flexion_values) / len(hip_flexion_values)
            current_knee_flexion = min(knee_flexion_values) if knee_flexion_values else None

            # Calculating average hip flexion during loading phase
            if prev_avg_hip_flexion is None:
                phase_state = "loading" if avg_hip_flexion <= 90 else "approach"
                if phase_state == "loading":
                    loading_min_hip_flexion = avg_hip_flexion
                    # Finding Minimum Hip Flexion during loading phase logic
                    if (
                        smallest_loading_min_hip_flexion is None
                        or loading_min_hip_flexion < smallest_loading_min_hip_flexion
                    ):
                        smallest_loading_min_hip_flexion = loading_min_hip_flexion

                    # Finding Minimum Knee Flexion during loading phase logic
                    if (
                        current_knee_flexion is not None
                        and (
                            smallest_loading_min_knee_flexion is None
                            or current_knee_flexion < smallest_loading_min_knee_flexion
                        )
                    ):
                        smallest_loading_min_knee_flexion = current_knee_flexion

                    # Finding Maximum Knee Flexion during loading phase logic
                    if (
                        current_knee_flexion is not None
                        and (
                            largest_loading_max_knee_flexion is None
                            or current_knee_flexion > largest_loading_max_knee_flexion
                        )
                    ):
                        largest_loading_max_knee_flexion = current_knee_flexion

            else:
                if phase_state == "approach" and avg_hip_flexion <= 90:
                    phase_state = "loading"
                    loading_min_hip_flexion = avg_hip_flexion
                    if (
                        smallest_loading_min_hip_flexion is None
                        or loading_min_hip_flexion < smallest_loading_min_hip_flexion
                    ):
                        smallest_loading_min_hip_flexion = loading_min_hip_flexion
                    if (
                        current_knee_flexion is not None
                        and (
                            smallest_loading_min_knee_flexion is None
                            or current_knee_flexion < smallest_loading_min_knee_flexion
                        )
                    ):
                        smallest_loading_min_knee_flexion = current_knee_flexion
                    if (
                        current_knee_flexion is not None
                        and (
                            largest_loading_max_knee_flexion is None
                            or current_knee_flexion > largest_loading_max_knee_flexion
                        )
                    ):
                        largest_loading_max_knee_flexion = current_knee_flexion
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
                        current_knee_flexion is not None
                        and (
                            smallest_loading_min_knee_flexion is None
                            or current_knee_flexion < smallest_loading_min_knee_flexion
                        )
                    ):
                        smallest_loading_min_knee_flexion = current_knee_flexion
                    if (
                        current_knee_flexion is not None
                        and (
                            largest_loading_max_knee_flexion is None
                            or current_knee_flexion > largest_loading_max_knee_flexion
                        )
                    ):
                        largest_loading_max_knee_flexion = current_knee_flexion

                    if (
                        avg_hip_flexion >= loading_min_hip_flexion + rebound_margin_deg
                        and (avg_hip_flexion - prev_avg_hip_flexion) >= dramatic_increase_deg
                    ):
                        phase_state = "takeoff"

            prev_avg_hip_flexion = avg_hip_flexion
            phase_text = f"Jump phase: {phase_state}"

            if phase_state == "loading" and not side_locked and analysis_side is not None:
                side_locked = True

            if phase_state == "loading" and selected_shoulder_angle is not None:
                if (
                    largest_loading_max_shoulder_angle is None
                    or selected_shoulder_angle > largest_loading_max_shoulder_angle
                ):
                    largest_loading_max_shoulder_angle = selected_shoulder_angle
                    loading_max_shoulder_timestamp = primary_frame_data["timestamp"]

            if phase_state == "takeoff" and selected_shoulder_angle is not None:
                if (
                    largest_takeoff_max_shoulder_angle is None
                    or selected_shoulder_angle > largest_takeoff_max_shoulder_angle
                ):
                    largest_takeoff_max_shoulder_angle = selected_shoulder_angle
                    takeoff_max_shoulder_timestamp = primary_frame_data["timestamp"]

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
    hip_normalized_score = max(0.0, 100.0 - abs(smallest_loading_min_hip_flexion - 70.0)) # Data to send
    # smallest_loading_min_hip_flexion # Data to send
    ideal_min_hip_flexion = 68.0
    ideal_max_hip_flexion = 72.0

    if ideal_min_hip_flexion <= smallest_loading_min_hip_flexion <= ideal_max_hip_flexion:
        hip_flexion_feedback = "hip flexion is in the ideal range"
    elif smallest_loading_min_hip_flexion > ideal_max_hip_flexion:
        hip_flexion_feedback = "lower your hip flexion angle by lowering your torso, you need more force"
    else:
        hip_flexion_feedback = "dont go too low for flexion angle"

    print(f"Hip flexion feedback: {hip_flexion_feedback}")
    print(f"Hip flexion normalized score: {hip_normalized_score:.1f}/100")

# Debug
else:
    print("Smallest loading_min_hip_flexion detected: not detected!")
    print("Hip flexion feedback: not detected!")
    print("Hip flexion normalized score: not detected!")

if smallest_loading_min_knee_flexion is not None:
    print(f"The minimum knee flexion angle during loading: {smallest_loading_min_knee_flexion:.1f}")
    knee_ideal_min = 83.0
    knee_ideal_max = 90.0
    knee_distance_from_range = max(
        knee_ideal_min - smallest_loading_min_knee_flexion,
        smallest_loading_min_knee_flexion - knee_ideal_max,
        0.0,
    )
    knee_normalized_score = max(0.0, 100.0 - knee_distance_from_range) # Data to send
    # smallest_loading_min_knee_flexion # Data to send

    if smallest_loading_min_knee_flexion < knee_ideal_min:
        knee_feedback = "Knees are going too low, you are wasting elastic energy"
    elif smallest_loading_min_knee_flexion > knee_ideal_max:
        knee_feedback = "Knees are not going low enough, you are limiting the force production you can get from your legs"
    else:
        knee_feedback = "Knee flexion is in the ideal range"

    print(f"Knee flexion feedback: {knee_feedback}")
    print(f"Knee flexion normalized score: {knee_normalized_score:.1f}/100")

# Debug
else:
    print("The minimum knee flexion angle during loading: not detected!")
    print("Knee flexion feedback: not detected!")
    print("Knee flexion normalized score: not detected!")

if largest_loading_max_shoulder_angle is not None:
    print(f"Analysis side used: {analysis_side if analysis_side is not None else 'not detected'}")
    print(f"The maximum shoulder angle during loading: {largest_loading_max_shoulder_angle:.1f}")
    print(f"The maximum shoulder angle during takeoff: {largest_takeoff_max_shoulder_angle:.1f}")
    shoulder_normalized_score = max(0.0, 100.0 - abs(largest_loading_max_shoulder_angle - 90.0))
    print(f"Shoulder angle normalized score: {shoulder_normalized_score:.1f}/100")

# Debug
else:
    print(f"Analysis side used: {analysis_side if analysis_side is not None else 'not detected'}")
    print("The maximum shoulder angle during loading: not detected!")
    print("Shoulder angle normalized score: not detected!")

if (
    largest_loading_max_shoulder_angle is not None
    and largest_takeoff_max_shoulder_angle is not None
    and loading_max_shoulder_timestamp is not None
    and takeoff_max_shoulder_timestamp is not None
):
    delta_angle = largest_takeoff_max_shoulder_angle - largest_loading_max_shoulder_angle
    delta_time = takeoff_max_shoulder_timestamp - loading_max_shoulder_timestamp
    if delta_time > 0:
        angular_velocity = int(delta_angle / delta_time) # Data to send
        print(f"Arm swing angular velocity (deg/s): {angular_velocity:.2f}")
        angular_velocity_score = max(0.0, min(100.0, (angular_velocity / 300.0) * 100.0)) # Data to send, maximum of 500
        print(f"Arm swing angular velocity score: {angular_velocity_score:.1f}/100")
    else:
        print("Arm swing angular velocity (deg/s): not detected!")
        print("Arm swing angular velocity score: not detected!")
else:
    print("Arm swing angular velocity (deg/s): not detected!")
    print("Arm swing angular velocity score: not detected!")
