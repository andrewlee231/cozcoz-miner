import streamlit as st
import google.generativeai as genai
from apify_client import ApifyClient
import pandas as pd
import json

# -----------------------------------------------------------------------------
# 1. 페이지 설정
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="코즈코즈 파트너 마이너 (Pro)",
    page_icon="💎",
    layout="wide"
)

# -----------------------------------------------------------------------------
# 2. 기초 데이터 (Knowledge Base)
# -----------------------------------------------------------------------------
PRODUCT_KNOWLEDGE_BASE = """
# [기초 데이터] 코즈코즈_두부토퍼_제안정보.md
## 1. 상품 기본 정보
- **상품명:** 코즈코즈 두부토퍼 (빨아쓰는 기능성 토퍼)
- **핵심전략:** Meta 파트너십 광고 지원 (매출 발생 시 광고비 분담)
## 2. [제안 멘트 전략] AI 자동 생성 가이드
### 전략 A: [Growth Hacking] - 정체기 탈출형
- **Hook:** "꽉 막힌 도달, 본사 AI 기술로 뚫어드립니다."
### 전략 B: [Revenue Scaling] - 비즈니스형
- **Hook:** "오가닉의 한계, 'Meta 파트너십 광고'로 매출 3배 확장."
### 전략 C: [Branding] - 이미지/감성형
- **Hook:** "브랜드의 '메인 엠버서더' 제안."
"""

# -----------------------------------------------------------------------------
# 3. 사이드바 (설정)
# -----------------------------------------------------------------------------
with st.sidebar:
    st.header("⚙️ 시스템 설정")
    api_key_gemini = st.text_input("Gemini API Key", type="password")
    api_key_apify = st.text_input("Apify API Key", type="password")
    
# -----------------------------------------------------------------------------
# 4. 핵심 로직 함수 (로봇 교체 완료!)
# -----------------------------------------------------------------------------
def fetch_instagram_data(username, apify_key):
    if not apify_key: return None, "Apify 키가 없습니다."
    
    # 🚨 중요: 로봇을 'Instagram API Scraper'로 교체했습니다.
    # 이 로봇은 공개 데이터를 더 잘 뚫습니다.
    ACTOR_ID = "shu8hvrXbJbY3Eb9W" 
    
    client = ApifyClient(apify_key)
    
    # 입력값 형식도 새 로봇에 맞게 변경
    run_input = {
        "usernames": [username],
        "limit": 15,  # 최근 15개
        "proxy": {
            "useApifyProxy": True
        }
    }
    
    try:
        # Actor 실행
        run = client.actor(ACTOR_ID).call(run_input=run_input)
        
        # 데이터 가져오기
        dataset_items = list(client.dataset(run["defaultDatasetId"]).iterate_items())
        
        if not dataset_items:
            return None, "데이터를 찾지 못했습니다. (비공개 계정이거나 ID 오타)"
            
        return dataset_items, None
    except Exception as e:
        return None, f"수집 실패: {str(e)}"

def analyze_with_gemini(data, gemini_key):
    if not gemini_key: return None
    genai.configure(api_key=gemini_key)
    model = genai.GenerativeModel("gemini-1.5-pro-latest", generation_config={"response_mime_type": "application/json"})
    
    # 데이터 양이 너무 많으면 에러나므로 텍스트만 추려서 전달
    simple_data = []
    for item in data[:10]: # 최근 10개만 분석
        simple_data.append({
            "caption": item.get("caption", ""),
            "likesCount": item.get("likesCount", 0),
            "commentsCount": item.get("commentsCount", 0),
            "timestamp": item.get("timestamp", ""),
            "type": item.get("type", "Image")
        })
        
    prompt = f"""
    당신은 마케팅 전략가입니다. 아래 데이터를 분석해 JSON으로 답하세요.
    [상품정보] {PRODUCT_KNOWLEDGE_BASE}
    [인플루언서 데이터] {json.dumps(simple_data, ensure_ascii=False)}
    
    [요구사항]
    1. 기초체력: 활동성, 릴스조회수, 컨택포인트(추정)
    2. 진정성: 공구횟수, 빌드업지수
    3. 구매력: 찐팬비율, 구매시그널
    4. 전략선택: A/B/C 중 택1
    5. 제안서: Hook을 포함한 DM 초안 작성
    
    [출력형식]
    {{
        "basic": {{ "activity": "...", "reels_view": "...", "contact": "..." }},
        "auth": {{ "count": 0, "buildup": 0.0, "category": "..." }},
        "power": {{ "signals": 0 }},
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
st.title("💎 CozCoz Partner Miner (v2.0)")
st.caption("강력해진 API 스크래퍼 탑재")

target_username = st.text_input("인스타그램 ID 입력 (@제외)")
analyze_btn = st.button("🚀 분석 시작")

if analyze_btn and target_username:
    with st.status("🕵️‍♀️ 강력한 로봇이 인스타그램에 잠입 중입니다...", expanded=True) as status:
        
        # 1. 수집
        st.write("1. 데이터 수집 중... (약 30초 소요)")
        raw_data, error = fetch_instagram_data(target_username, api_key_apify)
        
        if error:
            st.error(f"❌ 실패: {error}")
            status.update(label="분석 실패", state="error")
        else:
            st.write("2. Gemini AI가 전략 수립 중...")
            
            # 2. 분석
            res = analyze_with_gemini(raw_data, api_key_gemini)
            
            if res:
                status.update(label="✅ 분석 완료!", state="complete")
                
                st.divider()
                st.header("📊 분석 리포트")
                
                c1, c2, c3 = st.columns(3)
                c1.metric("활동성", res['basic']['activity'])
                c2.metric("릴스 조회수", res['basic']['reels_view'])
                c3.info(f"📞 {res['basic']['contact']}")
                
                c4, c5 = st.columns(2)
                c4.metric("월 공구 횟수", f"{res['auth']['count']}회")
                c5.metric("구매 시그널", f"{res['power']['signals']}건")
                
                st.success(f"🎯 추천 전략: {res['strategy']['type']}")
                st.info(res['strategy']['reason'])
                
                st.subheader("📋 제안서 초안")
                st.text_area("복사용", res['message'], height=250)
            else:
                st.error("AI 분석 중 오류가 발생했습니다.")
                status.update(label="AI 오류", state="error")
