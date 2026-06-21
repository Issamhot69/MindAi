import time, os
os.environ["SYNC_API_KEY"] = "sk-xJDchitVQiWcOOxW3uuviw.GLk-lBaR-o3F7nNGtsfgsjRrknHFpzBr"

from sync import Sync
from sync.common import Video, Audio, GenerationOptions

sync = Sync()

print("🚀 Envoi à Sync Labs...")
response = sync.generations.create(
    input=[
        Video(url="https://assets.sync.so/docs/example-video.mp4"),
        Audio(url="https://assets.sync.so/docs/example-audio.wav")
    ],
    model="lipsync-2",
    options=GenerationOptions(sync_mode="cut_off"),
    output_file_name="test_aimind"
)

job_id = response.id
print(f"✓ Job créé : {job_id}")

generation = sync.generations.get(job_id)
status = generation.status
while status not in ['COMPLETED', 'FAILED', 'REJECTED']:
    print(f"⏳ {status}...")
    time.sleep(10)
    generation = sync.generations.get(job_id)
    status = generation.status

if status == 'COMPLETED':
    print(f"🔥 VIDÉO PRÊTE : {generation.output_url}")
    import httpx
    video = httpx.get(generation.output_url)
    os.makedirs("public/videos", exist_ok=True)
    with open("public/videos/sync_test.mp4", "wb") as f:
        f.write(video.content)
    print("✓ Sauvegardée : public/videos/sync_test.mp4")
    os.system("open public/videos/sync_test.mp4")
else:
    print(f"❌ Échec : {status}")
