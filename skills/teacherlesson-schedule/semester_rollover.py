"""학기 넘김: 새 학기 지도서 행을 진도표에 붙이고, 지금까지 나간 곳까지 완료 표시한다.

    C:\\Python313\\python.exe semester_rollover.py rollover_3-2.json            # 미리보기
    C:\\Python313\\python.exe semester_rollover.py rollover_3-2.json --apply    # 실제 반영

설정 JSON (예시는 아래 EXAMPLE):
- append: 새로 붙일 과목과 teacherlesson-guide/mapper 결과 파일, 대단원 이름 바꾸기, 순서
- done_until: 과목별로 "여기까지 완료" 기준 (새 행 / 기존 행 모두). 대단원·수업내용 일부 글자로 찾는다
- update_titles: 기존 행의 수업내용·pdf파일을 새 결과로 고칠 과목(예: 도덕 5~8단원)
- close_old_rows: 이 과목들의 기존 행(지난 학기)은 모두 완료 처리
- clear_stale_dates_before: 완료 안 된 행 중 계획일이 이 날짜 이전이면 계획일·계획교시를 비운다(다시 배치되게)

반영 전 진도표 전체를 내 문서\\my-skills-data\\teacherlesson-schedule\\backup_<시각>.json 에 저장한다.
"""
from __future__ import annotations

import json
import pathlib
import re
import sys
import time
from datetime import date

import schedule

sys.path.insert(0, str(next(p / "_shared" for p in pathlib.Path(__file__).resolve().parents if (p / "_shared" / "skill_env.py").is_file())))
from skill_env import data_dir  # noqa: E402

DONE, PLAN_DATE, PLAN_PERIOD = schedule.COLUMN_DONE, schedule.COLUMN_DATE, "계획교시"


def norm(text) -> str:
    return re.sub(r"\s+", "", str(text or ""))


def matches(row: dict, rule: dict) -> bool:
    return norm(rule.get("unit", "")) in norm(row.get("대단원")) and norm(rule.get("title", "")) in norm(row.get("수업내용"))


def load_new_rows(cfg: dict) -> list[dict]:
    out = []
    for spec in cfg.get("append", []):
        data = json.loads(pathlib.Path(spec["rows_file"]).read_text(encoding="utf-8"))
        rows = data["rows"] if isinstance(data, dict) and "rows" in data else data
        if isinstance(rows, dict):
            rows = [r for sub in rows.values() for r in sub]
        rows = [dict(r) for r in rows if r.get("과목") == spec["subject"]]
        for r in rows:
            for old, new in spec.get("rename_units", {}).items():
                if r.get("대단원") == old:
                    r["대단원"] = new
            r["비고"] = spec.get("note", r.get("비고", ""))
            r[DONE] = False
        order = spec.get("unit_order")
        if order:
            rank = {u: i for i, u in enumerate(order)}
            rows.sort(key=lambda r: rank.get(r["대단원"], 999))  # sort 는 안정 정렬이라 단원 안 차시 순서 유지
        out.extend(rows)
    return out


def mark_until(rows: list[dict], rule: dict) -> int:
    """rows 순서대로 rule 에 맞는 마지막 행까지 완료로. 바뀐 개수."""
    idx = max((i for i, r in enumerate(rows) if matches(r, rule)), default=None)
    if idx is None:
        raise ValueError(f"'{rule}'에 맞는 행을 찾지 못했어요.")
    if rule.get("exclusive"):
        idx -= 1
    n = 0
    for r in rows[: idx + 1]:
        if not schedule._is_done(r):
            r[DONE] = True
            n += 1
    return n


