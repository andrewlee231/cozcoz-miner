import streamlit as st
import google.generativeai as genai
from apify_client import ApifyClient
import pandas as pd
import json

# 페이지 설정 (반드시 맨 처음에 와야 함)
st.set_page_config(
    page_title="코즈코즈 파트너 마이너",
    page_icon="💎",
    layout="wide"
)

# -----------------------------------------------------------------------------
# 1. 기초 데이터 (Knowledge Base) - 수정 가능 영역
# -----------------------------------------------------------------------------
PRODUCT_KNOWLEDGE_BASE = """
# [기초 데이터] 코즈코즈_두부토퍼_제안정보.md

## 1. 상품 기본 정보
- **상품명:** 코즈코즈 두부토퍼 (빨아쓰는 기능성 토퍼)
- **가격:** 공구가 39,800원~ (최대 71% 할인)
- **핵심전략:** Meta 파트너십 광고 지원 (매출 발생 시 광고비 분담)

## 2. [제안 멘트 전략] AI 자동 생성 가이드
### 전략 A: [Growth Hacking] - 정체기 탈출형
- **타겟:** 최근 팔로워 정체.
- **Hook:** "꽉 막힌 도달, 본사 AI 기술로 뚫어드립니다."
- **Message:** "단순 판매가 아닌, 계정에 '찐팬'을 유입시켜 드리는 트래픽 스폰서십."

### 전략 B: [Revenue Scaling] - 비즈니스형
- **타겟:** 공구 능숙, 구매 반응 많음.
- **Hook:** "오가닉의 한계, 'Meta 파트너십 광고'로 매출 3배 확장."
- **Message:** "구매 고관여 타겟에게 광고 송출, 압도적 정산금 경험."

### 전략 C: [Branding] - 이미지/감성형
- **타겟:** 공구 적음, 사진 고퀄리티.
- **Hook:** "브랜드의 '메인 엠버서더' 제안."
- **Message:** "본사 마케팅 팀의 전폭적인 계정 홍보 지원."
"""

# -----------------------------------------------------------------------------
# 2. 사이드바 (설정)
# -----------------------------------------------------------------------------
with st.sidebar:
    st.header("⚙️ 설정")
    api_key_gemini = st.text_input("Gemini API Key", type="password")
    api_key_apify = st.text_input("Apify API Key", type="password")
    st.info("API 키를 입력해야 작동합니다.")

# -----------------------------------------------------------------------------
# 3. 로직 함수
# -----------------------------------------------------------------------------
def fetch_instagram_data(username, apify_key):
    if not apify_key: return None, "Apify 키가 없습니다."
    client = ApifyClient(apify_key)
    run_input = { "usernames": [username], "resultsLimit": 15, "scrapePosts": True, "scrapeComments": True }
    try:
        run = client.actor("apify/instagram-scraper").call(run_input=run_input)
        dataset_items = list(client.dataset(run["defaultDatasetId"]).iterate_items())
        return dataset_items, None
    except Exception as e: return None, str(e)

def analyze_with_gemini(data, gemini_key):
    if not gemini_key: return None
    genai.configure(api_key=gemini_key)
    model = genai.GenerativeModel("gemini-1.5-pro-latest", generation_config={"response_mime_type": "application/json"})
    
    prompt = f"""
    당신은 마케팅 전략가입니다. 아래 데이터를 분석해 JSON으로 답하세요.
    
    [상품정보] {PRODUCT_KNOWLEDGE_BASE}
    [인플루언서 데이터] {str(data)[:20000]}
    
    [요구사항]
    1. 기초체력: 활동성, 릴스조회수(영상만), 팔로워추세, 컨택포인트(Bio분석)
    2. 진정성: 공구횟수, 빌드업지수(게시물수/공구건수), 최근카테고리
    3. 구매력: 찐팬비율, 구매시그널수
    4. 전략선택: A/B/C 중 택1 및 이유
    5. 제안서: Hook을 포함한 DM 초안
    
    [출력형식]
    {{
        "basic": {{ "activity": "", "reels_view": "", "trend": "", "contact": "" }},
        "auth": {{ "count": 0, "buildup": 0.0, "category": "", "competitor": "" }},
        "power": {{ "fan_ratio": "", "signals": 0, "cs": "" }},
        "strategy": {{ "type": "", "reason": "" }},
        "message": ""
    }}
    """
    try:
        res = model.generate_content(prompt)
        return json.loads(res.text)
    except: return None

# -----------------------------------------------------------------------------
# 4. 메인 화면
# -----------------------------------------------------------------------------
st.title("💎 CozCoz Partner Miner")
target_username = st.text_input("인스타그램 ID 입력 (@제외)")

if st.button("분석 시작") and target_username:
    with st.status("데이터 채굴 중..."):
        raw_data, err = fetch_instagram_data(target_username, api_key_apify)
        if raw_data:
            st.write("AI 분석 중...")
            res = analyze_with_gemini(raw_data, api_key_gemini)
            if res:
                st.success("분석 완료!")
                
                # 결과 출력
                st.header("1. 기초 체력")
                c1, c2, c3 = st.columns(3)
                c1.metric("활동성", res['basic']['activity'])
                c2.metric("릴스 조회수", res['basic']['reels_view'])
                c3.info(f"📞 {res['basic']['contact']}")
                
                st.header("2. 진정성 & 구매력")
                c4, c5, c6 = st.columns(3)
                c4.metric("월 공구", f"{res['auth']['count']}회")
                c5.metric("빌드업 지수", f"{res['auth']['buildup']}")
                c6.metric("구매 시그널", f"{res['power']['signals']}건")
                st.caption(f"최근 카테고리: {res['auth']['category']}")
                
                st.header("3. AI 제안 전략")
                st.success(f"추천: {res['strategy']['type']}")
                st.write(res['strategy']['reason'])
                
                st.subheader("📋 제안서 초안")
                st.text_area("복사용", res['message'], height=250)
        else:
            st.error(f"실패: {err}")