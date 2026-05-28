import asyncio
import threading
import queue
import sys
import importlib
import io
import os
import glob
import json
from flask import Flask, render_template, request, jsonify, Response

import parse_gongmun
from edufine_report import save_report
import playwright_edufine

app = Flask(__name__)

_state = {
    'running': False,
    'data': None
}
_q = queue.Queue()
_session = {
    'loop': None,
    'thread': None,
}

class _QueueWriter:
    def write(self, text):
        for line in text.split('\n'):
            line = line.rstrip()
            if line:
                _q.put(('log', line))
    def flush(self): pass
    def fileno(self): raise io.UnsupportedOperation('fileno')

def _start_event_loop():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    _session['loop'] = loop
    loop.run_forever()

def _ensure_loop():
    if _session['thread'] is None or not _session['thread'].is_alive():
        _session['loop'] = None
        t = threading.Thread(target=_start_event_loop, daemon=True)
        t.start()
        import time
        while _session['loop'] is None:
            time.sleep(0.01)

async def run_automation(target_path, dry_run, draft_title="", draft_summary=""):
    try:
        files_to_process = []
        is_empty_run = False
        
        if target_path == "NO_FILE":
            is_empty_run = True
        elif os.path.isfile(target_path):
            files_to_process.append(target_path)
        elif os.path.isdir(target_path):
            search_pattern = os.path.join(target_path, "*.odt")
            files_to_process = glob.glob(search_pattern)
            if not files_to_process:
                print(f"[안내] 디렉토리에 ODT 파일이 없습니다. 빈 기안 모드로 진행합니다.")
                is_empty_run = True
        else:
            print(f"[안내] 지정된 경로({target_path})를 찾을 수 없거나 파일이 없습니다. 빈 기안 모드로 진행합니다.")
            is_empty_run = True
            
        if not files_to_process and not is_empty_run:
            is_empty_run = True
            
        parsed_items = []
        if is_empty_run:
            print("[안내] ODT 파일 없이 수동 기안 모드로 실행합니다.")
            t = draft_title if draft_title else '빈 기안 (수동 작성)'
            s = draft_summary if draft_summary else '내용을 수동으로 입력하세요.'
            parsed_items.append({'_filepath': '수동 기안', 'data': {'제목': t, '내용': s}})
        else:
            print(f"[안내] 총 {len(files_to_process)}개의 파일을 처리합니다.\n")
            for file_path in files_to_process:
                print(f"[파싱 중] {os.path.basename(file_path)}")
                try:
                    data = parse_gongmun.parse_odt(file_path)
                    parsed_items.append({'_filepath': file_path, 'data': data})
                except Exception as e:
                    print(f"  [파싱 오류] {e}")
                    parsed_items.append({'_filepath': file_path, 'data': {'제목': f'오류 발생 문서 ({os.path.basename(file_path)})'}, 'error': str(e)})

        results = await playwright_edufine.process_batch(parsed_items, dry_run=dry_run)
        
        if results:
            try:
                report_path = save_report(results)
                print("=" * 60)
                print(f"[리포트 완료] 처리 결과 리포트(Excel)가 저장되었습니다:\n -> {os.path.abspath(report_path)}")
            except Exception as e:
                print(f"\n[오류] 리포트 저장 실패: {e}")
    finally:
        _state['running'] = False
        _q.put(('done', None))

def _run_in_bg(coro_func, *args):
    def wrapper():
        old_stdout = sys.stdout
        sys.stdout = _QueueWriter()
        try:
            _ensure_loop()
            future = asyncio.run_coroutine_threadsafe(
                coro_func(*args), _session['loop']
            )
            future.result(timeout=3600*3)
        except Exception as e:
            print(f"[오류] 백그라운드 작업 실패: {e}")
        finally:
            sys.stdout = old_stdout

    t = threading.Thread(target=wrapper, daemon=True)
    t.start()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/fetch-s2b', methods=['GET'])
