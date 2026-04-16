require('dotenv').config();
const express = require('express');
const cors = require('cors');
const https = require('node:https');
const path = require('path');
const tls = require('node:tls');
const { createClient } = require('@supabase/supabase-js');

const app = express();
const PORT = Number(process.env.PORT) || 3000;
const truthyValues = new Set(['1', 'true', 'yes', 'on']);
const isTruthy = (value) => truthyValues.has(String(value || '').trim().toLowerCase());
const useInsecureTls = isTruthy(process.env.SUPABASE_TLS_INSECURE);
const usingSystemCa = process.execArgv.includes('--use-system-ca');

if (useInsecureTls) {
  process.env.NODE_TLS_REJECT_UNAUTHORIZED = '0';
  console.warn('[StorageMap] SUPABASE_TLS_INSECURE=true so TLS certificate verification is disabled for this process.');
}

app.use(cors());
app.use(express.json({ limit: '2mb' }));
app.use(express.static('public'));

const TABLES = {
  spaces: process.env.SUPABASE_TABLE_SPACES || 'storage_map_spaces',
  furniture: process.env.SUPABASE_TABLE_FURNITURE || 'storage_map_furniture',
  zones: process.env.SUPABASE_TABLE_ZONES || 'storage_map_zones',
  items: process.env.SUPABASE_TABLE_ITEMS || 'storage_map_items',
  history: process.env.SUPABASE_TABLE_HISTORY || 'storage_map_history',
};

const COLUMNS = {
  spaces: ['space_id', 'name', 'description', 'created_at', 'updated_at'],
  furniture: ['furniture_id', 'space_id', 'name', 'type', 'pos_x', 'pos_y', 'width', 'height', 'color', 'notes', 'created_at', 'updated_at'],
  zones: ['zone_id', 'furniture_id', 'name', 'position_desc', 'created_at', 'updated_at'],
  items: ['item_id', 'name', 'furniture_id', 'zone_id', 'category', 'tags', 'memo', 'photo_url', 'quantity', 'context', 'created_at', 'updated_at'],
  history: ['history_id', 'item_id', 'from_furniture', 'from_zone', 'to_furniture', 'to_zone', 'moved_at', 'note'],
};

const ID_COLUMNS = {
  spaces: 'space_id',
  furniture: 'furniture_id',
  zones: 'zone_id',
  items: 'item_id',
  history: 'history_id',
};

