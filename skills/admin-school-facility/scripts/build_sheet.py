#!/usr/bin/env python3
"""학교 기물 대장 · 공간 사용 관리 시트(xlsx) 생성기.
사용법: python build_sheet.py --config config.json --out 관리시트.xlsx
config.json 형식은 assets/config.example.json 참고. 공간·교시·분류·상태·층 배치를 학교에 맞게 바꿔서 만든다.
"""
import argparse, json
from openpyxl.utils import get_column_letter
ap = argparse.ArgumentParser()
ap.add_argument("--config", default=None)
ap.add_argument("--out", default="school_facility_sheet.xlsx")
args = ap.parse_args()
CFG = json.load(open(args.config, encoding="utf-8")) if args.config else {}
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.formatting.rule import FormulaRule, DataBarRule
from datetime import date

F = "Arial"
base = Font(name=F, size=10)
bold = Font(name=F, size=10, bold=True)
white = Font(name=F, size=10, bold=True, color="FFFFFF")
inp = Font(name=F, size=10, color="0000FF")
grayf = Font(name=F, size=9, color="808080")
hdr_fill = PatternFill("solid", fgColor="2F5597")
auto_fill = PatternFill("solid", fgColor="EDEDED")
yel = PatternFill("solid", fgColor="FFFF00")
thin = Side(style="thin", color="BFBFBF")
box = Border(left=thin, right=thin, top=thin, bottom=thin)
center = Alignment(horizontal="center", vertical="center", wrap_text=True)
def header(ws, row, titles, col0=1):
    for i, t in enumerate(titles, col0):
        c = ws.cell(row=row, column=i, value=t)
        c.font = white; c.fill = hdr_fill; c.alignment = center; c.border = box

wb = Workbook()

# ---------- 안내 ----------
ws = wb.active; ws.title = "안내"
lines = [
 ("학교 기물 대장 · 공간 사용 관리 시트", True), ("", False),
 ("[한눈에 보기 – 입력 없이 보기만 하는 시트]", True),
 ("전체현황 : 날짜를 고르면 모든 공간 × 모든 교시의 사용자가 한 표로 나옵니다. 맨 아래에는 교시별 빈 공간 수가 나옵니다.", False),
 ("주간표 : 공간 하나를 골라 그 주 월~금 사용 현황을 봅니다.", False),
 ("기물위치 : 장소별 물품 수량(막대 그래프), 장소를 고르면 그곳의 물품 목록, 품명으로 찾기가 있습니다.", False),
 ("기물요약 : 분류 × 상태별 수량표와 '점검이 필요한 물건'(수리필요·수리중·분실) 목록이 자동으로 나옵니다.", False), ("", False),
 ("[입력하는 시트]", True),
 ("학생사용 : 학생이 교실 QR로 '사용 시작'을 누르면 웹앱이 자동으로 한 줄씩 기록합니다(직접 입력 X). 학생 화면은 웹앱 주소 뒤에 ?mode=student 를 붙여 엽니다.", False),
 ("고정시간표 : 매주 반복되는 정규 수업과 방과후·돌봄 프로그램. 이 시간에는 교사가 신청할 수 없고, 전체현황·주간표·학생 화면에 그대로 나옵니다. 방과후 프로그램은 기수마다 바뀌니 새 기수가 시작되면 이 표를 고치세요.", False),
 ("대여신청 : 교사가 웹앱에서 기물 대여를 신청하면 자동으로 기록됩니다. 상태를 바꿔 반납·반려를 처리할 수 있고, 반납예정일이 지난 대여는 빨갛게 표시됩니다.", False),
 ("사용신청 : 날짜·교시·공간별 사용 기록. 설정의 '승인 필요 공간'은 '승인대기'로 들어옵니다. 같은 칸에 겹치면 '⚠중복', 같은 사람이 같은 날 같은 교시에 두 곳을 신청하면 '⚠본인중복'으로 표시됩니다.", False),
 ("기물대장 : 기물 한 줄에 하나씩 등록. '현재 위치'는 이동수리이력을 보고 자동으로 바뀝니다.", False),
 ("이동수리이력 : 물건을 옮기면 '이동 후 장소'를 적으세요. 같은 물건의 가장 아래(최신) 이동 기록이 현재 위치가 됩니다.", False),
 ("설정 : 공간, 교시, 분류, 상태, 보관 장소 목록. 고치면 모든 드롭다운과 현황표에 반영됩니다. '공간' 칸에 없는 방(교무실, 교장실, 행정실, 학급 교실 등)은 3D에는 보여도 사용 신청을 받지 않습니다.", False),
 ("배치 : 3D 화면에 그릴 방별 위치·크기(시작층, 끝층, X, Y, 가로, 세로). 여러 층을 쓰는 공간은 끝층을 더 크게 적습니다. 3D 웹앱이 이 표를 읽습니다.", False), ("", False),
 ("[사용 규칙]", True),
 ("파란 글씨 = 직접 입력 / 회색 칸 = 자동 계산(건드리지 마세요) / 노란 칸 = 보기 조건을 고르는 칸.", False),
 ("기물대장·사용신청·이동수리이력의 첫 줄은 예시입니다. 실제 사용 전에 지워 주세요(자동 계산 칸의 수식은 지우지 마세요).", False),
 ("이동수리이력은 날짜 순서대로 아래에 이어서 적어야 '최신 이동'이 정확합니다.", False),
 ("자동 수식은 사용신청 500행, 기물대장·이동수리이력 1000행까지 들어 있습니다. 설정의 공간 칸은 사용 신청을 받는 방만 적습니다(최대 50개).", False),
 ("공간·보관 장소 이름을 바꿀 때는 기존 기록의 이름도 같이 고쳐야 현황표에 잡힙니다.", False),
]
for i,(t,b) in enumerate(lines,1):
    ws.cell(row=i, column=1, value=t).font = Font(name=F, size=12 if i==1 else 10, bold=b)
