#!/usr/bin/env python3
"""학교 배치(config의 layout)에서 3D 프린터용 STL을 만든다. 층별로 나눠 출력해 위로 쌓는 '돌하우스' 모형.

- 층마다: 바닥 슬래브(3mm) + 건물 바깥벽 + 방 칸막이 벽(문 틈 포함) + 층 맞춤 핀/홈 + 바닥 밑면의 층 번호 음각
- 여러 층을 쓰는 방(강당 등)은 위층 바닥에 구멍(보이드)을 내고 가장자리에 낮은 난간을 둔다
- 건물 윤곽은 웹 3D와 같은 방식(방이 차지한 칸에서 작은 틈을 복도로 메움)으로 구한다
- base.stl: 1층을 올려 두는 받침판(오목한 자리 포함)
사용법: python make_stl.py --config config.json --out stl_out --scale 200 --bed 210
필요: pip install trimesh shapely manifold3d scipy numpy
주의: 개략 배치를 그대로 굳히므로 오차가 모형에 남는다. 출력 전 슬라이서로 확인할 것.
"""
import argparse, json, math, os
import numpy as np
import trimesh
from scipy import ndimage
from shapely import affinity
from shapely.geometry import box, Point, Polygon, MultiPolygon
from shapely.ops import unary_union, polylabel

ap = argparse.ArgumentParser()
ap.add_argument("--config", required=True); ap.add_argument("--out", default="stl_out")
ap.add_argument("--scale", type=float, default=200, help="축척 분모. 1칸=1m로 보고 1:200이면 1칸=5mm")
ap.add_argument("--bed", type=float, default=210, help="프린터 출력 가능 한 변(mm). 넘으면 경고")
ap.add_argument("--slab", type=float, default=3.0); ap.add_argument("--ext-t", type=float, default=1.2); ap.add_argument("--int-t", type=float, default=1.0)
a = ap.parse_args()
os.makedirs(a.out, exist_ok=True)
SC = 1000.0 / a.scale                 # 1칸당 mm
SLAB, EXT_T, INT_T = a.slab, a.ext_t, a.int_t
STORY = 3.6 * SC                      # 바깥벽 높이
INT_H = 2.0 * SC                      # 방 칸막이 벽 높이
PIN_H, PIN_R, PAD_R, SOCK_R = 2.2, 1.4, 2.2, 1.7

cfg = json.load(open(a.config, encoding="utf-8"))
rooms = []
for r in cfg["layout"]:
    r = list(r) + [None] * (8 - len(r))
    f0, f1 = int(r[1]), int(r[2] or r[1])
    h = r[7] or 0
    if 0 < h < 1: continue            # 운동장 같은 바닥판은 건물이 아님
    rooms.append(dict(name=r[0], f0=f0, f1=f1, x=float(r[3]), y=float(r[4]), w=float(r[5]), d=float(r[6])))
maxF = max(r["f1"] for r in rooms)
X0 = math.floor(min(r["x"] for r in rooms)) - 4; X1 = math.ceil(max(r["x"] + r["w"] for r in rooms)) + 4
Y0 = math.floor(min(r["y"] for r in rooms)) - 4; Y1 = math.ceil(max(r["y"] + r["d"] for r in rooms)) + 4
NX, NY = X1 - X0, Y1 - Y0

def to_mm(g):                          # 칸 좌표(남쪽이 +y) -> mm (북쪽이 위=+y)
    g = affinity.scale(g, 1, -1, origin=(0, 0)); g = affinity.translate(g, -X0, Y1)
    return affinity.scale(g, SC, SC, origin=(0, 0))

def polys(g):
    if g is None or g.is_empty: return []
    if g.geom_type == "Polygon": return [g]
    return [p for part in getattr(g, "geoms", []) for p in polys(part)]

def extrude(g, z0, z1):
    ms = []
    for p in polys(g):
        if p.area < 0.05: continue
        m = trimesh.creation.extrude_polygon(p, z1 - z0); m.apply_translation([0, 0, z0]); ms.append(m)
    return ms

