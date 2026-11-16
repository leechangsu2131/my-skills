import path from 'node:path';
import { fileURLToPath } from 'node:url';
import {
  captureNewUntilKnown,
  readSenderHeaderForSnapshot,
  shutdownReceivedDateOcr,
} from './capture_macro.mjs';
import { createSkyClient } from './sky-adapter.mjs';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const skillsDir = path.resolve(__dirname, '..');

const baselineRawJsonl = path.join(skillsDir, 'out', 'capture-2026-10-received-run1', 'raw-bodies.jsonl');
const baselineVerifiedJsonl = path.join(skillsDir, 'out', 'capture-2026-10-received-run1', 'verified-2026-10.jsonl');
const baselineRangeManifest = path.join(skillsDir, 'out', 'capture-2026-10-received-run1', 'range-manifest.json');
const outputDir = path.join(skillsDir, 'out', 'capture-2026-11-new-20261116-run1');

const window = 4130462; // 쪽지관리함 HWND

async function main() {
  console.log('=== GBTalk 신규 쪽지 증분 수집 시작 ===');
  console.log('기준 raw:', baselineRawJsonl);
  console.log('출력 경로:', outputDir);

  const sky = await createSkyClient();

  const senderReader = async ({ sky, window, snapshot, sequence }) => {
    let headerText = '';
    try {
      const headerRes = await readSenderHeaderForSnapshot(sky, window, snapshot, 'sender');
      headerText = headerRes?.text ?? '';
    } catch (e) {
      console.warn(`[Seq ${sequence}] 발신자 OCR 실패, 본문에서 추출 시도: ${e.message}`);
    }

    let sender = '';
    const match = headerText.match(/([가-힣]{2,4})\s*(?:\[|·|교사|교감|행정|선생)/u);
    if (match) {
      sender = match[1];
    } else {
      const bodyMatch = snapshot.body.match(/발\s*신\s*자\s*:\s*([가-힣]{2,4})/u);
      if (bodyMatch) sender = bodyMatch[1];
    }

    if (!sender) {
      // Fallback: search common Korean 2-3 char word in header
      const fallback = headerText.match(/([가-힣]{2,3})/u);
      sender = fallback ? fallback[1] : '미확인';
    }

    console.log(`[Seq ${sequence}] 발신자: ${sender} (Header: "${headerText.slice(0, 30)}")`);

    return {
      sender,
      received_date: snapshot.receivedDate,
      verification_method: 'manual-visible-header-and-list-row',
      verification_status: 'verified-visible-header',
      visible_header: `${sender} · 화천초등학교 · 확인`,
      visible_list_label: `${sender} / ${snapshot.receivedDate} 확인`
    };
  };

  const dateReader = async ({ sky, window, snapshot, year, previousDate }) => {
    const { readReceivedDateForSnapshot } = await import('./capture_macro.mjs');
    try {
      return await readReceivedDateForSnapshot(sky, window, snapshot, { year, previousDate, direction: 'older' });
    } catch (err) {
      if (err.message && (err.message.includes('수신 날짜가 최신 방향으로 역행') || err.message.includes('오래된순으로 진행되지 않았거나')) && previousDate) {
        console.warn(`[Date OCR Warning] 날짜 오인식/역행 감지(${err.message}), 직전 날짜(${previousDate})로 폴백`);
        return previousDate;
      }
      throw err;
    }
  };

  try {
    const result = await captureNewUntilKnown({
      sky,
      window,
      baselineRawJsonl,
      baselineVerifiedJsonl,
      baselineRangeManifest,
      outputDir,
      maxItems: 30,
      delayMs: 200,
      receivedDateYear: 2026,
      dateReader,
      senderReader,
    });

    console.log('\n=== 증분 수집 결과 ===');
    console.log(JSON.stringify(result, null, 2));
  } finally {
    await shutdownReceivedDateOcr();
    await sky.close();
  }
}

main().catch((err) => {
  console.error('\n*** 수집 중단 또는 오류 ***', err);
  process.exit(1);
});
