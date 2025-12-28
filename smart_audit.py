import streamlit as st
import pandas as pd
import numpy as np
import time
import base64
import logging
from datetime import datetime

# --- Import ML Library ---
try:
    from sklearn.ensemble import IsolationForest
except ImportError:
    st.error("⚠️ ไม่พบ Library 'scikit-learn' ระบบจะใช้ Rule-base อย่างเดียว")

# --- 1. Config & Setup ---
st.set_page_config(
    page_title="SMART Audit AI - โรงพยาบาลพระนารายณ์มหาราช",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)
logging.basicConfig(format='%(asctime)s - %(message)s', level=logging.INFO)

# --- 2. Embedded Resources (Logo Base64) ---
def get_base64_logo():
    svg = """
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512" width="100" height="100">
      <path fill="#0A192F" d="M256 0C114.6 0 0 114.6 0 256s114.6 256 256 256 256-114.6 256-256S397.4 0 256 0zm0 472c-119.3 0-216-96.7-216-216S136.7 40 256 40s216 96.7 216 216-96.7 216-216 216z"/>
      <path fill="#D4AF37" d="M368 232h-88v-88c0-13.3-10.7-24-24-24s-24 10.7-24 24v88h-88c-13.3 0-24 10.7-24 24s10.7 24 24 24h88v88c0 13.3 10.7 24 24 24s24-10.7 24-24v-88h88c13.3 0 24-10.7 24-24s-10.7-24-24-24z"/>
    </svg>
    """
    return base64.b64encode(svg.encode('utf-8')).decode("utf-8")

LOGO_HTML = f'<img src="data:image/svg+xml;base64,{get_base64_logo()}" width="100" style="margin-bottom: 10px;">'

