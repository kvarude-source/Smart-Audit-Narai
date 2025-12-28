import streamlit as st
import pandas as pd
import numpy as np
import time
import re
import os
import io
import logging

# ตรวจสอบ Library scikit-learn
try:
    from sklearn.ensemble import RandomForestClassifier
except ModuleNotFoundError:
    st.error("⚠️ ไม่พบ Library 'scikit-learn' กรุณาสร้างไฟล์ requirements.txt ใน GitHub")
    st.stop()

from fpdf import FPDF
import plotly.express as px

# ------------------- 1. Config & Setup -------------------
st.set_page_config(page_title="SMART Audit AI", page_icon="🏥", layout="wide")

# ตั้งค่า Logging
logging.basicConfig(format='%(asctime)s - %(message)s', level=logging.INFO)

# ------------------- 2. CSS Styling (Blue/White Theme) -------------------
def apply_theme():
    st.markdown("""
        <style>
        /* กำหนดพื้นหลังเป็นสีฟ้าอ่อนไล่เฉดขาว */
        .stApp {
            background-image: linear-gradient(to bottom, #E3F2FD, #FFFFFF);
            background-attachment: fixed;
        }
        
        /* ปรับสีหัวข้อให้เป็นสีน้ำเงินเข้ม */
        h1, h2, h3 {
            color: #0D47A1 !important;
        }
        
        /* ปรับแต่งปุ่มกด */
        div.stButton > button {
            background-color: #1976D2;
            color: white;
            border-radius: 8px;
        }
        div.stButton > button:hover {
            background-color: #1565C0;
            border-color: #0D47A1;
        }

        /* ปรับช่อง Input ให้ดูสะอาดตา */
        .stTextInput > div > div > input {
            background-color: #FFFFFF;
            border: 1px solid #90CAF9;
            color: #333333;
            border-radius: 5px;
        }
        
        /* ลบ Padding ด้านบนเพื่อให้ดูสมดุล */
        .block-container {
            padding-top: 2rem;
        }
        </style>
    """, unsafe_allow_html=True)

# ------------------- 3. Session State -------------------
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'username' not in st.session_state:
    st.session_state.username = ""
if 'processed_data' not in st.session_state:
    st.session_state.processed_data = None
if 'current_page' not in st.session_state:
    st.session_state.current_page = "login"

# ------------------- 4. Helper Functions -------------------
def get_logo():
    if os.path.exists("logo.png"): return "logo.png"
    elif os.path.exists("logo.jpg"): return "logo.jpg"
    return "https://via.placeholder.com/150/006400/FFD700?text=SMART+Audit"

LOGO_PATH = get_logo()

@st.cache_resource
def get_ml_model():
    np.random.seed(42)
    X = np.random.rand(100, 2)
    y = np.random.choice([0, 1, 2], 100)
    clf = RandomForestClassifier(n_estimators=10)
    clf.fit(X, y)
    return clf

ml_model = get_ml_model()

def process_52_files(uploaded_files):
    findings = []
    progress_bar = st.progress(0)
    status_text = st.empty()
    total = len(uploaded_files)
    
    for idx, file in enumerate(uploaded_files):
        prog = (idx + 1) / total
        progress_bar.progress(prog)
        status_text.text(f"Processing: {file.name}")
        
        try:
            content = file.read().decode('TIS-620', errors='replace')
            lines = content.splitlines()
            if len(lines) < 2: continue
            
            header = lines[0].split('|')
            data_rows = [line.split('|') for line in lines[1:] if line.strip()]
            df = pd.DataFrame(data_rows, columns=header)
            
            # Simple Logic Check
            if 'IPDX' in file.name.upper() and 'DIAG' in df.columns:
                missing = df[df['DIAG'] == ''].shape[0]
                if missing > 0:
                    findings.append({"แฟ้ม": file.name, "เรื่อง": "ICD-10 ว่าง", "จำนวน": missing})
                    
        except Exception:
            pass

    progress_bar.empty()
    status_text.empty()
    
    if not findings:
        return pd.DataFrame(columns=["แฟ้ม", "เรื่อง", "จำนวน"]), "ต่ำ (Low)"
    
    return pd.DataFrame(findings), "ปานกลาง (Medium)"

# ------------------- 5. Pages -------------------

