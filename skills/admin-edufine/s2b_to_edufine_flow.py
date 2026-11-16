#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
s2b_to_edufine_flow.py
================================================================================
S2B 학교장터 장바구니 -> K-에듀파인 학교회계 품의등록 원스톱 자동화 스킬
================================================================================
1단계: S2B 장바구니 물품 분석 및 에듀파인 전용 엑셀(S2B_에듀파인연계_양식1.xls) 자동 다운로드
2단계: K-에듀파인 학교회계 품의등록(A00FAA0104001001) 탭 직결 호출
3단계: 에듀파인 품의 제목(edtCnsulSj) 및 개요 본문(txtareaCnsulSumrCn) 자동 주입
4단계: 품목 엑셀 업로드(파일 ⇧) 준비 및 클립보드 안전망 제공
"""

import os
import sys
import json
import asyncio
import urllib.request
import websockets
import base64
from datetime import datetime

CDP_HTTP = "http://127.0.0.1:9222"
DOWNLOAD_DIR = os.path.expanduser("~/Downloads")

def get_edufine_summary(item):
    """표준 품의서 제목 및 개요 생성"""
    year = datetime.now().year
    name = item.get("goods_name", "스타 넷볼 스포츠 골대 농구링 높이 조절형")
    spec = item.get("size", "2개1조/실버/약 50㎏/(L)120X(W)70X(H)175~305㎝/넷볼링38㎝")
    qty = item.get("estimate_quantity", "1")
    unit = item.get("credit_str", "조")
    price = int(item.get("estimate_amt", 650000))
    total = int(item.get("estimate_price", 650000))
    s2b_no = item.get("re_estimate_code", "202606028605894")
    vendor = item.get("company_name_b", "허니스쿨")

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
  다. 소요예산: 금{total:,}원 (부가세 및 배송료 포함)
  라. 예산과목: 학교회계 > 교수학습활동지원 > 교육과정운영 > 교구및기자재구입비
  마. 물품구분: {item_type}

4. 산출 내역
  - {name} [{spec}]
    : {price:,}원 × {qty}{unit} = 금{total:,}원

5. 공급업체 및 물품 정보
  가. S2B 물품번호: {s2b_no}
  나. 공급업체명: {vendor}
  다. 납품조건: 계약체결 후 7영업일 이내 (무료배송)

붙임  S2B 물품상세 및 견적서 1부.  끝."""

    return title, summary

