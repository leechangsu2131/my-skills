# -*- coding: utf-8 -*-
"""S2B 학교장터 — 사용자 Chrome(9222)의 내 탭 하나로 검색·비교·견적서 담기·에듀파인 엑셀 받기.

Playwright 로 새 브라우저를 띄우는 s2b_buyer.py 와 달리, 교사가 평소 쓰는 Chrome 에 백그라운드 탭을
하나 열어 쓴다. 로그인 세션이 남아 사람이 같은 견적서 목록을 바로 볼 수 있고, 에듀파인과 같은 Chrome 이다.

사용 예 (Python 3.10+, websockets 필요):
    python s2b_cdp.py login
    python s2b_cdp.py search "훌라후프 걸이대" "라켓 보관대" --top 15     # 전국, 낮은 금액순
    python s2b_cdp.py detail <물품번호> <물품번호>                       # 배송비·납품기간·규격 등
    python s2b_cdp.py add <물품번호>:30 <물품번호>:2                     # 물품번호:수량 → 견적서 접수
    python s2b_cdp.py cart                                               # 견적서 접수목록
    python s2b_cdp.py delete <견적접수코드> <견적접수코드>               # cart 의 첫 칸(rc)으로 삭제
    python s2b_cdp.py edufine-xls <rc>,<rc> [출력.xls]                   # 에듀파인 품목 업로드 양식

알아둘 것 (ISSUES.md ISSUE-001):
  - 검색 URL 의 searchQuery 는 EUC-KR 이라 UTF-8 로 넣으면 깨진다 → 검색창 폼에 값을 넣고 submit.
  - 로그인 계정 기본값은 "우리지역(경북)" 필터 → areaCode 를 비워야 전국 검색.
  - 견적서 담기 fnSave() 는 팝업 창을 연다 → confirm/window.open/form.submit 을 바꿔 fetch POST 로 보낸다.
  - 제시금액(estimate_price)에는 조건부 배송비가 붙는다. "5만원 미만" 기준은 공급가(부가세 제외)라
    1,700원×30개=51,000원이어도 배송비가 붙었다. 담은 뒤 cart 로 꼭 확인한다.
  - 에듀파인 연계 엑셀(estimateEdufine)에는 배송비 행이 없다 → 품의에 배송비를 따로 넣는다.
"""
from __future__ import annotations

import argparse
import base64
import json
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(next(p / "_shared" for p in Path(__file__).resolve().parents if (p / "_shared" / "skill_env.py").is_file())))
from skill_env import data_dir, load_env  # noqa: E402
from cdp_tab import Tab  # noqa: E402

BASE = "https://www.s2b.kr"
LOGIN_URL = BASE + "/S2BNCustomer/Login.do"
SEARCH_URL = BASE + "/S2BNCustomer/S2B/scrweb/remu/rema/searchengine/s2bCustomerSearch.jsp?actionType=MAIN_SEARCH&searchQuery="
DETAIL_URL = BASE + "/S2BNCustomer/rema100.do?forwardName=detail&f_re_estimate_code={}"
CART_URL = BASE + "/S2BNCustomer/remc100.do?forwardName=estimateList"


def tab() -> Tab:
    return Tab.open_or_new(data_dir("admin-s2b-buyer") / "cdp_tab_id.txt", LOGIN_URL, "s2b.kr")


# ───────────────────────── 로그인 ─────────────────────────
def login(t: Tab) -> bool:
    """세션이 살아 있으면 Login.do 가 index 로 넘어간다. 아니면 개인이용자 폼으로 로그인."""
    import os
    load_env()
    t.goto(LOGIN_URL, 2)
    if not t.js("!!document.querySelector('form[name=personal_loginForm]')"):
        return "Login.do" not in t.js("location.href")
    uid, pw = os.environ.get("S2B_USER_ID", ""), os.environ.get("S2B_USER_PW", "")
    if not uid or not pw:
        raise SystemExit("중앙 .env 에 S2B_USER_ID, S2B_USER_PW 가 없습니다.")
    t.js(f"""(()=>{{const tab=document.querySelector('ul.tabs a[href="#prlogin"]');if(tab)tab.click();
      const f=document.querySelector('form[name=personal_loginForm]');
      f.querySelector('input[name=uid]').value={json.dumps(uid)};
      f.querySelector('input[name=pwd]').value={json.dumps(pw)};
      f.querySelector('.btn_login a').click();}})()""", await_promise=False)
    time.sleep(4)
    t.wait_ready(2)
    if "pwd_changeinfo.jsp" in t.js("location.href"):  # 비밀번호 변경 안내 → 메인으로
        t.goto(BASE + "/S2BNCustomer/S2B/", 2)
    return "Login.do" not in t.js("location.href")


