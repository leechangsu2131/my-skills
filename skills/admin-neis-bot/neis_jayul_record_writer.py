import asyncio
import io
import json
import os
import sys
import argparse
from playwright.async_api import async_playwright

os.environ["no_proxy"] = "localhost,127.0.0.1"
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# ==============================================================================
# JAVASCRIPT SNIPPETS
# ==============================================================================

# 1. 메인 화면 초기화 (조회 클릭)
JS_REQUERY_MAIN = """
(function() {
    var app = cpr.core.Platform.INSTANCE.getAllRunningAppInstances().find(function(ai) {
        return ai.app && ai.app.id === "edu/sw/els/sdl/ce/els_sdlce00_m01";
    });
    if (!app) return {error: "메인 앱 els_sdlce00_m01을 찾을 수 없습니다."};
    
    var btnSearch = app.lookup("btnSearch");
    if (btnSearch) {
        btnSearch.click();
        return {success: true};
    }
    return {error: "조회 버튼을 찾을 수 없습니다."};
})();
"""

# 2. 활동일자 전체 가져오기
JS_GET_DATES = """
(function() {
    var app = cpr.core.Platform.INSTANCE.getAllRunningAppInstances().find(function(ai) {
        return ai.app && ai.app.id === "edu/sw/els/sdl/ce/els_sdlce00_m01";
    });
    if (!app) return {error: "메인 앱 못찾음"};
    
    var ds = app.lookup("dsActYmd");
    if (!ds) return {error: "dsActYmd 데이터셋 못찾음"};
    
    var dates = [];
    for (var r = 0; r < ds.getRowCount(); r++) {
        dates.push({
            idx: r,
            actYmd: ds.getValue(r, "actYmd"),
            actYmdNm: ds.getValue(r, "actYmdNm"),
            comptHr: Number(ds.getValue(r, "comptHr")),
            direcInptYn: ds.getValue(r, "direcInptYn"),
            rmkCn: ds.getValue(r, "rmkCn")
        });
    }
    return dates;
})();
"""

# 3. 날짜 그리드 행 선택
JS_SELECT_DATE = """
(function(dateIdx) {
    var app = cpr.core.Platform.INSTANCE.getAllRunningAppInstances().find(function(ai) {
        return ai.app && ai.app.id === "edu/sw/els/sdl/ce/els_sdlce00_m01";
    });
    if (!app) return {error: "메인 앱 못찾음"};
    
    var grd = app.lookup("grdActYmd");
    if (!grd) return {error: "grdActYmd 못찾음"};
    
    grd.selectRows([dateIdx]);
    if (grd.dispatchEvent) {
        grd.dispatchEvent("selection-change", {row: dateIdx, rowIndex: dateIdx});
    }
    return {success: true};
})(%DATE_IDX%);
"""

# 4. 학생 리스트 확인 및 체크박스 제어
JS_CHECK_STUDENTS = """
(function(currentDate, transferDate) {
    var app = cpr.core.Platform.INSTANCE.getAllRunningAppInstances().find(function(ai) {
        return ai.app && ai.app.id === "edu/sw/els/sdl/ce/els_sdlce00_m01";
    });
    if (!app) return {error: "메인 앱 못찾음"};
    
    var grd = app.lookup("grdMain");
    var ds = grd ? (grd.dataSet || grd._dataSet) : null;
    if (!grd || !ds) return {error: "학생 그리드/데이터셋 못찾음"};
    
    if (ds.getRowCount() === 0) {
        return {error: "학생 데이터 로드 대기 필요 (rowCount=0)"};
    }
    
    // 전체 체크
    grd.checkAllRow(true);
    
    // 전입생(최윤채) 체크 해제 판단 (전입일: 2026.05.11)
    var uncheckedList = [];
    for (var r = 0; r < ds.getRowCount(); r++) {
        var flctnYmd = ds.getValue(r, "schorFlctnYmd") || "";
        if (flctnYmd && currentDate < flctnYmd) {
            grd.setCheckRowIndex(r, false);
            uncheckedList.push(ds.getValue(r, "stuFlnm"));
        }
    }
    
    return {
        success: true,
        rowCount: ds.getRowCount(),
        uncheckedList: uncheckedList,
        checkedIndices: grd.getCheckRowIndices()
    };
})("%CURRENT_DATE%", "%TRANSFER_DATE%");
"""

# 5. 주간학습 가져오기 클릭
JS_CLICK_WEEK_BTN = """
(function() {
    var app = cpr.core.Platform.INSTANCE.getAllRunningAppInstances().find(function(ai) {
        return ai.app && ai.app.id === "edu/sw/els/sdl/ce/els_sdlce00_m01";
    });
    if (!app) return {error: "메인 앱 못찾음"};
    
    var btn = app.lookup("btnWeek");
    if (!btn) return {error: "btnWeek 버튼 못찾음"};
    
    btn.click();
    return {success: true};
})();
"""

