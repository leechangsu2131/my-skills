"""Windows launcher for the route analysis app.
Run by double-clicking start.bat, or: python start.py
"""
import os, subprocess, sys, time, urllib.request, webbrowser

ROOT = os.path.dirname(os.path.abspath(__file__))
os.chdir(ROOT)

def msg(*lines):
    print("=" * 42)
    for line in lines:
        print(line)
    print("=" * 42)

def wait_for_enter(prompt):
    try:
        input(prompt)
    except EOFError:
        print("No interactive console available; continuing.")

# Check Python
if sys.version_info < (3, 7):
    msg("Python 3.7+ required.", f"Current: {sys.version}")
    wait_for_enter("Press Enter to exit...")
    sys.exit(1)

# Check central .env (skills/_shared/skill_env.py)
import sys as _sys, pathlib as _pl; _sys.path.insert(0, str(next(p / "_shared" for p in _pl.Path(__file__).resolve().parents if (p / "_shared" / "skill_env.py").is_file())))
from skill_env import env_values, central_env_path
_key = env_values("util-map-time").get("KAKAO_API_KEY", "")
if not _key or "your_key" in _key:
    msg(
        f"[WARNING] KAKAO_API_KEY not set in central .env: {central_env_path()}",
        "Please replace 'your_key_here' with your actual API key.",
    )
    wait_for_enter("Press Enter to exit...")
    sys.exit(1)

# Start server in background
msg("Starting server...", "Wait a moment...")
proc = subprocess.Popen(
    [sys.executable, "server.py"],
    cwd=ROOT,
    creationflags=subprocess.CREATE_NEW_CONSOLE if sys.platform == "win32" else 0,
)

server_ready = False
for _ in range(20):
    if proc.poll() is not None:
        msg(
            "[ERROR] Server failed to start.",
            f"Exit code: {proc.returncode}",
            "Try running: python server.py",
        )
        wait_for_enter("Press Enter to exit...")
        sys.exit(proc.returncode or 1)

    try:
        with urllib.request.urlopen("http://localhost:5020/api/config", timeout=1):
            server_ready = True
            break
    except Exception:
        time.sleep(0.5)

if not server_ready:
    msg(
        "[ERROR] Server did not respond at http://localhost:5020",
        "The port may already be in use, or server.py may have crashed.",
    )
    proc.terminate()
    wait_for_enter("Press Enter to exit...")
    sys.exit(1)

# Open browser
print("Opening browser at http://localhost:5020 ...")
webbrowser.open("http://localhost:5020")

msg(
    "Server is running at http://localhost:5020",
    "Close the server window (black window) to stop.",
)

wait_for_enter("Press Enter to stop server...")
if proc.poll() is None:
    proc.terminate()
print("Server stopped.")
time.sleep(0.5)
