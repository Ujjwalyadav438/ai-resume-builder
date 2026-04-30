"""
AI Resume Builder — INT428 Project  ★ PREMIUM VERSION ★
Features : Space Splash · Login/Signup · Llama 4 AI · ATS Score · Job Tailor
           Cover Letter · Interview Q&A · Skill Gap · LinkedIn Summary · PDF Export
API      : SambaNova Cloud (Llama-4-Maverick-17B-128E-Instruct) — FREE
"""

import streamlit as st
from openai import OpenAI
import sqlite3, hashlib, re, io
from dotenv import load_dotenv
import os
load_dotenv()  # Load .env file
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable
from reportlab.lib.enums import TA_CENTER, TA_LEFT

# ─────────────────────────────────────────────
st.set_page_config(page_title="AI Resume Builder", page_icon="🌍",
                   layout="wide", initial_sidebar_state="collapsed")

# ─────────────────────────────────────────────
# DATABASE
# ─────────────────────────────────────────────
def init_db():
    c = sqlite3.connect("resume.db")
    c.execute("""CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        full_name TEXT, email TEXT UNIQUE,
        password TEXT, created TEXT)""")
    c.commit(); c.close()
init_db()

def hash_pw(p): return hashlib.sha256(p.encode()).hexdigest()

def register(name, email, pw):
    try:
        c = sqlite3.connect("resume.db")
        c.execute("INSERT INTO users(full_name,email,password,created) VALUES(?,?,?,?)",
                  (name, email.lower(), hash_pw(pw), datetime.now().strftime("%Y-%m-%d %H:%M")))
        c.commit(); c.close(); return True, "Account created!"
    except sqlite3.IntegrityError: return False, "Email already registered."
    except Exception as e: return False, str(e)

def login(email, pw):
    c = sqlite3.connect("resume.db")
    row = c.execute("SELECT full_name,email FROM users WHERE email=? AND password=?",
                    (email.lower(), hash_pw(pw))).fetchone()
    c.close()
    return (True, row[0], row[1]) if row else (False,"","")

def valid_email(e): return bool(re.match(r"^[\w\.-]+@[\w\.-]+\.\w{2,}$", e))

# ─────────────────────────────────────────────
# SESSION
# ─────────────────────────────────────────────
D = {"page":"splash","logged_in":False,"user_name":"","user_email":"",
     "api_key":"","api_ok":False,"temp":0.2,"topp":0.85,
     "resume_done":False,"resume_md":"","chat":[],"full_name":"",
     "job_title":"","email":"","phone":"","location":"","summary":"",
     "experience":"","education":"","skills":"",
     "rfont":"Georgia, serif","rsize":14,"rcolor":"#1a237e",
     "ats_score":"","cover_letter":"","interview_qa":"",
     "skill_gap":"","linkedin_sum":"","tailored_resume":""}
for k,v in D.items():
    if k not in st.session_state: st.session_state[k]=v

# ─────────────────────────────────────────────
# SAMBANOVA (Llama 4)
# ─────────────────────────────────────────────
SYSTEM = """You are ResumeAI, a Professional Career Coach and Resume Expert.
DOMAIN: Career, resumes, cover letters, job search, interview tips, LinkedIn only.
If asked off-topic: "I specialize in career development only. Let me help with your resume!"
Use professional language, strong action verbs, quantify achievements."""

SAMBANOVA_MODEL = "Llama-4-Maverick-17B-128E-Instruct"

def call_gemini(prompt, temp=0.2, topp=0.85, ctx=""):
    """Call SambaNova Cloud API (Llama 4) — drop-in replacement for Gemini."""
    import time
    client = OpenAI(
        api_key=st.session_state.api_key,
        base_url="https://api.sambanova.ai/v1"
    )
    full = f"EXISTING RESUME:\n{ctx}\n\nREQUEST:\n{prompt}" if ctx else prompt
    for attempt in range(4):
        try:
            response = client.chat.completions.create(
                model=SAMBANOVA_MODEL,
                messages=[
                    {"role": "system", "content": SYSTEM},
                    {"role": "user",   "content": full}
                ],
                temperature=temp,
                top_p=topp,
                max_tokens=2048,
            )
            return response.choices[0].message.content
        except Exception as e:
            err = str(e)
            if "429" in err or "quota" in err.lower() or "rate" in err.lower():
                wait = [15, 30, 60, 120][attempt]
                st.warning(f"⏳ API rate limit hit — waiting {wait}s then retrying (attempt {attempt+1}/4)...")
                time.sleep(wait)
            else:
                return f"⚠️ Error: {err}"
    return "⚠️ Rate limit exceeded. Please wait a moment and try again."

def build_resume_prompt(d):
    return f"""Generate a complete ATS-optimized professional resume in clean Markdown.
Name:{d['full_name']} | Title:{d['job_title']} | Email:{d['email']} | Phone:{d['phone']} | Location:{d['location']}
Summary:{d['summary'] or 'Write a compelling 3-sentence professional summary.'}
Experience:\n{d['experience']}
Education:\n{d['education']}
Skills:{d['skills']}
Rules: # for name, ## for sections, ### for job titles. Strong action verbs. Quantify achievements. Output ONLY the Markdown resume."""

# ─────────────────────────────────────────────
# PDF GENERATOR
# ─────────────────────────────────────────────
def generate_pdf(md_text, font_color):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4,
                            rightMargin=2*cm, leftMargin=2*cm,
                            topMargin=2*cm, bottomMargin=2*cm)
    styles = getSampleStyleSheet()
    try:
        r, g, b = int(font_color[1:3],16), int(font_color[3:5],16), int(font_color[5:7],16)
        accent = colors.Color(r/255, g/255, b/255)
    except: accent = colors.HexColor("#1a237e")

    name_style = ParagraphStyle('Name', parent=styles['Title'],
        fontSize=22, textColor=accent, spaceAfter=4, alignment=TA_CENTER)
    section_style = ParagraphStyle('Section', parent=styles['Heading2'],
        fontSize=11, textColor=accent, spaceBefore=12, spaceAfter=4,
        borderPadding=(0,0,2,0))
    job_style = ParagraphStyle('Job', parent=styles['Normal'],
        fontSize=10, fontName='Helvetica-Bold', spaceBefore=6)
    body_style = ParagraphStyle('Body', parent=styles['Normal'],
        fontSize=9.5, spaceAfter=2, leading=14)
    bullet_style = ParagraphStyle('Bullet', parent=styles['Normal'],
        fontSize=9.5, spaceAfter=2, leading=14, leftIndent=15,
        bulletIndent=5)

    story = []
    lines = md_text.split('\n')
    for line in lines:
        line = line.strip()
        if not line:
            story.append(Spacer(1, 4))
        elif line.startswith('# '):
            story.append(Paragraph(line[2:], name_style))
            story.append(HRFlowable(width="100%", thickness=2, color=accent, spaceAfter=6))
        elif line.startswith('## '):
            story.append(Spacer(1, 6))
            story.append(Paragraph(line[3:].upper(), section_style))
            story.append(HRFlowable(width="100%", thickness=0.5,
                         color=colors.lightgrey, spaceAfter=4))
        elif line.startswith('### '):
            story.append(Paragraph(line[4:], job_style))
        elif line.startswith('- '):
            story.append(Paragraph(f"• {line[2:]}", bullet_style))
        elif line.startswith('**') and line.endswith('**'):
            story.append(Paragraph(f"<b>{line[2:-2]}</b>", body_style))
        else:
            story.append(Paragraph(line, body_style))

    doc.build(story)
    buffer.seek(0)
    return buffer.read()

