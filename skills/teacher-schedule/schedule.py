"""
수업 진도 관리 앱
구글 시트에서 과목/진도 정보를 읽어 동적으로 운영
"""

import os
import sys
import json
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

def connect():
    creds_json = os.getenv("GOOGLE_CREDENTIALS_JSON")
    if creds_json:
        creds_json = creds_json.replace('\\n', '\n')
        creds_dict = json.loads(creds_json, strict=False)
        creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    else:
        creds = Credentials.from_service_account_file(CREDS_PATH, scopes=SCOPES)
        
    gc = gspread.authorize(creds)
    return gc.open_by_key(SHEET_ID).worksheet(SHEET_NAME)

def load_all(ws):
    records = ws.get_all_records()
    for i, r in enumerate(records):
        r["_row"] = i + 2
    return records

def get_subjects(records):
    seen = set()
    subjects = []
    for r in records:
        s = r.get("과목", "").strip()
        if s and s not in seen:
            seen.add(s)
            subjects.append(s)
    return subjects

def get_schedule_by_date(records, target_date: date):
    target_str = target_date.strftime("%Y-%m-%d")
    return [
        r for r in records
        if r.get("계획일", "").strip() == target_str
        and str(r.get("실행여부", "FALSE")).upper() != "TRUE"
    ]

def get_next_class(records, subject: str):
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
    all_lessons = [r for r in records if r.get("과목", "").strip() == subject]
    done = [r for r in all_lessons if str(r.get("실행여부", "FALSE")).upper() == "TRUE"]
    total = len(all_lessons)
    completed = len(done)
    pct = (completed / total * 100) if total > 0 else 0
    return {"과목": subject, "완료": completed, "전체": total, "진도율": f"{pct:.1f}%"}

def mark_done(ws, records, subject: str, target_date: date = None):
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
    base_str = from_date.strftime("%Y-%m-%d") if from_date else ""

    targets = [
        r for r in records
        if r.get("과목", "").strip() == subject
        and str(r.get("실행여부", "FALSE")).upper() != "TRUE"
        and (not base_str or r.get("계획일", "").strip() >= base_str)
    ]

    if not targets:
        print(f"  ⚠️  밀 수 있는 수업이 없습니다. (과목: {subject})")
        return

    updates = []
    for r in targets:
        old_date_str = r.get("계획일", "").strip()
        if not old_date_str: continue
        old_date = date.fromisoformat(old_date_str)
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

def extend_lesson(ws, records, subject: str):
    """현재 미완료 중 가장 빠른 차시를 복제하여 밑에 삽입 (1차시 분량 연장)"""
    next_cls = get_next_class(records, subject)
    if not next_cls:
        print(f"  ⚠️ 연장할 미완료 수업이 없습니다. ({subject})")
        return
        
    idx = next_cls['_row']
    try:
        raw_values = ws.row_values(idx)
        ws.insert_row(raw_values, index=idx + 1)
        print(f"  ⏳ [{subject}] '{next_cls['수업내용']}' 차시가 연장(복제)되었습니다!")
        print(f"     시트의 {idx+1}행에 추가되었으니, 필요시 구글 시트에서 계획일을 조정해 주세요.")
    except Exception as e:
        print(f"  ❌ 연장 처리 실패: {e}")

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

def select_subject(subjects):
    print("\n  과목 선택:")
    for i, sub in enumerate(subjects, 1):
        print(f"    {i}. {sub}")
    print("    0. 뒤로가기")
    
    while True:
        choice = input("  입력 (번호 또는 이름): ").strip()
        if choice == "0" or choice.lower() == "back" or choice == "":
            return None
        if choice.isdigit():
            idx = int(choice)
            if 1 <= idx <= len(subjects):
                return subjects[idx - 1]
        elif choice in subjects:
            return choice
        print("  ⚠️ 잘못된 입력입니다. 다시 선택해주세요.")

