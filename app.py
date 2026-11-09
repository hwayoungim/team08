from collections import Counter
import html
import os
import platform
import re
import time
import urllib.parse

from bs4 import BeautifulSoup
from kiwipiepy import Kiwi
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import requests
import streamlit as st
from wordcloud import WordCloud

# --- Kiwi 형태소 분석기 초기화 ---
kiwi = Kiwi()


# ---------------------------------------------------------
# 1. 공공 의료 데이터 로드 및 전처리 (data_loader.py 로직 통합)
# ---------------------------------------------------------
@st.cache_data
def load_medical_data():
    file_name = "국민건강보험공단_정신질환 상병 그룹별 진료 현황_20230523.csv"

    if not os.path.exists(file_name):
        raise FileNotFoundError(
            f"'{file_name}' 파일을 찾을 수 없습니다. 파이썬 스크립트와 동일한 폴더에 파일을 위치시켜 주세요."
        )

    df = pd.read_csv(file_name, encoding="cp949")

    # 진료년도에서 '년' 문자열 제거 후 정수형 변환 (예: '2021년' -> 2021)
    df["진료년도"] = (
        df["진료년도"].astype(str).str.replace("년", "").astype(int)
    )

    # 성별 매핑 ('남자' -> '남성', '여자' -> '여성')
    df["성별"] = df["성별"].map({"남자": "남성", "여자": "여성"})

    # 연령대 그룹화 함수
    def map_age_group(age_str):
        if age_str in ["0-4세", "5-9세", "10-14세", "15-19세"]:
            return "10대 이하"
        elif age_str in ["20-24세", "25-29세"]:
            return "20대"
        elif age_str in ["30-34세", "35-39세"]:
            return "30대"
        elif age_str in ["40-44세", "45-49세"]:
            return "40대"
        elif age_str in ["50-54세", "55-59세"]:
            return "50대"
        elif age_str in ["60-64세"]:
            return "60대"
        elif age_str in ["65세 이상"]:
            return "70대 이상"
        return "기타"

    df["연령대_그룹"] = df["연령"].apply(map_age_group)

    # 질병군 코드 매핑
    disease_map = {"기분장애": "F30-F39", "불안 및 스트레스 장애": "F40-F48"}
    rev_disease_map = {v: k for k, v in disease_map.items()}
    df["질병군명"] = df["주상병코드"].map(rev_disease_map)

    return df


# ---------------------------------------------------------
# 2. 뉴스 크롤링 및 자연어 분석 함수 (news_loader.py 로직 통합)
# ---------------------------------------------------------
def get_korean_font_path():
    system_name = platform.system()
    font_candidates = []
    if system_name == "Windows":
        font_candidates = [
            "C:/Windows/Fonts/malgun.ttf",
            "C:/Windows/Fonts/gulim.ttc",
            "malgun.ttf",
        ]
    elif system_name == "Darwin":
        font_candidates = [
            "/System/Library/Fonts/Supplemental/AppleGothic.ttf",
            "/Library/Fonts/AppleGothic.ttf",
        ]
    else:
        font_candidates = [
            "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
            "/usr/share/fonts/truetype/nanum/NanumBarunGothic.ttf",
        ]

    for path in font_candidates:
        if os.path.exists(path):
            return path
    return None


def crawl_news_data(keyword, count=30):
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
        print(f"뉴스 수집 중 오류 발생: {e}")

    time.sleep(0.3)
    return news_list


def analyze_nouns_with_kiwi(titles):
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
        tokens = kiwi.tokenize(title)
        for token in tokens:
            if token.tag in ("NNG", "NNP") and len(token.form) >= 2:
                if token.form not in stopwords:
                    nouns.append(token.form)
    return Counter(nouns)


def generate_wordcloud(word_counts):
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
            wc = WordCloud(
                background_color="white", width=700, height=350
            ).generate_from_frequencies(word_counts)
        return wc
    except Exception as e:
        print(f"WordCloud 생성 실패: {e}")
        return None


