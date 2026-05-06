/**
 * 4_apps_script.js  ★ 병합 최종버전
 * ─────────────────────────────────────────────────────────────
 * 출처: portfolio_gsheet_v2 (다른 LLM) + 투자관리시스템 (Claude)
 * 병합 추가 기능:
 *   ① checkTargetPrice()         — 목표가·손익 알림 (매일 09시)
 *   ② saveMonthlySnapshot()      — 월간 자동 스냅샷 (매월 1일)
 *   ③ reconstructPortfolioByDate()— 날짜별 잔고 SUMIF 복원 (수동)
 *   ④ syncSectorSummary()        ★NEW — 섹터현황 자동 집계 (매일 09시)
 *   ⑤ weeklyReviewReminder()     ★NEW — 주간 복기 알림 (매주 월요일)
 *   ⑥ onOpen()                   — 커스텀 메뉴 자동 등록
 *
 * 설치:
 *   Google Sheets → 확장 프로그램 → Apps Script
 *   → 전체 붙여넣기 → 저장 → 트리거 설정
 * ─────────────────────────────────────────────────────────────
 */

// ══════════════════════════════════════════════════════════════
// ⚙️  설정 (여기만 수정)
// ══════════════════════════════════════════════════════════════
const MY_EMAIL            = "your-email@gmail.com";   // ← 본인 이메일
const REALTIME_SHEET      = "📈 실시간현황";
const TRADE_SHEET         = "📒 매매일지";
const SNAPSHOT_SHEET      = "📅 특정일잔고";
const SECTOR_SHEET        = "🏭 섹터현황";
const REVIEW_SHEET        = "📝 복기노트";

// 실시간현황 컬럼 인덱스 (1-based)
const COL_CODE     = 2;   // B: 코드
const COL_NAME     = 3;   // C: 종목명
const COL_CUR      = 4;   // D: 통화
const COL_SECTOR   = 5;   // E: 섹터
const COL_QTY      = 6;   // F: 수량
const COL_PRICE_L  = 7;   // G: 현재가(현지)
const COL_PRICE_KRW= 8;   // H: 현재가(원화)
const COL_AVG      = 9;   // I: 매입가(원화)
const COL_EVAL     = 10;  // J: 평가금액
const COL_BUY      = 11;  // K: 매입금액
const COL_PNL      = 12;  // L: 평가손익
const COL_RET      = 13;  // M: 수익률
const COL_WEIGHT   = 14;  // N: 현재비중
const COL_TGT_W    = 15;  // O: 목표비중
const COL_TGT_P    = 16;  // P: 목표가
const COL_SIGNAL   = 17;  // Q: 매매신호
const DATA_START   = 4;   // 데이터 시작 행

// 알림 임계값
const ALERT_TARGET_PCT   = 0.90;  // 목표가의 90% 이상이면 알림
const ALERT_PROFIT_PCT   = 0.30;  // 수익 +30% 이상
const ALERT_LOSS_PCT     = -0.15; // 손실 -15% 이하
const ALERT_WEIGHT_OVER  = 0.05;  // 목표비중 초과 5%p 이상