const nowIso = () => new Date().toISOString();
const makeId = (prefix) => `${prefix}${Date.now()}${Math.floor(Math.random() * 1000).toString().padStart(3, '0')}`;
const toNumber = (value, fallback = 0) => {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : fallback;
};
const optionalString = (value) => (value === undefined || value === null || value === '' ? undefined : String(value));
const stripUndefined = (record) => Object.fromEntries(Object.entries(record).filter(([, value]) => value !== undefined));
const pickRecord = (tableKey, record) => stripUndefined(COLUMNS[tableKey].reduce((acc, column) => ({ ...acc, [column]: record[column] }), {}));
const countStats = (cache) => ({ spaces: cache.spaces.length, furniture: cache.furniture.length, items: cache.items.length, history: cache.history.length });
const unwrapErrorDetails = (error) => {
  const details = [];
  let current = error;
  let depth = 0;
  while (current && depth < 5) {
    const detail = [current.message, current.code].filter(Boolean).join(' ').trim();
    if (detail && !details.includes(detail)) details.push(detail);
    current = current.cause;
    depth += 1;
  }
  return details;
};
const formatSupabaseError = (error) => {
  const summary = unwrapErrorDetails(error).join(' <- ') || String(error);
  if (/(SELF_SIGNED_CERT_IN_CHAIN|DEPTH_ZERO_SELF_SIGNED_CERT|UNABLE_TO_VERIFY_LEAF_SIGNATURE)/i.test(summary)) {
    return 'TLS certificate trust error while connecting to Supabase. Start Node with --use-system-ca or set SUPABASE_TLS_INSECURE=true for local-only development.';
  }
  return summary;
};
const systemCaCertificates = (() => {
  if (useInsecureTls || typeof tls.getCACertificates !== 'function') return [];
  try {
    return Array.from(new Set([
      ...(tls.getCACertificates('default') || []),
      ...(tls.getCACertificates('system') || []),
    ]));
  } catch (_error) {
    return [];
  }
})();
const useSystemCaFetch = systemCaCertificates.length > 0;
const buildResponseHeaders = (headers = {}) => {
  const responseHeaders = new Headers();
  for (const [key, value] of Object.entries(headers)) {
    if (Array.isArray(value)) value.forEach((entry) => responseHeaders.append(key, entry));
    else if (value !== undefined) responseHeaders.set(key, String(value));
  }
  return responseHeaders;
};
const systemCaFetch = async (input, init = {}) => {
  const request = new Request(input, init);
  const url = new URL(request.url);
  if (url.protocol !== 'https:' || !useSystemCaFetch) return fetch(request);

  const headers = {};
  request.headers.forEach((value, key) => {
    headers[key] = value;
  });

  const bodyBuffer = request.method === 'GET' || request.method === 'HEAD'
    ? null
    : Buffer.from(await request.arrayBuffer());

  return new Promise((resolve, reject) => {
    const upstream = https.request({
      protocol: url.protocol,
      hostname: url.hostname,
      port: url.port || 443,
      path: `${url.pathname}${url.search}`,
      method: request.method,
      headers,
      ca: systemCaCertificates,
    }, (response) => {
      const chunks = [];
      response.on('data', (chunk) => chunks.push(chunk));
      response.on('end', () => {
        const status = response.statusCode || 500;
        const body = [204, 205, 304].includes(status) || request.method === 'HEAD'
          ? null
          : Buffer.concat(chunks);
        resolve(new Response(body, {
          status,
          statusText: response.statusMessage || '',
          headers: buildResponseHeaders(response.headers),
        }));
      });
    });

    upstream.on('error', reject);
    if (bodyBuffer) upstream.write(bodyBuffer);
    upstream.end();
  });
};

function parseTags(value) {
  if (Array.isArray(value)) return value.map(String).filter(Boolean);
  if (typeof value !== 'string') return [];
  const trimmed = value.trim();
  if (!trimmed) return [];
  if (trimmed.startsWith('[') && trimmed.endsWith(']')) {
    try {
      const parsed = JSON.parse(trimmed);
      if (Array.isArray(parsed)) return parsed.map(String).filter(Boolean);
    } catch (_error) {}
  }
  return trimmed.split(',').map((tag) => tag.trim()).filter(Boolean);
}

const NORMALIZE = {
  spaces: (row = {}) => ({
    space_id: String(row.space_id || ''),
    name: String(row.name || ''),
    description: String(row.description || ''),
    created_at: optionalString(row.created_at),
    updated_at: optionalString(row.updated_at),
  }),
  furniture: (row = {}) => ({
    furniture_id: String(row.furniture_id || ''),
    space_id: String(row.space_id || ''),
    name: String(row.name || ''),
    type: String(row.type || ''),
    pos_x: toNumber(row.pos_x, 0),
    pos_y: toNumber(row.pos_y, 0),
    width: toNumber(row.width, 120),
    height: toNumber(row.height, 80),
    color: optionalString(row.color),
    notes: String(row.notes || ''),
    created_at: optionalString(row.created_at),
    updated_at: optionalString(row.updated_at),
  }),
  zones: (row = {}) => ({
    zone_id: String(row.zone_id || ''),
    furniture_id: String(row.furniture_id || ''),
    name: String(row.name || ''),
    position_desc: optionalString(row.position_desc),
    created_at: optionalString(row.created_at),
    updated_at: optionalString(row.updated_at),
  }),
  items: (row = {}) => ({
    item_id: String(row.item_id || ''),
    name: String(row.name || ''),
    furniture_id: String(row.furniture_id || ''),
    zone_id: optionalString(row.zone_id),
    category: String(row.category || '기타'),
    tags: parseTags(row.tags),
    memo: String(row.memo || ''),
    photo_url: optionalString(row.photo_url),
    quantity: toNumber(row.quantity, 1),
    context: optionalString(row.context),
    created_at: optionalString(row.created_at),
    updated_at: optionalString(row.updated_at),
  }),
  history: (row = {}) => ({
    history_id: String(row.history_id || ''),
    item_id: String(row.item_id || ''),
    from_furniture: optionalString(row.from_furniture),
    from_zone: optionalString(row.from_zone),
    to_furniture: optionalString(row.to_furniture),
    to_zone: optionalString(row.to_zone),
    moved_at: optionalString(row.moved_at) || nowIso(),
    note: String(row.note || ''),
  }),
};

