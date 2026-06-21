import os, sys, json, shutil, urllib.request, threading, asyncio, subprocess
sys.path.append("src")

from fastapi import FastAPI, UploadFile, File, Form, Cookie
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, StreamingResponse, RedirectResponse
from studio.styles import STYLES
from core.auth import register_user, login_user, get_user_from_token
from dotenv import load_dotenv
load_dotenv()
import uvicorn

app = FastAPI(title="AI Mind")
COMFY_URL = "http://localhost:8188"
OUTPUT_DIR = os.path.expanduser("~/Documents/ComfyUI/output")
INPUT_DIR = os.path.expanduser("~/Documents/ComfyUI/input")

os.makedirs("public/images", exist_ok=True)
os.makedirs("public/uploads", exist_ok=True)
os.makedirs("public/audio", exist_ok=True)

app.mount("/images", StaticFiles(directory="public/images"), name="images")
app.mount("/uploads", StaticFiles(directory="public/uploads"), name="uploads")
app.mount("/audio", StaticFiles(directory="public/audio"), name="audio")
os.makedirs("public/videos", exist_ok=True)
app.mount("/videos", StaticFiles(directory="public/videos"), name="videos")

progress_store = {"value": 0, "status": "idle", "last_file": ""}

def send_to_comfy(image_path, style_key):
    style = STYLES[style_key]
    workflow = {
        "3": {"class_type": "KSampler", "inputs": {"cfg": style["cfg"], "denoise": style["denoise"], "latent_image": ["5", 0], "model": ["4", 0], "negative": ["7", 0], "positive": ["6", 0], "sampler_name": "euler", "scheduler": "karras", "seed": 42, "steps": style["steps"]}},
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
    return json.loads(urllib.request.urlopen(req).read()).get("prompt_id")

def wait_for_result(prompt_id, style_key):
    import time
    for i in range(120):
        time.sleep(1)
        pct = min(95, i * 2)
        progress_store["value"] = pct
        progress_store["status"] = f"Génération {STYLES[style_key]['emoji']}... {pct}%"
        try:
            data = json.loads(urllib.request.urlopen(f"{COMFY_URL}/history/{prompt_id}").read())
            if prompt_id in data and data[prompt_id].get("status", {}).get("completed"):
                for node_out in data[prompt_id].get("outputs", {}).values():
                    if "images" in node_out:
                        img = node_out["images"][0]
                        shutil.copy2(os.path.join(OUTPUT_DIR, img["filename"]), f"public/images/{img['filename']}")
                        progress_store.update({"value": 100, "status": "done", "last_file": img["filename"]})
                        return
        except:
            pass
    progress_store["status"] = "done"

@app.get("/progress")
async def progress():
    async def stream():
        while True:
            yield f"data: {progress_store['value']}|{progress_store['status']}|{progress_store['last_file']}\n\n"
            await asyncio.sleep(0.5)
            if progress_store["status"] == "done":
                break
    return StreamingResponse(stream(), media_type="text/event-stream")

@app.post("/transform")
async def transform(file: UploadFile = File(...), style: str = Form(...)):
    from PIL import Image
    import io
    content = await file.read()
    img = Image.open(io.BytesIO(content)).convert("RGB").resize((512, 512))
    upload_path = os.path.join(INPUT_DIR, file.filename)
    img.save(upload_path)
    progress_store.update({"value": 0, "status": "Démarrage...", "last_file": ""})
    threading.Thread(target=lambda: [send_to_comfy.__wrapped__ if hasattr(send_to_comfy, '__wrapped__') else None, wait_for_result(send_to_comfy(upload_path, style), style)]).start()
    return {"status": "started"}

@app.post("/api/voix")
async def api_voix(text: str = Form(...), voice: str = Form(...)):
    from datetime import datetime
    output = f"public/audio/{voice}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp3"
    result = subprocess.run(
        ["/Users/user/Documents/lipsync-env/bin/python3", "src/core/voice_worker.py", text, voice, output],
        capture_output=True, text=True, cwd="/Users/user/Documents/ai-mind"
    )
    if result.returncode == 0:
        return {"file": f"/{output}", "status": "ok"}
    return {"error": result.stderr[-200:]}

@app.post("/register")
async def register(email: str = Form(...), password: str = Form(...)):
    user, msg = register_user(email, password)
    if not user:
        return RedirectResponse(url=f"/login?error={msg}", status_code=303)
    token, _ = login_user(email, password)
    response = RedirectResponse(url="/studio", status_code=303)
    response.set_cookie("token", token, max_age=86400*30)
    return response

@app.post("/login")
async def login(email: str = Form(...), password: str = Form(...)):
    token, msg = login_user(email, password)
    if not token:
        return RedirectResponse(url=f"/login?error={msg}", status_code=303)
    response = RedirectResponse(url="/studio", status_code=303)
    response.set_cookie("token", token, max_age=86400*30)
    return response

@app.get("/logout")
async def logout():
    response = RedirectResponse(url="/", status_code=303)
    response.delete_cookie("token")
    return response

@app.get("/", response_class=HTMLResponse)
def landing():
    return """<html><head><title>AI Mind</title><meta name="viewport" content="width=device-width, initial-scale=1"><style>*{box-sizing:border-box;margin:0;padding:0}body{font-family:sans-serif;background:#0a0a0a;color:white;min-height:100vh;display:flex;flex-direction:column;align-items:center;justify-content:center;padding:40px}h1{font-size:48px;color:#a78bfa;margin-bottom:12px;text-align:center}p{color:#555;font-size:18px;margin-bottom:40px;text-align:center}.btns{display:flex;gap:16px}.btn{padding:16px 36px;border-radius:12px;border:none;font-size:16px;cursor:pointer;text-decoration:none}.btn-primary{background:#7c3aed;color:white}.btn-secondary{background:#1a1a1a;color:#888;border:1px solid #333}.features{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:20px;margin-top:60px;max-width:800px}.feature{background:#111;border-radius:12px;padding:24px;text-align:center}.feature-icon{font-size:36px;margin-bottom:12px}.feature h3{color:#a78bfa;margin-bottom:8px}.feature p{color:#555;font-size:14px}</style></head><body><h1 style="font-size:56px;background:linear-gradient(135deg,#7c3aed,#a78bfa,#c084fc);-webkit-background-clip:text;-webkit-text-fill-color:transparent">AI Mind</h1><p style="font-size:20px;color:#777;margin-bottom:12px">Le premier studio créatif IA tout-en-un</p><p style="color:#555;font-size:15px;margin-bottom:40px">Images · Voix · Lip Sync · Vidéos · Aliens — tout depuis ton navigateur</p><div class="btns"><a href="/register" class="btn btn-primary">Créer un compte gratuit</a><a href="/pricing" class="btn btn-secondary">Voir les tarifs</a><a href="/login" class="btn btn-secondary">Se connecter</a></div><div class="features"><div class="feature"><div class="feature-icon">🖼</div><h3>Images IA</h3><p>Transforme tes photos avec des styles professionnels</p></div><div class="feature"><div class="feature-icon">🎤</div><h3>30+ Voix</h3><p>Humain, animaux, aliens, nature — tout est possible</p></div><div class="feature"><div class="feature-icon">🎬</div><h3>Lip Sync</h3><p>Fais parler n importe quelle image ou personnage</p></div><div class="feature"><div class="feature-icon">👽</div><h3>Créatures</h3><p>Génère des aliens et créatures fantastiques uniques</p></div></div></body></html>"""

@app.get("/register", response_class=HTMLResponse)
def register_page(error: str = ""):
    return f"""<html><head><title>AI Mind — Inscription</title><meta name="viewport" content="width=device-width, initial-scale=1"><style>*{{box-sizing:border-box;margin:0;padding:0}}body{{font-family:sans-serif;background:#0a0a0a;color:white;min-height:100vh;display:flex;align-items:center;justify-content:center}}.card{{background:#111;border-radius:16px;padding:40px;width:400px}}h2{{color:#a78bfa;margin-bottom:24px;text-align:center}}input{{width:100%;padding:14px;border-radius:10px;border:1px solid #333;background:#1a1a1a;color:white;font-size:15px;margin-bottom:16px}}button{{width:100%;padding:16px;border-radius:10px;border:none;background:#7c3aed;color:white;font-size:16px;cursor:pointer}}.error{{color:#f87171;font-size:13px;margin-bottom:12px;text-align:center}}.link{{text-align:center;margin-top:16px;color:#555;font-size:14px}}.link a{{color:#a78bfa;text-decoration:none}}</style></head><body><div class="card"><h2>🧠 Créer un compte</h2>{"<div class='error'>"+error+"</div>" if error else ""}<form method="post" action="/register"><input type="email" name="email" placeholder="Email" required/><input type="password" name="password" placeholder="Mot de passe" required/><button type="submit">Créer mon compte gratuit</button></form><div class="link">Déjà un compte ? <a href="/login">Se connecter</a></div></div></body></html>"""

@app.get("/login", response_class=HTMLResponse)
def login_page(error: str = ""):
    return f"""<html><head><title>AI Mind — Connexion</title><meta name="viewport" content="width=device-width, initial-scale=1"><style>*{{box-sizing:border-box;margin:0;padding:0}}body{{font-family:sans-serif;background:#0a0a0a;color:white;min-height:100vh;display:flex;align-items:center;justify-content:center}}.card{{background:#111;border-radius:16px;padding:40px;width:400px}}h2{{color:#a78bfa;margin-bottom:24px;text-align:center}}input{{width:100%;padding:14px;border-radius:10px;border:1px solid #333;background:#1a1a1a;color:white;font-size:15px;margin-bottom:16px}}button{{width:100%;padding:16px;border-radius:10px;border:none;background:#7c3aed;color:white;font-size:16px;cursor:pointer}}.error{{color:#f87171;font-size:13px;margin-bottom:12px;text-align:center}}.link{{text-align:center;margin-top:16px;color:#555;font-size:14px}}.link a{{color:#a78bfa;text-decoration:none}}</style></head><body><div class="card"><h2>🧠 Se connecter</h2>{"<div class='error'>"+error+"</div>" if error else ""}<form method="post" action="/login"><input type="email" name="email" placeholder="Email" required/><input type="password" name="password" placeholder="Mot de passe" required/><button type="submit">Se connecter</button></form><div class="link">Pas encore de compte ? <a href="/register">S'inscrire</a></div></div></body></html>"""

@app.get("/studio", response_class=HTMLResponse)
def studio(token: str = Cookie(default=None)):
    user = get_user_from_token(token) if token else None
    if not user:
        return RedirectResponse(url="/login")
    images = sorted([f for f in os.listdir("public/images") if f.endswith(".png")], reverse=True)[:12]
    imgs_html = "".join([f'<img src="/images/{f}" onclick="openImg(this.src)" style="width:200px;margin:6px;border-radius:12px;cursor:pointer"/>' for f in images])
    styles_html = "".join([f'<div class="style-card" onclick="selectStyle(\'{k}\')" id="style-{k}"><div class="style-emoji">{v["emoji"]}</div><div class="style-name">{v["nom"]}</div></div>' for k, v in STYLES.items()])
    return f"""<html><head><title>AI Mind Studio</title><meta name="viewport" content="width=device-width, initial-scale=1"><style>*{{box-sizing:border-box;margin:0;padding:0}}body{{font-family:sans-serif;background:#0a0a0a;color:white;padding:40px}}.header{{display:flex;justify-content:space-between;align-items:center;margin-bottom:24px}}h1{{color:#a78bfa}}.nav{{display:flex;gap:12px;margin-bottom:24px}}.nav a{{background:#1a1a1a;color:#888;padding:10px 20px;border-radius:8px;text-decoration:none;font-size:14px;border:1px solid #333}}.nav a:hover{{border-color:#a78bfa;color:#a78bfa}}.user-info{{color:#555;font-size:14px}}.user-info a{{color:#a78bfa;text-decoration:none;margin-left:12px}}.upload-zone{{border:2px dashed #333;border-radius:16px;padding:50px;text-align:center;cursor:pointer;margin-bottom:24px}}.upload-zone:hover{{border-color:#a78bfa}}.upload-zone input{{display:none}}.upload-icon{{font-size:52px;margin-bottom:12px}}.upload-title{{font-size:18px;color:#a78bfa;font-weight:600;margin-bottom:6px}}.upload-sub{{font-size:13px;color:#444}}.preview-box{{display:none;text-align:center;margin-bottom:24px}}.preview-box img{{width:180px;border-radius:12px;border:2px solid #7c3aed}}.styles-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;margin-bottom:20px}}.style-card{{background:#1a1a1a;border:2px solid #222;border-radius:12px;padding:20px;text-align:center;cursor:pointer;transition:all 0.2s}}.style-card:hover,.style-card.selected{{border-color:#a78bfa;background:#1f1a2e}}.style-emoji{{font-size:32px;margin-bottom:8px}}.style-name{{font-size:14px;color:#888}}.style-card.selected .style-name{{color:#a78bfa}}.btn{{width:100%;padding:16px;border-radius:12px;border:none;background:#7c3aed;color:white;font-size:16px;cursor:pointer;margin-bottom:20px}}.btn:disabled{{background:#333;cursor:not-allowed}}.progress-wrap{{background:#1a1a1a;border-radius:10px;overflow:hidden;height:36px;margin-bottom:8px;display:none;position:relative}}.progress-bar{{height:100%;background:linear-gradient(90deg,#7c3aed,#a78bfa);width:0%;transition:width 0.3s}}.progress-text{{position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);font-size:14px;font-weight:600;color:white}}.status-line{{font-size:14px;color:#a78bfa;margin-bottom:20px;min-height:22px;text-align:center}}.gallery{{display:flex;flex-wrap:wrap;margin-top:24px}}.lightbox{{display:none;position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.92);z-index:99;align-items:center;justify-content:center}}.lightbox img{{max-width:90%;max-height:90%;border-radius:16px}}.lightbox.open{{display:flex}}.change-btn{{background:none;border:1px solid #333;color:#666;padding:6px 14px;border-radius:6px;cursor:pointer;font-size:12px;margin-top:8px}}</style></head><body>
    <div class="header"><h1>🧠 AI Mind Studio</h1><div class="user-info">👤 {user.email} · Plan {user.plan}<a href="/logout">Déconnexion</a></div></div>
    <div class="nav"><a href="/generate">✨ Générer</a><a href="/studio">🖼 Transformer</a><a href="/voix">🎤 Voix</a><a href="/aliens">👽 Aliens</a><a href="/video">🎬 Vidéo</a><a href="/film">🎥 Film</a><a href="/galerie">📁 Galerie</a></div>
    <div class="upload-zone" id="uploadZone" onclick="document.getElementById('imgfile').click()"><input type="file" id="imgfile" accept="image/*" onchange="previewImage(this)"/><div class="upload-icon">📁</div><div class="upload-title">Cliquez pour charger votre photo</div><div class="upload-sub">JPG, PNG — glissez ou cliquez</div></div>
    <div class="preview-box" id="previewBox"><img id="preview" src=""/><p style="color:#a78bfa;font-size:13px;margin-top:8px">✓ Photo chargée</p><button class="change-btn" onclick="document.getElementById('imgfile').click()">Changer</button></div>
    <p style="color:#666;font-size:14px;margin-bottom:12px">Choisissez un style :</p>
    <div class="styles-grid">{styles_html}</div>
    <button class="btn" id="transformBtn" onclick="transformImg()" disabled>✨ Transformer</button>
    <div class="progress-wrap" id="pw"><div class="progress-bar" id="pb"></div><div class="progress-text" id="pt">0%</div></div>
    <div class="status-line" id="pl"></div>
    <div class="gallery">{imgs_html}</div>
    <div class="lightbox" id="lb" onclick="this.classList.remove('open')"><img id="lbimg" src=""/></div>
    <script>
        let selectedStyle=null;
        function selectStyle(s){{document.querySelectorAll('.style-card').forEach(c=>c.classList.remove('selected'));document.getElementById('style-'+s).classList.add('selected');selectedStyle=s;checkReady();}}
        function checkReady(){{document.getElementById('transformBtn').disabled=!(document.getElementById('imgfile').files.length>0&&selectedStyle);}}
        function previewImage(input){{const file=input.files[0];if(!file)return;document.getElementById('preview').src=URL.createObjectURL(file);document.getElementById('uploadZone').style.display='none';document.getElementById('previewBox').style.display='block';checkReady();}}
        function openImg(src){{document.getElementById('lbimg').src=src;document.getElementById('lb').classList.add('open');}}
        async function transformImg(){{const file=document.getElementById('imgfile').files[0];if(!file||!selectedStyle)return;document.getElementById('pw').style.display='block';document.getElementById('pb').style.width='0%';document.getElementById('transformBtn').disabled=true;const fd=new FormData();fd.append('file',file);fd.append('style',selectedStyle);await fetch('/transform',{{method:'POST',body:fd}});const es=new EventSource('/progress');es.onmessage=e=>{{const[pct,status,fname]=e.data.split('|');document.getElementById('pb').style.width=pct+'%';document.getElementById('pt').innerText=pct+'%';if(status==='done'){{es.close();document.getElementById('pl').innerText='✓ Terminé !';document.getElementById('transformBtn').disabled=false;setTimeout(()=>location.reload(),800);}}else{{document.getElementById('pl').innerText=status;}}}};}}
    </script></body></html>"""

@app.get("/voix", response_class=HTMLResponse)
def voix_page(token: str = Cookie(default=None)):
    user = get_user_from_token(token) if token else None
    if not user:
        return RedirectResponse(url="/login")
    return """<html><head><title>AI Mind — Voix</title><meta name="viewport" content="width=device-width, initial-scale=1"><style>
        *{box-sizing:border-box;margin:0;padding:0}
        body{font-family:sans-serif;background:#0a0a0a;color:white;padding:40px}
        h1{color:#a78bfa;margin-bottom:6px}
        .sub{color:#555;margin-bottom:20px}
        .nav{display:flex;gap:8px;margin-bottom:24px;flex-wrap:wrap}
        .nav a{background:#1a1a1a;color:#888;padding:10px 20px;border-radius:8px;text-decoration:none;font-size:14px;border:1px solid #333}
        .nav a:hover{border-color:#a78bfa;color:#a78bfa}
        textarea{width:100%;padding:14px;border-radius:12px;border:1px solid #2a2a2a;background:#111;color:white;font-size:15px;height:100px;margin-bottom:16px;resize:vertical;outline:none}
        textarea:focus{border-color:#7c3aed}
        .search-box{width:100%;padding:14px 18px;border-radius:12px;border:1px solid #2a2a2a;background:#111;color:white;font-size:15px;margin-bottom:16px;outline:none}
        .search-box:focus{border-color:#7c3aed}
        .tabs{display:flex;gap:8px;margin-bottom:20px;flex-wrap:wrap}
        .tab{padding:10px 20px;border-radius:20px;border:1px solid #2a2a2a;cursor:pointer;color:#666;font-size:14px;background:#111;transition:all 0.2s}
        .tab.active{background:linear-gradient(135deg,#7c3aed,#a78bfa);color:white;border-color:transparent;font-weight:600}
        .tab:hover{border-color:#7c3aed;color:#a78bfa}
        .category{display:none}
        .category.active{display:block}
        .cat-title{color:#444;font-size:11px;margin-bottom:12px;text-transform:uppercase;letter-spacing:2px}
        .voices{display:grid;grid-template-columns:repeat(auto-fit,minmax(100px,1fr));gap:12px;margin-bottom:24px}
        .voice-card{background:linear-gradient(145deg,#111,#1a1a1a);border:1.5px solid #222;border-radius:16px;padding:18px 10px;text-align:center;cursor:pointer;transition:all 0.25s;position:relative;overflow:hidden}
        .voice-card::before{content:"";position:absolute;top:0;left:0;right:0;bottom:0;background:linear-gradient(135deg,#7c3aed11,#a78bfa11);opacity:0;transition:opacity 0.25s}
        .voice-card:hover::before,.voice-card.selected::before{opacity:1}
        .voice-card:hover,.voice-card.selected{border-color:#7c3aed;transform:translateY(-2px);box-shadow:0 8px 24px rgba(124,58,237,0.2)}
        .voice-card.hidden{display:none}
        .voice-emoji{font-size:30px;margin-bottom:8px;display:block}
        .voice-name{font-size:12px;color:#666;font-weight:500}
        .voice-card.selected .voice-name{color:#a78bfa;font-weight:600}
        .btn{width:100%;padding:18px;border-radius:14px;border:none;background:linear-gradient(135deg,#7c3aed,#9333ea);color:white;font-size:16px;font-weight:600;cursor:pointer;margin-bottom:16px;transition:all 0.2s;box-shadow:0 4px 20px rgba(124,58,237,0.3)}
        .btn:hover{transform:translateY(-1px);box-shadow:0 6px 28px rgba(124,58,237,0.4)}
        .btn:disabled{background:#222;cursor:not-allowed;box-shadow:none;transform:none}
        .spinner{display:inline-block;width:14px;height:14px;border:2px solid #a78bfa;border-top-color:transparent;border-radius:50%;animation:spin 0.8s linear infinite;margin-right:8px;vertical-align:middle}
        @keyframes spin{to{transform:rotate(360deg)}}
        .status{font-size:14px;color:#a78bfa;margin-bottom:16px;min-height:20px;text-align:center}
        .audio-box{display:none;background:#1a1a1a;border-radius:12px;padding:20px;text-align:center}
        .audio-box p{color:#a78bfa;margin-bottom:12px}
        audio{width:100%}
    </style></head><body>
    <div class="nav"><a href="/generate">✨ Générer</a><a href="/studio">🖼 Transformer</a><a href="/voix">🎤 Voix</a><a href="/aliens">👽 Aliens</a><a href="/video">🎬 Vidéo</a><a href="/film">🎥 Film</a><a href="/galerie">📁 Galerie</a></div>
    <h1>🎤 AI Mind — Voix</h1>
    <p class="sub">Écris un texte, choisis une voix et écoute !</p>
    <textarea id="text" placeholder="Écris ton texte ici...">Bonjour, je suis AI Mind, votre assistant créatif personnel.</textarea>
    <input class="search-box" type="text" placeholder="🔍 Rechercher une voix..." oninput="searchVoice(this.value)"/>
    <div class="tabs">
        <div class="tab active" onclick="showTab('humains')">👤 Humains</div>
        <div class="tab" onclick="showTab('animaux')">🦁 Animaux</div>
        <div class="tab" onclick="showTab('marins')">🌊 Marins</div>
        <div class="tab" onclick="showTab('nature')">🌿 Nature</div>
        <div class="tab" onclick="showTab('fantastique')">👽 Fantastique</div>
    </div>

    <div class="category active" id="cat-humains">
        <div class="cat-title">Voix humaines</div>
        <div class="voices">
            <div class="voice-card" onclick="selectVoice('humain')" id="v-humain" data-name="humain"><div class="voice-emoji">🗣</div><div class="voice-name">Humain</div></div>
            <div class="voice-card" onclick="selectVoice('femme')" id="v-femme" data-name="femme"><div class="voice-emoji">👩</div><div class="voice-name">Femme</div></div>
            <div class="voice-card" onclick="selectVoice('enfant')" id="v-enfant" data-name="enfant"><div class="voice-emoji">👦</div><div class="voice-name">Enfant</div></div>
        </div>
    </div>

    <div class="category" id="cat-animaux">
        <div class="cat-title">Animaux terrestres</div>
        <div class="voices">
            <div class="voice-card" onclick="selectVoice('lion')" id="v-lion" data-name="lion"><div class="voice-emoji">🦁</div><div class="voice-name">Lion</div></div>
            <div class="voice-card" onclick="selectVoice('tigre')" id="v-tigre" data-name="tigre"><div class="voice-emoji">🐯</div><div class="voice-name">Tigre</div></div>
            <div class="voice-card" onclick="selectVoice('loup')" id="v-loup" data-name="loup"><div class="voice-emoji">🐺</div><div class="voice-name">Loup</div></div>
            <div class="voice-card" onclick="selectVoice('ours')" id="v-ours" data-name="ours"><div class="voice-emoji">🐻</div><div class="voice-name">Ours</div></div>
            <div class="voice-card" onclick="selectVoice('elephant')" id="v-elephant" data-name="elephant"><div class="voice-emoji">🐘</div><div class="voice-name">Éléphant</div></div>
            <div class="voice-card" onclick="selectVoice('gorille')" id="v-gorille" data-name="gorille"><div class="voice-emoji">🦍</div><div class="voice-name">Gorille</div></div>
            <div class="voice-card" onclick="selectVoice('chien')" id="v-chien" data-name="chien"><div class="voice-emoji">🐕</div><div class="voice-name">Chien</div></div>
            <div class="voice-card" onclick="selectVoice('chat')" id="v-chat" data-name="chat"><div class="voice-emoji">🐈</div><div class="voice-name">Chat</div></div>
            <div class="voice-card" onclick="selectVoice('singe')" id="v-singe" data-name="singe"><div class="voice-emoji">🐒</div><div class="voice-name">Singe</div></div>
            <div class="voice-card" onclick="selectVoice('souris')" id="v-souris" data-name="souris"><div class="voice-emoji">🐭</div><div class="voice-name">Souris</div></div>
            <div class="voice-card" onclick="selectVoice('grenouille')" id="v-grenouille" data-name="grenouille"><div class="voice-emoji">🐸</div><div class="voice-name">Grenouille</div></div>
            <div class="voice-card" onclick="selectVoice('perroquet')" id="v-perroquet" data-name="perroquet"><div class="voice-emoji">🦜</div><div class="voice-name">Perroquet</div></div>
            <div class="voice-card" onclick="selectVoice('oiseau')" id="v-oiseau" data-name="oiseau"><div class="voice-emoji">🐦</div><div class="voice-name">Oiseau</div></div>
        </div>
    </div>

    <div class="category" id="cat-marins">
        <div class="cat-title">Animaux marins</div>
        <div class="voices">
            <div class="voice-card" onclick="selectVoice('dauphin')" id="v-dauphin" data-name="dauphin"><div class="voice-emoji">🐬</div><div class="voice-name">Dauphin</div></div>
            <div class="voice-card" onclick="selectVoice('baleine')" id="v-baleine" data-name="baleine"><div class="voice-emoji">🐋</div><div class="voice-name">Baleine</div></div>
            <div class="voice-card" onclick="selectVoice('requin')" id="v-requin" data-name="requin"><div class="voice-emoji">🦈</div><div class="voice-name">Requin</div></div>
            <div class="voice-card" onclick="selectVoice('poisson')" id="v-poisson" data-name="poisson"><div class="voice-emoji">🐟</div><div class="voice-name">Poisson</div></div>
        </div>
    </div>

    <div class="category" id="cat-nature">
        <div class="cat-title">Sons de la nature</div>
        <div class="voices">
            <div class="voice-card" onclick="selectVoice('pluie')" id="v-pluie" data-name="pluie"><div class="voice-emoji">🌧️</div><div class="voice-name">Pluie</div></div>
            <div class="voice-card" onclick="selectVoice('tempete')" id="v-tempete" data-name="tempete"><div class="voice-emoji">⛈️</div><div class="voice-name">Tempête</div></div>
            <div class="voice-card" onclick="selectVoice('vent')" id="v-vent" data-name="vent"><div class="voice-emoji">🌬️</div><div class="voice-name">Vent</div></div>
            <div class="voice-card" onclick="selectVoice('feu')" id="v-feu" data-name="feu"><div class="voice-emoji">🔥</div><div class="voice-name">Feu</div></div>
            <div class="voice-card" onclick="selectVoice('ocean')" id="v-ocean" data-name="ocean"><div class="voice-emoji">🌊</div><div class="voice-name">Océan</div></div>
            <div class="voice-card" onclick="selectVoice('foret')" id="v-foret" data-name="foret"><div class="voice-emoji">🌲</div><div class="voice-name">Forêt</div></div>
            <div class="voice-card" onclick="selectVoice('tonnerre')" id="v-tonnerre" data-name="tonnerre"><div class="voice-emoji">⚡</div><div class="voice-name">Tonnerre</div></div>
        </div>
    </div>

    <div class="category" id="cat-fantastique">
        <div class="cat-title">Créatures fantastiques</div>
        <div class="voices">
            <div class="voice-card" onclick="selectVoice('robot')" id="v-robot" data-name="robot"><div class="voice-emoji">🤖</div><div class="voice-name">Robot</div></div>
            <div class="voice-card" onclick="selectVoice('alien')" id="v-alien" data-name="alien"><div class="voice-emoji">👽</div><div class="voice-name">Alien</div></div>
            <div class="voice-card" onclick="selectVoice('dragon')" id="v-dragon" data-name="dragon"><div class="voice-emoji">🐉</div><div class="voice-name">Dragon</div></div>
            <div class="voice-card" onclick="selectVoice('ange')" id="v-ange" data-name="ange"><div class="voice-emoji">👼</div><div class="voice-name">Ange</div></div>
            <div class="voice-card" onclick="selectVoice('demon')" id="v-demon" data-name="demon"><div class="voice-emoji">😈</div><div class="voice-name">Démon</div></div>
            <div class="voice-card" onclick="selectVoice('zombie')" id="v-zombie" data-name="zombie"><div class="voice-emoji">🧟</div><div class="voice-name">Zombie</div></div>
        </div>
    </div>

    <button class="btn" id="btn" onclick="speak()" disabled>🎤 Générer la voix</button>
    <div class="status" id="status"></div>
    <div class="audio-box" id="audioBox"><p>✓ Voix générée !</p><audio id="player" controls></audio></div>

    <script>
        let selectedVoice=null;
        function showTab(name){
            document.querySelectorAll('.tab').forEach(t=>t.classList.remove('active'));
            document.querySelectorAll('.category').forEach(c=>c.classList.remove('active'));
            event.target.classList.add('active');
            document.getElementById('cat-'+name).classList.add('active');
        }
        function searchVoice(q){
            const query=q.toLowerCase().trim();
            if(!query){
                document.querySelectorAll('.voice-card').forEach(c=>c.classList.remove('hidden'));
                return;
            }
            document.querySelectorAll('.tab').forEach(t=>t.classList.remove('active'));
            document.querySelectorAll('.category').forEach(c=>c.classList.add('active'));
            document.querySelectorAll('.voice-card').forEach(c=>{
                const name=c.getAttribute('data-name')||'';
                c.classList.toggle('hidden', !name.includes(query));
            });
        }
        function selectVoice(v){
            document.querySelectorAll('.voice-card').forEach(c=>c.classList.remove('selected'));
            document.getElementById('v-'+v).classList.add('selected');
            selectedVoice=v;
            document.getElementById('btn').disabled=false;
        }
        async function speak(){
            const text=document.getElementById('text').value;
            if(!text||!selectedVoice)return;
            document.getElementById('btn').innerHTML='<span class="spinner"></span>Génération...';
            document.getElementById('btn').disabled=true;
            document.getElementById('status').innerHTML='<span class="spinner"></span>En cours...';
            const fd=new FormData();
            fd.append('text',text);
            fd.append('voice',selectedVoice);
            const resp=await fetch('/api/voix',{method:'POST',body:fd});
            const data=await resp.json();
            if(data.file){
                document.getElementById('player').src='/audio/'+data.file.split('/').pop()+'?t='+Date.now();
                document.getElementById('audioBox').style.display='block';
                document.getElementById('player').play();
                document.getElementById('status').innerText='✓ Terminé !';
            }
            document.getElementById('btn').innerHTML='🎤 Générer la voix';
            document.getElementById('btn').disabled=false;
        }
    </script></body></html>"""

@app.get("/aliens", response_class=HTMLResponse)
def aliens_page(token: str = Cookie(default=None)):
    user = get_user_from_token(token) if token else None
    if not user:
        return RedirectResponse(url="/login")
    alien_images = sorted([f for f in os.listdir("public/images") if f.endswith(".png") and "alien" in f.lower()], reverse=True)
    all_images = sorted([f for f in os.listdir("public/images") if f.endswith(".png")], reverse=True)[:20]
    imgs = alien_images if alien_images else all_images
    imgs_html = "".join([f'<img src="/images/{f}" onclick="openImg(this.src)" style="width:200px;margin:6px;border-radius:12px;cursor:pointer"/>' for f in imgs])

    ALIEN_PROMPTS = {
        "alien_bleu": "alien creature, bioluminescent blue skin, large black eyes, otherworldly, cinematic, 8K",
        "dragon_cosmique": "cosmic dragon, nebula wings, stars in scales, flying through galaxy, epic, cinematic, 8K",
        "sirene_spatiale": "space mermaid, crystalline body, floating in nebula, glowing, ethereal, cinematic, 8K",
        "demon_galactique": "galactic demon, dark matter body, red glowing eyes, cosmic horror, cinematic, 8K",
        "ange_celeste": "celestial angel, golden light, cosmic wings, divine, floating in space, cinematic, 8K",
        "fantome_quantique": "quantum ghost, translucent body, floating particles, ethereal, sci-fi, cinematic, 8K",
        "robot_ancien": "ancient robot alien, rusty metal, glowing eyes, mysterious, cinematic, 8K",
        "ovni_vivant": "living UFO creature, tentacles, bioluminescent, deep space, cinematic, 8K",
    }
    cards_html = "".join([f'<div class="alien-card" onclick="generateAlien(\'{k}\')"><div class="alien-name">{k.replace("_"," ").title()}</div></div>' for k in ALIEN_PROMPTS.keys()])

    return f"""<html><head><title>AI Mind — Aliens</title><meta name="viewport" content="width=device-width, initial-scale=1"><style>*{{box-sizing:border-box;margin:0;padding:0}}body{{font-family:sans-serif;background:#0a0a0a;color:white;padding:40px}}h1{{color:#a78bfa;margin-bottom:6px}}.sub{{color:#555;margin-bottom:24px}}.nav{{display:flex;gap:12px;margin-bottom:24px}}.nav a{{background:#1a1a1a;color:#888;padding:10px 20px;border-radius:8px;text-decoration:none;font-size:14px;border:1px solid #333}}.nav a:hover{{border-color:#a78bfa;color:#a78bfa}}.aliens-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;margin-bottom:24px}}.alien-card{{background:#1a1a1a;border:2px solid #222;border-radius:12px;padding:20px;text-align:center;cursor:pointer;transition:all 0.2s}}.alien-card:hover{{border-color:#a78bfa;background:#1f1a2e}}.alien-name{{font-size:14px;color:#888}}.alien-card:hover .alien-name{{color:#a78bfa}}.progress-wrap{{background:#1a1a1a;border-radius:10px;overflow:hidden;height:36px;margin-bottom:8px;display:none;position:relative}}.progress-bar{{height:100%;background:linear-gradient(90deg,#7c3aed,#a78bfa);width:0%;transition:width 0.3s}}.progress-text{{position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);font-size:14px;font-weight:600;color:white}}.status{{font-size:14px;color:#a78bfa;margin-bottom:20px;text-align:center}}.gallery{{display:flex;flex-wrap:wrap}}.lightbox{{display:none;position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.92);z-index:99;align-items:center;justify-content:center}}.lightbox img{{max-width:90%;max-height:90%;border-radius:16px}}.lightbox.open{{display:flex}}</style></head><body>
    <div class="nav"><a href="/generate">✨ Générer</a><a href="/studio">🖼 Transformer</a><a href="/voix">🎤 Voix</a><a href="/aliens">👽 Aliens</a><a href="/video">🎬 Vidéo</a><a href="/film">🎥 Film</a><a href="/galerie">📁 Galerie</a></div>
    <h1>👽 AI Mind — Créatures</h1><p class="sub">Génère des créatures extraterrestres uniques</p>
    <div class="aliens-grid">{cards_html}</div>
    <div class="progress-wrap" id="pw"><div class="progress-bar" id="pb"></div><div class="progress-text" id="pt">0%</div></div>
    <div class="status" id="status"></div>
    <div class="gallery">{imgs_html}</div>
    <div class="lightbox" id="lb" onclick="this.classList.remove('open')"><img id="lbimg" src=""/></div>
    <script>
        function openImg(src){{document.getElementById('lbimg').src=src;document.getElementById('lb').classList.add('open');}}
        async function generateAlien(type){{
            document.getElementById('pw').style.display='block';
            document.getElementById('pb').style.width='0%';
            document.getElementById('status').innerText='Génération '+type+' en cours...';
            await fetch('/api/alien?type='+type);
            const es=new EventSource('/progress');
            es.onmessage=e=>{{const[pct,status]=e.data.split('|');document.getElementById('pb').style.width=pct+'%';document.getElementById('pt').innerText=pct+'%';if(status==='done'){{es.close();document.getElementById('status').innerText='✓ Terminé !';setTimeout(()=>location.reload(),800);}}}};
        }}
    </script></body></html>"""

@app.get("/api/alien")
async def api_alien(type: str = "alien_bleu"):
    ALIEN_PROMPTS = {
        "alien_bleu": "alien creature, bioluminescent blue skin, large black eyes, otherworldly, cinematic, 8K, hyperrealistic",
        "dragon_cosmique": "cosmic dragon, nebula wings, stars in scales, flying through galaxy, epic, cinematic, 8K",
        "sirene_spatiale": "space mermaid, crystalline body, floating in nebula, glowing, ethereal, cinematic, 8K",
        "demon_galactique": "galactic demon, dark matter body, red glowing eyes, cosmic horror, cinematic, 8K",
        "ange_celeste": "celestial angel, golden light, cosmic wings, divine, floating in space, cinematic, 8K",
        "fantome_quantique": "quantum ghost, translucent body, floating particles, ethereal, sci-fi, cinematic, 8K",
        "robot_ancien": "ancient robot alien, rusty metal, glowing eyes, mysterious, cinematic, 8K",
        "ovni_vivant": "living UFO creature, tentacles, bioluminescent, deep space, cinematic, 8K",
    }
    prompt = ALIEN_PROMPTS.get(type, ALIEN_PROMPTS["alien_bleu"])
    workflow = {
        "1": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": "RealisticVision_V6.safetensors"}},
        "2": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["1", 1], "text": prompt}},
        "3": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["1", 1], "text": "ugly, deformed, watermark, blurry, low quality"}},
        "4": {"class_type": "EmptyLatentImage", "inputs": {"width": 512, "height": 512, "batch_size": 1}},
        "5": {"class_type": "KSampler", "inputs": {"model": ["1", 0], "positive": ["2", 0], "negative": ["3", 0], "latent_image": ["4", 0], "seed": 42, "steps": 30, "cfg": 8.0, "sampler_name": "euler", "scheduler": "karras", "denoise": 1.0}},
        "6": {"class_type": "VAEDecode", "inputs": {"samples": ["5", 0], "vae": ["1", 2]}},
        "7": {"class_type": "SaveImage", "inputs": {"filename_prefix": f"alien_{type}", "images": ["6", 0]}}
    }
    progress_store.update({"value": 0, "status": "Démarrage...", "last_file": ""})
    def run():
        data = json.dumps({"prompt": workflow}).encode()
        req = urllib.request.Request(f"{COMFY_URL}/prompt", data=data, headers={"Content-Type": "application/json"})
        pid = json.loads(urllib.request.urlopen(req).read()).get("prompt_id")
        wait_for_result(pid, "russe")
    threading.Thread(target=run).start()
    return {"status": "started"}



