#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
나이스(NEIS) 교원연수 이수실적 등록 (이수등록) 자동화 스크립트 v2.1
===================================================================
Target App ID: `edu/ga/tps/hrd/mm/tps_hrdmm01_p14` (연수 변경신청 상세 팝업)

사용법:
  python neis_training_completion.py --dry-run --data data/cpr_training_2026.json # 모의 실행
  python neis_training_completion.py --fill-only --data data/cpr_training_2026.json # 폼 필드 채우기만 수행
  python neis_training_completion.py --apply --confirm APPLY_NEIS --data data/cpr_training_2026.json # 실반영 및 저장
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
DEFAULT_DATA_PATH = Path(__file__).parent / "data" / "cpr_training_2026.json"

JS_FILL_TRAINING_FORM = r"""
return (function(data) {
  var platform = window.cpr && cpr.core && cpr.core.Platform && cpr.core.Platform.INSTANCE;
  if (!platform) return { success: false, error: "cpr Platform is not available" };

  var apps = platform.getAllRunningAppInstances();
  var targetApp = apps.find(function(a) { return a.app && a.app.id === "edu/ga/tps/hrd/mm/tps_hrdmm01_p14"; });
  if (!targetApp) {
    targetApp = apps.find(function(a) { return a.app && a.app.id && (a.app.id.indexOf("hrdmm01_p14") !== -1 || a.app.id.indexOf("hrd") !== -1); });
  }
  if (!targetApp && apps.length > 0) targetApp = apps[apps.length - 1];

  if (!targetApp) return { success: false, error: "연수 변경신청 상세(tps_hrdmm01_p14) 팝업을 찾을 수 없습니다." };

  var updatedFields = [];

  function setVal(ctrlId, val) {
    if (val === undefined || val === null) return;
    var c = targetApp.lookup ? targetApp.lookup(ctrlId) : null;
    if (c) {
      if (typeof c.setValue === "function") c.setValue(val);
      else c.value = val;
      if (typeof c.redraw === "function") { try { c.redraw(); } catch(e){} }
      updatedFields.push(ctrlId + " = " + val);
    }
  }

  // 1. 과정년도 (dtiTraiCrseYr)
  setVal("dtiTraiCrseYr", data.year || "2026");

  // 2. 교육유형 (cmbEduTypScCd) - 001: 교육기관교육
  setVal("cmbEduTypScCd", data.edu_type_code || "001");

  // 3. 연수구분 (cmbTraiScCd) - 02: 직무연수
  setVal("cmbTraiScCd", data.category_code || "02");

  // 4. 교육형태 (cmbEduStleCd) - B: 집합, C: 원격
  setVal("cmbEduStleCd", data.format_code || "B");

  // 5. 연수내용 (cmbTraiCnClfCd) - 02: 생활교육
  setVal("cmbTraiCnClfCd", data.content_code || "02");

  // 6. 직무관련성여부 (rdbDtyRlvncYn) - Y: 직무관련
  setVal("rdbDtyRlvncYn", data.job_relevance ? "Y" : "N");

  // 7. 연수과정명 (ipbTraiCrseNm)
  setVal("ipbTraiCrseNm", data.course_name || "2026심폐소생술등응급처치교육");

  // 8. 연수기관 (cmbTchTraiEduInstCd / ipbTraiInstNm)
  // 직접입력 버튼이 있는 경우 클릭 시도
  var btnDirect = targetApp.lookup ? (targetApp.lookup("btnDirect") || targetApp.lookup("btnInstDirect") || targetApp.lookup("btnTraiInstNm")) : null;
  if (btnDirect && typeof btnDirect.click === "function") {
    try { btnDirect.click(); } catch(e){}
  }
  if (data.institution_code) {
    setVal("cmbTchTraiEduInstCd", data.institution_code);
  }
  setVal("ipbTraiInstNm", data.institution || "동국대학교경주병원");

  // 9. 연수기간 시작/종료 (dtiTraiBgngYmd, dtiTraiEndYmd)
  setVal("dtiTraiBgngYmd", (data.start_date || "2026-09-30").replace(/-/g, ""));
  setVal("dtiTraiEndYmd", (data.end_date || "2026-09-30").replace(/-/g, ""));

  // 10. 연수시간/분 (nbeTraiHh, nbeTraiMm)
  setVal("nbeTraiHh", (data.hours !== undefined ? data.hours : 4).toString());
  setVal("nbeTraiMm", (data.minutes !== undefined ? data.minutes : 0).toString());

  // 11. 법정의무교육여부 (rdbSttyOblgEduYn)
  setVal("rdbSttyOblgEduYn", data.statutory_mandatory ? "Y" : "N");

  // 12. 이수번호 (ipbTraiComptNo)
  setVal("ipbTraiComptNo", data.completion_no || "동국대경주병원-초-직무-2026-202");

  // 13. 법정의무교육 구분 (ipbSttyOblgEduNm)
  setVal("ipbSttyOblgEduNm", data.statutory_category || "심폐소생술 등 응급처치에 관한 교육");

  // 14. Dataset dsMain 직접 동기화
  var dsMain = targetApp.lookup ? targetApp.lookup("dsMain") : null;
  if (dsMain && dsMain.getRowCount() > 0) {
    dsMain.setValue(0, "traiCrseYr", data.year || "2026");
    dsMain.setValue(0, "eduTypScCd", data.edu_type_code || "001");
    dsMain.setValue(0, "traiScCd", data.category_code || "02");
    dsMain.setValue(0, "eduStleCd", data.format_code || "B");
    dsMain.setValue(0, "traiCnClfCd", data.content_code || "02");
    dsMain.setValue(0, "dtyRlvncYn", data.job_relevance ? "Y" : "N");
    dsMain.setValue(0, "traiCrseNm", data.course_name || "2026심폐소생술등응급처치교육");
    if (data.institution_code) dsMain.setValue(0, "tchTraiEduInstCd", data.institution_code);
    dsMain.setValue(0, "traiInstNm", data.institution || "동국대학교경주병원");
    dsMain.setValue(0, "traiBgngYmd", (data.start_date || "2026-09-30").replace(/-/g, ""));
    dsMain.setValue(0, "traiEndYmd", (data.end_date || "2026-09-30").replace(/-/g, ""));
    dsMain.setValue(0, "traiHh", (data.hours !== undefined ? data.hours : 4).toString());
    dsMain.setValue(0, "traiMm", (data.minutes !== undefined ? data.minutes : 0).toString());
    dsMain.setValue(0, "sttyOblgEduYn", data.statutory_mandatory ? "Y" : "N");
    if (data.statutory_category_code) dsMain.setValue(0, "sttyOblgEduCd", data.statutory_category_code);
    dsMain.setValue(0, "traiComptNo", data.completion_no || "동국대경주병원-초-직무-2026-202");
    dsMain.setValue(0, "sttyOblgEduNm", data.statutory_category || "심폐소생술 등 응급처치에 관한 교육");
    updatedFields.push("dsMain 데이터셋 바인딩 동기화 완료");
  }

  return { success: true, appId: targetApp.app.id, updated: updatedFields };
})(arguments[0]);
"""

