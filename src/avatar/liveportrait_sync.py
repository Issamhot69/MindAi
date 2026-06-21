import subprocess
import os
from datetime import datetime

LIVEPORTRAIT_DIR = os.path.expanduser("~/Documents/ComfyUI/custom_nodes/LivePortrait")

def animate_face(source_image: str, driving_video: str) -> str:
    """Anime une image avec LivePortrait sur Mac Apple Silicon."""
    os.makedirs("public/videos", exist_ok=True)
    
    env = os.environ.copy()
    env["PYTORCH_ENABLE_MPS_FALLBACK"] = "1"
    
    print(f"🎬 LivePortrait : animation en cours...")
    result = subprocess.run(
        ["python", "inference.py", "-s", source_image, "-d", driving_video],
        capture_output=True, text=True, cwd=LIVEPORTRAIT_DIR, env=env
    )
    
    if result.returncode != 0:
        print(f"❌ Erreur : {result.stderr[-300:]}")
        return None
    
    # Trouve la vidéo générée
    anim_dir = os.path.join(LIVEPORTRAIT_DIR, "animations")
    videos = sorted([f for f in os.listdir(anim_dir) if f.endswith(".mp4") and "concat" not in f], key=lambda x: os.path.getmtime(os.path.join(anim_dir, x)), reverse=True)
    
    if videos:
        src = os.path.join(anim_dir, videos[0])
        dst = f"public/videos/liveportrait_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
        import shutil
        shutil.copy2(src, dst)
        print(f"✅ Vidéo sauvegardée : {dst}")
        return dst
    return None
