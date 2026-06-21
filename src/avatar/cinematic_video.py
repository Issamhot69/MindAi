import cv2
import numpy as np
import subprocess
import os
from datetime import datetime

class CinematicVideo:
    def __init__(self):
        os.makedirs("public/videos", exist_ok=True)
        print("🎬 Cinematic Video prêt")

    def create(self, image_path: str, audio_path: str, title: str = "AI Mind"):
        print(f"\n🎬 Création vidéo cinématique...")
        img = cv2.imread(image_path)
        if img is None:
            print("❌ Image non trouvée")
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
        frames_dir = "/tmp/cinematic_frames"
        os.makedirs(frames_dir, exist_ok=True)

        print(f"   Génération {total_frames} frames...")
        for i in range(total_frames):
            frame = img.copy()
            t = i / fps

            # Effet lumineux pulsant
            glow = abs(np.sin(t * 3 * np.pi))
            overlay = frame.copy()
            overlay[:, :, 0] = np.clip(overlay[:, :, 0] + glow * 20, 0, 255)
            frame = cv2.addWeighted(frame, 0.85, overlay, 0.15, 0)

            # Barre audio en bas
            bar_h = 60
            bar_y = h - bar_h - 20
            for b in range(20):
                bar_x = 30 + b * 34
                bar_height = int(abs(np.sin(t * 8 + b * 0.5)) * 40)
                color = (int(150 + glow * 100), int(50 + glow * 50), 255)
                cv2.rectangle(frame, (bar_x, bar_y + bar_h - bar_height),
                             (bar_x + 20, bar_y + bar_h), color, -1)

            # Titre
            cv2.putText(frame, title, (w//2 - 80, h - 20),
                       cv2.FONT_HERSHEY_SIMPLEX, 1.2, (255, 255, 255), 2)

            cv2.imwrite(f"{frames_dir}/frame_{i:05d}.png", frame)

        print("   Assemblage vidéo...")
        output = f"public/videos/cinematic_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
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
    video = CinematicVideo()
    result = video.create(
        "/Users/user/Documents/ComfyUI/output/alien_sirene_spatiale_00001_.png",
        "public/audio/humain_20260614_173039.wav",
        title="AI Mind"
    )
    if result:
        os.system(f"open {result}")
