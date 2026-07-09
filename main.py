"""
대중매체 관심도 FOMO 감쇠 곡선 비교 - Streamlit 앱

두 가지 데이터 소스를 비교:
1) 유튜브 조회수 (프록시 방법: 업로드 시점별 스냅샷)
2) 구글 트렌드 검색 관심도 (실제 일별 시계열)

실행: streamlit run app.py
"""

import streamlit as st
import pandas as pd
import requests
import altair as alt
from pytrends.request import TrendReq

st.set_page_config(page_title="대중매체 FOMO 감쇠 곡선 비교", layout="wide")

st.title("📉 대중매체 관심도 FOMO 감쇠 곡선 비교")
st.caption(
    "이슈 발생 후 대중의 관심(클릭·검색)이 시간에 따라 어떻게 줄어드는지 비교합니다. "
    "유튜브 조회수는 '업로드 시점별 스냅샷 프록시', 구글 트렌드는 '실제 일별 검색 시계열'로, "
    "서로 다른 방법론임을 유의해서 해석하세요."
)

with st.expander("📌 방법론 한계 (반드시 읽어보세요)", expanded=False):
    st.markdown(
        """
- **유튜브 조회수**: YouTube Data API는 개별 영상의 일별 조회수 변화 이력을 제공하지 않습니다
  (영상 소유자만 Studio Analytics에서 확인 가능). 따라서 이 앱은 "사건 발생 후 각기 다른 날짜에
  업로드된 영상들의 현재 누적 조회수"를 경과일수에 대해 산점도로 그리는 **프록시 방법**을 씁니다.
  전제: 뉴스 영상은 조회수가 업로드 초기에 집중된다는 가정.
- **구글 트렌드**: 실제 일별 검색 관심도(0~100 상대값) 시계열이지만, '조회수'가 아니라 '검색량'입니다.
- 두 지표는 종류가 다른 관심도 측정치이므로, 직접 비교보다는
  "관심도 감쇠라는 공통 현상을 다른 각도에서 보여주는 보조 자료"로 다루는 것이 안전합니다.
        """
    )

tab1, tab2 = st.tabs(["🎥 유튜브 조회수 (프록시)", "🔍 구글 트렌드 (시계열)"])

# ---------------- 공통 사이드바 입력 ----------------
st.sidebar.header("이슈 1 설정")
event1_name = st.sidebar.text_input("이슈 1 이름", "이란-이스라엘 전쟁")
event1_query = st.sidebar.text_input("이슈 1 검색 키워드", "이란 이스라엘 전쟁")
event1_date = st.sidebar.date_input("이슈 1 발생일", pd.to_datetime("2025-06-13"))
event1_end = st.sidebar.date_input("이슈 1 관찰 종료일", pd.to_datetime("2025-07-13"))

st.sidebar.header("이슈 2 설정")
event2_name = st.sidebar.text_input("이슈 2 이름", "월드컵 개막전")
event2_query = st.sidebar.text_input("이슈 2 검색 키워드", "월드컵 개막전")
event2_date = st.sidebar.date_input("이슈 2 발생일", pd.to_datetime("2026-06-11"))
event2_end = st.sidebar.date_input("이슈 2 관찰 종료일", pd.to_datetime("2026-07-11"))