def union(ms):
    ms = [m for m in ms if m is not None and len(m.faces)]
    if not ms: return None
    return ms[0] if len(ms) == 1 else trimesh.boolean.union(ms, engine="manifold")

def cyl(x, y, z0, z1, r):
    c = trimesh.creation.cylinder(radius=r, height=z1 - z0, sections=28); c.apply_translation([x, y, (z0 + z1) / 2]); return c

def footprint(f):                      # 그 층에서 방이 차지한 칸(작은 틈은 복도로 메움)
    occ = np.zeros((NY + 8, NX + 8), bool)
    for r in rooms:
        if r["f0"] <= f <= r["f1"]:
            occ[math.floor(r["y"]) - Y0 + 4: math.ceil(r["y"] + r["d"]) - Y0 + 4, math.floor(r["x"]) - X0 + 4: math.ceil(r["x"] + r["w"]) - X0 + 4] = True
    st = np.ones((5, 5), bool)
    reg = ndimage.binary_erosion(ndimage.binary_dilation(occ, st), st, border_value=0)[4:-4, 4:-4]
    cells = [box(X0 + cx, Y0 + cy, X0 + cx + 1, Y0 + cy + 1) for cy in range(NY) for cx in range(NX) if reg[cy, cx]]
    return to_mm(unary_union(cells)) if cells else None

def seven_seg(d, h=7.0, w=4.0, t=0.9):   # 층 번호(칠 세그먼트). 밑면에 새기므로 좌우를 뒤집어 그린다
    seg = {"a": (0, h - t, w, h), "b": (w - t, h / 2, w, h), "c": (w - t, 0, w, h / 2), "d": (0, 0, w, t), "e": (0, 0, t, h / 2), "f": (0, h / 2, t, h), "g": (0, h / 2 - t / 2, w, h / 2 + t / 2)}
    on = {1: "bc", 2: "abged", 3: "abgcd", 4: "fgbc", 5: "afgcd", 6: "afgedc", 7: "abc", 8: "abcdefg", 9: "abcdfg"}[d]
    g = unary_union([box(*seg[k]) for k in on]); g = affinity.translate(g, -w / 2, -h / 2); return affinity.scale(g, -1, 1, origin=(0, 0))

reg = {f: footprint(f) for f in range(1, maxF + 1)}
def room_rect(r):
    return to_mm(box(r["x"] + 0.15, r["y"] + 0.15, r["x"] + r["w"] - 0.15, r["y"] + r["d"] - 0.15))
void = {}
for f in range(1, maxF + 1):
    vs = [room_rect(r) for r in rooms if r["f0"] < f <= r["f1"]]
    void[f] = unary_union(vs) if vs else None
slab_poly = {f: (reg[f].difference(void[f]) if void[f] is not None else reg[f]) for f in reg if reg[f] is not None}

