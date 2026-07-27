# -*- coding: utf-8 -*-
"""
neis_gimjuan_entry.py
김주안 학생의 교과학습발달상황(국어·수학·사회·도덕) 세부능력특기사항과
행동특성 및 종합의견을 나이스에 자동 입력합니다.

Usage:
  python scratch/neis_gimjuan_entry.py --diagnose     # 열린 앱 목록 확인
  python scratch/neis_gimjuan_entry.py --dry-run      # 미리 보기만
  python scratch/neis_gimjuan_entry.py --apply        # 실제 저장
  python scratch/neis_gimjuan_entry.py --apply --subject-only   # 교과평어만
  python scratch/neis_gimjuan_entry.py --apply --behavior-only  # 행동특성만
"""

from __future__ import annotations
import argparse
import time
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

TARGET_NAME = "김주안"

# ─── 평어 데이터 ─────────────────────────────────────────────────────────────────
SUBJECT_DATA = {
    "국어": (
        "감각적 표현을 사용한 시를 읽고 경험을 생생하게 표현하는 말을 찾을 수 있으며 자신의 경험을 함께 말할 수 있음. "
        "상황에 알맞은 표정과 몸짓, 목소리, 말투를 사용하여 이야기하나 발표 상황에서는 부끄러워하는 모습을 보임. "
        "문장의 짜임을 파악하고 서술부를 도움을 받아 찾을 수 있으며, 짜임을 생각하며 이야기를 실감 나게 읽을 수 있음. "
        "중심 문장과 뒷받침 문장을 갖추어 자신을 소개하는 글을 써 보았고, 통일성 있는 문장 쓰기에 도움을 받아 도전하였으며 매체 소통 예절을 익힘. "
        "작품을 읽고 느낀 점을 문장으로 표현하는 데는 어려움을 보여 짧은 낱말 위주로 표현하려는 경향이 있음. "
        "설명을 듣고 중요한 내용을 힌트를 통해 찾아 말할 수 있으며, 영상 자료를 활용한 활동에는 적극적으로 참여함. "
        "인물과 이야기의 흐름을 중심으로 작품을 감상하고 마음을 전하는 글을 짧은 문장으로 써 보았으며, 사실과 의견을 구분하는 활동에 참여함."
    ),
    "수학": (
        "덧셈과 뺄셈의 계산 원리를 알아보고, 다음 과정으로 넘어가는 데 시간이 걸리나 받아올림과 받아내림이 없는 세 자리 수의 덧셈과 뺄셈을 할 수 있음. "
        "선분·반직선·직선을 이해하고 정확하게 구별하며 각을 이해하고 직각을 찾을 수 있음. "
        "직각삼각형·직사각형·정사각형을 이해하고 도형에서 직각을 찾았으며, 이를 이용한 그림을 도움을 받아 완성함. "
        "(몇십몇)×(몇)의 계산 원리를 이해하는 데 어려움이 있어 구구단표를 활용하여 문제를 해결하는 연습을 반복함. "
        "1분과 1초의 관계 및 길이 단위를 읽고 쓸 수 있으며 생활 속 상황에 알맞은 단위를 찾을 수 있고, "
        "교사의 안내에 따라 시간의 덧셈과 뺄셈 원리를 이해하여 계산함. "
        "전체에 대한 부분을 분수로 나타내는 활동에 흥미를 가지고 참여함."
    ),
    "사회": (
        "장소 카드를 통해 개인의 경험을 나누고 장소에 대해 각자 다른 생각을 가질 수 있음을 인지함. "
        "오래된 물건으로 옛날 사람들의 생활모습을 짐작하는 활동에서 잘 생각해내지 못하여 추가적인 지도와 지원이 필요함."
    ),
    "도덕": (
        "성실한 행동을 역할놀이를 통해 연습하고 자신이 세운 계획을 실천하지 못했던 경험을 돌아보는 시간을 가짐. "
        "효의 다양한 실천 방법을 친구들과 함께 탐구하는 과정에 참여하였으며, "
        "기본적인 예절과 관련된 내용을 이해하는 과정에서 교사의 안내가 지속적으로 필요한 수준임."
    ),
}

