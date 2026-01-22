import streamlit as st
import pandas as pd
import random
import time

# 1. 페이지 설정 (아이콘과 제목)
st.set_page_config(page_title="응급실 대기 현황", page_icon="🚑", layout="wide")

# 2. 화려한 UI를 위한 커스텀 CSS
st.markdown("""
    <style>
    .main {
        background-color: #f0f2f6;
    }
    .stButton>button {
        width: 100%;
        border-radius: 20px;
        height: 3em;
        background-color: #ff4b4b;
        color: white;
        font-weight: bold;
    }
    .status-card {
        padding: 20px;
        border-radius: 15px;
        background-color: white;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        margin-bottom: 10px;
        border-left: 5px solid #ff4b4b;
    }
    </style>
    """, unsafe_allow_html=True)

# 3. 가상 데이터 생성 (실제 API 연결 대신)
def get_mock_data(region):
    hospitals = [f"{region} {name}병원" for name in ["중앙", "성심", "대형", "메디컬", "긴급"]]
    data = []
    for h in hospitals:
        wait_time = random.randint(5, 120)
        beds = random.randint(0, 30)
        status = "🟢 원활" if wait_time < 30 else "🟡 지연" if wait_time < 60 else "🔴 혼잡"
        data.append({
            "병원명": h,
            "대기시간(분)": wait_time,
            "가용병상": beds,
            "상태": status,
            "위치": region
        })
    return pd.DataFrame(data)

# --- 사이드바: 지역 선택 ---
st.sidebar.title("🗺️ 지역 필터")
region_list = ["서울", "부산", "대구", "인천", "광주", "대전", "울산", "경기", "강원"]
selected_region = st.sidebar.selectbox("찾으시는 지역을 선택하세요 👇", region_list)

st.sidebar.markdown("---")
st.sidebar.write("🏥 **오늘의 응급 의료 팁**")
st.sidebar.info("심정지 환자 발생 시 즉시 119에 신고하고 심폐소생술을 실시하세요! 💓")

# --- 메인 화면 ---
st.title(f"🚨 {selected_region} 지역 응급실 실시간 현황")
st.markdown(f"**현재 시각:** {time.strftime('%Y-%m-%d %H:%M:%S')} ⏰")

# 데이터 불러오기 애니메이션
with st.spinner('실시간 정보를 가져오는 중... 📡'):
    df = get_mock_data(selected_region)
    time.sleep(0.5)

# 상단 대시보드 (메트릭)
col1, col2, col3 = st.columns(3)
col1.metric("🏥 검색된 병원", f"{len(df)}곳")
col2.metric("⏱️ 평균 대기", f"{int(df['대기시간(분)'].mean())}분")
col3.metric("🚑 즉시 진료 가능", f"{len(df[df['상태'] == '🟢 원활'])}곳")

st.markdown("---")

# 병원 리스트 출력
st.subheader("📍 가장 가까운 응급실 리스트")

for index, row in df.sort_values(by="대기시간(분)").iterrows():
    with st.container():
        # HTML을 이용한 커스텀 카드 UI
        st.markdown(f"""
            <div class="status-card">
                <h3 style='margin:0;'>{row['병원명']} {row['상태']}</h3>
                <p style='margin:5px 0;'>⏳ 예상 대기 시간: <b>{row['대기시간(분)']}분</b> | 🛏️ 남은 병상: {row['가용병상']}개</p>
            </div>
            """, unsafe_allow_html=True)
        
        # 상세 보기 버튼 (Streamlit 기본 버튼 활용)
        if st.button(f"📞 {row['병원명']} 전화 연결 및 길찾기", key=index):
            st.success(f"{row['병원명']}으로 전화를 연결합니다... (실제 앱에서는 119 연동 가능)")

# 하단 지도 표시 (가상 위치)
st.markdown("---")
st.subheader("🗺️ 내 주변 응급실 지도")
# 임의의 좌표 생성 (선택 지역 근처)
map_data = pd.DataFrame({
    'lat': [37.5665 + random.uniform(-0.05, 0.05) for _ in range(5)],
    'lon': [126.9780 + random.uniform(-0.05, 0.05) for _ in range(5)]
})
st.map(map_data)

# 푸터
st.markdown("---")
st.markdown("<p style='text-align: center;'>🩺 <b>건강한 하루 되세요! 본 정보는 시뮬레이션 데이터입니다.</b> 🩺</p>", unsafe_allow_html=True)
