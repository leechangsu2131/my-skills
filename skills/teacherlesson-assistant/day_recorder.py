"""하루 녹음 상주 프로그램 (T117, ISSUE-055 ①).

교실 PC 의 마이크를 ffmpeg 로 받아 30분 조각 파일로 쭉 저장한다. 브라우저 탭 녹음은 탭을 닫거나 PC 가
잠들면 끊겨서, 하루 녹음은 이 작은 프로그램이 따로 맡는다. 나누기·받아쓰기는 나중에 (T116·T118·T119).

    python day_recorder.py list              # 마이크(DirectShow 장치) 목록
    python day_recorder.py start [--mic 이름]  # 뒤에서 녹음 시작 (이미 켜져 있으면 안 켬)
    python day_recorder.py stop              # 녹음을 마무리하고 끔
    python day_recorder.py status            # 켜져 있는지, 오늘 조각이 몇 개인지

파일: 데이터 폴더 `day_audio/<날짜>/<시작 HHMMSS>.mp3` (64 kbps 모노). **PC 안에만 저장**하고 어디로도 보내지 않는다.
설정(config.json, 선택): `day_recorder_mic`(마이크 이름 일부), `ffmpeg_path`.

- 자정이 지나면 ffmpeg 를 새로 띄워 새 날짜 폴더에 이어 간다.
- ffmpeg 가 중간에 끊기면 다시 켠다(10분에 5번까지, 넘으면 멈추고 로그에 남김).
- 두 번 켜지지 않게 `day_audio/recorder.pid` 로 확인한다. 끌 때는 `stop.flag` 를 보고 ffmpeg 에 `q` 를 보내 파일을 깔끔히 닫는다.
- 순수 함수(명령 만들기·조각 이름·장치 목록 해석)와 부수 효과(프로세스·파일)를 나눠, 시험은 가짜 문자열·가짜 프로세스로 한다.
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import re
import subprocess
import sys
import time
from datetime import date, datetime, timedelta

SKILL_DIR = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(next(p / "_shared" for p in SKILL_DIR.parents if (p / "_shared" / "skill_env.py").is_file())))
from skill_env import data_dir  # noqa: E402

import audio_export  # noqa: E402  (ffmpeg 찾기 재사용)

SKILL = "teacherlesson-assistant"
SEGMENT_SECONDS = 30 * 60          # 조각 길이
BITRATE = "64k"                    # 말소리용 — 1시간 약 29 MB (ISSUE-055)
SAMPLE_RATE = "24000"
EXT = ".mp3"
MAX_RESTARTS = 5                   # 이 안에서만 다시 켬
RESTART_WINDOW = 600               # 초 (10분)
RESTART_WAIT = 5                   # 다시 켜기 전 쉬는 초
STOP_GRACE = 10                    # 끌 때 ffmpeg 가 파일을 닫을 때까지 기다리는 초
LOG_KEEP_BYTES = 200_000

SEGMENT_RE = re.compile(r"^(\d{2})(\d{2})(\d{2})\.\w+$")


# ───────────────────────── 순수 함수 ─────────────────────────

def parse_dshow_audio_devices(text: str) -> list[str]:
    """`ffmpeg -list_devices true -f dshow -i dummy` 가 돌려주는 글에서 마이크(오디오 장치) 이름만 뽑는다.

    새 모양:  [dshow @ ...] "마이크 (Realtek)" (audio)   /   옛 모양: 'DirectShow audio devices' 아래 줄들.
    'Alternative name' 줄(장치 경로)은 건너뛴다. 같은 이름은 한 번만.
    """
    names: list[str] = []
    in_audio_section = False
    for line in str(text or "").splitlines():
        if "DirectShow audio devices" in line:
            in_audio_section = True
            continue
        if "DirectShow video devices" in line:
            in_audio_section = False
            continue
        if "Alternative name" in line:
            continue
        m = re.search(r'"([^"]+)"\s*(?:\((\w+(?:,\s*\w+)*)\))?\s*$', line)
        if not m:
            continue
        kinds = (m.group(2) or "").replace(" ", "").split(",")
        if "audio" in kinds or (in_audio_section and not (set(kinds) & {"video"})):
            if m.group(1) not in names:
                names.append(m.group(1))
    return names


def pick_microphone(devices: list[str], preferred: str = "") -> str | None:
    """설정에 적은 이름(일부, 대소문자 무시)과 맞는 첫 장치. 적은 게 없으면 목록의 첫 번째. 목록이 비면 None.

    적은 이름이 목록에 없으면 None — 엉뚱한 마이크로 몰래 녹음하지 않고 알려 준다.
    """
    if not devices:
        return None
    want = (preferred or "").strip().lower()
    if not want:
        return devices[0]
    for d in devices:
        if want in d.lower():
            return d
    return None


def day_dir(root: pathlib.Path, day: date) -> pathlib.Path:
    return pathlib.Path(root) / day.isoformat()


def segment_name(moment: datetime, ext: str = EXT) -> str:
    """조각 파일 이름 = 시작 시각 'HHMMSS' + 확장자."""
    return moment.strftime("%H%M%S") + ext


def parse_segment_start(name: str, day: date) -> datetime | None:
    """조각 파일 이름 → 시작 시각. 모양이 다르거나 시각이 틀리면 None."""
    m = SEGMENT_RE.match(pathlib.Path(name).name)
    if not m:
        return None
    h, mi, s = (int(x) for x in m.groups())
    if h > 23 or mi > 59 or s > 59:
        return None
    return datetime(day.year, day.month, day.day, h, mi, s)


def seconds_until_midnight(now: datetime) -> int:
    """지금부터 다음 자정까지 올림한 초(최소 1)."""
    tomorrow = datetime(now.year, now.month, now.day) + timedelta(days=1)
    return max(1, int((tomorrow - now).total_seconds() + 0.999))


def build_record_command(ffmpeg: str, device: str, out_dir, run_seconds: int,
                         segment_seconds: int = SEGMENT_SECONDS) -> list[str]:
    """마이크 → 시작 시각 이름의 조각 파일. `run_seconds`(자정까지)가 지나면 ffmpeg 가 스스로 끝난다."""
    pattern = str(pathlib.Path(out_dir) / ("%H%M%S" + EXT))
    return [str(ffmpeg), "-v", "error", "-y",
            "-f", "dshow", "-i", f"audio={device}",
            "-t", str(int(run_seconds)),
            "-ac", "1", "-ar", SAMPLE_RATE, "-c:a", "libmp3lame", "-b:a", BITRATE,
            "-f", "segment", "-segment_time", str(int(segment_seconds)),
            "-strftime", "1", "-reset_timestamps", "1", pattern]


def may_restart(restart_times: list[float], now: float,
                limit: int = MAX_RESTARTS, window: float = RESTART_WINDOW) -> bool:
    """최근 `window`초 안에 다시 켠 횟수가 `limit` 미만이면 True (끝없이 켰다 꺼지는 것을 막는다)."""
    return sum(1 for t in restart_times if now - t < window) < limit


def summarize_day(files: list[tuple[str, int]], day: date) -> dict:
    """(이름, 바이트) 목록 → {'count','bytes','first','last'}. 이름 모양이 다른 파일은 건너뜀."""
    segs = sorted((st, size) for name, size in files if (st := parse_segment_start(name, day)))
    return {"count": len(segs), "bytes": sum(s for _, s in segs),
            "first": segs[0][0].strftime("%H:%M:%S") if segs else None,
            "last": segs[-1][0].strftime("%H:%M:%S") if segs else None}


# ───────────────────────── 파일·프로세스 ─────────────────────────

def audio_root() -> pathlib.Path:
    return data_dir(SKILL) / "day_audio"


def load_config() -> dict:
    path = data_dir(SKILL) / "config.json"
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    if os.name == "nt":
        try:
            out = subprocess.run(["tasklist", "/FI", f"PID eq {pid}", "/NH"], capture_output=True,
                                 text=True, timeout=10).stdout
        except (OSError, subprocess.SubprocessError):
            return False
        return str(pid) in out
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def list_devices(ffmpeg: str, runner=subprocess.run) -> list[str]:
    """ffmpeg 에게 마이크 목록을 묻는다(목록은 표준 오류로 나온다)."""
    res = runner([str(ffmpeg), "-hide_banner", "-list_devices", "true", "-f", "dshow", "-i", "dummy"],
                 capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=20)
    return parse_dshow_audio_devices((res.stderr or "") + "\n" + (res.stdout or ""))


class Recorder:
    """상주 녹음. 프로세스·시계·잠자기를 바꿔 끼울 수 있게 해 시험한다."""

    def __init__(self, root: pathlib.Path | None = None, cfg: dict | None = None, popen=subprocess.Popen,
                 now=datetime.now, sleep=time.sleep, monotonic=time.monotonic, alive=pid_alive):
        self.root = pathlib.Path(root) if root else audio_root()
        self.cfg = cfg if cfg is not None else load_config()
        self.popen, self.now, self.sleep, self.monotonic, self.alive = popen, now, sleep, monotonic, alive

    # 경로
    @property
    def pid_file(self): return self.root / "recorder.pid"
    @property
    def stop_flag(self): return self.root / "stop.flag"
    @property
    def log_file(self): return self.root / "recorder.log"

    def log(self, msg: str) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        with self.log_file.open("a", encoding="utf-8") as f:
            f.write(f"{self.now().strftime('%Y-%m-%d %H:%M:%S')} {msg}\n")

    def _trim_log(self) -> None:
        try:
            if self.log_file.stat().st_size > LOG_KEEP_BYTES:
                tail = self.log_file.read_text(encoding="utf-8", errors="replace").splitlines()[-300:]
                self.log_file.write_text("\n".join(tail) + "\n", encoding="utf-8")
        except OSError:
            pass

    def read_pid(self) -> int:
        try:
            return int(json.loads(self.pid_file.read_text(encoding="utf-8")).get("pid", 0))
        except (OSError, ValueError, AttributeError):
            return 0

    def is_running(self) -> bool:
        pid = self.read_pid()
        if pid and self.alive(pid):
            return True
        if pid:                                   # 죽은 프로그램이 남긴 pid 파일은 치운다
            self.pid_file.unlink(missing_ok=True)
        return False

    # 마이크 고르기
    def choose_microphone(self, ffmpeg: str, mic: str = "", runner=subprocess.run) -> tuple[str | None, list[str]]:
        devices = list_devices(ffmpeg, runner)
        return pick_microphone(devices, mic or str(self.cfg.get("day_recorder_mic") or "")), devices

    # 켜기·끄기·상태
    def start(self, mic: str = "", spawn=None) -> str:
        """뒤에서 도는 `run` 을 띄운다. 이미 켜져 있으면 그대로 두고 알린다."""
        if self.is_running():
            return f"이미 녹음 중이에요 (pid {self.read_pid()})."
        ffmpeg = audio_export.find_ffmpeg(self.cfg)
        if not ffmpeg:
            return audio_export.INSTALL_HELP
        device, devices = self.choose_microphone(ffmpeg, mic)
        if not device:
            if not devices:
                return "마이크를 찾지 못했어요. 마이크가 꽂혀 있는지 보고 `python day_recorder.py list` 로 확인해 주세요."
            wanted = mic or str(self.cfg.get("day_recorder_mic") or "")
            return f"'{wanted}' 이름의 마이크가 없어요. 있는 마이크: " + ", ".join(devices)
        self.root.mkdir(parents=True, exist_ok=True)
        self.stop_flag.unlink(missing_ok=True)
        self._trim_log()
        cmd = [sys.executable, str(pathlib.Path(__file__).resolve()), "run", "--mic", device]
        kw: dict = {"stdin": subprocess.DEVNULL, "stdout": subprocess.DEVNULL, "stderr": subprocess.DEVNULL}
        if os.name == "nt":
            kw["creationflags"] = 0x00000008 | 0x00000200      # DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP
        else:
            kw["start_new_session"] = True
        proc = (spawn or self.popen)(cmd, **kw)
        self.pid_file.write_text(json.dumps({"pid": proc.pid, "started": self.now().isoformat(timespec="seconds"),
                                             "mic": device}, ensure_ascii=False), encoding="utf-8")
        self.log(f"시작 pid={proc.pid} 마이크={device}")
        return f"녹음을 시작했어요 (마이크: {device})."

    def stop(self, wait_seconds: float = STOP_GRACE + 5) -> str:
        if not self.is_running():
            return "켜져 있지 않아요."
        pid = self.read_pid()
        self.root.mkdir(parents=True, exist_ok=True)
        self.stop_flag.write_text("stop", encoding="utf-8")
        deadline = self.monotonic() + wait_seconds
        while self.alive(pid) and self.monotonic() < deadline:
            self.sleep(0.5)
        if self.alive(pid):
            self.log(f"끄기 요청에 답이 없어 pid={pid} 을 강제로 끔")
            self._kill(pid)
            self.pid_file.unlink(missing_ok=True)
            return "정상 종료 신호에 답이 없어 강제로 껐어요(마지막 조각이 짧을 수 있어요)."
        self.pid_file.unlink(missing_ok=True)
        return "녹음을 껐어요."

    def _kill(self, pid: int) -> None:
        try:
            if os.name == "nt":
                subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], capture_output=True, timeout=15)
            else:
                os.kill(pid, 15)
        except (OSError, subprocess.SubprocessError):
            pass

    def status(self) -> dict:
        today = self.now().date()
        folder = day_dir(self.root, today)
        files = []
        if folder.is_dir():
            files = [(p.name, p.stat().st_size) for p in folder.iterdir() if p.is_file()]
        info = {"running": self.is_running(), "pid": self.read_pid() or None, "today": summarize_day(files, today)}
        try:
            info["mic"] = json.loads(self.pid_file.read_text(encoding="utf-8")).get("mic")
        except (OSError, ValueError):
            info["mic"] = None
        return info

    # 상주 본체
    def run(self, mic: str = "") -> int:
        """`start` 가 띄우는 본체. ffmpeg 를 자정까지 돌리고, 끊기면 다시 켜고, 자정이 되면 새 날짜 폴더로 간다."""
        ffmpeg = audio_export.find_ffmpeg(self.cfg)
        if not ffmpeg:
            self.log("ffmpeg 를 못 찾아 끝냄")
            return 2
        device, devices = self.choose_microphone(ffmpeg, mic)
        if not device:
            self.log("마이크를 못 찾아 끝냄: " + (", ".join(devices) or "(없음)"))
            return 3
        restarts: list[float] = []
        while not self.stop_flag.exists():
            now = self.now()
            out = day_dir(self.root, now.date())
            out.mkdir(parents=True, exist_ok=True)
            cmd = build_record_command(ffmpeg, device, out, seconds_until_midnight(now))
            self.log(f"ffmpeg 시작 → {out.name}")
            started = self.monotonic()
            proc = self.popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            code = self._wait(proc)
            if self.stop_flag.exists():
                break
            ran = self.monotonic() - started
            if code == 0 and self.now().date() != now.date():       # 자정에 정상으로 끝남 → 바로 새 날짜로
                continue
            self.log(f"ffmpeg 가 끝남 (코드 {code}, {int(ran)}초 동안)")
            t = self.monotonic()
            if not may_restart(restarts, t):
                self.log(f"{RESTART_WINDOW // 60}분 안에 {MAX_RESTARTS}번 끊겨 멈춤 — 마이크·ffmpeg 를 확인해 주세요")
                return 1
            restarts.append(t)
            self.sleep(RESTART_WAIT)
        self.log("끄기 요청을 받아 끝냄")
        self.pid_file.unlink(missing_ok=True)
        self.stop_flag.unlink(missing_ok=True)
        return 0

    def _wait(self, proc) -> int | None:
        """ffmpeg 가 끝나기를 기다리되 `stop.flag` 가 생기면 'q' 를 보내 깔끔히 닫는다."""
        while True:
            code = proc.poll()
            if code is not None:
                return code
            if self.stop_flag.exists():
                try:
                    proc.stdin.write(b"q")
                    proc.stdin.flush()
                except (OSError, ValueError, AttributeError):
                    pass
                end = self.monotonic() + STOP_GRACE
                while proc.poll() is None and self.monotonic() < end:
                    self.sleep(0.2)
                if proc.poll() is None:
                    proc.kill()
                return proc.poll()
            self.sleep(1)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="하루 녹음 상주 프로그램")
    ap.add_argument("action", choices=["list", "start", "stop", "status", "run"])
    ap.add_argument("--mic", default="", help="마이크 이름(일부). 없으면 config.json 의 day_recorder_mic, 그것도 없으면 첫 번째")
    args = ap.parse_args(argv)
    rec = Recorder()
    if args.action == "list":
        ffmpeg = audio_export.find_ffmpeg(rec.cfg)
        if not ffmpeg:
            print(audio_export.INSTALL_HELP)
            return 1
        devs = list_devices(ffmpeg)
        print("\n".join(f"- {d}" for d in devs) if devs else "마이크를 찾지 못했어요.")
        return 0
    if args.action == "start":
        msg = rec.start(args.mic)
        print(msg)
        return 0 if msg.startswith(("녹음을 시작", "이미")) else 1
    if args.action == "stop":
        print(rec.stop())
        return 0
    if args.action == "status":
        s = rec.status()
        t = s["today"]
        print(f"{'● 녹음 중' if s['running'] else '○ 꺼져 있음'}" + (f" (pid {s['pid']}, 마이크 {s['mic']})" if s["running"] else ""))
        print(f"오늘 조각 {t['count']}개, {t['bytes'] / 1_000_000:.1f} MB" + (f", {t['first']} ~ {t['last']} 시작" if t["count"] else ""))
        return 0
    return rec.run(args.mic)


if __name__ == "__main__":
    sys.exit(main())
