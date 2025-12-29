import streamlit as st
import pandas as pd
import numpy as np
import time
import base64
import random

# --- 0. AI CONFIGURATION ---
try:
    import google.generativeai as genai
    
    # ดึง Key จาก Secrets แทนการใส่ในโค้ดตรงๆ (ปลอดภัยกว่า)
    # ถ้าไม่มีใน Secrets ให้ใช้ค่าว่าง (เพื่อกัน Error ตอนรันในเครื่องตัวเองถ้าไม่ได้เซ็ต)
    if "GOOGLE_API_KEY" in st.secrets:
        YOUR_API_KEY = st.secrets["GOOGLE_API_KEY"]
    else:
        YOUR_API_KEY = "ใส่_KEY_สำรองตรงนี้_กรณีรันในเครื่อง_หรือปล่อยว่างไว้"

    genai.configure(api_key=YOUR_API_KEY)
    HAS_AI_CONNECTION = True

except ImportError:
    HAS_AI_CONNECTION = False
except Exception as e:
    # กันกรณี Secrets ยังไม่มา
    HAS_AI_CONNECTION = False

# --- 1. Config & Setup ---
st.set_page_config(
    page_title="SMART Audit AI - โรงพยาบาลพระนารายณ์มหาราช",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. Resources (Logo) ---
def get_base64_logo():
    # Logo SVG (Blue/Gold)
    svg = """
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512" width="100" height="100">
      <path fill="#1565C0" d="M256 0C114.6 0 0 114.6 0 256s114.6 256 256 256 256-114.6 256-256S397.4 0 256 0zm0 472c-119.3 0-216-96.7-216-216S136.7 40 256 40s216 96.7 216 216-96.7 216-216 216z"/>
      <path fill="#FFD700" d="M368 232h-88v-88c0-13.3-10.7-24-24-24s-24 10.7-24 24v88h-88c-13.3 0-24 10.7-24 24s10.7 24 24 24h88v88c0 13.3 10.7 24 24 24s24-10.7 24-24v-88h88c13.3 0 24-10.7 24-24s-10.7-24-24-24z"/>
    </svg>
    """
    return base64.b64encode(svg.encode('utf-8')).decode("utf-8")

LOGO_HTML = f'<img src="data:image/svg+xml;base64,{get_base64_logo()}" width="100">'
LOGO_SMALL = f'<img src="data:image/svg+xml;base64,{get_base64_logo()}" width="50" style="vertical-align:middle; margin-right:10px;">'

# --- 3. CSS Styling (Blue/White Theme) ---
def apply_theme():
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Prompt:wght@300;400;500;700&display=swap');
        
        :root { --primary-color: #1565C0; }
        
        /* Global Font & Colors */
        html, body, [class*="css"] {
            font-family: 'Prompt', sans-serif;
            background-color: #F8FAFC !important;
            color: #334155 !important;
        }
        
        /* Sidebar */
        section[data-testid="stSidebar"] {
            background-color: #FFFFFF !important;
            border-right: 1px solid #E2E8F0;
        }
        section[data-testid="stSidebar"] * { color: #1E3A8A !important; }
        
        /* Headers */
        h1, h2, h3 { color: #1565C0 !important; font-weight: 700 !important; }
        
        /* Input Fields */
        .stTextInput input, .stPasswordInput input {
            background-color: #FFFFFF !important;
            color: #1E3A8A !important;
            border: 2px solid #BFDBFE !important;
            border-radius: 8px;
        }
        
        /* Table */
        [data-testid="stDataFrame"] {
            background-color: #FFFFFF !important;
            border: 1px solid #E2E8F0;
            border-radius: 10px;
            padding: 10px;
        }
        [data-testid="stDataFrame"] * {
            background-color: #FFFFFF !important;
            color: #334155 !important;
        }
        
        /* Buttons */
        div.stButton > button {
            background-color: #1565C0 !important;
            color: white !important;
            border-radius: 8px;
            border: none;
            box-shadow: 0 4px 6px rgba(21, 101, 192, 0.2);
        }
        div.stButton > button:hover {
            background-color: #0D47A1 !important;
        }
        
        /* Login Box */
        .login-box {
            background: white !important;
            padding: 40px;
            border-radius: 16px;
            box-shadow: 0 10px 25px rgba(0,0,0,0.05);
            text-align: center;
            border-top: 5px solid #1565C0;
        }
        
        /* Metric Card */
        .metric-card {
            background: white !important;
            padding: 20px;
            border-radius: 12px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.05);
            border-left: 5px solid #1565C0;
            text-align: center;
        }
        
        /* Chat Bubble */
        .stChatMessage {
            background-color: #FFFFFF !important;
            border: 1px solid #E2E8F0;
        }
        </style>
    """, unsafe_allow_html=True)

# --- 4. Session State ---
if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'username' not in st.session_state: st.session_state.username = ""
if 'audit_data' not in st.session_state: st.session_state.audit_data = None
if 'summary' not in st.session_state: st.session_state.summary = {}
if 'current_page' not in st.session_state: st.session_state.current_page = "login"
if 'chat_history' not in st.session_state: 
    st.session_state.chat_history = [
        {"role": "assistant", "content": "สวัสดีครับ ผมคือ AI Consultant 🤖 ประจำโรงพยาบาลพระนารายณ์มหาราช \n\nท่านสามารถปรึกษาเรื่องกฎการ Audit, ถามวิธีแก้ Error Code หรือขอคำแนะนำเรื่องการเบิกจ่ายได้เลยครับ"}
    ]

# --- 5. Mock Logic ---
def process_data_mock(uploaded_files):
    progress_text = "กำลังวิเคราะห์ข้อมูล... (AI Processing)"
    my_bar = st.progress(0, text=progress_text)
    for percent_complete in range(100):
        time.sleep(0.01) 
        my_bar.progress(percent_complete + 1, text=progress_text)
    time.sleep(0.2)
    my_bar.empty()
    
    data = []
    pttypes = ['UCS', 'OFC', 'SSS', 'LGO']
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

# --- 6. AI Logic (REAL CONNECT) ---
def get_ai_response(user_input):
    """
    ฟังก์ชันเชื่อมต่อ Gemini Pro เพื่อตอบคำถามจริง
    """
    # 1. ตรวจสอบว่ามี Library และ Key หรือไม่
    if not HAS_AI_CONNECTION:
        return "⚠️ ขออภัยครับ ระบบยังไม่พบการติดตั้ง 'google-generativeai' กรุณาแจ้ง Admin ให้ติดตั้ง Library ก่อนครับ"
    
    if "นำ_API_KEY" in YOUR_API_KEY:
        return "⚠️ กรุณาใส่ API Key ในโค้ดก่อนครับ (บรรทัดที่ 15)"

    try:
        # 2. เตรียม Context ข้อมูล
        summary_text = "ไม่มีข้อมูล Audit ในขณะนี้"
        if st.session_state.summary:
            s = st.session_state.summary
            summary_text = f"ยอด Record={s['records']:,}, ยอด Impact={s['impact']:,.0f} บาท"

        # 3. สร้าง Prompt ส่งให้ AI
        system_prompt = f"""
        บทบาท: คุณคือ AI Consultant ผู้เชี่ยวชาญด้านเวชระเบียนและ Audit ของโรงพยาบาลพระนารายณ์มหาราช
        
        ข้อมูลบริบทปัจจุบัน: {summary_text}
        
        หน้าที่:
        1. ตอบคำถามเกี่ยวกับการตรวจสอบเวชระเบียน (Audit) และการเบิกจ่าย (Claim)
        2. อธิบายศัพท์เทคนิค เช่น Overclaim, Underclaim, DRG, RW
        3. ให้คำแนะนำวิธีแก้ไข Error 52 แฟ้ม อย่างสุภาพและเป็นทางการ
        4. ตอบสั้นกระชับ เข้าใจง่าย ภาษาไทย
        
        คำถามจากผู้ใช้: {user_input}
        """

        # 4. เรียกใช้งาน Gemini
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(system_prompt)
        
        return response.text

    except Exception as e:
        return f"เกิดข้อผิดพลาดในการเชื่อมต่อ AI: {str(e)} (กรุณาเช็ค API Key หรืออินเทอร์เน็ต)"

# --- 7. Helper UI ---
def render_card(title, value, sub_text=None, is_impact=False):
    style_color = "color: #1E3A8A;"
    if is_impact:
        val_num = float(str(value).replace(',','').replace(' ฿','').replace('+',''))
        if val_num < 0:
            style_color = "color: #EF4444;" # Red
            sub_text = "▼ Overclaim (เสี่ยงเรียกคืน)"
        elif val_num > 0:
            style_color = "color: #10B981;" # Green
            sub_text = "▲ Underclaim (เบิกเพิ่มได้)"
    
    st.markdown(f"""
    <div class="metric-card">
        <div style="font-size:14px; color:#64748B;">{title}</div>
        <div style="font-size:28px; font-weight:800; margin-top:5px; {style_color}">{value}</div>
        <div style="font-size:13px; margin-top:5px; {style_color}">{sub_text if sub_text else '&nbsp;'}</div>
    </div>
    """, unsafe_allow_html=True)

# --- 8. Pages ---

def login_page():
    c1, c2, c3 = st.columns([1, 1.5, 1])
    with c2:
        st.markdown("<br><br><br>", unsafe_allow_html=True)
        st.markdown('<div class="login-box">', unsafe_allow_html=True)
        st.markdown(LOGO_HTML, unsafe_allow_html=True)
        st.markdown('<h2 style="margin-top:20px; color:#1565C0;">โรงพยาบาลพระนารายณ์มหาราช</h2>', unsafe_allow_html=True)
        st.markdown('<p style="color:#64748B;">SMART Audit AI System</p>', unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        
        with st.form("login"):
            st.text_input("Username", key="u_input")
            st.text_input("Password", type="password", key="p_input")
            st.markdown("<br>", unsafe_allow_html=True)
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
        st.markdown(f"<div style='display:flex;align-items:center;'>{LOGO_SMALL}<h2 style='margin:0; color:#1565C0;'>Data Import Center</h2></div>", unsafe_allow_html=True)
    with c2:
        st.markdown(f"<div style='text-align:right;padding-top:10px;color:#1E3A8A;'><b>{st.session_state.username}</b></div>", unsafe_allow_html=True)
    
    st.markdown("---")
    st.markdown("""
    <div style="background:white; padding:50px; border-radius:16px; border:2px dashed #BFDBFE; text-align:center; margin-bottom:30px;">
        <h3 style="color:#1565C0;">📂 อัปโหลดไฟล์ 52 แฟ้ม</h3>
        <p style="color:#64748B;">ลากไฟล์ทั้งหมดมาวางที่นี่เพื่อเริ่มการวิเคราะห์ด้วย AI</p>
    </div>
    """, unsafe_allow_html=True)
    
    uploaded = st.file_uploader("", type=["txt"], accept_multiple_files=True, label_visibility="collapsed")
    
    if uploaded:
        st.info(f"📄 พบไฟล์จำนวน {len(uploaded)} ไฟล์ พร้อมวิเคราะห์")
        c1, c2, c3 = st.columns([1, 1, 1])
        with c2:
            if st.button("🚀 เริ่มวิเคราะห์ (Start Audit)", type="primary", use_container_width=True):
                df, summ = process_data_mock(uploaded)
                st.session_state.audit_data = df
                st.session_state.summary = summ
                st.session_state.current_page = "dashboard"
                st.rerun()

def dashboard_page():
    c1, c2 = st.columns([4, 1.2])
    with c1:
        st.markdown(f"<div style='display:flex;align-items:center;'>{LOGO_SMALL}<h2 style='margin:0; color:#1565C0;'>Executive Dashboard</h2></div>", unsafe_allow_html=True)
    with c2:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("↺ วิเคราะห์ใหม่", use_container_width=True):
            st.session_state.current_page = "upload"
            st.rerun()

    st.markdown("---")
    if st.session_state.audit_data is None:
        st.warning("กรุณาอัปโหลดข้อมูลก่อน")
        return

    summ = st.session_state.summary
    m1, m2, m3, m4 = st.columns(4)
    with m1: render_card("จำนวน Record", f"{summ['records']:,}", "รายการทั้งหมด")
    with m2: render_card("ยอดเงินก่อน Audit", f"{summ['pre_audit']:,.0f} ฿", "ยอดส่งเบิกตั้งต้น")
    with m3: render_card("ยอดเงินหลัง Audit", f"{summ['post_audit']:,.0f} ฿", "ยอดที่คาดว่าจะได้")
    with m4: render_card("Impact (ผลกระทบ)", f"{summ['impact']:+,.0f} ฿", "", True)

    st.markdown("<br>", unsafe_allow_html=True)
    
    t1, t2, t3 = st.tabs(["📋 ALL (ทั้งหมด)", "🩺 OPD (ผู้ป่วยนอก)", "🛏️ IPD (ผู้ป่วยใน)"])
    df = st.session_state.audit_data
    df_filtered = df[df['IMPACT'] != 0]
    df_filtered['HN_AN_SHOW'] = df_filtered.apply(lambda x: x['AN'] if x['TYPE']=='IPD' else x['HN'], axis=1)
    
    cfg = {
        "HN_AN_SHOW": st.column_config.TextColumn("HN / AN", width="medium"),
        "DATE": st.column_config.TextColumn("วันที่", width="small"),
        "PTTYPE": st.column_config.TextColumn("สิทธิฯ", width="small"),
        "FINDING": st.column_config.TextColumn("⚠️ สิ่งที่ตรวจพบ", width="large"),
        "ACTION": st.column_config.TextColumn("🔧 คำแนะนำ", width="large"),
        "IMPACT": st.column_config.NumberColumn("💰 Impact", format="%.0f ฿")
    }
    cols = ["HN_AN_SHOW", "DATE", "PTTYPE", "FINDING", "ACTION", "IMPACT"]
    
    c_space, c_btn = st.columns([5, 1])
    with c_btn:
        csv = df_filtered.to_csv(index=False).encode('utf-8-sig')
        st.download_button("📥 ส่งออก Excel", csv, "smart_audit_report.csv", "text/csv", type="primary", use_container_width=True)

    def show_table(data):
        if not data.empty:
            data = data.sort_values(by="IMPACT", ascending=True)
            st.dataframe(data, column_order=cols, column_config=cfg, use_container_width=True, height=600, hide_index=True)
        else:
            st.success("🎉 ไม่พบข้อผิดพลาด (Impact = 0 ถูกซ่อนไว้)")

    with t1: show_table(df_filtered)
    with t2: show_table(df_filtered[df_filtered['TYPE']=='OPD'])
    with t3: show_table(df_filtered[df_filtered['TYPE']=='IPD'])

def chat_page():
    c1, c2 = st.columns([4, 1])
    with c1:
        st.markdown(f"<div style='display:flex;align-items:center;'>{LOGO_SMALL}<h2 style='margin:0; color:#1565C0;'>AI Consultant</h2></div>", unsafe_allow_html=True)
    with c2:
        if st.button("⬅️ กลับ Dashboard"):
            st.session_state.current_page = "dashboard"
            st.rerun()
            
    st.markdown("---")

    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if prompt := st.chat_input("พิมพ์คำถามปรึกษา AI..."):
        st.session_state.chat_history.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.spinner("AI กำลังคิด..."):
            # เรียกใช้ฟังก์ชัน AI ของจริง
            response = get_ai_response(prompt)
            
        st.session_state.chat_history.append({"role": "assistant", "content": response})
        with st.chat_message("assistant"):
            st.markdown(response)

# --- 8. Main Router ---
def main():
    apply_theme()
    
    with st.sidebar:
        st.markdown(LOGO_HTML, unsafe_allow_html=True)
        st.markdown("### SMART Audit AI")
        if st.session_state.logged_in:
            st.markdown(f"User: **{st.session_state.username}**")
            st.markdown("---")
            if st.button("📊 Dashboard"):
                st.session_state.current_page = "dashboard"
                st.rerun()
            if st.button("💬 AI Consultant"):
                st.session_state.current_page = "chat"
                st.rerun()
            if st.button("📤 Upload Data"):
                st.session_state.current_page = "upload"
                st.rerun()
            st.markdown("<br><br>", unsafe_allow_html=True)
            if st.button("Log out"):
                st.session_state.clear()
                st.rerun()

    if not st.session_state.logged_in:
        login_page()
    elif st.session_state.current_page == "chat":
        chat_page()
    elif st.session_state.current_page == "dashboard":
        dashboard_page()
    else:
        upload_page()

if __name__ == "__main__":
    main()
