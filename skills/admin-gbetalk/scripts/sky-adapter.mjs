import { spawn } from 'node:child_process';
import readline from 'node:readline';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

const engineScript = fileURLToPath(new URL('./sky_engine.py', import.meta.url));
const pythonExe = 'C:\\Users\\user\\.gemini\\antigravity\\scratch\\repos\\windows-computer-use-mcp\\.venv\\Scripts\\python.exe';

export async function createSkyClient(options = {}) {
  // If in ChatGPT Codex environment
  if (globalThis.nodeRepl || process.env.OAI_SKY_CONFIG_PATH) {
    try {
      const { create_client } = await import('@oai/sky');
      return await create_client({ api: 'desktop', target: 'windows', ...options });
    } catch (e) {
      // Fallback if @oai/sky import fails
    }
  }

  // Antigravity / Local environment via sky_engine.py
  return createLocalEngineClient();
}

function createLocalEngineClient() {
  const child = spawn(pythonExe, [engineScript], {
    windowsHide: true,
    stdio: ['pipe', 'pipe', 'pipe']
  });

  const lines = readline.createInterface({ input: child.stdout, crlfDelay: Infinity });
  const pending = new Map();
  let nextRequestId = 0;
  let stderr = '';
  let closed = false;

  const failPending = (error) => {
    for (const request of pending.values()) request.reject(error);
    pending.clear();
  };

  lines.on('line', (line) => {
    let response;
    try {
      response = JSON.parse(line);
    } catch {
      failPending(new Error(`엔진 응답 JSON 파싱 실패: ${line.slice(0, 300)}`));
      return;
    }
    const request = pending.get(response.id);
    if (!request) return;
    pending.delete(response.id);
    if (response.ok) {
      request.resolve(response.data !== undefined ? response.data : true);
    } else {
      request.reject(new Error(`엔진 오류: ${response.error ?? '알 수 없는 오류'}`));
    }
  });

  child.stderr.on('data', (chunk) => {
    stderr = `${stderr}${chunk.toString('utf8')}`.slice(-2000);
  });

  child.on('error', (error) => {
    closed = true;
    failPending(new Error(`sky_engine 프로세스 시작 실패: ${error.message}`));
  });

  child.on('close', (code, signal) => {
    closed = true;
    failPending(new Error(`sky_engine 프로세스 종료됨 (${code ?? signal ?? 'unknown'}). ${stderr}`));
  });

  const sendRequest = (payload) => new Promise((resolve, reject) => {
    if (closed || child.stdin.destroyed) {
      reject(new Error('sky_engine 프로세스가 닫혀 있습니다.'));
      return;
    }
    const id = ++nextRequestId;
    pending.set(id, { resolve, reject });
    child.stdin.write(`${JSON.stringify({ ...payload, id })}\n`, (error) => {
      if (!error) return;
      pending.delete(id);
      reject(new Error(`요청 전송 실패: ${error.message}`));
    });
  });

  return {
    async get_window_state({ window, include_text = true, include_screenshot = false } = {}) {
      return await sendRequest({
        cmd: 'get_window_state',
        window,
        include_text,
        include_screenshot
      });
    },

    async press_key({ window, key } = {}) {
      return await sendRequest({
        cmd: 'press_key',
        window,
        key
      });
    },

    async click({ window, element_index = 8 } = {}) {
      return await sendRequest({
        cmd: 'click',
        window,
        element_index
      });
    },

    async close() {
      if (closed) return;
      closed = true;
      child.kill();
    }
  };
}
