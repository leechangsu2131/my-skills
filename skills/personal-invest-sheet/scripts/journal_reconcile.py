"""키움 매매내역(trades_rows_*.tsv)과 📒 매매일지를 대조한다 (읽기 전용, 시트에 쓰지 않는다).

- 키움 체결을 반영 규칙대로 "한 종목·하루·구분 = 1묶음"으로 합친다.
- 해외 거래는 미국 거래일과 한국 날짜가 하루 어긋날 수 있어 ±1일을 같은 것으로 본다.
- 일지에 없는 묶음을 종목별로 요약하고, 전체 목록을 data_dir()에 TSV로 저장한다.
- 일지에만 있는 행은 다른 계좌(토스·ISA 등) 기록일 수 있어 개수만 보여 준다.

실행: python -X utf8 journal_reconcile.py <trades_rows_*.tsv> [--since YYYY-MM-DD]
설정: 같은 폴더의 sheet_io.py 가 공용 .env 의 시트 ID·서비스 계정 키로 시트를 연다.
"""
import argparse
import collections
import csv
import os
import pathlib
import re
import sys
from datetime import date, timedelta

sys.path.insert(0, str(next(p / "_shared" for p in pathlib.Path(__file__).resolve().parents if (p / "_shared" / "skill_env.py").is_file())))
from skill_env import data_dir, load_env  # noqa: E402

load_env(skill="personal-invest-sheet")
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))  # 같은 폴더의 sheet_io.py
import sheet_io  # noqa: E402


def ticker(t):
    t = str(t).strip().upper().lstrip("0").replace(".", "")
    return "BRKB" if t == "BRKB" else t  # 키움 BRKb ↔ 일지 BRK.B


def day(s):
    m = re.findall(r"\d+", str(s))  # '2025. 10. 1', '2025-10-01', '20251001' 모두 처리
    if len(m) == 1 and len(m[0]) == 8:
        m = [m[0][:4], m[0][4:6], m[0][6:]]
    return date(int(m[0]), int(m[1]), int(m[2])) if len(m) >= 3 else None


def num(s):
    try:
        return float(str(s).replace(",", "") or 0)
    except ValueError:
        return 0.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("tsv")
    ap.add_argument("--since", help="이 날짜부터 대조 (기본: tsv의 첫 날짜)")
    a = ap.parse_args()

    groups = collections.OrderedDict()
    with open(a.tsv, encoding="utf-8-sig") as f:
        for r in csv.DictReader(f, delimiter="\t"):
            k = (day(r["매매일"]), ticker(r["티커"]), r["구분"][:2])
            g = groups.setdefault(k, {"매매일": r["매매일"], "포지션ID": r["포지션ID"], "티커": r["티커"],
                                      "종목명": r["종목명"], "구분": r["구분"], "수량": 0.0, "금액(원)": 0.0, "체결건수": 0})
            g["수량"] += num(r["수량"])
            g["금액(원)"] += num(r["금액(원)"])
            g["체결건수"] += 1
    if not groups:
        sys.exit("tsv에 행이 없습니다.")
    since = day(a.since) if a.since else min(k[0] for k in groups)

    ws = sheet_io.open_sheet().worksheet("📒 매매일지")
    last = int(str(ws.acell("Q3").value).replace(",", ""))
    journal, journal_rows = set(), set()
    for r in ws.get(f"A4:H{last}"):
        if len(r) <= 4 or not day(r[0]) or day(r[0]) < since:
            continue
        k = (ticker(r[2]), r[4][:2])
        journal.add((day(r[0]),) + k)
        journal_rows.add((day(r[0]),) + k)
        # 기간합산 행: 매매근거의 "기간합산 2026-06-08~07-30" 기간 전체를 기록된 것으로 본다
        m = re.search(r"기간합산 (\d{4})-(\d{2})-(\d{2})(?:~(\d{2})-(\d{2}))?", r[7] if len(r) > 7 else "")
        if m:
            ps = date(int(m[1]), int(m[2]), int(m[3]))
            pe = date(int(m[1]), int(m[4]), int(m[5])) if m[4] else ps
            if pe < ps:  # 연도를 넘긴 기간
                pe = pe.replace(year=pe.year + 1)
            for i in range((pe - ps).days + 1):
                journal.add((ps + timedelta(i),) + k)
    api_keys = set(groups)

    def near(k, pool):
        return any((k[0] + timedelta(d), k[1], k[2]) in pool for d in (-1, 0, 1))

    missing = [g for k, g in groups.items() if k[0] >= since and not near(k, journal)]
    only_journal = [k for k in journal_rows if not near(k, api_keys)]

    print(f"기간 {since} ~ / 키움 묶음 {sum(1 for k in groups if k[0] >= since)}개 / 일지 행 {len(journal_rows)}개")
    print(f"일지에 없는 키움 묶음 {len(missing)}개 (금액 합 약 {sum(g['금액(원)'] for g in missing) / 1e8:.1f}억원, 해외는 근사 환율)")
    print(f"키움에 없는 일지 행 {len(only_journal)}개 (다른 계좌 기록일 수 있음)")
    by = collections.defaultdict(list)
    for g in missing:
        by[(g["티커"], g["종목명"])].append(g)
    for (t, n), gs in sorted(by.items(), key=lambda x: -len(x[1]))[:25]:
        b = sum(1 for g in gs if g["구분"].startswith("매수"))
        print(f"  {t:8} {n[:14]:14} 매수 {b}일 매도 {len(gs) - b}일")

    if missing:
        out = data_dir() / f"매매일지_누락후보_{pathlib.Path(a.tsv).stem}.tsv"
        with open(out, "w", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(missing[0]), delimiter="\t")
            w.writeheader()
            for g in sorted(missing, key=lambda g: (day(g["매매일"]), g["티커"])):
                w.writerow({**g, "수량": f"{g['수량']:g}", "금액(원)": f"{g['금액(원)']:.0f}"})
        print("전체 목록:", out)


if __name__ == "__main__":
    main()
