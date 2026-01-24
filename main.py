import streamlit as st
import matplotlib.pyplot as plt

st.set_page_config(page_title="비만치료제의 나비효과", layout="wide")

# 제목
st.title("🦋 비만치료제의 나비효과")
st.subheader("위고비 · 삭센다 · 마운자로 · 오젬픽이 바꾸는 연쇄적 변화")

st.markdown("""
GLP-1 계열 비만치료제는 단순한 체중 감소를 넘어  
**의학 · 산업 · 사회 구조 전반에 파급 효과를 유발**한다.  
이 앱은 그 변화를 *나비효과* 관점에서 시각화한다.
""")

# 약물 선택
drug = st.selectbox(
    "비만치료제를 선택하세요",
    ["위고비 (Wegovy)", "삭센다 (Saxenda)", "마운자로 (Mounjaro)", "오젬픽 (Ozempic)"]
)

# 약물별 기본 정보
drug_info = {
    "위고비 (Wegovy)": "주 1회 투여 GLP-1 작용제, 강력한 식욕 억제와 체중 감소 효과",
    "삭센다 (Saxenda)": "매일 투여, 비교적 초기 세대 GLP-1 비만치료제",
    "마운자로 (Mounjaro)": "GLP-1 + GIP 이중 작용, 체중 감소 효과가 가장 큼",
    "오젬픽 (Ozempic)": "당뇨 치료제로 개발되었으나 비만 치료에 파급 효과 발생"
}

st.markdown(f"### 💊 {drug}")
st.write(drug_info[drug])

# 나비효과 단계
st.markdown("## 🔄 비만치료제의 나비효과 구조")

effects = {
    "개인": [
        "식욕 감소",
        "체중 감소",
        "혈당·혈압·지질 수치 개선",
        "자기효능감 증가"
    ],
    "의료 시스템": [
        "당뇨·고혈압·심혈관 질환 유병률 감소",
        "의료비 지출 구조 변화",
        "예방의학 중심 패러다임 강화"
    ],
    "산업": [
        "식품 산업의 저당·저열량 제품 확대",
        "헬스케어·바이오 산업 투자 급증",
        "보험·제약 시장 재편"
    ],
    "사회·문화": [
        "비만에 대한 인식 변화",
        "외모 중심 문화의 재구성",
        "노동 생산성 및 결근율 변화"
    ]
}

cols = st.columns(4)
for col, (stage, items) in zip(cols, effects.items()):
    with col:
        st.markdown(f"### {stage}")
        for item in items:
            st.write(f"- {item}")

# 시각화
st.markdown("## 📊 체중 감소로 인한 연쇄 효과 개념도")

x = [0, 1, 2, 3, 4]
y = [0, 2, 4, 6, 8]

labels = [
    "체중 감소",
    "대사 개선",
    "만성질환 감소",
    "의료비 절감",
    "사회경제적 효과"
]

fig, ax = plt.subplots()
ax.plot(x, y, marker='o')

ax.set_xticks(x)
ax.set_xticklabels(labels, rotation=30)
ax.set_ylabel("파급 효과 강도 (개념적)")
ax.set_title("비만치료제의 나비효과 흐름")

st.pyplot(fig)

# 탐구용 해석
st.markdown("## 🧪 탐구 보고서용 핵심 해석")

st.markdown("""
- 비만치료제의 1차 효과는 **식욕 억제와 체중 감소**이지만  
- 2차적으로는 **대사 항상성 회복**,  
- 3차적으로는 **만성질환 구조 변화**,  
- 최종적으로는 **사회적 비용과 문화 인식의 변화**로 확장된다.

이는 *작은 생물학적 개입이 거대한 사회적 결과로 증폭되는 전형적인 나비효과 사례*로 해석할 수 있다.
""")

st.success("📘 생명과학·의학·사회 융합 탐구 주제로 바로 사용 가능!")

