from flask import Flask, request, jsonify, render_template_string
from groq import Groq
from ddgs import DDGS
import re, os, tempfile, time
from urllib.parse import quote

app = Flask(__name__)

# ===== FIX 1: CACHE YAHAN HONA CHAHIYE =====
CACHE = {}
CACHE["user_name"] = ""

# ===== FIX 2: YAHAN 10-12 KEYS DAALO - ENV SE (GITHUB SAFE) =====
RAW_KEYS = os.environ.get("GROQ_API_KEYS", os.environ.get("GROQ_API_KEY", ""))
GROQ_KEYS = [k.strip() for k in RAW_KEYS.split(",") if k.strip() and len(k) > 20]

key_index = 0

def get_groq_client():
    global key_index
    if not GROQ_KEYS:
        return None
    key = GROQ_KEYS[key_index % len(GROQ_KEYS)]
    key_index += 1
    print(f"Using Key No. {key_index % len(GROQ_KEYS)} : {key[:10]}...")
    return Groq(api_key=key)

# ===== Aapne jo samjhaya tha - Wo sab yahan add hai - KUCH NAHI KAATA =====
def get_instant_answer(q_low):
    if any(x in q_low for x in ["main kaun hu","mai kaun hu","main kon hu","mai kon hu","mera naam kya hai"]):
        if "vikash" in q_low or "vikas" in CACHE.get("user_name",""):
            return "Boss aap Vikash ho! 😊 Aapne abhi bataya tha! Aap mere naye Boss ho 💖"
        return "Boss aapne abhi tak apna naam nahi bataya 😅 Aap batao aap kaun ho? Main yaad rakh lungi!"
    if any(x in q_low for x in ["mai to","main to","mera naam"]):
        if "vikash" in q_low or "vikas" in q_low:
            CACHE["user_name"] = "vikash"
            return "Arey waah Boss Vikash! 😍 Yaad rakh liya maine! Aaj se aap Vikash Boss ho! 💖 Ab batao kya help karu?"
        if "karan" in q_low:
            if "kaise" in q_low or "kaise ho sktha" in q_low:
                return "Haan Boss sahi bola aapne! 😅 Sorry sorry! Aap Vikash ho, Karan nahi! Karan toh is app ke owner hain Alot se! Aap batao Vikash Boss, kya kaam hai? 🙏"
    if "karan yadav" in q_low and "kisne banaya" not in q_low and "kaise" not in q_low:
        if any(x in q_low for x in ["kaun hai","kya karta","details","number","contact","ghar"]):
            return "Boss, mujhe mere Boss Karan Yadav ke baare me aur detail dene ki permission nahi hai."
    if any(x in q_low for x in ["kansana","idal","edal","aidal"]):
        return "Boss, Idal Singh Kansana MP ke Krishi Mantri hain.\n1. Post: MP Kisan Kalyan Mantri\n2. Seat: Sumawali, Morena se 5 baar Vidhayak\n3. Samaj: Gurjar samaj ke Chambal-Gwalior ke sabse bade neta"
    if any(x in q_low for x in ["jyotish","rashi","rashifal","kundli","kundali","horoscope","bhavishya","grah","nakshatra","janm","mangal dosh","shani"]):
        return "Boss Jyotish Vidya ke hisab se suno 💫:\n1. 12 Rashiyan: Mesh, Vrishabh, Mithun...\n2. 9 Grah: Surya, Chandra...\nBoss apni Rashi batao main detail bata deti hu! 🙏"
    if any(x in q_low for x in ["song","gaana","gana","movie","film","music","geet"]) and "kisne banaya" in q_low:
        return None
    if any(x in q_low for x in ["tumhe kisne banaya","who made you","tum kon ho","tum kaun ho","tu kaun hai"]):
        if "main kaun" not in q_low and "mai kaun" not in q_low:
            return "Main Sanjuu hu 💖 Ek AI Assistant hu! Mujhe poori Sanjuu Team ne banaya hai, mere owner Karan Yadav hain Alot, Ratlam MP se! 😊"
    if "love you" in q_low: return "Boss, I love you too! 💖😘"
    if q_low in ["accha ji","accha","ok","hyy","hi","hello","hii","kaise ho"] or q_low.startswith("hi ") or q_low.startswith("hello "):
        return "Boss, Hyy! Bolo kya kaam hai? 😊 Main sun rahi hu 💖"
    return None

def is_image_request(q_low):
    keywords = ["pic","pics","pix","photo","photos","foto","image","img","tasveer","chitra","elephant","haathi","hathi"]
    actions = ["bej","bhej","bejo","bhejo","dikhao","dikha","banao","send","chahiye","do"]
    has_key = any(k in q_low for k in keywords)
    has_act = any(a in q_low for a in actions)
    return has_key and has_act