class StorageMapService {
  constructor() {
    this.cache = { spaces: [], furniture: [], zones: [], items: [], history: [] };
    this.client = this.createSupabaseClient();
    this.mode = 'sample';
    this.lastError = null;
  }

  createSupabaseClient() {
    const url = process.env.SUPABASE_URL;
    const key = process.env.SUPABASE_SERVICE_ROLE_KEY || process.env.SUPABASE_KEY || process.env.SUPABASE_ANON_KEY;
    const placeholderUrl = url && url.includes('your-project.supabase.co');
    const placeholderKey = key && key.includes('your_service_role_key_here');
    if (!url || !key || placeholderUrl || placeholderKey) return null;
    return createClient(url, key, {
      auth: { autoRefreshToken: false, persistSession: false },
      global: { fetch: systemCaFetch },
    });
  }

  normalize(tableKey, row) {
    return NORMALIZE[tableKey](row);
  }

  isConfigured() {
    return Boolean(this.client);
  }

  isConnected() {
    return this.mode === 'supabase';
  }

  ensureConfigured() {
    if (!this.client) throw new Error('Supabase 환경변수가 설정되지 않았습니다. SUPABASE_URL과 서비스 키를 확인하세요.');
  }

  getStatus() {
    return {
      authenticated: this.isConnected(),
      configured: this.isConfigured(),
      provider: 'supabase',
      mode: this.mode,
      tls: {
        useSystemCa: usingSystemCa || useSystemCaFetch,
        insecure: useInsecureTls,
      },
      readOnly: !this.isConfigured(),
      lastError: this.lastError,
      tables: TABLES,
      timestamp: nowIso(),
    };
  }

  loadSampleData() {
    this.cache = {
      spaces: [
        { space_id: 's1', name: '교실 창고', description: '수업 교재와 비품을 보관하는 기본 샘플 공간' },
        { space_id: 's2', name: '거실 수납장', description: '가정용 수납 예시 공간' },
      ],
      furniture: [
        { furniture_id: 'f1', space_id: 's1', name: '교재 선반', type: '선반', pos_x: 20, pos_y: 40, width: 120, height: 70, color: '#CBD5E1', notes: '자주 쓰는 교재 보관' },
        { furniture_id: 'f2', space_id: 's1', name: '교사용 책상', type: '책상', pos_x: 250, pos_y: 25, width: 150, height: 60, color: '#BFDBFE', notes: '' },
        { furniture_id: 'f3', space_id: 's2', name: 'TV 수납장', type: '수납장', pos_x: 30, pos_y: 35, width: 180, height: 70, color: '#FDE68A', notes: '' },
      ],
      zones: [],
      items: [
        { item_id: 'i1', name: '리코더', furniture_id: 'f1', category: '교구', quantity: 25, memo: '', tags: [] },
        { item_id: 'i2', name: '과학 교재 세트', furniture_id: 'f1', category: '교재', quantity: 5, memo: '학기별 교체', tags: [] },
        { item_id: 'i3', name: '리모컨', furniture_id: 'f3', category: '전자기기', quantity: 2, memo: '', tags: [] },
      ],
      history: [],
    };
    return this.cache;
  }

