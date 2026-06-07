import requests
from bs4 import BeautifulSoup
import os

url = 'https://finance.naver.com/item/news_news.nhn?code=033500&page=1'
headers = {'User-Agent': 'Mozilla/5.0'}
r = requests.get(url, headers=headers)
r.encoding = 'euc-kr'
soup = BeautifulSoup(r.text, 'html.parser')

output_path = 'C:/Users/lee21/.gemini/antigravity/scratch/my-skills/skills/personal-record-trade/docs/research/033500_News_Original.md'

with open(output_path, 'w', encoding='utf-8') as f:
    f.write('# 동성화인텍 (033500) 최신 뉴스 원본 자료\n\n')
    
    # Find news links
    tbody = soup.find('tbody')
    if tbody:
        rows = tbody.find_all('tr')
        for row in rows:
            td_title = row.find('td', class_='title')
            if not td_title:
                continue
            a_tag = td_title.find('a')
            if not a_tag:
                continue
            
            title = a_tag.text.strip()
            link = 'https://finance.naver.com' + a_tag['href']
            date = row.find('td', class_='date').text.strip()
            source = row.find('td', class_='info').text.strip()
            
            f.write(f'## {title} ({source}, {date})\n')
            f.write(f'**Link**: {link}\n\n')
            
            # Fetch article content
            try:
                article_r = requests.get(link, headers=headers)
                article_r.encoding = 'euc-kr'
                article_soup = BeautifulSoup(article_r.text, 'html.parser')
                content_div = article_soup.find('div', id='news_read')
                if content_div:
                    # Remove unnecessary tags
                    for tag in content_div(['script', 'style', 'div']):
                        if tag.get('class') and 'link_news' in tag.get('class'):
                            tag.decompose()
                    
                    content = content_div.text.strip()
                    # Clean up empty lines
                    content = '\n'.join([line for line in content.splitlines() if line.strip()])
                    f.write(f"{content}\n\n---\n\n")
            except Exception as e:
                f.write(f"*(Failed to fetch article content: {e})*\n\n---\n\n")

print(f"Saved original news data to {output_path}")
