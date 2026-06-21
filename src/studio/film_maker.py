import subprocess
import os

ALIEN_VIDEO = os.path.expanduser("~/Documents/ComfyUI/custom_nodes/LivePortrait/animations/alien_alien_bleu_00001_--d6.mp4")
DIALOGUE = "public/audio/film_dialogue.mp3"
OUTPUT = "public/videos/film_ai_mind.mp4"

os.makedirs("public/videos", exist_ok=True)

# Étape 1 : Créer un titre d'intro (3 secondes)
print("🎬 Étape 1 : Création du titre...")
subprocess.run([
    "ffmpeg", "-y",
    "-f", "lavfi", "-i", "color=c=black:s=720x1280:d=3",
    "-vf", "drawtext=text='AI MIND':fontsize=72:fontcolor=white:x=(w-text_w)/2:y=(h-text_h)/2-40,drawtext=text='Le Premier Film IA':fontsize=28:fontcolor=#a78bfa:x=(w-text_w)/2:y=(h-text_h)/2+40",
    "-c:v", "libx264", "-pix_fmt", "yuv420p",
    "/tmp/intro.mp4"
], capture_output=True)

# Étape 2 : Redimensionner la vidéo alien en format vertical
print("🎬 Étape 2 : Préparation de la scène alien...")
subprocess.run([
    "ffmpeg", "-y",
    "-i", ALIEN_VIDEO,
    "-vf", "scale=720:1280:force_original_aspect_ratio=decrease,pad=720:1280:(ow-iw)/2:(oh-ih)/2:black",
    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-an",
    "/tmp/alien_scene.mp4"
], capture_output=True)

# Étape 3 : Ajouter le dialogue sur la scène alien
print("🎬 Étape 3 : Ajout du dialogue...")
subprocess.run([
    "ffmpeg", "-y",
    "-i", "/tmp/alien_scene.mp4",
    "-i", DIALOGUE,
    "-c:v", "copy", "-c:a", "aac",
    "-shortest",
    "/tmp/alien_with_voice.mp4"
], capture_output=True)

# Étape 4 : Créer un outro (3 secondes)
print("🎬 Étape 4 : Création du générique...")
subprocess.run([
    "ffmpeg", "-y",
    "-f", "lavfi", "-i", "color=c=black:s=720x1280:d=3",
    "-vf", "drawtext=text='Créé avec AI Mind':fontsize=36:fontcolor=#a78bfa:x=(w-text_w)/2:y=(h-text_h)/2-20,drawtext=text='aimind.ai':fontsize=24:fontcolor=white:x=(w-text_w)/2:y=(h-text_h)/2+30",
    "-c:v", "libx264", "-pix_fmt", "yuv420p",
    "/tmp/outro.mp4"
], capture_output=True)

# Étape 5 : Assembler le film
print("🎬 Étape 5 : Montage final...")
with open("/tmp/film_list.txt", "w") as f:
    f.write("file '/tmp/intro.mp4'\n")
    f.write("file '/tmp/alien_with_voice.mp4'\n")
    f.write("file '/tmp/outro.mp4'\n")

subprocess.run([
    "ffmpeg", "-y",
    "-f", "concat", "-safe", "0",
    "-i", "/tmp/film_list.txt",
    "-c:v", "libx264", "-c:a", "aac",
    "-pix_fmt", "yuv420p",
    OUTPUT
], capture_output=True)

print(f"\n🔥 FILM TERMINÉ : {OUTPUT}")
os.system(f"open {OUTPUT}")
