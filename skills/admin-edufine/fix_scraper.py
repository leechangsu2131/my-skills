import os

file_path = 's2b_cart_scraper.py'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace("items = await page.evaluate('''() => {", "items = await page.evaluate(r'''() => {")

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)
