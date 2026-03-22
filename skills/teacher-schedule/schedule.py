"""
수업 진도 관리 앱
구글 시트에서 과목/진도 정보를 읽어 동적으로 운영
"""

import os
import sys
from datetime import date, timedelta
from dotenv import load_dotenv
import gspread
from google.oauth2.service_account import Credentials

load_dotenv()

SHEET_ID = os.getenv("SHEET_ID")
CREDS_PATH = os.getenv("GOOGLE_CREDENTIALS_PATH", "credentials.json")
PDF_BASE_PATH = os.getenv("PDF_BASE_PATH", "./")
SHEET_NAME = os.getenv("SHEET_NAME", "시트1")

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

# ───────────────────────────────────────────────
# 연결 및 데이터 로드
# ───────────────────────────────────────────────

def connect():
    creds = Credentials.from_service_account_file(CREDS_PATH, scopes=SCOPES)
    gc = gspread.authorize(creds)
    return gc.open_by_key(SHEET_ID).worksheet(SHEET_NAME)


def load_all(ws):
    """전체 데이터를 한 번에 로드 (행번호 포함)"""
    records = ws.get_all_records()  # 헤더 기준 dict 리스트
    for i, r in enumerate(records):
        r["_row"] = i + 2  # 실제 시트 행번호 (헤더=1행, 데이터=2행~)
    return records


def get_subjects(records):
    """시트에서 과목 목록 동적 추출 (순서 유지, 중복 제거)"""
    seen = set()
    subjects = []
    for r in records:
        s = r.get("과목", "").strip()
        if s and s not in seen:
            seen.add(s)
            subjects.append(s)
    return subjects


# ───────────────────────────────────────────────
# 조회 기능
# ───────────────────────────────────────────────

def get_schedule_by_date(records, target_date: date):
    """특정 날짜의 미완료 수업 목록"""
    target_str = target_date.strftime("%Y-%m-%d")
    return [
        r for r in records
        if r.get("계획일", "").strip() == target_str
        and str(r.get("실행여부", "FALSE")).upper() != "TRUE"
    ]


def get_next_class(records, subject: str):
    """과목별 다음 차시 (미완료 중 가장 빠른 계획일)"""
    pending = [
        r for r in records
        if r.get("과목", "").strip() == subject
        and str(r.get("실행여부", "FALSE")).upper() != "TRUE"
        and r.get("계획일", "").strip()
    ]
    if not pending:
        return None
    pending.sort(key=lambda x: x.get("계획일", ""))
    return pending[0]


def get_progress(records, subject: str):
    """과목별 진도율"""
    all_lessons = [r for r in records if r.get("과목", "").strip() == subject]
    done = [r for r in all_lessons if str(r.get("실행여부", "FALSE")).upper() == "TRUE"]
    total = len(all_lessons)
    completed = len(done)
    pct = (completed / total * 100) if total > 0 else 0
    return {"과목": subject, "완료": completed, "전체": total, "진도율": f"{pct:.1f}%"}


# ───────────────────────────────────────────────
# 업데이트 기능
# ───────────────────────────────────────────────

def mark_done(ws, records, subject: str, target_date: date = None):
    """
    수업 완료 처리
    - target_date 지정 시 해당 날짜+과목 항목 완료
    - 미지정 시 해당 과목의 다음 차시 완료
    """
    if target_date:
        target_str = target_date.strftime("%Y-%m-%d")
        candidates = [
            r for r in records
            if r.get("과목", "").strip() == subject
            and r.get("계획일", "").strip() == target_str
            and str(r.get("실행여부", "FALSE")).upper() != "TRUE"
        ]
    else:
        next_cls = get_next_class(records, subject)
        candidates = [next_cls] if next_cls else []

    if not candidates:
        print(f"  ⚠️  완료할 수업을 찾지 못했습니다. (과목: {subject})")
        return

    # batch_update로 한 번에 처리
    updates = []
    for r in candidates:
        cell = f"F{r['_row']}"
        updates.append({"range": f"{SHEET_NAME}!{cell}", "values": [["TRUE"]]})

    ws.spreadsheet.values_batch_update({
        "valueInputOption": "RAW",
        "data": updates,
    })

    for r in candidates:
        print(f"  ✅ 완료: [{r['과목']}] {r['수업내용']} ({r['계획일']})")


