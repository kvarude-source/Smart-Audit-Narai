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
if 'audit_data' not in st.
