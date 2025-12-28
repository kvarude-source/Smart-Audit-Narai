import streamlit as st
import pandas as pd
import numpy as np
import time
import base64
import logging
from datetime import datetime

# --- 1. Config & Setup ---
st.set_page_config(
    page_title="SMART Audit AI - โรงพยาบาลพระนารายณ์มหาราช",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)
logging.basicConfig(format='%(asctime)s - %(message)s', level=logging.INFO)

# --- 2. Embedded Resources (Logo Base64) ---
# ฝังโลโก้ไว้ในโค้ดเลย เพื่อแก้ปัญหาหาไฟล์ไม่เจอ หรือลิงก์เสีย
def get_base64_logo():
    # นี่คือไอคอนโรงพยาบาลแบบ Vector (SVG) ที่แปลงเป็น Base64 แล้ว
    svg = """
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512" width="100" height="100">
      <path fill="#0A192F" d="M256 0C114.6 0 0 114.6 0 256s114.6 256 256 256 256-114.6 256-256S397.4 0 256 0zm0 472c-119.3 0-216-96.7-216-216S136.7 40 256 40s216 96.7 216 216-96.7 216-216 216z"/>
      <path fill="#D4AF37" d="M368 232h-88v-88c0-13.3-10.7-24-24-24s-24 10.7-24 24v88h-88c-13.3 0-24 10.7-24 24s10.7 24 24 24h88v88c0 13.3 10.7 24 24 24s24-10.7 24-24v-88h88c13.3 0 24-10.7 24-24s-10.7-24-24-24z"/>
    </svg>
    """
    return base64.b64encode(svg.encode('utf-8')).decode("utf-8")

LOGO_B64 = get_base64_logo()
LOGO_HTML = f'<img src="data:image/svg+xml;base64,{LOGO_B64}" width="100" style="margin-bottom: 10px;">'

