import os
import re

html_path = r'c:\Users\lee21\.gemini\antigravity\scratch\my-skills\skills\classmanage-exam-graderV2\webapp\static\review2.html'

with open(html_path, 'r', encoding='utf-8') as f:
    content = f.read()

new_html = """<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<title>오버레이 정렬 검수 (페이지 단위) | V2</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;background:#111827;color:#f3f4f6;display:flex;flex-direction:column;height:100vh;overflow:hidden}

/* 툴바 */
#tb{display:flex;align-items:center;gap:12px;padding:10px 16px;background:#1f2937;border-bottom:1px solid #374151;flex-shrink:0}
#tb h1{font-size:15px;font-weight:700;color:#e5e7eb;white-space:nowrap;margin-right:10px}
.sep{width:1px;height:24px;background:#374151}

.btn{display:inline-flex;align-items:center;justify-content:center;padding:6px 12px;border-radius:6px;border:none;cursor:pointer;font-size:13px;font-weight:600;white-space:nowrap;transition:0.15s}
.btn:disabled{opacity:0.4;cursor:not-allowed}
.bg{background:#374151;color:#d1d5db}.bg:hover:not(:disabled){background:#4b5563}
.bp{background:#2563eb;color:#fff}.bp:hover:not(:disabled){background:#1d4ed8}
.bg-green{background:#059669;color:#fff}.bg-green:hover:not(:disabled){background:#047857}
.bg-yellow{background:#d97706;color:#fff}.bg-yellow:hover:not(:disabled){background:#b45309}

.nav-group{display:flex;align-items:center;gap:6px;background:#111827;padding:4px;border-radius:8px;border:1px solid #374151}
.nav-text{font-size:13px;font-weight:600;min-width:120px;text-align:center;color:#60a5fa}

#main{flex:1;overflow:hidden;display:flex;background:#374151}

/* 사이드바 */
#sidebar{width:220px;background:#1f2937;border-right:1px solid #374151;display:flex;flex-direction:column;}
.sb-header{padding:12px;font-size:13px;font-weight:600;border-bottom:1px solid #374151;color:#9ca3af}
#student-list{flex:1;overflow-y:auto;padding:8px;font-size:12px;display:flex;flex-direction:column;gap:6px;}
.stu-item{display:flex;align-items:center;gap:6px;}
.stu-item input{accent-color:#2563eb;cursor:pointer;}
.stu-item label{cursor:pointer;word-break:break-all;}

#cw{flex:1;overflow:auto;display:flex;justify-content:center;align-items:flex-start;padding:20px}
#ow{position:relative;display:inline-block;line-height:0;box-shadow:0 10px 25px rgba(0,0,0,0.5)}

#cs,#ct,#cb{position:absolute;top:0;left:0;pointer-events:none}
#cs{position:relative}

</style>
</head>
<body>

<div id="tb">
  <h1>🔍 전체 오버레이 검수</h1>
  
  <div class="nav-group">
    <button class="btn bg" onclick="prevPage()" id="btn-prev">◀ 이전</button>
    <div class="nav-text" id="page-indicator">0 / 0 페이지</div>
    <button class="btn bg" onclick="nextPage()" id="btn-next">다음 ▶</button>
  </div>

  <div class="sep"></div>

  <div style="display:flex;flex-direction:column;gap:4px;">
      <div style="display:flex;align-items:center;gap:6px;">
          <label style="font-size:11px;color:#9ca3af;width:70px;">학생 투명도</label>
          <input type="range" id="sl-stu" min="0" max="100" value="80" style="width:80px;accent-color:#2563eb" oninput="updateOpacities()">
      </div>
      <div style="display:flex;align-items:center;gap:6px;">
          <label style="font-size:11px;color:#9ca3af;width:70px;">빈 시험지</label>
          <input type="range" id="sl-tmpl" min="0" max="100" value="40" style="width:80px;accent-color:#059669" oninput="updateOpacities()">
      </div>
  </div>

  <div class="sep" style="margin-left:auto"></div>

  <button class="btn bg-green" onclick="markPage('ok')" id="btn-ok">이 페이지 정렬 양호 ✅</button>
  <button class="btn bg-yellow" onclick="markPage('warn')" id="btn-warn">재정렬 필요 ⚠️</button>

  <div class="sep"></div>
  
  <button class="btn bp" id="btn-finish" onclick="finishReview()" disabled>검수 완료 (YOLO 저장)</button>
  <a href="/" class="btn bg" style="text-decoration:none;margin-left:6px">← 메인</a>
</div>

<div id="main">
  <div id="sidebar">
      <div class="sb-header">이 페이지 학생 목록</div>
      <div id="student-list"></div>
  </div>
  <div id="cw">
    <div id="ow">
      <canvas id="cs"></canvas>
      <canvas id="ct"></canvas>
      <canvas id="cb"></canvas>
    </div>
  </div>
</div>

<script>
let studentFilesByPage = {};
let pages = [];
let currentIndex = -1;
let pageStatus = []; // 'ok' | 'warn' | null
let loadedStudents = []; // {name, img, active}

let cW = 800, cH = 1100;
let tmplImg = new Image();

const CS = document.getElementById('cs');
const CT = document.getElementById('ct');
const CB = document.getElementById('cb');
const ctxS = CS.getContext('2d');
const ctxT = CT.getContext('2d');
const ctxB = CB.getContext('2d');

let regions = null;
let questions = [];
let pageQuestions = [];

window.onload = async () => {
  await loadRegions();
  await loadStudentList();
  updateOpacities();
};

function updateOpacities() {
    const stuVal = document.getElementById('sl-stu').value;
    const tmplVal = document.getElementById('sl-tmpl').value;
    CS.style.opacity = stuVal / 100;
    CT.style.opacity = tmplVal / 100;
}

function resize() {
  [CS, CT, CB].forEach(c => { c.width = cW; c.height = cH; });
  document.getElementById('ow').style.width = cW + 'px';
  document.getElementById('ow').style.height = cH + 'px';
}

async function loadRegions() {
  const r = await fetch('/api/regions');
  if (r.ok) {
    regions = await r.json();
    questions = regions.questions || [];
  }
}

async function loadStudentList() {
  const r = await fetch('/api/students');
  const d = await r.json();
  const students = d.students || [];
  
  const pageSet = new Set();
  studentFilesByPage = {};
  students.forEach(name => {
    const m = name.match(/_page_(\\d+)/i);
    const p = m ? parseInt(m[1]) : 1;
    pageSet.add(p);
    if (!studentFilesByPage[p]) studentFilesByPage[p] = [];
    studentFilesByPage[p].push(name);
  });
  
  pages = Array.from(pageSet).sort((a,b)=>a-b);
  pageStatus = new Array(pages.length).fill(null);
  
  if (pages.length > 0) {
    loadPage(0);
  } else {
    document.getElementById('page-indicator').textContent = '데이터 없음';
  }
}

function loadPage(idx) {
  if (idx < 0 || idx >= pages.length) return;
  currentIndex = idx;
  const pageNum = pages[idx];
  
  document.getElementById('page-indicator').textContent = `${idx + 1} / ${pages.length} (페이지 ${pageNum})`;
  document.getElementById('btn-prev').disabled = (idx === 0);
  document.getElementById('btn-next').disabled = (idx === pages.length - 1);
  
  pageQuestions = questions.filter(q => q.page === pageNum);

  tmplImg = new Image();
  tmplImg.onload = () => {
    cW = tmplImg.naturalWidth;
    cH = tmplImg.naturalHeight;
    resize();
    drawAll();
  };
  tmplImg.src = '/api/template/blank_p' + pageNum + '.jpg?t=' + Date.now();
  
  const files = studentFilesByPage[pageNum] || [];
  loadedStudents = [];
  let loadedCount = 0;
  
  renderSidebar(files);
  
  ctxS.clearRect(0, 0, cW, cH);
  
  if (files.length === 0) {
    drawAll();
    updateFinishButton();
    return;
  }
  
  files.forEach(name => {
    const img = new Image();
    img.onload = () => {
      loadedStudents.push({name: name, img: img, active: true});
      loadedCount++;
      if (loadedCount === files.length) {
        drawAll();
      }
    };
    img.src = '/api/student/' + encodeURIComponent(name) + '?t=' + Date.now();
  });
  
  updateFinishButton();
}

function renderSidebar(files) {
    const sl = document.getElementById('student-list');
    sl.innerHTML = '';
    files.forEach((name, i) => {
        const div = document.createElement('div');
        div.className = 'stu-item';
        div.innerHTML = `<input type="checkbox" id="chk-${i}" checked onchange="toggleStudent('${name}', this.checked)"> <label for="chk-${i}">${name}</label>`;
        sl.appendChild(div);
    });
}

function toggleStudent(name, isActive) {
    const s = loadedStudents.find(x => x.name === name);
    if(s) {
        s.active = isActive;
        drawAll();
    }
}

function prevPage() { loadPage(currentIndex - 1); }
function nextPage() { loadPage(currentIndex + 1); }

function drawAll() {
  ctxS.clearRect(0, 0, cW, cH);
  
  ctxS.fillStyle = 'white';
  ctxS.fillRect(0, 0, cW, cH);
  
  const activeStudents = loadedStudents.filter(s => s.active);
  if (activeStudents.length > 0) {
    ctxS.globalCompositeOperation = 'multiply';
    activeStudents.forEach(s => {
      ctxS.drawImage(s.img, 0, 0, cW, cH);
    });
    ctxS.globalCompositeOperation = 'source-over';
  }

  ctxT.clearRect(0, 0, cW, cH);
  if (tmplImg.complete && tmplImg.naturalWidth > 0) {
    ctxT.drawImage(tmplImg, 0, 0, cW, cH);
  }

  ctxB.clearRect(0, 0, cW, cH);
  pageQuestions.forEach(q => {
    const b = q.box;
    if (!b) return;
    const px = b.x * cW, py = b.y * cH, pw = b.w * cW, ph = b.h * cH;
    ctxB.strokeStyle = '#ef4444';
    ctxB.lineWidth = 1.5;
    ctxB.strokeRect(px, py, pw, ph);
  });
}

async function markPage(status) {
  if (currentIndex < 0) return;
  pageStatus[currentIndex] = status;
  
  await fetch('/api/log', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      event: status === 'ok' ? 'page_verified_ok' : 'page_needs_review',
      detail: { page: pages[currentIndex] }
    })
  });
  
  updateFinishButton();
  if (currentIndex < pages.length - 1) {
    nextPage();
  }
}

function updateFinishButton() {
  const allChecked = pageStatus.every(s => s !== null) && pages.length > 0;
  document.getElementById('btn-finish').disabled = !allChecked;
}

async function finishReview() {
  document.getElementById('btn-finish').textContent = '저장 중...';
  document.getElementById('btn-finish').disabled = true;
  
  let successCount = 0;
  for (let p in studentFilesByPage) {
      const qsForPage = questions.filter(q => q.page === parseInt(p));
      const files = studentFilesByPage[p];
      for(let name of files) {
          try {
            const res = await fetch('/api/yolo_save', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ name: name, questions: qsForPage })
            });
            if (res.ok) successCount++;
          } catch (e) {
            console.error('YOLO save error:', e);
          }
      }
  }
  
  await fetch('/api/log', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      event: 'review_completed',
      detail: { saved: successCount }
    })
  });
  
  alert(`YOLO 라벨 생성 완료 (${successCount}장)`);
  window.location.href = '/';
}
</script>
</body>
</html>
"""

with open(html_path, 'w', encoding='utf-8') as f:
    f.write(new_html)

print("Updated review2.html successfully.")