  async initialize() {
    if (!this.isConfigured()) {
      this.loadSampleData();
      console.log('ℹ️ Supabase 설정이 없어 샘플 데이터로 시작합니다.');
      return;
    }
    const result = await this.loadRemote({ fallbackToSample: true });
    console.log(result.source === 'supabase' ? '✅ Supabase 데이터 로드 완료' : '⚠️ Supabase 연결 실패로 샘플 데이터로 전환', countStats(result.data));
    if (result.warning) console.warn(`   원인: ${result.warning}`);
  }

  async fetchTable(tableKey, { orderBy, optional = false } = {}) {
    let query = this.client.from(TABLES[tableKey]).select('*');
    if (orderBy) query = query.order(orderBy, { ascending: true });
    const { data, error } = await query;
    if (error) {
      const formattedError = formatSupabaseError(error);
      if (optional) {
        console.warn(`⚠️ 선택 테이블 ${TABLES[tableKey]} 로드 실패: ${formattedError}`);
        return [];
      }
      throw new Error(`${TABLES[tableKey]} 테이블을 읽지 못했습니다: ${formattedError}`);
    }
    return data || [];
  }

  async loadRemote({ fallbackToSample = true } = {}) {
    this.ensureConfigured();
    try {
      const [spaces, furniture, zones, items, history] = await Promise.all([
        this.fetchTable('spaces', { orderBy: 'space_id' }),
        this.fetchTable('furniture', { orderBy: 'furniture_id' }),
        this.fetchTable('zones', { orderBy: 'zone_id', optional: true }),
        this.fetchTable('items', { orderBy: 'item_id' }),
        this.fetchTable('history', { orderBy: 'moved_at', optional: true }),
      ]);
      this.cache = {
        spaces: spaces.map((row) => this.normalize('spaces', row)).filter((row) => row.space_id),
        furniture: furniture.map((row) => this.normalize('furniture', row)).filter((row) => row.furniture_id),
        zones: zones.map((row) => this.normalize('zones', row)).filter((row) => row.zone_id),
        items: items.map((row) => this.normalize('items', row)).filter((row) => row.item_id),
        history: history.map((row) => this.normalize('history', row)).filter((row) => row.history_id),
      };
      this.mode = 'supabase';
      this.lastError = null;
      return { source: 'supabase', data: this.cache };
    } catch (error) {
      this.lastError = formatSupabaseError(error);
      if (!fallbackToSample) throw error;
      this.loadSampleData();
      this.mode = 'sample';
      return { source: 'sample', data: this.cache, warning: this.lastError };
    }
  }

  async upsert(tableKey, record) {
    this.ensureConfigured();
    const payload = pickRecord(tableKey, record);
    const { data, error } = await this.client.from(TABLES[tableKey]).upsert(payload, { onConflict: ID_COLUMNS[tableKey] }).select().maybeSingle();
    if (error) throw new Error(`${TABLES[tableKey]} 저장 실패: ${formatSupabaseError(error)}`);
    return this.normalize(tableKey, data || payload);
  }

  async delete(tableKey, idValue) {
    this.ensureConfigured();
    const { error } = await this.client.from(TABLES[tableKey]).delete().eq(ID_COLUMNS[tableKey], idValue);
    if (error) throw new Error(`${TABLES[tableKey]} 삭제 실패: ${formatSupabaseError(error)}`);
  }

  replaceCache(tableKey, record) {
    const idColumn = ID_COLUMNS[tableKey];
    const index = this.cache[tableKey].findIndex((row) => row[idColumn] === record[idColumn]);
    if (index === -1) this.cache[tableKey].push(record);
    else this.cache[tableKey][index] = record;
    return record;
  }

  removeCache(tableKey, idValue) {
    const idColumn = ID_COLUMNS[tableKey];
    const index = this.cache[tableKey].findIndex((row) => row[idColumn] === idValue);
    if (index === -1) return null;
    return this.cache[tableKey].splice(index, 1)[0];
  }

  async persist(tableKey, record) {
    const saved = await this.upsert(tableKey, record);
    return this.replaceCache(tableKey, saved);
  }

