import streamlit as st
import google.generativeai as genai
import requests
import json

# -----------------------------------------------------------------------------
# 1. 페이지 설정
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="코즈코즈 파트너 마이너 (Final Fix)",
    page_icon="💎",
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
    st.header("⚙️ 설정")
    api_key_gemini = st.text_input("Gemini API Key", type="password")
    api_key_rapid = st.text_input("RapidAPI Key", type="password")
    st.info("✅ 2025년형 파라미터 패치 완료")

# -----------------------------------------------------------------------------
# 4. 데이터 수집 함수 (파라미터 이름 수정됨)
# -----------------------------------------------------------------------------
def fetch_instagram_data_rapid(username, rapid_key):
    if not rapid_key: return None, "RapidAPI 키가 필요합니다."
    
    HOST = "instagram-scraper-20251.p.rapidapi.com"
    HEADERS = {
        "x-rapidapi-key": rapid_key,
        "x-rapidapi-host": HOST
    }
    
    try:
        # 1. 유저 정보 가져오기 (/userinfo)
        url_info = f"https://{HOST}/userinfo"
        
        # 🚨 [수정된 부분] 파라미터 이름을 API 명세서에 맞게 변경
        qs_info = {"username_or_id_username": username} 
        
        resp_info = requests.get(url_info, headers=HEADERS, params=qs_info)
        
        if resp_info.status_code != 200:
            # 에러 메시지를 더 자세히 반환
            return None, f"유저 검색 실패 ({resp_info.status_code}): {resp_info.text}"
            
        data_info = resp_info.json()
        
        # 데이터 구조 파싱
        if "data" in data_info:
            profile = data_info["data"]
        else:
            profile = data_info
            
        if not profile or "id" not in profile:
             return None, f"사용자 정보 없음 (응답값: {str(data_info)[:100]}...)"
             
        user_id = profile["id"]
        
        # 2. 게시물 가져오기 (/userposts)
        url_posts = f"https://{HOST}/userposts"
        qs_posts = {"userid": user_id, "limit": "10"}
        
        resp_posts = requests.get(url_posts, headers=HEADERS, params=qs_posts)
        data_posts = resp_posts.json()
        
        posts_list = []
        if "data" in data_posts and "items" in data_posts["data"]:
             posts_list = data_posts["data"]["items"]
        
        return {
            "profile": profile,
            "posts": posts_list
        }, None
        
    except Exception as e:
        return None, f"통신 에러: {str(e)}"

def analyze_with_gemini(data, gemini_key):
    if not gemini_key: return None
    genai.configure(api_key=gemini_key)
    model = genai.GenerativeModel("gemini-1.5-pro-latest", generation_config={"response_mime_type": "application/json"})
    
    profile = data['profile']
    posts = data['posts']
    
    simple_posts = []
    for p in posts[:8]:
        caption = p.get("caption", {}).get("text", "") if p.get("caption") else ""
        simple_posts.append({
            "type": "Video" if p.get("is_video") else "Image",
            "likes": p.get("like_count", 0),
            "comments": p.get("comment_count", 0),
            "caption": caption[:100]
        })

    prompt = f"""
    당신은 마케팅 전략가입니다. 아래 데이터를 분석해 JSON으로 답하세요.
    [상품정보] {PRODUCT_KNOWLEDGE_BASE}
    [프로필]
    - Bio: {profile.get('biography', '')}
    - Followers: {profile.get('follower_count', 0)}
    [최근 게시물] {json.dumps(simple_posts, ensure_ascii=False)}
    
    [출력형식]
    {{
        "basic": {{ "activity": "...", "reels_view": "...", "contact": "..." }},
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
st.title("💎 CozCoz Partner Miner (Final Fix)")

target_username = st.text_input("인스타그램 ID 입력 (예: nike)")

if st.button("분석 시작") and target_username:
    # 에러 메시지를 밖으로 꺼내기 위해 st.status 대신 st.spinner 사용
    with st.spinner("데이터 수집 중... (Rapid 2025)"):
        raw_data, error = fetch_instagram_data_rapid(target_username, api_key_rapid)
        
        if error:
            # 빨간색 박스로 에러를 크게 보여줌
            st.error(f"❌ 분석 실패: {error}")
            st.warning("팁: RapidAPI 키가 정확한지, ID에 오타는 없는지 확인해주세요.")
        else:
            st.success("데이터 수집 성공! AI 분석 시작...")
            res = analyze_with_gemini(raw_data, api_key_gemini)
            
            if res:
                st.divider()
                c1, c2, c3 = st.columns(3)
                c1.metric("팔로워", f"{raw_data['profile'].get('follower_count',0):,}명")
                c2.metric("전략", res['strategy']['type'])
                c3.info(res['basic']['contact'])
                
                st.subheader("📋 제안서 초안")
                st.text_area("복사용", res['message'], height=250)
                st.success(res['strategy']['reason'])
