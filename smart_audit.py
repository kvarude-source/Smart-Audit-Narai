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

# ------------------- Logging Setup -------------------
logging.basicConfig(
    filename='smart_audit.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# ------------------- Session State -------------------
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'username' not in st.session_state:
    st.session_state.username = ""
if 'findings_df' not in st.session_state:
    st.session_state.findings_df = None
if 'processed_data' not in st.session_state:
    st.session_state.processed_data = None

# ------------------- Logo -------------------
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
    password = st.text_input("🔒 รหัสผ่าน", type="password")

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
            logging.warning(f"Login failed: {username}")

    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('<div class="copyright">© 2025 COMMIT - SMART Audit AI Version 1.0</div>', unsafe_allow_html=True)

# ------------------- File Processing -------------------
def process_52_files(uploaded_files):
    findings = []

    progress_bar = st.progress(0)
    status_text = st.empty()

    for idx, file in enumerate(uploaded_files):
        try:
            # 52 แฟ้มส่วนใหญ่ใช้ encoding TIS-620
            content = file.read().decode('TIS-620', errors='replace')
            lines = content.splitlines()
            if not lines:
                continue
            header = lines[0].split('|')
            data = [line.split('|') for line in lines[1:] if line.strip()]
            df = pd.DataFrame(data, columns=header)
            df = df.replace('', np.nan)

            file_name = file.name.upper()

            # ตัวอย่าง Rule ตรวจสอบ (สามารถเพิ่มได้ตามต้องการ)
            if 'IPDX.TXT' in file_name:
                missing_icd10 = df['DIAG'].isna().sum()
                invalid_format = df['DIAG'].astype(str).apply(
                    lambda x: pd.notna(x) and not bool(re.match(r'^[A-Z]\d{2}(\.\d{1,4})?$', str(x).strip()))
                ).sum()
                duplicated_icd10 = df.duplicated(subset=['HN', 'AN', 'DIAG']).sum()

                if missing_icd10 > 0:
                    findings.append({"ประเภทปัญหา": "ICD-10 หาย/ว่าง", "จำนวน": missing_icd10})
                if invalid_format > 0:
                    findings.append({"ประเภทปัญหา": "รูปแบบ ICD-10 ไม่ถูกต้อง", "จำนวน": invalid_format})
                if duplicated_icd10 > 0:
                    findings.append({"ประเภทปัญหา": "ICD-10 ซ้ำในผู้ป่วยเดียวกัน", "จำนวน": duplicated_icd10})

            elif 'CHARGE.TXT' in file_name:
                if 'AMOUNT' in df.columns:
                    df['AMOUNT'] = pd.to_numeric(df['AMOUNT'], errors='coerce').fillna(0)
                    high_charge = (df['AMOUNT'] > 100000).sum()
                    zero_charge = (df['AMOUNT'] == 0).sum()
                    if high_charge > 0:
                        findings.append({"ประเภทปัญหา": "ค่ารักษาสูงผิดปกติ (>100,000)", "จำนวน": high_charge})
                    if zero_charge > 0:
                        findings.append({"ประเภทปัญหา": "ค่ารักษาเป็น 0", "จำนวน": zero_charge})

        except Exception as e:
            st.error(f"ไฟล์ {file.name} มีปัญหา: {e}")

        progress_bar.progress((idx + 1) / len(uploaded_files))
        status_text.text(f"กำลังประมวลผล: {file.name} ({idx+1}/52)")

    findings_df = pd.DataFrame(findings) if findings else pd.DataFrame(columns=["ประเภทปัญหา", "จำนวน"])

    # ML Risk Prediction (ตัวอย่างง่าย ๆ)
    total_issues = findings_df['จำนวน'].sum() if not findings_df.empty else 0
    feature_vector = np.zeros((1, 14))
    feature_vector[0, 0] = 1 if total_issues > 50 else 0
    feature_vector[0, 11] = 1 if "รูปแบบ ICD-10 ไม่ถูกต้อง" in findings_df['ประเภทปัญหา'].values else 0
    feature_vector[0, 13] = min(total_issues / 1000, 10)

    risk_pred = ml_model.predict(feature_vector)[0]
    risk_label = ["ต่ำ", "ปานกลาง", "สูง"][risk_pred]

    return findings_df, risk_label

# ------------------- Dashboard Page -------------------
def dashboard_page():
    st.markdown(f"""
        <div style='text-align: right; color: #555; margin-bottom: 20px;'>
            ผู้ใช้: <b>{st.session_state.username}</b> | 
            เวลา: {datetime.now().strftime("%d/%m/%Y %H:%M")}
        </div>
    """, unsafe_allow_html=True)

    st.title("📊 ผลการตรวจสอบข้อมูล 52 แฟ้ม")

    findings_df = st.session_state.processed_data[0]
    risk_label = st.session_state.processed_data[1]

    col1, col2, col3, col4 = st.columns(4)
    total_issues = findings_df['จำนวน'].sum() if not findings_df.empty else 0
    col1.metric("จำนวนปัญหาที่พบ", f"{total_issues:,}")
    col2.metric("ระดับความเสี่ยงโดยรวม", risk_label)
    col3.metric("จำนวนแฟ้มที่ตรวจ", "52")
    col4.metric("สถานะ", "เสร็จสิ้น")

    st.markdown("### รายละเอียดปัญหาที่พบ")

    if not findings_df.empty:
        fig = px.pie(findings_df, values='จำนวน', names='ประเภทปัญหา',
                     color_discrete_sequence=px.colors.sequential.Reds,
                     hole=0.4)
        fig.update_traces(textposition='inside', textinfo='percent+label')
        st.plotly_chart(fig, use_container_width=True)

        st.dataframe(findings_df.sort_values('จำนวน', ascending=False)
                     .style.background_gradient(cmap='Reds'), use_container_width=True)
    else:
        st.success("🎉 ไม่พบปัญหาใด ๆ ในข้อมูลที่อัปโหลด!")

    # Export
    st.markdown("### 📥 ดาวน์โหลดรายงาน")
    col1, col2 = st.columns(2)
    with col1:
        csv = findings_df.to_csv(index=False).encode('utf-8-sig')
        st.download_button("ดาวน์โหลด CSV", csv, "smart_audit_findings.csv", "text/csv")
    with col2:
        buffer = io.BytesIO()
        pdf = FPDF()
        pdf.add_page()
        pdf.add_font("THSarabun", "", "THSarabun.ttf", uni=True)  # ต้องมี font ไทย หรือใช้ Arial
        pdf.set_font("Arial", size=16)
        pdf.cell(200, 10, txt="รายงานผลการตรวจสอบ SMART Audit AI", ln=1, align='C')
        pdf.ln(10)
        pdf.set_font("Arial", size=12)
        for _, row in findings_df.iterrows():
            pdf.cell(200, 10, txt=f"{row['ประเภทปัญหา']}: {row['จำนวน']} รายการ", ln=1)
        pdf.output(buffer)
        st.download_button("ดาวน์โหลด PDF", buffer.getvalue(), "smart_audit_report.pdf", "application/pdf")

# ------------------- Upload Page -------------------
def upload_page():
    st.markdown("""
        <style>
        .upload-container {
            max-width: 800px; margin: 20px auto; padding: 30px;
            background-color: #f8fff8; border-radius: 15px;
            box-shadow: 0 6px 12px rgba(0,0,0,0.1);
        }
        </style>
    """, unsafe_allow_html=True)

    st.markdown('<div class="upload-container">', unsafe_allow_html=True)
    st.header("อัปโหลดไฟล์ 52 แฟ้ม (.txt)")
    st.info("กรุณาอัปโหลดไฟล์ทั้ง 52 แฟ้มในรูปแบบ .txt (encoding TIS-620)")

    uploaded_files = st.file_uploader(
        "เลือกไฟล์ทั้ง 52 แฟ้ม",
        type=["txt"],
