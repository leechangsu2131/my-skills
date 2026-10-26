"""Summarize text from the currently open GBTalk conversation (read-only)."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import pathlib
import re
import sys

BASE = pathlib.Path(__file__).resolve().parent
OUT = BASE / "out"
ARCHIVE = BASE / "inbox"
WINDOW_TITLE_RE = os.getenv("GBTALK_WINDOW_TITLE_RE", r".*(지비톡|GBTalk|gbtalk).*")
DEFAULT_MODEL = "claude-sonnet-4-5"
MAX_CHARS = 60_000
TEXT_CONTROL_TYPES = {"Text", "ListItem", "Edit", "Document", "DataItem"}


def now_tag() -> str:
    return dt.datetime.now().astimezone().strftime("%Y%m%d_%H%M%S")


def find_windows() -> list:
    try:
        from pywinauto import Desktop
    except ImportError as exc:
        raise RuntimeError("pywinauto가 없습니다. `python -m pip install -r requirements.txt`를 실행하세요.") from exc
    try:
        desktop = Desktop(backend="uia")
        matches = desktop.windows(title_re=WINDOW_TITLE_RE, visible_only=True)
        if matches:
            return matches
        # GBTalk's native window class can be more reliable than a localized title.
        return [win for win in desktop.windows(visible_only=True) if win.class_name() == "@Messenger7_MainWnd"]
    except Exception as exc:
        raise RuntimeError(f"Windows UI Automation에서 창 목록을 읽지 못했습니다: {exc}") from exc


def choose_window(index: int):
    wins = find_windows()
    if not wins:
        raise RuntimeError("지비톡 창을 찾지 못했습니다. 지비톡을 열고 창 제목 패턴을 확인하세요.")
    for i, win in enumerate(wins):
        print(f"[{i}] {win.window_text()!r} ({win.class_name()})")
    if index < 0 or index >= len(wins):
        raise RuntimeError(f"창 번호 {index}가 없습니다. 표시된 번호 중 하나를 `--window`에 지정하세요.")
    return wins[index]


def probe(index: int) -> None:
    win = choose_window(index)
    OUT.mkdir(exist_ok=True)
    path = OUT / f"probe_{now_tag()}.txt"
    try:
        rows = []
        for element in win.descendants():
            try:
                info = element.element_info
                label = (info.name or element.window_text() or "").replace("\r", " ").replace("\n", " ").strip()
                rows.append(f"{info.control_type}\t{info.class_name}\t{label}")
            except Exception:
                continue
        path.write_text("\n".join(rows) + "\n", encoding="utf-8")
    except Exception as exc:
        raise RuntimeError(f"컨트롤 트리를 저장하지 못했습니다: {exc}") from exc
    print(f"컨트롤 트리 저장: {path}")
    print("파일에 대화 내용이 보이면 uia 모드를 시험하고, 보이지 않으면 clipboard 모드를 사용하세요.")


def read_uia(index: int) -> str:
    win = choose_window(index)
    lines: list[str] = []
    seen: set[str] = set()
    try:
        descendants = win.descendants()
    except Exception as exc:
        raise RuntimeError(f"지비톡 화면 요소를 읽지 못했습니다: {exc}") from exc
    for element in descendants:
        try:
            if element.element_info.control_type not in TEXT_CONTROL_TYPES:
                continue
            value = (element.window_text() or "").strip()
        except Exception:
            continue
        # Avoid repeated labels without losing repeated message text.
        if value and value not in seen:
            seen.add(value)
            lines.append(value)
    text = "\n".join(lines)
    if len(text.strip()) < 10:
        raise RuntimeError("읽힌 텍스트가 거의 없습니다. 대화방을 열고 clipboard 모드를 사용해 보세요.")
    return text


def read_clipboard() -> str:
    try:
        import pyperclip
        text = pyperclip.paste()
    except ImportError as exc:
        raise RuntimeError("pyperclip이 없습니다. `python -m pip install -r requirements.txt`를 실행하세요.") from exc
    except Exception as exc:
        raise RuntimeError(f"클립보드를 읽지 못했습니다: {exc}") from exc
    if not text or not text.strip():
        raise RuntimeError("클립보드가 비어 있습니다. 지비톡 대화 내용을 복사한 뒤 다시 실행하세요.")
    return text


def load_input(mode: str, path: str | None, index: int) -> str:
    if mode == "uia":
        return read_uia(index)
    if mode == "clipboard":
        return read_clipboard()
    if not path:
        raise RuntimeError("file 모드는 입력 파일 경로가 필요합니다.")
    try:
        return pathlib.Path(path).expanduser().read_text(encoding="utf-8-sig")
    except (OSError, UnicodeError) as exc:
        raise RuntimeError(f"입력 파일을 읽지 못했습니다: {exc}") from exc


def archive_clipboard(title: str | None, period: str, sent_at: str | None) -> pathlib.Path:
    """Append copied note text to a local, date-based Markdown archive."""
    text = read_clipboard().strip()
    now = dt.datetime.now().astimezone()
    if sent_at:
        try:
            now = dt.datetime.fromisoformat(sent_at)
        except ValueError as exc:
            raise RuntimeError("--sent-at 형식은 YYYY-MM-DD HH:MM[:SS]로 입력하세요.") from exc
        if now.tzinfo is None:
            now = now.replace(tzinfo=dt.datetime.now().astimezone().tzinfo)
    if period == "day":
        filename = f"{now:%Y-%m-%d}.md"
    elif period == "week":
        iso = now.isocalendar()
        filename = f"{iso.year}-W{iso.week:02d}.md"
    else:
        filename = f"{now:%Y-%m}.md"
    archive_file = ARCHIVE / filename
    ARCHIVE.mkdir(parents=True, exist_ok=True)
    heading = title.strip() if title and title.strip() else "제목 미입력"
    with archive_file.open("a", encoding="utf-8", newline="\n") as stream:
        if archive_file.stat().st_size:
            stream.write("\n")
        stream.write(f"## {now:%Y-%m-%d %H:%M:%S} — {heading}\n\n{text}\n")
    return archive_file


def _session_path(cutoff: dt.date, period: str) -> pathlib.Path:
    """Return the durable checkpoint path for a collection range."""
    sessions = ARCHIVE / ".sessions"
    sessions.mkdir(parents=True, exist_ok=True)
    return sessions / f"{cutoff.isoformat()}-{period}.json"


def _write_session_state(path: pathlib.Path, state: dict) -> None:
    """Atomically persist a resumable collection checkpoint."""
    state["updated_at"] = dt.datetime.now().astimezone().isoformat(timespec="seconds")
    temp_path = path.with_suffix(path.suffix + ".tmp")
    temp_path.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temp_path.replace(path)


def _archive_path_for(received_at: dt.datetime, period: str) -> pathlib.Path:
    if period == "day":
        filename = f"{received_at:%Y-%m-%d}.md"
    elif period == "week":
        iso = received_at.isocalendar()
        filename = f"{iso.year}-W{iso.week:02d}.md"
    else:
        filename = f"{received_at:%Y-%m}.md"
    return ARCHIVE / filename


def _last_archive_checkpoint(cutoff: dt.date, period: str) -> dict | None:
    """Recover the last physically appended record when resuming an old archive."""
    local_zone = dt.datetime.now().astimezone().tzinfo
    path = _archive_path_for(dt.datetime.combine(cutoff, dt.time(), tzinfo=local_zone), period)
    if not path.exists():
        return None
    pattern = re.compile(r"(?ms)^## (\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) — (.*?)\n\n(.*?)(?=^## |\Z)")
    try:
        contents = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return None
    matches = list(pattern.finditer(contents))
    if not matches:
        return None
    # Archives may have been appended in batches, so the physical last row is
    # not always the oldest row (the correct newest-to-oldest resume boundary).
    match = min(matches, key=lambda row: row.group(1))
    body = match.group(3).strip()
    received_at = dt.datetime.fromisoformat(match.group(1)).replace(tzinfo=local_zone)
    return {
        "received_at": received_at.isoformat(timespec="seconds"),
        "title": match.group(2).strip(),
        "sha256": hashlib.sha256(body.encode("utf-8")).hexdigest(),
        "status": "recovered_from_archive",
        "archive_file": str(path),
    }


def _archive_block(text: str, title: str, received_at: dt.datetime, existing_size: int) -> bytes:
    separator = "\n" if existing_size else ""
    block = f"{separator}## {received_at:%Y-%m-%d %H:%M:%S} — {title}\n\n{text}\n"
    return block.encode("utf-8")


def _archive_prefix_sha256(path: pathlib.Path, length: int) -> str:
    """Hash exactly the existing archive prefix that precedes a pending append."""
    if length == 0:
        return hashlib.sha256(b"").hexdigest()
    digest = hashlib.sha256()
    remaining = length
    try:
        with path.open("rb") as stream:
            while remaining:
                chunk = stream.read(min(1024 * 1024, remaining))
                if not chunk:
                    raise RuntimeError("보관 파일이 체크포인트의 기록 전 크기보다 짧습니다.")
                digest.update(chunk)
                remaining -= len(chunk)
    except OSError as exc:
        raise RuntimeError(f"보관 파일 앞부분을 확인하지 못했습니다: {path} ({exc})") from exc
    return digest.hexdigest()


def _recover_pending_append(checkpoint_path: pathlib.Path, state: dict) -> None:
    """Reconcile an append that may have completed before its checkpoint update."""
    pending = state.get("pending_append")
    if not pending:
        return
    try:
        archive_file = pathlib.Path(pending["archive_file"]).resolve()
        received_at = dt.datetime.fromisoformat(pending["received_at"])
        expected_file = _archive_path_for(received_at, state["period"]).resolve()
        offset = int(pending["offset"])
        size = int(pending["block_size"])
        digest = pending["block_sha256"]
        prefix_digest = pending["prefix_sha256"]
    except (KeyError, TypeError, ValueError, OSError) as exc:
        raise RuntimeError(f"보관 중단 복구 정보가 올바르지 않습니다: {exc}") from exc
    if archive_file != expected_file or offset < 0 or size < 1:
        raise RuntimeError("보관 중단 복구 경로/크기가 예상과 다릅니다. 파일을 직접 확인하세요.")

    current_size = archive_file.stat().st_size if archive_file.exists() else 0
    if current_size < offset:
        raise RuntimeError(
            "보관 파일이 기록 전 크기보다 짧아졌습니다. 기존 내용을 변경하지 않고 중단했습니다. "
            f"{archive_file} (기록 전 크기 {offset}, 현재 크기 {current_size})"
        )
    if _archive_prefix_sha256(archive_file, offset) != prefix_digest:
        raise RuntimeError(
            "보관 파일의 기존 앞부분이 쓰기 의도 기록 후 변경됐습니다. "
            f"파일을 수정하지 않고 중단했습니다: {archive_file}"
        )
    if current_size == offset:
        # The process stopped before any archive bytes were appended.
        state.pop("pending_append", None)
        state["last_error"] = {"message": "이전 보관은 파일에 기록되기 전에 중단됨; 안전하게 재개 가능"}
        _write_session_state(checkpoint_path, state)
        return
    if current_size == offset + size:
        with archive_file.open("rb") as stream:
            stream.seek(offset)
            written = stream.read(size)
        if hashlib.sha256(written).hexdigest() == digest:
            record = {
                "received_at": pending["received_at"],
                "title": pending["title"],
                "sha256": pending["body_sha256"],
                "status": "saved_recovered_after_restart",
                "archive_file": str(archive_file),
            }
            state.setdefault("records", []).append(record)
            state["saved_count"] = int(state.get("saved_count", 0)) + 1
            state["last_saved"] = record
            state["status"] = "in_progress"
            if "input_index" in pending:
                state["batch_next_index"] = int(pending["input_index"]) + 1
                if pending.get("batch_prefix_sha256"):
                    state["batch_prefix_sha256"] = pending["batch_prefix_sha256"]
            state.pop("pending_append", None)
            state.pop("last_error", None)
            _write_session_state(checkpoint_path, state)
            print("직전 실행에서 파일에 완전히 저장된 쪽지를 체크포인트에 복구했습니다.")
            return
    raise RuntimeError(
        "직전 실행의 보관 파일 쓰기가 완전한지 확인할 수 없습니다. "
        f"자동으로 진행하지 않았습니다: {archive_file} (기록 전 크기 {offset}, 현재 크기 {current_size})"
    )


def archive_session(before_date: str, period: str) -> int:
    """Archive copied notes with durable checkpoints and strict date-order checks."""
    try:
        cutoff = dt.date.fromisoformat(before_date)
    except ValueError as exc:
        raise RuntimeError("--before 형식은 YYYY-MM-DD여야 합니다.") from exc

    ARCHIVE.mkdir(parents=True, exist_ok=True)
    checkpoint_path = _session_path(cutoff, period)
    if checkpoint_path.exists():
        try:
            state = json.loads(checkpoint_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"수집 체크포인트를 읽지 못했습니다: {checkpoint_path} ({exc})") from exc
        if state.get("cutoff") != cutoff.isoformat() or state.get("period") != period:
            raise RuntimeError("체크포인트의 기간 설정이 현재 실행과 다릅니다. 파일을 확인하세요.")
        if state.get("status") == "completed":
            print(f"이 기간은 이미 완료 처리되어 있습니다: {checkpoint_path}")
            print(f"완료 확인 기준 쪽지: {state.get('completion_seen_before', '기록 없음')}")
            print("실수로 다시 시작해 중복 저장하지 않도록 여기서 종료합니다.")
            return int(state.get("saved_count", 0))
        _recover_pending_append(checkpoint_path, state)
    else:
        baseline = _last_archive_checkpoint(cutoff, period)
        state = {
            "version": 1,
            "cutoff": cutoff.isoformat(),
            "period": period,
            "status": "in_progress",
            "saved_count": 0,
            "last_saved": baseline,
            "records": [],
        }
        _write_session_state(checkpoint_path, state)

    seen_hashes = existing_archive_hashes()
    session_hashes = {row.get("sha256") for row in state.get("records", [])}
    baseline_record = state.get("last_saved")
    if baseline_record and baseline_record.get("sha256"):
        session_hashes.add(baseline_record["sha256"])
    saved = int(state.get("saved_count", 0))
    last_saved = state.get("last_saved")
    print("\n쪽지 보관 세션을 시작합니다. 본문은 월별 Markdown 파일에 로컬 저장됩니다.")
    print(f"기준일: {cutoff:%Y-%m-%d} 이전 항목을 만나면 완료 처리합니다.")
    if last_saved:
        print("이전 저장 지점:")
        print(f"  {last_saved['received_at']} — {last_saved['title']}")
        print("  재개할 때는 이 항목 다음의 더 오래된 쪽지를 선택하세요. 마지막 저장 항목을 다시 선택해도 중복 확인으로 복구할 수 있습니다.")
    else:
        print("아직 저장된 지점이 없습니다. 목록의 가장 최신 쪽지부터 시작하세요.")
    if state.get("last_error"):
        print(f"직전 중단 사유: {state['last_error'].get('message', '확인 필요')}")
    print("쪽지관리함에서 본문을 복사한 뒤 날짜와 발신자를 입력하세요. 종료는 날짜 입력에 q입니다.\n")

    while True:
        try:
            date_text = input("쪽지 날짜/시각 (YYYY-MM-DD HH:MM[:SS], 종료=q): ").strip()
        except (EOFError, KeyboardInterrupt):
            state["status"] = "paused"
            state["last_error"] = {"message": "사용자 입력으로 중단"}
            _write_session_state(checkpoint_path, state)
            print("입력 중단을 체크포인트에 기록했습니다.")
            break
        if date_text.lower() in {"q", "quit", "끝"}:
            break
        try:
            received_at = dt.datetime.fromisoformat(date_text)
        except ValueError:
            state["status"] = "paused_input_error"
            state["last_error"] = {"input": date_text, "message": "날짜 형식 오류"}
            _write_session_state(checkpoint_path, state)
            print("날짜 형식 오류로 중단하고 체크포인트를 기록했습니다. 예: 2026-10-20 09:30")
            break
        if received_at.tzinfo is None:
            received_at = received_at.replace(tzinfo=dt.datetime.now().astimezone().tzinfo)
        if received_at.date() < cutoff:
            state["status"] = "completed"
            state["completion_seen_before"] = received_at.isoformat(timespec="seconds")
            _write_session_state(checkpoint_path, state)
            print(f"{received_at:%Y-%m-%d}은 기준일보다 이전이므로 세션을 완료 처리합니다. 저장 {saved}건.")
            break

        # The GBTalk inbox is expected to be newest-first. A newer timestamp after
        # a saved item usually means the user moved in the wrong direction.
        if last_saved:
            previous_at = dt.datetime.fromisoformat(last_saved["received_at"])
            if received_at > previous_at:
                state["status"] = "paused_order_error"
                state["last_error"] = {
                    "received_at": received_at.isoformat(timespec="seconds"),
                    "message": "새 쪽지 날짜가 직전 저장 지점보다 최신입니다. 목록 순서를 확인하세요.",
                }
                _write_session_state(checkpoint_path, state)
                print("날짜 순서가 예상과 달라 저장하지 않고 멈췄습니다.")
                print(f"직전 저장: {previous_at:%Y-%m-%d %H:%M:%S} — {last_saved['title']}")
                print(f"현재 입력: {received_at:%Y-%m-%d %H:%M:%S}. 목록에서 더 오래된 쪽지로 이동했는지 확인하세요.")
                break

        try:
            title = input("발신자/제목 (없으면 Enter): ").strip() or "제목 미입력"
            confirm = input("지금 선택한 쪽지 본문을 Ctrl+C로 복사했나요? [y/N]: ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            state["status"] = "paused"
            state["last_error"] = {"message": "사용자 입력으로 중단"}
            _write_session_state(checkpoint_path, state)
            print("입력 중단을 체크포인트에 기록했습니다.")
            break
        if confirm not in {"y", "yes", "ㅛ", "예"}:
            state["status"] = "paused_copy_not_confirmed"
            state["last_error"] = {"received_at": received_at.isoformat(timespec="seconds"), "message": "본문 복사 확인 안 됨"}
            _write_session_state(checkpoint_path, state)
            print("본문 복사 확인이 되지 않아 중단했습니다. 현재 쪽지를 확인한 뒤 재개하세요.")
            break
        try:
            text = read_clipboard().strip()
        except RuntimeError as exc:
            state["status"] = "paused_clipboard_error"
            state["last_error"] = {"received_at": received_at.isoformat(timespec="seconds"), "message": str(exc)}
            _write_session_state(checkpoint_path, state)
            print(f"클립보드 오류로 중단하고 체크포인트를 기록했습니다: {exc}")
            break
        if not text:
            state["status"] = "paused_clipboard_error"
            state["last_error"] = {"received_at": received_at.isoformat(timespec="seconds"), "message": "클립보드가 비어 있음"}
            _write_session_state(checkpoint_path, state)
            print("복사된 본문이 비어 있어 중단했습니다. 다시 복사한 뒤 재개하세요.")
            break
        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
        if digest in session_hashes:
            print("이번 수집 세션에서 이미 저장한 본문입니다. 같은 항목을 다시 선택했는지 확인하세요.")
            duplicate_action = input("같은 쪽지의 재선택이면 s(체크포인트만 갱신), 다른 쪽지면 d(중복 저장), 다시 복사하려면 Enter: ").strip().lower()
            if duplicate_action in {"s", "same", "ㅅ"}:
                record = {
                    "received_at": received_at.isoformat(timespec="seconds"),
                    "title": title,
                    "sha256": digest,
                    "status": "already_saved_checkpoint",
                }
                state.setdefault("records", []).append(record)
                state["last_saved"] = record
                state["status"] = "in_progress"
                state.pop("last_error", None)
                _write_session_state(checkpoint_path, state)
                last_saved = record
                print("기존 저장 항목을 확인하고 재개 지점을 갱신했습니다. 본문을 추가 저장하지 않았습니다.\n")
                continue
            if duplicate_action not in {"d", "different", "ㅇ"}:
                print("저장하지 않았습니다. 같은 쪽지를 다시 복사하거나 다음 항목을 확인하세요.\n")
                continue
        elif digest in seen_hashes:
            print("기존 보관 파일에서 같은 본문을 찾았습니다.")
            duplicate_ok = input("이전 실행에서 저장된 같은 쪽지임을 확인했으면 s, 다른 쪽지라면 d, 다시 복사하려면 Enter: ").strip().lower()
            if duplicate_ok in {"s", "same", "ㅅ"}:
                record = {
                    "received_at": received_at.isoformat(timespec="seconds"),
                    "title": title,
                    "sha256": digest,
                    "status": "already_saved_checkpoint",
                }
                state.setdefault("records", []).append(record)
                state["last_saved"] = record
                state["status"] = "in_progress"
                state.pop("last_error", None)
                _write_session_state(checkpoint_path, state)
                last_saved = record
                print("기존 저장 항목을 확인하고 재개 지점을 갱신했습니다. 본문을 추가 저장하지 않았습니다.\n")
                continue
            if duplicate_ok not in {"d", "different", "ㅇ"}:
                print("저장하지 않았습니다. 지비톡에서 본문을 다시 복사한 뒤 진행하세요.\n")
                continue
        # Archive with the original received timestamp rather than collection time.
        try:
            archive_file = _archive_path_for(received_at, period)
            existing_size = archive_file.stat().st_size if archive_file.exists() else 0
            prefix_digest = _archive_prefix_sha256(archive_file, existing_size) if existing_size else hashlib.sha256(b"").hexdigest()
            block = _archive_block(text, title, received_at, existing_size)
            state["pending_append"] = {
                "received_at": received_at.isoformat(timespec="seconds"),
                "title": title,
                "body_sha256": digest,
                "archive_file": str(archive_file.resolve()),
                "offset": existing_size,
                "prefix_sha256": prefix_digest,
                "block_size": len(block),
                "block_sha256": hashlib.sha256(block).hexdigest(),
            }
            _write_session_state(checkpoint_path, state)
            with archive_file.open("ab") as stream:
                stream.write(block)
                stream.flush()
                os.fsync(stream.fileno())
        except OSError as exc:
            state["status"] = "paused_archive_error"
            state["last_error"] = {"received_at": received_at.isoformat(timespec="seconds"), "message": str(exc)}
            _write_session_state(checkpoint_path, state)
            print(f"보관 파일 쓰기 오류로 멈췄습니다. 현재 쪽지는 저장되지 않았습니다: {exc}")
            break
        seen_hashes.add(digest)
        session_hashes.add(digest)
        saved += 1
        record = {
            "received_at": received_at.isoformat(timespec="seconds"),
            "title": title,
            "sha256": digest,
            "status": "saved",
            "archive_file": str(archive_file),
        }
        state.setdefault("records", []).append(record)
        state["saved_count"] = saved
        state["last_saved"] = record
        state["status"] = "in_progress"
        state.pop("pending_append", None)
        state.pop("last_error", None)
        _write_session_state(checkpoint_path, state)
        last_saved = record
        print(f"보관 완료 ({saved}건): {archive_file}")
        print(f"체크포인트 갱신: {checkpoint_path}")
        print("다음 쪽지로 이동해 본문을 복사한 뒤 계속하세요.\n")
    if state.get("status") == "in_progress":
        state["status"] = "paused"
        _write_session_state(checkpoint_path, state)
    print(f"세션 종료. 이 세션의 실제 신규 저장은 {saved}건입니다.")
    print(f"재개 정보: {checkpoint_path}")
    return saved


def archive_batch(jsonl_path: str, before_date: str, period: str, allow_duplicate_bodies: bool = False) -> int:
    """Archive a verified, newest-to-oldest JSONL capture using resumable checkpoints."""
    try:
        cutoff = dt.date.fromisoformat(before_date)
    except ValueError as exc:
        raise RuntimeError("--before 형식은 YYYY-MM-DD여야 합니다.") from exc

    source = pathlib.Path(jsonl_path).expanduser().resolve()
    try:
        raw = source.read_bytes()
        lines = raw.decode("utf-8-sig").splitlines()
    except (OSError, UnicodeError) as exc:
        raise RuntimeError(f"배치 입력 파일을 읽지 못했습니다: {source} ({exc})") from exc
    if not lines:
        raise RuntimeError("배치 입력 파일이 비어 있습니다.")

    rows: list[dict] = []
    previous_at: dt.datetime | None = None
    local_zone = dt.datetime.now().astimezone().tzinfo
    for line_number, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        try:
            item = json.loads(line)
            if not isinstance(item, dict):
                raise TypeError("각 줄은 JSON 객체여야 합니다")
            if not all(isinstance(item.get(key), str) for key in ("received_at", "title", "body")):
                raise TypeError("received_at, title, body는 문자열이어야 합니다")
            received_at = dt.datetime.fromisoformat(item["received_at"])
            title = re.sub(r"[\r\n\t]+", " ", item["title"]).strip()
            body = item["body"].strip()
        except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
            raise RuntimeError(f"JSONL {line_number}행의 필수 필드/형식이 잘못됐습니다: {exc}") from exc
        if received_at.tzinfo is None:
            received_at = received_at.replace(tzinfo=local_zone)
        if not title or not body:
            raise RuntimeError(f"JSONL {line_number}행의 제목 또는 본문이 비었습니다.")
        if previous_at is not None and received_at > previous_at:
            raise RuntimeError(
                f"JSONL 날짜가 최신 방향으로 역행합니다 ({line_number}행). "
                "쪽지관리함의 수신 시각 기준으로 최신순부터 오래된순으로 정렬하세요."
            )
        previous_at = received_at
        rows.append({
            "received_at": received_at,
            "title": title,
            "body": body,
            "line": line_number,
            "allow_duplicate": item.get("allow_duplicate") is True,
        })
    if not rows:
        raise RuntimeError("유효한 JSONL 쪽지가 없습니다.")

    source_digest = hashlib.sha256(raw).hexdigest()
    ARCHIVE.mkdir(parents=True, exist_ok=True)
    checkpoint_path = _session_path(cutoff, period)
    if checkpoint_path.exists():
        try:
            state = json.loads(checkpoint_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"수집 체크포인트를 읽지 못했습니다: {checkpoint_path} ({exc})") from exc
        if state.get("cutoff") != cutoff.isoformat() or state.get("period") != period:
            raise RuntimeError("체크포인트의 기간 설정이 현재 실행과 다릅니다. 파일을 확인하세요.")
        if state.get("status") == "completed":
            print(f"이 기간은 이미 완료 처리되어 있습니다: {checkpoint_path}")
            return int(state.get("saved_count", 0))
        _recover_pending_append(checkpoint_path, state)
        pinned_digest = state.get("batch_source_sha256")
        if pinned_digest and pinned_digest != source_digest:
            next_index = int(state.get("batch_next_index", 0))
            expected_prefix = state.get("batch_prefix_sha256")
            actual_prefix = _batch_prefix_digest(rows, next_index)
            if not expected_prefix or actual_prefix != expected_prefix:
                raise RuntimeError("재개 입력 파일의 이미 처리한 앞부분이 변경됐습니다. 체크포인트를 확인하세요.")
        if state.get("batch_next_index") is None and pinned_digest:
            raise RuntimeError("배치 재개 인덱스가 체크포인트에 없습니다. 자동으로 진행하지 않습니다.")
    else:
        state = {
            "version": 1,
            "cutoff": cutoff.isoformat(),
            "period": period,
            "status": "in_progress",
            "saved_count": 0,
            "last_saved": _last_archive_checkpoint(cutoff, period),
            "records": [],
            "batch_next_index": 0,
            "batch_prefix_sha256": _batch_prefix_digest(rows, 0),
        }

    state["batch_source_sha256"] = source_digest
    state["batch_total"] = len(rows)
    state.setdefault("batch_next_index", 0)
    state.setdefault("batch_prefix_sha256", _batch_prefix_digest(rows, int(state["batch_next_index"])))
    state["status"] = "in_progress"
    state.pop("last_error", None)
    _write_session_state(checkpoint_path, state)

    saved_this_run = 0
    existing_keys = _existing_archive_record_keys()
    existing_hashes = existing_archive_hashes()
    for record in state.get("records", []):
        if record.get("received_at") and record.get("title") and record.get("sha256"):
            existing_keys.add((record["received_at"][:19], record["title"], record["sha256"]))
            existing_hashes.add(record["sha256"])
    next_index = int(state["batch_next_index"])
    for index in range(next_index, len(rows)):
        item = rows[index]
        received_at = item["received_at"]
        title = item["title"]
        body = item["body"]
        digest = hashlib.sha256(body.encode("utf-8")).hexdigest()
        archive_key = (received_at.strftime("%Y-%m-%d %H:%M:%S"), title, digest)
        if received_at.date() < cutoff:
            state["status"] = "completed"
            state["completion_seen_before"] = received_at.isoformat(timespec="seconds")
            state["batch_next_index"] = index
            _write_session_state(checkpoint_path, state)
            print(f"{received_at:%Y-%m-%d} 쪽지를 확인해 수집 기간 완료로 기록했습니다. 신규 저장 {saved_this_run}건.")
            return saved_this_run
        if archive_key in existing_keys:
            state.setdefault("records", []).append({
                "received_at": received_at.isoformat(timespec="seconds"),
                "title": title,
                "sha256": digest,
                "status": "already_saved_checkpoint",
            })
            state["batch_next_index"] = index + 1
            state["batch_prefix_sha256"] = _batch_prefix_digest(rows, index + 1)
            state["status"] = "in_progress"
            state.pop("last_error", None)
            _write_session_state(checkpoint_path, state)
            print(f"이미 보관된 동일 쪽지 확인, 건너뜀: {received_at:%Y-%m-%d %H:%M:%S} — {title}")
            continue
        last_saved = state.get("last_saved")
        if last_saved:
            previous_saved_at = dt.datetime.fromisoformat(last_saved["received_at"])
            if received_at > previous_saved_at:
                state["status"] = "paused_order_error"
                state["last_error"] = {
                    "input_index": index,
                    "received_at": received_at.isoformat(timespec="seconds"),
                    "message": "배치 첫 항목 또는 다음 항목이 직전 저장 지점보다 최신입니다.",
                }
                _write_session_state(checkpoint_path, state)
                raise RuntimeError(
                    f"JSONL {item['line']}행이 직전 저장 지점보다 최신입니다. "
                    f"직전 저장: {previous_saved_at:%Y-%m-%d %H:%M:%S} — {last_saved['title']}"
                )

        if digest in existing_hashes and not (allow_duplicate_bodies or item.get("allow_duplicate", False)):
            state["status"] = "paused_duplicate"
            state["last_error"] = {
                "input_index": index,
                "received_at": received_at.isoformat(timespec="seconds"),
                "title": title,
                "sha256": digest,
                "message": "배치 본문이 기존 보관 본문과 같아 중복 여부 확인 필요",
            }
            _write_session_state(checkpoint_path, state)
            raise RuntimeError(f"JSONL {item['line']}행이 기존 보관 본문과 같아 멈췄습니다. 중복인지 확인하세요.")

        archive_file = _archive_path_for(received_at, period)
        try:
            existing_size = archive_file.stat().st_size if archive_file.exists() else 0
            prefix_digest = _archive_prefix_sha256(archive_file, existing_size) if existing_size else hashlib.sha256(b"").hexdigest()
            block = _archive_block(body, title, received_at, existing_size)
            state["pending_append"] = {
                "received_at": received_at.isoformat(timespec="seconds"),
                "title": title,
                "body_sha256": digest,
                "archive_file": str(archive_file.resolve()),
                "offset": existing_size,
                "prefix_sha256": prefix_digest,
                "block_size": len(block),
                "block_sha256": hashlib.sha256(block).hexdigest(),
                "input_index": index,
                "batch_prefix_sha256": _batch_prefix_digest(rows, index + 1),
            }
            _write_session_state(checkpoint_path, state)
            with archive_file.open("ab") as stream:
                stream.write(block)
                stream.flush()
                os.fsync(stream.fileno())
        except OSError as exc:
            state["status"] = "paused_archive_error"
            state["last_error"] = {"input_index": index, "message": str(exc)}
            _write_session_state(checkpoint_path, state)
            raise RuntimeError(f"JSONL {item['line']}행 보관 중 파일 쓰기 오류로 멈췄습니다: {exc}") from exc

        record = {
            "received_at": received_at.isoformat(timespec="seconds"),
            "title": title,
            "sha256": digest,
            "status": "saved",
            "archive_file": str(archive_file),
        }
        state.setdefault("records", []).append(record)
        state["saved_count"] = int(state.get("saved_count", 0)) + 1
        state["last_saved"] = record
        state["batch_next_index"] = index + 1
        state["batch_prefix_sha256"] = _batch_prefix_digest(rows, index + 1)
        state["status"] = "in_progress"
        state.pop("pending_append", None)
        state.pop("last_error", None)
        _write_session_state(checkpoint_path, state)
        existing_keys.add(archive_key)
        existing_hashes.add(digest)
        saved_this_run += 1
        print(f"보관 완료 ({saved_this_run}건): {received_at:%Y-%m-%d %H:%M:%S} — {title}")

    state["status"] = "paused_batch_exhausted"
    state["batch_prefix_sha256"] = _batch_prefix_digest(rows, len(rows))
    state["last_error"] = {"message": "배치 파일 끝까지 갔지만 기준일보다 오래된 항목을 확인하지 못함"}
    _write_session_state(checkpoint_path, state)
    print(f"배치 {len(rows)}건을 처리했지만 cutoff 이전 항목을 확인하지 못해 미완료 상태로 남겼습니다. 신규 저장 {saved_this_run}건.")
    print(f"재개 정보: {checkpoint_path}")
    return saved_this_run


def _batch_prefix_digest(rows: list[dict], length: int) -> str:
    """Hash processed record values so a batch may safely extend its unprocessed suffix."""
    prefix = [
        {
            "received_at": row["received_at"].isoformat(timespec="seconds"),
            "title": row["title"],
            "body": row["body"],
            "allow_duplicate": bool(row.get("allow_duplicate")),
        }
        for row in rows[:length]
    ]
    serialized = json.dumps(prefix, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def existing_archive_hashes() -> set[str]:
    """Return hashes of note bodies already present in local Markdown archives."""
    hashes: set[str] = set()
    if not ARCHIVE.exists():
        return hashes
    pattern = re.compile(r"(?ms)^## .*?\n\n(.*?)(?=^## |\Z)")
    for path in ARCHIVE.glob("*.md"):
        try:
            contents = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            continue
        for match in pattern.finditer(contents):
            body = match.group(1).strip()
            if body:
                hashes.add(hashlib.sha256(body.encode("utf-8")).hexdigest())
    return hashes


def _existing_archive_record_keys() -> set[tuple[str, str, str]]:
    """Return exact timestamp/title/body keys to safely skip a repeated batch row."""
    keys: set[tuple[str, str, str]] = set()
    if not ARCHIVE.exists():
        return keys
    pattern = re.compile(r"(?ms)^## (\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) — (.*?)\n\n(.*?)(?=^## |\Z)")
    for path in ARCHIVE.glob("*.md"):
        try:
            contents = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            continue
        for match in pattern.finditer(contents):
            body = match.group(3).strip()
            if body:
                keys.add((match.group(1), match.group(2).strip(), hashlib.sha256(body.encode("utf-8")).hexdigest()))
    return keys


def preprocess(text: str, limit: int) -> str:
    """Prepare bounded input. Privacy masking can be added here later."""
    text = text.strip()
    if not text:
        raise RuntimeError("입력 내용이 비어 있습니다.")
    if len(text) > limit:
        print(f"입력이 {len(text):,}자입니다. 뒤쪽 {len(text) - limit:,}자를 제외하고 요약합니다.", file=sys.stderr)
        text = text[-limit:]
    return text


def summarize(text: str, model: str) -> str:
    try:
        import anthropic
    except ImportError as exc:
        raise RuntimeError("anthropic 패키지가 없습니다. `python -m pip install -r requirements.txt`를 실행하세요.") from exc
    if not os.getenv("ANTHROPIC_API_KEY"):
        raise RuntimeError("ANTHROPIC_API_KEY 환경변수를 설정하세요.")
    system = (BASE / "prompt.md").read_text(encoding="utf-8")
    try:
        client = anthropic.Anthropic()
        response = client.messages.create(
            model=model,
            max_tokens=2500,
            system=system,
            # Keep untrusted chat text in a user message, not in system instructions.
            messages=[{"role": "user", "content": "다음은 요약할 지비톡 대화 원문입니다.\n\n" + text}],
        )
    except Exception as exc:
        raise RuntimeError(f"Anthropic API 요청이 실패했습니다: {exc}") from exc
    result = "\n".join(block.text for block in response.content if getattr(block, "type", None) == "text").strip()
    if not result:
        raise RuntimeError("API 응답에서 요약 텍스트를 받지 못했습니다.")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="지비톡 쪽지를 로컬에 보관하거나 텍스트를 요약합니다. 메시지 전송은 하지 않습니다.")
    parser.add_argument("mode", choices=["probe", "uia", "clipboard", "file", "archive", "archive-session", "archive-batch"], help="텍스트 입력 방식 또는 로컬 보관")
    parser.add_argument("path", nargs="?", help="file 모드의 UTF-8 텍스트 파일")
    parser.add_argument("--window", type=int, default=0, help="probe/uia 모드에서 사용할 지비톡 창 번호 (기본값: 0)")
    parser.add_argument("--model", default=os.getenv("ANTHROPIC_MODEL", DEFAULT_MODEL), help="Anthropic 모델 ID (ANTHROPIC_MODEL로도 지정 가능)")
    parser.add_argument("--max-chars", type=int, default=MAX_CHARS, help=f"API에 보낼 최대 글자 수 (기본값: {MAX_CHARS})")
    parser.add_argument("--save-raw", action="store_true", help="입력 원문을 out 폴더에 저장 (기본값: 저장 안 함)")
    parser.add_argument("--title", help="archive 항목에 붙일 제목(선택)")
    parser.add_argument("--period", choices=["day", "week", "month"], default="day", help="archive 파일을 나눌 기간 (기본값: day)")
    parser.add_argument("--sent-at", help="쪽지의 원래 날짜/시각 (예: '2026-10-22 11:20:00')")
    parser.add_argument("--before", help="archive-session/archive-batch가 이 날짜보다 오래된 쪽지를 만나면 완료 처리 (YYYY-MM-DD)")
    parser.add_argument("--allow-duplicate-bodies", action="store_true", help="archive-batch에서 중복 본문을 별개 쪽지로 확인한 경우 저장 허용")
    args = parser.parse_args()
    try:
        if args.max_chars < 1:
            raise RuntimeError("--max-chars는 1 이상이어야 합니다.")
        if args.mode == "probe":
            probe(args.window)
            return 0
        if args.mode == "archive":
            saved_path = archive_clipboard(args.title, args.period, args.sent_at)
            print(f"쪽지 내용을 로컬 보관함에 추가했습니다: {saved_path}")
            print("이 단계에서는 외부 AI로 내용을 보내지 않았습니다.")
            return 0
        if args.mode == "archive-session":
            if not args.before:
                raise RuntimeError("archive-session에는 --before YYYY-MM-DD가 필요합니다.")
            archive_session(args.before, args.period)
            return 0
        if args.mode == "archive-batch":
            if not args.before:
                raise RuntimeError("archive-batch에는 --before YYYY-MM-DD가 필요합니다.")
            if not args.path:
                raise RuntimeError("archive-batch에는 JSONL 입력 파일 경로가 필요합니다.")
            archive_batch(args.path, args.before, args.period, args.allow_duplicate_bodies)
            return 0
        raw = load_input(args.mode, args.path, args.window)
        text = preprocess(raw, args.max_chars)
        summary = summarize(text, args.model)
        OUT.mkdir(exist_ok=True)
        tag = now_tag()
        result_path = OUT / f"summary_{tag}.md"
        result_path.write_text(summary + "\n", encoding="utf-8")
        if args.save_raw:
            raw_path = OUT / f"raw_{tag}.txt"
            raw_path.write_text(raw, encoding="utf-8")
            print(f"원문 저장: {raw_path}")
        print(summary)
        print(f"\n요약 저장: {result_path}")
        return 0
    except (RuntimeError, OSError) as exc:
        print(f"오류: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
