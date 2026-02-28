import argparse
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
import cv2
import time

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

# Landmark Extraction Stuff
# Mapping index with body parts (the index is defined by MediaPipe docs)
KEYPOINT_NAMES = [
    "nose", "left_eye_inner", "left_eye", "left_eye_outer",
    "right_eye_inner", "right_eye", "right_eye_outer",
    "left_ear", "right_ear",
    "mouth_left", "mouth_right",
    "left_shoulder", "right_shoulder",
    "left_elbow", "right_elbow",
    "left_wrist", "right_wrist",
    "left_pinky", "right_pinky",
    "left_index", "right_index",
    "left_thumb", "right_thumb",
    "left_hip", "right_hip",
    "left_knee", "right_knee",
    "left_ankle", "right_ankle",
    "left_heel", "right_heel",
    "left_foot_index", "right_foot_index"
]

def extract_landmarks(frame_index, fps, landmark_results, frame_height, frame_width):
    landmarks_dict = {}
    for landmark_idx, landmark in enumerate(landmark_results): 
        x_normalized = landmark.x
        y_normalized = landmark.y

        x_pixel = x_normalized * frame_width
        y_pixel = y_normalized * frame_height

        landmarks_dict[KEYPOINT_NAMES[landmark_idx]] = {
            "x_pixel": x_pixel,
            "y_pixel": y_pixel,
            "z_pixel": landmark.z, # Z = depth
            "visibility": landmark.visibility
        }
    frame_data = {
        "frame_index": frame_index,
        "timestamp": frame_index / fps,
        "landmarks": landmarks_dict
    }
    return frame_data


# Setting up argparse
parser = argparse.ArgumentParser(description="A testing model for mediapipe")
parser.add_argument("--model", default="pose_landmarker_heavy.task", help="Path to the model file.")
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
cap = cv2.VideoCapture("volleyball_input.mp4")
frame_index = 0
all_landmark_frames = []
fps = cap.get(cv2.CAP_PROP_FPS)
if (fps == 0 or fps == None):
    fps = 30

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
    blank_canvas = np.zeros((frame_height, frame_width, 3), dtype=np.uint8)

    # Extract landmark data
    if detection_results.pose_landmarks:
        # pose_landmarks is a list of detected poses for THIS frame.
        # frame_index is a video frame counter, not a pose index.
        for pose_landmarks in detection_results.pose_landmarks:
            frame_data = extract_landmarks(
                frame_index, fps, pose_landmarks, frame_height, frame_width
            )
            all_landmark_frames.append(frame_data)
            print(frame_data["landmarks"]["nose"])

    frame_index += 1

    # Annotate the detected landmarks on the original Frame
    annotated_frame = draw_landmarks_on_image(frame_rgb, detection_results)

    annotated_frame_BGR = cv2.cvtColor(annotated_frame, cv2.COLOR_RGB2BGR)
    cv2.putText(
        blank_canvas,
        "XYZ: x,y from image; z encoded by color/radius",
        (10, 30),
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


