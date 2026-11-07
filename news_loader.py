import html
import os
import platform
import re
import time
import urllib.parse
from collections import Counter

from bs4 import BeautifulSoup
from kiwipiepy import Kiwi
import matplotlib.pyplot as plt
import pandas as pd
import requests
import streamlit as st
from wordcloud import WordCloud

# --- 1. Kiwi 형태소 분석기 초기화 ---
kiwi = Kiwi()


# --- 2. 한글 폰트 경로 탐색 함수 ---
def get_korean_font_path():
    """
    운영체제(Windows, Mac, Linux/Streamlit Cloud)에 맞춰 사용 가능한 한글 폰트 경로를 반환하는 함수
    """
    system_name = platform.system()

    font_candidates = []
    if system_name == "Windows":
        font_candidates = [
            "C:/Windows/Fonts/malgun.ttf",
            "C:/Windows/Fonts/gulim.ttc",
            "malgun.ttf",
        ]
    elif system_name == "Darwin":  # Mac OS
        font_candidates = [
            "/System/Library/Fonts/Supplemental/AppleGothic.ttf",
            "/Library/Fonts/AppleGothic.ttf",
        ]
    else:  # Linux (Streamlit Cloud 환경 등)
        font_candidates = [
            "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
            "/usr/share/fonts/truetype/nanum/NanumBarunGothic.ttf",
        ]

    for path in font_candidates:
        if os.path.exists(path):
            return path

    return None


# --- 3. 데이터 수집 함수 ---
def crawl_news_data(keyword, count=30):
    """
    지정한 키워드로 뉴스 피드를 요청하고 기사 제목과 메타데이터를 수집하는 함수
    """
    encoded_kw = urllib.parse.quote(keyword)
    url = f"https://news.google.com/rss/search?q={encoded_kw}&hl=ko&gl=KR&ceid=KR:ko"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }

    news_list = []
    try:
        response = requests.get(url, headers=headers, timeout=8)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")
            items = soup.find_all("item")

            for item in items[:count]:
                title_tag = item.find("title")
                link_tag = item.find("link")
                pubdate_tag = item.find("pubdate")

                if title_tag:
                    title_text = html.unescape(title_tag.get_text(strip=True))
                    link_text = (
                        link_tag.get_text(strip=True) if link_tag else ""
                    )
                    date_text = (
                        pubdate_tag.get_text(strip=True) if pubdate_tag else ""
                    )

                    news_list.append({
                        "키워드": keyword,
                        "기사제목": title_text,
                        "보도일시": date_text,
                        "링크": link_text,
                    })
    except Exception as e:
        print(f"수집 중 오류 발생: {e}")

    time.sleep(0.3)
    return news_list


# --- 4. Kiwi 기반 명사 추출 및 빈도 계산 함수 ---
def analyze_nouns_with_kiwi(titles):
    """
    Kiwi 형태소 분석기를 사용하여 명사(NNG, NNP)를 추출하고 빈도를 계산하는 함수
    """
    stopwords = {
        "뉴스",
        "기자",
        "포토",
        "오늘",
        "종합",
        "속보",
        "일보",
        "신문",
        "위해",
        "통해",
        "관련",
        "대한",
        "따른",
        "지난",
        "올해",
        "있는",
        "하는",
        "등",
        "및",
        "건",
        "명",
        "개",
    }

    nouns = []
    for title in titles:
        # 형태소 분석 토큰화
        tokens = kiwi.tokenize(title)
        for token in tokens:
            # 일반명사(NNG), 고유명사(NNP)만 추출하고 2글자 이상 필터링
            if token.tag in ("NNG", "NNP") and len(token.form) >= 2:
                if token.form not in stopwords:
                    nouns.append(token.form)

    return Counter(nouns)


