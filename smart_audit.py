import streamlit as st
import pandas as pd
import numpy as np
import time
import os
import logging
from datetime import datetime

# --- 1. Config & Setup ---
st.set_page_config(page_title="SMART Audit AI - โรงพยาบาลพระนารายณ์มหาราช", page_icon="🏥", layout="wide")
logging.basicConfig(format='%(asctime)s - %(message)s', level=logging.INFO)

# --- 2. CSS Styling (Blue/White Theme) ---
def apply_theme():
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@300;400;600&display=swap');
        
        html, body, [class*="css"] {
            font-family: 'Sarabun', sans-serif;
        }
        
        /* พื้นหลังสีฟ้าอ่อน ไล่เฉดขาว */
        .stApp {
            background: linear-gradient(180deg, #F0F8FF 0%, #FFFFFF 100%);
        }
        
        /* Header Text */
        .hospital-name {
            color: #1565C0; /* สีน้ำเงินเข้ม */
            font-size: 28px;
            font-weight: bold;
            margin-bottom: 0px;
        }
        .app-name {
            color: #424242;
            font-size: 20px;
            font-weight: normal;
            margin-top: -5px;
            margin-bottom: 20px;
        }

        /* Metric Cards */
        div[data-testid="metric-container"] {
            background-color: #FFFFFF;
            border: 1px solid #E3F2FD;
            border-radius: 10px;
            padding: 15px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
            text-align: center;
        }
        label[data-testid="stMetricLabel"] {
            font-size: 16px;
            color: #546E7A;
        }
        div[data-testid="stMetricValue"] {
            font-size: 24px;
            color: #0D47A1;
        }
        </style>
    """, unsafe_allow_html=True)

# --- 3. Session State ---
if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'username' not in st.session_state: st.session_state.username = ""
if 'audit_data' not in st.session_state: st.session_state.audit_data = None
if 'financial_summary' not in st.session_state: st.session_state.financial_summary = {}
if 'current_page' not in st.session_state: st.session_state.current_page = "login"

# --- 4. Logic Functions ---

def get_logo():
    # ใช้ URL โลโก้จริง (หากลิงก์เสียจะใช้ Placeholder)
    return "https://upload.wikimedia.org/wikipedia/th/f/f6/Phranaraimaharaj_Hospital_Logo.png"

LOGO_URL = get_logo()

def process_52_files(uploaded_files):
    details_list = []
    total_records = 0
    pre_audit_sum = 0
    
    # UI Progress
    progress_bar = st.progress(0)
    status_text = st.empty()
    total_files = len(uploaded_files)

    for idx, file in enumerate(uploaded_files):
        # Update Progress
        prog = (idx + 1) / total_files
        progress_bar.progress(prog)
        status_text.text(f"กำลังประมวลผลไฟล์: {file.name}")

        try:
            # อ่านไฟล์ (รองรับภาษาไทย)
            try:
                content = file.read().decode('TIS-620')
            except:
                file.seek(0)
                content = file.read().decode('utf-8', errors='replace')

            lines = content.splitlines()
            if len(lines) < 2: continue

            # แยก Header และ Data
            sep = '|' if '|' in lines[0] else ','
            header = [h.strip().upper() for h in lines[0].strip().split(sep)]
            rows = [line.strip().split(sep) for line in lines[1:] if line.strip()]
            
            df = pd.DataFrame(rows)
            # ปรับ Column ให้ตรง Header
            if df.shape[1] > len(header): df = df.iloc[:, :len(header)]
            if df.shape[1] == len(header): df.columns = header
            else: continue # ข้ามถ้าโครงสร้างผิด

            total_records += len(df)
            file_upper = file.name.upper()

            # --- Logic การตรวจสอบ ---
            
            # 1. ตรวจสอบ DIAGNOSIS (หา DIAGCODE ว่าง)
            if 'DIAG' in file_upper or 'IPDX' in file_upper or 'OPDX' in file_upper:
                col_diag = 'DIAGCODE' if 'DIAGCODE' in df.columns else 'DIAG'
                if col_diag in df.columns:
                    # Filter แถวที่ไม่มีรหัสโรค
                    errors = df[df[col_diag] == '']
                    for _, row in errors.iterrows():
                        is_ipd = 'IPD' in file_upper
                        hn = row.get('HN', '-')
                        an = row
