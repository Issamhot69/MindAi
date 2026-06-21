import os
import sys
sys.path.append("src")
from datetime import datetime

def generate_voice_file(text: str, voice_type: str) -> str:
    """Génère un fichier audio depuis un texte."""
    import torch
    import TTS.utils.radam
    torch.serialization.add_safe_globals([TTS.utils.radam.RAdam])
    from TTS.api import TTS

    MODELS = {
        "humain": "tts_models/fr/mai/tacotron2-DDC",
        "femme": "tts_models/fr/mai/tacotron2-DDC",
        "lion": "tts_models/fr/mai/tacotron2-DDC",
        "oiseau": "tts_models/fr/mai/tacotron2-DDC",
        "robot": "tts_models/fr/mai/tacotron2-DDC",
    }

    PITCH = {
        "humain": 1.0,
        "femme": 1.2,
        "lion": 0.3,
        "oiseau": 2.0,
        "robot": 0.8,
    }

    os.makedirs("public/audio", exist_ok=True)
    tts = TTS(model_name=MODELS.get(voice_type, MODELS["humain"]))
    filename = f"public/audio/{voice_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.wav"
    tts.tts_to_file(text=text, file_path=filename)

    pitch = PITCH.get(voice_type, 1.0)
    if pitch != 1.0:
        modified = filename.replace(".wav", "_mod.wav")
        os.system(f"ffmpeg -i {filename} -af 'asetrate=22050*{pitch},aresample=22050' {modified} -y -loglevel quiet")
        filename = modified

    return filename
