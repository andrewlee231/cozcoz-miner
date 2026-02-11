import streamlit as st
import google.generativeai as genai
from apify_client import ApifyClient
import json
import pandas as pd

# -----------------------------------------------------------------------------
# 1. 페이지 설정
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="코즈코즈 파트너 마이너 (Drone Ver)",
    page_icon="🚁",
    layout="wide"
)

# -----------------------------------------------------------------------------
# 2. 기초 데이터
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
# 3. 사이드바
# -----------------------------------------------------------------------------
with st.sidebar:
    st.header("⚙️ 시스템 설정")
    api_key_gemini = st.text_input("Gemini API Key", type="password")
    api_key_apify = st.text_input("Apify API Key", type="password")
    st.success("✅ 성공률 높은 'Profile Scraper' 탑재")

# -----------------------------------------------------------------------------
# 4. 데이터 수집 (Profile Scraper 사용)
# -----------------------------------------------------------------------------
def fetch_instagram_data_apify(username, apify_key):
    if not apify_key: return None, "Apify 키가 없습니다."
    
    # 🚨 [핵심 변경] 성공했던 그 로봇(Profile Scraper)으로 교체
    ACTOR_ID = "apify/instagram-profile-scraper"
    
    client = ApifyClient(apify_key)
    
    # 이 로봇은 입력 방식이 단순합니다.
    run_input = { "usernames": [username] }
    
    try:
        run = client.actor(ACTOR_ID).call(run_input=run_input)
        dataset_items = list(client.dataset(run["defaultDatasetId"]).iterate_items())
        
        if not dataset_items:
            return None, "데이터 없음 (비공개 계정이거나 ID 오타)"
            
        # 첫 번째 결과(프로필 정보 + 최근 게시물 포함됨)만 반환
        return dataset_items[0], None 
    except Exception as e:
        return None, f"Apify 에러: {str(e)}"

def analyze_with_gemini(data, gemini_key):
    if not gemini_key: return None
    genai.configure(api_key=gemini_key)
    model = genai.GenerativeModel("gemini-1.5-pro-latest", generation_config={"response_mime_type": "application/json"})
    
    # Profile Scraper의 데이터 구조에 맞춰 파싱
    # 이 로봇은 'latestPosts'라는 목록 안에 게시물을 담아줍니다.
    
    raw_posts = data.get("latestPosts", [])
    simple_posts = []
    
    for p in raw_posts[:6]: # 최근 6개만 분석
        simple_posts.append({
            "caption": p.get("caption", "")[:100],
            "likes": p.get("likesCount", 0),
            "comments": p.get("commentsCount", 0),
            "type": "Video" if p.get("type") == "Video" else "Image"
        })

    profile_info = {
        "bio": data.get("biography", ""),
        "followers": data.get("followersCount", 0),
        "url": data.get("externalUrl", "")
    }

    # 에러 방지를 위해 변수에 담기
    profile_json = json.dumps(profile_info, ensure_ascii=False)
    posts_json = json.dumps(simple_posts, ensure_ascii=False)

    prompt = f"""
    당신은 마케팅 전략가입니다. 아래 데이터를 분석해 JSON으로 답하세요.
    [상품정보] {PRODUCT_KNOWLEDGE_BASE}
    [프로필] {profile_json}
    [최근 게시물] {posts_json}
    
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
st.title("💎 CozCoz Partner Miner (Drone Ver)")
st.caption("🚁 성공률이 가장 높은 'Profile Scraper' 모드입니다.")

target_username = st.text_input("인스타그램 ID 입력 (예: cozcoz_official)")

if st.button("분석 시작") and target_username:
    with st.spinner("드론이 정찰 중입니다... (약 15초 소요)"):
        raw_data, error = fetch_instagram_data_apify(target_username, api_key_apify)
        
        if error:
            st.error(f"❌ 실패: {error}")
            st.warning("팁: ID가 정확한지 확인해주세요.")
        else:
            st.success("데이터 확보! AI 분석 중...")
            res = analyze_with_gemini(raw_data, api_key_gemini)
            
            if res:
                st.divider()
                c1, c2, c3 = st.columns(3)
                c1.metric("팔로워", f"{raw_data.get('followersCount',0):,}명")
                c2.metric("전략", res['strategy']['type'])
                c3.info(f"📞 {res['basic']['contact']}")
                
                st.subheader("📋 제안서 초안")
                st.text_area("복사용", res['message'], height=250)
                st.success(res['strategy']['reason'])