def ask_sanjoo(query):
    q_low = query.lower().strip()
    if not q_low: return "Boss kuch likho to sahi"
    if q_low in CACHE: return CACHE[q_low]
    instant = get_instant_answer(q_low)
    if instant:
        CACHE[q_low]=instant
        return instant
    if is_image_request(q_low):
        clean = q_low
        for w in ["pic","pics","pix","photo","photos","foto","image","img","ki","ka","bej","bhej","bejo","bhejo","dikhao","dikha","na","jara","please","plz","bej na","bhej na","bana","banao","mujhe","ek"]:
            clean = clean.replace(w, "")
        clean = clean.strip()
        if clean == "" or len(clean) < 3:
            if "elephant" in q_low or "haathi" in q_low or "hathi" in q_low:
                clean = "cute baby elephant"
            else:
                clean = "cute cat"
        url = f"https://image.pollinations.ai/prompt/{quote(clean)}?width=1024&height=1024&nologo=true&enhance=true&model=flux&seed={int(time.time())}"
        ans = f"__IMAGE__{url}__{clean}"
        CACHE[q_low]=ans
        return ans
    rag = ""
    if len(q_low.split()) > 4:
        try:
            with DDGS() as ddgs:
                r = list(ddgs.text(query, max_results=1))
                rag = r[0]['body'][:600] if r else ""
        except:
            rag=""
    prompt = f"You are Sanjuu made by Sanjuu Team owner Karan Yadav. You are a helpful friendly assistant. DATA:{rag} USER:{query} Answer short Hinglish 2 lines. Do not talk about jyotish, rashi, kundli unless user asks about it."
    if not GROQ_KEYS:
        return "Boss Render pe GROQ_API_KEYS set nahi hai 🙏 Environment Variables me keys daalo"
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
                print(f"Model {model_name} fail: {e}")
                time.sleep(0.2)
                if "429" in str(e) or "rate_limit" in str(e).lower():
                    break
                continue
    return "Boss 1 min ruko plz 🙏 Groq thoda busy hai"

