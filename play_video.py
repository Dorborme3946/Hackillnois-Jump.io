import cv2

# Load video
cap = cv2.VideoCapture("barra_jump.mov")

# Check if video opened successfully
if not cap.isOpened():
    print("Error: Could not open video.")
    exit()

# Get original FPS
fps = cap.get(cv2.CAP_PROP_FPS)
# delay = int(1000 / fps) if fps > 0 else 33  # fallback to ~30 FPS

while True:
    ret, frame = cap.read()

    if not ret:
        break  # End of video

    cv2.imshow("Video", frame)

    # Press 'q' to quit
    if cv2.waitKey(delay) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()