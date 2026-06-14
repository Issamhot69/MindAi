import os
import subprocess
from datetime import datetime

NATURE_SOUNDS = {
    "eau":      {"emoji": "💧", "desc": "Ruisseau qui coule"},
    "vent":     {"emoji": "🌬️", "desc": "Vent doux"},
    "tempete":  {"emoji": "⛈️", "desc": "Tempête dramatique"},
    "feu":      {"emoji": "🔥", "desc": "Feu crépitant"},
    "foret":    {"emoji": "🌲", "desc": "Forêt paisible"},
    "ocean":    {"emoji": "🌊", "desc": "Vagues de l'océan"},
    "pluie":    {"emoji": "🌧️", "desc": "Pluie douce"},
    "tonnerre": {"emoji": "⚡", "desc": "Orage puissant"},
}

def download_nature_sound(sound_type: str):
    """Génère un son de nature avec ffmpeg."""
    output = f"public/nature/{sound_type}.wav"
    if os.path.exists(output):
        return output

    print(f"🎵 Génération son : {sound_type}...")

    if sound_type == "pluie" or sound_type == "eau":
        cmd = f'ffmpeg -f lavfi -i "anoisesrc=color=pink:amplitude=0.3:duration=30" -af "lowpass=f=800,volume=0.5" {output} -y -loglevel quiet'
    elif sound_type == "vent":
        cmd = f'ffmpeg -f lavfi -i "anoisesrc=color=white:amplitude=0.2:duration=30" -af "lowpass=f=400,highpass=f=100,volume=0.4" {output} -y -loglevel quiet'
    elif sound_type == "tempete" or sound_type == "tonnerre":
        cmd = f'ffmpeg -f lavfi -i "anoisesrc=color=brown:amplitude=0.8:duration=30" -af "lowpass=f=600,volume=0.7" {output} -y -loglevel quiet'
    elif sound_type == "feu":
        cmd = f'ffmpeg -f lavfi -i "anoisesrc=color=pink:amplitude=0.4:duration=30" -af "bandpass=f=1000:width_type=h:w=800,volume=0.5" {output} -y -loglevel quiet'
    elif sound_type == "ocean" or sound_type == "foret":
        cmd = f'ffmpeg -f lavfi -i "anoisesrc=color=blue:amplitude=0.3:duration=30" -af "lowpass=f=500,volume=0.4" {output} -y -loglevel quiet'
    else:
        cmd = f'ffmpeg -f lavfi -i "anoisesrc=color=pink:amplitude=0.3:duration=30" {output} -y -loglevel quiet'

    os.system(cmd)
    print(f"✓ Son généré : {output}")
    return output

def mix_voice_with_nature(voice_file: str, nature_type: str):
    """Mixe la voix avec un son de nature en fond."""
    nature_file = download_nature_sound(nature_type)
    output = f"public/audio/mixed_{nature_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.wav"

    cmd = f'ffmpeg -i {voice_file} -i {nature_file} -filter_complex "[0:a]volume=1.5[voice];[1:a]volume=0.3[nature];[voice][nature]amix=inputs=2:duration=first" {output} -y -loglevel quiet'
    os.system(cmd)
    print(f"✓ Mix créé : {output}")
    return output

if __name__ == "__main__":
    for sound in ["pluie", "vent", "feu", "ocean"]:
        download_nature_sound(sound)
        print(f"✓ {sound} prêt")
