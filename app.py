import streamlit as st
import google.generativeai as genai
from apify_client import ApifyClient
import json
import pandas as pd
from datetime import datetime, timedelta
import statistics
import traceback 

# -----------------------------------------------------------------------------
# 1. 페이지 설정
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="코즈코즈 파트너 마이너 (Gen 2.0 Flash)",
    page_icon="⚡",
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
    
    st.success("⚡ Gemini 2.0 Flash 탑재")
    st.caption("빠르고 강력하며, 사용량 제한이 넉넉합니다.")

# -----------------------------------------------------------------------------
# 4. 데이터 수집 & 가공 함수
# -----------------------------------------------------------------------------
def fetch_instagram_data_apify(username, apify_key):
    if not apify_key: return None, "Apify 키가 없습니다."
    
    # 🚨 로봇 교체 완료: instagram-profile-scraper
    ACTOR_ID = "apify/instagram-profile-scraper"
    client = ApifyClient(apify_key)
    
    # Profile Scraper에 맞춘 심플한 입력값
    run_input = {
        "usernames": [username]
    }
    
    try:
        st.toast(f"🚁 드론 로봇이 '{username}' 프로필을 스캔 중...", icon="🚁")
        run = client.actor(ACTOR_ID).call(run_input=run_input)
        dataset_items = list(client.dataset(run["defaultDatasetId"]).iterate_items())
        
        if not dataset_items:
            return None, "데이터 없음 (비공개 계정 또는 차단)"
            
        # Profile Scraper는 1개의 딕셔너리에 프로필과 게시물을 모두 담아 반환함
        return dataset_items[0], None 
    except Exception as e:
        return None, f"Apify 에러: {str(e)}"

def calculate_raw_metrics(data):
    """Profile Scraper 구조에 맞춰 '실제 지표'를 계산하는 함수"""
    
    profile = data
    # 게시물 데이터는 'latestPosts' 안에 리스트로 들어있음
    posts = data.get('latestPosts', []) 
    
    # 최근 10개 게시물 통계
    recent_10_posts = posts[:10]
    
    likes_list = [p.get('likesCount', 0) for p in recent_10_posts]
    comments_list = [p.get('commentsCount', 0) for p in recent_10_posts]
    
    avg_likes = round(statistics.mean(likes_list), 1) if likes_list else 0
    avg_comments = round(statistics.mean(comments_list), 1) if comments_list else 0
    
    # 최근 1달 게시물 수 계산
    one_month_ago = datetime.utcnow() - timedelta(days=30)
    month_post_count = 0
    
    for p in posts:
        ts_str = p.get('timestamp')
        if ts_str:
            try:
                if '.' in ts_str:
                    ts = datetime.strptime(ts_str.replace('Z', ''), "%Y-%m-%dT%H:%M:%S.%f")
                else:
                    ts = datetime.strptime(ts_str.replace('Z', ''), "%Y-%m-%dT%H:%M:%S")
                if ts > one_month_ago:
                    month_post_count += 1
            except: pass

    # AI에게 넘겨줄 최종 규격 (기존과 100% 동일하게 맞춰서 다른 코드 변경 불필요)
    return {
        "username": profile.get('username', profile.get('ownerUsername', '')),
        "followers": profile.get('followersCount', 0),
        "total_posts": profile.get('postsCount', 0),
        "bio": profile.get('biography', ''),
        "month_post_count": month_post_count,
        "likes_list": likes_list,
        "likes_avg": avg_likes,
        "comments_list": comments_list,
        "comments_avg": avg_comments,
        "recent_posts_data": recent_10_posts
    }

# 👇 여기서부터 이어지는 def analyze_with_gemini(...) 함수는 건드리지 마세요!

