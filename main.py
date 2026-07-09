"""
매체 반응 FOMO 현상 5년 비교 분석 - Streamlit 앱

핵심 비교: 감정자극 뉴스 2건 vs 팩트형(전쟁·경제) 뉴스 2건
데이터: 네이버 검색어트렌드(DataLab) API (핵심) + KOSIS 국가데이터처 (보조 맥락)

실행: streamlit run app_media_fomo_5y.py

[사전 준비 - 네이버 API]
1. https://developers.naver.com/apps/#/register 접속
2. 애플리케이션 등록 -> 사용 API에서 "검색어트렌드" 선택
3. 발급받은 Client ID / Client Secret을 앱 사이드바에 입력

[사전 준비 - KOSIS API (선택)]
1. https://kosis.kr/openapi/ 에서 활용신청 -> API 키 발급
2. 원하는 통계표의 table ID(통계표 ID)를 KOSIS 홈페이지에서 조회해서 입력
"""

import streamlit as st
import pandas as pd
import requests
import json
import altair as alt

st.set_page_config(page_title="매체 FOMO 5년 비교 분석", layout="wide")

st.title("📰 매체 반응 FOMO 현상 — 5년 비교 분석")
st.caption(
    "감정을 자극하는 뉴스 2건과 전쟁·경제 등 팩트형 뉴스 2건에 대한 대중 관심도가 "
    "시간에 따라 어떻게 급등했다가 줄어드는지(FOMO 감쇠 곡선) 비교합니다."
)

with st.expander("📌 데이터 소스 및 방법론 한계 (반드시 읽어보세요)", expanded=False):
    st.markdown(
        """
- **네이버 검색어트렌드**: 특정 기간 내에서 키워드의 검색량 흐름을 **최댓값을 100으로 둔 상대값**으로 제공합니다.
  절대적인 검색 횟수나 조회수·시청자수가 아니라 '상대적 관심도 추이'입니다.
- **국가데이터처(구 통계청, 2025.10.1 개편) / KOSIS**: 뉴스 반응 자체를 측정하는 통계는 존재하지 않습니다.
  이 앱에서는 KOSIS를 "사회적 배경 맥락 지표"(예: 소비자심리지수 등)로만 보조적으로 사용합니다.
  즉 KOSIS 데이터가 뉴스 관심도와 직접 비교되는 것이 아니라는 점을 보고서에 명시해야 합니다.
- 4개 케이스를 "감정자극형"과 "팩트형"으로 그룹핑해 평균 감쇠 곡선을 비교하지만,
  각 그룹이 2건씩뿐이라 표본이 매우 작습니다 — 통계적 일반화가 아니라
  **사례 비교(case comparison) 수준의 탐색적 분석**임을 밝히는 것이 정직합니다.
        """
    )

# ==================== 사이드바: 네이버 API 인증 ====================
st.sidebar.header("🔑 네이버 API 인증")
client_id = st.sidebar.text_input("Naver Client ID")
client_secret = st.sidebar.text_input("Naver Client Secret", type="password")

st.sidebar.divider()
st.sidebar.header("📅 분석 기간 (5년 전체 흐름용)")
overview_start = st.sidebar.date_input("시작일", pd.to_datetime("2021-07-01"))
overview_end = st.sidebar.date_input("종료일", pd.to_datetime("2026-07-09"))

# ==================== 케이스 입력 ====================
st.header("1️⃣ 비교할 뉴스 케이스 4건 설정")

default_cases = [
    {"label": "감정자극 뉴스 1", "category": "감정자극", "name": "이태원 참사", "keywords": "이태원 참사", "event_date": "2022-10-29"},
    {"label": "감정자극 뉴스 2", "category": "감정자극", "name": "학교폭력 사건", "keywords": "학교폭력", "event_date": "2023-02-27"},
    {"label": "팩트형 뉴스 1", "category": "팩트형", "name": "이란-이스라엘 전쟁", "keywords": "이란 이스라엘 전쟁", "event_date": "2025-06-13"},
    {"label": "팩트형 뉴스 2", "category": "팩트형", "name": "기준금리 인상", "keywords": "기준금리 인상", "event_date": "2022-10-12"},
]

cases = []
cols = st.columns(4)
for i, col in enumerate(cols):
    with col:
        st.subheader(default_cases[i]["label"])
        category = st.selectbox(
            "분류", ["감정자극", "팩트형"],
            index=0 if default_cases[i]["category"] == "감정자극" else 1,
            key=f"cat_{i}",
        )
        name = st.text_input("케이스 이름", default_cases[i]["name"], key=f"name_{i}")
        keyword = st.text_input("검색 키워드", default_cases[i]["keywords"], key=f"kw_{i}")
        event_date = st.date_input(
            "이슈 발생일", pd.to_datetime(default_cases[i]["event_date"]), key=f"date_{i}"
        )
        cases.append({
            "label": default_cases[i]["label"],
            "category": category,
            "name": name,
            "keyword": keyword,
            "event_date": pd.to_datetime(event_date),
        })

