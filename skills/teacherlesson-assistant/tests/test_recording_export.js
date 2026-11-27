/**
 * tests/test_recording_export.js
 * web/recording_export.js 순수 함수 시험.  실행: node tests/test_recording_export.js
 */
'use strict';
const assert = require('assert');
const path = require('path');
const { exportUrl, exportName } = require(path.join(__dirname, '..', 'web', 'recording_export.js'));

let n = 0;
function t(name, fn) { fn(); n += 1; }

t('재생 주소를 내보내기 주소로 바꾼다', () => {
  assert.strictEqual(exportUrl('/api/recording/2026-11-27/3%EA%B5%90%EC%8B%9C_%EA%B5%AD%EC%96%B4.webm', 'mp3'),
    '/api/recording-export/2026-11-27/3%EA%B5%90%EC%8B%9C_%EA%B5%AD%EC%96%B4.webm?format=mp3');
});
t('형식은 m4a 만 따로, 그 밖은 mp3', () => {
  assert.ok(exportUrl('/api/recording/2026-11-27/a.webm', 'm4a').endsWith('?format=m4a'));
  assert.ok(exportUrl('/api/recording/2026-11-27/a.webm', 'wav').endsWith('?format=mp3'));
  assert.ok(exportUrl('/api/recording/2026-11-27/a.webm').endsWith('?format=mp3'));
});
t('재생 주소가 아니면 빈 글', () => {
  for (const bad of ['', null, undefined, '/api/recordings?date=2026-11-27', '/api/recording/2026-11-27',
    '/api/recording/2026-11-27/a/b.webm', 'https://x.example/api/recording/d/a.webm', '/api/recording-export/d/a.webm']) {
    assert.strictEqual(exportUrl(bad, 'mp3'), '', String(bad));
  }
});
t('저장 이름은 확장자만 바꾼다', () => {
  assert.strictEqual(exportName('3교시_국어_101500.webm', 'mp3'), '3교시_국어_101500.mp3');
  assert.strictEqual(exportName('a.b.mp4', 'm4a'), 'a.b.m4a');
  assert.strictEqual(exportName('이름만', 'mp3'), '이름만.mp3');
});
t('이름이 없거나 확장자만 있어도 깨지지 않는다', () => {
  assert.strictEqual(exportName('', 'mp3'), '녹음.mp3');
  assert.strictEqual(exportName(null, 'mp3'), '녹음.mp3');
  assert.strictEqual(exportName('.webm', 'mp3'), '녹음.mp3');
});
console.log(`recording_export: ${n}개 통과`);