// ══════════════════════════════════════════════════════════════
// ① 목표가·손익 알림 (매일 오전 9시)
// ══════════════════════════════════════════════════════════════
function checkTargetPrice() {
  const ss    = SpreadsheetApp.getActiveSpreadsheet();
  const sheet = ss.getSheetByName(REALTIME_SHEET);
  if (!sheet) { Logger.log("시트 없음: " + REALTIME_SHEET); return; }

  const lastRow = sheet.getLastRow();
  const alerts  = { target: [], profit: [], loss: [], weight: [] };
  const today   = _today();

  for (let r = DATA_START; r <= lastRow; r++) {
    const code   = sheet.getRange(r, COL_CODE).getValue();
    const name   = sheet.getRange(r, COL_NAME).getValue();
    const price  = sheet.getRange(r, COL_PRICE_L).getValue();
    const target = sheet.getRange(r, COL_TGT_P).getValue();
    const ret    = sheet.getRange(r, COL_RET).getValue();
    const wt     = sheet.getRange(r, COL_WEIGHT).getValue();
    const tgtWt  = sheet.getRange(r, COL_TGT_W).getValue();
    if (!code || !name) continue;

    // 🎯 목표가 근접
    if (target && price && price >= target * ALERT_TARGET_PCT) {
      const pct = (price / target * 100).toFixed(1);
      alerts.target.push(
        `🎯 [목표가 근접] ${name}(${code})\n` +
        `   현재가 ${_fmt(price)} → 목표가 ${_fmt(target)}의 ${pct}%\n` +
        `   → 분할매도 또는 목표가 재검토 시점`
      );
    }
    // 💰 차익실현 검토
    if (ret && ret >= ALERT_PROFIT_PCT) {
      alerts.profit.push(
        `💰 [차익실현 검토] ${name}(${code})  +${(ret*100).toFixed(1)}%\n` +
        `   → 목표 비중 대비 현황 점검 권장`
      );
    }
    // 🚨 하방 도달
    if (ret && ret <= ALERT_LOSS_PCT) {
      alerts.loss.push(
        `🚨 [하방 검토] ${name}(${code})  ${(ret*100).toFixed(1)}%\n` +
        `   → 투자 근거 재확인 필요. 손절 vs 추가매수 판단`
      );
    }
    // ⚖️ 비중 초과
    if (wt && tgtWt && (wt - tgtWt) >= ALERT_WEIGHT_OVER) {
      alerts.weight.push(
        `⚖️ [비중 초과] ${name}(${code})\n` +
        `   현재 ${(wt*100).toFixed(1)}% vs 목표 ${(tgtWt*100).toFixed(1)}%\n` +
        `   → 일부 매도 또는 다른 종목 매수로 리밸런싱`
      );
    }
  }

  const all = [...alerts.target, ...alerts.profit, ...alerts.loss, ...alerts.weight];
  if (all.length > 0) {
    const subject = `[포트폴리오 알림] ${today} — 신호 ${all.length}건`;
    const body =
      `안녕하세요,\n\n${today} 포트폴리오 점검 결과입니다.\n\n` +
      all.join("\n\n─────────────────\n\n") +
      `\n\n📊 시트 바로가기:\n${ss.getUrl()}\n\n` +
      `🔎 알림 기준:\n` +
      `  목표가 ${ALERT_TARGET_PCT*100}% 이상, ` +
      `수익 +${ALERT_PROFIT_PCT*100}%, ` +
      `손실 ${ALERT_LOSS_PCT*100}%, ` +
      `비중 초과 ${ALERT_WEIGHT_OVER*100}%p`;
    GmailApp.sendEmail(MY_EMAIL, subject, body);
    Logger.log(`알림 발송 완료: ${all.length}건`);
  } else {
    Logger.log(`${today}: 특이사항 없음`);
  }
}

// ══════════════════════════════════════════════════════════════
// ② 월간 스냅샷 자동 저장 (매월 1일)
// ══════════════════════════════════════════════════════════════
function saveMonthlySnapshot() {
  const ss        = SpreadsheetApp.getActiveSpreadsheet();
  const srcSheet  = ss.getSheetByName(REALTIME_SHEET);
  const destSheet = ss.getSheetByName(SNAPSHOT_SHEET);
  if (!srcSheet || !destSheet) { Logger.log("시트 없음"); return; }

  const today   = _today();
  const lastRow = srcSheet.getLastRow();
  const newRows = [];

  for (let r = DATA_START; r <= lastRow; r++) {
    const code   = srcSheet.getRange(r, COL_CODE).getValue();
    const name   = srcSheet.getRange(r, COL_NAME).getValue();
    const cur    = srcSheet.getRange(r, COL_CUR).getValue();
    const qty    = srcSheet.getRange(r, COL_QTY).getValue();
    const priceK = srcSheet.getRange(r, COL_PRICE_KRW).getValue();
    const eval_  = srcSheet.getRange(r, COL_EVAL).getValue();
    const wt     = srcSheet.getRange(r, COL_WEIGHT).getValue();
    if (!code || !qty) continue;

    newRows.push([
      today, code, name, cur, qty,
      Math.round(priceK), Math.round(eval_),
      wt ? (wt * 100).toFixed(2) + "%" : "",
      "월간 자동 스냅샷"
    ]);
  }

  if (newRows.length > 0) {
    const startRow = destSheet.getLastRow() + 1;
    destSheet.getRange(startRow, 1, newRows.length, 9).setValues(newRows);
    Logger.log(`${today} 스냅샷 ${newRows.length}건 저장 완료`);

    // 이메일 요약 발송 (선택)
    const totalEval = newRows.reduce((s, r) => s + (r[6] || 0), 0);
    GmailApp.sendEmail(
      MY_EMAIL,
      `[포트폴리오] ${today} 월간 스냅샷 저장 완료`,
      `${today} 기준 월간 스냅샷이 자동 저장되었습니다.\n\n` +
      `보유 종목 수: ${newRows.length}개\n` +
      `총 평가금액: ${_fmt(totalEval)}원\n\n` +
      ss.getUrl()
    );
  }
}

