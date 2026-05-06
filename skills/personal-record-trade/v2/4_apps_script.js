/**
 * 4_apps_script.js
 * ─────────────────────────────────────────────────────────────
 * Google Sheets Apps Script — 포트폴리오 자동 알림 시스템
 *
 * 설치 방법:
 *   1. Google Sheets 열기
 *   2. 확장 프로그램 → Apps Script
 *   3. 이 파일 전체 내용을 붙여넣기
 *   4. MY_EMAIL 변수를 본인 이메일로 수정
 *   5. 저장 (Ctrl+S)
 *   6. 트리거 설정 (시계 아이콘) → 아래 '트리거 설정' 참고
 * ─────────────────────────────────────────────────────────────
 */

// ══════════════════════════════════════════════════════════════
// 설정값 (여기만 수정하세요)
// ══════════════════════════════════════════════════════════════
const MY_EMAIL          = "your-email@gmail.com";  // ← 본인 이메일
const TARGET_SHEET_NAME = "📈 실시간현황";          // 실시간현황 시트명
const SIGNAL_COL        = 17;  // Q열: 매매신호
const NAME_COL          = 3;   // C열: 종목명
const CODE_COL          = 2;   // B열: 코드
const PRICE_COL         = 7;   // G열: 현재가(현지통화)
const TARGET_PRICE_COL  = 16;  // P열: 목표가
const RETURN_COL        = 13;  // M열: 수익률
const DATA_START_ROW    = 4;   // 데이터 시작 행

// ══════════════════════════════════════════════════════════════
// ① 목표가 알림 (매일 오전 9시 실행)
// ══════════════════════════════════════════════════════════════
function checkTargetPrice() {
  const ss    = SpreadsheetApp.getActiveSpreadsheet();
  const sheet = ss.getSheetByName(TARGET_SHEET_NAME);
  if (!sheet) { Logger.log("시트 없음: " + TARGET_SHEET_NAME); return; }

  const lastRow = sheet.getLastRow();
  const alerts  = [];
  const today   = Utilities.formatDate(new Date(), "Asia/Seoul", "yyyy-MM-dd");

  for (let row = DATA_START_ROW; row <= lastRow; row++) {
    const code    = sheet.getRange(row, CODE_COL).getValue();
    const name    = sheet.getRange(row, NAME_COL).getValue();
    const price   = sheet.getRange(row, PRICE_COL).getValue();
    const target  = sheet.getRange(row, TARGET_PRICE_COL).getValue();
    const ret     = sheet.getRange(row, RETURN_COL).getValue();
    const signal  = sheet.getRange(row, SIGNAL_COL).getValue();

    if (!code || !price) continue;

    // 🎯 목표가 90% 이상 도달
    if (target && price >= target * 0.9) {
      const pct = (price / target * 100).toFixed(1);
      alerts.push(
        `🎯 [목표가 근접] ${name}(${code})\n` +
        `   현재가: ${price.toLocaleString()}  목표가: ${target.toLocaleString()}  (${pct}% 달성)\n` +
        `   → 분할매도 검토`
      );
    }

    // 💰 수익률 30% 이상 → 차익실현 검토
    if (ret && ret >= 0.3) {
      alerts.push(
        `💰 [차익실현 검토] ${name}(${code})\n` +
        `   수익률: +${(ret * 100).toFixed(1)}%\n` +
        `   → 목표가 대비 비중 점검 권장`
      );
    }

    // 🚨 손실 -15% 이하 → 하방 검토
    if (ret && ret <= -0.15) {
      alerts.push(
        `🚨 [하방 도달 검토] ${name}(${code})\n` +
        `   수익률: ${(ret * 100).toFixed(1)}%\n` +
        `   → 투자 근거 재확인 필요`
      );
    }

    // ⚖️ 비중 초과
    if (signal && signal.includes("비중초과")) {
      alerts.push(
        `⚖️ [리밸런싱 필요] ${name}(${code})\n` +
        `   → 목표비중 초과. 일부 매도 또는 다른 종목 추가 매수 검토`
      );
    }
  }

  // 알림 발송
  if (alerts.length > 0) {
    const subject = `[포트폴리오 알림] ${today} — 신호 ${alerts.length}건`;
    const body    =
      `안녕하세요,\n\n오늘(${today}) 포트폴리오 점검 결과입니다.\n\n` +
      alerts.join("\n\n─────────────────\n\n") +
      `\n\n📊 시트 바로가기: ${ss.getUrl()}`;

    GmailApp.sendEmail(MY_EMAIL, subject, body);
    Logger.log(`알림 발송: ${alerts.length}건`);
  } else {
    Logger.log(`${today}: 특이사항 없음`);
  }
}

