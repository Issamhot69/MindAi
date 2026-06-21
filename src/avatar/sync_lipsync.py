import os, time, httpx

SYNC_API_KEY = "sk-xJDchitVQiWcOOxW3uuviw.GLk-lBaR-o3F7nNGtsfgsjRrknHFpzBr"

def create_lipsync_video(video_url: str, audio_url: str, output_path: str):
    """Crée une vidéo lip sync via Sync Labs API."""
    os.environ["SYNC_API_KEY"] = SYNC_API_KEY
    from sync import Sync
    from sync.common import Video, Audio, GenerationOptions

    sync = Sync()
    print("🚀 Envoi à Sync Labs...")

    response = sync.generations.create(
        input=[Video(url=video_url), Audio(url=audio_url)],
        model="lipsync-2",
        options=GenerationOptions(sync_mode="cut_off"),
        output_file_name="aimind_lipsync"
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
        video_data = httpx.get(generation.output_url)
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "wb") as f:
            f.write(video_data.content)
        print(f"🔥 Vidéo sauvegardée : {output_path}")
        return output_path
    else:
        print(f"❌ Échec : {status}")
        return None

def create_lipsync_from_image(image_url: str, audio_url: str, output_path: str):
    """Crée une vidéo lip sync depuis une image + audio."""
    os.environ["SYNC_API_KEY"] = SYNC_API_KEY
    from sync import Sync
    from sync.common import Image, Audio, GenerationOptions

    sync = Sync()
    print("🚀 Envoi image + audio à Sync Labs...")

    response = sync.generations.create(
        input=[Image(url=image_url), Audio(url=audio_url)],
        model="sync-3",
        options=GenerationOptions(sync_mode="cut_off"),
        output_file_name="aimind_lipsync"
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
        video_data = httpx.get(generation.output_url)
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "wb") as f:
            f.write(video_data.content)
        print(f"🔥 Vidéo sauvegardée : {output_path}")
        return output_path
    else:
        print(f"❌ Échec : {status}")
        return None