JS_SAVE_AND_DISMISS_MODALS = r"""
return (function() {
  var platform = window.cpr && cpr.core && cpr.core.Platform && cpr.core.Platform.INSTANCE;
  if (!platform) return { success: false, error: "cpr Platform is not available" };

  var apps = platform.getAllRunningAppInstances();
  var saved = false;

  // 1. 연수 팝업 앱(tps_hrdmm01_p14)의 btnSave 클릭
  var targetApp = apps.find(function(a) { return a.app && a.app.id === "edu/ga/tps/hrd/mm/tps_hrdmm01_p14"; });
  if (targetApp) {
    var btnSave = targetApp.lookup ? targetApp.lookup("btnSave") : null;
    if (btnSave && typeof btnSave.click === "function") {
      btnSave.click();
      saved = true;
    }
  }

  // 2. confirm/alert 팝업 자동 확인 처리
  var closedModals = 0;
  apps.forEach(function(ai) {
    if (ai && ai.app && ai.app.id && (ai.app.id.indexOf("confirm") !== -1 || ai.app.id.indexOf("alert") !== -1 || ai.app.id.indexOf("cmn") !== -1)) {
      try {
        var container = ai.getContainer ? ai.getContainer() : null;
        if (container && container.getAllRecursiveChildren) {
          container.getAllRecursiveChildren().forEach(function(c) {
            if (c && c.type === "button" && (c.value === "예" || c.value === "확인" || c.id === "btnOk" || c.id === "btnConfirm")) {
              if (typeof c.click === "function") {
                c.click();
                closedModals++;
              }
            }
          });
        }
      } catch(e) {}
    }
  });

  return { success: true, clickedSave: saved, closedModalsCount: closedModals };
})();
"""


