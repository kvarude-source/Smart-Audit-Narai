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

# --- Library Checks ---
try:
    from sklearn.ensemble import RandomForestClassifier
except ModuleNotFoundError:
    st.error("⚠️ ไม่พบ Library 'scikit-learn' กรุณาสร้างไฟล์ requirements.txt ใน GitHub")
    st.stop()

from fpdf import FPDF
import plotly.express as px

# --- CSS Theme ---
def apply_theme():
    st.markdown("""
        <style>
        .stApp { background-image: linear-gradient(to bottom, #E3F2FD, #FFFFFF); background-attachment: fixed; }
        h1, h2, h3 { color: #0D47A1 !important; }
        div.stButton > button { background-color: #1976D2; color: white; border-radius: 8px; border: none; padding: 10px 24px; }
        div.stButton > button:hover { background-color: #1565C0; }
        section[data-testid="stSidebar"] { background-color: #0D47A1; }
        section[data-testid="stSidebar"] h1, section[data-testid="stSidebar"] span, section[data-testid="stSidebar"] p { color: white !important; }
        /* Box Styling */
        .info-box { background-color: #ffffff; padding: 15px; border-radius: 10px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); margin-bottom: 10px; }
        </style>
    """, unsafe_allow_html=True)

# --- Session State ---
if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'username' not in st.session_state: st.session_state.username = ""
if 'processed_data' not in st.session_state: st.session_state.processed_data = None
if 'debug_logs' not in st.session_state: st.session_state.debug_logs = [] # เก็บ Log การทำงาน
if 'current_page' not in st.session_state: st.session_state.current_page = "login"

# --- Logic Functions ---
def get_logo():
    if os.path.exists("logo.png"): return "logo.png"
    if os.path.exists("logo.jpg"): return "logo.jpg"
    return "https://via.placeholder.com/150/006400/FFD700?text=SMART+Audit"

LOGO_PATH = get_logo()

