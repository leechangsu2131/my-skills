// Keyboard-driven, resumable raw-body capture for the GBTalk Message Manager.
// It stages message text and row fingerprints only; it never sends, replies, or deletes.

import fs from 'node:fs/promises';
import path from 'node:path';
import crypto from 'node:crypto';

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
const sha256 = (value) => crypto.createHash('sha256').update(value).digest('hex');

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

function bodyEditorIndex(state) {
  const match = (state?.accessibility?.tree ?? '').match(/\n\s*(\d+) 편집 Value:/);
  if (!match) throw new Error('본문 편집 컨트롤을 접근성 트리에서 찾지 못했습니다.');
  return Number(match[1]);
}

function snapshotFromState(state) {
  const row = extractSelectedRow(state);
  const body = extractBody(state);
  return { row, rowSha: sha256(row), body, bodySha: sha256(body) };
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
    const changed = !after || !sameSnapshot(current, after);
    if (changed && previous && sameSnapshot(current, previous)) return current;
    if (!changed) previous = null;
    else previous = current;
  }
  throw new Error('목록 행과 본문이 안정적으로 갱신되지 않아 캡처를 멈췄습니다.');
}

async function focusInboxList(sky, window) {
  let state = await latestState(sky, window);
  let focused = state?.accessibility?.focused_element?.trim() ?? '';
  if (!/^\s*\d+ 창 /.test(focused) || focused.includes('ScrollBar')) {
    await sky.click({ window, element_index: bodyEditorIndex(state) });
    await sky.press_key({ window, key: 'Shift+Tab' });
    await sky.press_key({ window, key: 'Shift+Tab' });
    await sleep(160);
    state = await latestState(sky, window);
    focused = state?.accessibility?.focused_element?.trim() ?? '';
  }
  if (!/^\s*\d+ 창 /.test(focused) || focused.includes('ScrollBar')) {
    throw new Error(`목록 행 포커스를 확인하지 못했습니다. Home/Down 입력을 보내지 않고 멈춥니다: ${focused || '(없음)'}`);
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
    checkpoint.next_row = null;
    checkpoint.pending_append = null;
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
  checkpoint.pending_append = null;
  checkpoint.status = 'paused';
  checkpoint.updated_at = new Date().toISOString();
  await atomicJson(checkpointPath, checkpoint);
}

async function saveNextCursor(checkpointPath, checkpoint, current, sequence, occurrence) {
  checkpoint.next_row = {
    sequence,
    row_sha256: current.rowSha,
    row_occurrence: occurrence,
    body_sha256: current.bodySha,
  };
  checkpoint.updated_at = new Date().toISOString();
  await atomicJson(checkpointPath, checkpoint);
}

async function advanceAndSettle(sky, window, previous, delayMs) {
  await sky.press_key({ window, key: 'Down' });
  let candidate = null;
  let unchangedCount = 0;
  for (let attempt = 0; attempt < 8; attempt += 1) {
    await sleep(delayMs);
    let current;
    try { current = snapshotFromState(await latestState(sky, window)); }
    catch { continue; }
    if (sameSnapshot(current, previous)) {
      unchangedCount += 1;
      candidate = null;
      if (unchangedCount >= 4) return { current, moved: false };
      continue;
    }
    unchangedCount = 0;
    if (candidate && sameSnapshot(candidate, current)) return { current, moved: true };
    candidate = current;
  }
  throw new Error('↓ 입력 뒤 선택 행과 본문이 안정되지 않아 캡처를 멈췄습니다.');
}

async function resyncFromHome(sky, window, rows, delayMs, maxResyncRows) {
  await sky.press_key({ window, key: 'Home' });
  let current = await stableSnapshot(sky, window, { delayMs });
  if (!rows.length) return current;
  if (rows.length > maxResyncRows) throw new Error('재개 위치가 안전 재탐색 상한보다 뒤에 있습니다. 자동으로 이어 쓰지 않습니다.');
  for (let index = 0; index < rows.length; index += 1) {
    const expected = rows[index];
    if (current.rowSha !== expected.row_sha256 || current.bodySha !== expected.body_sha256) {
      throw new Error(`Home부터 저장 행 ${index + 1}과 목록 순서가 일치하지 않습니다. JSONL에 이어 쓰지 않고 중단합니다.`);
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
 * Capture one small batch (30 by default) from newest to older. A checkpoint is
 * synced for every body; the caller should inspect the batch before starting another.
 */
export async function captureRawBodies({
  sky,
  window,
  outputDir,
  maxItems = 30,
  delayMs = 100,
  maxResyncRows = 300,
  stopBeforeRowSha256,
}) {
  if (!sky || !window || !outputDir) throw new Error('sky, window, outputDir가 필요합니다.');
  if (!Number.isInteger(maxItems) || maxItems < 1 || maxItems > 30) throw new Error('한 번의 캡처는 1~30건으로 제한합니다.');
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
    await sky.press_key({ window, key: 'Home' });
    current = await stableSnapshot(sky, window, { delayMs });
  }

  if (checkpoint.stop_before_row_sha256 && current.rowSha === checkpoint.stop_before_row_sha256) {
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
    const record = {
      sequence: rows.length + 1,
      row_sha256: current.rowSha,
      row_occurrence: occurrence,
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
