import pandas as pd

def load_medical_data():
    # 1. 파일 로드
    file_path = "국민건강보험공단_정신질환 상병 그룹별 진료 현황_20230523.csv"
    df = pd.read_csv(file_path, encoding='cp949')

    # 2. 필터링 및 3. 명칭 변경(매핑)
    filtered_df = df[df['주상병코드'].isin(['F30-F39', 'F40-F48'])].copy()
    filtered_df['질병군'] = filtered_df['주상병코드'].map({
        'F30-F39': '기분장애',
        'F40-F48': '불안 및 스트레스 장애'
    })

    # 4. 그룹화 및 진료실인원 합계 계산
    grouped_df = filtered_df.groupby(
        ['진료년도', '연령', '성별', '질병군'], 
        as_index=False
    )['진료실인원(명)'].sum()

    return grouped_df
