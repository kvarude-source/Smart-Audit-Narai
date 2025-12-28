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

# --- CSS Theme (Blue/White) ---
def apply_theme():
    st.markdown("""
        <style>
        .stApp { background-image: linear-gradient(to bottom, #E3F2FD, #FFFFFF); background-attachment: fixed; }
        h1, h2, h3 { color: #0D47A1 !important; }
        div.stButton > button { background-color: #1976D2; color: white; border-radius: 8px; border: none; padding: 10px 24px; }
        div.stButton > button:hover { background-color: #1565C0; }
        section[data-testid="stSidebar"] { background-color: #0D47A1; }
        section[data-testid="stSidebar"] h1, section[data-testid="stSidebar"] span, section[data-testid="stSidebar"] p { color: white !important; }
        /* Cards */
        .metric-card { background-color: white; padding: 20px; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); text-align: center; }
        </style>
    """, unsafe_allow_html=True)

# --- Session State ---
if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'username' not in st.session_state: st.session_state.username = ""
if 'processed_data' not in st.session_state: st.session_state.processed_data = None
if 'debug_logs' not in st.session_state: st.session_state.debug_logs = []
if 'current_page' not in st.session_state: st.session_state.current_page = "login"

# --- Logic Functions ---
def get_logo():
    # ลำดับการหา: ไฟล์ png -> jpg -> ลิงก์สำรอง
    if os.path.exists("logo.png"): return "logo.png"
    if os.path.exists("logo.jpg"): return "logo.jpg"
    return "https://via.placeholder.com/150/006400/FFD700?text=SMART+Audit"

LOGO_PATH = get_logo()

