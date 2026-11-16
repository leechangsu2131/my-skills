#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
s2b_poomui_runner.py
S2B(학교장터) 물품 정보 기반 K-에듀파인 학교회계 품의서 자동 생성 및 화면 직결 연동기
"""

import sys
import os
import json
import asyncio
import urllib.request
import subprocess
from datetime import datetime

CDP_HTTP = "http://127.0.0.1:9222"

def copy_to_clipboard(text):
    """PowerShell을 이용한 클립보드 복사 (인코딩 안전망)"""
    try:
        # PowerShell Set-Clipboard 사용
        cmd = ["powershell", "-NoProfile", "-Command", "$input | Set-Clipboard"]
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, text=True, encoding="utf-8")
        proc.communicate(input=text)
        return True
    except Exception as e:
        print(f"[경고] 클립보드 복사 실패: {e}")
        return False

def generate_poomui_data(item_info):
    """K-에듀파인 학교회계 표준 품의 데이터 생성"""
    year = datetime.now().year
    name = item_info.get("name", "스타 넷볼 스포츠 골대 농구링 높이 조절형")
    spec = item_info.get("spec", "NBM100 / 2개 1조 / 높이 175~305cm 조절형 / 스틸 외")
    qty = item_info.get("qty", 1)
    unit = item_info.get("unit", "조")
    price = item_info.get("price", 650000)
    total_amount = qty * price
    s2b_no = item_info.get("s2b_no", "202606028605894")
    vendor = item_info.get("vendor", "허니스쿨")
    vendor_tel = item_info.get("vendor_tel", "070-7775-3541")
    vendor_addr = item_info.get("vendor_addr", "경북 김천시 혁신로185 2층 231-4호")
    manufacturer = item_info.get("manufacturer", "(주)신신상사 / 중국")
    budget_category = item_info.get("budget_category", "학교회계 > 교수학습활동지원 > 교육과정운영 > 교구및기자재구입비")

    # 비품/소모품 판정: 단가 50만원 이상 & 내용연수 1년 이상
    is_asset = price >= 500000
    item_type = "비품 (정수/교구대장 등재 대상)" if is_asset else "소모품"

    title = f"{year}학년도 체육과 교수학습교구(넷볼 골대) 구입 품의"

    summary = f"""1. 관련
  가. {year}학년도 학교 교육과정 운영 계획
  나. 체육과 교수·학습활동 및 학생 체육활동 활성화 지원 계획

2. 목적 및 필요성
  체육 수업(구기활동 및 넷볼/농구형 게임)과 학생들의 기초 체력 향상을 위하여 높이 조절이 가능한 맞춤형 체육교구({name})를 구매하여 안전하고 효과적인 교수학습활동을 운영하고자 합니다.

3. 구매 개요
  가. 품명: {name}
  나. 구매방법: S2B(학교장터) 1인 수의계약 / 물품구매
  다. 소요예산: 금{total_amount:,}원 (부가세 및 배송료 포함)
  라. 예산과목: {budget_category}
  마. 물품구분: {item_type}

4. 산출 내역
  - {name} [{spec}]
    : {price:,}원 × {qty}{unit} = 금{total_amount:,}원

5. 공급업체 및 물품 정보
  가. S2B 물품번호: {s2b_no}
  나. 공급업체명: {vendor} (연락처: {vendor_tel})
  다. 공급업체 주소: {vendor_addr}
  라. 제조사/원산지: {manufacturer}
  마. 납품기한: 계약상대자 결정일로부터 7영업일 이내 (무료배송)