@app.get("/video", response_class=HTMLResponse)
def video_page(token: str = Cookie(default=None)):
    user = get_user_from_token(token) if token else None
    if not user:
        return RedirectResponse(url="/login")
    videos = sorted([f for f in os.listdir("public/videos") if f.endswith(".mp4")], reverse=True)[:6] if os.path.exists("public/videos") else []
    vhtml = "".join([f'<video src="/videos/{f}" controls style="width:280px;margin:6px;border-radius:12px"></video>' for f in videos])
    return """<html><head><title>AI Mind — Vidéo</title><meta name="viewport" content="width=device-width, initial-scale=1"><style>
        *{box-sizing:border-box;margin:0;padding:0}body{font-family:sans-serif;background:#0a0a0a;color:white;padding:40px}
        h1{color:#a78bfa;margin-bottom:6px}.sub{color:#555;margin-bottom:24px}
        .nav{display:flex;gap:8px;margin-bottom:24px;flex-wrap:wrap}.nav a{background:#111;color:#888;padding:10px 20px;border-radius:8px;text-decoration:none;font-size:14px;border:1px solid #222}.nav a:hover{border-color:#a78bfa;color:#a78bfa}
        .card{background:#111;border-radius:16px;padding:24px;margin-bottom:20px;border:1px solid #1a1a1a}.card h3{color:#a78bfa;margin-bottom:16px}
        input[type=file]{width:100%;padding:12px;border-radius:10px;border:1px solid #222;background:#1a1a1a;color:#888;margin-bottom:12px}
        .btn{width:100%;padding:16px;border-radius:12px;border:none;background:linear-gradient(135deg,#7c3aed,#9333ea);color:white;font-size:16px;font-weight:600;cursor:pointer}
        .btn:disabled{background:#333;cursor:not-allowed}
        .spinner{display:inline-block;width:14px;height:14px;border:2px solid #a78bfa;border-top-color:transparent;border-radius:50%;animation:spin 0.8s linear infinite;margin-right:8px;vertical-align:middle}
        @keyframes spin{to{transform:rotate(360deg)}}
        .status{text-align:center;color:#a78bfa;margin:16px 0;font-size:14px}
        .result{display:none;text-align:center;margin-top:20px}
        .gallery{display:flex;flex-wrap:wrap;margin-top:24px}
        .download-btn{display:inline-block;margin-top:10px;padding:10px 20px;background:#1a1a1a;border-radius:8px;color:#a78bfa;text-decoration:none;border:1px solid #7c3aed}
    </style></head><body>
    <div class="nav"><a href="/generate">✨ Générer</a><a href="/studio">🖼 Transformer</a><a href="/voix">🎤 Voix</a><a href="/aliens">👽 Aliens</a><a href="/video">🎬 Vidéo</a><a href="/film">🎥 Film</a><a href="/galerie">📁 Galerie</a></div>
    <h1>🎬 AI Mind — Vidéo Lip Sync</h1>
    <p class="sub">Crée une vidéo avec un personnage qui parle vraiment !</p>
    <div class="card"><h3>1️⃣ Upload ton image</h3><input type="file" id="imgfile" accept="image/*"/></div>
    <div class="card"><h3>2️⃣ Écris le texte à dire</h3><textarea id="textinput" placeholder="Écris ce que le personnage doit dire..." style="width:100%;padding:12px;border-radius:10px;border:1px solid #222;background:#1a1a1a;color:white;height:80px;font-size:14px">Bonjour, je suis AI Mind, votre assistant créatif.</textarea><select id="voiceinput" style="width:100%;padding:12px;border-radius:10px;border:1px solid #222;background:#1a1a1a;color:white;font-size:14px;margin-top:8px"><option value="fr-FR-HenriNeural">🗣 Homme (Henri)</option><option value="fr-FR-DeniseNeural">👩 Femme (Denise)</option><option value="fr-CA-ThierryNeural">🗣 Homme (Thierry)</option><option value="fr-BE-GerardNeural">🗣 Homme (Gerard)</option><option value="fr-FR-EloiseNeural">👧 Jeune fille (Eloise)</option></select></div>
    <button class="btn" onclick="createVideo()">🎬 Créer la vidéo Lip Sync</button>
    <div class="status" id="status"></div>
    <div class="result" id="result"><p style="color:#a78bfa;margin-bottom:12px;font-size:18px">🔥 Vidéo prête !</p><video id="player" controls style="width:400px;border-radius:12px;border:2px solid #7c3aed"></video><br><a id="downloadBtn" class="download-btn" download>⬇ Télécharger MP4</a></div>
    <script>
        async function createVideo(){
            const img=document.getElementById("imgfile").files[0];
            const text=document.getElementById("textinput").value;
            const voice=document.getElementById("voiceinput").value;
            if(!img||!text){alert("Image et texte requis !");return;}
            document.getElementById("status").innerHTML='<span class="spinner"></span>Création vidéo en cours... (5-10 minutes)';
            const fd=new FormData();fd.append("image",img);fd.append("text",text);fd.append("voice",voice);
            const resp=await fetch("/api/lipsync",{method:"POST",body:fd});
            const data=await resp.json();
            if(data.file){
                document.getElementById("player").src="/videos/"+data.file.split("/").pop()+"?t="+Date.now();
                document.getElementById("downloadBtn").href="/videos/"+data.file.split("/").pop();
                document.getElementById("result").style.display="block";
                document.getElementById("status").innerText="✓ Terminé !";
            } else {document.getElementById("status").innerText="❌ Erreur : "+(data.error||"inconnue");}
        }
    </script></body></html>"""