BEHAVIOR_TEXT = (
    "학기 초에는 큰 소리를 내거나 몸을 흔드는 등 주의가 산만해지는 모습을 보이고 주변 소음에 쉽게 몰입하여 지시에 집중하는 데 어려움을 겪기도 하였으나, "
    "점차 교사의 지시를 성실히 따르며 자신에게 주어진 과제에 집중하여 끝까지 해결해 내려는 모습이 눈에 띄게 늘어나고 있음. "
    "어려운 과제를 마주했을 때도 스스로 도움을 요청하며 차근차근 해결해 나가려는 태도를 보이고, 짝과 함께하는 활동에도 적극적으로 참여함. "
    "학습 준비와 과제 확인을 스스로 하는 습관을 길러간다면 더욱 안정적인 학교생활을 이어갈 것으로 기대됨."
)

# ─── 크롬 연결 ────────────────────────────────────────────────────────────────────
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


def switch_to_cpr_frame(driver, app_keyword: str) -> bool:
    """cpr 네임스페이스가 있고 app_keyword 앱이 실행 중인 프레임으로 전환."""
    handles = driver.window_handles
    for handle in handles:
        driver.switch_to.window(handle)
        driver.switch_to.default_content()
        # 메인 프레임 시도
        try:
            has_cpr = driver.execute_script("return typeof cpr !== 'undefined';")
            if has_cpr:
                found = driver.execute_script(f"""
                    var insts = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
                    return insts.some(function(ai) {{ return ai && ai.app && ai.app.id && ai.app.id.indexOf('{app_keyword}') >= 0; }});
                """)
                if found:
                    print(f"[위치] 메인 프레임에서 '{app_keyword}' 앱 발견")
                    return True
        except Exception:
            pass
        # iframe 순회
        try:
            frames = driver.find_elements(By.TAG_NAME, "iframe")
            for frame in frames:
                fid = frame.get_attribute("id") or frame.get_attribute("name") or "?"
                try:
                    driver.switch_to.default_content()
                    driver.switch_to.frame(frame)
                    has_cpr = driver.execute_script("return typeof cpr !== 'undefined';")
                    if has_cpr:
                        found = driver.execute_script(f"""
                            var insts = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
                            return insts.some(function(ai) {{ return ai && ai.app && ai.app.id && ai.app.id.indexOf('{app_keyword}') >= 0; }});
                        """)
                        if found:
                            print(f"[위치] iframe '{fid}'에서 '{app_keyword}' 앱 발견")
                            return True
                except Exception:
                    pass
        except Exception:
            pass
    return False


def js_find_app(driver, app_keyword: str, extra_js: str = "") -> object:
    """앱을 찾고 추가 JS를 실행합니다."""
    script = f"""
        var insts = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
        var inst = null;
        for (var i = 0; i < insts.length; i++) {{
            if (insts[i] && insts[i].app && insts[i].app.id && insts[i].app.id.indexOf('{app_keyword}') >= 0) {{
                inst = insts[i];
                break;
            }}
        }}
        if (!inst) return {{error: 'app not found: {app_keyword}'}};
        {extra_js}
    """
    return driver.execute_script(script)


def close_modals(driver):
    """eXBuilder6 confirm/alert 모달 모두 닫기."""
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
    except Exception as e:
        pass
    dismiss_alerts(driver)


# ─── 진단 ─────────────────────────────────────────────────────────────────────────
def run_diagnose(driver):
    print("\n[진단] 열린 nexacro 앱 목록")
    handled = set()
    for handle in driver.window_handles:
        driver.switch_to.window(handle)
        driver.switch_to.default_content()
        for ctx in ["main"] + list(range(20)):
            try:
                if ctx != "main":
                    frames = driver.find_elements(By.TAG_NAME, "iframe")
                    if ctx >= len(frames):
                        break
                    driver.switch_to.default_content()
                    driver.switch_to.frame(frames[ctx])
                has_cpr = driver.execute_script("return typeof cpr !== 'undefined';")
                if not has_cpr:
                    continue
                apps = driver.execute_script("""
                    return cpr.core.Platform.INSTANCE.getAllRunningAppInstances()
                        .map(function(ai) { return ai && ai.app ? ai.app.id : null; })
                        .filter(Boolean);
                """)
                if apps:
                    for a in apps:
                        if a not in handled:
                            print(f"  - {a}")
                            handled.add(a)
            except Exception:
                pass