ws.column_dimensions["A"].width = 120

# ---------- 설정 ----------
st = wb.create_sheet("설정")
header(st, 1, ["공간(사용 신청 대상)", "교시", "시간", "분류", "상태", "이동구분", "보관 장소", "신청자 명단(교사)", "학생 개방 공간(빈 교실)", "대여 가능 분류", "승인 필요 공간"])
spaces = CFG.get("spaces") or ["운동장","강당","체육관","도서실","컴퓨터실","과학실","음악실","빈교실 1","빈교실 2","빈교실 3"]
periods = [tuple(p) for p in (CFG.get("periods") or [["1교시","09:00-09:40"],["2교시","09:50-10:30"],["3교시","10:40-11:20"],["4교시","11:30-12:10"],["점심","12:10-13:00"],["5교시","13:00-13:40"],["6교시","13:50-14:30"],["7교시","14:40-15:20"],["방과후","15:30-17:00"]])]
NP = len(periods)
assert 1 <= NP <= 20, "교시는 1~20개까지"
LET = [get_column_letter(i+2) for i in range(NP)]
LASTL = LET[-1]
cats = CFG.get("categories") or ["교구","가구","전자기기","체육용품","실험기구","도서","기타"]
states = CFG.get("states") or ["양호","수리필요","수리중","분실","폐기"]
moves = CFG.get("moves") or ["이동","수리","폐기","분실","기타"]
MAXS, MAXP = 50, 240   # 신청 대상 공간 최대 50개, 보관 장소(모든 방 포함) 최대 240개
# 배치: [공간, 시작층, 끝층, X, Y, 가로, 세로, 높이(선택)]  (여러 층을 쓰는 공간은 끝층을 더 크게)
layout = []
for r in (CFG.get("layout") or []):
    r = list(r) + [None] * (8 - len(r))
    layout.append((r[0], int(r[1]), int(r[2] or r[1]), r[3], r[4], r[5], r[6], r[7]))