@app.post("/api/lipsync")
async def api_lipsync(image: UploadFile = File(...), driving: UploadFile = File(...)):
    from datetime import datetime
    os.makedirs("public/uploads", exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    img_path = f"public/uploads/lp_img_{ts}.jpg"
    drv_path = f"public/uploads/lp_drv_{ts}.mp4"
    with open(img_path, "wb") as f:
        f.write(await image.read())
    with open(drv_path, "wb") as f:
        f.write(await driving.read())
    
    from avatar.liveportrait_sync import animate_face
    result = animate_face(os.path.abspath(img_path), os.path.abspath(drv_path))
    if result:
        return {"file": result, "status": "ok"}
    return {"error": "LivePortrait a échoué"}


@app.get("/pricing", response_class=HTMLResponse)
def pricing():
    return """<html><head><title>AI Mind — Tarifs</title><meta name="viewport" content="width=device-width, initial-scale=1"><style>
        *{box-sizing:border-box;margin:0;padding:0}
        body{font-family:sans-serif;background:#0a0a0a;color:white;padding:40px;display:flex;flex-direction:column;align-items:center}
        h1{font-size:36px;background:linear-gradient(135deg,#7c3aed,#a78bfa);-webkit-background-clip:text;-webkit-text-fill-color:transparent;margin-bottom:8px}
        .sub{color:#555;margin-bottom:40px;font-size:16px}
        .plans{display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:24px;max-width:900px;width:100%}
        .plan{background:#111;border:2px solid #222;border-radius:20px;padding:32px;text-align:center;position:relative;transition:all 0.3s}
        .plan:hover{border-color:#7c3aed;transform:translateY(-4px)}
        .plan.popular{border-color:#7c3aed;background:#0f0a1a}
        .badge{position:absolute;top:-12px;left:50%;transform:translateX(-50%);background:linear-gradient(135deg,#7c3aed,#9333ea);color:white;padding:4px 16px;border-radius:12px;font-size:12px;font-weight:600}
        .plan-name{font-size:20px;color:#a78bfa;margin-bottom:8px;font-weight:600}
        .plan-price{font-size:42px;color:white;font-weight:700;margin-bottom:4px}
        .plan-price span{font-size:16px;color:#555;font-weight:400}
        .plan-desc{color:#555;font-size:13px;margin-bottom:24px}
        .features{text-align:left;margin-bottom:24px}
        .features div{color:#888;font-size:14px;padding:6px 0;border-bottom:1px solid #1a1a1a}
        .features div::before{content:"✓ ";color:#a78bfa}
        .plan-btn{width:100%;padding:14px;border-radius:12px;border:none;font-size:15px;font-weight:600;cursor:pointer}
        .plan-btn.free{background:#1a1a1a;color:#888}
        .plan-btn.pro{background:linear-gradient(135deg,#7c3aed,#9333ea);color:white}
        .plan-btn.enterprise{background:#1a1a1a;color:#a78bfa;border:1px solid #7c3aed}
        a{text-decoration:none}
        .back{color:#a78bfa;margin-top:32px;text-decoration:none;font-size:14px}
    </style></head><body>
    <h1>Tarifs AI Mind</h1>
    <p class="sub">Choisissez le plan qui vous convient</p>
    <div class="plans">
        <div class="plan">
            <div class="plan-name">Gratuit</div>
            <div class="plan-price">0$<span>/mois</span></div>
            <div class="plan-desc">Pour découvrir AI Mind</div>
            <div class="features">
                <div>5 transformations/jour</div>
                <div>3 voix/jour</div>
                <div>1 lip sync/jour</div>
                <div>Watermark AI Mind</div>
            </div>
            <a href="/register"><button class="plan-btn free">Commencer gratuitement</button></a>
        </div>
        <div class="plan popular">
            <div class="badge">POPULAIRE</div>
            <div class="plan-name">Pro</div>
            <div class="plan-price">19$<span>/mois</span></div>
            <div class="plan-desc">Pour les créateurs sérieux</div>
            <div class="features">
                <div>Transformations illimitées</div>
                <div>Toutes les voix illimitées</div>
                <div>Lip sync illimité</div>
                <div>Sans watermark</div>
                <div>Priorité de génération</div>
            </div>
            <form method="post" action="/api/checkout"><input type="hidden" name="plan" value="pro"/><button class="plan-btn pro" type="submit">Choisir Pro — 19$/mois</button></form>
        </div>
        <div class="plan">
            <div class="plan-name">Enterprise</div>
            <div class="plan-price">99$<span>/mois</span></div>
            <div class="plan-desc">Pour les équipes et studios</div>
            <div class="features">
                <div>Tout dans Pro</div>
                <div>API accès</div>
                <div>Support prioritaire</div>
                <div>Modèles personnalisés</div>
                <div>Multi-utilisateurs</div>
            </div>
            <form method="post" action="/api/checkout"><input type="hidden" name="plan" value="enterprise"/><button class="plan-btn enterprise" type="submit">Choisir Enterprise — 99$/mois</button></form>
        </div>
    </div>
    <a href="/" class="back">← Retour à l accueil</a>
    </body></html>"""


@app.get("/galerie", response_class=HTMLResponse)
def galerie(token: str = Cookie(default=None)):
    user = get_user_from_token(token) if token else None
    if not user:
        return RedirectResponse(url="/login")
    
    images = sorted([f for f in os.listdir("public/images") if f.endswith(".png")], reverse=True)[:24]
    audios = sorted([f for f in os.listdir("public/audio") if f.endswith(".mp3") or f.endswith(".wav")], reverse=True)[:12]
    videos = sorted([f for f in os.listdir("public/videos") if f.endswith(".mp4")], reverse=True)[:12] if os.path.exists("public/videos") else []
    
    imgs_html = "".join([f'<div class="item"><img src="/images/{f}" onclick="openLb(this.src)"/><a href="/images/{f}" download class="dl">⬇</a><a href="https://wa.me/?text=Regarde%20ce%20que%20j%20ai%20cree%20avec%20AI%20Mind" target="_blank" class="dl" style="bottom:32px">📱</a></div>' for f in images])
    auds_html = "".join([f'<div class="aud-item"><p>{f[:20]}...</p><audio src="/audio/{f}" controls></audio><a href="/audio/{f}" download class="dl">⬇</a></div>' for f in audios])
    vids_html = "".join([f'<div class="vid-item"><video src="/videos/{f}" controls></video><a href="/videos/{f}" download class="dl">⬇</a></div>' for f in videos])
    
    return f"""<html><head><title>AI Mind — Galerie</title><meta name="viewport" content="width=device-width, initial-scale=1"><style>
        *{{box-sizing:border-box;margin:0;padding:0}}
        body{{font-family:sans-serif;background:#0a0a0a;color:white;padding:40px}}
        h1{{color:#a78bfa;margin-bottom:6px}}
        .sub{{color:#555;margin-bottom:24px}}
        .nav{{display:flex;gap:12px;margin-bottom:24px}}
        .nav a{{background:#111;color:#888;padding:10px 20px;border-radius:8px;text-decoration:none;font-size:14px;border:1px solid #222}}
        .nav a:hover{{border-color:#a78bfa;color:#a78bfa}}
        .tabs{{display:flex;gap:8px;margin-bottom:20px}}
        .tab{{padding:10px 20px;border-radius:20px;border:1px solid #222;cursor:pointer;color:#666;font-size:14px;background:#111}}
        .tab.active{{background:linear-gradient(135deg,#7c3aed,#a78bfa);color:white;border-color:transparent;font-weight:600}}
        .section{{display:none}}.section.active{{display:block}}
        .grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px}}
        .item{{position:relative;border-radius:12px;overflow:hidden}}
        .item img{{width:100%;border-radius:12px;cursor:pointer;transition:transform 0.2s}}
        .item img:hover{{transform:scale(1.03)}}
        .dl{{position:absolute;bottom:8px;right:8px;background:rgba(124,58,237,0.9);color:white;padding:6px 10px;border-radius:8px;text-decoration:none;font-size:12px}}
        .aud-item{{background:#111;border-radius:12px;padding:16px;margin-bottom:12px;position:relative}}
        .aud-item p{{color:#a78bfa;font-size:13px;margin-bottom:8px}}
        .aud-item audio{{width:100%}}
        .aud-item .dl{{position:absolute;top:12px;right:12px}}
        .vid-item{{position:relative;margin-bottom:12px}}
        .vid-item video{{width:100%;border-radius:12px}}
        .vid-item .dl{{position:absolute;bottom:12px;right:12px;background:rgba(124,58,237,0.9);color:white;padding:6px 10px;border-radius:8px;text-decoration:none;font-size:12px}}
        .lightbox{{display:none;position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.92);z-index:99;align-items:center;justify-content:center}}
        .lightbox img{{max-width:90%;max-height:90%;border-radius:16px}}
        .lightbox.open{{display:flex}}
        .empty{{color:#555;text-align:center;padding:40px;font-size:14px}}
    </style></head><body>
    <div class="nav"><a href="/generate">✨ Générer</a><a href="/studio">🖼 Transformer</a><a href="/voix">🎤 Voix</a><a href="/aliens">👽 Aliens</a><a href="/video">🎬 Vidéo</a><a href="/film">🎥 Film</a><a href="/galerie">📁 Galerie</a></div>
    <h1>📁 Ma Galerie</h1>
    <p class="sub">Toutes tes créations AI Mind</p>
    <div class="tabs">
        <div class="tab active" onclick="showSec('images')">🖼 Images ({len(images)})</div>
        <div class="tab" onclick="showSec('audio')">🎤 Audio ({len(audios)})</div>
        <div class="tab" onclick="showSec('video')">🎬 Vidéos ({len(videos)})</div>
    </div>
    <div class="section active" id="sec-images">
        <div class="grid">{imgs_html if imgs_html else '<div class="empty">Aucune image encore</div>'}</div>
    </div>
    <div class="section" id="sec-audio">
        {auds_html if auds_html else '<div class="empty">Aucun audio encore</div>'}
    </div>
    <div class="section" id="sec-video">
        {vids_html if vids_html else '<div class="empty">Aucune vidéo encore</div>'}
    </div>
    <div class="lightbox" id="lb" onclick="this.classList.remove('open')"><img id="lbimg" src=""/></div>
    <script>
        function showSec(name){{
            document.querySelectorAll('.tab').forEach(t=>t.classList.remove('active'));
            document.querySelectorAll('.section').forEach(s=>s.classList.remove('active'));
            event.target.classList.add('active');
            document.getElementById('sec-'+name).classList.add('active');
        }}
        function openLb(src){{document.getElementById('lbimg').src=src;document.getElementById('lb').classList.add('open');}}
    </script></body></html>"""


@app.get("/film", response_class=HTMLResponse)
def film_page(token: str = Cookie(default=None)):
    user = get_user_from_token(token) if token else None
    if not user:
        return RedirectResponse(url="/login")
    return """<html><head><title>AI Mind — Film</title><meta name="viewport" content="width=device-width, initial-scale=1"><style>
        *{box-sizing:border-box;margin:0;padding:0}
        body{font-family:sans-serif;background:#0a0a0a;color:white;padding:40px}
        h1{color:#a78bfa;margin-bottom:6px}
        .sub{color:#555;margin-bottom:24px}
        .nav{display:flex;gap:12px;margin-bottom:24px;flex-wrap:wrap}
        .nav a{background:#111;color:#888;padding:10px 20px;border-radius:8px;text-decoration:none;font-size:14px;border:1px solid #222}
        .nav a:hover{border-color:#a78bfa;color:#a78bfa}
        .card{background:#111;border-radius:16px;padding:24px;margin-bottom:20px;border:1px solid #1a1a1a}
        .card h3{color:#a78bfa;margin-bottom:16px}
        input[type=file]{width:100%;padding:12px;border-radius:10px;border:1px solid #222;background:#1a1a1a;color:#888;margin-bottom:12px}
        input[type=text],textarea{width:100%;padding:12px;border-radius:10px;border:1px solid #222;background:#1a1a1a;color:white;font-size:14px;margin-bottom:12px}
        textarea{height:80px;resize:vertical}
        select{width:100%;padding:12px;border-radius:10px;border:1px solid #222;background:#1a1a1a;color:white;font-size:14px;margin-bottom:12px}
        .btn{width:100%;padding:16px;border-radius:12px;border:none;background:linear-gradient(135deg,#7c3aed,#9333ea);color:white;font-size:16px;font-weight:600;cursor:pointer}
        .btn:disabled{background:#333;cursor:not-allowed}
        .spinner{display:inline-block;width:14px;height:14px;border:2px solid #a78bfa;border-top-color:transparent;border-radius:50%;animation:spin 0.8s linear infinite;margin-right:8px;vertical-align:middle}
        @keyframes spin{to{transform:rotate(360deg)}}
        .status{text-align:center;color:#a78bfa;margin:16px 0;font-size:14px}
        .result{display:none;text-align:center;margin-top:20px}
        .download-btn{display:inline-block;margin-top:10px;padding:10px 20px;background:#1a1a1a;border-radius:8px;color:#a78bfa;text-decoration:none;border:1px solid #7c3aed}
    </style></head><body>
    <div class="nav"><a href="/generate">✨ Générer</a><a href="/studio">🖼 Transformer</a><a href="/voix">🎤 Voix</a><a href="/aliens">👽 Aliens</a><a href="/video">🎬 Vidéo</a><a href="/film">🎥 Film</a><a href="/galerie">📁 Galerie</a></div>
    <h1>🎥 AI Mind — Créateur de Films</h1>
    <p class="sub">Crée un court-métrage IA complet en quelques clics</p>

    <div class="card">
        <h3>1️⃣ Personnage — Upload une image</h3>
        <input type="file" id="charimg" accept="image/*"/>
    </div>

    <div class="card">
        <h3>2️⃣ Dialogue — Écris ce que le personnage dit</h3>
        <textarea id="dialogue" placeholder="Bonjour, je suis un explorateur de galaxies...">Bienvenue dans AI Mind. Je suis votre guide intergalactique. Ensemble nous allons explorer les frontières de la créativité.</textarea>
        <select id="voice">
            <option value="humain">🗣 Humain</option>
            <option value="femme">👩 Femme</option>
            <option value="alien" selected>👽 Alien</option>
            <option value="robot">🤖 Robot</option>
            <option value="dragon">🐉 Dragon</option>
            <option value="demon">😈 Démon</option>
            <option value="ange">👼 Ange</option>
        </select>
    </div>

    <div class="card">
        <h3>3️⃣ Titre du film</h3>
        <input type="text" id="title" value="AI Mind — Le Film"/>
    </div>

    <button class="btn" onclick="createFilm()">🎥 Créer mon film</button>

    <div class="status" id="status"></div>

    <div class="result" id="result">
        <p style="color:#a78bfa;margin-bottom:12px;font-size:18px">🔥 Film prêt !</p>
        <video id="player" controls style="width:300px;border-radius:12px;border:2px solid #7c3aed"></video>
        <br><a id="downloadBtn" class="download-btn" download>⬇ Télécharger le film</a>
    </div>

    <script>
        async function createFilm(){
            const img=document.getElementById("charimg").files[0];
            const dialogue=document.getElementById("dialogue").value;
            const voice=document.getElementById("voice").value;
            const title=document.getElementById("title").value;
            if(!img||!dialogue){alert("Image et dialogue requis !");return;}
            document.getElementById("status").innerHTML='<span class="spinner"></span>Création du film en cours... (5-10 minutes)';
            const fd=new FormData();
            fd.append("image",img);
            fd.append("dialogue",dialogue);
            fd.append("voice",voice);
            fd.append("title",title);
            const resp=await fetch("/api/film",{method:"POST",body:fd});
            const data=await resp.json();
            if(data.file){
                document.getElementById("player").src="/videos/"+data.file.split("/").pop()+"?t="+Date.now();
                document.getElementById("downloadBtn").href="/videos/"+data.file.split("/").pop();
                document.getElementById("result").style.display="block";
                document.getElementById("status").innerText="✓ Film terminé !";
            } else {document.getElementById("status").innerText="❌ Erreur : "+(data.error||"inconnue");}
        }
    </script></body></html>"""

@app.post("/api/film")
async def api_film(image: UploadFile = File(...), dialogue: str = Form(...), voice: str = Form("alien"), title: str = Form("AI Mind")):
    from datetime import datetime
    os.makedirs("public/uploads", exist_ok=True)
    os.makedirs("public/videos", exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    img_path = f"public/uploads/film_img_{ts}.jpg"
    with open(img_path, "wb") as f:
        f.write(await image.read())
    
    audio_path = f"public/audio/film_voice_{ts}.mp3"
    result = subprocess.run(
        ["/Users/user/Documents/lipsync-env/bin/python3", "src/core/voice_worker.py", dialogue, voice, audio_path],
        capture_output=True, text=True, cwd="/Users/user/Documents/ai-mind"
    )
    if result.returncode != 0:
        return {"error": "Erreur génération voix"}
    
    lp_dir = os.path.expanduser("~/Documents/ComfyUI/custom_nodes/LivePortrait")
    env = os.environ.copy()
    env["PYTORCH_ENABLE_MPS_FALLBACK"] = "1"
    anim_result = subprocess.run(
        ["python", "inference.py", "-s", os.path.abspath(img_path), "-d", "assets/examples/driving/d6.mp4"],
        capture_output=True, text=True, cwd=lp_dir, env=env
    )
    
    anim_dir = os.path.join(lp_dir, "animations")
    anim_videos = sorted([f for f in os.listdir(anim_dir) if f.endswith(".mp4") and "concat" not in f],
                         key=lambda x: os.path.getmtime(os.path.join(anim_dir, x)), reverse=True)
    
    if not anim_videos:
        return {"error": "LivePortrait a échoué"}
    
    anim_path = os.path.join(anim_dir, anim_videos[0])
    
    scene_path = f"/tmp/film_scene_{ts}.mp4"
    subprocess.run(["ffmpeg", "-y", "-i", anim_path, "-vf",
                   "scale=720:1280:force_original_aspect_ratio=decrease,pad=720:1280:(ow-iw)/2:(oh-ih)/2:black",
                   "-c:v", "libx264", "-pix_fmt", "yuv420p", "-an", scene_path], capture_output=True)
    
    scene_audio = f"/tmp/film_scene_audio_{ts}.mp4"
    subprocess.run(["ffmpeg", "-y", "-i", scene_path, "-i", audio_path,
                   "-c:v", "copy", "-c:a", "aac", "-shortest", scene_audio], capture_output=True)
    
    intro_path = f"/tmp/film_intro_{ts}.mp4"
    subprocess.run(["ffmpeg", "-y", "-f", "lavfi", "-i", "color=c=black:s=720x1280:d=3",
                   "-c:v", "libx264", "-pix_fmt", "yuv420p", intro_path], capture_output=True)
    
    outro_path = f"/tmp/film_outro_{ts}.mp4"
    subprocess.run(["ffmpeg", "-y", "-f", "lavfi", "-i", "color=c=black:s=720x1280:d=3",
                   "-c:v", "libx264", "-pix_fmt", "yuv420p", outro_path], capture_output=True)
    
    list_path = f"/tmp/film_list_{ts}.txt"
    with open(list_path, "w") as f:
        f.write(f"file '{intro_path}'\nfile '{scene_audio}'\nfile '{outro_path}'\n")
    
    output = f"public/videos/film_{ts}.mp4"
    subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", list_path,
                   "-c:v", "libx264", "-c:a", "aac", "-pix_fmt", "yuv420p", output], capture_output=True)
    
    if os.path.exists(output) and os.path.getsize(output) > 1000:
        return {"file": output, "status": "ok"}
    return {"error": "Erreur assemblage film"}


