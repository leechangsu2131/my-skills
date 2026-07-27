# -*- coding: utf-8 -*-
"""
neis_behavior_entry.py
2026_1학기_행동특성_창체_수정.md 파일에서 18명의 행동특성 및 종합의견을 파싱하여
나이스 행동특성및종합의견 화면(els_sdlbg00_m00)에 일괄 입력합니다.

Usage:
  python scratch/neis_behavior_entry.py --dry-run    # 미리보기
  python scratch/neis_behavior_entry.py --apply      # 실제 저장
"""

from __future__ import annotations
import argparse
import re
import time
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

DATA_FILE = Path(r"C:\Users\lee21\.gemini\antigravity\scratch\my-skills\skills\classmanage-evaluate-to-neis\data\2026_1학기_행동특성_창체_수정.md")
APP_KEYWORD = "els_sdlbg00"

# ─── 평어 파싱 ────────────────────────────────────────────────────────────────
def parse_behavior_opinions(file_path: Path) -> dict[str, str]:
    content = file_path.read_text(encoding="utf-8")
    # "## 행동특성 및 종합의견" 섹션만 추출
    section = re.search(r"## 행동특성 및 종합의견.*?(?=## 창의적 체험활동|---|$)", content, re.DOTALL)
    if not section:
        raise ValueError("행동특성 및 종합의견 섹션을 찾을 수 없습니다.")
    section_text = section.group(0)
    # **번호. 이름** 다음 줄 = 평어
    pattern = re.compile(r"\*\*\d+\.\s*([가-힣a-zA-Z\s]+)\*\*\n([^\n]+)")
    data = {}
    for name, text in pattern.findall(section_text):
        data[name.strip()] = text.strip()
    return data


# ─── 크롬 연결 ────────────────────────────────────────────────────────────────
def connect_cdp():
    opts = Options()
    opts.add_experimental_option("debuggerAddress", "localhost:9222")
    driver = webdriver.Chrome(options=opts)
    print(f"[연결] {driver.title}")
    return driver


def decode(s: str) -> str:
    if not s:
        return ""
    try:
        return s.encode("latin1").decode("euc-kr")
    except Exception:
        return s


def dismiss_alerts(driver):
    from selenium.common.exceptions import NoAlertPresentException
    try:
        alert = driver.switch_to.alert
        print(f"  [alert] 닫기: '{alert.text[:40]}'")
        alert.accept()
        time.sleep(0.5)
        dismiss_alerts(driver)
    except NoAlertPresentException:
        pass


def close_modals(driver):
    try:
        closed = driver.execute_script("""
            var insts = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
            var count = 0;
            insts.filter(function(ai) {
                return ai && ai.app && (ai.app.id === 'app/cmn/confirm' || ai.app.id === 'app/cmn/alert');
            }).forEach(function(m) {
                ['btnOk','btnConfirm','btn_confirm','btnClose','btnYes'].forEach(function(bid) {
                    try {
                        var b = m.lookup(bid);
                        if (b && typeof b.click === 'function') { b.click(); count++; }
                    } catch(e) {}
                });
            });
            return count;
        """)
        if closed:
            print(f"  [모달] {closed}개 닫힘")
    except Exception:
        pass
    dismiss_alerts(driver)


