#!/usr/bin/env python3
"""지비톡(경북교육청 메신저) 문자(SMS/LMS) 보내기 — msg.gbe.kr/messaging 을 9222 Chrome에서 CDP로 조작.

지비톡 [문자]는 평소 Chrome에 `https://msg.gbe.kr/ssa/<토큰>` 으로 열린다. 이 주소를 한 번 잡아 두면(capture)
9222 Chrome에서도 로그인된 문자 창을 열 수 있다. 주소(토큰)와 기본 발신번호는 data_dir 에만 저장한다(저장소 X).

사용법
  python gbetalk_sms.py capture [--seconds 180]
      실행 후 지비톡에서 [문자]를 한 번 누르면, 브라우저 실행 주소를 잡아 data_dir/sms_url.txt 에 저장
  python gbetalk_sms.py send --to 01012345678,01098765432 (--text "내용" | --text-file 파일) [--from 010-xxxx-xxxx]
      문자 창을 열어 내용·발신번호·수신번호를 채우고 [전송] 직전에 멈춤(화면 캡처 저장)
  python gbetalk_sms.py send ... --confirm SEND_SMS
      실제 전송. "문자 전송 완료!!" 확인 후 결과 기록(data_dir/sent_log.jsonl)
안전: 실제 전송은 --confirm SEND_SMS 일 때만. 받는 번호·내용은 출력에서 가린다.
"""
from __future__ import annotations

import argparse
import base64
import datetime as dt
import io
import json
import os
import re
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

import sys as _sys, pathlib as _pl
_sys.path.insert(0, str(next(p / "_shared" for p in _pl.Path(__file__).resolve().parents if (p / "_shared" / "skill_env.py").is_file())))
from skill_env import load_env, data_dir  # noqa: E402

if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
os.environ["no_proxy"] = "localhost,127.0.0.1"
load_env()
DATA = data_dir("admin-gbetalk", "sms")
DATA.mkdir(parents=True, exist_ok=True)
CDP = "http://127.0.0.1:9222"
URL_FILE = DATA / "sms_url.txt"
CFG = DATA / "config.json"


def log(*a):
    print(*a, flush=True)


def mask(num: str) -> str:
    d = re.sub(r"\D", "", num)
    return d[:3] + "-****-" + d[-4:] if len(d) >= 8 else "***"


# ─────────────── capture: 지비톡 [문자] 클릭 때 Chrome 실행 주소 잡기 ───────────────
def cmd_capture(a):
    log(f"[capture] {a.seconds}초 동안 대기 — 지금 지비톡에서 [문자]를 한 번 눌러 주세요.")
    ps = ("Get-CimInstance Win32_Process -Filter \"Name='chrome.exe' OR Name='msedge.exe'\" | "
          "Where-Object { $_.CommandLine -match 'msg\\.gbe\\.kr/ssa/' } | ForEach-Object { $_.CommandLine }")
    end = time.time() + a.seconds
    while time.time() < end:
        out = subprocess.run(["powershell", "-NoProfile", "-Command", ps], capture_output=True, text=True).stdout
        m = re.search(r"https://msg\.gbe\.kr/ssa/[^\s\"]+", out)
        if m:
            URL_FILE.write_text(m.group(0), encoding="utf-8")
            log(f"[capture] 주소 저장: {URL_FILE} (토큰은 출력하지 않음)")
            return
        time.sleep(0.3)
    sys.exit("[capture] 주소를 못 잡았습니다. 다시 실행하고 [문자]를 눌러 주세요.")


# ─────────────── CDP ───────────────
class Tab:
    def __init__(self, tid):
        import websocket
        t = next(x for x in json.loads(urllib.request.urlopen(f"{CDP}/json", timeout=5).read()) if x["id"] == tid)
        self.ws = websocket.create_connection(t["webSocketDebuggerUrl"], timeout=90, suppress_origin=True)
        self.n = 0
        self.cmd("Emulation.setFocusEmulationEnabled", {"enabled": True})

    def cmd(self, method, params=None):
        self.n += 1
        self.ws.send(json.dumps({"id": self.n, "method": method, "params": params or {}}))
        while True:
            m = json.loads(self.ws.recv())
            if m.get("id") == self.n:
                return m.get("result", m)

    def js(self, expr, timeout_ms=60000):
        r = self.cmd("Runtime.evaluate", {"expression": expr, "returnByValue": True, "awaitPromise": True, "timeout": timeout_ms})
        if "exceptionDetails" in r:
            raise RuntimeError(str(r["exceptionDetails"].get("exception", {}).get("description", r))[:300])
        return r.get("result", {}).get("value")

    def shot(self, name):
        p = DATA / f"{name}.png"
        p.write_bytes(base64.b64decode(self.cmd("Page.captureScreenshot", {"format": "png"})["data"]))
        return p


def open_sms_tab() -> Tab:
    tabs = json.loads(urllib.request.urlopen(f"{CDP}/json", timeout=5).read())
    t = next((x for x in tabs if x.get("type") == "page" and "msg.gbe.kr/messaging" in x.get("url", "")), None)
    if t:
        tab = Tab(t["id"])
        tab.js("location.reload(); 1")  # 이전 입력·받는사람 목록 비우기
        time.sleep(4)
    else:
        if not URL_FILE.exists():
            sys.exit("저장된 문자 창 주소가 없습니다 → 먼저 capture.")
        url = URL_FILE.read_text(encoding="utf-8").strip()
        req = urllib.request.Request(f"{CDP}/json/new?{url}", method="PUT")
        t = json.loads(urllib.request.urlopen(req, timeout=10).read())
        time.sleep(5)
        tab = Tab(t["id"])
    loc = tab.js("location.pathname")
    if "messaging" not in (loc or ""):
        sys.exit(f"문자 창 로그인 실패({loc}) → 토큰 만료. capture 를 다시 하세요.")
    return tab