@app.post("/api/checkout")
async def checkout(plan: str = Form(...), token: str = Cookie(default=None)):
    user = get_user_from_token(token) if token else None
    if not user:
        return RedirectResponse(url="/login")
    from core.payments import create_checkout
    url = create_checkout(plan, user.email)
    if url:
        return RedirectResponse(url=url, status_code=303)
    return RedirectResponse(url="/pricing?error=Plan invalide", status_code=303)


@app.get("/privacy", response_class=HTMLResponse)
def privacy():
    return """<html><head><title>AI Mind — Confidentialité</title><style>
        *{box-sizing:border-box;margin:0;padding:0}
        body{font-family:sans-serif;background:#0a0a0a;color:white;padding:40px;max-width:800px;margin:0 auto}
        h1{color:#a78bfa;margin-bottom:24px}
        h2{color:#a78bfa;margin-top:24px;margin-bottom:12px;font-size:18px}
        p{color:#888;line-height:1.8;margin-bottom:16px;font-size:14px}
        a{color:#a78bfa;text-decoration:none}
    </style></head><body>
    <a href="/">← Retour</a>
    <h1>Politique de Confidentialité</h1>
    <p>Dernière mise à jour : juin 2026</p>
    <h2>Données collectées</h2>
    <p>AI Mind collecte uniquement votre email et mot de passe pour la création de compte. Les images, voix et vidéos que vous créez sont stockées sur nos serveurs et accessibles uniquement par vous.</p>
    <h2>Utilisation des données</h2>
    <p>Vos données sont utilisées uniquement pour fournir le service AI Mind. Nous ne vendons pas vos données à des tiers.</p>
    <h2>Sécurité</h2>
    <p>Les mots de passe sont chiffrés avec bcrypt. Les communications sont sécurisées par HTTPS.</p>
    <h2>Suppression</h2>
    <p>Vous pouvez demander la suppression de votre compte et de toutes vos données en nous contactant à contact@aimind.ai.</p>
    <h2>Contact</h2>
    <p>Pour toute question : contact@aimind.ai</p>
    </body></html>"""


