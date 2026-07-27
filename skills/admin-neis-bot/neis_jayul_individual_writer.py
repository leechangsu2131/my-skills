"""
자율활동 누가기록 학생별 개별 입력 스크립트 (순수 기입 전용)
- Phase 1에서 모든 날짜가 완벽히 삭제되었으므로, 불필요한 삭제(btnDelete) 로직을 제외합니다.
- 날짜별로 순회하며:
  1. 날짜를 변경 선택합니다.
  2. 데이터셋이 확실히 갱신될 때까지 대기(최대 5초)합니다.
  3. 이번 날짜의 입력 대상 학생의 speclActSpablMteCn 필드에 자율활동 개별 문장을 setValue로 대입합니다.
  4. 저장 버튼을 누르고 확인 모달을 안전하게 승인하여 물리 저장을 완료합니다.
"""
import asyncio
import io
import json
import os
import re
import sys
import argparse
from playwright.async_api import async_playwright

os.environ["no_proxy"] = "localhost,127.0.0.1"
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

DRAFT_PATH = r"C:\Users\lee21\.gemini\antigravity\scratch\my-skills\skills\admin-neis-bot\data\독서동아리_누가기록_초안 (1).md"

# ==============================================================================
# DATA PARSING
# ==============================================================================

def parse_jayul_table(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    marker = "자율·자치활동 누가기록 초안"
    idx = content.find(marker)
    if idx < 0:
        print(f"Error: '{marker}' 섹션을 찾을 수 없습니다.")
        return []

    section = content[idx:]
    lines = section.split("\n")

    records = []
    for line in lines:
        line = line.strip()
        if not line.startswith("|"):
            continue
        parts = [p.strip() for p in line.split("|")]
        parts = [p for p in parts if p]
        if len(parts) < 4:
            continue
        if parts[0] in ("학생", "---"):
            continue
        if parts[0].startswith("---"):
            continue

        name_raw = parts[0]
        date_str = parts[1]
        content_text = parts[3]

        name = re.sub(r"\(.*?\)", "", name_raw).strip()

        date_match = re.match(r"(\d+)\.(\d+)\.\(", date_str)
        if date_match:
            month = int(date_match.group(1))
            day = int(date_match.group(2))
            act_ymd = f"2026{month:02d}{day:02d}"
        else:
            print(f"Warning: 날짜 파싱 실패 '{date_str}' (학생: {name})")
            continue

        records.append({
            "name": name,
            "date_str": date_str,
            "actYmd": act_ymd,
            "content": content_text
        })

    return records


def group_by_date(records):
    groups = {}
    for r in records:
        key = r["actYmd"]
        if key not in groups:
            groups[key] = {"actYmd": key, "date_str": r["date_str"], "students": []}
        groups[key]["students"].append({"name": r["name"], "content": r["content"]})
    return sorted(groups.values(), key=lambda g: g["actYmd"])


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

# 순수 개별 기입 전용 로직 (삭제 btnDelete 및 체크박스 제어 완전 배제)
JS_APPLY_INDIVIDUAL_WRITE_ONLY = """
(function(targetStudentsJson) {
    var app = cpr.core.Platform.INSTANCE.getAllRunningAppInstances().find(function(ai) {
        return ai.app && ai.app.id === "edu/sw/els/sdl/ce/els_sdlce00_m01";
    });
    if (!app) return {error: "앱 못찾음"};

    var grd = app.lookup("grdMain");
    var ds = grd ? (grd.dataSet || grd._dataSet) : null;
    if (!grd || !ds) return {error: "그리드/데이터셋 못찾음"};

    var targetStudents = targetStudentsJson;
    var targetMap = {};
    for (var i = 0; i < targetStudents.length; i++) {
        targetMap[targetStudents[i].name] = targetStudents[i].content;
    }

    var appliedList = [];
    for (var r = 0; r < ds.getRowCount(); r++) {
        var name = ds.getValue(r, "stuFlnm") || "";
        if (targetMap.hasOwnProperty(name)) {
            ds.setValue(r, "speclActSpablMteCn", targetMap[name]);
            appliedList.push(name);
        }
    }

    grd.redraw();
    return {
        success: true, 
        applied: appliedList,
        totalRows: ds.getRowCount()
    };
})(%TARGET_STUDENTS_JSON%);
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
    parser = argparse.ArgumentParser(description="자율활동 누가기록 개별 입력 스크립트")
    parser.add_argument("--limit", type=int, default=999, help="처리할 날짜그룹 개수 제한")
    parser.add_argument("--apply", action="store_true", help="실제 저장 실행")
    args = parser.parse_args()

    # 1. 데이터 파싱
    records = parse_jayul_table(DRAFT_PATH)
    if not records:
        print("Error: 자율·자치활동 데이터를 파싱하지 못했습니다.")
        return

    date_groups = group_by_date(records)

    print("=" * 60)
    print(" 자율활동 개별 기입 프로세스 (순수 기입 전용)")
    print(f"  - 모드: {'실반영 (APPLY)' if args.apply else '드라이런 (DRY RUN)'}")
    print(f"  - 학생 수: {len(records)}명")
    print(f"  - 날짜 그룹: {len(date_groups)}개")
    print(f"  - 제한: {args.limit}개 날짜그룹")
    print("=" * 60)

    # 2. 브라우저 연결
    async with async_playwright() as p:
        try:
            browser = await p.chromium.connect_over_cdp("http://127.0.0.1:9222")
        except Exception as e:
            print(f"Error: 크롬 9222 포트 연결 실패 ({e})")
            return

        target_page = None
        for ctx in browser.contexts:
            for pg in ctx.pages:
                try:
                    has_cpr = await pg.evaluate("typeof cpr !== 'undefined'")
                except:
                    has_cpr = False
                if has_cpr:
                    target_page = pg
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

        # 3. 날짜 목록 수집
        neis_dates = await target_page.evaluate(JS_GET_DATES)
        if isinstance(neis_dates, dict) and "error" in neis_dates:
            print(f"Error: {neis_dates['error']}")
            return

        date_idx_map = {d["actYmd"]: d["idx"] for d in neis_dates}
        print(f" - 나이스 활동일자 {len(neis_dates)}개 로드 완료")

        # 4. 날짜그룹별 처리
        processed = 0

        for g in date_groups:
            if processed >= args.limit:
                print(f"\n - 지정된 한도({args.limit}개)에 도달하여 작업을 종료합니다.")
                break

            act_ymd = g["actYmd"]
            if act_ymd not in date_idx_map:
                print(f"\n⚠️ 날짜 {g['date_str']} ({act_ymd})가 나이스 목록에 없으므로 건너뜁니다.")
                continue

            date_idx = date_idx_map[act_ymd]
            student_names = ", ".join(s["name"] for s in g["students"])
            print(f"\n[{processed+1}/{len(date_groups)}] {g['date_str']} ({act_ymd}) 처리 중...")
            print(f"   - 개별 기입 대상: {student_names}")

            # 날짜 선택
            await target_page.evaluate(JS_SELECT_DATE.replace("%DATE_IDX%", str(date_idx)))
            
            # 데이터 로드 대기 (최대 5초)
            loaded = False
            for wait_i in range(10):
                await asyncio.sleep(0.5)
                check = await target_page.evaluate(
                    JS_CHECK_DATA_LOADED.replace("%EXPECTED_YMD%", act_ymd)
                )
                if check.get("loaded"):
                    loaded = True
                    break
            
            if not loaded:
                print("   ⚠️ 데이터셋 갱신 대기 타임아웃, 1.5초 강제 대기 후 데이터 대입을 시도합니다.")
                await asyncio.sleep(1.5)

            # 학생별 개별 기입 처리
            apply_js = JS_APPLY_INDIVIDUAL_WRITE_ONLY.replace(
                "%TARGET_STUDENTS_JSON%", json.dumps(g["students"], ensure_ascii=False)
            )
            apply_res = await target_page.evaluate(apply_js)
            if isinstance(apply_res, dict) and "error" in apply_res:
                print(f"   ❌ 데이터 변경 중 오류 발생: {apply_res['error']}")
                continue

            # 로깅
            for app_name in apply_res.get("applied", []):
                print(f"   ✏️ 기입 완료: {app_name}")

            # 저장
            if args.apply:
                print("   - [저장] 현재 날짜 변경사항 저장 중...")
                await target_page.evaluate(JS_SAVE)
                await asyncio.sleep(1.0)
                # 다중 모달창 닫기
                for _ in range(4):
                    await dismiss_all_dialogs(target_page)
                    await asyncio.sleep(0.5)
                print("   ✅ 저장 완료!")
            else:
                print("   - [드라이런] 가입력 완료 (저장 안 함)")

            await dismiss_all_dialogs(target_page)
            processed += 1

        # 전체 완료 후 조회하여 그리드 리셋
        if args.apply:
            print("\n- 모든 날짜 적용 완료 후 조회를 눌러 상태를 갱신합니다.")
            await target_page.evaluate(JS_REQUERY)
            await asyncio.sleep(1.5)
            await dismiss_all_dialogs(target_page)

        print("\n" + "=" * 60)
        print(f" {'🎉 모든 처리가 성공적으로 완결되었습니다' if args.apply else '[드라이런 완료]'}")
        print(f" 처리된 날짜 그룹 수: {processed}개")
        print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())
