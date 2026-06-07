import requests
from bs4 import BeautifulSoup
import os

# Create folder if it doesn't exist
os.makedirs('C:/Users/lee21/.gemini/antigravity/scratch/my-skills/skills/personal-record-trade/docs/research', exist_ok=True)

# Naver Finance Company Research URL for Dongsung Finetec (033500)
url = 'https://finance.naver.com/research/company_list.naver?itemCode=033500'
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

r = requests.get(url, headers=headers)
r.encoding = 'euc-kr'
soup = BeautifulSoup(r.text, 'html.parser')

table = soup.find('table', class_='type_1')
if not table:
    print("No research reports found or table structure changed.")
    exit()

# Find all PDF links
rows = table.find_all('tr')[2:] # Skip header
downloaded = 0
for row in rows:
    tds = row.find_all('td')
    if len(tds) < 5:
        continue
        
    title = tds[1].text.strip()
    broker = tds[2].text.strip()
    date = tds[4].text.strip()
    
    # Extract link
    a_tag = tds[1].find('a')
    if not a_tag:
        continue
    
    # Sometimes PDF is in a different td (tds[3] has the file link)
    file_td = tds[3]
    file_a = file_td.find('a')
    if not file_a:
        continue
        
    pdf_url = file_a.get('href')
    
    # Fix URL if it's relative
    if not pdf_url.startswith('http'):
        pdf_url = 'https://finance.naver.com' + pdf_url
        
    # Download the PDF
    try:
        # Clean title for filename
        clean_title = "".join([c for c in title if c.isalpha() or c.isdigit() or c==' ']).rstrip()
        filename = f"033500_{date.replace('.', '')}_{broker}_{clean_title}.pdf"
        filepath = os.path.join('C:/Users/lee21/.gemini/antigravity/scratch/my-skills/skills/personal-record-trade/docs/research', filename)
        
        print(f"Downloading {filename} from {pdf_url}...")
        pdf_r = requests.get(pdf_url, headers=headers)
        if pdf_r.status_code == 200:
            with open(filepath, 'wb') as f:
                f.write(pdf_r.content)
            downloaded += 1
            if downloaded >= 3: # Just download top 3 latest
                break
    except Exception as e:
        print(f"Failed to download {pdf_url}: {e}")

print(f"Successfully downloaded {downloaded} research PDFs.")
