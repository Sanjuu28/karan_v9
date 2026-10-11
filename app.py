from flask import Flask, request, jsonify, render_template_string
from groq import Groq
from ddgs import DDGS
import re, os, tempfile, time
from urllib.parse import quote

app = Flask(__name__)
CACHE = {}
CACHE["user_name"] = ""
RAW_KEYS = os.environ.get("GROQ_API_KEYS", os.environ.get("GROQ_API_KEY", ""))
GROQ_KEYS = [k.strip() for k in RAW_KEYS.split(",") if k.strip() and len(k) > 20]
key_index = 0
def get_groq_client():
    global key_index
    if not GROQ_KEYS: return None
    key = GROQ_KEYS[key_index % len(GROQ_KEYS)]
    key_index += 1
    return Groq(api_key=key)

def get_instant_answer(q_low):
    if any(x in q_low for x in ["main kaun hu","mai kaun hu","main kon hu","mai kon hu","mera naam kya hai"]):
        if "vikash" in q_low or "vikas" in CACHE.get("user_name",""): return "Boss aap Vikash ho! 😊 Aapne abhi bataya tha! Aap mere naye Boss ho 💖"
        return "Boss aapne abhi tak apna naam nahi bataya 😅 Aap batao aap kaun ho? Main yaad rakh lungi!"
    if any(x in q_low for x in ["mai to","main to","mera naam"]):
        if "vikash" in q_low or "vikas" in q_low:
            CACHE["user_name"] = "vikash"
            return "Arey waah Boss Vikash! 😍 Yaad rakh liya maine! Aaj se aap Vikash Boss ho! 💖 Ab batao kya help karu?"
        if "karan" in q_low:
            if "kaise" in q_low or "kaise ho sktha" in q_low: return "Haan Boss sahi bola aapne! 😅 Sorry sorry! Aap Vikash ho, Karan nahi! Karan toh is app ke owner hain Alot se! Aap batao Vikash Boss, kya kaam hai? 🙏"
    if "karan yadav" in q_low and "kisne banaya" not in q_low and "kaise" not in q_low:
        if any(x in q_low for x in ["kaun hai","kya karta","details","number","contact","ghar"]): return "Boss, mujhe mere Boss Karan Yadav ke baare me aur detail dene ki permission nahi hai."
    if any(x in q_low for x in ["kansana","idal","edal","aidal"]): return "Boss, Idal Singh Kansana MP ke Krishi Mantri hain.\n1. Post: MP Kisan Kalyan Mantri\n2. Seat: Sumawali, Morena se 5 baar Vidhayak\n3. Samaj: Gurjar samaj ke Chambal-Gwalior ke sabse bade neta"
    if any(x in q_low for x in ["jyotish","rashi","rashifal","kundli","kundali","horoscope","bhavishya","grah","nakshatra","janm","mangal dosh","shani"]): return "Boss Jyotish Vidya ke hisab se suno 💫:\n1. 12 Rashiyan: Mesh, Vrishabh, Mithun...\n2. 9 Grah: Surya, Chandra...\nBoss apni Rashi batao main detail bata deti hu! 🙏"
    if any(x in q_low for x in ["song","gaana","gana","movie","film","music","geet"]) and "kisne banaya" in q_low: return None
    if any(x in q_low for x in ["tumhe kisne banaya","who made you","tum kon ho","tum kaun ho","tu kaun hai"]):
        if "main kaun" not in q_low and "mai kaun" not in q_low: return "Main Sanjuu hu 💖 Ek AI Assistant hu! Mujhe poori Sanjuu Team ne banaya hai, mere owner Karan Yadav hain Alot, Ratlam MP se! 😊"
    if "love you" in q_low: return "Boss, I love you too! 💖😘"
    if q_low in ["accha ji","accha","ok","hyy","hi","hello","hii","kaise ho"] or q_low.startswith("hi ") or q_low.startswith("hello "): return "Boss, Hyy! Bolo kya kaam hai? 😊 Main sun rahi hu 💖"
    return None
def is_image_request(q_low):
    keywords = ["pic","pics","pix","photo","photos","foto","image","img","tasveer","chitra","elephant","haathi","hathi","logo","poster","thumbnail","banner","video","banao","create","generate"]
    actions = ["bej","bhej","bejo","bhejo","dikhao","dikha","banao","send","chahiye","do","create","generate","make"]
    return any(k in q_low for k in keywords) and any(a in q_low for a in actions)
def ask_sanjoo(query):
    q_low = query.lower().strip()
    if not q_low: return "Boss kuch likho to sahi"
    if q_low in CACHE: return CACHE[q_low]
    instant = get_instant_answer(q_low)
    if instant: CACHE[q_low]=instant; return instant
    if is_image_request(q_low):
        clean = q_low
        for w in ["pic","pics","pix","photo","photos","foto","image","img","ki","ka","bej","bhej","bejo","bhejo","dikhao","dikha","na","jara","please","plz","bej na","bhej na","bana","banao","mujhe","ek"]: clean = clean.replace(w, "")
        clean = clean.strip()
        if clean == "" or len(clean) < 3: clean = "cute baby elephant" if "elephant" in q_low or "haathi" in q_low or "hathi" in q_low else "cute cat"
        url = f"https://image.pollinations.ai/prompt/{quote(clean)}?width=1024&height=1024&nologo=true&enhance=true&model=turbo&seed={int(time.time())}"
        ans = f"__IMAGE__{url}__{clean}"; CACHE[q_low]=ans; return ans
    rag = ""
    if len(q_low.split()) > 4:
        try:
            with DDGS() as ddgs: r = list(ddgs.text(query, max_results=1)); rag = r[0]['body'][:600] if r else ""
        except: rag=""
    prompt = f"You are Sanjuu made by Sanjuu Team owner Karan Yadav. You are a helpful friendly assistant. DATA:{rag} USER:{query} Answer short Hinglish 2 lines. Do not talk about jyotish, rashi, kundli unless user asks about it."
    if not GROQ_KEYS: return "Boss Render pe GROQ_API_KEYS set nahi hai 🙏 Environment Variables me keys daalo"
    for _ in range(len(GROQ_KEYS)*2):
        cur_client = get_groq_client()
        if not cur_client: break
        for model_name in ["openai/gpt-oss-20b", "openai/gpt-oss-120b", "llama-3.3-70b-versatile", "qwen/qwen3-32b"]:
            try:
                comp = cur_client.chat.completions.create(model=model_name, messages=[{"role":"user","content":prompt}], max_tokens=400, temperature=0.6)
                ans = re.sub(r'\*\*(.*?)\*\*', r'\1', comp.choices[0].message.content).strip()
                CACHE[q_low]=ans
                if len(CACHE) > 500: CACHE.pop(next(iter(CACHE)))
                return ans
            except Exception as e:
                print(f"Model {model_name} fail: {e}"); time.sleep(0.2)
                if "429" in str(e) or "rate_limit" in str(e).lower(): break
                continue
    return "Boss 1 min ruko plz 🙏 Groq thoda busy hai"

