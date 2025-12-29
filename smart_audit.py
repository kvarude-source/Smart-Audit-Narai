import streamlit as st
import pandas as pd
import numpy as np
import time
import base64
import logging
import random
from datetime import datetime

# --- Import ML (Optional) ---
try:
    from sklearn.ensemble import IsolationForest
    HAS_ML = True
except ImportError:
    HAS_ML = False

# --- 1. Config & Setup ---
st.set_page_config(
    page_title="SMART Audit AI - Executive",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. Resources (Logo) ---
def get_base64_logo():
    # Logo SVG (Premium Navy/Gold)
    svg = """
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512" width="100" height="100">
      <path fill="#0F172A" d="M256 0C114.6 0 0 114.6 0 256s114.6 256 256 256 256-114.6 256-256S397.4 0 256 0zm0 472c-119.3 0-216-96.7-216-216S136.7 40 256 40s216 96.7 216 216-96.7 216-216 216z"/>
      <path fill="#D4AF37" d="M368 232h-88v-88c0-13.3-10.7-24-24-24s-24 10.7-24 24v88h-88c-13.3 0-24 10.7-24 24s10.7 24 24 24h88v88c0 13.3 10.7 24 24 24s24-10.7 24-24v-88h88c13.3 0 24-10.7 24-24s-10.7-24-24-24z"/>
    </svg>
    """
    return base64.b64encode(svg.encode('utf-8')).decode("utf-8")

LOGO_HTML = f'<img src="data:image/svg+xml;base64,{get_base64_logo()}" width="80" style="vertical-align:middle; margin-right:15px;">'

# --- 3. CSS Styling (Ultra Premium) ---
def apply_theme():
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Prompt:wght@300;400;500;700&display=swap');
        
        html, body, [class*="css"] {
            font-family: 'Prompt', sans-serif;
            color: #1E293B;
        }
        .stApp { background-color: #F8FAFC; }
        
        /* Headers */
        h1, h2, h3 { color: #0F172A !important; }
        
        /* Sidebar */
        section[data-testid="stSidebar"] { background-color: #0F172A; }
        section[data-testid="stSidebar"] * { color: #F8FAFC !important; }
        
        /* Chat Interface Styling */
        .stChatMessage {
            background-color: white;
            border-radius: 15px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.05);
            border: 1px solid #E2E8F0;
            padding: 10px;
        }
        [data-testid="stChatMessageAvatarUser"] {
            background-color: #D4AF37 !important;
        }
        [data-testid="stChatMessageAvatarAssistant"] {
            background-color: #0F172A !important;
        }
        
        /* Metric Cards */
        .metric-card {
            background: white; padding: 25px; border-radius: 16px;
            box-shadow: 0 10px 25px -5px rgba(0,0,0,0.05);
            border-left: 8px solid #0F172A;
        }
        .metric-title { font-size: 16px; color: #64748B; font-weight: 600; }
        .metric-value { font-size: 32px; color: #0F172A; font-weight: 800; margin-top: 5px; }
        
        /* Buttons & Inputs */
        div.stButton > button {
            background: linear-gradient(135deg, #0F172A 0%, #1E293B 100%);
            color: white !important; border-radius: 12px; font-weight: 600;
        }
        .stTextInput input { border-radius: 10px; border: 2px solid #E2E8F0; }
        
        /* Tabs */
        .stTabs [data-baseweb="tab"][aria-selected="true"] {
            border-top: 4px solid #D4AF37; color: #0F172A;
        }
        </style>
    """, unsafe_allow_html=True)

# --- 4. Session State (Fixed) ---
if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'username' not in st.session_state: st.session_state.username = "" # เพิ่มบรรทัดนี้เพื่อแก้ Error
if 'audit_data' not in st.session_state: st.session_state.audit_data = None
if 'summary' not in st.session_state: st.session_state.summary = {}
if 'current_page' not in st.session_state: st.session_state.current_page = "login"
if 'chat_history' not in st.session_state: 
    st.session_state.chat_history = [
        {"role": "assistant", "content": "สวัสดีครับ ผมคือ AI Consultant ประจำโรงพยาบาลพระนารายณ์มหาราช 🏥 \n\nผมพร้อมให้คำปรึกษาเรื่อง Audit ข้อมูลครับ"}
    ]

# --- 5. Logic & Mock Data ---
def process_data_mock(uploaded_files):
    time.sleep(1.0)
    data = []
    pttypes = ['UCS', 'OFC', 'SSS', 'LGO']
    
    for i in range(150):
        is_ipd = np.random.choice([True, False], p=[0.3, 0.7])
        hn = f"{np.random.randint(60000, 69999):05d}"
        an = f"{np.random.randint(10000, 19999):05d}" if is_ipd else "-"
        pttype = np.random.choice(pttypes)
        
        case_type = np.random.choice(['Normal', 'Overclaim', 'Underclaim'], p=[0.6, 0.25, 0.15])
        finding, action, impact = "-", "-", 0
        
        if case_type == 'Overclaim':
            finding = "วันจำหน่ายก่อนวันรับเข้า (Date Error)"
            action = "แก้ไขวันที่ (DATEDSC) ให้ถูกต้อง"
            impact = -1 * np.random.randint(1000, 10000)
        elif case_type == 'Underclaim':
            finding = "ไม่ได้ลงรหัสหัตถการ (Missing Proc)"
            action = "เพิ่มรหัสหัตถการ (ICD-9) เพื่อเบิกเพิ่ม"
            impact = np.random.randint(500, 5000)
            
        data.append({
            "HN": hn, "AN": an, "DATE": "2024-03-15", "PTTYPE": pttype,
            "FINDING": finding, "ACTION": action, "IMPACT": impact,
            "TYPE": "IPD" if is_ipd else "OPD"
        })
        
    df = pd.DataFrame(data)
    pre = 8500000.0
    imp = df['IMPACT'].sum()
    
    return df, {"records": 166196, "pre_audit": pre, "post_audit": pre + imp, "impact": imp}

# --- 6. AI Consultant Logic ---
def get_ai_response(user_input):
    user_input = user_input.lower()
    summary_text = ""
    if st.session_state.summary:
        summ = st.session_state.summary
        summary_text = f"ยอด Impact รวมอยู่ที่ {summ['impact']:,.0f} บาท"
    
    if "date" in user_input or "วัน" in user_input:
        return f"สำหรับปัญหาเรื่อง **วันที่ (Date Error)** 📅 \n\nมักเกิดจากฟิลด์ `DATEDSC` (วันจำหน่าย) ลงเวลาเร็วกว่า `DATEADM` (วันรับเข้า) ครับ \n\n**วิธีแก้ไข:** \n1. ตรวจสอบเวชระเบียน \n2. แก้ไขวันที่ในระบบ HIS \n3. ส่งออกข้อมูลใหม่อีกครั้ง"
    elif "impact" in user_input or "เงิน" in user_input:
        return f"สถานะทางการเงินตอนนี้: **{summary_text}** ครับ \n\nสีแดง (Overclaim) คือความเสี่ยงถูกเรียกเงินคืนครับ"
    else:
        return "ผมพร้อมให้คำปรึกษาครับ พิมพ์คำถามได้เลย 😊"

# --- 7. Pages ---

def login_page():
    c1, c2, c3 = st.columns([1, 1.5, 1])
    with c2:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown('<div class="login-box" style="background:white; padding:50px; border-radius:20px; text-align:center; box-shadow:0 10px 30px rgba(0,0,0,0.1); border-top:6px solid #D4AF37;">', unsafe_allow_html=True)
        st.markdown(LOGO_HTML, unsafe_allow_html=True)
        st.markdown('<h2 style="color:#0F172A; margin-top:15px;">โรงพยาบาลพระนารายณ์มหาราช</h2>', unsafe_allow_html=True)
        st.markdown('<p style="color:#64748B;">SMART Audit AI System</p>', unsafe_allow_html=True)
        
        with st.form("login"):
            st.text_input("Username", key="u_input")
            st.text_input("Password", type="password", key="p_input")
            if st.form_submit_button("เข้าสู่ระบบ (LOGIN)", use_container_width=True):
                if st.session_state.u_input.lower().strip() == "hosnarai" and st.session_state.p_input.strip() == "h15000":
                    st.session_state.logged_in = True
                    st.session_state.username = "Hosnarai" # Set username here
                    st.session_state.current_page = "upload"
                    st.rerun()
                else:
                    st.error("รหัสผ่านไม่ถูกต้อง")
        st.markdown('</div>', unsafe_allow_html=True)

def upload_page():
    c1, c2 = st.columns([4, 1])
    with c1:
        st.markdown(f"<div style='display:flex;align-items:center;'>{LOGO_HTML}<div><h2 style='margin:0'>Data Import Center</h2><p style='margin:0'>ระบบนำเข้าข้อมูล 52 แฟ้ม</p></div></div>", unsafe_allow_html=True)
    with c2:
        st.markdown(f"<div style='text-align:right;padding-top:10px;'><b>{st.session_state.username}</b></div>", unsafe_allow_html=True)
    
    st.markdown("---")
    
    uploaded = st.file_uploader("", type=["txt"], accept_multiple_files=True)
    
    if uploaded:
        st.success(f"✅ Ready: {len(uploaded)} Files")
        if st.button("🚀 เริ่มวิเคราะห์ (Start Audit)", type="primary"):
            with st.spinner("AI กำลังวิเคราะห์..."):
                df, summ = process_data_mock(uploaded)
                st.session_state.audit_data = df
                st.session_state.summary = summ
                st.session_state.current_page = "dashboard"
                st.rerun()

def dashboard_page():
    # Header
    c1, c2 = st.columns([4, 1.2])
    with c1:
        st.markdown(f"<div style='display:flex;align-items:center;'>{LOGO_HTML}<div><h2 style='margin:0'>Executive Dashboard</h2><p style='margin:0'>โรงพยาบาลพระนารายณ์มหาราช</p></div></div>", unsafe_allow_html=True)
    with c2:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("↺ วิเคราะห์ใหม่", use_container_width=True):
            st.session_state.current_page = "upload"
            st.rerun()

    st.markdown("---")
    
    if st.session_state.audit_data is None:
        st.warning("No Data")
        return

    # Metrics
    summ = st.session_state.summary
    m1, m2, m3, m4 = st.columns(4)
    
    def card(t, v, sub, is_im=False):
        c = "#0F172A"
        if is_im:
            val = float(str(v).replace(',','').replace('฿',''))
            c = "#EF4444" if val < 0 else "#10B981"
            sub = "▼ Overclaim" if val < 0 else "▲ Underclaim"
        st.markdown(f"""<div class="metric-card"><div class="metric-title">{t}</div><div class="metric-value" style="color:{c}">{v}</div><div class="metric-sub" style="color:{c}">{sub}</div></div>""", unsafe_allow_html=True)

    with m1: card("Records", f"{summ['records']:,}", "รายการทั้งหมด")
    with m2: card("Pre-Audit", f"{summ['pre_audit']:,.0f} ฿", "ยอดตั้งต้น")
    with m3: card("Post-Audit", f"{summ['post_audit']:,.0f} ฿", "ยอดหลังตรวจ")
    with m4: card("Impact", f"{summ['impact']:+,.0f} ฿", "", True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Tabs
    t1, t2, t3 = st.tabs(["ALL", "OPD", "IPD"])
    df = st.session_state.audit_data
    df['HN_AN'] = df.apply(lambda x: x['AN'] if x['TYPE']=='IPD' else x['HN'], axis=1)
    
    cfg = {
        "HN_AN": st.column_config.TextColumn("HN / AN", width="medium"),
        "FINDING": st.column_config.TextColumn("⚠️ Findings", width="large"),
        "ACTION": st.column_config.TextColumn("🔧 AI Action", width="large"),
        "IMPACT": st.column_config.NumberColumn("💰 Impact", format="%.0f ฿")
    }
    cols = ["HN_AN", "DATE", "PTTYPE", "FINDING", "ACTION", "IMPACT"]
    
    with t1: st.dataframe(df, column_order=cols, column_config=cfg, use_container_width=True, height=500, hide_index=True)
    with t2: st.dataframe(df[df['TYPE']=='OPD'], column_order=cols, column_config=cfg, use_container_width=True, height=500, hide_index=True)
    with t3: st.dataframe(df[df['TYPE']=='IPD'], column_order=cols, column_config=cfg, use_container_width=True, height=500, hide_index=True)

def chat_page():
    st.markdown(f"""
    <div style="display:flex; align-items:center; margin-bottom:20px;">
        {LOGO_HTML}
        <div>
            <h2 style="margin:0; color:#0F172A;">AI Consultant</h2>
            <p style="margin:0; color:#64748B;">ผู้ช่วยอัจฉริยะ</p>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")

    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if prompt := st.chat_input("พิมพ์คำถามปรึกษา AI..."):
        st.session_state.chat_history.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.spinner("AI กำลังคิด..."):
            time.sleep(1)
            response = get_ai_response(prompt)
            
        st.session_state.chat_history.append({"role": "assistant", "content": response})
        with st.chat_message("assistant"):
            st.markdown(response)

# --- 8. Main Router ---
def main():
    apply_theme()
    
    with st.sidebar:
        st.markdown(LOGO_HTML, unsafe_allow_html=True)
        st.markdown("### SMART Audit AI")
        if st.session_state.logged_in:
            st.markdown(f"User: **{st.session_state.username}**")
            st.markdown("---")
            if st.button("📊 Dashboard"):
                st.session_state.current_page = "dashboard"
                st.rerun()
            if st.button("💬 AI Consultant"):
                st.session_state.current_page = "chat"
                st.rerun()
            if st.button("📤 Upload Data"):
                st.session_state.current_page = "upload"
                st.rerun()
            st.markdown("<br><br>", unsafe_allow_html=True)
            if st.button("Log out"):
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