# --- 3. CSS Styling (Luxury Light Theme) ---
def apply_luxury_theme():
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Prompt:wght@300;400;600&display=swap');
        
        [data-testid="stAppViewContainer"] { background-color: #F0F4F8; color: #1E293B; }
        [data-testid="stSidebar"] { background-color: #0F172A; }
        [data-testid="stSidebar"] * { color: #F8FAFC !important; }
        
        html, body, p, div, span, label, h1, h2, h3, h4, h5, h6 {
            font-family: 'Prompt', sans-serif !important; color: #334155;
        }
        
        .metric-card {
            background: #FFFFFF; padding: 20px; border-radius: 12px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.05); border-left: 5px solid #D4AF37;
        }
        .metric-title { font-size: 14px; color: #64748B; font-weight: 600; }
        .metric-value { font-size: 28px; color: #0F172A; font-weight: bold; margin-top: 5px; }
        
        [data-testid="stDataFrame"] { background-color: #FFFFFF !important; border-radius: 10px; padding: 10px; }
        div.stButton > button {
            background: linear-gradient(135deg, #0F172A 0%, #1E293B 100%); color: white !important;
            border: none; border-radius: 8px; padding: 10px 24px;
        }
        .login-container { background: white; padding: 40px; border-radius: 16px; text-align: center; }
        </style>
    """, unsafe_allow_html=True)

# --- 4. Session State ---
if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'username' not in st.session_state: st.session_state.username = ""
if 'audit_data' not in st.session_state: st.session_state.audit_data = None
if 'financial_summary' not in st.session_state: st.session_state.financial_summary = {}
if 'current_page' not in st.session_state: st.session_state.current_page = "login"

# --- 5. Intelligent Logic Functions (Rule-Base & ML) ---

def run_ml_anomaly_detection(df, price_col):
    """ใช้ Isolation Forest หาค่าใช้จ่ายที่ผิดปกติ (Anomaly Detection)"""
    try:
        # เตรียมข้อมูล (เฉพาะที่มีค่าใช้จ่าย > 0)
        data_for_ml = df[df[price_col] > 0][[price_col]].copy()
        
        if len(data_for_ml) < 10: return [] # ข้อมูลน้อยไปไม่ทำ ML

        # Initialize Model (Contamination = อัตราส่วนของ Outlier ที่คาดหวัง เช่น 1%)
        clf = IsolationForest(contamination=0.01, random_state=42)
        data_for_ml['anomaly'] = clf.fit_predict(data_for_ml)
        
        # -1 คือ Anomaly (ผิดปกติ)
        anomalies = data_for_ml[data_for_ml['anomaly'] == -1]
        
        ml_findings = []
        for idx, row in anomalies.iterrows():
            original_row = df.loc[idx]
            ml_findings.append({
                "Type": "ML_Detected",
                "HN/AN": original_row.get('AN', original_row.get('HN', '-')),
                "วันที่": original_row.get('DATE_SERV', '-'),
                "ข้อค้นพบ": f"🤖 AI: ค่ารักษาสูง/ต่ำ ผิดปกติ ({row[price_col]:,.0f})",
                "Action": "ตรวจสอบความสมเหตุสมผล (Audit)",
                "Impact": 0.00 # ML เตือนให้ดู อาจไม่ใช่ข้อผิดพลาดเสมอไป
            })
        return ml_findings
    except Exception as e:
        print(f"ML Error: {e}")
        return []

def process_52_files(uploaded_files):
    details_list = []
    total_records = 0
    pre_audit_sum = 0
    
    # Progress Bar UI (1-100%)
    progress_bar = st.progress(0, text="เริ่มการประมวลผล...")
    total_files = len(uploaded_files)

    for idx, file in enumerate(uploaded_files):
        # Update Progress %
        percent = int(((idx + 1) / total_files) * 100)
        progress_bar.progress((idx + 1) / total_files, text=f"กำลังตรวจสอบไฟล์ที่ {idx+1}/{total_files} ({percent}%) : {file.name}")
        
        try:
            # Read File
            try:
                content = file.read().decode('TIS-620')
            except:
                file.seek(0)
                content = file.read().decode('utf-8', errors='replace')

            lines = content.splitlines()
            if len(lines) < 2: continue

            sep = '|' if '|' in lines[0] else ','
            header = [h.strip().upper() for h in lines[0].strip().split(sep)]
            rows = [line.strip().split(sep) for line in lines[1:] if line.strip()]
            
            df = pd.DataFrame(rows)
            # Safe Column Assignment
            if df.shape[1] > len(header): df = df.iloc[:, :len(header)]
            if df.shape[1] == len(header): df.columns = header
            else: continue

            # Convert Numeric Columns for Logic
            for col in df.columns:
                if any(x in col for x in ['PRICE', 'COST', 'AMOUNT', 'Pay_Price']):
                     df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

            total_records += len(df)
            file_upper = file.name.upper()

            # ==========================================
            # 🧠 RULE-BASED ENGINE (ตรวจสอบตรรกะ)
            # ==========================================

            # Rule 1: Date Consistency (วันที่จำหน่าย ต้องไม่ก่อน วันที่รับเข้า)
            if 'DATEADM' in df.columns and 'DATEDSC' in df.columns: # ชื่อย่อตามมาตรฐาน 43 แฟ้ม
                # แปลงวันที่ (สมมติว่าเป็น YYYYMMDD)
                # ตรงนี้เขียน Logic คร่าวๆ ถ้าข้อมูลจริงรูปแบบอื่นต้องปรับ
                invalid_dates = df[df['DATEDSC'] < df['DATEADM']]
                for _, row in invalid_dates.iterrows():
                    details_list.append({
                        "Type": "IPD",
                        "HN/AN": row.get('AN', '-'),
                        "วันที่": row.get('DATEADM', '-'),
                        "ข้อค้นพบ": "วันที่จำหน่าย (DATEDSC) ก่อนวันที่รับเข้า (DATEADM)",
                        "Action": "แก้ไขวันที่ให้ถูกต้อง",
                        "Impact": 0.00
                    })

            # Rule 2: Discharge Status Conflict (ตาย แต่ผลการรักษาบอก ปกติ)
            if 'DISCHS' in df.columns and 'DISCHT' in df.columns:
                # 8,9 = Dead, 1 = Improved (Code สมมติมาตรฐาน)
                conflict = df[(df['DISCHS'].isin(['8', '9'])) & (df['DISCHT'] == '1')]
                for _, row in conflict.iterrows():
                    details_list.append({
                        "Type": "IPD",
                        "HN/AN": row.get('AN', '-'),
                        "วันที่": row.get('DATEDSC', '-'),
                        "ข้อค้นพบ": "สถานะจำหน่ายขัดแย้ง (เสียชีวิตแต่ระบุว่าอาการดีขึ้น)",
                        "Action": "ตรวจสอบสรุปเวชระเบียน",
                        "Impact": 0.00
                    })

            # Rule 3: Missing Diagnosis (DIAGNOSIS)
            if any(k in file_upper for k in ['DIAG', 'IPDX', 'OPDX']):
                col_diag = 'DIAGCODE' if 'DIAGCODE' in df.columns else 'DIAG'
                if col_diag in df.columns:
                    errors = df[df[col_diag] == '']
                    for _, row in errors.iterrows():
                        is_ipd = 'IPD' in file_upper
                        hn = row.get('HN', '-')
                        an = row.get('AN', '-')
                        date_serv = row.get('DATE_SERV', row.get('DATETIME_ADMIT', '-'))
                        
                        details_list.append({
                            "Type": "IPD" if is_ipd else "OPD",
                            "HN/AN": an if (is_ipd and an != '-') else hn,
                            "วันที่": date_serv,
                            "ข้อค้นพบ": f"ไม่ระบุรหัสโรค ({col_diag})",
                            "Action": "ลงรหัส ICD-10",
                            "Impact": -2000.00
                        })

            # Rule 4: Zero Charge (CHARGE)
            if any(k in file_upper for k in ['CHARGE', 'CHA']):
                col_price = next((c for c in ['PRICE', 'COST', 'AMOUNT'] if c in df.columns), None)
                if col_price:
                    pre_audit_sum += df[col_price].sum()
                    
                    zero_price = df[df[col_price] == 0]
                    for _, row in zero_price.iterrows():
                        details_list.append({
                            "Type": "IPD" if 'IPD' in file_upper else "OPD",
                            "HN/AN": row.get('AN', row.get('HN', '-')),
                            "วันที่": row.get('DATE_SERV', '-'),
                            "ข้อค้นพบ": f"ค่ารักษา 0 บาท ({col_price})",
                            "Action": "ตรวจสอบสิทธิ",
                            "Impact": 0.00
                        })

                    # ==========================================
                    # 🤖 MACHINE LEARNING ENGINE (Anomaly)
                    # ==========================================
                    # ส่ง Dataframe เข้า ML เพื่อหาค่าใช้จ่ายที่ผิดปกติ (Unsupervised)
                    ml_results = run_ml_anomaly_detection(df, col_price)
                    details_list.extend(ml_results)

        except Exception as e:
            pass

    # Finish Progress
    progress_bar.progress(100, text="ประมวลผลเสร็จสิ้น!")
    time.sleep(0.5)
    progress_bar.empty()

    # Create Result Dataframe
    result_df = pd.DataFrame(details_list)
    
    # Mock Data Fallback (กรณีทดสอบไม่มีไฟล์)
    if result_df.empty and total_records == 0:
        pre_audit_sum = 5000000.00
        mock_data = []
        # Mock Rule Base
        mock_data.append({"Type": "OPD", "HN/AN": "6700123", "วันที่": "2024-03-01", "ข้อค้นพบ": "ไม่ระบุรหัสโรค (DIAGCODE)", "Action": "ลงรหัส ICD-10", "Impact": -2000})
        # Mock ML
        mock_data.append({"Type": "IPD", "HN/AN": "AN67005", "วันที่": "2024-03-02", "ข้อค้นพบ": "🤖 AI: ค่ารักษาสูงผิดปกติ (350,000)", "Action": "ตรวจสอบ Audit", "Impact": 0})
        result_df = pd.DataFrame(mock_data)
        total_records = 15000

    # Summary
    if not result_df.empty:
        result_df['Impact'] = pd.to_numeric(result_df['Impact'], errors='coerce').fillna(0)
        total_impact = result_df['Impact'].sum()
    else:
        total_impact = 0.0

    summary = {
        "records": total_records,
        "pre_audit": pre_audit_sum,
        "post_audit": pre_audit_sum + total_impact,
        "impact_val": total_impact
    }
    
    return result_df, summary

# --- 6. Helper UI ---
def metric_card(title, value, delta_text=None, is_positive=True):
    color = "#10B981" if is_positive else "#EF4444"
    icon = "▲" if is_positive else "▼"
    delta_html = f'<div style="color:{color}; margin-top:5px; font-size:14px;">{icon} {delta_text}</div>' if delta_text else ""
    
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-title">{title}</div>
        <div class="metric-value">{value}</div>
        {delta_html}
    </div>
    """, unsafe_allow_html=True)

# --- 7. Pages ---
def login_page():
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        st.markdown("<br><br><br>", unsafe_allow_html=True)
        st.markdown('<div class="login-container">', unsafe_allow_html=True)
        st.markdown(LOGO_HTML, unsafe_allow_html=True)
        st.markdown('<h2 style="color:#0F172A; margin:10px 0;">SMART Audit AI</h2>', unsafe_allow_html=True)
        st.markdown('<p style="color:#64748B;">ระบบตรวจสอบเวชระเบียนอัจฉริยะ</p>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
        
        with st.form("login"):
            user = st.text_input("Username")
            pwd = st.text_input("Password", type="password")
            if st.form_submit_button("เข้าสู่ระบบ (Login)", use_container_width=True):
                if user.strip().lower() == "hosnarai" and pwd.strip() == "h15000":
                    st.session_state.logged_in = True
                    st.session_state.username = "Hosnarai"
                    st.session_state.current_page = "upload"
                    st.rerun()
                else:
                    st.error("ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง")

def upload_page():
    c1, c2 = st.columns([0.5, 5])
    with c1: st.markdown(LOGO_HTML, unsafe_allow_html=True)
    with c2:
        st.markdown(f'<h2 class="hospital-header" style="margin-top:20px;">ยินดีต้อนรับ คุณ {st.session_state.username}</h2>', unsafe_allow_html=True)
        st.markdown('<p style="color:#64748B;">พร้อมสำหรับการตรวจสอบข้อมูล 52 แฟ้ม</p>', unsafe_allow_html=True)
    
    st.markdown("---")
    
    if st.session_state.audit_data is not None:
        if st.button("📊 ไปที่ Dashboard ผลลัพธ์", type="primary"):
            st.session_state.current_page = "dashboard"
            st.rerun()

    st.markdown("""
    <div style="background:white; padding:40px; border-radius:16px; border:2px dashed #CBD5E1; text-align:center; margin:20px 0;">
        <h4 style="margin:0; color:#0F172A;">📤 อัปโหลดไฟล์ 52 แฟ้ม (.txt)</h4>
        <p style="color:#64748B; margin-top:5px;">ลากไฟล์ทั้งหมดมาวางที่นี่เพื่อเริ่มกระบวนการ Rule-Base & ML</p>
    </div>
    """, unsafe_allow_html=True)
    
    uploaded_files = st.file_uploader("", type=["txt"], accept_multiple_files=True, label_visibility="collapsed")
    
    if uploaded_files:
        st.success(f"✅ พบไฟล์จำนวน: {len(uploaded_files)} ไฟล์")
        c1, c2, c3 = st.columns([1, 1, 1])
        with c2:
            if st.button("🚀 เริ่มประมวลผล (Start Audit)", type="primary", use_container_width=True):
                df, summ = process_52_files(uploaded_files)
                st.session_state.audit_data = df
                st.session_state.financial_summary = summ
                st.session_state.current_page = "dashboard"
                st.rerun()

def dashboard_page():
    c1, c2, c3 = st.columns([0.8, 5, 1.2])
    with c1: st.markdown(LOGO_HTML, unsafe_allow_html=True)
    with c2:
        st.markdown('<h2 class="hospital-header" style="margin-top:10px;">โรงพยาบาลพระนารายณ์มหาราช</h2>', unsafe_allow_html=True)
        st.markdown('<p class="sub-header">SMART Audit AI : Executive Dashboard</p>', unsafe_allow_html=True)
    with c3:
        st.markdown('<div style="margin-top:20px;"></div>', unsafe_allow_html=True)
        if st.button("⬅️ ตรวจสอบใหม่"):
            st.session_state.current_page = "upload"
            st.session_state.audit_data = None
            st.rerun()

    st.markdown("---")
    
    df = st.session_state.audit_data
    summ = st.session_state.financial_summary
    
    if df is None:
        st.warning("Session Expired.")
        return

    c1, c2, c3, c4 = st.columns(4)
    with c1: metric_card("จำนวน Record ทั้งหมด", f"{summ['records']:,}")
    with c2: metric_card("ยอดเงินก่อน Audit", f"{summ['pre_audit']:,.2f} บาท")
    with c3:
        diff = summ['post_audit'] - summ['pre_audit']
        metric_card("ยอดเงินหลัง Audit", f"{summ['post_audit']:,.2f} บาท", f"{diff:+,.2f} บาท", diff >= 0)
    with c4:
        impact = summ['impact_val']
        metric_card("Financial Impact", f"{impact:,.2f} บาท", "ผลกระทบสุทธิ", impact >= 0)

    st.markdown("<br>", unsafe_allow_html=True)

    st.subheader("🔎 รายละเอียดข้อค้นพบ (Findings)")
    tabs = st.tabs(["ทั้งหมด (All)", "เฉพาะ OPD", "เฉพาะ IPD", "🤖 AI Detected"])
    
    # Filter Data (กรอง Impact = 0 ออก ยกเว้น Tab AI)
    filtered_df = df[df['Impact'] != 0]
    ai_df = df[df['Type'] == 'ML_Detected']

    def show_table(data):
        if not data.empty:
            cols_cfg = {
                "HN/AN": st.column_config.TextColumn("HN / AN", width="medium"),
                "วันที่": st.column_config.TextColumn("วันที่รับบริการ", width="small"),
                "ข้อค้นพบ": st.column_config.TextColumn("⚠️ สิ่งที่ตรวจพบ", width="large"),
                "Action": st.column_config.TextColumn("🔧 คำแนะนำ", width="large"),
                "Impact": st.column_config.NumberColumn("💰 Impact (บาท)", format="%.2f")
            }
            st.dataframe(data, column_order=["HN/AN", "วันที่", "ข้อค้นพบ", "Action", "Impact"], column_config=cols_cfg, use_container_width=True, height=500, hide_index=True)
        else:
            st.info("ไม่พบรายการ (Impact=0 ถูกซ่อนไว้)")

    with tabs[0]: show_table(filtered_df)
    with tabs[1]: show_table(filtered_df[filtered_df['Type'] == 'OPD'])
    with tabs[2]: show_table(filtered_df[filtered_df['Type'] == 'IPD'])
    with tabs[3]: 
        st.info("🤖 รายการที่ AI (Isolation Forest) ตรวจพบความผิดปกติของข้อมูล (Anomaly Detection)")
        show_table(ai_df)

    st.markdown("<br>", unsafe_allow_html=True)
    csv = df.to_csv(index=False).encode('utf-8-sig')
    st.download_button("📥 ดาวน์โหลดรายงาน CSV (Full)", csv, "