def analyze_with_gemini(raw_metrics, gemini_key):
    if not gemini_key: 
        st.error("Gemini API 키가 없습니다.")
        return None
        
    genai.configure(api_key=gemini_key)
    
    # 🚨 [해결책] 3.0(할당량 초과) 대신 2.0 Flash(속도+가성비) 사용
    model_name = "gemini-2.0-flash" 
    
    model = genai.GenerativeModel(model_name, generation_config={"response_mime_type": "application/json"})
    
    posts_text = []
    for p in raw_metrics['recent_posts_data']:
        posts_text.append({
            "caption": p.get("caption", "")[:500],
            "date": p.get("timestamp", "")
        })

    prompt = f"""
    당신은 10년차 E-commerce 전략가입니다. 아래 데이터를 분석해 JSON으로 답하세요.
    
    [상품정보] {PRODUCT_KNOWLEDGE_BASE}
    [프로필 정보]
    - Bio: {raw_metrics['bio']}
    - Followers: {raw_metrics['followers']}
    [최근 게시물 텍스트] {json.dumps(posts_text, ensure_ascii=False)}
    
    [분석 요청사항]
    1. 기초체력: 활동성 평가, 컨택포인트(Bio에서 카톡/이메일/DM 중 확인되는 것)
    2. **공구이력추출:** 게시물 캡션을 읽고, 최근 한 달간 판매(공구)를 진행한 **'제품명'**을 리스트로 추출. (없으면 빈 리스트)
    3. 전략선택: A/B/C 중 택1
    4. 제안서: 타겟의 상황에 맞춘 정중하고 매력적인 DM 초안.
    
    [출력형식]
    {{
        "basic": {{ "activity": "...", "contact": "..." }},
        "gonggu_history": ["제품A", "제품B"], 
        "strategy": {{ "type": "...", "reason": "..." }},
        "message": "..."
    }}
    """
    try:
        st.toast(f"⚡ {model_name} 모델이 초고속 분석 중...", icon="⚡")
        res = model.generate_content(prompt)
        return json.loads(res.text)
    except Exception as e:
        st.error(f"AI 분석 오류: {str(e)}")
        # 만약 이것도 429가 뜨면 정말 사용량이 꽉 찬 것이므로 1.5 Flash로 낮춰야 함을 안내
        if "429" in str(e):
            st.error("🚨 오늘의 AI 사용량이 모두 소진된 것 같습니다. 내일 다시 시도하거나 구글 클라우드 할당량을 확인하세요.")
        return None

# -----------------------------------------------------------------------------
# 5. 메인 화면 UI
# -----------------------------------------------------------------------------
st.title("⚡ CozCoz Partner Miner (Gen 2.0 Flash)")
st.caption("AI 전략 분석 + 팩트 체크(Raw Data) 통합 대시보드")

target_username = st.text_input("인스타그램 ID 입력 (예: cozcoz.sleep)")

if st.button("🚀 분석 시작") and target_username:
    
    with st.spinner("데이터 채굴 중..."):
        raw_data_list, error = fetch_instagram_data_apify(target_username, api_key_apify)
        
    if error:
        st.error(f"❌ 실패: {error}")
    else:
        metrics = calculate_raw_metrics(raw_data_list)
        
        with st.spinner("Gemini 2.0 Flash가 전략 수립 중..."):
            ai_res = analyze_with_gemini(metrics, api_key_gemini)
            
        if ai_res:
            st.divider()
            st.subheader("🤖 AI 전략 제안")
            
            c1, c2, c3 = st.columns(3)
            c1.metric("추천 전략", ai_res['strategy']['type'])
            c2.metric("팔로워", f"{metrics['followers']:,}명")
            c3.info(f"📞 {ai_res['basic']['contact']}")
            
            st.success(f"🎯 선정 이유: {ai_res['strategy']['reason']}")
            
            st.subheader("📨 제안서 (자동 생성)")
            st.caption("오른쪽 상단 📄 아이콘을 누르면 복사됩니다.")
            st.code(ai_res['message'], language="text") 
            
            st.divider()
            st.subheader("📉 [참고자료] 분석 전 실제 지표 (Raw Data)")
            
            with st.container(border=True):
                col_a, col_b, col_c = st.columns(3)
                col_a.metric("전체 게시물 수", f"{metrics['total_posts']:,}개")
                col_b.metric("최근 1달 게시물", f"{metrics['month_post_count']}개")
                
                gonggu_list = ai_res.get('gonggu_history', [])
                gonggu_str = ", ".join(gonggu_list) if gonggu_list else "감지된 이력 없음"
                col_c.metric("최근 공구 이력", gonggu_str)
                
                st.markdown("---")
                
                col_d, col_e = st.columns(2)
                with col_d:
                    st.markdown("**💬 댓글 반응 (최근 10개)**")
                    st.write(f"**평균: {metrics['comments_avg']}개**")
                    st.caption(f"상세: {metrics['comments_list']}")
                    
                with col_e:
                    st.markdown("**❤️ 좋아요 반응 (최근 10개)**")
                    st.write(f"**평균: {metrics['likes_avg']}개**")
                    st.caption(f"상세: {metrics['likes_list']}")
                
                st.markdown("---")
                st.markdown("**📝 바이오그래피 (원문)**")
                st.info(metrics['bio'])

        else:
            st.error("AI 분석에 실패했습니다. 키를 확인해주세요.")