// ══════════════════════════════════════════════════════════════
// ② 월간 스냅샷 자동 저장 (매월 1일 실행)
//    → 📅 특정일잔고 시트에 자동 추가
// ══════════════════════════════════════════════════════════════
function saveMonthlySnapshot() {
  const ss        = SpreadsheetApp.getActiveSpreadsheet();
  const srcSheet  = ss.getSheetByName(TARGET_SHEET_NAME);
  const destSheet = ss.getSheetByName("📅 특정일잔고");
  if (!srcSheet || !destSheet) { Logger.log("시트 없음"); return; }

  const today    = Utilities.formatDate(new Date(), "Asia/Seoul", "yyyy-MM-dd");
  const lastRow  = srcSheet.getLastRow();

  for (let row = DATA_START_ROW; row <= lastRow; row++) {
    const code   = srcSheet.getRange(row, CODE_COL).getValue();
    const name   = srcSheet.getRange(row, NAME_COL).getValue();
    const cur    = srcSheet.getRange(row, 4).getValue();   // D: 통화
    const sector = srcSheet.getRange(row, 5).getValue();   // E: 섹터
    const qty    = srcSheet.getRange(row, 6).getValue();   // F: 수량
    const price  = srcSheet.getRange(row, 8).getValue();   // H: 현재가(원화)
    const eval_  = srcSheet.getRange(row, 10).getValue();  // J: 평가금액
    const weight = srcSheet.getRange(row, 14).getValue();  // N: 비중

    if (!code) continue;

    const newRow = destSheet.getLastRow() + 1;
    destSheet.getRange(newRow, 1, 1, 9).setValues([[
      today, code, name, cur, qty, price, eval_,
      weight ? (weight * 100).toFixed(1) + "%" : "",
      "월간 자동 스냅샷"
    ]]);
  }
  Logger.log(`${today} 스냅샷 저장 완료`);
}

// ══════════════════════════════════════════════════════════════
// ③ 날짜별 포트폴리오 복원 (매매일지 SUMIF 방식)
//    → '📅 특정일잔고' 시트의 B1 셀 날짜 기준으로 재계산
//    → 수동 실행 or 버튼 연결
// ══════════════════════════════════════════════════════════════
function reconstructPortfolioByDate() {
  const ss         = SpreadsheetApp.getActiveSpreadsheet();
  const tradeSheet = ss.getSheetByName("📒 매매일지");
  const destSheet  = ss.getSheetByName("📅 특정일잔고");
  if (!tradeSheet || !destSheet) { Logger.log("시트 없음"); return; }

  // B1 셀에서 조회 날짜 읽기
  const queryDate = destSheet.getRange("B1").getValue();
  if (!queryDate) {
    SpreadsheetApp.getUi().alert("B1 셀에 조회 날짜를 입력해주세요. (형식: 2025-03-01)");
    return;
  }

  const qDate = new Date(queryDate);
  const trades = tradeSheet.getDataRange().getValues();
  const headers = trades[0];
  const dateIdx  = 0;  // A: 거래일
  const codeIdx  = 1;  // B: 코드
  const nameIdx  = 2;  // C: 종목명
  const typeIdx  = 3;  // D: 구분
  const qtyIdx   = 4;  // E: 수량
  const priceIdx = 8;  // I: 매입가(원화)
  const amtIdx   = 10; // K: 원화환산금액

  // 해당 날짜 이전 거래 집계
  const holdings = {};
  for (let i = 1; i < trades.length; i++) {
    const row = trades[i];
    const tradeDate = new Date(row[dateIdx]);
    if (!row[dateIdx] || tradeDate > qDate) continue;

    const code = row[codeIdx];
    const name = row[nameIdx];
    const type = row[typeIdx];
    const qty  = parseFloat(row[qtyIdx]) || 0;
    const amt  = parseFloat(row[amtIdx]) || 0;

    if (!holdings[code]) holdings[code] = {name, qty:0, totalAmt:0};
    if (type === "매수") {
      holdings[code].qty      += qty;
      holdings[code].totalAmt += amt;
    } else if (type === "매도") {
      holdings[code].qty      -= qty;
      // 매도 시 평균단가 비례로 매입금액 차감
      const avgBefore = holdings[code].qty > 0
        ? holdings[code].totalAmt / (holdings[code].qty + qty) : 0;
      holdings[code].totalAmt -= avgBefore * qty;
    }
  }

  // 결과 작성
  const resultStartRow = 4;
  destSheet.getRange(resultStartRow, 1, 50, 8).clearContent();
  destSheet.getRange("A2").setValue(`▶ 조회 기준일: ${Utilities.formatDate(qDate,"Asia/Seoul","yyyy-MM-dd")}`);
  destSheet.getRange(resultStartRow - 1, 1, 1, 8).setValues([
    ["코드","종목명","보유수량","평균단가(원)","평가금액(원화현재가기준)","비중","매입금액","메모"]
  ]);

  let totalAmt = 0;
  const rows = [];
  for (const [code, h] of Object.entries(holdings)) {
    if (h.qty <= 0) continue;
    const avg = h.qty > 0 ? h.totalAmt / h.qty : 0;
    rows.push([code, h.name, h.qty, Math.round(avg), "", "", Math.round(h.totalAmt), "SUMIF 복원"]);
    totalAmt += h.totalAmt;
  }
  if (rows.length > 0) {
    destSheet.getRange(resultStartRow, 1, rows.length, 8).setValues(rows);
  }

  SpreadsheetApp.getUi().alert(
    `${Utilities.formatDate(qDate,"Asia/Seoul","yyyy-MM-dd")} 기준\n` +
    `보유종목 ${rows.length}개 복원 완료\n` +
    `평가금액(매입가 기준): ${Math.round(totalAmt).toLocaleString()}원`
  );
}

