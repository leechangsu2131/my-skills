"""
자율활동 누가기록 일괄 삭제 스크립트 (나이스 btnDelete 적용)
- 기존 39개 일자에 입력된 자율활동 내용을 완전히 삭제합니다.
- 각 날짜마다 모든 학생을 체크박스 선택한 뒤, 공식 [btnDelete] (삭제) 버튼을 클릭해 지우고 저장합니다.
"""
import asyncio
import io
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

JS_REQUERY = """
(function() {
    var app = cpr.core.Platform.INSTANCE.getAllRunningAppInstances().find(function(ai) {
        return ai.app && ai.app.id === "edu/sw/els/sdl/ce/els_sdlce00_m01";
    });
    if (!app) return {error: "앱 못찾음"};
    var btn = app.lookup("btnSearch");
    if (btn) { btn.click(); return {success: true}; }
    return {error: "btnSearch 못찾음"};
})();
"""

JS_GET_DATES = """
(function() {
    var app = cpr.core.Platform.INSTANCE.getAllRunningAppInstances().find(function(ai) {
        return ai.app && ai.app.id === "edu/sw/els/sdl/ce/els_sdlce00_m01";
    });
    if (!app) return {error: "앱 못찾음"};
    var ds = app.lookup("dsActYmd");
    if (!ds) return {error: "dsActYmd 못찾음"};
    var dates = [];
    for (var r = 0; r < ds.getRowCount(); r++) {
        dates.push({
            idx: r,
            actYmd: ds.getValue(r, "actYmd"),
            actYmdNm: ds.getValue(r, "actYmdNm"),
            direcInptYn: ds.getValue(r, "direcInptYn")
        });
    }
    return dates;
})();
"""

JS_SELECT_DATE = """
(function(dateIdx) {
    var app = cpr.core.Platform.INSTANCE.getAllRunningAppInstances().find(function(ai) {
        return ai.app && ai.app.id === "edu/sw/els/sdl/ce/els_sdlce00_m01";
    });
    if (!app) return {error: "앱 못찾음"};
    var grd = app.lookup("grdActYmd");
    if (!grd) return {error: "grdActYmd 못찾음"};
    grd.selectRows([dateIdx]);
    if (grd.dispatchEvent) {
        grd.dispatchEvent("selection-change", {row: dateIdx, rowIndex: dateIdx});
    }
    return {success: true};
})(%DATE_IDX%);
"""

JS_CHECK_DATA_LOADED = """
(function(expectedYmd) {
    var app = cpr.core.Platform.INSTANCE.getAllRunningAppInstances().find(function(ai) {
        return ai.app && ai.app.id === "edu/sw/els/sdl/ce/els_sdlce00_m01";
    });
    if (!app) return {loaded: false};
    var grd = app.lookup("grdMain");
    var ds = grd ? (grd.dataSet || grd._dataSet) : null;
    if (!grd || !ds || ds.getRowCount() === 0) return {loaded: false};
    var ymd = ds.getValue(0, "speclActYmd") || "";
    return {loaded: ymd === expectedYmd, actualYmd: ymd, rowCount: ds.getRowCount()};
})("%EXPECTED_YMD%");
"""

JS_CHECK_AND_DELETE_ALL = """
(function() {
    var app = cpr.core.Platform.INSTANCE.getAllRunningAppInstances().find(function(ai) {
        return ai.app && ai.app.id === "edu/sw/els/sdl/ce/els_sdlce00_m01";
    });
    if (!app) return {error: "앱 못찾음"};
    
    var grd = app.lookup("grdMain");
    var ds = grd ? (grd.dataSet || grd._dataSet) : null;
    if (!grd || !ds) return {error: "그리드/데이터셋 못찾음"};

    // 이미 완전히 비어있는지 먼저 감지하여 최적화
    var alreadyEmpty = true;
    for (var r = 0; r < ds.getRowCount(); r++) {
        var val = ds.getValue(r, "speclActSpablMteCn") || "";
        if (val.trim() !== "") {
            alreadyEmpty = false;
            break;
        }
    }

    if (alreadyEmpty) {
        return {success: true, alreadyEmpty: true, rowCount: ds.getRowCount()};
    }
    
    // 전체 체크박스 선택
    grd.checkAllRow(true);
    
    // 삭제 버튼 클릭
    var btnDelete = app.lookup("btnDelete");
    if (!btnDelete) return {error: "btnDelete 못찾음"};
    btnDelete.click();
    
    return {success: true, alreadyEmpty: false, rowCount: ds.getRowCount()};
})();
"""

JS_SAVE = """
(function() {
    var app = cpr.core.Platform.INSTANCE.getAllRunningAppInstances().find(function(ai) {
        return ai.app && ai.app.id === "edu/sw/els/sdl/ce/els_sdlce00_m01";
    });
    if (!app) return {error: "앱 못찾음"};
    var btn = app.lookup("btnSave");
    if (!btn) return {error: "btnSave 못찾음"};
    btn.click();
    return {success: true};
})();
"""

