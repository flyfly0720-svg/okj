"""
유튜브 조회수 기반 이슈 관심도 변화 분석
- 이란-이스라엘 전쟁 뉴스 vs 월드컵 개막전 비교

[방법론 주의사항 - 반드시 읽을 것]
YouTube Data API v3는 개별 영상의 '일별 누적 조회수 변화 이력'을 제공하지 않는다.
(이는 영상 소유자만 YouTube Studio Analytics에서 볼 수 있는 데이터임)

따라서 이 스크립트는 대안적 프록시(proxy) 방법을 사용한다:

  같은 이슈를 다룬 여러 영상이 '사건 발생 후 각기 다른 날짜에 업로드'되었다고 보고,
    x축 = (영상 게시일 - 사건 발생일) = 경과일수
    y축 = 각 영상의 '현재까지 누적 조회수'
  로 산점도를 그린다.

  전제 가정: 뉴스 영상은 대부분의 조회수가 업로드 직후 며칠 내에 집중적으로 발생한다
  (뉴스 콘텐츠 특성상 롱테일보다 초기 집중 조회 비중이 큼).
  이 가정이 성립한다면 "사건 발생 후 늦게 올라온 영상일수록 조회수가 낮다"는
  패턴이 FOMO 감쇠 곡선의 근사치가 될 수 있다.

  단, 이는 참된 시계열이 아니라 '업로드 시점별 스냅샷 비교'이므로
  보고서/세특 서술 시 이 한계를 반드시 명시할 것.

[사전 준비]
1. https://console.cloud.google.com 접속 → 새 프로젝트 생성
2. "YouTube Data API v3" 활성화
3. 사용자 인증 정보 → API 키 발급 (무료, 일일 할당량 있음)
4. 아래 API_KEY 변수에 붙여넣기
"""

import requests
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import platform

# ---- 한글 폰트 설정 (OS별 분기) ----
if platform.system() == "Windows":
    plt.rcParams["font.family"] = "Malgun Gothic"
elif platform.system() == "Darwin":
    plt.rcParams["font.family"] = "AppleGothic"
else:
    plt.rcParams["font.family"] = "NanumGothic"
plt.rcParams["axes.unicode_minus"] = False

API_KEY = "YOUR_YOUTUBE_API_KEY"  # 여기에 발급받은 키 입력


def search_videos(query, published_after, published_before, max_results=50):
    """키워드로 영상 검색 (게시일 범위 지정, ISO 8601 형식 예: '2025-06-13T00:00:00Z')"""
    url = "https://www.googleapis.com/youtube/v3/search"
    videos = []
    page_token = None
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
            "key": API_KEY,
        }
        if page_token:
            params["pageToken"] = page_token
        res = requests.get(url, params=params).json()
        if "error" in res:
            print("API 오류:", res["error"].get("message"))
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


def get_view_counts(video_ids):
    """영상 ID 리스트로 조회수 일괄 조회 (최대 50개씩 배치)"""
    url = "https://www.googleapis.com/youtube/v3/videos"
    results = {}
    for i in range(0, len(video_ids), 50):
        chunk = video_ids[i:i + 50]
        params = {"part": "statistics", "id": ",".join(chunk), "key": API_KEY}
        res = requests.get(url, params=params).json()
        for item in res.get("items", []):
            results[item["id"]] = int(item["statistics"].get("viewCount", 0))
    return results


def build_dataframe(query, published_after, published_before, event_date):
    videos = search_videos(query, published_after, published_before)
    if not videos:
        print(f"'{query}' 검색 결과 없음 - 쿼리/기간 확인 필요")
        return pd.DataFrame()
    view_counts = get_view_counts([v["video_id"] for v in videos])
    df = pd.DataFrame(videos)
    df["views"] = df["video_id"].map(view_counts)
    df["published_at"] = pd.to_datetime(df["published_at"]).dt.tz_localize(None)
    event_dt = pd.to_datetime(event_date)
    df["days_since_event"] = (df["published_at"] - event_dt).dt.days
    return df.sort_values("days_since_event")


