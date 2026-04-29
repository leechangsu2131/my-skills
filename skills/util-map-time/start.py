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

# Check .env
env_path = os.path.join(ROOT, ".env")
if not os.path.exists(env_path):
    msg(
        "[WARNING] .env file not found.",
        "Please create .env with: KAKAO_API_KEY=your_key_here",
        "",
        "1. Go to https://developers.kakao.com",
        "2. Create app -> copy REST API key",
        "3. Save to .env file in this folder",
    )
    wait_for_enter("Press Enter to exit...")
    sys.exit(1)

# Check if KAKAO_API_KEY exists in .env
with open(env_path, "r", encoding="utf-8") as f:
    content = f.read()
if "KAKAO_API_KEY=" not in content or "your_key" in content:
    msg(
        "[WARNING] KAKAO_API_KEY not set in .env",
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
        with urllib.request.urlopen("http://localhost:8080/api/config", timeout=1):
            server_ready = True
            break
    except Exception:
        time.sleep(0.5)

if not server_ready:
    msg(
        "[ERROR] Server did not respond at http://localhost:8080",
        "The port may already be in use, or server.py may have crashed.",
    )
    proc.terminate()
    wait_for_enter("Press Enter to exit...")
    sys.exit(1)

# Open browser
print("Opening browser at http://localhost:8080 ...")
webbrowser.open("http://localhost:8080")

msg(
    "Server is running at http://localhost:8080",
    "Close the server window (black window) to stop.",
)

wait_for_enter("Press Enter to stop server...")
if proc.poll() is None:
    proc.terminate()
print("Server stopped.")
time.sleep(0.5)