  async persistHistory(record) {
    try {
      return await this.persist('history', record);
    } catch (error) {
      console.warn(`⚠️ 이동 이력 저장 실패: ${error.message}`);
      return record;
    }
  }

  searchItems(query) {
    const q = query.trim().toLowerCase();
    if (!q) return [];
    return this.cache.items
      .map((item) => {
        const score =
          item.name.toLowerCase() === q ? 100 :
          item.name.toLowerCase().includes(q) ? 80 :
          item.category.toLowerCase().includes(q) ? 60 :
          item.memo.toLowerCase().includes(q) ? 40 :
          item.tags.some((tag) => tag.toLowerCase().includes(q)) ? 40 : 0;
        if (!score) return null;
        const furniture = this.cache.furniture.find((row) => row.furniture_id === item.furniture_id);
        const space = this.cache.spaces.find((row) => row.space_id === furniture?.space_id);
        return { ...item, matchScore: score, furniture: furniture?.name || '위치 미정', space: space?.name || '공간 미정', path: `${space?.name || '?'} > ${furniture?.name || '?'}` };
      })
      .filter(Boolean)
      .sort((left, right) => right.matchScore - left.matchScore);
  }

  getSpaceData(spaceId) {
    const space = this.cache.spaces.find((row) => row.space_id === spaceId);
    if (!space) return null;
    const furniture = this.cache.furniture.filter((row) => row.space_id === spaceId);
    const items = this.cache.items.filter((item) => furniture.some((row) => row.furniture_id === item.furniture_id));
    return {
      space,
      furniture: furniture.map((row) => ({
        ...row,
        items: this.cache.items.filter((item) => item.furniture_id === row.furniture_id),
        itemCount: this.cache.items.filter((item) => item.furniture_id === row.furniture_id).length,
      })),
      items,
    };
  }

  getAllData() {
    return this.cache;
  }
}

const storageService = new StorageMapService();
const initializationPromise = storageService.initialize();

app.use('/api', async (_req, _res, next) => {
  try {
    await initializationPromise;
    next();
  } catch (error) {
    next(error);
  }
});

const requireRemoteStorage = (_req, res, next) => {
  if (!storageService.isConfigured()) {
    return res.status(503).json({ error: 'Supabase가 설정되지 않아 쓰기 작업을 할 수 없습니다. .env 파일을 먼저 설정하세요.' });
  }
  next();
};

const reloadData = async () => (
  storageService.isConfigured()
    ? storageService.loadRemote({ fallbackToSample: true })
    : { source: 'sample', data: storageService.loadSampleData() }
);

const reloadPayload = (result) => ({
  success: true,
  source: result.source,
  message: result.source === 'supabase' ? 'Supabase 데이터를 불러왔습니다.' : 'Supabase 연결에 실패해 샘플 데이터를 불러왔습니다.',
  warning: result.warning,
  stats: countStats(result.data),
  data: result.data,
});

app.get('/api/health', (_req, res) => res.json({ status: 'ok', ...storageService.getStatus(), stats: countStats(storageService.getAllData()) }));
app.get('/api/auth/status', (_req, res) => res.json(storageService.getStatus()));
app.get('/api/data', (_req, res) => res.json(storageService.getAllData()));
app.get('/api/data/load', async (_req, res) => { try { res.json(reloadPayload(await reloadData())); } catch (error) { res.status(500).json({ success: false, error: error.message }); } });
app.get('/api/data/reload', async (_req, res) => { try { res.json(reloadPayload(await reloadData())); } catch (error) { res.status(500).json({ success: false, error: error.message }); } });
app.get('/api/debug/supabase', (_req, res) => res.json({ ...storageService.getStatus(), stats: countStats(storageService.getAllData()), sampleSpace: storageService.cache.spaces[0] || null, sampleFurniture: storageService.cache.furniture[0] || null, sampleItem: storageService.cache.items[0] || null }));
app.get('/api/auth/token', (_req, res) => res.status(410).json({ error: 'Google OAuth 토큰 API는 제거되었습니다. Supabase 연결 정보는 .env 파일에서 관리하세요.' }));

