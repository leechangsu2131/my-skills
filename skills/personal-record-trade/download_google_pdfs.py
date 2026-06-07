import requests
from bs4 import BeautifulSoup
import os
import time

os.makedirs('C:/Users/lee21/.gemini/antigravity/scratch/my-skills/skills/personal-record-trade/docs/research', exist_ok=True)

query = "동성화인텍 리포트 OR 리서치 filetype:pdf"
url = f"https://www.google.com/search?q={query}"
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36'
}

r = requests.get(url, headers=headers)
soup = BeautifulSoup(r.text, 'html.parser')

pdf_links = []
for a in soup.find_all('a', href=True):
    href = a['href']
    if '.pdf' in href:
        # Sometimes google prepends /url?q=
        if href.startswith('/url?q='):
            href = href.split('/url?q=')[1].split('&')[0]
        if href.startswith('http') and '.pdf' in href:
            pdf_links.append(href)

print(f"Found {len(pdf_links)} PDF links from Google Search.")

downloaded = 0
for link in pdf_links[:3]:
    try:
        print(f"Downloading from Google result: {link}")
        pdf_r = requests.get(link, headers=headers, timeout=10)
        if pdf_r.status_code == 200:
            filename = f"033500_GoogleSearch_Report_{downloaded+1}.pdf"
            filepath = os.path.join('C:/Users/lee21/.gemini/antigravity/scratch/my-skills/skills/personal-record-trade/docs/research', filename)
            with open(filepath, 'wb') as f:
                f.write(pdf_r.content)
            downloaded += 1
            print(f"Saved {filename}")
        time.sleep(1)
    except Exception as e:
        print(f"Failed to download {link}: {e}")

print(f"Successfully downloaded {downloaded} PDFs from Google.")