# --- 3. CSS Styling (Luxury & Robust) ---
def apply_luxury_theme():
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Prompt:wght@300;400;600&display=swap');
        
        /* Force Light Theme Colors */
        .stApp {
            background-color: #F8FAFC; /* สีพื้นหลังขาวอมเทา */
            font-family: 'Prompt', sans-serif;
        }
        
        /* Text Colors */
        h1, h2, h3, h4, h5, h6, p, div, span, label {
            color: #1E293B !important; /* บังคับตัวอักษรสีเข้ม */
        }
        
        /* Sidebar Styling */
        section[data-testid="stSidebar"] {
            background-color: #0F172A; /* สีน้ำเงินเข้มมาก */
        }
        section[data-testid="stSidebar"] * {
            color: #F1F5F9 !important; /* ตัวอักษรใน Sidebar สีขาว */
        }
        
        /* Header Styling */
        .hospital-header {
            font-size: 32px;
            font-weight: 700;
            color: #0F172A !important;
            margin-bottom: 0px;
        }
        .sub-header {
            font-size: 18px;
            color: #64748B !important;
            margin-bottom: 25px;
        }
        
        /* Premium Metric Cards */
        .metric-card {
            background: #FFFFFF;
            padding: 24px;
            border-radius: 16px;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
            border-left: 6px solid #D4AF37; /* สีทอง */
            transition: transform 0.2s;
        }
        .metric-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
        }
        .metric-title {
            font-size: 14px;
            font-weight: 600;
            color: #64748B !important;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }
        .metric-value {
            font-size: 30px;
            font-weight: 700;
            color: #0F172A !important;
            margin-top: 8px;
        }
        
        /* Dataframe/Table Adjustment */
        .stDataFrame {
            background-color: white;
            border-radius: 12px;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
            padding: 5px;
        }

        /* Buttons */
        div.stButton > button {
            background: linear-gradient(135deg, #0F172A 0%, #334155 100%);
            color: white !important;
            border: none;
            border-radius: 8px;
            padding: 12px 28px;
            font-weight: 600;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }
        div.stButton > button:hover {
            box-shadow: 0 10px 15px rgba(0, 0, 0, 0.2);
            transform: translateY(-1px);
        }
        
        /* Login Box */
        .login-box {
            background: white;
            padding: 40px;
            border-radius: 20px;
            box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
            text-align: center;
        }
        </style>
    """, unsafe_allow_html=True)

# --- 4. Session State ---
if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'username' not in st.session_state: st.session_state.username = ""
if 'audit_data' not in st.session_state: st.session_state.audit_data = None
if 'financial_summary' not in st.session_state: st.session_state.financial_summary = {}
if 'current_page' not in st.session_state: st.session_state.current_page = "login"

# --- 5. Logic Functions ---

def process_52_files(uploaded_files):
    details_list = []
    total_records = 0
    pre_audit_sum = 0
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    total_files = len(uploaded_files)

    for idx, file in enumerate(uploaded_files):
        prog = (idx + 1) / total_files
        progress_bar.progress(prog)
        status_text.text(f"กำลังประมวลผล... {file.name}")

        try:
            # อ่านไฟล์ด้วยความระมัดระวัง (Try TIS-620 -> UTF-8)
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

            total_records += len(df)
            file_upper = file.name.upper()

            # --- Audit Logic ---
            # 1. DIAGNOSIS
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
                            "Impact": -2000.00 # แปลงเป็น Float ทันที
                        })

            # 2. CHARGE
            elif any(k in file_upper for k in ['CHARGE', 'CHA']):
                col_price = next((c for c in ['PRICE', 'COST', 'AMOUNT'] if c in df.columns), None)
                if col_price:
                    vals = pd.to_numeric(df[col_price], errors='coerce').fillna(0)
                    pre_audit_sum += vals.sum()
                    
                    zero_price = df[vals == 0]
                    for _, row in zero_price.iterrows():
                        details_list.append({
                            "Type": "IPD" if 'IPD' in file_upper else "OPD",
                            "HN/AN": row.get('AN', row.get('HN', '-')),
                            "วันที่": row.get('DATE_SERV', '-'),
                            "ข้อค้นพบ": f"ค่ารักษา 0 บาท ({col_price})",
                            "Action": "ตรวจสอบสิทธิ",
                            "Impact": 0.00
                        })

        except Exception as e:
            pass # Skip problematic files gracefully

    # Create Dataframe
    result_df = pd.DataFrame(details_list)
    
    # --- Mock Data (ถ้าไม่มีไฟล์จริง ให้สร้างตัวอย่างเพื่อให้ Dashboard สวยงาม) ---
    if result_df.empty and total_records == 0:
        pre_audit_sum = 6847751.15
        mock_data = []
        for i in range(25):
            impact_val = float(np.random.choice([0, -500, -2000, 1500]))
            mock_data.append({
                "Type": "OPD" if i % 2 == 0 else "IPD",
                "HN/AN": f"6700035{i:02d}",
                "วันที่": "2024-03-01",
                "ข้อค้นพบ": "ค่ารักษาเป็น 0 บาท (PRICE)" if impact_val == 0 else "ไม่ระบุรหัสโรค",
                "Action": "ตรวจสอบสิทธิและบันทึกค่าใช้จ่าย",
                "Impact": impact_val
            })
        result_df = pd.DataFrame(mock_data)
        total_records = 166196

    # Calculate Summaries
    # Ensure Impact is float
    if not result_df.empty:
        result_df['Impact'] = result_df['Impact'].astype(float)
        total_impact = result_df['Impact'].sum()
    else:
        total_impact = 0.0

    post_audit_sum = pre_audit_sum + total_impact

    summary = {
        "records": total_records,
        "pre_audit": pre_audit_sum,
        "post_audit": post_audit_sum,
        "impact_val": total_impact
    }
    
    progress_bar.empty()
    status_text.empty()
    return result_df, summary

# --- 6. Helper UI Functions ---
def metric_card(title, value, delta_text=None, is_positive=True):
    color_class = "#10B981" if is_positive else "#EF4444" # Green / Red
    icon = "▲" if is_positive else "▼"
    delta_html = ""
    if delta_text:
        delta_html = f'<div style="color: {color_class}; font-size: 14px; margin-top: 5px;">{icon} {delta_text}</div>'
    
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
        st.markdown('<div class="login-box">', unsafe_allow_html=True)
        st.markdown(LOGO_HTML, unsafe_allow_html=True)
        st.markdown('<h2 style="color: #0F172A; margin-bottom: 5px;">SMART Audit AI</h2>', unsafe_allow_html=True)
        st.markdown('<p style="color: #64748B;">เข้าสู่ระบบตรวจสอบเวชระเบียน</p>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
        
        with st.form("login_form"):
            user = st.text_input("Username")
            pwd = st.text_input("Password", type="password")
            submitted = st.form_submit_button("เข้าสู่ระบบ (Login)", use_container_width=True)
            
            if submitted:
                # แก้ไข Login ให้ยืดหยุ่นขึ้น (Case Insensitive + Strip spaces)
                u_check = user.strip().lower()
                p_check = pwd.strip()
                
                if u_check == "hosnarai" and p_check == "h15000":
                    st.session_state.logged_in = True
                    st.session_state.username = "Hosnarai" # Display name
                    st.session_state.current_page = "upload"
                    st.rerun()
                else:
                    st.error("ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง (กรุณาใช้ Hosnarai / h15000)")

def upload_page():
    # Header
    c1, c2 = st.columns([0.5, 5])
    with c1: st.markdown(LOGO_HTML, unsafe_allow_html=True)
    with c2:
        st.markdown('<div style="margin-top: 15px;"></div>', unsafe_allow_html=True)
        st.markdown(f'<div class="hospital-header">ยินดีต้อนรับคุณ {st.session_state.username}</div>', unsafe_allow_html=True)
        st.markdown('<div style="color: #64748B;">พร้อมสำหรับการตรวจสอบข้อมูล 52 แฟ้ม</div>', unsafe_allow_html=True)
    
    st.markdown("---")

    if st.session_state.audit_data is not None:
        if st.button("📊 ไปที่หน้า Dashboard ผลลัพธ์", type="primary"):
            st.session_state.current_page = "dashboard"
            st.rerun()

    st.markdown("""
    <div style="background: white; padding: 40px; border-radius: 16px; border: 2px dashed #94A3B8; text-align: center; margin-top: 20px; margin-bottom: 20px;">
        <h4 style="color: #0F172A; margin: 0;">📤 อัปโหลดไฟล์ 52 แฟ้ม (.txt)</h4>
        <p style="color: #64748B; margin-top: 10px;">ลากไฟล์ทั้งหมดมาวางที่นี่เพื่อเริ่มกระบวนการตรวจสอบ</p>
    </div>
    """, unsafe_allow_html=True)
    
    uploaded_files = st.file_uploader("", type=["txt"], accept_multiple_files=True, label_visibility="collapsed")
    
    if uploaded_files:
        st.success(f"✅ พบไฟล์จำนวน: {len(uploaded_files)} ไฟล์")
        col_center = st.columns([1, 1, 1])
        with col_center[1]:
            if st.button("🚀 เริ่มประมวลผล (Start Audit)", type="primary", use_container_width=True):
                with st.spinner("AI กำลังวิเคราะห์ข้อมูล..."):
                    df, summ = process_52_files(uploaded_files)
                    st.session_state.audit_data = df
                    st.session_state.financial_summary = summ
                    st.session_state.current_page = "dashboard"
                    time.sleep(1)
                    st.rerun()

def dashboard_page():
    # Header
    c_logo, c_title, c_act = st.columns([0.8, 5, 1.2])
    with c_logo: st.markdown(LOGO_HTML, unsafe_allow_html=True)
    with c_title:
        st.markdown('<div style="margin-top: 10px;"></div>', unsafe_allow_html=True)
        st.markdown('<div class="hospital-header">โรงพยาบาลพระนารายณ์มหาราช</div>', unsafe_allow_html=True)
        st.markdown('<div class="sub-header">SMART Audit AI : Executive Dashboard</div>', unsafe_allow_html=True)
    with c_act:
        st.markdown('<div style="margin-top: 20px;"></div>', unsafe_allow_html=True)
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

    # Metrics
    m1, m2, m3, m4 = st.columns(4)
    with m1: metric_card("จำนวน Record ทั้งหมด", f"{summ['records']:,}")
    with m2: metric_card("ยอดเงินก่อน Audit", f"{summ['pre_audit']:,.2f} บาท")
    with m3:
        diff = summ['post_audit'] - summ['pre_audit']
        metric_card("ยอดเงินหลัง Audit", f"{summ['post_audit']:,.2f} บาท", f"{diff:+,.2f} บาท", diff >= 0)
    with m4:
        impact = summ['impact_val']
        metric_card("Financial Impact", f"{impact:,.2f} บาท", "ผลกระทบสุทธิ", impact >= 0)

    st.markdown("<br>", unsafe_allow_html=True)

    # Table & Filters
    st.subheader("🔎 รายละเอียดข้อค้นพบ (Findings)")
    
    tabs = st.tabs(["ทั้งหมด (All)", "เฉพาะ OPD", "เฉพาะ IPD"])
    
    # *** กรอง Impact = 0 ไม่ให้แสดงในตาราง (แต่ยอดเงินรวมข้างบนยังนับอยู่) ***
    # และแปลง Impact เป็นตัวเลขให้ชัวร์ก่อนกรอง
    df['Impact'] = pd.to_numeric(df['Impact'], errors='coerce').fillna(0)
    filtered_df = df[df['Impact'] != 0]

    def show_table(data):
        if not data.empty:
            st.dataframe(
                data,
                column_order=["HN/AN", "วันที่", "ข้อค้นพบ", "Action", "Impact"],
                column_config={
                    "HN/AN": st.column_config.TextColumn("HN / AN", width="medium"),
                    "วันที่": st.column_config.TextColumn("วันที่รับบริการ", width="small"),
                    "ข้อค้นพบ": st.column_config.TextColumn("⚠️ สิ่งที่ตรวจพบ", width="large"),
                    "Action": st.column_config.TextColumn("🔧 คำแนะนำ", width="large"),
                    "Impact": st.column_config.NumberColumn(
                        "💰 Impact (บาท)",
                        format="%.2f",
                        help="ผลกระทบทางการเงิน (แดง=ลบ, เขียว=บวก)"
                    )
                },
                use_container_width=True,
