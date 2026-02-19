import streamlit as st
import google.generativeai as genai
from apify_client import ApifyClient
import json
from datetime import datetime, timedelta
import statistics

# -----------------------------------------------------------------------------
# 1. 페이지 설정 & UI 가독성 패치 (CSS 주입)
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="CozCoz Partner Miner (Master)",
    page_icon="💎",
    layout="wide"
)

# 🚨 [가독성 최적화 CSS] 폰트 축소, 제안서 스크롤 해제, 복사버튼 강조
st.markdown("""
<style>
    /* 전체 폰트 사이즈 약간 축소 */
    html, body, [class*="css"]  {
        font-size: 14px !important; 
    }
    
    /* 제목(Header) 폰트 사이즈 축소 */
    h1 { font-size: 1.6rem !important; margin-bottom: 0rem !important; }
    h2 { font-size: 1.3rem !important; margin-bottom: 0rem !important; }
    h3 { font-size: 1.1rem !important; margin-bottom: 0rem !important; }
    h4 { font-size: 1.0rem !important; margin-bottom: 0rem !important; }

    /* 메트릭(지표 숫자) 사이즈 압축 */
    [data-testid="stMetricValue"] {
        font-size: 1.3rem !important;
    }
    [data-testid="stMetricLabel"] {
        font-size: 0.85rem !important;
        color: #555 !important;
    }

    /* 💡 [핵심] 제안서 코드 박스 세로 스크롤 없애고 전체 펼치기 */
    .stCodeBlock pre {
        max-height: none !important; /* 높이 제한 해제 */
        white-space: pre-wrap !important; /* 가로 자동 줄바꿈 */
        word-break: break-word !important;
        background-color: #f8f9fa !important;
    }
    .stCodeBlock code {
        font-size: 13.5px !important;
        white-space: pre-wrap !important;
    }

    /* 💡 [핵심] 복사(Copy) 버튼 상시 노출 및 강조 */
    .stCodeBlock button {
        opacity: 1 !important; /* 마우스 안 올려도 항상 보임 */
        transform: scale(1.3); /* 크기 1.3배 확대 */
        right: 15px !important;
        top: 15px !important;
        background-color: #e9ecef !important;
        border-radius: 4px !important;
        border: 1px solid #ced4da !important;
    }
</style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 2. 세션 상태 (MD 파일 유지 기능)
# -----------------------------------------------------------------------------
if "md_content" not in st.session_state:
    st.session_state.md_content = ""
if "md_filename" not in st.session_state:
    st.session_state.md_filename = "업로드된 파일 없음"

# -----------------------------------------------------------------------------
# 3. 사이드바 (설정 & MD 파일 업로드)
# -----------------------------------------------------------------------------
with st.sidebar:
    st.header("⚙️ 시스템 설정")
    api_key_gemini = st.text_input("Gemini API Key", type="password")
    api_key_apify = st.text_input("Apify API Key", type="password")
    
    st.divider()
    st.markdown("#### 📄 제안 전략(MD) 파일 업로드")
    uploaded_file = st.file_uploader("가이드라인 MD/TXT 파일을 올려주세요.", type=['md', 'txt'])
    
    if uploaded_file is not None:
        st.session_state.md_content = uploaded_file.read().decode("utf-8")