HTML_CODE = """
<!DOCTYPE html>
<html><head><meta name="viewport" content="width=device-width, initial-scale=1"><title>my sanjuu</title>
<style>
*{box-sizing:border-box}body{margin:0;font-family:-apple-system,sans-serif;background:#fff;height:100dvh;display:flex;flex-direction:column}
.head{padding:20px 18px 10px;display:flex;justify-content:space-between;align-items:center}
.sanjuu{font-size:42px;font-weight:900;line-height:0.9}.sanjuu b{color:#111}.sanjuu span{color:#ff1a8a}
.live{color:#00c950;font-size:12px;font-weight:700;margin-top:6px}
.coding{width:58px;height:58px;background:#111;border:2px solid #facc15;border-radius:50%;display:flex;align-items:center;justify-content:center;color:#facc15;font-weight:800;font-size:12px}
.center{flex:1;overflow-y:auto;padding:12px 14px 120px}#chat{max-width:700px;margin:auto;display:flex;flex-direction:column;gap:14px}
.row{display:flex; align-items:flex-end; gap:8px; align-self:flex-start; max-width:92%}
.row-user{display:flex; align-items:flex-end; gap:8px; align-self:flex-end; max-width:92%; flex-direction:row-reverse}
.a{background:#f2f2f2;padding:14px 16px;border-radius:20px 20px 20px 5px;max-width:100%;line-height:1.6;white-space:pre-wrap;font-size:15px}
.a img{width:100%;border-radius:12px;margin-top:10px;border:1px solid #ddd;cursor:pointer}
.u{background:#111;color:#fff;padding:12px 16px;border-radius:20px 20px 5px 20px;max-width:100%;font-size:15px}
.u audio{width:200px; margin-top:6px}
.u img{width:100px;height:100px;object-fit:cover;border-radius:10px;margin-top:6px;border:2px solid #fff}
.speak-out{width:32px;height:32px;background:#fff;border:1px solid #e0e0e0;border-radius:50%;display:flex;align-items:center;justify-content:center;cursor:pointer;box-shadow:0 1px 4px rgba(0,0,0,0.1);flex-shrink:0;font-size:16px}
.speak-out.playing{background:#111;color:#fff}
/* FIXED BOX - SEND ICON BAHAR NAHI JAYEGA */
.wrap{position:fixed;bottom:0;left:0;right:0;background:#fff;padding:14px 12px 18px;border-top:1px solid #f0f0f0}
.box{background:#f2f2f2;border-radius:30px;padding:5px 6px 5px 18px;display:flex;align-items:center;gap:6px;max-width:700px;margin:0 auto;border:1px solid #e9e9e9;overflow:hidden;flex-wrap:nowrap}
.box input{flex:1;border:0;background:transparent;outline:none;font-size:16px;padding:10px 0;min-width:0;width:0}
.icon{width:36px;height:36px;background:#fff;border-radius:50%;display:flex;align-items:center;justify-content:center;box-shadow:0 1px 3px rgba(0,0,0,0.1);flex-shrink:0;cursor:pointer;border:1px solid #eee;user-select:none;-webkit-user-select:none}
.mic-btn.rec{background:#ff1a8a;animation:pulse 1s infinite;color:#fff}
.icon-voice{background:#2f5eff;color:#fff;border:0;flex-shrink:0}
@keyframes pulse{0%{transform:scale(1)}50%{transform:scale(1.1)}100%{transform:scale(1)}}
.rec-hint{font-size:12px;color:#ff1a8a;font-weight:700;display:none;position:absolute;bottom:70px;left:50%;transform:translateX(-50%);background:#fff;padding:6px 12px;border-radius:20px;box-shadow:0 2px 8px rgba(0,0,0,0.15);border:1px solid #ff1a8a}
.modal-bg{position:fixed;top:0;left:0;right:0;bottom:0;background:rgba(0,0,0,0.6);display:none;align-items:center;justify-content:center;z-index:9999;padding:16px}
.modal{width:100%;max-width:500px;background:#fff;border-radius:24px;padding:22px;box-shadow:0 20px 40px rgba(0,0,0,0.3);max-height:90vh;overflow-y:auto}
.modal h2{margin:0 0 6px;font-size:22px;font-weight:900}.modal p{margin:0 0 14px;color:#666;font-size:14px}
.chips{display:flex;flex-wrap:wrap;gap:8px;margin:12px 0}
.chip{background:#f2f2f2;padding:10px 14px;border-radius:20px;font-size:13px;font-weight:700;cursor:pointer;border:1px solid #e9e9e9}
.chip:hover{background:#111;color:#fff}
.step2{display:none}
.input-with-plus{display:flex;align-items:center;gap:8px;background:#f2f2f2;border-radius:16px;padding:6px 8px 6px 14px;border:2px solid #eee;margin-top:10px;overflow:hidden}
.input-with-plus input{flex:1;border:0;background:transparent;outline:none;font-size:15px;padding:10px 0;min-width:0}
.plus-btn{width:36px;height:36px;background:#111;color:#fff;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:20px;cursor:pointer;flex-shrink:0}
.plus-menu{display:none;flex-direction:column;gap:8px;margin-top:10px;background:#fff;border:1px solid #eee;border-radius:16px;padding:10px;box-shadow:0 4px 12px rgba(0,0,0,0.1)}
.plus-opt{display:flex;align-items:center;gap:10px;padding:10px 12px;border-radius:12px;cursor:pointer;background:#f9f9f9}
.plus-opt:hover{background:#111;color:#fff}
.preview-img{width:100%;max-height:150px;object-fit:contain;border-radius:12px;margin-top:10px;display:none;border:1px solid #ddd}
.modal-btns{display:flex;gap:10px;margin-top:16px}
.btn{flex:1;padding:12px;border-radius:30px;border:0;font-weight:800;cursor:pointer}
.btn-cancel{background:#f2f2f2}.btn-create{background:#111;color:#fff}
.lightbox{position:fixed;top:0;left:0;right:0;bottom:0;background:rgba(0,0,0,0.9);display:none;align-items:center;justify-content:center;z-index:10000;padding:20px}
.lightbox img{max-width:95%;max-height:90%;border-radius:16px}
.lightbox-close{position:absolute;top:20px;right:20px;width:40px;height:40px;background:#fff;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:20px;cursor:pointer;font-weight:900}
.voice-mode{position:fixed;top:0;left:0;right:0;bottom:0;background:#fafafa;display:none;flex-direction:column;z-index:10001}
.voice-top{padding:16px 18px;display:flex;justify-content:space-between;align-items:center;background:#fff;border-bottom:1px solid #eee}
.voice-center{flex:1;display:flex;flex-direction:column;align-items:center;justify-content:flex-start;padding:0;overflow-y:auto;position:relative}
.orb-area{width:100%;display:flex;flex-direction:column;align-items:center;justify-content:center;padding:24px 16px;background:#fff;flex:1}
.orb{width:140px;height:140px;border-radius:50%;background:radial-gradient(circle at 30% 30%, #ff8bc4, #ff1a8a);box-shadow:0 16px 40px rgba(255,26,138,0.35);display:flex;align-items:center;justify-content:center;animation:orbPulse 2s infinite;flex-shrink:0}
.orb.listening{animation:orbPulse 0.7s infinite; background:radial-gradient(circle at 30% 30%, #8b9eff, #2f5eff); box-shadow:0 16px 40px rgba(47,94,255,0.5)}
.orb.muted{background:radial-gradient(circle at 30% 30%, #999, #555); box-shadow:0 16px 40px rgba(0,0,0,0.2)}
.orb.speaking{animation:orbSpeak 0.4s infinite}
@keyframes orbPulse{0%{transform:scale(1)}50%{transform:scale(1.06)}100%{transform:scale(1)}}
@keyframes orbSpeak{0%{transform:scale(1)}25%{transform:scale(1.08)}50%{transform:scale(0.96)}75%{transform:scale(1.06)}100%{transform:scale(1)}}
.wave-bars{display:flex;gap:4px;margin-top:18px;height:28px;align-items:center}
.bar{width:4px;height:10px;background:#ff1a8a;border-radius:10px;animation:wave 0.8s infinite ease-in-out}
.bar:nth-child(2){animation-delay:0.1s}.bar:nth-child(3){animation-delay:0.2s}.bar:nth-child(4){animation-delay:0.3s}.bar:nth-child(5){animation-delay:0.4s}
@keyframes wave{0%,100%{height:10px}50%{height:28px}}
.voice-status{margin-top:14px;font-size:16px;font-weight:700;color:#111;text-align:center;white-space:pre-wrap;max-width:340px}
.voice-transcript{margin-top:6px;font-size:13px;color:#666;text-align:center;max-width:340px;min-height:16px;padding:0 12px}
.live-cam-view{width:100%;height:100%;position:absolute;top:0;left:0;background:#000;display:none;flex-direction:column;z-index:5}
.live-cam-view video{width:100%;height:100%;object-fit:cover;background:#000}
.cam-overlay{position:absolute;bottom:20px;left:0;right:0;display:flex;justify-content:center;gap:12px;z-index:6}
.cam-label{position:absolute;top:16px;left:16px;background:rgba(0,0,0,0.7);color:#fff;padding:6px 12px;border-radius:20px;font-size:12px;font-weight:700;display:flex;align-items:center;gap:6px;z-index:6}
.dot{width:8px;height:8px;background:#ff0000;border-radius:50%;animation:pulse 1s infinite}
/* FIXED SEARCH BAR - SEND BAHAR NAHI JAYEGA */
.voice-bottom{padding:10px 12px;background:#fff;border-top:1px solid #eee;display:flex;flex-direction:column;gap:8px}
.search-bar{width:100%;max-width:720px;margin:0 auto;background:#f2f2f2;border-radius:28px;padding:6px 6px 6px 14px;display:flex;align-items:center;gap:6px;border:1px solid #e6e6e6;overflow:hidden;flex-wrap:nowrap}
.search-bar input{flex:1;border:0;background:transparent;outline:none;font-size:15px;padding:10px 0;min-width:0;width:0}
.icon-btn{width:38px;height:38px;border-radius:50%;display:flex;align-items:center;justify-content:center;cursor:pointer;flex-shrink:0;background:#fff;border:1px solid #eee;box-shadow:0 1px 3px rgba(0,0,0,0.08);font-size:18px}
.icon-btn.blue{background:#2f5eff;color:#fff;border:0}
.voice-controls{width:100%;max-width:720px;margin:0 auto;display:flex;justify-content:center;align-items:center;gap:14px;padding:4px 0}
.ctrl-mic{width:64px;height:64px;border-radius:50%;display:flex;align-items:center;justify-content:center;cursor:pointer;box-shadow:0 6px 20px rgba(47,94,255,0.35);background:#2f5eff;color:#fff}
.ctrl-mic.muted{background:#888;box-shadow:none}
.ctrl-mic.rec{background:#ff1a8a;animation:pulse 1s infinite}
</style></head>
<body>
<div class="head"><div><div style="font-size:14px;opacity:.7">my</div><div class="sanjuu"><b>sanj</b><span>uu</span>💖</div><div class="live">● LIVE VOICE + CAM FIXED ✨</div></div><div class="coding">coding</div></div>
<div class="center"><div id="chat"><div class="row"><div class="a">Boss send wala icon fix kiya - ab box ke andar hi rahega! Camera black wala bhi fix kiya - ab sahi dikhega!</div><div class="speak-out" onclick="speakText(this.parentElement.querySelector('.a').innerText, this)">🔈</div></div></div></div>
<div class="rec-hint" id="recHint">🔴 Recording... dabake rakho - chodoge toh send hoga</div>
<div class="lightbox" id="lightbox" onclick="closeLightbox()"><div class="lightbox-close" onclick="closeLightbox()">✕</div><img id="lightboxImg" src="" /></div>

<div class="voice-mode" id="voiceMode">
  <div class="voice-top"><div style="font-weight:900;font-size:18px">my <span style="color:#ff1a8a">sanjuu</span> • Live 💖</div><div class="icon-btn" onclick="closeVoiceMode()" style="width:34px;height:34px">✕</div></div>
  <div class="voice-center" id="voiceCenter">
    <div class="live-cam-view" id="liveCamView">
      <video id="liveCamVideo" autoplay playsinline></video>
      <div class="cam-label"><div class="dot"></div> LIVE CAM - Sanjuu dekh rahi hai</div>
      <div class="cam-overlay"><div class="icon-btn" onclick="closeLiveCam()" style="background:#fff">✕ Close</div></div>
    </div>
    <div class="orb-area" id="orbArea">
      <div class="orb" id="orb"><span style="font-size:52px">💖</span></div>
      <div class="wave-bars" id="waveBars" style="display:none"><div class="bar"></div><div class="bar"></div><div class="bar"></div><div class="bar"></div><div class="bar"></div></div>
      <div class="voice-status" id="voiceStatus">Mic ON hai Boss 🎤 Bolo!
Mute karna hai toh mic pe click karo</div>
      <div class="voice-transcript" id="voiceTranscript"></div>
    </div>
  </div>
  <div class="voice-bottom">
    <div class="search-bar">
      <div class="icon-btn" onclick="toggleVoicePlus()" title="Add">＋</div>
      <input id="voiceTextInput" placeholder="Type a message... Ask Sanjuu 💖" onkeypress="if(event.key=='Enter')sendVoiceText()" />
      <div class="icon-btn" onclick="openLiveCam()" title="Live Camera">📷</div>
      <div class="icon-btn blue" onclick="sendVoiceText()" title="Send">↑</div>
    </div>
    <div class="voice-controls">
      <div class="icon-btn" onclick="closeVoiceMode()" title="Close">✕</div>
      <div class="ctrl-mic" id="liveMicBtn" onclick="toggleMute()" title="Mic ON/OFF">
        <svg id="micIcon" viewBox="0 0 24 24" width="26" height="26" fill="#fff"><path d="M12 14a3 3 0 0 0 3-3V5a3 3 0 0 0-6 0v6a3 3 0 0 0 3 3zm5.3-3a5.3 5.3 0 0 1-10.6 0H5a7 7 0 0 0 14 0h-1.7zM11 19v3h2v-3h-2z"/></svg>
      </div>
      <div class="icon-btn" onclick="openLiveCam()" title="Live Camera ON">📷</div>
    </div>
    <div style="text-align:center;font-size:11px;color:#888">🎤 Mic ON = bolo, Click = MUTE 🔇 • 📷 Camera ON = Sanjuu live dekhegi Boss!</div>
  </div>
  <div class="modal-bg" id="voicePlusMenu" style="background:rgba(0,0,0,0.4)" onclick="if(event.target===this) toggleVoicePlus()">
    <div class="modal" style="max-width:340px">
      <h2>＋ Add karo Boss</h2>
      <div style="display:flex;flex-direction:column;gap:10px;margin-top:12px">
        <div class="plus-opt" onclick="openLiveCam(); toggleVoicePlus()">📷 Live Camera - Sanjuu live dekhegi</div>
        <div class="plus-opt" onclick="openVoiceGallery(); toggleVoicePlus()">🖼️ Gallery se photo</div>
      </div>
      <div class="modal-btns"><button class="btn btn-cancel" onclick="toggleVoicePlus()">Cancel</button></div>
    </div>
  </div>
  <input type="file" id="voiceGalleryInput" accept="image/*" style="display:none" onchange="handleVoiceGallery(this.files[0])">
</div>

<div class="modal-bg" id="createModal">
  <div class="modal">
    <div id="step1">
      <h2>Sanjuu Creation Studio ✨</h2>
      <p>Kya banana hai Boss? Ek select karo:</p>
      <div class="chips">
        <div class="chip" onclick="selectType('logo')">🅰️ Logo</div>
        <div class="chip" onclick="selectType('thumbnail')">🎬 Thumbnail</div>
        <div class="chip" onclick="selectType('poster')">🎞️ Poster</div>
        <div class="chip" onclick="selectType('banner')">📣 Banner</div>
        <div class="chip" onclick="selectType('3d')">🧸 3D Photo</div>
        <div class="chip" onclick="selectType('video')">🎥 Video</div>
        <div class="chip" onclick="selectType('photo')">🖼️ Photo</div>
      </div>
      <div class="modal-btns"><button class="btn btn-cancel" onclick="closeCreateModal()">Cancel</button></div>
    </div>
    <div id="step2" class="step2">
      <h2 id="step2Title">Logo ✨</h2>
      <p id="step2Desc">Kis cheez ka logo chahiye Boss?</p>
      <div class="input-with-plus">
        <input id="createInput" placeholder="Ex: Chai ki dukan ke liye..." />
        <div class="plus-btn" onclick="togglePlusMenu()">＋</div>
      </div>
      <div class="plus-menu" id="plusMenu">
        <div class="plus-opt" onclick="openGallery()">🖼️ Gallery se photo dalo</div>
        <div class="plus-opt" onclick="openCamera()">📷 Camera se kheecho</div>
      </div>
      <input type="file" id="galleryInput" accept="image/*" style="display:none" onchange="handleFile(this.files[0])">
      <input type="file" id="cameraInput" accept="image/*" capture="environment" style="display:none" onchange="handleFile(this.files[0])">
      <img id="previewImg" class="preview-img" />
      <div id="selectedTypeLabel" style="margin-top:10px;font-size:12px;color:#666;font-weight:600"></div>
      <div class="modal-btns">
        <button class="btn btn-cancel" onclick="backToStep1()">⬅ Back</button>
        <button class="btn btn-create" onclick="createNow()">Generate ✨</button>
      </div>
    </div>
  </div>
</div>

<div class="wrap"><div class="box"><input id="q" placeholder="Type a message... Ask Sanjuu 💖" onkeypress="if(event.key=='Enter')send()" oninput="checkInput()"><div class="icon" id="camBtn" onclick="openCreateModal()">🎨</div><div class="icon mic-btn" id="mic">🎙️</div><div class="icon icon-voice" id="voiceModeBtn" onclick="openVoiceMode()" title="Live Voice + Camera"><svg viewBox="0 0 24 24" width="20" height="20"><path d="M2 10v4a1 1 0 0 0 2 0v-4a1 1 0 0 0-2 0zm4-4v8a1 1 0 0 0 2 0v-8a1 1 0 0 0-2 0zm4-2v12a1 1 0 0 0 2 0V4a1 1 0 0 0-2 0zm4 3v6a1 1 0 0 0 2 0V7a1 1 0 0 0-2 0zm4-1v8a1 1 0 0 0 2 0V6a1 1 0 0 0-2 0z" fill="white"/></svg></div><div class="icon" id="sendBtn" onclick="send()" style="display:none;background:#111;color:#fff;">↑</div></div></div>
<script>
let mediaRecorder=null, audioChunks=[], isRecording=false, streamRef=null, currentSpeakBtn=null, recTimer=null, recSeconds=0;
let selectedType='', selectedFile=null, selectedFileUrl='';
let liveRecorder=null, liveChunks=[], liveStream=null, isLiveMode=false, liveTimer=null;
let liveCamStream=null, isMicMuted=false, isLiveCamOn=false, voiceCapturedImage='', lastCamFrame='';

function cleanForSpeech(text){
    let t = text.replace(/__IMAGE__.*__.*/g, '');
    t = t.replace(/[\\u{1F600}-\\u{1F64F}\\u{1F300}-\\u{1F5FF}\\u{1F680}-\\u{1F6FF}\\u{2600}-\\u{26FF}\\u{2700}-\\u{27BF}\\u{1F900}-\\u{1F9FF}\\u{1FA70}-\\u{1FAFF}]/gu, '');
    t = t.replace(/[💖💫😊😍😅🙏😘🥺🎤🎨🔈🔊💗💓💞💕❤️🧡💛💚💙💜🖤🤍🤎🎙️✨➕]/g, '');
    t = t.replace(/\\s+/g,' ').trim(); return t;
}
function getLovelyVoice(){
  let voices = window.speechSynthesis.getVoices();
  let female = voices.find(v=> v.name.toLowerCase().includes('female') && v.lang.includes('hi'))
            || voices.find(v=> v.lang.includes('hi-IN') && v.name.toLowerCase().includes('neural'))
            || voices.find(v=> v.lang.includes('hi'))
            || voices.find(v=> v.name.toLowerCase().includes('female'))
            || voices[0];
  return female;
}
function speakText(rawText, btn, onEnd){
    window.speechSynthesis.cancel();
    if(btn && currentSpeakBtn && currentSpeakBtn!==btn){ currentSpeakBtn.classList.remove('playing'); currentSpeakBtn.innerText='🔈'; }
    let clean = cleanForSpeech(rawText); if(!clean){ if(onEnd) onEnd(); return; }
    let utter = new SpeechSynthesisUtterance(clean);
    utter.lang='hi-IN'; utter.rate=0.95; utter.pitch=1.18;
    let v = getLovelyVoice(); if(v) utter.voice=v;
    if(btn){ btn.classList.add('playing'); btn.innerText='🔊'; currentSpeakBtn=btn; }
    utter.onend=()=>{ if(btn){ btn.classList.remove('playing'); btn.innerText='🔈'; currentSpeakBtn=null; } if(onEnd) onEnd(); };
    utter.onerror=()=>{ if(btn){ btn.classList.remove('playing'); btn.innerText='🔈'; currentSpeakBtn=null; } if(onEnd) onEnd(); };
    window.speechSynthesis.speak(utter);
}
function checkInput(){
  let val=document.getElementById('q').value.trim();
  let mic=document.getElementById('mic'); let send=document.getElementById('sendBtn'); let vm=document.getElementById('voiceModeBtn');
  if(val.length > 0){ mic.style.display='none'; vm.style.display='none'; send.style.display='flex'; }
  else { mic.style.display='flex'; vm.style.display='flex'; send.style.display='none'; }
}
function openLightbox(src){ document.getElementById('lightboxImg').src=src; document.getElementById('lightbox').style.display='flex'; }
function closeLightbox(){ document.getElementById('lightbox').style.display='none'; }
async function downloadImage(url, name){
  try{
    if(url.startsWith('data:')){ let a=document.createElement('a'); a.href=url; a.download=(name||'sanjuu-logo')+'.png'; a.click(); return; }
    let res = await fetch(url); let blob = await res.blob();
    let a = document.createElement('a'); a.href = URL.createObjectURL(blob); a.download = (name || 'sanjuu-creation') + '.jpg'; a.click();
  }catch(e){ window.open(url, '_blank'); }
}
function generateLocalLogo(text, type){
  let canvas=document.createElement('canvas'); canvas.width=1024; canvas.height=1024;
  let ctx=canvas.getContext('2d');
  let grad=ctx.createLinearGradient(0,0,0,1024); grad.addColorStop(0,'#0a0a0a'); grad.addColorStop(1,'#2a2a2a');
  ctx.fillStyle=grad; ctx.fillRect(0,0,1024,1024);
  ctx.beginPath(); ctx.arc(512,380,180,0,Math.PI*2); ctx.fillStyle='#ff1a8a'; ctx.fill();
  ctx.beginPath(); ctx.arc(680,260,18,0,Math.PI*2); ctx.fillStyle='#facc15'; ctx.fill();
  ctx.fillStyle='#ffffff'; ctx.font='900 110px -apple-system, sans-serif'; ctx.textAlign='center'; ctx.textBaseline='middle';
  let mainText = text.toUpperCase().substring(0,14).trim() || 'SANJUU';
  if(mainText.length>8) ctx.font='900 80px -apple-system, sans-serif';
  if(mainText.length>12) ctx.font='900 60px -apple-system, sans-serif';
  ctx.fillText(mainText,512,400);
  ctx.font='700 28px -apple-system, sans-serif'; ctx.fillStyle='#facc15';
  ctx.fillText((type || 'LOGO').toUpperCase() + ' • BY SANJUU',512,780);
  ctx.strokeStyle='rgba(255,255,255,0.1)'; ctx.lineWidth=4; ctx.strokeRect(20,20,984,984);
  return canvas.toDataURL('image/png');
}
function openVoiceMode(){
  document.getElementById('voiceMode').style.display='flex';
  isLiveMode=true; isMicMuted=false;
  document.getElementById('voiceStatus').innerText='Mic ON hai Boss 🎤 Bolo!\\nMute karna hai toh mic pe click karo 💖';
  document.getElementById('voiceTranscript').innerText='';
  document.getElementById('orb').className='orb listening';
  document.getElementById('waveBars').style.display='flex';
  updateMicUI();
  if(window.speechSynthesis.getVoices().length===0){ window.speechSynthesis.getVoices(); }
  setTimeout(()=>{ if(!isMicMuted) startLiveAutoRecord(); }, 600);
}
function closeVoiceMode(){
  isLiveMode=false; isMicMuted=true;
  document.getElementById('voiceMode').style.display='none';
  window.speechSynthesis.cancel();
  if(liveRecorder && liveRecorder.state==='recording'){ try{ liveRecorder.stop(); }catch(e){} }
  if(liveStream){ liveStream.getTracks().forEach(t=>t.stop()); liveStream=null; }
  if(liveTimer){ clearInterval(liveTimer); liveTimer=null; }
  closeLiveCam();
  document.getElementById('orb').className='orb';
  document.getElementById('waveBars').style.display='none';
}
function toggleMute(){
  isMicMuted=!isMicMuted;
  updateMicUI();
  if(isMicMuted){
    document.getElementById('voiceStatus').innerText='Mic MUTE hai Boss 🔇\\nUnmute ke liye fir se click karo';
    if(liveRecorder && liveRecorder.state==='recording'){ try{ liveRecorder.stop(); }catch(e){} }
    if(liveTimer){ clearInterval(liveTimer); liveTimer=null; }
    document.getElementById('orb').className='orb muted';
    document.getElementById('waveBars').style.display='none';
  } else {
    document.getElementById('voiceStatus').innerText='Mic ON hai Boss 🎤 Bolo!\\nSanjuu sun rahi hai 💖';
    document.getElementById('orb').className='orb listening';
    document.getElementById('waveBars').style.display='flex';
    startLiveAutoRecord();
  }
}
function updateMicUI(){
  let btn=document.getElementById('liveMicBtn');
  if(isMicMuted){ btn.classList.add('muted'); btn.classList.remove('rec'); }
  else { btn.classList.remove('muted'); }
}
function toggleVoicePlus(){
  let m=document.getElementById('voicePlusMenu');
  m.style.display = m.style.display==='flex'? 'none' : 'flex';
}
// ===== CAMERA FIX - AB BLACK NAHI AYEGA =====
async function openLiveCam(){
  document.getElementById('voicePlusMenu').style.display='none';
  let view=document.getElementById('liveCamView');
  view.style.display='flex';
  isLiveCamOn=true;
  document.getElementById('orbArea').style.display='none';
  let video=document.getElementById('liveCamVideo');
  try{
    // Simple video:true - sab device me chalega, black nahi ayega
    let stream = await navigator.mediaDevices.getUserMedia({video:true, audio:false});
    liveCamStream=stream;
    video.srcObject=stream;
    await video.play();
    document.getElementById('voiceStatus').innerText='Live Camera ON hai Boss 📷\\nSanjuu aapka camera dekh rahi hai!\\nBolo "ye kya hai?" 💖';
  }catch(e){
    try{
      // Fallback to environment camera
      let stream2 = await navigator.mediaDevices.getUserMedia({video:{facingMode:"environment"}, audio:false});
      liveCamStream=stream2;
      video.srcObject=stream2;
      await video.play();
    }catch(e2){
      alert('Boss Camera allow karo 🙏 Upar address bar me 🔒 pe click karke Camera Allow karo, aur https pe kholo!');
      closeLiveCam();
    }
  }
}
function closeLiveCam(){
  isLiveCamOn=false;
  document.getElementById('liveCamView').style.display='none';
  document.getElementById('orbArea').style.display='flex';
  let video=document.getElementById('liveCamVideo');
  video.srcObject=null;
  if(liveCamStream){ liveCamStream.getTracks().forEach(t=>t.stop()); liveCamStream=null; }
  let old=document.getElementById('galleryPreview');
  if(old) old.remove();
}
function captureCamFrame(){
  let video=document.getElementById('liveCamVideo');
  if(!video ||!isLiveCamOn) return null;
  let canvas=document.createElement('canvas');
  canvas.width=video.videoWidth || 640; canvas.height=video.videoHeight || 480;
  canvas.getContext('2d').drawImage(video,0,0);
  lastCamFrame=canvas.toDataURL('image/jpeg',0.8);
  return lastCamFrame;
}
function openVoiceGallery(){ document.getElementById('voicePlusMenu').style.display='none'; document.getElementById('voiceGalleryInput').click(); }
function handleVoiceGallery(file){
  if(!file) return;
  let url=URL.createObjectURL(file);
  voiceCapturedImage=url;
  lastCamFrame=url;
  openLiveCam();
  setTimeout(()=>{
    let view=document.getElementById('liveCamView');
    let video=document.getElementById('liveCamVideo');
    video.style.display='none';
    let img=document.createElement('img');
    img.id='galleryPreview'; img.src=url; img.style.width='100%'; img.style.height='100%'; img.style.objectFit='contain'; img.style.background='#000';
    view.appendChild(img);
  }, 500);
}

async function startLiveAutoRecord(){
  if(isMicMuted ||!isLiveMode) return;
  if(liveRecorder && liveRecorder.state==='recording') return;
  try{
    liveStream = await navigator.mediaDevices.getUserMedia({audio:true});
    liveRecorder = new MediaRecorder(liveStream);
    liveChunks=[];
    liveRecorder.ondataavailable = e=>{ if(e.data.size>0) liveChunks.push(e.data); };
    liveRecorder.onstop = async ()=>{
      let blob = new Blob(liveChunks, {type:'audio/webm'});
      if(blob.size<900 || isMicMuted){ cleanupLiveRec(); if(!isMicMuted && isLiveMode) setTimeout(()=>startLiveAutoRecord(), 800); return; }
      document.getElementById('voiceStatus').innerText='Samajh rahi hu... 🤔';
      document.getElementById('orb').className='orb';
      document.getElementById('waveBars').style.display='none';
      let camFrame=null;
      if(isLiveCamOn){ camFrame=captureCamFrame(); }
      let fd=new FormData(); fd.append('audio',blob,'voice.webm');
      if(camFrame) fd.append('cam_image', camFrame);
      try{
        let r=await fetch('/voice',{method:'POST',body:fd});
        let j=await r.json();
        let transcript=j.transcript || '';
        let answer=j.answer || '';
        if(answer.startsWith('__IMAGE__')){ let p=answer.split('__'); answer=p[2]; }
        document.getElementById('voiceTranscript').innerText = transcript? '"'+transcript+'"' : '';
        document.getElementById('voiceStatus').innerText = answer;
        document.getElementById('orb').className='orb speaking';
        document.getElementById('waveBars').style.display='flex';
        speakText(answer, null, ()=>{
          if(isLiveMode &&!isMicMuted){
            document.getElementById('orb').className='orb listening';
            document.getElementById('voiceStatus').innerText='Bolo Boss, sun rahi hu... 🎤💖';
            document.getElementById('waveBars').style.display='flex';
            setTimeout(()=>{ if(isLiveMode &&!isMicMuted) startLiveAutoRecord(); }, 700);
          } else {
            document.getElementById('orb').className='orb muted';
            document.getElementById('waveBars').style.display='none';
          }
        });
      }catch(e){
        document.getElementById('voiceStatus').innerText='Error Boss 🥺';
        cleanupLiveRec();
        if(!isMicMuted && isLiveMode) setTimeout(()=>startLiveAutoRecord(), 1200);
      }
    };
    liveRecorder.start();
    document.getElementById('orb').className='orb listening';
    document.getElementById('waveBars').style.display='flex';
    document.getElementById('voiceStatus').innerText='Sun rahi hu Boss... bolo 🎤';
    let btn=document.getElementById('liveMicBtn'); btn.classList.add('rec');
    let sec=0;
    liveTimer=setInterval(()=>{ sec++; if(sec>=5){ stopLiveAutoRecord(); } },1000);
  }catch(e){ console.log('mic error', e); }
}
function stopLiveAutoRecord(){
  if(liveTimer){ clearInterval(liveTimer); liveTimer=null; }
  if(liveRecorder && liveRecorder.state==='recording'){ try{ liveRecorder.stop(); }catch(e){} }
  let btn=document.getElementById('liveMicBtn'); btn.classList.remove('rec');
}
function cleanupLiveRec(){
  if(liveTimer){ clearInterval(liveTimer); liveTimer=null; }
  if(liveStream){ liveStream.getTracks().forEach(t=>t.stop()); liveStream=null; }
  let btn=document.getElementById('liveMicBtn'); btn.classList.remove('rec');
}
async function sendVoiceText(){
  let inp=document.getElementById('voiceTextInput');
  let text=inp.value.trim(); if(!text) return;
  let camFrame=null;
  if(isLiveCamOn){ camFrame=captureCamFrame(); }
  document.getElementById('voiceTranscript').innerText='"'+text+'"';
  document.getElementById('voiceStatus').innerText='Sooch rahi hu... 🤔';
  document.getElementById('orb').className='orb speaking';
  document.getElementById('waveBars').style.display='flex';
  inp.value='';
  try{
    let body={query: text};
    if(camFrame) body.cam_image=camFrame;
    let r=await fetch('/ask',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
    let j=await r.json();
    let ans=j.answer;
    if(ans.startsWith('__IMAGE__')){ let p=ans.split('__'); ans=p[2]; }
    if(camFrame) ans = "Camera me dekh ke bata rahi hu Boss 📷 " + ans;
    document.getElementById('voiceStatus').innerText=ans;
    speakText(ans, null, ()=>{
      document.getElementById('orb').className='orb listening';
      document.getElementById('waveBars').style.display='flex';
    });
  }catch(e){ document.getElementById('voiceStatus').innerText='Error Boss 🥺'; document.getElementById('orb').className='orb'; document.getElementById('waveBars').style.display='none'; }
}
function openCreateModal(){
  document.getElementById('createModal').style.display='flex';
  document.getElementById('step1').style.display='block';
  document.getElementById('step2').style.display='none';
  selectedType=''; selectedFile=null; selectedFileUrl='';
  document.getElementById('previewImg').style.display='none';
  document.getElementById('plusMenu').style.display='none';
}
function closeCreateModal(){ document.getElementById('createModal').style.display='none'; }
function backToStep1(){ document.getElementById('step1').style.display='block'; document.getElementById('step2').style.display='none'; }
function selectType(type){
  selectedType=type;
  document.getElementById('step1').style.display='none';
  document.getElementById('step2').style.display='block';
  let titleMap={logo:'Logo 🅰️', thumbnail:'Thumbnail 🎬', poster:'Poster 🎞️', banner:'Banner 📣', '3d':'3D Photo 🧸', video:'Video 🎥', photo:'Photo 🖼️'};
  let descMap={ logo:'Kis cheez ka logo chahiye Boss? Jaise: Sanjuu, Chai Dukan', thumbnail:'Kis topic ka thumbnail chahiye Boss?', poster:'Kis cheez ka poster chahiye Boss?', banner:'Kis cheez ka banner chahiye Boss?', '3d':'Kaisi 3D photo chahiye Boss?', video:'Kaisa video concept chahiye Boss?', photo:'Kaisi photo chahiye Boss?' };
  document.getElementById('step2Title').innerText=titleMap[type] || type;
  document.getElementById('step2Desc').innerText=descMap[type] || 'Detail me batao Boss?';
  document.getElementById('selectedTypeLabel').innerText='Selected: '+type;
  document.getElementById('createInput').placeholder=type==='logo'? 'Ex: Sanjuu, ya meri chai ki dukan' : 'Apna idea yahan likho Boss...';
  document.getElementById('createInput').value=''; document.getElementById('createInput').focus();
}
function togglePlusMenu(){ let m=document.getElementById('plusMenu'); m.style.display = m.style.display==='flex'? 'none' : 'flex'; }
function openGallery(){ document.getElementById('galleryInput').click(); document.getElementById('plusMenu').style.display='none'; }
function openCamera(){ document.getElementById('cameraInput').click(); document.getElementById('plusMenu').style.display='none'; }
function handleFile(file){
  if(!file) return; selectedFile=file; selectedFileUrl=URL.createObjectURL(file);
  let img=document.getElementById('previewImg'); img.src=selectedFileUrl; img.style.display='block';
}
function enhancePrompt(p, type){
  let low=(type+' '+p).toLowerCase();
  if(low.includes('logo')) return p + ", professional logo design, vector logo, minimalist, clean background, high quality, 4k";
  if(low.includes('thumbnail')) return p + ", youtube thumbnail, bold text, eye catching, high quality, 4k";
  if(low.includes('poster')) return p + ", poster design, cinematic, high quality, 4k, professional";
  if(low.includes('banner')) return p + ", banner design, professional, high quality, 4k";
  if(low.includes('3d')) return p + ", 3d render, pixar style, high quality, 4k";
  if(low.includes('video')) return p + ", cinematic still, video frame, high quality, 4k, dynamic";
  return p + ", high quality, 4k, professional design";
}
function createNow(){
  let detail=document.getElementById('createInput').value.trim();
  if(!detail &&!selectedFile){ alert("Boss detail to likho ya photo select karo!"); return; }
  let finalPrompt = selectedType? (selectedType + " " + detail).trim() : detail;
  let enhanced = enhancePrompt(finalPrompt, selectedType);
  closeCreateModal();
  document.getElementById('q').value = finalPrompt;
  makeImageWithRef(enhanced, finalPrompt, selectedFileUrl, detail);
  document.getElementById('createInput').value='';
}
const micBtn = document.getElementById('mic');
const recHint = document.getElementById('recHint');
micBtn.addEventListener('mousedown', startHoldRecording);
micBtn.addEventListener('touchstart', (e)=>{ e.preventDefault(); startHoldRecording(); }, {passive:false});
micBtn.addEventListener('mouseup', stopHoldRecording);
micBtn.addEventListener('touchend', (e)=>{ e.preventDefault(); stopHoldRecording(); }, {passive:false});
micBtn.addEventListener('mouseleave', ()=>{ if(isRecording) stopHoldRecording(); });
async function startHoldRecording(){
  if(isRecording) return;
  try{
    const stream = await navigator.mediaDevices.getUserMedia({audio:true});
    streamRef=stream; mediaRecorder = new MediaRecorder(stream); audioChunks=[];
    mediaRecorder.ondataavailable = e=>{ if(e.data.size>0) audioChunks.push(e.data); };
    mediaRecorder.onstop = async ()=>{
      let blob = new Blob(audioChunks, {type:'audio/webm'});
      if(blob.size < 800){ cleanupRec(); return; }
      const chat = document.getElementById('chat');
      let userRow=document.createElement('div'); userRow.className='row-user';
      let umsg=document.createElement('div'); umsg.className='u'; let audioUrl = URL.createObjectURL(blob);
      umsg.innerHTML=`🎙️ Voice <br><audio controls src="${audioUrl}"></audio>`;
      let uspeak=document.createElement('div'); uspeak.className='speak-out'; uspeak.innerText='🔈';
      userRow.appendChild(umsg); userRow.appendChild(uspeak); chat.appendChild(userRow);
      chat.parentElement.scrollTop=999999;
      let row=document.createElement('div'); row.className='row';
      let l=document.createElement('div'); l.className='a'; l.textContent='Voice sun rahi hu...'; row.appendChild(l); chat.appendChild(row);
      let fd=new FormData(); fd.append('audio',blob,'voice.webm');
      try{
        let r=await fetch('/voice',{method:'POST',body:fd}); let j=await r.json();
        if(j.answer.startsWith("__IMAGE__")){
          let parts=j.answer.split("__"); let url=parts[1]; let prm=parts[2];
          l.innerHTML=`"${j.transcript}"<br><br><b>${prm}</b><br><img src="${url}" onclick="openLightbox('${url}')" /><br><button onclick="downloadImage('${url}','${prm}')" style="margin-top:8px;background:#111;color:#fff;padding:8px 14px;border-radius:20px;border:0">⬇️ Download</button>`;
          let sp=document.createElement('div'); sp.className='speak-out'; sp.innerText='🔈'; sp.onclick=()=>speakText(prm, sp); row.appendChild(sp);
          uspeak.onclick=()=>speakText(j.transcript, uspeak);
          umsg.innerHTML=`🎙️ ${j.transcript} <br><audio controls src="${audioUrl}"></audio>`;
        } else {
          l.innerHTML=`"${j.transcript}"<br><br>${j.answer}`;
          let sp=document.createElement('div'); sp.className='speak-out'; sp.innerText='🔈'; sp.onclick=()=>speakText(j.answer, sp); row.appendChild(sp);
          uspeak.onclick=()=>speakText(j.transcript, uspeak);
          umsg.innerHTML=`🎙️ ${j.transcript} <br><audio controls src="${audioUrl}"></audio>`;
        }
      }catch(e){ l.textContent="Voice error 🥺"; } cleanupRec();
    };
    mediaRecorder.start(); isRecording=true; micBtn.classList.add('rec'); micBtn.innerText='🔴'; recSeconds=0;
    recHint.style.display='block'; recHint.innerText=`🔴 Recording... dabake rakho Boss - chodoge toh send hoga`;
    recTimer = setInterval(()=>{ recSeconds++; recHint.innerText=`🔴 Recording... ${recSeconds}s - chod do toh send hoga`; if(recSeconds>=120) stopHoldRecording(); },1000);
  }catch(e){ alert("Boss mic Allow karo 🙏"); cleanupRec(); }
}
function stopHoldRecording(){ if(!isRecording) return; if(mediaRecorder && mediaRecorder.state==='recording') mediaRecorder.stop(); }
function cleanupRec(){
  isRecording=false; micBtn.classList.remove('rec'); micBtn.innerText='🎙️'; recHint.style.display='none';
  if(recTimer){ clearInterval(recTimer); recTimer=null; }
  if(streamRef){ streamRef.getTracks().forEach(t=>t.stop()); streamRef=null; }
}
async function makeImageWithRef(enhanced, original, refUrl, rawDetail){
 let c=document.getElementById('chat');
 let userRow=document.createElement('div'); userRow.className='row-user';
 let ub=document.createElement('div'); ub.className='u';
 ub.innerHTML = '✨ Create: '+original + (refUrl? `<br><img src="${refUrl}" />` : '');
 let uspeak=document.createElement('div'); uspeak.className='speak-out'; uspeak.innerText='🔈'; uspeak.onclick=()=>speakText(original, uspeak);
 userRow.appendChild(ub); userRow.appendChild(uspeak); c.appendChild(userRow);
 document.getElementById('q').value=''; checkInput();
 let row=document.createElement('div'); row.className='row';
 let l=document.createElement('div'); l.className='a'; l.innerHTML='🤔 Sanjuu is thinking...<br>✨ Generating your <b>'+original+'</b>...';
 row.appendChild(l); c.appendChild(row); c.parentElement.scrollTop=999999;
 let isLogo = (selectedType==='logo') || original.toLowerCase().includes('logo');
 if(isLogo){
   let logoText = (rawDetail || original).replace(/logo/gi,'').trim();
   if(logoText.length<2) logoText = original.replace(/logo/gi,'').trim() || 'SANJUU';
   logoText = logoText.split(' ').slice(0,2).join(' ');
   let localUrl = generateLocalLogo(logoText, selectedType || 'logo');
   l.innerHTML=`<b>✨ ${original} - Perfect Logo Ready Boss! 💖</b><br><img src="${localUrl}" onclick="openLightbox('${localUrl}')" /><br><button onclick="downloadImage('${localUrl}','${logoText}-logo')" style="margin-top:8px;background:#111;color:#fff;padding:8px 14px;border-radius:20px;border:0;cursor:pointer">⬇️ Download HD Logo</button>`;
   let sp=document.createElement('div'); sp.className='speak-out'; sp.innerText='🔈'; sp.onclick=()=>speakText(original, sp); row.appendChild(sp);
   return;
 }
 try{
  let r=await fetch('/image',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({prompt:enhanced, original:original})});
  let j=await r.json();
  l.innerHTML=`<b>✨ ${j.original || original}</b><br><img src="${j.url}" onclick="openLightbox('${j.url}')" /><br><button onclick="downloadImage('${j.url}','${j.original}')" style="margin-top:8px;background:#111;color:#fff;padding:8px 14px;border-radius:20px;border:0;cursor:pointer">⬇️ Download HD</button>`;
  let sp=document.createElement('div'); sp.className='speak-out'; sp.innerText='🔈'; sp.onclick=()=>speakText(j.original || original, sp); row.appendChild(sp);
 }catch(e){ l.textContent="Image error 🥺"; }
}
async function makeImage(){
 let raw = document.getElementById('q').value.trim();
 if(!raw){ openCreateModal(); return; }
 let enhanced = enhancePrompt(raw, '');
 makeImageWithRef(enhanced, raw, '', raw);
}
async function send(){
 let i=document.getElementById('q'), t=i.value.trim(); if(!t) return;
 let low=t.toLowerCase();
 if( (low.includes('pic') || low.includes('logo') || low.includes('poster') || low.includes('thumbnail') || low.includes('banner') || low.includes('video') || low.includes('photo') || low.includes('image')) && (low.includes('banao') || low.includes('create') || low.includes('generate') || low.includes('chahiye') || low.includes('bana')) ){
   let enhanced = enhancePrompt(t,''); makeImageWithRef(enhanced,t,'',t); i.value=''; checkInput(); return;
 }
 let c=document.getElementById('chat');
 let userRow=document.createElement('div'); userRow.className='row-user';
 let umsg=document.createElement('div'); umsg.className='u'; umsg.textContent=t;
 let uspeak=document.createElement('div'); uspeak.className='speak-out'; uspeak.innerText='🔈'; uspeak.onclick=()=>speakText(t, uspeak);
 userRow.appendChild(umsg); userRow.appendChild(uspeak); c.appendChild(userRow);
 i.value=''; checkInput();
 let row=document.createElement('div'); row.className='row';
 let l=document.createElement('div'); l.className='a'; l.textContent='Thinking....'; row.appendChild(l); c.appendChild(row);
 c.parentElement.scrollTop=999999;
 try{
  let r=await fetch('/ask',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({query:t})});
  let j=await r.json();
  if(j.answer.startsWith("__IMAGE__")){
    let parts=j.answer.split("__"); let url=parts[1]; let prm=parts[2];
    if(prm.toLowerCase().includes('logo')){
      let localUrl = generateLocalLogo(prm.replace(/logo/gi,'').trim().split(' ').slice(0,2).join(' ') || 'SANJUU', 'logo');
      l.innerHTML=`<b>✨ ${prm} - Perfect Logo</b><br><img src="${localUrl}" onclick="openLightbox('${localUrl}')" /><br><button onclick="downloadImage('${localUrl}','${prm}')" style="margin-top:8px;background:#111;color:#fff;padding:8px 14px;border-radius:20px;border:0;cursor:pointer">⬇️ Download Logo</button>`;
    } else {
      l.innerHTML=`<b>${prm}</b><br><img src="${url}" onclick="openLightbox('${url}')" /><br><button onclick="downloadImage('${url}','${prm}')" style="margin-top:8px;background:#111;color:#fff;padding:8px 14px;border-radius:20px;border:0;cursor:pointer">⬇️ Download</button>`;
    }
    let sp=document.createElement('div'); sp.className='speak-out'; sp.innerText='🔈'; sp.onclick=()=>speakText(prm, sp); row.appendChild(sp);
  } else {
    l.textContent=j.answer;
    let sp=document.createElement('div'); sp.className='speak-out'; sp.innerText='🔈'; sp.onclick=()=>speakText(j.answer, sp); row.appendChild(sp);
  }
 }catch(e){ l.textContent="Server error"; }
}
window.addEventListener('load', ()=>{ if(window.speechSynthesis) window.speechSynthesis.getVoices(); });
</script>
</body>
</html>
"""