// ══════════════════════════════════════════════════════════════
// ③ 날짜별 포트폴리오 복원 (매매일지 SUMIF 방식)  ★ 핵심
//    → '📅 특정일잔고' 시트 B1에 날짜 입력 후 메뉴에서 실행
// ══════════════════════════════════════════════════════════════
function reconstructPortfolioByDate() {
  const ss         = SpreadsheetApp.getActiveSpreadsheet();
  const tradeSheet = ss.getSheetByName(TRADE_SHEET);
  const destSheet  = ss.getSheetByName(SNAPSHOT_SHEET);
  if (!tradeSheet || !destSheet) { Logger.log("시트 없음"); return; }

  const queryDate = destSheet.getRange("B1").getValue();
  if (!queryDate) {
    SpreadsheetApp.getUi().alert("B1 셀에 조회 날짜를 입력해주세요.\n예) 2025-03-01");
    return;
  }
  const qDate = new Date(queryDate);

  const trades  = tradeSheet.getDataRange().getValues();
  const holdings = {};

  for (let i = 1; i < trades.length; i++) {
    const row       = trades[i];
    const tradeDate = new Date(row[0]);  // A: 거래일
    if (!row[0] || tradeDate > qDate) continue;

    const code  = row[1];   // B: 티커
    const name  = row[2];   // C: 종목명
    const type  = row[3];   // D: 구분
    const qty   = parseFloat(row[4]) || 0;   // E: 수량
    const amt   = parseFloat(row[6]) || 0;   // G: 금액(원)

    if (!code) continue;
    if (!holdings[code]) holdings[code] = { name, qty: 0, totalAmt: 0 };

    if (type === "매수") {
      holdings[code].qty      += qty;
      holdings[code].totalAmt += amt;
    } else if (type === "매도") {
      // 총평균법: 매도 비중만큼 매입금액 차감
      const totalQtyBefore = holdings[code].qty;
      if (totalQtyBefore > 0) {
        const ratio = qty / totalQtyBefore;
        holdings[code].totalAmt -= holdings[code].totalAmt * ratio;
      }
      holdings[code].qty -= qty;
    }
  }

  // 결과 작성 (행 4부터)
  const RESULT_START = 4;
  destSheet.getRange(RESULT_START - 1, 1, 50, 8).clearContent();
  destSheet.getRange("A2").setValue(
    `▶ 복원 기준일: ${Utilities.formatDate(qDate, "Asia/Seoul", "yyyy-MM-dd")} (매매일지 SUMIF)`
  );
  destSheet.getRange(RESULT_START - 1, 1, 1, 8).setValues([[
    "코드","종목명","보유수량","평균단가(원)","평가금액(매입가기준)","비중(매입가기준)","매입금액","비고"
  ]]);

  let totalAmt = 0;
  const rows = [];
  for (const [code, h] of Object.entries(holdings)) {
    if (h.qty <= 0.0001) continue;
    const avg = h.qty > 0 ? h.totalAmt / h.qty : 0;
    rows.push([
      code, h.name, h.qty, Math.round(avg),
      "", "",              // 평가금액/비중은 현재가 없으므로 공란
      Math.round(h.totalAmt), "SUMIF 자동 복원"
    ]);
    totalAmt += h.totalAmt;
  }

  // 비중 계산
  rows.forEach(r => { r[5] = totalAmt > 0 ? (r[6] / totalAmt * 100).toFixed(1) + "%" : ""; });

  if (rows.length > 0) {
    destSheet.getRange(RESULT_START, 1, rows.length, 8).setValues(rows);
  }

  SpreadsheetApp.getUi().alert(
    `복원 완료 ✅\n` +
    `기준일: ${Utilities.formatDate(qDate, "Asia/Seoul", "yyyy-MM-dd")}\n` +
    `보유 종목: ${rows.length}개\n` +
    `매입금액 합계: ${_fmt(Math.round(totalAmt))}원`
  );
}