# ───────────────────────── 검색 ─────────────────────────
_PARSE = r"""(()=>{const out=[];document.querySelectorAll('input[name=checkFlag]').forEach(c=>{const tr=c.closest('tr');
 const a=tr.querySelector('.obj_name .l01 a');if(!a)return;const sp=a.querySelector('span');const spec=sp?sp.innerText.trim():'';
 const name=a.innerText.replace(spec,'').trim();const pl=[...tr.querySelectorAll('.lt_mulpumprice li')].map(l=>l.innerText.trim());
 const etc=tr.querySelectorAll('td.obj_etc');
 out.push({id:c.value,name,spec,price:parseInt((pl[0]||'0').replace(/[^0-9]/g,''))||0,ship:pl.slice(3).join('/'),
  vendor:etc[0]?etc[0].innerText.split('\n')[0].trim():'',region:etc[1]?etc[1].innerText.replace(/\s+/g,' ').trim():''})});return out})()"""


def search(t: Tab, query: str, nationwide: bool = True) -> tuple[int, list[dict]]:
    """낮은 금액순(PCAC) 첫 페이지(50개) 결과."""
    if not t.js("!!(document.forms['s2bSearchForm'] && document.forms['s2bSearchForm'].sortField && document.querySelector('#searchQuery'))"):
        t.goto(SEARCH_URL, 2)
    # 전국: 지역 코드·체크를 모두 비운다. 우리지역: 계정 기본 지역 코드를 그대로 둔다.
    area_reset = ("f.areaCode.value='';f.localAreaCode.value='';"
                  "document.querySelectorAll('input[id^=areaEach_],input[id^=localAreaEach_]').forEach(x=>x.checked=false);"
                  if nationwide else "")
    t.js(f"""(()=>{{const f=document.forms['s2bSearchForm'];document.querySelector('#searchQuery').value={json.dumps(query)};
      f.sortField.value='PCAC';['priceMin','priceMax','priceMinSet','priceMaxSet','startIndex'].forEach(k=>{{if(f[k])f[k].value=''}});
      const r=document.querySelector('input[name=locationGbn][value={"all" if nationwide else "local"}]');if(r)r.checked=true;
      {area_reset}
      f.submit();}})()""", await_promise=False)
    time.sleep(2)
    t.wait_ready(1.5)
    total = t.js(r"(document.body.innerText.match(/검색결과는 총([0-9,]+)건/)||['','0'])[1]")
    return int(str(total).replace(",", "") or 0), t.js(_PARSE) or []


# ───────────────────────── 상세 ─────────────────────────
_KEYS = ["제시금액", "배송비", "제주 추가배송비", "묶음배송여부", "납품가능(용역완료)기간", "배송가능지역",
         "제조사 / 원산지", "모델명 / 규격", "견적서 유효기간", "공급업체명"]


def detail(t: Tab, item_id: str) -> dict:
    t.goto(DETAIL_URL.format(item_id), 1.5)
    lines = [re.sub(r"\s+", " ", x).strip() for x in (t.js("document.body.innerText") or "").split("\n")]
    lines = [x for x in lines if x]
    out = {"id": item_id}
    for i, line in enumerate(lines):
        if "HOME > 견적정보" in line and i + 2 < len(lines):
            out["분류"], out["물품명"] = lines[i + 1], lines[i + 2].replace(item_id, "").strip()
        if "만족도 평가점수" in line:
            out["계약이행신뢰도"] = " ".join(lines[i + 1:i + 3])
        for k in _KEYS:
            if line.startswith(k) and k not in out:
                v = line[len(k):].strip(" :")
                if (not v or k == "제시금액") and i + 1 < len(lines):
                    v = lines[i + 1]
                out[k] = v
    return out


# ───────────────────────── 견적서 담기 ─────────────────────────
_ADD = r"""(async (qty)=>{
  const msgs=[]; window.alert=m=>msgs.push('alert:'+m); window.confirm=m=>{msgs.push('confirm:'+m);return true};
  window.open=()=>null; const form=document.rema100Form; let posted=null;
  form.submit=function(){ posted=new URLSearchParams(new FormData(form)).toString(); };
  document.querySelector('#qnt').value=String(qty); fnSave();
  if(!posted) return {ok:false,msgs};
  const r=await fetch(form.action,{method:'POST',headers:{'Content-Type':'application/x-www-form-urlencoded'},body:posted,credentials:'include'});
  return {ok:r.ok,status:r.status,msgs};
})"""


def add(t: Tab, item_id: str, qty: int) -> dict:
    t.goto(DETAIL_URL.format(item_id), 1.5)
    if not t.js("!!document.querySelector('#qnt') && typeof fnSave==='function'"):
        return {"ok": False, "msgs": ["상세 페이지에 수량칸/fnSave 가 없음(로그인 확인)"]}
    return t.js(_ADD + f"({int(qty)})")