def process_52_files(uploaded_files):
    findings = []
    logs = []
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    total = len(uploaded_files)
    
    # Dummy Model
    ml_model = RandomForestClassifier(n_estimators=10)
    ml_model.fit(np.random.rand(10, 2), np.random.choice([0, 1], 10))

    for idx, file in enumerate(uploaded_files):
        prog = (idx + 1) / total
        progress_bar.progress(prog)
        status_text.text(f"⏳ กำลังตรวจสอบ: {file.name}")
        
        try:
            # อ่านไฟล์ (รองรับ TIS-620 และ UTF-8)
            try:
                content = file.read().decode('TIS-620')
            except UnicodeDecodeError:
                file.seek(0)
                content = file.read().decode('utf-8', errors='replace')
                logs.append(f"⚠️ {file.name}: ใช้ UTF-8 แทน TIS-620")

            lines = content.splitlines()
            if len(lines) > 1:
                sep = '|' if '|' in lines[0] else ','
                header = [h.strip().upper() for h in lines[0].strip().split(sep)]
                rows = [line.strip().split(sep) for line in lines[1:] if line.strip()]
                
                df = pd.DataFrame(rows)
                
                # ปรับ Header ให้ตรง
                if df.shape[1] == len(header):
                    df.columns = header
                else:
                    df = df.iloc[:, :len(header)]
                    df.columns = header[:df.shape[1]]

                file_upper = file.name.upper()
                row_cnt = len(df)
                
                # --- แก้ไขจุดที่ Error ตรงนี้ครับ ---
                col_preview = str(list(df.columns[:5]))
                logs.append(f"✅ {file.name}: อ่านได้ {row_cnt} บรรทัด | Cols: {col_preview}")

                # --- กฎการตรวจสอบ (Updated) ---
                
                # 1. แฟ้ม DIAGNOSIS (วินิจฉัยโรค)
                if 'DIAGNOSIS' in file_upper or 'IPDX' in file_upper or 'OPDX' in file_upper:
                    target_col = 'DIAGCODE' if 'DIAGCODE' in df.columns else 'DIAG'
                    
                    if target_col in df.columns:
                        missing = df[df[target_col] == ''].shape[0]
                        if missing > 0:
                            findings.append({"แฟ้ม": file.name, "เรื่อง": f"รหัสโรค ({target_col}) ว่าง", "จำนวน": missing})
                    else:
                        logs.append(f"❌ {file.name}: ไม่พบคอลัมน์ DIAGCODE หรือ DIAG")

                # 2. แฟ้ม PROCEDURE (หัตถการ)
                elif 'PROCEDURE' in file_upper or 'OOP' in file_upper:
                    if 'PROCEDCODE' in df.columns:
                        missing = df[df['PROCEDCODE'] == ''].shape[0]
                        if missing > 0:
                            findings.append({"แฟ้ม": file.name, "เรื่อง": "รหัสหัตถการ (PROCEDCODE) ว่าง", "จำนวน": missing})
                    else:
                        logs.append(f"❌ {file.name}: ไม่พบคอลัมน์ PROCEDCODE")

                # 3. แฟ้ม DRUG (ยา)
                elif 'DRUG' in file_upper:
                    if 'DIDSTD' in df.columns:
                        missing = df[df['DIDSTD'] == ''].shape[0]
                        if missing > 0:
                            findings.append({"แฟ้ม": file.name, "เรื่อง": "รหัสยามาตรฐาน (DIDSTD) ว่าง", "จำนวน": missing})
                    else:
                        logs.append(f"❌ {file.name}: ไม่พบคอลัมน์ DIDSTD")

                # 4. แฟ้ม CHARGE (ค่าใช้จ่าย)
                elif 'CHARGE' in file_upper or 'CHA' in file_upper:
                    price_col = None
                    for c in ['PRICE', 'COST', 'AMOUNT', 'TOTAL']:
                        if c in df.columns:
                            price_col = c
                            break
                    
                    if price_col:
                        vals = pd.to_numeric(df[price_col], errors='coerce').fillna(0)
                        high_cost = (vals > 100000).sum()
                        zero_cost = (vals == 0).sum()
                        
                        if high_cost > 0:
                            findings.append({"แฟ้ม": file.name, "เรื่อง": f"ค่ารักษาสูงผิดปกติ (>100,000)", "จำนวน": high_cost})
                        if zero_cost > 0:
                            findings.append({"แฟ้ม": file.name, "เรื่อง": f"ค่ารักษาเป็น 0 ({price_col})", "จำนวน": zero_cost})
                    else:
                        logs.append(f"❌ {file.name}: ไม่พบคอลัมน์ PRICE/COST")

            else:
                logs.append(f"⚠️ {file.name}: ไฟล์ว่างเปล่า")

        except Exception as e:
            logs.append(f"❌ Error {file.name}: {str(e)}")
            
    progress_bar.empty()
    status_text.empty()
    
    # สรุปผล
    risk_label = "ต่ำ (Low)"
    total_issues = sum([f['จำนวน'] for f in findings])
    if total_issues > 100: risk_label = "สูง (High)"
    elif total_issues > 0: risk_label = "ปานกลาง (Medium)"
        
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
         if st.button("📊 ข้อมูลเดิมมีอยู่แล้ว คลิกเพื่อดูผลลัพธ์"):
             st.session_state.current_page = "dashboard"
             st.rerun()

    st.info("💡 ลากไฟล์ 52 แฟ้มมาวางที่นี่ (ระบบจะตรวจสอบรหัสโรค, ยา, ค่ารักษา อัตโนมัติ)")
    files = st.file_uploader("", type=["txt"], accept_multiple_files=True)
    
    if files:
        st.success(f"✅ พร้อมตรวจสอบ: {len(files)} ไฟล์")
        if st.button("🚀 เริ่มตรวจสอบ (Start Audit)", type="primary"):
            with st.spinner("AI กำลังวิเคราะห์ข้อมูล..."):
                findings, risk, logs = process_52_files(files)
                st.session_state.processed_data = (findings, risk)
                st.session_state.debug_logs = logs
                st.session_state.current_page = "dashboard"
                time.sleep(0.5)
                st.rerun()

def dashboard_page():
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
        
        # Metrics Cards
        m1, m2, m3 = st.columns(3)
        count = findings['จำนวน'].sum() if not findings.empty else 0
        m1.metric("ข้อผิดพลาดที่พบ", f"{count:,}")
        m2.metric("ระดับความเสี่ยง", risk)
        m3.metric("สถานะ", "เสร็จสิ้น")
        
        # Display Data
        if not findings.empty:
            c_chart, c_tbl = st.columns([1, 1])
            with c_chart:
                fig = px.pie(findings, values='จำนวน', names='แฟ้ม', title="สัดส่วนปัญหาแยกตามแฟ้ม")
                st.plotly_chart(fig, use_container_width=True)
            with c_tbl:
                st.write("#### รายการที่พบปัญหา")
                st.dataframe(findings, use_container_width=True, height=350)
                
                csv = findings.to_csv(index=False).encode('utf-8-sig')
                st.download_button("📥 ดาวน์โหลดรายงาน (CSV)", csv, "audit_report.csv", "text/csv")
        else:
            st.success("🎉 ไม่พบข้อผิดพลาด! ข้อมูลสมบูรณ์ตามกฎที่ตั้งไว้")
            
        # Debug Logs
        st.markdown("<br>", unsafe_allow_html=True)
        with st.expander("🛠️ ดู Log การทำงานละเอียด (คลิก)"):
            for log in st.session_state.debug_logs:
                if "❌" in log: st.error(log)
                elif "✅" in log: st.success(log)
                else: st.text(log)
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
