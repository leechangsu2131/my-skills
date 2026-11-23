#!/usr/bin/env python3
"""한글(.hwpx) 파일의 본문 문단과 표를 텍스트 격자로 뽑는다. (hwpx = ZIP 안의 XML, 별도 프로그램 불필요)
- 병합된 칸은 시작 칸에만 내용이 있고 colSpan/rowSpan 정보가 같이 나온다. 요일 머리글의 열 범위로 칸을 요일에 맞춰 읽을 때 쓴다.
사용법: python hwpx_tables.py 파일.hwpx [--json out.json]
"""
import argparse, json, re, zipfile
from xml.etree import ElementTree as ET
NS = "{http://www.hancom.co.kr/hwpml/2011/paragraph}"
ap = argparse.ArgumentParser(); ap.add_argument("hwpx"); ap.add_argument("--json")
a = ap.parse_args()
z = zipfile.ZipFile(a.hwpx)
text = lambda el: re.sub(r"\s+", " ", "".join(t.text or "" for t in el.iter(NS + "t"))).strip()
out = []
for name in sorted(n for n in z.namelist() if re.match(r"Contents/section\d+\.xml", n)):
    root = ET.fromstring(z.read(name))
    for ti, tbl in enumerate(root.iter(NS + "tbl")):
        cells = []
        for tr in tbl.findall(NS + "tr"):
            for tc in tr.findall(NS + "tc"):
                ad, sp = tc.find(NS + "cellAddr"), tc.find(NS + "cellSpan")
                cells.append(dict(row=int(ad.get("rowAddr")), col=int(ad.get("colAddr")), rowSpan=int(sp.get("rowSpan", 1)), colSpan=int(sp.get("colSpan", 1)), text=text(tc)))
        out.append(dict(section=name, table=ti, rows=int(tbl.get("rowCnt")), cols=int(tbl.get("colCnt")), cells=cells))
        print(f"== {name} 표 {ti}: {tbl.get('rowCnt')}행 x {tbl.get('colCnt')}열")
        g = {(c["row"], c["col"]): c["text"] for c in cells}
        for r in range(int(tbl.get("rowCnt"))):
            print(r, " | ".join((g.get((r, c)) or "·")[:14] for c in range(int(tbl.get("colCnt")))))
if a.json: json.dump(out, open(a.json, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