# ─── 앱 탐색 + JS 실행 ────────────────────────────────────────────────────────
def switch_to_app_frame(driver, app_keyword: str) -> bool:
    for handle in driver.window_handles:
        driver.switch_to.window(handle)
        driver.switch_to.default_content()
        try:
            if driver.execute_script("return typeof cpr !== 'undefined';"):
                found = driver.execute_script(f"""
                    var insts = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
                    return insts.some(function(ai) {{
                        return ai && ai.app && ai.app.id && ai.app.id.indexOf('{app_keyword}') >= 0;
                    }});
                """)
                if found:
                    print(f"[위치] 메인 프레임에서 '{app_keyword}' 앱 발견")
                    return True
        except Exception:
            pass
        try:
            frames = driver.find_elements(By.TAG_NAME, "iframe")
            for frame in frames:
                fid = frame.get_attribute("id") or frame.get_attribute("name") or "?"
                try:
                    driver.switch_to.default_content()
                    driver.switch_to.frame(frame)
                    if driver.execute_script("return typeof cpr !== 'undefined';"):
                        found = driver.execute_script(f"""
                            var insts = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
                            return insts.some(function(ai) {{
                                return ai && ai.app && ai.app.id && ai.app.id.indexOf('{app_keyword}') >= 0;
                            }});
                        """)
                        if found:
                            print(f"[위치] iframe '{fid}'에서 '{app_keyword}' 앱 발견")
                            return True
                except Exception:
                    pass
        except Exception:
            pass
    return False


def js_app(driver, app_keyword: str, extra_js: str) -> object:
    script = f"""
        var insts = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
        var inst = null;
        for (var i = 0; i < insts.length; i++) {{
            if (insts[i] && insts[i].app && insts[i].app.id &&
                insts[i].app.id.indexOf('{app_keyword}') >= 0) {{
                inst = insts[i];
                break;
            }}
        }}
        if (!inst) return {{error: 'app not found: {app_keyword}'}};
        {extra_js}
    """
    return driver.execute_script(script)


def get_dataset(driver, app_keyword: str, candidates: list[str]) -> dict | None:
    for ds_name in candidates:
        result = js_app(driver, app_keyword, f"""
            var ds = inst.lookup('{ds_name}');
            if (!ds) return null;
            var cols = ds.getColumnNames ? ds.getColumnNames() : [];
            if (cols.length === 0 && ds.getColCount) {{
                for (var c = 0; c < ds.getColCount(); c++) cols.push(ds.getColID(c));
            }}
            var rows = [];
            for (var r = 0; r < ds.getRowCount(); r++) {{
                var row = {{}};
                for (var j = 0; j < cols.length; j++) row[cols[j]] = ds.getValue(r, cols[j]);
                rows.push(row);
            }}
            return {{ds: '{ds_name}', cols: cols, rows: rows}};
        """)
        if result and isinstance(result, dict) and "cols" in result and result.get("cols"):
            print(f"  [데이터셋] '{ds_name}': {result['cols'][:6]}... ({len(result['rows'])}행)")
            return result
    return None


