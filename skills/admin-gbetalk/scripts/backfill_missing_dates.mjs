// Fill missing received dates in a separate, resumable sidecar.
// The source JSONL is read-only; this module never opens message actions or attachments.

import fs from 'node:fs/promises';
import path from 'node:path';
import crypto from 'node:crypto';
import {
  isInboxRowFocus,
  readReceivedDateForSnapshot,
  snapshotFromState,
} from './capture_macro.mjs';

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
const sha256 = (value) => crypto.createHash('sha256').update(value).digest('hex');

function parseJournal(buffer, filePath) {
  if (!buffer.length) throw new Error(`원본 JSONL이 비어 있습니다: ${filePath}`);
  if (!buffer.toString('utf8').endsWith('\n')) {
    throw new Error(`원본 JSONL 마지막 행이 온전하지 않습니다. 변경하지 않고 멈춥니다: ${filePath}`);
  }
  const rows = buffer.toString('utf8').trimEnd().split(/\r?\n/u).map((line, index) => {
    let row;
    try { row = JSON.parse(line); }
    catch (error) { throw new Error(`JSONL ${index + 1}행을 읽지 못했습니다: ${error.message}`); }
    if (row.sequence !== index + 1 || !/^[a-f0-9]{64}$/u.test(row.row_sha256 ?? '')
      || !/^[a-f0-9]{64}$/u.test(row.body_sha256 ?? '')
      || typeof row.body !== 'string'
      || sha256(row.body) !== row.body_sha256) {
      throw new Error(`JSONL ${index + 1}행의 순번 또는 본문 지문이 올바르지 않습니다.`);
    }
    return row;
  });
  return rows;
}

function dateValue(row) {
  const value = row.received_date ?? row.received_at?.slice(0, 10) ?? null;
  if (value === null) return null;
  if (typeof value !== 'string' || !/^\d{4}-\d{2}-\d{2}$/u.test(value)
    || new Date(`${value}T00:00:00Z`).toISOString().slice(0, 10) !== value) {
    throw new Error(`${row.sequence}번의 기존 날짜 형식이 올바르지 않습니다: ${value}`);
  }
  return value;
}

async function atomicJson(filePath, value) {
  const tempPath = `${filePath}.${crypto.randomUUID()}.tmp`;
  const handle = await fs.open(tempPath, 'wx');
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
  throw lastError;
}

function samePair(snapshot, row) {
  return snapshot.rowSha === row.row_sha256 && snapshot.bodySha === row.body_sha256;
}

function pairFor(row) {
  return { row_sha256: row.row_sha256, body_sha256: row.body_sha256 };
}

function validateMap(map, { dataset, sourcePath, sourceHash, rows, targetSequenceMax }) {
  if (map.schema_version !== 1 || map.dataset !== dataset
    || map.source_path !== sourcePath || map.source_file_sha256 !== sourceHash
    || map.total_rows !== rows.length || map.target_sequence_max !== targetSequenceMax
    || !Array.isArray(map.records)) {
    throw new Error('날짜 매핑 파일의 원본 연결 정보가 다릅니다. 덮어쓰지 않고 멈춥니다.');
  }
  const seen = new Set();
  for (const record of map.records) {
    const source = rows[record.sequence - 1];
    if (!source || seen.has(record.sequence)
      || source.row_sha256 !== record.row_sha256
      || source.body_sha256 !== record.body_sha256
      || !/^\d{4}-\d{2}-\d{2}$/u.test(record.received_date ?? '')
      || new Date(`${record.received_date}T00:00:00Z`).toISOString().slice(0, 10) !== record.received_date) {
      throw new Error(`날짜 매핑 ${record.sequence}번의 순번/지문/날짜가 원본과 맞지 않습니다.`);
    }
    seen.add(record.sequence);
  }
  if (map.cursor) {
    const source = rows[map.cursor.sequence - 1];
    if (!source || source.row_sha256 !== map.cursor.row_sha256
      || source.body_sha256 !== map.cursor.body_sha256) {
      throw new Error('저장된 날짜 재개 커서가 원본 지문과 다릅니다. 키 입력 없이 멈춥니다.');
    }
  }
  if (map.navigation_pending) {
    const { from_sequence: from, to_sequence: to } = map.navigation_pending;
    if (to !== from - 1 || !rows[from - 1] || !rows[to - 1]
      || rows[from - 1].row_sha256 !== map.navigation_pending.from_row_sha256
      || rows[from - 1].body_sha256 !== map.navigation_pending.from_body_sha256
      || rows[to - 1].row_sha256 !== map.navigation_pending.to_row_sha256
      || rows[to - 1].body_sha256 !== map.navigation_pending.to_body_sha256) {
      throw new Error('저장된 이동 전 체크포인트가 원본 순번과 다릅니다. 키 입력 없이 멈춥니다.');
    }
  }
}

