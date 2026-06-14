import os
import torch
import soundfile as sf
from datetime import datetime
from transformers import AutoProcessor, MusicgenForConditionalGeneration

class AIMusic:
    def __init__(self):
        self.model = None
        self.processor = None
        os.makedirs("public/music", exist_ok=True)
        print("🎵 AI Music prêt")

    def load_model(self):
        if self.model:
            return
        print("⏳ Chargement MusicGen...")
        self.processor = AutoProcessor.from_pretrained("facebook/musicgen-small")
        self.model = MusicgenForConditionalGeneration.from_pretrained("facebook/musicgen-small")
        print("✓ MusicGen chargé")

    def generate(self, description: str, duration: int = 10):
        self.load_model()
        print(f"\n🎵 Génération musique : {description}")
        inputs = self.processor(text=[description], padding=True, return_tensors="pt")
        tokens = duration * 50
        with torch.no_grad():
            audio = self.model.generate(**inputs, max_new_tokens=tokens)
        audio_data = audio[0, 0].numpy()
        filename = f"public/music/music_{datetime.now().strftime('%Y%m%d_%H%M%S')}.wav"
        sf.write(filename, audio_data, samplerate=32000)
        print(f"✓ Musique sauvegardée : {filename}")
        return filename

MUSIC_STYLES = {
    "cinematique": {
        "emoji": "🎬",
        "nom": "Cinématique",
        "prompt": "epic cinematic orchestral music, dramatic strings, powerful brass, emotional, film score"
    },
    "ambiante": {
        "emoji": "🌿",
        "nom": "Ambiante",
        "prompt": "peaceful ambient music, soft piano, nature sounds, relaxing, meditation, gentle"
    },
    "electronique": {
        "emoji": "⚡",
        "nom": "Électronique",
        "prompt": "modern electronic music, energetic beat, synthesizer, TikTok style, upbeat, dance"
    },
    "alien": {
        "emoji": "👽",
        "nom": "Extraterrestre",
        "prompt": "otherworldly alien music, strange sounds, cosmic, ethereal, sci-fi, mysterious frequencies"
    },
    "nature": {
        "emoji": "🌊",
        "nom": "Nature",
        "prompt": "nature soundscape, birds, water, wind, forest, peaceful, organic sounds"
    },
    "mystique": {
        "emoji": "🔮",
        "nom": "Mystique",
        "prompt": "mystical fantasy music, magical, enchanted forest, fairy tale, dreamy, soft bells"
    }
}

if __name__ == "__main__":
    music = AIMusic()
    f = music.generate("epic cinematic orchestral music, dramatic strings", duration=8)
    print(f"✓ Fichier : {f}")
    import os
    os.system(f"open {f}")
