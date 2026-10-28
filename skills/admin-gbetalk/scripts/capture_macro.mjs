// Keyboard-driven, resumable raw-body capture for the GBTalk Message Manager.
// It stages message text and row fingerprints only; it never sends, replies, or deletes.

import fs from 'node:fs/promises';
import path from 'node:path';
import crypto from 'node:crypto';
import os from 'node:os';
import { spawn } from 'node:child_process';
import readline from 'node:readline';
import { fileURLToPath } from 'node:url';

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
const sha256 = (value) => crypto.createHash('sha256').update(value).digest('hex');
const receivedDateOcrScript = fileURLToPath(new URL('./read_received_date.ps1', import.meta.url));
let receivedDateOcrWorker = null;

function createReceivedDateOcrWorker() {
  const child = spawn('powershell.exe', [
    '-NoLogo', '-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass',
    '-File', receivedDateOcrScript,
  ], { windowsHide: true, stdio: ['pipe', 'pipe', 'pipe'] });
  const lines = readline.createInterface({ input: child.stdout, crlfDelay: Infinity });
  const pending = new Map();
  let nextRequestId = 0;
  let stderr = '';
  const worker = { child, pending, closed: false, idleTimer: null };

  const failPending = (error) => {
    for (const request of pending.values()) request.reject(error);
    pending.clear();
  };
  lines.on('line', (line) => {
    let response;
    try { response = JSON.parse(line); }
    catch { failPending(new Error(`날짜 OCR 응답을 해석하지 못했습니다: ${line.slice(0, 300)}`)); return; }
    const request = pending.get(response.id);
    if (!request) return;
    pending.delete(response.id);
    if (response.ok && typeof response.text === 'string') request.resolve(response.text);
    else request.reject(new Error(`Windows 날짜 OCR 실패: ${response.error ?? '알 수 없는 오류'}`));
  });
  child.stderr.on('data', (chunk) => { stderr = `${stderr}${chunk.toString('utf8')}`.slice(-2000); });
  child.on('error', (error) => {
    worker.closed = true;
    failPending(new Error(`Windows 날짜 OCR 프로세스를 시작하지 못했습니다: ${error.message}`));
    if (receivedDateOcrWorker === worker) receivedDateOcrWorker = null;
  });
  child.on('close', (code, signal) => {
    worker.closed = true;
    clearTimeout(worker.idleTimer);
    failPending(new Error(`Windows 날짜 OCR 프로세스가 종료됐습니다 (${code ?? signal ?? 'unknown'}). ${stderr}`));
    if (receivedDateOcrWorker === worker) receivedDateOcrWorker = null;
  });

  worker.recognize = (imagePath, op = 'date') => new Promise((resolve, reject) => {
    if (worker.closed || child.stdin.destroyed) { reject(new Error('Windows 날짜 OCR 프로세스가 닫혀 있습니다.')); return; }
    const id = ++nextRequestId;
    pending.set(id, { resolve, reject });
    child.stdin.write(`${JSON.stringify({ id, path: imagePath, op })}\n`, (error) => {
      if (!error) return;
      pending.delete(id);
      reject(new Error(`날짜 OCR 요청을 전달하지 못했습니다: ${error.message}`));
    });
    clearTimeout(worker.idleTimer);
    worker.idleTimer = setTimeout(() => { void closeReceivedDateOcrWorker(worker); }, 30000);
    worker.idleTimer.unref?.();
  });
  return worker;
}

async function closeReceivedDateOcrWorker(worker = receivedDateOcrWorker) {
  if (!worker || worker.closed) return;
  clearTimeout(worker.idleTimer);
  await new Promise((resolve) => {
    const timeout = setTimeout(() => worker.child.kill(), 3000);
    worker.child.once('close', () => { clearTimeout(timeout); resolve(); });
    worker.child.stdin.write(`${JSON.stringify({ op: 'stop' })}\n`, (error) => {
      if (error) worker.child.kill();
    });
  });
}

export async function shutdownReceivedDateOcr() {
  await closeReceivedDateOcrWorker();
}

function getReceivedDateOcrWorker() {
  if (!receivedDateOcrWorker || receivedDateOcrWorker.closed) {
    receivedDateOcrWorker = createReceivedDateOcrWorker();
  }
  return receivedDateOcrWorker;
}

export function parseReceivedDateFromOcr(text, { year, previousDate = null, monthCorrection = null, direction = 'older' } = {}) {
  const ocrText = String(text);
  const explicit = [...ocrText.matchAll(/(?<!\d)(20\d{2})\s*[./-]\s*(\d{1,2})\s*[./-]\s*(\d{1,2})(?!\d)/gu)]
    .map((match) => ({ year: Number(match[1]), month: Number(match[2]), day: Number(match[3]) }));
  const isAfterMeridiem = (match) => /(?:오전|오후)\s*$/u.test(ocrText.slice(0, match.index));
  const short = [...ocrText.matchAll(/(?<!\d)(\d{1,2})\s*[./-]\s*(\d{1,2})(?!\d)/gu)]
    .filter((match) => !isAfterMeridiem(match))
    .map((match) => ({ month: Number(match[1]), day: Number(match[2]) }));
  const compact = [...ocrText.matchAll(/(?<!\d)(0[1-9]|1[0-2])([0-3]\d)(?!\d)/gu)]
    // OCR can remove the colon from a header time such as "오전 09:12",
    // turning it into "오전 0912". Do not treat that HHMM token as MMDD.
    // It can also replace the colon with a dot, e.g. "오후 12.01".
    .filter((match) => !isAfterMeridiem(match))
    .map((match) => ({ month: Number(match[1]), day: Number(match[2]) }));
  const candidates = explicit.length ? explicit : short.length ? short : compact;
  const unique = new Map(candidates.map((item) => [`${item.year ?? ''}-${item.month}-${item.day}`, item]));
  if (unique.size === 0 && previousDate && /(?:오전|오후)/u.test(ocrText)) {
    const damagedDate = ocrText.match(/(?<!\d)(\d{1,2})[^\d\s./-]+(\d{1,2})(?!\d)/u);
    if (damagedDate) {
      const [, previousYear, previousMonth, previousDay] = previousDate.match(/^(\d{4})-(\d{2})-(\d{2})$/u) ?? [];
      const observedMonth = Number(damagedDate[1]);
      const observedDay = Number(damagedDate[2]);
      const expectedDay = Number(previousDay);
      // OCR sometimes replaces the date separator with a Korean glyph and
      // drops the tens digit from dates like 09.16. Reuse the prior date only
      // when the visible partial date still identifies its month/day suffix;
      // a different day fails closed and requires another inspection.
      if (
        previousYear
        && observedMonth === Number(previousMonth)
        && observedDay === (expectedDay >= 10 ? expectedDay % 10 : expectedDay)
      ) return previousDate;
    }
  }
  if (unique.size === 0 && /(?:오전|오후)\s*\d{1,2}\s*:?\s*\d{2}/u.test(ocrText)) {
    // GBTalk shows a time-only header for today's messages and a date for older
    // messages. Reuse the previous date within a date group; for the first row,
    // resolve today's date explicitly in the configured Korean local timezone.
    if (previousDate) return previousDate;
    const fields = Object.fromEntries(new Intl.DateTimeFormat('en-US', {
      timeZone: 'Asia/Seoul', year: 'numeric', month: '2-digit', day: '2-digit',
    }).formatToParts(new Date()).map(({ type, value }) => [type, value]));
    return isoDate(Number(fields.year), Number(fields.month), Number(fields.day));
  }
  if (unique.size !== 1) throw new Error(`날짜 OCR 결과가 없거나 여러 날짜로 모호합니다: ${ocrText.trim() || '(빈 결과)'}`);

  const candidate = [...unique.values()][0];
  if (!candidate.year && previousDate && monthCorrection) {
    const [, previousYear, previousMonth, previousDay] = previousDate.match(/^(\d{4})-(\d{2})-(\d{2})$/u) ?? [];
    const dayDistance = Number(previousDay) - candidate.day;
    if (
      previousYear === String(monthCorrection.year)
      && Number(previousMonth) === monthCorrection.month
      && candidate.month === monthCorrection.ocr_month
      && dayDistance >= 0
      && dayDistance <= (monthCorrection.max_day_distance ?? 7)
    ) candidate.month = monthCorrection.month;
  }
  let resolvedYear = candidate.year ?? year;
  if (!Number.isInteger(resolvedYear) || resolvedYear < 1900 || resolvedYear > 2100) {
    throw new Error('화면 날짜에 연도가 없어 사용할 기준 연도가 올바르지 않습니다.');
  }
  let receivedDate = isoDate(resolvedYear, candidate.month, candidate.day);
  if (!candidate.year && previousDate && direction === 'older' && receivedDate > previousDate) {
    const previous = new Date(`${previousDate}T00:00:00Z`);
    if (candidate.month > previous.getUTCMonth() + 1) {
      resolvedYear -= 1;
      receivedDate = isoDate(resolvedYear, candidate.month, candidate.day);
    }
  }
  if (!candidate.year && previousDate && direction === 'newer' && receivedDate < previousDate) {
    const previous = new Date(`${previousDate}T00:00:00Z`);
    if (candidate.month < previous.getUTCMonth() + 1) {
      resolvedYear += 1;
      receivedDate = isoDate(resolvedYear, candidate.month, candidate.day);
    }
  }
  if (previousDate && direction === 'older' && receivedDate > previousDate) {
    throw new Error(`목록이 오래된순으로 진행되지 않았거나 OCR 날짜가 바뀌었습니다: ${receivedDate} 다음 기준 ${previousDate}`);
  }
  if (previousDate && direction === 'newer' && receivedDate < previousDate) {
    throw new Error(`목록이 최신순으로 진행되지 않았거나 OCR 날짜가 바뀌었습니다: ${receivedDate} 이전 기준 ${previousDate}`);
  }
  return receivedDate;
}