def login_page():
    # จัด Layout: ใช้ Column บีบหน้าจอให้เนื้อหาอยู่ตรงกลางและไม่กว้างเกินไป
    # แบ่งอัตราส่วน 1 : 1 : 1 (เนื้อหาอยู่ตรงกลาง 1 ส่วน)
    col_left, col_center, col_right = st.columns([1, 1, 1]) 
    
    with col_center:
        st.markdown("<br><br>", unsafe_allow_html=True)
        
        # จัดโลโก้ให้อยู่ตรงกลาง (ใช้ Nested Columns เพื่อความชัวร์)
        c_logo_1, c_logo_2, c_logo_3 = st.columns([1, 2, 1])
        with c_logo_2:
            st.image(LOGO_PATH, use_container_width=True)

        # หัวข้อ
        st.markdown("<h1 style='text-align: center;'>SMART Audit AI</h1>", unsafe_allow_html=True)
        st.markdown("<h4 style='text-align: center; color: #546E7A;'>ระบบตรวจสอบเวชระเบียนอัจฉริยะ</h4>", unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)

        # ฟอร์ม Login (ไม่มีกล่องขาวพื้นหลังแล้ว)
        with st.form("login_form"):
            usr = st.text_input("Username")
            pwd = st.text_input("Password", type="password")
            
            st.markdown("<br>", unsafe_allow_html=True)
            submit = st.form_submit_button("เข้าสู่ระบบ", type="primary", use_container_width=True)
            
            if submit:
                if usr.strip() == "Hosnarai" and pwd.strip() == "h15000":
                    st.session_state.logged_in = True
                    st.session_state.username = usr.strip()
                    st.session_state.current_page = "upload"
                    st.rerun()
                else:
                    st.error("ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง")

def upload_page():
    st.markdown(f"### 📂 ยินดีต้อนรับคุณ **{st.session_state.username}**")
    st.info("💡 กรุณาเลือกไฟล์ 52 แฟ้มทั้งหมด แล้วลากลงในกล่องด้านล่างทีเดียว")
    
    uploaded_files = st.file_uploader("", type=["txt"], accept_multiple_files=True)
    
    if uploaded_files:
        st.success(f"พบไฟล์จำนวน: {len(uploaded_files)} ไฟล์")
        if st.button("🚀 เริ่มประมวลผล", type="primary"):
            with st.spinner("กำลังวิเคราะห์ข้อมูล..."):
                findings, risk = process_52_files(uploaded_files)
                st.session_state.processed_data = (findings, risk)
                st.session_state.current_page = "dashboard"
                time.sleep(0.5)
                st.rerun()

def dashboard_page():
    st.button("⬅️ ตรวจสอบใหม่", on_click=lambda: st.session_state.update(current_page="upload"))
    st.markdown("---")
    
    findings_df, risk = st.session_state.processed_data
    
    c1, c2, c3 = st.columns(3)
    total = findings_df['จำนวน'].sum() if not findings_df.empty else 0
    c1.metric("ข้อผิดพลาดที่พบ", f"{total:,}")
    c2.metric("ความเสี่ยง", risk)
    c3.metric("สถานะ", "✅ เสร็จสิ้น")
    
    if not findings_df.empty:
        c_chart, c_tbl = st.columns([1,1])
        with c_chart:
            fig = px.pie(findings_df, values='จำนวน', names='เรื่อง', title="สัดส่วนปัญหา")
            st.plotly_chart(fig, use_container_width=True)
        with c_tbl:
            st.dataframe(findings_df, use_container_width=True)
            csv = findings_df.to_csv(index=False).encode('utf-8-sig')
            st.download_button("📥 ดาวน์โหลด CSV", csv, "report.csv", "text/csv")
    else:
        st.success("ไม่พบข้อผิดพลาด")

# ------------------- 6. Main Controller -------------------
def main():
    apply_theme() # เรียกใช้ Theme สีฟ้าขาว
    
    if not st.session_state.logged_in:
        login_page()
    else:
        with st.sidebar:
            st.image(LOGO_PATH, width=80)
            st.write(f"User: {st.session_state.username}")
            st.divider()
            if st.button("ออกจากระบบ"):
                st.session_state.clear()
                st.rerun()
        
        if st.session_state.current_page == "upload":
            upload_page()
        elif st.session_state.current_page == "dashboard":
            dashboard_page()
        else:
            upload_page()

if __name__ == "__main__":
    main()
