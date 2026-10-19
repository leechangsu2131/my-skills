from __future__ import annotations

import argparse
import csv
import json
import re
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import urlopen

from websockets.sync.client import connect


def page_target(port: int, host: str) -> dict:
    with urlopen(f"http://127.0.0.1:{port}/json", timeout=3) as response:
        targets = json.load(response)
    for target in targets:
        parsed = urlsplit(target.get("url", ""))
        if target.get("type") == "page" and (
            parsed.hostname == host or (parsed.hostname or "").endswith("." + host)
        ):
            return target
    raise RuntimeError(f"Open the authorized course page on {host} in the CDP Chrome first.")


class PageCDP:
    def __init__(self, websocket_url: str):
        self.ws = connect(websocket_url, open_timeout=4, close_timeout=2, max_size=2_000_000)
        self.next_id = 0

    def call(self, method: str, params: dict | None = None) -> dict:
        self.next_id += 1
        command_id = self.next_id
        self.ws.send(json.dumps({"id": command_id, "method": method, "params": params or {}}))
        while True:
            message = json.loads(self.ws.recv(timeout=5))
            if message.get("id") != command_id:
                continue
            if "error" in message:
                raise RuntimeError(f"Chrome DevTools error calling {method}.")
            return message.get("result", {})

    def evaluate(self, expression: str, context_id: int | None = None):
        params = {"expression": expression, "returnByValue": True}
        if context_id is not None:
            params["contextId"] = context_id
        result = self.call("Runtime.evaluate", params).get("result", {})
        if "exceptionDetails" in result:
            raise RuntimeError("Page evaluation failed; stop without retrying the click.")
        return result.get("value")

    def frame_tree(self) -> dict:
        return self.call("Page.getFrameTree").get("frameTree", {})

    def close(self):
        self.ws.close()


def flatten_frames(node: dict):
    frame = node.get("frame", {})
    yield frame
    for child in node.get("childFrames", []):
        yield from flatten_frames(child)


def course_state(cdp: PageCDP, course: str) -> list[dict]:
    course_json = json.dumps(course, ensure_ascii=False)
    expression = f"""(() => {{
      const title = {course_json};
      const heading = Array.from(document.querySelectorAll('h1,h2,h3'))
        .find(el => (el.innerText || '').trim() === title);
      const card = heading && heading.closest('li');
      if (!card) return null;
      return Array.from(card.querySelectorAll('tr')).map(row => {{
        const cells = Array.from(row.cells || []).map(cell => (cell.innerText || '').trim());
        const number = cells.find(text => /^\\d+차시$/.test(text));
        if (!number) return null;
        return {{
          lesson: Number(number.replace('차시', '')),
          title: cells[1] || '',
          progress: cells.find(text => /^\\d{{1,3}}%$/.test(text)) || '',
          button: !!row.querySelector('button[title="학습하기"],button[title="수강하기"]')
        }};
      }}).filter(Boolean);
    }})()"""
    result = cdp.evaluate(expression)
    if result is None:
        raise RuntimeError("The exact course title is not visible; do not select a different course.")
    return result


def progress_value(row: dict) -> int | None:
    match = re.fullmatch(r"(\d{1,3})%", row.get("progress", ""))
    return int(match.group(1)) if match else None


def open_lesson(cdp: PageCDP, course: str, lesson: int, timeout: float) -> tuple[str, bool]:
    course_json = json.dumps(course, ensure_ascii=False)
    expression = f"""(() => {{
      const heading = Array.from(document.querySelectorAll('h1,h2,h3'))
        .find(el => (el.innerText || '').trim() === {course_json});
      const card = heading && heading.closest('li');
      const row = card && Array.from(card.querySelectorAll('tr')).find(row =>
        Array.from(row.cells || []).some(cell => (cell.innerText || '').trim() === '{lesson}차시'));
      const button = row && row.querySelector('button[title="학습하기"],button[title="수강하기"]');
      if (!button || button.disabled) return false;
      button.click();
      return true;
    }})()"""
    if not cdp.evaluate(expression):
        raise RuntimeError(f"Lesson {lesson} play button was not available.")
    cdp.call("Page.enable")
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        frames = list(flatten_frames(cdp.frame_tree()))
        for frame in frames:
            url = frame.get("url", "")
            path = urlsplit(url).path.lower()
            if path.endswith((".mp4", ".webm", ".m3u8", ".mpd")):
                paused = False
                try:
                    world = cdp.call("Page.createIsolatedWorld", {
                        "frameId": frame.get("id"), "worldName": "pause-for-url-capture"
                    })
                    context_id = world.get("executionContextId")
                    paused = bool(cdp.evaluate(
                        "(() => { const video=document.querySelector('video'); "
                        "if(!video)return false; video.pause(); return video.paused; })()",
                        context_id,
                    ))
                except Exception:
                    pass
                return url, paused
        time.sleep(0.15)
    raise RuntimeError(f"No visible media frame appeared for lesson {lesson}; stop and inspect manually.")


