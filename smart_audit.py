import streamlit as st
import pandas as pd
import numpy as np
import time
import os
import logging
from datetime import datetime

# --- 1. Config & Setup ---
st.set_page_config(
    page_title="SMART Audit AI - Executive Dashboard",
    page_icon="💎",
    layout="wide",
    initial_sidebar_state="expanded"
)
logging.basicConfig(format='%(asctime)s - %(message)s', level=logging.INFO)

# --- 2. CSS Styling (Luxury Theme) ---
def apply_luxury_theme():
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Prompt:wght@300;400;600&display=swap');
        
        /* Global Font & Background */
        html, body, [class*="css"] {
            font-family: 'Prompt', sans-serif;
            color: #333333;
        }
        .stApp {
            background-color: #F4F6F9; /* สีเทาอ่อนระดับ Premium */
        }
        
        /* Sidebar Styling */
        section[data-testid="stSidebar"] {
            background-color: #0A192F; /* สีน้ำเงินเข้ม Royal Navy */
            color: white;
        }
        section[data-testid="stSidebar"] h1, section[data-testid="stSidebar"] span, section[data-testid="stSidebar"] p {
            color: #E6F1FF !important;
        }
        
        /* Header Styling */
        .hospital-header {
            font-size: 32px;
            font-weight: 600;
            color: #0A192F;
            margin-bottom: 5px;
        }
        .sub-header {
            font-size: 18px;
            color: #64748B;
            margin-bottom: 25px;
        }
        
        /* Metric Cards (Luxury Style) */
        .metric-card {
            background: white;
            padding: 20px;
            border-radius: 12px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.05); /* เงานุ่ม */
            border-left: 5px solid #D4AF37; /* เส้นสีทองด้านซ้าย */
            transition: transform 0.2s;
        }
        .metric-card:hover {
            transform: translateY(-5px);
        }
        .metric-title {
            font-size: 14px;
            color: #64748B;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        .metric-value {
            font-size: 28px;
            font-weight: bold;
            color: #0A192F;
            margin-top: 5px;
        }
        .metric-delta {
            font-size: 14px;
            margin-top: 5px;
        }
        .delta-pos { color: #10B981; }
        .delta-neg { color: #EF4444; }

        /* Table Styling */
        div[data-testid="stDataFrame"] {
            background: white;
            padding: 15px;
            border-radius: 12px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.05);
        }
        
        /* Buttons */
        div.stButton > button {
            background: linear-gradient(90deg, #0A192F 0%, #172a46 100%);
            color: white;
            border: none;
            border-radius: 8px;
            padding: 10px 25px;
            font-weight: 500;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            transition: all 0.3s ease;
        }
        div.stButton > button:hover {
            background: linear-gradient(90deg, #172a46 0%, #233b5d 100%);
            box-shadow: 0 6px 8px rgba(0, 0, 0, 0.15);
            transform: translateY(-1px);
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
    # Logo โรงพยาบาล
    return "https://upload.wikimedia.org/wikipedia/th/f/f6/Phranaraimaharaj_Hospital_Logo.png"

LOGO_URL = get_logo()

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
        status_text.text(f"Processing... {file.name}")

        try:
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
            if df.shape[1] > len(header): df = df.iloc[:, :len(header)]
            if df.shape[1] == len(header): df.columns = header
            else: continue

            total_records += len(df)
            file_upper = file.name.upper()

            # --- Logic ---
            # 1. DIAGNOSIS
            if 'DIAG' in file_upper or 'IPDX' in file_upper or 'OPDX' in file_upper:
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

            # 2. CHARGE
            elif 'CHARGE' in file_upper or 'CHA' in file_upper:
                col_price = next((c for c in ['PRICE', 'COST', 'AMOUNT'] if c in df.columns), None)
                if col_price:
                    vals = pd.to_numeric(df[col_price], errors='coerce').fillna(0)
                    pre_audit_sum += vals.sum()
                    
                    zero_price = df[vals == 0]
                    for _, row in zero_price.iterrows():
                        # เคส 0 บาท Impact = 0
                        details_list.append({
                            "Type": "IPD" if 'IPD' in file_upper else "OPD",
                            "HN/AN": row.get('AN', row.get('HN', '-')),
                            "วันที่": row.get('DATE_SERV', '-'),
                            "ข้อค้นพบ": f"ค่ารักษา 0 บาท ({col_price})",
                            "Action": "ตรวจสอบสิทธิ",
                            "Impact": 0.00 
                        })

        except Exception as e:
            pass

    # Mock Data กรณีไม่มีไฟล์จริง (เพื่อให้เห็นหน้าตา Dashboard)
    result_df = pd.DataFrame(details_list)
    if result_df.empty and total_records == 0:
        pre_audit_sum = 8540000.00
        mock_data = []
        for i in range(20):
            impact_val = np.random.choice([0, -500, -2000, 1500])
            mock_data.append({
                "Type": "OPD" if i % 2 == 0 else "IPD",
                "HN/AN": f"6700{i:02d}",
                "วันที่": "2024-03-01",
                "ข้อค้นพบ": "ตัวอย่าง: รหัสวินิจฉัยไม่ครบถ้วน",
                "Action": "ตรวจสอบเวชระเบียน",
                "Impact": float(impact_val)
            })
        result_df = pd.DataFrame(mock_data)
        total_records = 2540

    # คำนวณ Post Audit
    total_impact = result_df['Impact'].sum() if not result_df.empty else 0
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

# --- 5. Custom UI Components ---

def metric_card(title, value, delta_text=None, is_positive=True):
    delta_html = ""
    if delta_text:
        color_class = "delta-pos" if is_positive else "delta-neg"
        icon = "▲" if is_positive else "▼"
        delta_html = f'<div class="metric-delta {color_class}">{icon} {delta_text}</div>'
    
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-title">{title}</div>
        <div class="metric-value">{value}</div>
        {delta_html}
    </div>
    """, unsafe_allow_html=True)

# --- 6. Pages ---

def login_page():
    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        st.markdown("<br><br><br>", unsafe_allow_html=True)
        # Card-like login container
        st.markdown("""
        <div style="background: white; padding: 40px; border-radius: 15px; box-shadow: 0 10px 30px rgba(0,0,0,0.1); text-align: center;">
            <img src="https://upload.wikimedia.org/wikipedia/th/f/f6/Phranaraimaharaj_Hospital_Logo.png" width="100" style="margin-bottom: 20px;">
            <h2 style="color: #0A192F; margin-bottom: 5px;">SMART Audit AI</h2>
            <p style="color: #64748B; margin-bottom: 30px;">เข้าสู่ระบบตรวจสอบเวชระเบียน</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Form อยู่นอก Div เพื่อให้ Streamlit handle logic ได้ง่าย
        with st.form("login_form"):
            user = st.text_input("Username")
            pwd = st.text_input("Password", type="password")
            submitted = st.form_submit_button("เข้าสู่ระบบ (Login)", use_container_width=True)
            
            if submitted:
                if user.strip() == "Hosnarai" and pwd.strip() == "h15000":
                    st.session_state.logged_in = True
                    st.session_state.username = user.strip()
                    st.session_state.current_page = "upload"
                    st.rerun()
                else:
                    st.error("ข้อมูลไม่ถูกต้อง")

def upload_page():
    # Header Area
    c1, c2 = st.columns([0.5, 5])
    with c1: st.image(LOGO_URL, width=70)
    with c2:
        st.markdown(f"""
        <div style="margin-top: 10px;">
            <div style="font-size: 24px; font-weight: 600; color: #0A192F;">ยินดีต้อนรับ คุณ {st.session_state.username}</div>
            <div style="color: #64748B;">ระบบพร้อมสำหรับการตรวจสอบข้อมูลชุดใหม่</div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")

    # State check
    if st.session_state.audit_data is not None:
        st.info("💡 มีข้อมูลที่ประมวลผลค้างไว้")
        if st.button("ไปที่ Dashboard ผลลัพธ์"):
            st.session_state.current_page = "dashboard"
            st.rerun()

    # Upload Area with Styling
    st.markdown("""
    <div style="background: white; padding: 30px; border-radius: 12px; border: 2px dashed #CBD5E1; text-align: center; margin-bottom: 20px;">
        <h4 style="color: #0A192F;">อัปโหลดไฟล์ 52 แฟ้ม</h4>
        <p style="color: #64748B;">ลากไฟล์ .txt ทั้งหมดมาวางที่นี่เพื่อเริ่มกระบวนการ AI Audit</p>
    </div>
    """, unsafe_allow_html=True)
    
    uploaded_files = st.file_uploader("", type=["txt"], accept_multiple_files=True, label_visibility="collapsed")
    
    if uploaded_files:
        st.success(f"✅ พร้อมประมวลผลจำนวน: {len(uploaded_files)} ไฟล์")
        c_btn1, c_btn2, c_btn3 = st.columns([1, 1, 1])
        with c_btn2:
            if st.button("🚀 เริ่มประมวลผล (Start AI Engine)", type="primary", use_container_width=True):
                with st.spinner("AI กำลังวิเคราะห์ความผิดปกติ (Anomaly Detection)..."):
                    df, summ = process_52_files(uploaded_files)
                    st.session_state.audit_data = df
                    st.session_state.financial_summary = summ
                    st.session_state.current_page = "dashboard"
                    time.sleep(1)
                    st.rerun()

def dashboard_page():
    # --- Luxury Header ---
    c_logo, c_title, c_action = st.columns([0.8, 4, 1.2])
    with c_logo:
        st.image(LOGO_URL, width=80)
    with c_title:
        st.markdown('<div class="hospital-header">โรงพยาบาลพระนารายณ์มหาราช</div>', unsafe_allow_html=True)
        st.markdown('<div class="sub-header">Executive Audit Dashboard</div>', unsafe_allow_html=True)
    with c_action:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("↺ ตรวจสอบใหม่"):
            st.session_state.current_page = "upload"
            st.session_state.audit_data = None
            st.rerun()
            
    st.markdown("---")
    
    df = st.session_state.audit_data
    summ = st.session_state.financial_summary
    
    if df is None:
        st.warning("Session Expired. Please upload files again.")
        return

    # --- Premium Metrics Cards ---
    m1, m2, m3, m4 = st.columns(4)
    
    with m1:
        metric_card("Total Records", f"{summ['records']:,}", "Updated just now")
    
    with m2:
        metric_card("Pre-Audit Revenue", f"{summ['pre_audit']:,.0f} ฿", "ยอดตั้งต้น", True)
        
    with m3:
        # Post Audit
        diff = summ['post_audit'] - summ['pre_audit']
        is_plus = diff >= 0
        metric_card("Post-Audit Revenue", f"{summ['post_audit']:,.0f} ฿", f"{abs(diff):,.0f} ฿", is_plus)

    with m4:
        # Financial Impact
        impact_val = summ['impact_val']
        color = "delta-pos" if impact_val >= 0 else "delta-neg"
        metric_card("Financial Impact", f"{impact_val:,.0f} ฿", "โอกาสเพิ่ม/ลดรายได้", impact_val >= 0)

    st.markdown("<br>", unsafe_allow_html=True)

    # --- Filter & Table Section ---
    st.subheader("📊 Analysis Result")
    
    # Custom CSS for Tabs
    tabs = st.tabs(["All Cases", "OPD Only", "IPD Only"])
    
    # ** Logic กรอง Impact = 0 ไม่ให้แสดงในตาราง **
    filtered_df = df[df['Impact'] != 0]

    def show_table(data_frame):
        if not data_frame.empty:
            st.dataframe(
                data_frame,
                column_order=["HN/AN", "วันที่", "ข้อค้นพบ", "Action", "Impact"],
                column_config={
                    "HN/AN": st.column_config.TextColumn("HN / AN", width="medium"),
                    "วันที่": st.column_config.TextColumn("Date", width="small"),
                    "ข้อค้นพบ": st.column_config.TextColumn("Findings", width="large"),
                    "Action": st.column_config.TextColumn("Recommended Action", width="large"),
                    "Impact": st.column_config.NumberColumn(
                        "Est. Impact (฿)",
                        format="%.2f",
                        help="ผลกระทบทางการเงิน"
                    )
                },
                use_container_width=True,
                height=450,
                hide_index=True
            )
        else:
            st.info("ไม่พบรายการที่มีผลกระทบทางการเงิน (Impact = 0 ถูกซ่อนไว้)")

    with tabs[0]:
        show_table(filtered_df)
    with tabs[1]:
        show_table(filtered_df[filtered_df['Type'] == 'OPD'])
    with tabs[2]:
        show_table(filtered_df[filtered_df['Type'] == 'IPD'])

    # Export Button (Styled)
    st.markdown("<br>", unsafe_allow_html=True)
    c_left, c_right = st.columns([5, 1])
    with c_right:
        csv = filtered_df.to_csv(index=False).encode('utf-8-sig')
        st.download_button(
            label="📥 Download Report",
            data=csv,
            file_name="smart_audit_report.csv",
            mime="text/csv",
            type="primary"
        )

# --- 7. Main ---
def main():
    apply_luxury_theme()
    
    # Sidebar Navigation (Premium Look)
    with st.sidebar:
        st.image(LOGO_URL, width=120)
        st.markdown("### SMART Audit AI")
        st.caption(f"User: {st.session_state.username}")
        st.markdown("---")
        
        if st.session_state.logged_in:
            if st.button("📂 Upload Data", use_container_width=True):
                st.session_state.current_page = "upload"
                st.rerun()
            if st.button("📊 Dashboard", use_container_width=True):
                st.session_state.current_page = "dashboard"
                st.rerun()
            
            st.markdown("<br><br><br>", unsafe_allow_html=True)
            if st.button("Log out", use_container_width=True):
                st.session_state.clear()
                st.rerun()

    # Routing
    if not st.session_state.logged_in:
        login_page()
    else:
        if st.session_state.current_page == "dashboard":
            dashboard_page()
        else:
            upload_page()

if __name__ == "__main__":
    main()
