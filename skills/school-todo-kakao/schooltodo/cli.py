"""사용법:
  python -m schooltodo sync     공용 시트 -> 일정DB (새 일정만 추가)
  python -m schooltodo morning  일정DB -> 아침 카톡 (+ 지정한 요일에 가족 등에게 '출장' 주간 메시지)
  python -m schooltodo friends  카카오 친구의 uuid 조회(받는 사람 등록용, 로컬에서만 실행)
시험: --db-csv/--week-csv/--today-csv/--today/--dry-run 으로 자격증명 없이 돌려볼 수 있다.
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from datetime import date, datetime
from zoneinfo import ZoneInfo

from .classify import load_config
from .db import CsvDb, SheetsDb, need
from .envload import load_env, update_env_value
from .inbox import plan_inbox
from .kakao import KakaoError, list_friends, refresh_access_token, send_friends, send_memo
from . import recipients as rcp
from .message import (
    IMMINENT_DAYS,
    build_message,
    build_weekend_message,
    build_weekly_trips,
    friend_rows,
    one_message,
    split_message,
)
from .sources import SourceError, fetch_rows, parse_today, parse_week, read_csv_file
from .sync import plan_sync


def _today(args) -> date:
    if args.today:
        return date.fromisoformat(args.today)
    return datetime.now(ZoneInfo("Asia/Seoul")).date()


def _open_db(args):
    if args.db_csv:
        args.dry_run = True  # CSV는 읽기 전용
        return CsvDb(args.db_csv)
    return SheetsDb.from_env()


def _load_rows(path: str | None, id_env: str, gid_env: str):
    if path:
        return read_csv_file(path)
    sheet_id = os.environ.get(id_env, "").strip()
    if sheet_id:
        return fetch_rows(sheet_id, os.environ.get(gid_env, "0").strip() or "0")
    return None


def _sync_inbox(db, today, dry_run: bool, verbose: bool) -> list[dict]:
    """'빠른입력' 탭의 새 글을 일정DB 행으로. 공용 시트를 못 읽는 날에도 먼저 처리된다."""
    inbox = db.inbox()
    if inbox is None:
        return []
    items = inbox.pending()
    if not items:
        return []
    keys = {(r.get("키") or "").strip() for r in db.rows()}
    rows, marks = plan_inbox(items, keys, today)
    if verbose:
        for r in rows:
            print(f"  + {r['날짜']} [{r['구분']}|수동] {r['내용']}")
    if not dry_run:
        db.append(rows)
        inbox.mark(marks)
    print(f"inbox: 빠른입력 {len(items)}건 중 새로 추가 {len(rows)}건" + (" (dry-run)" if dry_run else ""))
    return rows


def cmd_sync(args) -> int:
    today = _today(args)
    cfg = load_config()
    db = _open_db(args)
    verbose = args.dry_run or args.verbose  # 공개 로그에는 일정 내용을 남기지 않는다
    pending_inbox = _sync_inbox(db, today, args.dry_run, verbose)  # 원본 시트 읽기보다 먼저

    cands = []
    used = 0
    week = _load_rows(args.week_csv, "SRC_WEEK_SHEET_ID", "SRC_WEEK_GID")
    if week is not None:
        used += 1
        cands += parse_week(week, today)
    tod = _load_rows(args.today_csv, "SRC_TODAY_SHEET_ID", "SRC_TODAY_GID")
    if tod is not None:
        used += 1
        cands += parse_today(tod, today, os.environ.get("MY_NAME", "").strip())
    if not used:
        print("읽을 원본이 없습니다: SRC_WEEK_SHEET_ID 또는 SRC_TODAY_SHEET_ID (또는 --week-csv/--today-csv)")
        return 2

    # dry-run에서는 빠른입력 행이 아직 DB에 없으니 중복 판단에 같이 넣는다
    added = plan_sync(db.rows() + (pending_inbox if args.dry_run else []), cands, today, cfg)
    if verbose:
        for r in added:
            print(f"  + {r['날짜']} [{r['구분']}|{r['대상']}] {r['내용']}")
    if not args.dry_run:
        db.append(added)
    print(f"sync: 원본 {used}곳, 후보 {len(cands)}건, 새로 추가 {len(added)}건" + (" (dry-run)" if args.dry_run else ""))
    return 0


def cmd_morning(args) -> int:
    today = _today(args)
    db = _open_db(args)
    rows = db.rows()
    task_day, imminent_days = _task_settings()
    weekend = today.weekday() >= 5
    if weekend:
        # 주말에는 평소 메시지를 보내지 않고, 오늘 행사(출장 등)가 있을 때만 그것만 보낸다.
        lines, count = build_weekend_message(rows, today)
    else:
        lines, count = build_message(rows, today, task_day=task_day, imminent_days=imminent_days)
    sync_failed = bool(os.environ.get("SYNC_FAILED"))
    skip_if_empty = os.environ.get("SKIP_IF_EMPTY", "").lower() in ("1", "true")
    send_main = not (count == 0 and (weekend or (skip_if_empty and not sync_failed)))
    if send_main and sync_failed:
        lines.append("⚠ 공용 시트 동기화 실패: 일정이 최신이 아닐 수 있어요")

    chunks = split_message(lines) if send_main else []
    env_weekly, weekly_day = _weekly_settings()
    weekly_due = args.weekly or today.weekday() == weekly_day
    wlines, wcount = build_weekly_trips(rows, today)
    rsheet = db.recipients() if hasattr(db, "recipients") else None
    rrows = rsheet.rows() if rsheet else []
    has_weekly = bool(env_weekly) or any(r.get("받기") == rcp.KIND_WEEKLY for r in rrows)
    weekly_ready = weekly_due and has_weekly and wcount > 0
    if args.dry_run:
        if send_main:
            for i, c in enumerate(chunks, 1):
                print(f"----- 메시지 {i}/{len(chunks)} ({len(c)}자) -----\n{c}")
        else:
            print("----- 메시지 없음: " + ("주말이고 오늘 행사가 없어 보내지 않음" if weekend else "보낼 일정이 없어 건너뜀") + " -----")
        if weekly_due:
            if wcount:
                for i, c in enumerate(split_message(wlines), 1):
                    print(f"----- 주간 출장 메시지 {i} ({len(c)}자) -----\n{c}")
            else:
                print("----- 주간 출장 메시지: 이번 주 출장이 없어 보내지 않음 -----")
        env_daily = os.environ.get("KAKAO_FRIEND_UUIDS", "").strip()
        if rrows or env_daily:
            print(_recipient_summary(rrows))
            flines, fcount = (build_weekend_message if weekend else build_message)(friend_rows(rows), today)
            if fcount:
                fm = one_message(flines)
                print(f"----- 친구용 한 통 ({len(fm)}자, 개인 할 일 제외) -----" + chr(10) + fm)
            if weekly_due and wcount:
                wm = one_message(wlines)
                print(f"----- 친구용 주간 출장 한 통 ({len(wm)}자) -----" + chr(10) + wm)
        return 0
    if not send_main and not weekly_ready:
        print("morning: " + ("주말이고 오늘 행사가 없어 건너뜀" if weekend else "보낼 일정이 없어 건너뜀"))
        return 0

    rt_file = _new_rt_path()
    token = refresh_access_token(
        need("KAKAO_REST_API_KEY"),
        need("KAKAO_REFRESH_TOKEN"),
        os.environ.get("KAKAO_CLIENT_SECRET", ""),
        str(rt_file),
    )
    _adopt_new_refresh_token(rt_file)
    to_me = os.environ.get("KAKAO_SEND_TO_ME", "1").strip().lower() not in ("0", "false", "no")
    link = os.environ.get("MESSAGE_LINK_URL") or f"https://docs.google.com/spreadsheets/d/{need('DB_SHEET_ID')}"
    # 1) 내 메시지를 먼저 보낸다. 아래 친구 단계에서 무슨 오류가 나도 이미 간 뒤다.
    if to_me:
        for i, c in enumerate(chunks):
            if i:
                time.sleep(1)
            send_memo(token, c, link)
        if send_main:
            print(f"morning: 카톡 {len(chunks)}통 전송, 일정 {count}건")
    elif send_main:
        print("morning: KAKAO_SEND_TO_ME=0 이라 내 메시지는 보내지 않음")
    # 2) 가족·동료(친구에게 보내기): 오류는 경고만 남기고 실행은 성공으로 끝낸다.
    try:
        _morning_friends(token, db, rsheet, rrows, rows, today, weekend, weekly_due, weekly_ready, wlines, wcount, env_weekly, link)
    except Exception as e:  # noqa: BLE001 - 친구 쪽 실패가 아침 실행 전체를 실패로 만들지 않게
        print(f"⚠ 친구 발송 단계 오류({type(e).__name__}): {e}")
    return 0


def _morning_friends(token, db, rsheet, rrows, rows, today, weekend, weekly_due, weekly_ready, wlines, wcount, env_weekly, link) -> None:
    """가족·동료: 개인 할 일은 빼고, 사람당 하루 한 통(요약 + '자세히 보기' 버튼 → 읽기 전용 페이지)."""
    if rsheet and rcp.needs_lookup(rrows):
        _fill_recipients(token, rsheet, rrows)
    env_daily = [u.strip() for u in os.environ.get("KAKAO_FRIEND_UUIDS", "").split(",") if u.strip()]
    friends = rcp.merge(env_daily, rcp.targets(rrows, rcp.KIND_DAILY))
    flines, fcount = (build_weekend_message if weekend else build_message)(friend_rows(rows), today)
    daily_to = friends if fcount else []
    # 매일 받는 사람은 그날 일정에 출장이 이미 있으니 같은 날 주간 메시지를 또 보내지 않는다(하루 한 통).
    weekly_to = [u for u in rcp.merge(env_weekly, rcp.targets(rrows, rcp.KIND_WEEKLY)) if u not in daily_to] if weekly_ready else []
    if not daily_to and not weekly_to:
        if weekly_due:
            print("morning: 주간 출장 메시지는 보내지 않음(받는 사람 미설정·미확인 또는 출장 없음)")
        return
    if len(daily_to) + len(weekly_to) > rcp.DAILY_QUOTA:
        print(f"⚠ 친구 발송 예정 {len(daily_to) + len(weekly_to)}건이 카카오 하루 한도({rcp.DAILY_QUOTA}건)를 넘을 수 있어요.")
    share = {}
    try:
        share = _share_links(db, flines if daily_to else None, wlines if weekly_to else None, today)
    except Exception as e:  # noqa: BLE001 - 페이지 갱신이 안 돼도 메시지는 보낸다(버튼은 시트 링크)
        print(f"⚠ 공유 페이지 갱신 실패({type(e).__name__}): 버튼은 시트 링크로 보냅니다.")
    failed = 0
    if daily_to:
        failed += _send_to_friends(token, daily_to, one_message(flines), share.get("daily") or link, button_title="자세히 보기")
        print(f"morning: 친구 {len(daily_to)}명에게 한 통" + ("" if share.get("daily") else " (공유 페이지 없음: 시트 링크)"))
    if weekly_to:
        failed += _send_to_friends(token, weekly_to, one_message(wlines), share.get("weekly") or link, button_title="자세히 보기")
        print(f"morning: 주간 출장 메시지 받는 사람 {len(weekly_to)}명, 출장 {wcount}건")
    if failed:
        print(f"⚠ 친구에게 보내기 {failed}번 실패(위 메시지 참고). 내 메시지는 정상 전송됐어요.")


def _new_rt_path():
    """새 리프레시 토큰 저장 위치. 깃허브 액션(.env 없음)에서는 현재 폴더(워크플로가 여기서 읽음),
    로컬에서는 공용 폴더가 아니라 .env가 있는 OneDrive 폴더에 둔다."""
    from pathlib import Path

    from .envload import ENV_DIRS, resolve_path

    name = os.environ.get("NEW_RT_FILE", "").strip()
    if name:
        return resolve_path(name)
    return (ENV_DIRS[-1] if ENV_DIRS else Path.cwd()) / "new_refresh_token.txt"


def _task_settings() -> tuple[int | None, int]:
    """'기한 있는 할 일'을 전부 보여 주는 요일(TASK_DAY: 0=월 … 6=일, 기본 월요일, 'daily'면 매일)과 임박 알림 일수(TASK_IMMINENT_DAYS, 기본 3)."""
    raw = (os.environ.get("TASK_DAY") or "0").strip().lower()
    if raw in ("daily", "매일", "-1"):
        day = None
    else:
        day = int(raw) if raw.isdigit() and 0 <= int(raw) <= 6 else 0
    try:
        imminent = int((os.environ.get("TASK_IMMINENT_DAYS") or str(IMMINENT_DAYS)).strip())
    except ValueError:
        imminent = IMMINENT_DAYS
    return day, max(imminent, 1)


def _send_to_friends(token, uuids, text, link, button_title="일정DB 열기") -> int:
    """5명씩 나눠 보낸다. 실패해도 멈추지 않고 실패 횟수만 돌려준다(내 메시지는 이미 갔으므로)."""
    failed = 0
    for group in rcp.batches(uuids):
        try:
            send_friends(token, group, text, link, button_title=button_title)
        except Exception as e:  # noqa: BLE001 - 네트워크 오류 등도 다음 묶음은 계속 보낸다
            failed += 1
            print(f"⚠ {e}" if isinstance(e, KakaoError) else f"⚠ 친구에게 보내기 오류({type(e).__name__})")
    return failed


def _share_links(db, daily_lines, weekly_lines, today) -> dict[str, str]:
    """'자세히 보기' 페이지 본문을 공유링크 탭에 쓰고 {'daily': 주소, 'weekly': 주소}를 돌려준다.
    탭에 WEBAPP_URL이 없거나 시트가 아니면 빈 dict(→ 예전처럼 시트 링크)."""
    if daily_lines is None and weekly_lines is None:
        return {}
    tab = db.share_tab() if hasattr(db, "share_tab") else None
    if tab is None:
        return {}
    import secrets

    vals = tab.values()
    base = vals.get("WEBAPP_URL", "").strip()
    if not base:
        print("⚠ 공유링크 탭에 WEBAPP_URL이 없어 '자세히 보기'는 시트 링크로 보냅니다.")
        return {}
    updates = {}
    token = vals.get("VIEW_TOKEN", "").strip()
    if not token:
        token = secrets.token_urlsafe(24)
        updates["VIEW_TOKEN"] = token
    out = {}
    if daily_lines is not None:
        updates["DAILY_TEXT"] = "\n".join(daily_lines)
        out["daily"] = rcp.view_link(base, token, "daily")
    if weekly_lines is not None:
        updates["WEEKLY_TEXT"] = "\n".join(weekly_lines)
        out["weekly"] = rcp.view_link(base, token, "weekly")
    now = datetime.now(ZoneInfo("Asia/Seoul")).strftime("%Y-%m-%d %H:%M")
    if "daily" in out:
        updates["DAILY_UPDATED"] = now
    if "weekly" in out:
        updates["WEEKLY_UPDATED"] = now
    tab.save(updates)
    return out


def _fill_recipients(token, rsheet, rrows) -> None:
    """받는사람 탭에서 uuid·이름이 빈 사람을 친구 목록에서 찾아 채운다(실패해도 아침 메시지는 계속)."""
    try:
        changes = rcp.fill_from_friends(rrows, list_friends(token))
        rsheet.write(changes)
    except Exception as e:  # noqa: BLE001 - 시트 쓰기·네트워크 오류여도 이미 확인된 사람에게는 보낸다
        print(f"⚠ 받는 사람 확인 실패: {e}" if isinstance(e, KakaoError) else f"⚠ 받는 사람 확인 실패({type(e).__name__})")
        return
    for kind in (rcp.KIND_DAILY, rcp.KIND_WEEKLY):
        n = rcp.waiting(rrows, kind)
        if n:
            print(f"⚠ '{kind}' 받는 사람 {n}명을 친구 목록에서 못 찾았어요(카톡 친구인지, 앱 멤버인지, 프로필 공개인지 확인).")


def _recipient_summary(rrows) -> str:
    parts = []
    for kind in (rcp.KIND_DAILY, rcp.KIND_WEEKLY):
        ok, wait = len(rcp.targets(rrows, kind)), rcp.waiting(rrows, kind)
        if ok or wait:
            parts.append(f"{kind} {ok}명" + (f"(+확인 대기 {wait}명)" if wait else ""))
    return "----- 받는사람 탭: " + (", ".join(parts) if parts else "받기 설정된 사람 없음") + " -----"


def _weekly_settings() -> tuple[list[str], int]:
    """주간 출장 메시지 받는 사람(WEEKLY_FRIEND_UUIDS, 쉼표로 최대 5명)과 보내는 요일(WEEKLY_DAY, 0=월 ... 6=일, 기본 월)."""
    uuids = [u.strip() for u in os.environ.get("WEEKLY_FRIEND_UUIDS", "").split(",") if u.strip()][:5]
    try:
        day = int((os.environ.get("WEEKLY_DAY") or "0").strip())
    except ValueError:
        day = 0
    return uuids, day if 0 <= day <= 6 else 0


def cmd_friends(args) -> int:
    rt_file = _new_rt_path()
    token = refresh_access_token(
        need("KAKAO_REST_API_KEY"),
        need("KAKAO_REFRESH_TOKEN"),
        os.environ.get("KAKAO_CLIENT_SECRET", ""),
        str(rt_file),
    )
    _adopt_new_refresh_token(rt_file)
    friends = list_friends(token)
    if not friends:
        print("조회된 친구가 없습니다. 상대가 등록 링크로 동의했는지, 내 카카오톡 친구인지, 앱 멤버로 등록됐는지, 프로필이 공개인지 확인하세요.")
        return 0
    print("이 앱에 동의한 카카오톡 친구:")
    for f in friends:
        print(f"  {f['name']}")
    rsheet = None
    try:
        rsheet = SheetsDb.from_env().recipients()
    except SystemExit as e:
        print(f"(시트에 연결하지 못해 받는사람 탭은 건너뜀: {e})")
    if rsheet:
        rrows = rsheet.rows()
        changes = rcp.fill_from_friends(rrows, friends)
        rsheet.write(changes)
        print(f"받는사람 탭: {len({c[0] for c in changes})}명 확인해 채움")
        print(_recipient_summary(rrows))
    else:
        print("받는사람 탭이 없습니다. 등록 링크로 한 명이라도 등록하면 생깁니다.")
    return 0


def _adopt_new_refresh_token(rt_file) -> None:
    """로컬 실행에서 카카오가 새 리프레시 토큰을 줬으면 .env의 그 한 줄만 고친다(토큰은 출력하지 않는다).
    깃허브 액션에는 .env가 없어 아무것도 하지 않고, 워크플로가 파일을 Secret으로 저장한다."""
    try:
        new = rt_file.read_text(encoding="utf-8").strip() if rt_file.is_file() else ""
    except OSError:
        return
    if not new or new == os.environ.get("KAKAO_REFRESH_TOKEN", ""):
        return
    f = update_env_value("KAKAO_REFRESH_TOKEN", new)
    if f is not None:
        rt_file.unlink(missing_ok=True)  # .env에 반영했으니 토큰이 담긴 임시 파일은 지운다
        print(f"[env] 새 리프레시 토큰을 받아 KAKAO_REFRESH_TOKEN 줄만 갱신했습니다: {f}")


def main(argv: list[str] | None = None) -> int:
    # 윈도우 콘솔(cp949)은 이모지를 못 찍어 dry-run이 멈추므로 UTF-8로 출력한다.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    load_env()
    p = argparse.ArgumentParser(prog="schooltodo")
    sub = p.add_subparsers(dest="cmd", required=True)
    for name in ("sync", "morning"):
        s = sub.add_parser(name)
        s.add_argument("--db-csv", help="일정DB 대신 읽을 로컬 CSV(읽기 전용, 시험용)")
        s.add_argument("--today", help="오늘 날짜 덮어쓰기 YYYY-MM-DD (시험용)")
        s.add_argument("--dry-run", action="store_true", help="쓰기·전송 없이 결과만 출력")
        if name == "morning":
            s.add_argument("--weekly", action="store_true", help="요일과 상관없이 주간 출장 메시지도 보냄(시험용)")
        if name == "sync":
            s.add_argument("--week-csv", help="주간 일정 CSV 파일(시험용)")
            s.add_argument("--today-csv", help="오늘 일정 CSV 파일(시험용)")
            s.add_argument("--verbose", action="store_true", help="추가할 일정 내용까지 출력")
    sub.add_parser("friends")
    args = p.parse_args(argv)
    try:
        if args.cmd == "friends":
            return cmd_friends(args)
        return cmd_sync(args) if args.cmd == "sync" else cmd_morning(args)
    except (SourceError, KakaoError) as e:
        print(f"오류: {e}")
        return 1
