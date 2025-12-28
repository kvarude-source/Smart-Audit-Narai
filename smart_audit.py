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

# ------------------- 1. Logging & Config Setup -------------------
st.set_page_config(page_title="SMART Audit AI", page_icon="🔍", layout="wide")

logging.basicConfig(
    filename='smart_audit.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# ------------------- 2. Session State Initialization -------------------
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'username' not in st.session_state:
    st.session_state.username = ""
if 'processed_data' not in st.session_state:
    # เก็บข้อมูลเป็น Tuple: (dataframe_findings, risk_label)
    st.session_state.processed_data = None
if 'menu_selection' not in st.session_state:
    st.session_state.menu_selection = "อัปโหลดข้อมูล"

# ------------------- 3. Constants & Resources -------------------
LOGO_URL = "https://via.placeholder.com/150/006400/FFD700?text=PNH" # สามารถเปลี่ยนเป็น URL โลโก้จริงได้

@st.cache_resource
def get_ml_model():
    # จำลองการสร้าง Model (ในระบบจริงอาจจะ Load model ที่ train แล้วเข้ามา)
    np.random.seed(42)
    num_samples = 1000
    data = pd.DataFrame({
        'total_issues': np.random.randint(0, 100, num_samples),
        'risk_score': np.random.uniform(0, 10, num_samples),
        'risk_level': np.random.choice([0, 1, 2], num_samples, p=[0.7, 0.25, 0.05]) 
        # 0=Low, 1=Medium, 2=High
    })
    X = data[['total_issues', 'risk_score']]
    y = data['risk_level']
    
    clf = RandomForestClassifier(n_estimators=100, random_state=42)
    clf.fit(X, y)
    return clf

ml_model = get_ml_model()

# ------------------- 4. Helper Functions (Processing) -------------------
def process_52_files(uploaded_files):
    findings = []
    
    # Progress Bar UI
    progress_bar = st.progress(0)
    status_text = st.empty()

    for idx, file in enumerate(uploaded_files):
        try:
            # อ่านไฟล์ด้วย Encoding ภาษาไทย (TIS-620)
            content = file.read().decode('TIS-620', errors='replace')
            lines = content.splitlines()
            
            if not lines:
                continue
                
            header = lines[0].split('|')
            # กรองบรรทัดว่างออก
            data = [line.split('|') for line in lines[1:] if line.strip()]
            
            # สร้าง DataFrame
            df = pd.DataFrame(data, columns=header)
            df = df.replace('', np.nan)
            
            file_name = file.name.upper()

            # --- Rule Logic (ตัวอย่าง) ---
            if 'IPDX.TXT' in file_name:
                # ตรวจสอบ DIAG ว่าง
                if 'DIAG' in df.columns:
                    missing_icd10 = df['DIAG'].isna().sum()
                    if missing_icd10 > 0:
                        findings.append({"ประเภทปัญหา": "ICD-10 หาย/ว่าง", "จำนวน": missing_icd10, "แฟ้ม": file_name})

                    # ตรวจสอบรูปแบบ ICD-10 (คร่าวๆ)
                    invalid_format = df['DIAG'].astype(str).apply(
                        lambda x: pd.notna(x) and not bool(re.match(r'^[A-Z]\d{2}(\.\d{1,4})?$', str(x).strip()))
                    ).sum()
                    if invalid_format > 0:
                        findings.append({"ประเภทปัญหา": "รูปแบบ ICD-10 ผิด", "จำนวน": invalid_format, "แฟ้ม": file_name})

            elif 'CHARGE.TXT' in file_name:
                if 'AMOUNT' in df.columns:
                    # แปลงเป็นตัวเลข
                    df['AMOUNT'] = pd.to_numeric(df['AMOUNT'], errors='coerce').fillna(0)
                    high_charge = (df['AMOUNT'] > 100000).sum()
                    if high_charge > 0:
                        findings.append({"ประเภทปัญหา": "ค่ารักษาสูงผิดปกติ (>1แสน)", "จำนวน": high_charge, "แฟ้ม": file_name})

        except Exception as e:
            st.error(f"Error reading {file.name}: {e}")
        
        # Update Progress
        progress_bar.progress((idx + 1) / len(uploaded_files))
        status_text.text(f"กำลังประมวลผล: {file.name}")

    # สรุปผล
    findings_df = pd.DataFrame(findings) if findings else pd.DataFrame(columns=["ประเภทปัญหา", "จำนวน", "แฟ้ม"])
    
    # AI Risk Prediction (จำลอง)
    total_issues = findings_df['จำนวน'].sum() if not findings_df.empty else 0
    # สร้าง feature vector ปลอมๆ เพื่อ test model
    input_vector = np.array([[total_issues, total_issues/10]]) 
    
    risk_pred = ml_model.predict(input_vector)[0]
    risk_mapping = {0: "ต่ำ (Low)", 1: "ปานกลาง (Medium)", 2: "สูง (High)"}
    risk_label = risk_mapping.get(risk_pred, "Unknown")
    
    time.sleep(0.5) # หน่วงเวลาเล็กน้อยให้เห็น progress เต็ม
    status_text.empty()
    progress_bar.empty()
    
    return findings_df, risk_label

# ------------------- 5. Pages -------------------

def login_page():
    st.markdown("""
        <style>
        .login-box {
            padding: 50px; border-radius: 10px;
            background-color: #f0f2f6; text-align: center;
            max-width: 500px; margin: 0 auto;
        }
        </style>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        st.markdown('<div class="login-box">', unsafe_allow_html=True)
        st.image(LOGO_URL, width=100)
        st.title("SMART Audit AI")
        st.subheader("เข้าสู่ระบบตรวจสอบข้อมูล")
        
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        
        if st.button("Login", use_container_width=True, type="primary"):
            if username == "Hosnarai" and password == "h15000":
                st.session_state.logged_in = True
                st.session_state.username = username
                logging.info(f"User {username} logged in.")
                st.success("Login สำเร็จ!")
                time.sleep(0.5)
                st.rerun()
            else:
                st.error("ชื่อผู้ใช้หรือรหัสผ่านผิดพลาด")
        
        st.markdown('</div>', unsafe_allow_html=True)

def dashboard_page():
    st.header("📊 Dashboard ผลการตรวจสอบ")
    
    if st.session_state.processed_data is None:
        st.info("ยังไม่มีข้อมูลผลลัพธ์ กรุณาไปที่เมนู 'อัปโหลดข้อมูล' เพื่อประมวลผลก่อน")
        return

    findings_df, risk_label = st.session_state.processed_data
    
    # Metrics Row
    c1, c2, c3 = st.columns(3)
    total_err = findings_df['จำนวน'].sum() if not findings_df.empty else 0
    c1.metric("จำนวนข้อผิดพลาดทั้งหมด", f"{total_err:,}")
    c2.metric("ระดับความเสี่ยง (AI)", risk_label, 
              delta="High Risk" if "สูง" in risk_label else "Normal",
              delta_color="inverse" if "สูง" in risk_label else "normal")
    c3.metric("เวลาที่ตรวจสอบ", datetime.now().strftime("%H:%M:%S"))

    st.markdown("---")

    # Charts & Table
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("สัดส่วนปัญหาที่พบ")
        if not findings_df.empty:
            fig = px.pie(findings_df, values='จำนวน', names='ประเภทปัญหา', hole=0.4)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.success("ไม่พบข้อมูลผิดพลาด")

    with col2:
        st.subheader("ตารางรายละเอียด")
        if not findings_df.empty:
            st.dataframe(findings_df, use_container_width=True, height=300)
        else:
            st.write("-")

    # Export Section
    st.markdown("### 📥 Download Reports")
    if not findings_df.empty:
        c_down1, c_down2 = st.columns(2)
        
        # CSV
        csv = findings_df.to_csv(index=False).encode('utf-8-sig')
        c_down1.download_button("Download CSV", csv, "audit_result.csv", "text/csv")
        
        # PDF
        try:
            pdf = FPDF()
            pdf.add_page()
            # หมายเหตุ: หากไม่มีไฟล์ฟอนต์ THSarabun.ttf ในโฟลเดอร์เดียวกันโค้ดจะ Error
            # ตรงนี้จึงใส่ try/except ไว้เพื่อความปลอดภัยในการรันครั้งแรก
            try:
                pdf.add_font('THSarabun', '', 'THSarabun.ttf', uni=True)
                pdf.set_font('THSarabun', size=16)
            except:
                pdf.set_font("Arial", size=12)
                st.toast("ไม่พบฟอนต์ไทย ใช้ฟอนต์มาตรฐานแทน", icon="⚠️")

            pdf.cell(200, 10, txt="Smart Audit Report", ln=1, align='C')
            pdf.ln(10)
            
            for index, row in findings_df.iterrows():
                # Encode text เพื่อป้องกัน error หากใช้ Arial กับภาษาไทย
                txt_line = f"{row['ประเภทปัญหา']} : {row['จำนวน']}"
                if pdf.font_family == 'Arial':
                     txt_line = "Error Found (Thai font missing)"
                pdf.cell(0, 10, txt=txt_line, ln=1)
                
            pdf_out = pdf.output(dest='S').encode('latin-1')
            c_down2.download_button("Download PDF", pdf_out, "audit_report.pdf", "application/pdf")
        except Exception as e:
            st.error(f"PDF Generation Error: {e}")

def upload_page():
    st.header("📂 อัปโหลดข้อมูล 52 แฟ้ม")
    st.markdown("กรุณาเลือกไฟล์ .txt ที่ต้องการตรวจสอบ (เลือกได้หลายไฟล์พร้อมกัน)")
    
    uploaded_files = st.file_uploader(
        "Upload Files", 
        type=['txt'], 
        accept_multiple_files=True
    )
    
    if uploaded_files:
        st.info(f"เลือกไฟล์แล้วจำนวน: {len(uploaded_files)} ไฟล์")
        
        if st.button("🚀 เริ่มประมวลผล (Start Audit)", type="primary"):
            with st.spinner("AI กำลังทำงาน..."):
                findings, risk = process_52_files(uploaded_files)
                st.session_state.processed_data = (findings, risk)
                st.success("ประมวลผลเสร็จสิ้น!")
                time.sleep(1)
                # เปลี่ยนหน้าไป Dashboard อัตโนมัติ (Optional)
                # st.session_state.menu_selection = "Dashboard Result" 
                # st.rerun() 

# ------------------- 6. Main App Controller -------------------
def main():
    if not st.session_state.logged_in:
        login_page()
    else:
        # Sidebar Menu
        with st.sidebar:
            st.image(LOGO_URL, width=100)
            st.write(f"สวัสดี, **{st.session_state.username}**")
            st.markdown("---")
            
            menu = st.radio("เมนูหลัก", ["อัปโหลดข้อมูล", "Dashboard Result"])
            
            st.markdown("---")
            if st.button("ออกจากระบบ", use_container_width=True):
                st.session_state.logged_in = False
                st.session_state.processed_data = None
                st.rerun()

        # Routing
        if menu == "อัปโหลดข้อมูล":
            upload_page()
        elif menu == "Dashboard Result":
            dashboard_page()

if __name__ == "__main__":
    main()