HTML_CODE = """
<!DOCTYPE html>
<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>my sanjuu</title>
<style>
*{box-sizing:border-box}body{margin:0;font-family:-apple-system,sans-serif;background:#fff;height:100dvh;display:flex;flex-direction:column}
.head{padding:20px 18px 10px;display:flex;justify-content:space-between;align-items:center}
.sanjuu{font-size:42px;font-weight:900;line-height:0.9}.sanjuu b{color:#111}.sanjuu span{color:#ff1a8a}
.live{color:#00c950;font-size:12px;font-weight:700;margin-top:6px}
.coding{width:58px;height:58px;background:#111;border:2px solid #facc15;border-radius:50%;display:flex;align-items:center;justify-content:center;color:#facc15;font-weight:800;font-size:12px}
.center{flex:1;overflow-y:auto;padding:12px 14px 120px}#chat{max-width:700px;margin:auto;display:flex;flex-direction:column;gap:14px}
.a{background:#f2f2f2;padding:14px 16px;border-radius:20px 20px 20px 5px;align-self:flex-start;max-width:88%;line-height:1.6;white-space:pre-wrap;font-size:15px}
.a img{width:100%;border-radius:12px;margin-top:10px;border:1px solid #ddd}
.u{background:#111;color:#fff;padding:12px 16px;border-radius:20px 20px 5px 20px;align-self:flex-end;max-width:80%;font-size:15px}
.wrap{position:fixed;bottom:0;left:0;right:0;background:#fff;padding:14px 12px 18px;border-top:1px solid #f0f0f0}
.box{background:#f2f2f2;border-radius:30px;padding:5px 5px 5px 18px;display:flex;align-items:center;gap:5px;max-width:700px;margin:0 auto;border:1px solid #e9e9e9;overflow:hidden}
.box input{flex:1;border:0;background:transparent;outline:none;font-size:16px;padding:10px 0;min-width:0}
.icon{width:36px;height:36px;background:#fff;border-radius:50%;display:flex;align-items:center;justify-content:center;box-shadow:0 1px 3px rgba(0,0,0,0.1);flex-shrink:0;cursor:pointer;border:1px solid #eee}
.mic-btn svg{width:20px;height:20px;fill:#111}
.mic-btn.rec{background:#ff1a8a;animation:pulse 1s infinite}.mic-btn.rec svg{fill:#fff}
@keyframes pulse{0%{transform:scale(1)}50%{transform:scale(1.1)}100%{transform:scale(1)}}
</style>
</head>
<body>
<div class="head"><div><div style="font-size:14px;opacity:.7">my</div><div class="sanjuu"><b>sanj</b><span>uu</span>💖</div><div class="live">● 0.0ms BRAIN CONNECTED • VOICE 🎤</div></div><div class="coding">coding</div></div>
<div class="center"><div id="chat"><div class="a">Boss, mic pe click karo - Allow ka option ayega! 🎤 Jaise Meta AI me aata hai!</div></div></div>
<div class="wrap"><div class="box"><input id="q" placeholder="Ask your sanjuu..." onkeypress="if(event.key=='Enter')send()" oninput="checkInput()"><div class="icon" id="camBtn" onclick="makeImage()">📷</div><div class="icon mic-btn" id="mic" onclick="startVoice()"><svg viewBox="0 0 24 24"><path d="M12 14a3 3 0 0 0 3-3V5a3 3 0 0 0-6 0v6a3 3 0 0 0 3 3zm5.3-3a5.3 5.3 0 0 1-10.6 0H5a7 7 0 0 0 14 0h-1.7zM11 19v3h2v-3h-2z"/></svg></div><div class="icon" id="sendBtn" onclick="send()" style="display:none;background:#111;color:#fff;">↑</div></div></div>
<script>
let recognition = null;
let mediaRecorder, audioChunks=[], isRecording=false, streamRef=null;
function checkInput(){
  let val=document.getElementById('q').value.trim();
  let mic=document.getElementById('mic');
  let send=document.getElementById('sendBtn');
  if(val.length > 0){ mic.style.display='none'; send.style.display='flex'; }
  else { mic.style.display='flex'; send.style.display='none'; }
}
function startVoice(){
  if(location.protocol!== 'https:' && location.hostname!== 'localhost' && location.hostname!== '127.0.0.1'){
    let c=document.getElementById('chat');
    c.innerHTML+=`<div class='a'>⚠️ Boss ye IP pe hai: ${location.hostname} \\nChrome IP pe mic Allow nahi deta! \\n\\n✅ Solution:\\n1. Laptop pe localhost:5000 pe kholo\\n2. Ya Render ka https://...onrender.com wala link pe kholo - tab Allow / Block ka option ayega! 🙏</div>`;
    c.parentElement.scrollTop=999999;
  }
  if('webkitSpeechRecognition' in window || 'SpeechRecognition' in window){
    let SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    recognition = new SR();
    recognition.lang = 'hi-IN';
    recognition.interimResults = false;
    recognition.onstart = ()=>{
      document.getElementById('mic').classList.add('rec');
      document.getElementById('q').placeholder='Sun rahi hu... bolo Boss 🎤';
    };
    recognition.onend = ()=>{
      document.getElementById('mic').classList.remove('rec');
      document.getElementById('q').placeholder='Ask your sanjuu...';
    };
    recognition.onresult = (e)=>{
      let text = e.results[0][0].transcript;
      document.getElementById('q').value=text;
      checkInput();
      send();
    };
    recognition.onerror = (e)=>{
      document.getElementById('mic').classList.remove('rec');
      if(e.error === 'not-allowed'){
        let c=document.getElementById('chat');
        c.innerHTML+=`<div class='a'>Boss mic Block hai 🙏\\nUpar address bar me 🔒 icon pe click karo > Permissions > Microphone > Allow karo. Fir page reload karo!</div>`;
        c.parentElement.scrollTop=999999;
      } else { startRecording(); }
    };
    try{ recognition.start(); }catch(err){ startRecording(); }
  } else { startRecording(); }
}
async function startRecording(){
  const micBtn=document.getElementById('mic');
  const chat=document.getElementById('chat');
  if(isRecording){ if(mediaRecorder) mediaRecorder.stop(); isRecording=false; micBtn.classList.remove('rec'); return; }
  try{
    const stream=await navigator.mediaDevices.getUserMedia({audio:true});
    streamRef=stream;
    mediaRecorder=new MediaRecorder(stream);
    audioChunks=[];
    mediaRecorder.ondataavailable=e=>audioChunks.push(e.data);
    mediaRecorder.onstop=async()=>{
      let blob=new Blob(audioChunks,{type:'audio/webm'});
      if(blob.size<800) return;
      chat.innerHTML+=`<div class='u'>🎤 Voice...</div>`;
      let l=document.createElement('div'); l.className='a'; l.textContent='Voice sun rahi hu...'; chat.appendChild(l);
      chat.parentElement.scrollTop=999999;
      let fd=new FormData(); fd.append('audio',blob,'voice.webm');
      try{
        let r=await fetch('/voice',{method:'POST',body:fd});
        let j=await r.json();
        if(j.answer.startsWith("__IMAGE__")){
          let parts=j.answer.split("__");
          let url=parts[1]; let prm=parts[2];
          l.innerHTML=`"${j.transcript}"<br><br><b>${prm}</b><br><img src="${url}" />`;
        } else {
          l.textContent=`"${j.transcript}"\\n\\n${j.answer}`;
        }
      }catch(e){ l.textContent="Voice error 🥺"; }
      chat.parentElement.scrollTop=999999;
      if(streamRef) streamRef.getTracks().forEach(t=>t.stop());
    };
    mediaRecorder.start();
    isRecording=true;
    micBtn.classList.add('rec');
  }catch(e){
    let l=document.createElement('div');
    l.className='a';
    l.textContent="Boss mic blocked hai 🙏 Upar 🔒 pe click karke Allow karo. Ya https wale link pe kholo!";
    chat.appendChild(l);
    chat.parentElement.scrollTop=999999;
  }
}
async function makeImage(){
 let p=document.getElementById('q').value.trim() || prompt("Kaisi photo banau Boss?");
 if(!p) return;
 let c=document.getElementById('chat'); c.innerHTML+=`<div class='u'>🎨 ${p}</div>`; document.getElementById('q').value=''; checkInput();
 let l=document.createElement('div'); l.className='a'; l.textContent='🎨 Photo bana rahi hu...'; c.appendChild(l);
 c.parentElement.scrollTop=999999;
 try{
  let r=await fetch('/image',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({prompt:p})});
  let j=await r.json(); l.innerHTML=`<b>${j.prompt}</b><br><img src="${j.url}" />`;
 }catch(e){ l.textContent="Image error 🥺"; }
 c.parentElement.scrollTop=999999;
}
async function send(){
 let i=document.getElementById('q'), t=i.value.trim(); if(!t) return;
 let low=t.toLowerCase();
 if( (low.includes('pic') || low.includes('pix') || low.includes('photo') || low.includes('foto') || low.includes('image') || low.includes('elephant') || low.includes('haathi')) && (low.includes('bej') || low.includes('bhej') || low.includes('dikhao') || low.includes('banao') || low.includes('send') || low.includes('chahiye')) ){
   makeImage(); return;
 }
 let c=document.getElementById('chat'); c.innerHTML+=`<div class='u'>${t}</div>`; i.value=''; checkInput();
 let l=document.createElement('div'); l.className='a'; l.textContent='Thinking....'; c.appendChild(l);
 c.parentElement.scrollTop=999999;
 try{
  let r=await fetch('/ask',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({query:t})});
  let j=await r.json();
  if(j.answer.startsWith("__IMAGE__")){
    let parts=j.answer.split("__");
    let url=parts[1]; let prm=parts[2];
    l.innerHTML=`<b>${prm}</b><br><img src="${url}" />`;
  } else {
    l.textContent=j.answer;
  }
 }catch(e){ l.textContent="Server error"; }
 c.parentElement.scrollTop=999999;
}
</script>
</body>
</html>
"""