# ==================== 탭 1: 유튜브 ====================
with tab1:
    api_key = st.text_input(
        "YouTube Data API 키",
        type="password",
        help="https://console.cloud.google.com 에서 YouTube Data API v3 활성화 후 발급",
    )
    max_results = st.slider("이슈당 최대 검색 영상 수", 10, 200, 50, step=10)
    run_youtube = st.button("유튜브 데이터 수집 및 분석 실행")

    @st.cache_data(show_spinner=False)
    def search_videos(query, published_after, published_before, api_key, max_results):
        url = "https://www.googleapis.com/youtube/v3/search"
        videos, page_token = [], None
        while len(videos) < max_results:
            params = {
                "part": "snippet",
                "q": query,
                "type": "video",
                "order": "date",
                "publishedAfter": published_after,
                "publishedBefore": published_before,
                "maxResults": min(50, max_results - len(videos)),
                "regionCode": "KR",
                "relevanceLanguage": "ko",
                "key": api_key,
            }
            if page_token:
                params["pageToken"] = page_token
            res = requests.get(url, params=params).json()
            if "error" in res:
                st.error(f"API 오류: {res['error'].get('message')}")
                break
            for item in res.get("items", []):
                videos.append({
                    "video_id": item["id"]["videoId"],
                    "title": item["snippet"]["title"],
                    "published_at": item["snippet"]["publishedAt"],
                })
            page_token = res.get("nextPageToken")
            if not page_token:
                break
        return videos

    @st.cache_data(show_spinner=False)
    def get_view_counts(video_ids, api_key):
        url = "https://www.googleapis.com/youtube/v3/videos"
        results = {}
        for i in range(0, len(video_ids), 50):
            chunk = video_ids[i:i + 50]
            params = {"part": "statistics", "id": ",".join(chunk), "key": api_key}
            res = requests.get(url, params=params).json()
            for item in res.get("items", []):
                results[item["id"]] = int(item["statistics"].get("viewCount", 0))
        return results

    def build_youtube_df(query, start, end, event_date, api_key, max_results):
        published_after = f"{start}T00:00:00Z"
        published_before = f"{end}T00:00:00Z"
        videos = search_videos(query, published_after, published_before, api_key, max_results)
        if not videos:
            return pd.DataFrame()
        view_counts = get_view_counts([v["video_id"] for v in videos], api_key)
        df = pd.DataFrame(videos)
        df["views"] = df["video_id"].map(view_counts)
        df["published_at"] = pd.to_datetime(df["published_at"]).dt.tz_localize(None)
        df["days_since_event"] = (df["published_at"] - pd.to_datetime(event_date)).dt.days
        return df.sort_values("days_since_event")

    if run_youtube:
        if not api_key:
            st.warning("YouTube API 키를 입력해주세요.")
        else:
            with st.spinner("데이터 수집 중..."):
                df1 = build_youtube_df(event1_query, event1_date, event1_end, event1_date, api_key, max_results)
                df1["issue"] = event1_name
                df2 = build_youtube_df(event2_query, event2_date, event2_end, event2_date, api_key, max_results)
                df2["issue"] = event2_name
                combined = pd.concat([df1, df2], ignore_index=True)

            if combined.empty:
                st.error("검색 결과가 없습니다. 키워드나 날짜 범위를 확인하세요.")
            else:
                chart = (
                    alt.Chart(combined)
                    .mark_circle(size=80, opacity=0.7)
                    .encode(
                        x=alt.X("days_since_event:Q", title="사건 발생 후 경과일수"),
                        y=alt.Y("views:Q", title="영상 누적 조회수", scale=alt.Scale(type="log")),
                        color=alt.Color("issue:N", title="이슈"),
                        tooltip=["title", "published_at:T", "views", "days_since_event"],
                    )
                    .properties(height=450)
                    .interactive()
                )
                st.altair_chart(chart, use_container_width=True)
                st.caption("y축은 log scale입니다. 점에 마우스를 올리면 영상 제목을 볼 수 있어요.")

                col1, col2 = st.columns(2)
                with col1:
                    st.download_button(
                        f"{event1_name} CSV 다운로드",
                        df1.to_csv(index=False).encode("utf-8-sig"),
                        f"{event1_name}_views.csv",
                    )
                with col2:
                    st.download_button(
                        f"{event2_name} CSV 다운로드",
                        df2.to_csv(index=False).encode("utf-8-sig"),
                        f"{event2_name}_views.csv",
                    )

                with st.expander("원본 데이터 보기"):
                    st.dataframe(combined)


# ==================== 탭 2: 구글 트렌드 ====================
with tab2:
    run_trends = st.button("구글 트렌드 데이터 수집 및 분석 실행")

    @st.cache_data(show_spinner=False)
    def get_trend(keyword, timeframe, geo="KR"):
        pytrends = TrendReq(hl="ko-KR", tz=540)
        pytrends.build_payload([keyword], timeframe=timeframe, geo=geo)
        df = pytrends.interest_over_time()
        if df.empty:
            return pd.DataFrame()
        out = df[[keyword]].reset_index()
        out.columns = ["date", "interest"]
        out["days_since_start"] = (out["date"] - out["date"].min()).dt.days
        return out

    if run_trends:
        with st.spinner("구글 트렌드 데이터 수집 중..."):
            tf1 = f"{event1_date} {event1_end}"
            tf2 = f"{event2_date} {event2_end}"
            t1 = get_trend(event1_query, tf1)
            t1["issue"] = event1_name
            t2 = get_trend(event2_query, tf2)
            t2["issue"] = event2_name
            trend_combined = pd.concat([t1, t2], ignore_index=True)

        if trend_combined.empty:
            st.error("트렌드 데이터가 없습니다. 키워드나 기간을 확인하세요.")
        else:
            chart = (
                alt.Chart(trend_combined)
                .mark_line(point=True)
                .encode(
                    x=alt.X("days_since_start:Q", title="사건 발생 후 경과일수"),
                    y=alt.Y("interest:Q", title="구글 트렌드 상대적 관심도 (0-100)"),
                    color=alt.Color("issue:N", title="이슈"),
                    tooltip=["date:T", "interest", "issue"],
                )
                .properties(height=450)
                .interactive()
            )
            st.altair_chart(chart, use_container_width=True)

            st.download_button(
                "구글 트렌드 데이터 CSV 다운로드",
                trend_combined.to_csv(index=False).encode("utf-8-sig"),
                "trends_comparison.csv",
            )

            with st.expander("원본 데이터 보기"):
                st.dataframe(trend_combined)
