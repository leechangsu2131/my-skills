"""투자시트 건강 점검 (읽기 전용, 시트에 쓰지 않는다).

점검 항목
  1. 오류 셀(#N/A, #REF!, #VALUE!, #DIV/0! 등) 위치  — 📊 가격데이터는 커서 제외
  2. 🎯 비중조절신호 하방(I열)이 '현재가×0.95' 같은 임시식인 종목
  3. 🔬 기업분석에 남아 있는데 📊 포트폴리오에 없는 종목 (2026-11-06 결정상 행 삭제 대상 후보)

설정: 같은 폴더의 sheet_io.py 가 공용 .env 의 시트 ID·서비스 계정 키로 시트를 연다.
실행: python -X utf8 sheet_check.py
"""
import collections
import os
import pathlib
import re
import sys

sys.path.insert(0, str(next(p / "_shared" for p in pathlib.Path(__file__).resolve().parents if (p / "_shared" / "skill_env.py").is_file())))
from skill_env import load_env  # noqa: E402

load_env(skill="personal-invest-sheet")
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))  # 같은 폴더의 sheet_io.py
import gspread  # noqa: E402
import sheet_io  # noqa: E402

ERR = re.compile(r"^#(N/A|REF!|DIV/0!|VALUE!|NAME\?|NUM!|ERROR!|NULL!)")
SKIP = {"📊 가격데이터"}
a1 = gspread.utils.rowcol_to_a1


def errors(sh):
    tabs = [w.title for w in sh.worksheets() if w.title not in SKIP]
    res = sh.values_batch_get([f"'{t}'!A1:AJ400" for t in tabs])
    found = False
    for t, vr in zip(tabs, res["valueRanges"]):
        where = collections.defaultdict(list)
        for i, row in enumerate(vr.get("values", []), 1):
            for j, v in enumerate(row):
                if ERR.match(str(v)):
                    where[v].append(a1(i, j + 1))
        for k, cells in where.items():
            found = True
            more = f" 외 {len(cells) - 10}칸" if len(cells) > 10 else ""
            print(f"  {t}  {k}  {len(cells)}칸: {', '.join(cells[:10])}{more}")
    if not found:
        print("  없음")


def placeholder_downside(sh):
    ws = sh.worksheet("🎯 비중조절신호")
    rows = ws.get("A5:I34", value_render_option="FORMULA")
    hits = [(i, r[0]) for i, r in enumerate(rows, 5)
            if len(r) > 8 and re.search(r"\*\s*0\.9\d?\b", str(r[8]))]
    for i, t in hits:
        print(f"  I{i}  {t}  {rows[i - 5][8]}")
    if not hits:
        print("  없음")


def stale_holdings(sh):
    held = {str(r[0]).lstrip("0") for r in sh.worksheet("📊 포트폴리오").get("C5:C60") if r and r[0]}
    rows = sh.worksheet("🔬 기업분석").get("A5:D60")
    hits = [(i, r) for i, r in enumerate(rows, 5)
            if len(r) > 3 and r[3] == "보유" and str(r[1]).lstrip("0") not in held]
    for i, r in hits:
        print(f"  {i}행  {r[1]} {r[2]}  (📊에 없음 → 행 삭제 후보)")
    if not hits:
        print("  없음")


def main():
    sh = sheet_io.open_sheet()
    for title, fn in [("1. 오류 셀", errors), ("2. 하방 임시식(현재가×0.9x)", placeholder_downside),
                      ("3. 🔬에 남은 청산 종목 (행 삭제 후보)", stale_holdings)]:
        print(title)
        fn(sh)


if __name__ == "__main__":
    main()
