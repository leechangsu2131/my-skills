#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NEIS 교과 연간지도계획 전체 과목 자동 다운로드 스크립트.

학급담임 > 진도표 관리 > 교과진도표관리 > 교과 연간지도계획 화면에서
과목 콤보박스에 있는 모든 과목의 연간지도계획을 순서대로 다운로드합니다.

실행 방법:
  # 1단계: 화면 구조 진단 (앱 ID / 컨트롤 / 데이터셋 목록 출력)
  python skills/admin-neis-bot/neis_annual_plan_downloader.py --diagnose

  # 2단계: 전체 과목 다운로드
  python skills/admin-neis-bot/neis_annual_plan_downloader.py --apply --confirm APPLY_NEIS

  # 특정 과목만
  python skills/admin-neis-bot/neis_annual_plan_downloader.py --apply --confirm APPLY_NEIS --subjects 국어 수학

  # 다운로드 폴더 지정 (기본: ./downloads/annual_plan/)
  python skills/admin-neis-bot/neis_annual_plan_downloader.py --apply --confirm APPLY_NEIS --output-dir "C:/Users/user/Downloads/연간지도계획"

사전 요건:
  - 나이스 크롬(포트 9222)이 실행·로그인된 상태여야 합니다.
  - 실행 방법: 나이스_마스터크롬.bat 더블클릭 → 나이스 로그인
