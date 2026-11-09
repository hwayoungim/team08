# 공공 의료데이터 및 뉴스 빅데이터 기반 정신질환 진료 추이 분석 대시보드

## 1. 프로젝트 소개
- 본 웹 애플리케이션은 국민건강보험공단의 진료 빅데이터와 실시간 포털 뉴스 데이터를 결합하여, 연령·성별에 따른 주요 정신질환(기분장애, 불안 및 스트레스 장애)의 진료 현황 추이와 미디어 보도 동향을 탐색하고 시각화하는 대시보드입니다.

## 2. 팀원 및 역할 분담
- 김성민: 포털 뉴스 검색 크롤링 및 Kiwi 형태소 분석, 워드클라우드 시각화 모듈 구현 (`news_loader.py`)
- 송가현: Streamlit 대시보드 UI/UX 레이아웃 설계, 조건별 사이드바 컨트롤러 및 그래프 구성 (`app.py`)
- 윤현민: 데이터-UI 파이프라인 연동, 지표 집계 계산 로직 구현 및 의존성 환경 구축 (`requirements.txt`)
- 임화영: 공공 의료데이터 수집, 전처리 및 상병코드 매핑 로직 구현 (`data_loader.py`), GitHub 형상 및 커밋 관리

## 3. 실행 방법
```bash
# 1. 의존성 라이브러리 설치
pip install -r requirements.txt

# 2. Streamlit 웹 애플리케이션 실행
streamlit run app.py
```

## 4. 사용 라이브러리
streamlit, pandas, numpy, requests, beautifulsoup4, kiwipiepy, matplotlib, wordcloud

## 5. 앱 실행 화면
<img width="1776" height="910" alt="1794218999309" src="https://github.com/user-attachments/assets/573af867-cfa4-4372-9fed-d7dc7115b417" />
<img width="1803" height="700" alt="1794218999243" src="https://github.com/user-attachments/assets/36996763-082f-439f-a7f9-df09e0682fb5" />
<img width="1752" height="702" alt="1794218999184" src="https://github.com/user-attachments/assets/1408a993-f72f-415d-ae6c-486f10abffe4" />
<img width="1762" height="902" alt="1794218999046" src="https://github.com/user-attachments/assets/c49e630c-5d86-4f6f-a88b-b2eb11c04395" />



