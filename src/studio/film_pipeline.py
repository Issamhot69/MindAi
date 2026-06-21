import subprocess
import os
from datetime import datetime

class FilmMaker:
    def __init__(self):
        os.makedirs("public/videos", exist_ok=True)
        os.makedirs("public/audio", exist_ok=True)
        self.scenes = []
        print("🎬 FilmMaker prêt")

    def add_scene(self, image_path, text, voice="fr-FR-HenriNeural", name="scene"):
        """Ajoute une scène au film."""
        ts = datetime.now().strftime("%H%M%S")
        audio_path = f"public/audio/film_{name}_{ts}.mp3"
        video_path = f"/tmp/film_{name}_{ts}.mp4"
        
        # Génère la voix avec Edge TTS
        print(f"🎤 Voix pour {name}...")
        subprocess.run(["edge-tts", "--text", text, "--voice", voice, "--write-media", audio_path])
        
        # Crée la scène vidéo — format standardisé
        print(f"🖼 Scène {name}...")
        subprocess.run([
            "ffmpeg", "-y",
            "-loop", "1", "-i", image_path,
            "-i", audio_path,
            "-vf", "scale=720:1280:force_original_aspect_ratio=decrease,pad=720:1280:(ow-iw)/2:(oh-ih)/2:black",
            "-c:v", "libx264", "-profile:v", "baseline", "-level", "3.0",
            "-c:a", "aac", "-ar", "44100", "-ac", "2",
            "-shortest", "-pix_fmt", "yuv420p",
            "-r", "25",
            video_path
        ], capture_output=True)
        
        self.scenes.append(video_path)
        print(f"✅ {name} ajoutée")

    def render(self, output="public/videos/film_final.mp4"):
        """Assemble toutes les scènes en un film."""
        if not self.scenes:
            print("❌ Aucune scène")
            return None
        
        print(f"\n🎬 Assemblage de {len(self.scenes)} scènes...")
        
        # Re-encode chaque scène avec exactement les mêmes paramètres
        standardized = []
        for i, scene in enumerate(self.scenes):
            std_path = f"/tmp/film_std_{i}.mp4"
            subprocess.run([
                "ffmpeg", "-y", "-i", scene,
                "-c:v", "libx264", "-profile:v", "baseline", "-level", "3.0",
                "-c:a", "aac", "-ar", "44100", "-ac", "2", "-b:a", "128k",
                "-r", "25", "-pix_fmt", "yuv420p",
                "-s", "720x1280",
                std_path
            ], capture_output=True)
            standardized.append(std_path)
        
        # Crée le fichier liste
        list_path = "/tmp/film_concat.txt"
        with open(list_path, "w") as f:
            for s in standardized:
                f.write(f"file '{s}'\n")
        
        # Concat
        subprocess.run([
            "ffmpeg", "-y",
            "-f", "concat", "-safe", "0",
            "-i", list_path,
            "-c", "copy",
            output
        ], capture_output=True)
        
        if os.path.exists(output) and os.path.getsize(output) > 5000:
            print(f"\n🔥 FILM TERMINÉ : {output}")
            return output
        else:
            print("❌ Erreur assemblage")
            return None

if __name__ == "__main__":
    OUT = os.path.expanduser("~/Documents/ComfyUI/output")
    
    film = FilmMaker()
    
    # Voix disponibles Edge TTS :
    # fr-FR-HenriNeural (homme adulte)
    # fr-FR-DeniseNeural (femme)
    # fr-FR-EloiseNeural (jeune fille)
    # ar-MA-MounaNeural (femme arabe)
    # ar-MA-JamalNeural (homme arabe)
    
    film.add_scene(
        f"{OUT}/film_desert_puits_00001_.png",
        "Il faut se debarrasser de lui maintenant. Personne ne saura.",
        voice="fr-FR-HenriNeural",
        name="frere"
    )
    
    film.add_scene(
        f"{OUT}/film_marchand_00001_.png",
        "Vingt pieces d argent pour ce jeune garcon. C est mon dernier prix.",
        voice="ar-MA-JamalNeural",
        name="marchand"
    )
    
    film.add_scene(
        f"{OUT}/film_roi_egypte_00001_.png",
        "Cet homme possede un don extraordinaire. Il interpretera mes reves.",
        voice="fr-FR-HenriNeural",
        name="roi"
    )
    
    film.add_scene(
        f"{OUT}/film_palais_egypte_00001_.png",
        "Et c est ainsi que la verite triompha. La patience est la cle de toute reussite.",
        voice="fr-FR-DeniseNeural",
        name="narrateur"
    )
    
    result = film.render()
    if result:
        os.system(f"open {result}")