붙임  S2B 물품상세 및 견적서 1부.  끝."""

    grid_item = {
        "itemNm": name,
        "spec": spec,
        "qty": qty,
        "unit": unit,
        "price": price,
        "amount": total_amount,
        "s2bNo": s2b_no
    }

    return {
        "title": title,
        "summary": summary,
        "total_amount": total_amount,
        "item_type": item_type,
        "grid_item": grid_item
    }

async def open_poomui_in_edufine(title, summary):
    """Chrome 9222 포트를 통해 K-에듀파인에 학교회계 품의등록 화면 호출 시도"""
    import websockets
    try:
        # 브라우저 WS 버전 확인
        with urllib.request.urlopen(f"{CDP_HTTP}/json/version", timeout=3) as r:
            ver = json.loads(r.read())
        browser_ws = ver.get("webSocketDebuggerUrl", "")
        if not browser_ws:
            print("[안내] 브라우저 디버거 WebSocket을 찾지 못했습니다.")
            return False

        with urllib.request.urlopen(f"{CDP_HTTP}/json", timeout=3) as r:
            tabs = json.loads(r.read())

        target_id = None
        for t in tabs:
            url = t.get("url", "").lower()
            if t.get("type") == "page" and "klef.gbe.kr" in url:
                target_id = t.get("id")
                break

        if not target_id:
            print("[안내] K-에듀파인 탭이 열려있지 않습니다.")
            return False

        async with websockets.connect(browser_ws, max_size=10*1024*1024, open_timeout=5) as ws:
            # 타겟 활성화
            await ws.send(json.dumps({
                "id": 1,
                "method": "Target.activateTarget",
                "params": {"targetId": target_id}
            }))
            await ws.recv()

            # attach
            await ws.send(json.dumps({
                "id": 2,
                "method": "Target.attachToTarget",
                "params": {"targetId": target_id, "flatten": True}
            }))
            
            session_id = None
            for _ in range(5):
                raw = await ws.recv()
                msg = json.loads(raw)
                if msg.get("id") == 2:
                    session_id = msg.get("result", {}).get("sessionId")
                    break

            if not session_id:
                return False

            # JS 실행으로 학교회계 품의등록 메뉴 호출 및 팝업 정리
            js_script = """
            (function() {
                try {
                    var app = window._pApplication || window._application || (typeof nexacro !== 'undefined' ? nexacro.getApplication() : null);
                    if (!app) return "NO_APP";

                    // 1. 공지사항 팝업 제거
                    try {
                        var main = app.mainframe.MainVFrameSet.SubHFrameSet.MainFrame;
                        if (main && main.noticePopup0) main.noticePopup0.destroy();
                    } catch(e) {}

                    // 2. 학교회계(A00FA) 시스템 전환
                    try {
                        var top = app.mainframe.MainVFrameSet.TopFrame;
                        var cbo = top.form.cboJobList;
                        if (cbo && cbo.value != 'A00FA') {
                            cbo.set_value('A00FA');
                            var ei = new nexacro.ItemChangeEventInfo(cbo, 'onitemchanged', 0, 0, 0, 'A00FA');
                            top.form.cboJobList_onitemchanged(cbo, ei);
                        }
                    } catch(e) {}

                    // 3. 품의등록 메뉴(A00FAA0104001001) 오픈
                    try {
                        var lf = app.mainframe.MainVFrameSet.SubHFrameSet.LeftFrame;
                        if (lf && lf.form && lf.form.gfnOpenMenu) {
                            lf.form.gfnOpenMenu('A00FAA0104001001');
                            return "MENU_CALLED_SUCCESS";
                        }
                    } catch(e) {
                        return "LEFTFRAME_ERROR: " + e.message;
                    }
                    return "READY";
                } catch(err) {
                    return "ERROR: " + err.message;
                }
            })();
            """

            payload = {
                "id": 10,
                "sessionId": session_id,
                "method": "Runtime.evaluate",
                "params": {
                    "expression": js_script,
                    "returnByValue": True
                }
            }
            await ws.send(json.dumps(payload))
            res = json.loads(await ws.recv())
            val = res.get("result", {}).get("result", {}).get("value", "")
            print(f"[K-EduFine Direct Call] 메뉴 오픈 시도 결과: {val}")
            return True
    except Exception as e:
        print(f"[안내] 에듀파인 브라우저 직접 호출 생략 ({e})")
        return False

def main():
    # 사용자가 업로드한 S2B 장바구니 이미지 정보
    target_item = {
        "name": "스타 넷볼 스포츠 골대 농구링 높이 조절형",
        "spec": "NBM100 / 2개 1조 / 실버 / 높이 175~305cm 조절 / 넷볼링 38cm / 약 50kg / 스틸 외",
        "qty": 1,
        "unit": "조",
        "price": 650000,
        "s2b_no": "202606028605894",
        "vendor": "허니스쿨",
        "vendor_tel": "070-7775-3541",
        "vendor_addr": "경북 김천시 혁신로185 2층 231-4호",
        "manufacturer": "(주)신신상사 / 중국",
        "purpose": "체육 수업(구기활동 및 넷볼/농구 종목)과 학생 신체활동 증진을 위한 체육교구 구비",
        "budget_category": "학교회계 > 교수학습활동지원 > 교육과정운영 > 교구및기자재구입비",
    }

    poomui = generate_poomui_data(target_item)

    print("=" * 70)
    print("🏫 K-에듀파인 학교회계 물품구매 품의서 생성 결과")
    print("=" * 70)
    print(f"📌 [품의 제목] : {poomui['title']}")
    print("-" * 70)
    print("📄 [품의 개요 및 본문] :")
    print(poomui["summary"])
    print("-" * 70)
    print(f"💰 [산출 내역] : {poomui['grid_item']['itemNm']} | {poomui['grid_item']['spec']}")
    print(f"                수량: {poomui['grid_item']['qty']}{poomui['grid_item']['unit']} | 단가: {poomui['grid_item']['price']:,}원 | 합계: {poomui['total_amount']:,}원")
    print(f"📦 [물품 구분] : {poomui['item_type']}")
    print("=" * 70)

    # 클립보드에 품의 전체 내용 복사
    clipboard_content = f"[품의 제목]\n{poomui['title']}\n\n[품의 개요]\n{poomui['summary']}"
    if copy_to_clipboard(clipboard_content):
        print("✅ [성공] 품의 제목 및 개요 본문이 Windows 클립보드에 복사되었습니다! (Ctrl+V로 붙여넣기 가능)")

    # 에듀파인 브라우저 메뉴 직결 호출 시도
    print("\n🌐 K-에듀파인 화면 연동 시도 중...")
    try:
        asyncio.run(open_poomui_in_edufine(poomui['title'], poomui['summary']))
    except Exception as e:
        print(f"브라우저 직결 호출 패스: {e}")

if __name__ == "__main__":
    main()