// ══════════════════════════════════════════════════════════════
// ④ 섹터현황 자동 집계 ★NEW (매일 또는 수동)
//    → 실시간현황 시트의 섹터 컬럼을 읽어서 섹터현황에 집계
// ══════════════════════════════════════════════════════════════
function syncSectorSummary() {
  const ss         = SpreadsheetApp.getActiveSpreadsheet();
  const srcSheet   = ss.getSheetByName(REALTIME_SHEET);
  const secSheet   = ss.getSheetByName(SECTOR_SHEET);
  if (!srcSheet || !secSheet) { Logger.log("시트 없음"); return; }

  const lastRow  = srcSheet.getLastRow();
  const sectorMap = {};  // { 섹터명: { evalAmt, buyAmt, count } }
  let totalEval  = 0;

  for (let r = DATA_START; r <= lastRow; r++) {
    const code   = srcSheet.getRange(r, COL_CODE).getValue();
    const sector = srcSheet.getRange(r, COL_SECTOR).getValue();
    const eval_  = srcSheet.getRange(r, COL_EVAL).getValue();
    const buy    = srcSheet.getRange(r, COL_BUY).getValue();
    if (!code || !sector) continue;

    if (!sectorMap[sector]) sectorMap[sector] = { evalAmt: 0, buyAmt: 0, count: 0 };
    sectorMap[sector].evalAmt += eval_ || 0;
    sectorMap[sector].buyAmt  += buy || 0;
    sectorMap[sector].count   += 1;
    totalEval += eval_ || 0;
  }

  // 섹터현황 시트 업데이트 (2행부터 — 1행은 헤더)
  const secData = secSheet.getDataRange().getValues();
  const updates = [];
  for (let i = 1; i < secData.length; i++) {
    const secName = secData[i][0];
    if (!secName || !sectorMap[secName]) continue;
    const s = sectorMap[secName];
    const pnl  = s.evalAmt - s.buyAmt;
    const ret  = s.buyAmt > 0 ? pnl / s.buyAmt : 0;
    const wt   = totalEval > 0 ? s.evalAmt / totalEval : 0;
    // B:종목수, C:평가금액, D:매입금액, E:손익, F:수익률%, G:비중%
    secSheet.getRange(i + 1, 2, 1, 6).setValues([[
      s.count,
      Math.round(s.evalAmt),
      Math.round(s.buyAmt),
      Math.round(pnl),
      (ret * 100).toFixed(2) + "%",
      (wt * 100).toFixed(2) + "%"
    ]]);
  }
  Logger.log(`섹터현황 업데이트 완료: ${Object.keys(sectorMap).length}개 섹터`);
}

