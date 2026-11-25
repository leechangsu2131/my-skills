# -*- coding: utf-8 -*-
"""K-에듀파인 학교회계 품의 — 예산 잔액 조회, 품의 목록 조회, 품의 작성·저장 (사용자 Chrome 9222, 내 탭 하나).

업무포털에 로그인된 Chrome 에 에듀파인 탭을 백그라운드로 새로 열어 넥사크로 객체를 직접 다룬다.
사람이 쓰는 에듀파인 탭은 건드리지 않는다. [결재요청]은 하지 않는다(저장 뒤 뜨는 "결재요청 하시겠습니까?"는 취소).

사용 예:
    python edufine_poomui_cdp.py budgets                       # 내 예산 산출내역별 현액·잔액 (읽기만)
    python edufine_poomui_cdp.py list --from 20260101 [--kw 키워드]   # 품의 목록 + 개요(관련 문서번호 찾기)
    python edufine_poomui_cdp.py fill plan.json                # 품의등록 화면에 채우기만 (저장 안 함)
    python edufine_poomui_cdp.py fill plan.json --save         # 채우고 [저장] → 품의번호 출력

plan.json 형식 (예산은 예산선택 창의 산출내역(cptBasisCn) 이름 그대로):
{
  "title": "2026학년도 ○○ 물품 구입",
  "summary": "1. 관련: ○○-1234(2026. 3. 13.)\\n2. ...  끝.",
  "budgets": ["[추가]공모동아리(○○)", "○○운영비"],
  "items": [
    {"budget": 0, "name": "물품명", "spec": "규격", "qty": 1, "unit": "대", "price": 540000, "s2b": "2023...", "rm": "S2B 판매처"},
    {"budget": 1, "name": "배송비(○○)", "spec": "", "qty": 1, "unit": "식", "price": 4000}
  ]
}
  - budget: budgets 목록의 순번(0부터). 한 품의에 예산 여러 개를 쓰면 품목마다 어느 예산인지 정한다.
  - unit: 개·대·식·세트(SET)·조·벌 등 에듀파인 단위 이름.
  - 소요예산이 예산별 잔액을 넘으면 저장 전에 멈춘다.

확인된 내부 구조 (ISSUES.md 2026-11-25):
  - 예산선택 팝업 FADMANGEXCN004P01 의 dsMain 에서 choise=1 → btnCnfirm_onclick → dsBgtDtlList 바인딩
  - 품목 dsPrdlstDtlList 는 선택한 예산 행으로 filter 된다. dsBgtDtlList.set_rowposition(i) 후
    divAuth2.btnRowAdit.click() 하면 그 예산의 코드(detlBsnsCd·aebgtSn 등)가 든 행이 생긴다.
  - fnExpectAmtCreat() 로 예산별 요구액(dmndAmt) 동기화, fnSaveExpdCnsulWrtgList() 로 저장.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(next(p / "_shared" for p in Path(__file__).resolve().parents if (p / "_shared" / "skill_env.py").is_file())))
from skill_env import data_dir  # noqa: E402
from cdp_tab import Tab  # noqa: E402

MAIN_URL = "https://klef.gbe.kr/keris_ui/main.do"
MENU_REG = "A00FAA0104001001"   # 학교회계 > 품의등록
MENU_LIST = "A00FAA0104001002"  # 학교회계 > 품의목록
APP = "var app=window._pApplication||window._application;var mf=app.mainframe;var SH=mf.MainVFrameSet.SubHFrameSet;"


class Edufine:
    def __init__(self):
        self.t = Tab.open_or_new(data_dir("admin-edufine") / "cdp_tab_id.txt", MAIN_URL, "klef.gbe.kr")
        for _ in range(30):
            try:
                if self.t.js("!!((window._pApplication||window._application)||{}).mainframe", await_promise=False):
                    break
            except Exception:
                pass
            time.sleep(1)
        else:
            raise SystemExit("에듀파인 앱이 뜨지 않습니다. 업무포털 로그인 상태를 확인하세요.")
        time.sleep(2)

    def run(self, body: str, timeout: float = 60):
        return self.t.js("(function(){" + APP + body + "})()", await_promise=False, timeout=timeout)

    def kill_popups(self):
        return self.run("""var n=0;try{var m=SH.MainFrame;for(var k in m){if(/^noticePopup/.test(k)&&m[k]&&m[k].destroy){m[k].destroy();n++}}}catch(e){}
          try{var pf=nexacro.getPopupFrames();for(var i=pf.length-1;i>=0;i--){if(/notice/i.test(pf[i].name)){pf[i].form.close();n++}}}catch(e){}return n;""")

    def to_school_accounting(self):
        self.kill_popups()
        r = self.run("""var top=mf.MainVFrameSet.TopFrame;var c=top.form.cboJobList;if(c.value!='A00FA'){c.set_value('A00FA');
          top.form.cboJobList_onitemchanged(c,new nexacro.ItemChangeEventInfo(c,'onitemchanged',0,0,0,'A00FA'));return 'switched'}return 'already';""")
        if r == "switched":
            time.sleep(4)
            self.kill_popups()

    def open_window(self, menu_id: str) -> str:
        self.to_school_accounting()
        before = set(self.windows())
        self.run(f"SH.LeftFrame.form.gfnOpenMenu('{menu_id}');return 1;")
        for _ in range(20):
            time.sleep(1)
            ws = [w for w in self.windows() if menu_id in w]
            new = [w for w in ws if w not in before]
            if new or ws:
                time.sleep(2)
                return (new or ws)[-1]
        raise RuntimeError("메뉴 창이 열리지 않음: " + menu_id)

    def windows(self) -> list[str]:
        return self.run("var wf=SH.WorkVFrameSet.WorkFrame;var o=[];for(var k in wf){if(/^winId_/.test(k))o.push(k)}return o;") or []

    def W(self, win: str) -> str:
        return "var w=SH.WorkVFrameSet.WorkFrame['%s'];var f=w.form.divWork.form;" % win

    # ── 예산 잔액 ──
    def budgets(self) -> list[dict]:
        win = self.open_window(MENU_REG)
        self.run(self.W(win) + "f.divAuth1.form.btnBgtDtl.click();return 1;")
        time.sleep(4)
        rows = self.run(r"""var p=nexacro.getPopupFrames()['FADMANGEXCN004P01'];if(!p)return null;var d=p.form.dsMain;var o=[];
          function v(x){return x&&x.hi!==undefined?x.hi:x}
          for(var r=0;r<d.rowcount;r++){if(!d.getColumn(r,'cptBasisCn'))continue;o.push({부서:d.getColumn(r,'sclDeptNm'),세부사업:d.getColumn(r,'sclDetlBsnsNm'),
            세부항목:d.getColumn(r,'detlIemNm'),산출내역:d.getColumn(r,'cptBasisCn'),원가비목:d.getColumn(r,'prmpcStatsExpitmNm'),
            현액:v(d.getColumn(r,'bgtCrntam')),잔액:v(d.getColumn(r,'bgtBlce'))})}
          p.form.close();return o;""")
        return rows or []

    # ── 품의 목록 ──
    def cnsul_list(self, begin: str) -> list[dict]:
        win = self.open_window(MENU_LIST)
        self.run(self.W(win) + f"f.divSearch.form.calCnsulBeginDte.set_value('{begin}');f.divAuth.form.btnAuthS01.click();return 1;")
        time.sleep(4)
        return self.run(self.W(win) + r"""var d=f.grdMain.getBindDataset();var o=[];function v(x){return x&&x.hi!==undefined?x.hi:x}
          for(var r=0;r<d.rowcount;r++)o.push({일자:d.getColumn(r,'cnsulDte'),품의번호:d.getColumn(r,'sclCnsulNo'),제목:d.getColumn(r,'sj'),
            세부사업:d.getColumn(r,'detlBsnsNm'),금액:v(d.getColumn(r,'cnsulAmt')),상태:d.getColumn(r,'sclExpdStsSeNm'),개요:d.getColumn(r,'cnsulPurpsCn')});return o;""") or []

    # ── 품의 작성 ──
    def fill(self, plan: dict, save: bool = False) -> dict:
        win = self.open_window(MENU_REG)
        W = self.W(win)
        # 1) 예산 선택
        self.run(W + "f.divAuth1.form.btnBgtDtl.click();return 1;")
        time.sleep(4)
        sel = self.run(r"""var names=%s;var p=nexacro.getPopupFrames()['FADMANGEXCN004P01'];if(!p)return {err:'예산선택 창 없음'};
          var d=p.form.dsMain;var hit={};for(var r=0;r<d.rowcount;r++){var c=d.getColumn(r,'cptBasisCn');if(names.indexOf(c)>=0&&hit[c]===undefined){hit[c]=r}}
          var miss=names.filter(function(n){return hit[n]===undefined});if(miss.length){p.form.close();return {err:'예산 없음: '+miss.join(', ')}}
          names.forEach(function(n){d.setColumn(hit[n],'choise','1')});p.form.btnCnfirm_onclick.call(p.form,p.form.btnCnfirm,{});return {ok:true};"""
                       % json.dumps(plan["budgets"], ensure_ascii=False))
        if not sel or sel.get("err"):
            raise SystemExit(f"예산 선택 실패: {sel}")
        time.sleep(3)
        # 2) 품목 + 제목·개요
        res = self.run(W + r"""var plan=%s;var b=f.grdBgtDtl.getBindDataset();var d=f.grdPrdlstDtl.getBindDataset();
          var names=plan.budgets;var idx={};for(var i=0;i<b.rowcount;i++)idx[b.getColumn(i,'cptDtl')]=i;
          var uds=w.form.dsEAB0005200||f.dsEAB0005200;var unit={};if(uds){for(var i=0;i<uds.rowcount;i++)unit[uds.getColumn(i,'cmmnDetailCdNm')]=uds.getColumn(i,'cmmnDetailCd')}
          var log=[];var fs0=d.filterstr;d.filter('');for(var r=d.rowcount-1;r>=0;r--){if(!d.getColumn(r,'prdlstCn'))d.deleteRow(r)}d.filter(fs0);
          plan.items.forEach(function(it){var bi=idx[names[it.budget]];if(bi===undefined){log.push('예산행 없음 '+it.name);return}
            b.set_rowposition(bi);var before=d.rowcount;f.divAuth2.form.btnRowAdit.click();if(d.rowcount!=before+1){log.push('행추가 실패 '+it.name);return}
            var r=d.rowcount-1;var u=unit[it.unit]||it.unit||'001';
            d.setColumn(r,'prdlstCn',it.name);d.setColumn(r,'stndrd',it.spec||'');d.setColumn(r,'qty',it.qty);d.setColumn(r,'thngUnitSeCd',u);
            d.setColumn(r,'expectUntpc',it.price);d.setColumn(r,'expectAmt',it.qty*it.price);if(it.s2b)d.setColumn(r,'s2bThngNo',it.s2b);if(it.rm)d.setColumn(r,'rm',it.rm);
            log.push(names[it.budget]+' | '+it.name+' | '+it.qty+' x '+it.price);});
          f.fnExpectAmtCreat();var m=f.divMain.form;m.edtCnsulSj.set_value(plan.title);m.txtareaCnsulSumrCn.set_value(plan.summary);
          function v(x){return x&&x.hi!==undefined?x.hi:Number(x)}var bg=[];var over=[];
          for(var i=0;i<b.rowcount;i++){var dm=v(b.getColumn(i,'dmndAmt')),bl=v(b.getColumn(i,'bgtBlce'));bg.push(b.getColumn(i,'cptDtl')+': 요구 '+dm+' / 잔액 '+bl);if(dm>bl)over.push(b.getColumn(i,'cptDtl'))}
          return {log:log,budgets:bg,over:over};""" % json.dumps(plan, ensure_ascii=False))
        if res.get("over"):
            raise SystemExit(f"예산 잔액 초과: {res}")
        if not save:
            res["saved"] = False
            return res
        # 3) 저장 (확인창 자동 승인, 저장 뒤 '결재요청 하시겠습니까?'는 취소)
        self.run(W + r"""window.__efMsgs=[];f.gfnConfirm=function(){window.__efMsgs.push('confirm:'+[].slice.call(arguments).join('|'));return true};
          f.fnSaveExpdCnsulWrtgList();return 1;""")
        time.sleep(5)
        self.run(r"""var p=nexacro.getPopupFrames()['sanctnRequst'];if(p&&p.form.btnCancle)p.form.btnCancle.click();return 1;""")
        time.sleep(1)
        res.update(self.run(W + "var m=f.divMain.form;return {saved:true,품의번호:m.edtCnsulNo.value,상태:m.edtProgrsSts.value,msgs:window.__efMsgs};"))
        return res


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("budgets")
    ls = sub.add_parser("list"); ls.add_argument("--from", dest="begin", default=time.strftime("%Y") + "0101"); ls.add_argument("--kw", default="")
    fl = sub.add_parser("fill"); fl.add_argument("plan"); fl.add_argument("--save", action="store_true")
    args = ap.parse_args()
    ef = Edufine()
    if args.cmd == "budgets":
        for b in ef.budgets():
            print(f"{b['부서']} | {b['세부사업']} | {b['세부항목']} | {b['산출내역']} | {b['원가비목']} | 현액 {b['현액']:,} | 잔액 {b['잔액']:,}")
    elif args.cmd == "list":
        for r in ef.cnsul_list(args.begin):
            if args.kw and args.kw not in (r["제목"] or "") + (r["개요"] or ""):
                continue
            print(f"\n{r['일자']} | {r['품의번호']} | {r['제목']} | {r['세부사업']} | {r['금액']:,} | {r['상태']}")
            if args.kw:
                print(r["개요"])
    elif args.cmd == "fill":
        plan = json.loads(Path(args.plan).read_text(encoding="utf-8"))
        print(json.dumps(ef.fill(plan, save=args.save), ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
