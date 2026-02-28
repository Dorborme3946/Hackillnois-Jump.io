from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from analyzer import analyze_video
import shutil, os

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {"message": "JumpIQ API is running"}

@app.post("/analyze")
async def analyze_jump(video: UploadFile = File(...), user_height: float = 70):
    # Use absolute path so OpenCV can always find the file
    base_dir = os.path.dirname(os.path.abspath(__file__))
    temp_path = os.path.join(base_dir, f"temp_{video.filename}")
    
    print(f"💾 Saving video to: {temp_path}")
    
    with open(temp_path, "wb") as buffer:
        shutil.copyfileobj(video.file, buffer)
    
    print(f"💾 File saved — size: {os.path.getsize(temp_path)} bytes")
    
    result = analyze_video(temp_path, user_height_inches=user_height)
    
    # Cleanup
    if os.path.exists(temp_path):
        os.remove(temp_path)
    converted = temp_path.rsplit(".", 1)[0] + "_converted.mp4"
    if os.path.exists(converted):
        os.remove(converted)
    
    return result