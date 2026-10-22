#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
나이스(NEIS) 출장신청 자동화 스크립트 v1.0
=========================================
Target Menu: 복무 > 개인출장관리 (MENU_ID: AMCMC40046, Page: edu/ga/srv/mym/mm/srv_mymmm03_m00)
Target Popup: `edu/ga/srv/mym/mm/srv_mymmm03_p00` (출장신청 팝업)

사용법:
  python neis_business_trip.py --dry-run --data data/trip_aiedap_2026.json
  python neis_business_trip.py --fill-only --data data/trip_aiedap_2026.json
  python neis_business_trip.py --apply --confirm APPLY_NEIS --data data/trip_aiedap_2026.json
"""

from __future__ import annotations

import argparse
import io
import json
import os
import sys
import time
from pathlib import Path

# CP949 터미널 깨짐 방지
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

REMOTE_PORT = 9222
DEFAULT_DATA_PATH = Path(__file__).parent / "data" / "trip_aiedap_2026.json"

JS_CHECK_AND_OPEN_POPUP = r"""
return (function() {
  var platform = window.cpr && cpr.core && cpr.core.Platform && cpr.core.Platform.INSTANCE;
  if (!platform) return { success: false, error: "cpr Platform이 로드되지 않았습니다." };

  var apps = platform.getAllRunningAppInstances();
  // 1. 이미 팝업이 떠 있는지 확인
  var popup = apps.find(function(a) { return a.app && a.app.id === "edu/ga/srv/mym/mm/srv_mymmm03_p00"; });
  if (popup) return { success: true, status: "popup_already_open" };

  // 2. 메인 화면(srv_mymmm03_m00)이 열려 있는지 확인
  var main = apps.find(function(a) { return a.app && a.app.id === "edu/ga/srv/mym/mm/srv_mymmm03_m00"; });
  if (!main) {
    // MDI 메뉴 열기 시도
    if (window.openMdiMenu) {
      window.openMdiMenu("AMCMC40046");
      return { success: true, status: "menu_opened_waiting" };
    }
    return { success: false, error: "개인출장관리 화면을 찾을 수 없고 openMdiMenu 함수가 없습니다." };
  }

  // 3. 신청 버튼 클릭
  var btnAply = main.lookup("btnAply");
  if (btnAply && typeof btnAply.click === "function") {
    btnAply.click();
    return { success: true, status: "apply_button_clicked" };
  }

  return { success: false, error: "메인 화면에서 신청(btnAply) 버튼을 찾을 수 없습니다." };
})();
"""

JS_FILL_TRIP_FORM = r"""
return (function(data) {
  var platform = window.cpr && cpr.core && cpr.core.Platform && cpr.core.Platform.INSTANCE;
  if (!platform) return { success: false, error: "cpr Platform이 로드되지 않았습니다." };

  var apps = platform.getAllRunningAppInstances();
  var popup = apps.find(function(a) { return a.app && a.app.id === "edu/ga/srv/mym/mm/srv_mymmm03_p00"; });
  if (!popup) return { success: false, error: "출장신청 팝업(srv_mymmm03_p00)을 찾을 수 없습니다." };

  var updatedFields = [];

  function setCtrlVal(ctrlId, val) {
    if (val === undefined || val === null) return;
    var c = popup.lookup(ctrlId);
    if (c) {
      if (typeof c.setValue === "function") c.setValue(val);
      else c.value = val;
      try {
        c.dispatchEvent(new cpr.events.CValueChangeEvent("value-change", { oldValue: "", newValue: val }));
      } catch(e) {}
      if (typeof c.redraw === "function") { try { c.redraw(); } catch(e){} }
      updatedFields.push(ctrlId + " = " + val);
    }
  }

  // 1. 기간 설정. `periods`는 날짜별 행을 유지해야 하는 관내 다일 출장에 사용.
  var periods = data.periods || [{
    start_date: data.start_date,
    start_hour: data.start_hour,
    start_minute: data.start_minute,
    end_date: data.end_date,
    end_hour: data.end_hour,
    end_minute: data.end_minute
  }];
  if (!periods.length) return { success: false, error: "출장 기간(periods)이 비어 있습니다." };

  function ymd(v) { return String(v || "").replace(/-/g, ""); }
  function time(v, fallback) { return String(v === undefined || v === null ? fallback : v).padStart(2, "0"); }
  function setDs(ds, row, col, val) {
    if (ds && row < ds.getRowCount() && val !== undefined && val !== null && col in (ds.getRowDataRanged()[row] || {})) {
      ds.setValue(row, col, String(val));
    }
  }
  var dsBsrp = popup.lookup("dsBsrp");
  var dsTgpr = popup.lookup("dsTgpr");
  for (var i = 0; i < periods.length; i++) {
    var p = periods[i];
    if (i > 0 && (!dsBsrp || dsBsrp.getRowCount() <= i)) {
      var add = popup.lookup("btnAddPeriod");
      if (!add || typeof add.click !== "function") return { success: false, error: "기간추가(btnAddPeriod) 버튼을 찾지 못했습니다.", addedRows: i };
      add.click();
    }
    var sy = ymd(p.start_date), ey = ymd(p.end_date || p.start_date);
    var sh = time(p.start_hour, "09"), sm = time(p.start_minute, "00");
    var eh = time(p.end_hour, "17"), em = time(p.end_minute, "00");
    if (!(/^\d{8}$/.test(sy) && /^\d{8}$/.test(ey))) return { success: false, error: "기간 날짜는 YYYY-MM-DD 형식이어야 합니다.", periodIndex: i };
    if (i === 0) {
      setCtrlVal("dti1", sy); setCtrlVal("cmb10", sh); setCtrlVal("cmb2", sm);
      setCtrlVal("dti2", ey); setCtrlVal("cmb3", eh); setCtrlVal("cmb4", em);
    }
    // 기간추가가 만든 기본 행(오늘 날짜 등)을 요청 데이터로 바로 덮어쓴다.
    setDs(dsBsrp, i, "bgngYmd", sy); setDs(dsBsrp, i, "bgngHh", sh); setDs(dsBsrp, i, "bgngMm", sm); setDs(dsBsrp, i, "bgngHm", sh + sm);
    setDs(dsBsrp, i, "endYmd", ey); setDs(dsBsrp, i, "endHh", eh); setDs(dsBsrp, i, "endMm", em); setDs(dsBsrp, i, "endHm", eh + em);
    setDs(dsBsrp, i, "bsrpSn", String(i));
    var duration = Math.max(0, (Date.parse(ey.slice(0,4) + "-" + ey.slice(4,6) + "-" + ey.slice(6,8) + "T" + eh + ":" + em) - Date.parse(sy.slice(0,4) + "-" + sy.slice(4,6) + "-" + sy.slice(6,8) + "T" + sh + ":" + sm)) / 60000);
    setDs(dsBsrp, i, "allBsrpHrDdCnt", String(Math.floor(duration / 1440)));
    setDs(dsBsrp, i, "allBsrpHrHCnt", String(Math.floor((duration % 1440) / 60)));
    setDs(dsBsrp, i, "allBsrpHrMCnt", String(duration % 60));
  }
  if (!dsBsrp || dsBsrp.getRowCount() < periods.length) {
    return { success: false, error: "기간 행 생성이 완료되지 않았습니다.", expectedRows: periods.length, actualRows: dsBsrp ? dsBsrp.getRowCount() : 0 };
  }

  // 2. 출장종류 (10: 관내, 20: 관외, 40: 연수)
  setCtrlVal("cmbBsrpScCd", data.trip_type || "10");

  // 3. 연락처
  var cleanPhone = (data.contact || "010-4233-0844").replace(/[^0-9]/g, "");
  setCtrlVal("mse1", cleanPhone);

  // 4. 출장지
  setCtrlVal("ipbDobtNm", data.destination || "경상북도 경주시 더케이호텔 경주");

  // 5. 출장목적
  setCtrlVal("ipbBsrpCn", data.purpose || "교육부 「2026 AIEDAP 마스터교원 신규연수 초등 1차」 집합연수 참석");

  // 6. 이동사항
  setCtrlVal("ipbMvmnMteCn", data.transportation || "자가용");

  // 7. 기타 옵션 체크박스
  if (data.official_vehicle !== undefined) setCtrlVal("cbxOfflVhcUtilzYn", data.official_vehicle ? "Y" : "N");
  if (data.no_travel_expense !== undefined) setCtrlVal("cbxTvctPyrfYn", data.no_travel_expense ? "Y" : "N");
  if (data.include_lunch !== undefined) setCtrlVal("cbxLunchHrWorkInclsYn", data.include_lunch ? "Y" : "N");
  if (data.is_training !== undefined) setCtrlVal("cbxEduDisciYn", data.is_training ? "Y" : "N");

  // 상단 입력값을 날짜별 기간 행마다 동기화한다.
  var commonFields = {
    instNm: data.expense_institution || data.institution_name || "",
    bsrpScCd: data.trip_type || "10",
    bsrpScNm: data.trip_type_name || "",
    bsrpCn: data.purpose || "",
    dobtNm: data.destination || "",
    mvmnMteCn: data.transportation || "",
    emgCnctTelno: cleanPhone,
    offlVhcUtilzYn: data.official_vehicle ? "Y" : "N",
    tvctPyrfYn: data.no_travel_expense ? "Y" : "N",
    lunchHrWorkInclsYn: data.include_lunch ? "Y" : "N",
    eduDisciYn: data.is_training ? "Y" : "N",
    ddRpatYn: "N"
  };
  for (var ri = 0; ri < periods.length; ri++) {
    Object.keys(commonFields).forEach(function(col) { setDs(dsBsrp, ri, col, commonFields[col]); });
    var rp = periods[ri];
    var rSy = ymd(rp.start_date), rEy = ymd(rp.end_date || rp.start_date);
    var rSh = time(rp.start_hour, "09"), rSm = time(rp.start_minute, "00");
    var rEh = time(rp.end_hour, "17"), rEm = time(rp.end_minute, "00");
    var rDuration = Math.max(0, (Date.parse(rEy.slice(0,4) + "-" + rEy.slice(4,6) + "-" + rEy.slice(6,8) + "T" + rEh + ":" + rEm) - Date.parse(rSy.slice(0,4) + "-" + rSy.slice(4,6) + "-" + rSy.slice(6,8) + "T" + rSh + ":" + rSm)) / 60000);
    setDs(dsBsrp, ri, "allBsrpHrDdCnt", String(Math.floor(rDuration / 1440)));
    setDs(dsBsrp, ri, "allBsrpHrHCnt", String(Math.floor((rDuration % 1440) / 60)));
    setDs(dsBsrp, ri, "allBsrpHrMCnt", String(rDuration % 60));
  }

  // 8. 기간추가가 복제한 출장자 목록의 날짜도 기간별로 맞춘다.
  var grdTgpr = popup.lookup("grdTgpr");
  if (dsTgpr && dsTgpr.getRowCount() < periods.length) {
    return { success: false, error: "출장자 기간 행 수가 기간 수보다 적습니다.", expectedRows: periods.length, actualRows: dsTgpr.getRowCount() };
  }
  for (var ti = 0; dsTgpr && ti < periods.length; ti++) {
    var tp = periods[ti];
    var tSy = ymd(tp.start_date), tEy = ymd(tp.end_date || tp.start_date);
    var tSh = time(tp.start_hour, "09"), tSm = time(tp.start_minute, "00");
    var tEh = time(tp.end_hour, "17"), tEm = time(tp.end_minute, "00");
    [["bsrpSn", String(ti)], ["bgngYmd", tSy], ["bgngHh", tSh], ["bgngMm", tSm], ["bgngHm", tSh + tSm],
     ["endYmd", tEy], ["endHh", tEh], ["endMm", tEm], ["endHm", tEh + tEm], ["rprsYn", "Y"], ["sameBsrpPriodYn", "Y"]]
      .forEach(function(pair) { setDs(dsTgpr, ti, pair[0], pair[1]); });
  }
  if (grdTgpr && typeof grdTgpr.redraw === "function") grdTgpr.redraw();
  var grdMain = popup.lookup("grdMain");
  if (grdMain && typeof grdMain.redraw === "function") grdMain.redraw();

  // 포커스를 폼 하단으로 이동하여 스크롤 유도
  var ipbBsrpCn = popup.lookup("ipbBsrpCn");
  if (ipbBsrpCn && typeof ipbBsrpCn.focus === "function") {
    try { ipbBsrpCn.focus(); } catch(e){}
  }

  return {
    success: true,
    updatedFields: updatedFields,
    bsrpData: dsBsrp ? dsBsrp.getRowDataRanged().map(function(r) { return { bsrpSn: String(r.bsrpSn), instNm: r.instNm, bgngYmd: r.bgngYmd, bgngHm: r.bgngHm, endYmd: r.endYmd, endHm: r.endHm, days: r.allBsrpHrDdCnt, hours: r.allBsrpHrHCnt, minutes: r.allBsrpHrMCnt, type: r.bsrpScCd }; }) : null,
    tgprData: dsTgpr ? dsTgpr.getRowDataRanged().map(function(r) { return { bsrpSn: r.bsrpSn, invlFlnm: r.invlFlnm, rprsYn: r.rprsYn, bgngYmd: r.bgngYmd, bgngHm: r.bgngHm, endYmd: r.endYmd, endHm: r.endHm }; }) : null
  };
})(arguments[0]);
"""

JS_DISMISS_ALERTS = r"""
return (function() {
  var platform = window.cpr && cpr.core && cpr.core.Platform && cpr.core.Platform.INSTANCE;
  if (!platform) return false;
  var apps = platform.getAllRunningAppInstances();
  var dismissed = false;
  for (var i = 0; i < apps.length; i++) {
    var a = apps[i];
    if (a.app && a.app.id && (a.app.id.indexOf("alert") !== -1 || a.app.id.indexOf("confirm") !== -1)) {
      var btn = a.lookup("btnConfirm") || a.lookup("btnOk");
      if (btn && typeof btn.click === "function") {
        btn.click();
        dismissed = true;
      }
    }
  }
  return dismissed;
})();
"""

JS_CLICK_APPLY_SAVE = r"""
return (function() {
  var platform = window.cpr && cpr.core && cpr.core.Platform && cpr.core.Platform.INSTANCE;
  if (!platform) return { success: false, error: "cpr Platform이 로드되지 않았습니다." };

  var apps = platform.getAllRunningAppInstances();
  var popup = apps.find(function(a) { return a.app && a.app.id === "edu/ga/srv/mym/mm/srv_mymmm03_p00"; });
  if (!popup) return { success: false, error: "출장신청 팝업(srv_mymmm03_p00)을 찾을 수 없습니다." };

  var btnAply = popup.lookup("btnAply");
  if (!btnAply || typeof btnAply.click !== "function") {
    return { success: false, error: "승인요청(btnAply) 버튼을 찾을 수 없습니다." };
  }

  btnAply.click();
  return { success: true, message: "승인요청 버튼을 클릭했습니다." };
})();
"""


def get_driver():
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options

    os.environ["no_proxy"] = "localhost,127.0.0.1"
    opts = Options()
    opts.add_experimental_option("debuggerAddress", f"127.0.0.1:{REMOTE_PORT}")
    return webdriver.Chrome(options=opts)


def ensure_neis_tab(driver):
    neis_handle = None
    for h in driver.window_handles:
        driver.switch_to.window(h)
        if "neis.go.kr" in driver.current_url:
            neis_handle = h
            break

    if neis_handle:
        driver.switch_to.window(neis_handle)
        return True

    # SSO를 통한 나이스 탭 오픈
    for h in driver.window_handles:
        driver.switch_to.window(h)
        if "eduptl" in driver.current_url:
            sso_url = driver.execute_script("""
                var btn = document.querySelector('a.menuBtn[id*="neis"]');
                return btn ? btn.id : null;
            """)
            if sso_url:
                print(f"[SSO] 포털에서 나이스 접속 URL 추출 성공: {sso_url[:60]}...")
                driver.switch_to.new_window("tab")
                driver.get(sso_url)
                time.sleep(6)
                return True

    return False


def main():
    parser = argparse.ArgumentParser(description="나이스(NEIS) 출장신청 자동화")
    parser.add_argument("--data", default=str(DEFAULT_DATA_PATH), help="출장 데이터 JSON 파일 경로")
    parser.add_argument("--dry-run", action="store_true", help="모의 실행 (입력 내용만 검증)")
    parser.add_argument("--fill-only", action="store_true", default=True, help="폼 필드 채우기만 수행 (기본값)")
    parser.add_argument("--apply", action="store_true", help="승인요청(저장) 버튼 클릭 수행")
    parser.add_argument("--confirm", default="", help="--apply 시 안전 확인 토큰 (APPLY_NEIS 필요)")
    parser.add_argument("--screenshot", default=None, help="스크린샷 저장 경로")
    args = parser.parse_args()

    data_file = Path(args.data)
    if not data_file.exists():
        print(f"[오류] 데이터 파일이 존재하지 않습니다: {data_file}")
        sys.exit(1)

    with open(data_file, "r", encoding="utf-8") as f:
        trip_data = json.load(f)

    print("=" * 60)
    print(" [NEIS] 출장신청 자동화 프로세스 시작")
    print(f" - 출장목적: {trip_data.get('purpose')}")
    periods = trip_data.get("periods") or [trip_data]
    print(f" - 출장기간: {len(periods)}개 기간")
    for idx, period in enumerate(periods, 1):
        print(f"   {idx}) {period.get('start_date')} {period.get('start_hour')}:{period.get('start_minute')} ~ {period.get('end_date', period.get('start_date'))} {period.get('end_hour')}:{period.get('end_minute')}")
    print(f" - 출장지: {trip_data.get('destination')}")
    print(f" - 출장종류: {trip_data.get('trip_type_name')} ({trip_data.get('trip_type')})")
    print(f" - 연락처: {trip_data.get('contact')}")
    print(f" - 이동사항: {trip_data.get('transportation')}")
    print("=" * 60)

    if args.dry_run:
        print("[Dry-run] 모의 실행 모드입니다. 브라우저 조작 없이 데이터를 정상 확인했습니다.")
        return

    try:
        driver = get_driver()
    except Exception as e:
        print(f"[오류] Chrome 9222 포트에 연결할 수 없습니다: {e}")
        sys.exit(1)

    if not ensure_neis_tab(driver):
        print("[오류] 나이스 탭을 찾을 수 없고 SSO 로그인도 불가능합니다.")
        sys.exit(1)

    print(f"[NEIS] 나이스 탭 연결 완료: {driver.title}")

    # 1. 팝업 확인 또는 열기
    ret = driver.execute_script(JS_CHECK_AND_OPEN_POPUP)
    print(f"[1단계] 팝업 확인/오픈 결과: {ret}")

    if ret.get("status") in ("menu_opened_waiting", "apply_button_clicked"):
        time.sleep(3)
        # 만약 한 번 더 클릭 필요하면 재확인
        ret = driver.execute_script(JS_CHECK_AND_OPEN_POPUP)
        print(f"[1단계 재확인] {ret}")
        time.sleep(2)

    # 2. 폼 입력
    fill_res = driver.execute_script(JS_FILL_TRIP_FORM, trip_data)
    print("[2단계] 폼 필드 입력 결과:")
    print(json.dumps(fill_res, ensure_ascii=False, indent=2))
    if not fill_res or not fill_res.get("success"):
        print("[오류] 폼 입력이 완료되지 않아 이후 단계를 중단합니다.")
        sys.exit(1)

    # 불필요한 알림이 떴다면 닫기
    time.sleep(1)
    driver.execute_script(JS_DISMISS_ALERTS)

    # 스크린샷 저장
    screenshot_path = args.screenshot
    if not screenshot_path:
        screenshot_path = str(Path(__file__).parent / "data" / "trip_last_filled.png")
    try:
        driver.save_screenshot(screenshot_path)
        print(f"[스크린샷] 현재 화면 캡처 저장: {screenshot_path}")
    except Exception as e:
        print(f"[경고] 스크린샷 캡처 실패: {e}")

    # 3. 승인요청(저장) 처리
    if args.apply:
        if args.confirm != "APPLY_NEIS":
            print("[안전 차단] --apply 실행 시에는 반드시 `--confirm APPLY_NEIS` 옵션이 필요합니다.")
            sys.exit(2)
        print("[3단계] 승인요청 버튼 클릭 진행 중...")
        save_res = driver.execute_script(JS_CLICK_APPLY_SAVE)
        print(f"[3단계 결과] {save_res}")
        time.sleep(2)
    else:
        print("[완료] 폼 입력이 완료되었습니다 (--fill-only 모드). 나이스 화면에서 검토 후 [승인요청]을 진행하세요.")


if __name__ == "__main__":
    main()