st.divider()


# ==================== 네이버 API 호출 함수 ====================
@st.cache_data(show_spinner=False)
def get_naver_trend(client_id, client_secret, keyword_groups, start_date, end_date, time_unit="week"):
    url = "https://openapi.naver.com/v1/datalab/search"
    headers = {
        "X-Naver-Client-Id": client_id,
        "X-Naver-Client-Secret": client_secret,
        "Content-Type": "application/json",
    }
    body = {
        "startDate": start_date,
        "endDate": end_date,
        "timeUnit": time_unit,
        "keywordGroups": keyword_groups,
    }
    res = requests.post(url, headers=headers, data=json.dumps(body))
    if res.status_code != 200:
        return None, f"네이버 API 오류 {res.status_code}: {res.text}"
    return res.json(), None


def naver_result_to_df(result):
    """네이버 API 응답을 tidy dataframe으로 변환"""
    rows = []
    for group in result.get("results", []):
        gname = group["title"]
        for point in group["data"]:
            rows.append({"group": gname, "date": point["period"], "ratio": point["ratio"]})
    df = pd.DataFrame(rows)
    if not df.empty:
        df["date"] = pd.to_datetime(df["date"])
    return df


tab1, tab2, tab3 = st.tabs(["📈 5년 전체 흐름", "📉 이슈 발생일 기준 감쇠 곡선 비교", "📊 KOSIS 보조 지표 (선택)"])

# ==================== 탭 1: 5년 전체 흐름 ====================
with tab1:
    st.subheader("5년간 달력 시간 기준 검색 관심도 흐름")
    run_overview = st.button("5년 전체 흐름 분석 실행", key="btn_overview")

    if run_overview:
        if not client_id or not client_secret:
            st.warning("사이드바에 네이버 API Client ID / Secret을 입력해주세요.")
        else:
            keyword_groups = [{"groupName": c["name"], "keywords": [c["keyword"]]} for c in cases]
            result, err = get_naver_trend(
                client_id, client_secret, keyword_groups,
                str(overview_start), str(overview_end), time_unit="week",
            )
            if err:
                st.error(err)
            else:
                df = naver_result_to_df(result)
                cat_map = {c["name"]: c["category"] for c in cases}
                df["category"] = df["group"].map(cat_map)

                chart = (
                    alt.Chart(df)
                    .mark_line()
                    .encode(
                        x=alt.X("date:T", title="날짜"),
                        y=alt.Y("ratio:Q", title="네이버 검색 상대 관심도 (0-100)"),
                        color=alt.Color("group:N", title="케이스"),
                        strokeDash=alt.StrokeDash("category:N", title="분류"),
                        tooltip=["group", "date:T", "ratio", "category"],
                    )
                    .properties(height=450)
                    .interactive()
                )
                st.altair_chart(chart, use_container_width=True)
                st.download_button(
                    "5년 전체 데이터 CSV 다운로드",
                    df.to_csv(index=False).encode("utf-8-sig"),
                    "naver_5year_overview.csv",
                )
                with st.expander("원본 데이터"):
                    st.dataframe(df)


