import os, requests
from dotenv import load_dotenv
load_dotenv(".env")
TOKEN = os.getenv("DISCORD_BOT_TOKEN")
CHANNEL_ID = os.getenv("DISCORD_CHANNEL_ID")
r = requests.get(
    f"https://discord.com/api/v10/channels/{CHANNEL_ID}/messages?limit=10", 
    headers={"Authorization": f"Bot {TOKEN}"},
    verify=False
)
import json
with open('messages.json', 'w', encoding='utf-8') as f:
    json.dump([{'author': m.get('author',{}).get('username'), 'content': m.get('content')} for m in r.json()], f, ensure_ascii=False, indent=2)