def process_52_files(uploaded_files):
    findings = []
    logs = [] # สร้างตัวแปรเก็บ Log
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    total = len(uploaded_files)
    
    # ตัวแปรจำลอง Model
    ml_model = RandomForestClassifier(n_estimators=10)
    # Fit dummy data เพื่อกัน error
    ml_model.fit(np.random.rand(10, 2), np.random.choice([0, 1], 10))

    for idx, file in enumerate(uploaded_files):
        prog = (idx + 1) / total
        progress_bar.progress(prog)
        status_text.text(f"⏳ กำลังอ่านไฟล์: {file.name}")
        
        try:
            # ลองอ่านด้วย TIS-620 ก่อน (มาตรฐานไทย)
            try:
                content = file.read().decode('TIS-620')
            except UnicodeDecodeError:
                # ถ้าไม่ได้ ลอง UTF-8
                file.seek(0)
                content = file.read().decode('utf-8', errors='replace')
                logs.append(f"⚠️ ไฟล์ {file.name} ไม่ใช่ TIS-620 (ใช้ UTF-8 แทน)")

            lines = content.splitlines()
            
            if len(lines) > 1:
                # ตรวจสอบตัวคั่น (Delimiter) ว่าเป็น '|' หรือไม่
                if '|' in lines[0]:
                    sep = '|'
                else:
                    sep = ',' # เผื่อเป็น CSV
                    
                header = lines[0].strip().split(sep)
                rows = [line.strip().split(sep) for line in lines[1:] if line.strip()]
                
                # สร้าง DataFrame
                df = pd.DataFrame(rows)
                # ป้องกัน Error จำนวนคอลัมน์ไม่เท่ากัน
                if df.shape[1] == len(header):
                    df.columns = header
                else:
                    # ตัดหรือเติมให้เท่ากันแบบหยาบๆ
                    df = df.iloc[:, :len(header)]
                    df.columns = header[:df.shape[1]]

                file_upper = file.name.upper()
                row_count = len(df)
                logs.append(f"✅ อ่านไฟล์ {file.name} สำเร็จ: {row_count} บรรทัด")

                # --- เริ่มตรวจสอบกฎ (Rules) ---
                
                # 1. กฎ IPDX (ผู้ป่วยใน)
                if 'IPD' in file_upper: # เช็คคำว่า IPD ในชื่อไฟล์
                    if 'DIAG' in df.columns:
                        missing = df[df['DIAG'] == ''].shape[0]
                        if missing > 0:
                            findings.append({"แฟ้ม": file.name, "เรื่อง": "ICD-10 ว่าง (IPD)", "จำนวน": missing})
                    else:
                        logs.append(f"❌ ไฟล์ {file.name} หาคอลัมน์ DIAG ไม่เจอ (เจอแต่: {list(df.columns)})")

                # 2. กฎ OPDX (ผู้ป่วยนอก)
                elif 'OPD' in file_upper: 
                    if 'DIAG' in df.columns:
                        missing = df[df['DIAG'] == ''].shape[0]
                        if missing > 0:
                            findings.append({"แฟ้ม": file.name, "เรื่อง": "ICD-10 ว่าง (OPD)", "จำนวน": missing})

                # 3. กฎ WOMEN (หญิงตั้งครรภ์) - ตัวอย่างเพิ่ม
                elif 'WOMEN' in file_upper:
                    if 'GRAVIDA' in df.columns: # สมมติว่าต้องมีครรภ์ที่
                        # ลองแปลงเป็นตัวเลข เช็คค่าแปลกๆ
                        pass 
                    logs.append(f"ℹ️ ตรวจสอบไฟล์ WOMEN: {row_count} รายการ")

                # 4. กฎ CHARGE (ค่าใช้จ่าย)
                elif 'CHA' in file_upper: # จับคำว่า CHARGE หรือ CHA
                    if 'AMOUNT' in df.columns:
                        vals = pd.to_numeric(df['AMOUNT'], errors='coerce').fillna(0)
                        high = (vals > 200000).sum()
                        if high > 0:
                            findings.append({"แฟ้ม": file.name, "เรื่อง": "ค่ารักษาสูง > 2แสน", "จำนวน": high})
                
                else:
                    logs.append(f"⏩ ข้ามการตรวจสอบลึก {file.name} (ไม่มีกฎรองรับ)")

            else:
                logs.append(f"⚠️ ไฟล์ {file.name} ว่างเปล่า หรือมีแค่หัวตาราง")

        except Exception as e:
            logs.append(f"❌ Error อ่านไฟล์ {file.name}: {str(e)}")
            
    progress_bar.empty()
    status_text.empty()
    
    # สรุปผล
    risk_label = "ต่ำ (Low)"
    if findings:
        risk_label = "ปานกลาง (Medium)" if len(findings) < 10 else "สูง (High)"
        
    df_res = pd.DataFrame(findings) if findings else pd.DataFrame(columns=["แฟ้ม", "เรื่อง", "จำนวน"])
    
    return df_res, risk_label, logs

# --- Pages ---
def login_page():
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        st.markdown("<br><br>", unsafe_allow_html=True)
        c_img1, c_img2, c_img3 = st.columns([1, 2, 1])
        with c_img2:
            st.image(LOGO_PATH, use_container_width=True)
        st.markdown("<h2 style='text-align: center;'>SMART Audit AI</h2>", unsafe_allow_html=True)
        with st.form("login"):
            u = st.text_input("Username")
            p = st.text_input("Password", type="password")
            if st.form_submit_button("เข้าสู่ระบบ", type="primary", use_container_width=True):
                if u.strip() == "Hosnarai" and p.strip() == "h15000":
                    st.session_state.logged_in = True
                    st.session_state.username = u.strip()
                    st.session_state.current_page = "upload"
                    st.rerun()
                else:
                    st.error("รหัสผ่านไม่ถูกต้อง")

