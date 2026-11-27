/* 저장된 녹음 → 클로바노트용 MP3 받기 (T99, 설계 docs/plans/clova-export.md)
 * 서버(/api/recording-export/…)가 원본은 그대로 두고 MP3 로 바꿔 주면, 그 파일을 저장한다.
 * 순수 함수 exportUrl·exportName 은 node 로 시험한다(tests/test_recording_export.js). */

/** 재생 주소(/api/recording/<날짜>/<파일>) → 내보내기 주소. 재생 주소가 아니면 ''. */
function exportUrl(url, fmt) {
  const m = /^\/api\/recording\/([^/?#]+)\/([^/?#]+)$/.exec(String(url || ''));
  if (!m) return '';
  return `/api/recording-export/${m[1]}/${m[2]}?format=${fmt === 'm4a' ? 'm4a' : 'mp3'}`;
}

/** 원래 파일 이름 → 저장할 이름(확장자만 바꿈). */
function exportName(file, fmt) {
  const ext = fmt === 'm4a' ? 'm4a' : 'mp3';
  const base = String(file || '녹음').replace(/\.[^./\\]+$/, '') || '녹음';
  return `${base}.${ext}`;
}

async function downloadExport(btn) {
  const url = exportUrl(btn.dataset.url, 'mp3');
  if (!url) return;
  const label = btn.textContent;
  btn.disabled = true;
  btn.textContent = '변환 중… (50분 녹음은 30초쯤 걸려요)';
  try {
    const res = await fetch(url);
    if (!res.ok) {
      const j = await res.json().catch(() => ({}));
      throw new Error(j.message || `변환하지 못했어요 (${res.status})`);
    }
    const blob = await res.blob();
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = exportName(btn.dataset.file, 'mp3');
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(a.href), 60000);
    btn.textContent = '✓ 받았어요 (다시 받기)';
  } catch (e) {
    btn.textContent = label;
    alert(e.message || '변환하지 못했어요.');
  } finally {
    btn.disabled = false;
  }
}

if (typeof document !== 'undefined') {
  document.addEventListener('click', ev => {
    const btn = ev.target.closest && ev.target.closest('.rec-export');
    if (btn) downloadExport(btn);
  });
}

if (typeof module !== 'undefined') {
  module.exports = { exportUrl, exportName };
}
