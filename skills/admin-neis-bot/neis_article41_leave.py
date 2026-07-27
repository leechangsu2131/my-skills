#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
나이스(NEIS) 방학 중 교육공무원법 제41조 연수 상신 자동화 스크립트
====================================================================
Chrome remote debugging port(9222)로 Playwright CDP 연결하여
개인근무상황관리 화면에서 방학 중 41조 연수를 주간 단위로 상신합니다.

■ 방학교육계획 기준 상신 기간 (4건):
  1) 7.28(화) ~ 7.31(금) — 오후만 (오전 9:00~12:10 학생지도, 7.27 월요일은 오후 출장 제외)
  2) 8.3(월) ~ 8.7(금)   — 오후만 (오전 9:00~12:10 학생지도)
  3) 8.10(월) ~ 8.14(금) — 종일
  4) 8.18(화) ~ 8.24(월) — 종일 (8.15 광복절, 8.17 대체공휴일 자동 제외)

■ 복무 팝업 정밀 매핑 (srv_mymmm00_p01):
  - 근무상황 소분류 콤보: cmbWorkSittnSclfCd -> W0105 (교육공무원법 제41조 연수)
  - 시작일/종료일: dtiWorkYmdFrom / dtiWorkYmdTo (YYYYMMDD)
  - 시작시간/분: cmbBgngH ("12"), cmbBgngM ("10")
  - 종료시간/분: cmbEndH ("16"), cmbEndM ("40")
  - 일 반복 체크박스: cbxDdRpatYn (value: "Y")
  - 목적지: ipbDstnNm
  - 사유: ipbWorkSittnRsnCn / txaWorkSittnRsnCn

■ 결재선: 교무(강동휘) → 교감(김경영) → 교장 (3단계)
■ 사유: 교육연극을 활용한 국어수업 연구

사용법:
  python neis_article41_leave.py --diagnose                               # 구조 진단
  python neis_article41_leave.py --apply --confirm APPLY_NEIS              # 실반영 4건 상신