// ══════════════════════════════════════════════════════════════
// ④ 메뉴 등록 (스프레드시트 열릴 때 자동 실행)
// ══════════════════════════════════════════════════════════════
function onOpen() {
  SpreadsheetApp.getUi()
    .createMenu("📈 포트폴리오")
    .addItem("🔔 지금 알림 체크", "checkTargetPrice")
    .addSeparator()
    .addItem("📸 이달 스냅샷 저장", "saveMonthlySnapshot")
    .addItem("📅 날짜별 잔고 복원", "reconstructPortfolioByDate")
    .addSeparator()
    .addItem("ℹ️ 사용 안내", "showHelp")
    .addToUi();
}

function showHelp() {
  SpreadsheetApp.getUi().alert(
    "📈 포트폴리오 자동화 안내\n\n" +
    "🔔 알림 체크: 매일 오전 9시 자동 실행 (트리거 설정 필요)\n" +
    "   - 목표가 90% 도달 시 이메일 알림\n" +
    "   - 수익률 +30% 이상 차익실현 알림\n" +
    "   - 손실 -15% 이하 하방 검토 알림\n" +
    "   - 비중 초과 리밸런싱 알림\n\n" +
    "📸 스냅샷: 매월 1일 자동 실행 (트리거 설정 필요)\n\n" +
    "📅 날짜별 복원: '📅 특정일잔고' 시트 B1에 날짜 입력 후 실행\n\n" +
    "⚙️ 트리거 설정: Apps Script → 시계 아이콘 → 트리거 추가\n" +
    "   checkTargetPrice: 시간 기반 → 하루 → 오전 8~9시\n" +
    "   saveMonthlySnapshot: 시간 기반 → 월 → 1일"
  );
}

/**
 * ══════════════════════════════════════════════════════════════
 * 트리거 설정 요약
 * ══════════════════════════════════════════════════════════════
 * 1. Apps Script 편집기 좌측 시계(⏰) 아이콘 클릭
 * 2. "+ 트리거 추가" 클릭
 *
 * [checkTargetPrice — 매일 알림]
 *   함수: checkTargetPrice
 *   이벤트 소스: 시간 기반
 *   시간 유형: 하루 타이머
 *   시간: 오전 8시 ~ 9시
 *
 * [saveMonthlySnapshot — 월간 스냅샷]
 *   함수: saveMonthlySnapshot
 *   이벤트 소스: 시간 기반
 *   시간 유형: 월 타이머
 *   날짜: 매월 1일
 */
