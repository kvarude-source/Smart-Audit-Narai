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
    initial_sidebar_state="collapsed"
)

# --- 0. AI CONFIGURATION ---
HAS_AI_CONNECTION = False
AI_ERROR_MSG = ""

try:
    import google.generativeai as genai
    
    # พยายามดึง Key
    if "GOOGLE_API_KEY" in st.secrets:
        api_key = st.secrets["GOOGLE_API_KEY"]
        genai.configure(api_key=api_key)
        HAS_AI_CONNECTION = True
    else:
        # Hardcode Key (บรรทัดนี้สั้นลงเพื่อความปลอดภัยในการ Copy)
        KEY = "AIzaSyCW-ITlPRTPWjEzOieG8KdYU1Gh8Hg-gy0" 
        genai.configure(api_key=KEY)
        HAS_AI_CONNECTION = True

except ImportError:
    AI_ERROR_MSG = "Error: Library not found."
except Exception as e:
    AI_ERROR_MSG = f"Error: {str(e)}"

# --- 2. Resources (Logo) ---
def get_base64_logo():
    # Logo SVG (Split to avoid truncation)
    p1 = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512" width="100" height="100">'
    p2 = '<path fill="#1565C0" d="M256 0C114.6 0 0 114.6 0 256s114.6 256 256 256 256-114.6 256-256S397.4 0 256 0zm0 472c-119.3 0-216-96.7-216-216S136.7 40 256 40s216 96.7 216 216-96.7 216-216 216z"/>'
    p3 = '<path fill="#FFD700" d="M368 232h-88v-88c0-13.3-10.7-24-24-24s-24 10.7-24 24v88h-88c-13.3 0-24 10.7-24 24s10.7 24 24 24h88v88c0 13.3 10.7 24 24 24s24-10.7 24-24v-88h88c13.3 0 24-10.7 24-24s-10.7-24-24-24z"/>'
    p4 = '</svg>'
    svg = p1 + p2 + p3 + p4
    return base64.b64encode(svg.encode('utf-8')).decode("utf-8")

LOGO_HTML = f'<img src="data:image/svg+xml;base64,{get_base64_logo()}" width="100">'
LOGO_SIDE = f'<img src="data:image/svg+xml;base64,{get_base64_logo()}" width="80" style="display:block;margin:0 auto 20px;">'

# --- 3. CSS Styling (Safe Mode) ---
def apply_theme():
    # CSS แยกเป็นส่วนๆ เพื่อป้องกัน Error
    css_main = """
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Prompt:wght@300;400;500;700&display=swap');
        html, body, [class*="css"] {
            font-family: 'Prompt', sans-serif;
            color: #333333 !important;
        }
        section[data-testid="stSidebar"] {
            background-color: #FFFFFF !important;
            border-right: 1px solid #E0E0E0;
        }
    </style>
    """
    
    css_btn = """
    <style>
        div.stButton > button {
            background-color: #1B5E20 !important;
            color: #FFFFFF !important;
            border: none;
            border-radius: 8px;
            padding: 12px 20px;
            font-weight: 600;
            width: 100%;
            box-shadow: 0 2px 5px rgba(0,0,0,0.2);
        }
        div.stButton > button:hover {
            background-color: #2E7D32 !important;
        }
    </style>
    """
    
    css_table = """
    <style>
        [data-testid="stDataFrame"] {
            background-color: #FFFFFF !important;
            border: 1px solid #E0E0E0;
            border-radius: 10px;
            padding: 5px;
        }
        [data-testid="stDataFrame"] div, [data-testid="stDataFrame"] span {
            color: #000000 !important;
        }
        [data-testid="stDataFrame"] th {
            background-color: #F1F8E9 !important;
            color: #1B5E20 !important;
        }
    </style>
    """
    
    css_others = """
    <style>
        .stTextInput input, .stPasswordInput input {
            background-color: #FFFFFF !important;
            color: #000000 !important;
            border: 1px solid #CCCCCC !important;
            border-radius: 6px;
        }
        .metric-card {
            background: white; padding: 20px; border-radius: 12px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.05);
            border-left: 5px solid #1B5E20;
            text-align: center;
        }
        .login-box {
            background: white; padding: 40px; border-radius: 16px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
            text-align: center; border-top: 5px solid #1B5E20;
        }
    </style>
    """
    
    st.markdown(css_main + css_btn + css_table + css_others, unsafe_allow_html=True)

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

