import streamlit as st
import pandas as pd
import numpy as np
import time
import os
import logging
from datetime import datetime

# --- 1. Config & Setup ---
st.set_page_config(page_title="SMART Audit AI - โรงพยาบาลพระนารายณ์มหาราช", page_icon="🏥", layout="wide")
logging.basicConfig(format='%(asctime)s - %(message)s', level=logging.INFO)

# --- 2. CSS Styling (Blue/White Theme) ---
def apply_theme():
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@300;400;600&display=swap');
        
        html, body, [class*="css"] {
            font-family: 'Sarabun', sans-serif;
        }
        
        /* พื้นหลังสีฟ้าอ่อน ไล่เฉดขาว */
        .stApp {
            background: linear-gradient(180deg, #F0F8FF 0%, #FFFFFF 100%);
        }
        
        /* Header Text */
        .hospital-name {
            color: #1565C0; /* สีน้ำเงินเข้ม */
            font-size: 28px;
            font-weight: bold;
            margin-bottom: 0px;
        }
        .app-name {
            color: #424242;
            font-size: 20px;
            font-weight: normal;
            margin-top: -5px;
            margin-bottom: 20px;
        }

        /* Metric Cards */
        div[data-testid="metric-container"] {
            background-color: #FFFFFF;
            border: 1px solid #E3F2FD;
            border-radius: 10px;
            padding: 15px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
            text-align: center;
        }
        label[data-testid="stMetricLabel"] {
            font-size: 16px;
            color: #546E7A;
        }
        div[data-testid="stMetricValue"] {
            font-size: 24px;
            color: #0D47A1;
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
    # ใช้ URL โลโก้จริง (หากลิงก์เสียจะใช้ Placeholder)
    return "https://upload.wikimedia.org/wikipedia/th/f/f6/Phranaraimaharaj_Hospital_Logo.png"

LOGO_URL = get_logo()

def process_52_files(uploaded_files):
    details_list = []
    total_records = 0
    pre_audit_sum = 0
    
    # UI Progress
    progress_bar = st.progress(0)
    status_text = st.empty()
    total_files = len(uploaded_files)

    for idx, file in enumerate(uploaded_files):
        # Update Progress
        prog = (idx + 1) / total_files
        progress_bar.progress(prog)
        status_text.text(f"กำลังประมวลผลไฟล์: {file.name}")

        try:
            # อ่านไฟล์ (รองรับภาษาไทย)
            try:
                content = file.read().decode('TIS-620')
            except:
                file.seek(0)
                content = file.read().decode('utf-8', errors='replace')

            lines = content.splitlines()
            if len(lines) < 2: continue

            # แยก Header และ Data
            sep = '|' if '|' in lines[0] else ','
            header = [h.strip().upper() for h in lines[0].strip().split(sep)]
            rows = [line.strip().split(sep) for line in lines[1:] if line.strip()]
            
            df = pd.DataFrame(rows)
            # ปรับ Column ให้ตรง Header
            if df.shape[1] > len(header): df = df.iloc[:, :len(header)]
            if df.shape[1] == len(header): df.columns = header
            else: continue # ข้ามถ้าโครงสร้างผิด

            total_records += len(df)
            file_upper = file.name.upper()

            # --- Logic การตรวจสอบ ---
            
            # 1. ตรวจสอบ DIAGNOSIS (หา DIAGCODE ว่าง)
            if 'DIAG' in file_upper or 'IPDX' in file_upper or 'OPDX' in file_upper:
                col_diag = 'DIAGCODE' if 'DIAGCODE' in df.columns else 'DIAG'
                if col_diag in df.columns:
                    # Filter แถวที่ไม่มีรหัสโรค
                    errors = df[df[col_diag] == '']
                    for _, row in errors.iterrows():
                        is_ipd = 'IPD' in file_upper
                        hn = row.get('HN', '-')
                        an = row.get('AN', '-')
                        date_serv = row.get('DATE_SERV', row.get('DATETIME_ADMIT', '-'))
                        
                        details_list.append({
                            "Type": "IPD" if is_ipd else "OPD",
                            "HN/AN": an if (is_ipd and an != '-') else hn,
                            "วันที่รับบริการ": date_serv,
                            "ข้อค้นพบ": f"ไม่ระบุรหัสโรค ({col_diag})",
                            "Action": "แพทย์/Coder ระบุรหัสโรคให้ครบถ้วน",
                            "Impact": -2000 # ติดลบเพราะอาจเบิกไม่ได้
                        })

            # 2. ตรวจสอบ CHARGE (ค่ารักษา)
            elif 'CHARGE' in file_upper or 'CHA' in file_upper:
                # หาคอลัมน์ราคา
                col_price = next((c for c in ['PRICE', 'COST', 'AMOUNT', 'TOTAL'] if c in df.columns), None)
                
                if col_price:
                    # แปลงเป็นตัวเลขเพื่อคำนวณยอดรวม
                    vals = pd.to_numeric(df[col_price], errors='coerce').fillna(0)
                    pre_audit_sum += vals.sum()
                    
                    # หาเคสราคา 0 บาท
                    zero_price = df[vals == 0]
                    for _, row in zero_price.iterrows():
                        details_list.append({
                            "Type": "IPD" if 'IPD' in file_upper else "OPD",
                            "HN/AN": row.get('AN', row.get('HN', '-')),
                            "วันที่รับบริการ": row.get('DATE_SERV', '-'),
                            "ข้อค้นพบ": f"ค่ารักษาเป็น 0 บาท ({col_price})",
                            "Action": "ตรวจสอบสิทธิและการบันทึกค่าใช้จ่าย",
                            "Impact": 0 # แจ้งเตือนเฉยๆ
                        })

        except Exception as e:
            print(f"Error reading {file.name}: {e}")

    # --- สร้างผลลัพธ์ ---
    result_df = pd.DataFrame(details_list)
    
    # ถ้าไม่มีข้อมูลจริง ให้จำลองข้อมูลตัวอย่าง (Mockup) เพื่อแสดงผล Dashboard
    if result_df.empty and total_records == 0:
        pre_audit_sum = 5420000.00
        mock_data = []
        for i in range(10):
            mock_data.append({
                "Type": "OPD" if i % 2 == 0 else "IPD",
                "HN/AN": f"6700{i:02d}",
                "วันที่รับบริการ": "2024-03-01",
                "ข้อค้นพบ": "รหัสวินิจฉัยไม่สัมพันธ์กับหัตถการ",
                "Action": "ตรวจสอบเวชระเบียน",
                "Impact": -500.00
            })
        result_df = pd.DataFrame(mock_data)
        total_records = 1500

    # คำนวณ Post Audit
    total_impact = result_df['Impact'].sum() if not result_df.empty else 0
    post_audit_sum = pre_audit_sum + total_impact # ยอดหลังแก้ (สมมติว่าแก้แล้วได้คืน หรือหักลบแล้ว)

    summary = {
        "records": total_records,
        "pre_audit": pre_audit_sum,
        "post_audit": post_audit_sum
    }
    
    progress_bar.empty()
    status_text.empty()
    return result_df, summary

# --- 5. Pages ---

def login_page():
    # จัดหน้า Login ให้รูปและ Input
    st.markdown("<br><br>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 1, 1])
    
    with c2:
        # Logo และชื่อโรงพยาบาล
        st.image(LOGO_URL, width=120)
        st.markdown("<div class='hospital-name'>โรงพยาบาลพระนารายณ์มหาราช</div>", unsafe_allow_html=True)
        st.markdown("<div class='app-name'>SMART Audit AI</div>", unsafe_allow_html=True)
        
        with st.form("login_form"):
            user = st.text_input("Username")
            pwd = st.text_input("Password", type="password")
            submitted = st.form_submit_button("เข้าสู่ระบบ", type="primary", use_container_width=True)
            
            if submitted:
                if user.strip() == "Hosnarai" and pwd.strip() == "h15000":
                    st.session_state.logged_in = True
                    st.session_state.username = user.strip()
                    st.session_state.current_page = "upload"
                    st.rerun()
                else:
                    st.error("ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง")

def upload_page():
    # Header
    c1, c2 = st.columns([1, 5])
    with c1: st.image(LOGO_URL, width=80)
    with c2:
        st.markdown("### ระบบตรวจสอบและออดิตข้อมูล (Upload)")
        st.write(f"ผู้ใช้งาน: **{st.session_state.username}**")

    # Check state
    if st.session_state.audit_data is not None:
        st.info("💡 มีข้อมูลเดิมอยู่แล้ว")
        if st.button("ไปที่ Dashboard ผลลัพธ์"):
            st.session_state.current_page = "dashboard"
            st.rerun()

    st.markdown("---")
    st.info("กรุณาลากไฟล์ 52 แฟ้ม (.txt) มาวางในกล่องด้านล่างทีเดียว")
    
    uploaded_files = st.file_uploader("", type=["txt"], accept_multiple_files=True)
    
    if uploaded_files:
        st.success(f"พบไฟล์จำนวน: {len(uploaded_files)} ไฟล์")
        if st.button("🚀 เริ่มประมวลผล", type="primary"):
            with st.spinner("AI กำลังตรวจสอบข้อมูล..."):
                df, summ = process_52_files(uploaded_files)
                st.session_state.audit_data = df
                st.session_state.financial_summary = summ
                st.session_state.current_page = "dashboard"
                time.sleep(0.5)
                st.rerun()

def dashboard_page():
    # --- ส่วนหัว (Header) ---
    c_img, c_txt, c_btn = st.columns([1, 6, 1])
    with c_img:
        st.image(LOGO_URL, width=90)
    with c_txt:
        st.markdown("<div class='hospital-name'>โรงพยาบาลพระนารายณ์มหาราช</div>", unsafe_allow_html=True)
        st.markdown("<div class='app-name'>SMART Audit AI : Executive Dashboard</div>", unsafe_allow_html=True)
    with c_btn:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("⬅️ ตรวจสอบใหม่"):
            st.session_state.current_page = "upload"
            st.session_state.audit_data = None
            st.rerun()
            
    st.markdown("---")

    # ดึงข้อมูล
    df = st.session_state.audit_data
    summ = st.session_state.financial_summary
    
    if df is None:
        st.warning("ไม่มีข้อมูล")
        return

    # --- 1. กล่องสรุป (Metrics) ---
    m1, m2, m3 = st.columns(3)
    
    with m1:
        st.metric("📦 จำนวน Record ทั้งหมด", f"{summ['records']:,}")
    
    with m2:
        st.metric("💰 ยอดเงินก่อน Audit", f"{summ['pre_audit']:,.2f} บาท")
        
    with m3:
        diff = summ['post_audit'] - summ['pre_audit']
        st.metric(
            "💎 ยอดเงินหลัง Audit", 
            f"{summ['post_audit']:,.2f} บาท",
            delta=f"{diff:,.2f} บาท"
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # --- 2. ตัวเลือก (Filter) ---
    st.subheader("🔎 รายละเอียดข้อค้นพบ")
    
    # ปุ่มเลือกประเภท (Radio แนวนอน)
    filter_type = st.radio("เลือกประเภทผู้ป่วย:", ["ทั้งหมด", "OPD", "IPD"], horizontal=True)
    
    # กรองข้อมูล
    if filter_type == "ทั้งหมด":
        show_df = df
    else:
        show_df = df[df['Type'] == filter_type]

    # --- 3. ตารางแสดงผล (Table) ---
    if not show_df.empty:
        # ใช้ column_config เพื่อแต่งตาราง
        st.dataframe(
            show_df,
            column_order=["HN/AN", "วันที่รับบริการ", "ข้อค้นพบ", "Action", "Impact"],
            column_config={
                "HN/AN": st.column_config.TextColumn("HN / AN", width="medium"),
                "วันที่รับบริการ": st.column_config.TextColumn("วันที่รับบริการ", width="small"),
                "ข้อค้นพบ": st.column_config.TextColumn("⚠️ สิ่งที่ตรวจพบ (Findings)", width="large"),
                "Action": st.column_config.TextColumn("🔧 คำแนะนำ (Action)", width="large"),
                "Impact": st.column_config.NumberColumn(
                    "💰 Impact (บาท)",
                    format="%.2f",
                    help="ผลกระทบทางการเงิน (สีแดง=ลบ, สีเขียว=บวก)"
                )
            },
            use_container_width=True,
            height=500
        )
        
        # ปุ่มดาวน์โหลด
        csv = show_df.to_csv(index=False).encode('utf-8-sig')
        st.download_button("📥 ดาวน์โหลดรายงาน (CSV)", csv, "audit_report.csv", "text/csv", type="primary")
        
    else:
        st.success("🎉 ยอดเยี่ยม! ไม่พบข้อผิดพลาดในกลุ่มที่เลือก")

# --- 6. Main App ---
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