def menu(ws, records, subjects):
    today = date.today()
    tomorrow = today + timedelta(days=1)

    while True:
        print(f"\n{'='*50}")
        print(f"  📚 수업 진도 관리  |  {today.strftime('%Y-%m-%d (%a)')}")
        print(f"{'='*50}")
        print("  1. 오늘 수업 확인")
        print("  2. 내일 수업 확인")
        print("  3. 다음 주 수업 확인")
        print("  4. 과목별 다음 차시")
        print("  5. 과목별 진도율")
        print("  6. 수업 완료 처리")
        print("  7. 한 차시 연장 처리")
        print("  8. 날짜 밀기")
        print("  9. 데이터 새로고침")
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
            next_monday = today + timedelta(days=(7 - today.weekday()))
            found_any = False
            for i in range(5):
                d = next_monday + timedelta(days=i)
                lessons = get_schedule_by_date(records, d)
                if lessons:
                    print_schedule(lessons, f"다음 주 수업 ({d.strftime('%Y-%m-%d, %a')})")
                    found_any = True
            if not found_any:
                print("\n  ⚠️ 다음 주에 계획된 미완료 수업이 없습니다.")

        elif choice == "4":
            print_next_classes(records, subjects)

        elif choice == "5":
            print_progress(records, subjects)

        elif choice == "6":
            subject = select_subject(subjects)
            if not subject: continue
            
            all_sub = [r for r in records if r.get("과목", "").strip() == subject]
            done_list = [r for r in all_sub if str(r.get("실행여부", "FALSE")).upper() == "TRUE"]
            pending_list = [r for r in all_sub if str(r.get("실행여부", "FALSE")).upper() != "TRUE"]
            
            print(f"\n  [{subject}] 시트 현황 요약")
            if done_list:
                last = done_list[-1]
                print(f"  ✅ 직전 완료: {last.get('차시')}차시 - {last.get('수업내용')} ({last.get('계획일','')})")
            if pending_list:
                curr = pending_list[0]
                print(f"  🎯 현재 대상: {curr.get('차시')}차시 - {curr.get('수업내용')} ({curr.get('계획일','')})")
                if len(pending_list) > 1:
                    nxt = pending_list[1]
                    print(f"  ⏭️ 다음 예정: {nxt.get('차시')}차시 - {nxt.get('수업내용')} ({nxt.get('계획일','')})")
            
            print("\n  위 정보를 확인하셨습니까?")
            date_input = input("  완료할 날짜 (Enter=위의 '현재 대상' 처리, YYYY-MM-DD=특정날짜): ").strip()
            target = date.fromisoformat(date_input) if date_input else None
            mark_done(ws, records, subject, target)
            records = load_all(ws)

        elif choice == "7":
            subject = select_subject(subjects)
            if not subject: continue
            extend_lesson(ws, records, subject)
            records = load_all(ws)

        elif choice == "8":
            subject = select_subject(subjects)
            if not subject: continue
            
            print("\n  1. 미완료 수업 전체 밀기")
            print("  2. 특정 날짜 이후 수업만 밀기")
            opt = input("  선택 (번호, Enter=1): ").strip()
            
            try:
                days = int(input("  밀어낼 일수 (예: 1 또는 7): ").strip())
            except ValueError:
                print("  ⚠️ 숫자를 입력하세요.")
                continue
                
            from_date = None
            if opt == "2":
                d_str = input("  기준 날짜 (YYYY-MM-DD): ").strip()
                if d_str: from_date = date.fromisoformat(d_str)
                
            push_schedule(ws, records, subject, days, from_date)
            records = load_all(ws)

        elif choice == "9":
            print("  ⟳ 데이터 새로고침 중...")
            records = load_all(ws)
            subjects = get_subjects(records)
            print(f"  ✅ 완료. 과목: {', '.join(subjects)}")

        elif choice == "0":
            print("\n  종료합니다.\n")
            break

        else:
            print("  ⚠️ 잘못된 선택입니다.")


def cli_mode():
    """
    터미널에서 직접 명령어로 실행하는 모드
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
    elif cmd == "nextweek":
        next_monday = today + timedelta(days=(7 - today.weekday()))
        for i in range(5):
            d = next_monday + timedelta(days=i)
            lessons = get_schedule_by_date(records, d)
            if lessons: print_schedule(lessons, f"다음 주 수업 ({d.strftime('%Y-%m-%d, %a')})")
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
        menu(ws, records, subjects)


if __name__ == "__main__":
    cli_mode()