def main() -> None:
    cfg = json.loads(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"))
    apply = "--apply" in sys.argv
    ws = schedule.connect()
    # 진도표 머리글이 수업배치 머리글로 덮인 경우가 있어 schedule 의 보정된 열 지도를 쓴다.
    real = ("수업내용", "과목", "대단원", "소단원", "차시", "계획일", "실행여부", "pdf파일",
            "시작페이지", "끝페이지", "비고", "lesson_id", "계획교시")
    col = {k: v for k, v in schedule.get_header_map(ws).items() if k in real}
    print("열 지도:", col)
    if len(set(col.values())) != len(col):
        raise SystemExit("열 지도에 같은 칸을 가리키는 이름이 있어 멈춥니다.")
    width = len(ws.row_values(1))
    raw = ws.get_all_values()[1:]
    records = [{name: (row[idx - 1] if idx - 1 < len(row) else "") for name, idx in col.items()} for row in raw]
    changes: dict[tuple[int, str], object] = {}  # (시트 행, 열 이름) → 값
    report = []

    def setv(row_no: int, key: str, value):
        if key not in col:
            raise ValueError(f"진도표에 '{key}' 열이 없어요.")
        changes[(row_no, key)] = value

    # 1) 지난 학기 행 닫기
    for subject in cfg.get("close_old_rows", []):
        n = 0
        for i, r in enumerate(records, start=2):
            if r.get("과목") == subject and not schedule._is_done(r):
                setv(i, DONE, True)
                n += 1
        report.append(f"[{subject}] 지난 학기 행 {n}개 완료 처리")

    # 2) 기존 행 제목·PDF 고치기 (예: 도덕 2학기 단원)
    new_rows = load_new_rows(cfg)
    existing = {(r.get("과목"), r.get("대단원"), str(r.get("차시")), r.get("비고")) for r in records}
    dup = [r for r in new_rows if (r.get("과목"), r.get("대단원"), str(r.get("차시")), r.get("비고")) in existing]
    if dup:
        raise SystemExit(f"새로 붙일 행 중 {len(dup)}개가 이미 진도표에 있어요(이미 반영한 설정으로 보임). 중복을 막으려고 멈춥니다.")
    for spec in cfg.get("update_titles", []):
        data = json.loads(pathlib.Path(spec["rows_file"]).read_text(encoding="utf-8"))
        src = data["rows"] if isinstance(data, dict) and "rows" in data else data
        if isinstance(src, dict):
            src = [r for sub in src.values() for r in sub]
        src = [r for r in src if r.get("과목") == spec["subject"] and r.get("대단원") in spec["units"]]
        n = 0
        for r_new in src:
            for i, r in enumerate(records, start=2):
                if r.get("과목") == spec["subject"] and r.get("대단원") == r_new["대단원"] and str(r.get("차시")) == str(r_new["차시"]):
                    setv(i, "수업내용", r_new["수업내용"])
                    setv(i, "pdf파일", r_new["pdf파일"])
                    n += 1
        report.append(f"[{spec['subject']}] 기존 행 {n}개 제목·PDF 고침")

    # 3) 기존 행 중 '여기까지 완료' (음악·미술 등)
    for rule in cfg.get("done_until_existing", []):
        rows = [(i, r) for i, r in enumerate(records, start=2) if r.get("과목") == rule["subject"]]
        idx = max((k for k, (_, r) in enumerate(rows) if matches(r, rule)), default=None)
        if idx is None:
            raise ValueError(f"기존 행에서 '{rule}'을 찾지 못했어요.")
        n = 0
        for i, r in rows[: idx + 1]:
            if not schedule._is_done(r):
                setv(i, DONE, True)
                n += 1
        report.append(f"[{rule['subject']}] 기존 행 '{rule.get('title') or rule.get('unit')}'까지 {n}개 완료 처리 (다음: {rows[idx + 1][1].get('수업내용', '')[:30] if idx + 1 < len(rows) else '없음'})")

    # 4) 새 행 완료 표시
    for rule in cfg.get("done_until_new", []):
        rows = [r for r in new_rows if r["과목"] == rule["subject"]]
        n = mark_until(rows, rule)
        nxt = next((r for r in rows if not r[DONE]), None)
        nxt_text = f"{nxt['대단원'][:14]} {nxt['차시']} {nxt['수업내용'][:30]}" if nxt else "없음(모두 완료)"
        report.append(f"[{rule['subject']}] 새 행 {len(rows)}개 중 {n}개 완료 · 다음 수업: {nxt_text}")

    # 5) 지난 계획일 비우기 (완료 안 된 행)
    cutoff = cfg.get("clear_stale_dates_before")
    if cutoff:
        n = 0
        for i, r in enumerate(records, start=2):
            d = str(r.get(PLAN_DATE, ""))[:10]
            done_after = changes.get((i, DONE), schedule._is_done(r))
            if d and d < cutoff and not done_after:
                setv(i, PLAN_DATE, "")
                if PLAN_PERIOD in col:
                    setv(i, PLAN_PERIOD, "")
                n += 1
        report.append(f"완료 안 된 행 중 {cutoff} 이전 계획일 {n}개 비움")

    print("\n".join(report))
    print(f"기존 행 고칠 칸 {len(changes)}개 · 새로 붙일 행 {len(new_rows)}개")
    if not apply:
        print("[미리보기] --apply 를 붙이면 반영합니다.")
        return

    backup = data_dir("teacherlesson-schedule") / f"backup_{time.strftime('%Y%m%d_%H%M%S')}.json"
    backup.write_text(json.dumps({"columns": col, "values": ws.get_all_values()}, ensure_ascii=False), encoding="utf-8")
    print(f"[백업] {backup}")

    import gspread
    cells = [gspread.Cell(row, col[key], ("TRUE" if v is True else "FALSE" if v is False else v)) for (row, key), v in changes.items()]
    if cells:
        ws.update_cells(cells, value_input_option="USER_ENTERED")
    if new_rows:
        values = []
        for r in new_rows:
            line = [""] * width
            for name, idx in col.items():
                v = r.get(name, "")
                line[idx - 1] = "TRUE" if v is True else "FALSE" if v is False else v
            values.append(line)
        ws.append_rows(values, value_input_option="USER_ENTERED")
    print(f"[반영] 칸 {len(cells)}개 수정, 행 {len(new_rows)}개 추가")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