# --- 5. Logic ---
def process_data_mock(uploaded_files):
    # Progress Bar
    bar = st.progress(0, text="Processing...")
    for i in range(100):
        time.sleep(0.01)
        bar.progress(i + 1)
    time.sleep(0.1)
    bar.empty()
    
    # Mock Data Creation (Safe Mode Loop)
    data = []
    types = ['UCS', 'OFC', 'SSS', 'LGO']
    
    for i in range(150):
        is_ipd = np.random.choice([True, False], p=[0.3, 0.7])
        
        # Create row safely
        row = {}
        row["HN"] = f"{np.random.randint(60000, 69999):05d}"
        row["AN"] = f"{np.random.randint(10000, 19999):05d}" if is_ipd else "-"
        row["DATE"] = f"2024-{np.random.randint(1,13):02d}-{np.random.randint(1,28):02d}"
        row["PTTYPE"] = np.random.choice(types)
        row["TYPE"] = "IPD" if is_ipd else "OPD"
        
        case = np.random.choice(['Normal', 'Over', 'Under'], p=[0.6, 0.25, 0.15])
        
        if case == 'Over':
            row["FINDING"] = "วันจำหน่ายก่อนวันรับเข้า"
            row["ACTION"] = "แก้ไขวันที่ (DATEDSC)"
            row["IMPACT"] = -1 * np.random.randint(1000, 10000)
        elif case == 'Under':
            row["FINDING"] = "ไม่ลงรหัสหัตถการ"
            row["ACTION"] = "เพิ่มรหัสหัตถการ"
            row["IMPACT"] = np.random.randint(500, 5000)
        else:
            row["FINDING"] = "-"
            row["ACTION"] = "-"
            row["IMPACT"] = 0
            
        data.append(row)
        
    df = pd.DataFrame(data)
    pre = 8500000.0
    imp = df['IMPACT'].sum()
    
    summ = {
        "records": 166196,
        "pre_audit": pre,
        "post_audit": pre + imp,
        "impact": imp
    }
    return df, summ

def get_ai_response(user_input):
    if not HAS_AI_CONNECTION:
        return f"{AI_ERROR_MSG} (Check requirements.txt)"

    try:
        # Context
        info = "No Data"
        if st.session_state.summary:
            s = st.session_state.summary
            info = f"Records={s['records']:,}, Impact={s['impact']:,.0f}"

        prompt = f"""
        Role: AI Consultant for Hospital Audit.
        Context: {info}
        Task: Answer question about medical audit/claim in Thai.
        Question: {user_input}
        """
        
        # Auto-detect Model
        m_name = 'gemini-pro'
        try:
            mods = genai.list_models()
            for m in mods:
                if 'flash' in m.name:
                    m_name = m.name
                    break
        except:
            pass

        model = genai.GenerativeModel(m_name)
        res = model.generate_content(prompt)
        return res.text

    except Exception as e:
        return f"Error: {str(e)}"

