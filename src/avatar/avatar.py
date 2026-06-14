import os
from datetime import datetime

class AIAvatar:
    def __init__(self, brain):
        self.brain = brain
        self.tts = None
        os.makedirs("public/videos", exist_ok=True)
        os.makedirs("public/audio", exist_ok=True)
        print("🎭 AI Avatar prêt")

    def load_voice(self, model_name):
        from TTS.api import TTS
        print(f"⏳ Chargement voix : {model_name}")
        self.tts = TTS(model_name=model_name)
        print("✓ Voix chargée")

    def generate_voice(self, text: str, voice_type: str = "humain"):
        VOICES = {
            "humain":   {"model": "tts_models/fr/mai/tacotron2-DDC",     "emoji": "🗣"},
            "femme":    {"model": "tts_models/fr/mai/tacotron2-DDC",     "emoji": "👩"},
            "enfant":   {"model": "tts_models/multilingual/multi-dataset/xtts_v2", "emoji": "👦"},
            "lion":     {"model": "tts_models/fr/mai/tacotron2-DDC",     "emoji": "🦁", "pitch": 0.3},
            "oiseau":   {"model": "tts_models/fr/mai/tacotron2-DDC",     "emoji": "🐦", "pitch": 2.0},
            "loup":     {"model": "tts_models/fr/mai/tacotron2-DDC",     "emoji": "🐺", "pitch": 0.2},
            "robot":    {"model": "tts_models/fr/mai/tacotron2-DDC",     "emoji": "🤖", "pitch": 0.8},
        }

        config = VOICES.get(voice_type, VOICES["humain"])
        self.load_voice(config["model"])

        filename = f"public/audio/{voice_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.wav"
        print(f"\n{config['emoji']} Génération voix {voice_type}...")
        self.tts.tts_to_file(text=text, file_path=filename)

        pitch = config.get("pitch", 1.0)
        if pitch != 1.0:
            modified = filename.replace(".wav", "_modified.wav")
            os.system(f"ffmpeg -i {filename} -af 'asetrate=22050*{pitch},aresample=22050' {modified} -y -loglevel quiet")
            filename = modified

        print(f"✓ Audio sauvegardé : {filename}")
        return filename

    def list_voices(self):
        print("""
🎭 VOIX DISPONIBLES :
  humain  🗣  — Voix humaine naturelle
  femme   👩  — Voix féminine douce
  enfant  👦  — Voix enfant
  lion    🦁  — Voix grave puissante
  oiseau  🐦  — Voix aiguë légère
  loup    🐺  — Voix grave sauvage
  robot   🤖  — Voix robotique
        """)

if __name__ == "__main__":
    import sys
    sys.path.append("src")
    from core.brain import AIMind
    brain = AIMind("ahmed")
    avatar = AIAvatar(brain)
    avatar.list_voices()
    audio = avatar.generate_voice(
        "Bonjour, je suis AI Mind, votre assistant créatif personnel.",
        voice_type="humain"
    )
    print(f"✓ Audio : {audio}")

EXTRA_VOICES = {
    "alien":      {"emoji": "👽", "pitch": 1.8,  "desc": "Voix alien modulée"},
    "fantome":    {"emoji": "👻", "pitch": 0.6,  "desc": "Voix fantôme éthérée"},
    "dragon":     {"emoji": "🐉", "pitch": 0.15, "desc": "Voix dragon puissante"},
    "sirene":     {"emoji": "🧜", "pitch": 2.2,  "desc": "Voix sirène cristalline"},
    "demon":      {"emoji": "😈", "pitch": 0.1,  "desc": "Voix démon grave"},
    "ange":       {"emoji": "👼", "pitch": 2.5,  "desc": "Voix ange céleste"},
    "zombie":     {"emoji": "🧟", "pitch": 0.4,  "desc": "Voix zombie gutturale"},
    "esprit":     {"emoji": "🌀", "pitch": 1.5,  "desc": "Voix esprit mystique"},
    "ovni":       {"emoji": "🛸", "pitch": 3.0,  "desc": "Voix signal extraterrestre"},
    "oracle":     {"emoji": "🔮", "pitch": 0.7,  "desc": "Voix oracle ancestrale"},
}
