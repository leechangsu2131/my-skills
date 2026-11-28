"""PC 스피커로 나가는 소리의 '크기'만 적어 두고, 영상이 재생된 구간을 찾는다 (T121, ISSUE-055 '조심할 것' ①)

    python speaker_level.py start      # 켜기(백그라운드). 두 번 켜지지 않는다
    python speaker_level.py status     # 켜져 있는지, 마지막으로 적은 때
    python speaker_level.py stop       # 끄기
    python speaker_level.py segments --date 2026-11-28   # 그날 '영상 재생' 구간 보기
    python speaker_level.py run        # (start 가 부르는 것) 앞에서 계속 돌리기

왜: PC 에서 영상을 틀면 스피커 소리가 마이크로 들어가 받아쓴 글에 영상 대사가 섞인다. 녹음은 멈추지 않고,
그 구간만 표시해 받아쓰기에서 뺀다(교사 결정 2026-11-28).

- 적는 것은 1초마다 '시각, 소리 크기(dB)' 한 줄뿐이다. **소리 자체는 저장하지도 보내지도 않는다.**
  파일: 데이터 폴더 `day_audio/<날짜>/speaker_level.csv` (내 PC 에만, 저장소·홈페이지로 보내지 않음)
- 받는 방법: WASAPI 루프백을 `soundcard` 패키지의 `include_loopback` 으로 받는다(윈도우, 순수 파이썬, 장치 이름만 알면 됨).
  `PyAudioWPatch` 도 되지만 윈도우용 바퀴 파일이 따로 필요해 설치가 더 번거로워 고르지 않았다.
  패키지가 없으면 설치 방법만 안내하고 켜지 않는다: `pip install soundcard`
- '영상 재생' 구간: 정한 크기(LOUD_DB)를 넘는 소리가 이어지고(짧은 끊김 JOIN_GAP_SECONDS 는 이어 붙임),
  길이가 MIN_VIDEO_SECONDS 이상인 것. 알림음 같은 짧은 소리는 빠진다. 값은 아래 상수에서 고친다.
- 확인 필요: 교사 PC(교실)에서 실제 영상을 틀어 구간이 맞게 찾아지는지, LOUD_DB 가 맞는지.
"""
import argparse
import importlib.util
import math
import os
import pathlib
import subprocess
import sys
import time
from datetime import date, datetime, timedelta

SKILL_DIR = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(next(p / "_shared" for p in SKILL_DIR.parents if (p / "_shared" / "skill_env.py").is_file())))
from skill_env import data_dir  # noqa: E402

SKILL = "teacherlesson-assistant"

SAMPLE_SECONDS = 1.0        # 크기를 적는 간격
SAMPLE_RATE = 16000         # 크기만 필요해서 낮게(소리는 저장하지 않음)
LOUD_DB = -45.0             # 이보다 큰 소리가 나오면 '소리 나는 중' (0 dB = 가장 큰 소리, 조용하면 -100 쪽)
MIN_VIDEO_SECONDS = 20.0    # 이보다 짧게 끝나는 소리(알림음·효과음)는 영상으로 안 봄
JOIN_GAP_SECONDS = 8.0      # 소리 사이 이만큼까지 끊겨도 한 영상으로 이어 붙임(장면 사이 조용한 부분)
FLOOR_DB = -100.0           # 소리가 아주 없을 때 적는 값
MAX_READ_ERRORS = 10        # 연달아 이만큼 못 읽으면 멈춤(장치가 사라짐)

LEVEL_FILE = "speaker_level.csv"
PID_FILE = "speaker_level.pid"
INSTALL_HELP = ("스피커 소리 크기를 받는 도구(soundcard)가 없어요. 설치: pip install soundcard "
                "(윈도우에서 PC 스피커로 나가는 소리의 크기만 적어요. 소리는 저장하지 않아요).")


# ── 순수 함수: 크기·기록·구간 ──

def rms_db(samples) -> float:
    """소리 조각(-1~1 숫자들)의 크기를 dB(0 = 가장 큼)로. 비었거나 무음이면 FLOOR_DB."""
    total, count = 0.0, 0
    for x in samples:
        total += float(x) * float(x)
        count += 1
    if not count or total <= 0:
        return FLOOR_DB
    return round(max(FLOOR_DB, 10 * math.log10(total / count)), 1)


