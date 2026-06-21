import cv2
import numpy as np
import subprocess
import os
from datetime import datetime

def detect_mouth(image_path):
    """Détecte la zone de bouche avec OpenCV (cascade)."""
    img = cv2.imread(image_path)
    if img is None:
        return None, None
    
    img = cv2.resize(img, (512, 512))
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # Détecteur visage OpenCV
    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
    faces = face_cascade.detectMultiScale(gray, 1.1, 4)
    
    if len(faces) == 0:
        print("⚠️ Pas de visage détecté — utilisation centre image")
        h, w = img.shape[:2]
        return img, {"cx": w//2, "cy": int(h*0.72), "mw": 80, "mh": 20}
    
    x, y, fw, fh = faces[0]
    # Bouche = bas du visage
    cx = x + fw//2
    cy = y + int(fh * 0.80)
    mw = int(fw * 0.45)
    mh = int(fh * 0.12)
    
    print(f"✓ Visage détecté — bouche à ({cx},{cy})")
    return img, {"cx": cx, "cy": cy, "mw": mw, "mh": mh}

def create_lipsync(image_path: str, audio_path: str):
    print(f"\n🎬 LipSync en cours...")
    img, mouth = detect_mouth(image_path)
    if img is None:
        return None
    
    h, w = img.shape[:2]
    cx, cy = mouth["cx"], mouth["cy"]
    mw, mh = mouth["mw"], mouth["mh"]

    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", audio_path],
        capture_output=True, text=True
    )
    duration = float(result.stdout.strip())
    fps = 25
    total_frames = int(duration * fps)
    frames_dir = "/tmp/lipsync_frames"
    os.makedirs(frames_dir, exist_ok=True)

    print(f"   {total_frames} frames à générer...")
    for i in range(total_frames):
        frame = img.copy()
        t = i / fps
        open_amt = int(abs(np.sin(t * 12 * np.pi)) * mh * 0.7)

        if open_amt > 1:
            # Dessine ouverture bouche
            cv2.ellipse(frame, (cx, cy), (mw//2, open_amt//2 + 1), 0, 0, 360, (15, 8, 8), -1)
            # Dents (ligne blanche)
            if open_amt > 4:
                cv2.line(frame, (cx - mw//3, cy - open_amt//4), 
                        (cx + mw//3, cy - open_amt//4), (200, 200, 200), 1)

        cv2.imwrite(f"{frames_dir}/f_{i:05d}.png", frame)

    output = f"public/videos/lipsync_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
    subprocess.run([
        "ffmpeg", "-y", "-r", str(fps),
        "-i", f"{frames_dir}/f_%05d.png",
        "-i", audio_path,
        "-c:v", "libx264", "-c:a", "aac",
        "-shortest", "-pix_fmt", "yuv420p", output
    ], capture_output=True)
    subprocess.run(["rm", "-rf", frames_dir])
    print(f"✓ Vidéo créée : {output}")
    return output

if __name__ == "__main__":
    result = create_lipsync(
        "/Users/user/Documents/ComfyUI/output/alien_alien_bleu_00001_.png",
        "public/audio/test.wav"
    )
    if result:
        os.system(f"open {result}")