# ─────────────────────────────────────────────
# RESUME HTML RENDERER
# ─────────────────────────────────────────────
def render_html(md, font, size, color):
    html = ""
    for line in md.split("\n"):
        if line.startswith("# "):
            html += f'<h1 style="font-size:{size+8}px;border-bottom:3px solid {color};padding-bottom:8px;color:#111;font-family:{font}">{line[2:]}</h1>'
        elif line.startswith("## "):
            html += f'<h2 style="font-size:{size+1}px;text-transform:uppercase;letter-spacing:2px;color:{color};border-bottom:1px solid #ddd;margin-top:18px;padding-bottom:4px">{line[3:]}</h2>'
        elif line.startswith("### "):
            html += f'<h3 style="font-size:{size+1}px;font-weight:700;margin-top:12px;color:#222">{line[4:]}</h3>'
        elif line.startswith("- "):
            html += f'<li style="margin-left:20px;margin-bottom:3px;font-size:{size}px">{line[2:]}</li>'
        elif line.strip()=="": html += '<div style="height:5px"></div>'
        else: html += f'<p style="margin:2px 0;font-size:{size}px">{line}</p>'
    return html

# ─────────────────────────────────────────────
# GLOBAL CSS
# ─────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=Orbitron:wght@400;600;700;900&family=Rajdhani:wght@400;500;600;700&display=swap');
*{box-sizing:border-box;}
html,body,[class*="css"]{font-family:'Inter',sans-serif;}
.stApp{background:#020510;}
#MainMenu,footer,header{visibility:hidden;}
.stDeployButton{display:none;}
div[data-testid="stSidebar"]{display:none;}
.stTextInput>div>div>input,
.stTextArea>div>div>textarea{
    background:rgba(255,255,255,0.04)!important;
    border:1px solid rgba(100,160,255,0.2)!important;
    border-radius:8px!important;color:#d0e8ff!important;
    font-family:'Inter',sans-serif!important;}
.stTextInput>div>div>input:focus,
.stTextArea>div>div>textarea:focus{
    border-color:rgba(100,160,255,0.6)!important;
    box-shadow:0 0 0 2px rgba(100,160,255,0.12)!important;}
.stButton>button{font-family:'Inter',sans-serif!important;font-weight:600!important;
    border-radius:10px!important;transition:all 0.2s!important;}
.stButton>button:hover{transform:translateY(-2px)!important;}
.stTabs [data-baseweb="tab-list"]{border-bottom:1px solid rgba(100,160,255,0.12);}
.stTabs [data-baseweb="tab"]{color:#334a60!important;font-size:.85rem!important;}
.stTabs [aria-selected="true"]{color:#60b4ff!important;border-bottom:2px solid #60b4ff!important;}
.sh{color:#60b4ff;font-weight:700;font-size:.94rem;
    border-bottom:1px solid rgba(96,180,255,0.18);padding-bottom:6px;margin-bottom:14px;}
.icard{background:rgba(96,180,255,0.05);border:1px solid rgba(96,180,255,0.18);
    border-radius:10px;padding:.9rem 1.1rem;margin-bottom:.8rem;font-size:.86rem;color:#6a9abf;}
.cu{background:rgba(0,70,180,0.28);border:1px solid rgba(96,180,255,0.18);
    border-radius:16px 16px 4px 16px;padding:.65rem .95rem;
    margin:.35rem 0 .35rem 2.5rem;color:#a8d4ff;font-size:.87rem;}
.cb{background:rgba(255,255,255,0.04);border:1px solid rgba(255,255,255,0.07);
    border-radius:16px 16px 16px 4px;padding:.65rem .95rem;
    margin:.35rem 2.5rem .35rem 0;color:#c8e4ff;font-size:.87rem;}
.scard{background:rgba(96,180,255,0.04);border:1px solid rgba(96,180,255,0.13);
    border-radius:12px;padding:1.1rem 1.3rem;margin-bottom:.9rem;}
.snum{display:inline-block;width:26px;height:26px;border-radius:50%;
    background:linear-gradient(135deg,#0d47a1,#1976d2);color:white;
    font-weight:700;font-size:.82rem;text-align:center;line-height:26px;margin-right:9px;}
.score-big{font-family:'Orbitron',monospace;font-size:3.5rem;font-weight:900;text-align:center;line-height:1;}
.feature-result{background:rgba(255,255,255,0.03);border:1px solid rgba(96,180,255,0.15);
    border-radius:12px;padding:1.2rem 1.4rem;white-space:pre-wrap;
    color:#c0d8f0;font-size:.86rem;line-height:1.7;max-height:400px;overflow-y:auto;}
</style>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════
# PAGE 1 — AI RESUME BUILDER SPLASH
# ══════════════════════════════════════════════
def show_splash():
    st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700;900&family=Rajdhani:wght@500;600;700&display=swap');
@keyframes fadeUp{from{opacity:0;transform:translateY(40px)}to{opacity:1;transform:translateY(0)}}
@keyframes float1{0%,100%{transform:translateY(0) rotate(-2deg)}50%{transform:translateY(-18px) rotate(2deg)}}
@keyframes float2{0%,100%{transform:translateY(0)}50%{transform:translateY(-12px)}}
@keyframes float3{0%,100%{transform:translateY(0) rotate(2deg)}50%{transform:translateY(-20px) rotate(-2deg)}}
@keyframes scanline{0%{top:-60px}100%{top:110%}}
@keyframes pulse-ring{0%{transform:scale(0.9);opacity:.8}100%{transform:scale(1.8);opacity:0}}
@keyframes particle-rise{0%{transform:translateY(0) translateX(0);opacity:.9}100%{transform:translateY(-130px) translateX(var(--dx));opacity:0}}
@keyframes ai-dot{0%,100%{transform:scale(1);opacity:.5}50%{transform:scale(2);opacity:1}}
@keyframes shimmer{0%{background-position:-200% center}100%{background-position:200% center}}
@keyframes glow-border{0%,100%{box-shadow:0 0 10px rgba(64,200,80,.15)}50%{box-shadow:0 0 30px rgba(64,200,80,.45)}}
.splash-bg{min-height:100vh;
    background:linear-gradient(135deg,#030a03 0%,#050f0a 50%,#030808 100%);
    background-image:radial-gradient(ellipse at 15% 25%,rgba(20,180,80,.07) 0%,transparent 55%),
    radial-gradient(ellipse at 85% 75%,rgba(20,120,200,.06) 0%,transparent 55%);
    display:flex;flex-direction:column;align-items:center;justify-content:center;
    overflow:hidden;padding:1.5rem 1rem;position:relative;}
.grid-bg{position:fixed;inset:0;pointer-events:none;z-index:0;
    background-image:linear-gradient(rgba(20,200,80,.03) 1px,transparent 1px),
    linear-gradient(90deg,rgba(20,200,80,.03) 1px,transparent 1px);background-size:50px 50px;}
.pt{position:fixed;width:3px;height:3px;border-radius:50%;background:#40c860;pointer-events:none;z-index:0;}
.p1{left:10%;top:80%;--dx:20px;animation:particle-rise 4s ease-out infinite;}
.p2{left:25%;top:90%;--dx:-15px;animation:particle-rise 5s ease-out infinite 1s;}
.p3{left:50%;top:85%;--dx:30px;animation:particle-rise 3.5s ease-out infinite .5s;}
.p4{left:70%;top:88%;--dx:-25px;animation:particle-rise 4.5s ease-out infinite 1.5s;}
.p5{left:85%;top:82%;--dx:10px;animation:particle-rise 5.5s ease-out infinite 2s;}
.p6{left:40%;top:92%;--dx:-20px;background:#40b0ff;animation:particle-rise 4s ease-out infinite 2.5s;}
.p7{left:60%;top:78%;--dx:15px;background:#ffb040;animation:particle-rise 6s ease-out infinite .8s;}
.splash-wrap{position:relative;z-index:2;display:flex;align-items:center;gap:3.5rem;
    max-width:1050px;width:100%;animation:fadeUp .8s ease both;}
.rdoc-scene{flex-shrink:0;position:relative;width:280px;height:390px;}
.rdoc{width:230px;height:305px;background:linear-gradient(145deg,#0a1a0a,#081208);
    border:1px solid rgba(64,200,80,.28);border-radius:8px;
    position:absolute;top:40px;left:25px;overflow:hidden;
    box-shadow:0 0 0 1px rgba(64,200,80,.1),0 20px 60px rgba(0,0,0,.8),0 0 60px rgba(64,200,80,.06);
    animation:float1 5s ease-in-out infinite,glow-border 4s ease-in-out infinite;}
.rbeam{position:absolute;left:0;right:0;height:2px;
    background:linear-gradient(90deg,transparent,#40c860,rgba(64,200,80,.3),transparent);
    box-shadow:0 0 8px rgba(64,200,80,.6);animation:scanline 2.5s linear infinite;z-index:5;}
.rscan{position:absolute;left:0;right:0;height:50px;
    background:linear-gradient(180deg,transparent,rgba(64,200,80,.06),transparent);
    animation:scanline 3s linear infinite;z-index:4;}
.rh{padding:14px 13px 10px;border-bottom:1px solid rgba(64,200,80,.18);margin-bottom:8px;}
.rn{height:9px;background:linear-gradient(90deg,#40c860,#40c860 65%,transparent);
    border-radius:5px;margin-bottom:5px;width:68%;box-shadow:0 0 8px rgba(64,200,80,.35);}
.rr{height:5px;background:rgba(64,200,80,.25);border-radius:3px;width:48%;margin-bottom:3px;}
.rc{height:4px;background:rgba(64,200,80,.12);border-radius:3px;width:78%;}
.rs{padding:0 13px;margin-bottom:8px;}
.rst{height:6px;border-radius:3px;margin-bottom:7px;}
.st-g{width:38%;background:linear-gradient(90deg,#40c860,transparent);}
.st-b{width:38%;background:linear-gradient(90deg,#40b0ff,transparent);}
.st-y{width:38%;background:linear-gradient(90deg,#ffb040,transparent);}
.rl{height:4px;background:rgba(255,255,255,.07);border-radius:2px;margin-bottom:4px;}
.w90{width:90%}.w80{width:80%}.w65{width:65%}.w75{width:75%}.w55{width:55%}.w70{width:70%}
.sbadge{position:absolute;top:-14px;right:-14px;width:54px;height:54px;border-radius:50%;
    background:linear-gradient(135deg,#071507,#0d2e0d);border:2px solid #40c860;
    display:flex;flex-direction:column;align-items:center;justify-content:center;
    box-shadow:0 0 20px rgba(64,200,80,.5);z-index:20;animation:float2 4s ease-in-out infinite;}
.sbn{color:#40c860;font-family:'Orbitron',monospace;font-weight:900;font-size:.82rem;line-height:1.1;}
.sbl{color:rgba(64,200,80,.55);font-size:.42rem;letter-spacing:1px;text-transform:uppercase;}
.mc{position:absolute;background:rgba(4,14,6,.92);border:1px solid rgba(64,200,80,.22);
    border-radius:8px;padding:7px 11px;backdrop-filter:blur(10px);
    box-shadow:0 4px 20px rgba(0,0,0,.6);white-space:nowrap;z-index:15;}
.mc1{top:-5px;right:-10px;animation:float2 4.5s ease-in-out infinite;}
.mc2{bottom:15px;left:-15px;animation:float3 5.2s ease-in-out infinite;}
.mc3{top:48%;right:-25px;transform:translateY(-50%);animation:float1 5.8s ease-in-out infinite 1s;}
.mci{font-size:.85rem;margin-right:3px;}
.mct{color:rgba(140,210,140,.8);font-family:'Rajdhani',sans-serif;font-size:.7rem;font-weight:600;letter-spacing:.5px;}
.mcv{color:#40c860;font-family:'Orbitron',monospace;font-size:.72rem;font-weight:700;}
.aic{position:absolute;bottom:-5px;left:50%;transform:translateX(-50%);width:72px;height:72px;}
.air{position:absolute;inset:0;border-radius:50%;border:1px solid rgba(64,200,80,.25);
    animation:pulse-ring 2s ease-out infinite;}
.air:nth-child(2){animation-delay:.7s;}
.air:nth-child(3){animation-delay:1.4s;}
.aicore{position:absolute;inset:20px;border-radius:50%;
    background:radial-gradient(circle,rgba(64,200,80,.25),rgba(64,200,80,.05));
    border:1px solid rgba(64,200,80,.4);display:flex;align-items:center;justify-content:center;font-size:1.1rem;}
.stxt{flex:1;max-width:540px;}
.tagline{display:inline-block;background:rgba(64,200,80,.07);border:1px solid rgba(64,200,80,.22);
    border-radius:20px;padding:4px 15px;color:rgba(64,200,80,.65);
    font-family:'Rajdhani',sans-serif;font-size:.76rem;letter-spacing:3px;
    text-transform:uppercase;margin-bottom:.9rem;animation:fadeUp .7s ease both;}
.mtitle{font-family:'Orbitron',monospace;font-weight:900;
    font-size:clamp(1.7rem,4vw,2.7rem);line-height:1.2;margin-bottom:.4rem;
    background:linear-gradient(135deg,#fff 0%,#a0ffb0 35%,#40ffb4 65%,#40c8ff 100%);
    background-size:200% auto;-webkit-background-clip:text;-webkit-text-fill-color:transparent;
    animation:fadeUp .85s ease both,shimmer 4s linear infinite;}
.msub{font-family:'Rajdhani',sans-serif;font-size:.95rem;color:rgba(64,200,80,.45);
    letter-spacing:3px;text-transform:uppercase;margin-bottom:.7rem;animation:fadeUp .95s ease both;}
.mdesc{color:rgba(140,190,140,.45);font-size:.86rem;line-height:1.8;
    margin-bottom:1.2rem;animation:fadeUp 1.05s ease both;max-width:450px;}
.flist{display:flex;flex-direction:column;gap:7px;margin-bottom:1.2rem;animation:fadeUp 1.1s ease both;}
.fi{display:flex;align-items:center;gap:9px;padding:7px 13px;
    background:rgba(64,200,80,.03);border:1px solid rgba(64,200,80,.09);border-radius:8px;}
.fdot{width:5px;height:5px;border-radius:50%;background:#40c860;
    box-shadow:0 0 7px #40c860;flex-shrink:0;animation:ai-dot 2s infinite;}
.flbl{color:rgba(160,220,160,.65);font-size:.8rem;font-family:'Rajdhani',sans-serif;font-weight:600;letter-spacing:.4px;}
.fbdg{margin-left:auto;background:rgba(64,200,80,.08);border:1px solid rgba(64,200,80,.18);
    border-radius:12px;padding:2px 9px;color:#40c860;font-size:.67rem;font-family:'Orbitron',monospace;}
.srow{display:flex;gap:10px;margin-bottom:1.2rem;animation:fadeUp 1.15s ease both;}
.sb2{flex:1;background:rgba(64,200,80,.03);border:1px solid rgba(64,200,80,.1);
    border-radius:10px;padding:9px 10px;text-align:center;}
.sbn2{font-family:'Orbitron',monospace;font-size:1rem;font-weight:700;color:#40c860;display:block;margin-bottom:1px;}
.sbl2{font-size:.62rem;color:rgba(80,130,80,.45);letter-spacing:1px;text-transform:uppercase;}
.hud{display:flex;gap:12px;flex-wrap:wrap;animation:fadeUp 1.2s ease both;}
.hi{display:flex;align-items:center;gap:5px;font-family:'Rajdhani',sans-serif;
    font-size:.7rem;color:rgba(70,120,70,.55);letter-spacing:.8px;text-transform:uppercase;}
.hg{width:5px;height:5px;border-radius:50%;background:#40c860;box-shadow:0 0 6px #40c860;animation:ai-dot 1.5s infinite;}
.hb{width:5px;height:5px;border-radius:50%;background:#40b0ff;box-shadow:0 0 6px #40b0ff;animation:ai-dot 2s infinite .5s;}
.hy{width:5px;height:5px;border-radius:50%;background:#ffb040;box-shadow:0 0 6px #ffb040;animation:ai-dot 2.5s infinite 1s;}
.sfoot2{text-align:center;color:rgba(40,80,40,.4);font-size:.66rem;margin-top:1rem;letter-spacing:1px;position:relative;z-index:2;}
</style>
<div class="grid-bg"></div>
<div class="pt p1"></div><div class="pt p2"></div><div class="pt p3"></div>
<div class="pt p4"></div><div class="pt p5"></div><div class="pt p6"></div><div class="pt p7"></div>
<div class="splash-bg">
<div class="splash-wrap">
  <div class="rdoc-scene">
    <div class="sbadge"><div class="sbn">98</div><div class="sbl">ATS</div></div>
    <div class="rdoc">
      <div class="rbeam"></div><div class="rscan"></div>
      <div class="rh"><div class="rn"></div><div class="rr"></div><div class="rc"></div></div>
      <div class="rs"><div class="rst st-g"></div><div class="rl w90"></div><div class="rl w75"></div><div class="rl w65"></div></div>
      <div class="rs"><div class="rst st-b"></div><div class="rl w80"></div><div class="rl w70"></div><div class="rl w90"></div><div class="rl w55"></div></div>
      <div class="rs"><div class="rst st-y"></div><div class="rl w75"></div><div class="rl w65"></div></div>
    </div>
    <div class="mc mc1"><span class="mci">🤖</span><span class="mct">GEMINI AI</span><div class="mcv">ACTIVE</div></div>
    <div class="mc mc2"><span class="mci">📊</span><span class="mct">ATS SCORE</span><div class="mcv">98/100</div></div>
    <div class="mc mc3"><span class="mci">✅</span><span class="mct">OPTIMIZED</span></div>
    <div class="aic"><div class="air"></div><div class="air"></div><div class="air"></div><div class="aicore">🧠</div></div>
  </div>
  <div class="stxt">
    <div class="tagline">✦ INT428 · Generative AI · 2026 ✦</div>
    <div class="mtitle">AI RESUME<br>BUILDER</div>
    <div class="msub">★ Career Intelligence Platform ★</div>
    <div class="mdesc">Build ATS-optimized resumes in seconds. Score, tailor, generate cover letters, prep for interviews — powered by Gemini Flash Lite.</div>
    <div class="flist">
      <div class="fi"><div class="fdot"></div><div class="flbl">AI Resume Generation</div><div class="fbdg">LLAMA 4</div></div>
      <div class="fi"><div class="fdot" style="background:#40b0ff;box-shadow:0 0 7px #40b0ff"></div><div class="flbl">ATS Score Analyzer</div><div class="fbdg" style="color:#40b0ff;border-color:rgba(64,176,255,.2)">100/100</div></div>
      <div class="fi"><div class="fdot" style="background:#ffb040;box-shadow:0 0 7px #ffb040"></div><div class="flbl">Job Description Tailoring</div><div class="fbdg" style="color:#ffb040;border-color:rgba(255,176,64,.2)">SMART</div></div>
      <div class="fi"><div class="fdot" style="background:#c040ff;box-shadow:0 0 7px #c040ff"></div><div class="flbl">PDF Export + Cover Letter</div><div class="fbdg" style="color:#c040ff;border-color:rgba(192,64,255,.2)">FREE</div></div>
      <div class="fi"><div class="fdot"></div><div class="flbl">Interview Prep + Skill Gap</div><div class="fbdg">NEW</div></div>
    </div>
    <div class="srow">
      <div class="sb2"><span class="sbn2">4K+</span><span class="sbl2">Free/Day</span></div>
      <div class="sb2"><span class="sbn2">8</span><span class="sbl2">Features</span></div>
      <div class="sb2"><span class="sbn2">PDF</span><span class="sbl2">Export</span></div>
      <div class="sb2"><span class="sbn2">FREE</span><span class="sbl2">API</span></div>
    </div>
    <div class="hud">
      <div class="hi"><div class="hg"></div>LLAMA 4 MAVERICK ONLINE</div>
      <div class="hi"><div class="hb"></div>ATS ENGINE ACTIVE</div>
      <div class="hi"><div class="hy"></div>PDF READY</div>
      <div class="hi"><div class="hg"></div>DOMAIN LOCKED</div>
    </div>
  </div>
</div>
</div>
""", unsafe_allow_html=True)
    _, c, _ = st.columns([1,1,1])
    with c:
        if st.button("🚀  Enter Dashboard", use_container_width=True):
            st.session_state.page="auth"; st.rerun()
    st.markdown('<div class="sfoot2">Powered by SambaNova Cloud · Llama-4-Maverick &nbsp;•&nbsp; Python + Streamlit &nbsp;•&nbsp; INT428 © 2026</div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════
# PAGE 2 — AUTH
# ══════════════════════════════════════════════
def show_auth():
    if st.button("← Back to Home"):
        st.session_state.page="splash"; st.rerun()
    _, center, _ = st.columns([1,1.2,1])
    with center:
        st.markdown("""
<div style="text-align:center;font-size:2.2rem;margin-bottom:.3rem">📄</div>
<div style="font-family:'Orbitron',monospace;font-size:1.3rem;font-weight:700;
background:linear-gradient(135deg,#4090ff,#80c4ff);
-webkit-background-clip:text;-webkit-text-fill-color:transparent;
text-align:center;margin-bottom:.2rem">AI RESUME BUILDER</div>
<div style="text-align:center;color:#102030;font-size:.8rem;margin-bottom:1.4rem">Sign in or create your account</div>
""", unsafe_allow_html=True)
        # API Key - shown above both tabs
        st.markdown("""
<div style="background:rgba(64,255,176,.05);border:1px solid rgba(64,255,176,.25);
border-radius:10px;padding:1rem 1.1rem;margin-bottom:1rem">
<div style="color:#40ffb0;font-weight:700;font-size:.85rem;margin-bottom:.5rem">
🔑 SambaNova Cloud API Key (FREE)</div>
<div style="color:#1a4a3a;font-size:.75rem;line-height:1.6">
Get free key → <strong style="color:#40c090">cloud.sambanova.ai</strong><br>
Sign up → Go to API Keys → Create & Copy your key
</div></div>""", unsafe_allow_html=True)
        # Pre-fill from .env if available
        env_key_login = os.getenv("SAMBANOVA_API_KEY", "")
        api_key_input = st.text_input("Paste SambaNova API Key here", key="auth_api",
                                       type="password", placeholder="sn-...",
                                       value=env_key_login)
        if env_key_login:
            st.markdown('<div style="color:#40c860;font-size:.78rem;margin-top:-10px">✅ Loaded from .env file</div>',unsafe_allow_html=True)
        st.markdown('<hr style="border-color:rgba(96,180,255,0.1);margin:.6rem 0">',unsafe_allow_html=True)

        tl, ts = st.tabs(["🔑  Login","✨  Create Account"])
        with tl:
            st.markdown("<br>",unsafe_allow_html=True)
            le = st.text_input("Email", key="le", placeholder="you@example.com")
            lp = st.text_input("Password", key="lp", type="password", placeholder="Your password")
            st.markdown("<br>",unsafe_allow_html=True)
            if st.button("🚀 Login & Start Building", key="lbtn", use_container_width=True):
                if not le or not lp:
                    st.error("Please fill email and password.")
                elif not api_key_input:
                    st.error("Please enter your SambaNova API key above.")
                else:
                    ok,name,email = login(le,lp)
                    if ok:
                        with st.spinner("Verifying API key..."):
                            try:
                                client = OpenAI(api_key=api_key_input, base_url="https://api.sambanova.ai/v1")
                                client.chat.completions.create(
                                    model=SAMBANOVA_MODEL,
                                    messages=[{"role":"user","content":"hi"}],
                                    max_tokens=5)
                                st.session_state.update({
                                    "logged_in":True,"user_name":name,"user_email":email,
                                    "full_name":name,"api_key":api_key_input,
                                    "api_ok":True,"temp":0.2,"topp":0.85,"page":"main"})
                                st.success(f"✅ Welcome, {name}!"); st.rerun()
                            except Exception as e:
                                st.error(f"❌ API Error: {str(e)}")
                    else: st.error("❌ Invalid email or password.")
        with ts:
            st.markdown("<br>",unsafe_allow_html=True)
            rn=st.text_input("Full Name",key="rn",placeholder="John Doe")
            re_=st.text_input("Email",key="re",placeholder="you@example.com")
            rp=st.text_input("Password",key="rp",type="password",placeholder="Min 6 chars")
            rp2=st.text_input("Confirm Password",key="rp2",type="password",placeholder="Repeat")
            st.markdown("<br>",unsafe_allow_html=True)
            if st.button("🚀 Create Account & Start",key="sbtn",use_container_width=True):
                if not all([rn,re_,rp,rp2]): st.error("Fill all fields.")
                elif not valid_email(re_): st.error("Enter a valid email.")
                elif len(rp)<6: st.error("Password min 6 characters.")
                elif rp!=rp2: st.error("Passwords don't match.")
                elif not api_key_input: st.error("Please enter your SambaNova API key above.")
                else:
                    ok,msg=register(rn,re_,rp)
                    if ok:
                        with st.spinner("Verifying API key..."):
                            try:
                                client = OpenAI(api_key=api_key_input, base_url="https://api.sambanova.ai/v1")
                                client.chat.completions.create(
                                    model=SAMBANOVA_MODEL,
                                    messages=[{"role":"user","content":"hi"}],
                                    max_tokens=5)
                                st.session_state.update({
                                    "logged_in":True,"user_name":rn,"user_email":re_,
                                    "full_name":rn,"api_key":api_key_input,
                                    "api_ok":True,"temp":0.2,"topp":0.85,"page":"main"})
                                st.success(f"✅ Account created! Welcome, {rn}!"); st.rerun()
                            except Exception as e:
                                st.error(f"❌ API Error: {str(e)}")
                    else: st.error(f"❌ {msg}")
        st.markdown('<div style="text-align:center;color:#081018;font-size:.68rem;margin-top:1rem">🔒 SHA-256 encrypted &nbsp;•&nbsp; INT428 © 2026</div>',unsafe_allow_html=True)

# ══════════════════════════════════════════════
# PAGE 3 — API SETUP
# ══════════════════════════════════════════════
def show_api_setup():
    st.markdown("""<div style="font-family:'Orbitron',monospace;font-size:1.5rem;font-weight:700;
background:linear-gradient(135deg,#4090ff,#40ffb0);
-webkit-background-clip:text;-webkit-text-fill-color:transparent;margin-bottom:.3rem">
🔑 API Configuration</div>""",unsafe_allow_html=True)
    st.markdown(f'<div style="color:#1a3a50;margin-bottom:1.4rem">Welcome, <strong style="color:#60b4ff">{st.session_state.user_name}</strong>! Set up your free SambaNova Cloud API key.</div>',unsafe_allow_html=True)
    c1,c2=st.columns([1.2,1],gap="large")
    with c1:
        st.markdown('<div class="sh">🚀 Get Your FREE SambaNova API Key</div>',unsafe_allow_html=True)
        for num,title,desc in [
            ("1","Open SambaNova Cloud","Go to: cloud.sambanova.ai"),
            ("2","Sign Up / Log In","Create a free account — no credit card needed"),
            ("3","Go to API Keys","Click 'API Keys' in the dashboard → Create key"),
            ("4","Paste Below","Copy your key and paste it here"),]:
            st.markdown(f'<div class="scard"><span class="snum">{num}</span><strong style="color:#90b8d8">{title}</strong><br><span style="color:#1a3a50;font-size:.82rem;margin-left:35px">{desc}</span></div>',unsafe_allow_html=True)
        st.markdown("""<div style="background:rgba(64,255,176,.05);border:1px solid rgba(64,255,176,.15);
border-radius:10px;padding:.9rem 1.1rem;font-size:.82rem;color:#1a4a3a">
✅ <strong style="color:#40ffb0">Free tier available</strong><br>
✅ No credit card required<br>✅ Llama-4-Maverick-17B model</div>""",unsafe_allow_html=True)
    with c2:
        st.markdown('<div class="sh">🔐 Enter API Key</div>',unsafe_allow_html=True)
        # Pre-fill from .env if available
        env_key = os.getenv("SAMBANOVA_API_KEY", "")
        api_in=st.text_input("SambaNova Cloud API Key",type="password",
                             placeholder="sn-...",
                             value=env_key,
                             help="Auto-loaded from .env file if SAMBANOVA_API_KEY is set")
        if env_key:
            st.markdown('<div style="color:#40c860;font-size:.78rem;margin-top:-10px">✅ API key loaded from .env file</div>',unsafe_allow_html=True)
        st.markdown("---")
        st.markdown('<div class="sh">⚙️ Model Settings</div>',unsafe_allow_html=True)
        temp=st.slider("🌡️ Temperature",0.0,1.0,0.2,0.05)
        topp=st.slider("🎯 Top-p",0.1,1.0,0.85,0.05)
        st.markdown(f"""<div style="background:rgba(64,144,255,.06);border:1px solid rgba(64,144,255,.14);
border-radius:8px;padding:9px 13px;font-size:.8rem;color:#1a3050;margin-bottom:.9rem">
🌡️ Temp <strong style="color:#60b4ff">{temp}</strong> — {"✅ Precise & professional" if temp<=0.4 else "⚠️"}<br>
🎯 Top-p <strong style="color:#60b4ff">{topp}</strong> — Top {int(topp*100)}% tokens</div>""",unsafe_allow_html=True)
        if st.button("✅  Connect & Continue →",use_container_width=True):
            if not api_in: st.error("Please enter your API key.")
            else:
                with st.spinner("Verifying..."):
                    try:
                        client = OpenAI(api_key=api_in, base_url="https://api.sambanova.ai/v1")
                        client.chat.completions.create(
                            model=SAMBANOVA_MODEL,
                            messages=[{"role":"user","content":"hi"}],
                            max_tokens=5)
                        st.session_state.update({"api_key":api_in,"api_ok":True,
                            "temp":temp,"topp":topp,"page":"main"})
                        st.success("✅ Connected!"); st.rerun()
                    except Exception as e: st.error(f"❌ {str(e)}")
    st.markdown("---")
    if st.button("← Logout"):
        for k in list(st.session_state.keys()): del st.session_state[k]
        st.rerun()

# ══════════════════════════════════════════════
# PAGE 4 — MAIN APP (ALL FEATURES)
# ══════════════════════════════════════════════
def show_main():
    temp=st.session_state.get("temp",0.2)
    topp=st.session_state.get("topp",0.85)

    # NAV BAR
    n1,n2,n3,n4=st.columns([3,1,1,1])
    with n1:
        st.markdown("""<div style="padding:5px 0">
<span style="font-family:'Orbitron',monospace;font-size:1.05rem;font-weight:700;
background:linear-gradient(135deg,#4090ff,#40ffb0);
-webkit-background-clip:text;-webkit-text-fill-color:transparent">
📄 AI RESUME BUILDER</span>
<span style="color:#0f2030;font-size:.76rem;margin-left:10px">INT428 · Llama 4 AI · Premium</span>
</div>""",unsafe_allow_html=True)
    with n2:
        st.markdown(f'<div style="text-align:center;padding-top:7px"><span style="background:rgba(64,144,255,.1);border:1px solid rgba(64,144,255,.2);border-radius:20px;padding:4px 12px;color:#4090ff;font-size:.76rem">👤 {st.session_state.user_name.split()[0]}</span></div>',unsafe_allow_html=True)
    with n3:
        if st.button("⚙️ API"): st.session_state.page="api_setup"; st.rerun()
    with n4:
        if st.button("🚪 Logout"):
            for k in list(st.session_state.keys()): del st.session_state[k]; st.rerun()

    st.markdown('<hr style="border-color:rgba(64,144,255,.1);margin:5px 0 16px">',unsafe_allow_html=True)

    # ALL TABS
    tab1,tab2,tab3,tab4,tab5,tab6,tab7,tab8 = st.tabs([
        "✍️ Build","💬 Chat","📊 ATS Score",
        "🎯 Job Tailor","📝 Cover Letter",
        "❓ Interview Prep","🔍 Skill Gap","💼 LinkedIn"])

    # ════ TAB 1 — BUILD RESUME ════
    with tab1:
        cl,cr=st.columns([1,1],gap="large")
        with cl:
            st.markdown('<div class="sh">👤 Personal Information</div>',unsafe_allow_html=True)
            a,b=st.columns(2)
            with a:
                st.session_state.full_name=st.text_input("Full Name *",value=st.session_state.full_name,placeholder="John Doe")
                st.session_state.email=st.text_input("Email *",value=st.session_state.email,placeholder="john@email.com")
                st.session_state.location=st.text_input("Location",value=st.session_state.location,placeholder="New Delhi, India")
            with b:
                st.session_state.job_title=st.text_input("Target Job Title *",value=st.session_state.job_title,placeholder="Software Engineer")
                st.session_state.phone=st.text_input("Phone",value=st.session_state.phone,placeholder="+91 98765 43210")

            st.markdown('<div class="sh" style="margin-top:.9rem">💼 Professional Details</div>',unsafe_allow_html=True)
            st.session_state.summary=st.text_area("Summary (AI writes if blank)",value=st.session_state.summary,height=60)
            st.session_state.experience=st.text_area("Work Experience *",value=st.session_state.experience,height=120,
                placeholder="Software Engineer at TCS (2021–Now)\n- Built REST APIs\n- Reduced load time by 40%")
            st.session_state.education=st.text_area("Education *",value=st.session_state.education,height=60,
                placeholder="B.Tech CSE — GGSIPU (2018–2022)")
            st.session_state.skills=st.text_area("Skills *",value=st.session_state.skills,height=60,
                placeholder="Python, React, SQL, AWS, Docker, Git")

            st.markdown('<div class="sh" style="margin-top:.9rem">🎨 Resume Style</div>',unsafe_allow_html=True)
            FONTS={"Georgia (Classic)":"Georgia, serif","Times New Roman (Formal)":"'Times New Roman', serif",
                   "Garamond (Elegant)":"Garamond, serif","Arial (Modern)":"Arial, sans-serif",
                   "Helvetica (Clean)":"Helvetica, Arial, sans-serif","Trebuchet (Friendly)":"'Trebuchet MS', sans-serif"}
            COLORS={"🔵 Navy Blue":"#1a237e","🔴 Deep Red":"#c0392b","🟢 Forest Green":"#1b5e20",
                    "🟣 Royal Purple":"#4a148c","⚫ Charcoal":"#263238","🟠 Burnt Orange":"#e65100",
                    "🩵 Steel Blue":"#1565c0","🌸 Maroon":"#880e4f"}
            s1,s2,s3=st.columns(3)
            with s1:
                fl=st.selectbox("✏️ Font",list(FONTS.keys()),index=0)
                st.session_state.rfont=FONTS[fl]
            with s2:
                st.session_state.rsize=st.slider("🔠 Size",11,18,st.session_state.rsize)
            with s3:
                cl2=st.selectbox("🎨 Color",list(COLORS.keys()),index=0)
                st.session_state.rcolor=COLORS[cl2]

            st.markdown(f"""<div style="display:flex;align-items:center;gap:10px;padding:9px 13px;
background:rgba(255,255,255,.02);border:1px solid rgba(255,255,255,.05);border-radius:8px;margin-top:6px">
<div style="width:26px;height:26px;border-radius:6px;background:{st.session_state.rcolor};flex-shrink:0"></div>
<div style="font-size:.78rem;color:#1a3040">
<strong style="color:#4a8aaf">{fl.split('(')[0].strip()}</strong> · <strong style="color:#4a8aaf">{st.session_state.rsize}px</strong> · <strong style="color:{st.session_state.rcolor}">{cl2.split(' ',1)[1]}</strong>
</div></div>""",unsafe_allow_html=True)

            st.markdown("<br>",unsafe_allow_html=True)
            req=all([st.session_state.full_name,st.session_state.job_title,
                     st.session_state.education,st.session_state.skills])
            if not req: st.info("📝 Fill Name, Job Title, Education & Skills.")
            if st.button("✨  Generate Resume + All Features",disabled=not req,use_container_width=True):
                d = {
                    "full_name":st.session_state.full_name,"job_title":st.session_state.job_title,
                    "email":st.session_state.email,"phone":st.session_state.phone,
                    "location":st.session_state.location,"summary":st.session_state.summary,
                    "experience":st.session_state.experience,"education":st.session_state.education,
                    "skills":st.session_state.skills}

                prog = st.progress(0, text="🤖 Step 1/7 — Generating Resume...")
                res = call_gemini(build_resume_prompt(d), temp, topp)
                st.session_state.resume_md = res
                st.session_state.resume_done = True

                prog.progress(14, text="📊 Step 2/7 — Analyzing ATS Score...")
                ats_prompt = f"""Analyze this resume for ATS compatibility.\nResume:\n{res}\nProvide:\n1. ATS SCORE: X/100\n2. STRENGTHS: 3-4 bullet points\n3. WEAKNESSES: 3-4 bullet points\n4. MISSING KEYWORDS\n5. TOP 5 IMPROVEMENTS"""
                st.session_state.ats_score = call_gemini(ats_prompt, 0.2, 0.85)

                prog.progress(28, text="📝 Step 3/7 — Writing Cover Letter...")
                cl_prompt = f"""Write a professional cover letter based on this resume.\nRESUME:\n{res}\nCompany: Top Tech Company\nPosition: {st.session_state.job_title}\nTone: Professional\n3-4 paragraphs. Output ONLY the cover letter."""
                st.session_state.cover_letter = call_gemini(cl_prompt, 0.4, 0.9)

                prog.progress(42, text="❓ Step 4/7 — Generating Interview Q&A...")
                iq_prompt = f"""Based on this resume, generate 10 interview questions with suggested answers.\nRESUME:\n{res}\nFormat each as:\nQ[number]: [Question]\nA: [2-3 sentence answer using STAR method]"""
                st.session_state.interview_qa = call_gemini(iq_prompt, 0.4, 0.9)

                prog.progress(57, text="🔍 Step 5/7 — Analyzing Skill Gap...")
                sg_prompt = f"""Analyze skill gap for {st.session_state.job_title} role.\nRESUME:\n{res}\nProvide:\n1. CURRENT SKILLS MATCH (✅)\n2. MISSING CRITICAL SKILLS (❌)\n3. NICE-TO-HAVE (💡)\n4. LEARNING ROADMAP with free resources\n5. ESTIMATED TIME to bridge gap"""
                st.session_state.skill_gap = call_gemini(sg_prompt, 0.3, 0.85)

                prog.progress(71, text="💼 Step 6/7 — Generating LinkedIn Summary...")
                li_prompt = f"""Write an optimized LinkedIn About section.\nRESUME:\n{res}\nTone: Professional. Length: Medium (250 words).\nStart with a hook. Include achievements, skills, what you seek. Use emojis sparingly.\nOutput ONLY the LinkedIn About text."""
                st.session_state.linkedin_sum = call_gemini(li_prompt, 0.5, 0.9)

                prog.progress(85, text="🎯 Step 7/7 — Creating Tailored Version...")
                tl_prompt = f"""Improve this resume to be more impactful and ATS-friendly.\nRESUME:\n{res}\nStrengthen bullet points with metrics, improve summary, optimize keywords for {st.session_state.job_title}.\nKeep same Markdown format. Output ONLY the improved resume."""
                st.session_state.tailored_resume = call_gemini(tl_prompt, 0.3, 0.85)

                prog.progress(100, text="✅ All 7 features generated!")
                st.session_state.chat = [{"role":"assistant","content":"✅ All features generated at once! Switch between tabs to see your Resume, ATS Score, Cover Letter, Interview Q&A, Skill Gap, LinkedIn Summary and Tailored Resume — all ready!"}]
                st.success("🎉 All 7 features generated! Switch tabs to explore everything!")

        with cr:
            st.markdown('<div class="sh">📄 Resume Preview</div>',unsafe_allow_html=True)
            if st.session_state.resume_done:
                rhtml=render_html(st.session_state.resume_md,st.session_state.rfont,st.session_state.rsize,st.session_state.rcolor)
                st.markdown(f"""<div style="background:#fff;color:#111;border-radius:12px;padding:1.8rem 2.1rem;
font-family:{st.session_state.rfont};line-height:1.8;
box-shadow:0 20px 60px rgba(0,0,0,.55);max-height:65vh;overflow-y:auto">
{rhtml}</div>""",unsafe_allow_html=True)
                st.markdown("<br>",unsafe_allow_html=True)
                d1,d2,d3=st.columns(3)
                fn=st.session_state.full_name.replace(" ","_")
                with d1:
                    st.download_button("⬇️ Markdown",data=st.session_state.resume_md,
                        file_name=f"resume_{fn}.md",mime="text/markdown",use_container_width=True)
                with d2:
                    st.download_button("⬇️ Text",data=st.session_state.resume_md,
                        file_name=f"resume_{fn}.txt",mime="text/plain",use_container_width=True)
                with d3:
                    # PDF Export
                    try:
                        pdf_bytes=generate_pdf(st.session_state.resume_md,st.session_state.rcolor)
                        st.download_button("⬇️ PDF",data=pdf_bytes,
                            file_name=f"resume_{fn}.pdf",mime="application/pdf",use_container_width=True)
                    except Exception as e:
                        st.button("⬇️ PDF (install reportlab)",disabled=True,use_container_width=True)
            else:
                st.markdown(f"""<div style="text-align:center;padding:5rem 1.5rem;
border:2px dashed rgba(64,144,255,.1);border-radius:12px">
<div style="font-size:3rem">📄</div>
<div style="color:#0f2030;font-size:.92rem;margin-top:.9rem">Resume preview will appear here</div>
<div style="font-size:.78rem;color:#091820;margin-top:.3rem">Fill your details and click Generate</div>
</div>""",unsafe_allow_html=True)

    # ════ TAB 2 — CHAT ════
    with tab2:
        st.markdown('<div class="sh">💬 Chat & Edit Resume</div>',unsafe_allow_html=True)
        if not st.session_state.resume_done:
            st.info("👆 Fill in your details and click **Generate Resume + All Features** — everything generates at once!")
        else:
            st.markdown('<div class="icard">💡 <strong>Session Memory Active</strong> — Ask me to improve, tailor, or rewrite any section.</div>',unsafe_allow_html=True)
            for m in st.session_state.chat:
                css="cu" if m["role"]=="user" else "cb"
                ic="👤" if m["role"]=="user" else "🤖"
                st.markdown(f'<div class="{css}">{ic} {m["content"]}</div>',unsafe_allow_html=True)
            um=st.chat_input("Ask Llama 4 to edit your resume...")
            if um:
                st.session_state.chat.append({"role":"user","content":um})
                with st.spinner("Llama 4 is thinking..."):
                    reply=call_gemini(um,temp,topp,ctx=st.session_state.resume_md)
                if "##" in reply and len(reply)>300:
                    st.session_state.resume_md=reply
                    reply="✅ Resume updated! Switch to Build tab to see changes."
                st.session_state.chat.append({"role":"assistant","content":reply})
                st.rerun()

    # ════ TAB 3 — ATS SCORE ════
    with tab3:
        st.markdown('<div class="sh">📊 ATS Resume Scorer</div>',unsafe_allow_html=True)
        if not st.session_state.resume_done:
            st.info("👆 Fill in your details and click **Generate Resume + All Features** — everything generates at once!")
        else:
            st.markdown('<div class="icard">🎯 ATS Score auto-generated when you clicked Generate Resume — results shown below!</div>',unsafe_allow_html=True)
            if st.session_state.ats_score:
                # Extract score number
                score_text=st.session_state.ats_score
                score_num=None
                for line in score_text.split('\n'):
                    if '/100' in line:
                        nums=re.findall(r'\d+',line)
                        if nums: score_num=int(nums[0]); break

                if score_num:
                    color="#22c55e" if score_num>=80 else "#f59e0b" if score_num>=60 else "#ef4444"
                    st.markdown(f"""
<div style="text-align:center;padding:1.5rem;background:rgba(255,255,255,.03);
border:1px solid {color}40;border-radius:16px;margin-bottom:1.2rem">
<div class="score-big" style="color:{color}">{score_num}</div>
<div style="color:#666;font-size:.9rem;margin-top:.3rem">out of 100</div>
<div style="color:{color};font-size:.85rem;margin-top:.4rem;font-weight:600">
{"🟢 Excellent!" if score_num>=80 else "🟡 Good — needs improvement" if score_num>=60 else "🔴 Needs significant improvement"}
</div></div>""",unsafe_allow_html=True)

                st.markdown(f'<div class="feature-result">{score_text}</div>',unsafe_allow_html=True)

    # ════ TAB 4 — JOB TAILOR ════
    with tab4:
        st.markdown('<div class="sh">🎯 Job Description Tailoring</div>',unsafe_allow_html=True)
        if not st.session_state.resume_done:
            st.info("👆 Fill in your details and click **Generate Resume + All Features** — everything generates at once!")
        else:
            st.markdown('<div class="icard">📋 Paste a job description below → AI rewrites your resume to match that job with relevant keywords.</div>',unsafe_allow_html=True)
            jd=st.text_area("Paste Job Description Here",height=200,
                placeholder="Software Engineer at Google\nRequirements:\n- 3+ years Python experience\n- REST API development\n- Cloud experience (AWS/GCP)\n...")
            if st.button("🎯  Tailor My Resume for This Job",disabled=not jd.strip(),use_container_width=True):
                with st.spinner("🤖 Tailoring your resume for this job..."):
                    prompt=f"""Tailor this resume specifically for the job description below.
ORIGINAL RESUME:\n{st.session_state.resume_md}
JOB DESCRIPTION:\n{jd}
Instructions:
- Add relevant keywords from the job description naturally
- Rewrite bullet points to match required skills
- Highlight experiences most relevant to this role
- Keep same Markdown format (# name, ## sections, ### job titles)
- Output ONLY the tailored resume Markdown."""
                    st.session_state.tailored_resume=call_gemini(prompt,0.3,0.85)

            if st.session_state.tailored_resume:
                st.success("✅ Tailored resume ready!")
                rhtml=render_html(st.session_state.tailored_resume,st.session_state.rfont,st.session_state.rsize,st.session_state.rcolor)
                st.markdown(f"""<div style="background:#fff;color:#111;border-radius:12px;padding:1.5rem 2rem;
font-family:{st.session_state.rfont};max-height:500px;overflow-y:auto;
box-shadow:0 10px 40px rgba(0,0,0,.4)">{rhtml}</div>""",unsafe_allow_html=True)
                st.markdown("<br>",unsafe_allow_html=True)
                d1,d2=st.columns(2)
                fn=st.session_state.full_name.replace(" ","_")
                with d1:
                    st.download_button("⬇️ Download Tailored Resume",
                        data=st.session_state.tailored_resume,
                        file_name=f"tailored_resume_{fn}.md",mime="text/markdown",use_container_width=True)
                with d2:
                    try:
                        pdf_b=generate_pdf(st.session_state.tailored_resume,st.session_state.rcolor)
                        st.download_button("⬇️ Download as PDF",data=pdf_b,
                            file_name=f"tailored_resume_{fn}.pdf",mime="application/pdf",use_container_width=True)
                    except: pass

    # ════ TAB 5 — COVER LETTER ════
    with tab5:
        st.markdown('<div class="sh">📝 Cover Letter Generator</div>',unsafe_allow_html=True)
        if not st.session_state.resume_done:
            st.info("👆 Fill in your details and click **Generate Resume + All Features** — everything generates at once!")
        else:
            st.markdown('<div class="icard">✅ Cover letter was auto-generated! Showing below. Customise company/position above and click Regenerate if needed.</div>',unsafe_allow_html=True)
            cj1,cj2=st.columns(2)
            with cj1:
                company=st.text_input("Company Name",placeholder="Google, Microsoft, TCS...")
            with cj2:
                position=st.text_input("Position Applying For",placeholder="Software Engineer")
            tone=st.select_slider("Tone",options=["Formal","Professional","Enthusiastic"],value="Professional")
            if st.session_state.cover_letter:
                st.markdown(f'<div class="feature-result">{st.session_state.cover_letter}</div>',unsafe_allow_html=True)
                st.download_button("⬇️ Download Cover Letter",
                    data=st.session_state.cover_letter,
                    file_name="cover_letter.txt",mime="text/plain",use_container_width=True)

    # ════ TAB 6 — INTERVIEW PREP ════
    with tab6:
        st.markdown('<div class="sh">❓ Interview Question Generator</div>',unsafe_allow_html=True)
        if not st.session_state.resume_done:
            st.info("👆 Fill in your details and click **Generate Resume + All Features** — everything generates at once!")
        else:
            st.markdown('<div class="icard">✅ Interview questions auto-generated! Scroll to review all Q&As below.</div>',unsafe_allow_html=True)
            iq1,iq2=st.columns(2)
            with iq1:
                num_q=st.slider("Number of Questions",5,15,10)
            with iq2:
                q_type=st.selectbox("Question Type",["Mixed (Technical + HR)","Technical Only","HR & Behavioral Only"])
            if st.session_state.interview_qa:
                st.markdown(f'<div class="feature-result">{st.session_state.interview_qa}</div>',unsafe_allow_html=True)
                st.download_button("⬇️ Download Q&A",
                    data=st.session_state.interview_qa,
                    file_name="interview_prep.txt",mime="text/plain",use_container_width=True)

    # ════ TAB 7 — SKILL GAP ════
    with tab7:
        st.markdown('<div class="sh">🔍 Skill Gap Analyzer</div>',unsafe_allow_html=True)
        if not st.session_state.resume_done:
            st.info("👆 Fill in your details and click **Generate Resume + All Features** — everything generates at once!")
        else:
            st.markdown('<div class="icard">✅ Skill gap analysis auto-generated for your job title! Review below.</div>',unsafe_allow_html=True)
            dream_job=st.text_input("Enter Your Dream Job Title",placeholder="Data Scientist, Full Stack Developer, DevOps Engineer...")
            if st.session_state.skill_gap:
                st.markdown(f'<div class="feature-result">{st.session_state.skill_gap}</div>',unsafe_allow_html=True)
                st.download_button("⬇️ Download Skill Gap Report",
                    data=st.session_state.skill_gap,
                    file_name="skill_gap_report.txt",mime="text/plain",use_container_width=True)

    # ════ TAB 8 — LINKEDIN ════
    with tab8:
        st.markdown('<div class="sh">💼 LinkedIn Summary Generator</div>',unsafe_allow_html=True)
        if not st.session_state.resume_done:
            st.info("👆 Fill in your details and click **Generate Resume + All Features** — everything generates at once!")
        else:
            st.markdown('<div class="icard">✅ LinkedIn summary auto-generated! Copy it directly to your LinkedIn profile.</div>',unsafe_allow_html=True)
            li1,li2=st.columns(2)
            with li1:
                li_tone=st.selectbox("Summary Tone",["Professional","Conversational","Bold & Confident"])
            with li2:
                li_len=st.selectbox("Length",["Short (150 words)","Medium (250 words)","Long (400 words)"])
            if st.session_state.linkedin_sum:
                st.markdown(f'<div class="feature-result">{st.session_state.linkedin_sum}</div>',unsafe_allow_html=True)
                d1,d2=st.columns(2)
                with d1:
                    st.download_button("⬇️ Download LinkedIn Summary",
                        data=st.session_state.linkedin_sum,
                        file_name="linkedin_summary.txt",mime="text/plain",use_container_width=True)
                with d2:
                    char_count=len(st.session_state.linkedin_sum)
                    color_c="#22c55e" if char_count<=2600 else "#ef4444"
                    st.markdown(f'<div style="text-align:center;padding:.8rem;background:rgba(255,255,255,.03);border-radius:8px;color:{color_c};font-size:.85rem">{"✅" if char_count<=2600 else "⚠️"} {char_count} chars {"(within LinkedIn limit)" if char_count<=2600 else "(too long — LinkedIn max is 2600)"}</div>',unsafe_allow_html=True)

# ══════════════════════════════════════════════
# ROUTER
# ══════════════════════════════════════════════
p=st.session_state.page
if   p=="splash":    show_splash()
elif p=="auth":      show_auth()
elif p=="api_setup":
    if not st.session_state.logged_in: st.session_state.page="auth"; st.rerun()
    show_api_setup()
elif p=="main":
    if not st.session_state.logged_in or not st.session_state.api_ok:
        st.session_state.page="auth"; st.rerun()
    show_main()
