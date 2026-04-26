import os
import re

html_path = r'c:\Users\lee21\.gemini\antigravity\scratch\my-skills\skills\classmanage-exam-graderV2\webapp\templates\index.html'

with open(html_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Replace the body content
new_body = """
<body>
<h1>📋 시험지 라벨링 시스템 V2</h1>
<p class="sub">수동 기반 워크플로우 — 파일 준비 → 프롬프트 생성 → 캔버스 수정 → 정렬 → 검수</p>

<!-- STEP 0: 파일 현황 -->
<div class="step">
  <div class="step-title"><span class="step-num">0</span>파일 현황 및 업로드</div>
  <p class="step-desc">각 단계에 필요한 파일들을 준비합니다.</p>
  <div id="file-status-container" style="display:flex; flex-direction:column; gap:12px;">로딩 중...</div>
  
  <div style="display:none">
    <input type="file" id="tmpl-file" accept=".pdf" onchange="uploadTemplate()">
    <input type="file" id="ans-file" accept=".pdf" onchange="uploadAnswers()">
    <input type="file" id="stu-files" accept=".pdf,.jpg,.jpeg,.png" multiple onchange="uploadStudents()">
  </div>
</div>

<!-- STEP 1: Gemini 프롬프트 및 JSON 수신 -->
<div class="step">
  <div class="step-title"><span class="step-num">1</span>Gemini 프롬프트 및 JSON 수신</div>
  <p class="step-desc">모든 빈 시험지 이미지를 한 번에 첨부하고, 아래 프롬프트를 사용하여 전체 문항 좌표를 추출합니다.</p>
  
  <div class="bridge-box">
    <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:8px">
      <span style="font-size:12px;font-weight:600;color:var(--muted)">📋 전체 페이지 프롬프트 자동 생성</span>
      <button class="btn btn-ghost" onclick="copyPrompt()" style="padding:4px 10px;font-size:11px">복사</button>
    </div>
    <div class="prompt-preview" id="prompt-text">템플릿을 업로드하면 프롬프트가 자동 생성됩니다.</div>
    
    <hr style="border-color:var(--border);margin:12px 0">
    <label style="font-size:12px;font-weight:600;color:var(--muted)">✏️ Gemini 결과 붙여넣기</label>
    <textarea id="json-input" placeholder='여기에 Gemini 결과물을 붙여넣으세요. ```json ... ``` 코드블록은 자동 제거됩니다.' oninput="onJsonInput()"></textarea>
    
    <div id="json-status" style="margin-top:8px;font-size:12px;min-height:18px"></div>
    <div style="display:flex;gap:8px;margin-top:10px;flex-wrap:wrap">
      <button class="btn btn-yellow" onclick="doValidateAll()">🔍 JSON 파싱 및 전체 요약 보기</button>
      <button class="btn btn-green" id="save-regions-btn" onclick="doSaveAll()" disabled>✅ 전체 regions.json 저장</button>
    </div>
  </div>
</div>

<!-- STEP 2: 답안 영역 수정 에디터 -->
<div class="step">
  <div class="step-title"><span class="step-num">2</span>답안 영역 수정 에디터</div>
  <p class="step-desc">regions.json 저장 후, 페이지별로 정밀하게 박스를 수정합니다.</p>
  <div style="margin-bottom:12px; display:flex; align-items:center; gap:8px;">
    <label style="font-size:12px;font-weight:600;color:var(--muted)">📄 편집할 페이지 선택:</label>
    <select id="prompt-page-select" class="btn bg" onchange="loadEditorForPage()">
      {% for tmpl in templates %}
      <option value="{{ tmpl }}">{{ tmpl }}</option>
      {% endfor %}
      {% if not templates %}
      <option value="blank_p1.jpg">blank_p1.jpg</option>
      {% endif %}
    </select>
    <button class="btn btn-ghost" onclick="loadEditorForPage()" style="padding:4px 10px;font-size:11px;">불러오기</button>
  </div>
  
  <div id="editor-container" style="display:none;">
    <div style="display:flex;gap:12px;align-items:flex-start">
      <div style="flex:1;min-width:0">
        <div style="display:flex;gap:6px;margin-bottom:6px;flex-wrap:wrap;align-items:center">
          <button class="btn btn-ghost" id="mode-select-btn" onclick="setEditorMode('select')" style="font-size:11px;padding:4px 10px">&#9654; 선택/이동</button>
          <button class="btn btn-ghost" id="mode-draw-btn"   onclick="setEditorMode('draw')"   style="font-size:11px;padding:4px 10px">&#10011; 새 박스</button>
          <button class="btn btn-ghost" id="del-btn" onclick="deleteSelected()" style="font-size:11px;padding:4px 10px;color:#ef4444" disabled>&#10006; 삭제</button>
          <span id="mode-label" style="font-size:11px;color:#64748b">클릭=선택 · 드래그=이동 · 모서리=크기</span>
        </div>
        <div style="border:1px solid var(--border);border-radius:8px;overflow:hidden">
          <canvas id="preview-canvas" style="display:block;width:100%;height:auto"></canvas>
        </div>
        <div style="display:flex;gap:10px;margin-top:6px;font-size:11px">
          <span><span style="width:10px;height:10px;background:rgba(59,130,246,0.6);display:inline-block;vertical-align:middle;border-radius:2px"></span> 객관식</span>
          <span><span style="width:10px;height:10px;background:rgba(34,197,94,0.6);display:inline-block;vertical-align:middle;border-radius:2px"></span> 단답형</span>
          <span><span style="width:10px;height:10px;background:rgba(249,115,22,0.6);display:inline-block;vertical-align:middle;border-radius:2px"></span> 서술형</span>
        </div>
      </div>
      <div style="width:175px;flex-shrink:0">
        <div style="font-size:11px;font-weight:600;color:#7dd3fc;margin-bottom:6px">선택 문항 편집</div>
        <div id="editor-panel" style="background:#0f172a;border:1px solid var(--border);border-radius:8px;padding:12px;font-size:12px;color:#94a3b8">문항을 선택하세요</div>
      </div>
    </div>
    <div style="margin-top:10px;">
      <button class="btn btn-green" onclick="saveEditorForPage()">✅ 현재 페이지 수정 완료 (저장)</button>
      <span id="editor-save-status" style="font-size:12px;margin-left:10px;"></span>
    </div>
  </div>
</div>

<!-- STEP 3: 학생 시험지 정렬 -->
<div class="step">
  <div class="step-title"><span class="step-num">3</span>학생 시험지 정렬 파이프라인</div>
  <p class="step-desc">업로드된 학생 시험지를 각 페이지에 맞는 템플릿 기준으로 원근 정렬합니다.</p>
  <button class="btn btn-blue" id="pipeline-btn" onclick="runPipeline()">🚀 정렬 실행</button>
  <span id="pipeline-status" style="font-size:12px;margin-left:10px;color:var(--muted)"></span>
</div>

<!-- STEP 4: 정렬 검증 및 병합 -->
<div class="step">
  <div class="step-title"><span class="step-num">4</span>정렬 검증 (전체 오버레이) 및 완료</div>
  <p class="step-desc">학생 필기를 모두 겹쳐 정렬 상태를 한눈에 확인합니다.</p>
  <a href="/review" class="btn btn-green" style="text-decoration:none">🔍 전체 오버레이 검수 열기 →</a>
</div>

<div style="height:40px"></div>

<!-- 상태 바 -->
<div id="status-bar">
  <span>🟢 서버: http://127.0.0.1:8080</span>
  <span id="regions-status">regions.json: {% if has_regions %}✓ 있음{% else %}⚠️ 없음{% endif %}</span>
  <span>template: {% if template_exists %}✓ 있음{% else %}⚠️ 없음{% endif %}</span>
</div>

<script>
let globalRegions = { questions: [] };
let fileStatus = null;

window.addEventListener('DOMContentLoaded', async () => {
    await loadFileStatus();
    try {
        const r = await fetch('/api/regions');
        if (r.ok) {
            globalRegions = await r.json();
            if(!globalRegions.questions) globalRegions.questions = [];
        }
    } catch(e) {}
});

async function loadFileStatus() {
    document.getElementById('file-status-container').innerHTML = '로딩 중...';
    try {
        const r = await fetch('/api/files/status');
        fileStatus = await r.json();
        renderFileStatus();
        updatePromptText();
    } catch (e) {
        document.getElementById('file-status-container').innerHTML = '❌ 상태를 불러올 수 없습니다.';
    }
}

function renderFileStatus() {
    const c = document.getElementById('file-status-container');
    let html = '';
    
    // 빈 시험지
    html += `<div style="background:#0f172a; padding:12px; border-radius:8px; border:1px solid var(--border);">`;
    if (fileStatus.template.count > 0) {
        html += `<div style="margin-bottom:8px;">✅ <b>빈 시험지</b> (${fileStatus.template.count}장)</div>`;
        html += `<div style="display:flex; gap:8px; overflow-x:auto;">`;
        fileStatus.template.files.forEach(f => {
            html += `<div style="text-align:center;">
                <img src="/api/thumbnail?path=data/template/${f}&size=120" style="width:80px; height:auto; border:1px solid #334155; border-radius:4px;">
                <div style="font-size:10px; margin-top:4px; color:var(--muted);">${f}</div>
            </div>`;
        });
        html += `</div>`;
        html += `<div style="margin-top:8px;"><button class="btn btn-ghost" style="font-size:11px;" onclick="document.getElementById('tmpl-file').click()">새 PDF 파일로 교체</button></div>`;
    } else {
        html += `<div style="margin-bottom:8px;">❌ <b>빈 시험지 없음</b></div>`;
        html += `<button class="btn btn-blue" onclick="document.getElementById('tmpl-file').click()">📁 PDF 업로드 (페이지 자동 분할)</button>`;
    }
    html += `</div>`;

    // 답안지
    html += `<div style="background:#0f172a; padding:12px; border-radius:8px; border:1px solid var(--border);">`;
    if (fileStatus.answers.count > 0) {
        html += `<div style="margin-bottom:8px;">✅ <b>답안지</b> (${fileStatus.answers.count}개)</div>`;
        html += `<div style="display:flex; gap:8px; overflow-x:auto;">`;
        fileStatus.answers.files.forEach(f => {
            html += `<div style="text-align:center;">
                <img src="/api/thumbnail?path=data/answers/${f}&size=120" style="width:80px; height:auto; border:1px solid #334155; border-radius:4px;">
                <div style="font-size:10px; margin-top:4px; color:var(--muted);">${f}</div>
            </div>`;
        });
        html += `</div>`;
        html += `<div style="margin-top:8px;"><button class="btn btn-ghost" style="font-size:11px;" onclick="document.getElementById('ans-file').click()">새 PDF 파일로 교체</button></div>`;
    } else {
        html += `<div style="margin-bottom:8px;">❌ <b>답안지 없음</b></div>`;
        html += `<button class="btn btn-blue" onclick="document.getElementById('ans-file').click()">📁 PDF 업로드</button>`;
    }
    html += `</div>`;
    
    // 학생 파일
    html += `<div style="background:#0f172a; padding:12px; border-radius:8px; border:1px solid var(--border);">`;
    if (fileStatus.students.count > 0) {
        html += `<div style="margin-bottom:8px;">✅ <b>학생 시험지</b> (${fileStatus.students.count}개 파일)</div>`;
        html += `<div style="display:flex; gap:8px; overflow-x:auto;">`;
        fileStatus.students.files.forEach(f => {
            html += `<div style="text-align:center;">
                <img src="/api/thumbnail?path=data/raw_pdfs/${f}&size=120" style="width:80px; height:auto; border:1px solid #334155; border-radius:4px;">
                <div style="font-size:10px; margin-top:4px; color:var(--muted); max-width:80px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">${f}</div>
            </div>`;
        });
        html += `</div>`;
        html += `<div style="margin-top:8px;"><button class="btn btn-ghost" style="font-size:11px;" onclick="document.getElementById('stu-files').click()">추가 업로드</button></div>`;
    } else {
        html += `<div style="margin-bottom:8px;">❌ <b>학생 시험지 없음</b></div>`;
        html += `<button class="btn btn-blue" onclick="document.getElementById('stu-files').click()">📁 다중 PDF 업로드</button>`;
    }
    html += `</div>`;
    
    c.innerHTML = html;
}

// 업로드 로직들
async function uploadTemplate(){
  const fi = document.getElementById('tmpl-file');
  if(!fi.files.length) return;
  const fd = new FormData(); fd.append('file', fi.files[0]);
  document.getElementById('file-status-container').innerHTML = '업로드 중...';
  await fetch('/api/upload/template', {method:'POST', body:fd});
  location.reload();
}
async function uploadAnswers(){
  const fi = document.getElementById('ans-file');
  if(!fi.files.length) return;
  const fd = new FormData(); fd.append('file', fi.files[0]);
  document.getElementById('file-status-container').innerHTML = '업로드 중...';
  await fetch('/api/upload/answers', {method:'POST', body:fd});
  location.reload();
}
async function uploadStudents(){
  const fi = document.getElementById('stu-files');
  if(!fi.files.length) return;
  const fd = new FormData();
  for(let f of fi.files) fd.append('files', f);
  document.getElementById('file-status-container').innerHTML = '업로드 중...';
  await fetch('/api/upload/students', {method:'POST', body:fd});
  location.reload();
}

function updatePromptText() {
  const pages = fileStatus ? fileStatus.template.count : 1;
  const hasAnswers = fileStatus && fileStatus.answers.count > 0;
  
  let p = `첨부한 이미지들은 한국 초등학교 3학년 수학 단원평가 시험지입니다.
이미지는 총 ${pages}장이며 각각 1페이지부터 ${pages}페이지까지입니다.

[시험지 구조]
- A4 세로, 좌우 2단 레이아웃
- 객관식: 문항 끝 ( ) 괄호 안에 번호를 씀
- 단답형: '답' 동그라미 아이콘 옆 밑줄 위에 씀
- 서술형: '풀이' 줄 + '답' 줄 두 영역\n\n`;

  if (hasAnswers) {
    p += `[답안지 정보]
(첨부된 정답지를 참고하여 객관식/단답형/서술형을 정확히 구분하세요)\n\n`;
  }

  p += `각 페이지의 모든 문항에서 학생이 답을 적는 영역의 위치를
아래 JSON 형식으로 한 번에 반환하세요.
JSON 코드블록만 반환하고 설명은 쓰지 마세요.

{
  "questions": [
    {
      "number": 1,
      "page": 1,
      "type": "객관식",
      "box": {"x": 0.72, "y": 0.18, "w": 0.12, "h": 0.04}
    },
    {
      "number": 9,
      "page": 2,
      "type": "객관식",
      "box": {"x": 0.72, "y": 0.18, "w": 0.12, "h": 0.04}
    }
  ]
}

좌표는 각 페이지 이미지 크기 기준 0~1 비율값.
page 값은 반드시 이미지 순서(1, 2, 3...)와 일치해야 합니다.`;
  
  document.getElementById('prompt-text').textContent = p;
}

function copyPrompt(){
  const txt = document.getElementById('prompt-text').textContent;
  navigator.clipboard.writeText(txt).then(()=>{
    const btn = event.target; btn.textContent = '✓ 복사됨!';
    setTimeout(()=>btn.textContent='복사', 1500);
  });
}

function onJsonInput(){
  document.getElementById('save-regions-btn').disabled = true;
  setJsonStatus('', '');
}

function extractJson(raw) {
  let s = raw.trim();
  const cbMatch = s.match(/```(?:json)?\s*([\\s\\S]*?)```/i);
  if (cbMatch) { s = cbMatch[1].trim(); }
  else {
    const start = Math.min(
      s.indexOf('{') === -1 ? Infinity : s.indexOf('{'),
      s.indexOf('[') === -1 ? Infinity : s.indexOf('[')
    );
    if (start === Infinity) throw new SyntaxError('JSON 구조를 찾을 수 없습니다.');
    s = s.slice(start, Math.max(s.lastIndexOf('}'), s.lastIndexOf(']')) + 1);
  }
  return JSON.parse(s);
}

let _parsedAllData = null;

function doValidateAll() {
  _parsedAllData = null;
  const raw = document.getElementById('json-input').value;
  if (!raw.trim()) { setJsonStatus('❌ 입력창이 비어있습니다.', 'red'); return; }

  let data;
  try { data = extractJson(raw); }
  catch (e) {
    setJsonStatus('❌ JSON 파싱 실패: ' + e.message, 'red');
    return;
  }

  let qs = data.questions;
  if (!qs && Array.isArray(data)) qs = data;
  if (!qs || !Array.isArray(qs)) {
    setJsonStatus('❌ "questions" 배열을 찾을 수 없습니다.', 'red'); return;
  }

  const pages = new Set(qs.map(q => q.page || 1));
  let pageSummary = [];
  for(let p=1; p<=fileStatus.template.count; p++) {
      const c = qs.filter(q => (q.page||1) === p).length;
      pageSummary.push(`${p}p: ${c}문항`);
  }

  setJsonStatus(`✅ 파싱 성공! 총 ${qs.length}문항 (${pageSummary.join(', ')})`, 'green');
  document.getElementById('save-regions-btn').disabled = false;
  _parsedAllData = { questions: qs };
}

async function doSaveAll() {
  if (!_parsedAllData) return;
  globalRegions = _parsedAllData;
  document.getElementById('save-regions-btn').disabled = true;
  setJsonStatus('저장 중...', 'muted');
  const r = await fetch('/api/regions', {
    method:'POST', headers:{'Content-Type':'application/json'},
    body: JSON.stringify(globalRegions)
  });
  if(r.ok) {
    setJsonStatus('✅ 전체 regions.json 저장 완료!', 'green');
  } else {
    setJsonStatus('❌ 저장 실패', 'red');
  }
}

// ── STEP 2: 에디터 ──────────────────────────────────
function getSelectedPageNum() {
  const sel = document.getElementById('prompt-page-select');
  const val = sel ? sel.value : 'blank_p1.jpg';
  const m = val.match(/blank_p(\\d+)/i);
  return m ? parseInt(m[1]) : 1;
}

async function loadEditorForPage() {
  const page = getSelectedPageNum();
  const qs = globalRegions.questions.filter(q => q.page === page);
  
  document.getElementById('editor-container').style.display = 'block';
  document.getElementById('editor-save-status').textContent = '로딩 중...';
  
  try {
    const bgImg = await new Promise((ok, fail) => {
      const i = new Image();
      i.onload = () => ok(i);
      i.onerror = () => fail(new Error('템플릿 이미지 없음'));
      const pageStr = document.getElementById('prompt-page-select').value;
      i.src = '/api/template/' + encodeURIComponent(pageStr) + '?t=' + Date.now();
    });
    
    // 에디터 초기화
    if(typeof editorInit === 'function') {
        editorInit(qs, bgImg);
        setEditorMode('select');
        document.getElementById('editor-save-status').textContent = `${page}페이지 로드 완료.`;
        document.getElementById('editor-save-status').style.color = 'var(--green)';
    } else {
        document.getElementById('editor-save-status').textContent = '에디터 스크립트 로드 실패';
    }
  } catch (err) {
    document.getElementById('editor-save-status').textContent = err.message;
  }
}

async function saveEditorForPage() {
  const liveQs = (typeof editorGetQuestions === 'function') ? editorGetQuestions() : [];
  const currentPageNum = getSelectedPageNum();
  
  liveQs.forEach(q => { if(!q.page) q.page = currentPageNum; });

  const otherQs = globalRegions.questions.filter(q => q.page !== currentPageNum);
  globalRegions.questions = [...otherQs, ...liveQs];
  
  document.getElementById('editor-save-status').textContent = '저장 중...';
  document.getElementById('editor-save-status').style.color = 'var(--muted)';
  
  const r = await fetch('/api/regions', {
    method:'POST', headers:{'Content-Type':'application/json'},
    body: JSON.stringify(globalRegions)
  });
  if(r.ok) {
    document.getElementById('editor-save-status').textContent = `✅ ${currentPageNum}페이지 저장 완료!`;
    document.getElementById('editor-save-status').style.color = 'var(--green)';
  } else {
    document.getElementById('editor-save-status').textContent = '❌ 저장 실패';
    document.getElementById('editor-save-status').style.color = 'var(--red)';
  }
}

// 파이프라인
async function runPipeline(){
  const btn = document.getElementById('pipeline-btn');
  btn.disabled = true;
  document.getElementById('pipeline-status').textContent = '실행 중... (시간이 걸릴 수 있습니다)';
  try{
    const r = await fetch('/api/run_pipeline', {method:'POST'});
    const d = await r.json();
    if(d.success){
      document.getElementById('pipeline-status').textContent = `✅ 정렬 완료 (성공 ${d.aligned}장, 실패 ${d.failed}장) — 확인 후 새로고침하세요.`;
      document.getElementById('pipeline-status').style.color = 'var(--green)';
    } else {
      document.getElementById('pipeline-status').textContent = '❌ ' + d.error;
    }
  } catch(e){
    document.getElementById('pipeline-status').textContent = '❌ 서버 통신 오류';
  }
  btn.disabled = false;
}

function setStatus(id, msg, col){
  const el = document.getElementById(id);
  if(!el) return;
  el.textContent = msg;
  el.style.color = col==='green'?'#22c55e':col==='red'?'#ef4444':'#94a3b8';
}
function setJsonStatus(msg, col){
  setStatus('json-status', msg, col);
}
</script>
<script src="/static/editor.js"></script>
</body>
"""

new_content = content.split("<body>")[0] + new_body

with open(html_path, 'w', encoding='utf-8') as f:
    f.write(new_content)

print("Updated index.html successfully.")