def push_schedule(ws, records, subject: str, days: int, from_date: date = None):
    """
    특정 과목의 미완료 수업 계획일을 N일 밀기
    from_date 지정 시 해당 날짜 이후만 밀기 (기본: 오늘 이후)
    """
    base = from_date or date.today()
    base_str = base.strftime("%Y-%m-%d")

    targets = [
        r for r in records
        if r.get("과목", "").strip() == subject
        and str(r.get("실행여부", "FALSE")).upper() != "TRUE"
        and r.get("계획일", "").strip() >= base_str
    ]

    if not targets:
        print(f"  ⚠️  밀 수 있는 수업이 없습니다. (과목: {subject}, {base_str} 이후)")
        return

    updates = []
    for r in targets:
        old_date = date.fromisoformat(r["계획일"].strip())
        new_date = old_date + timedelta(days=days)
        cell = f"E{r['_row']}"
        updates.append({
            "range": f"{SHEET_NAME}!{cell}",
            "values": [[new_date.strftime("%Y-%m-%d")]]
        })

    ws.spreadsheet.values_batch_update({
        "valueInputOption": "RAW",
        "data": updates,
    })

    print(f"  📅 [{subject}] {len(targets)}개 수업을 {days}일 밀었습니다.")
    print(f"     ({base_str} 이후 → +{days}일)")


# ───────────────────────────────────────────────
# 출력 헬퍼
# ───────────────────────────────────────────────

def print_schedule(lessons, title: str):
    print(f"\n{'='*50}")
    print(f"  {title}")
    print(f"{'='*50}")
    if not lessons:
        print("  수업 없음 (또는 모두 완료)")
        return
    for r in lessons:
        print(f"  [{r['과목']}] {r['수업내용']}")
        print(f"    대단원: {r['대단원']} | 차시: {r['차시']}")
        if r.get("pdf파일"):
            print(f"    PDF: {r['pdf파일']} (p.{r['시작페이지']}~{r['끝페이지']})")
        print()


def print_next_classes(records, subjects):
    print(f"\n{'='*50}")
    print(f"  과목별 다음 차시")
    print(f"{'='*50}")
    for subject in subjects:
        next_cls = get_next_class(records, subject)
        if next_cls:
            print(f"  [{subject}] {next_cls['수업내용']}")
            print(f"    계획일: {next_cls['계획일']} | 차시: {next_cls['차시']}")
        else:
            print(f"  [{subject}] 모든 진도 완료 🎉")
    print()


def print_progress(records, subjects):
    print(f"\n{'='*50}")
    print(f"  과목별 진도율")
    print(f"{'='*50}")
    for subject in subjects:
        p = get_progress(records, subject)
        bar_len = 20
        filled = int(bar_len * p["완료"] / p["전체"]) if p["전체"] > 0 else 0
        bar = "█" * filled + "░" * (bar_len - filled)
        print(f"  [{subject}] {bar} {p['진도율']} ({p['완료']}/{p['전체']})")
    print()


# ───────────────────────────────────────────────
# 메인 메뉴
# ───────────────────────────────────────────────

