"""
S2B 학교장터 자동 구매 — Flask 웹 서버 (2단계 플로우)

플로우: 검색 → 결과 확인 → 물품 선택 → 견적신청
실행: python app.py
접속: http://localhost:5026
"""

import asyncio
import threading
import queue
import sys
import io
import os
import json
from datetime import datetime

from flask import Flask, render_template, request, jsonify, Response, send_file

app = Flask(__name__)

# ── 전역 상태 ─────────────────────────────────────────────
_state = {
    'running': False,
    'report_path': None,
}
_q: queue.Queue = queue.Queue()

# Playwright 브라우저 세션 (이벤트 루프 스레드 전용)
_session = {
    'loop': None,
    'thread': None,
    'pw': None,
    'browser': None,
    'page': None,
}


# ── 이벤트 루프 관리 ─────────────────────────────────────
def _start_event_loop():
    """백그라운드에서 영구적으로 돌아가는 asyncio 이벤트 루프"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    _session['loop'] = loop
    loop.run_forever()


def _ensure_loop():
    """이벤트 루프가 돌고 있는지 확인하고, 없으면 시작"""
    if _session['thread'] is None or not _session['thread'].is_alive():
        _session['loop'] = None
        t = threading.Thread(target=_start_event_loop, daemon=True)
        t.start()
        _session['thread'] = t
        import time
        while _session['loop'] is None:
            time.sleep(0.01)


# ── stdout → SSE 큐 변환기 ────────────────────────────────
class _QueueWriter:
    """print() 출력을 SSE 큐로 전달"""
    def write(self, text):
        for line in text.split('\n'):
            line = line.rstrip()
            if line:
                _q.put(('log', line))

    def flush(self):
        pass

    def fileno(self):
        raise io.UnsupportedOperation('fileno')


# ── 백그라운드 실행 헬퍼 ──────────────────────────────────
def _run_in_bg(coro_func, *args):
    """코루틴을 이벤트 루프에서 실행하고, stdout을 SSE 큐로 리다이렉트"""
    def wrapper():
        old_stdout = sys.stdout
        sys.stdout = _QueueWriter()
        try:
            _ensure_loop()
            future = asyncio.run_coroutine_threadsafe(
                coro_func(*args), _session['loop']
            )
            future.result(timeout=600)  # 최대 10분
        except Exception as e:
            print(f"❌ 오류 발생: {e}")
        finally:
            sys.stdout = old_stdout
            _state['running'] = False
            _q.put(('done', None))

    t = threading.Thread(target=wrapper, daemon=True)
    t.start()


# ── 비동기 작업: 검색 ────────────────────────────────────
async def _do_search(items, uid, pwd):
    """S2B에서 물품을 검색하고 결과를 SSE로 전달"""
    from s2b_login import login as s2b_login
    from s2b_search import search_items

    # 브라우저가 없으면 새로 시작 + 로그인
    if _session.get('browser') is None:
        from playwright.async_api import async_playwright
        pw = await async_playwright().start()
        _session['pw'] = pw
        browser = await pw.chromium.launch(headless=False, slow_mo=300)
        ctx = await browser.new_context(
            viewport={'width': 1280, 'height': 900},
            locale='ko-KR',
        )
        page = await ctx.new_page()
        _session['browser'] = browser
        _session['page'] = page

        print("🔐 S2B 로그인 중...")
        login_ok = await s2b_login(page, uid, pwd)
        if not login_ok:
            print("❌ 로그인 실패. 작업을 종료합니다.")
            await _do_close_browser()
            return
        print("✅ 로그인 성공!\n")

    page = _session['page']
    all_results = {}

    print(f"🔍 총 {len(items)}개 검색어에 대해 물품을 검색합니다.")
    print("=" * 50)

    for i, item in enumerate(items):
        name = item['name']
        print(f"\n── [{i+1}/{len(items)}] '{name}' 검색 중...")
        found = await search_items(page, name)
        all_results[name] = found or []
        count = len(found or [])
        if count > 0:
            print(f"  ✅ {count}개 결과 발견")
        else:
            print(f"  ⚠ 검색 결과 없음")

    print(f"\n{'='*50}")
    total = sum(len(v) for v in all_results.values())
    print(f"📊 검색 완료 — 총 {total}개 물품을 찾았습니다.")
    print("아래 검색 결과에서 원하는 물품을 선택하고 견적신청해주세요.")

    # 검색 결과를 SSE로 전송
    _q.put(('search_results', all_results))


# ── 비동기 작업: 견적신청 ─────────────────────────────────
async def _do_add_to_cart(selected_items, dry_run):
    """선택된 물품들을 견적서에 담기"""
    from s2b_cart import add_to_cart
    from s2b_report import save_report

    page = _session.get('page')
    if page is None:
        print("❌ 브라우저 세션이 없습니다. 먼저 검색을 실행해주세요.")
        return

    results = []
    print(f"📦 견적서 담기 시작 — 총 {len(selected_items)}개 물품")
    if dry_run:
        print("   ※ 테스트 모드: 실제 담기는 하지 않습니다.")
    print("=" * 50)

    for i, item in enumerate(selected_items):
        item_id = item['id']
        qty = item.get('quantity', 1)
        title = item.get('title', '')
        print(f"\n── [{i+1}/{len(selected_items)}] {title[:45]}")
        print(f"   물품번호: {item_id}  |  수량: {qty}")

        entry = {
            'request_name': title,
            'quantity': qty,
            'selected_title': title,
            'selected_id': item_id,
            'image': item.get('image', ''),
            'price': item.get('price', ''),
            'link': item.get('link', ''),
            'success': False,
            'fail_reason': '',
            'processed_at': datetime.now(),
        }

        ok = await add_to_cart(page, item_id, quantity=qty, dry_run=dry_run)
        entry['success'] = ok
        entry['processed_at'] = datetime.now()
        if not ok:
            entry['fail_reason'] = '견적서 담기 실패'

        results.append(entry)
        await page.wait_for_timeout(2000)

    # 리포트 저장
    if results:
        try:
            path = save_report(results)
            _state['report_path'] = path
            _q.put(('report', path))
            success = sum(1 for r in results if r['success'])
            print(f"\n{'='*50}")
            print(f"📊 리포트 저장 완료: {os.path.basename(path)}")
            print(f"✅ 완료 — 성공 {success}건 / 실패 {len(results) - success}건")
        except Exception as e:
            print(f"⚠ 리포트 저장 중 오류: {e}")


# ── 비동기 작업: 브라우저 종료 ─────────────────────────────
async def _do_close_browser():
    """Playwright 브라우저 세션 정리"""
    if _session.get('browser'):
        try:
            await _session['browser'].close()
        except Exception:
            pass
    if _session.get('pw'):
        try:
            await _session['pw'].stop()
        except Exception:
            pass
    _session['browser'] = None
    _session['page'] = None
    _session['pw'] = None
    print("🔒 브라우저 세션이 종료되었습니다.")


# ── Flask 라우트 ─────────────────────────────────────────

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/env-status')
def env_status():
    """.env 파일 인증정보 존재 여부 반환"""
    from s2b_login import S2B_USER_ID, S2B_USER_PW
    return jsonify({
        'has_uid': bool(S2B_USER_ID),
        'has_pwd': bool(S2B_USER_PW),
    })


@app.route('/api/search', methods=['POST'])
def search_route():
    """검색어 목록으로 S2B 검색 실행"""
    if _state['running']:
        return jsonify({'error': '이미 작업이 진행 중입니다.'}), 409

    data = request.get_json() or {}
    items = data.get('items', [])
    uid = data.get('uid', '').strip()
    pwd = data.get('pwd', '').strip()

    if not uid or not pwd:
        from s2b_login import S2B_USER_ID, S2B_USER_PW
        uid = uid or S2B_USER_ID
        pwd = pwd or S2B_USER_PW

    if not items:
        return jsonify({'error': '검색할 품목을 하나 이상 입력해주세요.'}), 400
    if not uid or not pwd:
        return jsonify({'error': 'S2B 아이디/비밀번호를 입력하거나 .env 파일을 설정해주세요.'}), 400

    # 큐 초기화
    while not _q.empty():
        try:
            _q.get_nowait()
        except queue.Empty:
            break

    _state['running'] = True
    _state['report_path'] = None

    _run_in_bg(_do_search, items, uid, pwd)
    return jsonify({'status': 'started'})


@app.route('/api/add-to-cart', methods=['POST'])
def add_to_cart_route():
    """선택된 물품들을 견적서에 담기"""
    if _state['running']:
        return jsonify({'error': '이미 작업이 진행 중입니다.'}), 409

    data = request.get_json() or {}
    selected = data.get('selected', [])
    dry_run = bool(data.get('dry_run', False))

    if not selected:
        return jsonify({'error': '선택된 물품이 없습니다.'}), 400

    if _session.get('page') is None:
        return jsonify({'error': '브라우저 세션이 없습니다. 먼저 검색을 실행해주세요.'}), 400

    # 큐 초기화
    while not _q.empty():
        try:
            _q.get_nowait()
        except queue.Empty:
            break

    _state['running'] = True
    _state['report_path'] = None

    _run_in_bg(_do_add_to_cart, selected, dry_run)
    return jsonify({'status': 'started'})


@app.route('/api/close-browser', methods=['POST'])
def close_browser_route():
    """브라우저 세션 종료"""
    if _session.get('browser') is None:
        return jsonify({'status': 'already_closed'})

    _ensure_loop()
    asyncio.run_coroutine_threadsafe(
        _do_close_browser(), _session['loop']
    )
    return jsonify({'status': 'closing'})


@app.route('/api/stream')
def stream():
    """SSE — 자동화 진행 로그 및 검색 결과를 실시간으로 전달"""
    def generate():
        while True:
            try:
                typ, payload = _q.get(timeout=25)
            except queue.Empty:
                yield "data: ping\n\n"
                continue

            if typ == 'log':
                yield f"data: {json.dumps({'type': 'log', 'text': payload}, ensure_ascii=False)}\n\n"
            elif typ == 'search_results':
                yield f"data: {json.dumps({'type': 'search_results', 'data': payload}, ensure_ascii=False)}\n\n"
            elif typ == 'report':
                yield f"data: {json.dumps({'type': 'report'})}\n\n"
            elif typ == 'done':
                yield f"data: {json.dumps({'type': 'done'})}\n\n"
                break

    return Response(
        generate(),
        mimetype='text/event-stream',
        headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'},
    )


@app.route('/api/download')
def download():
    """엑셀 리포트 다운로드"""
    path = _state.get('report_path')
    if not path or not os.path.exists(path):
        return jsonify({'error': '다운로드할 리포트 파일이 없습니다.'}), 404
    return send_file(
        path,
        as_attachment=True,
        download_name=os.path.basename(path),
    )


if __name__ == '__main__':
    print("=" * 50)
    print("🌐 S2B 자동 구매 서버 시작")
    print("   접속 주소: http://localhost:5026")
    print("=" * 50)
    app.run(host='0.0.0.0', port=5026, debug=False, threaded=True)
