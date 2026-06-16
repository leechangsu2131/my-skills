"""
app.py — i-scream 과목별 평가 자동 기록 Flask 웹 서버

Supabase 데이터를 연동하고, 웹 브라우저를 통해 학생들의 교과 평가 내용을 미리 확인 및 편집한 뒤,
CDP로 연결된 Chrome 브라우저를 통해 i-scream 사이트에 자동으로 입력하는 웹 UI를 제공합니다.

실행: python app.py
접속: http://localhost:5028
"""

import asyncio
import threading
import queue
import sys
import io
import os
import json
from datetime import datetime
from typing import Optional

from flask import Flask, render_template, request, jsonify, Response

import supabase_fetch
import eval_builder
import iscream_evaluate

app = Flask(__name__)

# ── 전역 상태 관리 ───────────────────────────────────────────
_state = {
    'running': False,
    'results': None,
}
_log_queue: queue.Queue = queue.Queue()

# Playwright 비동기 이벤트 루프 스레드 세션
_session = {
    'loop': None,
    'thread': None,
}


# ── 이벤트 루프 관리 ─────────────────────────────────────────
def _start_event_loop():
    """백그라운드에서 실행될 asyncio 이벤트 루프"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    _session['loop'] = loop
    loop.run_forever()


def _ensure_loop():
    """이벤트 루프가 활성화되어 있는지 확인하고 시작합니다."""
    if _session['thread'] is None or not _session['thread'].is_alive():
        _session['loop'] = None
        t = threading.Thread(target=_start_event_loop, daemon=True)
        t.start()
        _session['thread'] = t
        import time
        while _session['loop'] is None:
            time.sleep(0.01)


# ── Stdout 리다이렉션을 위한 SSE 큐 작성기 ───────────────────
class SSEQueueWriter:
    """sys.stdout의 내용을 캡처하여 SSE 큐로 전달합니다."""
    def write(self, text):
        for line in text.split('\n'):
            line = line.rstrip()
            if line:
                _log_queue.put(('log', line))

    def flush(self):
        pass

    def fileno(self):
        raise io.UnsupportedOperation('fileno')


# ── 백그라운드 태스크 실행 래퍼 ──────────────────────────────────
def _run_in_background(coro_func, *args):
    """코루틴을 백그라운드 이벤트 루프에서 실행하며, 콘솔 출력을 큐로 보냅니다."""
    def wrapper():
        old_stdout = sys.stdout
        sys.stdout = SSEQueueWriter()
        try:
            _ensure_loop()
            future = asyncio.run_coroutine_threadsafe(
                coro_func(*args), _session['loop']
            )
            # 완료 대기 (최대 30분)
            results = future.result(timeout=1800)
            _state['results'] = results
            print("🎉 모든 자동화 처리가 정상적으로 완료되었습니다!")
        except Exception as e:
            print(f"❌ 자동화 처리 중 오류 발생: {e}")
            import traceback
            traceback.print_exc()
        finally:
            sys.stdout = old_stdout
            _state['running'] = False
            _log_queue.put(('done', None))

    t = threading.Thread(target=wrapper, daemon=True)
    t.start()


# ── 비동기 작업: i-scream 일괄 평가 기록 ───────────────────────
async def _do_evaluate_batch(eval_data_list, port, dry_run):
    """실제 자동 기록 모듈을 호출하여 브라우저 제어를 실행합니다."""
    print(f"🚀 자동 입력 시작 — 총 {len(eval_data_list)}건의 평가 기록")
    print(f"   [디버깅 포트: {port} | Dry Run: {'활성화 (저장 안 함)' if dry_run else '비활성화 (실제 저장)'}]")
    print("=" * 65)

    results = await iscream_evaluate.process_batch(
        eval_data_list=eval_data_list,
        port=port,
        dry_run=dry_run,
        preview=False  # 웹 UI를 통해 미리 검토하므로 CLI 대기 비활성화
    )
    return results


# ── Flask API 라우트 ─────────────────────────────────────────

@app.route('/')
def index():
    """메인 대시보드 페이지"""
    return render_template('index.html')


@app.route('/api/env-status')
def env_status():
    """Supabase 연결을 위한 환경 변수 세팅 상태 확인"""
    try:
        url, key = supabase_fetch._load_env()
        has_credentials = bool(url and key)
    except Exception:
        has_credentials = False

    # CDP 포트 조회
    cdp_port = int(os.environ.get("ISCREAM_CDP_PORT", 9222))

    return jsonify({
        'supabase_configured': has_credentials,
        'cdp_port': cdp_port,
        'running': _state['running']
    })


@app.route('/api/students')
def get_students():
    """Supabase에서 전체 학생 목록 및 기록 요약을 조회합니다."""
    try:
        records = supabase_fetch.fetch_all_records()
        if not records:
            return jsonify({'students': []})

        students = supabase_fetch.get_unique_students(records)
        student_list = []

        for name in students:
            student_records = supabase_fetch.get_records_for_student(records, name)
            summary = eval_builder.build_eval_summary(name, student_records)
            
            # 과목별 요약 정보
            subjects = []
            for subj, data in summary['subjects'].items():
                if subj == "출결":
                    continue
                subjects.append({
                    'name': subj,
                    'count': data['count'],
                    'sentiment': {
                        'pos': data['positive_pct'],
                        'neu': data['neutral_pct'],
                        'neg': data['negative_pct'],
                    },
                    'start_date': data['date_range']['start'],
                    'end_date': data['date_range']['end'],
                })

            student_list.append({
                'name': name,
                'record_count': summary['total_records'],
                'subjects': subjects
            })

        return jsonify({'students': student_list})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/preview', methods=['POST'])
def generate_preview():
    """
    선택한 학생들의 과목별 평가 미리보기 초안을 일괄 생성합니다.
    (LLM 생성 평가가 있으면 해당 텍스트를, 없으면 누적 기록 단순 연결본 제공)
    """
    data = request.get_json() or {}
    student_names = data.get('students', [])
    
    if not student_names:
        return jsonify({'error': '학생을 최소 한 명 이상 선택해주세요.'}), 400

    try:
        records = supabase_fetch.fetch_all_records()
        preview_data = []

        for name in student_names:
            student_records = supabase_fetch.get_records_for_student(records, name)
            if not student_records:
                continue

            summary = eval_builder.build_eval_summary(name, student_records)
            evals = eval_builder.build_eval_data_for_iscream(name, student_records)
            
            for ev in evals:
                subject = ev['subject']
                if subject == "출결":
                    continue
                
                # 해당 과목 통계 추출
                subj_sum = summary['subjects'].get(subject, {})
                
                # 주요 기록 스니펫 추출
                snippets = []
                for rec in subj_sum.get('key_records', []):
                    snippets.append({
                        'date': rec['date'],
                        'title': rec['title'],
                        'content': rec['content'],
                        'sentiment': rec['sentiment']
                    })

                preview_data.append({
                    'student': name,
                    'subject': subject,
                    'eval_text': ev['eval_text'],
                    'record_count': subj_sum.get('count', 0),
                    'start_date': subj_sum.get('date_range', {}).get('start', ''),
                    'end_date': subj_sum.get('date_range', {}).get('end', ''),
                    'sentiment': {
                        'pos': subj_sum.get('positive_pct', 0),
                        'neu': subj_sum.get('neutral_pct', 0),
                        'neg': subj_sum.get('negative_pct', 0),
                    },
                    'key_records': snippets
                })

        return jsonify({'preview': preview_data})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/run', methods=['POST'])
def run_automation():
    """웹 UI에서 검토 및 수정한 평가 데이터를 바탕으로 자동 입력을 시작합니다."""
    if _state['running']:
        return jsonify({'error': '이미 자동화 작업이 진행 중입니다.'}), 409

    data = request.get_json() or {}
    eval_data_list = data.get('eval_data', [])
    dry_run = bool(data.get('dry_run', False))
    port = int(data.get('port', 9222))

    if not eval_data_list:
        return jsonify({'error': '입력할 평가 데이터가 없습니다.'}), 400

    # 큐 비우기
    while not _log_queue.empty():
        try:
            _log_queue.get_nowait()
        except queue.Empty:
            break

    _state['running'] = True
    _state['results'] = None
    iscream_evaluate.stop_requested = False

    # 백그라운드 스레드에서 자동화 기동
    _run_in_background(_do_evaluate_batch, eval_data_list, port, dry_run)
    return jsonify({'status': 'started'})


@app.route('/api/stop', methods=['POST'])
def stop_automation():
    """진행 중인 자동 입력을 긴급 중단합니다."""
    iscream_evaluate.stop_requested = True
    print("\n🛑 [웹 UI] 자동화 중단 요청이 접수되었습니다. 현재 학생까지만 처리 후 정지합니다.")
    return jsonify({'status': 'stopping'})


@app.route('/api/close-browser', methods=['POST'])
def close_browser():
    """브라우저 연결 해제 및 리소스 해제"""
    # 비동기로 브라우저를 닫습니다.
    _ensure_loop()
    
    async def cleanup():
        print("\n🧹 브라우저 리소스를 해제합니다.")
        # 브라우저 연결 닫기는 iscream_evaluate 내 finalize 로직이나,
        # 플레이라이트 인스턴스 소멸을 유도합니다.
        # process_batch가 끝날 때 자동으로 close 되나, 수동 세션 클리어용입니다.
        
    asyncio.run_coroutine_threadsafe(cleanup(), _session['loop'])
    return jsonify({'status': 'cleanup_scheduled'})


@app.route('/api/stream')
def stream_logs():
    """SSE(Server-Sent Events)를 통해 실시간 로그를 브라우저로 전송합니다."""
    def generate():
        while True:
            try:
                typ, payload = _log_queue.get(timeout=20)
            except queue.Empty:
                # 연결 유지용 핑
                yield "data: ping\n\n"
                continue

            if typ == 'log':
                yield f"data: {json.dumps({'type': 'log', 'text': payload}, ensure_ascii=False)}\n\n"
            elif typ == 'done':
                # 자동화 작업이 끝났음을 브라우저에 공지하고 결과 전송
                yield f"data: {json.dumps({'type': 'done', 'results': _state['results']}, ensure_ascii=False)}\n\n"
                break

    return Response(
        generate(),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no',
            'Content-Type': 'text/event-stream'
        }
    )


if __name__ == '__main__':
    port = int(os.environ.get("FLASK_PORT", 5028))
    print("=" * 65)
    print(f"🌟 i-scream 과목별 평가 자동 입력 시스템 서버가 기동되었습니다.")
    print(f"👉 접속 주소: http://localhost:{port}")
    print("=" * 65)
    app.run(host='0.0.0.0', port=port, debug=False, threaded=True)
