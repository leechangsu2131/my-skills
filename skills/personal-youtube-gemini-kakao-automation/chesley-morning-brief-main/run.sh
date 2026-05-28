#!/bin/bash
# 체슬리모닝브리프 자동요약 실행 스크립트
# cron에서 호출됨

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
VENV_DIR="$SCRIPT_DIR/.venv"
LOG_FILE="$SCRIPT_DIR/chesley_brief.log"

# 로그 함수
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

log "===== 실행 시작 ====="

# 가상환경 생성 (최초 1회)
if [ ! -d "$VENV_DIR" ]; then
    log "가상환경 생성 중..."
    python3 -m venv "$VENV_DIR"
    "$VENV_DIR/bin/pip" install -q -r "$SCRIPT_DIR/requirements.txt"
    "$VENV_DIR/bin/python" -m patchright install chromium
    log "가상환경 설정 완료"
fi

# 스크립트 실행
log "chesley_brief.py 실행 중..."
"$VENV_DIR/bin/python" "$SCRIPT_DIR/chesley_brief.py" 2>&1 | tee -a "$LOG_FILE"

log "===== 실행 완료 ====="
