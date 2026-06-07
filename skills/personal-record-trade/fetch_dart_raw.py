import os
import requests
import json
from dotenv import load_dotenv

load_dotenv('C:/Users/lee21/.gemini/antigravity/scratch/my-skills/skills/personal-record-trade/.env')
DART_API_KEY = os.getenv('DART_API_KEY')

if not DART_API_KEY:
    print("DART_API_KEY not found in .env")
    exit(1)

# Corp code for 동성화인텍: 033500 -> We need the 8-digit corp_code from DART.
# Let's search for corp_code using OpenDart API
corp_code_url = 'https://opendart.fss.or.kr/api/corpCode.xml'
# downloading the corpCode.xml is a zip file, it's a bit heavy.

# Let's use OpenDartReader if installed, otherwise we'll just fetch a news article.
try:
    import OpenDartReader
    dart = OpenDartReader(DART_API_KEY)
    
    # 1. Fetch recent disclosures
    disclosures = dart.list('동성화인텍', start='2025-01-01')
    print(disclosures.head(5))
    
    # Save the disclosure list to a file
    disclosures.to_csv('C:/Users/lee21/.gemini/antigravity/scratch/my-skills/skills/personal-record-trade/docs/research/033500_DART_Disclosures.csv', encoding='utf-8-sig', index=False)
    
    # Let's also get the latest earnings (e.g., 2026 Q1)
    # Using finstate
    fin = dart.finstate('동성화인텍', 2025, reprt_code='11011') # 2025 사업보고서
    if fin is not None:
        fin.to_csv('C:/Users/lee21/.gemini/antigravity/scratch/my-skills/skills/personal-record-trade/docs/research/033500_DART_2025_Annual.csv', encoding='utf-8-sig', index=False)
        print("Saved 2025 Annual Financial Statement to docs/research/033500_DART_2025_Annual.csv")
        
    try:
        fin_q1 = dart.finstate('동성화인텍', 2026, reprt_code='11013') # 2026 1분기
        if fin_q1 is not None:
            fin_q1.to_csv('C:/Users/lee21/.gemini/antigravity/scratch/my-skills/skills/personal-record-trade/docs/research/033500_DART_2026_Q1.csv', encoding='utf-8-sig', index=False)
            print("Saved 2026 Q1 Financial Statement to docs/research/033500_DART_2026_Q1.csv")
    except Exception as e:
        print(f"Could not fetch 2026 Q1 data: {e}")
        
except ImportError:
    print("OpenDartReader is not installed.")
    
