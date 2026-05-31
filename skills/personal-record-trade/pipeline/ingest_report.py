import json
import sys
import os
from pathlib import Path
import pypdf

# Windows cp949 인코딩 오류 방지
if hasattr(sys.stdout, 'reconfigure'):
    if sys.stdout.encoding != 'utf-8':
        sys.stdout.reconfigure(encoding='utf-8')

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
    LLM API 호출 시뮬레이션
    향후 실제 google-genai 또는 OpenAI 연동 시 이 함수를 교체합니다.
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
        ]
    }

def main():
    root_dir = Path(__file__).parent.parent
    pdf_path = root_dir / "data" / "report" / "CM0079_4443_1.pdf"
    output_dir = root_dir / "data" / "report_context"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"📄 리포트 읽기 시작 ({pdf_path.name})")
    text = extract_text_from_pdf(str(pdf_path))
    
    print("🤖 LLM 분석 진행 중...")
    result = parse_report_with_llm(text)
    
    ticker = result.get("ticker", "unknown")
    output_file = output_dir / f"{ticker}.json"
    
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
        
    print(f"✅ 리포트 파싱 완료 및 저장됨: {output_file}")

if __name__ == "__main__":
    main()
