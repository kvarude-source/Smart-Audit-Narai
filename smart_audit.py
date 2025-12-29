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
    page_icon="💎",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- 2. Resources (Logo) ---
def get_base64_logo():
    # SVG Logo (Navy/Gold)
    svg = """
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512" width="100" height="100">
      <path fill="#0F172A" d="M256 0C114.6 0 0 114.6 0 256s114.6 256 256 256 256-114.6 256-256S397.4 0 256 0zm0 472c-119.3 0-216-96.7-216-216S136.7 40 256 40s216 96.7 216 216-96.7 216-216 216z"/>
      <path fill="#D4AF37" d="M368 232h-88v-88c0-13.3-10.7-24-24-24s-24 10.7-24 24v88h-88c-13.3 0-24 10.7-24 24s10.7 24 24 24h88v88c0 13.3 10.7 24 24 24s24-10.7 24-24v-88h88c13.3 0 24-10.7 24-24s-10.7-24-24-24z"/>
    </svg>
    """
    return base64.b64encode(svg.encode('utf-8')).decode("utf-8")

LOGO_HTML = f'<img src="data:image/svg+xml;base64,{get_base64_logo()}" width="60" style="vertical-align:middle; margin-right:15px;">'

# --- 3. CSS Styling (C1 Style - Clean & Modern) ---
def apply_theme():
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Prompt:wght@300;400;500;600;700&display=swap');
        
        /* Global Font */
        html, body, [class*="css"] {
            font-family: 'Prompt', sans-serif;
            color: #334155; /* Slate 700 */
        }
        
        /* Background */
        .stApp {
            background-color: #F8FAFC; /* Slate 50 (Very light gray/blue) */
        }
        
        /* --- 1. PREMIUM CARD STYLE (Like C1.png) --- */
        .premium-card {
            background-color: #FFFFFF;
            border-radius: 16px;
            padding: 24px;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03);
            border: 1px solid #F1F5F9;
            text-align: center;
            height: 100%;
            transition: all 0.3s ease;
        }
        .premium-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
        }
        .card-icon {
            font-size: 24px;
            margin-bottom: 10px;
            display: inline-block;
            padding: 10px;
            border-radius: 50%;
            background-color: #F1F5F9;
        }
        .card-title {
            font-size: 14px;
            color: #64748B;
            font-weight: 600;
            margin-bottom: 5px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        .card-value {
            font-size: 28px;
            font-weight: 700;
            color: #0F172A;
            margin-bottom: 5px;
        }
        .card-sub {
            font-size: 13px;
            font-weight: 500;
        }
        
        /* --- 2. TAB STYLING FIX (High Contrast) --- */
        .stTabs [data-baseweb="tab-list"] {
            gap: 8px;
            background-color: transparent;
            margin-bottom: 20px;
        }
        .stTabs [data-baseweb="tab"] {
            height: 50px;
            background-color: #FFFFFF;
            border-radius: 8px;
            border: 1px solid #E2E8F0;
            color: #64748B; /* Text Color (Inactive) */
            font-weight: 600;
            font-size: 16px;
            padding: 0 24px;
        }
        .stTabs [data-baseweb="tab"]:hover {
            background-color: #F8FAFC;
            color: #0F172A;
        }
        .stTabs [data-baseweb="tab"][aria-selected="true"] {
            background-color: #0F172A !important; /* Active Background (Navy) */
            color: #FFFFFF !important; /* Active Text (White) */
            border: 1px solid #0F172A;
        }
        
        /* --- 3. TABLE STYLING --- */
        [data-testid="stDataFrame"] {
            background-color: #FFFFFF;
            padding: 20px;
            border-radius: 16px;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
            border: 1px solid #F1F5F9;
        }
        
        /* --- 4. BUTTONS --- */
        div.stButton > button {
            background-color: #0F172A;
            color: #FFFFFF !important;
            border-radius: 10px;
            font-weight: 600;
            padding: 12px 24px;
            border: none;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            transition: all 0.2s;
        }
        div.stButton > button:hover {
            background-color: #1E293B;
            box-shadow: 0 6px 8px rgba(0,0,0,0.15);
            transform: translateY(-1px);
        }
        
        /* Login Box */
        .login-box {
            background: white;
            padding: 40px;
            border-radius: 20px;
            box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1);
            text-align: center;
            border-top: 6px solid #D4AF37;
        }
        
        /* Headers */
        h1, h2, h3 { color: #0F172A !important; font-weight: 700 !important; }
        </style>
    """, unsafe_allow_html=True)

# --- 4. Session State ---
if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'username' not in st.session_state: st.session_state.username = ""
if 'audit_data' not in st.session_state: st.session_state.audit_data = None
if 'summary' not in st.session_state: st.session_state.summary = {}
if 'current_page' not in st.session_state: st.session_state.current_page = "login"

# --- 5. Mock Data Processing ---
def process_data_mock(uploaded_files):
    time.sleep(1.2)
    data = []
    pttypes = ['UCS (บัตรทอง)', 'OFC (ข้าราชการ)', 'SSS (ประกันสังคม)', 'LGO (อปท.)']
    
    for i in range(150):
        is_ipd = np.random.choice([True, False], p=[0.3, 0.7])
        hn = f"{np.random.randint(60000, 69999):05d}"
        an = f"{np.random.randint(10000, 19999):05d}" if is_ipd else "-"
        date_serv = f"2024-{np.random.randint(1,13):02d}-{np.random.randint(1,28):02d}"
        pttype = np.random.choice(pttypes)
        
        case_type = np.random.choice(['Normal', 'Overclaim', 'Underclaim'], p=[0.6, 0.25, 0.15])
        finding, action, impact = "-", "-", 0
        
        if case_type == 'Overclaim':
            finding = "วันจำหน่ายก่อนวันรับเข้า (Date Error)"
            action = "แก้ไขวันที่ (DATEDSC)"
            impact = -1 * np.random.randint(1000, 10000)
        elif case_type == 'Underclaim':
            finding = "ไม่ลงรหัสหัตถการ (Missing Proc)"
            action = "เพิ่มรหัสหัตถการ (ICD-9)"
            impact = np.random.randint(500, 5000)
            
        data.append({
            "HN": hn, "AN": an, "DATE": date_serv, "PTTYPE": pttype,
            "FINDING": finding, "ACTION": action, "IMPACT": impact,
            "TYPE": "IPD" if is_ipd else "OPD"
        })
        
    df = pd.DataFrame(data)
    pre = 8500000.0
    imp = df['IMPACT'].sum()
    return df, {"records": 166196, "pre_audit": pre, "post_audit": pre + imp, "impact": imp}

# --- 6. Helper UI (Card Component like c1.png) ---
def render_premium_card(title, value, sub_text=None, is_impact=False, icon="📊"):
    color_style = "color: #0F172A;"
    bg_icon = "#F1F5F9"
    
    if is_impact:
        val_num = float(str(value).replace(',','').replace(' ฿','').replace('+',''))
        if val_num < 0:
            color_style = "color: #EF4444;" # Red
            sub_text = "▼ Overclaim (เสี่ยงเรียกคืน)"
            bg_icon = "#FEF2F2"
            icon = "⚠️"
        elif val_num > 0:
            color_style = "color: #10B981;" # Green
            sub_text = "▲ Underclaim (เบิกเพิ่มได้)"
            bg_icon = "#F0FDF4"
            icon = "💰"
    
    st.markdown(f"""
    <div class="premium-card">
        <div class="card-icon" style="background-color: {bg_icon};">{icon}</div>
        <div class="card-title">{title}</div>
        <div class="card-value" style="{color_style}">{value}</div>
        <div class="card-sub" style="{color_style}">{sub_text if sub_text else '&nbsp;'}</div>
    </div>
    """, unsafe_allow_html=True)

# --- 7. Pages ---

def login_page():
    c1, c2, c3 = st.columns([1, 1.2, 1])
    with c2:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown('<div class="login-box">', unsafe_allow_html=True)
        st.markdown(LOGO_HTML, unsafe_allow_html=True)
        st.markdown('<h2 style="margin-top:10px;">โรงพยาบาลพระนารายณ์มหาราช</h2>', unsafe_allow_html=True)
        st.markdown('<p>SMART Audit AI System</p>', unsafe_allow_html=True)
        
        with st.form("login"):
            st.text_input("Username", key="u_input")
            st.text_input("Password", type="password", key="p_input")
            if st.form_submit_button("เข้าสู่ระบบ (LOGIN)", use_container_width=True):
                if st.session_state.u_input.lower().strip() == "hosnarai" and st.session_state.p_input.strip() == "h15000":
                    st.session_state.logged_in = True
                    st.session_state.username = "Hosnarai"
                    st.session_state.current_page = "upload"
                    st.rerun()
                else:
                    st.error("รหัสผ่านไม่ถูกต้อง")
        st.markdown('</div>', unsafe_allow_html=True)

def upload_page():
    c1, c2 = st.columns([4, 1])
    with c1:
        st.markdown(f"<div style='display:flex;align-items:center;'>{LOGO_HTML}<div><h2 style='margin:0'>Data Import Center</h2><p style='margin:0'>ระบบนำเข้าข้อมูล 52 แฟ้ม</p></div></div>", unsafe_allow_html=True)
    with c2:
        st.markdown(f"<div style='text-align:right;padding-top:15px; font-size:18px;'><b>{st.session_state.username}</b></div>", unsafe_allow_html=True)
    
    st.markdown("---")
    
    st.markdown("""
    <div style="background:white; padding:50px; border-radius:16px; border:2px dashed #CBD5E1; text-align:center; margin-bottom:30px;">
        <h3 style="color:#0F172A;">📂 อัปโหลดไฟล์ 52 แฟ้ม</h3>
        <p style="font-size:18px; color:#64748B;">ลากไฟล์ทั้งหมดมาวางที่นี่เพื่อเริ่มการวิเคราะห์ด้วย AI</p>
    </div>
    """, unsafe_allow_html=True)
    
    uploaded = st.file_uploader("", type=["txt"], accept_multiple_files=True, label_visibility="collapsed")
    
    if uploaded:
        st.success(f"✅ พร้อมวิเคราะห์จำนวน {len(uploaded)} ไฟล์")
        c1, c2, c3 = st.columns([1, 1, 1])
        with c2:
            if st.button("🚀 เริ่มวิเคราะห์ (Start Audit)", type="primary", use_container_width=True):
                with st.spinner("AI กำลังประมวลผล..."):
                    df, summ = process_data_mock(uploaded)
                    st.session_state.audit_data = df
                    st.session_state.summary = summ
                    st.session_state.current_page = "dashboard"
                    st.rerun()

def dashboard_page():
    # Header
    c1, c2 = st.columns([4, 1.2])
    with c1:
        st.markdown(f"""
        <div style="display:flex; align-items:center;">
            {LOGO_HTML}
            <div>
                <h2 style="margin:0;">โรงพยาบาลพระนารายณ์มหาราช</h2>
                <p style="margin:0;">SMART Audit AI : Executive Dashboard</p>
            </div>
        </div>
        """, unsafe_allow_html=True)
    with c2:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("↺ วิเคราะห์ใหม่", use_container_width=True):
            st.session_state.current_page = "upload"
            st.rerun()

    st.markdown("---")
    
    if st.session_state.audit_data is None:
        st.warning("No Data Found")
        return

    # Metrics (Card Style)
    summ = st.session_state.summary
    m1, m2, m3, m4 = st.columns(4)
    with m1: render_premium_card("จำนวน Record", f"{summ['records']:,}", "รายการทั้งหมด", icon="📂")
    with m2: render_premium_card("ยอดเงินก่อน Audit", f"{summ['pre_audit']:,.0f} ฿", "ยอดส่งเบิกตั้งต้น", icon="📉")
    with m3: render_premium_card("ยอดเงินหลัง Audit", f"{summ['post_audit']:,.0f} ฿", "ยอดที่คาดว่าจะได้", icon="📈")
    with m4: render_premium_card("Financial Impact", f"{summ['impact']:+,.0f} ฿", is_impact=True, icon="⚖️")

    st.markdown("<br>", unsafe_allow_html=True)

    # Tabs & Table (Fixed Visibility)
    t_all, t_opd, t_ipd = st.tabs(["📋 ALL (ทั้งหมด)", "🩺 OPD (ผู้ป่วยนอก)", "🛏️ IPD (ผู้ป่วยใน)"])
    
    df = st.session_state.audit_data
    df['HN_AN_SHOW'] = df.apply(lambda x: x['AN'] if x['TYPE']=='IPD' else x['HN'], axis=1)
    
    # Table Config
    cfg = {
        "HN_AN_SHOW": st.column_config.TextColumn("HN / AN", width="medium"),
        "DATE": st.column_config.TextColumn("วันที่รับบริการ", width="small"),
        "PTTYPE": st.column_config.TextColumn("สิทธิการรักษา", width="small"),
        "FINDING": st.column_config.TextColumn("⚠️ ข้อค้นพบ (Findings)", width="large"),
        "ACTION": st.column_config.TextColumn("🔧 คำแนะนำ (Action)", width="large"),
        "IMPACT": st.column_config.NumberColumn("💰 Impact", format="%.0f ฿")
    }
    cols = ["HN_AN_SHOW", "DATE", "PTTYPE", "FINDING", "ACTION", "IMPACT"]
    
    # Export Button (Visible on Right)
    c_space, c_btn = st.columns([5, 1])
    with c_btn:
        csv = df.to_csv(index=False).encode('utf-8-sig')
        st.download_button("📥 ส่งออก Excel", csv, "smart_audit_report.csv", "text/csv", type="primary", use_container_width=True)

    def show_table(data):
        if not data.empty:
            data = data.sort_values(by="IMPACT", ascending=True)
            st.dataframe(data, column_order=cols, column_config=cfg, use_container_width=True, height=600, hide_index=True)
        else:
            st.info("ไม่พบข้อมูล")

    with t_all: show_table(df)
    with t_opd: show_table(df[df['TYPE']=='OPD'])
    with t_ipd: show_table(df[df['TYPE']=='IPD'])

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
