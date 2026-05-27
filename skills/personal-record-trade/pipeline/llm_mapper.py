import os
import sys
import json

try:
    from google import genai
    from google.genai import types
except ImportError:
    print("google-genai 라이브러리가 설치되어 있지 않습니다.")
    print("설치: pip install google-genai")
    sys.exit(1)

def map_dart_to_metrics(dart_records: list, year: int, quarter: str = "A", yf_data: dict = None) -> list:
    """
    DART에서 추출한 Raw JSON 리스트를 규칙 기반으로 분석하여
    valuation_app이 요구하는 핵심 지표 규격(metrics.json)으로 매핑합니다.
    (기존 LLM 방식을 제거하고 Deterministic 파싱으로 변경)
    """
    import pandas as pd
    
    df = pd.DataFrame(dart_records)
    # 연결재무제표(CFS)만 필터
    if 'fs_div' in df.columns:
        df = df[df['fs_div'] == 'CFS']
        
    metrics = []
    
    def extract_value(keywords, is_negative=False, exclude_keywords=None):
        exclude_keywords = exclude_keywords or []
        for idx, row in df.iterrows():
            acc_name = str(row.get('account_nm', '')).strip().replace(' ', '')
            
            if any(ex_kw in acc_name for ex_kw in exclude_keywords):
                continue
                
            for kw in keywords:
                if kw in acc_name:
                    try:
                        val = int(row.get('thstrm_amount', 0))
                        return -val if is_negative else val
                    except:
                        pass
        return 0

    # 주요 항목 규칙 매핑
    revenue = extract_value(['수익(매출액)', '매출액', '영업수익'])
    op_income = extract_value(['영업이익', '영업이익(손실)'])
    net_income = extract_value(['당기순이익', '연결당기순이익', '분기순이익', '반기순이익', '당기순이익(손실)', '분기순이익(손실)', '반기순이익(손실)'], exclude_keywords=['주당', '포괄', '지분', '비지배'])
    op_cashflow = extract_value(['영업활동현금흐름', '영업활동으로인한현금흐름'])
    capex = extract_value(['유형자산의취득', '유형자산취득', '유형자산의증가'], is_negative=True)
    if capex < 0: capex = -capex # CAPEX는 보통 음수 표기되므로 양수로 통일
    
    total_equity = extract_value(['자본총계'])
    cash = extract_value(['현금및현금성자산'])
    short_debt = extract_value(['단기차입금', '유동성장기차입금'])
    long_debt = extract_value(['장기차입금', '사채'])
    
    # 파생 지표
    fcf = op_cashflow - capex if op_cashflow and capex else 0
    net_debt = short_debt + long_debt - cash
    ebit = op_income
    tax_rate = 0.22 # 임시 고정값
    eps = extract_value(['기본주당이익', '기본주당순이익', '주당순이익', '주당이익', '기본주당분기순이익', '기본주당반기순이익', '기본주당이익(손실)'])
    
    mapped_dict = {
        "revenue": ("Revenue", revenue),
        "operating_income": ("Operating Income", op_income),
        "net_income": ("Net Income", net_income),
        "eps": ("EPS", eps),
        "ebit": ("EBIT", ebit),
        "tax_rate": ("Tax Rate", tax_rate),
        "op_cashflow": ("Operating Cash Flow", op_cashflow),
        "capex": ("Capital Expenditures", capex),
        "fcf": ("Free Cash Flow", fcf),
        "total_equity": ("Total Equity", total_equity),
        "cash": ("Cash and Cash Equivalents", cash),
        "short_debt": ("Short-Term Debt", short_debt),
        "long_debt": ("Long-Term Debt", long_debt),
        "net_debt": ("Net Debt", net_debt),
    }

    for key, (label, val) in mapped_dict.items():
        yf_val = yf_data.get(key) if yf_data else None
        
        metrics.append({
            "metric_key": key,
            "label": label,
            "value": float(val) if key == "tax_rate" else int(val),
            "unit": "ratio" if key == "tax_rate" else ("KRW/share" if key == "eps" else "KRW"),
            "period": f"{year}{quarter}",
            "source_method": "rule",
            "report_year": str(year),
            "statement_name": "Mapped from DART Raw",
            "original_account_name": key,
            "original_amount": val,
            "yf_value": yf_val,
            "confidence": 0.8,
            "note": f"Deterministic mapping for {year} {quarter}"
        })
        
    return metrics

if __name__ == "__main__":
    print("이 모듈은 단독 실행보다 파이프라인에서 호출하여 사용합니다.")
