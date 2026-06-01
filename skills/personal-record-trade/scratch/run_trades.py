import os
import json
import subprocess
import sys

BASE_DIR = r"C:\Users\user\.gemini\antigravity\scratch\repos\my-skills\skills\personal-record-trade"
SCRIPT_PATH = os.path.join(BASE_DIR, "2_add_trade.py")

trades = [
    # 2026-06-01 당일매도
    {"date": "2026-06-01", "ticker": "", "name": "TIGER 미국S&P500", "type": "매도", "qty": 782, "price": 28570, "amount": 22341740, "reason": "당일매도"},
    {"date": "2026-06-01", "ticker": "", "name": "PLUS 미국테크TOP10", "type": "매도", "qty": 1166, "price": 25429, "amount": 29650214, "reason": "당일매도"},
    {"date": "2026-06-01", "ticker": "", "name": "SOL 미국AI소프트웨어", "type": "매도", "qty": 615, "price": 16910, "amount": 10399650, "reason": "당일매도"},
    
    # 2026-05-21 미국 주식 매수 (환율 1360원 적용)
    {"date": "2026-05-21", "ticker": "UNH", "name": "유나이티드헬스 그룹", "type": "매수", "qty": 21, "price": 518663, "amount": 10891923, "memo": "환율 1360원 임의 적용 (단가 $381.37)"},
    {"date": "2026-05-21", "ticker": "META", "name": "메타 플랫폼스", "type": "매수", "qty": 5, "price": 820080, "amount": 4100400, "memo": "환율 1360원 임의 적용 (단가 $603.00)"},
    {"date": "2026-05-21", "ticker": "BRKb", "name": "버크셔 해서웨이 B", "type": "매수", "qty": 4, "price": 654160, "amount": 2616640, "memo": "환율 1360원 임의 적용 (단가 $481.00)"},
    {"date": "2026-05-21", "ticker": "AAPL", "name": "애플", "type": "매수", "qty": 4, "price": 409700, "amount": 1638800, "memo": "환율 1360원 임의 적용 (단가 $301.25)"}
]

for t in trades:
    cmd = [sys.executable, SCRIPT_PATH, "--json", json.dumps(t)]
    print(f"Running: {t['name']}")
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=BASE_DIR)
    if result.returncode == 0:
        print(result.stdout)
    else:
        print(f"Error for {t['name']}: {result.stderr}")