# ---------------------------------------------------------
# 3. 메인 애플리케이션 실행 함수
# ---------------------------------------------------------
def main():
    st.set_page_config(
        page_title="정신질환 진료 추이 및 뉴스 동향 통합 분석",
        page_icon="📊",
        layout="wide",
    )

    # 탭 메뉴 구성 (의료데이터 분석 vs 뉴스 미디어 동향 분석)
    tab_medical, tab_news = st.tabs(
        ["🏥 공공 의료데이터 분석", "📰 정신건강 뉴스 동향 분석"]
    )

    # ==========================================
    # TAB 1: 공공 의료데이터 분석
    # ==========================================
    with tab_medical:
        try:
            df = load_medical_data()
        except Exception as e:
            st.error(f"⚠️ **데이터 로드 실패**: {e}")
            st.info(
                "💡 팁: 스트림릿을 실행 중인 폴더에 CSV 파일이 있는지 확인해주세요."
            )
            return

        st.markdown(
            "# 공공 의료데이터를 활용한 연령, 성별 정신질환 진료 추이 분석"
        )
        st.markdown(
            "### 본 웹 애플리케이션은 공공 의료 빅데이터를 바탕으로 연령·성별·질병군에 따른 정신건강 진료 현황 및 추세를 탐색하고 시각화합니다."
        )
        st.markdown("---")

        # 사이드바 컨트롤러
        st.sidebar.header("🔍 의료데이터 분석 조건 설정")
        available_years = list(range(2021, 2009, -1))
        selected_year = st.sidebar.selectbox(
            "기준 연도 선택", options=available_years, index=0
        )
        selected_age = st.sidebar.selectbox(
            "연령대 선택",
            options=[
                "전체",
                "10대 이하",
                "20대",
                "30대",
                "40대",
                "50대",
                "60대",
                "70대 이상",
            ],
            index=0,
        )
        selected_gender = st.sidebar.selectbox(
            "성별 선택", options=["전체", "남성", "여성"], index=0
        )
        selected_disease = st.sidebar.selectbox(
            "질병군 선택", options=["기분장애", "불안 및 스트레스 장애"], index=0
        )

        st.sidebar.markdown("---")
        st.sidebar.caption(
            f"📌 **현재 조건**: {selected_year}년 | {selected_age} | {selected_gender} | {selected_disease}"
        )

        # 데이터 필터링 로직
        disease_code = (
            "F30-F39" if selected_disease == "기분장애" else "F40-F48"
        )

        df_filtered = df[
            (df["진료년도"] == selected_year)
            & (df["주상병코드"] == disease_code)
        ]
        df_prev = (
            df[
                (df["진료년도"] == selected_year - 1)
                & (df["주상병코드"] == disease_code)
            ]
            if selected_year > 2010
            else None
        )

        if selected_gender != "전체":
            df_filtered = df_filtered[df_filtered["성별"] == selected_gender]
            if df_prev is not None and len(df_prev) > 0:
                df_prev = df_prev[df_prev["성별"] == selected_gender]

        if selected_age != "전체":
            df_filtered = df_filtered[
                df_filtered["연령대_그룹"] == selected_age
            ]
            if df_prev is not None and len(df_prev) > 0:
                df_prev = df_prev[df_prev["연령대_그룹"] == selected_age]

        current_patients = (
            int(df_filtered["진료실인원(명)"].sum())
            if len(df_filtered) > 0
            else 0
        )
        current_claims = (
            int(df_filtered["진료건수(건)"].sum()) if len(df_filtered) > 0 else 0
        )
        avg_treatments = (
            round(current_claims / current_patients, 1)
            if current_patients > 0
            else 0.0
        )

        if df_prev is not None and len(df_prev) > 0:
            prev_patients = int(df_prev["진료실인원(명)"].sum())
            prev_claims = int(df_prev["진료건수(건)"].sum())
            prev_avg_treatments = (
                prev_claims / prev_patients if prev_patients > 0 else 0.0
            )

            growth_rate = (
                round(
                    ((current_patients - prev_patients) / prev_patients) * 100,
                    2,
                )
                if prev_patients > 0
                else 0.0
            )
            avg_treatments_growth = (
                round(
                    (
                        (avg_treatments - prev_avg_treatments)
                        / prev_avg_treatments
                    )
                    * 100,
                    2,
                )
                if prev_avg_treatments > 0
                else 0.0
            )
        else:
            growth_rate = 0.0
            avg_treatments_growth = 0.0

        df_year_total = df[df["진료년도"] == selected_year]
        total_all_disease_patients = df_year_total["진료실인원(명)"].sum()
        disease_share = (
            round(
                (current_patients / total_all_disease_patients) * 100,
                1,
            )
            if total_all_disease_patients > 0
            else 0.0
        )

        # 주요 지표 요약 카드
        st.subheader("📌 주요 진료 현황 요약")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric(
                label=f"{selected_year}년 총 진료인원",
                value=f"{current_patients:,} 명",
                delta=f"{growth_rate}% (전년 대비)",
            )
        with col2:
            st.metric(
                label="1인당 평균 진료건수(내원일수 추정)",
                value=f"{avg_treatments} 건",
                delta=f"{avg_treatments_growth}% (전년 대비)",
            )
        with col3:
            st.metric(
                label="전체 정신질환 중 해당 질병군 비중",
                value=f"{disease_share}%",
                delta=None,
            )

        st.markdown("---")

        # 시각화 영역 (3단 나란히)
        st.subheader("📈 진료 추이 및 비교 분석 시각화")
        chart_col1, chart_col2, chart_col3 = st.columns(3)

        with chart_col1:
            st.markdown("##### 1. 연도별 진료인원 추이 (2010~2021)")
            df_trend = df[df["주상병코드"] == disease_code]
            if selected_gender != "전체":
                df_trend = df_trend[df_trend["성별"] == selected_gender]
            if selected_age != "전체":
                df_trend = df_trend[df_trend["연령대_그룹"] == selected_age]
            trend_data = df_trend.groupby("진료년도")["진료실인원(명)"].sum()
            st.line_chart(trend_data)

        with chart_col2:
            st.markdown("##### 2. 연령대 및 성별 인원 비교")
            df_age_gender = df[
                (df["진료년도"] == selected_year)
                & (df["주상병코드"] == disease_code)
            ]
            pivot_age_gender = df_age_gender.pivot_table(
                index="연령대_그룹",
                columns="성별",
                values="진료실인원(명)",
                aggfunc="sum",
            ).reindex([
                "10대 이하",
                "20대",
                "30대",
                "40대",
                "50대",
                "60대",
                "70대 이상",
            ]).fillna(0)
            st.bar_chart(pivot_age_gender)

        with chart_col3:
            st.markdown("##### 3. 질병군별 진료 비중 비교")
            df_disease_comp = df[df["진료년도"] == selected_year]
            if selected_gender != "전체":
                df_disease_comp = df_disease_comp[
                    df_disease_comp["성별"] == selected_gender
                ]
            if selected_age != "전체":
                df_disease_comp = df_disease_comp[
                    df_disease_comp["연령대_그룹"] == selected_age
                ]
            disease_comp_data = df_disease_comp.groupby("질병군명")[
                "진료실인원(명)"
            ].sum()
            st.bar_chart(disease_comp_data)

        st.markdown("---")

        # 📌 [추가 기능] 그래프 하단 필터링된 실제 데이터 출력 영역
        st.subheader("📋 조건별 필터링된 상세 의료 데이터")
        st.markdown(
            f"현재 적용된 조건 (`{selected_year}년`, `{selected_age}`, `{selected_gender}`, `{selected_disease}`)에 해당하는 상세 원본 데이터입니다."
        )

        if not df_filtered.empty:
            st.dataframe(df_filtered, use_container_width=True)

            # CSV 다운로드 버튼 제공
            csv_data = df_filtered.to_csv(index=False, encoding="utf-8-sig")
            st.download_button(
                label="📥 필터링된 데이터 CSV 다운로드",
                data=csv_data,
                file_name=f"filtered_mental_health_{selected_year}.csv",
                mime="text/csv",
            )
        else:
            st.warning(
                "조건에 일치하는 데이터가 존재하지 않습니다. 다른 조건을 선택해 보세요."
            )

    # ==========================================
    # TAB 2: 정신건강 뉴스 동향 분석 (news_loader 통합)
    # ==========================================
    with tab_news:
        st.title("네이버/구글 뉴스 정신질환 보도 동향 분석")
        st.caption(
            "Kiwi 형태소 분석기를 활용하여 우울증 및 불안장애 관련 뉴스를 수집·분석합니다."
        )

        col_ctrl, col_view = st.columns([1, 2])

        with col_ctrl:
            st.subheader("수집 설정")
            selected_keywords = st.multiselect(
                "수집할 키워드 선택",
                options=[
                    "우울증",
                    "불안장애",
                    "기분장애",
                    "청년 우울증",
                    "스트레스",
                ],
                default=["우울증", "불안장애"],
            )
            article_limit = st.slider(
                "키워드당 수집 기사 수",
                min_value=10,
                max_value=50,
                value=30,
                step=10,
            )
            start_button = st.button("뉴스 데이터 수집 시작")

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
                df_news = pd.DataFrame(all_results)

                if not df_news.empty:
                    m1, m2 = st.columns(2)
                    m1.metric("수집된 총 기사 수", f"{len(df_news)}건")
                    m2.metric("선택 키워드 수", f"{total_kw}개")

                    st.dataframe(df_news, use_container_width=True)

                    df_news.to_csv(
                        "news_mental_data.csv",
                        index=False,
                        encoding="utf-8-sig",
                    )
                    st.caption(
                        "수집된 데이터가 news_mental_data.csv 파일로 저장되었습니다."
                    )

                    st.markdown(
                        "### 주요 키워드 빈도 분석 (Kiwi 형태소 분석)"
                    )
                    word_counts = analyze_nouns_with_kiwi(
                        df_news["기사제목"].tolist()
                    )

                    tab_wc, tab_bar = st.tabs(
                        ["워드클라우드", "단어 빈도수 상위 10선"]
                    )

                    with tab_wc:
                        wc = generate_wordcloud(word_counts)
                        if wc:
                            fig, ax = plt.subplots(figsize=(10, 5))
                            ax.imshow(wc, interpolation="bilinear")
                            ax.axis("off")
                            st.pyplot(fig)
                        else:
                            st.warning(
                                "시스템에서 적합한 한글 폰트를 찾지 못해 워드클라우드를 렌더링할 수 없습니다."
                            )

                    with tab_bar:
                        top10 = word_counts.most_common(10)
                        df_top10 = pd.DataFrame(
                            top10, columns=["단어", "빈도수"]
                        )
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