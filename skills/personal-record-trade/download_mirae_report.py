import requests
import os

url = "https://vertexaisearch.cloud.google.com/grounding-api-redirect/AUZIYQEt4Qv84uSPyA37Oi7aDmsGfxBMQOINslIk-W3YzWGm4i9kj2Vv52Afu1JQfEWvUK37N9C371r3euc-olPVrRbbfH2R64Xn5kyK5GI1O5ua58DpenxTEyqbRVue3RDlizFw6Udx2NOGvBpLKpRtEayG1btuJRmNorb3YlLQ97dB4-GlfmjB"

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36'
}

r = requests.get(url, headers=headers, allow_redirects=True)
if r.status_code == 200:
    filepath = 'C:/Users/lee21/.gemini/antigravity/scratch/my-skills/skills/personal-record-trade/data/report/033500/미래에셋증권_동성화인텍_260327.pdf'
    with open(filepath, 'wb') as f:
        f.write(r.content)
    print("Successfully downloaded Mirae Asset PDF.")
else:
    print(f"Failed to download: Status {r.status_code}")
