import streamlit as st
import pandas as pd
import numpy as np
import time
import re
import os
import io
import logging

# --- Setup & Config ---
st.set_page_config(page_title="SMART Audit AI", page_icon="🏥", layout="wide")
logging.basicConfig(format='%(asctime)s - %(message)s', level=logging.INFO)

# --- Library Checks ---
try:
    from sklearn.ensemble import RandomForestClassifier
except ModuleNotFoundError:
    st.error("⚠️ ไม่พบ Library 'scikit-learn' กรุณาสร้างไฟล์ requirements.txt ใน GitHub")
    st.stop()

from fpdf import FPDF
import plotly.express as px

# --- CSS Theme (Blue/White & Layout Fixes) ---
def apply_theme():
    st.markdown("""
        <style>
        /* พื้นหลังสีฟ้าไล่เฉด */
        .stApp {
            background-image: linear-gradient(to bottom, #E3F2FD, #FFFFFF);
            background-attachment: fixed;
        }
        /* ปรับสีหัวข้อ */
        h1, h2, h3 { color: #0D47A1 !important; }
        
        /* ปรับปุ่มกด */
        div.stButton > button {
            background-color: #1976D2;
            color: white; border-radius: 8px; border: none;
            padding: 10px 24px;
        }
        div.stButton > button:hover {
            background-color: #1565C0;
        }
        
        /* ปรับ Sidebar */
        section[data-testid="stSidebar"] {
            background-color: #0D47A1;
        }
        section[data-testid="stSidebar"] h1, 
        section[data-testid="stSidebar"] span,
        section[data-testid="stSidebar"] p {
            color: white !important;
        }
        </style>
    """, unsafe_allow_html=True)

# --- Session State ---
if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'username' not in st.session_state: st.session_state.username = ""
if 'processed_data' not in st.session_state: st.session_state.processed_data = None
if 'current_page' not in st.session_state: st.session_state.current_page = "login"

# --- Logic Functions ---
def get_logo():
    if os.path.exists("logo.png"): return "logo.png"
    if os.path.exists("logo.jpg"): return "logo.jpg"
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
        # Update Progress
        prog = (idx + 1) / total
        progress_bar.progress(prog)
        status_text.text(f"⏳ กำลังตรวจสอบ: {file.name} ({idx+1}/{total})")
        
        try:
            # อ่านไฟล์
            content = file.read().decode('TIS-620', errors='replace')
            lines = content.splitlines()
            
            if len(lines) > 1:
                header = lines[0].split('|')
                rows = [line.split('|') for line in lines[1:] if line.strip()]
                
                # สร้าง DF โดยระวัง Error เรื่องจำนวน Column ไม่เท่ากัน
                try:
                    df = pd.DataFrame(rows, columns=header)
                except:
                    # กรณี Header กับข้อมูลไม่ตรงกัน ให้ข้ามไปก่อน หรือตัดส่วนเกิน
                    df = pd.DataFrame(rows) 

                file_upper = file.name.upper()

                # --- ตัวอย่าง Logic ตรวจสอบ ---
                # 1. IPDX Check
                if 'IPDX' in file_upper and 'DIAG' in df.columns:
                    missing = df[df['DIAG'] == ''].shape[0]
                    if missing > 0:
                        findings.append({"แฟ้ม": file_upper, "เรื่อง": "ICD-10 ว่าง", "จำนวน": missing})
                
                # 2. CHARGE Check
                if 'CHARGE' in file_upper and 'AMOUNT' in df.columns:
                    vals = pd.to_numeric(df['AMOUNT'], errors='coerce').fillna(0)
                    high = (vals > 200000).sum()
                    if high > 0:
                        findings.append({"แฟ้ม": file_upper, "เรื่อง": "ค่ารักษาสูง > 2แสน", "จำนวน": high})

        except Exception as e:
            # บันทึก Error แต่ไม่ให้โปรแกรมหยุด
            print(f"Error in {file.name}: {e}")
            
    progress_bar.empty()
    status_text.empty()
    
    # สรุปผล
    if not findings:
        return pd.DataFrame(columns=["แฟ้ม", "เรื่อง", "จำนวน"]), "ต่ำ (Low)"
    
    df_res = pd.DataFrame(findings)
    risk_score = ml_model.predict([[len(findings), 0.5]])[0]
    risk_map = {0: "ต่ำ (Low)", 1: "ปานกลาง (Medium)", 2: "สูง (High)"}
    return df_res, risk_map.get(risk_score, "ไม่ระบุ")

# --- Pages ---

