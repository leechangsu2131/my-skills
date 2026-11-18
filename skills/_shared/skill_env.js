// my-skills 공통 환경 로더 (Node용). 규칙은 skill_env.py 와 동일하다.
//   const { loadEnv, dataDir } = require('../_shared/skill_env.js');
//   loadEnv('util-storagemap');
// ESM(next.config.mjs 등):  import { createRequire } from 'module'; createRequire(import.meta.url)('../_shared/skill_env.js').loadEnv('스킬명');
'use strict';
const fs = require('fs');
const os = require('os');
const path = require('path');

const ONEDRIVE_FOLDER_NAME = 'OneDrive - gyo6.net';
const CENTRAL_ENV_RELATIVE = path.join('96. 인증', '.env');
const DATA_FOLDER_NAME = 'my-skills-data';

const expand = (v) =>
  v.replace(/%([A-Za-z_][A-Za-z0-9_]*)%/g, (m, name) => (process.env[name] ?? m))
   .replace(/^~(?=$|[\\/])/, os.homedir());

function centralEnvPath() {
  const cands = [];
  if (process.env.MY_SKILLS_ENV) cands.push(expand(process.env.MY_SKILLS_ENV));
  for (const v of ['OneDriveCommercial', 'OneDrive']) if (process.env[v]) cands.push(path.join(process.env[v], CENTRAL_ENV_RELATIVE));
  cands.push(path.join(os.homedir(), ONEDRIVE_FOLDER_NAME, CENTRAL_ENV_RELATIVE));
  return cands.find((p) => { try { return fs.statSync(p).isFile(); } catch { return false; } }) || null;
}

// python-dotenv 와 같은 규칙: "…"(여러 줄 가능, \n 등 이스케이프 해석), '…'(여러 줄 가능, 그대로), 따옴표 없음(# 주석 제거)
function parse(text) {
  const src = text.replace(/^﻿/, '').replace(/\r\n?/g, '\n');
  const out = {};
  const re = /^[ \t]*(?:export[ \t]+)?([A-Za-z_][A-Za-z0-9_.-]*)[ \t]*=[ \t]*/gm;
  let m;
  while ((m = re.exec(src))) {
    const key = m[1];
    let i = re.lastIndex;
    const q = src[i];
    let value;
    if (q === '"' || q === "'") {
      let j = i + 1;
      while (j < src.length && !(src[j] === q && src[j - 1] !== '\\')) j++;
      value = src.slice(i + 1, j);
      value = q === '"'
        ? value.replace(/\\([\\'"abfnrtv])/g, (_, c) => ({ a: '\x07', b: '\b', f: '\f', n: '\n', r: '\r', t: '\t', v: '\v' }[c] ?? c))
        : value.replace(/\\([\\'])/g, '$1');
      const eol = src.indexOf('\n', j);
      re.lastIndex = eol === -1 ? src.length : eol;
    } else {
      const eol = src.indexOf('\n', i);
      value = src.slice(i, eol === -1 ? src.length : eol).replace(/[ \t]+#.*$/, '').trim();
      re.lastIndex = eol === -1 ? src.length : eol;
    }
    out[key] = value;
  }
  return out;
}

function envValues(skill) {
  const p = centralEnvPath();
  if (!p) return {};
  const raw = parse(fs.readFileSync(p, 'utf8'));
  const prefix = skill ? skill.toUpperCase().replace(/-/g, '_') + '__' : null;
  const merged = {}; const scoped = {};
  for (const [k, v] of Object.entries(raw)) {
    if (k.includes('__')) { if (prefix && k.startsWith(prefix)) scoped[k.slice(prefix.length)] = v; continue; }
    merged[k] = v;
  }
  Object.assign(merged, scoped);
  for (const k of Object.keys(merged)) merged[k] = expand(String(merged[k] ?? ''));
  return merged;
}

function loadEnv(skill, { override = false } = {}) {
  const values = envValues(skill);
  for (const [k, v] of Object.entries(values)) if (override || !(k in process.env)) process.env[k] = v;
  return centralEnvPath();
}

function dataDir(skill, ...sub) {
  const base = process.env.MY_SKILLS_DATA_DIR || envValues(skill).MY_SKILLS_DATA_DIR;
  const root = base ? expand(base) : path.join(os.homedir(), 'Documents', DATA_FOLDER_NAME);
  const p = path.join(root, skill || '_misc', ...sub);
  fs.mkdirSync(p, { recursive: true });
  return p;
}

module.exports = { loadEnv, envValues, dataDir, centralEnvPath };
