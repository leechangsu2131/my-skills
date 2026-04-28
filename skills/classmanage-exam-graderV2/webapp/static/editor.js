/* ── Step 3 캔버스 박스 에디터 ────────────────────────────
   기능: 선택/이동, 모서리 크기조절, 새 박스 그리기, 삭제
   ──────────────────────────────────────────────────── */

const TC = {
  '객관식': { fill:'rgba(59,130,246,0.28)', stroke:'#3b82f6' },
  '단답형': { fill:'rgba(34,197,94,0.28)',  stroke:'#22c55e' },
  '서술형': { fill:'rgba(249,115,22,0.28)', stroke:'#f97316' },
};
function tc(t){ return TC[t]||{fill:'rgba(124,58,237,0.28)',stroke:'#7c3aed'}; }

/* ── 전역 상태 ── */
let _qs = [];          // questions 배열 (live)
let _sel = -1;         // 선택 인덱스
let _mode = 'select';  // 'select' | 'draw'
let _bgImg = null;     // blank.jpg Image 객체
let _cW = 0, _cH = 0;

/* 드래그 상태 */
let _drag = null;
// { type:'move'|'resize'|'draw', qi, ox,oy, bx0,by0,bw0,bh0, handle:'tl'|'tr'|'bl'|'br'|'tc'|'bc'|'ml'|'mr', changed:boolean }

const HANDLE = 8; // 핸들 반경(px)

/* Undo / Redo 상태 */
let _history = [];
let _histIdx = -1;

function saveState() {
  const state = JSON.parse(JSON.stringify(_qs));
  _history = _history.slice(0, _histIdx + 1);
  _history.push(state);
  _histIdx++;
  updateUndoRedoUI();
}

function undo() {
  if (_histIdx > 0) {
    _histIdx--;
    _qs = JSON.parse(JSON.stringify(_history[_histIdx]));
    _sel = -1; redraw(); updatePanel(); updateUndoRedoUI();
  }
}

function redo() {
  if (_histIdx < _history.length - 1) {
    _histIdx++;
    _qs = JSON.parse(JSON.stringify(_history[_histIdx]));
    _sel = -1; redraw(); updatePanel(); updateUndoRedoUI();
  }
}

function resetEditor() {
  if(_history.length > 0) {
    _qs = JSON.parse(JSON.stringify(_history[0]));
    saveState();
    _sel = -1; redraw(); updatePanel();
  }
}

function updateUndoRedoUI() {
  const bu = document.getElementById('btn-undo');
  const br = document.getElementById('btn-redo');
  if(bu) bu.disabled = _histIdx <= 0;
  if(br) br.disabled = _histIdx >= _history.length - 1;
}

/* ── 초기화 ──────────────────────────────────────────── */
function editorInit(questions, bgImg, canvasId='preview-canvas'){
  _qs = questions.map(q=>({...q, box:{...q.box}}));
  _bgImg = bgImg;
  _sel = -1;
  _drag = null;
  const cv = document.getElementById(canvasId);
  
  // 배경 이미지가 주어지면 캔버스 내부 해상도를 원본과 맞춰 좌표 오차를 방지한다.
  if (bgImg && bgImg.naturalWidth > 0 && bgImg.naturalHeight > 0) {
    cv.width = bgImg.naturalWidth;
    cv.height = bgImg.naturalHeight;
  }

  _cW = cv.width;
  _cH = cv.height;
  
  cv.removeEventListener('mousedown', _onDown);
  cv.removeEventListener('mousemove', _onMove);
  cv.removeEventListener('mouseup',   _onUp);
  cv.removeEventListener('contextmenu', e=>e.preventDefault());
  cv.addEventListener('mousedown',    _onDown);
  cv.addEventListener('mousemove',    _onMove);
  cv.addEventListener('mouseup',      _onUp);
  cv.addEventListener('contextmenu',  e=>e.preventDefault());
  
  _history = [];
  _histIdx = -1;
  window._currentEditorCanvas = canvasId;
  saveState();
  
  redraw();
  console.log('[Editor] _cW:', _cW, '_cH:', _cH);
  console.log('[Editor] canvas BoundingRect:', cv.getBoundingClientRect());
  if(typeof updatePanel === 'function') updatePanel();
}

