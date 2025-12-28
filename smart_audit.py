import streamlit as st
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from datetime import datetime
import time
import io
import re
import plotly.express as px
from fpdf import FPDF
import logging
import os

# Setup logging
logging.basicConfig(filename='smart_audit.log', level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s')

# Session state initialization
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'username' not in st.session_state:
    st.session_state.username = ""
if 'findings_df' not in st.session_state:
    st.session_state.findings_df = None
if 'processed_data' not in st.session_state:
    st.session_state.processed_data = None

# Logo
LOGO_URL = "https://via.placeholder.com/150/006400/FFD700?text=PNH"

# ------------------- ML Model -------------------
def train_ml_model():
    np.random.seed(42)
    num_samples = 1000
    data = pd.DataFrame({
        'missing_icd10': np.random.randint(0, 2, num_samples),
        'missing_icd9cm': np.random.randint(0, 2, num_samples),
        'missing_drug': np.random.randint(0, 2, num_samples),
        'missing_proc': np.random.randint(0, 2, num_samples),
        'missing_lab': np.random.randint(0, 2, num_samples),
        'missing_disease': np.random.randint(0, 2, num_samples),
        'missing_right': np.random.randint(0, 2, num_samples),
        'icd_disease_mismatch': np.random.randint(0, 2, num_samples),
        'drug_proc_mismatch': np.random.randint(0, 2, num_samples),
        'lab_abnormal': np.random.randint(0, 2, num_samples),
        'icd9_proc_mismatch': np.random.randint(0, 2, num_samples),
        'icd10_format_invalid': np.random.randint(0, 2, num_samples),
        'icd10_duplicated': np.random.randint(0, 2, num_samples),
        'charge_amount': np.random.uniform(100, 20000, num_samples),
        'risk': np.random.choice([0, 1, 2], num_samples, p=[0.7, 0.25, 0.05])
    })
    X = data.drop('risk', axis=1)
    y = data['risk']
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    clf = RandomForestClassifier(n_estimators=200, max_depth=10, random_state=42)
    clf.fit(X_train, y_train)
    return clf

@st.cache_resource
def get_ml_model():
    return train_ml_model()

ml_model = get_ml_model()

# ------------------- Login Page -------------------
def login_page():
    st.markdown("""
        <style>
        .login-container { 
            text-align: center; 
            padding: 60px; 
            background: linear-gradient(135deg, #e3f2fd, #bbdefb); 
            border-radius: 15px; 
            box-shadow: 0 8px 16px rgba(0,0,0,0.15); 
            margin: 40px auto;
            max-width: 500px;
        }
        .copyright { text-align: center; margin-top: 50px; color: #666; font-size: 13px; }
        </style>
    """, unsafe_allow_html=True)

    st.image(LOGO_URL, width=180)
    st.markdown('<div class="login-container">', unsafe_allow_html=True)
    st.title("🔍 SMART Audit AI")
    st.subheader("ระบบตรวจสอบข้อมูล 52 แฟ้มด้วยปัญญาประดิษฐ์")

    username = st.text_input("👤 ชื่อผู้ใช้", placeholder="เช่น Hosnarai")
    password = st.text_input("🔒 รหัสผ่าน", type="password", placeholder="กรอกรหัสผ่าน")

    if st.button("เข้าสู่ระบบ", use_container_width=True, type="primary"):
        if username == "Hosnarai" and password == "h15000":
            st.session_state.logged_in = True
            st.session_state.username = username
            logging.info(f"Login success: {username}")
            st.success("เข้าสู่ระบบสำเร็จ!")
            time.sleep(1)
            st.rerun()
        else:
            st.error("ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง")
            logging.warning(f"Login failed attempt: {username}")

    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('<div class="copyright">© 2025 COMMIT - SMART Audit AI Version 1.0</div>', unsafe_allow_html=True)

# ------------------- File Processing & Rule Engine -------------------
def process_52_files(uploaded_files):
    all_dfs = {}
    total_records = 0
    
    progress_bar = st.progress(0)
    status_text = st.empty()

    for idx, file in enumerate(uploaded_files):
        try:
            content = file.read().decode('TIS-620', errors='replace')  # 52 แฟ้มส่วนใหญ่เป็น TIS-620
            lines = content.splitlines()
            if not lines:
                continue
            header = lines[0].split('|')
            data = [line.split('|') for line in lines[1:] if line.strip()]
            df = pd.DataFrame(data, columns=header)
            df = df.replace('', np.nan)
            
            file_name = file.name.upper()
            all_dfs[file_name] = df
            total_records += len(df)
            
        except Exception as e:
            st.error(f"ไม่สามารถอ่านไฟล์ {file.name}: {e}")
            return None, None

        progress = (idx + 1) / len(uploaded_files)
        progress_bar.progress(progress)
        status_text.text(f"กำลังโหลดไฟล์: {file.name} ({idx+1}/{len(uploaded_files)})")

    # ตัวอย่างการตรวจสอบ rule เบื้องต้น (สามารถเพิ่มได้มากกว่านี้)
    findings = []

    # ตัวอย่างไฟล์สำคัญ
    if 'IPDX.TXT' in all_dfs:
        ipdx = all_dfs['IPDX.TXT']
        missing_icd10 = ipdx['DIAG'].isna().sum()
        invalid_icd10 = ipdx['DIAG'].astype(str).apply(lambda x: bool(re.match(r'^[A-Z]\d{2}', x)) == False and pd.notna(x)).sum()
        findings.append({"ประเภทปัญหา": "ICD-10 หาย", "จำนวน": missing_icd10})
        findings.append({"ประเภทปัญหา": "รูปแบบ ICD-10 ไม่ถูกต้อง", "จำนวน": invalid_icd10})

    if 'CHARGE.TXT' in all_dfs:
        charge = all_dfs['CHARGE.TXT']
        charge['AMOUNT'] = pd.to_numeric(charge.get('AMOUNT', 0), errors='coerce')
        high_charge = (charge['AMOUNT'] > 100000).sum()
        findings.append({"ประเภทปัญหา": "ค่ารักษาสูงผิดปกติ (>100,000)", "จำนวน": high_charge})

    # เพิ่ม rule อื่น ๆ ได้ที่นี่...

    findings_df = pd.DataFrame(findings)
    
    # ML Risk Prediction (ตัวอย่าง)
    if not findings_df.empty:
        feature_vector = np.zeros((1, 14))
        feature_vector[0, 0] = 1 if "ICD-10 หาย" in findings_df['ประเภทปัญหา'].values else 0
        feature_vector[0, 11] = 1 if "รูปแบบ ICD-10 ไม่ถูกต้อง" in findings_df['ประเภทปัญหา'].values else 0
        feature_vector[0, 13] = findings_df['จำนวน'].sum() / 1000
        
        risk_pred = ml_model.predict(feature_vector)[0]
        risk_label = ["