def format_row(when: datetime, db: float) -> str:
    return f"{when.replace(microsecond=0).isoformat()},{db:.1f}"


def parse_rows(text: str) -> list[tuple[datetime, float]]:
    """csv 글 → [(시각, dB)] 시각 순. 머리글·깨진 줄은 건너뛴다."""
    rows = []
    for line in str(text or "").splitlines():
        head, _, tail = line.strip().partition(",")
        try:
            rows.append((datetime.fromisoformat(head), float(tail)))
        except ValueError:
            continue
    return sorted(rows, key=lambda r: r[0])


def find_video_segments(rows, loud_db: float = LOUD_DB, min_seconds: float = MIN_VIDEO_SECONDS,
                        join_gap: float = JOIN_GAP_SECONDS, sample_seconds: float = SAMPLE_SECONDS):
    """크기 기록 → '영상 재생' 구간 [(시작, 끝)].

    loud_db 를 넘는 줄만 모아, 앞 줄과 join_gap 초 안이면 같은 구간으로 잇는다. 끝은 마지막 소리 줄 + 1 칸.
    길이가 min_seconds 보다 짧은 구간(알림음 등)은 뺀다. 기록이 없는 시간(PC 잠듦·꺼짐)은 끊김으로 본다.
    """
    segments, start, last = [], None, None
    for when, db in sorted(rows, key=lambda r: r[0]):
        if db <= loud_db:
            continue
        if start is None:
            start = last = when
        elif (when - last).total_seconds() <= join_gap:
            last = when
        else:
            segments.append((start, last))
            start = last = when
    if start is not None:
        segments.append((start, last))
    out = []
    for first, final in segments:
        end = final + timedelta(seconds=sample_seconds)
        if (end - first).total_seconds() >= min_seconds:
            out.append((first, end))
    return out


def segments_text(segments) -> str:
    if not segments:
        return "영상 재생 구간이 없어요."
    return "\n".join(f"{a:%H:%M:%S} ~ {b:%H:%M:%S} ({int((b - a).total_seconds() // 60)}분 {int((b - a).total_seconds() % 60)}초)"
                     for a, b in segments)


def level_path(base: pathlib.Path, day) -> pathlib.Path:
    return pathlib.Path(base) / str(day) / LEVEL_FILE


def segments_for_day(base: pathlib.Path, day, **kwargs):
    path = level_path(base, day)
    if not path.is_file():
        return []
    return find_video_segments(parse_rows(path.read_text(encoding="utf-8", errors="replace")), **kwargs)


# ── 기록 돌리기 (장치는 read_block 으로 받아서 시험에서는 가짜) ──

def run_loop(read_block, base: pathlib.Path, now=datetime.now, should_stop=lambda: False,
             max_errors: int = MAX_READ_ERRORS, on_error=lambda exc: None) -> str:
    """1초 분량을 읽을 때마다 '시각,크기' 한 줄을 그날 폴더에 덧붙인다(자정이 지나면 다음 날 폴더). 멈춘 까닭을 돌려준다."""
    errors = 0
    while not should_stop():
        try:
            samples = read_block()
        except Exception as exc:  # 장치가 잠깐 끊김 — 연달아 많이 실패할 때만 멈춘다
            errors += 1
            on_error(exc)
            if errors >= max_errors:
                return "장치를 읽지 못해 멈췄어요"
            continue
        errors = 0
        when = now()
        path = level_path(base, when.date())
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as f:
            f.write(format_row(when, rms_db(samples)) + "\n")
    return "끔"


def open_loopback_reader(sc=None):
    """soundcard 로 기본 스피커의 루프백을 열어 read_block() 을 돌려준다. 없으면 ImportError."""
    if sc is None:
        import soundcard as sc  # noqa: PLC0415
    speaker = sc.default_speaker()
    mic = sc.get_microphone(id=str(speaker.name), include_loopback=True)
    recorder = mic.recorder(samplerate=SAMPLE_RATE, channels=1)
    recorder.__enter__()
    frames = int(SAMPLE_RATE * SAMPLE_SECONDS)

    def read_block():
        data = recorder.record(numframes=frames)
        return [float(v) for v in data.reshape(-1)]
    return read_block


# ── 켜기·끄기·상태 (pid 파일) ──

