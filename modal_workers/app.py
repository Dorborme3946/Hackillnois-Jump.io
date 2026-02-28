"""
Modal app definition — entry point for all GPU workers.

Deploy with:
    modal deploy modal_workers/app.py

Requires MODAL_TOKEN_ID and MODAL_TOKEN_SECRET env vars (or modal setup).
"""

import modal

# Shared image with all CV / ML dependencies
jumpai_image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install(
        "ultralytics==8.2.0",
        "torch==2.3.0",
        "torchvision==0.18.0",
        "opencv-python-headless==4.10.0.84",
        "numpy==1.26.4",
        "scipy==1.13.1",
        "httpx==0.27.2",
    )
)

app = modal.App("jumpai", image=jumpai_image)

# Import workers so Modal registers their functions
from modal_workers import pose_worker, scoring_worker  # noqa: F401, E402