# 6. 주간학습 팝업 데이터셋 정보 및 행 개수 가져오기
JS_GET_WEEKLY_LIST = """
(function() {
    var popup = cpr.core.Platform.INSTANCE.getAllRunningAppInstances().find(function(ai) {
        return ai.app && ai.app.id === "edu/sw/els/sdl/ce/els_sdlce00_p06";
    });
    if (!popup) return {error: "주간학습 가져오기 팝업 앱(els_sdlce00_p06)을 찾을 수 없습니다."};
    
    var ds = popup.lookup("dsCeRec");
    if (!ds) return {error: "dsCeRec 데이터셋 못찾음"};
    
    var list = [];
    for (var r = 0; r < ds.getRowCount(); r++) {
        list.push({
            rowIdx: r,
            pir: ds.getValue(r, "pir"),
            wikLrnUitNm: ds.getValue(r, "wikLrnUitNm"),
            wikLrnCn: ds.getValue(r, "wikLrnCn")
        });
    }
    return list;
})();
"""

# 7. 주간학습 특정 행 클릭 및 적용
JS_APPLY_WEEKLY_ROW = """
(function(rowIdx) {
    var popup = cpr.core.Platform.INSTANCE.getAllRunningAppInstances().find(function(ai) {
        return ai.app && ai.app.id === "edu/sw/els/sdl/ce/els_sdlce00_p06";
    });
    if (!popup) return {error: "주간학습 가져오기 팝업 앱(els_sdlce00_p06)을 찾을 수 없습니다."};
    
    var grd = popup.lookup("grdMain");
    if (!grd) return {error: "grdMain 못찾음"};
    
    var gridUuid = grd.uuid;
    var gridDomId = "uuid-" + gridUuid;
    var gridEl = document.getElementById(gridDomId);
    if (!gridEl) return {error: "그리드 DOM 엘리먼트 못찾음"};
    
    var cellEl = gridEl.querySelector('[data-rowindex="' + rowIdx + '"] [data-cellindex="2"]');
    if (!cellEl) {
        var rowEl = gridEl.querySelector('[data-rowindex="' + rowIdx + '"]');
        if (rowEl) {
            cellEl = rowEl.querySelector('.cl-output') || rowEl.firstElementChild;
        }
    }
    
    if (!cellEl) return {error: "클릭할 셀 요소를 찾을 수 없습니다. rowIdx=" + rowIdx};
    
    // 마우스 이벤트 시뮬레이션
    var events = ["mousedown", "mouseup", "click"];
    events.forEach(function(evtType) {
        var evt = new MouseEvent(evtType, {
            bubbles: true,
            cancelable: true,
            view: window
        });
        cellEl.dispatchEvent(evt);
    });
    
    // 적용하기 버튼 클릭
    var btn = popup.lookup("wekBtnApl");
    if (!btn) return {error: "wekBtnApl 버튼 못찾음"};
    btn.click();
    
    return {success: true};
})(%ROW_IDX%);
"""

# 8. 팝업이 열려있는 경우 강제 닫기 (취소/닫기 클릭)
JS_CLOSE_WEEK_POPUP = """
(function() {
    var popup = cpr.core.Platform.INSTANCE.getAllRunningAppInstances().find(function(ai) {
        return ai.app && ai.app.id === "edu/sw/els/sdl/ce/els_sdlce00_p06";
    });
    if (popup) {
        var btn = popup.lookup("btnCancel");
        if (btn) {
            btn.click();
            return {closed: true};
        }
    }
    return {closed: false};
})();
"""

# 9. 메인 화면 저장 클릭
JS_SAVE_MAIN = """
(function() {
    var app = cpr.core.Platform.INSTANCE.getAllRunningAppInstances().find(function(ai) {
        return ai.app && ai.app.id === "edu/sw/els/sdl/ce/els_sdlce00_m01";
    });
    if (!app) return {error: "메인 앱 못찾음"};
    
    var btn = app.lookup("btnSave");
    if (!btn) return {error: "저장 버튼 못찾음"};
    btn.click();
    return {success: true};
})();
"""