def menu(ws, records, subjects):
    today = date.today()
    tomorrow = today + timedelta(days=1)

    while True:
        print(f"\n{'='*50}")
        print(f"  📚 수업 진도 관리  |  {today.strftime('%Y-%m-%d (%a)')}")
        print(f"{'='*50}")
        print("  1. 오늘 수업 확인")
        print("  2. 내일 수업 확인")
        print("  3. 과목별 다음 차시")
        print("  4. 과목별 진도율")
        print("  5. 수업 완료 처리")
        print("  6. 날짜 밀기")
        print("  7. 데이터 새로고침")
        print("  0. 종료")
        print(f"{'='*50}")

        choice = input("  선택: ").strip()

        if choice == "1":
            lessons = get_schedule_by_date(records, today)
            print_schedule(lessons, f"오늘 수업 ({today})")

        elif choice == "2":
            lessons = get_schedule_by_date(records, tomorrow)
            print_schedule(lessons, f"내일 수업 ({tomorrow})")

        elif choice == "3":
            print_next_classes(records, subjects)

        elif choice == "4":
            print_progress(records, subjects)

        elif choice == "5":
            print(f"\n  과목 선택: {', '.join(subjects)}")
            subject = input("  과목: ").strip()
            if subject not in subjects:
                print(f"  ⚠️  '{subject}'은 없는 과목입니다.")
                continue
            date_input = input("  날짜 (Enter=다음 차시, YYYY-MM-DD=특정날짜): ").strip()
            target = date.fromisoformat(date_input) if date_input else None
            mark_done(ws, records, subject, target)
            # 완료 후 데이터 새로고침
            records = load_all(ws)

        elif choice == "6":
            print(f"\n  과목 선택: {', '.join(subjects)}")
            subject = input("  과목: ").strip()
            if subject not in subjects:
                print(f"  ⚠️  '{subject}'은 없는 과목입니다.")
                continue
            try:
                days = int(input("  밀 일수 (예: 7): ").strip())
            except ValueError:
                print("  ⚠️  숫자를 입력하세요.")
                continue
            from_input = input("  시작 날짜 (Enter=오늘, YYYY-MM-DD): ").strip()
            from_date = date.fromisoformat(from_input) if from_input else None
            push_schedule(ws, records, subject, days, from_date)
            records = load_all(ws)

        elif choice == "7":
            print("  ⟳ 데이터 새로고침 중...")
            records = load_all(ws)
            subjects = get_subjects(records)
            print(f"  ✅ 완료. 과목: {', '.join(subjects)}")

        elif choice == "0":
            print("\n  종료합니다.\n")
            break

        else:
            print("  잘못된 선택입니다.")


# ───────────────────────────────────────────────
# CLI 직접 실행 모드
# ───────────────────────────────────────────────

def cli_mode():
    """
    터미널에서 직접 명령어로 실행하는 모드
    사용법:
        python schedule.py today
        python schedule.py tomorrow
        python schedule.py next
        python schedule.py progress
        python schedule.py done 수학
        python schedule.py push 수학 7
    """
    ws = connect()
    records = load_all(ws)
    subjects = get_subjects(records)
    today = date.today()
    tomorrow = today + timedelta(days=1)

    cmd = sys.argv[1] if len(sys.argv) > 1 else None

    if cmd == "today":
        lessons = get_schedule_by_date(records, today)
        print_schedule(lessons, f"오늘 수업 ({today})")

    elif cmd == "tomorrow":
        lessons = get_schedule_by_date(records, tomorrow)
        print_schedule(lessons, f"내일 수업 ({tomorrow})")

    elif cmd == "next":
        print_next_classes(records, subjects)

    elif cmd == "progress":
        print_progress(records, subjects)

    elif cmd == "done" and len(sys.argv) > 2:
        subject = sys.argv[2]
        date_arg = sys.argv[3] if len(sys.argv) > 3 else None
        target = date.fromisoformat(date_arg) if date_arg else None
        mark_done(ws, records, subject, target)

    elif cmd == "push" and len(sys.argv) > 3:
        subject = sys.argv[2]
        days = int(sys.argv[3])
        from_arg = sys.argv[4] if len(sys.argv) > 4 else None
        from_date = date.fromisoformat(from_arg) if from_arg else None
        push_schedule(ws, records, subject, days, from_date)

    else:
        # 명령어 없으면 대화형 메뉴
        menu(ws, records, subjects)


if __name__ == "__main__":
    cli_mode()
