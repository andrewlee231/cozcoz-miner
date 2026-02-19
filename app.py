import streamlit as st
import google.generativeai as genai
from apify_client import ApifyClient
import json
from datetime import datetime, timedelta
import statistics

# -----------------------------------------------------------------------------
# 1. 페이지 설정 & 안전한 UI 패치
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="CozCoz Partner Miner (Master)",
    page_icon="💎",
    layout="wide"
)

# 🚨 메인 화면을 날린 위험한 코드를 제거하고 안전한 필수 기능만 남겼습니다.
st.markdown("""
<style>
    /* 메트릭(지표 숫자) 사이즈 압축하여 한눈에 들어오게 조절 */
    [data-testid="stMetricValue"] {
        font-size: 1.5rem !important;
    }
    
    /* 💡 [핵심] 제안서 코드 박스 세로 스크롤 없애고 전체 펼치기 */
    .stCodeBlock pre {
        max-height: none !important; 
        white-space: pre-wrap !important; 
        word-break: break-word !important;
    }
    
    /* 💡 [핵심] 복사(Copy) 버튼 상시 노출 및 강조 */
    .stCodeBlock button {
        opacity: 1 !important; 
        transform: scale(1.2); 
        right: 15px !important;
        top: 15px !important;
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
        st.session_state.md_filename = uploaded_file.name
        st.success(f"✅ 파일 업데이트 완료!")
        
    if st.session_state.md_content:
        st.info(f"📁 현재 적용 중: {st.session_state.md_filename}")
    else:
        st.warning("⚠️ 분석 전 MD 파일을 업로드해주세요.")

# -----------------------------------------------------------------------------
# 4. 데이터 수집 & 가공 함수
# -----------------------------------------------------------------------------
def fetch_instagram_data_apify(username, apify_key):
    if not apify_key: return None, "Apify 키가 없습니다."
    
    ACTOR_ID = "apify/instagram-profile-scraper"
    client = ApifyClient(apify_key)
    run_input = {"usernames": [username]}
    
    try:
        st.toast(f"🚁 드론 로봇이 '{username}' 프로필 스캔 중...", icon="🚁")
        run = client.actor(ACTOR_ID).call(run_input=run_input)
        dataset_items = list(client.dataset(run["defaultDatasetId"]).iterate_items())
        
        if not dataset_items: return None, "데이터 없음 (비공개 계정 또는 차단)"
        return dataset_items[0], None 
    except Exception as e:
        return None, f"Apify 에러: {str(e)}"

def calculate_raw_metrics(data):
    profile = data
    posts = data.get('latestPosts', []) 
    
    one_month_ago = datetime.utcnow() - timedelta(days=30)
    recent_posts = []
    reels_views = []
    
    for p in posts:
        ts_str = p.get('timestamp')
        if ts_str:
            try:
                if '.' in ts_str:
                    ts = datetime.strptime(ts_str.replace('Z', ''), "%Y-%m-%dT%H:%M:%S.%f")
                else:
                    ts = datetime.strptime(ts_str.replace('Z', ''), "%Y-%m-%dT%H:%M:%S")
                
                if ts > one_month_ago:
                    recent_posts.append(p)
                    if p.get('type') == 'Video' and p.get('videoViewCount'):
                        reels_views.append(p.get('videoViewCount'))
            except: pass

    if len(recent_posts) < 5:
        recent_posts = posts[:10]

    likes_list = [p.get('likesCount', 0) for p in recent_posts]
    comments_list = [p.get('commentsCount', 0) for p in recent_posts]
    
    avg_likes = round(statistics.mean(likes_list)) if likes_list else 0
    avg_comments = round(statistics.mean(comments_list)) if comments_list else 0
    avg_reels = round(statistics.mean(reels_views)) if reels_views else 0

    return {
        "username": profile.get('username', profile.get('ownerUsername', '')),
        "followers": profile.get('followersCount', 0),
        "bio": profile.get('biography', ''),
        "external_url": profile.get('externalUrl', ''),
        "month_post_count": len(recent_posts),
        "avg_likes": avg_likes,
        "avg_comments": avg_comments,
        "avg_reels_views": avg_reels,
        "recent_posts_data": recent_posts[:15]
    }

def analyze_with_gemini(raw_metrics, gemini_key, md_context):
    if not gemini_key: return None
    genai.configure(api_key=gemini_key)
    model = genai.GenerativeModel("gemini-2.0-flash", generation_config={"response_mime_type": "application/json"})
    
    posts_text = []
    for p in raw_metrics['recent_posts_data']:
        posts_text.append({
            "type": p.get("type", "Image"),
            "caption": p.get("caption", "")[:400],
            "likes": p.get("likesCount", 0),
            "comments": p.get("commentsCount", 0)
        })

    prompt = f"""
    당신은 실력 있는 E-commerce 파트장입니다. 아래 데이터를 분석해 JSON으로 반환하세요.
    
    [상품 및 제안 기준 MD 파일 내용]
    {md_context}
    
    [인플루언서 스펙]
    - Bio 원문: {raw_metrics['bio']}
    - Link: {raw_metrics['external_url']}
    - Followers: {raw_metrics['followers']}
    [최근 게시물 내용] {json.dumps(posts_text, ensure_ascii=False)}
    
    [분석 요청사항]
    1. 컨택 포인트: Bio와 Link를 스캔하여 '오픈카톡' 또는 '개인이메일' 추출. (기본 linktr.ee 자체 주소나 의미 없는 버튼은 무시). 
       - 찾으면: "[카카오톡/이메일] 해당 주소" 
       - 못 찾으면: "컨택 포인트 없음 (추정 링크: ...)"
    2. 공구 진정성: 캡션을 보고 월 공구 횟수, 빌드업 지수(예고-오픈 흐름 여부), 최근 한 달 판매 목록(경쟁사 제품이면 Bad 표기) 추출.
    3. 찐팬 지표 & 구매 시그널: 캡션의 소통 방식과 평균 좋아요/댓글을 바탕으로 찐팬 비율 추정 및 CS 친절도/소통력 유추.
    4. AI 추천 전략 & 제안서: MD 파일 내용을 기반으로 해당 계정에 맞는 맞춤형 제안서 작성. 복사해서 바로 붙여넣기 좋도록 가독성 있게 작성.
    
    [출력형식]
    {{
        "contact": "...",
        "authenticity": {{
            "gonggu_count": "...",
            "buildup_index": "...",
            "recent_sales_list": "..."
        }},
        "power": {{
            "true_fans": "...",
            "cs_signal": "..."
        }},
        "strategy": "...",
        "message": "..."
    }}
    """
    try:
        st.toast("🧠 AI가 MD 문서를 기반으로 분석 중...", icon="⚡")
        res = model.generate_content(prompt)
        return json.loads(res.text)
    except Exception as e:
        st.error(f"AI 분석 오류: {str(e)}")
        return None

# -----------------------------------------------------------------------------
# 5. 메인 화면 UI (복구 완료)
# -----------------------------------------------------------------------------
st.title("💎 CozCoz Partner Miner")

target_username = st.text_input("🔍 인스타그램 ID 입력 (예: cozcoz.sleep)")

if st.button("🚀 심층 분석 시작") and target_username:
    if not st.session_state.md_content:
        st.error("⚠️ 왼쪽 사이드바에서 제안서 기준(MD) 파일을 먼저 업로드해주세요!")
    else:
        with st.spinner("로봇 채굴 중..."):
            raw_data, error = fetch_instagram_data_apify(target_username, api_key_apify)
            
        if error:
            st.error(f"❌ 실패: {error}")
        else:
            metrics = calculate_raw_metrics(raw_data)
            
            with st.spinner("AI가 분석 대시보드를 생성 중입니다..."):
                ai_res = analyze_with_gemini(metrics, api_key_gemini, st.session_state.md_content)
                
            if ai_res:
                
                # ==========================================
                # 1. 기초 체력 (Basic Health)
                # ==========================================
                st.markdown("#### 📊 1. 기초 체력 (Basic Health) - 최근 30일")
                
                with st.container(border=True):
                    st.info(f"**📝 프로필 소개 (Bio):**\n{metrics['bio']}")
                    st.success(f"**📞 [핵심] 컨택 포인트:** {ai_res['contact']}")
                    
                    st.markdown("---")
                    
                    col1, col2, col3, col4, col5 = st.columns(5)
                    col1.metric("팔로워", f"{metrics['followers']:,}명")
                    col2.metric("게시물 수", f"{metrics['month_post_count']}개")
                    col3.metric("🎬 릴스 평균조회", f"{metrics['avg_reels_views']:,}회") 
                    col4.metric("평균 좋아요", f"{metrics['avg_likes']:,}개")
                    col5.metric("평균 댓글", f"{metrics['avg_comments']:,}개")

                # ==========================================
                # 2. 공구 진정성 검증 (Authenticity Check)
                # ==========================================
                st.markdown("#### 🚨 2. 공구 진정성 검증 (Authenticity Check)")
                
                with st.container(border=True):
                    auth = ai_res['authenticity']
                    c_auth1, c_auth2 = st.columns(2)
                    c_auth1.metric("🛒 월 공구 횟수", auth['gonggu_count'])
                    c_auth2.metric("📈 빌드업 지수", auth['buildup_index'])
                    
                    st.markdown("**📋 최근 판매 목록 (최근 한 달)**")
                    st.write(f"> {auth['recent_sales_list']}")

                # ==========================================
                # 3. 구매력 및 팬덤 화력 (Buying Power)
                # ==========================================
                st.markdown("#### 🔥 3. 구매력 및 팬덤 화력 (Buying Power)")
                
                with st.container(border=True):
                    pwr = ai_res['power']
                    st.write(f"**💎 찐팬 지표:** {pwr['true_fans']}")
                    st.write(f"**🗣️ 구매 시그널 & CS 응대력:** {pwr['cs_signal']}")

                # ==========================================
                # 4. [최종] AI 추천 전략 & 자동 제안서
                # ==========================================
                st.markdown("#### 🎯 4. AI 추천 전략 & 맞춤 제안서")
                
                st.info(f"**💡 AI 추천 전략:** {ai_res['strategy']}")
                
                st.markdown("**📨 자동 제안서 (아래 내용 전체가 한눈에 펼쳐집니다)**")
                # wrap_lines=True 가로 스크롤 방지
                st.code(ai_res['message'], language="text", wrap_lines=True)