# ───────────────────────── 견적서 접수목록 ─────────────────────────
def cart(t: Tab) -> list[dict]:
    t.goto(CART_URL, 2)
    rows = t.js(r"""(()=>{const o=[];document.querySelectorAll('input.input_check').forEach(c=>{try{o.push(JSON.parse(c.value))}catch(e){}});return o})()""") or []
    return [r for r in rows if r.get("rc_estimate_code")]


def delete(t: Tab, rc_codes: list[str]) -> dict:
    """견적접수코드(rc_estimate_code)로 골라 '선택삭제'. 수의시담 중·에듀파인 연계 물품은 사이트가 거부한다."""
    t.goto(CART_URL, 2)
    r = t.js(r"""((codes)=>{const msgs=[];window.confirm=m=>{msgs.push(m);return true};window.alert=m=>msgs.push('alert:'+m);
      document.querySelectorAll('input[type=checkbox]').forEach(c=>c.checked=false);let n=0;
      document.querySelectorAll('input.input_check').forEach(c=>{try{const v=JSON.parse(c.value);if(codes.indexOf(v.rc_estimate_code)>=0){c.checked=true;n++}}catch(e){}});
      if(n!==codes.length) return {n,msgs,aborted:true};
      estimateSelDelete(); return {n,msgs}})(%s)""" % json.dumps(rc_codes), await_promise=False)
    time.sleep(3)
    t.wait_ready(1)
    return r


# ───────────────────────── 에듀파인 연계 엑셀 ─────────────────────────
def edufine_xls(t: Tab, rc_codes: list[str], out: Path) -> Path:
    """[내용, 규격, 수량, 예상단가, 물품번호] 양식 .xls (에듀파인 품의 품목 [파일 ⇧] 업로드용)."""
    if "s2b.kr" not in (t.js("location.href") or ""):
        t.goto(CART_URL, 2)
    b64 = t.js(r"""(async()=>{const r=await fetch('/S2BNCustomer/remc100.do',{method:'POST',headers:{'Content-Type':'application/x-www-form-urlencoded'},
      body:new URLSearchParams({f_rc_estimate_code:%s,f_sep:'1',forwardName:'estimateEdufine'}),credentials:'include'});
      const b=new Uint8Array(await r.arrayBuffer());let s='';for(let i=0;i<b.length;i++)s+=String.fromCharCode(b[i]);return btoa(s)})()"""
               % json.dumps(",".join(rc_codes)))
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(base64.b64decode(b64))
    return out


# ───────────────────────── CLI ─────────────────────────
def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("login")
    s = sub.add_parser("search"); s.add_argument("queries", nargs="+"); s.add_argument("--local", action="store_true"); s.add_argument("--top", type=int, default=15)
    d = sub.add_parser("detail"); d.add_argument("ids", nargs="+")
    a = sub.add_parser("add"); a.add_argument("items", nargs="+", help="물품번호:수량")
    sub.add_parser("cart")
    x = sub.add_parser("delete"); x.add_argument("rc_codes", nargs="+")
    e = sub.add_parser("edufine-xls"); e.add_argument("rc_codes", help="쉼표로 구분"); e.add_argument("out", nargs="?")
    args = ap.parse_args()

    t = tab()
    if args.cmd == "login":
        print("로그인 상태:", login(t))
        return
    if not login(t):
        raise SystemExit("S2B 로그인 실패")
    if args.cmd == "search":
        for q in args.queries:
            total, rows = search(t, q, nationwide=not args.local)
            print(f"\n### {q}  (총 {total}건, {'우리지역' if args.local else '전국'}, 낮은 금액순)")
            for r in rows[:args.top]:
                print(f"{r['price']:>9,} | {r['id']} | {r['name'][:40]} | {r['spec'][:50]} | {r['vendor'][:12]} | {r['region']} | {r['ship']}")
    elif args.cmd == "detail":
        for i in args.ids:
            print(json.dumps(detail(t, i), ensure_ascii=False))
    elif args.cmd == "add":
        for it in args.items:
            iid, qty = it.split(":")
            print(iid, qty, add(t, iid, int(qty)))
        print("※ 배송비가 붙었는지 cart 로 확인하세요.")
    elif args.cmd == "cart":
        for v in cart(t):
            print(f"{v['rc_estimate_code']} | {v['re_estimate_code']} | {v['goods_name'][:30]} | {v['estimate_quantity']} × {int(v['estimate_amt']):,}"
                  f" = {int(v['estimate_price']):,} (배송비 {v.get('delivery_fee', '?')}) | {v['company_name_b']} | 유효 {v.get('estimate_validate_dt', '')}")
    elif args.cmd == "delete":
        print(delete(t, args.rc_codes))
    elif args.cmd == "edufine-xls":
        out = Path(args.out) if args.out else data_dir("admin-s2b-buyer") / "result" / f"{time.strftime('%Y%m%d_%H%M%S')}_에듀파인연계.xls"
        print("저장:", edufine_xls(t, args.rc_codes.split(","), out))


if __name__ == "__main__":
    main()
