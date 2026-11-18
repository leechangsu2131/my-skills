import os, requests, json
import sys as _sys, pathlib as _pl; _sys.path.insert(0, str(next(p / "_shared" for p in _pl.Path(__file__).resolve().parents if (p / "_shared" / "skill_env.py").is_file())))
from skill_env import load_env

load_env()
user_channel_id = os.getenv("DISCORD_CHANNEL_ID")
bot_token = os.getenv("DISCORD_BOT_TOKEN")

r = requests.get(
    f"https://discord.com/api/v10/channels/{user_channel_id}/messages?limit=3", 
    headers={"Authorization": f"Bot {bot_token}"}
)

msgs = r.json()
for m in msgs:
    author = m.get("author", {}).get("username")
    content = m.get("content", "")
    attachments = m.get("attachments", [])
    print(f"[{author}] {content}")
    for a in attachments:
        print(f"  - 첨부파일: {a.get('filename')} ({a.get('url')})")
        
        # 첫 번째 이미지만 로컬로 임시 다운로드해보기
        if a.get('content_type', '').startswith('image/'):
            img_data = requests.get(a.get('url')).content
            with open('temp_img.jpg', 'wb') as f:
                f.write(img_data)
            print("  --> temp_img.jpg 저장 완료")
