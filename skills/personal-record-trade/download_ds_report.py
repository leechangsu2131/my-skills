import requests
import os

url = "https://vertexaisearch.cloud.google.com/grounding-api-redirect/AUZIYQGBQlHfIrAH8WQDtPMazSPQJKfDsDlaAxev1ikf5k6pIqswcN_es93l7B35_rCK3hdDaigkNHncMyGtMtqyxR01Lr8qtP4HFGtlNpFuXOLfpCVE7loxMWKhbpVzBU9BBh49cMEnCkhw79qtXABQZCBanDEmyQ=="

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36'
}

r = requests.get(url, headers=headers, allow_redirects=True)
if r.status_code == 200:
    filepath = 'C:/Users/lee21/.gemini/antigravity/scratch/my-skills/skills/personal-record-trade/data/report/033500/DS투자증권_동성화인텍_260519.pdf'
    with open(filepath, 'wb') as f:
        f.write(r.content)
    print("Successfully downloaded DS Securities PDF.")
else:
    print(f"Failed to download: Status {r.status_code}")
