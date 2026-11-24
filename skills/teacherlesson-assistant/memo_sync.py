"""수업 메모 ↔ Supabase(lesson_memos 표) 동기화. 기본 파이썬(urllib)만 쓴다.

    올리기  from memo_sync import push_session; push_session(session_dict)   # assistant_server.save_session 뒤에서 부를 것
    내려받기 python memo_sync.py pull --if-older 24       # 마지막 내려받기가 24시간 안이면 아무것도 안 함(아침 bat 용)
             python memo_sync.py pull --days 30 | --since 2026-11-01 | --all
    대기열   python memo_sync.py flush                    # 못 올린 것만 다시 올리기

규칙
  * 올리기는 수업 화면을 멈추지 않는다: 시간 제한 5초, 어떤 실패에도 예외를 던지지 않고 결과 dict 를 돌려준다.
    실패하면 데이터 폴더 memo_queue/ 에 쌓아 두고 다음 호출 때 먼저 다시 올린다. 인터넷이 끊겨 있으면
    새 요청을 또 보내지 않고(5초를 두 번 기다리지 않게) 바로 대기열에 넣는다.
  * 같은 메모는 memo_key(고유값)로 한 번만 들어간다. 이미 있는 행은 건드리지 않는다(resolution=ignore-duplicates).
    그래서 다른 PC 가 올린 행의 pc·created_at 이 덮어써지지 않는다.
  * 🙋 학생 발표 메모(kind=student)는 올리지도, 내려받지도 않는다. 녹음 파일도 다루지 않는다.
  * 내려받기는 sessions/<날짜>/<교시>교시_<과목>.json 에 없는 메모만 덧붙인다. 이 PC 에서 쓴 메모와 그 밖의 칸(notice 등)은
    그대로 둔다. 파일이 깨져 읽을 수 없으면 건드리지 않고 건너뛴다.
  * 비밀값(SUPABASE_URL 또는 NEXT_PUBLIC_SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)은 중앙 .env 에서 읽는다.
    값·주소는 출력하지도 기록하지도 않는다(오류 글에는 상태 번호만 쓴다).
  * 이 파일은 assistant_server.py·web/index.html 을 고치지 않는다. 연결은 교사 PC 에서(PR 설명 참고).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
import uuid
from datetime import date, datetime, timedelta
from pathlib import Path

SKILL = "teacherlesson-assistant"
SKILL_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(next(p / "_shared" for p in SKILL_DIR.parents if (p / "_shared" / "skill_env.py").is_file())))
from skill_env import data_dir, load_env  # noqa: E402

TABLE = "lesson_memos"
PUSH_TIMEOUT = 5        # 초. 수업 화면이 인터넷 때문에 멈추지 않게 짧게
PULL_TIMEOUT = 20       # 초. 아침에 한 번 받는 일이라 조금 여유
PAGE = 1000             # 내려받기 한 쪽 크기(PostgREST 기본 상한과 같음)
BATCH = 500             # 올리기 한 번에 보내는 행 수
DEFAULT_DAYS = 14       # --since/--all 이 없으면 오늘부터 이만큼 전 수업 메모부터 받음(늦게 올라온 것도 잡으려고 넉넉히)
SKIP_KINDS = {"student"}  # 학생 기록 표는 따로 정함 → 이 표에는 올리지 않는다
EXTRA_KEYS = ("at", "idx", "delta")   # 화면이 단계 복원·시간 조정에 쓰는 값

_pushed: set[str] = set()   # 이 프로세스에서 이미 올라간 memo_key (자동 저장 때마다 같은 요청을 되풀이하지 않으려고)
_trust_done = False


class SyncError(Exception):
    """올리기·내려받기 실패. 메시지에는 주소·키를 넣지 않는다."""

    def __init__(self, message: str, *, network: bool = False, status: int | None = None):
        super().__init__(message)
        self.network = network   # True 면 연결·시간 초과(다시 시도해도 지금은 안 됨), False 면 서버가 답함
        self.status = status


class ConfigMissing(SyncError):
    pass


# ──────────────────────────── 설정·요청 ────────────────────────────

def _data(data) -> Path:
    return Path(data) if data else data_dir(SKILL)


def _config() -> tuple[str, str]:
    load_env(skill=SKILL)
    url = (os.getenv("SUPABASE_URL") or os.getenv("NEXT_PUBLIC_SUPABASE_URL") or "").rstrip("/")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or ""
    if not url or not key:
        raise ConfigMissing("중앙 .env에 SUPABASE_URL과 SUPABASE_SERVICE_ROLE_KEY가 필요합니다.")
    local = url.startswith(("http://127.0.0.1", "http://localhost"))
    if not (url.startswith("https://") or local):
        raise ConfigMissing("Supabase 주소는 https:// 여야 합니다(키를 평문으로 보내지 않기 위해).")
    return url, key


def _ensure_trust() -> None:
    """학교망처럼 인증서를 바꿔 끼우는 곳을 위해, truststore 가 이미 설치돼 있으면 윈도우 인증서를 쓴다(없으면 기본값)."""
    global _trust_done
    if _trust_done:
        return
    _trust_done = True
    try:
        import truststore
        truststore.inject_into_ssl()
    except Exception:
        pass


def _request(method: str, path: str, *, query: dict | None = None, body=None, prefer: str | None = None, timeout: float):
    url, key = _config()
    full = f"{url}/rest/v1/{path}"
    if query:
        full += "?" + urllib.parse.urlencode(query)
    data = json.dumps(body, ensure_ascii=False).encode("utf-8") if body is not None else None
    headers = {"apikey": key, "Authorization": f"Bearer {key}",
               "Content-Type": "application/json", "Accept": "application/json"}
    if prefer:
        headers["Prefer"] = prefer
    request = urllib.request.Request(full, data=data, method=method, headers=headers)
    _ensure_trust()
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read()
    except urllib.error.HTTPError as exc:
        status = exc.code
        try:
            exc.close()
        except Exception:
            pass
        raise SyncError(f"Supabase가 오류로 답했어요 ({status})", status=status) from None
    except (urllib.error.URLError, OSError):
        # TimeoutError·연결 거부·이름 찾기 실패 모두 여기. 예외 글에 주소가 들어 있을 수 있어 연결하지 않는다(from None).
        raise SyncError("Supabase에 연결하지 못했거나 시간이 지났어요.", network=True) from None
    if not raw or not raw.strip():
        return None
    try:
        return json.loads(raw.decode("utf-8"))
    except ValueError:
        raise SyncError("Supabase 응답 형식이 올바르지 않아요.") from None


# ──────────────────────────── 메모 ↔ 행 ────────────────────────────

def safe_name(text) -> str:
    """assistant_server.safe_name 과 같은 규칙(파일 이름용). 서버를 가져오면 무거워서 같은 식을 여기에 둔다."""
    return re.sub(r'[\\/:*?"<>|\s]+', "_", str(text)).strip("_")[:80] or "x"


def _period_no(value) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def memo_key(day, period, subject, memo: dict) -> str:
    """같은 메모면 어느 PC 에서 계산해도 같은 값. 적은 시각(at)이 없으면 t 로 대신한다."""
    basis = "\x1f".join([str(day), str(_period_no(period)), str(subject),
                         str(memo.get("at") or memo.get("t") or ""), str(memo.get("kind") or ""), str(memo.get("text") or "")])
    return hashlib.sha1(basis.encode("utf-8")).hexdigest()


def _pc_name() -> str:
    return (os.getenv("MEMO_PC") or platform.node() or "pc").strip()[:60]


def rows_for_session(session: dict, pc: str | None = None) -> list[dict]:
    """session_dict(assistant_server.save_session 의 body) → lesson_memos 행들. 학생 메모는 뺀다."""
    day = str(session.get("date") or "")
    date.fromisoformat(day)                      # 날짜가 아니면 ValueError
    period = _period_no(session.get("period"))
    subject = str(session.get("subject") or "")
    pc = pc if pc is not None else _pc_name()
    rows = []
    for memo in session.get("memos") or []:
        if not isinstance(memo, dict):
            continue
        kind = str(memo.get("kind") or "")
        if not kind or kind in SKIP_KINDS:
            continue
        rows.append({
            "date": day, "period": period or None, "subject": subject,
            "record_key": str(session.get("record_key") or ""), "unit": str(session.get("unit") or ""),
            "lesson": str(session.get("lesson") or ""), "title": str(session.get("title") or ""),
            "kind": kind, "text": str(memo.get("text") or ""), "t": str(memo.get("t") or ""), "pc": pc,
            "extra": {k: memo[k] for k in EXTRA_KEYS if memo.get(k) is not None},
            "memo_key": memo_key(day, period, subject, memo),
        })
    return rows


def _post_rows(rows: list[dict], timeout: float) -> None:
    for i in range(0, len(rows), BATCH):
        _request("POST", TABLE, query={"on_conflict": "memo_key"}, body=rows[i:i + BATCH],
                 prefer="resolution=ignore-duplicates,return=minimal", timeout=timeout)


# ──────────────────────────── 올리기·대기열 ────────────────────────────

def _queue_dir(data: Path) -> Path:
    return data / "memo_queue"


def _write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, path)


def _queue_rows(data: Path, session: dict, rows: list[dict]) -> Path:
    """수업(날짜·교시·과목) 하나당 파일 하나. 자동 저장이 계속 실패해도 그 수업의 최신 메모만 남아 대기열이 불어나지 않는다."""
    name = f"{session.get('date')}_{_period_no(session.get('period'))}_{safe_name(session.get('subject') or '')}.json"
    path = _queue_dir(data) / name
    _write_json(path, {"queued_at": datetime.now().isoformat(timespec="seconds"), "rows": rows})
    return path


def flush_queue(data=None, *, timeout: float = PUSH_TIMEOUT) -> dict:
    """대기열 파일을 오래된 순으로 다시 올린다. 예외를 던지지 않는다.
    서버가 오류로 답한 파일은 남겨 두고 다음 파일로 가고, 연결이 안 되면 거기서 멈춘다."""
    result = {"sent": 0, "failed": 0, "network_error": False}
    folder = _queue_dir(_data(data))
    if not folder.is_dir():
        return result
    for path in sorted(folder.glob("*.json")):
        try:
            rows = json.loads(path.read_text(encoding="utf-8")).get("rows") or []
            rows = [r for r in rows if isinstance(r, dict) and r.get("kind") not in SKIP_KINDS]
        except (OSError, ValueError, AttributeError):
            result["failed"] += 1
            continue
        try:
            if rows:
                _post_rows(rows, timeout)
        except ConfigMissing:
            return result
        except SyncError as exc:
            if exc.network:
                result["network_error"] = True
                return result
            result["failed"] += 1
            continue
        _pushed.update(r["memo_key"] for r in rows if r.get("memo_key"))
        try:
            path.unlink()
        except OSError:
            pass
        result["sent"] += 1
    return result


def push_session(session: dict, *, data=None, timeout: float = PUSH_TIMEOUT) -> dict:
    """그 수업의 메모들을 Supabase 에 올린다(memo_key 기준 upsert). 절대 예외를 던지지 않는다.
    돌려주는 status: success(올림) | nothing_new(새 메모 없음) | queued(못 올려 대기열에 넣음) | no_config(.env 없음) | skipped(날짜 이상)"""
    try:
        data = _data(data)
        rows = rows_for_session(session)
    except (ValueError, TypeError, AttributeError):
        return {"status": "skipped", "message": "날짜가 올바르지 않아 메모를 올리지 않았어요."}
    try:
        _config()
    except ConfigMissing as exc:
        # 키가 없으면 대기열에 쌓아도 영영 못 올리니 쌓지 않는다. 메모는 sessions 파일에 그대로 있다.
        return {"status": "no_config", "message": str(exc)}
    try:
        flushed = flush_queue(data, timeout=timeout)       # 먼저 못 올린 것부터
        fresh = [r for r in rows if r["memo_key"] not in _pushed]
        if not fresh:
            return {"status": "nothing_new", "sent": 0, "flushed": flushed["sent"]}
        if flushed["network_error"]:                       # 연결이 안 되는 걸 방금 확인 → 또 기다리지 않고 바로 쌓기
            _queue_rows(data, session, fresh)
            return {"status": "queued", "queued": len(fresh), "message": "인터넷이 안 되어 대기열에 넣었어요."}
        try:
            _post_rows(fresh, timeout)
        except ConfigMissing as exc:
            return {"status": "no_config", "message": str(exc)}
        except SyncError as exc:
            _queue_rows(data, session, fresh)
            return {"status": "queued", "queued": len(fresh), "message": str(exc)}
        _pushed.update(r["memo_key"] for r in fresh)
        return {"status": "success", "sent": len(fresh), "flushed": flushed["sent"]}
    except Exception as exc:  # 수업 화면을 멈추지 않는 것이 먼저. 파일 쓰기 실패 등 예상 밖 오류도 삼킨다
        return {"status": "queued", "queued": 0, "message": f"메모를 올리지 못했어요 ({type(exc).__name__})."}


# ──────────────────────────── 내려받기 ────────────────────────────

def _state_path(data: Path) -> Path:
    return data / "memo_sync_state.json"


def last_pull(data=None) -> datetime | None:
    try:
        raw = json.loads(_state_path(_data(data)).read_text(encoding="utf-8")).get("last_pull")
        return datetime.fromisoformat(raw) if raw else None
    except (OSError, ValueError, AttributeError):
        return None


def pull_due(hours: float, data=None, now: datetime | None = None) -> bool:
    """마지막 내려받기가 hours 시간보다 오래됐거나 기록이 없으면 True."""
    last = last_pull(data)
    if last is None:
        return True
    now = now or datetime.now(last.tzinfo)
    try:
        return now - last >= timedelta(hours=hours)
    except TypeError:        # 시간대 있음/없음 섞임 → 안전하게 다시 받는다
        return True


def _fetch_rows(since: str | None, timeout: float) -> list[dict]:
    out, offset = [], 0
    while True:
        query = {"select": "*", "order": "id.asc", "limit": str(PAGE), "offset": str(offset)}
        if since:
            query["date"] = f"gte.{since}"
        page = _request("GET", TABLE, query=query, timeout=timeout)
        if not isinstance(page, list):
            raise SyncError("Supabase 응답 형식이 올바르지 않아요.")
        out.extend(page)
        if len(page) < PAGE:
            return out
        offset += len(page)


def _memo_from_row(row: dict) -> dict:
    extra = row.get("extra") if isinstance(row.get("extra"), dict) else {}
    memo = {"t": row.get("t") or "", "at": extra.get("at") or row.get("created_at") or "",
            "kind": row["kind"], "text": row.get("text") or ""}
    for key in ("idx", "delta"):
        if key in extra:
            memo[key] = extra[key]
    return memo


def _read_session(path: Path):
    """(내용, 상태). 상태: 'new'(파일 없음) | 'ok' | 'broken'(있는데 읽을 수 없음 → 건드리지 않는다)"""
    if not path.is_file():
        return None, "new"
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return None, "broken"
    return (value, "ok") if isinstance(value, dict) else (None, "broken")


def _merge_group(data: Path, day: str, period_no: int, subject: str, rows: list[dict]) -> tuple[int, int, str]:
    """한 수업의 새 메모를 파일에 합친다. (추가, 건너뜀, 상태) 를 돌려준다."""
    sessions = data / "sessions"
    path = sessions / day / f"{period_no}교시_{safe_name(subject)}.json"
    if not path.resolve().is_relative_to(sessions.resolve()):
        return 0, 0, "broken"
    session, state = _read_session(path)
    if state == "broken":
        return 0, 0, "broken"
    if session is None:
        first = rows[0]
        session = {"date": day, "period": period_no, "subject": subject, "publisher": "",
                   "title": first.get("title") or "", "unit": first.get("unit") or "", "lesson": first.get("lesson") or "",
                   "record_key": first.get("record_key") or "", "memos": [], "notice": ""}
    memos = session.get("memos")
    if not isinstance(memos, list):
        memos = session["memos"] = []
    have = {memo_key(day, period_no, subject, m) for m in memos if isinstance(m, dict)}
    added = skipped = 0
    for row in rows:
        key = row.get("memo_key") or ""
        if key in have:
            skipped += 1
            continue
        memos.append(_memo_from_row(row))
        have.add(key)
        added += 1
    if added:
        # 모든 메모에 적은 시각(at)이 있을 때만 시간순으로 정렬(이 PC 메모와 섞여도 단계 복원이 마지막 단계를 찾도록)
        if all(isinstance(m, dict) and isinstance(m.get("at"), str) and m["at"] for m in memos):
            memos.sort(key=lambda m: m["at"])
        _write_json(path, session)
    return added, skipped, "ok"


def pull(since_date=None, *, data=None, timeout: float = PULL_TIMEOUT) -> dict:
    """Supabase 메모를 받아 sessions/<날짜>/ 파일에 합친다. since_date 이후 수업(없으면 전부). 예외를 던지지 않는다.
    status: success | partial(깨진 파일이 있어 일부 건너뜀) | error | no_config"""
    data = _data(data)
    try:
        since = date.fromisoformat(str(since_date)).isoformat() if since_date else None
        rows = _fetch_rows(since, timeout)
    except ConfigMissing as exc:
        return {"status": "no_config", "message": str(exc)}
    except SyncError as exc:
        return {"status": "error", "message": str(exc)}
    except ValueError:
        return {"status": "error", "message": "내려받을 시작 날짜가 올바르지 않아요."}

    groups: dict[tuple, list[dict]] = {}
    ignored = 0
    for row in rows:
        try:
            if not isinstance(row, dict) or not row.get("kind") or row["kind"] in SKIP_KINDS:
                raise ValueError
            day = date.fromisoformat(str(row.get("date"))).isoformat()
            groups.setdefault((day, _period_no(row.get("period")), str(row.get("subject") or "")), []).append(row)
        except (ValueError, TypeError):
            ignored += 1
    added = skipped = broken = files = 0
    for (day, period_no, subject), group_rows in groups.items():
        a, s, state = _merge_group(data, day, period_no, subject, group_rows)
        added, skipped = added + a, skipped + s
        files += 1 if a else 0
        broken += 1 if state == "broken" else 0
    status = "partial" if broken else "success"
    if not broken:   # 깨진 파일이 남았으면 기록하지 않아 다음에 다시 시도한다(중복은 memo_key 로 걸러짐)
        _write_json(_state_path(data), {"last_pull": datetime.now().astimezone().isoformat(timespec="seconds")})
    return {"status": status, "fetched": len(rows), "added": added, "skipped": skipped,
            "files": files, "ignored": ignored, "broken": broken}


# ──────────────────────────── 명령줄 ────────────────────────────

def _iso_date(text: str) -> str:
    try:
        return date.fromisoformat(text).isoformat()
    except ValueError:
        raise argparse.ArgumentTypeError("날짜는 YYYY-MM-DD 로 적어 주세요.") from None


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="수업 메모 Supabase 동기화")
    sub = parser.add_subparsers(dest="cmd", required=True)
    pl = sub.add_parser("pull", help="Supabase 메모를 받아 sessions 파일에 합치기")
    pl.add_argument("--since", type=_iso_date, help="이 날짜 이후 수업만(YYYY-MM-DD)")
    pl.add_argument("--days", type=int, default=DEFAULT_DAYS, help=f"오늘부터 이만큼 전 수업부터(기본 {DEFAULT_DAYS})")
    pl.add_argument("--all", action="store_true", help="날짜 제한 없이 전부")
    pl.add_argument("--if-older", type=float, metavar="시간", help="마지막 내려받기가 이 시간보다 오래됐을 때만 실행")
    sub.add_parser("flush", help="못 올린 메모(memo_queue)만 다시 올리기")
    args = parser.parse_args(argv)
    data = _data(None)

    if args.cmd == "flush":
        result = flush_queue(data)
        print(f"대기열: {result['sent']}개 올림, 실패 {result['failed']}개" + (" (인터넷 안 됨)" if result["network_error"] else ""))
        return 1 if result["network_error"] or result["failed"] else 0

    if args.if_older is not None and not pull_due(args.if_older, data):
        print(f"마지막 내려받기가 {args.if_older:g}시간 안이라 건너뜁니다.")
        return 0
    flushed = flush_queue(data)                       # 못 올린 것이 있으면 먼저(실패해도 내려받기는 계속)
    if flushed["sent"]:
        print(f"대기열 {flushed['sent']}개를 올렸어요.")
    since = None if args.all else (args.since or (date.today() - timedelta(days=max(args.days, 0))).isoformat())
    result = pull(since, data=data)
    if result["status"] in ("error", "no_config"):
        print(result["message"])
        return 1
    print(f"내려받기: 받은 {result['fetched']}개 중 새 메모 {result['added']}개를 {result['files']}개 수업 파일에 합쳤어요"
          f" (이미 있음 {result['skipped']}개)" + (f" · 깨진 파일 {result['broken']}개는 건드리지 않았어요" if result["broken"] else ""))
    return 0 if result["status"] == "success" else 1


if __name__ == "__main__":
    sys.exit(main())
