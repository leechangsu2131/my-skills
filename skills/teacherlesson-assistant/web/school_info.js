// 위쪽 오른쪽 "🍱 오늘 메뉴 · ☀ 12°" 한 줄 (T109). /api/school-info 를 한 번 불러 채운다.
// 급식·날씨 둘 다 없거나 인터넷이 안 되면 조용히 숨긴다(오류를 띄우지 않는다).
'use strict';

// 알레르기 번호 "(5.6)" 는 서버에서도 지우지만 한 번 더 지운다.
function stripAllergy(text) {
  return String(text == null ? '' : text).replace(/\(\s*[\d.\s,]+\s*\)/g, '').replace(/\s+/g, ' ').trim();
}

// 보여 줄 한 줄 글. 보여 줄 게 없으면 ''.
function schoolInfoText(info) {
  if (!info || info.status !== 'success') return '';
  const parts = [];
  const meal = stripAllergy(info.meal);
  if (meal) parts.push('🍱 ' + meal);
  const w = info.weather;
  if (w && Number.isFinite(Number(w.temp)) && w.temp !== null && w.temp !== '') {
    parts.push((w.icon || '🌡') + ' ' + Math.round(Number(w.temp)) + '°');
  }
  return parts.join(' · ');
}

function renderSchoolInfo(info) {
  const box = document.getElementById('schoolInfo');
  if (!box) return;
  const text = schoolInfoText(info);
  box.textContent = text;
  box.title = text;
  box.hidden = !text;
}

async function loadSchoolInfo() {
  try {
    const res = await fetch('/api/school-info');
    if (!res.ok) throw new Error(String(res.status));
    renderSchoolInfo(await res.json());
  } catch (e) {
    renderSchoolInfo(null);
  }
}

if (typeof document !== 'undefined') loadSchoolInfo();
if (typeof module !== 'undefined' && module.exports) module.exports = { stripAllergy, schoolInfoText, renderSchoolInfo };
