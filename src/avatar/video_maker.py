import cv2
import numpy as np
import subprocess
import os
from datetime import datetime

def create_video(image_path: str, audio_path: str, title: str = "AI Mind") -> str:
    os.makedirs("public/videos", exist_ok=True)
    img = cv2.imread(image_path)
    if img is None:
        return None

    img = cv2.resize(img, (720, 1280))
    h, w = img.shape[:2]

    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", audio_path],
        capture_output=True, text=True
    )
    duration = float(result.stdout.strip())
    fps = 25
    total_frames = int(duration * fps)
    frames_dir = "/tmp/video_frames"
    os.makedirs(frames_dir, exist_ok=True)

    for i in range(total_frames):
        frame = img.copy()
        t = i / fps
        glow = abs(np.sin(t * 2 * np.pi))

        # Effet lumineux
        overlay = frame.copy()
        overlay[:, :, 2] = np.clip(overlay[:, :, 2] + int(glow * 15), 0, 255)
        frame = cv2.addWeighted(frame, 0.9, overlay, 0.1, 0)

        # Barres audio
        for b in range(18):
            bx = 20 + b * 38
            bh = int(abs(np.sin(t * 6 + b * 0.6)) * 35)
            color = (int(120 + glow * 135), int(40 + glow * 40), 255)
            cv2.rectangle(frame, (bx, h-80+35-bh), (bx+26, h-80+35), color, -1)
            cv2.rectangle(frame, (bx, h-80+35-bh), (bx+26, h-80+35), (255,255,255,30), 1)

        # Titre
        cv2.putText(frame, title, (w//2-90, h-20),
                   cv2.FONT_HERSHEY_SIMPLEX, 1.0, (200, 160, 255), 2)

        cv2.imwrite(f"{frames_dir}/f_{i:05d}.png", frame)

    output = f"public/videos/video_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
    subprocess.run([
        "ffmpeg", "-y", "-r", str(fps),
        "-i", f"{frames_dir}/f_%05d.png",
        "-i", audio_path,
        "-c:v", "libx264", "-c:a", "aac",
        "-shortest", "-pix_fmt", "yuv420p", output
    ], capture_output=True)
    subprocess.run(["rm", "-rf", frames_dir])
    return output
