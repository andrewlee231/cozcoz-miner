import streamlit as st
import google.generativeai as genai
import requests
import json
import pandas as pd

# -----------------------------------------------------------------------------
# 1. 페이지 설정
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="코즈코즈 파트너 마이너 (Final)",
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
    api_key_rapid = st.text_input("RapidAPI Key", type="password", help="RapidAPI에서 발급받은 키 (X-RapidAPI-Key)")
    
    st.info("💡 엔진을 RapidAPI로 교체했습니다. 훨씬 안정적입니다.")

# -----------------------------------------------------------------------------
# 4. 데이터 수집 함수 (RapidAPI 사용)
# -----------------------------------------------------------------------------
def fetch_instagram_data_rapid(username, rapid_key):
    if not rapid_key: return None, "RapidAPI 키가 필요합니다."
    
    # 1. 사용자 정보 가져오기
    url_info = "https://instagram-scraper-2022.p.rapidapi.com/ig/info_username/"
    querystring = {"user": username}
    headers = {
        "X-RapidAPI-Key": rapid_key,
        "X-RapidAPI-Host": "instagram-scraper-2022.p.rapidapi.com"
    }
    
    try:
        # User Info 호출
        response_info = requests.get(url_info, headers=headers, params=querystring)
        data_info = response_info.json()
        
        if "user" not in data_info:
            return None, "사용자를 찾을 수 없습니다. (ID 확인)"
            
        user_pk = data_info['user']['pk'] # 유저 고유 번호
        
        # 2. 최근 게시물 가져오기 (댓글 분석을 위해)
        url_posts = "https://instagram-scraper-2022.p.rapidapi.com/ig/posts/"
        querystring_posts = {"id_user": user_pk}
        response_posts = requests.get(url_posts, headers=headers, params=querystring_posts)
        data_posts = response_posts.json()
        
        posts_list = data_posts.get('data', {}).get('user', {}).get('edge_owner_to_timeline_media', {}).get('edges', [])
        
        return {
            "profile": data_info['user'],
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
    
    # 게시물 데이터 경량화 (AI에게 보낼 것만 추림)
    simple_posts = []
    for p in posts[:10]: # 최근 10개
        node = p['node']
        caption = node['edge_media_to_caption']['edges'][0]['node']['text'] if node['edge_media_to_caption']['edges'] else ""
        simple_posts.append({
            "type": "Video" if node['is_video'] else "Image",
            "likes": node['edge_liked_by']['count'],
            "comments_count": node['edge_media_to_comment']['count'],
            "caption": caption[:200], # 너무 길면 자름
            "video_view_count": node.get('video_view_count', 0)
        })

    prompt = f"""
    당신은 마케팅 전략가입니다. 아래 데이터를 분석해 JSON으로 답하세요.
    [상품정보] {PRODUCT_KNOWLEDGE_BASE}
    [프로필]
    - Bio: {profile.get('biography', '')}
    - Link: {profile.get('external_url', '')}
    - Followers: {profile.get('follower_count', 0)}
    [최근 게시물 요약] {json.dumps(simple_posts, ensure_ascii=False)}
    
    [필수 분석 항목]
    1. 기초체력: 활동성, 릴스조회수(Video 타입만 평균), 컨택포인트(Bio+Link 분석)
    2. 진정성: 공구진행여부(Caption 분석), 주력 카테고리
    3. 구매력: 댓글 수와 좋아요 비율로 '찐팬 화력' 추정
    4. 전략: A/B/C 중 택1
    5. 제안서: DM 초안
    
    [출력형식]
    {{
        "basic": {{ "activity": "...", "reels_view": "...", "contact": "..." }},
        "auth": {{ "is_gonggu": "Yes/No", "category": "..." }},
        "power": {{ "engagement_rate": "...", "fan_power": "..." }},
        "strategy": {{ "type": "...", "reason": "..." }},
        "message": "..."
    }}
    """
    try:
        res = model.generate_content(prompt)
        return json.loads(res.text)
    except Exception as e:
        return None

# -----------------------------------------------------------------------------
# 5. 메인 화면
# -----------------------------------------------------------------------------
st.title("💎 CozCoz Partner Miner (Rapid Engine)")
st.info("🚀 RapidAPI 엔진을 탑재하여 깊은 분석이 가능합니다.")

target_username = st.text_input("인스타그램 ID 입력 (@제외)")

if st.button("분석 시작") and target_username:
    with st.status("데이터를 사오는 중입니다... (RapidAPI)") as status:
        raw_data, error = fetch_instagram_data_rapid(target_username, api_key_rapid)
        
        if error:
            st.error(f"실패: {error}")
            status.update(label="실패", state="error")
        else:
            st.write("AI가 심층 분석 중입니다...")
            res = analyze_with_gemini(raw_data, api_key_gemini)
            
            if res:
                status.update(label="완료!", state="complete")
                
                st.divider()
                st.header("📊 분석 결과")
                
                c1, c2, c3 = st.columns(3)
                c1.metric("릴스 평균 조회수", res['basic']['reels_view'])
                c2.metric("찐팬 화력(Engage)", res['power']['fan_power'])
                c3.info(f"📞 {res['basic']['contact']}")
                
                st.subheader("🎯 전략 및 제안서")
                st.success(f"추천 전략: {res['strategy']['type']} ({res['strategy']['reason']})")
                st.text_area("DM 복사용", res['message'], height=300)
