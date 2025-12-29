import streamlit as st
import pandas as pd
import numpy as np
import time
import base64
import random

# --- 1. Config & Setup ---
st.set_page_config(
    page_title="SMART Audit AI",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="collapsed" # เริ่มต้นพับแถบซ้าย (แก้ปัญหา Login เห็น sidebar)
)

# --- 0. AI CONFIGURATION ---
try:
    import google.generativeai as genai
    # ดึง Key จาก Secrets หรือใช้ Hardcode
    if "GOOGLE_API_KEY" in st.secrets:
        api_key = st.secrets["GOOGLE_API_KEY"]
        genai.configure(api_key=api_key)
        HAS_AI_CONNECTION = True
        AI_ERROR_MSG = ""
    else:
        # ใส่ Key ของอาจารย์ตรงนี้
        HARDCODED_KEY = "AIzaSyCW-ITlPRTPWjEzOieG8KdYU1Gh8Hg-gy0" 
        genai.configure(api_key=HARDCODED_KEY)
        HAS_AI_CONNECTION = True
        AI_ERROR_MSG = ""
except ImportError:
    HAS_AI_CONNECTION = False
    AI_ERROR_MSG = "⚠️ ยังไม่ได้ติดตั้ง google-generativeai"
except Exception as e:
    HAS_AI_CONNECTION = False
    AI_ERROR_MSG = f"⚠️ Error: {str(e)}"

# --- 2. Resources (Logo) ---
def get_base64_logo():
    # Logo SVG (Blue/Gold)
    svg = """
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512" width="100" height="100">
      <path fill="#1565C0" d="M256 0C114.6 0 0 114.6 0 256s114.6 256 256 256 256-114.6 256-256S397.4 0 256 0zm0 472c-119.3 0-216-96.7-216-216S136.7 40 256 40s216 96.7 216 216-96.7 216-216 216z"/>
      <path fill="#FFD700" d="M368 232h-88v-88c0-13.3-10.7-24-24-24s-24 10.7-24 24v88h-88c-13.3 0-24 10.7-24 24s10.7 24 24 24h88v88c0 13.3 10.7 24 24 24s24-10.7 24-24v-88h88c13.3 0 24-10.7 24-24s-10.7-24-24-24z"/>
    </svg>
    """
    return base64.b64encode(svg.encode('utf-8')).decode("utf-8")

LOGO_HTML = f'<img src="data:image/svg+xml;base64,{get_base64_logo()}" width="100">'
LOGO_SIDEBAR = f'<img src="data:image/svg+xml;base64,{get_base64_logo()}" width="80" style="display:block; margin: 0 auto 20px auto;">'

