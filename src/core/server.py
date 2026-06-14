import os, sys, json, shutil, urllib.request, threading, asyncio
sys.path.append("src")

from fastapi import FastAPI, UploadFile, File, Form
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, StreamingResponse
from studio.styles import STYLES
import uvicorn

app = FastAPI(title="AI Mind")
COMFY_URL = "http://localhost:8188"
OUTPUT_DIR = os.path.expanduser("~/Documents/ComfyUI/output")
INPUT_DIR = os.path.expanduser("~/Documents/ComfyUI/input")

os.makedirs("public/images", exist_ok=True)
os.makedirs("public/uploads", exist_ok=True)
app.mount("/images", StaticFiles(directory="public/images"), name="images")

progress_store = {"value": 0, "status": "idle", "last_file": ""}

def send_to_comfy(image_path, style_key):
    style = STYLES[style_key]
    workflow = {
        "3": {"class_type": "KSampler", "inputs": {
            "cfg": style["cfg"], "denoise": style["denoise"],
            "latent_image": ["5", 0], "model": ["4", 0],
            "negative": ["7", 0], "positive": ["6", 0],
            "sampler_name": "euler", "scheduler": "karras",
            "seed": 42, "steps": style["steps"]
        }},
        "4": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": "RealisticVision_V6.safetensors"}},
        "5": {"class_type": "VAEEncode", "inputs": {"pixels": ["8", 0], "vae": ["4", 2]}},
        "6": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["4", 1], "text": style["prompt"]}},
        "7": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["4", 1], "text": style["negative"]}},
        "8": {"class_type": "LoadImage", "inputs": {"image": os.path.basename(image_path), "upload": "image"}},
        "9": {"class_type": "VAEDecode", "inputs": {"samples": ["3", 0], "vae": ["4", 2]}},
        "10": {"class_type": "SaveImage", "inputs": {"filename_prefix": f"aimind_{style_key}", "images": ["9", 0]}}
    }
    data = json.dumps({"prompt": workflow}).encode()
    req = urllib.request.Request(f"{COMFY_URL}/prompt", data=data, headers={"Content-Type": "application/json"})
    resp = urllib.request.urlopen(req)
    result = json.loads(resp.read())
    return result.get("prompt_id")

def wait_for_result(prompt_id, style_key):
    import time
    for i in range(120):
        time.sleep(1)
        pct = min(95, i * 2)
        progress_store["value"] = pct
        progress_store["status"] = f"Génération {STYLES[style_key]['emoji']}... {pct}%"
        try:
            req = urllib.request.Request(f"{COMFY_URL}/history/{prompt_id}")
            resp = urllib.request.urlopen(req)
            data = json.loads(resp.read())
            if prompt_id in data:
                entry = data[prompt_id]
                if entry.get("status", {}).get("completed"):
                    outputs = entry.get("outputs", {})
                    for node_id, node_out in outputs.items():
                        if "images" in node_out:
                            img = node_out["images"][0]
                            src = os.path.join(OUTPUT_DIR, img["filename"])
                            dst = f"public/images/{img['filename']}"
                            shutil.copy2(src, dst)
                            progress_store["value"] = 100
                            progress_store["status"] = "done"
                            progress_store["last_file"] = img["filename"]
                            return
        except:
            pass
    progress_store["status"] = "done"

@app.get("/progress")
async def progress():
    async def stream():
        while True:
            v = progress_store["value"]
            s = progress_store["status"]
            f = progress_store["last_file"]
            yield f"data: {v}|{s}|{f}\n\n"
            await asyncio.sleep(0.5)
            if s == "done":
                break
    return StreamingResponse(stream(), media_type="text/event-stream")

@app.post("/transform")
async def transform(file: UploadFile = File(...), style: str = Form(...)):
    filename = file.filename
    upload_path = os.path.join(INPUT_DIR, filename)
    content = await file.read()
    from PIL import Image
    import io
    img = Image.open(io.BytesIO(content)).convert("RGB").resize((512, 512))
    img.save(upload_path)
    progress_store["value"] = 0
    progress_store["status"] = "Démarrage..."
    progress_store["last_file"] = ""
    def run():
        pid = send_to_comfy(upload_path, style)
        wait_for_result(pid, style)
    threading.Thread(target=run).start()
    return {"status": "started"}