function isoDate(year, month, day) {
  const value = `${String(year).padStart(4, '0')}-${String(month).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
  const parsed = new Date(`${value}T00:00:00Z`);
  if (Number.isNaN(parsed.valueOf()) || parsed.toISOString().slice(0, 10) !== value) {
    throw new Error(`화면에서 읽은 날짜가 달력상 유효하지 않습니다: ${value}`);
  }
  return value;
}

export async function readReceivedDateForSnapshot(sky, window, expected, { year, previousDate = null, monthCorrection = null, direction = 'older' } = {}) {
  let mismatch = null;
  for (let attempt = 0; attempt < 4; attempt += 1) {
    const state = await sky.get_window_state({ window, include_text: true, include_screenshot: true });
    let observed;
    try { observed = snapshotFromState(state); }
    catch (error) { mismatch = error; await sleep(100); continue; }
    if (!sameSnapshot(expected, observed)) {
      mismatch = new Error('날짜를 읽는 동안 선택 행 또는 본문이 바뀌었습니다.');
      await sleep(100);
      continue;
    }
    const accessibleDateText = receivedDateTextFromAccessibility(state);
    if (accessibleDateText) return parseReceivedDateFromOcr(accessibleDateText, { year, previousDate, monthCorrection, direction });

    const screenshot = [...(state.screenshots ?? [])]
      .filter((item) => typeof item.url === 'string' && item.url.startsWith('data:image/'))
      .sort((left, right) => ((right.width ?? 0) * (right.height ?? 0)) - ((left.width ?? 0) * (left.height ?? 0)))[0];
    if (!screenshot) throw new Error('날짜 인식에 사용할 전체 화면 스크린샷이 없습니다.');

    const tempDir = await fs.mkdtemp(path.join(os.tmpdir(), 'gbtalk-date-'));
    const imagePath = path.join(tempDir, 'selected-message.jpg');
    try {
      await fs.writeFile(imagePath, Buffer.from(screenshot.url.slice(screenshot.url.indexOf(',') + 1), 'base64'));
      const text = await getReceivedDateOcrWorker().recognize(imagePath);
      return parseReceivedDateFromOcr(text, { year, previousDate, monthCorrection, direction });
    } finally {
      await fs.rm(tempDir, { recursive: true, force: true });
    }
  }
  throw new Error(`날짜 판독 전에 선택 행/본문 일치를 확인하지 못했습니다: ${mismatch?.message ?? '알 수 없는 UI 불일치'}`);
}

export async function readSenderHeaderForSnapshot(sky, window, expected, op = 'sender') {
  if (!['sender', 'sender-row'].includes(op) && !/^sender-row-[2-8]$/u.test(op)) {
    throw new Error(`지원하지 않는 발신자 OCR 영역입니다: ${op}`);
  }
  let mismatch = null;
  for (let attempt = 0; attempt < 4; attempt += 1) {
    const state = await sky.get_window_state({ window, include_text: true, include_screenshot: true });
    let observed;
    try { observed = snapshotFromState(state); }
    catch (error) { mismatch = error; await sleep(100); continue; }
    if (!sameSnapshot(expected, observed)) {
      mismatch = new Error('발신자를 읽는 동안 선택 행 또는 본문이 바뀌었습니다.');
      await sleep(100);
      continue;
    }
    const screenshot = [...(state.screenshots ?? [])]
      .filter((item) => typeof item.url === 'string' && item.url.startsWith('data:image/'))
      .sort((left, right) => ((right.width ?? 0) * (right.height ?? 0)) - ((left.width ?? 0) * (left.height ?? 0)))[0];
    if (!screenshot) throw new Error('발신자를 읽을 전체 쪽지관리함 스크린샷이 없습니다.');

    const tempDir = await fs.mkdtemp(path.join(os.tmpdir(), 'gbtalk-sender-'));
    const imagePath = path.join(tempDir, 'selected-message.jpg');
    try {
      await fs.writeFile(imagePath, Buffer.from(screenshot.url.slice(screenshot.url.indexOf(',') + 1), 'base64'));
      const text = await getReceivedDateOcrWorker().recognize(imagePath, op);
      return {
        text: text.trim(),
        rowSha: observed.rowSha,
        bodySha: observed.bodySha,
        area: op,
        verificationStatus: 'unverified-ocr-candidate',
        requiresVisualReview: true,
      };
    } finally {
      await fs.rm(tempDir, { recursive: true, force: true });
    }
  }
  throw new Error(`발신자 판독 전에 선택 행/본문 일치를 확인하지 못했습니다: ${mismatch?.message ?? '알 수 없는 UI 불일치'}`);
}

export function createVerifiedSenderReader(records) {
  if (!Array.isArray(records)) throw new Error('검토된 발신자 매핑 records 배열이 필요합니다.');
  const bySequence = new Map();
  for (const record of records) {
    const sequence = record?.sequence;
    const sender = typeof record?.sender === 'string' ? record.sender.trim() : '';
    const hasVisibleEvidence = Boolean(
      (typeof record?.visible_header === 'string' && record.visible_header.trim())
      || (typeof record?.visible_list_label === 'string' && record.visible_list_label.trim())
    );
    if (
      !Number.isInteger(sequence)
      || sequence < 1
      || bySequence.has(sequence)
      || !/^[a-f0-9]{64}$/u.test(record?.row_sha256 ?? '')
      || !/^[a-f0-9]{64}$/u.test(record?.body_sha256 ?? '')
      || !sender
      || sender.length > 120
      || /[\r\n]/u.test(sender)
      || typeof record?.received_date !== 'string'
      || !/^\d{4}-\d{2}-\d{2}$/u.test(record.received_date)
      || isoDate(...record.received_date.split('-').map(Number)) !== record.received_date
      || typeof record?.verification_method !== 'string'
      || !record.verification_method.trim()
      || !(record.manually_verified === true || record.verification_status === 'verified-visible-header')
      || !hasVisibleEvidence
    ) throw new Error(`검토된 발신자 매핑 ${sequence ?? '(순번 없음)'}의 필수 근거가 빠졌거나 중복입니다.`);
    bySequence.set(sequence, record);
  }
  return async ({ sequence, snapshot }) => {
    const record = bySequence.get(sequence);
    if (!record) throw new Error(`순번 ${sequence}의 화면 검토 발신자 매핑이 없습니다.`);
    if (record.row_sha256 !== snapshot.rowSha || record.body_sha256 !== snapshot.bodySha) {
      throw new Error(`순번 ${sequence}의 화면 행/본문 지문이 발신자 매핑과 다릅니다.`);
    }
    if (record.received_date !== snapshot.receivedDate) {
      throw new Error(`순번 ${sequence}의 화면 날짜가 발신자 매핑과 다릅니다.`);
    }
    return { ...record, verification_status: 'verified-visible-header' };
  };
}

function receivedDateTextFromAccessibility(state) {
  const lines = (state?.accessibility?.tree ?? '').split(/\r?\n/);
  const listIndex = lines.findIndex((line) => /^\s*\d+ 창 UltariList\b/.test(line));
  const bodyIndex = lines.findIndex((line) => line.includes(' 편집 Value: '));
  const end = bodyIndex < 0 ? lines.length : bodyIndex;
  const candidateLines = [];
  let inList = false;
  let listIndent = -1;

  for (let index = 0; index < end; index += 1) {
    const line = lines[index];
    const indent = (line.match(/^\s*/) ?? [''])[0].length;
    if (index === listIndex) {
      inList = true;
      listIndent = indent;
      continue;
    }
    if (inList) {
      if (!line.trim() || indent > listIndent) continue;
      inList = false;
    }
    candidateLines.push(line);
  }

  const datePattern = /(?<!\d)(?:20\d{2}\s*[./-]\s*\d{1,2}\s*[./-]\s*\d{1,2}|\d{1,2}\s*[./-]\s*\d{1,2})(?!\d)/u;
  const matches = candidateLines.filter((line) => datePattern.test(line));
  return matches.length ? matches.join('\n') : null;
}

async function dateForRecord(sky, window, current, checkpoint, { year, reader, checkpointPath } = {}) {
  const previousDate = checkpoint.last_received_date ?? null;
  const inferredYear = year ?? Number(previousDate?.slice(0, 4) ?? new Date().getFullYear());
  try {
    const expectedSequence = checkpoint.next_row?.sequence ?? checkpoint.next_sequence;
    const matchingOverrides = (checkpoint.date_ocr_manual_overrides ?? []).filter((override) => (
      override.sequence === expectedSequence
      && override.row_sha256 === current.rowSha
      && override.body_sha256 === current.bodySha
    ));
    if (matchingOverrides.length > 1) {
      throw new Error('같은 쪽지에 적용되는 수동 날짜 확인이 여러 개 있어 저장하지 않고 멈춥니다.');
    }
    let receivedDate;
    if (matchingOverrides.length === 1) {
      const override = matchingOverrides[0];
      const observed = snapshotFromState(await latestState(sky, window));
      if (!sameSnapshot(current, observed)) {
        throw new Error('수동 날짜 확인을 적용하기 전에 선택 행 또는 본문이 바뀌었습니다.');
      }
      receivedDate = override.received_date;
      current.receivedDateEvidence = {
        method: override.verification_method ?? 'visible-manager-header',
        visible_header: override.visible_header ?? null,
        verified_at: override.verified_at ?? null,
      };
    } else {
      receivedDate = reader
        ? await reader({ sky, window, snapshot: current, year: inferredYear, previousDate })
        : await readReceivedDateForSnapshot(sky, window, current, {
          year: inferredYear,
          previousDate,
          monthCorrection: checkpoint.date_ocr_month_correction ?? null,
        });
    }
    if (typeof receivedDate !== 'string' || !/^\d{4}-\d{2}-\d{2}$/.test(receivedDate) || isoDate(...receivedDate.split('-').map(Number)) !== receivedDate) {
      throw new Error(`날짜 판독기가 YYYY-MM-DD 값을 반환하지 않았습니다: ${receivedDate}`);
    }
    if (previousDate && receivedDate > previousDate) {
      throw new Error(`수신 날짜가 최신 방향으로 역행해 저장을 멈춥니다: ${receivedDate} 다음 기준 ${previousDate}`);
    }
    if (previousDate) {
      const gapDays = (Date.parse(`${previousDate}T00:00:00Z`) - Date.parse(`${receivedDate}T00:00:00Z`)) / 86400000;
      if (gapDays > 31) {
        throw new Error(`수신 날짜가 앞 기록보다 ${gapDays}일 오래되어 화면 확인이 필요합니다: ${receivedDate} 다음 기준 ${previousDate}`);
      }
    }
    current.receivedDate = receivedDate;
    checkpoint.next_received_date = receivedDate;
    checkpoint.received_date_year = Number(receivedDate.slice(0, 4));
    checkpoint.status = 'paused';
    delete checkpoint.date_capture_error;
    if (checkpointPath) await atomicJson(checkpointPath, checkpoint);
    return receivedDate;
  } catch (error) {
    checkpoint.status = 'paused-date-read-error';
    checkpoint.next_received_date = null;
    checkpoint.date_capture_error = {
      sequence: checkpoint.next_row?.sequence ?? checkpoint.next_sequence,
      row_sha256: current.rowSha,
      body_sha256: current.bodySha,
      message: error.message,
      failed_at: new Date().toISOString(),
    };
    checkpoint.updated_at = new Date().toISOString();
    if (checkpointPath) await atomicJson(checkpointPath, checkpoint);
    throw error;
  }
}

async function senderForRecord(sky, window, current, checkpoint, { reader, checkpointPath } = {}) {
  const sequence = checkpoint.next_row?.sequence ?? checkpoint.next_sequence;
  try {
    const pending = checkpoint.next_sender;
    const canReusePending = pending
      && pending.sequence === sequence
      && pending.row_sha256 === current.rowSha
      && pending.body_sha256 === current.bodySha;
    if (pending && !canReusePending) delete checkpoint.next_sender;
    if (!canReusePending && typeof reader !== 'function') {
      throw new Error('발신자 확인기(senderReader)가 없습니다. 확인되지 않은 발신자를 저장하지 않습니다.');
    }
    const result = canReusePending ? {
      sender: pending.sender,
      ...pending.evidence,
      verification_status: 'verified-visible-header',
    } : await reader({ sky, window, snapshot: current, sequence });
    const sender = typeof result?.sender === 'string' ? result.sender.trim() : '';
    const hasVisibleEvidence = Boolean(
      (typeof result?.visible_header === 'string' && result.visible_header.trim())
      || (typeof result?.visible_list_label === 'string' && result.visible_list_label.trim())
    );
    if (
      !sender
      || sender.length > 120
      || /[\r\n]/u.test(sender)
      || result?.received_date !== current.receivedDate
      || typeof result?.verification_method !== 'string'
      || !result.verification_method.trim()
      || !(result.verification_status === 'verified-visible-header' || result.manually_verified === true)
      || !hasVisibleEvidence
    ) {
      throw new Error('발신자 확인 결과에 이름, 화면 근거, 시각 확인 상태가 모두 필요합니다. OCR 후보만으로는 저장할 수 없습니다.');
    }

    const observed = snapshotFromState(await latestState(sky, window));
    if (!sameSnapshot(current, observed)) {
      throw new Error('발신자 확인 중 선택 행 또는 본문이 바뀌었습니다.');
    }
    const evidence = {
      received_date: result.received_date,
      verification_method: result.verification_method.trim(),
      ...(result.visible_header ? { visible_header: String(result.visible_header).trim() } : {}),
      ...(result.visible_list_label ? { visible_list_label: String(result.visible_list_label).trim() } : {}),
      verified_at: result.verified_at ?? new Date().toISOString(),
    };
    checkpoint.next_sender = {
      sequence,
      row_sha256: current.rowSha,
      body_sha256: current.bodySha,
      sender,
      evidence,
    };
    checkpoint.status = 'paused';
    delete checkpoint.sender_capture_error;
    checkpoint.updated_at = new Date().toISOString();
    if (checkpointPath) await atomicJson(checkpointPath, checkpoint);
    return { sender, evidence };
  } catch (error) {
    checkpoint.status = 'paused-sender-read-error';
    checkpoint.sender_capture_error = {
      sequence,
      row_sha256: current.rowSha,
      body_sha256: current.bodySha,
      message: error.message,
      failed_at: new Date().toISOString(),
    };
    checkpoint.updated_at = new Date().toISOString();
    if (checkpointPath) await atomicJson(checkpointPath, checkpoint);
    throw error;
  }
}

function extractSelectedRow(state) {
  const lines = (state?.accessibility?.tree ?? '').split(/\r?\n/);
  const listIndex = lines.findIndex((line) => /^\s*\d+ 창 UltariList\b/.test(line));
  if (listIndex < 0) throw new Error('수신 목록(UltariList)을 접근성 트리에서 찾지 못했습니다.');
  const listIndent = (lines[listIndex].match(/^\s*/) ?? [''])[0].length;
  for (let index = listIndex + 1; index < lines.length; index += 1) {
    const line = lines[index];
    if (!line.trim()) continue;
    const indent = (line.match(/^\s*/) ?? [''])[0].length;
    if (indent <= listIndent) break;
    const match = line.match(/^\s*\d+ 창 (.*)$/);
    if (!match || /^(UltariScrollBar|UltariList)\b/.test(match[1])) continue;
    const rowParts = [match[1]];
    const rowIndent = indent;
    for (let continuation = index + 1; continuation < lines.length; continuation += 1) {
      const next = lines[continuation];
      if (!next.trim()) continue;
      const nextIndent = (next.match(/^\s*/) ?? [''])[0].length;
      if (nextIndent <= rowIndent) break;
      rowParts.push(next.trim());
    }
    const row = rowParts.join('\n').trim();
    if (!row) throw new Error('선택된 목록 행의 텍스트가 비어 있습니다.');
    return row;
  }
  throw new Error('선택된 수신 쪽지 행을 찾지 못했습니다.');
}

function inboxRowElementIndex(state) {
  const lines = (state?.accessibility?.tree ?? '').split(/\r?\n/);
  const listIndex = lines.findIndex((line) => /^\s*\d+ 창 UltariList\b/.test(line));
  if (listIndex < 0) throw new Error('수신 목록(UltariList)을 접근성 트리에서 찾지 못했습니다.');
  const listIndent = (lines[listIndex].match(/^\s*/) ?? [''])[0].length;
  for (let index = listIndex + 1; index < lines.length; index += 1) {
    const line = lines[index];
    if (!line.trim()) continue;
    const indent = (line.match(/^\s*/) ?? [''])[0].length;
    if (indent <= listIndent) break;
    const match = line.match(/^\s*(\d+) 창 (.*)$/);
    if (!match || /^(UltariScrollBar|UltariList)\b/.test(match[2])) continue;
    return Number(match[1]);
  }
  throw new Error('수신 목록에서 선택된 쪽지 행을 찾지 못했습니다.');
}

export function isInboxRowFocus(state) {
  const focused = state?.accessibility?.focused_element?.trim() ?? '';
  const match = focused.match(/^\s*(\d+) 창\s+/);
  if (!match) return false;
  try { return Number(match[1]) === inboxRowElementIndex(state); }
  catch { return false; }
}

function extractBody(state) {
  const tree = state?.accessibility?.tree ?? '';
  const marker = ' 편집 Value: ';
  const start = tree.indexOf(marker);
  if (start < 0) throw new Error('본문 편집 값이 접근성 트리에 없습니다.');
  const valueStart = start + marker.length;
  const idMarker = ' ID: 1022';
  let end = tree.indexOf(idMarker, valueStart);
  if (end < 0) end = tree.indexOf('\n', valueStart);
  if (end < 0) end = tree.length;
  const body = tree.slice(valueStart, end).trimEnd();
  if (!body.trim()) {
    if (tree.includes('취소된 메시지입니다.')) return '취소된 메시지입니다.';
    throw new Error('선택 쪽지 본문이 비어 있습니다.');
  }
  return body;
}

function attachmentFilenameFromRow(row) {
  const match = String(row ?? '').trim().match(/^([\p{L}\p{N}_ .()\-]{1,180}\.(?:pdf|docx?|xlsx?|pptx?|hwp|hwpx|zip|7z|jpe?g|png|gif|bmp|tiff?|heic|mp4|mov))$/iu);
  return match?.[1]?.trim() ?? null;
}

export function snapshotFromState(state) {
  const row = extractSelectedRow(state);
  // A recalled message can leave the previous message in the preview's UIA
  // Value. The selected list row itself is the authoritative visible marker.
  const body = row === '취소된 메시지입니다.' ? row : extractBody(state);
  return {
    row,
    rowSha: sha256(row),
    body,
    bodySha: sha256(body),
    attachmentFilename: body === '?' ? attachmentFilenameFromRow(row) : null,
  };
}

function sameSnapshot(left, right) {
  return left.rowSha === right.rowSha && left.bodySha === right.bodySha;
}

async function atomicJson(filePath, value) {
  const tempPath = `${filePath}.${crypto.randomUUID()}.tmp`;
  const handle = await fs.open(tempPath, 'w');
  try {
    await handle.writeFile(`${JSON.stringify(value, null, 2)}\n`, 'utf8');
    await handle.sync();
  } finally {
    await handle.close();
  }
  let lastError;
  for (let attempt = 0; attempt < 8; attempt += 1) {
    try {
      await fs.rename(tempPath, filePath);
      return;
    } catch (error) {
      lastError = error;
      if (!['EPERM', 'EACCES', 'EBUSY'].includes(error.code) || attempt === 7) break;
      await sleep(Math.min(80 * (2 ** attempt), 1000));
    }
  }
  // Keep the synced temporary file for recovery if Windows still holds the target.
  throw lastError;
}

async function latestState(sky, window) {
  return sky.get_window_state({ window, include_text: true, include_screenshot: false });
}

async function stableSnapshot(sky, window, { delayMs = 100, after = null, maxAttempts = 8 } = {}) {
  let previous = null;
  for (let attempt = 0; attempt < maxAttempts; attempt += 1) {
    if (attempt > 0 || delayMs > 0) await sleep(delayMs);
    let current;
    try {
      current = snapshotFromState(await latestState(sky, window));
    } catch (error) {
      if (attempt === maxAttempts - 1) throw error;
      continue;
    }
    // When a navigation key has just been sent, a partially refreshed UIA tree
    // can expose the new body while still reporting the old selected row (or
    // vice versa). Treat that mixed state as provisional, never as settled.
    const changed = !after || (
      current.rowSha !== after.rowSha
      && current.bodySha !== after.bodySha
    );
    if (changed && previous && sameSnapshot(current, previous)) return current;
    if (!changed) previous = null;
    else previous = current;
  }
  throw new Error('목록 행과 본문이 안정적으로 갱신되지 않아 캡처를 멈췄습니다.');
}

async function focusInboxList(sky, window) {
  let state = await latestState(sky, window);
  const before = snapshotFromState(state);
  if (!isInboxRowFocus(state)) {
    const rowElementIndex = inboxRowElementIndex(state);
    await sky.click({ window, element_index: rowElementIndex });
    state = await latestState(sky, window);
    const after = snapshotFromState(state);
    if (!sameSnapshot(before, after)) {
      throw new Error('목록 행을 클릭한 뒤 선택 쪽지 본문이 바뀌었습니다. 추가 키 입력 없이 멈춥니다.');
    }
  }
  if (!isInboxRowFocus(state)) {
    const focused = state?.accessibility?.focused_element?.trim() ?? '';
    throw new Error(`수신 목록 행 포커스를 확인하지 못했습니다. Home/Down 입력을 보내지 않고 멈춥니다: ${focused || '(없음)'}`);
  }
  return snapshotFromState(state);
}

function parseJournal(buffer, journalPath) {
  if (!buffer.length) return [];
  const raw = buffer.toString('utf8');
  if (!raw.endsWith('\n')) throw new Error(`JSONL 마지막 행이 온전하지 않습니다. 원본을 보존하고 확인이 필요합니다: ${journalPath}`);
  return raw.trimEnd().split('\n').map((line, index) => {
    let item;
    try { item = JSON.parse(line); }
    catch (error) { throw new Error(`JSONL ${index + 1}행을 읽지 못했습니다: ${error.message}`); }
    if (item.sequence !== index + 1 || typeof item.body !== 'string' || !item.body.trim()) {
      throw new Error(`JSONL ${index + 1}행의 순번 또는 본문이 올바르지 않습니다.`);
    }
    if (item.received_date !== undefined && (
      typeof item.received_date !== 'string'
      || !/^\d{4}-\d{2}-\d{2}$/.test(item.received_date)
      || isoDate(...item.received_date.split('-').map(Number)) !== item.received_date
    )) throw new Error(`JSONL ${index + 1}행의 수신 날짜가 YYYY-MM-DD 형식이 아닙니다.`);
    if (sha256(item.body) !== item.body_sha256 || typeof item.row_sha256 !== 'string') {
      throw new Error(`JSONL ${index + 1}행의 본문/목록 행 해시가 맞지 않습니다.`);
    }
    return item;
  });
}

function checkpointForEmpty(journalPath) {
  return {
    schema_version: 2,
    status: 'paused',
    started_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    saved_count: 0,
    next_sequence: 1,
    journal_file: path.basename(journalPath),
    journal_bytes: 0,
    prefix_sha256: sha256(Buffer.alloc(0)),
    last_row_sha256: null,
    last_body_sha256: null,
    last_received_date: null,
    last_sender: null,
    date_group_count: 0,
    next_received_date: null,
    next_sender: null,
    next_row: null,
    pending_append: null,
    stop_before_row_sha256: null,
  };
}

function validateSavedPrefix(buffer, checkpoint, rows, journalPath) {
  if (checkpoint.schema_version !== 2) throw new Error('이 캡처 폴더의 체크포인트 버전이 달라 안전하게 이어 쓸 수 없습니다. 기존 파일을 보존하고 새 폴더를 사용하세요.');
  if (!Number.isInteger(checkpoint.saved_count) || checkpoint.saved_count > rows.length) {
    throw new Error('체크포인트가 JSONL보다 앞서 있습니다. 파일을 수정하지 않고 중단합니다.');
  }
  const prefixText = rows.slice(0, checkpoint.saved_count).map((row) => JSON.stringify(row)).join('\n');
  const prefix = checkpoint.saved_count ? Buffer.from(`${prefixText}\n`, 'utf8') : Buffer.alloc(0);
  if (prefix.length > buffer.length || sha256(prefix) !== checkpoint.prefix_sha256) {
    throw new Error(`확정된 JSONL 앞부분이 체크포인트와 다릅니다. 원본을 보존하고 중단합니다: ${journalPath}`);
  }
  if (!checkpoint.pending_append && rows.length !== checkpoint.saved_count) {
    throw new Error('체크포인트 뒤에 미확정 JSONL 행이 있습니다. 원본을 보존하고 중단합니다.');
  }
}

async function recoverPendingAppend(journalPath, checkpointPath, checkpoint, buffer) {
  const pending = checkpoint.pending_append;
  if (!pending) return { checkpoint, buffer };
  if (!Number.isInteger(pending.prefix_bytes) || pending.prefix_bytes < 0 || pending.prefix_bytes > buffer.length) {
    throw new Error('미확정 저장의 앞부분 크기가 올바르지 않습니다. 파일을 보존하고 중단합니다.');
  }
  const prefix = buffer.subarray(0, pending.prefix_bytes);
  if (sha256(prefix) !== pending.prefix_sha256) throw new Error('미확정 저장 앞의 기존 JSONL이 변경됐습니다. 파일을 보존하고 중단합니다.');
  const expected = Buffer.from(`${pending.line}\n`, 'utf8');
  const tail = buffer.subarray(pending.prefix_bytes);
  const isExpectedPrefix = tail.length <= expected.length && tail.equals(expected.subarray(0, tail.length));
  if (!isExpectedPrefix) throw new Error('미확정 JSONL 꼬리가 예상한 기록과 다릅니다. 파일을 보존하고 중단합니다.');

  if (tail.length > 0 && tail.length < expected.length) {
    const handle = await fs.open(journalPath, 'r+');
    try { await handle.truncate(pending.prefix_bytes); await handle.sync(); }
    finally { await handle.close(); }
    buffer = buffer.subarray(0, pending.prefix_bytes);
  } else if (tail.length === expected.length) {
    const recovered = Buffer.concat([prefix, expected]);
    const record = JSON.parse(pending.line);
    if (record.sequence !== checkpoint.saved_count + 1) throw new Error('미확정 쪽지 순번이 체크포인트와 달라 중단합니다.');
    checkpoint.saved_count += 1;
    checkpoint.next_sequence = checkpoint.saved_count + 1;
    checkpoint.journal_bytes = recovered.length;
    checkpoint.prefix_sha256 = sha256(recovered);
    checkpoint.last_row_sha256 = record.row_sha256;
    checkpoint.last_row_occurrence = record.row_occurrence;
    checkpoint.last_body_sha256 = record.body_sha256;
    if (record.received_date) {
      if (record.received_date !== checkpoint.last_received_date) checkpoint.date_group_count = (checkpoint.date_group_count ?? 0) + 1;
      checkpoint.last_received_date = record.received_date;
    }
    if (record.sender) checkpoint.last_sender = record.sender;
    checkpoint.next_received_date = null;
    checkpoint.next_sender = null;
    checkpoint.next_row = null;
    checkpoint.pending_append = null;
    checkpoint.stop_reason = null;
    checkpoint.status = 'paused';
    checkpoint.updated_at = new Date().toISOString();
    await atomicJson(checkpointPath, checkpoint);
    return { checkpoint, buffer: recovered };
  }

  checkpoint.pending_append = null;
  checkpoint.next_row = null;
  checkpoint.journal_bytes = buffer.length;
  checkpoint.prefix_sha256 = sha256(buffer);
  checkpoint.status = 'paused';
  checkpoint.stop_reason = null;
  checkpoint.updated_at = new Date().toISOString();
  await atomicJson(checkpointPath, checkpoint);
  return { checkpoint, buffer };
}

async function commitRecord(journalPath, checkpointPath, checkpoint, record) {
  const before = await fs.readFile(journalPath).catch((error) => error.code === 'ENOENT' ? Buffer.alloc(0) : Promise.reject(error));
  const line = JSON.stringify(record);
  const pending = {
    line,
    prefix_bytes: before.length,
    prefix_sha256: sha256(before),
  };
  checkpoint.pending_append = pending;
  checkpoint.next_row = null;
  delete checkpoint.replay_cursor;
  checkpoint.updated_at = new Date().toISOString();
  await atomicJson(checkpointPath, checkpoint);

  const handle = await fs.open(journalPath, 'a');
  try { await handle.writeFile(`${line}\n`, 'utf8'); await handle.sync(); }
  finally { await handle.close(); }

  const after = await fs.readFile(journalPath);
  const expected = Buffer.concat([before, Buffer.from(`${line}\n`, 'utf8')]);
  if (!after.equals(expected)) throw new Error('JSONL 저장 후 검증이 맞지 않습니다. 미확정 체크포인트를 보존하고 중단합니다.');
  checkpoint.saved_count = record.sequence;
  checkpoint.next_sequence = record.sequence + 1;
  checkpoint.journal_bytes = after.length;
  checkpoint.prefix_sha256 = sha256(after);
  checkpoint.last_row_sha256 = record.row_sha256;
  checkpoint.last_row_occurrence = record.row_occurrence;
  checkpoint.last_body_sha256 = record.body_sha256;
  if (record.received_date) {
    if (record.received_date !== checkpoint.last_received_date) checkpoint.date_group_count = (checkpoint.date_group_count ?? 0) + 1;
    checkpoint.last_received_date = record.received_date;
  }
  if (record.sender) checkpoint.last_sender = record.sender;
  checkpoint.next_received_date = null;
  checkpoint.next_sender = null;
  checkpoint.pending_append = null;
  checkpoint.stop_reason = null;
  checkpoint.status = 'paused';
  delete checkpoint.sender_capture_error;
  checkpoint.updated_at = new Date().toISOString();
  await atomicJson(checkpointPath, checkpoint);
}

async function saveNextCursor(checkpointPath, checkpoint, current, sequence, occurrence) {
  delete checkpoint.replay_cursor;
  checkpoint.stop_reason = null;
  checkpoint.status = 'paused';
  checkpoint.next_received_date = current.receivedDate ?? null;
  checkpoint.next_sender = null;
  checkpoint.next_row = {
    sequence,
    row_sha256: current.rowSha,
    row_occurrence: occurrence,
    body_sha256: current.bodySha,
    ...(current.receivedDate ? { received_date: current.receivedDate } : {}),
  };
  checkpoint.updated_at = new Date().toISOString();
  await atomicJson(checkpointPath, checkpoint);
}

async function saveReplayCursor(checkpointPath, checkpoint, record) {
  checkpoint.replay_cursor = {
    sequence: record.sequence,
    row_sha256: record.row_sha256,
    body_sha256: record.body_sha256,
    verified_at: new Date().toISOString(),
  };
  checkpoint.updated_at = new Date().toISOString();
  await atomicJson(checkpointPath, checkpoint);
}

async function advanceAndSettle(sky, window, previous, delayMs, {
  allowSameBodyTransition = null,
} = {}) {
  const beforeState = await latestState(sky, window);
  if (!isInboxRowFocus(beforeState)) {
    const focused = beforeState?.accessibility?.focused_element?.trim() ?? '';
    throw new Error(`↓ 입력 전 수신 목록 행 포커스를 확인하지 못했습니다. 추가 입력 없이 멈춥니다: ${focused || '(없음)'}`);
  }
  await sky.press_key({ window, key: 'Down' });
  let candidate = null;
  let unchangedCount = 0;
  for (let attempt = 0; attempt < 16; attempt += 1) {
    await sleep(delayMs);
    let current;
    try {
      const state = await latestState(sky, window);
      if (!isInboxRowFocus(state)) {
        const focused = state?.accessibility?.focused_element?.trim() ?? '';
        throw new Error(`↓ 입력 뒤 수신 목록 행 포커스를 잃었습니다. 추가 키 입력 없이 멈춥니다: ${focused || '(없음)'}`);
      }
      current = snapshotFromState(state);
    }
    catch (error) {
      if (error instanceof Error && error.message.includes('수신 목록 행 포커스')) throw error;
      continue;
    }
    const rowChanged = current.rowSha !== previous.rowSha;
    const bodyChanged = current.bodySha !== previous.bodySha;
    if (!rowChanged && !bodyChanged) {
      unchangedCount += 1;
      candidate = null;
      if (unchangedCount >= 12) return { current, moved: false };
      continue;
    }
    // Wait out mixed snapshots where either the selected row or body has
    // refreshed first. A move is valid only after both fingerprints changed
    // together and that pair appears in consecutive observations.
    const confirmedSameBodyTransition = rowChanged && !bodyChanged
      && (
        Boolean(allowSameBodyTransition?.(current))
        || (
          previous.body === '?'
          && Boolean(previous.attachmentFilename)
          && current.body === '?'
          && Boolean(current.attachmentFilename)
        )
      );
    if (!rowChanged || (!bodyChanged && !confirmedSameBodyTransition)) {
      unchangedCount = 0;
      candidate = null;
      continue;
    }
    unchangedCount = 0;
    if (candidate && sameSnapshot(candidate, current)) return { current, moved: true };
    candidate = current;
  }
  throw new Error('↓ 입력 뒤 선택 행과 본문이 함께 갱신되지 않아 캡처를 멈췄습니다.');
}

async function resyncFromHome(sky, window, rows, delayMs, maxResyncRows) {
  let state = await latestState(sky, window);
  if (!isInboxRowFocus(state)) {
    const focused = state?.accessibility?.focused_element?.trim() ?? '';
    throw new Error(`Home 입력 전 수신 목록 행 포커스를 확인하지 못했습니다. 추가 입력 없이 멈춥니다: ${focused || '(없음)'}`);
  }
  await sky.press_key({ window, key: 'Home' });
  let current = await stableSnapshot(sky, window, { delayMs });
  state = await latestState(sky, window);
  if (!isInboxRowFocus(state)) {
    const focused = state?.accessibility?.focused_element?.trim() ?? '';
    throw new Error(`Home 입력 뒤 수신 목록 행 포커스를 확인하지 못했습니다. 추가 입력 없이 멈춥니다: ${focused || '(없음)'}`);
  }
  if (!rows.length) return current;
  if (rows.length > maxResyncRows) throw new Error('재개 위치가 안전 재탐색 상한보다 뒤에 있습니다. 자동으로 이어 쓰지 않습니다.');
  for (let index = 0; index < rows.length; index += 1) {
    const expected = rows[index];
    const bodyOccurrenceCount = rows.reduce((count, row) => count + Number(row.body_sha256 === expected.body_sha256), 0);
    const bodyMatches = current.bodySha === expected.body_sha256;
    const rowMatches = current.rowSha === expected.row_sha256;
    if (!bodyMatches || (!rowMatches && bodyOccurrenceCount !== 1)) {
      throw new Error(`Home부터 저장 행 ${index + 1}의 본문 또는 유일성 검증이 맞지 않습니다. JSONL에 이어 쓰지 않고 중단합니다.`);
    }
    if (index < rows.length - 1) {
      const moved = await advanceAndSettle(sky, window, current, delayMs);
      if (!moved.moved) throw new Error(`재개 지점 탐색 중 ${index + 1}행 다음에서 더 이동하지 못했습니다.`);
      current = moved.current;
    }
  }
  const next = await advanceAndSettle(sky, window, current, delayMs);
  if (!next.moved) return null;
  return next.current;
}

/**
 * Capture one small batch (30 by default) from newest to older. Each row needs
 * a visually verified senderReader entry tied to its date and row/body hashes.
 * A checkpoint is synced for every record; inspect the batch before starting another.
 */
export async function captureRawBodies({
  sky,
  window,
  outputDir,
  maxItems = 30,
  delayMs = 100,
  maxResyncRows = 300,
  stopBeforeRowSha256,
  receivedDateYear,
  dateReader,
  senderReader,
}) {
  if (!sky || !window || !outputDir) throw new Error('sky, window, outputDir가 필요합니다.');
  if (!Number.isInteger(maxItems) || maxItems < 1 || maxItems > 30) throw new Error('한 번의 캡처는 1~30건으로 제한합니다.');
  if (typeof senderReader !== 'function') throw new Error('senderReader가 필요합니다. 발신자 확인 없이 캡처를 시작하지 않습니다.');
  await fs.mkdir(outputDir, { recursive: true });

  const journalPath = path.join(outputDir, 'raw-bodies.jsonl');
  const checkpointPath = path.join(outputDir, 'capture-checkpoint.json');
  let buffer = await fs.readFile(journalPath).catch((error) => error.code === 'ENOENT' ? Buffer.alloc(0) : Promise.reject(error));
  const checkpointText = await fs.readFile(checkpointPath, 'utf8').catch((error) => error.code === 'ENOENT' ? '' : Promise.reject(error));
  let checkpoint = checkpointText ? JSON.parse(checkpointText) : checkpointForEmpty(journalPath);

  if (!checkpointText && buffer.length) throw new Error('체크포인트 없이 JSONL이 있습니다. 덮어쓰거나 자동 재개하지 않습니다.');
  if (checkpointText) {
    if (checkpoint.pending_append) {
      const committedPrefix = buffer.subarray(0, checkpoint.journal_bytes);
      if (
        checkpoint.pending_append.prefix_bytes !== checkpoint.journal_bytes
        || checkpoint.pending_append.prefix_sha256 !== checkpoint.prefix_sha256
        || committedPrefix.length !== checkpoint.journal_bytes
        || sha256(committedPrefix) !== checkpoint.prefix_sha256
      ) throw new Error('미확정 저장 앞의 확정 JSONL이 체크포인트와 다릅니다. 원본을 보존하고 중단합니다.');
      const committedRows = parseJournal(committedPrefix, journalPath);
      if (committedRows.length !== checkpoint.saved_count) throw new Error('미확정 저장 앞의 행 수가 체크포인트와 다릅니다.');
    } else {
      const parsed = parseJournal(buffer, journalPath);
      validateSavedPrefix(buffer, checkpoint, parsed, journalPath);
    }
    ({ checkpoint, buffer } = await recoverPendingAppend(journalPath, checkpointPath, checkpoint, buffer));
  } else {
    await atomicJson(checkpointPath, checkpoint);
  }

  let rows = parseJournal(buffer, journalPath);
  validateSavedPrefix(buffer, checkpoint, rows, journalPath);
  if (stopBeforeRowSha256 !== undefined) checkpoint.stop_before_row_sha256 = stopBeforeRowSha256;
  let current = await focusInboxList(sky, window);

  const nextCursor = checkpoint.next_row;
  const rowOccurrences = new Map();
  for (const row of rows) rowOccurrences.set(row.row_sha256, Math.max(rowOccurrences.get(row.row_sha256) ?? 0, row.row_occurrence));
  if (nextCursor && current.rowSha === nextCursor.row_sha256 && current.bodySha === nextCursor.body_sha256) {
    const expectedOccurrence = (rowOccurrences.get(current.rowSha) ?? 0) + 1;
    if (nextCursor.row_occurrence !== expectedOccurrence) throw new Error('재개 행의 동일 행 순번이 체크포인트와 달라 중단합니다.');
  } else if (rows.length) {
    current = await resyncFromHome(sky, window, rows, delayMs, maxResyncRows);
    if (!current) {
      checkpoint.status = 'stalled-at-oldest-or-focus-loss';
      checkpoint.updated_at = new Date().toISOString();
      await atomicJson(checkpointPath, checkpoint);
      return { count: 0, total: rows.length, status: checkpoint.status, journalPath, checkpointPath };
    }
  } else {
    const beforeHome = await latestState(sky, window);
    if (!isInboxRowFocus(beforeHome)) {
      const focused = beforeHome?.accessibility?.focused_element?.trim() ?? '';
      throw new Error(`Home 입력 전 수신 목록 행 포커스를 확인하지 못했습니다. 추가 입력 없이 멈춥니다: ${focused || '(없음)'}`);
    }
    await sky.press_key({ window, key: 'Home' });
    current = await stableSnapshot(sky, window, { delayMs });
    const afterHome = await latestState(sky, window);
    if (!isInboxRowFocus(afterHome)) {
      const focused = afterHome?.accessibility?.focused_element?.trim() ?? '';
      throw new Error(`Home 입력 뒤 수신 목록 행 포커스를 확인하지 못했습니다. 추가 입력 없이 멈춥니다: ${focused || '(없음)'}`);
    }
  }

  if (checkpoint.stop_before_row_sha256 && (
    current.rowSha === checkpoint.stop_before_row_sha256
    || current.bodySha === checkpoint.stop_before_row_sha256
  )) {
    checkpoint.status = 'paused-before-outside-period';
    checkpoint.updated_at = new Date().toISOString();
    await atomicJson(checkpointPath, checkpoint);
    return { count: 0, total: rows.length, status: checkpoint.status, journalPath, checkpointPath };
  }

  const currentOccurrence = (rowOccurrences.get(current.rowSha) ?? 0) + 1;
  await saveNextCursor(checkpointPath, checkpoint, current, rows.length + 1, currentOccurrence);

  const startedCount = rows.length;
  while (rows.length - startedCount < maxItems) {
    const occurrence = (rowOccurrences.get(current.rowSha) ?? 0) + 1;
    const receivedDate = await dateForRecord(sky, window, current, checkpoint, { year: receivedDateYear, reader: dateReader, checkpointPath });
    const senderCapture = await senderForRecord(sky, window, current, checkpoint, { reader: senderReader, checkpointPath });
    const record = {
      sequence: rows.length + 1,
      row_sha256: current.rowSha,
      row_occurrence: occurrence,
      received_date: receivedDate,
      sender: senderCapture.sender,
      sender_evidence: senderCapture.evidence,
      body: current.body,
      body_sha256: current.bodySha,
      captured_at: new Date().toISOString(),
      source: 'gbtalk-message-manager-uia-keyboard-navigation',
      capture_status: current.body === '취소된 메시지입니다.' ? 'recalled-placeholder' : 'captured',
    };
    await commitRecord(journalPath, checkpointPath, checkpoint, record);
    rows.push(record);
    rowOccurrences.set(current.rowSha, occurrence);

    const moved = await advanceAndSettle(sky, window, current, delayMs);
    if (!moved.moved) {
      checkpoint.status = 'stalled-at-oldest-or-focus-loss';
      checkpoint.next_row = null;
      checkpoint.updated_at = new Date().toISOString();
      await atomicJson(checkpointPath, checkpoint);
      return { count: rows.length - startedCount, total: rows.length, status: checkpoint.status, journalPath, checkpointPath };
    }
    current = moved.current;
    const nextOccurrence = (rowOccurrences.get(current.rowSha) ?? 0) + 1;
    await saveNextCursor(checkpointPath, checkpoint, current, rows.length + 1, nextOccurrence);
    if (rows.length - startedCount >= maxItems) break;
  }

  checkpoint.status = 'paused-batch-complete';
  checkpoint.updated_at = new Date().toISOString();
  await atomicJson(checkpointPath, checkpoint);
  return { count: rows.length - startedCount, total: rows.length, status: checkpoint.status, journalPath, checkpointPath };
}

function classifyKnownSnapshot(current, baselineRows) {
  const samePair = baselineRows.find((row) => row.row_sha256 === current.rowSha && row.body_sha256 === current.bodySha);
  if (samePair) return { kind: 'known', sequence: samePair.sequence };
  const sameBody = baselineRows.filter((row) => row.body_sha256 === current.bodySha).map((row) => row.sequence);
  const sameRow = baselineRows.filter((row) => row.row_sha256 === current.rowSha).map((row) => row.sequence);
  if (sameBody.length || sameRow.length) return { kind: 'ambiguous', sameBody, sameRow };
  return { kind: 'new' };
}

function classifyPreviouslyCapturedSnapshot(current, baselineRows) {
  const samePair = baselineRows.filter((row) => (
    row.row_sha256 === current.rowSha && row.body_sha256 === current.bodySha
  ));
  const sameBody = baselineRows.filter((row) => row.body_sha256 === current.bodySha).map((row) => row.sequence);
  const sameRow = baselineRows.filter((row) => row.row_sha256 === current.rowSha).map((row) => row.sequence);
  if (samePair.length === 1) return { kind: 'known', sequence: samePair[0].sequence };
  if (samePair.length > 1 || sameBody.length || sameRow.length) {
    return {
      kind: 'ambiguous',
      same_pair_sequences: samePair.map((row) => row.sequence),
      sameBody,
      sameRow,
    };
  }
  return { kind: 'new' };
}

function verifiedMessageAt(verifiedRange, sequence) {
  const row = verifiedRange?.bySequence.get(sequence);
  if (!row) return undefined;
  return {
    received_at: row.received_at ?? row.received_date,
    sender: row.title,
    body_preview: row.body.replace(/\s+/g, ' ').trim().slice(0, 120),
    row_sha256: row.row_sha256,
    body_sha256: row.body_sha256,
  };
}

function validateConfirmedBaselineDuplicate(current, confirmation, {
  baselineRows,
  verifiedRange,
  anchor,
  previousRecord,
  expectedAfterSequence,
}) {
  if (!confirmation || !current) return null;
  if (
    current.rowSha !== confirmation.row_sha256
    || current.bodySha !== confirmation.body_sha256
    || current.body !== '취소된 메시지입니다.'
  ) return null;

  const pairMatches = baselineRows
    .filter((row) => row.row_sha256 === current.rowSha && row.body_sha256 === current.bodySha)
    .map((row) => row.sequence)
    .sort((left, right) => left - right);
  const confirmedSequences = Array.isArray(confirmation.baseline_match_sequences)
    ? [...confirmation.baseline_match_sequences].sort((left, right) => left - right)
    : [];
  if (!pairMatches.length || JSON.stringify(pairMatches) !== JSON.stringify(confirmedSequences)) {
    throw new Error('취소 쪽지 중복 확인의 기준 순번이 raw 기준 파일과 다릅니다. 저장하지 않습니다.');
  }

  const receivedDate = confirmation.received_date
    ?? (typeof confirmation.received_at === 'string' ? confirmation.received_at.slice(0, 10) : null);
  const sender = typeof confirmation.sender === 'string' ? confirmation.sender.trim() : '';
  if (
    typeof receivedDate !== 'string'
    || !/^\d{4}-\d{2}-\d{2}$/.test(receivedDate)
    || isoDate(...receivedDate.split('-').map(Number)) !== receivedDate
    || receivedDate >= anchor.received_at.slice(0, 10)
    || !sender
  ) throw new Error('취소 쪽지의 화면 확인 날짜/발신자가 유효한 과거 경계 정보가 아닙니다.');

  const metadataMatchSequences = [...new Set(baselineRows
    .filter((row) => row.row_sha256 === current.rowSha || row.body_sha256 === current.bodySha)
    .map((row) => row.sequence))].sort((left, right) => left - right);
  const visibleMatches = metadataMatchSequences.map((sequence) => {
    const row = verifiedRange?.bySequence.get(sequence);
    if (!row) throw new Error(`취소 placeholder 기준 ${sequence}번의 검증 메타데이터가 없습니다.`);
    if (
      (row.row_sha256 !== current.rowSha && row.body_sha256 !== current.bodySha)
      || row.capture_sequence !== sequence
    ) {
      throw new Error(`취소 placeholder 기준 ${sequence}번의 행/본문 지문이 검증 파일과 다릅니다.`);
    }
    return row;
  });
  if (visibleMatches.some((row) => row.received_at?.slice(0, 10) === receivedDate && row.title === sender)) {
    throw new Error('화면에서 확인한 날짜/발신자가 기존 placeholder 메시지와 일치합니다. 중복으로 저장하지 않습니다.');
  }

  if (
    !previousRecord
    || confirmation.after_sequence !== expectedAfterSequence
    || previousRecord.sequence !== expectedAfterSequence
    || confirmation.after_row_sha256 !== previousRecord.row_sha256
    || confirmation.after_body_sha256 !== previousRecord.body_sha256
  ) return null;

  return {
    received_date: receivedDate,
    sender,
    baseline_match_sequences: pairMatches,
    row_sha256: current.rowSha,
    body_sha256: current.bodySha,
    after_sequence: expectedAfterSequence,
    after_row_sha256: previousRecord.row_sha256,
    after_body_sha256: previousRecord.body_sha256,
    confirmation_method: 'visible-manager-header-row-and-adjacent-cursor',
    confirmed_at: confirmation.confirmed_at ?? new Date().toISOString(),
  };
}

function validateConfirmedRepeatBodyTransition(current, confirmation, {
  baselineRows,
  verifiedRange,
  savedRows,
  previousRecord,
  expectedAfterSequence,
  anchor,
}) {
  if (!confirmation || !current) return null;
  const rowSha = current.rowSha ?? current.row_sha256;
  const bodySha = current.bodySha ?? current.body_sha256;
  if (rowSha !== confirmation.row_sha256 || bodySha !== confirmation.body_sha256) {
    throw new Error('같은 본문 재개 후보의 화면 행/본문 지문이 확인 정보와 다릅니다. 입력 없이 멈춥니다.');
  }
  if (
    !previousRecord
    || confirmation.after_sequence !== expectedAfterSequence
    || previousRecord.sequence !== expectedAfterSequence
    || confirmation.after_row_sha256 !== previousRecord.row_sha256
    || confirmation.after_body_sha256 !== previousRecord.body_sha256
    || rowSha === previousRecord.row_sha256
    || bodySha !== previousRecord.body_sha256
  ) throw new Error('같은 본문 재개 후보가 직전 저장 커서와 연결되지 않습니다. 입력 없이 멈춥니다.');

  const receivedAt = confirmation.received_at;
  const afterReceivedAt = confirmation.after_received_at;
  const sender = typeof confirmation.sender === 'string' ? confirmation.sender.trim() : '';
  const afterSender = typeof confirmation.after_sender === 'string' ? confirmation.after_sender.trim() : '';
  const isTimestamp = (value) => typeof value === 'string'
    && /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}$/.test(value);
  if (
    !isTimestamp(receivedAt)
    || !isTimestamp(afterReceivedAt)
    || !(receivedAt < afterReceivedAt && afterReceivedAt < anchor.received_at)
    || !sender
    || !afterSender
  ) throw new Error('같은 본문 재개 후보의 화면 확인 날짜/발신자 순서가 유효하지 않습니다.');

  const pairMatches = baselineRows
    .filter((row) => row.row_sha256 === rowSha && row.body_sha256 === bodySha)
    .map((row) => row.sequence)
    .sort((left, right) => left - right);
  const sameBody = baselineRows
    .filter((row) => row.body_sha256 === bodySha)
    .map((row) => row.sequence);
  const sameRow = baselineRows
    .filter((row) => row.row_sha256 === rowSha)
    .map((row) => row.sequence);
  const confirmedSequences = Array.isArray(confirmation.baseline_match_sequences)
    ? [...confirmation.baseline_match_sequences].sort((left, right) => left - right)
    : [];
  if (JSON.stringify(pairMatches) !== JSON.stringify(confirmedSequences)) {
    throw new Error('같은 본문 재개 후보의 기준 raw 일치 순번이 확인 정보와 다릅니다.');
  }
  for (const sequence of new Set([...pairMatches, ...sameBody, ...sameRow])) {
    const baseline = verifiedRange?.bySequence.get(sequence);
    if (!baseline) throw new Error(`같은 본문 재개 후보 기준 ${sequence}번의 검증 메타데이터가 없습니다.`);
    if (baseline.received_at === receivedAt && baseline.title === sender) {
      throw new Error('같은 본문 재개 후보의 날짜/발신자가 기존 기준 항목과 같습니다.');
    }
  }
  if ((savedRows ?? []).some((row) => row.row_sha256 === rowSha)) {
    throw new Error('같은 본문 재개 후보의 행 지문이 이미 저장되어 있습니다.');
  }

  return {
    received_at: receivedAt,
    sender,
    row_sha256: rowSha,
    body_sha256: bodySha,
    after_received_at: afterReceivedAt,
    after_sender: afterSender,
    after_sequence: expectedAfterSequence,
    after_row_sha256: previousRecord.row_sha256,
    after_body_sha256: previousRecord.body_sha256,
    confirmation_method: 'visible-manager-header-row-and-adjacent-cursor',
    confirmed_at: confirmation.confirmed_at ?? new Date().toISOString(),
  };
}

function validateConfirmedAttachmentReference(current, confirmation, {
  checkpoint,
  baselineRows,
  verifiedRange,
  savedRows,
  previousRecord,
  expectedAfterSequence,
  anchor,
}) {
  if (!confirmation || !current) return null;
  const isLive = typeof current.rowSha === 'string';
  const rowSha = isLive ? current.rowSha : current.row_sha256;
  const bodySha = isLive ? current.bodySha : current.body_sha256;
  const filename = isLive ? current.attachmentFilename : current.attachment_filename;
  const observedBodySha = isLive ? current.bodySha : current.observed_ui_body_sha256;
  if (isLive) {
    if (current.body !== '?' || !filename) return null;
  } else if (
    current.capture_status !== 'attachment-reference-only'
    || current.body !== `첨부파일 참조: ${filename}`
    || !filename
  ) return null;

  if (
    rowSha !== confirmation.row_sha256
    || observedBodySha !== confirmation.observed_body_sha256
    || filename !== confirmation.filename
  ) return null;

  const samePairs = baselineRows
    .filter((row) => row.row_sha256 === rowSha && row.body_sha256 === observedBodySha)
    .map((row) => row.sequence)
    .sort((left, right) => left - right);
  const sameBody = baselineRows
    .filter((row) => row.body_sha256 === observedBodySha)
    .map((row) => row.sequence)
    .sort((left, right) => left - right);
  const sameRow = baselineRows
    .filter((row) => row.row_sha256 === rowSha)
    .map((row) => row.sequence)
    .sort((left, right) => left - right);
  const confirmedSequences = Array.isArray(confirmation.baseline_match_sequences)
    ? [...confirmation.baseline_match_sequences].sort((left, right) => left - right)
    : [];
  if (
    samePairs.length
    || !sameBody.length
    || sameRow.length
    || JSON.stringify(sameBody) !== JSON.stringify(confirmedSequences)
  ) throw new Error('첨부 전용 후보의 기준 placeholder 지문과 확인 순번이 일치하지 않습니다. 저장하지 않습니다.');

  if (isLive) {
    const stopped = checkpoint?.stop_reason;
    if (
      checkpoint?.status !== 'paused-ambiguous-existing'
      || checkpoint.saved_count !== expectedAfterSequence
      || checkpoint.next_row !== null
      || stopped?.row_sha256 !== rowSha
      || stopped?.body_sha256 !== observedBodySha
      || JSON.stringify([...(stopped?.same_body_sequences ?? [])].sort((a, b) => a - b)) !== JSON.stringify(sameBody)
      || (stopped?.same_pair_sequences?.length ?? 0) !== 0
      || (stopped?.same_row_sequences?.length ?? 0) !== 0
    ) return null;
  } else if (
    bodySha !== sha256(current.body)
    || current.observed_ui_body_sha256 !== confirmation.observed_body_sha256
  ) throw new Error('저장된 첨부 참조의 원본 UI placeholder 지문이 확인 메타데이터와 다릅니다.');

  const receivedAt = confirmation.received_at;
  const afterReceivedAt = confirmation.after_received_at;
  const sender = typeof confirmation.sender === 'string' ? confirmation.sender.trim() : '';
  const afterSender = typeof confirmation.after_sender === 'string' ? confirmation.after_sender.trim() : '';
  const isTimestamp = (value) => typeof value === 'string'
    && /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}$/.test(value);
  if (
    !isTimestamp(receivedAt)
    || !isTimestamp(afterReceivedAt)
    || !(receivedAt < afterReceivedAt && afterReceivedAt < anchor.received_at)
    || !sender
    || !afterSender
  ) throw new Error('첨부 전용 후보의 화면 날짜/발신자 및 직전 항목 순서가 유효하지 않습니다.');

  for (const sequence of sameBody) {
    const baseline = verifiedRange?.bySequence.get(sequence);
    if (!baseline) throw new Error(`첨부 전용 placeholder 기준 ${sequence}번의 검증 메타데이터가 없습니다.`);
    if (baseline.received_at === receivedAt && baseline.title === sender) {
      throw new Error('첨부 전용 후보의 날짜/발신자가 기존 placeholder 항목과 같습니다.');
    }
  }

  if (
    !previousRecord
    || previousRecord.sequence !== expectedAfterSequence
    || confirmation.after_sequence !== expectedAfterSequence
    || confirmation.after_row_sha256 !== previousRecord.row_sha256
    || confirmation.after_body_sha256 !== previousRecord.body_sha256
  ) return null;
  if (!isLive && savedRows?.some((row) => row.sequence === current.sequence && row.row_sha256 !== rowSha)) {
    throw new Error('저장된 첨부 참조 순번의 행 지문이 달라졌습니다.');
  }

  return {
    row_sha256: rowSha,
    observed_body_sha256: observedBodySha,
    filename,
    received_at: receivedAt,
    sender,
    baseline_match_sequences: sameBody,
    after_sequence: expectedAfterSequence,
    after_received_at: afterReceivedAt,
    after_sender: afterSender,
    after_row_sha256: previousRecord.row_sha256,
    after_body_sha256: previousRecord.body_sha256,
    confirmation_method: 'visible-manager-header-row-and-attachment-reference',
    confirmed_at: confirmation.confirmed_at ?? new Date().toISOString(),
  };
}

async function loadVerifiedRange({ baselineRows, baselineVerifiedJsonl, baselineRangeManifest }) {
  if (!baselineVerifiedJsonl && !baselineRangeManifest) return null;
  if (!baselineVerifiedJsonl || !baselineRangeManifest) {
    throw new Error('baselineVerifiedJsonl과 baselineRangeManifest를 함께 지정해야 합니다.');
  }
  const verifiedPath = path.resolve(baselineVerifiedJsonl);
  const manifestPath = path.resolve(baselineRangeManifest);
  const [verifiedBuffer, manifestBuffer] = await Promise.all([
    fs.readFile(verifiedPath),
    fs.readFile(manifestPath),
  ]);
  let manifest;
  try { manifest = JSON.parse(manifestBuffer.toString('utf8')); }
  catch (error) { throw new Error(`기준 범위 매니페스트 JSON을 읽지 못했습니다: ${error.message}`); }
  if (!verifiedBuffer.length || !verifiedBuffer.toString('utf8').endsWith('\n')) {
    throw new Error('검증된 기준 JSONL이 비어 있거나 마지막 행이 완전하지 않습니다.');
  }
  let previousSequence = 0;
  const verifiedRows = verifiedBuffer.toString('utf8').trimEnd().split('\n').map((line, index) => {
    let row;
    try { row = JSON.parse(line); }
    catch (error) { throw new Error(`검증 기준 JSONL ${index + 1}행을 읽지 못했습니다: ${error.message}`); }
    const receivedValue = row.received_at ?? row.received_date;
    if (
      !Number.isInteger(row.capture_sequence)
      || row.capture_sequence <= previousSequence
      || typeof receivedValue !== 'string'
      || !/^\d{4}-\d{2}-\d{2}(?:T\d{2}:\d{2}:\d{2})?$/.test(receivedValue)
      || typeof row.title !== 'string'
      || !row.title.trim()
      || typeof row.body !== 'string'
      || sha256(row.body) !== row.body_sha256
    ) throw new Error(`검증 기준 JSONL ${index + 1}행의 순번·메타데이터·해시가 올바르지 않습니다.`);
    previousSequence = row.capture_sequence;
    row.received_at = receivedValue;
    const raw = baselineRows.find((candidate) => candidate.sequence === row.capture_sequence);
    if (!raw || raw.row_sha256 !== row.row_sha256 || raw.body_sha256 !== row.body_sha256) {
      throw new Error(`검증 기준 JSONL ${index + 1}행이 raw 기준과 일치하지 않습니다.`);
    }
    return row;
  });
  const verifiedSha256 = sha256(verifiedBuffer);
  const manifestSha256 = sha256(manifestBuffer);
  const first = verifiedRows[0];
  const last = verifiedRows.at(-1);
  const bySequence = new Map(verifiedRows.map((row) => [row.capture_sequence, row]));
  const sameBoundary = (saved, row) => saved
    && saved.capture_sequence === row.capture_sequence
    && (saved.received_at ?? saved.received_date) === (row.received_at ?? row.received_date)
    && saved.sender === row.title
    && saved.row_sha256 === row.row_sha256
    && saved.body_sha256 === row.body_sha256;
  if (
    manifest.schema_version !== 1
    || manifest.scope !== 'gbetalk-received-inbox'
    || typeof manifest.month !== 'string'
    || verifiedRows.some((row) => !row.received_at.startsWith(`${manifest.month}-`))
    || manifest.record_count !== verifiedRows.length
    || manifest.verified_jsonl_sha256 !== verifiedSha256
    || !sameBoundary(manifest.newest, first)
    || !sameBoundary(manifest.oldest, last)
  ) throw new Error('기준 범위 매니페스트가 검증 JSONL과 다릅니다.');
  return {
    verifiedPath,
    manifestPath,
    verifiedRows,
    bySequence,
    manifest,
    verifiedSha256,
    manifestSha256,
    baselineRows: baselineRows.filter((row) => bySequence.has(row.sequence)),
  };
}

async function resyncIncrementalFromHome(sky, window, rows, delayMs, maxResyncRows) {
  if (rows.length > maxResyncRows) {
    throw new Error('신규 캡처 재개 지점이 안전 재탐색 상한보다 뒤에 있습니다. 자동으로 이어 쓰지 않습니다.');
  }
  let state = await latestState(sky, window);
  if (!isInboxRowFocus(state)) {
    const focused = state?.accessibility?.focused_element?.trim() ?? '';
    throw new Error(`Home 입력 전 수신 목록 행 포커스를 확인하지 못했습니다. 추가 입력 없이 멈춥니다: ${focused || '(없음)'}`);
  }
  await sky.press_key({ window, key: 'Home' });
  let current = await stableSnapshot(sky, window, { delayMs });
  state = await latestState(sky, window);
  if (!isInboxRowFocus(state)) {
    const focused = state?.accessibility?.focused_element?.trim() ?? '';
    throw new Error(`Home 입력 뒤 수신 목록 행 포커스를 확인하지 못했습니다. 추가 입력 없이 멈춥니다: ${focused || '(없음)'}`);
  }
  for (let index = 0; index < rows.length; index += 1) {
    const expected = rows[index];
    if (current.rowSha !== expected.row_sha256 || current.bodySha !== expected.body_sha256) {
      throw new Error(`Home부터 신규 캡처 ${index + 1}행의 행/본문 지문이 달라졌습니다. 이어 쓰지 않고 멈춥니다.`);
    }
    if (index < rows.length - 1) {
      const moved = await advanceAndSettle(sky, window, current, delayMs);
      if (!moved.moved) throw new Error(`신규 캡처 재개 위치를 찾기 전에 ${index + 1}행 다음에서 멈췄습니다.`);
      current = moved.current;
    }
  }
  if (!rows.length) return current;
  const next = await advanceAndSettle(sky, window, current, delayMs);
  return next.moved ? next.current : null;
}

function finishIncrementalStop(checkpoint, checkpointPath, status, details) {
  checkpoint.status = status;
  checkpoint.stop_reason = details;
  checkpoint.updated_at = new Date().toISOString();
  return atomicJson(checkpointPath, checkpoint);
}

/**
 * Capture only messages newer than a trusted raw capture. Start at Home,
 * write new messages in small batches with a verified sender, and stop before
 * a known row/body-pair boundary candidate. Partial fingerprint matches stop as ambiguous.
 */
export async function captureNewUntilKnown({
  sky,
  window,
  baselineRawJsonl,
  baselineVerifiedJsonl,
  baselineRangeManifest,
  outputDir,
  maxItems = 30,
  delayMs = 100,
  maxResyncRows = 300,
  receivedDateYear,
  dateReader,
  senderReader,
}) {
  if (!sky || !window || !baselineRawJsonl || !outputDir) {
    throw new Error('sky, window, baselineRawJsonl, outputDir가 필요합니다.');
  }
  if (!Number.isInteger(maxItems) || maxItems < 1 || maxItems > 30) {
    throw new Error('한 번의 증분 캡처는 1~30건으로 제한합니다.');
  }
  if (typeof senderReader !== 'function') throw new Error('senderReader가 필요합니다. 발신자 확인 없이 증분 캡처를 시작하지 않습니다.');

  const baselinePath = path.resolve(baselineRawJsonl);
  const outputPath = path.resolve(outputDir);
  const baselineDirectory = path.dirname(baselinePath);
  const baselineRelativeToOutput = path.relative(outputPath, baselineDirectory);
  const outputRelativeToBaseline = path.relative(baselineDirectory, outputPath);
  const isInside = (relative) => relative === '' || (
    relative !== '..'
    && !relative.startsWith(`..${path.sep}`)
    && !path.isAbsolute(relative)
  );
  if (
    isInside(baselineRelativeToOutput)
    || isInside(outputRelativeToBaseline)
  ) {
    throw new Error('증분 출력 폴더는 기존 raw 캡처와 분리해야 합니다.');
  }
  const baselineBuffer = await fs.readFile(baselinePath);
  const baselineRows = parseJournal(baselineBuffer, baselinePath);
  if (!baselineRows.length) throw new Error('기준 raw JSONL이 비어 있어 증분 중복 경계를 만들 수 없습니다.');
  const baselineSha256 = sha256(baselineBuffer);
  const verifiedRange = await loadVerifiedRange({
    baselineRows,
    baselineVerifiedJsonl,
    baselineRangeManifest,
  });
  for (const inputPath of [verifiedRange?.verifiedPath, verifiedRange?.manifestPath].filter(Boolean)) {
    const inputDirectory = path.dirname(inputPath);
    if (isInside(path.relative(outputPath, inputDirectory)) || isInside(path.relative(inputDirectory, outputPath))) {
      throw new Error('증분 출력 폴더는 기준 JSONL/매니페스트 폴더와도 분리해야 합니다.');
    }
  }
  const trustedBaselineRows = verifiedRange?.baselineRows ?? baselineRows;
  await fs.mkdir(outputPath, { recursive: true });

  const journalPath = path.join(outputPath, 'new-bodies.jsonl');
  const checkpointPath = path.join(outputPath, 'incremental-checkpoint.json');
  let buffer = await fs.readFile(journalPath).catch((error) => error.code === 'ENOENT' ? Buffer.alloc(0) : Promise.reject(error));
  const checkpointText = await fs.readFile(checkpointPath, 'utf8').catch((error) => error.code === 'ENOENT' ? '' : Promise.reject(error));
  let checkpoint = checkpointText ? JSON.parse(checkpointText) : checkpointForEmpty(journalPath);

  if (!checkpointText && buffer.length) throw new Error('체크포인트 없이 신규 JSONL이 있습니다. 자동 재개하지 않습니다.');
  if (checkpointText) {
    if (checkpoint.schema_version !== 2 || checkpoint.mode !== 'incremental') {
      throw new Error('증분 캡처 체크포인트 형식이 다릅니다. 기존 파일을 보존하고 중단합니다.');
    }
    if (checkpoint.baseline_path !== baselinePath || checkpoint.baseline_sha256 !== baselineSha256) {
      throw new Error('증분 캡처 기준 raw 파일이 바뀌었습니다. 새 출력 폴더를 사용하세요.');
    }
    if (
      (checkpoint.baseline_verified_sha256 ?? null) !== (verifiedRange?.verifiedSha256 ?? null)
      || (checkpoint.baseline_manifest_sha256 ?? null) !== (verifiedRange?.manifestSha256 ?? null)
    ) throw new Error('증분 캡처의 검증 기준 범위가 바뀌었습니다. 기존 파일을 보존하고 새 출력 폴더를 사용하세요.');
    if (['paused-existing-boundary', 'paused-ambiguous-existing', 'paused-before-known-boundary'].includes(checkpoint.status)) {
      return { count: 0, total: checkpoint.saved_count, status: checkpoint.status, journalPath, checkpointPath };
    }
    if (checkpoint.pending_append) {
      const committedPrefix = buffer.subarray(0, checkpoint.journal_bytes);
      if (
        checkpoint.pending_append.prefix_bytes !== checkpoint.journal_bytes
        || checkpoint.pending_append.prefix_sha256 !== checkpoint.prefix_sha256
        || committedPrefix.length !== checkpoint.journal_bytes
        || sha256(committedPrefix) !== checkpoint.prefix_sha256
      ) throw new Error('신규 캡처의 미확정 저장 앞부분이 체크포인트와 다릅니다. 파일을 보존하고 중단합니다.');
      const committedRows = parseJournal(committedPrefix, journalPath);
      if (committedRows.length !== checkpoint.saved_count) throw new Error('신규 캡처의 확정 행 수가 체크포인트와 다릅니다.');
    } else {
      const parsed = parseJournal(buffer, journalPath);
      validateSavedPrefix(buffer, checkpoint, parsed, journalPath);
    }
    ({ checkpoint, buffer } = await recoverPendingAppend(journalPath, checkpointPath, checkpoint, buffer));
  } else {
    checkpoint.mode = 'incremental';
    checkpoint.baseline_path = baselinePath;
    checkpoint.baseline_sha256 = baselineSha256;
    checkpoint.baseline_verified_sha256 = verifiedRange?.verifiedSha256 ?? null;
    checkpoint.baseline_manifest_path = verifiedRange?.manifestPath ?? null;
    checkpoint.baseline_manifest_sha256 = verifiedRange?.manifestSha256 ?? null;
    checkpoint.baseline_range = verifiedRange ? {
      record_count: verifiedRange.manifest.record_count,
      newest: verifiedRange.manifest.newest,
      oldest: verifiedRange.manifest.oldest,
    } : null;
    checkpoint.journal_file = path.basename(journalPath);
    await atomicJson(checkpointPath, checkpoint);
  }

  let rows = parseJournal(buffer, journalPath);
  validateSavedPrefix(buffer, checkpoint, rows, journalPath);
  for (const row of rows) {
    if (classifyKnownSnapshot({ rowSha: row.row_sha256, bodySha: row.body_sha256 }, trustedBaselineRows).kind === 'known') {
      throw new Error(`신규 JSONL ${row.sequence}행이 기존 기준 캡처와 겹칩니다. 자동 재개를 멈춥니다.`);
    }
  }

  let current = await focusInboxList(sky, window);
  current = await resyncIncrementalFromHome(sky, window, rows, delayMs, maxResyncRows);
  if (!current) {
    await finishIncrementalStop(checkpoint, checkpointPath, 'paused-before-known-boundary', {
      message: '목록 끝에 도달하기 전에 기존 메시지 지문을 찾지 못했습니다.',
    });
    return { count: 0, total: rows.length, status: checkpoint.status, journalPath, checkpointPath };
  }

  const startedCount = rows.length;
  const rowOccurrences = new Map();
  for (const row of rows) rowOccurrences.set(row.row_sha256, Math.max(rowOccurrences.get(row.row_sha256) ?? 0, row.row_occurrence));

  while (rows.length - startedCount < maxItems) {
    const classification = classifyKnownSnapshot(current, trustedBaselineRows);
    if (classification.kind === 'known') {
      await finishIncrementalStop(checkpoint, checkpointPath, 'paused-existing-boundary', {
        baseline_sequence: classification.sequence,
        baseline_message: verifiedMessageAt(verifiedRange, classification.sequence),
        row_sha256: current.rowSha,
        body_sha256: current.bodySha,
        row_text: current.row,
      });
      return { count: rows.length - startedCount, total: rows.length, status: checkpoint.status, journalPath, checkpointPath };
    }
    if (classification.kind === 'ambiguous') {
      await finishIncrementalStop(checkpoint, checkpointPath, 'paused-ambiguous-existing', {
        message: '행 지문 또는 본문 지문 하나만 기준 캡처와 일치합니다. 저장하지 않고 확인이 필요합니다.',
        same_body_sequences: classification.sameBody,
        same_row_sequences: classification.sameRow,
        row_sha256: current.rowSha,
        body_sha256: current.bodySha,
        row_text: current.row,
      });
      return { count: rows.length - startedCount, total: rows.length, status: checkpoint.status, journalPath, checkpointPath };
    }

    const occurrence = (rowOccurrences.get(current.rowSha) ?? 0) + 1;
    const receivedDate = await dateForRecord(sky, window, current, checkpoint, { year: receivedDateYear, reader: dateReader, checkpointPath });
    const senderCapture = await senderForRecord(sky, window, current, checkpoint, { reader: senderReader, checkpointPath });
    const record = {
      sequence: rows.length + 1,
      row_sha256: current.rowSha,
      row_occurrence: occurrence,
      received_date: receivedDate,
      sender: senderCapture.sender,
      sender_evidence: senderCapture.evidence,
      body: current.body,
      body_sha256: current.bodySha,
      captured_at: new Date().toISOString(),
      source: 'gbtalk-message-manager-uia-keyboard-incremental',
      capture_status: current.body === '취소된 메시지입니다.' ? 'recalled-placeholder' : 'captured',
    };
    await commitRecord(journalPath, checkpointPath, checkpoint, record);
    rows.push(record);
    rowOccurrences.set(current.rowSha, occurrence);

    const moved = await advanceAndSettle(sky, window, current, delayMs);
    if (!moved.moved) {
      await finishIncrementalStop(checkpoint, checkpointPath, 'paused-before-known-boundary', {
        message: '더 오래된 행으로 이동할 수 없어 중단했습니다. 기존 경계는 확인되지 않았습니다.',
        last_saved_sequence: rows.length,
      });
      return { count: rows.length - startedCount, total: rows.length, status: checkpoint.status, journalPath, checkpointPath };
    }
    current = moved.current;
    await saveNextCursor(checkpointPath, checkpoint, current, rows.length + 1, (rowOccurrences.get(current.rowSha) ?? 0) + 1);

    if (rows.length - startedCount >= maxItems) {
      const nextClass = classifyKnownSnapshot(current, trustedBaselineRows);
      if (nextClass.kind === 'known') {
        await finishIncrementalStop(checkpoint, checkpointPath, 'paused-existing-boundary', {
          baseline_sequence: nextClass.sequence,
          baseline_message: verifiedMessageAt(verifiedRange, nextClass.sequence),
          row_sha256: current.rowSha,
          body_sha256: current.bodySha,
          row_text: current.row,
        });
      } else if (nextClass.kind === 'ambiguous') {
        await finishIncrementalStop(checkpoint, checkpointPath, 'paused-ambiguous-existing', {
          message: '행 지문 또는 본문 지문 하나만 기준 캡처와 일치합니다. 저장하지 않고 확인이 필요합니다.',
          same_body_sequences: nextClass.sameBody,
          same_row_sequences: nextClass.sameRow,
          row_sha256: current.rowSha,
          body_sha256: current.bodySha,
          row_text: current.row,
        });
      } else {
        checkpoint.status = 'paused-batch-complete';
        checkpoint.updated_at = new Date().toISOString();
        await atomicJson(checkpointPath, checkpoint);
      }
      return { count: rows.length - startedCount, total: rows.length, status: checkpoint.status, journalPath, checkpointPath };
    }
  }

  return { count: rows.length - startedCount, total: rows.length, status: checkpoint.status, journalPath, checkpointPath };
}

/**
 * Backfill messages older than the oldest item in a verified archived range.
 * The first call only locates and records the anchor candidate. The caller
 * must compare the visible date/sender with the range manifest and call again
 * with confirmedAnchor and a verified senderReader before any older body is written.
 */
export async function captureOlderThanKnown({
  sky,
  window,
  baselineRawJsonl,
  baselineVerifiedJsonl,
  baselineRangeManifest,
  outputDir,
  confirmedAnchor,
  confirmedDistinctCandidate,
  confirmedRepeatBodyCandidate,
  confirmedAttachmentReference,
  maxItems = 30,
  delayMs = 100,
  maxAnchorScanRows = 1000,
  receivedDateYear,
  dateReader,
  senderReader,
}) {
  if (!sky || !window || !baselineRawJsonl || !baselineVerifiedJsonl || !baselineRangeManifest || !outputDir) {
    throw new Error('sky, window, 기준 raw/검증 JSONL/범위 매니페스트, outputDir가 필요합니다.');
  }
  if (!Number.isInteger(maxItems) || maxItems < 1 || maxItems > 30) {
    throw new Error('한 번의 과거 쪽지 캡처는 1~30건으로 제한합니다.');
  }
  if (!Number.isInteger(maxAnchorScanRows) || maxAnchorScanRows < 1) {
    throw new Error('maxAnchorScanRows는 양의 정수여야 합니다.');
  }

  const baselinePath = path.resolve(baselineRawJsonl);
  const outputPath = path.resolve(outputDir);
  const baselineDirectory = path.dirname(baselinePath);
  const outputRelativeToBaseline = path.relative(baselineDirectory, outputPath);
  const baselineRelativeToOutput = path.relative(outputPath, baselineDirectory);
  const isInside = (relative) => relative === '' || (
    relative !== '..'
    && !relative.startsWith(`..${path.sep}`)
    && !path.isAbsolute(relative)
  );
  if (isInside(baselineRelativeToOutput) || isInside(outputRelativeToBaseline)) {
    throw new Error('과거 캡처 출력 폴더는 기준 파일 폴더와 분리해야 합니다.');
  }

  const baselineBuffer = await fs.readFile(baselinePath);
  const allBaselineRows = parseJournal(baselineBuffer, baselinePath);
  if (!allBaselineRows.length) throw new Error('기준 raw JSONL이 비어 있습니다.');
  const verifiedRange = await loadVerifiedRange({
    baselineRows: allBaselineRows,
    baselineVerifiedJsonl,
    baselineRangeManifest,
  });
  for (const inputPath of [verifiedRange.verifiedPath, verifiedRange.manifestPath]) {
    const inputDirectory = path.dirname(inputPath);
    if (isInside(path.relative(outputPath, inputDirectory)) || isInside(path.relative(inputDirectory, outputPath))) {
      throw new Error('과거 캡처 출력 폴더는 기준 JSONL/매니페스트 폴더와도 분리해야 합니다.');
    }
  }
  const trustedBaselineRows = verifiedRange.baselineRows;
  const anchor = verifiedRange.manifest.oldest;
  const anchorRaw = trustedBaselineRows.find((row) => row.sequence === anchor.capture_sequence);
  if (!anchorRaw) throw new Error('범위의 가장 오래된 기준 행이 raw 파일에 없습니다.');
  const anchorPairMatches = trustedBaselineRows.filter((row) => (
    row.row_sha256 === anchorRaw.row_sha256 && row.body_sha256 === anchorRaw.body_sha256
  ));
  if (anchorPairMatches.length !== 1) {
    throw new Error('가장 오래된 기준 쪽지의 행/본문 지문이 범위 안에서 유일하지 않아 안전한 앵커로 쓸 수 없습니다.');
  }
  const anchorConfirmation = confirmedAnchor ? {
    received_at: confirmedAnchor.received_at,
    sender: confirmedAnchor.sender,
  } : null;
  if (anchorConfirmation && (
    anchorConfirmation.received_at !== anchor.received_at
    || anchorConfirmation.sender !== anchor.sender
  )) throw new Error('확인한 날짜/발신자가 범위 매니페스트의 가장 오래된 쪽지와 다릅니다.');
  if (anchorConfirmation && typeof senderReader !== 'function') {
    throw new Error('senderReader가 필요합니다. 발신자 확인 없이 과거 캡처를 시작하지 않습니다.');
  }

  await fs.mkdir(outputPath, { recursive: true });
  const journalPath = path.join(outputPath, 'older-bodies.jsonl');
  const checkpointPath = path.join(outputPath, 'backfill-checkpoint.json');
  let buffer = await fs.readFile(journalPath).catch((error) => error.code === 'ENOENT' ? Buffer.alloc(0) : Promise.reject(error));
  const checkpointText = await fs.readFile(checkpointPath, 'utf8').catch((error) => error.code === 'ENOENT' ? '' : Promise.reject(error));
  let checkpoint = checkpointText ? JSON.parse(checkpointText) : checkpointForEmpty(journalPath);

  if (!checkpointText && buffer.length) throw new Error('체크포인트 없이 과거 캡처 JSONL이 있습니다. 자동 재개하지 않습니다.');
  if (checkpointText) {
    if (checkpoint.schema_version !== 2 || checkpoint.mode !== 'backfill') {
      throw new Error('과거 캡처 체크포인트 형식이 다릅니다. 기존 파일을 보존하고 중단합니다.');
    }
    if (
      checkpoint.baseline_path !== baselinePath
      || checkpoint.baseline_sha256 !== sha256(baselineBuffer)
      || checkpoint.baseline_verified_sha256 !== verifiedRange.verifiedSha256
      || checkpoint.baseline_manifest_sha256 !== verifiedRange.manifestSha256
    ) throw new Error('과거 캡처 기준 범위가 바뀌었습니다. 새 출력 폴더를 사용하세요.');
    if (checkpoint.status === 'paused-oldest-reached') {
      return { count: 0, total: checkpoint.saved_count, status: checkpoint.status, journalPath, checkpointPath };
    }
    if (checkpoint.pending_append) {
      const committedPrefix = buffer.subarray(0, checkpoint.journal_bytes);
      if (
        checkpoint.pending_append.prefix_bytes !== checkpoint.journal_bytes
        || checkpoint.pending_append.prefix_sha256 !== checkpoint.prefix_sha256
        || committedPrefix.length !== checkpoint.journal_bytes
        || sha256(committedPrefix) !== checkpoint.prefix_sha256
      ) throw new Error('과거 캡처의 미확정 저장 앞부분이 체크포인트와 다릅니다.');
      if (parseJournal(committedPrefix, journalPath).length !== checkpoint.saved_count) {
        throw new Error('과거 캡처의 확정 행 수가 체크포인트와 다릅니다.');
      }
    } else {
      const parsed = parseJournal(buffer, journalPath);
      validateSavedPrefix(buffer, checkpoint, parsed, journalPath);
    }
    ({ checkpoint, buffer } = await recoverPendingAppend(journalPath, checkpointPath, checkpoint, buffer));
    if (checkpoint.anchor_confirmation && anchorConfirmation && (
      checkpoint.anchor_confirmation.received_at !== anchorConfirmation.received_at
      || checkpoint.anchor_confirmation.sender !== anchorConfirmation.sender
    )) throw new Error('저장된 앵커 확인과 새 확인이 다릅니다. 기존 파일을 보존하고 중단합니다.');
  } else {
    checkpoint.mode = 'backfill';
    checkpoint.baseline_path = baselinePath;
    checkpoint.baseline_sha256 = sha256(baselineBuffer);
    checkpoint.baseline_verified_sha256 = verifiedRange.verifiedSha256;
    checkpoint.baseline_manifest_path = verifiedRange.manifestPath;
    checkpoint.baseline_manifest_sha256 = verifiedRange.manifestSha256;
    checkpoint.baseline_range = {
      record_count: verifiedRange.manifest.record_count,
      newest: verifiedRange.manifest.newest,
      oldest: verifiedRange.manifest.oldest,
    };
    checkpoint.anchor_confirmation = null;
    checkpoint.journal_file = path.basename(journalPath);
    await atomicJson(checkpointPath, checkpoint);
  }

  let rows = parseJournal(buffer, journalPath);
  validateSavedPrefix(buffer, checkpoint, rows, journalPath);
  const rowOccurrences = new Map();
  for (let index = 0; index < rows.length; index += 1) {
    const row = rows[index];
    rowOccurrences.set(row.row_sha256, Math.max(rowOccurrences.get(row.row_sha256) ?? 0, row.row_occurrence ?? 1));
    const previousRecord = rows[index - 1] ?? null;
    const duplicateConfirmation = row.baseline_duplicate_confirmation
      ? validateConfirmedBaselineDuplicate({
        rowSha: row.row_sha256,
        bodySha: row.body_sha256,
        body: row.body,
      }, row.baseline_duplicate_confirmation, {
        baselineRows: allBaselineRows,
        verifiedRange,
        anchor,
        previousRecord,
        expectedAfterSequence: row.sequence - 1,
      })
      : null;
    const repeatBodyConfirmation = row.same_body_transition_confirmation
      ? validateConfirmedRepeatBodyTransition({
        rowSha: row.row_sha256,
        bodySha: row.body_sha256,
        body: row.body,
      }, row.same_body_transition_confirmation, {
        baselineRows: allBaselineRows,
        verifiedRange,
        savedRows: rows.slice(0, index),
        previousRecord,
        expectedAfterSequence: row.sequence - 1,
        anchor,
      })
      : null;
    const attachmentReferenceConfirmation = row.attachment_reference_confirmation
      ? validateConfirmedAttachmentReference({
        sequence: row.sequence,
        row_sha256: row.row_sha256,
        body: row.body,
        body_sha256: row.body_sha256,
        capture_status: row.capture_status,
        attachment_filename: row.attachment_filename,
        observed_ui_body_sha256: row.observed_ui_body_sha256,
      }, row.attachment_reference_confirmation, {
        checkpoint,
        baselineRows: allBaselineRows,
        verifiedRange,
        savedRows: rows.slice(0, index),
        previousRecord,
        expectedAfterSequence: row.sequence - 1,
        anchor,
      })
      : null;
    if (row.baseline_duplicate_confirmation && !duplicateConfirmation) {
      throw new Error(`과거 신규 JSONL ${row.sequence}행의 저장된 중복 예외가 바로 앞 행과 연결되지 않습니다.`);
    }
    if (row.same_body_transition_confirmation && !repeatBodyConfirmation) {
      throw new Error(`과거 신규 JSONL ${row.sequence}행의 같은 본문 전환 확인이 직전 행과 연결되지 않습니다.`);
    }
    if (row.attachment_reference_confirmation && !attachmentReferenceConfirmation) {
      throw new Error(`과거 신규 JSONL ${row.sequence}행의 첨부 참조 확인이 UI placeholder와 직전 행에 연결되지 않습니다.`);
    }
    if (
      classifyPreviouslyCapturedSnapshot({ rowSha: row.row_sha256, bodySha: row.body_sha256 }, allBaselineRows).kind !== 'new'
      && !duplicateConfirmation
      && !repeatBodyConfirmation
      && !attachmentReferenceConfirmation
    ) {
      throw new Error(`과거 신규 JSONL ${row.sequence}행이 기존 raw 캡처와 겹치거나 모호합니다. 자동 재개를 멈춥니다.`);
    }
  }

  const advancePastExistingRawTail = async (start, expectedRecord = null) => {
    let cursor = start;
    let skipped = 0;
    let skippedAttachments = 0;
    while (cursor) {
      const attachmentConfirmation = validateConfirmedAttachmentReference(cursor, confirmedAttachmentReference, {
        checkpoint,
        baselineRows: allBaselineRows,
        verifiedRange,
        savedRows: rows,
        previousRecord: rows.at(-1) ?? null,
        expectedAfterSequence: rows.length,
        anchor,
      });
      if (attachmentConfirmation) return { current: cursor, skipped, attachmentConfirmation };
      const duplicateConfirmation = validateConfirmedBaselineDuplicate(cursor, confirmedDistinctCandidate, {
        baselineRows: allBaselineRows,
        verifiedRange,
        anchor,
        previousRecord: rows.at(-1) ?? null,
        expectedAfterSequence: rows.length,
      });
      if (duplicateConfirmation) return { current: cursor, skipped, duplicateConfirmation };
      const isExpectedSavedRecord = expectedRecord
        && cursor.rowSha === expectedRecord.row_sha256
        && cursor.bodySha === expectedRecord.body_sha256;
      if (cursor.body === '?' && cursor.attachmentFilename && !isExpectedSavedRecord) {
        const fingerprint = `${cursor.rowSha}:${cursor.bodySha}`;
        const skippedPairs = checkpoint.skipped_attachment_pairs ?? [];
        if (!skippedPairs.some((item) => `${item.row_sha256}:${item.body_sha256}` === fingerprint)) {
          skippedPairs.push({
            row_sha256: cursor.rowSha,
            body_sha256: cursor.bodySha,
            filename: cursor.attachmentFilename,
          });
          checkpoint.skipped_attachment_pairs = skippedPairs;
          checkpoint.updated_at = new Date().toISOString();
          await atomicJson(checkpointPath, checkpoint);
        }
        const moved = await advanceBackfillAndSettle(cursor);
        if (!moved.moved) return { current: null, skipped, skipped_attachments: skippedAttachments + 1 };
        cursor = moved.current;
        skippedAttachments += 1;
        continue;
      }
      const savedPrevious = expectedRecord
        ? rows[expectedRecord.sequence - 2] ?? null
        : null;
      if (
        expectedRecord?.baseline_duplicate_confirmation
        && cursor.rowSha === expectedRecord.row_sha256
        && cursor.bodySha === expectedRecord.body_sha256
      ) {
        const savedDuplicateConfirmation = validateConfirmedBaselineDuplicate(
          cursor,
          expectedRecord.baseline_duplicate_confirmation,
          {
            baselineRows: allBaselineRows,
            verifiedRange,
            anchor,
            previousRecord: savedPrevious,
            expectedAfterSequence: expectedRecord.sequence - 1,
          },
        );
        if (!savedDuplicateConfirmation) {
          throw new Error(`저장된 중복 예외 ${expectedRecord.sequence}번이 화면 커서와 연결되지 않습니다.`);
        }
        return { current: cursor, skipped, skipped_attachments: skippedAttachments, duplicateConfirmation: savedDuplicateConfirmation };
      }
      if (
        expectedRecord?.same_body_transition_confirmation
        && cursor.rowSha === expectedRecord.row_sha256
        && cursor.bodySha === expectedRecord.body_sha256
      ) {
        const savedRepeatBodyConfirmation = validateConfirmedRepeatBodyTransition(
          cursor,
          expectedRecord.same_body_transition_confirmation,
          {
            baselineRows: allBaselineRows,
            verifiedRange,
            savedRows: rows.slice(0, expectedRecord.sequence - 1),
            previousRecord: savedPrevious,
            expectedAfterSequence: expectedRecord.sequence - 1,
            anchor,
          },
        );
        if (!savedRepeatBodyConfirmation) {
          throw new Error(`저장된 같은 본문 전환 확인 ${expectedRecord.sequence}번이 화면 커서와 연결되지 않습니다.`);
        }
        return { current: cursor, skipped, skipped_attachments: skippedAttachments, repeatBodyConfirmation: savedRepeatBodyConfirmation };
      }
      const classification = classifyPreviouslyCapturedSnapshot(cursor, allBaselineRows);
      if (classification.kind === 'ambiguous') {
        const details = {
          row_sha256: cursor.rowSha,
          body_sha256: cursor.bodySha,
          same_pair_sequences: classification.same_pair_sequences,
          same_body_sequences: classification.sameBody,
          same_row_sequences: classification.sameRow,
          detected_during: 'skip-existing-raw-tail',
          message: '기존 raw 지문과 여러 번 또는 일부만 일치하는 후보입니다. 날짜/발신자와 목록 위치를 확인하기 전까지 저장하지 않습니다.',
        };
        await finishIncrementalStop(checkpoint, checkpointPath, 'paused-ambiguous-existing', details);
        throw new Error(`기존 raw 캡처 ${classification.same_pair_sequences?.length ? '중복 행/본문 쌍' : '행 또는 본문 지문'}과 모호하게 일치합니다. 후보와 기준 순번을 체크포인트에 기록해 안전하게 중단했습니다.`);
      }
      if (classification.kind === 'new' || classification.sequence <= anchor.capture_sequence) {
        return { current: cursor, skipped, skipped_attachments: skippedAttachments };
      }
      if (skipped >= allBaselineRows.length - anchor.capture_sequence) {
        throw new Error('기존 raw 꼬리 재사용 행 수가 기준 길이를 넘었습니다. 안전하게 중단합니다.');
      }
      const moved = await advanceBackfillAndSettle(cursor, expectedRecord);
      if (!moved.moved) return { current: null, skipped: skipped + 1, skipped_attachments: skippedAttachments };
      cursor = moved.current;
      skipped += 1;
    }
    return { current: null, skipped, skipped_attachments: skippedAttachments };
  };
  const advanceBackfillAndSettle = async (previous, expectedRecord = null) => {
    const allowSameBodyTransition = expectedRecord?.same_body_transition_confirmation
      ? (candidate) => Boolean(validateConfirmedRepeatBodyTransition(
        candidate,
        expectedRecord.same_body_transition_confirmation,
        {
          baselineRows: allBaselineRows,
          verifiedRange,
          savedRows: rows.slice(0, expectedRecord.sequence - 1),
          previousRecord: rows[expectedRecord.sequence - 2] ?? null,
          expectedAfterSequence: expectedRecord.sequence - 1,
          anchor,
        },
      ))
      : null;
    try {
      return await advanceAndSettle(sky, window, previous, delayMs, { allowSameBodyTransition });
    } catch (error) {
      await finishIncrementalStop(checkpoint, checkpointPath, 'paused-ui-sync-error', {
        last_stable_row_sha256: previous.rowSha,
        last_stable_body_sha256: previous.bodySha,
        message: error instanceof Error ? error.message : String(error),
      });
      throw error;
    }
  };

  let current = await focusInboxList(sky, window);
  let savedReplayCursor = checkpoint.replay_cursor ?? null;
  let resumeAtReplayCursor = false;
  if (savedReplayCursor) {
    const expectedReplayRecord = rows[savedReplayCursor.sequence - 1] ?? null;
    if (
      checkpoint.status !== 'paused-ui-sync-error'
      || checkpoint.next_row !== null
      || checkpoint.saved_count !== rows.length
      || !Number.isInteger(savedReplayCursor.sequence)
      || !expectedReplayRecord
      || expectedReplayRecord.row_sha256 !== savedReplayCursor.row_sha256
      || expectedReplayRecord.body_sha256 !== savedReplayCursor.body_sha256
    ) throw new Error('저장된 과거 재생 커서와 JSONL 행이 다릅니다. 키 입력 없이 멈춥니다.');
    resumeAtReplayCursor = current.rowSha === savedReplayCursor.row_sha256
      && current.bodySha === savedReplayCursor.body_sha256;
  }
  if (!resumeAtReplayCursor && (
    checkpoint.status === 'paused-ui-sync-error'
    && checkpoint.saved_count === rows.length
    && checkpoint.next_row === null
    && checkpoint.stop_reason?.last_stable_row_sha256
    && checkpoint.stop_reason?.last_stable_body_sha256
  )) {
    const adjacentReplayMatches = rows.filter((record, index) => (
      index > 0
      && record.row_sha256 === current.rowSha
      && record.body_sha256 === current.bodySha
      && rows[index - 1].row_sha256 === checkpoint.stop_reason.last_stable_row_sha256
      && rows[index - 1].body_sha256 === checkpoint.stop_reason.last_stable_body_sha256
    ));
    if (adjacentReplayMatches.length === 1) {
      await saveReplayCursor(checkpointPath, checkpoint, adjacentReplayMatches[0]);
      savedReplayCursor = checkpoint.replay_cursor;
      resumeAtReplayCursor = true;
    } else if (savedReplayCursor) {
      throw new Error('저장된 과거 재생 커서와 현재 화면이 다르고 직전 체크포인트에도 연결되지 않습니다. 키 입력 없이 멈춥니다.');
    }
  }
  const savedCandidate = checkpoint.status === 'paused-oldest-anchor-candidate'
    ? checkpoint.stop_reason
    : null;
  const resumeAtCandidate = savedCandidate
    && current.rowSha === savedCandidate.row_sha256
    && current.bodySha === savedCandidate.body_sha256;
  const savedNext = checkpoint.next_row;
  const lastRecord = rows.at(-1) ?? null;
  let resumeAtLastStableCursor = Boolean(
    checkpoint.status === 'paused-ui-sync-error'
    && checkpoint.saved_count === rows.length
    && checkpoint.next_row === null
    && lastRecord
    && checkpoint.stop_reason?.last_stable_row_sha256 === lastRecord.row_sha256
    && checkpoint.stop_reason?.last_stable_body_sha256 === lastRecord.body_sha256
    && current.bodySha === lastRecord.body_sha256
    && (
      current.rowSha === lastRecord.row_sha256
      || (
        rows.filter((row) => row.body_sha256 === current.bodySha).length === 1
        && classifyPreviouslyCapturedSnapshot(current, allBaselineRows).kind === 'new'
      )
    ),
  );
  if (resumeAtLastStableCursor && current.rowSha !== lastRecord.row_sha256) {
    try {
      const observedDate = await readReceivedDateForSnapshot(sky, window, current, {
        year: receivedDateYear ?? Number(checkpoint.last_received_date?.slice(0, 4) ?? anchor.received_at.slice(0, 4)),
        previousDate: checkpoint.last_received_date ?? null,
      });
      resumeAtLastStableCursor = observedDate === checkpoint.last_received_date;
    } catch {
      resumeAtLastStableCursor = false;
    }
  }
  const confirmedCurrentDuplicate = validateConfirmedBaselineDuplicate(current, confirmedDistinctCandidate, {
    baselineRows: allBaselineRows,
    verifiedRange,
    anchor,
    previousRecord: rows.at(-1) ?? null,
    expectedAfterSequence: rows.length,
  });
  if (confirmedDistinctCandidate && !confirmedCurrentDuplicate) {
    throw new Error('화면의 현재 항목 또는 직전 저장 커서가 취소 쪽지 확인 정보와 다릅니다. 입력 없이 멈춥니다.');
  }
  const confirmedCurrentAttachment = validateConfirmedAttachmentReference(current, confirmedAttachmentReference, {
    checkpoint,
    baselineRows: allBaselineRows,
    verifiedRange,
    savedRows: rows,
    previousRecord: rows.at(-1) ?? null,
    expectedAfterSequence: rows.length,
    anchor,
  });
  if (confirmedAttachmentReference && !confirmedCurrentAttachment) {
    throw new Error('화면의 첨부 전용 쪽지 또는 직전 저장 커서가 확인 정보와 다릅니다. 키 입력 없이 멈춥니다.');
  }
  const resumeAtCommittedAttachmentCursor = Boolean(
    lastRecord?.capture_status === 'attachment-reference-only'
    && checkpoint.saved_count === rows.length
    && checkpoint.next_row === null
    && current.body === '?'
    && current.rowSha === lastRecord.row_sha256
    && current.bodySha === lastRecord.observed_ui_body_sha256
    && current.attachmentFilename === lastRecord.attachment_filename,
  );
  const resumeAtConfirmedAttachment = Boolean(
    confirmedCurrentAttachment
    && checkpoint.status === 'paused-ambiguous-existing'
    && checkpoint.saved_count === rows.length
    && checkpoint.next_row === null,
  );
  const confirmedCurrentRepeatBody = validateConfirmedRepeatBodyTransition(current, confirmedRepeatBodyCandidate, {
    baselineRows: allBaselineRows,
    verifiedRange,
    savedRows: rows,
    previousRecord: rows.at(-1) ?? null,
    expectedAfterSequence: rows.length,
    anchor,
  });
  if (confirmedRepeatBodyCandidate && (
    !confirmedCurrentRepeatBody
    || checkpoint.status !== 'paused-ui-sync-error'
    || checkpoint.saved_count !== rows.length
    || checkpoint.next_row !== null
    || checkpoint.stop_reason?.last_stable_row_sha256 !== rows.at(-1)?.row_sha256
    || checkpoint.stop_reason?.last_stable_body_sha256 !== rows.at(-1)?.body_sha256
  )) throw new Error('같은 본문 전환 후보가 저장된 UI 동기화 중단 지점과 일치하지 않습니다. 입력 없이 멈춥니다.');
  const resumeAtConfirmedDuplicate = Boolean(
    confirmedCurrentDuplicate
    && rows.length > 0
    && checkpoint.saved_count === rows.length
    && checkpoint.next_row === null,
  );
  const resumeAtConfirmedRepeatBody = Boolean(confirmedCurrentRepeatBody);
  const resumeAtNextCursor = !resumeAtReplayCursor
    && !resumeAtCandidate
    && !resumeAtConfirmedAttachment
    && !resumeAtCommittedAttachmentCursor
    && !resumeAtConfirmedRepeatBody
    && Boolean(checkpoint.anchor_confirmation)
    && savedNext
    && savedNext.sequence === rows.length + 1
    && savedNext.row_occurrence === (rowOccurrences.get(savedNext.row_sha256) ?? 0) + 1
    && current.rowSha === savedNext.row_sha256
    && current.bodySha === savedNext.body_sha256;
  // If the operator already inspected this candidate and the live selection
  // still matches it, continue from that exact row instead of rescanning Home.
  let scanned = resumeAtCandidate ? (savedCandidate.scanned_rows ?? 1) : 1;
  if (!resumeAtReplayCursor && !resumeAtCandidate && !resumeAtNextCursor && !resumeAtLastStableCursor && !resumeAtConfirmedDuplicate && !resumeAtConfirmedRepeatBody
    && !resumeAtConfirmedAttachment && !resumeAtCommittedAttachmentCursor) {
    let state = await latestState(sky, window);
    if (!isInboxRowFocus(state)) throw new Error('Home 입력 전 받은쪽지 목록 행 포커스를 확인하지 못했습니다.');
    const beforeHome = current;
    await sky.press_key({ window, key: 'Home' });
    current = await stableSnapshot(sky, window, { delayMs, after: beforeHome, maxAttempts: 16 });
    state = await latestState(sky, window);
    if (!isInboxRowFocus(state)) throw new Error('Home 입력 뒤 받은쪽지 목록 행 포커스를 확인하지 못했습니다.');
  }

  while (!resumeAtReplayCursor && !resumeAtNextCursor && !resumeAtLastStableCursor && !resumeAtConfirmedDuplicate && !resumeAtConfirmedRepeatBody
    && !resumeAtConfirmedAttachment && !resumeAtCommittedAttachmentCursor
    && (current.rowSha !== anchorRaw.row_sha256 || current.bodySha !== anchorRaw.body_sha256)) {
    if (scanned >= maxAnchorScanRows) {
      await finishIncrementalStop(checkpoint, checkpointPath, 'paused-anchor-not-found', {
        scanned_rows: scanned,
        message: '최오래된 보관 경계를 안전 탐색 한도 안에서 찾지 못했습니다. 저장을 시작하지 않았습니다.',
        expected: verifiedMessageAt(verifiedRange, anchor.capture_sequence),
      });
      return { count: 0, total: rows.length, status: checkpoint.status, journalPath, checkpointPath };
    }
    const moved = await advanceBackfillAndSettle(current);
    if (!moved.moved) {
      await finishIncrementalStop(checkpoint, checkpointPath, 'paused-anchor-not-found', {
        scanned_rows: scanned,
        message: '최오래된 보관 경계 전에 목록 끝에 도달했습니다. 저장을 시작하지 않았습니다.',
        expected: verifiedMessageAt(verifiedRange, anchor.capture_sequence),
      });
      return { count: 0, total: rows.length, status: checkpoint.status, journalPath, checkpointPath };
    }
    current = moved.current;
    scanned += 1;
  }

  if (!resumeAtReplayCursor && !resumeAtNextCursor && !resumeAtLastStableCursor && !resumeAtConfirmedDuplicate && !resumeAtConfirmedRepeatBody
    && !resumeAtConfirmedAttachment && !resumeAtCommittedAttachmentCursor) {
    const expectedAnchor = verifiedMessageAt(verifiedRange, anchor.capture_sequence);
    if (!checkpoint.anchor_confirmation && !anchorConfirmation) {
      await finishIncrementalStop(checkpoint, checkpointPath, 'paused-oldest-anchor-candidate', {
        scanned_rows: scanned,
        anchor: expectedAnchor,
        row_sha256: current.rowSha,
        body_sha256: current.bodySha,
        row_text: current.row,
        message: '경계 후보를 찾았습니다. 화면의 날짜와 발신자를 매니페스트와 대조한 뒤 다시 실행하세요. 아직 쪽지를 저장하지 않았습니다.',
      });
      return { count: 0, total: rows.length, status: checkpoint.status, journalPath, checkpointPath };
    }
    if (anchorConfirmation) {
      checkpoint.anchor_confirmation = {
        ...anchorConfirmation,
        row_sha256: anchor.row_sha256,
        body_sha256: anchor.body_sha256,
        confirmed_at: new Date().toISOString(),
        confirmation_method: 'visible-date-and-sender-compared-by-operator',
      };
      await atomicJson(checkpointPath, checkpoint);
    }

    const afterAnchor = await advanceBackfillAndSettle(current);
    if (!afterAnchor.moved) {
      await finishIncrementalStop(checkpoint, checkpointPath, 'paused-oldest-reached', {
        anchor: expectedAnchor,
        message: '기준 범위가 목록의 가장 오래된 쪽지였습니다. 이전 쪽지가 없습니다.',
      });
      return { count: 0, total: rows.length, status: checkpoint.status, journalPath, checkpointPath };
    }
    current = afterAnchor.current;

    // If no exact next cursor is available, re-find the anchor and verify the
    // committed older prefix before continuing.
    for (let index = 0; index < rows.length; index += 1) {
      const expected = rows[index];
      const uncaptured = await advancePastExistingRawTail(current, expected);
      if (!uncaptured.current) {
        throw new Error(`기존 raw 캡처 뒤에서 저장된 과거 캡처 ${index + 1}행을 찾기 전에 목록 끝에 도달했습니다.`);
      }
      current = uncaptured.current;
      if (current.rowSha !== expected.row_sha256 || current.bodySha !== expected.body_sha256) {
        throw new Error(`최오래된 기준 뒤의 저장 쪽지 ${index + 1}행 지문이 바뀌었습니다. 이어 쓰지 않고 중단합니다.`);
      }
      await saveReplayCursor(checkpointPath, checkpoint, expected);
      if (index < rows.length - 1) {
        const moved = await advanceBackfillAndSettle(current, rows[index + 1]);
        if (!moved.moved) throw new Error(`과거 캡처 재개 위치를 찾기 전에 ${index + 1}행 다음에서 멈췄습니다.`);
        current = moved.current;
      }
    }
    if (rows.length) {
      const next = await advanceBackfillAndSettle(current);
      if (!next.moved) {
        await finishIncrementalStop(checkpoint, checkpointPath, 'paused-oldest-reached', {
          last_saved_sequence: rows.length,
          message: '저장한 쪽지 뒤에 더 오래된 항목이 없습니다.',
        });
        return { count: 0, total: rows.length, status: checkpoint.status, journalPath, checkpointPath };
      }
      current = next.current;
    }
  }

  if (resumeAtReplayCursor) {
    for (let sequence = savedReplayCursor.sequence + 1; sequence <= rows.length; sequence += 1) {
      const expected = rows[sequence - 1];
      const moved = await advanceBackfillAndSettle(current, expected);
      if (!moved.moved) throw new Error(`저장된 과거 재생 커서 ${sequence - 1}번 뒤에서 목록이 끝났습니다.`);
      current = moved.current;
      if (current.rowSha !== expected.row_sha256 || current.bodySha !== expected.body_sha256) {
        throw new Error(`저장된 과거 재생 커서 뒤의 ${sequence}번 행이 일치하지 않습니다. 캡처하지 않고 중단합니다.`);
      }
      await saveReplayCursor(checkpointPath, checkpoint, expected);
    }
    if (rows.length) {
      const next = await advanceBackfillAndSettle(current);
      if (!next.moved) {
        await finishIncrementalStop(checkpoint, checkpointPath, 'paused-oldest-reached', {
          last_saved_sequence: rows.length,
          message: '저장한 쪽지 뒤에 더 오래된 항목이 없습니다.',
        });
        return { count: 0, total: rows.length, status: checkpoint.status, journalPath, checkpointPath };
      }
      current = next.current;
    }
  }

  if (resumeAtCommittedAttachmentCursor) {
    const next = await advanceBackfillAndSettle(current);
    if (!next.moved) {
      await finishIncrementalStop(checkpoint, checkpointPath, 'paused-oldest-reached', {
        last_saved_sequence: rows.length,
        message: '이미 기록한 첨부 참조 다음에 더 오래된 쪽지가 없습니다.',
      });
      return { count: 0, total: rows.length, status: checkpoint.status, journalPath, checkpointPath };
    }
    current = next.current;
  }

  if (resumeAtLastStableCursor) {
    const next = await advanceBackfillAndSettle(current);
    if (!next.moved) {
      await finishIncrementalStop(checkpoint, checkpointPath, 'paused-oldest-reached', {
        last_saved_sequence: rows.length,
        message: '마지막으로 확인한 쪽지 다음에 더 오래된 항목이 없습니다.',
      });
      return { count: 0, total: rows.length, status: checkpoint.status, journalPath, checkpointPath };
    }
    current = next.current;
  }

  const firstUncaptured = await advancePastExistingRawTail(current);
  if (!firstUncaptured.current) {
    await finishIncrementalStop(checkpoint, checkpointPath, 'paused-oldest-reached', {
      last_saved_sequence: rows.length,
      skipped_existing_raw_rows: firstUncaptured.skipped,
      message: '기존 raw 캡처의 미검증 꼬리를 건너뛴 뒤 목록 끝에 도달했습니다.',
    });
    return { count: 0, total: rows.length, status: checkpoint.status, journalPath, checkpointPath };
  }
  current = firstUncaptured.current;
  await saveNextCursor(
    checkpointPath,
    checkpoint,
    current,
    rows.length + 1,
    (rowOccurrences.get(current.rowSha) ?? 0) + 1,
  );

  const startedCount = rows.length;
  let repeatBodyConfirmationPending = Boolean(confirmedCurrentRepeatBody);
  let attachmentReferenceConfirmationPending = firstUncaptured.attachmentConfirmation ?? null;
  while (rows.length - startedCount < maxItems) {
    const duplicateConfirmation = validateConfirmedBaselineDuplicate(current, confirmedDistinctCandidate, {
      baselineRows: allBaselineRows,
      verifiedRange,
      anchor,
      previousRecord: rows.at(-1) ?? null,
      expectedAfterSequence: rows.length,
    });
    const known = attachmentReferenceConfirmationPending
      ? { kind: 'new' }
      : classifyKnownSnapshot(current, trustedBaselineRows);
    if (known.kind === 'known' && !duplicateConfirmation) {
      await finishIncrementalStop(checkpoint, checkpointPath, 'paused-baseline-overlap', {
        baseline_sequence: known.sequence,
        baseline_message: verifiedMessageAt(verifiedRange, known.sequence),
        row_sha256: current.rowSha,
        body_sha256: current.bodySha,
        message: '최오래된 경계를 지난 뒤 기준 범위 쪽지가 다시 나타났습니다. 순서가 예상과 달라 저장을 멈췄습니다.',
      });
      return { count: rows.length - startedCount, total: rows.length, status: checkpoint.status, journalPath, checkpointPath };
    }
    if (known.kind === 'ambiguous' && !duplicateConfirmation) {
      await finishIncrementalStop(checkpoint, checkpointPath, 'paused-ambiguous-existing', {
        same_body_sequences: known.sameBody,
        same_row_sequences: known.sameRow,
        row_sha256: current.rowSha,
        body_sha256: current.bodySha,
        message: '기존 기준과 행 또는 본문 지문만 겹칩니다. 저장하지 않고 멈췄습니다.',
      });
      return { count: rows.length - startedCount, total: rows.length, status: checkpoint.status, journalPath, checkpointPath };
    }

    const occurrence = (rowOccurrences.get(current.rowSha) ?? 0) + 1;
    const attachmentReference = attachmentReferenceConfirmationPending;
    const receivedDate = await dateForRecord(sky, window, current, checkpoint, {
      year: receivedDateYear ?? Number(anchor.received_at.slice(0, 4)),
      reader: dateReader,
      checkpointPath,
    });
    const senderCapture = await senderForRecord(sky, window, current, checkpoint, {
      reader: senderReader,
      checkpointPath,
    });
    const expectedSenders = [
      attachmentReference?.sender,
      duplicateConfirmation?.sender,
      confirmedCurrentRepeatBody?.sender,
    ].filter((value) => typeof value === 'string' && value.trim());
    if (expectedSenders.some((value) => value !== senderCapture.sender)) {
      await finishIncrementalStop(checkpoint, checkpointPath, 'paused-confirmation-sender-mismatch', {
        expected_senders: [...new Set(expectedSenders)],
        observed_sender: senderCapture.sender,
        row_sha256: current.rowSha,
        body_sha256: current.bodySha,
        message: '기존 중복/첨부 확인 발신자와 화면에서 확인한 발신자가 다릅니다. 저장하지 않고 멈췄습니다.',
      });
      throw new Error('중복/첨부 확인 발신자와 화면 발신자가 다릅니다. 저장하지 않고 멈췄습니다.');
    }
    if (duplicateConfirmation && duplicateConfirmation.received_date !== receivedDate) {
      await finishIncrementalStop(checkpoint, checkpointPath, 'paused-confirmation-date-mismatch', {
        expected_received_date: duplicateConfirmation.received_date,
        observed_received_date: receivedDate,
        row_sha256: current.rowSha,
        body_sha256: current.bodySha,
        message: '중복 예외 확인 날짜와 화면 OCR 날짜가 다릅니다. 저장하지 않고 멈췄습니다.',
      });
      throw new Error('취소 placeholder 확인 날짜와 화면 OCR 날짜가 다릅니다. 저장하지 않고 멈췄습니다.');
    }
    const recordBody = attachmentReference
      ? `첨부파일 참조: ${attachmentReference.filename}`
      : current.body;
    const record = {
      sequence: rows.length + 1,
      row_sha256: current.rowSha,
      row_occurrence: occurrence,
      received_date: receivedDate,
      sender: senderCapture.sender,
      sender_evidence: senderCapture.evidence,
      ...(current.receivedDateEvidence ? { received_date_verification: current.receivedDateEvidence } : {}),
      body: recordBody,
      body_sha256: sha256(recordBody),
      captured_at: new Date().toISOString(),
      source: 'gbtalk-message-manager-uia-keyboard-backfill',
      capture_status: attachmentReference
        ? 'attachment-reference-only'
        : current.body === '취소된 메시지입니다.' ? 'recalled-placeholder' : 'captured',
      ...(attachmentReference ? {
        attachment_filename: attachmentReference.filename,
        observed_ui_body_sha256: current.bodySha,
        received_at: attachmentReference.received_at,
        sender: attachmentReference.sender,
        attachment_reference_confirmation: attachmentReference,
      } : {}),
      ...(duplicateConfirmation ? {
        sender: duplicateConfirmation.sender,
        baseline_duplicate_confirmation: duplicateConfirmation,
      } : {}),
      ...(repeatBodyConfirmationPending && confirmedCurrentRepeatBody ? {
        received_at: confirmedCurrentRepeatBody.received_at,
        sender: confirmedCurrentRepeatBody.sender,
        same_body_transition_confirmation: confirmedCurrentRepeatBody,
      } : {}),
    };
    await commitRecord(journalPath, checkpointPath, checkpoint, record);
    rows.push(record);
    repeatBodyConfirmationPending = false;
    attachmentReferenceConfirmationPending = null;
    rowOccurrences.set(current.rowSha, occurrence);

    const moved = await advanceBackfillAndSettle(current);
    if (!moved.moved) {
      await finishIncrementalStop(checkpoint, checkpointPath, 'paused-oldest-reached', {
        last_saved_sequence: rows.length,
        message: '목록의 가장 오래된 항목까지 저장했습니다.',
      });
      return { count: rows.length - startedCount, total: rows.length, status: checkpoint.status, journalPath, checkpointPath };
    }
    const nextUncaptured = await advancePastExistingRawTail(moved.current);
    if (!nextUncaptured.current) {
      await finishIncrementalStop(checkpoint, checkpointPath, 'paused-oldest-reached', {
        last_saved_sequence: rows.length,
        skipped_existing_raw_rows: nextUncaptured.skipped,
        message: '기존 raw 캡처의 미검증 꼬리를 건너뛴 뒤 목록의 가장 오래된 항목까지 저장했습니다.',
      });
      return { count: rows.length - startedCount, total: rows.length, status: checkpoint.status, journalPath, checkpointPath };
    }
    current = nextUncaptured.current;
    await saveNextCursor(
      checkpointPath,
      checkpoint,
      current,
      rows.length + 1,
      (rowOccurrences.get(current.rowSha) ?? 0) + 1,
    );
    if (rows.length - startedCount >= maxItems) {
      const nextKnown = classifyKnownSnapshot(current, trustedBaselineRows);
      if (nextKnown.kind === 'known') {
        await finishIncrementalStop(checkpoint, checkpointPath, 'paused-baseline-overlap', {
          baseline_sequence: nextKnown.sequence,
          baseline_message: verifiedMessageAt(verifiedRange, nextKnown.sequence),
          row_sha256: current.rowSha,
          body_sha256: current.bodySha,
        });
      } else if (nextKnown.kind === 'ambiguous') {
        await finishIncrementalStop(checkpoint, checkpointPath, 'paused-ambiguous-existing', {
          same_body_sequences: nextKnown.sameBody,
          same_row_sequences: nextKnown.sameRow,
          row_sha256: current.rowSha,
          body_sha256: current.bodySha,
        });
      } else {
        checkpoint.status = 'paused-batch-complete';
        checkpoint.updated_at = new Date().toISOString();
        await atomicJson(checkpointPath, checkpoint);
      }
      return { count: rows.length - startedCount, total: rows.length, status: checkpoint.status, journalPath, checkpointPath };
    }
  }

  return { count: rows.length - startedCount, total: rows.length, status: checkpoint.status, journalPath, checkpointPath };
}