/* ── 모드 전환 ───────────────────────────────────────── */
function setEditorMode(m){
  _mode = m;
  const canvasId = window._currentEditorCanvas || 'preview-canvas';
  const cv = document.getElementById(canvasId);
  if (cv) {
    cv.style.cursor = m === 'draw' ? 'crosshair' : 'default';
  }
  ['select','draw'].forEach(k=>{
    const b = document.getElementById('mode-'+k+'-btn');
    if(b) b.style.background = k===m ? '#1d4ed8' : '';
  });
  const modeLabel = document.getElementById('mode-label');
  if (modeLabel) {
    modeLabel.textContent =
      m==='draw' ? '드래그로 새 박스를 그리세요' : '클릭=선택 · 드래그=이동 · 모서리=크기조절';
  }
}

/* ── 좌표 변환 ───────────────────────────────────────── */
function _mp(e){
  const rc = e.target.getBoundingClientRect();
  // canvas 내부 해상도(_cW,_cH)와 화면 표시 크기(rc.width,rc.height)가 다를 수 있으므로
  // 반드시 스케일 보정한다
  return {
    x: (e.clientX - rc.left) * (_cW / rc.width),
    y: (e.clientY - rc.top)  * (_cH / rc.height)
  };
}

function _boxPx(b){
  return {
    px: b.x * _cW,
    py: b.y * _cH,
    pw: b.w * _cW,
    ph: b.h * _cH
  };
}

/* ── 핸들 검사 ───────────────────────────────────────── */
function _handleAt(p, b){
  const {px,py,pw,ph} = _boxPx(b);
  const handles = {
    tl:[px,py], tc:[px+pw/2,py], tr:[px+pw,py],
    ml:[px,py+ph/2], mr:[px+pw,py+ph/2],
    bl:[px,py+ph], bc:[px+pw/2,py+ph], br:[px+pw,py+ph]
  };
  for(const [k,[hx,hy]] of Object.entries(handles)){
    if(Math.abs(p.x-hx)<HANDLE+2 && Math.abs(p.y-hy)<HANDLE+2) return k;
  }
  return null;
}

/* ── 박스 히트 검사 ──────────────────────────────────── */
function _hitBox(p, b){
  const {px,py,pw,ph} = _boxPx(b);
  return p.x>=px && p.x<=px+pw && p.y>=py && p.y<=py+ph;
}

/* ── 이벤트 ─────────────────────────────────────────── */
function _onDown(e){
  e.preventDefault();
  const p = _mp(e);

  if(_mode === 'draw'){
    _drag = { type:'draw', x0:p.x, y0:p.y, x1:p.x, y1:p.y };
    return;
  }

  /* 선택 모드 */
  if(_sel >= 0){
    const h = _handleAt(p, _qs[_sel].box);
    if(h){
      const b = _qs[_sel].box;
      _drag = { type:'resize', qi:_sel, handle:h, ox:p.x, oy:p.y,
                bx0:b.x, by0:b.y, bw0:b.w, bh0:b.h };
      return;
    }
  }

  /* 박스 클릭 */
  for(let i=_qs.length-1;i>=0;i--){
    if(_hitBox(p, _qs[i].box)){
      _sel = i;
      const b = _qs[i].box;
      _drag = { type:'move', qi:i, ox:p.x, oy:p.y,
                bx0:b.x, by0:b.y };
      redraw(); updatePanel(); return;
    }
  }
  _sel = -1; redraw(); updatePanel();
}