def close_player(cdp: PageCDP) -> None:
    cdp.evaluate("""(() => {
      const e = document.querySelector("#modal span[onclick*='studyEnd']");
      if (!e) return false;
      e.click();
      return true;
    })()""")
    time.sleep(0.2)
    if cdp.evaluate("!!document.querySelector('#modal')"):
        raise RuntimeError("Player modal remains open; stop for manual cleanup.")


def write_outputs(output_dir: Path, rows: list[dict]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = output_dir / "lesson_media_urls.csv"
    md_path = output_dir / "lesson_media_urls.md"
    fields = ["lesson", "title", "media_url", "captured_at", "progress_before", "progress_after", "status"]
    by_lesson = {}
    if csv_path.exists():
        with csv_path.open(newline="", encoding="utf-8-sig") as file:
            for existing in csv.DictReader(file):
                by_lesson[int(existing["lesson"])] = existing
    by_lesson.update({int(row["lesson"]): row for row in rows})
    ordered = [by_lesson[key] for key in sorted(by_lesson)]
    with csv_path.open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        writer.writerows(ordered)
    lines = ["# 강의 미디어 주소 목록", "", "이 파일은 사용자가 접근 권한이 있는 강의 플레이어에서 확인한 주소를 로컬에 보관합니다. 주소는 만료되거나 로그인 세션에 종속될 수 있습니다.", "", "| 차시 | 강의명 | 상태 | 진도 전→후 |", "|---:|---|---|---|"]
    for row in ordered:
        before = row.get("progress_before", "")
        after = row.get("progress_after", "")
        lines.append(f"| {row['lesson']} | {row['title']} | {row['status']} | {before} → {after} |")
    lines.extend(["", "미디어 URL 원문은 함께 생성된 CSV에만 기록했습니다.", ""])
    md_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Capture media URLs shown by an authorized course player.")
    parser.add_argument("--course", required=True, help="Exact visible course title")
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--start", type=int, default=1)
    parser.add_argument("--end", type=int, required=True)
    parser.add_argument("--port", type=int, default=9222)
    parser.add_argument("--host", default="krcls.kr")
    parser.add_argument("--frame-timeout", type=float, default=8.0)
    parser.add_argument(
        "--continue-after-progress-change", action="store_true",
        help="Continue only when the user has been informed and explicitly asks to proceed.",
    )
    args = parser.parse_args()

    target = page_target(args.port, args.host)
    cdp = PageCDP(target["webSocketDebuggerUrl"])
    captured: list[dict] = []
    try:
        state = course_state(cdp, args.course)
        selected = [row for row in state if args.start <= row["lesson"] <= args.end]
        if not selected:
            raise RuntimeError("No lessons matched the requested range.")
        for original in selected:
            before_rows = course_state(cdp, args.course)
            current = next(row for row in before_rows if row["lesson"] == original["lesson"])
            before = current.get("progress", "")
            url, paused = open_lesson(cdp, args.course, original["lesson"], args.frame_timeout)
            close_player(cdp)
            after_rows = course_state(cdp, args.course)
            after = next(row for row in after_rows if row["lesson"] == original["lesson"]).get("progress", "")
            status = "확인·일시정지" if paused else "확인·정지 확인 불가"
            row = {
                "lesson": original["lesson"], "title": original["title"], "media_url": url,
                "captured_at": datetime.now().astimezone().isoformat(timespec="seconds"),
                "progress_before": before, "progress_after": after, "status": status,
            }
            captured.append(row)
            write_outputs(args.output_dir, captured)
            changed = before != after
            print(f"{original['lesson']}차시: captured; paused={paused}; progress={before}->{after}")
            if changed and not args.continue_after_progress_change:
                print("Progress changed. Stop here and review before continuing.")
                break
    finally:
        cdp.close()
    print(f"Saved {len(captured)} row(s) under {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
