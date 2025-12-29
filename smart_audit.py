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
    page_title="SMART Audit AI - โรงพยาบาลพระนารายณ์มหาราช",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="collapsed" # ซ่อน Sidebar เพื่อความ Clean แบบ Executive
)

# --- 2. Resources (Logo) ---
def get_base64_logo():
    # SVG Logo (Navy/Gold Theme)
    svg = """
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512" width="100" height="100">
      <path fill="#0F172A" d="M256 0C114.6 0 0 114.6 0 256s114.6 256 256 256 256-114.6 256-256S397.4 0 256 0zm0 472c-119.3 0-216-96.7-216-216S136.7 40 256 40s216 96.7 216 216-96.7 216-216 216z"/>
      <path fill="#D4AF37" d="M368 232h-88v-88c0-13.3-10.7-24-24-24s-24 10.7-24 24v88h-88c-13.3 0-24 10.7-24 24s10.7 24 24 24h88v88c0 13.3 10.7 24 24 24s24-10.7 24-24v-88h88c13.3 0 24-10.7 24-24s-10.7-24-24-24z"/>
    </svg>
    """
    return base64.b64encode(svg.encode('utf-8')).decode("utf-8")

LOGO_HTML = f'<img src="data:image/svg+xml;base64,{get_base64_logo()}" width="80" style="vertical-align:middle; margin-right:15px;">'