# --- 3. CSS Styling (Green Buttons & Visible Table) ---
def apply_theme():
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Prompt:wght@300;400;500;700&display=swap');
        
        /* 1. Global Font */
        html, body, [class*="css"] {
            font-family: 'Prompt', sans-serif;
            color: #333333 !important; /* บังคับตัวหนังสือดำเทา */
        }
        
        /* 2. Sidebar Styling */
        section[data-testid="stSidebar"] {
            background-color: #FFFFFF !important;
            border-right: 1px solid #E0E0E0;
        }
        
        /* 3. Green Buttons (Equal Size) */
        div.stButton > button {
            background-color: #1B5E20 !important; /* สีเขียวเข้ม */
            color: #FFFFFF !important; /* ตัวหนังสือขาว */
            border: none;
            border-radius: 8px;
            padding: 12px 20px;
            font-weight: 600;
            width: 100%; /* กว้างเต็มช่อง */
            box-shadow: 0 2px 5px rgba(0,0,0,0.2);
            transition: all 0.3s;
        }
        div.stButton > button:hover {
            background-color: #2E7D32 !important; /* เขียวสว่างขึ้นตอนเอาเมาส์ชี้ */
            box-shadow: 0 4px 8px rgba(0,0,0,0.3);
            transform: translateY(-2px);
        }
        
        /* 4. Table Styling (Fix Invisible Text) */
        [data-testid="stDataFrame"] {
            background-color: #FFFFFF !important;
            border: 1px solid #E0E0E0;
            border-radius: 10px;
            padding: 5px;
        }
        [data-testid="stDataFrame"] div, [data-testid="stDataFrame"] span {
            color: #000000 !important; /* บังคับตัวหนังสือดำสนิท */
        }
        [data-testid="stDataFrame"] th {
            background-color: #F1F8E9 !important; /* หัวตารางเขียวอ่อน */
            color: #1B5E20 !important; /* ตัวหนังสือหัวตารางเขียวเข้ม */
            font-weight: bold !important;
        }
        
        /* 5. Inputs */
        .stTextInput input, .stPasswordInput input {
            background-color: #FFFFFF !important;
            color: #000000 !important;
            border: 1px solid #CCCCCC !important;
            border-radius: 6px;
        }
        
        /* 6. Metric Cards */
        .metric-card {
            background: white; padding: 20px; border-radius: 12px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.05);
            border-left: 5px solid #1B5E20; /* ขอบเขียว */
            text-align: center;
        }
        
        /* Login Box */
        .login-box {
            background: white; padding: 40px; border-radius: 16px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
            text-align: center; border-top: 5px solid #1B5E20;
        }
        </style>
    """, unsafe_allow_html=True)

# --- 4. Session State ---
if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'username' not in st.session_state: st.session_state.username = ""
if 'audit_data' not in st.session_state: st.session_state.audit_data = None
if 'summary' not in st.session_state: st.session_state.summary = {}
if 'current_page' not in st.session_state: st.session_state.current_page = "login"
if 'chat_history' not in st.session_state: 
    st.session_state.chat_history = [
        {"role": "assistant", "content": "สวัสดีครับ ผมคือ AI Consultant 🤖 พร้อมให้คำปรึกษาครับ"}
    ]

# --- 5. Mock Logic ---
def process_data_mock(uploaded_files):
    progress_text = "AI กำลังตรวจสอบข้อมูล..."
    my_bar = st.progress(0, text=progress_text)
    for percent_complete in range(100):
        time.sleep(0.01) 
        my_bar.progress(percent_complete + 1, text=progress_text)
    time.sleep(0.2)
    my_bar.empty()
    
    data = []
    pttypes = ['UCS', 'OFC', 'SSS', 'LGO']
    for i in range(150):
        is_ipd = np.random.choice([True, False], p=[0.3, 0.7])
        hn = f"{np.random.randint(60000, 69999):05d}"
        an = f"{np.random.randint(10000, 19999):05d}" if is_ipd else "-"
        date_serv = f"2024-{np.random.randint(1,13):02d}-{np.random.randint(1,28):02d}"
        pttype = np.random.choice(pttypes)
        
        case_type = np.random.choice(['Normal', 'Overclaim', 'Underclaim'], p=[0.6, 0.25, 0.15])
        finding, action, impact = "-", "-", 0
        
        if case_type == 'Overclaim':
            finding = "วันจำหน่ายก่อนวันรับเข้า (Date Error)"
            action = "แก้ไขวันที่ (DATEDSC)"
            impact = -1 * np.random.randint(1000, 10000)
        elif case_type == 'Underclaim':
            finding = "ไม่ลงรหัสหัตถการ (Missing Proc)"
            action = "เพิ่มรหัสหัตถการ (ICD-9)"
            impact = np.random.randint(500, 5000)
            
        data.append({
            "HN": hn, "AN": an, "DATE": date_serv, "PTTYPE": pttype,
            "FINDING": finding, "ACTION": action, "IMPACT": impact,
            "TYPE": "IPD" if is_ipd else "OPD"
        })
        
    df = pd.DataFrame(data)
    pre = 8500000.0
    imp = df['IMPACT'].sum()
    return df, {"records": 166196, "pre_audit": pre, "post_audit": pre + imp, "impact": imp}

def get_ai_response(user_input):
    if not HAS_AI_CONNECTION:
        return f"{AI_ERROR_MSG} (กรุณาอัปเดต requirements.txt)"

    try:
        summary_text = "ไม่มีข้อมูล Audit"
        if st.session_state.summary:
            s = st.session_state.summary
            summary_text = f"ยอด Record={s['records']:,}, Impact={s['impact']:,.0f} บาท"

        system_prompt = f"""
        คุณคือ AI Consultant โรงพยาบาลพระนารายณ์มหาราช
        ข้อมูล: {summary_text}
        หน้าที่: ตอบคำถาม Audit/Claim สั้นกระชับ สุภาพ ภาษาไทย
        คำถาม: {user_input}
        """
        
        # Auto-detect Model Logic
        model_name = 'gemini-pro