if __name__ == "__main__":
    # ---- 실제 사건 날짜로 반드시 수정할 것 ----
    iran_israel_df = build_dataframe(
        query="이란 이스라엘 전쟁",
        published_after="2025-06-13T00:00:00Z",   # 사건 발생일로 수정
        published_before="2025-07-13T00:00:00Z",   # 관찰 종료일로 수정
        event_date="2025-06-13",
    )

    worldcup_df = build_dataframe(
        query="월드컵 개막전",
        published_after="2026-06-11T00:00:00Z",   # 실제 개막일로 수정
        published_before="2026-07-11T00:00:00Z",
        event_date="2026-06-11",
    )

    if not iran_israel_df.empty:
        iran_israel_df.to_csv("iran_israel_views.csv", index=False, encoding="utf-8-sig")
    if not worldcup_df.empty:
        worldcup_df.to_csv("worldcup_views.csv", index=False, encoding="utf-8-sig")

    fig, ax = plt.subplots(figsize=(10, 6))
    if not iran_israel_df.empty:
        ax.scatter(iran_israel_df["days_since_event"], iran_israel_df["views"],
                   label="이란-이스라엘 전쟁 뉴스", alpha=0.7)
    if not worldcup_df.empty:
        ax.scatter(worldcup_df["days_since_event"], worldcup_df["views"],
                   label="월드컵 개막전", alpha=0.7)
    ax.set_xlabel("사건 발생 후 경과일수 (영상 게시일 기준)")
    ax.set_ylabel("영상 누적 조회수 (log scale)")
    ax.set_title("이슈별 유튜브 조회수 비교 — 업로드 시점 스냅샷 프록시")
    ax.set_yscale("log")
    ax.legend()
    plt.tight_layout()
    plt.savefig("youtube_comparison.png", dpi=150)
    plt.show()
"""
Google Trends 기반 실시간 관심도 시계열 비교
(FOMO 감쇠 곡선 분석용 - 유튜브 스냅샷 프록시보다 방법론적으로 더 적합)

[핵심 차이 - 보고서에 명시할 것]
- 유튜브 조회수 = 실제 시청/클릭 행동 지표, 하지만 시계열 접근 불가 (스냅샷만 가능)
- 구글 트렌드 = '검색 행동' 지표, 조회수는 아니지만 실제 일별 시계열 제공
두 지표는 서로 다른 종류의 관심도를 측정하므로, "유튜브 조회수와 직접 비교"가 아니라
"관심도 감쇠 패턴이라는 공통 현상을 서로 다른 각도에서 보여주는 보조 자료"로
위치시켜 서술하는 것이 방법론적으로 안전함.

[사전 준비]
pip install pytrends
"""

from pytrends.request import TrendReq
import matplotlib.pyplot as plt
import platform

# ---- 한글 폰트 설정 ----
if platform.system() == "Windows":
    plt.rcParams["font.family"] = "Malgun Gothic"
elif platform.system() == "Darwin":
    plt.rcParams["font.family"] = "AppleGothic"
else:
    plt.rcParams["font.family"] = "NanumGothic"
plt.rcParams["axes.unicode_minus"] = False

pytrends = TrendReq(hl="ko-KR", tz=540)


def get_trend(keyword, timeframe, geo="KR"):
    pytrends.build_payload([keyword], timeframe=timeframe, geo=geo)
    df = pytrends.interest_over_time()
    if df.empty:
        print(f"'{keyword}' 데이터 없음 - timeframe/geo 확인 필요")
        return None
    return df[keyword]


if __name__ == "__main__":
    # ---- 실제 사건 날짜 범위로 수정할 것 (timeframe 형식: 'YYYY-MM-DD YYYY-MM-DD') ----
    series1 = get_trend("이란 이스라엘", "2025-06-01 2025-08-01")
    series2 = get_trend("월드컵", "2026-06-01 2026-08-01")

    fig, ax = plt.subplots(figsize=(10, 6))
    if series1 is not None:
        ax.plot(range(len(series1)), series1.values, label="이란-이스라엘 전쟁 (검색 관심도)")
    if series2 is not None:
        ax.plot(range(len(series2)), series2.values, label="월드컵 개막전 (검색 관심도)")
    ax.set_xlabel("사건 발생 후 경과일수")
    ax.set_ylabel("구글 트렌드 상대적 관심도 (0-100)")
    ax.set_title("이슈별 대중 관심도 감쇠 곡선 비교 (Google Trends)")
    ax.legend()
    plt.tight_layout()
    plt.savefig("trends_comparison.png", dpi=150)
    plt.show()