def pid_alive(pid) -> bool:
    try:
        pid = int(pid)
    except (TypeError, ValueError):
        return False
    if pid <= 0:
        return False
    try:
        import ctypes
        handle = ctypes.windll.kernel32.OpenProcess(0x1000, False, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
        if not handle:
            return False
        code = ctypes.c_ulong()
        ctypes.windll.kernel32.GetExitCodeProcess(handle, ctypes.byref(code))
        ctypes.windll.kernel32.CloseHandle(handle)
        return code.value == 259  # STILL_ACTIVE
    except (AttributeError, OSError):  # 윈도우가 아님
        try:
            os.kill(pid, 0)
            return True
        except OSError:
            return False


def read_pid(base: pathlib.Path):
    try:
        return int((pathlib.Path(base) / PID_FILE).read_text(encoding="utf-8").strip())
    except (OSError, ValueError):
        return None


def status(base: pathlib.Path, alive=pid_alive, today: date | None = None) -> dict:
    pid = read_pid(base)
    running = pid is not None and alive(pid)
    last = None
    rows = parse_rows(level_path(base, today or date.today()).read_text(encoding="utf-8", errors="replace")) \
        if level_path(base, today or date.today()).is_file() else []
    if rows:
        last = rows[-1][0]
    return {"running": running, "pid": pid if running else None, "last_row": last}


def status_text(info: dict) -> str:
    if not info["running"]:
        return "꺼져 있어요" + (f" (오늘 마지막 기록 {info['last_row']:%H:%M:%S})" if info["last_row"] else "")
    return f"켜져 있어요(pid {info['pid']})" + (f", 마지막 기록 {info['last_row']:%H:%M:%S}" if info["last_row"] else ", 아직 기록 없음")


def start(base: pathlib.Path, spawn=None, alive=pid_alive, have_package=None) -> str:
    """이미 켜져 있으면 다시 켜지 않는다. 패키지가 없으면 안내만 하고 켜지 않는다."""
    base = pathlib.Path(base)
    if status(base, alive)["running"]:
        return "이미 켜져 있어요."
    if have_package is None:
        have_package = importlib.util.find_spec("soundcard") is not None
    if not have_package:
        return INSTALL_HELP
    base.mkdir(parents=True, exist_ok=True)
    if spawn is None:
        flags = (subprocess.DETACHED_PROCESS | subprocess.CREATE_NO_WINDOW) if os.name == "nt" else 0
        spawn = lambda: subprocess.Popen([sys.executable, str(pathlib.Path(__file__).resolve()), "run"],  # noqa: E731
                                         creationflags=flags, stdin=subprocess.DEVNULL,
                                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).pid
    pid = spawn()
    (base / PID_FILE).write_text(str(pid), encoding="utf-8")
    return f"켰어요(pid {pid}). 끄려면 python speaker_level.py stop"


def stop(base: pathlib.Path, alive=pid_alive, kill=None) -> str:
    base = pathlib.Path(base)
    pid = read_pid(base)
    if pid is None or not alive(pid):
        (base / PID_FILE).unlink(missing_ok=True)
        return "켜져 있지 않아요."
    if kill is None:
        def kill(p):
            if os.name == "nt":
                subprocess.run(["taskkill", "/PID", str(p), "/F"], check=False, capture_output=True)
            else:
                os.kill(p, 15)
    kill(pid)
    (base / PID_FILE).unlink(missing_ok=True)
    return "껐어요."


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="PC 스피커 소리 크기 기록 → 영상 재생 구간 (소리는 저장하지 않음)")
    ap.add_argument("action", choices=["start", "stop", "status", "run", "segments"])
    ap.add_argument("--date", default=str(date.today()), help="segments 에서 볼 날짜 (기본: 오늘)")
    args = ap.parse_args(argv)
    base = data_dir(SKILL) / "day_audio"
    if args.action == "start":
        print(start(base))
    elif args.action == "stop":
        print(stop(base))
    elif args.action == "status":
        print(status_text(status(base)))
    elif args.action == "segments":
        print(segments_text(segments_for_day(base, args.date)))
    else:  # run
        try:
            read_block = open_loopback_reader()
        except ImportError:
            print(INSTALL_HELP)
            return 1
        base.mkdir(parents=True, exist_ok=True)
        (base / PID_FILE).write_text(str(os.getpid()), encoding="utf-8")
        try:
            print(run_loop(read_block, base, on_error=lambda exc: time.sleep(1)))
        finally:
            (base / PID_FILE).unlink(missing_ok=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
