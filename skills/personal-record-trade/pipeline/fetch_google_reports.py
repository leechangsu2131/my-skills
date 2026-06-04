import os
import sys
import time
import requests
import urllib.parse
from pathlib import Path
import pypdf
from dotenv import load_dotenv

# Load environment variables
env_path = Path(r'C:\Users\lee21\.gemini\antigravity\scratch\my-skills\skills\personal-record-trade\.env')
load_dotenv(env_path)

def validate_pdf_content(pdf_path: Path, ticker: str, company_name: str) -> bool:
    """Read the first 2 pages of the PDF to verify if it belongs to the target company."""
    try:
        reader = pypdf.PdfReader(pdf_path)
        text = ""
        for i in range(min(2, len(reader.pages))):
            extracted = reader.pages[i].extract_text()
            if extracted:
                text += extracted
        
        if ticker in text or company_name in text:
            return True
        return False
    except Exception as e:
        print(f"⚠️ PDF 읽기 에러 (검증 실패): {e}")
        return False

def download_pdf(url: str, save_path: Path):
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        resp = requests.get(url, headers=headers, stream=True, timeout=10)
        if resp.status_code == 200:
            with open(save_path, 'wb') as f:
                for chunk in resp.iter_content(chunk_size=1024):
                    if chunk:
                        f.write(chunk)
            return True
        else:
            print(f"❌ 다운로드 실패 (Status {resp.status_code}): {url}")
            return False
    except Exception as e:
        print(f"❌ 다운로드 에러: {e}")
        return False

def fetch_google_reports_serpapi(ticker: str, company_name: str):
    api_key = os.getenv("SERPAPI_KEY")
    if not api_key:
        print("❌ SERPAPI_KEY가 .env 파일에 없습니다.")
        return
        
    # 소연님 제안대로 검색 쿼리를 단순화 (최대한 많이 긁어오고 파이썬으로 필터링)
    query = f'{company_name} 리서치 filetype:pdf'
    print(f"🔍 SerpApi 검색 시작: {query} (API 호출 1건 차감 예상)")
    
    params = {
        "engine": "google",
        "q": query,
        "tbs": "qdr:m6", # 최근 6개월
        "api_key": api_key
    }
    
    try:
        resp = requests.get("https://serpapi.com/search.json", params=params, timeout=20)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        print(f"🚨 SerpApi 호출 실패: {e}")
        return

    organic_results = data.get("organic_results", [])
    unique_links = {res.get("link"): res.get("title", "report") for res in organic_results if "link" in res and res["link"].lower().endswith(".pdf")}
    
    print(f"📑 SerpApi에서 {len(unique_links)}개의 고유 PDF 링크를 찾았습니다.")
    
    root_dir = Path(__file__).parent.parent
    report_dir = root_dir / "data" / "report" / ticker
    report_dir.mkdir(parents=True, exist_ok=True)
    
    # 기존 캐시 초기화
    for f in report_dir.glob("*.pdf"):
        f.unlink()
        
    count = 0
    for i, (url, title) in enumerate(unique_links.items()):
        safe_title = "".join(c for c in title[:50] if c.isalnum() or c in " _-").strip()
        if not safe_title:
            safe_title = f"report_{i+1}"
            
        filename = f"{safe_title}.pdf"
        save_path = report_dir / filename
        
        print(f"[{i+1}] 다운로드 시도: {url}")
        if download_pdf(url, save_path):
            if validate_pdf_content(save_path, ticker, company_name):
                print(f"✅ 검증 통과 및 다운로드 완료: {save_path.name}")
                count += 1
            else:
                print(f"🗑️ 검증 실패 (본문에 종목코드/사명 없음). 파일 삭제: {save_path.name}")
                save_path.unlink()
        
        time.sleep(1) # 다운로드 간격
        
    print(f"🎉 총 {count}개의 유효한 리포트가 {report_dir}에 저장되었습니다.")

if __name__ == "__main__":
    if hasattr(sys.stdout, 'reconfigure'):
        if sys.stdout.encoding != 'utf-8':
            sys.stdout.reconfigure(encoding='utf-8')
            
    fetch_google_reports_serpapi("067160", "SOOP")