# 10. 열려있는 확인(confirm) 또는 경고(alert) 창 자동 확인/예 처리 (DOM 매크로 보강)
JS_DISMISS_DIALOGS = """
(function() {
    var clicked = 0;
    var closedApps = [];
    
    // DOM 기반 버튼 강제 매크로 클릭 (가장 확실함)
    var elements = document.querySelectorAll('button, div, span, a');
    elements.forEach(function(el) {
        var text = (el.innerText || el.textContent || "").trim();
        if (text === "확인" || text === "예" || text === "Confirm" || text === "Yes") {
            try {
                el.click();
                clicked++;
                closedApps.push("DOM:" + text);
            } catch(e) {}
        }
    });
    
    // eXBuilder6 인스턴스 탐색
    try {
        var apps = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
        for (var i = 0; i < apps.length; i++) {
            var ai = apps[i];
            if (!ai) continue;
            var appId = "";
            try { if (ai.app && ai.app.id) appId = ai.app.id; } catch(e) {}
            
            if (appId.indexOf("alert") >= 0 || appId.indexOf("confirm") >= 0 || appId.indexOf("cmn") >= 0) {
                var container = null;
                try { container = ai.getContainer ? ai.getContainer() : null; } catch(e) {}
                if (container && container.getAllRecursiveChildren) {
                    var children = container.getAllRecursiveChildren();
                    for (var j = 0; j < children.length; j++) {
                        var c = children[j];
                        if (c && c.type === "button" && (c.value === "확인" || c.value === "예")) {
                            try {
                                c.click();
                                clicked++;
                                closedApps.push(appId + ":" + c.value);
                            } catch(e2) {}
                        }
                    }
                }
            }
        }
    } catch(e) {}
    
    return {clickedCount: clicked, closed: closedApps};
})();
"""

# ==============================================================================
# CORE SCRIPTS
# ==============================================================================

async def dismiss_all_dialogs(page):
    """
    화면에 활성화된 모든 확인/경고 팝업을 즉시 닫습니다.
    """
    try:
        res = await page.evaluate(JS_DISMISS_DIALOGS)
        if res and res.get("clickedCount", 0) > 0:
            print(f"     [Dialog Manager] Dismissed dialogs: {res['closed']}")
            return True
    except Exception as e:
        pass
    return False