# ─── 메인 입력 로직 ───────────────────────────────────────────────────────────
def run_behavior_entry(driver, behavior_data: dict[str, str], dry_run: bool = True) -> bool:
    print("\n" + "="*60)
    print("[행동특성] 및 종합의견 입력")
    print("="*60)

    if not switch_to_app_frame(driver, APP_KEYWORD):
        print("  [오류] 행동특성및종합의견 화면이 없습니다.")
        print("  => 나이스에서 [행동특성및종합의견] 메뉴를 열고 [조회]를 눌러주세요.")
        return False

    ds = get_dataset(driver, APP_KEYWORD, ["dsScrgRec", "dsMain", "dsBehavior", "dsStdnt", "dsGnrlzRec"])
    if not ds:
        print("  [오류] 데이터셋을 찾을 수 없습니다. [조회] 버튼을 눌러주세요.")
        return False

    rows = ds["rows"]
    cols = ds["cols"]
    ds_name = ds["ds"]

    # 컬럼 자동 탐색
    name_col = next((c for c in ["stdntNm", "stuFlnm", "studentName", "stu_nm", "stdNm"] if c in cols), None)
    cont_col = next((c for c in ["gnrlzOpiCn", "speclNote", "content", "opi_cn", "cn"] if c in cols), None)

    if not name_col or not cont_col:
        print(f"  [오류] 필수 컬럼 없음. 전체 컬럼: {cols}")
        print("  => 샘플 행:")
        for r in rows[:3]:
            print(f"     {r}")
        return False

    print(f"  컬럼: name={name_col}, content={cont_col}")

    # 각 행 매칭
    updates = []
    unmatched_neis = []
    for i, row in enumerate(rows):
        raw_name = row.get(name_col, "") or ""
        name = decode(raw_name) if raw_name else raw_name
        
        matched_key = None
        for key in behavior_data:
            if key in name or name in key:
                matched_key = key
                break
        
        if matched_key:
            curr = row.get(cont_col, "") or ""
            target = behavior_data[matched_key]
            status = "변경없음" if curr.strip() == target.strip() else "수정필요"
            updates.append({
                "row": i,
                "name": name,
                "key": matched_key,
                "current": curr,
                "target": target,
                "status": status,
            })
        else:
            unmatched_neis.append(f"[{i}] {name}")

    if unmatched_neis:
        print(f"\n  [경고] 파일에서 이름을 찾지 못한 나이스 행: {unmatched_neis}")

    # 파일에 있는데 나이스에 없는 학생
    matched_keys = {u["key"] for u in updates}
    unmatched_file = [k for k in behavior_data if k not in matched_keys]
    if unmatched_file:
        print(f"  [경고] 나이스 목록에 없는 파일 학생: {unmatched_file}")

    need_update = [u for u in updates if u["status"] == "수정필요"]
    no_change = [u for u in updates if u["status"] == "변경없음"]

    print(f"\n  총 {len(updates)}명 매칭, 수정 필요: {len(need_update)}명, 변경 없음: {len(no_change)}명")
    print("\n  [수정 예정]")
    for u in need_update:
        print(f"    [{u['row']}] {u['name']}: {len(u['current'])}자 → {len(u['target'])}자")
        if dry_run:
            print(f"      미리보기: {u['target'][:80]}...")

    if dry_run:
        print("\n  [DRY-RUN] 저장하지 않습니다.")
        return True

    # 실제 저장
    for u in need_update:
        escaped = u["target"].replace("\\", "\\\\").replace("'", "\\'").replace("\n", " ")
        result = js_app(driver, APP_KEYWORD, f"""
            var ds = inst.lookup('{ds_name}');
            if (!ds) return 'ds_not_found';
            ds.setValue({u['row']}, '{cont_col}', '{escaped}');
            return 'ok';
        """)
        print(f"  [{u['name']}] setValue -> {result}")
        time.sleep(0.2)

    # 저장 버튼 클릭
    save_r = js_app(driver, APP_KEYWORD, """
        var btn = inst.lookup('btnSave');
        if (btn && btn.click) { btn.click(); return 'clicked'; }
        return 'btn_not_found';
    """)
    print(f"\n  [저장] btnSave -> {save_r}")
    time.sleep(2)
    close_modals(driver)
    time.sleep(7)
    close_modals(driver)

    # 검증
    modified = js_app(driver, APP_KEYWORD, f"""
        var ds = inst.lookup('{ds_name}');
        return ds ? ds.isModified() : null;
    """)
    if modified is False:
        print("  [완료] 저장 성공 (isModified=false)")
    else:
        print(f"  [주의] isModified={modified} — 화면에서 직접 확인 필요")

    return True


# ─── 진입점 ───────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="행동특성 및 종합의견 일괄 입력")
    parser.add_argument("--dry-run", action="store_true", help="미리보기 (저장 안 함)")
    parser.add_argument("--apply", action="store_true", help="실제 저장")
    args = parser.parse_args()

    if not any([args.dry_run, args.apply]):
        parser.print_help()
        return

    # 평어 파싱
    print(f"[파일] {DATA_FILE}")
    behavior_data = parse_behavior_opinions(DATA_FILE)
    print(f"[파싱] {len(behavior_data)}명 로드: {list(behavior_data.keys())}")

    driver = connect_cdp()
    dry_run = not args.apply

    mode = "DRY-RUN" if dry_run else "APPLY (실제 저장)"
    print(f"\n[모드] {mode}\n")

    try:
        run_behavior_entry(driver, behavior_data, dry_run=dry_run)
    finally:
        driver.quit()

    print("\n[완료]")


if __name__ == "__main__":
    main()
