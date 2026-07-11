import streamlit as st
import matplotlib.pyplot as plt
import pandas as pd

st.set_page_config(page_title="miRNA Binding Simulator", layout="wide")
st.title("🧬 miRNA-mRNA Binding Affinity Simulator")
st.markdown("**RNA의 역사(Thomas R. Cech)**를 읽고 개발한 miRNA 결합 예측 도구")

# 입력 부분
st.sidebar.header("입력 설정")
mirna_seed = st.sidebar.text_input("miRNA Seed Region (5'→3')", value="GAGGUAG", max_chars=20).upper().strip()
target_seq = st.sidebar.text_input("Target mRNA Sequence", value="CUCCAUC", max_chars=50).upper().strip()

st.sidebar.subheader("SNP 시뮬레이션")
snp_position = st.sidebar.number_input("SNP 위치 (0부터 시작)", min_value=0, value=3, step=1)
mut_base = st.sidebar.selectbox("돌연변이 염기", ["A", "U", "G", "C"], index=2)

def calculate_binding_score(target, seed):
    target = target[:len(seed)]
    score = 0.0
    matches = []
    for i, (a, b) in enumerate(zip(target, seed)):
        if a == b:
            score += 1.0
            matches.append("Perfect")
        elif (a, b) in {('A','U'), ('U','A'), ('G','C'), ('C','G')}:
            score += 1.0
            matches.append("WC")
        elif (a, b) in {('G','U'), ('U','G')}:
            score += 0.5
            matches.append("Wobble")
        else:
            score -= 0.8
            matches.append("Mismatch")
    return round(score, 2), matches

if st.button("🔬 Binding Score 계산하기", type="primary"):
    if not mirna_seed or not target_seq:
        st.error("miRNA Seed와 Target 서열을 입력해주세요.")
    else:
        wt_score, wt_matches = calculate_binding_score(target_seq, mirna_seed)
        
        # Mutant 생성
        mut_list = list(target_seq)
        if snp_position < len(mut_list):
            mut_list[snp_position] = mut_base
        mut_target = "".join(mut_list)
        mut_score, mut_matches = calculate_binding_score(mut_target, mirna_seed)
        
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Wild Type")
            st.code(f"Target: {target_seq}\nmiRNA: {mirna_seed}")
            st.metric("Binding Score", wt_score)
        
        with col2:
            st.subheader("Mutant")
            st.code(f"Target: {mut_target} (위치 {snp_position} → {mut_base})")
            st.metric("Binding Score", mut_score, delta=f"{mut_score - wt_score:.2f}")
        
        # 상세 테이블
        df = pd.DataFrame({
            "Position": range(len(mirna_seed)),
            "miRNA": list(mirna_seed),
            "WT Target": list(target_seq[:len(mirna_seed)]),
            "WT Pair": wt_matches,
            "Mut Target": list(mut_target[:len(mirna_seed)]),
            "Mut Pair": mut_matches
        })
        st.dataframe(df, use_container_width=True)
        
        # 그래프
        fig, ax = plt.subplots(figsize=(8, 5))
        ax.bar(["Wild Type", "Mutant"], [wt_score, mut_score], color=["#1f77b4", "#ff7f0e"])
        ax.set_ylabel("Binding Score")
        ax.set_title("SNP에 따른 miRNA 결합 Affinity 변화")
        st.pyplot(fig)
        
        st.success("분석 완료! RNA 서열 변화가 유전자 조절에 미치는 영향을 확인했습니다.")

st.caption("생기부 활동으로 개발한 Streamlit 웹 앱입니다. 실제 연구에서는 RNAhybrid, ViennaRNA 등의 전문 도구를 사용합니다.")