"""

from __future__ import annotations

import argparse
import io
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import NoAlertPresentException, JavascriptException

# ──────────────────────────────────────────────────────────────────────────────
# 콘솔 인코딩 (Windows CP949 환경 대응)
# ──────────────────────────────────────────────────────────────────────────────
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# ──────────────────────────────────────────────────────────────────────────────
# 상수
# ──────────────────────────────────────────────────────────────────────────────
REMOTE_PORT = 9222

# 나이스 교과 연간지도계획 메뉴 경로 (예상)
MENU_PATH = ["학급담임", "진도표 관리", "교과진도표관리", "교과 연간지도계획"]

# 예상 앱 ID (--diagnose 결과로 업데이트 필요)
# 실제 값은 --diagnose 실행 후 출력된 결과에서 확인합니다.
EXPECTED_APP_ID = None  # 예: "edu/sw/els/edc/lp/els_edclp00_m00"

# 예상 컨트롤 ID (--diagnose 결과로 업데이트 필요)
# 아래 값은 초기 추정이며, 실제 화면 진단 후 업데이트됩니다.
SUBJECT_COMBO_ID = "cmbSbjt"   # 과목 선택 콤보박스 (예상 ID)
SEARCH_BTN_ID    = "btnSearch" # 조회 버튼
EXCEL_BTN_IDS    = [           # 다운로드/Excel 버튼 후보 (우선순위 순)
    "btnExcel",
    "btnDown",
    "btnDownload",
    "btnPrint",
    "btnExcelDown",
    "btnXls",
]


# ──────────────────────────────────────────────────────────────────────────────
# 유틸리티
# ──────────────────────────────────────────────────────────────────────────────

def log(msg: str) -> None:
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}")


def dismiss_alerts(driver) -> None:
    """브라우저 시스템 얼럿을 모두 닫습니다."""
    try:
        alert = driver.switch_to.alert
        text = alert.text
        log(f"  [alert] 시스템 얼럿 닫기: '{text}'")
        alert.accept()
        time.sleep(0.8)
        dismiss_alerts(driver)
    except NoAlertPresentException:
        pass


def dismiss_neis_modals(driver) -> None:
    """나이스 eXBuilder6 모달(확인/알림창)을 닫습니다."""
    try:
        driver.execute_script("""
            try {
                var instances = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
                instances.forEach(function(ai) {
                    if (!ai || !ai.app) return;
                    var id = ai.app.id || "";
                    if (id.indexOf("confirm") !== -1 || id.indexOf("alert") !== -1 || id.indexOf("cmn") !== -1) {
                        var container = ai.getContainer ? ai.getContainer() : null;
                        if (!container) return;
                        var children = container.getAllRecursiveChildren ? container.getAllRecursiveChildren() : [];
                        children.forEach(function(c) {
                            if (!c) return;
                            var val = c.value || c.text || "";
                            var cid = c.id || "";
                            if (cid === "btnOk" || cid === "btnConfirm" || val === "확인" || val === "예" || val === "OK") {
                                if (typeof c.click === "function") c.click();
                            }
                        });
                    }
                });
            } catch(e) {}
        """)
    except Exception:
        pass
    time.sleep(0.5)


# ──────────────────────────────────────────────────────────────────────────────
# 드라이버 연결
# ──────────────────────────────────────────────────────────────────────────────

def connect_cdp(port: int = REMOTE_PORT):
    """Chrome 원격 디버깅(CDP) 세션에 연결합니다."""
    # EVPN 환경 대응: 로컬 루프백 프록시 예외
    os.environ.setdefault("no_proxy", "localhost,127.0.0.1")

    opts = Options()
    opts.add_experimental_option("debuggerAddress", f"127.0.0.1:{port}")
    driver = webdriver.Chrome(options=opts)
    log(f"[연결 성공] 페이지 제목: {driver.title}")
    dismiss_alerts(driver)
    return driver


# ──────────────────────────────────────────────────────────────────────────────
# 메뉴 이동
# ──────────────────────────────────────────────────────────────────────────────

def navigate_to_annual_plan_menu(driver) -> bool:
    """
    나이스 메인 앱의 dsAllMenu 데이터셋에서 교과 연간지도계획 메뉴를 검색하여
    클릭(menuClick) API로 이동합니다.

    탐색 키워드: '연간지도', '연간 지도', '교과진도', '연간계획'
    """
    SEARCH_KEYWORDS = ["연간지도", "연간 지도", "교과진도", "연간계획", "연간지도계획"]

    log("메뉴 검색 중: 교과 연간지도계획...")
    result = driver.execute_script("""
        return (function(keywords) {
            try {
                var platform = cpr.core.Platform.INSTANCE;
                if (!platform) return {error: "cpr Platform 없음"};

                var indexApp = platform.getAllRunningAppInstances().find(function(ai) {
                    return ai && ai.app && ai.app.id === "app/com/main/Index";
                });
                if (!indexApp) return {error: "app/com/main/Index 앱 없음"};

                var datasetIds = ["dsAllMenu", "dsAllMenuNew", "dsAllMenuLocal"];
                var matches = [];
                var seen = {};

                function getValue(ds, row, names) {
                    for (var i = 0; i < names.length; i++) {
                        try {
                            var v = ds.getValue(row, names[i]);
                            if (v !== undefined && v !== null && String(v) !== "") return String(v);
                        } catch(e) {}
                    }
                    return "";
                }

                datasetIds.forEach(function(dsId) {
                    var ds = indexApp.lookup(dsId);
                    if (!ds || !ds.getRowCount) return;
                    var rowCount = ds.getRowCount();
                    for (var r = 0; r < rowCount; r++) {
                        var menuName = getValue(ds, r, ["MENU_NM", "menuNm"]);
                        var path = getValue(ds, r, ["menuNmDepth", "pgePathNm", "DESC", "MENU_DESC"]);
                        var haystack = (menuName + " " + path).toLowerCase();
                        var hit = keywords.some(function(k) {
                            return haystack.indexOf(k.toLowerCase()) >= 0;
                        });
                        if (!hit) continue;

                        var menuId = getValue(ds, r, ["MENU_ID", "menuId", "V_MENU_ID", "vMenuId"]);
                        var pageId = getValue(ds, r, ["PGM_ID", "pgeId", "CALL_PAGE"]);
                        var key = menuName + "|" + menuId + "|" + pageId;
                        if (seen[key]) continue;
                        seen[key] = true;
                        matches.push({
                            dsId: dsId,
                            row: r,
                            menuName: menuName,
                            path: path,
                            menuId: menuId,
                            pageId: pageId
                        });
                    }
                });
                return {ok: true, matches: matches};
            } catch(e) {
                return {error: String(e)};
            }
        })(arguments[0]);
    """, SEARCH_KEYWORDS)

    if result.get("error"):
        log(f"  ✗ 메뉴 검색 오류: {result['error']}")
        return False

    matches = result.get("matches", [])
    if not matches:
        log("  ✗ '교과 연간지도계획' 관련 메뉴를 찾을 수 없습니다.")
        log("    → --diagnose 모드에서 전체 메뉴 목록을 확인하세요.")
        return False

    log(f"  메뉴 후보 {len(matches)}개 발견:")
    for i, m in enumerate(matches):
        log(f"    [{i}] {m['menuName']} | {m['path']} | menuId={m['menuId']} | pageId={m['pageId']}")

    # 가장 일치하는 메뉴 선택 ('연간지도계획' 또는 '교과진도표' 포함 우선)
    target = None
    priority_keywords = ["연간지도계획", "교과 연간", "연간지도"]
    for kw in priority_keywords:
        for m in matches:
            if kw in m["menuName"] or kw in m["path"]:
                target = m
                break
        if target:
            break
    if not target:
        target = matches[0]

    log(f"  → 선택: '{target['menuName']}' (menuId={target['menuId']})")

    # 메뉴 클릭 시도 (eXBuilder6 menuClick API 또는 DOM 클릭)
    clicked = driver.execute_script("""
        return (function(menuId, menuName) {
            try {
                var platform = cpr.core.Platform.INSTANCE;
                var indexApp = platform.getAllRunningAppInstances().find(function(ai) {
                    return ai && ai.app && ai.app.id === "app/com/main/Index";
                });
                if (!indexApp) return {error: "Index 앱 없음"};

                // 방법 1: menuClick 함수 직접 호출
                if (typeof indexApp.menuClick === "function") {
                    indexApp.menuClick(menuId);
                    return {ok: true, method: "menuClick API"};
                }

                // 방법 2: 메뉴 DOM 요소 클릭
                var allLinks = document.querySelectorAll("a, li, span, div");
                for (var i = 0; i < allLinks.length; i++) {
                    var el = allLinks[i];
                    var text = (el.innerText || el.textContent || "").trim();
                    if (text === menuName && el.offsetParent !== null) {
                        el.click();
                        return {ok: true, method: "DOM click", text: text};
                    }
                }

                return {error: "클릭 방법 없음"};
            } catch(e) {
                return {error: String(e)};
            }
        })(arguments[0], arguments[1]);
    """, target["menuId"], target["menuName"])

    if clicked.get("error"):
        log(f"  ✗ 메뉴 클릭 실패: {clicked['error']}")
        log("    → 메뉴를 수동으로 열고 해당 화면에서 --diagnose 를 다시 실행하세요.")
        return False

    log(f"  ✓ 메뉴 이동 완료 (방법: {clicked.get('method', '?')})")
    time.sleep(3)
    return True


# ──────────────────────────────────────────────────────────────────────────────
# 화면 진단
# ──────────────────────────────────────────────────────────────────────────────

def diagnose_screen(driver, output_dir: Path) -> dict:
    """
    현재 활성화된 eXBuilder6 앱/컨트롤/데이터셋 구조를 덤프합니다.
    결과를 JSON 파일로 저장하고 딕셔너리로 반환합니다.
    """
    log("\n=== 화면 진단 시작 ===")

    result = driver.execute_script("""
        return (function() {
            try {
                var platform = cpr.core.Platform.INSTANCE;
                if (!platform) return {error: "cpr Platform 없음"};

                var allApps = platform.getAllRunningAppInstances();
                var appList = allApps.map(function(ai) {
                    if (!ai || !ai.app) return null;
                    return {appId: ai.app.id};
                }).filter(Boolean);

                // 메인 Index 제외, 현재 화면 앱 후보 추출
                var candidates = allApps.filter(function(ai) {
                    return ai && ai.app &&
                           ai.app.id !== "app/com/main/Index" &&
                           !ai.app.id.startsWith("app/cmn/") &&
                           !ai.app.id.startsWith("app/com/");
                });

                var details = candidates.map(function(ai) {
                    var info = {appId: ai.app.id, controls: [], datasets: []};
                    try {
                        // 컨트롤 목록
                        var container = ai.getContainer ? ai.getContainer() : null;
                        if (container && container.getAllRecursiveChildren) {
                            var children = container.getAllRecursiveChildren();
                            children.forEach(function(c) {
                                if (!c || !c.id) return;
                                var item = {id: c.id, type: c.type || "?"};
                                // 버튼이면 라벨도
                                if (c.type === "button") {
                                    item.value = c.value || "";
                                    item.enabled = (typeof c.enabled === "boolean") ? c.enabled : "?";
                                }
                                // 콤보박스면 아이템 목록
                                if (c.type === "combo" || (c.id && (c.id.indexOf("cmb") === 0 || c.id.indexOf("Cmb") >= 0))) {
                                    try {
                                        var items = c.getItems ? c.getItems() : [];
                                        item.comboItems = items.map(function(it) {
                                            return {label: it.label, value: it.value};
                                        });
                                        item.currentValue = c.getValue ? c.getValue() : "";
                                        item.currentText = c.getText ? c.getText() : "";
                                    } catch(e2) {}
                                }
                                info.controls.push(item);
                            });
                        }
                    } catch(e) {
                        info.controlError = String(e);
                    }

                    try {
                        // 데이터셋 목록 (allRecursiveChildren에서 dataset 타입 찾기)
                        var container2 = ai.getContainer ? ai.getContainer() : null;
                        if (container2 && container2.getAllRecursiveChildren) {
                            var ch2 = container2.getAllRecursiveChildren();
                            ch2.forEach(function(c) {
                                if (!c) return;
                                if (c.type === "dataset" || (c.getColumnCount && c.getRowCount)) {
                                    var dsInfo = {id: c.id || "?", rowCount: 0, columns: []};
                                    try {
                                        dsInfo.rowCount = c.getRowCount();
                                        var colCnt = c.getColumnCount ? c.getColumnCount() : 0;
                                        for (var i = 0; i < Math.min(colCnt, 30); i++) {
                                            dsInfo.columns.push(c.getColumnId(i));
                                        }
                                    } catch(e3) {}
                                    info.datasets.push(dsInfo);
                                }
                            });
                        }
                    } catch(e) {
                        info.datasetError = String(e);
                    }

                    return info;
                });

                return {ok: true, allApps: appList, details: details};
            } catch(e) {
                return {error: String(e)};
            }
        })();
    """)

    if result.get("error"):
        log(f"  ✗ 진단 오류: {result['error']}")
        return {}

    # 전체 앱 목록 출력
    log(f"\n[전체 앱 목록] {len(result.get('allApps', []))}개:")
    for a in result.get("allApps", []):
        log(f"  - {a['appId']}")

    # 상세 정보 출력
    details = result.get("details", [])
    log(f"\n[현재 화면 앱 후보] {len(details)}개:")
    for d in details:
        log(f"\n  ▶ 앱 ID: {d['appId']}")

        # 버튼 목록
        buttons = [c for c in d.get("controls", []) if c.get("type") == "button"]
        if buttons:
            log(f"    버튼 ({len(buttons)}개):")
            for b in buttons:
                log(f"      - id={b['id']}, value='{b.get('value', '')}', enabled={b.get('enabled', '?')}")

        # 콤보박스 목록
        combos = [c for c in d.get("controls", [])
                  if c.get("type") == "combo" or "cmb" in c.get("id", "").lower()]
        if combos:
            log(f"    콤보박스 ({len(combos)}개):")
            for cb in combos:
                items_preview = cb.get("comboItems", [])[:5]
                log(f"      - id={cb['id']}, 현재='{cb.get('currentText', '')}', "
                    f"아이템 수={len(cb.get('comboItems', []))}")
                for it in items_preview:
                    log(f"        ▪ {it['label']} (value={it['value']})")

        # 데이터셋
        datasets = d.get("datasets", [])
        if datasets:
            log(f"    데이터셋 ({len(datasets)}개):")
            for ds in datasets:
                log(f"      - id={ds['id']}, 행수={ds['rowCount']}, 컬럼={ds['columns'][:8]}")

    # JSON 저장
    output_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    diag_path = output_dir / f"annual_plan_diagnose_{ts}.json"
    diag_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    log(f"\n  → 진단 결과 저장: {diag_path}")

    return result


# ──────────────────────────────────────────────────────────────────────────────
# 앱 인스턴스 찾기
# ──────────────────────────────────────────────────────────────────────────────

def find_app_instance(driver, app_id: str | None) -> str | None:
    """
    활성화된 eXBuilder6 앱 인스턴스 중에서 대상 앱 ID를 반환합니다.
    app_id가 None이면 메인/공통 앱 제외 첫 번째 앱을 반환합니다.
    """
    result = driver.execute_script("""
        return (function(targetId) {
            try {
                var platform = cpr.core.Platform.INSTANCE;
                if (!platform) return null;
                var all = platform.getAllRunningAppInstances();
                if (targetId) {
                    var found = all.find(function(ai) {
                        return ai && ai.app && ai.app.id === targetId;
                    });
                    return found ? targetId : null;
                }
                // 자동 탐지: main/공통 제외
                var candidate = all.find(function(ai) {
                    if (!ai || !ai.app) return false;
                    var id = ai.app.id;
                    return id !== "app/com/main/Index" &&
                           !id.startsWith("app/cmn/") &&
                           !id.startsWith("app/com/");
                });
                return candidate ? candidate.app.id : null;
            } catch(e) {
                return null;
            }
        })(arguments[0]);
    """, app_id)
    return result


# ──────────────────────────────────────────────────────────────────────────────
# 과목 목록 조회
# ──────────────────────────────────────────────────────────────────────────────

def get_subject_list(driver, app_id: str, combo_id: str = SUBJECT_COMBO_ID) -> list[dict]:
    """
    지정 앱의 과목 콤보박스에서 전체 과목 목록을 반환합니다.
    반환 형식: [{"label": "국어", "value": "NE00001"}, ...]
    """
    result = driver.execute_script("""
        return (function(appId, comboId) {
            try {
                var platform = cpr.core.Platform.INSTANCE;
                var inst = platform.getAllRunningAppInstances().find(function(ai) {
                    return ai && ai.app && ai.app.id === appId;
                });
                if (!inst) return {error: "앱을 찾을 수 없음: " + appId};

                var cmb = inst.lookup(comboId);
                if (!cmb) return {error: "콤보박스를 찾을 수 없음: " + comboId};

                var items = cmb.getItems ? cmb.getItems() : [];
                return {
                    ok: true,
                    currentValue: cmb.getValue ? cmb.getValue() : "",
                    currentText: cmb.getText ? cmb.getText() : "",
                    items: items.map(function(it) {
                        return {label: it.label, value: it.value};
                    })
                };
            } catch(e) {
                return {error: String(e)};
            }
        })(arguments[0], arguments[1]);
    """, app_id, combo_id)

    if result.get("error"):
        log(f"  ✗ 과목 목록 조회 실패: {result['error']}")
        return []

    items = result.get("items", [])
    log(f"  과목 {len(items)}개 발견 (현재: '{result.get('currentText', '')}'):")
    for it in items:
        log(f"    - {it['label']} (value={it['value']})")
    return items


# ──────────────────────────────────────────────────────────────────────────────
# 과목 선택 + 조회
# ──────────────────────────────────────────────────────────────────────────────

def select_subject_and_search(driver, app_id: str, value: str,
                               combo_id: str = SUBJECT_COMBO_ID,
                               search_btn_id: str = SEARCH_BTN_ID) -> bool:
    """과목 콤보박스에서 값을 선택하고 조회 버튼을 클릭합니다."""
    dismiss_alerts(driver)
    result = driver.execute_script("""
        return (function(appId, comboId, value, btnId) {
            try {
                var platform = cpr.core.Platform.INSTANCE;
                var inst = platform.getAllRunningAppInstances().find(function(ai) {
                    return ai && ai.app && ai.app.id === appId;
                });
                if (!inst) return {error: "앱 없음: " + appId};

                var cmb = inst.lookup(comboId);
                if (!cmb) return {error: "콤보박스 없음: " + comboId};
                cmb.selectItemByValue(value, true);

                return {ok: true, selected: cmb.getText ? cmb.getText() : value};
            } catch(e) {
                return {error: String(e)};
            }
        })(arguments[0], arguments[1], arguments[2], arguments[3]);
    """, app_id, combo_id, value, search_btn_id)

    if result.get("error"):
        log(f"    ✗ 과목 선택 실패: {result['error']}")
        return False

    log(f"    → 과목 선택: '{result.get('selected', value)}'")
    time.sleep(1.5)

    # 조회 버튼 클릭
    btn_result = driver.execute_script("""
        return (function(appId, btnId) {
            try {
                var platform = cpr.core.Platform.INSTANCE;
                var inst = platform.getAllRunningAppInstances().find(function(ai) {
                    return ai && ai.app && ai.app.id === appId;
                });
                if (!inst) return {error: "앱 없음"};
                var btn = inst.lookup(btnId);
                if (!btn) return {error: "조회버튼 없음: " + btnId};
                btn.click();
                return {ok: true};
            } catch(e) {
                return {error: String(e)};
            }
        })(arguments[0], arguments[1]);
    """, app_id, search_btn_id)

    if btn_result.get("error"):
        log(f"    ✗ 조회 버튼 실패: {btn_result['error']}")
        return False

    log(f"    → 조회 클릭 완료")
    time.sleep(2)
    dismiss_alerts(driver)
    return True


# ──────────────────────────────────────────────────────────────────────────────
# 다운로드 버튼 탐색 및 클릭
# ──────────────────────────────────────────────────────────────────────────────

def find_and_click_download(driver, app_id: str) -> dict:
    """
    다운로드/Excel 버튼 후보를 순서대로 탐색하여 클릭합니다.
    반환: {"ok": True, "btnId": "btnExcel"} 또는 {"error": "..."}
    """
    btn_candidates = json.dumps(EXCEL_BTN_IDS)
    result = driver.execute_script("""
        return (function(appId, candidates) {
            try {
                var platform = cpr.core.Platform.INSTANCE;
                var inst = platform.getAllRunningAppInstances().find(function(ai) {
                    return ai && ai.app && ai.app.id === appId;
                });
                if (!inst) return {error: "앱 없음: " + appId};

                // 후보 ID 순서대로 시도
                for (var i = 0; i < candidates.length; i++) {
                    var btn = inst.lookup(candidates[i]);
                    if (btn && (btn.enabled === true || btn.enabled === undefined)) {
                        btn.click();
                        return {ok: true, btnId: candidates[i]};
                    }
                }

                // 후보 없으면 모든 버튼 목록 반환
                var container = inst.getContainer ? inst.getContainer() : null;
                var allBtns = [];
                if (container && container.getAllRecursiveChildren) {
                    container.getAllRecursiveChildren().forEach(function(c) {
                        if (c && c.type === "button") {
                            allBtns.push({id: c.id, value: c.value, enabled: c.enabled});
                        }
                    });
                }
                return {error: "다운로드 버튼 없음", availableButtons: allBtns};
            } catch(e) {
                return {error: String(e)};
            }
        })(arguments[0], arguments[1]);
    """, app_id, EXCEL_BTN_IDS)

    return result


def wait_for_download(download_dir: Path, before_files: set[Path],
                      timeout: int = 30) -> Path | None:
    """
    다운로드 폴더를 감시하여 새로 생긴 파일이 안정화되면 경로를 반환합니다.
    .crdownload / .tmp 등 임시 파일은 완료 전으로 간주합니다.
    """
    deadline = time.time() + timeout
    while time.time() < deadline:
        current_files = set(download_dir.glob("*"))
        new_files = current_files - before_files
        # 임시 파일 제외
        done = [f for f in new_files
                if f.suffix not in (".crdownload", ".tmp", ".part")
                and f.stat().st_size > 0]
        if done:
            # 가장 최근에 생성된 파일
            return max(done, key=lambda f: f.stat().st_mtime)
        time.sleep(1)
    return None


# ──────────────────────────────────────────────────────────────────────────────
# Chrome 다운로드 폴더 설정
# ──────────────────────────────────────────────────────────────────────────────

def set_chrome_download_dir(driver, download_dir: Path) -> None:
    """
    Chrome DevTools Protocol을 통해 다운로드 경로를 지정합니다.
    (Selenium + CDP execute_cdp_cmd 방식)
    """
    try:
        driver.execute_cdp_cmd("Page.setDownloadBehavior", {
            "behavior": "allow",
            "downloadPath": str(download_dir.resolve())
        })
        log(f"  Chrome 다운로드 경로 설정: {download_dir.resolve()}")
    except Exception as e:
        log(f"  ⚠ 다운로드 경로 설정 실패 (무시): {e}")
        log(f"    → Chrome 기본 다운로드 폴더를 사용합니다.")


# ──────────────────────────────────────────────────────────────────────────────
# 메인 실행
# ──────────────────────────────────────────────────────────────────────────────

def run_diagnose(args) -> None:
    """--diagnose 모드: 메뉴 이동 후 화면 구조 덤프."""
    driver = connect_cdp(args.port)
    output_dir = Path(args.output_dir)

    log("\n=== [STEP 1] 교과 연간지도계획 메뉴 이동 ===")
    if args.skip_nav:
        log("  --skip-nav: 메뉴 이동 생략 (이미 해당 화면에 있어야 합니다)")
    else:
        ok = navigate_to_annual_plan_menu(driver)
        if not ok:
            log("\n  ⚠ 메뉴 자동 이동 실패. 수동으로 화면을 열고 --diagnose --skip-nav 를 실행하세요.")
        time.sleep(2)

    log("\n=== [STEP 2] 화면 구조 진단 ===")
    diag = diagnose_screen(driver, output_dir)

    if not diag.get("details"):
        log("\n  ✗ 현재 화면에서 eXBuilder6 앱을 찾을 수 없습니다.")
        log("    → 나이스에서 '교과 연간지도계획' 화면을 직접 열어두고 다시 실행하세요.")
        return

    log("\n=== 진단 완료 ===")
    log("다음 단계:")
    log("  1. 위 출력에서 앱 ID, 과목 콤보박스 ID, 다운로드 버튼 ID를 확인하세요.")
    log("  2. 필요하면 스크립트 상단의 EXPECTED_APP_ID, SUBJECT_COMBO_ID, EXCEL_BTN_IDS 를 수정하세요.")
    log("  3. python skills/admin-neis-bot/neis_annual_plan_downloader.py --apply --confirm APPLY_NEIS")


def run_apply(args) -> None:
    """--apply 모드: 전체 과목 연간지도계획 다운로드."""
    if args.confirm != "APPLY_NEIS":
        log("✗ --confirm APPLY_NEIS 를 지정해야 실제 다운로드가 수행됩니다.")
        sys.exit(1)

    driver = connect_cdp(args.port)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Chrome 다운로드 경로 지정
    set_chrome_download_dir(driver, output_dir)

    log("\n=== [STEP 1] 교과 연간지도계획 메뉴 이동 ===")
    if args.skip_nav:
        log("  --skip-nav: 메뉴 이동 생략")
    else:
        ok = navigate_to_annual_plan_menu(driver)
        if not ok:
            log("\n  ⚠ 메뉴 자동 이동 실패.")
            log("    → 수동으로 '교과 연간지도계획' 화면을 열고 --skip-nav 옵션으로 재실행하세요.")
            sys.exit(1)
        time.sleep(2)

    log("\n=== [STEP 2] 앱 인스턴스 탐색 ===")
    app_id = args.app_id or EXPECTED_APP_ID or find_app_instance(driver, None)
    if not app_id:
        log("  ✗ 활성화된 앱 인스턴스를 찾을 수 없습니다.")
        log("    → --diagnose 를 먼저 실행하여 앱 ID를 확인하세요.")
        log("    → 또는 --app-id 옵션으로 직접 지정하세요.")
        sys.exit(1)
    log(f"  앱 ID: {app_id}")

    log("\n=== [STEP 3] 과목 목록 조회 ===")
    combo_id = args.combo_id or SUBJECT_COMBO_ID
    subjects = get_subject_list(driver, app_id, combo_id)
    if not subjects:
        log("  ✗ 과목 목록을 가져올 수 없습니다.")
        log(f"    → 콤보박스 ID '{combo_id}'가 맞는지 --diagnose 로 확인하세요.")
        sys.exit(1)

    # 특정 과목만 처리 필터링
    if args.subjects:
        target_names = set(args.subjects)
        subjects = [s for s in subjects if s["label"] in target_names]
        if not subjects:
            log(f"  ✗ 지정한 과목을 찾을 수 없습니다: {args.subjects}")
            sys.exit(1)
        log(f"  → 필터링 후 {len(subjects)}개 과목 처리")

    log(f"\n=== [STEP 4] 과목별 다운로드 시작 (총 {len(subjects)}개) ===")
    results = []

    for idx, subj in enumerate(subjects, 1):
        log(f"\n[{idx}/{len(subjects)}] {subj['label']} (value={subj['value']})")

        # 다운로드 전 파일 목록 스냅샷
        before_files = set(output_dir.glob("*"))

        # 과목 선택 + 조회
        ok = select_subject_and_search(
            driver, app_id, subj["value"],
            combo_id=combo_id,
            search_btn_id=args.search_btn_id or SEARCH_BTN_ID
        )
        if not ok:
            results.append({"subject": subj["label"], "status": "select_failed"})
            continue

        time.sleep(1)

        # 다운로드 버튼 클릭
        dl_result = find_and_click_download(driver, app_id)
        if dl_result.get("error"):
            log(f"    ✗ 다운로드 버튼 오류: {dl_result['error']}")
            if dl_result.get("availableButtons"):
                log("    사용 가능한 버튼 목록:")
                for b in dl_result["availableButtons"]:
                    log(f"      - id={b['id']}, value='{b.get('value', '')}', enabled={b.get('enabled')}")
            results.append({
                "subject": subj["label"],
                "status": "download_btn_not_found",
                "availableButtons": dl_result.get("availableButtons", [])
            })
            continue

        log(f"    → 다운로드 버튼 클릭: {dl_result.get('btnId', '?')}")

        # 다운로드 모달 처리 (인쇄 팝업 등이 뜰 경우 닫기)
        time.sleep(1)
        dismiss_alerts(driver)
        dismiss_neis_modals(driver)

        # 파일 완료 대기
        downloaded_file = wait_for_download(output_dir, before_files, timeout=30)
        if downloaded_file:
            # 파일명 변경: {과목명}_연간지도계획.{확장자}
            safe_name = subj["label"].replace("/", "_").replace("\\", "_")
            new_name = output_dir / f"{safe_name}_연간지도계획{downloaded_file.suffix}"
            try:
                downloaded_file.rename(new_name)
                log(f"    ✓ 저장 완료: {new_name.name}")
                results.append({"subject": subj["label"], "status": "ok", "file": str(new_name)})
            except Exception as e:
                log(f"    ⚠ 파일 이름 변경 실패 ({e}), 원본 파일: {downloaded_file}")
                results.append({"subject": subj["label"], "status": "ok_renamed_fail", "file": str(downloaded_file)})
        else:
            log(f"    ✗ 다운로드 파일을 감지하지 못했습니다 (30초 초과)")
            log(f"       → 다운로드가 브라우저 다이얼로그로 열렸거나 다른 방식일 수 있습니다.")
            log(f"       → --diagnose 로 화면 구조를 재확인하세요.")
            results.append({"subject": subj["label"], "status": "download_timeout"})

        time.sleep(1)

    # 결과 요약
    log(f"\n{'='*60}")
    log("📊 다운로드 결과 요약")
    log(f"{'='*60}")
    success = [r for r in results if r["status"] == "ok"]
    failed  = [r for r in results if r["status"] != "ok"]
    log(f"  성공: {len(success)}/{len(results)}")
    for r in results:
        icon = "✅" if r["status"] == "ok" else "❌"
        log(f"  {icon} {r['subject']} → {r['status']}")

    # 결과 JSON 저장
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = output_dir / f"annual_plan_download_log_{ts}.json"
    log_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    log(f"\n  로그 저장: {log_path}")

    if failed:
        log("\n  ⚠ 일부 과목 다운로드 실패. 위 로그를 확인하세요.")
        log("    → 실패 원인이 버튼 ID 불일치인 경우, --diagnose 후 스크립트 상단의 EXCEL_BTN_IDS 를 수정하세요.")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="NEIS 교과 연간지도계획 전체 과목 자동 다운로드",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--diagnose", action="store_true",
                      help="화면 구조 진단 (앱 ID / 컨트롤 / 데이터셋 목록 출력)")
    mode.add_argument("--apply", action="store_true",
                      help="실제 다운로드 수행")

    parser.add_argument("--confirm", default="",
                        help="실반영 시 'APPLY_NEIS' 를 입력해야 합니다.")
    parser.add_argument("--port", type=int, default=REMOTE_PORT,
                        help=f"Chrome 원격 디버깅 포트 (기본: {REMOTE_PORT})")
    parser.add_argument("--output-dir", default="downloads/annual_plan",
                        help="다운로드 저장 폴더 (기본: downloads/annual_plan/)")
    parser.add_argument("--subjects", nargs="*",
                        help="특정 과목만 처리 (예: --subjects 국어 수학 영어)")
    parser.add_argument("--skip-nav", action="store_true",
                        help="메뉴 자동 이동 생략 (이미 해당 화면에 있을 때)")
    parser.add_argument("--app-id", default=None,
                        help="eXBuilder6 앱 ID 직접 지정 (--diagnose 결과 참조)")
    parser.add_argument("--combo-id", default=None,
                        help=f"과목 콤보박스 ID 직접 지정 (기본 추정: {SUBJECT_COMBO_ID})")
    parser.add_argument("--search-btn-id", default=None,
                        help=f"조회 버튼 ID 직접 지정 (기본 추정: {SEARCH_BTN_ID})")

    args = parser.parse_args()

    if args.diagnose:
        run_diagnose(args)
    elif args.apply:
        run_apply(args)


if __name__ == "__main__":
    main()