async function stableExpectedState(sky, window, expected, { delayMs = 100, attempts = 18 } = {}) {
  let consecutive = 0;
  for (let attempt = 0; attempt < attempts; attempt += 1) {
    await sleep(delayMs);
    const state = await sky.get_window_state({ window, include_text: true, include_screenshot: false });
    if (!isInboxRowFocus(state)) {
      throw new Error(`쪽지 행 포커스를 잃었습니다. 추가 키 입력 없이 멈춥니다: ${state.accessibility?.focused_element ?? '(없음)'}`);
    }
    let observed;
    try { observed = snapshotFromState(state); }
    catch { consecutive = 0; continue; }
    if (samePair(observed, expected)) {
      consecutive += 1;
      if (consecutive >= 2) return { state, snapshot: observed };
    } else {
      consecutive = 0;
    }
  }
  throw new Error(`↑ 이동 결과가 예상한 다음 행/본문과 안정적으로 일치하지 않습니다 (sequence ${expected.sequence ?? '?'})`);
}

function matchingSkip(snapshot, skipPairs) {
  return skipPairs.find((pair) => (
    snapshot.rowSha === pair.row_sha256 && snapshot.bodySha === pair.body_sha256
  )) ?? null;
}

async function stableExpectedOrSkip(sky, window, expected, skipPairs, { delayMs = 100, attempts = 18 } = {}) {
  let candidate = null;
  let consecutive = 0;
  for (let attempt = 0; attempt < attempts; attempt += 1) {
    await sleep(delayMs);
    const state = await sky.get_window_state({ window, include_text: true, include_screenshot: false });
    if (!isInboxRowFocus(state)) {
      throw new Error(`쪽지 행 포커스를 잃었습니다. 추가 키 입력 없이 멈춥니다: ${state.accessibility?.focused_element ?? '(없음)'}`);
    }
    let snapshot;
    try { snapshot = snapshotFromState(state); }
    catch { candidate = null; consecutive = 0; continue; }
    const skip = matchingSkip(snapshot, skipPairs);
    const kind = samePair(snapshot, expected) ? 'expected' : skip ? 'known-skip' : null;
    if (!kind) {
      candidate = null;
      consecutive = 0;
      continue;
    }
    const identicalCandidate = candidate?.kind === kind
      && candidate.snapshot.rowSha === snapshot.rowSha
      && candidate.snapshot.bodySha === snapshot.bodySha;
    consecutive = identicalCandidate ? consecutive + 1 : 1;
    candidate = { kind, skip, snapshot, state };
    if (consecutive >= 2) return candidate;
  }
  throw new Error(`↑ 이동 결과가 예상 행 또는 사전 확인된 제외 첨부 지문과 안정적으로 일치하지 않습니다 (sequence ${expected.sequence ?? '?'})`);
}

