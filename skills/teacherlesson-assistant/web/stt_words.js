// 🎙 받아쓰기 사전 고치는 칸 (T111 ③). 순수 함수(Node 시험)와 화면 코드. 사전은 데이터 폴더 stt_words.json(학생 이름이 있을 수 있어 저장소 밖)에 저장된다.

// 한 줄에 하나 → 낱말 목록(빈 줄·앞뒤 공백·같은 낱말 뺌)
function parseWordLines(text) {
  const out = [];
  for (const line of String(text || '').split(/\r?\n/)) {
    const w = line.trim();
    if (w && !out.includes(w)) out.push(w);
  }
  return out;
}

// "틀린 말 → 맞는 말" 줄들 → {fixes, bad}. → · -> · => · = 로 나눔(첫 번째 표시에서). 틀린 말이 같으면 뒤 줄이 이김. 나눌 수 없는 줄은 bad(줄 번호).
function parseFixLines(text) {
  const fixes = {};
  const bad = [];
  String(text || '').split(/\r?\n/).forEach((line, i) => {
    if (!line.trim()) return;
    const m = line.match(/^(.*?)\s*(?:→|->|=>|=)\s*(.*)$/);
    const from = m ? m[1].trim() : '';
    if (!m || !from) { bad.push(i + 1); return; }
    fixes[from] = m[2].trim();
  });
  return { fixes, bad };
}

function formatWordLines(words) { return (words || []).join('\n'); }
function formatFixLines(fixes) { return Object.keys(fixes || {}).map(k => `${k} → ${fixes[k]}`).join('\n'); }

if (typeof module !== 'undefined' && module.exports) {
  module.exports = { parseWordLines, parseFixLines, formatWordLines, formatFixLines };
}

// ──────── 화면 (브라우저에서만) ────────
if (typeof document !== 'undefined' && document.getElementById('sttBox')) {
  const sttFill = async () => {
    const j = await (await fetch('/api/stt-words')).json().catch(() => null);
    if (!j || j.status !== 'success') { document.getElementById('sttMsg').textContent = '사전을 불러오지 못했어요.'; return; }
    document.getElementById('sttWords').value = formatWordLines(j.words);
    document.getElementById('sttFixes').value = formatFixLines(j.fixes);
    document.getElementById('sttMsg').textContent = (j.notes || []).join(' ');
  };
  document.getElementById('sttBox').addEventListener('toggle', e => { if (e.target.open) sttFill(); });
  document.getElementById('sttSave').onclick = async () => {
    const { fixes, bad } = parseFixLines(document.getElementById('sttFixes').value);
    if (bad.length) { document.getElementById('sttMsg').textContent = `고쳐 쓰기 ${bad.join(', ')}번째 줄을 "틀린 말 → 맞는 말" 모양으로 고쳐 주세요.`; return; }
    const r = await post('/api/stt-words', { words: parseWordLines(document.getElementById('sttWords').value), fixes });
    document.getElementById('sttMsg').textContent = r.message || '';
    if (r.status === 'success') { document.getElementById('sttWords').value = formatWordLines(r.words); document.getElementById('sttFixes').value = formatFixLines(r.fixes); }
  };
}
