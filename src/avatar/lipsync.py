import os
import subprocess
from datetime import datetime

class AILipSync:
    def __init__(self):
        os.makedirs("public/videos", exist_ok=True)
        print("🎭 LipSync prêt")

    def create_talking_avatar(self, image_path: str, audio_path: str):
        output = f"public/videos/avatar_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
        print(f"\n🎬 Création avatar parlant...")
        print(f"   Image : {image_path}")
        print(f"   Audio : {audio_path}")

        cmd = [
            "ffmpeg",
            "-loop", "1",
            "-i", image_path,
            "-i", audio_path,
            "-c:v", "libx264",
            "-tune", "stillimage",
            "-c:a", "aac",
            "-b:a", "192k",
            "-pix_fmt", "yuv420p",
            "-shortest",
            "-y",
            output
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✓ Vidéo créée : {output}")
            return output
        else:
            print(f"❌ Erreur : {result.stderr}")
            return None

if __name__ == "__main__":
    import sys
    sys.path.append("src")
    from core.brain import AIMind
    from avatar.avatar import AIAvatar

    brain = AIMind("ahmed")
    avatar = AIAvatar(brain)
    lipsync = AILipSync()

    audio = avatar.generate_voice(
        "Bonjour, je suis AI Mind. Je peux transformer vos idées en réalité.",
        voice_type="humain"
    )

    result = lipsync.create_talking_avatar(
        "public/uploads/chines.jpg",
        audio
    )
    if result:
        import os
        os.system(f"open {result}")