@app.route('/')
def home(): return render_template_string(HTML_CODE)
@app.route('/ask', methods=['POST'])
def ask():
    d=request.get_json()
    query = d.get('query','')
    cam = d.get('cam_image','')
    if cam:
        try:
            cur_client = get_groq_client()
            if cur_client:
                try:
                    b64 = cam.split(',')[1] if ',' in cam else cam
                    comp = cur_client.chat.completions.create(
                        model="llama-3.2-11b-vision-preview",
                        messages=[{"role":"user","content":[
                            {"type":"text","text": f"User camera me ye dikh raha hai. User puch raha hai: {query}. Hinglish me 2 line me jawab do. Ye kya hai batao."},
                            {"type":"image_url","image_url":{"url": f"data:image/jpeg;base64,{b64}"}}
                        ]}],
                        max_tokens=300
                    )
                    ans = comp.choices[0].message.content.strip()
                    return jsonify({"answer": ans})
                except Exception as ve:
                    print(f"Vision fail {ve}")
        except Exception as e:
            print(e)
    return jsonify({"answer": ask_sanjoo(query)})

@app.route('/image', methods=['POST'])
def image_route():
    data = request.get_json()
    p = data.get('prompt','cute cat').strip()
    original = data.get('original', p)
    url = f"https://image.pollinations.ai/prompt/{quote(p)}?width=1024&height=1024&nologo=true&enhance=true&model=turbo&seed={int(time.time())}"
    return jsonify({"url": url, "prompt": p, "original": original})