def load_training_data(args: argparse.Namespace) -> dict:
    """CLI 인자 또는 JSON 파일에서 연수 이수 정보를 로드합니다."""
    data = {
        "year": args.year,
        "edu_type_code": args.edu_type_code,
        "category_code": args.category_code,
        "format_code": args.format_code,
        "content_code": args.content_code,
        "job_relevance": True if args.job_relevance == "Y" else False,
        "course_name": args.course_name,
        "institution_code": args.institution_code,
        "institution": args.institution,
        "start_date": args.start_date,
        "end_date": args.end_date,
        "hours": args.hours,
        "minutes": args.minutes,
        "statutory_mandatory": True if args.statutory_mandatory == "Y" else False,
        "completion_no": args.completion_no,
        "statutory_category": args.statutory_category,
        "attachment_filename": args.attachment
    }

    if args.data and Path(args.data).exists():
        with open(args.data, "r", encoding="utf-8") as f:
            file_data = json.load(f)
            data.update(file_data)
            print(f"[data] JSON 데이터 로드 완료 ({args.data})")

    return data


def attach_chrome(port: int = REMOTE_PORT):
    """원격 Chrome에 연결합니다."""
    os.environ["no_proxy"] = "localhost,127.0.0.1"
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    opts = Options()
    opts.add_experimental_option("debuggerAddress", f"127.0.0.1:{port}")
    driver = webdriver.Chrome(options=opts)
    return driver


def find_hrd_window(driver):
    """연수 팝업 또는 나이스가 열려있는 윈도우 핸들로 전환합니다."""
    js_check = """
    var platform = window.cpr && cpr.core && cpr.core.Platform && cpr.core.Platform.INSTANCE;
    if (!platform) return false;
    var apps = platform.getAllRunningAppInstances();
    return apps.some(function(a) {
        return a.app && a.app.id && (a.app.id.indexOf("hrd") !== -1 || a.app.id.indexOf("Index") !== -1);
    });
    """
    for h in driver.window_handles:
        driver.switch_to.window(h)
        try:
            if driver.execute_script(js_check):
                print(f"[window] 연수 관련 앱이 실행 중인 윈도우 발견: {driver.title} ({driver.current_url})")
                return True
        except Exception:
            pass
    return False


def run_dry_run(data: dict):
    """모의 실행 요약을 출력합니다."""
    print("=" * 65)
    print("  [DRY-RUN] 교원연수 이수실적 등록 모의 실행 요약 (심폐소생술 교육)")
    print("=" * 65)
    print(f"  • 과정년도        : {data['year']}")
    print(f"  • 교육유형        : {data.get('edu_type', '교육기관교육')} (코드: {data['edu_type_code']})")
    print(f"  • 연수구분        : {data.get('category', '직무연수')} (코드: {data['category_code']})")
    print(f"  • 교육형태        : {data.get('format', '집합')} (코드: {data['format_code']})")
    print(f"  • 연수내용        : {data.get('content_category', '생활교육')} (코드: {data['content_code']})")
    print(f"  • 직무관련성여부  : {'직무관련 (Y)' if data['job_relevance'] else '직무무관 (N)'}")
    print(f"  • 연수과정명      : {data['course_name']}")
    print(f"  • 연수기관        : {data['institution']} (코드: {data.get('institution_code', '직접입력')})")
    print(f"  • 연수기간        : {data['start_date']} ~ {data['end_date']} (1일간)")
    print(f"  • 연수시간        : {data['hours']}시간 {data['minutes']}분")
    print(f"  • 이수번호        : {data['completion_no']}")
    print(f"  • 법정의무교육여부: {'예 (Y)' if data['statutory_mandatory'] else '아니오 (N)'}")
    print(f"  • 법정의무교육명  : {data['statutory_category']}")
    default_fp = 'C:/FBKR_SCAN/' + data.get('attachment_filename', '')
    print(f"  • 증빙자료 파일명 : {data['attachment_filename']}")
    print(f"  • 증빙자료 실경로 : {data.get('attachment_filepath', default_fp)}")
    print("=" * 65)