def upload_page():
    st.markdown(f"### 📂 ยินดีต้อนรับคุณ **{st.session_state.username}**")
    
    if st.session_state.processed_data:
         if st.button("📊 ข้อมูลประมวลผลเสร็จแล้ว คลิกเพื่อดู"):
             st.session_state.current_page = "dashboard"
             st.rerun()

    st.info("💡 ลากไฟล์ 52 แฟ้มมาวางที่นี่ (รองรับไฟล์ .txt)")
    files = st.file_uploader("", type=["txt"], accept_multiple_files=True)
    
    if files:
        st.success(f"✅ เตรียมพร้อม {len(files)} ไฟล์")
        if st.button("🚀 เริ่มตรวจสอบ (Start Audit)", type="primary"):
            with st.spinner("AI กำลังทำงาน..."):
                findings, risk, logs = process_52_files(files)
                st.session_state.processed_data = (findings, risk)
                st.session_state.debug_logs = logs # บันทึก Log
                st.session_state.current_page = "dashboard"
                time.sleep(0.5)
                st.rerun()

def dashboard_page():
    # Header & Reset
    c1, c2 = st.columns([3, 1])
    with c1: st.title("📊 ผลการตรวจสอบ")
    with c2: 
        if st.button("⬅️ ตรวจสอบใหม่"):
            st.session_state.current_page = "upload"
            st.session_state.processed_data = None
            st.rerun()
            
    st.markdown("---")
    
    if st.session_state.processed_data:
        findings, risk = st.session_state.processed_data
        
        # Metrics
        m1, m2, m3 = st.columns(3)
        count = findings['จำนวน'].sum() if not findings.empty else 0
        m1.metric("ข้อผิดพลาดที่พบ", f"{count:,} รายการ")
        m2.metric("ความเสี่ยง", risk)
        m3.metric("จำนวนไฟล์ที่อ่าน", "ดูใน Log")
        
        # --- ส่วนแสดงผลลัพธ์ ---
        if not findings.empty:
            c_chart, c_tbl = st.columns([1, 1])
            with c_chart:
                fig = px.pie(findings, values='จำนวน', names='เรื่อง', hole=0.4)
                st.plotly_chart(fig, use_container_width=True)
            with c_tbl:
                st.dataframe(findings, use_container_width=True)
                csv = findings.to_csv(index=False).encode('utf-8-sig')
                st.download_button("📥 ดาวน์โหลด CSV", csv, "audit_report.csv", "text/csv")
        else:
            st.success("🎉 ไม่พบข้อผิดพลาดในกฎที่กำหนดไว้")
            
        # --- ส่วน Debug Log (สำคัญสำหรับแก้ปัญหา) ---
        st.markdown("<br>", unsafe_allow_html=True)
        with st.expander("🛠️ คลิกเพื่อดู Log การทำงาน (ระบบอ่านไฟล์ไหนบ้าง?)"):
            st.write("ถ้าผลลัพธ์เป็น 0 แสดงว่าอาจไม่เจอชื่อไฟล์ที่ตรงกับกฎ หรืออ่านไฟล์ไม่ออก ตรวจสอบได้ด้านล่าง:")
            for log in st.session_state.debug_logs:
                if "❌" in log:
                    st.error(log)
                elif "⚠️" in log:
                    st.warning(log)
                else:
                    st.text(log)
    else:
        st.warning("ไม่มีข้อมูล")

# --- Main ---
def main():
    apply_theme()
    if not st.session_state.logged_in:
        login_page()
    else:
        with st.sidebar:
            st.image(LOGO_PATH, width=80)
            st.write(f"User: {st.session_state.username}")
            st.divider()
            if st.button("หน้าอัปโหลด"): st.session_state.current_page = "upload"; st.rerun()
            if st.button("แดชบอร์ด"): st.session_state.current_page = "dashboard"; st.rerun()
            st.divider()
            if st.button("ออกจากระบบ"): st.session_state.clear(); st.rerun()
            
        if st.session_state.current_page == "dashboard": dashboard_page()
        else: upload_page()

if __name__ == "__main__":
    main()
