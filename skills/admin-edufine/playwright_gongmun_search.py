#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
playwright_gongmun_search.py
======================================================
[트랙 3] K-에듀파인 관련 공문 검색 및 열람 자동화 봇
경로: [업무포털 / K-에듀파인] -> [문서관리] -> [문서함] -> [문서등록대장]
특징:
  - 브라우저 타겟 락을 우회하는 탭 직접 웹소켓(CDP JSON-RPC) 고속 통신 지원
  - 검색 시작일자 자동 확장 (2학기/연초 등)
  - WXSClient(네이티브 공문 뷰어 새창) 즉시 호출
======================================================
"""

import asyncio
import time
import sys
import os
import json
import urllib.request
import websockets

if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

CDP_HTTP = "http://127.0.0.1:9222"

def get_edufine_ws_url():
    """Chrome HTTP API에서 K-에듀파인 탭의 전용 WebSocket URL 가져오기"""
    try:
        req = urllib.request.urlopen(f"{CDP_HTTP}/json", timeout=3)
        tabs = json.loads(req.read().decode('utf-8'))
        # 1. type이 'page'인 K-에듀파인 메인 탭 우선 탐색
        for t in tabs:
            if t.get('type') == 'page':
                url = t.get('url', '')
                if 'klef' in url and 'keris_ui' in url:
                    return t.get('webSocketDebuggerUrl')
        # 2. 기타 page 타입 klef 탭
        for t in tabs:
            if t.get('type') == 'page' and 'klef' in t.get('url', ''):
                return t.get('webSocketDebuggerUrl')
        # 3. 포털 메인 page 탭
        for t in tabs:
            if t.get('type') == 'page' and 'eduptl' in t.get('url', ''):
                return t.get('webSocketDebuggerUrl')
    except Exception as e:
        print(f"[CDP 연결 확인 실패] {e}")
    return None


async def execute_gongmun_search(keyword: str, open_first: bool = True, start_date: str = "2026-08-01"):
    """
    [트랙 3 메인 엔트리포인트]
    키워드로 관련 공문 검색 후 결과 목록 반환 및 첫 번째 공문 열람
    """
    print("=" * 65)
    print(f">> [트랙 3] K-에듀파인 관련 공문 검색 & 열람 가동")
    print(f"   검색 키워드: '{keyword}' (검색 시작일: {start_date})")
    print("=" * 65)

    ws_url = get_edufine_ws_url()
    if not ws_url:
        print("[오류] Chrome 9222 포트에서 K-에듀파인/포털 탭을 찾을 수 없습니다.")
        print("  -> launch_chrome.bat 으로 크롬이 실행되어 있는지 확인해 주세요.")
        return []

    try:
        async with websockets.connect(ws_url) as ws:
            msg_id = 1
            
            async def call_eval(expr):
                nonlocal msg_id
                cmd = {
                    "id": msg_id,
                    "method": "Runtime.evaluate",
                    "params": {
                        "expression": expr,
                        "returnByValue": True,
                        "awaitPromise": True
                    }
                }
                msg_id += 1
                await ws.send(json.dumps(cmd))
                raw = await asyncio.wait_for(ws.recv(), timeout=12)
                data = json.loads(raw)
                return data.get('result', {}).get('result', {}).get('value')

            # 1. 문서등록대장 화면 탐색 및 검색 실행
            js_search = f"""(() => {{
                // 1. 공지사항 팝업 닫기 시도
                try {{
                    let closeBtn = document.querySelector('[id*="noticePopup"][id*="btnClose"]');
                    if (closeBtn) closeBtn.click();
                }} catch(e) {{}}

                // 2. 문서등록대장 iframe 탐색
                let targetWin = null;
                let iframes = document.querySelectorAll('iframe');
                for (let f of iframes) {{
                    try {{
                        let url = f.contentWindow.location.href || '';
                        if (url.includes('DocRegistRegstrList') || url.includes('retrieveDocRegistRegstrList')) {{
                            targetWin = f.contentWindow;
                            break;
                        }}
                    }} catch(e) {{}}
                }}

                if (!targetWin) {{
                    return {{status: 'need_nav', message: '문서등록대장 화면을 열어야 합니다.'}};
                }}

                let doc = targetWin.document;

                // 3. 검색 시작일자 조정
                let startDate = doc.getElementById('basicReportDe');
                if (startDate && '{start_date}') {{
                    startDate.value = '{start_date}';
                    startDate.dispatchEvent(new Event('input', {{bubbles: true}}));
                    startDate.dispatchEvent(new Event('change', {{bubbles: true}}));
                }}

                // 4. 제목 검색창에 키워드 주입
                let inputSj = doc.getElementById('basicSj');
                if (inputSj) {{
                    inputSj.value = '{keyword}';
                    inputSj.dispatchEvent(new Event('input', {{bubbles: true}}));
                    inputSj.dispatchEvent(new Event('change', {{bubbles: true}}));
                }}

                // 5. 조회 버튼 클릭
                let btn = doc.getElementById('searchDocBtn');
                if (btn) {{
                    btn.click();
                }}

                return {{status: 'ok', message: '조회 요청 완료'}};
            }})()"""

            search_res = await call_eval(js_search)
            
            # 문서등록대장이 아직 안 열려 있는 경우 메뉴 클릭 유도
            if search_res and search_res.get('status') == 'need_nav':
                print("   [안내] 문서등록대장 화면이 열려있지 않아 좌측 메뉴를 호출합니다...")
                js_nav = """(() => {
                    // 좌측 메뉴에서 문서함 -> 문서등록대장 클릭
                    let rows = document.querySelectorAll('[id*="gridMenu.body.gridrow_"]');
                    for (let r of rows) {
                        if (r.innerText.includes('문서함') && !r.innerText.includes('내문서함')) {
                            r.click();
                            break;
                        }
                    }
                    setTimeout(() => {
                        let subRows = document.querySelectorAll('[id*="gridMenu.body.gridrow_"]');
                        for (let sr of subRows) {
                            if (sr.innerText.includes('문서등록대장')) {
                                sr.click();
                                break;
                            }
                        }
                    }, 500);
                })()"""
                await call_eval(js_nav)
                await asyncio.sleep(3)
                # 재시도
                search_res = await call_eval(js_search)

            print("   -> 검색 조회 진행 중...")
            await asyncio.sleep(2.5)

            # 2. 결과 테이블 파싱
            js_parse_results = """(() => {
                let targetWin = null;
                let iframes = document.querySelectorAll('iframe');
                for (let f of iframes) {
                    try {
                        let url = f.contentWindow.location.href || '';
                        if (url.includes('DocRegistRegstrList') || url.includes('retrieveDocRegistRegstrList')) {
                            targetWin = f.contentWindow;
                            break;
                        }
                    } catch(e) {}
                }
                if (!targetWin) return [];

                let doc = targetWin.document;
                let rows = [];
                let trs = doc.querySelectorAll('#tbList tbody tr');
                trs.forEach((tr, idx) => {
                    let tds = tr.querySelectorAll('td');
                    if (tds.length >= 7) {
                        let titleLink = tr.querySelector('a.ellipsisTitle');
                        let title = titleLink ? titleLink.innerText.trim() : (tds[3] ? tds[3].innerText.trim() : '');
                        let docNo = tds[2] ? tds[2].innerText.trim() : '';
                        let regDate = tds[6] ? tds[6].innerText.trim() : '';
                        let sender = tds[4] ? tds[4].innerText.trim() : '';
                        let status = tds[1] ? tds[1].innerText.trim() : '';
                        if (title && !title.includes('조회된 데이터가 없습니다')) {
                            rows.push({
                                idx: idx,
                                title: title,
                                docNo: docNo,
                                regDate: regDate,
                                sender: sender,
                                status: status
                            });
                        }
                    }
                });
                return rows;
            })()"""

            results = await call_eval(js_parse_results) or []
            print(f"   [완료] 총 {len(results)}건의 공문이 검색되었습니다.")

            print("\n" + "-" * 65)
            print(f"[검색 결과 목록] (총 {len(results)}건):")
            for i, r in enumerate(results[:15]):
                print(f" [{i+1}] [{r['regDate']}] [{r['sender']}] {r['title']} ({r['docNo']})")
            print("-" * 65)

            # 3. 첫 번째(또는 요청된) 공문 열기
            if open_first and results:
                target_idx = results[0]['idx']
                print(f"\n[공문 열기] 1번째 공문 열람 호출: '{results[0]['title']}'")
                js_open = f"""(() => {{
                    let targetWin = null;
                    let iframes = document.querySelectorAll('iframe');
                    for (let f of iframes) {{
                        try {{
                            let url = f.contentWindow.location.href || '';
                            if (url.includes('DocRegistRegstrList') || url.includes('retrieveDocRegistRegstrList')) {{
                                targetWin = f.contentWindow;
                                break;
                            }}
                        }} catch(e) {{}}
                    }}
                    if (!targetWin) return false;

                    let doc = targetWin.document;
                    let trs = doc.querySelectorAll('#tbList tbody tr');
                    if (trs[{target_idx}]) {{
                        let a = trs[{target_idx}].querySelector('a.ellipsisTitle') || trs[{target_idx}].querySelector('a');
                        if (a) {{
                            a.click();
                            return true;
                        }}
                    }}
                    return false;
                }})()"""
                opened = await call_eval(js_open)
                if opened:
                    print("   [성공] 공문 열람 신호 전송 완료! WXSClient 뷰어가 열립니다.")

            return results
    except Exception as e:
        print(f"[오류 발생] {e}")
        return []


async def open_specific_gongmun(row_index: int):
    """특정 순번의 공문 열람 (프레임 컨텍스트 직접 실행)"""
    ws_url = get_edufine_ws_url()
    if not ws_url:
        return False
    async with websockets.connect(ws_url) as ws:
        cmd = {
            "id": 1,
            "method": "Runtime.evaluate",
            "params": {
                "expression": f"""(() => {{
                    let targetWin = null;
                    let iframes = document.querySelectorAll('iframe');
                    for (let f of iframes) {{
                        try {{
                            let url = f.contentWindow.location.href || '';
                            if (url.includes('DocRegistRegstrList') || url.includes('retrieveDocRegistRegstrList')) {{
                                targetWin = f.contentWindow;
                                break;
                            }}
                        }} catch(e) {{}}
                    }}
                    if (!targetWin) return false;
                    let doc = targetWin.document;
                    let tr = doc.querySelectorAll('#tbList tbody tr')[{row_index}];
                    let a = tr ? (tr.querySelector('a.ellipsisTitle') || tr.querySelector('a')) : null;
                    if (a) {{
                        let code = a.getAttribute('onclick');
                        if (code) {{
                            targetWin.eval(code);
                            return true;
                        }}
                        a.click();
                        return true;
                    }}
                    return false;
                }})()""",
                "returnByValue": True
            }
        }
        await ws.send(json.dumps(cmd))
        raw = await ws.recv()
        data = json.loads(raw)
        return data.get('result', {}).get('result', {}).get('value', False)


if __name__ == '__main__':
    kw = sys.argv[1] if len(sys.argv) > 1 else "진학지원금"
    asyncio.run(execute_gongmun_search(kw, open_first=True))