if not layout:
    layout = [(s,1,1,(i%6)*9,(i//6)*8,8,6,None) for i,s in enumerate(spaces)]
_extra = CFG.get("extra_places") if CFG.get("extra_places") is not None else ["창고","교무실","행정실"]
places = []
for n in list(spaces) + [r[0] for r in layout] + list(_extra):
    if n not in places: places.append(n)
assert len(spaces) <= MAXS and len(places) <= MAXP, f"신청 대상 공간은 {MAXS}개, 보관 장소는 {MAXP}개까지"
import re as _re, sys as _sys
_adm = [n for n in spaces if _re.search(r"교무|행정|교장|방송|보건|상담|위클래스|원감|전기실|당직", n)]
if _adm: print("주의: 신청 대상(spaces)에 행정·지원실로 보이는 이름이 있어요 -> " + ", ".join(_adm) + " (신청을 받지 않는 방이면 spaces에서 빼세요. 배치(layout)에는 그대로 둬도 3D에 보여요)", file=_sys.stderr)
S0 = spaces[0]; S1 = spaces[1] if len(spaces) > 1 else spaces[0]; P2 = periods[min(2, NP-1)][0]
for i,v in enumerate(spaces,2): st.cell(row=i,column=1,value=v)
for i,(p,t) in enumerate(periods,2):
    st.cell(row=i,column=2,value=p); st.cell(row=i,column=3,value=t)
for i,v in enumerate(cats,2): st.cell(row=i,column=4,value=v)
for i,v in enumerate(states,2): st.cell(row=i,column=5,value=v)
for i,v in enumerate(moves,2): st.cell(row=i,column=6,value=v)
for i,v in enumerate(places,2): st.cell(row=i,column=7,value=v)
PEOPLE = [str(x).strip() for x in (CFG.get("people") or []) if str(x).strip()]
assert len(PEOPLE) <= 200, "신청자 명단은 200명까지"
for i,v in enumerate(PEOPLE,2): st.cell(row=i,column=8,value=v)
STUDENT_ROOMS = [r for r in (CFG.get("student_rooms") or []) if r]
assert len(STUDENT_ROOMS) <= 100, "학생 개방 공간은 100개까지"
for i,v in enumerate(STUDENT_ROOMS,2): st.cell(row=i,column=9,value=v)
LEND_CATS = [str(x) for x in (CFG.get("lendable_categories") if CFG.get("lendable_categories") is not None else cats) if x]
APPROVAL = [str(x) for x in (CFG.get("approval_spaces") or []) if x]
for i,v in enumerate(LEND_CATS,2): st.cell(row=i,column=10,value=v)
for i,v in enumerate(APPROVAL,2): st.cell(row=i,column=11,value=v)
for r in st.iter_rows(min_row=2,max_row=MAXP+1,max_col=11):
    for c in r: c.font = inp; c.border = box
for col,w in zip("ABCDEFGHIJK",[20,10,14,12,12,12,14,18,22,16,22]): st.column_dimensions[col].width = w
st["M1"] = "※ 대여 가능 분류(J열)에 적은 분류의 물품만 웹앱에서 대여 신청을 받습니다(비우면 모든 분류). 승인 필요 공간(K열)에 적은 공간은 신청하면 '승인대기'가 되고, 관리자가 사용신청 시트의 상태를 '확정'으로 바꾸거나 웹앱 관리자 화면에서 승인해야 확정됩니다.  ※ 학생 개방 공간(I열)에 적은 방은 학생 화면(QR)에서 빈 교실로 보이고 학생이 사용을 시작할 수 있습니다. 이름은 배치 시트의 공간 이름과 똑같이 적습니다.  ※ 신청자 명단(H열)을 채우면 웹앱 신청 화면에서 이름을 목록에서 고르게 되어, 같은 사람이 같은 시간에 두 곳을 신청하는 것을 정확히 막을 수 있습니다. 비워 두면 이름을 직접 입력합니다.  ※ 시간표는 예시값입니다. 학교 시정에 맞게 고쳐 주세요. 신청 대상 공간은 최대 50개, 보관 장소(모든 방 포함)는 최대 240개까지 현황표에 나옵니다. 공간 칸에는 사용 신청을 받을 곳만 적습니다."; st["M1"].font = grayf
SP = f"=설정!$A$2:$A${MAXS+1}"; PD = "=설정!$B$2:$B$30"; CT = "=설정!$D$2:$D$30"; SS = "=설정!$E$2:$E$30"; MV = "=설정!$F$2:$F$30"; PL = f"=설정!$G$2:$G${MAXP+1}"

# ---------- 기물대장 ----------
al = wb.create_sheet("기물대장")
header(al, 1, ["관리번호","품명","분류","규격","수량","취득일","취득가(원)","최초 보관 장소","현재 위치(자동)","담당자","상태","비고","(목록용·자동)","(점검목록·자동)","(검색결과·자동)"])
ex = ["A-0001","접이식 책상","가구","600x450mm",10,date(2024,3,4),450000,places[min(1,len(places)-1)],None,"홍길동","양호","예시 행 – 삭제하세요"]
for i,v in enumerate(ex,1):
    if v is not None: al.cell(row=2,column=i,value=v)
H = "이동수리이력"
for r in range(2,1001):
    n = f"SUMPRODUCT(MAX(({H}!$B$2:$B$1000=A{r})*({H}!$E$2:$E$1000<>\"\")*(ROW({H}!$E$2:$E$1000)-1)))"
    al.cell(row=r,column=9,value=f'=IF(A{r}="","",IF({n}=0,H{r},INDEX({H}!$E$2:$E$1000,{n})))')
    al.cell(row=r,column=13,value=f'=IF(AND(A{r}<>"",I{r}=기물위치!$H$1),COUNTIF($I$2:I{r},I{r}),"")')
    al.cell(row=r,column=14,value=f'=IF(AND(A{r}<>"",OR(K{r}="수리필요",K{r}="수리중",K{r}="분실")),COUNTIF($K$2:K{r},"수리필요")+COUNTIF($K$2:K{r},"수리중")+COUNTIF($K$2:K{r},"분실"),"")')
    al.cell(row=r,column=15,value=f'=IF(AND(A{r}<>"",기물위치!$M$1<>"",ISNUMBER(SEARCH(기물위치!$M$1,B{r}&" "&A{r}&" "&C{r}&" "&D{r}&" "&J{r}&" "&L{r}))),MAX(O$1:O{r-1})+1,"")')
    for c in range(1,16):
        cell = al.cell(row=r,column=c)
        if c in (9,13,14,15): cell.font = grayf; cell.fill = auto_fill
        else: cell.font = inp
        cell.border = box
    al.cell(row=r,column=6).number_format = "yyyy-mm-dd"
    al.cell(row=r,column=7).number_format = "#,##0"
for col,w in zip("ABCDEFGHIJKLMNO",[12,20,12,16,8,12,14,16,16,10,10,24,12,12,12]): al.column_dimensions[col].width = w
al.freeze_panes = "A2"
def dvl(ws, f, rng, strict=True):
    d = DataValidation(type="list", formula1=f, allow_blank=True, showErrorMessage=strict); ws.add_data_validation(d); d.add(rng)
dvl(al, CT, "C2:C1000"); dvl(al, PL, "H2:H1000"); dvl(al, SS, "K2:K1000")
al.conditional_formatting.add("A2:A1000", FormulaRule(formula=['AND(A2<>"",COUNTIF($A$2:$A$1000,A2)>1)'], fill=PatternFill("solid", bgColor="FFC7CE")))
al.conditional_formatting.add("K2:K1000", FormulaRule(formula=['OR(K2="수리필요",K2="수리중")'], fill=PatternFill("solid", bgColor="FFEB9C")))
al.conditional_formatting.add("K2:K1000", FormulaRule(formula=['K2="분실"'], fill=PatternFill("solid", bgColor="FFC7CE")))
al.conditional_formatting.add("K2:K1000", FormulaRule(formula=['K2="폐기"'], fill=PatternFill("solid", bgColor="D9D9D9")))

# ---------- 이동수리이력 ----------
hs = wb.create_sheet(H)
header(hs, 1, ["일자","관리번호","품명(자동)","구분","이동 후 장소","내용","처리자"])
for i,v in enumerate([date(2025,5,2),"A-0001",None,"이동",places[0],f"{places[min(1,len(places)-1)]}에서 {places[0]}로 이동 (예시)","홍길동"],1):
    if v is not None: hs.cell(row=2,column=i,value=v)
for r in range(2,1001):
    hs.cell(row=r,column=3,value=f'=IF(B{r}="","",IFERROR(INDEX(기물대장!$B$2:$B$1000,MATCH(B{r},기물대장!$A$2:$A$1000,0)),"관리번호 없음"))')
    for c in range(1,8):
        cell = hs.cell(row=r,column=c); cell.border = box
        if c==3: cell.font = grayf; cell.fill = auto_fill
        else: cell.font = inp
    hs.cell(row=r,column=1).number_format = "yyyy-mm-dd"
for col,w in zip("ABCDEFG",[12,12,20,10,16,36,10]): hs.column_dimensions[col].width = w
hs.freeze_panes = "A2"
dvl(hs, MV, "D2:D1000"); dvl(hs, PL, "E2:E1000")
hs["I1"] = "※ 물건을 옮길 때만 '이동 후 장소'를 적으세요. 수리·폐기 기록은 비워도 됩니다."; hs["I1"].font = grayf

# ---------- 고정시간표 (정규 수업) ----------
fx = wb.create_sheet("고정시간표")
header(fx, 1, ["공간","요일","교시","내용(예: 정규 6-1 과학 / 방과후 놀이스포츠)","키(자동)"])
FIXED = [list(x) for x in (CFG.get("fixed_schedule") or [])]
assert len(FIXED) <= 390, "고정 시간표는 390칸까지"
for i, row in enumerate(FIXED, 2):
    for j, v in enumerate(row[:4], 1): fx.cell(row=i, column=j, value=v)
for r in range(2, 401):
    fx.cell(row=r, column=5, value=f'=IF(OR(A{r}="",B{r}="",C{r}=""),"",A{r}&"|"&B{r}&"|"&C{r})')
    for c in range(1, 6):
        cell = fx.cell(row=r, column=c); cell.border = box
        if c == 5: cell.font = grayf; cell.fill = auto_fill
        else: cell.font = inp
for col, w in zip("ABCDE", [20, 8, 10, 24, 28]): fx.column_dimensions[col].width = w
fx.freeze_panes = "A2"
_d = DataValidation(type="list", formula1='"월,화,수,목,금,토,일"', allow_blank=True); fx.add_data_validation(_d); _d.add("B2:B400")
fx["G1"] = "※ 매주 반복되는 정규 수업과 방과후·돌봄 프로그램. 이 칸에 있는 시간에는 교사가 사용 신청을 할 수 없고, 학생 화면에서도 '선생님 수업·프로그램 중'으로 보입니다. 내용 앞에 '정규' 또는 '방과후'를 붙여 구분하세요."
fx["G2"] = "※ 공간 이름은 설정 시트의 공간 이름과 똑같이 적습니다. 학기가 바뀌면 이 표만 고치면 됩니다."
for a in ("G1", "G2"): fx[a].font = grayf

# ---------- 사용신청 ----------
rq = wb.create_sheet("사용신청")
header(rq, 1, ["신청일","사용일","요일(자동)","교시","공간","신청자","용도","중복체크(자동)","키(자동)","표시(자동)","상태"])
for i,v in enumerate([date(2026,10,13),date(2026,10,19),None,P2,S1,"김교사","6학년 합창 연습 (예시)"],1):
    if v is not None: rq.cell(row=2,column=i,value=v)
N = 500
for r in range(2,N+1):
    rq.cell(row=r,column=3,value=f'=IF(B{r}="","",CHOOSE(WEEKDAY(B{r},2),"월","화","수","목","금","토","일"))')
    rq.cell(row=r,column=8,value=f'=IF(I{r}="","",IF(COUNTIF($I$2:$I${N},I{r})>1,"⚠중복",IF(AND(F{r}<>"",COUNTIFS($B$2:$B${N},B{r},$D$2:$D${N},D{r},$F$2:$F${N},F{r})>1),"⚠본인중복",IF(COUNTIF(고정시간표!$E$2:$E$400,E{r}&"|"&C{r}&"|"&D{r})>0,"⚠고정 일정과 겹침","OK"))))')
    rq.cell(row=r,column=9,value=f'=IF(OR(B{r}="",D{r}="",E{r}="",K{r}="반려",K{r}="취소"),"",E{r}&"|"&B{r}&"|"&D{r})')
    rq.cell(row=r,column=10,value=f'=IF(I{r}="","",IF(K{r}="승인대기","⏳ ","")&F{r}&IF(G{r}="",""," ("&G{r}&")"))')
    for c in range(1,12):
        cell = rq.cell(row=r,column=c); cell.border = box
        if c in (3,8,9,10): cell.font = grayf; cell.fill = auto_fill
        else: cell.font = inp
    rq.cell(row=r,column=1).number_format = "yyyy-mm-dd"; rq.cell(row=r,column=2).number_format = "yyyy-mm-dd"
for col,w in zip("ABCDEFGHIJK",[12,12,10,10,14,12,24,14,22,28,12]): rq.column_dimensions[col].width = w
rq.freeze_panes = "A2"
dvl(rq, PD, f"D2:D{N}"); dvl(rq, SP, f"E2:E{N}")
if PEOPLE: dvl(rq, "=설정!$H$2:$H$201", f"F2:F{N}", strict=False)
rq.conditional_formatting.add(f"A2:H{N}", FormulaRule(formula=['LEFT($H2,1)="⚠"'], fill=PatternFill("solid", bgColor="FFC7CE")))
dvl(rq, '"확정,승인대기,반려,취소"', f"K2:K{N}")
rq.conditional_formatting.add(f"A2:K{N}", FormulaRule(formula=['$K2="승인대기"'], fill=PatternFill("solid", bgColor="FFEB9C")))
rq.conditional_formatting.add(f"A2:K{N}", FormulaRule(formula=['OR($K2="반려",$K2="취소")'], font=Font(color="A6A6A6", strike=True)))
rq["M1"] = "※ 상태 칸: 비워 두거나 '확정' = 정상. '승인대기' = 관리자 승인이 필요한 공간의 신청(승인하면 '확정', 거절하면 '반려'). '취소'·'반려'가 되면 그 시간은 다시 비어요."; rq["M1"].font = grayf

# ---------- 대여신청 (웹앱이 자동 기록) ----------
ln = wb.create_sheet("대여신청")
header(ln, 1, ["신청번호","신청일시","관리번호","품명","수량","신청자","대여일","반납예정일","사용 목적","상태","반납일","비고"])
for r in range(2, 402):
    for c in range(1, 13):
        cell = ln.cell(row=r, column=c); cell.font = base; cell.border = box
        if c == 2: cell.number_format = "yyyy-mm-dd hh:mm"
        if c in (7, 8, 11): cell.number_format = "yyyy-mm-dd"
for col, w in zip("ABCDEFGHIJKL", [10, 17, 11, 18, 6, 10, 12, 12, 22, 10, 12, 20]): ln.column_dimensions[col].width = w
ln.freeze_panes = "A2"
dvl(ln, '"승인대기,승인,반납완료,반려,취소"', "J2:J400")
ln.conditional_formatting.add("A2:L400", FormulaRule(formula=['AND($J2="승인",$H2<>"",$H2<TODAY())'], fill=PatternFill("solid", bgColor="FFC7CE")))
ln.conditional_formatting.add("A2:L400", FormulaRule(formula=['$J2="승인대기"'], fill=PatternFill("solid", bgColor="FFEB9C")))
ln.conditional_formatting.add("A2:L400", FormulaRule(formula=['OR($J2="반납완료",$J2="취소",$J2="반려")'], font=Font(color="A6A6A6")))
ln["N1"] = "※ 웹앱에서 교사가 대여를 신청하면 이 시트에 한 줄씩 자동으로 기록됩니다(직접 입력하지 마세요). 대여 가능 수량과 기간 겹침은 서버가 확인하고, 수량이 남아 있으면 바로 '승인'됩니다."
ln["N2"] = "※ 관리자는 상태 칸을 바꿔 처리합니다: 반납했으면 '반납완료', 거절하면 '반려'. 반납예정일이 지났는데 '승인' 그대로면 빨갛게(연체) 표시됩니다."
for a in ("N1", "N2"): ln[a].font = grayf

# ---------- 교직원PIN (숨김) ----------
pn = wb.create_sheet("교직원PIN")
header(pn, 1, ["이름","salt","hash","정한 날"])
pn["F1"] = "※ 교직원 개인 PIN의 암호화(해시) 기록입니다. 수정하지 마세요. PIN을 잊은 사람은 해당 줄의 내용을 지우면 다시 정할 수 있어요(웹앱 관리자 화면에서도 초기화)."
pn["F1"].font = grayf
pn.sheet_state = "hidden"


# ---------- 기물요약 (보기 전용) ----------
sm = wb.create_sheet("기물요약")
sm["A1"] = "기물 현황 요약"; sm["A1"].font = Font(name=F, size=12, bold=True)
sm["A2"] = "(기물대장의 수량 기준 · 보기 전용)"; sm["A2"].font = grayf
sm["A4"] = "분류 \\ 상태"
for j in range(8): sm.cell(row=4, column=2+j, value=f'=IF(설정!E{2+j}="","",설정!E{2+j})')
sm.cell(row=4, column=10, value="합계")
for c in range(1, 11):
    x = sm.cell(row=4, column=c); x.font = white; x.fill = hdr_fill; x.alignment = center; x.border = box
for i in range(14):
    r = 5 + i
    sm.cell(row=r, column=1, value=f'=IF(설정!D{2+i}="","",설정!D{2+i})')
    for j in range(8):
        L = get_column_letter(2+j)
        sm.cell(row=r, column=2+j, value=f'=IF(OR($A{r}="",{L}$4=""),"",SUMIFS(기물대장!$E$2:$E$1000,기물대장!$C$2:$C$1000,$A{r},기물대장!$K$2:$K$1000,{L}$4))')
    sm.cell(row=r, column=10, value=f'=IF($A{r}="","",SUM(B{r}:I{r}))')
    for c in range(1, 11):
        x = sm.cell(row=r, column=c); x.font = bold if c in (1, 10) else base; x.border = box
        if c > 1: x.alignment = Alignment(horizontal="center")
sm.cell(row=19, column=1, value="합계")
for c in range(2, 11):
    L = get_column_letter(c)
    sm.cell(row=19, column=c, value=f'=SUM({L}5:{L}18)')
for c in range(1, 11):
    x = sm.cell(row=19, column=c); x.font = bold; x.fill = auto_fill; x.border = box
    if c > 1: x.alignment = Alignment(horizontal="center")
sm.conditional_formatting.add("B5:I18", FormulaRule(formula=['AND(B$4<>"",B$4<>"양호",B$4<>"폐기",N(B5)>0)'], fill=PatternFill("solid", bgColor="FFEB9C")))
sm["A22"] = "점검이 필요한 물건 (수리필요·수리중·분실)"; sm["A22"].font = Font(name=F, size=11, bold=True)
sm["A23"] = "※ 40건까지 보여 줍니다. 더 많으면 기물대장에서 '상태'로 걸러 보세요."; sm["A23"].font = grayf
heads = ["번호","관리번호","품명","분류","수량","현재 위치","상태","담당자","비고"]
src = [None,"A","B","C","E","I","K","J","L"]
for j, h in enumerate(heads, 1):
    x = sm.cell(row=24, column=j, value=h); x.font = white; x.fill = hdr_fill; x.alignment = center; x.border = box
for k in range(1, 41):
    r = 24 + k
    sm.cell(row=r, column=1, value=k)
    for j in range(1, 9):
        sm.cell(row=r, column=1+j+0, value=f'=IFERROR(INDEX(기물대장!${src[j]}$2:${src[j]}$1000,MATCH($A{r},기물대장!$N$2:$N$1000,0))' + ('' if src[j] == 'E' else '&""') + ',"")')
    for c in range(1, 10):
        x = sm.cell(row=r, column=c); x.font = grayf if c == 1 else base; x.border = box
sm.conditional_formatting.add("A25:I64", FormulaRule(formula=['$G25="분실"'], fill=PatternFill("solid", bgColor="FFC7CE")))
for col, w in zip("ABCDEFGHIJ", [14, 12, 20, 12, 10, 16, 10, 10, 24, 10]): sm.column_dimensions[col].width = w

# ---------- 학생사용 (QR로 시작한 학생 활동 기록) ----------
su = wb.create_sheet("학생사용")
header(su, 1, ["시작","공간","학급·별명","활동","종료예정","종료(실제)"])
import datetime as _dt
_ex = [_dt.datetime(2026,10,15,10,5), (STUDENT_ROOMS[0] if STUDENT_ROOMS else S1), "5-2-7", "모둠 토의 (예시)", _dt.datetime(2026,10,15,10,35), _dt.datetime(2026,10,15,10,30)]
for j,v in enumerate(_ex,1): su.cell(row=2,column=j,value=v)
for r in range(2,402):
    for c in range(1,7):
        cell = su.cell(row=r,column=c); cell.font = inp if r==2 else base; cell.border = box
        if c in (1,5,6): cell.number_format = "yyyy-mm-dd hh:mm"
for col,w in zip("ABCDEF",[18,18,14,24,18,18]): su.column_dimensions[col].width = w
su.freeze_panes = "A2"
su["H1"] = "※ 학생이 QR로 '사용 시작'을 누르면 웹앱이 이 시트의 맨 아래에 한 줄씩 자동으로 기록합니다. 직접 입력하지 마세요(첫 줄은 예시이니 지워도 됩니다)."
su["H2"] = "※ 학급·번호나 별명만 적게 하고 실명은 받지 않습니다. 기록이 쌓이면 학기말에 다른 파일로 보관하고 비우세요."
for a in ("H1","H2"): su[a].font = grayf

# ---------- 주간표 ----------
wk = wb.create_sheet("주간표")
wk["A1"] = "공간"; wk["A2"] = "기준 날짜(그 주 아무 날)"; wk["A3"] = "그 주 월요일(자동)"
wk["B1"] = S1; wk["B2"] = date(2026,10,19); wk["B3"] = "=B2-WEEKDAY(B2,2)+1"
for r in (1,2,3): wk.cell(row=r,column=1).font = bold
wk["B1"].font = inp; wk["B2"].font = inp; wk["B1"].fill = yel; wk["B2"].fill = yel
wk["B3"].font = base; wk["B3"].fill = auto_fill
wk["B2"].number_format = "yyyy-mm-dd"; wk["B3"].number_format = "yyyy-mm-dd"
wk["C1"] = "← 노란 칸 두 곳만 바꾸세요"; wk["C1"].font = grayf
dvl(wk, SP, "B1")
header(wk, 5, ["교시 / 시간"]+[None]*5)
for j,d in enumerate(["월","화","수","목","금"]):
    col = j+2
    c = wk.cell(row=5,column=col,value=f'="{d} "&TEXT($B$3+{j},"m/d")')
    c.font = white; c.fill = hdr_fill; c.alignment = center; c.border = box
    h = wk.cell(row=4,column=col,value=f"=$B$3+{j}"); h.number_format = "yyyy-mm-dd"; h.font = grayf
wk["A4"] = "(날짜 계산용)"; wk["A4"].font = grayf
for i in range(NP):
    r = 6+i
    a = wk.cell(row=r,column=1,value=f'=설정!B{2+i}&CHAR(10)&설정!C{2+i}')
    a.font = bold; a.alignment = center; a.border = box; a.fill = PatternFill("solid", fgColor="DDEBF7")
    for j in range(5):
        L = "BCDEF"[j]; DAY = "월화수목금"[j]
        c = wk.cell(row=r,column=j+2,
            value=f'=IFERROR(INDEX(사용신청!$J$2:$J${N},MATCH($B$1&"|"&{L}$4&"|"&설정!$B${2+i},사용신청!$I$2:$I${N},0)),IFERROR(INDEX(고정시간표!$D$2:$D$400,MATCH($B$1&"|{DAY}|"&설정!$B${2+i},고정시간표!$E$2:$E$400,0)),""))')
        c.font = base; c.alignment = center; c.border = box
    wk.row_dimensions[r].height = 36
wk.column_dimensions["A"].width = 24
for L in "BCDEF": wk.column_dimensions[L].width = 22
wk.conditional_formatting.add(f"B6:F{5+NP}", FormulaRule(formula=['B6<>""'], fill=PatternFill("solid", bgColor="C6E0B4")))
wk.freeze_panes = "B6"

# ---------- 전체현황 ----------
ov = wb.create_sheet("전체현황")
ov["A1"] = "날짜"; ov["A1"].font = bold
ov["B1"] = date(2026,10,19); ov["B1"].font = inp; ov["B1"].fill = yel; ov["B1"].number_format = "yyyy-mm-dd"
ov["C1"] = '=IF(B1="","",TEXT(B1,"yyyy년 m월 d일")&" ("&CHOOSE(WEEKDAY(B1,2),"월","화","수","목","금","토","일")&") 전체 공간 사용 현황")'
ov["C1"].font = Font(name=F, size=12, bold=True)
ov["A2"] = "← 노란 칸에 날짜만 바꾸면 됩니다. 초록 = 사용 중, 회색 글씨 = 비어 있음"; ov["A2"].font = grayf
header(ov, 4, ["공간"]+[None]*NP)
for i in range(NP):
    c = ov.cell(row=4,column=i+2,value=f'=설정!B{2+i}&CHAR(10)&설정!C{2+i}')
    c.font = white; c.fill = hdr_fill; c.alignment = center; c.border = box
ov.row_dimensions[4].height = 30
SR = 5 + MAXS
for k in range(MAXS):
    r = 5+k
    a = ov.cell(row=r,column=1,value=f'=IF(설정!A{2+k}="","",설정!A{2+k})')
    a.font = bold; a.fill = PatternFill("solid", fgColor="DDEBF7"); a.border = box; a.alignment = center
    for i in range(NP):
        c = ov.cell(row=r,column=i+2,
            value=f'=IF($A{r}="","",IFERROR(INDEX(사용신청!$J$2:$J${N},MATCH($A{r}&"|"&$B$1&"|"&설정!$B${2+i},사용신청!$I$2:$I${N},0)),IFERROR(INDEX(고정시간표!$D$2:$D$400,MATCH($A{r}&"|"&CHOOSE(WEEKDAY($B$1,2),"월","화","수","목","금","토","일")&"|"&설정!$B${2+i},고정시간표!$E$2:$E$400,0)),"(비어있음)")))')
        c.font = base; c.alignment = center; c.border = box
    ov.row_dimensions[r].height = 30
ov.cell(row=SR,column=1,value="빈 공간 수").font = bold
ov.cell(row=SR+1,column=1,value="사용 중 공간 수").font = bold
for i in range(NP):
    L = LET[i]
    ov.cell(row=SR,column=i+2,value=f'=COUNTIF({L}5:{L}{SR-1},"(비어있음)")')
    ov.cell(row=SR+1,column=i+2,value=f'=COUNTIF({L}5:{L}{SR-1},"?*")-COUNTIF({L}5:{L}{SR-1},"(비어있음)")')
    for rr in (SR,SR+1):
        c = ov.cell(row=rr,column=i+2); c.font = bold; c.alignment = center; c.border = box; c.fill = auto_fill
for rr in (SR,SR+1):
    ov.cell(row=rr,column=1).border = box; ov.cell(row=rr,column=1).fill = auto_fill
ov.column_dimensions["A"].width = 16
for L in LET: ov.column_dimensions[L].width = 18
ov.conditional_formatting.add(f"B5:{LASTL}{SR-1}", FormulaRule(formula=['B5="(비어있음)"'], font=Font(color="A6A6A6")))
ov.conditional_formatting.add(f"B5:{LASTL}{SR-1}", FormulaRule(formula=['AND(B5<>"",B5<>"(비어있음)")'], fill=PatternFill("solid", bgColor="C6E0B4")))
ov.conditional_formatting.add(f"B{SR}:{LASTL}{SR}", FormulaRule(formula=[f'B{SR}=0'], font=Font(color="C00000", bold=True)))
ov.freeze_panes = "B5"

# ---------- 기물위치 ----------
ml = wb.create_sheet("기물위치")
ml["G1"] = "물품 목록을 볼 장소"; ml["G1"].font = bold
ml["H1"] = places[0]; ml["H1"].font = inp; ml["H1"].fill = yel
dvl(ml, PL, "H1")
ml["A1"] = "장소별 물품 현황"; ml["A1"].font = Font(name=F, size=12, bold=True)
ml["A2"] = "(기물대장의 '현재 위치' 기준)"; ml["A2"].font = grayf
header(ml, 4, ["장소","품목 수","총 수량","수리필요·수리중"])
TR = 5 + MAXP
for k in range(MAXP):
    r = 5+k
    ml.cell(row=r,column=1,value=f'=IF(설정!G{2+k}="","",설정!G{2+k})')
    ml.cell(row=r,column=2,value=f'=IF(A{r}="","",COUNTIF(기물대장!$I$2:$I$1000,A{r}))')
    ml.cell(row=r,column=3,value=f'=IF(A{r}="","",SUMIF(기물대장!$I$2:$I$1000,A{r},기물대장!$E$2:$E$1000))')
    ml.cell(row=r,column=4,value=f'=IF(A{r}="","",COUNTIFS(기물대장!$I$2:$I$1000,A{r},기물대장!$K$2:$K$1000,"수리필요")+COUNTIFS(기물대장!$I$2:$I$1000,A{r},기물대장!$K$2:$K$1000,"수리중"))')
    for c in range(1,5):
        cell = ml.cell(row=r,column=c); cell.font = bold if c==1 else base; cell.border = box
        if c>1: cell.alignment = Alignment(horizontal="center")
ml.cell(row=TR,column=1,value="합계").font = bold
for c,L in ((2,"B"),(3,"C"),(4,"D")):
    x = ml.cell(row=TR,column=c,value=f"=SUM({L}5:{L}{TR-1})"); x.font = bold; x.alignment = Alignment(horizontal="center"); x.fill = auto_fill; x.border = box
ml.cell(row=TR,column=1).border = box; ml.cell(row=TR,column=1).fill = auto_fill
ml.conditional_formatting.add(f"C5:C{TR-1}", DataBarRule(start_type="num", start_value=0, end_type="max", color="5B9BD5"))
ml.conditional_formatting.add(f"D5:D{TR-1}", FormulaRule(formula=['AND(D5<>"",D5>0)'], fill=PatternFill("solid", bgColor="FFEB9C")))
# 장소별 목록
header(ml, 4, ["관리번호","품명","수량","상태"], col0=7)
for k in range(30):
    r = 5+k
    m = f'MATCH({k+1},기물대장!$M$2:$M$1000,0)'
    for c,col in ((7,"A"),(8,"B"),(9,"E"),(10,"K")):
        cell = ml.cell(row=r,column=c,value=f'=IFERROR(INDEX(기물대장!${col}$2:${col}$1000,{m}),"")')
        cell.font = base; cell.border = box
ml["G35"] = "※ 한 번에 30개까지 표시됩니다."; ml["G35"].font = grayf
# 검색
ml["L1"] = "물품 찾기"; ml["L1"].font = bold
ml["M1"] = "책상"; ml["M1"].font = inp; ml["M1"].fill = yel
ml["L2"] = '=IF($M$1="","","일치 "&COUNT(기물대장!$O$2:$O$1000)&"건 (20건까지 표시)")'; ml["L2"].font = grayf
header(ml, 4, ["관리번호","품명","수량","현재 위치","상태"], col0=12)
ml["L3"] = "← 품명·관리번호·분류·규격·담당자·비고의 일부를 쓰면 일치하는 물건을 모두 보여 줍니다."; ml["L3"].font = grayf
for k in range(1, 21):
    r = 4 + k
    for c, col in ((12, "A"), (13, "B"), (14, "E"), (15, "I"), (16, "K")):
        cell = ml.cell(row=r, column=c, value=f'=IFERROR(INDEX(기물대장!${col}$2:${col}$1000,MATCH({k},기물대장!$O$2:$O$1000,0))' + ('' if col == "E" else '&""') + ',"")')
        cell.font = base; cell.border = box
        if c == 14: cell.alignment = Alignment(horizontal="center")
ml.conditional_formatting.add("P5:P24", FormulaRule(formula=['OR(P5="수리필요",P5="수리중",P5="분실")'], fill=PatternFill("solid", bgColor="FFEB9C")))
for col,w in zip("ABCDEFGHIJKLMNOP",[16,10,10,16,3,3,14,22,8,10,3,12,22,8,16,10]): ml.column_dimensions[col].width = w


# ---------- 배치 (3D 화면용) ----------
lo = wb.create_sheet("배치")
header(lo, 1, ["공간","시작층","끝층","X 위치","Y 위치","가로","세로","높이(선택)"])
for i,row in enumerate(layout,2):
    for j,v in enumerate(row,1):
        if v is not None: lo.cell(row=i,column=j,value=v)
for r in range(2,max(len(layout)+40,300)):
    for c in range(1,9):
        cell = lo.cell(row=r,column=c); cell.font = inp; cell.border = box
        if c>1: cell.alignment = Alignment(horizontal="center")
for col,w in zip("ABCDEFGH",[22,8,8,10,10,8,8,10]): lo.column_dimensions[col].width = w
lo["J1"] = "※ 3D 화면에 그려지는 블록의 위치와 크기입니다. 건물의 모든 방을 적어도 되고, 사용 신청을 받을 방만 설정 시트의 '공간' 목록에 같은 이름으로 넣습니다."
lo["J2"] = "※ X는 왼쪽→오른쪽, Y는 위→아래(앞쪽) 방향, 단위는 임의의 칸입니다. 배치도 시트의 칸 위치를 그대로 쓰면 편합니다."
lo["J3"] = "※ 여러 층을 쓰는 공간(강당 등)은 시작층과 끝층을 다르게 적습니다(예: 3, 4). 한 층만 쓰면 둘 다 같은 층 번호입니다."
lo["J4"] = "※ 높이는 비워 두면 층수에 맞춰 자동 계산됩니다. 운동장처럼 낮은 바닥만 필요하면 0.3처럼 적습니다."
for a in ("J1","J2","J3","J4"): lo[a].font = grayf
lo.freeze_panes = "A2"

wb._sheets = [wb[n] for n in ["안내","전체현황","주간표","기물위치","기물요약","사용신청","대여신청","고정시간표","학생사용","기물대장","이동수리이력","설정","배치","교직원PIN"]]
wb.save(args.out)
