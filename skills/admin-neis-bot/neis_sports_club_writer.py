import asyncio
import io
import json
import os
import sys
import argparse
from playwright.async_api import async_playwright

# CP949 터미널 한글 깨짐 방지 및 EVPN 용 no_proxy 설정
os.environ["no_proxy"] = "localhost,127.0.0.1"

if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

txt_path = r"C:\Users\lee21\.gemini\antigravity\scratch\my-skills\skills\admin-neis-bot\data\스포츠클럽활동내용.txt"

def load_activities(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    contents = []
    # 홀수 라인은 차시 번호, 짝수 라인은 활동 내용
    for line in lines:
        line = line.strip()
        if not line:
            continue
        # 차시 숫자라인 건너뛰기
        if line.isdigit():
            continue
        contents.append(line)
        
    # 18차시용 마지막 내용 추가
    if len(contents) >= 17:
        contents.append(contents[16] + " 및 응용 연습")
    else:
        contents.append("줄넘기 마무리 응용 연습")
        
    return contents

# eXBuilder6 얼럿/컨펌창 승인 헬퍼 JS
JS_CLICK_DIALOG_OK = """
(function() {
    var clicked = false;
    var apps = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
    apps.forEach(function(ai) {
        if (ai && ai.app && (ai.app.id.indexOf("confirm") !== -1 || ai.app.id.indexOf("alert") !== -1 || ai.app.id.indexOf("cmn") !== -1)) {
            try {
                var container = ai.getContainer ? ai.getContainer() : null;
                if (container && container.getAllRecursiveChildren) {
                    container.getAllRecursiveChildren().forEach(function(c) {
                        if (c && c.type === "button") {
                            var val = c.value || c.text || "";
                            if (val === "예" || val === "확인" || val.indexOf("확인") !== -1 || val.indexOf("예") !== -1) {
                                try { c.click(); clicked = true; } catch(e) {}
                            }
                        }
                    });
                }
            } catch(err) {}
        }
    });
    return clicked;
})();
"""

# 1회 등록 트랜잭션 JS 로직
JS_SUBMIT_TRANSACTION = """
(function() {
    var popup1 = cpr.core.Platform.INSTANCE.getAllRunningAppInstances().find(function(ai) {
        return ai.app && ai.app.id === "edu/sa/phe/phe/sm/phe_phesm02_p01";
    });
    if (!popup1) return {error: "Popup1 app (phe_phesm02_p01) not found"};

    // 1. 값 주입
    var dtiCal = popup1.lookup("dtiCal");
    var ipbActMm = popup1.lookup("ipbActMm");
    var ipbCompeNm = popup1.lookup("ipbCompeNm");
    var txaAct = popup1.lookup("txaAct");

    if (dtiCal) dtiCal.value = "PARAM_YMD_HM";
    if (ipbActMm) ipbActMm.value = "20";
    if (ipbCompeNm) ipbCompeNm.value = "줄넘기";
    if (txaAct) txaAct.value = "PARAM_ACT_TEXT";

    // 2. 전체 체크박스 선택 (순번 왼쪽 전체 체크)
    var ds = popup1.lookup("dsPartiStdntList");
    var grd = popup1.lookup("grdActStdntList");
    var rowCount = 0;
    if (!ds || ds.getRowCount() === 0) {
        return {error: "참가자 목록이 아직 비어있습니다. 학생 추가가 정상 반영될 때까지 대기하세요."};
    }
    
    if (ds && grd) {
        rowCount = ds.getRowCount();
        for (var r=0; r<rowCount; r++) {
            grd.setCheckRowIndex(r, true);
        }
    }

    // 3. 내용 일괄적용 클릭
    var btnPheActCn = popup1.lookup("btnPheActCn");
    if (btnPheActCn) btnPheActCn.click();

    return {status: "in_progress", rowCount: rowCount};
})();


"""

JS_APPLY_TIME_AND_SAVE = """
(function() {
    var popup1 = cpr.core.Platform.INSTANCE.getAllRunningAppInstances().find(function(ai) {
        return ai.app && ai.app.id === "edu/sa/phe/phe/sm/phe_phesm02_p01";
    });
    if (!popup1) return {error: "Popup1 not found"};

    // 시간 일괄적용 클릭
    var btnActHr = popup1.lookup("btnActHr");
    if (btnActHr) btnActHr.click();

    // 저장 클릭 함수 등록
    window.__clickSaveSports = function() {
        var btnReg = popup1.lookup("btnReg");
        if (btnReg) {
            btnReg.click();
            return true;
        }
        return false;
    };

    return {status: "time_applied"};
})();
"""

JS_FILTER_ABSENT_STUDENTS = """
(function() {
    var popup2 = cpr.core.Platform.INSTANCE.getAllRunningAppInstances().find(function(ai) {
        return ai.app && ai.app.id === "edu/sa/phe/phe/sm/phe_phesm02_p02";
    });
    if (!popup2) return {error: "Student selection popup2 (phe_phesm02_p02) not found"};

    var ds = popup2.lookup("dsCompeList");
    var grd = popup2.lookup("grdCompeList");
    if (!ds || !grd) return {error: "Dataset or Grid not found in popup2"};

    var count = ds.getRowCount();
    var absent_students = [];
    var normal_count = 0;

    for (var r=0; r<count; r++) {
        var name = ds.getValue(r, "stuNm");
        var status = ds.getValue(r, "atteScNm") || "";
        
        // 결석, 지각, 조퇴 등이 적혀 있으면 추가 제외
        if (status.indexOf("결") !== -1 || status.indexOf("지") !== -1 || status.indexOf("조") !== -1 || status.indexOf("퇴") !== -1) {
            try { grd.setCheckRowIndex(r, false); } catch(e) {}
            absent_students.push(name + "(" + status + ")");
        } else {
            try { grd.setCheckRowIndex(r, true); } catch(e) {}
            normal_count++;
        }
    }
    
    grd.redraw();
    
    // 추가 버튼 클릭
    var btnAdd = popup2.lookup("btnAdd");
    if (btnAdd) {
        btnAdd.click();
    }

    return {status: "filtered", absent: absent_students, added: normal_count};
})();


"""

async def wait_dialog(page, ms=3000):
    start = Date.now() if 'Date' in globals() else 0
    # 백그라운드 얼럿/컨펌 자동 승인 루프
    for _ in range(int(ms/300)):
        closed = await page.evaluate(JS_CLICK_DIALOG_OK)
        if closed:
            await asyncio.sleep(0.3)
            return True
        await asyncio.sleep(0.3)
    return False

async def main():
    parser = argparse.ArgumentParser(description="스포츠클럽 누가기록 일괄등록 자동화")
    parser.add_argument("--apply", action="store_true", help="실제 저장 처리 여부")
    parser.add_argument("--limit", type=int, default=18, help="등록할 차시 제한 (기본 18)")
    args = parser.parse_args()

    activities = load_activities(txt_path)
    print(f"Loaded activities counts: {len(activities)}")

    # 9일의 수요일 스케줄 빌드
    dates = ["20260527", "20260603", "20260610", "20260617", "20260624", "20260701", "20260708", "20260715", "20260722"]
    schedule = []
    
    idx = 0
    for d in dates:
        # 아침 세션
        if idx < len(activities) and len(schedule) < args.limit:
            schedule.append({
                "ymd_hm": f"{d}0840",
                "text": activities[idx],
                "session": "아침"
            })
            idx += 1
        # 점심 세션
        if idx < len(activities) and len(schedule) < args.limit:
            schedule.append({
                "ymd_hm": f"{d}1240",
                "text": activities[idx],
                "session": "점심"
            })
            idx += 1

    print(f"Build entry schedules count: {len(schedule)}")
    
    async with async_playwright() as p:
        try:
            print("Connecting to Chrome over CDP on port 9222...")
            browser = await p.chromium.connect_over_cdp("http://127.0.0.1:9222")
            
            target_page = None
            for context in browser.contexts:
                for page in context.pages:
                    url = page.url.lower()
                    try:
                        has_cpr = await page.evaluate("typeof cpr !== 'undefined'")
                    except:
                        has_cpr = False
                    
                    if has_cpr and "vpn" not in url:
                        target_page = page
                        break
                if target_page:
                    break
            
            if not target_page:
                print("Error: Active NEIS page not found.")
                return
                
            print(f"Connected to page: {await target_page.title()}")

            for i, sch in enumerate(schedule):
                print(f"\n[차시 {i+1}/18] 등록 진행 중... 일시: {sch['ymd_hm']} ({sch['session']}) -> '{sch['text']}'")
                
                # 1. 메인 화면 [등록] 클릭
                print(" - Clicking '등록' button on Main screen...")
                main_click = await target_page.evaluate("""
                    (function() {
                        var main = cpr.core.Platform.INSTANCE.getAllRunningAppInstances().find(function(ai) {
                            return ai.app && ai.app.id === "edu/sa/phe/phe/sm/phe_phesm02_m00";
                        });
                        if (!main) return {error: "Main not found"};
                        
                        var grdClubList = main.lookup("grdClubList");
                        if (grdClubList) {
                            // 그리드 HTML DOM 셀 찾아서 물리 클릭 수행
                            var gridEl = document.getElementById("uuid-" + grdClubList.uuid);
                            if (gridEl) {
                                var cells = gridEl.querySelectorAll('.cl-grid-cell');
                                var clicked = false;
                                for (var c = 0; c < cells.length; c++) {
                                    if (cells[c].innerText && cells[c].innerText.indexOf("줄넘기(3-2)") !== -1) {
                                        cells[c].click();
                                        clicked = true;
                                        break;
                                    }
                                }
                                if (!clicked) return {error: "줄넘기(3-2) 셀을 찾았으나 클릭하지 못했습니다."};
                            } else {
                                return {error: "그리드 HTML 요소를 찾을 수 없습니다."};
                            }
                        } else {
                            return {error: "grdClubList를 찾을 수 없습니다."};
                        }
                        
                        var btnReg = main.lookup("btnReg");
                        if (btnReg) {
                            btnReg.click();
                            return {status: "success"};
                        }
                        return {error: "등록 버튼을 찾을 수 없습니다."};
                    })()
                """)

                if isinstance(main_click, dict) and "error" in main_click:
                    print("Error from Main Selection JS:", main_click["error"])
                    return
                if not main_click:
                    print("Error: 메인 화면의 등록 버튼을 클릭하지 못했습니다.")
                    return
                
                await asyncio.sleep(1.5) # 등록 팝업창 활성화 대기
 
                # 2. 등록 팝업창 활성화 대기 및 [참가자 추가] 클릭
                print(" - Waiting for Registration popup1 and opening Student popup2...")
                pop1_click = None
                for r_pop1 in range(4):
                    pop1_click = await target_page.evaluate("""
                        (function() {
                            var popup1 = cpr.core.Platform.INSTANCE.getAllRunningAppInstances().find(function(ai) {
                                return ai.app && ai.app.id === "edu/sa/phe/phe/sm/phe_phesm02_p01";
                            });
                            if (!popup1) return {status: "not_found"};
                            var btnStdntPop = popup1.lookup("btnStdntPop");
                            if (btnStdntPop) {
                                btnStdntPop.click();
                                return {status: "success"};
                            }
                            return {status: "btn_not_found"};
                        })()
                    """)
                    if isinstance(pop1_click, dict) and pop1_click["status"] == "success":
                        break
                    print(f"   -> Popup1 not ready yet... Retrying ({r_pop1+1}/4)")
                    await asyncio.sleep(1.5)
                
                if not isinstance(pop1_click, dict) or pop1_click["status"] != "success":
                    print("Error: 등록 팝업1을 찾지 못했거나 '참가자 추가' 버튼이 누락되었습니다. 상태:", pop1_click)
                    return
                
                await asyncio.sleep(2.5) # 학생 추가 팝업창 활성화 대기


                # 3. 학생 추가 팝업창 활성화 대기 및 결석/지각 학생 필터링 후 추가
                print(" - Waiting for Student popup2 and filtering...")
                pop2_ready = False
                for r_pop2 in range(4):
                    pop2_ready = await target_page.evaluate("""
                        (function() {
                            var popup2 = cpr.core.Platform.INSTANCE.getAllRunningAppInstances().find(function(ai) {
                                return ai.app && ai.app.id === "edu/sa/phe/phe/sm/phe_phesm02_p02";
                            });
                            return !!popup2;
                        })()
                    """)
                    if pop2_ready:
                        break
                    print(f"   -> Popup2 not ready yet... Retrying ({r_pop2+1}/4)")
                    await asyncio.sleep(1.5)
                
                if not pop2_ready:
                    print("Error: Student selection popup2 (phe_phesm02_p02) did not open.")
                    return

                filter_res = await target_page.evaluate(JS_FILTER_ABSENT_STUDENTS)
                if "error" in filter_res:
                    print("Error from Filter JS:", filter_res["error"])
                    return
                print(f"   -> Added: {filter_res['added']} students, Filtered out: {filter_res['absent']}")


                # 학생 추가 확인 얼럿(예: "추가되었습니다.") 강제 닫기 및 팝업 대기
                print(" - Waiting for '추가되었습니다' dialog to close...")
                await wait_dialog(target_page, 3000)
                await asyncio.sleep(3.0) # 원래 팝업 복귀 및 데이터셋 바인딩 넉넉히 대기


                # 4. 정보 주입 및 내용 일괄적용
                print(" - Injecting fields and applying content...")
                payload = JS_SUBMIT_TRANSACTION.replace("PARAM_YMD_HM", sch['ymd_hm']).replace("PARAM_ACT_TEXT", sch['text'])
                
                sub_res = None
                # 최대 4회 재시도 (비동기 학생 추가 바인딩 딜레이 극복)
                for retry in range(4):
                    sub_res = await target_page.evaluate(payload)
                    if isinstance(sub_res, dict) and "error" in sub_res:
                        if "비어있습니다" in sub_res["error"]:
                            print(f"   -> Waiting for student grid binding... (Retry {retry+1}/4)")
                            await asyncio.sleep(1.5)
                            continue
                        else:
                            print("Error during submission:", sub_res["error"])
                            return
                    break
                
                if isinstance(sub_res, dict) and "error" in sub_res:
                    print("Error: Student binding timed out. Submission aborted.")
                    return
                
                # 내용 일괄적용 얼럿 닫기
                await wait_dialog(target_page, 2000)


                # 5. 시간 일괄적용
                print(" - Applying activity time...")
                time_res = await target_page.evaluate(JS_APPLY_TIME_AND_SAVE)
                if "error" in time_res:
                    print("Error during time application:", time_res["error"])
                    return
                
                # 시간 일괄적용 얼럿 닫기
                await wait_dialog(target_page, 2000)

                # 6. 저장 및 확인 처리 (실제 반영 플래그 체크)
                if args.apply:
                    print(" - Apply flag detected. Saving record...")
                    saved = await target_page.evaluate("window.__clickSaveSports()")
                    if saved:
                        # 저장 확인 confirm 및 저장완료 alert 수락 루프
                        for _ in range(4):
                            await asyncio.sleep(1.0)
                            await target_page.evaluate(JS_CLICK_DIALOG_OK)
                        print("   -> Save sequence successfully finished.")
                    else:
                        print("Error: Save button not found.")
                        return
                else:
                    print(" - [DRY RUN] Apply flag not set. Clicking Close...")
                    await target_page.evaluate("""
                        (function() {
                            var popup1 = cpr.core.Platform.INSTANCE.getAllRunningAppInstances().find(function(ai) {
                                return ai.app && ai.app.id === "edu/sa/phe/phe/sm/phe_phesm02_p01";
                            });
                            if (popup1) {
                                var btnCancel = popup1.lookup("btnCancel");
                                if (btnCancel) btnCancel.click();
                            }
                        })()
                    """)
                    await asyncio.sleep(1.5)
                    # 취소 시 컨펌 다이얼로그 닫기
                    await wait_dialog(target_page, 2000)

                await asyncio.sleep(2.0) # 트랜잭션 마무리 대기

            print("\n🎉 All entry schedules successfully processed!")
            
            # 최종 새로고침 조회
            print("Refreshing Main page...")
            await target_page.evaluate("""
                (function() {
                    var main = cpr.core.Platform.INSTANCE.getAllRunningAppInstances().find(function(ai) {
                        return ai.app && ai.app.id === "edu/sa/phe/phe/sm/phe_phesm02_m00";
                    });
                    if (main) {
                        var btnSearch = main.lookup("btnSearch");
                        if (btnSearch) btnSearch.click();
                    }
                })()
            """)
            await asyncio.sleep(2.0)
            
            # 스크린샷 저장
            os.makedirs("scratch", exist_ok=True)
            await target_page.screenshot(path="scratch/sports_club_finished.png")
            print("Final screen verification captured at scratch/sports_club_finished.png")

        except Exception as e:
            print("Error occurred during sports club processing:", e)

if __name__ == "__main__":
    asyncio.run(main())