async def main():
    parser = argparse.ArgumentParser(description="자율활동 누가기록 일괄 입력 자동화 스크립트")
    parser.add_argument("--limit", type=int, default=999, help="처리할 날짜 개수 제한 (테스트용)")
    parser.add_argument("--apply", action="store_true", help="실제 서버 저장 실행 (지정하지 않으면 저장 전까지만 입력하고 롤백)")
    parser.add_argument("--transfer-date", type=str, default="20260511", help="전입생 전입일자 (최윤채: 20260511)")
    args = parser.parse_args()

    print("=" * 70)
    print(f" 자율활동 누가기록 일괄 입력 자동화 (1일 단위 저장 완결 모델)")
    print(f"  - 모드: {'실반영 저장 (APPLY)' if args.apply else '체크 및 입력 모니터링 (DRY RUN)'}")
    print(f"  - 제한: {args.limit}개 날짜")
    print(f"  - 전입생 전입일자: {args.transfer_date}")
    print("=" * 70)

    async with async_playwright() as p:
        try:
            browser = await p.chromium.connect_over_cdp("http://127.0.0.1:9222")
        except Exception as e:
            print(f"Error: 크롬 디버깅 포트(9222)에 연결할 수 없습니다. ({e})")
            return

        target_page = None
        for context in browser.contexts:
            for page in context.pages:
                try:
                    has_cpr = await page.evaluate("typeof cpr !== 'undefined'")
                except:
                    has_cpr = False
                if has_cpr:
                    target_page = page
                    break
            if target_page:
                break

        if not target_page:
            print("Error: 나이스 시스템 화면을 찾을 수 없습니다.")
            return

        print(f" - 연결된 나이스 탭: '{await target_page.title()}'")
        
        # 1. 화면 정리 및 리셋 (조회)
        print(" - 화면 정리 및 조회 초기화 진행 중...")
        await dismiss_all_dialogs(target_page)
        await target_page.evaluate(JS_REQUERY_MAIN)
        await asyncio.sleep(2.0)
        
        # 2. 날짜 목록 수집
        dates = await target_page.evaluate(JS_GET_DATES)
        if "error" in dates:
            print(f"Error: {dates['error']}")
            return

        print(f" - 총 {len(dates)}개의 활동일자가 로드되었습니다.")
        target_dates = [d for d in dates if d["direcInptYn"] != "Y"]
        print(f" - 직접입력 제외 자동화 대상 날짜: {len(target_dates)}개")
        
        processed_count = 0
        
        for d in target_dates:
            if processed_count >= args.limit:
                print(f"\n - 지정된 한도({args.limit}개)에 도달하여 작업을 종료합니다.")
                break
                
            print(f"\n[{processed_count + 1}/{len(target_dates)}] 날짜 처리: {d['actYmdNm']} (이수시간: {d['comptHr']}시간)")
            
            # 날짜 클릭 선택
            sel_res = await target_page.evaluate(JS_SELECT_DATE.replace("%DATE_IDX%", str(d["idx"])))
            if "error" in sel_res:
                print(f"   -> 날짜 선택 에러: {sel_res['error']}")
                continue
            
            # 학생 데이터 로드 대기
            await asyncio.sleep(2.0)
            
            # 학생 체크박스 설정 (전입일 조건 처리)
            check_res = await target_page.evaluate(
                JS_CHECK_STUDENTS.replace("%CURRENT_DATE%", d["actYmd"]).replace("%TRANSFER_DATE%", args.transfer_date)
            )
            if "error" in check_res:
                print(f"   -> 학생 체크 에러: {check_res['error']}")
                continue
                
            print(f"   - 학생 목록 로드 및 체크 완료 ({len(check_res['checkedIndices'])}명 체크)")
            if check_res.get("uncheckedList"):
                print(f"     ⚠️ 전입생 제외: {check_res['uncheckedList']}")
                
            # 주간학습 가져오기 클릭
            week_click = await target_page.evaluate(JS_CLICK_WEEK_BTN)
            if "error" in week_click:
                print(f"   -> 주간학습 가져오기 클릭 에러: {week_click['error']}")
                continue
                
            await asyncio.sleep(2.0)
            
            # 주간학습 리스트 조회
            weekly_list = await target_page.evaluate(JS_GET_WEEKLY_LIST)
            if isinstance(weekly_list, dict) and "error" in weekly_list:
                print(f"   -> 주간학습 팝업 조회 실패: {weekly_list['error']}")
                await target_page.evaluate(JS_CLOSE_WEEK_POPUP)
                continue
                
            # 이수시간(comptHr) 만큼 적용
            apply_limit = min(d["comptHr"], len(weekly_list))
            print(f"   - 시간표 교시 적용 ({apply_limit}개 교시 대상)")
            
            for apply_idx in range(apply_limit):
                if apply_idx > 0:
                    # 팝업 재호출
                    await target_page.evaluate(
                        JS_CHECK_STUDENTS.replace("%CURRENT_DATE%", d["actYmd"]).replace("%TRANSFER_DATE%", args.transfer_date)
                    )
                    await asyncio.sleep(0.5)
                    await target_page.evaluate(JS_CLICK_WEEK_BTN)
                    await asyncio.sleep(2.0)
                
                wl_item = weekly_list[apply_idx]
                print(f"     -> 적용 ({apply_idx + 1}/{apply_limit}): {wl_item['pir']}교시 '{wl_item['wikLrnCn']}'")
                
                apply_res = await target_page.evaluate(JS_APPLY_WEEKLY_ROW.replace("%ROW_IDX%", str(apply_idx)))
                if "error" in apply_res:
                    print(f"        ⚠️ 적용 오류: {apply_res['error']}")
                
                await asyncio.sleep(1.5)
            
            # [실반영 저장 처리] - 1일 완료 즉시 매번 저장
            if args.apply:
                print("   - [저장] 현재 날짜 기입사항 저장 중...")
                save_res = await target_page.evaluate(JS_SAVE_MAIN)
                if "error" in save_res:
                    print(f"     ❌ 저장 오류: {save_res['error']}")
                else:
                    # 확인/성공 다이얼로그 처리 (저장하시겠습니까 -> 저장되었습니다)
                    await asyncio.sleep(1.0)
                    for _ in range(4):
                        await dismiss_all_dialogs(target_page)
                        await asyncio.sleep(0.5)
                    print("     ✅ 기입 및 저장 완료!")
            else:
                # DRY RUN일 경우 다음 행으로 넘어갈 때 뜰 "변경사항 미반영" 팝업 자동 통과(예) 처리
                print("   - [드라이런] 가입력 완료. 다음 단계 시 미반영 팝업 닫기를 대기합니다.")
                await asyncio.sleep(0.5)
                
            # 다음 루프 돌기 전 활성화되어 있을 수 있는 확인 모달을 최종 클리어
            await dismiss_all_dialogs(target_page)
            
            processed_count += 1
            
        print("\n" + "=" * 50)
        if args.apply:
            print(f" 🎉 총 {processed_count}개 자율활동 일자의 서버 저장이 무사히 종료되었습니다.")
        else:
            print(f" [드라이런 완료] 총 {processed_count}개 날짜에 대한 체크박스 및 주간학습 적용 흐름 검증 완료.")
            print("  - 메인 조회를 다시 눌러 화면을 초기화합니다.")
            await target_page.evaluate(JS_REQUERY_MAIN)
            await asyncio.sleep(1.5)
            await dismiss_all_dialogs(target_page)
        print("=" * 50)

if __name__ == "__main__":
    asyncio.run(main())
