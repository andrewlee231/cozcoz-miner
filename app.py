import streamlit as st
import google.generativeai as genai
from apify_client import ApifyClient
import json
import pandas as pd
from datetime import datetime, timedelta
import statistics

# -----------------------------------------------------------------------------
# 1. 페이지 설정
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="코즈코즈 파트너 마이너 (Dashboard V4)",
    page_icon="🇨🇳",
    layout="wide"
)

# -----------------------------------------------------------------------------
# 2. 기초 데이터
# -----------------------------------------------------------------------------
PRODUCT_KNOWLEDGE_BASE = """
# [기초 데이터] 코즈코즈_두부토퍼_제안정보.md
## 1. 상품 기본 정보
- **상품명:** 코즈코즈 두부토퍼 (빨아쓰는 3단 접이식 토퍼)
- **타겟:** 육아맘, 반려동물 가정, 1인 가구
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
    st.success("🇨🇳 China Roaming Mode ON")
    st.caption("소프트뱅크 로밍망을 이용하여\n보안 우회 가능성이 높습니다.")

# -----------------------------------------------------------------------------
# 4. 데이터 수집 & 가공 함수
# -----------------------------------------------------------------------------
def fetch_instagram_data_apify(username, apify_key):
    if not apify_key: return None, "Apify 키가 없습니다."
    
    ACTOR_ID = "apify/instagram-scraper"
    client = ApifyClient(apify_key)
    
    # 통계 산출을 위해 넉넉히 15개 수집
    run_input = {
        "usernames": [username],
        "resultsLimit": 15, 
        "scrapePosts": True,
        "scrapeComments": True,
    }
    
    try:
        run = client.actor(ACTOR_ID).call(run_input=run_input)
        dataset_items = list(client.dataset(run["defaultDatasetId"]).iterate_items())
        
        if not dataset_items:
            return None, "데이터 수집 실패 (비공개 계정 또는 차단)"
            
        return dataset_items, None
    except Exception as e:
        return None, f"Apify 에러: {str(e)}"

def calculate_raw_metrics(data):
    """수집된 데이터에서 '실제 지표'를 계산하는 함수"""
    
    # 1. 프로필 찾기
    profile = {}
    posts = []
    for item in data:
        if 'followersCount' in item and not profile:
            profile = item
        if 'caption' in item: # 게시물만 필터링
            posts.append(item)
            
    if not profile:
        profile = posts[0] if posts else {} # 비상용

    # 2. 최근 10개 게시물 통계
    recent_posts = posts[:10]
    
    likes_list = [p.get('likesCount', 0) for p in recent_posts]
    comments_list = [p.get('commentsCount', 0) for p in recent_posts]
    
    avg_likes = statistics.mean(likes_list) if likes_list else 0
    avg_comments = statistics.mean(comments_list) if comments_list else 0
    
    # 3. 최근 한 달 게시물 수 계산
    one_month_ago = datetime.utcnow() - timedelta(days=30)
    month_post_count = 0
    
    for p in posts:
        ts_str = p.get('timestamp')
        if ts_str:
            try:
                # 타임스탬프 형식 처리 (ISO format)
                ts = datetime.strptime(ts_str.replace('Z', ''), "%Y-%m-%dT%H:%M:%S.%f") if '.' in ts_str else datetime.strptime(ts_str.replace('Z', ''), "%Y-%m-%dT%H:%M:%S")
                if ts > one_month_ago:
                    month_post_count += 1
            except:
                pass # 날짜 파싱 실패시 패스

    return {
        "username": profile.get('ownerUsername', ''),
        "followers": profile.get('followersCount', 0),
        "total_posts": profile.get('postsCount', 0),
        "bio": profile.get('biography', ''),
        "month_post_count": month_post_count,
        "likes_list": likes_list,
        "likes_avg": round(avg_likes, 1),
        "comments_list": comments_list,
        "comments_avg": round(avg_comments, 1),
        "recent_posts_data": recent_posts # AI에게 넘길 데이터
    }

def analyze_with_gemini(raw_metrics, gemini_key):
    if not gemini_key: return None
    genai.configure(api_key=gemini_key)
    model = genai.GenerativeModel("gemini-1.5-pro-latest", generation_config={"response_mime_type": "application/json"})
    
    # AI에게 넘길 데이터 경량화
    posts_for_ai = []
    for p in raw_metrics['recent_posts_data']:
        posts_for_ai.append({
            "caption": p.get("caption", "")[:150],
            "likes": p.get("likesCount", 0),
            "date": p.get("timestamp", "")
        })

    prompt = f"""
    당신은 E-commerce 전략가입니다. 아래 데이터를 분석해 JSON으로 답하세요.
    [상품정보] {PRODUCT_KNOWLEDGE_BASE}
    [프로필 및 통계]
    - Bio: {raw_metrics['bio']}
    - Followers: {raw_metrics['followers']}
    - Avg Likes: {raw_metrics['likes_avg']}
    [최근 게시물] {json.dumps(posts_for_ai, ensure_ascii=False)}
    
    [분석 요청사항]
    1. 기초체력: 활동성, 컨택포인트(Bio 분석하여 카톡/이메일 추출)
    2. 공구이력추적: 게시물 캡션들을 분석해서 **최근 한 달간 진행한 것으로 보이는 공구 제품명**을 추출해줘. (없으면 '없음'으로 표기)
    3. 전략선택: A/B/C 중 택1
    4. 제안서: DM 초안 작성
    
    [출력형식]
    {{
        "basic": {{ "activity": "...", "contact": "..." }},
        "history": {{ "recent_products": ["제품1", "제품2"] }}, 
        "strategy": {{ "type": "...", "reason": "..." }},
        "message": "..."
    }}
    """
    try:
        res = model.generate_content(prompt)
        return json.loads(res.text)
    except: return None

# -----------------------------------------------------------------------------
# 5. 메인 화면 UI
# -----------------------------------------------------------------------------
st.title("🇨🇳 CozCoz Partner Miner (Dashboard)")
st.caption("AI 전략 분석 + 팩트 체크(Raw Data) 통합 버전")

target_username = st.text_input("인스타그램 ID 입력 (예: cozcoz_official)")

if st.button("🚀 분석 시작") and target_username:
    with st.spinner("1단계: 로봇이 데이터를 채굴 중입니다..."):
        raw_data_list, error = fetch_instagram_data_apify(target_username, api_key_apify)
        
        if error:
            st.error(f"❌ 실패: {error}")
        else:
            # 2단계: 데이터 가공 (통계 계산)
            metrics = calculate_raw_metrics(raw_data_list)
            
            with st.spinner("2단계: AI가 전략을 수립 중입니다..."):
                ai_res = analyze_with_gemini(metrics, api_key_gemini)
                
                if ai_res:
                    # --- [상단] AI 분석 결과 ---
                    st.divider()
                    st.subheader("🤖 AI 전략 리포트")
                    
                    c1, c2, c3 = st.columns(3)
                    c1.metric("추천 전략", ai_res['strategy']['type'])
                    c2.metric("팔로워", f"{metrics['followers']:,}명")
                    c3.info(f"📞 {ai_res['basic']['contact']}")
                    
                    st.success(f"💡 선정 이유: {ai_res['strategy']['reason']}")
                    
                    # DM 제안서 (복사 버튼 포함)
                    st.subheader("📨 제안서 (자동 생성)")
                    st.caption("오른쪽 위의 📄 버튼을 누르면 복사됩니다.")
                    st.code(ai_res['message'], language="text") # st.code는 복사 버튼이 자동 내장됨
                    
                    # --- [하단] 팩트 체크 (Raw Data) ---
                    st.divider()
                    st.subheader("📉 [참고자료] 실제 지표 (Raw Data)")
                    st.caption("AI 분석 전, 실제 수집된 팩트 데이터입니다.")
                    
                    with st.container(border=True):
                        col_a, col_b = st.columns(2)
                        
                        with col_a:
                            st.markdown("**1. 활동성 지표**")
                            st.text(f"• 전체 게시물 수: {metrics['total_posts']:,}개")
                            st.text(f"• 최근 1달 게시물: {metrics['month_post_count']}개 (수집 범위 내)")
                            st.text(f"• 팔로워 수: {metrics['followers']:,}명")
                            
                            st.markdown("---")
                            st.markdown("**2. 최근 10개 반응도 (평균)**")
                            st.text(f"• 좋아요: 평균 {metrics['likes_avg']}개")
                            st.caption(f"상세: {metrics['likes_list']}")
                            st.text(f"• 댓글: 평균 {metrics['comments_avg']}개")
                            st.caption(f"상세: {metrics['comments_list']}")

                        with col_b:
                            st.markdown("**3. 바이오그래피 (원문)**")
                            st.info(metrics['bio'])
                            
                            st.markdown("**4. 최근 공구 이력 (AI 추출)**")
                            products = ai_res['history']['recent_products']
                            if products and products[0] != "없음":
                                for prod in products:
                                    st.write(f"- 🏷️ {prod}")
                            else:
                                st.write("- 🔍 감지된 공구 제품 없음")
                                
                else:
                    st.error("AI 분석 중 오류가 발생했습니다.")
