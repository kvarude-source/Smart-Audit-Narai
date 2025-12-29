import streamlit as st
import pandas as pd
import numpy as np
import time
import base64
import logging
from datetime import datetime

# --- Import ML (Optional) ---
try:
    from sklearn.ensemble import IsolationForest
    HAS_ML = True
except ImportError:
    HAS_ML = False

# --- 1. Config & Setup ---
st.set_page_config(
    page_title="SMART Audit AI - Executive",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- 2. Resources (Logo) ---
def get_base64_logo():
    # Logo SVG (Premium Navy/Gold)
    svg = """
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512" width="100" height="100">
      <path fill="#0F172A" d="M256 0C114.6 0 0 114.6 0 256s114.6 256 256 256 256-114.6 256-256S397.4 0 256 0zm0 472c-119.3 0-216-96.7-216-216S136.7 40 256 40s216 96.7 216 216-96.7 216-216 216z"/>
      <path fill="#D4AF37" d="M368 232h-88v-88c0-13.3-10.7-24-24-24s-24 10.7-24 24v88h-88c-13.3 0-24 10.7-24 24s10.7 24 24 24h88v88c0 13.3 10.7 24 24 24s24-10.7 24-24v-88h88c13.3 0 24-10.7 24-24s-10.7-24-24-24z"/>
    </svg>
    """
    return base64.b64encode(svg.encode('utf-8')).decode("utf-8")

LOGO_HTML = f'<img src="data:image/svg+xml;base64,{get_base64_logo()}" width="90" style="vertical-align:middle; margin-right:15px;">'

# --- 3. CSS Styling (Ultra Premium & Large Font) ---
def apply_theme():
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Prompt:wght@300;400;500;700&display=swap');
        
        /* 1. Global Font Upsizing (ขยายฟอนต์ทั้งระบบ) */
        html, body, [class*="css"] {
            font-family: 'Prompt', sans-serif;
            font-size: 18px !important; /* เพิ่มขนาดฐาน */
            color: #1E293B; /* สีน้ำเงินเข้ม */
        }
        
        /* 2. Background Clean White/Blue */
        .stApp {
            background-color: #F8FAFC;
        }
        
        /* 3. Headers (ใหญ่และชัด) */
        h1 { font-size: 3rem !important; font-weight: 700 !important; color: #0F172A !important; }
        h2 { font-size: 2.2rem !important; font-weight: 700 !important; color: #0F172A !important; }
        h3 { font-size: 1.8rem !important; font-weight: 600 !important; color: #1E293B !important; }
        p { font-size: 1.1rem !important; color: #475569 !important; }
        
        /* 4. Input Fields (แก้สีดำให้เป็นขาวสะอาด) */
        .stTextInput input, .stPasswordInput input {
            background-color: #FFFFFF !important;
            color: #0F172A !important;
            border: 2px solid #E2E8F0 !important;
            border-radius: 10px !important;
            padding: 15px !important;
            font-size: 18px !important;
        }
        .stTextInput input:focus, .stPasswordInput input:focus {
            border-color: #D4AF37 !important; /* Focus สีทอง */
            box-shadow: 0 0 0 2px rgba(212, 175, 55, 0.2) !important;
        }
        /* Label ของ Input */
        .stTextInput label, .stPasswordInput label {
            font-size: 18px !important;
            font-weight: 600 !important;
            color: #1E293B !important;
        }
        
        /* 5. Buttons (ใหญ่ พรีเมี่ยม) */
        div.stButton > button {
            background: linear-gradient(135deg, #0F172A 0%, #1E293B 100%) !important;
            color: #FFFFFF !important;
            border: none !important;
            border-radius: 12px !important;
            padding: 12px 32px !important;
            font-size: 20px !important; /* ตัวหนังสือปุ่มใหญ่ */
            font-weight: 600 !important;
            box-shadow: 0 4px 15px rgba(15, 23, 42, 0.2) !important;
            transition: all 0.3s ease !important;
        }
        div.stButton > button:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 20px rgba(15, 23, 42, 0.3) !important;
        }
        
        /* 6. Metric Cards (การ์ดแสดงผล) */
        .metric-card {
            background: white;
            padding: 25px;
            border-radius: 16px;
            box-shadow: 0 10px 25px -5px rgba(0,0,0,0.05);
            border-left: 8px solid #0F172A;
            transition: transform 0.2s;
        }
        .metric-card:hover { transform: scale(1.02); }
        .metric-title { font-size: 16px; color: #64748B; font-weight: 600; letter-spacing: 0.5px; }
        .metric-value { font-size: 36px; color: #0F172A; font-weight: 800; margin-top: 10px; }
        .metric-sub { font-size: 14px; font-weight: 500; margin-top: 5px; }
        
        /* 7. Tabs (แถบเลือก) */
        .stTabs [data-baseweb="tab-list"] { gap: 8px; }
        .stTabs [data-baseweb="tab"] {
            height: 60px; /* สูงขึ้น */
            font-size: 20px !important; /* ตัวหนังสือใหญ่ */
            background-color: #F1F5F9;
            border-radius: 10px 10px 0 0;
            color: #64748B;
            font-weight: 600;
        }
        .stTabs [data-baseweb="tab"][aria-selected="true"] {
            background-color: #FFFFFF;
            color: #0F172A;
            border-top: 4px solid #D4AF37; /* แถบทองด้านบน */
        }
        
        /* 8. Table/Dataframe (พื้นขาว ตัวใหญ่) */
        [data-testid="stDataFrame"] {
            background-color: white !important;
            padding: 15px;
            border-radius: 15px;
            box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);
            font-size: 16px !important;
        }
        
        /* Login Box Specific */
        .login-box {
            background: white;
            padding: 50px;
            border-radius: 24px;
            box-shadow: 0 20px 50px rgba(0,0,0,0.1);
            border-top: 8px solid #D4AF37;
            text-align: center;
        }
        </style>
    """, unsafe_allow_html=True)

# --- 4. Session State ---
if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'audit_data' not in st.session_state: st.session_state.audit_data = None
if 'summary' not in st.session_state: st.session_state.summary = {}
if 'current_page' not in st.session_state: st.session_state.current_page = "login"

# --- 5. Logic Processing (Mock Logic) ---
def process_data_mock(uploaded_files):
    time.sleep(1.2) # Simulate calculation
    
    data = []
    pttypes = ['UCS (บัตรทอง)', 'OFC (ข้าราชการ)', 'SSS (ประกันสังคม)', 'LGO (อปท.)']
    
    # Generate Mock Data (High quality mock)
    for i in range(150):
        is_ipd = np.random.choice([True, False], p=[0.3, 0.7])
        hn = f"{np.random.randint(60000, 69999):05d}"
        an = f"{np.random.randint(10000, 19999):05d}" if is_ipd else "-"
        date_serv = f"2024-{np.random.randint(1,13):02d}-{np.random.randint(1,28):02d}"
        pttype = np.random.choice(pttypes)
        
        case_type = np.random.choice(['Normal', 'Overclaim', 'Underclaim'], p=[0.6, 0.25, 0.15])
        
        finding = "-"
        action = "-"
        impact = 0
        
        if case_type == 'Overclaim':
            finding = "วันจำหน่ายก่อนวันรับเข้า (Date Error)"
            action = "แก้ไขวันที่ (DATEDSC) ให้ถูกต้อง"
            impact = -1 * np.random.randint(1000, 10000)
        elif case_type == 'Underclaim':
            finding = "ไม่ได้ลงรหัสหัตถการ (Missing Proc)"
            action = "เพิ่มรหัสหัตถการ (ICD-9) เพื่อเบิกเพิ่ม"
            impact = np.random.randint(500, 5000)
            
        data.append({
            "HN": hn, "AN": an, "DATE": date_serv, "PTTYPE": pttype,
            "FINDING": finding, "ACTION": action, "IMPACT": impact,
            "TYPE": "IPD" if is_ipd else "OPD"
        })
        
    df = pd.DataFrame(data)
    pre_audit = 8500000.0
    net_impact = df['IMPACT'].sum()
    
    return df, {
        "records": 166196, 
        "pre_audit": pre_audit,
        "post_audit": pre_audit + net_impact,
        "impact": net_impact
    }

# --- 6. Helper UI ---
def render_metric(title, value, sub_text=None, is_impact=False):
    style_color = "color: #0F172A;" # Default Blue
    border_style = ""
    
    if is_impact:
        val_num = float(str(value).replace(',','').replace(' ฿','').replace('+',''))
        if val_num < 0:
            style_color = "color: #EF4444;" # Red
            sub_text = "▼ Overclaim (เสี่ยงเรียกคืน)"
            border_style = "border-left: 8px solid #EF4444;"
        elif val_num > 0:
            style_color = "color: #10B981;" # Green
            sub_text = "▲ Underclaim (เบิกเพิ่มได้)"
            border_style = "border-left: 8px solid #10B981;"
    
    st.markdown(f"""
    <div class="metric-card" style="{border_style}">
        <div class="metric-title">{title}</div>
        <div class="metric-value" style="{style_color}">{value}</div>
        <div class="metric-sub" style="{style_color}">{sub_text if sub_text else '&nbsp;'}</div>
    </div>
    """, unsafe_allow_html=True)

# --- 7. Pages ---

def login_page():
    c1, c2, c3 = st.columns([1, 1.5, 1])
    with c2:
        st.markdown("<br><br>", unsafe_allow_html=True)
        
        # Login Container
        st.markdown('<div class="login-box">', unsafe_allow_html=True)
        st.markdown(LOGO_HTML, unsafe_allow_html=True)
        st.markdown('<h1 style="margin-top:20px; font-size:2.5rem !important;">โรงพยาบาลพระนารายณ์มหาราช</h1>', unsafe_allow_html=True)
        st.markdown('<p style="font-size:1.2rem !important; margin-bottom:30px;">SMART Audit AI System</p>', unsafe_allow_html=True)
        
        # Form
        with st.form("login_form"):
            st.markdown('<div style="text-align:left; font-weight:bold; margin-bottom:5px;">Username</div>', unsafe_allow_html=True)
            user = st.text_input("Username", placeholder="ระบุชื่อผู้ใช้งาน", label_visibility="collapsed")
            
            st.markdown('<div style="text-align:left; font-weight:bold; margin-top:15px; margin-bottom:5px;">Password</div>', unsafe_allow_html=True)
            pwd = st.text_input("Password", type="password", placeholder="ระบุรหัสผ่าน", label_visibility="collapsed")
            
            st.markdown("<br>", unsafe_allow_html=True)
            submit = st.form_submit_button("เข้าสู่ระบบ (LOGIN)", use_container_width=True)
            
            if submit:
                if user.strip().lower() == "hosnarai" and pwd.strip() == "h15000":
                    st.session_state.logged_in = True
                    st.session_state.current_page = "upload" # ไปหน้า Upload ก่อนตาม Flow ปกติ
                    st.rerun()
                else:
                    st.error("ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง")
        
        st.markdown('</div>', unsafe_allow_html=True)

def upload_page():
    # Header
    c1, c2 = st.columns([4, 1])
    with c1:
        st.markdown(f"""
        <div style="display:flex; align-items:center;">
            {LOGO_HTML}
            <div>
                <h2 style="margin:0;">โรงพยาบาลพระนารายณ์มหาราช</h2>
                <p style="margin:0;">ระบบนำเข้าข้อมูลเพื่อการตรวจสอบ (Data Import)</p>
            </div>
        </div>
        """, unsafe_allow_html=True)
    with c2:
        st.markdown(f"<div style='text-align:right; padding-top:20px; font-size:18px;'>👤 <b>{st.session_state.username}</b></div>", unsafe_allow_html=True)

    st.markdown("---")
    
    # Upload Area Large
    st.markdown("""
    <div style="background:white; padding:60px; border-radius:20px; border:3px dashed #CBD5E1; text-align:center; margin-bottom:30px;">
        <h3 style="color:#0F172A; font-size:2rem;">📂 อัปโหลดไฟล์ 52 แฟ้ม</h3>
        <p style="font-size:1.2rem;">ลากไฟล์ทั้งหมดมาวางที่นี่เพื่อเริ่มการวิเคราะห์ด้วย AI</p>
    </div>
    """, unsafe_allow_html=True)
    
    uploaded_files = st.file_uploader("", type=["txt"], accept_multiple_files=True, label_visibility="collapsed")
    
    if uploaded_files:
        st.success(f"✅ พร้อมวิเคราะห์จำนวน {len(uploaded_files)} ไฟล์")
        c_a, c_b, c_c = st.columns([1, 1, 1])
        with c_b:
            if st.button("🚀 เริ่มวิเคราะห์ข้อมูล (Start Audit)", type="primary", use_container_width=True):
                with st.spinner("AI กำลังประมวลผลข้อมูล..."):
                    df, summ = process_data_mock(uploaded_files)
                    st.session_state.audit_data = df
                    st.session_state.summary = summ
                    st.session_state.current_page = "dashboard"
                    st.rerun()

def dashboard_page():
    # --- Header (Logo + Title + Re-Analyze Button) ---
    c_head1, c_head2 = st.columns([4, 1.2])
    with c_head1:
        st.markdown(f"""
        <div style="display:flex; align-items:center;">
            {LOGO_HTML}
            <div>
                <h1 style="margin:0;">โรงพยาบาลพระนารายณ์มหาราช</h1>
                <p style="margin:0; font-size:1.2rem;">SMART Audit AI : Executive Summary</p>
            </div>
        </div>
        """, unsafe_allow_html=True)
    with c_head2:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("↺ วิเคราะห์ใหม่", use_container_width=True):
            st.session_state.current_page = "upload"
            st.rerun()

    st.markdown("---")
    
    if st.session_state.audit_data is None:
        st.warning("กรุณาอัปโหลดข้อมูลก่อน")
        return

    # --- Metrics (Large Cards) ---
    summ = st.session_state.summary
    m1, m2, m3, m4 = st.columns(4)
    with m1: render_metric("จำนวน Record", f"{summ['records']:,}", "รายการทั้งหมด")
    with m2: render_metric("ยอดเงินก่อน Audit", f"{summ['pre_audit']:,.0f} ฿", "ยอดส่งเบิกตั้งต้น")
    with m3: render_metric("ยอดเงินหลัง Audit", f"{summ['post_audit']:,.0f} ฿", "ยอดที่คาดว่าจะได้")
    with m4: render_metric("Impact (ผลกระทบ)", f"{summ['impact']:+,.0f} ฿", is_impact=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # --- Tabs & Table ---
    st.subheader("🔎 รายละเอียดผลการตรวจสอบ (Audit Findings)")
    
    tabs = st.tabs(["📋 ALL (ทั้งหมด)", "🩺 OPD (ผู้ป่วยนอก)", "🛏️ IPD (ผู้ป่วยใน)"])
    
    df = st.session_state.audit_data
    df['HN_AN_SHOW'] = df.apply(lambda x: x['AN'] if x['TYPE'] == 'IPD' else x['HN'], axis=1)
    
    # Config Table (Big Font)
    table_cfg = {
        "HN_AN_SHOW": st.column_config.TextColumn("HN / AN", width="medium"),
        "DATE": st.column_config.TextColumn("วันที่รับบริการ", width="small"),
        "PTTYPE": st.column_config.TextColumn("สิทธิการรักษา", width="small"),
        "FINDING": st.column_config.TextColumn("⚠️ ข้อค้นพบ (Findings)", width="large"),
        "ACTION": st.column_config.TextColumn("🔧 คำแนะนำ (AI Action)", width="large"),
        "IMPACT": st.column_config.NumberColumn("💰 Impact", format="%.0f ฿")
    }
    col_order = ["HN_AN_SHOW", "DATE", "PTTYPE", "FINDING", "ACTION", "IMPACT"]

    def show_table(data_view):
        if not data_view.empty:
            # Sort by impact to show problems first
            data_view = data_view.sort_values(by="IMPACT", ascending=True)
            st.dataframe(
                data_view,
                column_order=col_order,
                column_config=table_cfg,
                use_container_width=True,
                height=600, # ตารางสูงขึ้น
                hide_index=True
            )
        else:
            st.info("ไม่พบรายการ")

    with tabs[0]: show_table(df)
    with tabs[1]: show_table(df[df['TYPE'] == 'OPD'])
    with tabs[2]: show_table(df[df['TYPE'] == 'IPD'])

    # --- Export Button ---
    st.markdown("<br>", unsafe_allow_html=True)
    c_left, c_right = st.columns([5, 1])
    with c_right:
        csv = df.to_csv(index=False).encode('utf-8-sig')
        st.download_button(
            label="📥 ส่งออก Excel (CSV)",
            data=csv,
            file_name="smart_audit_report.csv",
            mime="text/csv",
            type="primary",
            use_container_width=True
        )

# --- 8. Main ---
def main():
    apply_theme()
    if not st.session_state.logged_in:
        login_page()
    else:
        if st.session_state.current_page == "dashboard":
            dashboard_page()
        else:
            upload_page()

if __name__ == "__main__":
    main()