@app.get("/generate", response_class=HTMLResponse)
def generate_page(token: str = Cookie(default=None)):
    user = get_user_from_token(token) if token else None
    if not user:
        return RedirectResponse(url="/login")
    return """<html><head><title>AI Mind — Générer</title><meta name="viewport" content="width=device-width, initial-scale=1"><style>
        *{box-sizing:border-box;margin:0;padding:0}
        body{font-family:sans-serif;background:#0a0a0a;color:white;padding:40px}
        h1{color:#a78bfa;margin-bottom:6px}
        .sub{color:#555;margin-bottom:24px}
        .nav{display:flex;gap:8px;margin-bottom:24px;flex-wrap:wrap}
        .nav a{background:#111;color:#888;padding:10px 20px;border-radius:8px;text-decoration:none;font-size:14px;border:1px solid #222}
        .nav a:hover{border-color:#a78bfa;color:#a78bfa}
        textarea{width:100%;padding:14px;border-radius:12px;border:1px solid #222;background:#111;color:white;font-size:15px;height:100px;margin-bottom:16px}
        textarea:focus{border-color:#7c3aed;outline:none}
        .btn{width:100%;padding:16px;border-radius:12px;border:none;background:linear-gradient(135deg,#7c3aed,#9333ea);color:white;font-size:16px;font-weight:600;cursor:pointer;margin-bottom:16px}
        .btn:disabled{background:#333;cursor:not-allowed}
        .spinner{display:inline-block;width:14px;height:14px;border:2px solid #a78bfa;border-top-color:transparent;border-radius:50%;animation:spin 0.8s linear infinite;margin-right:8px;vertical-align:middle}
        @keyframes spin{to{transform:rotate(360deg)}}
        .status{text-align:center;color:#a78bfa;margin:16px 0;font-size:14px}
        .result{display:none;text-align:center;margin-top:20px}
        .result img{max-width:512px;width:100%;border-radius:16px;border:2px solid #7c3aed}
        .download-btn{display:inline-block;margin-top:10px;padding:10px 20px;background:#1a1a1a;border-radius:8px;color:#a78bfa;text-decoration:none;border:1px solid #7c3aed}
        .examples{display:flex;gap:8px;margin-bottom:16px;flex-wrap:wrap}
        .example{background:#111;border:1px solid #222;padding:8px 14px;border-radius:8px;color:#888;font-size:12px;cursor:pointer}
        .example:hover{border-color:#7c3aed;color:#a78bfa}
    </style></head><body>
    <div class="nav"><a href="/generate">✨ Générer</a><a href="/studio">🖼 Transformer</a><a href="/voix">🎤 Voix</a><a href="/aliens">👽 Aliens</a><a href="/video">🎬 Vidéo</a><a href="/film">🎥 Film</a><a href="/galerie">📁 Galerie</a></div>
    <h1>✨ AI Mind — Générer une image</h1>
    <p class="sub">Décris ce que tu veux voir et AI Mind le crée</p>
    <p style="color:#555;font-size:13px;margin-bottom:8px">Exemples :</p>
    <div class="examples">
        <div class="example" onclick="setPrompt('A beautiful woman in golden light, cinematic portrait, 8K')">Portrait doré</div>
        <div class="example" onclick="setPrompt('Ancient Egyptian palace with golden columns and torches, epic, 8K')">Palais égyptien</div>
        <div class="example" onclick="setPrompt('Alien creature with bioluminescent blue skin, large eyes, sci-fi, 8K')">Alien bleu</div>
        <div class="example" onclick="setPrompt('Cosmic dragon flying through galaxy, nebula wings, epic, 8K')">Dragon cosmique</div>
        <div class="example" onclick="setPrompt('Futuristic city at night, neon lights, cyberpunk, rain, cinematic, 8K')">Ville futuriste</div>
        <div class="example" onclick="setPrompt('Deep ocean underwater scene with glowing jellyfish, mysterious, 8K')">Océan profond</div>
    </div>
    <textarea id="prompt" placeholder="Décris ton image... Ex: A beautiful sunset over mountains, cinematic, 8K"></textarea>
    <button class="btn" id="btn" onclick="generate()">✨ Générer l image</button>
    <div class="status" id="status"></div>
    <div class="result" id="result">
        <p style="color:#a78bfa;margin-bottom:12px;font-size:18px">🔥 Image générée !</p>
        <img id="resultImg" src=""/>
        <br><a id="downloadBtn" class="download-btn" download>⬇ Télécharger</a>
    </div>
    <script>
        function setPrompt(p){document.getElementById('prompt').value=p;}
        async function generate(){
            const prompt=document.getElementById('prompt').value;
            if(!prompt){alert('Écris une description !');return;}
            document.getElementById('btn').disabled=true;
            document.getElementById('status').innerHTML='<span class="spinner"></span>Génération de 4 variations... (2-3 minutes)';
            const resp=await fetch('/api/generate',{method:'POST',headers:{'Content-Type':'application/x-www-form-urlencoded'},body:'prompt='+encodeURIComponent(prompt)});
            const data=await resp.json();
            if(data.files){
                let html='';
                data.files.forEach(f=>{html+='<div style="display:inline-block;margin:8px"><img src="/images/'+f+'?t='+Date.now()+'" style="width:240px;border-radius:12px;cursor:pointer;border:2px solid #222" onclick="selectImg(this.src)"/><br><a href="/images/'+f+'" download style="color:#a78bfa;font-size:12px">⬇ Télécharger</a></div>';});
                document.getElementById('result').innerHTML='<p style="color:#a78bfa;margin-bottom:12px;font-size:18px">🔥 4 variations générées !</p>'+html;
                document.getElementById('result').style.display='block';
                document.getElementById('status').innerText='✓ Terminé !';
            } else if(data.file){
                document.getElementById('result').innerHTML='<img src="/images/'+data.file+'" style="max-width:512px;border-radius:16px"/>';
                document.getElementById('result').style.display='block';
                document.getElementById('status').innerText='✓ Terminé !';
            } else {document.getElementById('status').innerText='❌ Erreur : '+(data.error||'inconnue');}
            document.getElementById('btn').disabled=false;
        }
    </script></body></html>"""