app.get('/api/spaces', (_req, res) => {
  res.json(storageService.cache.spaces.map((space) => ({ ...space, furnitureCount: storageService.cache.furniture.filter((row) => row.space_id === space.space_id).length })));
});

app.get('/api/spaces/:spaceId/furniture', (req, res) => {
  const { spaceId } = req.params;
  res.json(storageService.cache.furniture.filter((row) => row.space_id === spaceId).map((row) => {
    const items = storageService.cache.items.filter((item) => item.furniture_id === row.furniture_id);
    return { ...row, itemCount: items.length, items };
  }));
});

app.get('/api/spaces/:spaceId', (req, res) => {
  const data = storageService.getSpaceData(req.params.spaceId);
  if (!data) return res.status(404).json({ error: '공간을 찾을 수 없습니다.' });
  res.json(data);
});

app.get('/api/search', (req, res) => {
  if (!req.query.q) return res.status(400).json({ error: '검색어가 필요합니다.' });
  res.json({ query: req.query.q, results: storageService.searchItems(String(req.query.q)) });
});

app.get('/api/floorplan/:spaceId', (req, res) => {
  const data = storageService.getSpaceData(req.params.spaceId);
  if (!data) return res.status(404).json({ error: '공간을 찾을 수 없습니다.' });
  res.json({ space: data.space, furniture: data.furniture.map((row) => ({ id: row.furniture_id, name: row.name, type: row.type, x: row.pos_x, y: row.pos_y, width: row.width, height: row.height, itemCount: row.itemCount, items: row.items })) });
});

app.put('/api/furniture/:furnitureId/position', requireRemoteStorage, async (req, res) => {
  try {
    const furniture = storageService.cache.furniture.find((row) => row.furniture_id === req.params.furnitureId);
    if (!furniture) return res.status(404).json({ error: '가구를 찾을 수 없습니다.' });
    const saved = await storageService.persist('furniture', NORMALIZE.furniture({ ...furniture, pos_x: req.body.x !== undefined ? toNumber(req.body.x, furniture.pos_x) : furniture.pos_x, pos_y: req.body.y !== undefined ? toNumber(req.body.y, furniture.pos_y) : furniture.pos_y, width: req.body.width !== undefined ? toNumber(req.body.width, furniture.width) : furniture.width, height: req.body.height !== undefined ? toNumber(req.body.height, furniture.height) : furniture.height, updated_at: nowIso() }));
    res.json({ success: true, message: '가구 위치가 업데이트되었습니다.', furniture: { id: saved.furniture_id, x: saved.pos_x, y: saved.pos_y, width: saved.width, height: saved.height } });
  } catch (error) {
    res.status(500).json({ error: `위치 업데이트 실패: ${error.message}` });
  }
});

app.put('/api/furniture/:furnitureId', requireRemoteStorage, async (req, res) => {
  try {
    const furniture = storageService.cache.furniture.find((row) => row.furniture_id === req.params.furnitureId);
    if (!furniture) return res.status(404).json({ error: '가구를 찾을 수 없습니다.' });
    const saved = await storageService.persist('furniture', NORMALIZE.furniture({ ...furniture, name: req.body.name !== undefined ? String(req.body.name) : furniture.name, type: req.body.type !== undefined ? String(req.body.type) : furniture.type, color: req.body.color !== undefined ? optionalString(req.body.color) : furniture.color, notes: req.body.notes !== undefined ? String(req.body.notes) : furniture.notes, updated_at: nowIso() }));
    res.json({ success: true, message: '가구 정보가 업데이트되었습니다.', furniture: saved });
  } catch (error) {
    res.status(500).json({ error: `가구 정보 업데이트 실패: ${error.message}` });
  }
});