// ══════════════════════════════════════════════════════════════
// ⑤ 주간 복기 알림 ★NEW (매주 월요일 오전)
// ══════════════════════════════════════════════════════════════
function weeklyReviewReminder() {
  const ss    = SpreadsheetApp.getActiveSpreadsheet();
  const today = _today();

  // 지난 7일간 매매일지 건수 카운트
  const tradeSheet = ss.getSheetByName(TRADE_SHEET);
  let recentTrades = 0;
  if (tradeSheet) {
    const trades   = tradeSheet.getDataRange().getValues();
    const cutoff   = new Date(); cutoff.setDate(cutoff.getDate() - 7);
    for (let i = 1; i < trades.length; i++) {
      const d = new Date(trades[i][0]);
      if (d >= cutoff) recentTrades++;
    }
  }

  GmailApp.sendEmail(
    MY_EMAIL,
    `[주간 복기] ${today} — 이번 주 포트폴리오 점검`,
    `안녕하세요! 매주 월요일 주간 복기 알림입니다.\n\n` +
    `📋 지난 7일 매매 건수: ${recentTrades}건\n\n` +
    `✅ 이번 주 점검 항목:\n` +
    `  □ 지난 주 매매 결과 복기 (만족도, 인지오류)\n` +
    `  □ 섹터별 비중 점검 (목표 대비 ±5%p 이내?)\n` +
    `  □ 이번 주 주요 이벤트 확인 (실적발표, 연준 회의 등)\n` +
    `  □ 관심 종목 목표가/하방 업데이트\n` +
    `  □ 전략·전망 시트 가설 검증\n\n` +
    `📊 포트폴리오 시트: ${ss.getUrl()}\n\n` +
    `좋은 한 주 되세요! 💪`
  );
  Logger.log(`주간 복기 알림 발송: ${today}`);
}

// ══════════════════════════════════════════════════════════════
// ⑥ 커스텀 메뉴 (스프레드시트 열릴 때 자동 등록)
// ══════════════════════════════════════════════════════════════
function onOpen() {
  SpreadsheetApp.getUi()
    .createMenu("📈 포트폴리오")
    .addItem("🔔 지금 알림 체크", "checkTargetPrice")
    .addSeparator()
    .addItem("📸 이달 스냅샷 저장", "saveMonthlySnapshot")
    .addItem("📅 날짜별 잔고 복원", "reconstructPortfolioByDate")
    .addSeparator()
    .addItem("🏭 섹터현황 동기화", "syncSectorSummary")
    .addItem("📬 주간 복기 알림 (수동)", "weeklyReviewReminder")
    .addSeparator()
    .addItem("ℹ️ 사용 안내", "showHelp")
    .addToUi();
}

function showHelp() {
  SpreadsheetApp.getUi().alert(
    "📈 포트폴리오 자동화 안내\n\n" +
    "🔔 알림 체크: 매일 오전 9시 자동 실행\n" +
    "   ▸ 목표가 90% 이상 도달\n" +
    "   ▸ 수익률 +30% 이상 (차익실현 검토)\n" +
    "   ▸ 손실 -15% 이하 (하방 검토)\n" +
    "   ▸ 목표비중 대비 +5%p 초과 (리밸런싱)\n\n" +
    "📸 스냅샷: 매월 1일 자동 실행\n\n" +
    "📅 날짜별 복원: 특정일잔고 시트 B1에 날짜 입력 후 실행\n" +
    "   ▸ 매매일지를 SUMIF로 역산하여 그날 잔고 자동 복원\n\n" +
    "🏭 섹터현황 동기화: 실시간현황 → 섹터현황 자동 집계\n\n" +
    "📬 주간 복기 알림: 매주 월요일 오전 자동 발송\n\n" +
    "⚙️ 트리거 설정: Apps Script → ⏰ 아이콘\n" +
    "   checkTargetPrice   → 하루 타이머 → 오전 8~9시\n" +
    "   saveMonthlySnapshot → 월 타이머 → 매월 1일\n" +
    "   weeklyReviewReminder → 주 타이머 → 매주 월요일"
  );
}

// ══════════════════════════════════════════════════════════════
// 유틸리티
// ══════════════════════════════════════════════════════════════
function _today() {
  return Utilities.formatDate(new Date(), "Asia/Seoul", "yyyy-MM-dd");
}
function _fmt(n) {
  return Math.round(n).toLocaleString();
}

/**
 * ══════════════════════════════════════════════════════════════
 * 트리거 설정 요약
 * ══════════════════════════════════════════════════════════════
 * Apps Script → 좌측 ⏰ → + 트리거 추가
 *
 * [1] checkTargetPrice     → 하루 타이머  → 오전 8~9시
 * [2] saveMonthlySnapshot  → 월 타이머    → 매월 1일
 * [3] weeklyReviewReminder → 주 타이머    → 매주 월요일
 * [4] syncSectorSummary    → 하루 타이머  → 오전 9~10시 (선택)
 */
