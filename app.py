import streamlit as st
import google.generativeai as genai
from apify_client import ApifyClient
import json
import pandas as pd
from datetime import datetime, timedelta
import statistics
import traceback # 에러 추적용 도구

# -----------------------------------------------------------------------------
# 1. 페이지 설정
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="코즈코즈 파트너 마이너 (Debug Mode)",
    page_icon="🔧",
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
    st.warning("🔧 디버그 모드 작동 중")
    st.caption("모든 처리 과정이 화면에 표시됩니다.")

# -----------------------------------------------------------------------------
# 4. 데이터 수집 & 가공 함수 (로그 출력 추가)
# -----------------------------------------------------------------------------
def fetch_instagram_data_apify(username, apify_key):
    if not apify_key: return None, "Apify 키가 없습니다."
    
    ACTOR_ID = "apify/instagram-scraper"
    client = ApifyClient(apify_key)
    
    run_input = {
        "usernames": [username],
        "resultsLimit": 15, 
        "scrapePosts": True,
        "scrapeComments": True,
    }
    
    try:
        # [로그] 실행 시작
        st.toast(f"🤖 Apify 로봇에게 '{username}' 수집 명령 전달...")
        
        run = client.actor(ACTOR_ID).call(run_input=run_input)
        
        # [로그] 수집 완료
        dataset_items = list(client.dataset(run["defaultDatasetId"]).iterate_items())
        
        if not dataset_items:
            return None, "데이터가 비어있습니다. (비공개 계정 또는 차단)"
            
        return dataset_items, None
    except Exception as e:
        # [로그] 상세 에러 리턴
        return None, f"Apify 에러 발생: {str(e)}"

def calculate_raw_metrics(data):
    """수집된 데이터에서 '실제 지표'를 계산하는 함수"""
    
    profile = {}
    posts = []
    for item in data:
        if 'followersCount' in item and not profile:
            profile = item
        if 'caption' in item:
            posts.append(item)
            
    if not profile:
        profile = posts[0] if posts else {}

    recent_posts = posts[:10]
    
    likes_list = [p.get('likesCount', 0) for p in recent_posts]
    comments_list = [p.get('commentsCount', 0) for p in recent_posts]
    
    avg_likes = statistics.mean(likes_list) if likes_list else 0
    avg_comments = statistics.mean(comments_list) if comments_list else 0
    
    one_month_ago = datetime.utcnow() - timedelta(days=30)
    month_post_count = 0
    
    for p in posts:
        ts_str = p.get('timestamp')
        if ts_str:
            try:
                ts = datetime.strptime(ts_str.replace('Z', ''), "%Y-%m-%dT%H:%M:%S.%f") if '.' in ts_str else datetime.strptime(ts_str.replace('Z', ''), "%Y-%m-%dT%H:%M:%S")
                if ts > one_month_ago:
                    month_post_count += 1
            except: pass

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
        "recent_posts_data": recent_posts
    }

def analyze_with_gemini(raw_metrics, gemini_key):
    if not gemini_key: 
        st.error("Gemini API 키가 입력되지 않았습니다.")
        return None
        
    genai.configure(api_key=gemini_key)
    model = genai.GenerativeModel("gemini-1.5-pro-latest", generation_config={"response_mime_type": "application/json"})
    
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
        # [로그] AI 요청 시작
        st.toast("🧠 Gemini에게 분석 요청 중...")
        res = model.generate_content(prompt)
        return json.loads(res.text)
    except Exception as e:
        # 🚨 여기서 에러가 나면 화면에 바로 찍어버림
        st.error("❌ Gemini 분석 중 치명적 오류 발생!")
        st.code(traceback.format_exc()) # 에러 위치 추적
        return None

# -----------------------------------------------------------------------------
# 5. 메인 화면 UI (디버그 창 포함)
# -----------------------------------------------------------------------------
st.title("🔧 CozCoz Partner Miner (Debug)")
st.caption("에러가 나면 아래 '상세 로그'를 열어보세요.")

target_username = st.text_input("인스타그램 ID 입력 (예: cozcoz_official)")

if st.button("🚀 분석 시작") and target_username:
    
    # 1. 상세 로그를 볼 수 있는 확장형 박스 생성
    debug_expander = st.expander("🔍 [개발자용] 상세 처리 과정 로그 (클릭)", expanded=True)
    
    with debug_expander:
        st.write("1️⃣ 데이터 수집 시작...")
        raw_data_list, error = fetch_instagram_data_apify(target_username, api_key_apify)
        
        if error:
            st.error(f"수집 실패: {error}")
        else:
            st.success(f"수집 성공! 데이터 {len(raw_data_list)}개 확보")
            # [디버그] 수집된 데이터 샘플 보여주기
            st.json(raw_data_list[0] if raw_data_list else "데이터 없음")
            
            st.write("2️⃣ 통계 데이터 가공 중...")
            metrics = calculate_raw_metrics(raw_data_list)
            st.json(metrics) # 계산된 통계 보여주기
            
            st.write("3️⃣ AI 분석 요청 중...")
            ai_res = analyze_with_gemini(metrics, api_key_gemini)
            
            if ai_res:
                st.success("AI 분석 완료!")
                
                # --- [결과 화면] ---
                st.divider()
                st.subheader("✅ 최종 결과 리포트")
                
                c1, c2, c3 = st.columns(3)
                c1.metric("추천 전략", ai_res['strategy']['type'])
                c2.metric("팔로워", f"{metrics['followers']:,}명")
                c3.info(f"📞 {ai_res['basic']['contact']}")
                
                st.success(f"💡 선정 이유: {ai_res['strategy']['reason']}")
                st.subheader("📨 제안서")
                st.code(ai_res['message'], language="text")
                
            else:
                st.error("AI가 응답하지 못했습니다. 위 로그를 확인하세요.")