app.post('/api/items', requireRemoteStorage, async (req, res) => {
  if (!req.body.name || !req.body.furniture_id) return res.status(400).json({ error: '물건 이름과 가구 ID가 필요합니다.' });
  if (!storageService.cache.furniture.some((row) => row.furniture_id === req.body.furniture_id)) return res.status(404).json({ error: '대상 가구를 찾을 수 없습니다.' });
  try {
    const timestamp = nowIso();
    const saved = await storageService.persist('items', NORMALIZE.items({ item_id: makeId('i'), name: String(req.body.name), furniture_id: String(req.body.furniture_id), category: req.body.category ? String(req.body.category) : '기타', quantity: req.body.quantity !== undefined ? toNumber(req.body.quantity, 1) : 1, memo: req.body.memo ? String(req.body.memo) : '', tags: [], created_at: timestamp, updated_at: timestamp }));
    res.json({ success: true, item: saved });
  } catch (error) {
    res.status(500).json({ error: `물건 추가 실패: ${error.message}` });
  }
});

app.post('/api/furniture', requireRemoteStorage, async (req, res) => {
  if (!req.body.name || !req.body.space_id) return res.status(400).json({ error: '가구 이름과 공간 ID가 필요합니다.' });
  if (!storageService.cache.spaces.some((row) => row.space_id === req.body.space_id)) return res.status(404).json({ error: '대상 공간을 찾을 수 없습니다.' });
  try {
    const timestamp = nowIso();
    const saved = await storageService.persist('furniture', NORMALIZE.furniture({ furniture_id: makeId('f'), name: String(req.body.name), space_id: String(req.body.space_id), type: req.body.type ? String(req.body.type) : '', pos_x: req.body.pos_x !== undefined ? toNumber(req.body.pos_x, 50) : 50, pos_y: req.body.pos_y !== undefined ? toNumber(req.body.pos_y, 50) : 50, width: req.body.width !== undefined ? toNumber(req.body.width, 120) : 120, height: req.body.height !== undefined ? toNumber(req.body.height, 80) : 80, color: req.body.color ? String(req.body.color) : undefined, notes: req.body.notes ? String(req.body.notes) : '', created_at: timestamp, updated_at: timestamp }));
    res.json({ success: true, furniture: saved });
  } catch (error) {
    res.status(500).json({ error: `가구 추가 실패: ${error.message}` });
  }
});

app.post('/api/spaces', requireRemoteStorage, async (req, res) => {
  if (!req.body.name) return res.status(400).json({ error: '공간 이름이 필요합니다.' });
  try {
    const timestamp = nowIso();
    const saved = await storageService.persist('spaces', NORMALIZE.spaces({ space_id: makeId('s'), name: String(req.body.name), description: req.body.description ? String(req.body.description) : '', created_at: timestamp, updated_at: timestamp }));
    res.json({ success: true, space: saved });
  } catch (error) {
    res.status(500).json({ error: `공간 추가 실패: ${error.message}` });
  }
});

app.put('/api/items/:itemId', requireRemoteStorage, async (req, res) => {
  try {
    const item = storageService.cache.items.find((row) => row.item_id === req.params.itemId);
    if (!item) return res.status(404).json({ error: '물건을 찾을 수 없습니다.' });
    if (req.body.furniture_id && !storageService.cache.furniture.some((row) => row.furniture_id === req.body.furniture_id)) return res.status(404).json({ error: '이동할 가구를 찾을 수 없습니다.' });
    const moved = req.body.furniture_id && req.body.furniture_id !== item.furniture_id;
    const saved = await storageService.persist('items', NORMALIZE.items({ ...item, ...stripUndefined({ name: req.body.name !== undefined ? String(req.body.name) : undefined, furniture_id: req.body.furniture_id !== undefined ? String(req.body.furniture_id) : undefined, zone_id: optionalString(req.body.zone_id), category: req.body.category !== undefined ? String(req.body.category) : undefined, tags: req.body.tags !== undefined ? parseTags(req.body.tags) : undefined, memo: req.body.memo !== undefined ? String(req.body.memo) : undefined, photo_url: optionalString(req.body.photo_url), quantity: req.body.quantity !== undefined ? toNumber(req.body.quantity, item.quantity) : undefined, context: optionalString(req.body.context) }), updated_at: nowIso() }));
    if (moved) {
      await storageService.persistHistory(NORMALIZE.history({ history_id: makeId('h'), item_id: req.params.itemId, from_furniture: item.furniture_id, from_zone: item.zone_id, to_furniture: String(req.body.furniture_id), to_zone: optionalString(req.body.zone_id), moved_at: nowIso(), note: '' }));
    }
    res.json({ success: true, item: saved });
  } catch (error) {
    res.status(500).json({ error: `물건 수정 실패: ${error.message}` });
  }
});