async def run_flow():
    print("=" * 70)
    print("🚀 [edufine 스킬] S2B 장바구니 -> 에듀파인 품의등록 자동화 시작")
    print("=" * 70)

    # 1. 크롬 CDP 탭 목록 확인
    with urllib.request.urlopen(f"{CDP_HTTP}/json") as r:
        tabs = json.loads(r.read())

    s2b_tab = next((t for t in tabs if "s2b.kr" in t.get("url", "").lower()), None)
    klef_tab = next((t for t in tabs if "klef.gbe.kr" in t.get("url", "").lower()), None)

    if not s2b_tab:
        print("❌ S2B 탭을 찾을 수 없습니다. (s2b.kr 로그인 필요)")
        return
    if not klef_tab:
        print("❌ K-에듀파인 탭을 찾을 수 없습니다. (klef.gbe.kr 로그인 필요)")
        return

    # [1단계] S2B에서 에듀파인 연계 엑셀 다운로드
    print("\n[1단계] S2B 장바구니 품목 추출 및 에듀파인 전용 엑셀 다운로드 중...")
    target_item = None
    excel_path = None

    async with websockets.connect(s2b_tab["webSocketDebuggerUrl"]) as ws:
        js_get_item = """
        (function() {
            var cbs = document.querySelectorAll('input.input_check');
            for (var i = 0; i < cbs.length; i++) {
                try {
                    var val = JSON.parse(cbs[i].value);
                    if (val.goods_name && val.goods_name.includes('넷볼')) {
                        return val;
                    }
                } catch(e) {}
            }
            return null;
        })()
        """
        await ws.send(json.dumps({"id": 1, "method": "Runtime.evaluate", "params": {"expression": js_get_item, "returnByValue": True}}))
        res = json.loads(await ws.recv())
        target_item = res.get("result", {}).get("result", {}).get("value")

        if not target_item:
            print("   -> 넷볼 품목 기본값 적용")
            target_item = {
                "goods_name": "스타 넷볼 스포츠 골대 농구링 높이 조절형",
                "size": "2개1조/실버/약 50㎏/(L)120X(W)70X(H)175~305㎝/넷볼링38㎝",
                "estimate_quantity": "1",
                "credit_str": "조",
                "estimate_amt": "650000",
                "estimate_price": "650000",
                "re_estimate_code": "202606028605894",
                "company_name_b": "허니스쿨",
                "rc_estimate_code": "2026111600448"
            }
        else:
            print(f"   -> S2B 장바구니 감지: {target_item['goods_name']} (단가: {int(target_item['estimate_amt']):,}원)")

        # 에듀파인 엑셀 파일 다운로드 (f_sep=1)
        js_download = f"""
        (async function() {{
            var resp = await fetch('https://www.s2b.kr/S2BNCustomer/remc100.do', {{
                method: 'POST',
                headers: {{'Content-Type': 'application/x-www-form-urlencoded'}},
                body: new URLSearchParams({{
                    'f_rc_estimate_code': '{target_item.get("rc_estimate_code", "2026111600448")}',
                    'f_sep': '1',
                    'forwardName': 'estimateEdufine'
                }})
            }});
            var blob = await resp.blob();
            var reader = new FileReader();
            return new Promise((resolve) => {{
                reader.onloadend = () => resolve(reader.result.split(',')[1]);
                reader.readAsDataURL(blob);
            }});
        }})()
        """
        await ws.send(json.dumps({"id": 2, "method": "Runtime.evaluate", "params": {"expression": js_download, "awaitPromise": True, "returnByValue": True}}))
        res_dl = json.loads(await ws.recv())
        b64 = res_dl.get("result", {}).get("result", {}).get("value")
        if b64:
            excel_path = os.path.join(DOWNLOAD_DIR, "S2B_에듀파인연계_양식1.xls")
            with open(excel_path, "wb") as f:
                f.write(base64.b64decode(b64))
            print(f"   ✅ 에듀파인 전용 엑셀 다운로드 완료: {excel_path}")

    # [2단계] K-에듀파인 품의등록 화면 열기 및 제목/개요 주입
    title, summary = get_edufine_summary(target_item)
    print("\n[2단계] K-에듀파인 품의등록 탭 호출 및 데이터 주입 중...")

    async with websockets.connect(klef_tab["webSocketDebuggerUrl"]) as ws:
        # 학교회계 전환 및 품의등록(A00FAA0104001001) 오픈
        js_open_and_fill = f"""
        (function() {{
            var app = window._pApplication || window._application || nexacro.getApplication();
            if (!app) return "NO_APP";

            // 1. 공지사항 팝업 제거
            try {{
                var main = app.mainframe.MainVFrameSet.SubHFrameSet.MainFrame;
                if (main && main.noticePopup0) main.noticePopup0.destroy();
            }} catch(e) {{}}

            // 2. 학교회계 전환
            try {{
                var top = app.mainframe.MainVFrameSet.TopFrame;
                var cbo = top.form.cboJobList;
                if (cbo && cbo.value != 'A00FA') {{
                    cbo.set_value('A00FA');
                    var ei = new nexacro.ItemChangeEventInfo(cbo, 'onitemchanged', 0, 0, 0, 'A00FA');
                    top.form.cboJobList_onitemchanged(cbo, ei);
                }}
            }} catch(e) {{}}

            // 3. 품의등록 탭 열기
            try {{
                var lf = app.mainframe.MainVFrameSet.SubHFrameSet.LeftFrame;
                if (lf && lf.form && lf.form.gfnOpenMenu) {{
                    lf.form.gfnOpenMenu('A00FAA0104001001');
                }}
            }} catch(e) {{}}

            // 4. 품의등록 창이 있으면 제목/개요 주입
            var win = app.mainframe.MainVFrameSet.SubHFrameSet.WorkVFrameSet.WorkFrame.winId_A00FAA0104001001_411;
            if (win && win.form && win.form.divWork) {{
                var divMain = win.form.divWork.form.divMain.form;
                var edtTitle = divMain.edtCnsulSj;
                var txtSumr = divMain.txtareaCnsulSumrCn;

                if (edtTitle) {{
                    edtTitle.set_value({json.dumps(title)});
                    if (edtTitle._apply_client_value) edtTitle._apply_client_value();
                }}
                if (txtSumr) {{
                    txtSumr.set_value({json.dumps(summary)});
                    if (txtSumr._apply_client_value) txtSumr._apply_client_value();
                }}
                return "INJECTED_SUCCESS";
            }}
            return "MENU_OPENED_WAITING_LOAD";
        }})()
        """
        await ws.send(json.dumps({"id": 10, "method": "Runtime.evaluate", "params": {"expression": js_open_and_fill, "returnByValue": True}}))
        res_fill = json.loads(await ws.recv())
        val_fill = res_fill.get("result", {}).get("result", {}).get("value")
        print(f"   ✅ 에듀파인 주입 상태: {val_fill}")

    # [3단계] 클립보드 안전망 복사
    try:
        import subprocess
        cmd = ["powershell", "-NoProfile", "-Command", "$input | Set-Clipboard"]
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, text=True, encoding="utf-8")
        proc.communicate(input=f"[품의제목]\n{title}\n\n[품의개요]\n{summary}")
        print("   ✅ 품의 본문이 Windows 클립보드에 복사되었습니다. (Ctrl+V 상시 가능)")
    except Exception as e:
        print(f"   (클립보드 복사 건너뜀: {e})")

    print("\n" + "=" * 70)
    print("🎉 [정비 완료] K-에듀파인 화면에 품의 작성이 준비되었습니다!")
    print("=" * 70)
    print("1. 에듀파인 화면에서 [예산선택] 버튼을 눌러 본교 체육 관련 세부사업을 지정하세요.")
    print(f"2. 하단 품목내역의 [파일 ⇧] 버튼을 눌러 아래 엑셀 파일을 선택하면 품목이 자동 등록됩니다:")
    print(f"   📁 {excel_path}")
    print("3. 품목 등록 후 [저장] -> [결재요청]을 진행하시면 품의가 완료됩니다.")
    print("=" * 70)

if __name__ == "__main__":
    asyncio.run(run_flow())
