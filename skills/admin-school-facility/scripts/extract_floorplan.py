#!/usr/bin/env python3
"""엑셀로 그려진 학교 배치도(칸에 방 이름·호수를 적은 평면도)에서 방 목록과 대략적인 위치를 뽑는다.

- 층 구분: --floor-tops "1:1,2:28,3:56,..." (층:그 층이 시작하는 행). 층마다 세로로 이어 그린 배치도용.
- 호수(100 이상 숫자), 학급 표기(엑셀이 '1-1'을 날짜로 바꾼 칸), 방 이름을 읽고,
  같은 줄의 오른쪽 숫자 / 이름 위·아래의 숫자를 짝으로 묶는다. 사람이 그린 도면이라 틀릴 수 있어 conf(신뢰도)를 같이 낸다.
- 결과 JSON: [{floor,name,number,cls,x,y,w,d,conf,cell}]. x는 열 번호, y는 층 시작 행 기준 행 번호.
이 결과는 '초안'이다. 여러 층을 쓰는 공간 합치기, 이름 정리, 신청 대상 고르기는 사람과 확인하며 손본다.
사용법: python extract_floorplan.py --xlsx 배치도.xlsx --sheet 1.학교배치도 --floor-tops 1:1,2:28,3:56 --out rooms.json
"""
import argparse, datetime, json, re
from openpyxl import load_workbook
from openpyxl.utils import get_column_letter as L

ap = argparse.ArgumentParser()
ap.add_argument("--xlsx", required=True); ap.add_argument("--sheet", required=True)
ap.add_argument("--floor-tops", required=True); ap.add_argument("--out", required=True)
ap.add_argument("--skip", default="EV,계단,계단실,화장실,공조실,휀룸,폐기물,외부데크,외부계단,하부오픈,외부용,장애인,1인,실,1층,2층,3층,4층,5층,지하")
a = ap.parse_args()
tops = {int(k): int(v) for k, v in (x.split(":") for x in a.floor_tops.split(","))}
SKIP = set(a.skip.split(","))
AC = re.compile(r"^[사저중고]\d+$")
floor_of = lambda r: max(f for f, t in tops.items() if t <= r)

ws = load_workbook(a.xlsx, data_only=True)[a.sheet]
names, nums = [], []
for row in ws.iter_rows():
    for c in row:
        v = c.value
        if v in (None, ""): continue
        t = dict(r=c.row, c=c.column)
        if isinstance(v, datetime.datetime):
            names.append(dict(t, kind="class", val=f"{v.month}-{v.day}"))
        elif isinstance(v, (int, float)):
            if int(v) >= 100: nums.append(dict(t, val=int(v)))
        else:
            s = str(v).strip()
            if s in SKIP or AC.match(s) or s.startswith("(") or s.endswith(")") or re.match(r"^\d\(", s): continue
            names.append(dict(t, kind="name", val=s))

cand = []
for n in nums:
    for t in names:
        dr, dc = n["r"] - t["r"], n["c"] - t["c"]      # dr>0: 이름이 숫자 위, dr<0: 이름이 숫자 아래
        if dr == 0 and 1 <= dc <= 4: d = dc
        elif 1 <= dr <= 3 and -1 <= dc <= 1: d = 1.5 * dr + abs(dc)
        elif -2 <= dr <= -1 and -1 <= dc <= 1: d = 1.5 * abs(dr) + abs(dc) + 0.7
        else: continue
        cand.append((d, id(n), id(t), n, t))
cand.sort(key=lambda x: x[0])
un, ut, link = set(), set(), {}
for d, i, j, n, t in cand:
    if i in un or j in ut: continue
    un.add(i); ut.add(j); link[i] = (t, d)

rooms = []
def add(tokens, name, number, cls, conf):
    cs = [t["c"] for t in tokens]; rs = [t["r"] for t in tokens]
    fl = floor_of(min(rs)); top = tops[fl]
    rooms.append(dict(floor=fl, name=name, number=number, cls=cls, conf=conf, cell=f"{L(min(cs))}{min(rs)}",
                      x=min(cs), y=min(rs) - top, w=max(2, max(cs) - min(cs) + 2), d=max(3, max(rs) - min(rs) + 3)))
for n in nums:
    t, d = link.get(id(n), (None, None))
    if t is None: add([n], "", n["val"], "", "번호만")
    elif t["kind"] == "class": add([n, t], "", n["val"], t["val"], "높음" if d <= 2 else "낮음")
    else: add([n, t], t["val"], n["val"], "", "높음" if d <= 2 else "낮음")
for t in names:
    if id(t) not in ut: add([t], t["val"] if t["kind"] == "name" else "", None, t["val"] if t["kind"] == "class" else "", "이름만")
rooms.sort(key=lambda r: (r["floor"], r["y"], r["x"]))
json.dump(rooms, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
from collections import Counter
print(len(rooms), "rooms", dict(Counter(r["conf"] for r in rooms)), dict(Counter(r["floor"] for r in rooms)))
