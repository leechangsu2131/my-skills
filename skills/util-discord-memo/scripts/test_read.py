import os, json, requests
import sys as _sys, pathlib as _pl; _sys.path.insert(0, str(next(p / "_shared" for p in _pl.Path(__file__).resolve().parents if (p / "_shared" / "skill_env.py").is_file())))
from skill_env import load_env

load_env()
TOKEN = os.getenv("DISCORD_BOT_TOKEN")
CHANNEL_ID = os.getenv("DISCORD_CHANNEL_ID")

r = requests.get(
    f"https://discord.com/api/v10/channels/{CHANNEL_ID}/messages?limit=10", 
    headers={"Authorization": f"Bot {TOKEN}"}
)

msgs = r.json()
for m in msgs:
    print(f"[{m.get('author',{}).get('username')}] {m.get('content')}")
