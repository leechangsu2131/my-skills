import json
import sys
from pathlib import Path
import pypdf

# Windows cp949 인코딩 오류 방지
if hasattr(sys.stdout, 'reconfigure'):
    if sys.stdout.encoding != 'utf-8':
        sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    if sys.stderr.encoding != 'utf-8':
        sys.stderr.reconfigure(encoding='utf-8')

def extract_text_from_pdf(pdf_path: str) -> str:
    text = ""
    try:
        with open(pdf_path, 'rb') as f:
            reader = pypdf.PdfReader(f)
            for page in reader.pages:
                extracted = page.extract_text()
                if extracted:
                    text += extracted + "\n"
    except Exception as e:
        print(f"PDF 읽기 오류: {e}")
    return text

def parse_report_with_llm(text: str) -> dict:
    """
    실전에서는 여기에 google-genai API(또는 OpenAI) 호출 코드가 들어갑니다.
    프롬프트에 Pydantic Schema나 JSON 형식을 지정하여 정형화된 데이터를 받아옵니다.
    지금은 테스트 및 구조 논의를 위해 추출될 데이터 형태를 하드코딩하여 보여줍니다.
    """
    return {
        "ticker": "042700",
        "company_name": "한미반도체",
        "brokerage": "상상인증권",
        "date": "2026-05-21",
        "investment_opinion": "Buy",
        "target_price": 380000,
        "metrics": {
            "24M_fwd_eps": 5430,
            "peer_target_per": 69.8,
            "upside_potential_percent": 14.3
        },
        "summary": "1분기는 비수기 및 투자 공백으로 부진했으나, 2분기부터 북미 고객사향 TC 본더 출하가 본격화되며 V자 반등이 예상됨. 하반기부터 2.5D 패키징용 신규 장비 및 HBF 모멘텀 개화 기대.",
        "key_factors": [
            "주요 고객사의 HBM4 투자는 2분기 이후로 이연됨",
            "글로벌 Peer BESI의 2026년 예상 PER 69.8배를 밸류에이션에 적용",
            "26년 연간 매출액 7,850억원, 영업이익 3,694억원으로 사상 최대 실적 기대"
        ],
        "validation_warnings": [
            # 파이프라인에서 표의 숫자와 텍스트 숫자가 다를 경우 경고를 남길 수 있습니다.
        ]
    }

def main():
    root_dir = Path(__file__).parent.parent
    pdf_path = root_dir / "data" / "report" / "CM0079_4443_1.pdf"
    
    print(f"📄 1단계: 리포트 읽기 시작 ({pdf_path.name})")
    text = extract_text_from_pdf(str(pdf_path))
    print(f"✔️ 텍스트 추출 완료 (길이: {len(text)}자)")
    print(f"   [샘플] {text[:100]}...\n")
    
    print("🤖 2단계: LLM 분석 진행 중 (Structured JSON 추출 시뮬레이션)...")
    result = parse_report_with_llm(text)
    
    print("\n========================================")
    print("📊 리포트 파싱 결과 (JSON 형태)")
    print("========================================")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    
    print("\n========================================")
    print("💡 이 데이터를 시트의 어디에 어떻게 넣을까요?")
    print("========================================")
    print("예시 1) 시트에 '목표가', '투자의견' 열을 새로 만들어서 result['target_price'] 값을 바로 꽂기")
    print("예시 2) R열(한줄판단)에 result['summary'] 텍스트를 조합해서 넣기")
    print("예시 3) K열(섹터PER대비)을 계산할 때, 기존 industry_context.json 대신 리포트의 result['metrics']['peer_target_per'](69.8)을 덮어쓰기")

if __name__ == "__main__":
    main()