# ─────────────── send ───────────────
FILL = r"""
(async (text, sender, nums) => {
  const sleep = ms => new Promise(r => setTimeout(r, ms));
  $('#message').val(text).trigger('keyup').trigger('input').trigger('change');
  const sel = document.getElementById('sndNumber');
  const want = sender.replace(/\D/g, '');
  const opt = [...sel.options].find(o => o.value.replace(/\D/g, '') === want || o.text.replace(/\D/g, '') === want);
  if (want && !opt) return {err: 'sender', options: [...sel.options].map(o => o.text)};
  if (opt) { sel.value = opt.value; $(sel).trigger('change'); }
  const bad = [];
  for (const n of nums) {
    $('#quickAddr').val(n.replace(/\D/g, ''));
    setQuickAddrToRcvList();
    await sleep(300);
  }
  if (typeof setRcvListCount === 'function') setRcvListCount();
  const rows = [...document.querySelectorAll('#rcvList .chkItem')].map(c => c.getAttribute('data-mobile') || c.getAttribute('data-key'));
  return {sender: sel.options[sel.selectedIndex].text, rows, type: ($('#serviceType').text() || '').trim(),
          bytes: ([...document.body.innerText.matchAll(/(\d+)\s*byte/g)].pop() || [])[1],  // 첫 일치는 안내문의 "140byte" count: (document.body.innerText.match(/받는사람\s*:\s*(\d+)/) || [])[1]};
})
"""


def cmd_send(a):
    nums = [n for n in re.split(r"[,\s]+", a.to or "") if n]
    if not nums:
        sys.exit("--to 받는 번호가 필요합니다.")
    text = Path(a.text_file).read_text(encoding="utf-8") if a.text_file else (a.text or "")
    if not text.strip():
        sys.exit("--text 또는 --text-file 내용이 필요합니다.")
    cfg = json.loads(CFG.read_text(encoding="utf-8")) if CFG.exists() else {}
    sender = a.sender or cfg.get("from", "")
    tab = open_sms_tab()
    r = tab.js(f"{FILL}({json.dumps(text)}, {json.dumps(sender)}, {json.dumps(nums)})")
    if r.get("err") == "sender":
        sys.exit(f"발신번호 {sender} 가 목록에 없습니다: {r['options']}")
    got = [re.sub(r"\D", "", x or "") for x in r["rows"]]
    miss = [n for n in nums if re.sub(r"\D", "", n) not in got]
    log(f"[send] 발신 {r['sender']} | 수신 {len(got)}명 {', '.join(mask(x) for x in got)} | {r['type'] or '?'} {r['bytes'] or '?'}byte")
    shot = tab.shot("sms_before_send")
    log(f"  화면: {shot}")
    if miss:
        sys.exit(f"수신 목록에 안 들어간 번호: {', '.join(mask(m) for m in miss)} (번호 형식 확인)")
    if a.sender and not CFG.exists():
        CFG.write_text(json.dumps({"from": a.sender}, ensure_ascii=False), encoding="utf-8")
    if a.confirm != "SEND_SMS":
        log("  (전송 직전 멈춤. 실제 전송: --confirm SEND_SMS)")
        return
    tab.js("window.__smsDlg=[]; window.alert=m=>window.__smsDlg.push('A:'+m); window.confirm=m=>{window.__smsDlg.push('C:'+m); return true;}; $('#btnRegistMessage').trigger('click'); 1")
    status = ""
    for _ in range(60):
        time.sleep(1)
        status = tab.js("($('#progressbar-label').text()||'') + ' | ' + (window.__smsDlg||[]).join(' / ')")
        if "완료" in status or "실패" in status or "A:" in status:
            break
    log(f"[send] 결과: {status}")
    ok = "전송 완료" in status
    with open(DATA / "sent_log.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps({"at": dt.datetime.now().isoformat(timespec="seconds"), "ok": ok, "to": got,
                            "sender": r["sender"], "text": text}, ensure_ascii=False) + "\n")
    log(f"  화면: {tab.shot('sms_after_send')}")
    if ok:
        tab.js("try{ $('#dialog_progressbar').dialog('close'); }catch(e){} 1")
    else:
        sys.exit("전송 완료를 확인하지 못했습니다. 화면과 '문자 전송내역'을 확인하세요.")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest="cmd", required=True)
    p = sp.add_parser("capture")
    p.add_argument("--seconds", type=int, default=180)
    p = sp.add_parser("send")
    p.add_argument("--to", required=True, help="받는 번호(쉼표로 여러 명)")
    p.add_argument("--text")
    p.add_argument("--text-file")
    p.add_argument("--from", dest="sender", help="발신번호(처음 한 번 주면 data_dir/config.json 에 기본값 저장)")
    p.add_argument("--confirm", default="")
    a = ap.parse_args()
    {"capture": cmd_capture, "send": cmd_send}[a.cmd](a)


if __name__ == "__main__":
    main()
