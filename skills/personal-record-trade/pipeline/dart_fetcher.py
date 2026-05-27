import os
import sys

try:
    from opendartreader import OpenDartReader
except ImportError:
    print("opendartreader 라이브러리가 설치되어 있지 않습니다.")
    print("설치: pip install OpenDartReader")
    sys.exit(1)

def get_dart_data(corp_code: str, year: int):
    """
    DART API를 통해 특정 기업의 특정 연도 재무제표 Raw 데이터를 수집합니다.
    """
    api_key = os.getenv("DART_API_KEY")
    if not api_key:
        print("[오류] DART_API_KEY 환경변수가 설정되지 않았습니다.")
        print("DART 에코시스템(https://opendart.fss.or.kr)에서 API 키를 발급받아 설정하세요.")
        print("예: set DART_API_KEY=당신의키")
        sys.exit(1)

    dart = OpenDartReader(api_key)
    
    print(f"[{corp_code}] {year}년도 DART 재무제표 수집 중...")
    try:
        # 주요 재무제표 (손익계산서, 재무상태표, 현금흐름표 등) 전체 수집 (연결 기준)
        # report_code: '11011' (사업보고서)
        fin_data = dart.finstate_all(corp_code, year, reprt_code='11011', fs_div='CFS')
        
        if fin_data is None or fin_data.empty:
            print("[경고] 데이터를 찾을 수 없습니다. (사업보고서 미발간 또는 연결 재무제표 없음)")
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
