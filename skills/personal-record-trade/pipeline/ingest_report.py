import re
import json
import sys
import os
from pathlib import Path
import pypdf

# Add pipeline directory to sys.path if not there
pipeline_dir = str(Path(__file__).parent)
if pipeline_dir not in sys.path:
    sys.path.append(pipeline_dir)

try:
    from fetch_naver_consensus import fetch_consensus_metrics
except ImportError:
    print("Warning: fetch_naver_consensus module not found.")
    def fetch_consensus_metrics(ticker): return {}

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

def parse_report_with_regex(text: str, ticker: str = "unknown") -> dict:
    """
    정규표현식을 사용하여 PDF 텍스트에서 투자의견과 목표주가만 빠르고 정확하게 추출합니다.
    """
    # 1. 투자 의견 추출 (Buy, Hold, 매수 등)
    opinion = "N/A"
    opinion_match = re.search(r'(투자의견|Rating|투자등급)[\s:;\|]*(Buy|Hold|Sell|매수|중립|매도)', text, re.IGNORECASE)
    if opinion_match:
        opinion = opinion_match.group(2).capitalize()
    
    # 2. 목표 주가 추출
    target_price = 0
    kr_match = re.search(r'(목표주가|적정주가)[\s:;\|]*([0-9]+)만\s*([0-9]+)?\s*천?원?', text)
    if kr_match:
        man = int(kr_match.group(2)) * 10000
        chun = int(kr_match.group(3)) * 1000 if kr_match.group(3) else 0
        target_price = man + chun

    if target_price == 0:
        price_match = re.search(r'(목표주가|적정주가|Target Price)[\s:;\|]*([0-9,]+)\s*(원)?', text, re.IGNORECASE)
        if price_match:
            val_str = price_match.group(2).replace(',', '')
            if val_str.isdigit() and int(val_str) > 100:
                target_price = int(val_str)

    return {
        "ticker": ticker,
        "investment_opinion": opinion,
        "target_price": target_price,
    }

def main():
    root_dir = Path(__file__).parent.parent
    ticker = "067160"
    report_dir = root_dir / "data" / "report" / ticker
    output_dir = root_dir / "data" / "report_context"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    pdfs = list(report_dir.glob("*.pdf"))
    if not pdfs:
        print(f"No PDFs found for {ticker}")
        return
        
    print(f"🌐 [{ticker}] 네이버 금융 컨센서스(전망치) 데이터 수집 중...")
    consensus_data = fetch_consensus_metrics(ticker)
    if consensus_data:
        print(f"   성공: {consensus_data}")
    else:
        print("   실패: 컨센서스 데이터를 가져오지 못했습니다.")
        
    for i, pdf_path in enumerate(pdfs):
        print(f"\n📄 리포트 읽기 시작 ({pdf_path.name})")
        text = extract_text_from_pdf(str(pdf_path))
        
        print("🤖 정규식 기반 핵심 데이터 추출 진행 중...")
        result = parse_report_with_regex(text, ticker=ticker)
        
        # 합체: PDF 추출 데이터 + 네이버 컨센서스 데이터
        result["consensus_metrics"] = consensus_data
        
        output_file = output_dir / f"{ticker}_{i+1}.json"
        
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
            
        print(f"✅ 리포트 파싱 완료 및 저장됨: {output_file}")
        print(f"   추출 결과: 투자의견={result['investment_opinion']}, 목표가={result['target_price']}")

if __name__ == "__main__":
    main()
