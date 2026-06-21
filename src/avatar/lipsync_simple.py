import cv2
import numpy as np
import subprocess
import os
from datetime import datetime

class SimpleLipSync:
    def __init__(self):
        os.makedirs("public/videos", exist_ok=True)
        print("🎭 LipSync Simple prêt")

    def animate_lips(self, image_path: str, audio_path: str):
        print(f"\n🎬 Animation lèvres en cours...")
        img = cv2.imread(image_path)
        if img is None:
            print("❌ Image non trouvée")
            return None

        # Redimensionner pour éviter problèmes mémoire
        img = cv2.resize(img, (512, 512))
        h, w = img.shape[:2]

        # Durée audio
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

        # Zone bouche
        my = int(h * 0.72)
        mx = int(w * 0.30)
        mw = int(w * 0.40)
        mh = int(h * 0.08)

        print(f"   Génération {total_frames} frames...")
        for i in range(total_frames):
            frame = img.copy()
            t = i / fps
            open_amt = int(abs(np.sin(t * 8 * np.pi)) * mh * 0.5)

            if open_amt > 2:
                y1 = my
                y2 = min(my + open_amt, h)
                x1 = mx
                x2 = min(mx + mw, w)
                if y2 > y1:
                    roi = frame[y1:y2, x1:x2].copy()
                    dark = (roi * 0.5).astype(np.uint8)
                    frame[y1:y2, x1:x2] = dark

            cv2.imwrite(f"{frames_dir}/frame_{i:05d}.png", frame)

        print("   Assemblage vidéo...")
        output = f"public/videos/lipsync_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
        cmd = [
            "ffmpeg", "-y",
            "-r", str(fps),
            "-i", f"{frames_dir}/frame_%05d.png",
            "-i", audio_path,
            "-c:v", "libx264",
            "-c:a", "aac",
            "-shortest",
            "-pix_fmt", "yuv420p",
            output
        ]
        subprocess.run(cmd, capture_output=True)
        subprocess.run(["rm", "-rf", frames_dir])
        print(f"✓ Vidéo créée : {output}")
        return output

if __name__ == "__main__":
    lipsync = SimpleLipSync()
    result = lipsync.animate_lips(
        "/Users/user/Documents/ComfyUI/output/alien_sirene_spatiale_00001_.png",
        "public/audio/humain_20260614_173039.wav"
    )
    if result:
        os.system(f"open {result}")