app.delete('/api/items/:itemId', requireRemoteStorage, async (req, res) => {
  try {
    if (!storageService.cache.items.some((row) => row.item_id === req.params.itemId)) return res.status(404).json({ error: '물건을 찾을 수 없습니다.' });
    await storageService.delete('items', req.params.itemId);
    res.json({ success: true, deleted: storageService.removeCache('items', req.params.itemId) });
  } catch (error) {
    res.status(500).json({ error: `물건 삭제 실패: ${error.message}` });
  }
});

app.delete('/api/furniture/:furnitureId', requireRemoteStorage, async (req, res) => {
  try {
    if (storageService.cache.items.some((row) => row.furniture_id === req.params.furnitureId)) return res.status(400).json({ error: '가구 안에 물건이 있습니다. 먼저 물건을 비워주세요.' });
    if (!storageService.cache.furniture.some((row) => row.furniture_id === req.params.furnitureId)) return res.status(404).json({ error: '가구를 찾을 수 없습니다.' });
    await storageService.delete('furniture', req.params.furnitureId);
    res.json({ success: true, deleted: storageService.removeCache('furniture', req.params.furnitureId) });
  } catch (error) {
    res.status(500).json({ error: `가구 삭제 실패: ${error.message}` });
  }
});

app.put('/api/spaces/:spaceId', requireRemoteStorage, async (req, res) => {
  try {
    const space = storageService.cache.spaces.find((row) => row.space_id === req.params.spaceId);
    if (!space) return res.status(404).json({ error: '공간을 찾을 수 없습니다.' });
    const saved = await storageService.persist('spaces', NORMALIZE.spaces({ ...space, name: req.body.name !== undefined ? String(req.body.name) : space.name, description: req.body.description !== undefined ? String(req.body.description) : space.description, updated_at: nowIso() }));
    res.json({ success: true, space: saved });
  } catch (error) {
    res.status(500).json({ error: `공간 수정 실패: ${error.message}` });
  }
});

app.delete('/api/spaces/:spaceId', requireRemoteStorage, async (req, res) => {
  try {
    if (storageService.cache.furniture.some((row) => row.space_id === req.params.spaceId)) return res.status(400).json({ error: '공간 안에 가구가 있습니다. 먼저 가구를 삭제해주세요.' });
    if (!storageService.cache.spaces.some((row) => row.space_id === req.params.spaceId)) return res.status(404).json({ error: '공간을 찾을 수 없습니다.' });
    await storageService.delete('spaces', req.params.spaceId);
    res.json({ success: true, deleted: storageService.removeCache('spaces', req.params.spaceId) });
  } catch (error) {
    res.status(500).json({ error: `공간 삭제 실패: ${error.message}` });
  }
});

app.get('*', (_req, res) => res.sendFile(path.join(__dirname, 'public', 'index.html')));

if (require.main === module) {
  initializationPromise.catch((error) => console.error(`❌ 초기 데이터 로드 실패: ${error.message}`)).finally(() => {
    const server = app.listen(PORT, () => {
      console.log(`StorageMap 서버가 http://localhost:${PORT} 에서 실행 중입니다.`);
    });
    server.on('error', (error) => {
      if (error.code === 'EADDRINUSE') {
        console.error(`[StorageMap] Port ${PORT} is already in use. If StorageMap is already open, use http://localhost:${PORT} in your browser.`);
        return;
      }
      console.error(`[StorageMap] Server failed to start: ${error.message}`);
    });
  });
}

module.exports = app;
