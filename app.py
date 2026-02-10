import streamlit as st
import google.generativeai as genai
import requests
import json

# -----------------------------------------------------------------------------
# 1. 페이지 설정
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="코즈코즈 파트너 마이너 (Rapid 2025)",
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
    st.header("⚙️ 시스템 설정")
    api_key_gemini = st.text_input("Gemini API Key", type="password")
    api_key_rapid = st.text_input("RapidAPI Key", type="password")
    st.caption("✅ Instagram Scraper 2025 엔진 탑재")

# -----------------------------------------------------------------------------
# 4. 데이터 수집 함수 (2025년형 수정완료!)
# -----------------------------------------------------------------------------
def fetch_instagram_data_rapid(username, rapid_key):
    if not rapid_key: return None, "RapidAPI 키가 필요합니다."
    
    # 🚨 중요: 2025년형 호스트 주소로 변경됨
    HOST = "instagram-scraper-20251.p.rapidapi.com"
    HEADERS = {
        "x-rapidapi-key": rapid_key,
        "x-rapidapi-host": HOST
    }
    
    try:
        # 1. 유저 정보 가져오기 (/userinfo)
        url_info = f"https://{HOST}/userinfo"
        qs_info = {"username_or_id_url": username} # 파라미터명 변경됨
        
        resp_info = requests.get(url_info, headers=HEADERS, params=qs_info)
        
        if resp_info.status_code != 200:
            return None, f"API 오류 ({resp_info.status_code}): {resp_info.text}"
            
        data_info = resp_info.json()
        
        # 데이터 구조가 복잡해서 안전하게 파싱
        if "data" in data_info:
            profile = data_info["data"]
        else:
            profile = data_info # 구조가 다를 경우 대비
            
        if not profile or "id" not in profile:
             return None, "사용자를 찾을 수 없습니다. (ID 확인)"
             
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
    
    # 데이터 경량화
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
    - Link: {profile.get('external_url', '')}
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
st.title("💎 CozCoz Partner Miner (2025 Ver)")
st.caption("🚀 최신 RapidAPI 엔진이 적용되었습니다.")

target_username = st.text_input("인스타그램 ID 입력")

if st.button("분석 시작") and target_username:
    with st.status("데이터 수집 중... (2025 Engine)") as status:
        raw_data, error = fetch_instagram_data_rapid(target_username, api_key_rapid)
        
        if error:
            st.error(f"❌ 실패: {error}")
            status.update(label="실패", state="error")
        else:
            st.write("AI 분석 중...")
            res = analyze_with_gemini(raw_data, api_key_gemini)
            
            if res:
                status.update(label="완료!", state="complete")
                st.divider()
                
                c1, c2, c3 = st.columns(3)
                c1.metric("팔로워", f"{raw_data['profile'].get('follower_count',0):,}명")
                c2.metric("전략", res['strategy']['type'])
                c3.info(res['basic']['contact'])
                
                st.subheader("📋 제안서 초안")
                st.text_area("복사용", res['message'], height=250)
                st.success(res['strategy']['reason'])
