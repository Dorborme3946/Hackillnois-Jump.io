import cv2
import os
from dataclasses import dataclass, field


@dataclass
class VideoValidationResult:
    is_valid: bool
    width: int
    height: int
    fps: float
    frame_count: int
    duration_seconds: float
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


class VideoValidator:
    MIN_HEIGHT = 480
    MIN_FPS = 24  # Slightly relaxed from spec for prototype
    MAX_DURATION = 60
    SUPPORTED_FORMATS = [".mp4", ".mov", ".avi", ".webm"]

    def validate(self, video_path: str) -> VideoValidationResult:
        errors = []
        warnings = []

        ext = os.path.splitext(video_path)[1].lower()
        if ext not in self.SUPPORTED_FORMATS:
            errors.append(f"Unsupported format: {ext}. Supported: {', '.join(self.SUPPORTED_FORMATS)}")

        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            return VideoValidationResult(False, 0, 0, 0, 0, 0,
                                         ["Could not open video file"], [])

        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = frame_count / fps if fps > 0 else 0
        cap.release()

        actual_height = max(width, height)

        if actual_height < self.MIN_HEIGHT:
            errors.append(f"Resolution too low: {width}x{height}. Minimum height: 480px")
        if fps < self.MIN_FPS:
            errors.append(f"Frame rate too low: {fps:.1f} FPS. Minimum: {self.MIN_FPS} FPS")
        if duration > self.MAX_DURATION:
            warnings.append(f"Video is long ({duration:.1f}s). Processing may take longer.")
        if duration < 0.5:
            errors.append("Video is too short to analyze a jump.")
        if duration > 30:
            warnings.append("Recommend 1–30 second clips for best results.")

        return VideoValidationResult(
            is_valid=len(errors) == 0,
            width=width,
            height=height,
            fps=fps,
            frame_count=frame_count,
            duration_seconds=round(duration, 2),
            errors=errors,
            warnings=warnings,
        )