# --- 6. Components ---
def render_card(title, value, sub, is_impact=False):
    color = "#1B5E20"
    if is_impact:
        val_num = float(str(value).replace(',','').replace(' ฿','').replace('+',''))
        if val_num < 0:
            color = "#D32F2F"
            sub = "▼ Overclaim"
        elif val_num > 0:
            color = "#388E3C"
            sub = "▲ Underclaim"
    
    # HTML String แยกบรรทัดเพื่อความปลอดภัย
    html = f"""
    <div class="metric-card">
        <div style="font-size:14px; color:#666;">{title}</div>
        <div style="font-size:28px; font-weight:800; margin-top:5px; color:{color};">{value}</div>
        <div style="font-size:13px; margin-top:5px; color:{color};">{sub}</div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)

# --- 7. Pages ---
def login_page():
    c1, c2, c3 = st.columns([1, 1.5, 1])
    with c2:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown('<div class="login-box">', unsafe_allow_html=True)
        st.markdown(LOGO_HTML, unsafe_allow_html=True)
        st.markdown('<h2 style="color:#1B5E20;">โรงพยาบาลพระนารายณ์มหาราช</h2>', unsafe_allow_html=True)
        st.markdown('<p>SMART Audit AI System</p><br>', unsafe_allow_html=True)
        
        with st.form("login"):
            st.text_input("Username", key="u_input")
            st.text_input("Password", type="password", key="p_input")
            st.markdown("<br>", unsafe_allow_html=True)
            if st.form_submit_button("LOGIN", use_container_width=True):
                u = st.session_state.u_input.lower().strip()
                p = st.session_state.p_input.strip()
                if u == "hosnarai" and p == "h15000":
                    st.session_state.logged_in = True
                    st.session_state.username = "Hosnarai"
                    st.session_state.current_page = "upload"
                    st.rerun()
                else:
                    st.error("Invalid Username/Password")
        st.markdown('</div>', unsafe_allow_html=True)

def upload_page():
    c1, c2 = st.columns([4, 1])
    with c1: st.markdown(f"<h2 style='color:#1B5E20;'>Data Import Center</h2>", unsafe_allow_html=True)
    with c2: st.markdown(f"<div style='text-align:right;padding-top:10px;'><b>{st.session_state.username}</b></div>", unsafe_allow_html=True)
    
    st.markdown("---")
    st.markdown("""
    <div style="background:white; padding:40px; border:2px dashed #A5D6A7; text-align:center; margin-bottom:20px;">
        <h3 style="color:#1B5E20;">📂 Upload 52 Files</h3>
    </div>
    """, unsafe_allow_html=True)
    
    up = st.file_uploader("", accept_multiple_files=True)
    if up:
        st.info(f"Files loaded: {len(up)}")
        if st.button("🚀 Start Audit", type="primary"):
            df, summ = process_data_mock(up)
            st.session_state.audit_data = df
            st.session_state.summary = summ
            st.session_state.current_page = "dashboard"
            st.rerun()

def dashboard_page():
    c1, c2 = st.columns([4, 1.2])
    with c1: st.markdown(f"<h2 style='color:#1B5E20;'>Executive Dashboard</h2>", unsafe_allow_html=True)
    with c2: 
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("↺ Analyze New"):
            st.session_state.current_page = "upload"
            st.rerun()

    st.markdown("---")
    if st.session_state.audit_data is None:
        st.warning("Please upload data first.")
        return

    s = st.session_state.summary
    m1, m2, m3, m4 = st.columns(4)
    with m1: render_card("Total Records", f"{s['records']:,}", "All Files")
    with m2: render_card("Pre-Audit", f"{s['pre_audit']:,.0f} ฿", "Initial")
    with m3: render_card("Post-Audit", f"{s['post_audit']:,.0f} ฿", "Expected")
    with m4: render_card("Financial Impact", f"{s['impact']:+,.0f} ฿", "", True)

    st.markdown("<br>", unsafe_allow_html=True)
    
    tabs = st.tabs(["ALL", "OPD", "IPD"])
    df = st.session_state.audit_data
    
    # Config Table
    cfg = {
        "HN": st.column_config.TextColumn("HN", width="small"),
        "FINDING": st.column_config.TextColumn("Findings", width="large"),
        "ACTION": st.column_config.TextColumn("Action", width="large"),
        "IMPACT": st.column_config.NumberColumn("Impact", format="%.0f ฿")
    }
    
    def show(d):
        if not d.empty:
            st.dataframe(d, column_config=cfg, use_container_width=True, height=500)
        else:
            st.success("No Findings")

    with tabs[0]: show(df)
    with tabs[1]: show(df[df['TYPE']=='OPD'])
    with tabs[2]: show(df[df['TYPE']=='IPD'])

def chat_page():
    st.markdown(f"<h2 style='color:#1B5E20;'>AI Consultant</h2>", unsafe_allow_html=True)
    st.markdown("---")
    
    for msg in st.session_state.chat_history:
        role = msg["role"]
        with st.chat_message(role):
            st.markdown(msg["content"])

    if p := st.chat_input("Ask AI..."):
        st.session_state.chat_history.append({"role":"user", "content":p})
        with st.chat_message("user"): st.markdown(p)
        
        with st.spinner("Thinking..."):
            ans = get_ai_response(p)
            
        st.session_state.chat_history.append({"role":"assistant", "content":ans})
        with st.chat_message("assistant"): st.markdown(ans)

# --- 8. Main ---
def main():
    apply_theme()
    
    if st.session_state.logged_in:
        with st.sidebar:
            st.markdown(LOGO_SIDE, unsafe_allow_html=True)
            st.markdown("---")
            if st.button("📊 Dashboard"):
                st.session_state.current_page = "dashboard"
                st.rerun()
            st.write("")
            if st.button("💬 AI Consultant"):
                st.session_state.current_page = "chat"
                st.rerun()
            st.write("")
            if st.button("📤 Upload Data"):
                st.session_state.current_page = "upload"
                st.rerun()
            st.write("")
            st.markdown("---")
            if st.button("Logout"):
                st.session_state.clear()
                st.rerun()

    if not st.session_state.logged_in:
        login_page()
    elif st.session_state.current_page == "chat":
        chat_page()
    elif st.session_state.current_page == "dashboard":
        dashboard_page()
    else:
        upload_page()

if __name__ == "__main__":
    main()
