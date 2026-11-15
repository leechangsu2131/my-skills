"""사용법:
  python -m schooltodo sync     공용 시트 -> 일정DB (새 일정만 추가)
  python -m schooltodo morning  일정DB -> 아침 카톡
시험: --db-csv/--week-csv/--today-csv/--today/--dry-run 으로 자격증명 없이 돌려볼 수 있다.
"""
from __future__ import annotations

import argparse
import os
import time
from datetime import date, datetime
from zoneinfo import ZoneInfo

from .classify import load_config
from .db import CsvDb, SheetsDb, need
from .envload import load_env, update_env_value
from .kakao import KakaoError, refresh_access_token, send_friends, send_memo
from .message import build_message, split_message
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


def cmd_sync(args) -> int:
    today = _today(args)
    cfg = load_config()
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

    db = _open_db(args)
    added = plan_sync(db.rows(), cands, today, cfg)
    verbose = args.dry_run or args.verbose  # 공개 로그에는 일정 내용을 남기지 않는다
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
    lines, count = build_message(db.rows(), today)
    sync_failed = bool(os.environ.get("SYNC_FAILED"))
    if sync_failed:
        lines.append("⚠ 공용 시트 동기화 실패: 일정이 최신이 아닐 수 있어요")
    if os.environ.get("SKIP_IF_EMPTY", "").lower() in ("1", "true") and count == 0 and not sync_failed:
        print("morning: 보낼 일정이 없어 건너뜀")
        return 0

    chunks = split_message(lines)
    if args.dry_run:
        for i, c in enumerate(chunks, 1):
            print(f"----- 메시지 {i}/{len(chunks)} ({len(c)}자) -----\n{c}")
        return 0

    rt_file = _new_rt_path()
    token = refresh_access_token(
        need("KAKAO_REST_API_KEY"),
        need("KAKAO_REFRESH_TOKEN"),
        os.environ.get("KAKAO_CLIENT_SECRET", ""),
        str(rt_file),
    )
    _adopt_new_refresh_token(rt_file)
    friends = [u.strip() for u in os.environ.get("KAKAO_FRIEND_UUIDS", "").split(",") if u.strip()][:5]
    to_me = os.environ.get("KAKAO_SEND_TO_ME", "1").strip().lower() not in ("0", "false", "no")
    if not to_me and not friends:
        raise SystemExit("KAKAO_SEND_TO_ME=0 인데 KAKAO_FRIEND_UUIDS가 비어 있어 보낼 곳이 없습니다.")
    link = os.environ.get("MESSAGE_LINK_URL") or f"https://docs.google.com/spreadsheets/d/{need('DB_SHEET_ID')}"
    for i, c in enumerate(chunks):
        if i:
            time.sleep(1)
        if to_me:
            send_memo(token, c, link)
        if friends:
            send_friends(token, friends, c, link)
    print(f"morning: 카톡 {len(chunks)}통 전송, 일정 {count}건")
    return 0


def _new_rt_path():
    """새 리프레시 토큰 저장 위치. 깃허브 액션(.env 없음)에서는 현재 폴더(워크플로가 여기서 읽음),
    로컬에서는 공용 폴더가 아니라 .env가 있는 OneDrive 폴더에 둔다."""
    from pathlib import Path

    from .envload import ENV_DIRS, resolve_path

    name = os.environ.get("NEW_RT_FILE", "").strip()
    if name:
        return resolve_path(name)
    return (ENV_DIRS[-1] if ENV_DIRS else Path.cwd()) / "new_refresh_token.txt"


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
    load_env()
    p = argparse.ArgumentParser(prog="schooltodo")
    sub = p.add_subparsers(dest="cmd", required=True)
    for name in ("sync", "morning"):
        s = sub.add_parser(name)
        s.add_argument("--db-csv", help="일정DB 대신 읽을 로컬 CSV(읽기 전용, 시험용)")
        s.add_argument("--today", help="오늘 날짜 덮어쓰기 YYYY-MM-DD (시험용)")
        s.add_argument("--dry-run", action="store_true", help="쓰기·전송 없이 결과만 출력")
        if name == "sync":
            s.add_argument("--week-csv", help="주간 일정 CSV 파일(시험용)")
            s.add_argument("--today-csv", help="오늘 일정 CSV 파일(시험용)")
            s.add_argument("--verbose", action="store_true", help="추가할 일정 내용까지 출력")
    args = p.parse_args(argv)
    try:
        return cmd_sync(args) if args.cmd == "sync" else cmd_morning(args)
    except (SourceError, KakaoError) as e:
        print(f"오류: {e}")
        return 1
