import sys
from pipeline.fetch_google_reports import fetch_google_reports_serpapi

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

print("Fetching reports for 동성화인텍(033500) using SerpApi...")
fetch_google_reports_serpapi("033500", "동성화인텍")
