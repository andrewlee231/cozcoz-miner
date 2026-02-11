import streamlit as st
import google.generativeai as genai
from apify_client import ApifyClient
import json
import pandas as pd

# -----------------------------------------------------------------------------
# 1. 페이지 설정
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="코즈코즈 파트너 마이너 (Apify Ver)",
    page_icon="💎",
    layout="wide"
)

# -----------------------------------------------------------------------------
# 2. 기초 데이터 (지식 베이스)
# -----------------------------------------------------------------------------
PRODUCT_KNOWLEDGE_BASE = """
# [기초 데이터] 코즈코즈_두부토퍼_제안정보.md
## 1. 상품 기본 정보
- **상품명:** 코즈코즈 두부토퍼
- **핵심전략:** Meta 파트너십 광고 지원 (매출 발생 시 광고비 분담)
## 2. [제안 멘트 전략]
### 전략 A: [Growth Hacking] - 정체기 탈출형
- Hook: "꽉 막힌 도달, 본사 AI 기술로 뚫어드립니다."
### 전략 B: [Revenue Scaling] - 비즈니스형
- Hook: "오가닉의 한계, 'Meta 파트너십 광고'로 매출 3배 확장."
### 전략 C: [Branding] - 이미지/감성형
- Hook: "브랜드의 '메인 엠버서더' 제안."
"""

# -----------------------------------------------------------------------------
# 3. 사이드바 (설정)
# -----------------------------------------------------------------------------
with st.sidebar:
    st.header("⚙️ 시스템 설정")
    api_key_gemini = st.text_input("Gemini API Key", type="password")
    api_key_apify = st.text_input("Apify API Key", type="password")
    st.info("✅ Apify 로봇으로 복귀했습니다.")

# -----------------------------------------------------------------------------
# 4. 데이터 수집 함수 (Apify Actor 사용)
# -----------------------------------------------------------------------------
def fetch_instagram_data_apify(username, apify_key):
    if not apify_key: return None, "Apify 키가 없습니다."
    
    # 🚨 Apify의 표준 인스타그램 스크래퍼 사용
    ACTOR_ID = "apify/instagram-scraper"
    
    client = ApifyClient(apify_key)
    
    # 설정: 최근 게시물 5개만 가져오되, 댓글까지 긁어서 심층 분석
    run_input = {
        "usernames": [username],
        "resultsLimit": 5, 
        "scrapePosts": True,
        "scrapeComments": True, # 댓글 분석 활성화
    }
    
    try:
        # Actor 실행
        run = client.actor(ACTOR_ID).call(run_input=run_input)
        
        # 데이터 가져오기
        dataset_items = list(client.dataset(run["defaultDatasetId"]).iterate_items())
        
        if not dataset_items:
            return None, "데이터 수집 실패 (비공개 계정이거나 일시적 차단)"
            
        return dataset_items, None
    except Exception as e:
        return None, f"Apify 에러: {str(e)}"

def analyze_with_gemini(data, gemini_key):
    if not gemini_key: return None
    genai.configure(api_key=gemini_key)
    model = genai.GenerativeModel("gemini-1.5-pro-latest", generation_config={"response_mime_type": "application/json"})
    
    # 데이터 전처리 (프로필과 게시물 분리)
    profile_summary = {}
    posts_summary = []
    
    for item in data:
        # 게시물 데이터 정리
        if 'caption' in item: # 게시물인 경우
            posts_summary.append({
                "caption": item.get("caption", "")[:100],
                "likes": item.get("likesCount", 0),
                "comments": item.get("commentsCount", 0),
                "type": item.get("type", "Image")
            })
        
        # 프로필 데이터 찾기
        if 'followersCount' in item and not profile_summary:
            profile_summary = {
                "username": item.get("ownerUsername", ""),
                "followers": item.get("followersCount", 0),
                "bio": item.get("biography", ""),
                "url": item.get("externalUrl", "")
            }

    # [수정된 부분] 텍스트 변환을 미리 수행해서 에러 방지
    profile_txt = json.dumps(profile_summary, ensure_ascii=False)
    posts_txt = json.dumps(posts_summary, ensure_ascii=False)

    prompt = f"""
    당신은 마케팅 전략가입니다. 아래 데이터를 분석해 JSON으로 답하세요.
    [상품정보] {PRODUCT_KNOWLEDGE_BASE}
    [인플루언서 프로필] {profile_txt}
    [최근 게시물] {posts_txt}
    
    [출력형식]
    {{
        "basic": {{ "activity": "...", "contact": "..." }},
        "auth": {{ "is_gonggu": "...", "category": "..." }},
        "power": {{ "fan_power": "..." }},
        "strategy": {{ "type": "...", "reason": "..." }},
        "message": "..."
    }}
    """
    try:
        res = model.generate_content(prompt)
        return json.loads(res.text)
    except: return None

# -----------------------------------------------------------------------------
# 5. 메인 화면
# -----------------------------------------------------------------------------
st.title("💎 CozCoz Partner Miner (Apify)")
st.caption("돌아온 Apify 로봇")

target_username = st.text_input("인스타그램 ID 입력 (예: cozcoz_official)")

if st.button("분석 시작") and target_username:
    with st.spinner("Apify 로봇이 출동했습니다... (약 30~50초 소요)"):
        raw_data, error = fetch_instagram_data_apify(target_username, api_key_apify)
        
        if error:
            st.error(f"❌ 실패: {error}")
            st.warning("팁: 잠시 후에 다시 시도하거나, 다른 계정으로 테스트해보세요.")
        else:
            st.success("데이터 수집 성공! AI 분석 중...")
            res = analyze_with_gemini(raw_data, api_key_gemini)
            
            if res:
                st.divider()
                c1, c2 = st.columns(2)
                c1.metric("전략 유형", res['strategy']['type'])
                c2.info(f"📞 컨택: {res['basic']['contact']}")
                
                st.subheader("📋 제안서