def run_apply(driver, data: dict, save: bool = True):
    """실제 나이스 연수 팝업 화면에 데이터를 주입합니다. save가 False이면 저장을 누르지 않습니다."""
    if not find_hrd_window(driver):
        print("[warn] 현재 원격 Chrome에 'tps_hrdmm01_p14' (연수 변경신청 상세) 팝업이 활성화되어 있지 않습니다.")
        print("나이스 화면에서 [연수이수결과 등록신청] 팝업을 띄운 후 다시 실행해 주십시오.")
        return False

    print("[apply] eXBuilder6 폼 필드 데이터 주입 중...")
    res_fill = driver.execute_script(JS_FILL_TRAINING_FORM, data)
    print(f"[apply] 필드 주입 결과: {json.dumps(res_fill, ensure_ascii=False, indent=2)}")

    if not res_fill.get("success"):
        print(f"[error] 주입 실패: {res_fill.get('error')}")
        return False

    if not save:
        print("\n[OK] 폼 필드 채우기가 완료되었습니다! (저장은 누르지 않음)")
        print(f"화면에서 증빙자료 파일({data.get('attachment_filename')})을 [찾기] 버튼으로 첨부하신 후 [저장]을 눌러주십시오.")
        return True

    time.sleep(1)

    print("[apply] [저장] 버튼 클릭 및 모달 해제 실행 중...")
    res_save = driver.execute_script(JS_SAVE_AND_DISMISS_MODALS)
    print(f"[apply] 저장 처리 결과: {json.dumps(res_save, ensure_ascii=False, indent=2)}")

    time.sleep(2)
    driver.execute_script(JS_SAVE_AND_DISMISS_MODALS)
    print("✅ [완료] 연수 이수실적 데이터 주입 및 저장이 완료되었습니다!")
    return True


def main():
    parser = argparse.ArgumentParser(description="나이스 연수 이수실적 등록 자동화 스크립트")
    parser.add_argument("--data", type=str, default=str(DEFAULT_DATA_PATH), help="이수증 JSON 데이터 파일 경로")
    parser.add_argument("--course-name", type=str, default="2026심폐소생술등응급처치교육", help="연수과정명")
    parser.add_argument("--completion-no", type=str, default="동국대경주병원-초-직무-2026-202", help="이수번호")
    parser.add_argument("--start-date", type=str, default="2026-09-30", help="연수 시작일 (YYYY-MM-DD)")
    parser.add_argument("--end-date", type=str, default="2026-09-30", help="연수 종료일 (YYYY-MM-DD)")
    parser.add_argument("--hours", type=int, default=4, help="연수 인정 시간")
    parser.add_argument("--minutes", type=int, default=0, help="연수 인정 분")
    parser.add_argument("--institution-code", type=str, default="0600000150", help="연수기관 코드")
    parser.add_argument("--institution", type=str, default="동국대학교경주병원", help="연수기관명")
    parser.add_argument("--year", type=str, default="2026", help="과정년도")
    parser.add_argument("--edu-type-code", type=str, default="001", help="교육유형 코드 (001: 교육기관교육)")
    parser.add_argument("--category-code", type=str, default="02", help="연수구분 코드 (02: 직무연수)")
    parser.add_argument("--format-code", type=str, default="B", help="교육형태 코드 (B: 집합)")
    parser.add_argument("--content-code", type=str, default="02", help="연수내용 코드 (02: 생활교육)")
    parser.add_argument("--job-relevance", type=str, default="Y", help="직무관련성 여부 (Y/N)")
    parser.add_argument("--statutory-mandatory", type=str, default="Y", help="법정의무교육 여부 (Y/N)")
    parser.add_argument("--statutory-category", type=str, default="심폐소생술 등 응급처치에 관한 교육", help="법정의무교육 구분명")
    parser.add_argument("--attachment", type=str, default="2026심폐소생술등응급처치교육이수증(이창수).pdf", help="증빙자료 파일명")

    parser.add_argument("--dry-run", action="store_true", help="모의 실행 (화면 변동 없음)")
    parser.add_argument("--fill-only", action="store_true", help="폼 필드 채우기만 수행하고 저장은 누르지 않음")
    parser.add_argument("--apply", action="store_true", help="실제 나이스 저장 처리")
    parser.add_argument("--confirm", type=str, default="", help="실반영 확인 문구 (APPLY_NEIS 필수)")

    args = parser.parse_args()

    data = load_training_data(args)

    if args.dry_run or (not args.apply and not args.fill_only):
        run_dry_run(data)
        return

    driver = attach_chrome(REMOTE_PORT)
    if not driver:
        print("[error] Remote Chrome 9222 포트에 연결할 수 없습니다.")
        sys.exit(1)

    if args.fill_only:
        run_apply(driver, data, save=False)
        return

    if args.apply:
        if args.confirm != "APPLY_NEIS":
            print("[error] 실반영을 위해서는 '--confirm APPLY_NEIS' 옵션이 필수입니다.")
            sys.exit(1)
        run_apply(driver, data, save=True)


if __name__ == "__main__":
    main()