@app.post("/api/generate")
async def api_generate(prompt: str = Form(...)):
    import urllib.request, json, time, shutil, random
    seeds = [random.randint(1, 999999) for _ in range(4)]
    prompt_ids = []
    
    from studio.prompt_enhancer import enhance_prompt
    prompt = enhance_prompt(prompt)
    
    for seed in seeds:
        workflow = {
            "1": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": "RealisticVision_V6.safetensors"}},
            "2": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["1", 1], "text": prompt}},
            "3": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["1", 1], "text": "ugly, deformed, watermark, blurry, low quality, cartoon"}},
            "4": {"class_type": "EmptyLatentImage", "inputs": {"width": 512, "height": 512, "batch_size": 1}},
            "5": {"class_type": "KSampler", "inputs": {"model": ["1", 0], "positive": ["2", 0], "negative": ["3", 0], "latent_image": ["4", 0], "seed": seed, "steps": 30, "cfg": 8.0, "sampler_name": "euler", "scheduler": "karras", "denoise": 1.0}},
            "6": {"class_type": "VAEDecode", "inputs": {"samples": ["5", 0], "vae": ["1", 2]}},
            "7": {"class_type": "SaveImage", "inputs": {"filename_prefix": "aimind_gen", "images": ["6", 0]}}
        }
        data = json.dumps({"prompt": workflow}).encode()
        req = urllib.request.Request("http://localhost:8188/prompt", data=data, headers={"Content-Type": "application/json"})
        try:
            resp = urllib.request.urlopen(req)
            result = json.loads(resp.read())
            prompt_ids.append(result.get("prompt_id"))
        except:
            return {"error": "ComfyUI non disponible"}
    
    files = []
    for pid in prompt_ids:
        for i in range(180):
            time.sleep(1)
            try:
                hist = json.loads(urllib.request.urlopen(f"http://localhost:8188/history/{pid}").read())
                if pid in hist and hist[pid].get("status", {}).get("completed"):
                    for node_out in hist[pid].get("outputs", {}).values():
                        if "images" in node_out:
                            img = node_out["images"][0]
                            src = os.path.join(os.path.expanduser("~/Documents/ComfyUI/output"), img["filename"])
                            shutil.copy2(src, f"public/images/{img['filename']}")
                            files.append(img["filename"])
                    break
            except:
                pass
    if files:
        return {"files": files, "status": "ok"}
    return {"error": "Timeout"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8035)