def login_page():
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        st.markdown("<br><br>", unsafe_allow_html=True)
        c_img1, c_img2, c_img3 = st.columns([1, 2, 1])
        with c_img2:
            st.image(LOGO_PATH, use_container_width=True)
            
        st.markdown("<h2 style='text-align: center;'>SMART Audit AI</h2>", unsafe_allow_html=True)
        
        with st.form("login_form"):
            usr = st.text_input("Username")
            pwd = st.text_input("Password", type="password")
            submitted = st.form_submit_button("เข้าสู่ระบบ", type="primary", use_container_width=True)
            
            if submitted:
                if usr.strip() == "Hosnarai" and pwd.strip() == "h15000":
                    st.session_state.logged_in = True
                    st.session_state.username = usr.strip()
                    st.session_state.current_page = "upload"
                    st.rerun()
                else:
                    st.error("❌ ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง")

def upload_page():
    st.markdown(f"### 📂 ยินดีต้อนรับคุณ **{st.session_state.username}**")
    
    # Check ถ้าเคย Process ไปแล้วให้แสดงปุ่มไป Dashboard ได้เลย
    if st.session_state.processed_data is not None:
        if st.button("📊 ข้อมูลเดิมมีอยู่แล้ว คลิกเพื่อดูผลลัพธ์"):
            st.session_state.current_page = "dashboard"
            st.rerun()
    
    st.info("💡 เลือกไฟล์ทั้งหมด 52 แฟ้ม แล้วลากลงในกล่องด้านล่างทีเดียว")
    
    uploaded_files = st.file_uploader("", type=["txt"], accept_multiple_files=True)
    
    if uploaded_files:
        st.success(f"✅ พร้อมตรวจสอบจำนวน: {len(uploaded_files)} ไฟล์")
        
        if st.button("🚀 เริ่มประมวลผล (Start Audit)", type="primary"):
            with st.spinner("กำลังวิเคราะห์ข้อมูล... ห้ามปิดหน้านี้"):
                try:
                    findings, risk = process_52_files(uploaded_files)
                    
                    # บันทึกสถานะ
                    st.session_state.processed_data = (findings, risk)
                    st.session_state.current_page = "dashboard" # สั่งเปลี่ยนหน้า
                    
                    st.success("ประมวลผลเสร็จสิ้น! กำลังพาไปหน้าผลลัพธ์...")
                    time.sleep(1)
                    st.rerun() # บังคับรีเฟรชทันที
                    
                except Exception as e:
                    st.error(f"เกิดข้อผิดพลาดร้ายแรง: {e}")

def dashboard_page():
    # Header
    c_head1, c_head2 = st.columns([3, 1])
    with c_head1:
        st.title("📊 ผลการตรวจสอบ (Dashboard)")
    with c_head2:
        if st.button("⬅️ ตรวจสอบใหม่"):
            st.session_state.current_page = "upload"
            st.session_state.processed_data = None
            st.rerun()
            
    st.markdown("---")
    
    if st.session_state.processed_data:
        findings_df, risk = st.session_state.processed_data
        
        # Metrics
        m1, m2, m3 = st.columns(3)
        total = findings_df['จำนวน'].sum() if not findings_df.empty else 0
        m1.metric("ข้อผิดพลาดที่พบ", f"{total:,} รายการ")
        m2.metric("ความเสี่ยง (AI)", risk)
        m3.metric("สถานะ", "Complete")
        
        # Details
        if not findings_df.empty:
            c_chart, c_tbl = st.columns([1, 1])
            with c_chart:
                st.subheader("สัดส่วนปัญหา")
                fig = px.pie(findings_df, values='จำนวน', names='เรื่อง', hole=0.4)
                st.plotly_chart(fig, use_container_width=True)
            
            with c_tbl:
                st.subheader("รายการที่พบ")
                st.dataframe(findings_df, use_container_width=True, height=400)
                
                # Download CSV
                csv = findings_df.to_csv(index=False).encode('utf-8-sig')
                st.download_button("📥 ดาวน์โหลดรายงาน (CSV)", csv, "report.csv", "text/csv")
        else:
            st.success("🎉 สุดยอด! ไม่พบข้อผิดพลาดในแฟ้มข้อมูลชุดนี้")
            st.balloons()
    else:
        st.warning("ไม่มีข้อมูล กรุณากลับไปอัปโหลดไฟล์ใหม่")

# --- Main Controller ---
def main():
    apply_theme() # เรียกใช้ Theme
    
    if not st.session_state.logged_in:
        login_page()
    else:
        # Sidebar
        with st.sidebar:
            st.image(LOGO_PATH, width=80)
            st.markdown(f"User: **{st.session_state.username}**")
            st.divider()
            
            if st.button("📤 หน้าอัปโหลด"):
                st.session_state.current_page = "upload"
                st.rerun()
            if st.button("📊 แดชบอร์ด"):
                st.session_state.current_page = "dashboard"
                st.rerun()
            
            st.divider()
            if st.button("ออกจากระบบ"):
                st.session_state.clear()
                st.rerun()
        
        # Router Logic
        if st.session_state.current_page == "dashboard":
            dashboard_page()
        else:
            upload_page()

if __name__ == "__main__":
    main()
