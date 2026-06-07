import requests
from bs4 import BeautifulSoup
import pandas as pd
import io

def fetch_consensus_metrics(ticker: str) -> dict:
    url = f"https://finance.naver.com/item/main.naver?code={ticker}"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
    }
    resp = requests.get(url, headers=headers)
    soup = BeautifulSoup(resp.text, 'html.parser')
    
    tables = soup.find_all('table', {'class': 'tb_type1 tb_num tb_type1_ifrs'})
    if not tables:
        return {}
        
    html_io = io.StringIO(str(tables[0]))
    df = pd.read_html(html_io)[0]
    
    # 컬럼 레벨 평탄화
    df.columns = df.columns.droplevel([0, 2])
    
    # 0번 컬럼이 주요재무정보(이름), 1~4번 컬럼이 연도별 데이터
    # "최근 예상치(E)" 연도 컬럼 찾기
    est_cols = [col for col in df.columns[1:5] if '(E)' in str(col)]
    target_col = est_cols[-1] if est_cols else df.columns[4] # 내년/가장 최신 연도
    
    metrics = {}
    
    # 인덱스 매핑 (네이버 금융 고정 양식)
    # 0: 매출액, 1: 영업이익, 2: 당기순이익, 5: ROE, 9: EPS, 10: PER
    try:
        metrics['revenue'] = float(df.iloc[0][target_col]) if pd.notna(df.iloc[0][target_col]) else None
        metrics['op'] = float(df.iloc[1][target_col]) if pd.notna(df.iloc[1][target_col]) else None
        metrics['roe'] = float(df.iloc[5][target_col]) if pd.notna(df.iloc[5][target_col]) else None
        metrics['eps'] = float(df.iloc[9][target_col]) if pd.notna(df.iloc[9][target_col]) else None
        
        # PER은 10번 인덱스에 있으나, 없거나 NaN일 경우 대비
        per_val = df.iloc[10][target_col]
        metrics['f_per'] = float(per_val) if pd.notna(per_val) else None
        
        metrics['target_year'] = str(target_col)
    except Exception as e:
        print(f"Metrics extraction error: {e}")
        
    return metrics

if __name__ == "__main__":
    print(fetch_consensus_metrics("067160"))
