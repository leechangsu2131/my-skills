import requests
import os

os.makedirs('C:/Users/lee21/.gemini/antigravity/scratch/my-skills/skills/personal-record-trade/docs/research', exist_ok=True)

url = "https://vertexaisearch.cloud.google.com/grounding-api-redirect/AUZIYQGwjAHL6a5rqRX5OUq3K35VOxcVaXj8NrE5rfgkvgT9Ruq7UJSl0zZnffwHNZCEg2gDLb-PfqPgLaKqcrAjdek2n0aFlp00pzoOGMRnXeeUta-H4rTa-x6nsbG4jWLhG8dIRmjSA80tTZ-5JXqPQPvSInLmR9-N7t5-HlTJnGvverf8B3zVT6XxCsaVCm69QdSQRXb6KkK0zFROzsx7evKI2PYJk1OLJD0mYrNCQyoKGRLmuWaJtiYzkYIr4J6GHYUCZNrXW0mTCr1RiOIjYWp0k6eoc_A7uGzwU-R-7cw_c9h9bA7uzFYtTLr0sViq7MvpXcD3biWmzzkML5gvqQpOXDH1dsSAMVB561Ob0hOL19dATrYlnG8Jy9oAh6a6SseYuleL5GZTcNsDwdwLK-k8M5nNNVvCfT8IZPhG2w=="

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36'
}

r = requests.get(url, headers=headers, allow_redirects=True)
if r.status_code == 200:
    filepath = 'C:/Users/lee21/.gemini/antigravity/scratch/my-skills/skills/personal-record-trade/docs/research/033500_GoogleSearch_Report_1.pdf'
    with open(filepath, 'wb') as f:
        f.write(r.content)
    print("Successfully downloaded PDF from Google Search grounding link.")
else:
    print(f"Failed to download: Status {r.status_code}")
