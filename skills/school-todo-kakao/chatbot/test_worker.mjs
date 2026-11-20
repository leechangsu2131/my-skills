import http from 'node:http';
import worker from './cloudflare_worker.js';

// 앱스 스크립트 웹앱 흉내: POST /exec → 302 → GET /echo 가 실제 JSON을 준다
let received = null;
const srv = http.createServer((req, res) => {
  if (req.method === 'POST' && req.url.startsWith('/exec')) {
    let b = ''; req.on('data', d => b += d); req.on('end', () => {
      received = { url: req.url, body: b };
      res.writeHead(302, { Location: `http://127.0.0.1:${srv.address().port}/echo?x=1` }); res.end();
    });
  } else if (req.method === 'GET' && req.url.startsWith('/echo')) {
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ version: '2.0', template: { outputs: [{ simpleText: { text: '선생님의 챗봇 아이디예요:\ntest' } }] } }));
  } else if (req.url.startsWith('/bad')) { res.writeHead(200); res.end('<html>not json</html>'); }
  else { res.writeHead(404); res.end(); }
});
await new Promise(r => srv.listen(0, '127.0.0.1', r));
const base = `http://127.0.0.1:${srv.address().port}`;
const env = { KAKAO_KEY: 'k1', APPS_SCRIPT_URL: base + '/exec', APPS_KEY: 'a b&c' };
let pass = 0, fail = 0;
const check = (n, c, x) => c ? pass++ : (fail++, console.log('FAIL', n, x ?? ''));
const call = (method, qs, body, e = env) => worker.fetch(new Request('https://w.example/' + qs, { method, body }), e);

let r = await call('POST', '?key=k1', JSON.stringify({ userRequest: { utterance: '내아이디', user: { id: 'U1' } } }));
let t = await r.text();
check('follows 302 and returns json', r.status === 200 && JSON.parse(t).template.outputs[0].simpleText.text.includes('test'), t);
check('forwards body unchanged', JSON.parse(received.body).userRequest.user.id === 'U1', received.body);
check('adds apps key (url-encoded)', received.url.includes('key=a%20b%26c'), received.url);
check('content-type json', r.headers.get('content-type').includes('application/json'));
r = await call('POST', '?key=wrong', '{}'); check('wrong key → 403', r.status === 403);
r = await call('POST', '', '{}'); check('no key → 403', r.status === 403);
r = await call('GET', '', undefined); check('GET alive', r.status === 200 && (await r.text()).includes('켜져'));
r = await call('POST', '?key=k1', '{}', { ...env, APPS_SCRIPT_URL: base + '/bad' });
t = await r.text(); check('non-json upstream → friendly json', r.status === 200 && JSON.parse(t).version === '2.0' && t.includes('서버 연결'), t);
r = await call('POST', '?key=k1', '{}', { ...env, APPS_SCRIPT_URL: 'http://127.0.0.1:1/exec' });
t = await r.text(); check('upstream down → friendly json', r.status === 200 && t.includes('서버 연결'), t);
r = await call('POST', '?key=k1', '{}', { ...env, KAKAO_KEY: '' }); check('unset key rejects', r.status === 403);
console.log(pass + ' passed, ' + fail + ' failed');
srv.close();