def pin_points(f):                     # 아래층 바깥벽 안쪽(없으면 두 층이 겹치는 안쪽)에서 위층 바닥이 덮는 곳 4곳
    if f + 1 not in slab_poly or f not in slab_poly: return []
    low, up = slab_poly[f].buffer(-2.3), slab_poly[f + 1].buffer(-2.3)
    cand = []
    line = reg[f].buffer(-2.3).boundary
    for L in (line.geoms if hasattr(line, "geoms") else [line]):
        n = max(2, int(L.length // 4))
        for i in range(n):
            p = L.interpolate(i / n, normalized=True)
            if low.contains(p) and up.contains(p): cand.append((p.x, p.y))
    if len(cand) < 4:                                              # 위층이 작을 때: 겹치는 영역 안쪽 격자점도 후보로
        inter = low.intersection(up)
        if not inter.is_empty:
            x0, y0, x1, y1 = inter.bounds
            for gx in np.arange(x0, x1 + 0.1, 4.0):
                for gy in np.arange(y0, y1 + 0.1, 4.0):
                    if inter.contains(Point(gx, gy)): cand.append((float(gx), float(gy)))
    if len(cand) < 3: return cand
    c0 = up.centroid if not up.is_empty else reg[f].centroid
    pts = [max(cand, key=lambda c: (c[0] - c0.x) ** 2 + (c[1] - c0.y) ** 2)]
    while len(pts) < 4:
        pts.append(max(cand, key=lambda c: min((c[0] - q[0]) ** 2 + (c[1] - q[1]) ** 2 for q in pts)))
    return pts
pins = {f: pin_points(f) for f in range(1, maxF + 1)}

report = []
for f in range(1, maxF + 1):
    if f not in slab_poly: continue
    R, S = reg[f], slab_poly[f]
    parts = []
    slab = union(extrude(S, 0, SLAB))
    cut = [cyl(x, y, -0.1, 2.2, SOCK_R) for (x, y) in pins.get(f - 1, [])]                       # 아래층 핀이 꽂히는 홈
    big = max(polys(S), key=lambda p: p.area); pole = polylabel(big, tolerance=1.0)
    cut += extrude(affinity.translate(seven_seg(f), pole.x, pole.y), -0.1, 0.8)                    # 밑면 층 번호 음각
    slab = trimesh.boolean.difference([slab, union(cut)], engine="manifold")
    parts.append(slab)
    parts += extrude(R.difference(R.buffer(-EXT_T, join_style=2)), SLAB - 0.05, SLAB + STORY)     # 바깥벽
    iw = []
    for r in rooms:
        if r["f0"] != f: continue
        rc = room_rect(r); wall = rc.difference(rc.buffer(-INT_T, join_style=2)); W = (r["w"] - 0.3) * SC
        if W >= 2.7 * SC:                                                                           # 앞(남쪽)에 문 틈
            gap = min(1.3 * SC, 0.35 * W); cx = (rc.bounds[0] + rc.bounds[2]) / 2
            wall = wall.difference(box(cx - gap / 2, rc.bounds[1] - 0.2, cx + gap / 2, rc.bounds[1] + INT_T + 0.2))
        iw.append(wall)
    if iw: parts += extrude(unary_union(iw).intersection(R.buffer(0.2)), SLAB - 0.05, SLAB + INT_H)   # 방 칸막이 벽
    if void[f] is not None:                                                                        # 여러 층 공간의 구멍 가장자리 난간
        parts += extrude(void[f].buffer(1.0, join_style=2).difference(void[f]).intersection(S), SLAB - 0.05, SLAB + 3.0)
    for (x, y) in pins.get(f, []):
        parts.append(cyl(x, y, SLAB - 0.05, SLAB + STORY, PAD_R)); parts.append(cyl(x, y, SLAB + STORY - 0.05, SLAB + STORY + PIN_H, PIN_R))
    m = union(parts)
    fn = os.path.join(a.out, "floor_%d.stl" % f); m.export(fn)
    bx = m.bounds[1] - m.bounds[0]
    report.append(dict(floor=f, file=os.path.basename(fn), size_mm=[round(float(v), 1) for v in bx], watertight=bool(m.is_watertight), volume_cm3=round(float(m.volume) / 1000, 1), faces=int(len(m.faces)),
                       fits_bed=bool(bx[0] <= a.bed and bx[1] <= a.bed), pins=len(pins.get(f, [])), sockets=len(pins.get(f - 1, []))))

R1 = reg[1]; minx, miny, maxx, maxy = R1.bounds                                                    # 받침판
base = union(extrude(box(minx - 8, miny - 8, maxx + 8, maxy + 8), 0, 3.0))
base = trimesh.boolean.difference([base, union(extrude(R1.buffer(0.4), 1.8, 3.1))], engine="manifold"); base.export(os.path.join(a.out, "base.stl"))
bb = base.bounds[1] - base.bounds[0]
report.append(dict(floor=0, file="base.stl", size_mm=[round(float(v), 1) for v in bb], watertight=bool(base.is_watertight), volume_cm3=round(float(base.volume) / 1000, 1), faces=int(len(base.faces)), fits_bed=bool(bb[0] <= a.bed and bb[1] <= a.bed), pins=0, sockets=0))
json.dump(dict(scale=f"1:{int(a.scale)}", mm_per_unit=SC, slab=SLAB, ext_wall=EXT_T, int_wall=INT_T, story_mm=STORY, files=report), open(os.path.join(a.out, "report.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
for r in report: print(r)