function _onMove(e){
  if(!_drag) return;
  const p = _mp(e);
  const r = v => Math.round(v*1000)/1000;

  if(_drag.type === 'draw'){
    _drag.x1 = p.x; _drag.y1 = p.y;
    redraw();
    const cid = window._currentEditorCanvas || 'preview-canvas';
    const curCanvas = document.getElementById(cid);
    if (!curCanvas) return;
    const ctx = curCanvas.getContext('2d');
    const x=Math.min(_drag.x0,_drag.x1), y=Math.min(_drag.y0,_drag.y1);
    const w=Math.abs(_drag.x1-_drag.x0), h=Math.abs(_drag.y1-_drag.y0);
    ctx.strokeStyle='#fbbf24'; ctx.lineWidth=2; ctx.setLineDash([4,3]);
    ctx.strokeRect(x,y,w,h); ctx.setLineDash([]);
    return;
  }

  if(_drag.type === 'move'){
    const dx=(p.x-_drag.ox)/_cW, dy=(p.y-_drag.oy)/_cH;
    if(dx !== 0 || dy !== 0) _drag.changed = true;
    _qs[_drag.qi].box.x = r(Math.max(0,Math.min(1-_qs[_drag.qi].box.w, _drag.bx0+dx)));
    _qs[_drag.qi].box.y = r(Math.max(0,Math.min(1-_qs[_drag.qi].box.h, _drag.by0+dy)));
    redraw(); updatePanel(); return;
  }

  if(_drag.type === 'resize'){
    const dx=(p.x-_drag.ox)/_cW, dy=(p.y-_drag.oy)/_cH;
    if(dx !== 0 || dy !== 0) _drag.changed = true;
    let {bx0,by0,bw0,bh0,handle,qi} = _drag;
    let nx=bx0,ny=by0,nw=bw0,nh=bh0;
    if(handle.includes('r')){ nw=r(Math.max(0.01,bw0+dx)); }
    if(handle.includes('l')){ nx=r(Math.min(bx0+bw0-0.01, bx0+dx)); nw=r(Math.max(0.01,bx0+bw0-nx)); }
    if(handle.includes('b')){ nh=r(Math.max(0.01,bh0+dy)); }
    if(handle.includes('t')){ ny=r(Math.min(by0+bh0-0.01, by0+dy)); nh=r(Math.max(0.01,by0+bh0-ny)); }
    _qs[qi].box = {x:nx,y:ny,w:nw,h:nh};
    redraw(); updatePanel();
  }
}

function _onUp(e){
  if(_drag && _drag.type==='draw'){
    const x=Math.min(_drag.x0,_drag.x1), y=Math.min(_drag.y0,_drag.y1);
    const w=Math.abs(_drag.x1-_drag.x0), h=Math.abs(_drag.y1-_drag.y0);
    const r=v=>Math.round(v*1000)/1000;
    if(w/_cW>0.01 && h/_cH>0.01){
      _qs.push({ number:_qs.length+1, type:'객관식', page:1,
        box:{x:r(x/_cW),y:r(y/_cH),w:r(w/_cW),h:r(h/_cH)} });
      _sel = _qs.length-1;
      setEditorMode('select');
      saveState();
      redraw(); updatePanel();
    }
  } else if (_drag && (_drag.type === 'move' || _drag.type === 'resize') && _drag.changed) {
    saveState();
  }
  _drag = null;
}

/* ── 삭제 ───────────────────────────────────────────── */
function deleteSelected(){
  if(_sel<0) return;
  _qs.splice(_sel,1);
  _sel = -1; saveState(); redraw(); updatePanel();
}