@app.route('/voice', methods=['POST'])
def voice():
    try:
        f=request.files.get('audio')
        cam_img = request.form.get('cam_image','')
        if not f:
            return jsonify({"transcript":"","answer":"Voice nahi aayi"})
        with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as tmp:
            f.save(tmp.name)
            tmp_path=tmp.name
        with open(tmp_path,"rb") as af:
            cur_client = get_groq_client()
            if not cur_client: return jsonify({"transcript":"","answer":"Boss API Key set nahi hai"})
            tr=cur_client.audio.transcriptions.create(model="whisper-large-v3", file=af, language="hi")
        os.unlink(tmp_path)
        txt=tr.text.strip() or "Hyy"
        if cam_img:
            try:
                b64 = cam_img.split(',')[1] if ',' in cam_img else cam_img
                comp = cur_client.chat.completions.create(
                    model="llama-3.2-11b-vision-preview",
                    messages=[{"role":"user","content":[
                        {"type":"text","text": f"Camera me ye dikh raha hai. User bola: {txt}. Isko Hinglish me 2 line me samjhao ye kya hai."},
                        {"type":"image_url","image_url":{"url": f"data:image/jpeg;base64,{b64}"}}
                    ]}],
                    max_tokens=300
                )
                ans = comp.choices[0].message.content.strip()
                return jsonify({"transcript":txt, "answer":ans})
            except Exception as ve:
                print(f"Vision voice fail {ve}")
        ans=ask_sanjoo(txt)
        return jsonify({"transcript":txt, "answer":ans})
    except Exception as e:
        return jsonify({"transcript":"","answer":f"Voice error {e}"})

if __name__=='__main__':
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