def fetch_s2b():
    import s2b_cart_scraper
    import importlib
    importlib.reload(s2b_cart_scraper)
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        items = loop.run_until_complete(s2b_cart_scraper.get_s2b_cart_items())
        loop.close()
        
        if not items:
            return jsonify({'error': '장바구니에 물품이 없거나 로그인에 실패했습니다.'})
            
        item_list = "".join([f"{item['name']}\t\t{item['quantity']}\t\t{item['unit_price']}\n" for item in items])
        return jsonify({'item_list': item_list})
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/api/generate-prompt', methods=['POST'])
def generate_prompt():
    data = request.get_json() or {}
    target_path = data.get('path', '').strip()
    item_list = data.get('items', '').strip()
    # 기본 안내문구를 지운 경우 무시
    if item_list.startswith("[S2B"):
        item_list = ""
    elif item_list.startswith("S2B 장바구니 데이터를"):
        item_list = ""
    elif item_list.startswith("오류 발생:"):
        item_list = ""
    
    prompt = "당신은 대한민국 초등학교 행정실 담당자입니다.\n"
    
    if target_path and os.path.isfile(target_path) and target_path.lower().endswith('.odt'):
        try:
            parsed_data = parse_gongmun.parse_odt(target_path)
            
            sender = parsed_data.get('발신처', '')
            title = parsed_data.get('제목', '')
            sihaeng_no = parsed_data.get('sihaeng_no', '')
            sihaeng_date = parsed_data.get('sihaeng_date', '').replace('-', '.')
            jeopsu_no = parsed_data.get('jeopsu_no', '')
            jeopsu_date = parsed_data.get('jeopsu_date', '').replace('-', '.')
            
            if item_list:
                prompt += "아래 수신 공문 정보와 구매할 물품 목록을 바탕으로 에듀파인 기안문의 '제목'과 '본문'을 작성해주세요.\n\n"
            else:
                prompt += "아래 수신 공문 정보를 바탕으로 에듀파인 기안문의 '제목'과 '본문'을 작성해주세요.\n\n"
                
            prompt += "[수신 공문 정보]\n"
            prompt += f"- 발신처: {sender}\n"
            prompt += f"- 원문 제목: {title}\n"
            if sihaeng_no:
                prompt += f"- 시행 공문번호: {sihaeng_no} ({sihaeng_date})\n"
            if jeopsu_no:
                prompt += f"- 접수 공문번호: {jeopsu_no} ({jeopsu_date})\n"
                
            related = parsed_data.get('관련공문', [])
            if related:
                prompt += f"- 관련 공문번호: {related[0]['번호']} ({related[0]['일자']})\n"
                
            if item_list:
                prompt += f"\n[구매 예정 물품 목록]\n{item_list}\n"
                
            prompt += "\n[작성 규칙]\n"
            prompt += "1. 제목: 원문 제목을 그대로 쓰지 말고, 우리 학교 입장의 처리 행위가 드러나도록 작성\n"
            prompt += "   예) 원문 \"체육시설 개선 사업비 교부 안내\" → 기안 제목 \"2026년 학교 체육시설 개선 사업비 수령 및 집행 계획\"\n"
            
            if item_list:
                prompt += "2. 본문 구성: 품의명세서 양식을 엄격하게 따를 것\n"
            else:
                prompt += "2. 본문 구성:\n"
                if sihaeng_no:
                    prompt += f"   - 관련: {sender}-{sihaeng_no}({sihaeng_date}) 으로 시작\n"
                elif jeopsu_no:
                    prompt += f"   - 관련: 본교 {jeopsu_no}({jeopsu_date}) 으로 시작\n"
                else:
                    prompt += "   - 관련 공문번호로 시작\n"
                prompt += "   - 2~3개 항목으로 간결하게 작성\n"
                prompt += "   - 마지막 항목은 반드시 \"붙임\" 또는 \"이상\" 으로 마무리\n"
                
            prompt += "3. 격식체(합쇼체) 사용\n"
            prompt += "4. 항목 번호는 1. 2. 3. 형식, 세부항목은 가. 나. 형식\n\n"
            
            prompt += "[출력 형식]\n"
            prompt += "제목: (기안문 제목)\n\n"
            prompt += "본문:\n"
            
            if item_list:
                prompt += "1. 관련: (수신 공문번호, 없을시 생략가능)\n"
                prompt += "2. (해당사업명) 관련 물품을 아래와 같이 구입하고자 합니다.\n"
                prompt += "  가. 내역: (대표물품명) 외 O건\n"
                prompt += "  나. 용도: (물품 구매 용도)\n"
                prompt += "  다. 소요예산: 금O,OOO원\n"
                prompt += "  라. 산출내역: 품목을 바탕으로 계산식 작성 (품의명세서 참조)\n"
                prompt += "붙임  지출(지급)품의서 1부.  끝.\n"
            else:
                prompt += "1. 관련: ...\n"
                prompt += "2. ...\n"
                prompt += "3. ...\n"
                prompt += "붙임 없음.  끝.\n"
            
        except Exception as e:
            return jsonify({'error': f"ODT 파싱 오류: {str(e)}"})
    else:
        # 파일 없음 - S2B 물품만 있는 경우
        if not item_list:
            return jsonify({'error': '공문 파일(ODT)을 지정하거나, S2B 물품 목록을 불러와주세요.'})
            
        prompt += "아래 학교장터(S2B) 물품 구매를 위한 에듀파인 기안문의 '제목'과 '본문'을 작성해주세요.\n\n"
        prompt += f"[물품 목록]\n{item_list}\n\n"
        prompt += "[작성 규칙]\n"
        prompt += "1. 제목: 간결하고 명확하게 작성 (예: 2026학년도 체육수업 교구 구입 품의)\n"
        prompt += "2. 본문 구성: 아래 품의명세서 양식을 엄격하게 따를 것\n"
        prompt += "3. 격식체(합쇼체) 사용\n"
        prompt += "4. 항목 번호는 1. 2. 3. 형식, 세부항목은 가. 나. 형식\n\n"
        prompt += "[출력 형식]\n"
        prompt += "제목: (기안문 제목)\n\n"
        prompt += "본문:\n"
        prompt += "1. 관련: (관련 근거, 없을시 생략가능)\n"
        prompt += "2. (해당사업명) 관련 물품을 아래와 같이 구입하고자 합니다.\n"
        prompt += "  가. 내역: (대표물품명) 외 O건\n"
        prompt += "  나. 용도: (물품 구매 용도)\n"
        prompt += "  다. 소요예산: 금O,OOO원\n"
        prompt += "  라. 산출내역: 품목을 바탕으로 계산식 작성 (품의명세서 참조)\n"
        prompt += "붙임  지출(지급)품의서 1부.  끝.\n"

    return jsonify({'prompt': prompt})