async function settleNextSequence(sky, window, expected, skipPairs, { delayMs = 100 } = {}) {
  const skipped = [];
  const maxSkips = Math.min(skipPairs.length, 6);
  for (let count = 0; count <= maxSkips; count += 1) {
    const settled = await stableExpectedOrSkip(sky, window, expected, skipPairs, { delayMs });
    if (settled.kind === 'expected') return { ...settled, skipped };
    skipped.push(settled.skip);
    if (count === maxSkips) break;
    // This exact message is already listed as an excluded attachment. Keep it unopened and move on.
    await sky.press_key({ window, key: 'Up' });
  }
  throw new Error(`사전 확인된 제외 첨부 항목이 ${maxSkips}개를 넘어 예상 순번에 도달하지 못했습니다.`);
}

export async function backfillMissingDates({
  sky,
  window,
  journalPath,
  mapPath,
  dataset = 'older-backfill',
  startSequence,
  targetSequenceMax,
  stopSequence = 1,
  maxRows = 30,
  delayMs = 100,
  year = 2026,
  skipPairs = [],
  monthCorrection = null,
  manualOverrides = [],
}) {
  if (!sky || !window || !journalPath || !mapPath) {
    throw new Error('sky, window, journalPath, mapPath가 필요합니다.');
  }
  if (!Number.isInteger(maxRows) || maxRows < 1 || maxRows > 30) {
    throw new Error('날짜 보완 배치는 1~30개 행으로 제한합니다.');
  }
  if (!Number.isInteger(targetSequenceMax) || targetSequenceMax < stopSequence) {
    throw new Error('대상 순번 범위가 올바르지 않습니다.');
  }

  const sourcePath = path.resolve(journalPath);
  const outputPath = path.resolve(mapPath);
  const sourceBuffer = await fs.readFile(sourcePath);
  const sourceHash = sha256(sourceBuffer);
  const rows = parseJournal(sourceBuffer, sourcePath);
  if (targetSequenceMax > rows.length || stopSequence < 1) {
    throw new Error('대상 순번이 원본 JSONL 범위를 벗어났습니다.');
  }
  const sourceDir = path.dirname(sourcePath);
  const inside = (rel) => rel === '' || (rel !== '..' && !rel.startsWith(`..${path.sep}`) && !path.isAbsolute(rel));
  if (inside(path.relative(sourceDir, outputPath)) || inside(path.relative(outputPath, sourceDir))) {
    throw new Error('날짜 매핑 파일은 원본 JSONL 폴더와 분리된 경로여야 합니다.');
  }
  const normalizedSkipPairs = skipPairs.map((pair) => ({
    row_sha256: pair.row_sha256,
    body_sha256: pair.body_sha256,
    filename: pair.filename ?? null,
  }));
  if (normalizedSkipPairs.some((pair) => !/^[a-f0-9]{64}$/u.test(pair.row_sha256 ?? '')
    || !/^[a-f0-9]{64}$/u.test(pair.body_sha256 ?? ''))) {
    throw new Error('제외 첨부 목록에 유효하지 않은 행/본문 지문이 있습니다.');
  }
  for (const override of manualOverrides) {
    const source = rows[override.sequence - 1];
    if (!source || override.sequence > targetSequenceMax
      || source.row_sha256 !== override.row_sha256
      || source.body_sha256 !== override.body_sha256
      || !/^\d{4}-\d{2}-\d{2}$/u.test(override.received_date ?? '')
      || new Date(`${override.received_date}T00:00:00Z`).toISOString().slice(0, 10) !== override.received_date
      || typeof override.visible_header !== 'string' || !override.visible_header.trim()) {
      throw new Error(`수동 날짜 확인 ${override.sequence ?? '?'}번의 원본 지문/날짜/머리글이 올바르지 않습니다.`);
    }
  }

  await fs.mkdir(path.dirname(outputPath), { recursive: true });
  let map;
  try { map = JSON.parse(await fs.readFile(outputPath, 'utf8')); }
  catch (error) {
    if (error.code !== 'ENOENT') throw new Error(`기존 날짜 매핑을 읽지 못했습니다: ${error.message}`);
    map = {
      schema_version: 1,
      dataset,
      source_path: sourcePath,
      source_file_sha256: sourceHash,
      total_rows: rows.length,
      target_sequence_max: targetSequenceMax,
      target_stop_sequence: stopSequence,
      date_policy: '화면 머리글에서 확인한 메시지 날짜만 저장. captured_at은 메시지 날짜로 사용하지 않는다.',
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      status: 'ready',
      cursor: null,
      navigation_pending: null,
      pending_date: null,
      skip_pairs: normalizedSkipPairs,
      skipped_ui_items: [],
      records: [],
    };
  }
  validateMap(map, { dataset, sourcePath, sourceHash, rows, targetSequenceMax });
  if (map.target_stop_sequence !== stopSequence) throw new Error('날짜 매핑의 종료 순번 설정이 다릅니다.');
  let migratedSkipCheckpoint = false;
  if (map.skip_pairs === undefined && map.records.length === 0 && map.skipped_ui_items === undefined) {
    map.skip_pairs = normalizedSkipPairs;
    map.skipped_ui_items = [];
    migratedSkipCheckpoint = true;
  }
  if (JSON.stringify(map.skip_pairs ?? []) !== JSON.stringify(normalizedSkipPairs)) {
    throw new Error('재개 시 지정한 제외 첨부 지문이 날짜 매핑 체크포인트와 다릅니다.');
  }
  if (!Array.isArray(map.skipped_ui_items)) throw new Error('건너뛴 제외 첨부 체크포인트가 배열이 아닙니다.');

  const persist = async () => {
    map.updated_at = new Date().toISOString();
    await atomicJson(outputPath, map);
  };
  if (migratedSkipCheckpoint) await persist();
  const status = async (value, message, detail = {}) => {
    map.status = value;
    map.last_error = { message, at: new Date().toISOString(), ...detail };
    await persist();
    throw new Error(message);
  };
  const observedState = await sky.get_window_state({ window, include_text: true, include_screenshot: false });
  if (!isInboxRowFocus(observedState)) {
    return status('paused-focus-mismatch', '현재 키보드 포커스가 받은 쪽지 행이 아닙니다.', {
      focused_element: observedState.accessibility?.focused_element ?? null,
    });
  }
  let current;
  try { current = snapshotFromState(observedState); }
  catch (error) { return status('paused-ui-mismatch', error.message); }

  let sequence;
  let compareFromDate = null;
  if (map.navigation_pending) {
    const pending = map.navigation_pending;
    const fromRow = rows[pending.from_sequence - 1];
    const toRow = rows[pending.to_sequence - 1];
    if (samePair(current, toRow)) {
      sequence = pending.to_sequence;
      compareFromDate = pending.from_received_date;
    } else if (samePair(current, fromRow)) {
      if (!samePair(current, map.cursor)) return status('paused-ui-mismatch', '이동 전 행/본문이 저장 커서와 다릅니다.');
      await sky.press_key({ window, key: 'Up' });
      let settled;
      try { settled = await settleNextSequence(sky, window, { ...toRow, sequence: pending.to_sequence }, normalizedSkipPairs, { delayMs }); }
      catch (error) { return status('paused-ui-mismatch', error.message, { from_sequence: pending.from_sequence, to_sequence: pending.to_sequence }); }
      current = settled.snapshot;
      for (const skipped of settled.skipped) {
        const entry = {
          from_sequence: pending.from_sequence,
          to_sequence: pending.to_sequence,
          ...skipped,
          observed_at: new Date().toISOString(),
        };
        if (map.skipped_ui_items.some((item) => item.row_sha256 === entry.row_sha256 && item.body_sha256 === entry.body_sha256)) {
          return status('paused-repeated-skipped-item', '이미 건너뛴 제외 첨부 항목이 다시 나타나 원본 순번 대조를 멈췄습니다.', entry);
        }
        map.skipped_ui_items.push(entry);
      }
      await persist();
      sequence = pending.to_sequence;
      compareFromDate = pending.from_received_date;
    } else if (matchingSkip(current, normalizedSkipPairs)) {
      let settled;
      try { settled = await settleNextSequence(sky, window, { ...toRow, sequence: pending.to_sequence }, normalizedSkipPairs, { delayMs }); }
      catch (error) { return status('paused-ui-mismatch', error.message, { from_sequence: pending.from_sequence, to_sequence: pending.to_sequence }); }
      current = settled.snapshot;
      for (const skipped of settled.skipped) {
        const entry = {
          from_sequence: pending.from_sequence,
          to_sequence: pending.to_sequence,
          ...skipped,
          observed_at: new Date().toISOString(),
        };
        if (map.skipped_ui_items.some((item) => item.row_sha256 === entry.row_sha256 && item.body_sha256 === entry.body_sha256)) {
          return status('paused-repeated-skipped-item', '이미 건너뛴 제외 첨부 항목이 다시 나타나 원본 순번 대조를 멈췄습니다.', entry);
        }
        map.skipped_ui_items.push(entry);
      }
      await persist();
      sequence = pending.to_sequence;
      compareFromDate = pending.from_received_date;
    } else {
      return status('paused-ui-mismatch', '화면이 저장된 이동 전/후 순번 어느 쪽과도 맞지 않습니다.', {
        observed_row_sha256: current.rowSha,
        observed_body_sha256: current.bodySha,
        from_sequence: pending.from_sequence,
        to_sequence: pending.to_sequence,
      });
    }
  } else if (map.cursor) {
    sequence = map.cursor.sequence;
    if (!samePair(current, map.cursor)) {
      return status('paused-ui-mismatch', '현재 화면이 저장된 날짜 재개 커서와 다릅니다.', {
        expected_sequence: sequence,
        observed_row_sha256: current.rowSha,
        observed_body_sha256: current.bodySha,
      });
    }
  } else {
    sequence = startSequence;
    if (!Number.isInteger(sequence) || sequence < stopSequence || sequence > rows.length) {
      return status('paused-ui-mismatch', '첫 실행에 필요한 시작 순번이 올바르지 않습니다.');
    }
    if (!samePair(current, rows[sequence - 1])) {
      return status('paused-ui-mismatch', '현재 화면의 행/본문 지문이 지정한 시작 순번과 다릅니다.', {
        expected_sequence: sequence,
        observed_row_sha256: current.rowSha,
        observed_body_sha256: current.bodySha,
      });
    }
  }

  let processed = 0;
  let lastSequence = null;
  while (processed < maxRows && sequence >= stopSequence) {
    const source = rows[sequence - 1];
    if (!samePair(current, source)) {
      return status('paused-ui-mismatch', `현재 화면이 ${sequence}번 원본 지문과 다릅니다.`, {
        expected_row_sha256: source.row_sha256,
        expected_body_sha256: source.body_sha256,
        observed_row_sha256: current.rowSha,
        observed_body_sha256: current.bodySha,
      });
    }

    const mapped = map.records.find((record) => record.sequence === sequence);
    const storedDate = dateValue(source) ?? mapped?.received_date ?? null;
    let receivedDate = storedDate;
    const needsDate = sequence <= targetSequenceMax && dateValue(source) === null && !mapped;
    const sameAsSavedCursor = map.cursor?.sequence === sequence && samePair(current, map.cursor);
    const comparisonDate = map.pending_date?.sequence === sequence
      ? map.pending_date.previous_received_date
      : map.navigation_pending?.to_sequence === sequence
        ? map.navigation_pending.from_received_date
        : sameAsSavedCursor ? null : compareFromDate;

    map.cursor = { sequence, ...pairFor(source), received_date: receivedDate, verified_at: new Date().toISOString() };
    let override = null;
    if (needsDate) {
      map.pending_date = {
        sequence,
        ...pairFor(source),
        previous_received_date: comparisonDate,
        started_at: map.pending_date?.sequence === sequence ? map.pending_date.started_at : new Date().toISOString(),
      };
      map.status = 'reading-date';
      await persist();
      override = manualOverrides.find((item) => item.sequence === sequence
        && item.row_sha256 === source.row_sha256
        && item.body_sha256 === source.body_sha256);
      if (override) {
        receivedDate = override.received_date;
      } else {
        try {
          receivedDate = await readReceivedDateForSnapshot(sky, window, current, {
            year,
            previousDate: comparisonDate,
            monthCorrection,
            direction: 'newer',
          });
        } catch (error) {
          return status('paused-date-read-error', error.message, { sequence, ...pairFor(source) });
        }
      }
    }
    if (comparisonDate && receivedDate && receivedDate < comparisonDate) {
      return status('paused-date-order-error', `날짜가 최신 방향으로 역행했습니다: ${sequence}번 ${receivedDate}, 이전 순번 날짜 ${comparisonDate}`, {
        sequence,
        ...pairFor(source),
      });
    }
    if (needsDate) {
      map.records.push({
        sequence,
        ...pairFor(source),
        received_date: receivedDate,
        verification_method: override ? 'visible-manager-header-manual' : 'visible-manager-header-ocr',
        ...(override ? { visible_header: override.visible_header } : {}),
        verified_at: new Date().toISOString(),
      });
    }
    map.cursor = { sequence, ...pairFor(source), received_date: receivedDate, verified_at: new Date().toISOString() };
    map.pending_date = null;
    map.navigation_pending = null;
    map.status = 'in_progress';
    delete map.last_error;
    await persist();
    processed += 1;
    lastSequence = sequence;
    compareFromDate = null;

    if (sequence === stopSequence) {
      map.status = 'complete';
      await persist();
      return { status: map.status, processed, lastSequence, mappedCount: map.records.length, mapPath: outputPath };
    }
    if (processed >= maxRows) break;

    const nextSequence = sequence - 1;
    const next = rows[nextSequence - 1];
    if (source.row_sha256 === next.row_sha256 && source.body_sha256 === next.body_sha256) {
      return status('paused-indistinguishable-adjacent-rows', '인접한 쪽지의 행/본문 지문이 모두 같아 키 이동을 안전하게 판별할 수 없습니다.', {
        from_sequence: sequence,
        to_sequence: nextSequence,
      });
    }
    map.navigation_pending = {
      from_sequence: sequence,
      from_row_sha256: source.row_sha256,
      from_body_sha256: source.body_sha256,
      from_received_date: receivedDate,
      to_sequence: nextSequence,
      to_row_sha256: next.row_sha256,
      to_body_sha256: next.body_sha256,
      started_at: new Date().toISOString(),
    };
    map.status = 'navigation_pending';
    await persist();
    await sky.press_key({ window, key: 'Up' });
    let settled;
    try { settled = await settleNextSequence(sky, window, { ...next, sequence: nextSequence }, normalizedSkipPairs, { delayMs }); }
    catch (error) {
      return status('paused-ui-sync-error', error.message, { from_sequence: sequence, to_sequence: nextSequence });
    }
    current = settled.snapshot;
    for (const skipped of settled.skipped) {
      const entry = {
        from_sequence: sequence,
        to_sequence: nextSequence,
        ...skipped,
        observed_at: new Date().toISOString(),
      };
      if (map.skipped_ui_items.some((item) => item.row_sha256 === entry.row_sha256 && item.body_sha256 === entry.body_sha256)) {
        return status('paused-repeated-skipped-item', '이미 건너뛴 제외 첨부 항목이 다시 나타나 원본 순번 대조를 멈췄습니다.', entry);
      }
      map.skipped_ui_items.push(entry);
    }
    await persist();
    sequence = nextSequence;
    compareFromDate = receivedDate;
  }

  map.status = 'paused-batch-complete';
  await persist();
  return { status: map.status, processed, lastSequence, mappedCount: map.records.length, mapPath: outputPath };
}
