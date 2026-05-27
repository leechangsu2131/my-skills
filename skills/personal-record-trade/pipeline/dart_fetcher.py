import os
import sys

try:
    from opendartreader import OpenDartReader
except ImportError:
    print("opendartreader 라이브러리가 설치되어 있지 않습니다.")
    print("설치: pip install OpenDartReader")
    sys.exit(1)

def get_dart_data(corp_code: str, year: int, quarter: str = "A"):
    """
    DART API를 통해 특정 기업의 재무제표 Raw 데이터를 수집합니다.
    quarter: 'A'(연간/사업보고서), 'Q1'(1분기), 'H1'(반기), 'Q3'(3분기)
    """
    api_key = os.getenv("DART_API_KEY")
    if not api_key:
        print("[오류] DART_API_KEY 환경변수가 설정되지 않았습니다.")
        sys.exit(1)

    dart = OpenDartReader(api_key)
    
    # 보고서 코드 매핑
    report_codes = {
        "A": "11011",   # 사업보고서
        "Q1": "11013",  # 1분기보고서
        "H1": "11012",  # 반기보고서
        "Q3": "11014"   # 3분기보고서
    }
    reprt_code = report_codes.get(quarter.upper(), "11011")
    
    print(f"[{corp_code}] {year}년도 {quarter} DART 재무제표 수집 중...")
    try:
        fin_data = dart.finstate_all(corp_code, year, reprt_code=reprt_code, fs_div='CFS')
        
        if fin_data is None or fin_data.empty:
            print(f"[경고] 데이터를 찾을 수 없습니다. (발간 전이거나 연결 재무제표 없음)")
            return None
            
        # DataFrame을 JSON/Dict 형태로 변환하여 LLM에 넘겨줄 준비
        records = fin_data.to_dict(orient='records')
        return records

    except Exception as e:
        print(f"[오류] DART 수집 실패: {e}")
        return None

if __name__ == "__main__":
    # 테스트용: 삼성전기(009150), 2024년
    res = get_dart_data("009150", 2024)
    if res:
        print(f"총 {len(res)}개의 재무 계정 항목을 수집했습니다.")
        print(res[:3])
