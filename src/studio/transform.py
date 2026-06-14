import os
import torch
from diffusers import StableDiffusionImg2ImgPipeline
from PIL import Image
from datetime import datetime

class AITransform:
    def __init__(self, brain):
        self.brain = brain
        self.pipe = None
        os.makedirs("public/images", exist_ok=True)
        print("🔄 AI Transform prêt")

    def load_model(self):
        if self.pipe:
            return
        print("⏳ Chargement modèle transformation...")
        self.pipe = StableDiffusionImg2ImgPipeline.from_pretrained(
            "runwayml/stable-diffusion-v1-5",
            torch_dtype=torch.float32,
            safety_checker=None
        ).to("mps")
        print("✓ Modèle chargé")

    def transform(self, image_path, prompt, strength=0.65, progress_cb=None):
        self.load_model()
        full_prompt = f"{prompt}, ultra realistic, 8K, cinematic lighting, sharp focus, professional photography"
        negative = "cartoon, anime, blurry, ugly, deformed, watermark, bad quality"
        print(f"\n🔄 Transformation : {full_prompt}")

        image = Image.open(image_path).convert("RGB").resize((512, 512))

        def step_cb(pipe, step, timestep, kwargs):
            if progress_cb:
                pct = int((step / 50) * 100)
                progress_cb(pct, f"Transformation... {pct}%")
            return kwargs

        result = self.pipe(
            prompt=full_prompt,
            negative_prompt=negative,
            image=image,
            strength=strength,
            guidance_scale=8.5,
            num_inference_steps=50,
            callback_on_step_end=step_cb
        ).images[0]

        filename = f"public/images/transform_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        result.save(filename)
        print(f"✓ Sauvegardé : {filename}")
        return filename
