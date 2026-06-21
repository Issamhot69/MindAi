#!/usr/bin/env python3
import sys, os, json, subprocess

text = sys.argv[1]
voice_type = sys.argv[2]
output_path = sys.argv[3]

mp3_path = output_path if output_path.endswith(".mp3") else output_path.replace(".wav", ".mp3")

NATURE_SOUNDS = {
    "pluie":    "anoisesrc=color=pink:amplitude=0.4:duration=10",
    "tempete":  "anoisesrc=color=brown:amplitude=0.8:duration=10",
    "vent":     "anoisesrc=color=white:amplitude=0.3:duration=10",
    "feu":      "anoisesrc=color=pink:amplitude=0.5:duration=10",
    "ocean":    "anoisesrc=color=blue:amplitude=0.3:duration=10",
    "foret":    "anoisesrc=color=pink:amplitude=0.2:duration=10",
    "tonnerre": "anoisesrc=color=brown:amplitude=1.0:duration=10",
}

if voice_type in NATURE_SOUNDS:
    subprocess.run(["ffmpeg", "-f", "lavfi", "-i", NATURE_SOUNDS[voice_type],
                   "-codec:a", "libmp3lame", mp3_path, "-y", "-loglevel", "quiet"])
    print(json.dumps({"file": mp3_path, "status": "ok"}))
    sys.exit(0)

import torch
original_load = torch.load
def patched_load(*args, **kwargs):
    kwargs['weights_only'] = False
    return original_load(*args, **kwargs)
torch.load = patched_load

from TTS.api import TTS
tts = TTS(model_name="tts_models/fr/mai/tacotron2-DDC")
wav_path = mp3_path.replace(".mp3", "_raw.wav")
tts.tts_to_file(text=text, file_path=wav_path)

PITCH = {
    "humain": 1.0, "femme": 1.3, "enfant": 1.7,
    "lion": 0.3, "tigre": 0.28, "loup": 0.25, "ours": 0.2,
    "elephant": 0.15, "gorille": 0.22,
    "chien": 1.6, "chat": 1.9, "singe": 1.4,
    "oiseau": 2.2, "perroquet": 2.0, "souris": 3.0,
    "dauphin": 2.8, "poisson": 1.1, "requin": 0.18,
    "baleine": 0.1, "grenouille": 1.8,
    "robot": 0.8, "alien": 1.8, "dragon": 0.15,
    "ange": 2.5, "demon": 0.1, "zombie": 0.4,
}

pitch = PITCH.get(voice_type, 1.0)
if pitch != 1.0:
    pitched = wav_path.replace("_raw.wav", "_p.wav")
    os.system(f"ffmpeg -i {wav_path} -af 'asetrate=22050*{pitch},aresample=22050' {pitched} -y -loglevel quiet")
    wav_path = pitched

subprocess.run(["ffmpeg", "-i", wav_path, "-codec:a", "libmp3lame", "-qscale:a", "2", mp3_path, "-y", "-loglevel", "quiet"])
print(json.dumps({"file": mp3_path, "status": "ok"}))