# ─── 데이터셋 탐색 헬퍼 ───────────────────────────────────────────────────────────
def get_dataset(driver, app_keyword: str, ds_candidates: list[str]) -> dict | None:
    for ds_name in ds_candidates:
        result = js_find_app(driver, app_keyword, f"""
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
        if result and not isinstance(result, dict):
            continue
        if result and "cols" in result:
            print(f"  [데이터셋] '{ds_name}': {result['cols'][:6]}... ({len(result['rows'])}행)")
            return result
    return None


# ─── 교과학습발달상황 입력 ────────────────────────────────────────────────────────
def run_subject_entry(driver, dry_run=True):
    print("\n" + "="*60)
    print("[교과] 세부능력특기사항 입력")
    print("="*60)

    # 화면 전환
    APP = "els_scres20"
    if not switch_to_cpr_frame(driver, APP):
        print("  [오류] 교과학습발달상황 화면이 없습니다.")
        print("  => 나이스에서 [교과학습발달상황] 화면을 열고 [조회]를 눌러주세요.")
        return False

    # 데이터셋 찾기
    ds = get_dataset(driver, APP, ["dsGnrlzOpinListByYear", "dsMain", "dsGnrlzOpin", "dsSbjt"])
    if not ds:
        print("  [오류] 데이터셋을 찾을 수 없습니다. [조회] 버튼을 눌러주세요.")
        return False

    rows = ds["rows"]
    cols = ds["cols"]
    ds_name = ds["ds"]

    # 컬럼 자동 탐색
    name_col = next((c for c in ["stdntNm", "stuFlnm", "studentName", "stu_nm"] if c in cols), None)
    subj_col = next((c for c in ["sbjtNm", "sbjtCdNm", "subjectName", "sbjt_nm"] if c in cols), None)
    cont_col = next((c for c in ["gnrlzOpiCn", "speclNote", "content", "opi_cn"] if c in cols), None)

    if not all([name_col, subj_col, cont_col]):
        print(f"  [오류] 필수 컬럼 없음. 전체 컬럼: {cols}")
        print("  => 샘플 행:")
        for r in rows[:3]:
            print(f"     {r}")
        return False

    print(f"  컬럼: name={name_col}, subject={subj_col}, content={cont_col}")

    # 김주안 행 찾기
    updates = []
    for i, row in enumerate(rows):
        raw_name = row.get(name_col, "") or ""
        name = decode(raw_name) if raw_name else raw_name
        raw_subj = row.get(subj_col, "") or ""
        subj = decode(raw_subj) if raw_subj else raw_subj

        if TARGET_NAME in name:
            for target_subj, target_text in SUBJECT_DATA.items():
                if target_subj in subj:
                    curr = row.get(cont_col, "") or ""
                    updates.append({"row": i, "subject": subj, "current": curr, "text": target_text})

    if not updates:
        print(f"  [경고] '{TARGET_NAME}' 행을 찾지 못했습니다.")
        names = list(set(decode(r.get(name_col, "") or "") for r in rows))
        print(f"  => 전체 학생명: {names[:15]}")
        return False

    print(f"\n  수정 예정: {len(updates)}개 과목")
    for u in updates:
        status = "변경없음" if u["current"].strip() == u["text"].strip() else "수정필요"
        print(f"  [{u['row']}] {u['subject']} ({status}, 현재 {len(u['current'])}자 -> 목표 {len(u['text'])}자)")
        if dry_run:
            print(f"       미리보기: {u['text'][:70]}...")

    if dry_run:
        print("\n  [DRY-RUN] 저장하지 않습니다.")
        return True

    # 실제 저장
    for u in updates:
        escaped = u["text"].replace("\\", "\\\\").replace("'", "\\'").replace("\n", " ")
        result = js_find_app(driver, APP, f"""
            var ds = inst.lookup('{ds_name}');
            if (!ds) return 'ds_not_found';
            ds.setValue({u['row']}, '{cont_col}', '{escaped}');
            var grid = inst.lookup('grdCurrByRec') || inst.lookup('grdMain');
            if (grid && grid.redraw) grid.redraw();
            return 'ok:' + ds.isModified();
        """)
        print(f"  [{u['subject']}] setValue -> {result}")
        time.sleep(0.3)

    # 저장 버튼
    save_r = js_find_app(driver, APP, """
        var btn = inst.lookup('btnSave');
        if (btn && btn.click) { btn.click(); return 'clicked'; }
        return 'btn_not_found';
    """)
    print(f"  [저장] btnSave -> {save_r}")
    time.sleep(2)
    close_modals(driver)
    time.sleep(7)
    close_modals(driver)

    # 검증
    modified = js_find_app(driver, APP, f"""
        var ds = inst.lookup('{ds_name}');
        return ds ? ds.isModified() : null;
    """)
    if modified is False:
        print("  [완료] 저장 성공 (isModified=false)")
    else:
        print(f"  [주의] isModified={modified} — 화면에서 직접 확인 필요")

    return True


# ─── 행동특성 및 종합의견 입력 ────────────────────────────────────────────────────
def run_behavior_entry(driver, dry_run=True):
    print("\n" + "="*60)
    print("[행동특성] 및 종합의견 입력")
    print("="*60)

    APP = "els_sdlbg00_m00"
    if not switch_to_cpr_frame(driver, APP):
        print("  [오류] 행동특성및종합의견 화면이 없습니다.")
        print("  => 나이스에서 [행동특성및종합의견] 메뉴를 열고 [조회]를 눌러주세요.")
        return False

    ds = get_dataset(driver, APP, ["dsScrgRec", "dsMain", "dsBehavior"])
    if not ds:
        print("  [오류] 데이터셋을 찾을 수 없습니다.")
        return False

    rows = ds["rows"]
    cols = ds["cols"]
    ds_name = ds["ds"]

    name_col = next((c for c in ["stdntNm", "stuFlnm", "studentName"] if c in cols), None)
    cont_col = next((c for c in ["gnrlzOpiCn", "speclNote", "content"] if c in cols), None)

    if not name_col or not cont_col:
        print(f"  [오류] 필수 컬럼 없음. 전체 컬럼: {cols}")
        return False

    print(f"  컬럼: name={name_col}, content={cont_col}")

    target_row = None
    curr_text = ""
    for i, row in enumerate(rows):
        raw = row.get(name_col, "") or ""
        name = decode(raw) if raw else raw
        if TARGET_NAME in name:
            target_row = i
            curr_text = row.get(cont_col, "") or ""
            break

    if target_row is None:
        print(f"  [경고] '{TARGET_NAME}'을 찾지 못했습니다.")
        names = [decode(r.get(name_col, "") or "") for r in rows]
        print(f"  => 전체 학생명: {names}")
        return False

    print(f"\n  대상 행: [{target_row}] {TARGET_NAME}")
    print(f"  현재({len(curr_text)}자): {curr_text[:80]}...")
    print(f"  목표({len(BEHAVIOR_TEXT)}자): {BEHAVIOR_TEXT[:80]}...")

    if dry_run:
        print("\n  [DRY-RUN] 저장하지 않습니다.")
        return True

    escaped = BEHAVIOR_TEXT.replace("\\", "\\\\").replace("'", "\\'").replace("\n", " ")
    result = js_find_app(driver, APP, f"""
        var ds = inst.lookup('{ds_name}');
        if (!ds) return 'ds_not_found';
        ds.setValue({target_row}, '{cont_col}', '{escaped}');
        var grid = inst.lookup('grdMain');
        if (grid && grid.redraw) grid.redraw();
        return 'ok:' + ds.isModified();
    """)
    print(f"  [setValue] -> {result}")
    time.sleep(1)

    save_r = js_find_app(driver, APP, """
        var btn = inst.lookup('btnSave');
        if (btn && btn.click) { btn.click(); return 'clicked'; }
        return 'btn_not_found';
    """)
    print(f"  [저장] btnSave -> {save_r}")
    time.sleep(2)
    close_modals(driver)
    time.sleep(7)
    close_modals(driver)

    modified = js_find_app(driver, APP, f"""
        var ds = inst.lookup('{ds_name}');
        return ds ? ds.isModified() : null;
    """)
    if modified is False:
        print("  [완료] 저장 성공 (isModified=false)")
    else:
        print(f"  [주의] isModified={modified} — 화면에서 직접 확인 필요")

    return True


# ─── 메인 ─────────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="김주안 NEIS 평어 입력")
    parser.add_argument("--dry-run", action="store_true", help="미리보기 (저장 안 함)")
    parser.add_argument("--apply", action="store_true", help="실제 저장")
    parser.add_argument("--diagnose", action="store_true", help="열린 앱 목록 확인")
    parser.add_argument("--subject-only", action="store_true", help="교과평어만")
    parser.add_argument("--behavior-only", action="store_true", help="행동특성만")
    args = parser.parse_args()

    if not any([args.dry_run, args.apply, args.diagnose]):
        parser.print_help()
        return

    driver = connect_cdp()
    dry_run = not args.apply

    try:
        if args.diagnose:
            run_diagnose(driver)
            return

        mode = "DRY-RUN" if dry_run else "APPLY (실제 저장)"
        print(f"\n[모드] {mode} | 대상: {TARGET_NAME}\n")

        if not args.behavior_only:
            run_subject_entry(driver, dry_run=dry_run)

        if not args.subject_only:
            run_behavior_entry(driver, dry_run=dry_run)

        print("\n[완료]")

    finally:
        driver.quit()


if __name__ == "__main__":
    main()