@app.route('/api/start', methods=['POST'])
def start_automation():
    try:
        if _state['running']:
            if _session['thread'] and not _session['thread'].is_alive():
                _state['running'] = False
            else:
                # 이전 작업을 강제 종료 시도
                import playwright_edufine
                import importlib
                importlib.reload(playwright_edufine)
                playwright_edufine.stop_requested = True
                
                evt = getattr(playwright_edufine, 'next_event', None)
                if evt:
                    if _session.get('loop'):
                        _session['loop'].call_soon_threadsafe(evt.set)
                    else:
                        evt.set()
                    
                import time
                time.sleep(0.5) # 스레드 종료 대기
                
                if _session['thread'] and _session['thread'].is_alive():
                    return jsonify({'error': '이전 봇 작업이 종료되는 중입니다. 1~2초 후 다시 눌러주세요.'}), 409
                else:
                    _state['running'] = False
        
        data = request.get_json() or {}
        target_path = data.get('path', '')
        if target_path:
            target_path = target_path.strip()
        else:
            target_path = "NO_FILE"
            
        dry_run = data.get('dry_run', False)
        
        draft_title = data.get('title', '')
        if draft_title:
            draft_title = draft_title.strip()
            
        draft_summary = data.get('summary', '')
        if draft_summary:
            draft_summary = draft_summary.strip()
            
        while not _q.empty():
            try: _q.get_nowait()
            except queue.Empty: break

        _state['running'] = True
        import playwright_edufine
        playwright_edufine.stop_requested = False
        
        _run_in_bg(run_automation, target_path, dry_run, draft_title, draft_summary)
        return jsonify({'status': 'started'})
    except Exception as e:
        import traceback
        trace = traceback.format_exc()
        return jsonify({'error': f"서버 내부 오류: {str(e)}\n{trace}"}), 500

@app.route('/api/browse-file', methods=['GET'])
def browse_file():
    import tkinter as tk
    from tkinter import filedialog
    try:
        root = tk.Tk()
        root.withdraw()
        root.attributes('-topmost', True)
        file_path = filedialog.askopenfilename(
            parent=root, 
            title="기안할 공문(ODT) 파일을 선택하세요",
            filetypes=[("ODT 파일", "*.odt"), ("모든 파일", "*.*")]
        )
        root.destroy()
        return jsonify({'path': file_path or ''})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/trigger-event', methods=['POST'])
def trigger_event():
    data = request.get_json() or {}
    event_type = data.get('event')
    items_text = data.get('items', '')
    
    if event_type == 'stop':
        playwright_edufine.stop_requested = True
    else:
        playwright_edufine.current_event_type = event_type
        playwright_edufine.current_items_text = items_text
        
    if _session.get('loop'):
        _session['loop'].call_soon_threadsafe(playwright_edufine.next_event.set)
    else:
        playwright_edufine.next_event.set()
        
    # 로그 출력
    if event_type == 'add_row':
        _q.put(('log', "[시스템] '행추가' 신호를 봇에게 전송했습니다..."))
    elif event_type == 'fetch_s2b_cart':
        _q.put(('log', "[시스템] 'S2B 장바구니 불러오기' 신호를 봇에게 전송했습니다..."))
    elif event_type == 'next':
        _q.put(('log', "[시스템] '기안 완료' 신호를 봇에게 전송했습니다..."))
    elif event_type == 'stop':
        _q.put(('log', "[시스템] 중단 요청을 처리 중입니다..."))
        
    return jsonify({'status': 'ok'})

@app.route('/api/stream')
def stream():
    def generate():
        while True:
            try:
                typ, payload = _q.get(timeout=25)
            except queue.Empty:
                yield "data: ping\n\n"
                continue

            if typ == 'log':
                yield f"data: {json.dumps({'type': 'log', 'text': payload}, ensure_ascii=False)}\n\n"
            elif typ == 'done':
                yield f"data: {json.dumps({'type': 'done'})}\n\n"
                break
    return Response(generate(), mimetype='text/event-stream', headers={'Cache-Control': 'no-cache'})

if __name__ == '__main__':
    from dotenv import load_dotenv
    load_dotenv()
    
    print("=" * 50)
    print("[안내] 에듀파인 다중 기안 자동화 웹 서버 시작 (V4 하이브리드)")
    print("   접속 주소: http://localhost:5030")
    print("=" * 50)
    app.run(host='0.0.0.0', port=5030, threaded=True)
