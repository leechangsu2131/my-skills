import os, json, requests
from dotenv import load_dotenv

load_dotenv(".env")
TOKEN = os.getenv("DISCORD_BOT_TOKEN")
CHANNEL_ID = os.getenv("DISCORD_CHANNEL_ID")

r = requests.get(
    f"https://discord.com/api/v10/channels/{CHANNEL_ID}/messages?limit=10", 
    headers={"Authorization": f"Bot {TOKEN}"}
)

msgs = r.json()
for m in msgs:
    print(f"[{m.get('author',{}).get('username')}] {m.get('content')}")
