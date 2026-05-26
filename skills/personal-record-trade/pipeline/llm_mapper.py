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

def map_dart_to_metrics(dart_records: list, year: int) -> list:
    """
    DART에서 추출한 Raw JSON 리스트를 LLM(Gemini)에 통과시켜
    valuation_app이 요구하는 16개 핵심 지표 규격(metrics.json)으로 매핑합니다.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("[오류] GEMINI_API_KEY 환경변수가 설정되지 않았습니다.")
        sys.exit(1)

    client = genai.Client(api_key=api_key)
    
    # 1. 추출해야 할 타겟 스키마 정의
    target_keys = [
        "revenue", "operating_income", "net_income", "eps", "ebit", "tax_rate",
        "op_cashflow", "capex", "fcf", "total_equity", "cash", "short_debt",
        "long_debt", "net_debt"
    ]
    
    # 2. LLM에 전달할 프롬프트 구성
    prompt = f"""
    당신은 대한민국 최고 수준의 공인회계사(CPA)이자 금융 데이터 엔지니어입니다.
    아래 제공되는 DART(전자공시시스템)의 {year}년도 연결 재무제표 Raw 데이터를 분석하여, 
    가치평가 모델이 요구하는 필수 재무 지표를 정확히 추출하고 표준 JSON 포맷으로 매핑해 주세요.

    [추출해야 할 지표 목록 (metric_key)]
    {', '.join(target_keys)}

    [Raw 데이터 예시의 일부 필드 설명]
    - fs_div: CFS(연결), OFS(별도) (반드시 CFS 기준 데이터 우선 사용)
    - sj_div: BS(재무상태표), IS(손익계산서), CIS(포괄손익계산서), CF(현금흐름표)
    - account_nm: 계정과목명 (예: '매출액', '영업이익', '영업활동현금흐름')
    - thstrm_amount: 당기 금액 (목표 연도 금액)

    [출력 포맷 (JSON Array)]
    반드시 아래와 같은 JSON 배열 구조로만 출력하세요. 마크다운 블록(```json)이나 부가 설명은 절대 넣지 마세요.
    [
      {{
        "metric_key": "revenue",
        "label": "Revenue",
        "value": 123456789000,
        "unit": "KRW",
        "period": "{year}A",
        "source_method": "llm_mapped",
        "report_year": "{year}",
        "statement_name": "Consolidated Income Statement",
        "original_account_name": "매출액",
        "original_amount": 123456789000,
        "confidence": 0.95,
        "note": "DART CIS 추출"
      }},
      ... 나머지 지표들도 동일한 구조로 ...
    ]
    
    [주의사항]
    - CAPEX(자본적 지출)는 보통 현금흐름표의 '유형자산의 취득' 항목(음수)을 양수로 변환하여 기재합니다.
    - FCF나 Net Debt 처럼 DART에 직접 없는 계정은 수집된 다른 계정을 조합하여 계산(value)해 주세요.
    - 단위는 모두 '원(KRW)' 단위 절대값 정수로 변환하세요.

    [DART Raw 데이터 (JSON)]
    {json.dumps(dart_records, ensure_ascii=False)}
    """
    
    print("LLM(Gemini)에 DART 데이터 분석 및 매핑을 요청합니다...")
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.0,
                response_mime_type="application/json"
            )
        )
        
        # JSON 파싱
        mapped_metrics = json.loads(response.text)
        return mapped_metrics
        
    except Exception as e:
        print(f"[오류] LLM 매핑 실패: {e}")
        return None

if __name__ == "__main__":
    print("이 모듈은 단독 실행보다 파이프라인에서 호출하여 사용합니다.")
