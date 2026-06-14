import os
import torch
from diffusers import StableDiffusionPipeline
from PIL import Image
from datetime import datetime

class AIStudio:
    def __init__(self, brain):
        self.brain = brain
        os.makedirs("public/images", exist_ok=True)
        self.pipe = None
        print("🎨 AI Studio prêt — mode local")

    def load_model(self):
        if self.pipe:
            return
        print("⏳ Chargement du modèle IA local...")
        self.pipe = StableDiffusionPipeline.from_pretrained(
            "runwayml/stable-diffusion-v1-5",
            torch_dtype=torch.float32
        )
        self.pipe = self.pipe.to("mps")
        print("✓ Modèle chargé sur Apple Silicon")

    def generate_image(self, prompt):
        self.load_model()
        style = self.brain.recall("style") or "réaliste"
        full_prompt = f"{prompt}, style {style}, 4K, haute qualité"
        print(f"\n🖼  Génération en cours...")
        print(f"   Prompt : {full_prompt}")
        image = self.pipe(full_prompt).images[0]
        filename = f"public/images/{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        image.save(filename)
        self.brain.remember("derniere_image", filename)
        print(f"✓ Image sauvegardée : {filename}")
        return filename

if __name__ == "__main__":
    import sys
    sys.path.append("src")
    from core.brain import AIMind
    brain = AIMind("ahmed")
    brain.remember("style", "cinématique réaliste")
    studio = AIStudio(brain)
    studio.generate_image("un lion dans une forêt brumeuse au coucher du soleil")