/* ── 패널 업데이트 ───────────────────────────────────── */
function updatePanel(){
  const delBtn = document.getElementById('del-btn');
  if (delBtn) delBtn.disabled = (_sel<0);
  const panel = document.getElementById('editor-panel');
  if (!panel) return;
  if(_sel<0){ panel.innerHTML='<span style="color:#64748b">문항을 선택하세요</span>'; return; }
  const q = _qs[_sel]; const b = q.box;
  panel.innerHTML = `
    <div style="margin-bottom:8px;font-weight:600;color:#f1f5f9">문항 ${q.number}</div>
    <label style="font-size:10px;color:#64748b">번호</label>
    <input type="number" value="${q.number}" min="1"
      onchange="_qs[${_sel}].number=+this.value;saveState();redraw()"
      style="width:100%;padding:3px 6px;background:#1e293b;border:1px solid #334155;border-radius:4px;color:#f1f5f9;font-size:12px;margin-bottom:6px">
    <label style="font-size:10px;color:#64748b">유형</label>
    <select onchange="_qs[${_sel}].type=this.value;saveState();redraw()"
      style="width:100%;padding:3px 6px;background:#1e293b;border:1px solid #334155;border-radius:4px;color:#f1f5f9;font-size:12px;margin-bottom:6px">
      ${['객관식','단답형','서술형'].map(t=>`<option${t===q.type?' selected':''}>${t}</option>`).join('')}
    </select>
    <label style="font-size:10px;color:#64748b">페이지</label>
    <input type="number" value="${q.page||1}" min="1"
      onchange="_qs[${_sel}].page=+this.value;saveState()"
      style="width:100%;padding:3px 6px;background:#1e293b;border:1px solid #334155;border-radius:4px;color:#f1f5f9;font-size:12px;margin-bottom:6px">
    <div style="font-size:10px;color:#64748b;margin-bottom:2px">박스 좌표 (0~1)</div>
    ${['x','y','w','h'].map(k=>`
    <div style="display:flex;align-items:center;gap:4px;margin-bottom:3px">
      <span style="width:12px;color:#94a3b8;font-size:11px">${k}</span>
      <input type="number" value="${b[k]}" step="0.001" min="0" max="1"
        onchange="_qs[${_sel}].box.${k}=+this.value;saveState();redraw()"
        style="flex:1;padding:2px 5px;background:#1e293b;border:1px solid #334155;border-radius:4px;color:#f1f5f9;font-size:11px">
    </div>`).join('')}`;
}

/* ── 렌더링 ─────────────────────────────────────────── */
function redraw(){
  const cid = window._currentEditorCanvas || 'preview-canvas';
  const cv = document.getElementById(cid);
  if(!cv) return;
  const ctx = cv.getContext('2d');
  ctx.clearRect(0,0,_cW,_cH);
  
  if(_bgImg) {
      ctx.drawImage(_bgImg,0,0,_cW,_cH);
  }
  
  _qs.forEach((q,i)=>{
    const b=q.box;
    if(!b) return;
    const {px,py,pw,ph} = _boxPx(b);
    const col = tc(q.type);
    const isSel = (i===_sel);
    ctx.fillStyle = col.fill; ctx.fillRect(px,py,pw,ph);
    ctx.strokeStyle = isSel?'#fbbf24':col.stroke;
    ctx.lineWidth   = isSel?2.5:1.5;
    ctx.strokeRect(px,py,pw,ph);
    ctx.fillStyle='#fff';
    ctx.font=`bold ${Math.max(11,Math.round(_cH*0.016))}px sans-serif`;
    ctx.fillText(String(q.number), px+3, py+Math.max(13,Math.round(_cH*0.018)));

    /* 선택된 박스 핸들 */
    if(isSel && _mode==='select'){
      [[px,py],[px+pw/2,py],[px+pw,py],
       [px,py+ph/2],[px+pw,py+ph/2],
       [px,py+ph],[px+pw/2,py+ph],[px+pw,py+ph]].forEach(([hx,hy])=>{
        ctx.fillStyle='#fbbf24';
        ctx.fillRect(hx-HANDLE/2,hy-HANDLE/2,HANDLE,HANDLE);
      });
    }
  });
}

/* ── 외부 접근용 getter ─────────────────────────────── */
function editorGetQuestions(){ return _qs; }