# ==================== 탭 2: 이슈 발생일 기준 감쇠 곡선 정렬 비교 ====================
with tab2:
    st.subheader("이슈 발생일을 0으로 맞춰 정렬한 감쇠 곡선 비교")
    st.caption("각 케이스의 '이슈 발생일'을 기준으로 -2주 ~ +26주 구간을 잘라서, 경과 주(week) 기준으로 나란히 비교합니다.")

    weeks_before = st.slider("발생일 이전 관찰 기간(주)", 0, 8, 2)
    weeks_after = st.slider("발생일 이후 관찰 기간(주)", 4, 52, 26)
    run_decay = st.button("감쇠 곡선 비교 분석 실행", key="btn_decay")

    if run_decay:
        if not client_id or not client_secret:
            st.warning("사이드바에 네이버 API Client ID / Secret을 입력해주세요.")
        else:
            all_dfs = []
            for c in cases:
                start = (c["event_date"] - pd.Timedelta(weeks=weeks_before)).strftime("%Y-%m-%d")
                end = (c["event_date"] + pd.Timedelta(weeks=weeks_after)).strftime("%Y-%m-%d")
                result, err = get_naver_trend(
                    client_id, client_secret,
                    [{"groupName": c["name"], "keywords": [c["keyword"]]}],
                    start, end, time_unit="week",
                )
                if err:
                    st.error(f"{c['name']}: {err}")
                    continue
                df = naver_result_to_df(result)
                if df.empty:
                    st.warning(f"{c['name']}: 데이터 없음")
                    continue
                df["category"] = c["category"]
                df["weeks_since_event"] = ((df["date"] - c["event_date"]).dt.days / 7).round().astype(int)
                all_dfs.append(df)

            if all_dfs:
                combined = pd.concat(all_dfs, ignore_index=True)

                # 개별 케이스 라인
                individual_chart = (
                    alt.Chart(combined)
                    .mark_line(point=True)
                    .encode(
                        x=alt.X("weeks_since_event:Q", title="이슈 발생 후 경과 주(week)"),
                        y=alt.Y("ratio:Q", title="검색 상대 관심도 (0-100)"),
                        color=alt.Color("group:N", title="케이스"),
                        strokeDash=alt.StrokeDash("category:N", title="분류"),
                        tooltip=["group", "weeks_since_event", "ratio", "category"],
                    )
                    .properties(height=400, title="케이스별 감쇠 곡선")
                    .interactive()
                )
                st.altair_chart(individual_chart, use_container_width=True)

                # 카테고리 평균 곡선 (감정자극 평균 vs 팩트형 평균)
                cat_avg = (
                    combined.groupby(["category", "weeks_since_event"])["ratio"]
                    .mean()
                    .reset_index()
                )
                cat_chart = (
                    alt.Chart(cat_avg)
                    .mark_line(size=3)
                    .encode(
                        x=alt.X("weeks_since_event:Q", title="이슈 발생 후 경과 주(week)"),
                        y=alt.Y("ratio:Q", title="평균 검색 상대 관심도"),
                        color=alt.Color("category:N", title="분류"),
                        tooltip=["category", "weeks_since_event", "ratio"],
                    )
                    .properties(height=350, title="분류별 평균 감쇠 곡선 (감정자극 vs 팩트형)")
                    .interactive()
                )
                st.altair_chart(cat_chart, use_container_width=True)

                # 감쇠 속도 요약 지표: 피크 대비 몇 주 만에 절반 이하로 떨어지는지
                st.subheader("감쇠 속도 요약")
                summary_rows = []
                for name, g in combined.groupby("group"):
                    g = g.sort_values("weeks_since_event")
                    peak_row = g.loc[g["ratio"].idxmax()]
                    peak_val = peak_row["ratio"]
                    after_peak = g[g["weeks_since_event"] > peak_row["weeks_since_event"]]
                    half_life = after_peak[after_peak["ratio"] <= peak_val / 2]
                    weeks_to_half = (
                        half_life["weeks_since_event"].iloc[0] - peak_row["weeks_since_event"]
                        if not half_life.empty else None
                    )
                    summary_rows.append({
                        "케이스": name,
                        "분류": g["category"].iloc[0],
                        "피크 관심도": peak_val,
                        "피크까지 경과주": peak_row["weeks_since_event"],
                        "피크 후 반토막까지 걸린 주": weeks_to_half,
                    })
                st.dataframe(pd.DataFrame(summary_rows))

                st.download_button(
                    "감쇠 곡선 데이터 CSV 다운로드",
                    combined.to_csv(index=False).encode("utf-8-sig"),
                    "naver_decay_curves.csv",
                )


# ==================== 탭 3: KOSIS 보조 지표 ====================
with tab3:
    st.subheader("KOSIS(국가데이터처) 보조 맥락 지표")
    st.caption(
        "뉴스 관심도를 직접 측정하는 통계는 아니며, 사회적 배경을 참고하기 위한 보조 자료입니다. "
        "예: 소비자심리지수, 사회조사 지표 등. 통계표 ID는 KOSIS 홈페이지(kosis.kr)에서 직접 확인해야 합니다."
    )

    kosis_key = st.text_input("KOSIS Open API 인증키", type="password")
    org_id = st.text_input("기관코드(orgId)", placeholder="예: 101 (국가데이터처)")
    tbl_id = st.text_input("통계표 ID(tblId)", placeholder="KOSIS 홈페이지에서 조회")
    item_start = st.text_input("조회 시작 시점 (예: 202101)")
    item_end = st.text_input("조회 종료 시점 (예: 202606)")

    run_kosis = st.button("KOSIS 데이터 조회")

    if run_kosis:
        if not (kosis_key and org_id and tbl_id):
            st.warning("KOSIS 인증키, 기관코드, 통계표 ID를 모두 입력해주세요.")
        else:
            url = "https://kosis.kr/openapi/Param/statisticsParameterData.do"
            params = {
                "method": "getList",
                "apiKey": kosis_key,
                "itmId": "ALL",
                "objL1": "ALL",
                "format": "json",
                "jsonVD": "Y",
                "prdSe": "M",
                "startPrdDe": item_start,
                "endPrdDe": item_end,
                "orgId": org_id,
                "tblId": tbl_id,
            }
            res = requests.get(url, params=params)
            try:
                data = res.json()
                df = pd.DataFrame(data)
                st.dataframe(df)
                st.download_button(
                    "KOSIS 데이터 CSV 다운로드",
                    df.to_csv(index=False).encode("utf-8-sig"),
                    "kosis_context_data.csv",
                )
            except Exception as e:
                st.error(f"데이터 파싱 실패: {e}\n응답 원문: {res.text[:500]}")