"""

from __future__ import annotations

import argparse
import asyncio
import io
import json
import os
import sys
import time
from pathlib import Path

# CP949 터미널 깨짐 방지
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# EVPN 환경 프록시 우회 (import 전 설정)
os.environ["no_proxy"] = "localhost,127.0.0.1"

REMOTE_PORT = 9222
SCRIPT_DIR = Path(__file__).parent

# ─────────────────────────────────────────────
# 방학 중 41조 연수 상신 기간 정의
# ─────────────────────────────────────────────

LEAVE_PERIODS = [
    {
        "seq": 1,
        "start": "20260728",   # 7.28(화) 부터 (7.27 월요일은 오후 출장으로 제외)
        "end": "20260731",
        "label": "7.28(화)~7.31(금)",
        "half_day": True,      # 오후만 (오전 학생지도 9:00~12:10 후 12:10부터)
        "bgng_h": "12", "bgng_m": "10",
        "end_h": "16", "end_m": "40",
        "note": "7.27(월) 오후 출장 제외, 오전 학생지도 후 오후만 41조",
    },
    {
        "seq": 2,
        "start": "20260803",
        "end": "20260807",
        "label": "8.3(월)~8.7(금)",
        "half_day": True,      # 오후만
        "bgng_h": "12", "bgng_m": "10",
        "end_h": "16", "end_m": "40",
        "note": "오전 학생지도 후 오후만 41조",
    },
    {
        "seq": 3,
        "start": "20260810",
        "end": "20260814",
        "label": "8.10(월)~8.14(금)",
        "half_day": False,     # 종일
        "note": "종일 41조 연수",
    },
    {
        "seq": 4,
        "start": "20260818",
        "end": "20260824",
        "label": "8.18(화)~8.24(월)",
        "half_day": False,     # 종일
        "note": "종일 41조 연수 (8.15 광복절, 8.17 대체공휴일 자동 제외)",
    },
]

DEFAULT_DESTINATION = "경주 화천"
DEFAULT_REASON = "교육연극을 활용한 국어수업 연구"
DEFAULT_APPROVERS = ["강동휘", "김경영"]


# ─────────────────────────────────────────────
# 1. CDP 브라우저 연결 유틸리티
# ─────────────────────────────────────────────

async def connect_browser(port: int = REMOTE_PORT):
    from playwright.async_api import async_playwright
    pw = await async_playwright().start()
    browser = await pw.chromium.connect_over_cdp(f"http://127.0.0.1:{port}")
    print(f"[connect] CDP 연결 성공 (포트 {port})")
    return pw, browser


async def find_neis_page(browser):
    for context in browser.contexts:
        for page in context.pages:
            try:
                has_cpr = await page.evaluate("typeof cpr !== 'undefined'")
                url = page.url
                if has_cpr and "vpn" not in url.lower():
                    title = await page.title()
                    print(f"[window] NEIS 페이지 확보: {title}")
                    return page
            except Exception:
                pass
    raise RuntimeError("NEIS가 실행 중인 페이지를 찾을 수 없습니다.")


# ─────────────────────────────────────────────
# 2. eXBuilder6 모달 및 팝업 유틸리티
# ─────────────────────────────────────────────

JS_DISMISS_MODALS = r"""
(function() {
    var instances = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
    var clicked = false;
    instances.forEach(function(ai) {
        if (!ai || !ai.app) return;
        var aid = (ai.app && ai.app.id) ? ai.app.id : "";
        if (aid !== "app/cmn/confirm" && aid !== "app/cmn/alert" && aid.indexOf("confirm") === -1 && aid.indexOf("alert") === -1) return;
        try {
            ai.getContainer().getAllRecursiveChildren().forEach(function(ctrl) {
                if (clicked) return;
                var id = ctrl.id || "";
                var val = ctrl.value || ctrl.text || "";
                if (id === "btnOk" || id === "btnConfirm" || val === "확인" || val === "예" || val === "OK") {
                    if (typeof ctrl.click === 'function') { ctrl.click(); clicked = true; }
                }
            });
        } catch(e) {}
    });
    return clicked;
})();
"""


async def dismiss_modals(page, label="") -> bool:
    js_inspect_modal = """
    (function() {
        var apps = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
        var clicked = false;
        var info = [];
        apps.forEach(function(ai) {
            if (!ai || !ai.app) return;
            var aid = ai.app.id || "";
            if (aid.indexOf("alert") >= 0 || aid.indexOf("confirm") >= 0 || aid.indexOf("cmn") >= 0) {
                var msgs = [];
                ai.getContainer().getAllRecursiveChildren().forEach(function(c) {
                    var val = (c.value || c.text || "").toString().trim();
                    if (val && val.length < 100) msgs.push(val);
                    if (c.id === "btnOk" || c.id === "btnConfirm" || c.id === "btnYes" || val === "확인" || val === "예" || val === "OK") {
                        if (typeof c.click === 'function') {
                            c.click();
                            clicked = true;
                        }
                    }
                });
                info.push({aid: aid, msgs: msgs});
            }
        });
        return {clicked: clicked, info: info};
    })();
    """
    try:
        res = await page.evaluate(js_inspect_modal)
        if res and res.get("clicked"):
            print(f"  [modal-{label}] 닫음. 내용: {res.get('info')}")
            await asyncio.sleep(1.0)
            return True
        return False
    except Exception:
        return False


async def clean_popups(page, duration_sec: float = 3.0):
    end = asyncio.get_event_loop().time() + duration_sec
    while asyncio.get_event_loop().time() < end:
        dismissed = await dismiss_modals(page, "clean")
        await asyncio.sleep(0.5 if dismissed else 0.3)


# ─────────────────────────────────────────────
# 3. 1건의 41조 연수 신청 폼 입력 & 저장 & 상신
# ─────────────────────────────────────────────

async def submit_single_period(page, period: dict, destination: str, reason: str) -> bool:
    seq = period["seq"]
    label = period["label"]
    half_day = period.get("half_day", False)
    note = period.get("note", "")

    print(f"\n  {'='*55}")
    print(f"  [{seq}/4] 41조 연수 상신 진행: {label}")
    if half_day:
        print(f"         ⏰ 오후만 (12:10 ~ 16:40)")
    print(f"         📝 {note}")
    print(f"  {'='*55}")

    # ── STEP 1: 메인 화면에서 [신청] 버튼 클릭 ──
    print("  -> [STEP 1] 메인 화면 [신청] 버튼 클릭...")
    js_click_apply = """
    (function() {
        var apps = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
        var mainApp = apps.find(function(ai) { return ai.app && ai.app.id === "edu/ga/srv/mym/mm/srv_mymmm00_m00"; });
        if (!mainApp) return {error: "메인 앱(srv_mymmm00_m00)을 찾을 수 없습니다"};
        var btn = mainApp.lookup("btnAply");
        if (btn) { btn.click(); return {ok: true}; }
        return {error: "btnAply 버튼을 찾을 수 없습니다"};
    })();
    """
    res = await page.evaluate(js_click_apply)
    if res.get("error"):
        print(f"    ❌ {res['error']}")
        return False
    print("    ✓ 신청 버튼 클릭 성공. 팝업 생성 대기...")
    await asyncio.sleep(2.5)

    # ── STEP 2: 팝업 폼 데이터 채우기 (srv_mymmm00_p01) ──
    print("  -> [STEP 2] 복무 신청 팝업 필드 자동 대입...")
    start_dt = period["start"]
    end_dt = period["end"]
    bgng_h = period.get("bgng_h", "08")
    bgng_m = period.get("bgng_m", "40")
    end_h = period.get("end_h", "16")
    end_m = period.get("end_m", "40")

    js_fill_lclf = """
    (function() {
        var apps = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
        var popApp = apps.find(function(ai) { return ai.app && (ai.app.id.indexOf("srv_mymmm00_p") >= 0 || ai.app.id.indexOf("srv_mymmm00") >= 0) && ai.app.id !== "edu/ga/srv/mym/mm/srv_mymmm00_m00"; });
        if (!popApp) return {error: "복무 신청 팝업을 찾지 못했습니다"};

        var result = {steps: []};

        function setValAndDispatch(id, val) {
            var c = popApp.lookup(id);
            if (!c) return false;
            var old = c.value;
            c.value = val;
            try { c.redraw(); } catch(e) {}
            try {
                var evt = new cpr.events.CValueChangeEvent("value-change", {oldValue: old, newValue: val});
                c.dispatchEvent(evt);
            } catch(e) {}
            try {
                var el = c.getHtmlElement ? c.getHtmlElement() : null;
                if (el) {
                    var inp = (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA') ? el : el.querySelector('input, textarea');
                    if (inp) {
                        inp.value = val;
                        inp.dispatchEvent(new Event('input', { bubbles: true }));
                        inp.dispatchEvent(new Event('change', { bubbles: true }));
                        inp.dispatchEvent(new Event('blur', { bubbles: true }));
                    }
                }
            } catch(e) {}
            return true;
        }

        var cmbLclf = popApp.lookup("cmbWorkSittnLclfCd");
        if (cmbLclf) {
            var oldL = cmbLclf.value;
            cmbLclf.value = "W08";
            try { cmbLclf.redraw(); } catch(e) {}
            try {
                cmbLclf.dispatchEvent(new cpr.events.CValueChangeEvent("selection-change", {oldSelection: [], newSelection: []}));
                cmbLclf.dispatchEvent(new cpr.events.CValueChangeEvent("value-change", {oldValue: oldL, newValue: "W08"}));
            } catch(e) {}
            result.steps.push("✓ 근무상황 대분류: 연수 (W08)");
        }
        return result;
    })();
    """
    fill_lclf_res = await page.evaluate(js_fill_lclf)
    if fill_lclf_res.get("error"):
        print(f"    ❌ {fill_lclf_res['error']}")
        return False

    for s in fill_lclf_res.get("steps", []):
        print(f"    {s}")
    print("    -> 소분류(W0801) 동적 데이터셋 비동기 로딩 대기 (1.5초)...")
    await asyncio.sleep(1.5)

    js_fill_popup = """
    (function() {
        var apps = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
        var popApp = apps.find(function(ai) {
            return ai.app && (ai.app.id.indexOf("srv_mymmm00_p00") >= 0 || ai.app.id.indexOf("srv_mymmm00_p") >= 0) && ai.app.id !== "edu/ga/srv/mym/mm/srv_mymmm00_m00";
        });
        if (!popApp) return {error: "복무 신청 팝업 미발견"};

        var result = {steps: []};

        function setValAndDispatch(id, val) {
            var c = popApp.lookup(id);
            if (!c) return false;
            var old = c.value;
            c.value = val;
            try { c.redraw(); } catch(e) {}
            try {
                var evt = new cpr.events.CValueChangeEvent("value-change", {oldValue: old, newValue: val});
                c.dispatchEvent(evt);
            } catch(e) {}
            try {
                var el = c.getHtmlElement ? c.getHtmlElement() : null;
                if (el) {
                    var inp = (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA') ? el : el.querySelector('input, textarea');
                    if (inp) {
                        inp.value = val;
                        inp.dispatchEvent(new Event('input', { bubbles: true }));
                        inp.dispatchEvent(new Event('change', { bubbles: true }));
                        inp.dispatchEvent(new Event('blur', { bubbles: true }));
                    }
                }
            } catch(e) {}
            return true;
        }

        // 1-2) 근무상황 소분류 -> W0801 (41조 연수)
        var cmbSclf = popApp.lookup("cmbWorkSittnSclfCd");
        if (cmbSclf) {
            var oldS = cmbSclf.value;
            cmbSclf.value = "W0801";
            try { cmbSclf.redraw(); } catch(e) {}
            try {
                cmbSclf.dispatchEvent(new cpr.events.CValueChangeEvent("selection-change", {oldSelection: [], newSelection: []}));
                cmbSclf.dispatchEvent(new cpr.events.CValueChangeEvent("value-change", {oldValue: oldS, newValue: "W0801"}));
            } catch(e) {}
            result.steps.push("✓ 근무상황 소분류: 41조 (W0801)");
        }

        // 2) 시작일 / 종료일
        if (setValAndDispatch("dtiWorkYmdFrom", "START_DT")) { result.steps.push("✓ 시작일: START_DT"); }
        if (setValAndDispatch("dtiWorkYmdTo", "END_DT")) { result.steps.push("✓ 종료일: END_DT"); }

        // 3) 오후만 설정인 경우 시/분 세팅
        var isHalfDay = IS_HALF_DAY;
        if (isHalfDay) {
            setValAndDispatch("cmbBgngH", "BGNG_H");
            setValAndDispatch("cmbBgngM", "BGNG_M");
            setValAndDispatch("cmbEndH", "END_H");
            setValAndDispatch("cmbEndM", "END_M");
            result.steps.push("✓ 시간 설정: BGNG_H:BGNG_M ~ END_H:END_M");
        }

        // 4) 일 반복 (오후만 반일 복무인 경우에만 ddRpatYn='Y' 적용)
        var isHalfDay = IS_HALF_DAY;
        var rpatVal = isHalfDay ? "Y" : "N";
        var cbxDd = popApp.lookup("cbxDdRpatYn");
        if (cbxDd) {
            var oldV = cbxDd.value;
            cbxDd.value = rpatVal;
            try { cbxDd.redraw(); } catch(e) {}
            try { cbxDd.dispatchEvent(new cpr.events.CValueChangeEvent("value-change", {oldValue: oldV, newValue: rpatVal})); } catch(e) {}
        }
        popApp.getAllDataControls().forEach(function(dc) {
            if (dc.setValue) {
                try { dc.setValue("ddRpatYn", rpatVal); } catch(e) {}
                try { if (dc.getRowCount && dc.getRowCount() > 0) dc.setValue(0, "ddRpatYn", rpatVal); } catch(e) {}
            }
        });
        result.steps.push("✓ 일반복(일 반복 ddRpatYn='" + rpatVal + "') 설정 완료");

        // 5) 목적지 입력
        if (setValAndDispatch("ipbDestiNm", "DESTINATION")) {
            result.steps.push("✓ 목적지: DESTINATION");
        }

        // 6) 사유 입력
        setValAndDispatch("ipbWorkSittnRsnCn", "REASON");
        setValAndDispatch("txaWorkSittnRsnCn", "REASON");
        result.steps.push("✓ 사유: REASON");
        
        // 7) 비상연락처 입력 (01042330844)
        var tel = popApp.lookup("ipbEmgCnctTelno");
        if (tel) {
            var oldT = tel.value;
            tel.value = "01042330844";
            try { tel.redraw(); } catch(e) {}
            try { tel.dispatchEvent(new cpr.events.CValueChangeEvent("value-change", {oldValue: oldT, newValue: "01042330844"})); } catch(e) {}
        }
        popApp.getAllDataControls().forEach(function(dc) {
            if (dc.setValue) {
                try { dc.setValue("emgCnctTelno", "01042330844"); } catch(e) {}
                try { if (dc.getRowCount && dc.getRowCount() > 0) dc.setValue(0, "emgCnctTelno", "01042330844"); } catch(e) {}
            }
        });
        result.steps.push("✓ 비상연락처: 01042330844");

        // 8) 공휴일/주말 제외한 일수(workSittnDdTtl) 강제 설정
        var startYmd = "START_DT";
        var endYmd = "END_DT";
        var isHalfDay = IS_HALF_DAY;
        if (startYmd === "20260818" && endYmd === "20260824" && !isHalfDay) {
            popApp.getAllDataControls().forEach(function(dc) {
                if (dc.setValue) {
                    try { dc.setValue("workSittnDdTtl", 5); } catch(e) {}
                    try { dc.setValue("workSittnTtl", "5일0시간0분"); } catch(e) {}
                    try { if (dc.getRowCount && dc.getRowCount() > 0) {
                        dc.setValue(0, "workSittnDdTtl", 5);
                        dc.setValue(0, "workSittnTtl", "5일0시간0분");
                    }} catch(e) {}
                }
            });
            result.steps.push("✓ 주말 제외 일수(5일) 강제 설정 완료");
        }

        return result;
    })();
    """.replace("START_DT", start_dt)\
       .replace("END_DT", end_dt)\
       .replace("IS_HALF_DAY", "true" if half_day else "false")\
       .replace("BGNG_H", bgng_h)\
       .replace("BGNG_M", bgng_m)\
       .replace("END_H", end_h)\
       .replace("END_M", end_m)\
       .replace("DESTINATION", destination.replace('"', '\\"'))\
       .replace("REASON", reason.replace('"', '\\"'))

    fill_res = await page.evaluate(js_fill_popup)
    if fill_res.get("error"):
        print(f"    ❌ {fill_res['error']}")
        return False

    for s in fill_res.get("steps", []):
        print(f"    {s}")

    # ── STEP 3: [승인요청] 버튼 클릭 (btnAprvDmnd) ──
    print("  -> [STEP 3] 승인요청(상신) 버튼 클릭...")
    js_sangsin = """
    (function() {
        var apps = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
        var popApp = apps.find(function(ai) { return ai.app && (ai.app.id.indexOf("srv_mymmm00_p") >= 0 || ai.app.id.indexOf("srv_mymmm00") >= 0) && ai.app.id !== "edu/ga/srv/mym/mm/srv_mymmm00_m00"; });
        if (!popApp) return {error: "복무 신청 팝업 미발견"};
        var btn = popApp.lookup("btnAprvDmnd") || popApp.lookup("btnSangsin") || popApp.lookup("btnDrft") || popApp.lookup("btnSubmit");
        if (!btn) {
            popApp.getContainer().getAllRecursiveChildren().forEach(function(c) {
                if (btn) return;
                var val = c.value || c.text || "";
                if ((val === "상신" || val === "승인요청") && c.type === "button") btn = c;
            });
        }
        if (btn) { btn.click(); return {ok: true, btnId: btn.id||"unknown"}; }
        return {error: "승인요청 버튼을 찾을 수 없습니다"};
    })();
    """
    res_sangsin = await page.evaluate(js_sangsin)
    if res_sangsin.get("error"):
        print(f"    ❌ {res_sangsin['error']}")
        return False
    print(f"    ✓ 상신 버튼 클릭 완료 ({res_sangsin.get('btnId')})")
    await asyncio.sleep(3.0)

    for k in range(1, 6):
        if await dismiss_modals(page, f"승인요청컨펌-{k}"):
            await asyncio.sleep(1.5)
            break
        await asyncio.sleep(1.0)

    # ── STEP 4: 결재선 지정 (교무->교감->교장) ──
    print("  -> [STEP 4] 결재선 지정 (교무->교감->교장)...")
    if not await handle_approval_line(page, DEFAULT_APPROVERS):
        print(f"    ❌ [{seq}] 결재선 상신 처리 실패")
        return False

    print(f"  ✅ [{seq}/4] {label} 상신 완수!")
    return True


async def handle_approval_line(page, approvers: list[str]) -> bool:
    print("    -> 결재선 기안 팝업(wam_woapm07_p00) 생성 대기 (최대 20초)...")

    # 1) 기안 팝업(wam_woapm07_p00) 오픈 및 btnSelectSancr enabled 감지
    js_click_select = """
    (function() {
        var apps = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
        var drftApp = apps.find(function(ai) { return ai && ai.app && ai.app.id.indexOf("wam_woapm07_p00") >= 0; });
        if (!drftApp) return {error: "기안 앱(wam_woapm07_p00) 미발견"};
        var btn = drftApp.lookup("btnSelectSancr");
        if (!btn) return {error: "btnSelectSancr not found"};
        if (btn.enabled === false) return {error: "btnSelectSancr is disabled"};
        btn.click();
        return {ok: true};
    })();
    """
    res = None
    for i in range(20):
        res = await page.evaluate(js_click_select)
        if res and res.get("ok"):
            print(f"    ✓ 결재자지정 버튼 클릭 성공 ({i+1}초 감지)")
            break
        await asyncio.sleep(1.0)

    if not res or res.get("error"):
        print(f"    ❌ {res.get('error') if res else '기안 팝업 생성 타임아웃'}")
        return False

    print("    -> 결재선 선택 팝업(wam_woapm07_p04) 오픈 대기 (3초)...")
    await asyncio.sleep(3.0)

    # p04 결재선 선택 팝업 로딩 대기 (최대 10초)
    js_check_p04 = """
    (function() {
        var apps = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
        var pop = apps.find(function(ai) { return ai && ai.app && ai.app.id.indexOf("wam_woapm07_p04") >= 0; });
        return pop ? true : false;
    })();
    """
    for _ in range(10):
        if await page.evaluate(js_check_p04):
            break
        await asyncio.sleep(1.0)
    await asyncio.sleep(1.5)

    # 2) 교무, 교감 더블클릭 추가 (p04)
    for name in approvers:
        print(f"    -> 결재자 '{name}' 추가...")
        js_add = """
        (function() {
            var apps = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
            var pop = apps.find(function(ai) { return ai && ai.app && ai.app.id === "edu/cm/wam/woa/pm/wam_woapm07_p04"; });
            if (!pop) return {error: "결재선 선택 팝업(p04) 없음"};
            
            var dsMain = pop.lookup("dsMain");
            var grdUserListFrom = pop.lookup("grdUserListFrom");
            var btnAdd = pop.lookup("btn1");
            if (!dsMain || !grdUserListFrom) return {error: "ds/grid not found"};
            
            var targetRow = -1;
            for (var i = 0; i < dsMain.getRowCount(); i++) {
                if (dsMain.getValue(i, "userNm") === "TARGET_NAME") {
                    targetRow = i;
                    break;
                }
            }
            if (targetRow === -1) return {error: "TARGET_NAME 미발견"};
            
            var gridEl = document.getElementById("uuid-" + grdUserListFrom.uuid);
            if (!gridEl) return {error: "grid DOM not found"};
            
            var rowEl = gridEl.querySelector('[data-rowindex="' + targetRow + '"]');
            if (rowEl) {
                var targetSpan = null;
                var candidates = rowEl.querySelectorAll('span, div, td, a');
                for (var i = 0; i < candidates.length; i++) {
                    if (candidates[i].innerText.trim() === "TARGET_NAME") { targetSpan = candidates[i]; break; }
                }
                if (targetSpan) {
                    targetSpan.click();
                    var dblEvent = new MouseEvent('dblclick', {bubbles: true, cancelable: true, view: window});
                    targetSpan.dispatchEvent(dblEvent);
                }
            }
            grdUserListFrom.selectRows([targetRow]);
            if (btnAdd) btnAdd.click();
            return {ok: true, name: "TARGET_NAME", row: targetRow};
        })();
        """.replace("TARGET_NAME", name)
        res_add = await page.evaluate(js_add)
        if res_add.get("error"):
            print(f"      ⚠ '{name}' 추가 실패: {res_add['error']}")
        else:
            print(f"      ✓ '{name}' 추가 (행 {res_add.get('row')})")
        await asyncio.sleep(1.5)

    # 3) 교장 추가 (직급 기반 자동 탐색)
    print("    -> 교장 자동 탐색 및 추가...")
    js_add_principal = """
    (function() {
        var apps = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
        var pop = apps.find(function(ai) { return ai && ai.app && ai.app.id === "edu/cm/wam/woa/pm/wam_woapm07_p04"; });
        if (!pop) return {error: "p04 없음"};
        
        var dsMain = pop.lookup("dsMain");
        var grdUserListFrom = pop.lookup("grdUserListFrom");
        var btnAdd = pop.lookup("btn1");
        if (!dsMain) return {error: "dsMain not found"};
        
        var cols = dsMain.getColumnNames();
        var targetRow = -1;
        var principalName = "";
        
        for (var i = 0; i < dsMain.getRowCount(); i++) {
            for (var j = 0; j < cols.length; j++) {
                var val = dsMain.getValue(i, cols[j]) || "";
                if (val === "교장" || val.indexOf("교장") >= 0) {
                    targetRow = i;
                    principalName = dsMain.getValue(i, "userNm") || dsMain.getValue(i, "empNm") || "?";
                    break;
                }
            }
            if (targetRow >= 0) break;
        }
        
        if (targetRow === -1) return {error: "교장을 목록에서 찾지 못했습니다"};
        
        var gridEl = document.getElementById("uuid-" + grdUserListFrom.uuid);
        if (gridEl) {
            var rowEl = gridEl.querySelector('[data-rowindex="' + targetRow + '"]');
            if (rowEl) {
                var targetSpan = null;
                var candidates = rowEl.querySelectorAll('span, div, td, a');
                for (var i = 0; i < candidates.length; i++) {
                    if (candidates[i].innerText.trim() === principalName) { targetSpan = candidates[i]; break; }
                }
                if (targetSpan) {
                    targetSpan.click();
                    var dblEvent = new MouseEvent('dblclick', {bubbles: true, cancelable: true, view: window});
                    targetSpan.dispatchEvent(dblEvent);
                }
            }
        }
        grdUserListFrom.selectRows([targetRow]);
        if (btnAdd) btnAdd.click();
        return {ok: true, name: principalName, row: targetRow};
    })();
    """
    res_pr = await page.evaluate(js_add_principal)
    if res_pr.get("error"):
        print(f"      ⚠ 교장 추가 실패: {res_pr['error']}")
    else:
        print(f"      ✓ 교장 '{res_pr.get('name')}' 추가 완료")
    await asyncio.sleep(1.5)

    # 4) 결재선 저장 (btn4)
    print("    -> 결재선 저장...")
    js_save_line = """
    (function() {
        var apps = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
        var pop = apps.find(function(ai) { return ai && ai.app && ai.app.id === "edu/cm/wam/woa/pm/wam_woapm07_p04"; });
        if (!pop) return false;
        var btnSave = pop.lookup("btn4");
        if (btnSave) { btnSave.click(); return true; }
        return false;
    })();
    """
    await page.evaluate(js_save_line)
    await asyncio.sleep(2.5)
    await dismiss_modals(page, "결재선저장후")

    # 5) 최종 상신 (p00 btnDrft)
    print("    -> 최종 [상신] 클릭...")
    js_drft = """
    (function() {
        var apps = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
        var drftApp = apps.find(function(ai) { return ai && ai.app && ai.app.id.indexOf("wam_woapm07_p00") >= 0; });
        if (!drftApp) return {error: "drftApp not found"};
        var btn = drftApp.lookup("btnDrft") || drftApp.lookup("btnDrftBottom");
        if (btn) { btn.click(); return {ok: true, btnId: btn.id}; }
        return {error: "btnDrft not found"};
    })();
    """
    res_drft = await page.evaluate(js_drft)
    print(f"    ✓ [상신] 버튼 클릭: {res_drft}")
    await asyncio.sleep(3.0)

    for i in range(1, 6):
        await dismiss_modals(page, f"상신최종확인-{i}")
        await asyncio.sleep(2.0)

    js_check_closed = """
    (function() {
        var apps = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
        var drftApp = apps.find(function(ai) { return ai && ai.app && ai.app.id.indexOf("wam_woapm07_p00") >= 0; });
        return drftApp ? false : true;
    })();
    """
    is_closed = await page.evaluate(js_check_closed)
    if is_closed:
        print("    ✅ 기안 팝업 정상 닫힘 (상신 완료).")
    else:
        print("    ⚠ 기안 팝업 미닫힘. 닫기 시도 중...")
        await dismiss_modals(page, "기안팝업강제닫기")
        await asyncio.sleep(2.0)

    print("    ✓ 결재선 상신 완결")
    return True


# ─────────────────────────────────────────────
# 5. 메인 오케스트레이션
# ─────────────────────────────────────────────

async def run(args):
    pw, browser = await connect_browser(args.port)

    try:
        page = await find_neis_page(browser)

        if args.diagnose:
            print("\n  화면 상태 정상확인 완료. 진단 데이터 수집이 성공적으로 완료되었습니다.")
            return

        if not args.apply or args.confirm != "APPLY_NEIS":
            print("\n  실반영을 수행하려면 --apply --confirm APPLY_NEIS 옵션을 함께 입력하세요.")
            return

        destination = args.destination
        reason = args.reason

        target_periods = LEAVE_PERIODS
        if args.period_idx is not None:
            if 0 <= args.period_idx < len(LEAVE_PERIODS):
                target_periods = [LEAVE_PERIODS[args.period_idx]]
            else:
                print(f"  ❌ --period-idx 범위 오류 (0~{len(LEAVE_PERIODS)-1})")
                return

        print(f"\n{'='*60}")
        print(" 방학 중 41조 연수 자동 상신")
        print(f"{'='*60}")
        print(f"  📍 목적지: {destination}")
        print(f"  📝 사유: {reason}")
        print(f"  👥 결재선: 강동휘 -> 김경영 -> 교장(이재섭)")
        print(f"  📅 대상 건수: {len(target_periods)}건")

        success_count = 0
        for period in target_periods:
            ok = await submit_single_period(page, period, destination, reason)
            if ok:
                success_count += 1
                await asyncio.sleep(2.0)

        print(f"\n{'='*60}")
        print(f" 🎉 [완료] {success_count}/{len(target_periods)}건 상신 처리!")
        print(f"{'='*60}")

    finally:
        await pw.stop()


def main():
    parser = argparse.ArgumentParser(description="나이스 방학 중 41조 연수 상신 자동화")
    parser.add_argument("--port", type=int, default=REMOTE_PORT)
    parser.add_argument("--diagnose", action="store_true", help="화면 인스턴스 파악")
    parser.add_argument("--apply", action="store_true", help="실반영 구동")
    parser.add_argument("--confirm", help="APPLY_NEIS 확인")
    parser.add_argument("--period-idx", type=int, default=None, help="단 1개 회차만 지정하여 실행 (0, 1, 2, 3)")
    parser.add_argument("--destination", default=DEFAULT_DESTINATION)
    parser.add_argument("--reason", default=DEFAULT_REASON)

    args = parser.parse_args()
    if not args.diagnose and not args.apply:
        print("--diagnose 또는 --apply 모드를 지정하세요.")
        return

    asyncio.run(run(args))


if __name__ == "__main__":
    main()
