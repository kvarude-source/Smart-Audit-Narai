import streamlit as st
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from datetime import datetime
import time
import io
import re  # สำหรับ validate ICD10 format
import plotly.express as px  # สำหรับ pie chart
from fpdf import FPDF  # สำหรับ export PDF
import logging  # สำหรับ logging

# Setup logging
logging.basicConfig(filename='smart_audit.log', level=logging.INFO, format='%(asctime)s - %(message)s')

# Session state for login and data persistence
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'username' not in st.session_state:
    st.session_state.username = ""
if 'findings_df' not in st.session_state:
    st.session_state.findings_df = None

# Logo URL (แทนที่ด้วยโลโก้จริงของคุณ)
LOGO_URL = "https://via.placeholder.com/150/006400/FFD700?text=PNH"  # Placeholder

# ML model training (สามารถ retrain ด้วย data จริง)
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
        'missing_right': np.random.randint(0, 2, num_samples),  # New for สิทธิการรักษา
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
        .stButton > button { background-color: #1890ff; color: white; border-radius: 5px; }
        .copyright { text-align: center; margin-top: 20px; color: #888; font-size: 12px; }
        </style>
    """, unsafe_allow_html=True)

    st.image(LOGO_URL, width=150)
    st.markdown('<div class="login-container">', unsafe_allow_html=True)
    st.header("เข้าสู่ระบบ SMART Audit AI")
    username = st.text_input("ชื่อผู้ใช้", value="")
    password = st.text_input("รหัสผ่าน", type="password", value="")
    if st.button("เข้าสู่ระบบ"):
        if username == "Hosnarai" and password == "h15000":
            st.session_state.logged_in = True
            st.session_state.username = username
            logging.info(f"User {username} logged in")
            st.rerun()
        else:
            st.error("ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง")
            logging.warning("Failed login attempt")
    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('<div class="copyright">Copyright: By COMMIT version 1.0</div>', unsafe_allow_html=True)

# Upload Page
def upload_page():
    st.markdown("""
        <style>
        .upload-container { max-width: 600px; margin: auto; padding: 20px; background-color: #ffffff; border-radius: 10px; box-shadow: 0 4px 8px rgba(0,0,0,0.1); }
        </style>
    """, unsafe_allow_html=True)

    st.markdown('<div class="upload-container">', unsafe_allow_html=True)
    st.subheader("อัปโหลดไฟล์ข้อมูล 52 แฟ้ม (.txt)")
    uploaded_files = st.file_uploader("เลือกไฟล์ .txt 52 แฟ้ม", type="txt", accept_multiple_files=True)
    if st.button("เริ่มตรวจสอบ") and uploaded_files:
        if len(uploaded_files) != 52:
            st.error(f"ต้องอัปโหลดครบ 52 แฟ้ม (อัปโหลดแล้ว {len(uploaded_files)} แฟ้ม)")
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
                        header = lines[0].split('|')  # Assume pipe-separated; adjust sep if needed
                        data = [line.split('|') for line in lines[1:]]
                        df = pd.DataFrame(data, columns=header)
                        all_data.append(df)
                        total_records += len(df)
                except Exception as e:
                    logging.error(f"Error processing file {file.name}: {e}")
                    st.warning(f"ไฟล์ {file.name} มีปัญหา ข้ามไฟล์นี้")

                progress = (idx + 1) / 52
                progress_bar.progress(progress)
                status_text.text(f"ประมวลผล {idx+1}/52 ({int(progress*100)}%)")
                time.sleep(0.05)

            if all_data:
                combined_df = pd.concat(all_data, ignore_index=True)
                combined_df['Charge'] = pd.to_numeric(combined_df.get('Charge', 0), errors='coerce').fillna(0)

                # Detailed Rule-based (enhanced for ICD10 and others)
                columns_to_check = ['ICD10', 'ICD9CM', 'Drug', 'Procedure', 'Lab', 'Disease', 'Right']
                for col in columns_to_check:
                    combined_df[f'missing_{col.lower()}'] = combined_df[col].isna() | (combined_df[col] == '')

                # Enhanced ICD10 rules:
                def validate_icd10(code):
                    if pd.isna(code) or code == '':
                        return False
                    return bool(re.match(r'^[A-Z][0-9]{2}(\.[0-9]{1,2})?$', code))

                combined_df['icd10_format_invalid'] = ~combined_df['ICD10'].apply(validate_icd10)
                
                def check_duplicated_icd10(codes):
                    if pd.isna(codes) or codes == '':
                        return False
                    code_list = [c.strip() for c in codes.split(',')]
                    return len(code_list) != len(set(code_list))

                combined_df['icd10_duplicated'] = combined_df['ICD10'].apply(check_duplicated_icd10)
                
                disease_icd_map = {'Diabetes': ['E10', 'E11', 'E12', 'E13', 'E14'], 'Hypertension': ['I10']}  # Expand with real map
                def icd_disease_mismatch(row):
                    disease = row.get('Disease', '')
                    icd10 = row.get('ICD10', '')
                    if not disease or not icd10 or disease not in disease_icd_map:
                        return False
                    return not any(icd10.startswith(prefix) for prefix in disease_icd_map[disease])

                combined_df['icd_disease_mismatch'] = combined_df.apply(icd_disease_mismatch, axis=1)
                
                # Other rules
                combined_df['drug_proc_mismatch'] = (~combined_df['missing_drug']) & combined_df['missing_proc']
                combined_df['lab_abnormal'] = combined_df['Lab'].str.contains('abnormal', case=False, na=False) | (pd.to_numeric(combined_df['Lab'], errors='coerce') > 100).fillna(False)
                combined_df['icd9_proc_mismatch'] = (~combined_df['missing_proc']) & combined_df['missing_icd9cm']

                # Assign findings
                combined_df['finding'] = 'ปกติ'
                conditions = [
                    (combined_df['icd10_format_invalid'], 'ICD10 รูปแบบไม่ถูกต้อง (Rule)'),
                    (combined_df['icd10_duplicated'], 'ICD10 ซ้ำกัน (Rule)'),
                    (combined_df['icd_disease_mismatch'], 'ICD10 ไม่สอดคล้องโรค (Rule)'),
                    (combined_df['missing_icd10'], 'ข้อมูล ICD10 ไม่ครบ (Rule)'),
                    (combined_df['missing_icd9cm'], 'ข้อมูล ICD9CM ไม่ครบ (Rule)'),
                    (combined_df['missing_drug'], 'ข้อมูลยาไม่ครบ (Rule)'),
                    (combined_df['missing_proc'], 'ข้อมูลหัตถการไม่ครบ (Rule)'),
                    (combined_df['missing_lab'], 'ข้อมูล LAB ไม่ครบ (Rule)'),
                    (combined_df['missing_disease'], 'ข้อมูลโรคไม่ครบ (Rule)'),
                    (combined_df['missing_right'], 'ข้อมูลสิทธิการรักษาไม่ครบ (Rule)'),
                    (combined_df['drug_proc_mismatch'], 'ยาไม่สอดคล้องหัตถการ (Rule)'),
                    (combined_df['lab_abnormal'], 'ผล LAB ผิดปกติ (Rule)'),
                    (combined_df['icd9_proc_mismatch'], 'ICD9CM ไม่สอดคล้องหัตถการ (Rule)')
                ]
                for cond, msg in conditions:
                    combined_df.loc[cond, 'finding'] = msg

                # Recommendations
                combined_df['action'] = 'ตรวจสอบข้อมูลเพิ่มเติม'
                combined_df.loc[combined_df['finding'].str.contains('ICD10'), 'action'] = 'ตรวจสอบและแก้ไขรหัส ICD10 ให้ถูกต้องตามรูปแบบและโรค'
                combined_df.loc[combined_df['finding'].str.contains('ICD9CM'), 'action'] = 'เพิ่ม/แก้ไขรหัส ICD9CM และตรวจสอบสอดคล้องหัตถการ'
                combined_df.loc[combined_df['finding'].str.contains('ยา'), 'action'] = 'เพิ่มรายละเอียดยาและตรวจสอบสอดคล้องหัตถการ/LAB'
                combined_df.loc[combined_df['finding'].str.contains('หัตถการ'), 'action'] = 'เพิ่มหัตถการและตรวจสอบค่าใช้จ่าย'
                combined_df.loc[combined_df['finding'].str.contains('LAB'), 'action'] = 'เพิ่มผล LAB และวิเคราะห์ความผิดปกติ'
                combined_df.loc[combined_df['finding'].str.contains('โรค'), 'action'] = 'เพิ่มข้อมูลโรคและเชื่อมโยง ICD'
                combined_df.loc[combined_df['finding'].str.contains('สิทธิ'), 'action'] = 'เพิ่มข้อมูลสิทธิการรักษาและตรวจสอบสอดคล้อง'

                # Impact
                combined_df['impact'] = 1000
                combined_df.loc[combined_df['finding'].str.contains('ICD10'), 'impact'] = combined_df['Charge'] * 0.2
                combined_df.loc[combined_df['finding'] != 'ปกติ', 'impact'] = combined_df['Charge'] * 0.15

                # ML prediction
                features_cols = [f'missing_{col.lower()}' for col in columns_to_check] + ['icd_disease_mismatch', 'drug_proc_mismatch', 'lab_abnormal', 'icd9_proc_mismatch', 'icd10_format_invalid', 'icd10_duplicated', 'Charge']
                features = combined_df[features_cols].copy()
                features['Charge'] = features['Charge'].fillna(0)
                combined_df['ml_risk'] = ml_model.predict(features)
                combined_df.loc[combined_df['ml_risk'] == 1, 'finding'] += ' (ML Underclaim)'
                combined_df.loc[combined_df['ml_risk'] == 2, 'finding'] += ' (ML Overclaim)'

                # Format Date
                combined_df['Date'] = pd.to_datetime(combined_df['Date'], errors='coerce').dt.strftime('%d-%m-%Y')

                # HN/AN as Number
                combined_df['Number'] = combined_df.get('HN', '') .combine_first(combined_df.get('AN', ''))

                # Type
                combined_df['Type'] = np.where(combined_df['Number'].str.startswith('HN'), 'OPD', 'IPD')

                st.session_state.findings_df = combined_df
                logging.info(f"Processed {total_records} records")
                st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)

# Dashboard Page
def dashboard_page():
    st.markdown("""
        <style>
        .dashboard-header { display: flex; align-items: center; justify-content: space-between; background-color: #1890ff; padding: 10px; border-radius: 10px; color: white; }
        .header-text { font-family: 'Arial Black', sans-serif; font-size: 24px; text-shadow: 1px 1px 2px rgba(0,0,0,0.3); }
        .username { font-size: 16px; }
        .stats-container { display: flex; justify-content: space-between; margin-top: 20px; flex-wrap: wrap; }
        .stat-box { background-color: #e6f7ff; padding: 15px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); width: 24%; text-align: center; margin-bottom: 10px; }
        @media (max-width: 768px) { .stat-box { width: 48%; } }
        </style>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns([1, 5])
    with col1:
        st.image(LOGO_URL, width=100)
    with col2:
        st.markdown('<div class="dashboard-header">', unsafe_allow_html=True)
        st.markdown('<span class="header-text">โรงพยาบาลพระนารายณ์มหาราช ลพบุรี<br>SMART Audit AI</span>', unsafe_allow_html=True)
        st.markdown(f'<span class="username">ผู้ใช้: {st.session_state.username}</span>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    if st.session_state.findings_df is not None:
        df = st.session_state.findings_df
        total_records = len(df)
        pre_amount = df['Charge'].sum()
        post_amount = pre_amount + df['impact'].sum()
        underclaim = df[df['finding'].str.contains('Underclaim')]
        avg_increase = underclaim['impact'].mean() if not underclaim.empty else 0

        st.markdown('<div class="stats-container">', unsafe_allow_html=True)
        st.markdown(f'<div class="stat-box">จำนวนไฟล์ที่ตรวจสอบ: {52}</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="stat-box">จำนวน Record ทั้งหมด: {total_records}</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="stat-box">ยอดเงินก่อน audit: {pre_amount:,.0f} บาท</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="stat-box">ยอดเงินหลัง audit: {post_amount:,.0f} บาท</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

        # Summary Report with Pie Chart
        if not df.empty:
            error_counts = df['finding'].value_counts()
            fig = px.pie(error_counts, values=error_counts.values, names=error_counts.index, title="สรุป % ข้อค้นพบ")
            st.plotly_chart(fig, use_container_width=True)

        tab_all, tab_opd, tab_ipd = st.tabs(["ทั้งหมด", "เฉพาะ OPD", "เฉพาะ IPD"])
        with tab_all:
            st.dataframe(df[['Number', 'Date', 'finding', 'action', 'impact', 'Right']], use_container_width=True, height=400)
        with tab_opd:
            opd_df = df[df['Type'] == 'OPD']
            st.dataframe(opd_df[['Number', 'Date', 'finding', 'action', 'impact', 'Right']], use_container_width=True, height=400)
        with tab_ipd:
            ipd_df = df[df['Type'] == 'IPD']
            st.dataframe(ipd_df[['Number', 'Date', 'finding', 'action', 'impact', 'Right']], use_container_width=True, height=400)

        # Export Excel
        if st.button("ส่งออกเป็น Excel"):
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='Findings', index=False)
                pd.DataFrame({'สรุป': ['จำนวนไฟล์', 'จำนวน Record', 'ยอดเงินก่อน', 'ยอดเงินหลัง', 'เพิ่มได้เฉลี่ย/เคส'],
                              'ค่า': [52, total_records, f"{pre_amount:,.0f} บาท", f"{post_amount:,.0f} บาท", f"{avg_increase:,.0f} บาท"]}).to_excel(writer, sheet_name='Summary', index=False)
            st.download_button("ดาวน์โหลดรายงาน Excel", output.getvalue(), "SmartAudit_Report.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

        # Export PDF (new addition)
        if st.button("ส่งออกเป็น PDF"):
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", size=12)
            pdf.cell(200, 10, txt="Smart Audit AI Report", ln=1, align='C')
            pdf.cell(200, 10, txt=f"จำนวน Record: {total_records}", ln=1)
            pdf.cell(200, 10, txt=f"ยอดเงินก่อน audit: {pre_amount:,.0f} บาท", ln=1)
            pdf.cell(200, 10, txt=f"ยอดเงินหลัง audit: {post_amount:,.0f} บาท", ln=1)
            pdf.output("SmartAudit_Report.pdf")
            with open("SmartAudit_Report.pdf", "rb") as f:
                st.download_button("ดาวน์โหลดรายงาน PDF", f, "SmartAudit_Report.pdf")
            os.remove("SmartAudit_Report.pdf")

# Main logic
if not st.session_state.logged_in:
    login_page()
else:
    upload_page()
    dashboard_page()
</parameter>
</xai:function_call>