JS_DISMISS_DIALOGS = """
(function() {
    var clicked = 0;
    var closedApps = [];
    var elements = document.querySelectorAll('button, div, span, a');
    elements.forEach(function(el) {
        var text = (el.innerText || el.textContent || "").trim();
        if (text === "확인" || text === "예" || text === "Confirm" || text === "Yes") {
            try { el.click(); clicked++; closedApps.push("DOM:" + text); } catch(e) {}
        }
    });
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
                            try { c.click(); clicked++; closedApps.push(appId + ":" + c.value); } catch(e2) {}
                        }
                    }
                }
            }
        }
    } catch(e) {}
    return {clickedCount: clicked, closed: closedApps};
})();
"""

async def dismiss_all_dialogs(page):
    try:
        res = await page.evaluate(JS_DISMISS_DIALOGS)
        if res and res.get("clickedCount", 0) > 0:
            return True
    except:
        pass
    return False

async def main():
    parser = argparse.ArgumentParser(description="자율활동 누가기록 일괄 삭제")
    parser.add_argument("--limit", type=int, default=999, help="처리할 날짜 개수 제한")
    parser.add_argument("--apply", action="store_true", help="실제 저장 실행")
    args = parser.parse_args()

    print("=" * 60)
    print(f" 자율활동 누가기록 일괄 삭제 (공식 btnDelete 적용)")
    print(f"  - 모드: {'실반영 (APPLY)' if args.apply else '드라이런 (DRY RUN)'}")
    print(f"  - 제한: {args.limit}개 날짜")
    print("=" * 60)

    async with async_playwright() as p:
        try:
            browser = await p.chromium.connect_over_cdp("http://127.0.0.1:9222")
        except Exception as e:
            print(f"Error: 크롬 9222 포트 연결 실패 ({e})")
            return

        target_page = None
        for ctx in browser.contexts:
            for page in ctx.pages:
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
            print("Error: 나이스 화면을 찾을 수 없습니다.")
            return

        print(f" - 연결: '{await target_page.title()}'")
        
        # 조회 초기화
        await dismiss_all_dialogs(target_page)
        await target_page.evaluate(JS_REQUERY)
        await asyncio.sleep(2.0)

        # 날짜 목록 수집
        dates = await target_page.evaluate(JS_GET_DATES)
        if isinstance(dates, dict) and "error" in dates:
            print(f"Error: {dates['error']}")
            return

        target_dates = [d for d in dates if d["direcInptYn"] != "Y"]
        print(f" - 총 {len(dates)}개 중 직접입력 제외 {len(target_dates)}개 삭제 대상")

        processed = 0

        for d in target_dates:
            if processed >= args.limit:
                print(f"\n - 제한({args.limit})에 도달, 종료")
                break

            print(f"\n[{processed+1}/{len(target_dates)}] {d['actYmdNm']}")

            # 날짜 선택
            await target_page.evaluate(JS_SELECT_DATE.replace("%DATE_IDX%", str(d["idx"])))
            
            # 데이터 로드 대기 (최대 5초)
            loaded = False
            for wait_i in range(10):
                await asyncio.sleep(0.5)
                check = await target_page.evaluate(
                    JS_CHECK_DATA_LOADED.replace("%EXPECTED_YMD%", d["actYmd"])
                )
                if check.get("loaded"):
                    loaded = True
                    break
            if not loaded:
                print("   ⚠️ 데이터셋 갱신 대기 타임아웃, 1.5초 강제 대기 후 삭제를 시도합니다.")
                await asyncio.sleep(1.5)

            # 삭제 클릭
            del_res = await target_page.evaluate(JS_CHECK_AND_DELETE_ALL)
            if isinstance(del_res, dict) and "error" in del_res:
                print(f"   ❌ 오류: {del_res['error']}")
                continue

            if del_res.get("alreadyEmpty"):
                print("   - 이미 비어있어 삭제 스킵")
                processed += 1
                continue

            print("   - 모든 학생 체크 및 삭제 클릭 완료")

            # 삭제 확인 팝업 클리어
            await asyncio.sleep(0.5)
            await dismiss_all_dialogs(target_page)

            # 저장
            if args.apply:
                print(f"   - [저장] 삭제 내용 저장 중...")
                await target_page.evaluate(JS_SAVE)
                await asyncio.sleep(1.0)
                for _ in range(4):
                    await dismiss_all_dialogs(target_page)
                    await asyncio.sleep(0.5)
                print(f"   ✅ 저장 완료")
            else:
                print(f"   - [드라이런] 저장 건너뜀")

            await dismiss_all_dialogs(target_page)
            processed += 1

        # 완료 후 재조회
        if args.apply:
            await target_page.evaluate(JS_REQUERY)
            await asyncio.sleep(1.5)
            await dismiss_all_dialogs(target_page)

        print("\n" + "=" * 60)
        print(f" {'🗑️ 삭제 프로세스가 완료되었습니다' if args.apply else '드라이런 완료'}: {processed}개 날짜 처리")
        print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())
