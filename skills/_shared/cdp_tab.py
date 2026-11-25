# -*- coding: utf-8 -*-
"""사용자 Chrome(원격 디버깅 9222)의 탭 하나를 CDP로 직접 다루는 작은 도우미.

Playwright connect_over_cdp 는 사용자 Chrome 전체를 잡아 멈추는 일이 있어(에듀파인 ISSUES 수칙 9),
브라우저 웹소켓 + Target.attachToTarget(flatten) 으로 "내 탭 하나"에만 붙는다.

■ 원칙
  - 다른 세션·사람이 쓰는 탭은 건드리지 않는다. 작업용 탭은 Tab.new(url) 로 백그라운드에 새로 연다.
  - Chrome 창이 가려져 있어도 동작하도록 Emulation.setFocusEmulationEnabled 를 켠다.
  - 페이지의 alert/confirm 은 자동 수락하고 Tab.dialogs 에 내용을 남긴다.
  - Chrome 이 다시 시작되면 target id 가 바뀐다(복원된 탭은 로드 전이라 응답이 없을 수 있음).
    저장해 둔 id 로 못 붙으면 Tab.new 로 새로 연다 (open_or_new 참고).

■ 사용법
    import sys, pathlib; sys.path.insert(0, str(next(p / "_shared" for p in pathlib.Path(__file__).resolve().parents if (p / "_shared" / "cdp_tab.py").is_file())))
    from cdp_tab import Tab
    t = Tab.new("https://www.s2b.kr/")      # 백그라운드 새 탭
    t.wait_ready()
    print(t.js("document.title"))
    t.close()

필요 패키지: websockets (>= 12, sync client)
"""
from __future__ import annotations

import base64
import json
import time
import urllib.request
from pathlib import Path

from websockets.sync.client import connect

CDP_HTTP = "http://127.0.0.1:9222"  # localhost 는 IPv6(::1) 로 붙어 거부될 수 있다


def list_tabs() -> list[dict]:
    """열린 페이지 탭 목록 (type == page)."""
    data = json.loads(urllib.request.urlopen(CDP_HTTP + "/json", timeout=5).read())
    return [t for t in data if t.get("type") == "page"]


def _browser_ws() -> str:
    return json.loads(urllib.request.urlopen(CDP_HTTP + "/json/version", timeout=5).read())["webSocketDebuggerUrl"]


class Tab:
    def __init__(self, target_id: str, attach_timeout: float = 20):
        self.target_id = target_id
        self.ws = connect(_browser_ws(), max_size=64 * 1024 * 1024, open_timeout=10)
        self._id = 0
        self.dialogs: list[str] = []
        self.sid = None
        self.sid = self.call("Target.attachToTarget", {"targetId": target_id, "flatten": True},
                             session=False)["sessionId"]
        self.call("Runtime.enable", timeout=attach_timeout)
        self.call("Page.enable", timeout=attach_timeout)
        try:
            self.call("Emulation.setFocusEmulationEnabled", {"enabled": True})
        except Exception:
            pass

    # ── 만들기 ──
    @classmethod
    def new(cls, url: str, background: bool = True) -> "Tab":
        ws = connect(_browser_ws(), open_timeout=10)
        ws.send(json.dumps({"id": 1, "method": "Target.createTarget",
                            "params": {"url": url, "background": background}}))
        while True:
            m = json.loads(ws.recv(timeout=15))
            if m.get("id") == 1:
                break
        ws.close()
        return cls(m["result"]["targetId"])

    @classmethod
    def open_or_new(cls, id_file: Path, url: str, url_contains: str) -> "Tab":
        """id_file 에 적힌 내 탭에 다시 붙고, 없거나 응답이 없으면 새로 연 뒤 id 를 저장한다."""
        id_file = Path(id_file)
        if id_file.is_file():
            tid = id_file.read_text().strip()
            if any(t["id"] == tid and url_contains in t.get("url", "") for t in list_tabs()):
                try:
                    return cls(tid, attach_timeout=8)
                except Exception:
                    pass
        t = cls.new(url)
        t.wait_ready()
        id_file.parent.mkdir(parents=True, exist_ok=True)
        id_file.write_text(t.target_id)
        return t

    # ── 기본 호출 ──
    def call(self, method: str, params: dict | None = None, session: bool = True, timeout: float = 60):
        self._id += 1
        mid = self._id
        msg = {"id": mid, "method": method, "params": params or {}}
        if session and self.sid:
            msg["sessionId"] = self.sid
        self.ws.send(json.dumps(msg))
        end = time.time() + timeout
        while time.time() < end:
            m = json.loads(self.ws.recv(timeout=max(0.1, end - time.time())))
            if self._handle_event(m):
                continue
            if m.get("id") == mid:
                if "error" in m:
                    raise RuntimeError(m["error"])
                return m.get("result", {})
        raise TimeoutError(method)

    def _handle_event(self, m: dict) -> bool:
        if m.get("method") == "Page.javascriptDialogOpening":
            self.dialogs.append(m["params"].get("message", ""))
            self.ws.send(json.dumps({"id": 0, "sessionId": self.sid, "method": "Page.handleJavaScriptDialog",
                                     "params": {"accept": True}}))
            return True
        return "method" in m

    def js(self, expr: str, await_promise: bool = True, timeout: float = 60):
        """식을 실행하고 값(JSON 가능 값)을 돌려준다. 예외는 RuntimeError."""
        r = self.call("Runtime.evaluate", {"expression": expr, "returnByValue": True,
                                           "awaitPromise": await_promise}, timeout=timeout)
        if r.get("exceptionDetails"):
            ex = r["exceptionDetails"]
            raise RuntimeError(ex.get("exception", {}).get("description") or ex.get("text") or ex)
        return r.get("result", {}).get("value")

    # ── 이동·대기 ──
    def goto(self, url: str, extra: float = 1.5):
        self.call("Page.navigate", {"url": url})
        self.wait_ready(extra)

    def wait_ready(self, extra: float = 1.0, timeout: float = 30):
        """readyState complete + 실제 http 주소가 될 때까지 기다린다(새 탭은 잠깐 about:blank)."""
        end = time.time() + timeout
        time.sleep(0.5)
        while time.time() < end:
            try:
                if str(self.js("document.readyState + '|' + location.href", await_promise=False)).startswith("complete|http"):
                    break
            except Exception:
                pass
            time.sleep(0.3)
        self.pump(extra)

    def pump(self, seconds: float):
        """잠깐 이벤트를 받아 대화상자 등을 처리한다."""
        end = time.time() + seconds
        while time.time() < end:
            try:
                m = json.loads(self.ws.recv(timeout=max(0.05, end - time.time())))
            except TimeoutError:
                break
            self._handle_event(m)

    def screenshot(self, path) -> None:
        data = self.call("Page.captureScreenshot", {"format": "png"})["data"]
        Path(path).write_bytes(base64.b64decode(data))

    def close(self):
        """이 탭을 닫는다 (내가 연 탭에만 쓴다)."""
        try:
            self.call("Target.closeTarget", {"targetId": self.target_id}, session=False)
        finally:
            self.ws.close()
