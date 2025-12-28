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
logging.basicConfig(filename='smart_audit.log', level=logging.INFO, format='%(asctime)s - %(message)s')

# Session state
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'username' not in st.session_state:
    st.session_state.username = ""
if 'findings_df' not in st.session_state:
    st.session_state.findings_df = None

# Logo (เปลี่ยนเป็น URL โลโก้จริงของคุณ)
LOGO_URL = "https://via.placeholder.com/150/006400/FFD700?text=PNH"

# ML Model
def train_ml_model():
    np.random.seed(42)
    num_samples = 200
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
        'charge': np.random.randint(100, 5000, num_samples),
        'risk': np.random.choice([0, 1, 2], num_samples)
    })
    X = data.drop('risk', axis=1)
    y = data['risk']
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    clf = RandomForestClassifier(n_estimators=100, max_depth=15, random_state=42)
    clf.fit(X_train, y_train)
    return clf

@st.cache_resource
def get_ml_model():
    return train_ml_model()

ml_model = get_ml_model()

# Login Page
def login_page():
    st.markdown("""
        <style>
        .login-container { text-align: center; padding: 50px; background-color: #e6f7ff; border-radius: 10px; box-shadow: 0 4px 8px rgba(0,0,0,0.1); }
        .copyright { text-align: center; margin-top: 20px; color: #888; font-size: 12px; }
        </style>
    """, unsafe_allow_html=True)

    st.image(LOGO_URL, width=150)
    st.markdown('<div class="login-container">', unsafe_allow_html=True)
    st.header("เข้าสู่ระบบ SMART Audit AI")
    username = st.text_input("ชื่อผู้ใช้")
    password = st.text_input("รหัสผ่าน", type="password")
    if st.button("เข้าสู่ระบบ"):
        if username == "Hosnarai" and password == "h15000":
            st.session_state.logged_in = True
            st.session_state.username = username
            logging.info(f"Login success: {username}")
            st.rerun()
        else:
            st.error("ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง")
    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('<div class="copyright">Copyright: By COMMIT version 1.0</div>', unsafe_allow_html=True)

# Upload & Process
def upload_page():
    st.markdown("""
        <style>
        .upload-container { max-width: 700px; margin: auto; padding: 20px; background-color: #ffffff; border-radius: 10px; box-shadow: 0 4px 8px rgba(0,0,0,0.1); }
        </style>
    """, unsafe_allow_html=True)

    st.markdown('<div class="upload-container">', unsafe_allow_html=True)
    st.subheader("อัปโหลดไฟล์ข้อมูล 52 แฟ้ม (.txt)")
    uploaded_files = st.file_uploader("เลือกไฟล์ .txt ทั้งหมด 52 แฟ้ม", type="txt", accept_multiple_files=True)

    if st.button("เริ่มตรวจสอบ") and uploaded_files:
        if len(uploaded_files) != 52:
            st.error(f"กรุณาอัปโหลดครบ 52 แฟ้ม (ปัจจุบัน: {len(uploaded_files)} แฟ้ม)")
        else:
            progress_bar = st.progress(0)
            status_text = st.empty()
            all_data = []
            total_records = 0

            for idx, file in enumerate(uploaded_files):
                try:
                    content = file.read().decode('utf-8', errors='ignore')
                    lines = content.splitlines()
                    if lines:
                        header = lines[0].split('|')  # ปรับ sep ถ้าไม่ใช่ |
                        data = [line.split('|') for line in lines[1:]]
                        df = pd.DataFrame(data, columns=header)
                        all_data.append(df)
                        total_records += len(df)
                except Exception as e:
                    st.warning(f"ไฟล์ {file.name} มีปัญหา: {e}")

                progress = (idx + 1) / 52
                progress_bar.progress(progress)
                status_text.text(f"กำลังประมวลผลไฟล์ที่ {idx+1}/52 ({int(progress*100)}%)")
                time.sleep(0.05)

            if all_data:
                combined_df = pd.concat(all_data, ignore_index=True)
                combined_df['Charge'] = pd.to_numeric(combined_df.get('Charge', 0), errors='coerce').fillna(0)

                # Rule-based + ICD10 detailed (เหมือนเวอร์ชันก่อน)
                # ... (โค้ด rule ทั้งหมดเหมือนที่เคยให้) ...

                # หลัง process เสร็จ
                st.session_state.findings_df = combined_df
                st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)

# Dashboard (เหมือนเดิม)
def dashboard_page():
    # โค้ด dashboard ทั้งหมด (header, stats, pie chart, tabs, table with สิทธิการรักษา, export Excel/PDF)
    # ... (เหมือนเวอร์ชันก่อนหน้า) ...

# Main
if not st.session_state.logged_in:
    login_page()
else:
    upload_page()
    if st.session_state.findings_df is not None:
        dashboard_page()