# --- 3. CSS Styling (Premium Theme: White/Blue/Gold) ---
def apply_theme():
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Prompt:wght@300;400;600&display=swap');
        
        /* Global Settings */
        .stApp {
            background-color: #F8FAFC; /* สีพื้นหลังขาวอมฟ้าจางๆ */
            font-family: 'Prompt', sans-serif;
        }
        
        /* Text Colors */
        h1, h2, h3, h4, p, div, span, label {
            color: #1E293B; /* สีน้ำเงินเข้มเกือบดำ */
        }
        
        /* Login Box Styling */
        .login-container {
            background: white;
            padding: 40px;
            border-radius: 20px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.08);
            border-top: 6px solid #D4AF37; /* ขลิบทอง */
            text-align: center;
        }
        
        /* Metric Cards */
        .metric-card {
            background: white;
            padding: 20px;
            border-radius: 12px;
            box-shadow: 0 4px 10px rgba(0,0,0,0.05);
            border-left: 5px solid #0F172A; /* ขลิบน้ำเงิน */
            transition: transform 0.2s;
        }
        .metric-card:hover { transform: translateY(-3px); }
        .metric-card.impact { border-left: 5px solid #D4AF37; } /* ขลิบทองสำหรับ Impact */
        
        .metric-title { font-size: 14px; color: #64748B; font-weight: 600; text-transform: uppercase; }
        .metric-value { font-size: 26px; color: #0F172A; font-weight: bold; margin-top: 5px; }
        .metric-sub { font-size: 12px; margin-top: 5px; }
        
        /* Buttons */
        div.stButton > button {
            background: linear-gradient(135deg, #0F172A 0%, #1E293B 100%);
            color: #FFFFFF !important;
            border: none;
            border-radius: 8px;
            padding: 10px 24px;
            font-weight: 500;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        div.stButton > button:hover {
            background: #1E293B;
            box-shadow: 0 6px 10px rgba(0,0,0,0.15);
        }
        
        /* Tabs Customization */
        .stTabs [data-baseweb="tab-list"] {
            gap: 10px;
            background-color: transparent;
        }
        .stTabs [data-baseweb="tab"] {
            height: 45px;
            background-color: #FFFFFF;
            border-radius: 8px;
            border: 1px solid #E2E8F0;
            color: #64748B;
            font-weight: 600;
        }
        .stTabs [data-baseweb="tab"][aria-selected="true"] {
            background-color: #0F172A;
            color: #FFFFFF;
            border: 1px solid #0F172A;
        }
        
        /* Table Styling */
        [data-testid="stDataFrame"] {
            background-color: white;
            padding: 10px;
            border-radius: 12px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.05);
        }
        </style>
    """, unsafe_allow_html=True)

# --- 4. Session State ---
if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'audit_data' not in st.session_state: st.session_state.audit_data = None
if 'summary' not in st.session_state: st.session_state.summary = {}
if 'current_page' not in st.session_state: st.session_state.current_page = "login"

# --- 5. Logic & Processing ---

def process_data_mock(uploaded_files):
    """
    ฟังก์ชันจำลองการประมวลผลและสร้าง Dataframe
    (ในระบบจริงจะอ่านจาก uploaded_files)
    """
    time.sleep(1.5) # Simulate processing time
    
    # สร้าง Mock Data จำนวน 100 รายการ
    data = []
    pttypes = ['UCS', 'OFC', 'SSS', 'LGO'] # สิทธิการรักษา
    
    for i in range(100):
        is_ipd = np.random.choice([True, False], p=[0.3, 0.7])
        hn = f"{np.random.randint(60000, 69999):05d}"
        an = f"{np.random.randint(10000, 19999):05d}" if is_ipd else "-"
        date_serv = f"2024-{np.random.randint(1,13):02d}-{np.random.randint(1,28):02d}"
        pttype = np.random.choice(pttypes)
        
        # Random Case Generation
        case_type = np.random.choice(['Normal', 'Overclaim', 'Underclaim'], p=[0.7, 0.2, 0.1])
        
        finding = "-"
        action = "-"
        impact = 0
        
        if case_type == 'Overclaim':
            finding = "วันจำหน่ายก่อนวันรับเข้า (Date Mismatch)"
            action = "ตรวจสอบและแก้ไขวันที่ (DATEDSC)"
            impact = -1 * np.random.randint(500, 5000) # ติดลบ = Overclaim (ต้องคืนเงิน)
        elif case_type == 'Underclaim':
            finding = "ไม่ได้ลงรหัสหัตถการ (Missing Proc)"
            action = "เพิ่มรหัสหัตถการเพื่อเบิกเพิ่ม"
            impact = np.random.randint(500, 3000) # บวก = Underclaim (ได้เงินเพิ่ม)
            
        data.append({
            "HN": hn,
            "AN": an,
            "DATE": date_serv,
            "PTTYPE": pttype,
            "FINDING": finding,
            "ACTION": action,
            "IMPACT": impact,
            "TYPE": "IPD" if is_ipd else "OPD"
        })
        
    df = pd.DataFrame(data)
    
    # Calculate Summary
    pre_audit = 5000000.0
    net_impact = df['IMPACT'].sum()
    post_audit = pre_audit + net_impact
    
    summary = {
        "records": 166196, # Mock total records from files
        "pre_audit": pre_audit,
        "post_audit": post_audit,
        "impact": net_impact
    }
    
    return df, summary

# --- 6. Helper UI Functions ---

def render_metric_card(title, value, sub_text=None, is_impact=False):
    color_style = ""
    if is_impact:
        # ถ้า Impact ติดลบ (Overclaim) ให้เป็นสีแดง, ถ้าบวก (Underclaim) เป็นสีเขียว
        val_num = float(str(value).replace(',','').replace(' ฿',''))
        if val_num < 0:
            color_style = "color: #EF4444;" # Red
            sub_text = "▼ Overclaim (เสี่ยงเรียกคืน)"
        elif val_num > 0:
            color_style = "color: #10B981;" # Green
            sub_text = "▲ Underclaim (เบิกเพิ่มได้)"
        else:
            color_style = "color: #64748B;"
            
    extra_class = "impact" if is_impact else ""
    
    st.markdown(f"""
    <div class="metric-card {extra_class}">
        <div class="metric-title">{title}</div>
        <div class="metric-value" style="{color_style}">{value}</div>
        <div class="metric-sub" style="{color_style}">{sub_text if sub_text else ''}</div>
    </div>
    """, unsafe_allow_html=True)

# --- 7. Pages ---

def login_page():
    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        st.markdown("<br><br>", unsafe_allow_html=True)
        # Login Container
        st.markdown('<div class="login-container">', unsafe_allow_html=True)
        
        # Logo & Hospital Name
        st.markdown(LOGO_HTML, unsafe_allow_html=True)
        st.markdown('<h2 style="margin-top:15px; color:#0F172A;">โรงพยาบาลพระนารายณ์มหาราช</h2>', unsafe_allow_html=True)
        st.markdown('<p style="color:#64748B; font-weight:300;">SMART Audit AI System</p>', unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Login Form (แยกออกมาเพื่อให้ Streamlit จัดการ State ได้ดี)
        st.markdown("<br>", unsafe_allow_html=True)
        with st.form("login_form"):
            user = st.text_input("Username", placeholder="ระบุชื่อผู้ใช้งาน")
            pwd = st.text_input("Password", type="password", placeholder="ระบุรหัสผ่าน")
            
            submit = st.form_submit_button("เข้าสู่ระบบ (Login)", use_container_width=True)
            
            if submit:
                # Login Logic (Flexible)
                if user.strip().lower() == "hosnarai" and pwd.strip() == "h15000":
                    st.session_state.logged_in = True
                    st.session_state.current_page = "dashboard" # ไปหน้า Dashboard ทันที (ข้าม Upload ตาม Flow ใหม่ที่อาจมีข้อมูลแล้ว)
                    # ถ้าต้องการให้ไปหน้า Upload ก่อน ให้เปลี่ยนเป็น "upload"
                    st.session_state.current_page = "upload" 
                    st.rerun()
                else:
                    st.error("ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง")

def upload_page():
    # หน้า Upload แบบ Clean
    st.markdown(f"""
    <div style="display:flex; align-items:center; justify-content:space-between; padding:20px; background:white; border-radius:15px; box-shadow:0 2px 5px rgba(0,0,0,0.05);">
        <div style="display:flex; align-items:center;">
            {LOGO_HTML}
            <div>
                <h3 style="margin:0; color:#0F172A;">โรงพยาบาลพระนารายณ์มหาราช</h3>
                <span style="color:#64748B;">SMART Audit AI : Upload Center</span>
            </div>
        </div>
        <div style="text-align:right;">
            <span style="color:#0F172A; font-weight:bold;">ยินดีต้อนรับ User: Hosnarai</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Upload Area
    st.markdown("""
    <div style="background:white; padding:40px; border-radius:15px; border:2px dashed #CBD5E1; text-align:center;">
        <h4 style="color:#0F172A;">📂 อัปโหลดไฟล์ 52 แฟ้ม</h4>
        <p style="color:#64748B;">ลากไฟล์ทั้งหมดมาวางที่นี่เพื่อเริ่มการวิเคราะห์</p>
    </div>
    """, unsafe_allow_html=True)
    
    uploaded_files = st.file_uploader("", type=["txt"], accept_multiple_files=True, label_visibility="collapsed")
    
    if uploaded_files:
        st.success(f"✅ พบไฟล์จำนวน {len(uploaded_files)} ไฟล์")
        if st.button("🚀 เริ่มวิเคราะห์ข้อมูล (Start Audit)", type="primary"):
            with st.spinner("กำลังประมวลผลข้อมูล..."):
                df, summ = process_data_mock(uploaded_files)
                st.session_state.audit_data = df
                st.session_state.summary = summ
                st.session_state.current_page = "dashboard"
                st.rerun()

def dashboard_page():
    # --- Header Section (ข้อ 1 & 5) ---
    c_head1, c_head2 = st.columns([4, 1])
    with c_head1:
        st.markdown(f"""
        <div style="display:flex; align-items:center;">
            {LOGO_HTML}
            <div>
                <h2 style="margin:0; color:#0F172A; font-weight:bold;">โรงพยาบาลพระนารายณ์มหาราช</h2>
                <p style="margin:0; color:#64748B;">SMART Audit AI : Executive Summary</p>
            </div>
        </div>
        """, unsafe_allow_html=True)
    with c_head2:
        st.markdown("<br>", unsafe_allow_html=True)
        # ปุ่มวิเคราะห์ใหม่ (ขวาบน)
        if st.button("↺ วิเคราะห์ใหม่", use_container_width=True):
            st.session_state.current_page = "upload"
            st.session_state.audit_data = None
            st.rerun()

    st.markdown("---")
    
    if st.session_state.audit_data is None:
        st.warning("ไม่พบข้อมูลการวิเคราะห์ กรุณาอัปโหลดไฟล์ใหม่")
        return

    # --- Metrics Section (ข้อ 2) ---
    summ = st.session_state.summary
    m1, m2, m3, m4 = st.columns(4)
    
    with m1: render_metric_card("จำนวน Record", f"{summ['records']:,}", "รายการทั้งหมด")
    with m2: render_metric_card("ยอดเงินก่อน Audit", f"{summ['pre_audit']:,.0f} ฿", "ยอดส่งเบิกตั้งต้น")
    with m3: render_metric_card("ยอดเงินหลัง Audit", f"{summ['post_audit']:,.0f} ฿", "ยอดที่คาดว่าจะได้")
    with m4: render_metric_card("Impact (ผลกระทบ)", f"{summ['impact']:+,.0f} ฿", is_impact=True) # มีสีแดง/เขียว

    st.markdown("<br>", unsafe_allow_html=True)

    # --- Tabs & Table Section (ข้อ 3 & 4) ---
    st.subheader("🔎 รายละเอียดผลการตรวจสอบ (Audit Findings)")
    
    # Tabs แยกกลุ่ม
    tabs = st.tabs(["📋 ALL (ทั้งหมด)", "🩺 OPD (ผู้ป่วยนอก)", "🛏️ IPD (ผู้ป่วยใน)"])
    
    df = st.session_state.audit_data
    
    # Column Config (ข้อ 4)
    # แสดง HN/AN รวมกันในคอลัมน์เดียวตามเงื่อนไข (ใน Dataframe เราแยกไว้แล้ว แต่ตอนโชว์จะใช้ Column Config)
    # แต่เพื่อให้ง่าย เราสร้างคอลัมน์โชว์เฉพาะกิจ
    df['HN_AN_SHOW'] = df.apply(lambda x: x['AN'] if x['TYPE'] == 'IPD' else x['HN'], axis=1)
    
    table_cfg = {
        "HN_AN_SHOW": st.column_config.TextColumn("HN / AN", width="medium"),
        "DATE": st.column_config.TextColumn("วันที่รับบริการ", width="small"),
        "PTTYPE": st.column_config.TextColumn("สิทธิการรักษา", width="small"),
        "FINDING": st.column_config.TextColumn("⚠️ ข้อค้นพบ (Findings)", width="large"),
        "ACTION": st.column_config.TextColumn("🔧 คำแนะนำ (AI Action)", width="large"),
        "IMPACT": st.column_config.NumberColumn(
            "💰 Impact", 
            format="%.0f ฿",
            help="แดง = Overclaim (คืนเงิน), เขียว = Underclaim (ได้เพิ่ม)"
        )
    }
    
    column_order = ["HN_AN_SHOW", "DATE", "PTTYPE", "FINDING", "ACTION", "IMPACT"]

    def show_table(data_view):
        if not data_view.empty:
            # Sort ให้เห็น Impact เยอะๆ ก่อน
            data_view = data_view.sort_values(by="IMPACT", ascending=True)
            st.dataframe(
                data_view,
                column_order=column_order,
                column_config=table_cfg,
                use_container_width=True,
                height=500,
                hide_index=True
            )
        else:
            st.info("ไม่พบรายการในกลุ่มนี้")

    with tabs[0]: # ALL
        show_table(df)
        
    with tabs[1]: # OPD
        show_table(df[df['TYPE'] == 'OPD'])
        
    with tabs[2]: # IPD
        show_table(df[df['TYPE'] == 'IPD'])

    # --- Export Section (ข้อ 6) ---
    st.markdown("<br>", unsafe_allow_html=True)
    c_empty, c_export = st.columns([6, 1])
    with c_export:
        csv = df.to_csv(index=False).encode('utf-8-sig')
        st.download_button(
            label="📥 ส่งออก Excel (CSV)",
            data=csv,
            file_name="smart_audit_report.csv",
            mime="text/csv",
            type="primary",
            use_container_width=True
        )

# --- 8. Main Controller ---
def main():
    apply_theme() # เรียกใช้ Theme Premium
    
    if not st.session_state.logged_in:
        login_page()
    else:
        if st.session_state.current_page == "dashboard":
            dashboard_page()
        else:
            upload_page()

if __name__ == "__main__":
    main()