# --- 5. 워드클라우드 생성 함수 (예외 처리 포함) ---
def generate_wordcloud(word_counts):
    """
    단어 빈도수 딕셔너리와 가용 폰트를 기반으로 워드클라우드를 안전하게 생성하는 함수
    """
    font_path = get_korean_font_path()

    try:
        if font_path:
            wc = WordCloud(
                font_path=font_path,
                background_color="white",
                width=700,
                height=350,
            ).generate_from_frequencies(word_counts)
        else:
            # 지정 폰트 파일이 없을 경우 기본 설정 시도
            wc = WordCloud(
                background_color="white", width=700, height=350
            ).generate_from_frequencies(word_counts)
        return wc
    except Exception as e:
        print(f"WordCloud 생성 실패: {e}")
        return None


# --- 6. 메인 UI 및 실행 로직 ---
def main():
    st.set_page_config(page_title="정신건강 뉴스 분석기", layout="wide")
    st.title("네이버 뉴스 정신질환 보도 동향 분석")
    st.caption(
        "Kiwi 형태소 분석기를 활용하여 우울증 및 불안장애 관련 뉴스를 수집·분석합니다."
    )

    col_ctrl, col_view = st.columns([1, 2])

    with col_ctrl:
        st.subheader("수집 설정")
        selected_keywords = st.multiselect(
            "수집할 키워드 선택",
            options=["우울증", "불안장애", "기분장애", "청년 우울증", "스트레스"],
            default=["우울증", "불안장애"],
        )
        article_limit = st.slider(
            "키워드당 수집 기사 수",
            min_value=10,
            max_value=50,
            value=30,
            step=10,
        )
        start_button = st.button("데이터 수집 시작")

    with col_view:
        st.subheader("수집 데이터 및 시각화 결과")

        if start_button:
            if not selected_keywords:
                st.warning("수집할 키워드를 1개 이상 선택하십시오.")
                return

            all_results = []
            progress_bar = st.progress(0)
            status_text = st.empty()

            total_kw = len(selected_keywords)
            for idx, kw in enumerate(selected_keywords, start=1):
                status_text.text(f"[{idx}/{total_kw}] '{kw}' 뉴스 수집 중...")
                data = crawl_news_data(kw, count=article_limit)
                all_results.extend(data)
                progress_bar.progress(idx / total_kw)

            status_text.text("데이터 수집 완료")

            df = pd.DataFrame(all_results)

            if not df.empty:
                m1, m2 = st.columns(2)
                m1.metric("수집된 총 기사 수", f"{len(df)}건")
                m2.metric("선택 키워드 수", f"{total_kw}개")

                st.dataframe(df, use_container_width=True)

                df.to_csv(
                    "news_mental_data.csv", index=False, encoding="utf-8-sig"
                )
                st.caption(
                    "수집된 데이터가 news_mental_data.csv 파일로 저장되었습니다."
                )

                st.markdown("### 주요 키워드 빈도 분석 (Kiwi 형태소 분석)")
                word_counts = analyze_nouns_with_kiwi(df["기사제목"].tolist())

                tab_wc, tab_bar = st.tabs(["워드클라우드", "단어 빈도수 상위 10선"])

                with tab_wc:
                    wc = generate_wordcloud(word_counts)
                    if wc:
                        fig, ax = plt.subplots(figsize=(10, 5))
                        ax.imshow(wc, interpolation="bilinear")
                        ax.axis("off")
                        st.pyplot(fig)
                    else:
                        st.warning(
                            "시스템에서 적합한 한글 폰트를 찾지 못해 워드클라우드를 렌더링할 수 없습니다. 상위 10선 탭의 차트를 확인하십시오."
                        )

                with tab_bar:
                    top10 = word_counts.most_common(10)
                    df_top10 = pd.DataFrame(top10, columns=["단어", "빈도수"])
                    st.bar_chart(df_top10.set_index("단어"))
                    st.table(df_top10)
            else:
                st.warning("수집된 데이터가 없습니다.")
        else:
            st.info(
                "왼쪽 패널에서 키워드를 선택하고 수집 시작 버튼을 누르십시오."
            )


if __name__ == "__main__":
    main()