@app.route('/')
def home(): return render_template_string(HTML_CODE)

@app.route('/ask', methods=['POST'])
def ask():
    d=request.get_json()
    return jsonify({"answer": ask_sanjoo(d.get('query',''))})

@app.route('/image', methods=['POST'])
def image_route():
    p = request.get_json().get('prompt','cute cat').strip()
    url = f"https://image.pollinations.ai/prompt/{quote(p)}?width=1024&height=1024&nologo=true&enhance=true&model=flux&seed={int(time.time())}"
    return jsonify({"url": url, "prompt": p})

@app.route('/voice', methods=['POST'])
def voice():
    try:
        f=request.files['audio']
        with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as tmp:
            f.save(tmp.name)
            tmp_path=tmp.name
        with open(tmp_path,"rb") as af:
            cur_client = get_groq_client()
            if not cur_client:
                return jsonify({"transcript":"","answer":"Boss API Key set nahi hai"})
            tr=cur_client.audio.transcriptions.create(model="whisper-large-v3", file=af, language="hi")
        os.unlink(tmp_path)
        txt=tr.text.strip() or "Hyy"
        ans=ask_sanjoo(txt)
        return jsonify({"transcript":txt, "answer":ans})
    except Exception as e:
        return jsonify({"transcript":"","answer":f"Voice error {e}"})

if __name__=='__main__':
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