@app.get("/", response_class=HTMLResponse)
def home():
    images = sorted([f for f in os.listdir("public/images") if f.endswith(".png")], reverse=True)[:12]
    imgs_html = "".join([f'<img src="/images/{f}" onclick="openImg(this.src)" style="width:200px;margin:6px;border-radius:12px;cursor:pointer"/>' for f in images])
    styles_html = "".join([f'''
    <div class="style-card" onclick="selectStyle('{k}')" id="style-{k}">
        <div class="style-emoji">{v["emoji"]}</div>
        <div class="style-name">{v["nom"]}</div>
    </div>''' for k, v in STYLES.items()])

    return f"""
    <html>
    <head>
        <title>AI Mind Studio</title>
        <style>
            *{{box-sizing:border-box;margin:0;padding:0}}
            body{{font-family:sans-serif;background:#0a0a0a;color:white;padding:40px}}
            h1{{color:#a78bfa;margin-bottom:6px;font-size:28px}}
            .sub{{color:#555;margin-bottom:30px}}
            .upload-zone{{border:2px dashed #333;border-radius:16px;padding:50px;text-align:center;cursor:pointer;margin-bottom:24px;transition:border 0.2s}}
            .upload-zone:hover{{border-color:#a78bfa}}
            .upload-zone input{{display:none}}
            .upload-icon{{font-size:52px;margin-bottom:12px}}
            .upload-title{{font-size:18px;color:#a78bfa;font-weight:600;margin-bottom:6px}}
            .upload-sub{{font-size:13px;color:#444}}
            .preview-box{{display:none;text-align:center;margin-bottom:24px}}
            .preview-box img{{width:180px;border-radius:12px;border:2px solid #7c3aed}}
            .preview-box p{{color:#a78bfa;font-size:13px;margin-top:8px}}
            .styles-grid{{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:24px}}
            .style-card{{background:#1a1a1a;border:2px solid #222;border-radius:12px;padding:20px;text-align:center;cursor:pointer;transition:all 0.2s}}
            .style-card:hover{{border-color:#7c3aed;background:#1f1a2e}}
            .style-card.selected{{border-color:#a78bfa;background:#1f1a2e}}
            .style-emoji{{font-size:32px;margin-bottom:8px}}
            .style-name{{font-size:14px;color:#888}}
            .style-card.selected .style-name{{color:#a78bfa}}
            .btn{{width:100%;padding:16px;border-radius:12px;border:none;background:#7c3aed;color:white;font-size:16px;cursor:pointer;margin-bottom:20px}}
            .btn:hover{{background:#6d28d9}}
            .btn:disabled{{background:#333;cursor:not-allowed}}
            .progress-wrap{{background:#1a1a1a;border-radius:10px;overflow:hidden;height:36px;margin-bottom:8px;display:none;position:relative}}
            .progress-bar{{height:100%;background:linear-gradient(90deg,#7c3aed,#a78bfa);width:0%;transition:width 0.4s}}
            .progress-text{{position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);font-size:14px;font-weight:600;color:white}}
            .spinner{{display:inline-block;width:14px;height:14px;border:2px solid #a78bfa;border-top-color:transparent;border-radius:50%;animation:spin 0.8s linear infinite;margin-right:8px;vertical-align:middle}}
            @keyframes spin{{to{{transform:rotate(360deg)}}}}
            .status-line{{font-size:14px;color:#a78bfa;margin-bottom:20px;min-height:22px;text-align:center}}
            .result-box{{display:none;text-align:center;margin-bottom:24px}}
            .result-box img{{width:300px;border-radius:16px;border:2px solid #a78bfa}}
            .result-box p{{color:#a78bfa;margin-top:10px;font-size:14px}}
            .gallery{{display:flex;flex-wrap:wrap;margin-top:10px}}
            .lightbox{{display:none;position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.92);z-index:99;align-items:center;justify-content:center}}
            .lightbox img{{max-width:90%;max-height:90%;border-radius:16px}}
            .lightbox.open{{display:flex}}
            .change-btn{{background:none;border:1px solid #333;color:#666;padding:6px 14px;border-radius:6px;cursor:pointer;font-size:12px;margin-top:8px}}
        </style>
    </head>
    <body>
        <h1>🧠 AI Mind Studio</h1>
        <p class="sub">Transformez vos photos avec l'IA — Choisissez votre style</p>

        <div class="upload-zone" id="uploadZone" onclick="document.getElementById('imgfile').click()">
            <input type="file" id="imgfile" accept="image/*" onchange="previewImage(this)"/>
            <div class="upload-icon">📁</div>
            <div class="upload-title">Cliquez pour charger votre photo</div>
            <div class="upload-sub">JPG, PNG — glissez ou cliquez</div>
        </div>

        <div class="preview-box" id="previewBox">
            <img id="preview" src=""/>
            <p>✓ Photo chargée</p>
            <button class="change-btn" onclick="document.getElementById('imgfile').click()">Changer</button>
        </div>

        <p style="color:#666;font-size:14px;margin-bottom:12px">Choisissez un style :</p>
        <div class="styles-grid">{styles_html}</div>

        <button class="btn" id="transformBtn" onclick="transformImg()" disabled>✨ Transformer</button>

        <div class="progress-wrap" id="pw"><div class="progress-bar" id="pb"></div><div class="progress-text" id="pt">0%</div></div>
        <div class="status-line" id="pl"></div>

        <div class="result-box" id="resultBox">
            <img id="resultImg" src=""/>
            <p>✓ Transformation terminée !</p>
        </div>

        <div class="gallery">{imgs_html}</div>
        <div class="lightbox" id="lb" onclick="this.classList.remove('open')"><img id="lbimg" src=""/></div>

        <script>
            let selectedStyle = null;
            function selectStyle(s) {{
                document.querySelectorAll('.style-card').forEach(c => c.classList.remove('selected'));
                document.getElementById('style-'+s).classList.add('selected');
                selectedStyle = s;
                checkReady();
            }}
            function checkReady() {{
                const hasFile = document.getElementById('imgfile').files.length > 0;
                document.getElementById('transformBtn').disabled = !(hasFile && selectedStyle);
            }}
            function previewImage(input) {{
                const file = input.files[0];
                if (!file) return;
                document.getElementById('preview').src = URL.createObjectURL(file);
                document.getElementById('uploadZone').style.display = 'none';
                document.getElementById('previewBox').style.display = 'block';
                checkReady();
            }}
            function openImg(src) {{
                document.getElementById('lbimg').src = src;
                document.getElementById('lb').classList.add('open');
            }}
            async function transformImg() {{
                const file = document.getElementById('imgfile').files[0];
                if (!file || !selectedStyle) return;
                document.getElementById('pw').style.display = 'block';
                document.getElementById('pb').style.width = '0%';
                document.getElementById('pt').innerText = '0%';
                document.getElementById('pl').innerHTML = '<span class="spinner"></span>Transformation en cours...';
                document.getElementById('resultBox').style.display = 'none';
                document.getElementById('transformBtn').disabled = true;
                const fd = new FormData();
                fd.append('file', file);
                fd.append('style', selectedStyle);
                await fetch('/transform', {{method:'POST', body:fd}});
                const es = new EventSource('/progress');
                es.onmessage = e => {{
                    const [pct, status, fname] = e.data.split('|');
                    document.getElementById('pb').style.width = pct+'%';
                    document.getElementById('pt').innerText = pct+'%';
                    if (status === 'done') {{
                        es.close();
                        document.getElementById('pl').innerText = '✓ Terminé !';
                        if (fname) {{
                            document.getElementById('resultImg').src = '/images/'+fname+'?t='+Date.now();
                            document.getElementById('resultBox').style.display = 'block';
                        }}
                        document.getElementById('transformBtn').disabled = false;
                        setTimeout(() => location.reload(), 2000);
                    }} else {{
                        document.getElementById('pl').innerHTML = '<span class="spinner"></span>'+status;
                    }}
                }};
            }}
        </script>
    </body>
    </html>
    """

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8035)
