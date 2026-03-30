require('dotenv').config();
const express = require('express');
const cors = require('cors');
const bodyParser = require('body-parser');
const { google } = require('googleapis');
const { v4: uuidv4 } = require('uuid');

const app = express();
const PORT = process.env.PORT || 3000;

// 미들웨어 설정
app.use(cors());
app.use(bodyParser.json());
app.use(express.static('public'));

// Google Sheets API 초기화 (OAuth 2.0)
const oauth2Client = new google.auth.OAuth2(
  process.env.GOOGLE_CLIENT_ID,
  process.env.GOOGLE_CLIENT_SECRET,
  process.env.REDIRECT_URI || 'http://localhost:3000/auth/callback'
);

const sheets = google.sheets({ version: 'v4', auth: oauth2Client });

const spreadsheetId = process.env.GOOGLE_SHEETS_SPREADSHEET_ID;

// 세션 미들웨어
const session = require('express-session');
app.use(session({
  secret: process.env.SESSION_SECRET || 'storagemap-secret-key',
  resave: false,
  saveUninitialized: false,
  cookie: { secure: false } // 개발 환경에서는 false
}));

// 서버 자동 인증 상태
let serverAutoAuth = null;

// 인증 미들웨어 - 서버 자동 인증 또는 세션 인증 지원
function checkAuth(req, res, next) {
  // 1. 세션 인증 확인 (브라우저 OAuth 로그인)
  if (req.session && req.session.tokens) {
    oauth2Client.setCredentials(req.session.tokens);
    return next();
  }
  
  // 2. 서버 자동 인증 확인 (.env의 GOOGLE_REFRESH_TOKEN)
  if (serverAutoAuth && serverAutoAuth.credentials) {
    oauth2Client.setCredentials(serverAutoAuth.credentials);
    return next();
  }
  
  // 인증 실패
  return res.status(401).json({ error: '인증이 필요합니다. /auth/google로 이동하세요' });
}

// Google OAuth 라우트
app.get('/auth/google', (req, res) => {
  const scopes = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/userinfo.profile'
  ];
  
  const url = oauth2Client.generateAuthUrl({
    access_type: 'offline',
    scope: scopes,
    prompt: 'consent'
  });
  
  res.redirect(url);
});

// OAuth 콜백
app.get('/auth/callback', async (req, res) => {
  const { code } = req.query;
  
  try {
    const { tokens } = await oauth2Client.getToken(code);
    req.session.tokens = tokens;
    
    console.log('✅ Google OAuth 인증 성공');
    res.redirect('/');
  } catch (error) {
    console.error('❌ OAuth 인증 실패:', error.message);
    res.status(500).send('인증 실패: ' + error.message);
  }
});

// 인증 상태 확인 (서버 자동 인증 포함)
app.get('/api/auth/status', (req, res) => {
  const isAuthenticated = !!(req.session.tokens || (serverAutoAuth && serverAutoAuth.credentials));
  res.json({
    authenticated: isAuthenticated,
    serverAutoAuth: !!(serverAutoAuth && serverAutoAuth.credentials),
    timestamp: new Date().toISOString()
  });
});

// 데이터 모델 (스펙 문서 3장 참조)
class StorageMapService {
  constructor() {
    this.cache = {
      spaces: [],
      furniture: [],
      zones: [],
      items: [],
      history: []
    };
  }

  // Google Sheets에서 데이터 로드
  async loadFromSheets() {
    try {
      const requests = [
        { range: process.env.SHEET_SPACES || 'Spaces' },
        { range: process.env.SHEET_FURNITURE || 'Furniture' },
        { range: process.env.SHEET_ZONES || 'Zones' },
        { range: process.env.SHEET_ITEMS || 'Items' },
        { range: process.env.SHEET_HISTORY || 'History' }
      ];

      const results = await Promise.all(
        requests.map(req => 
          sheets.spreadsheets.values.get({
            spreadsheetId,
            range: req.range
          })
        )
      );

      // 데이터 파싱 (첫 행은 헤더로 가정)
      this.cache.spaces = this.parseSheetData(results[0].data.values);
      this.cache.furniture = this.parseSheetData(results[1].data.values);
      this.cache.zones = this.parseSheetData(results[2].data.values);
      this.cache.items = this.parseSheetData(results[3].data.values);
      this.cache.history = this.parseSheetData(results[4].data.values);

      console.log('Google Sheets 데이터 로드 완료');
    } catch (error) {
      console.error('Google Sheets 로드 실패:', error.message);
      // 개발용 샘플 데이터
      this.loadSampleData();
    }
  }

  // Google Sheets에서 데이터 로드 (인증 필요) - 상세 디버깅 버전
  async loadFromSheetsWithAuth(auth) {
    try {
      const sheetsClient = google.sheets({ version: 'v4', auth });
      
      console.log('🔍 [DEBUG] Google Sheets 로드 시작');
      console.log('  Spreadsheet ID:', spreadsheetId);

      // Spaces 데이터 가져오기
      console.log('\n📊 [DEBUG] Spaces 시트 요청 중...');
      let spacesResult;
      try {
        spacesResult = await sheetsClient.spreadsheets.values.get({
          spreadsheetId,
          range: process.env.SHEET_SPACES || 'Spaces'
        });
        console.log('  ✅ Spaces 응답 받음');
        console.log('  Raw values:', JSON.stringify(spacesResult.data.values, null, 2));
      } catch (e) {
        console.error('  ❌ Spaces 오류:', e.message);
        spacesResult = { data: { values: [] } };
      }

      // Furniture 데이터 가져오기
      console.log('\n📊 [DEBUG] Furniture 시트 요청 중...');
      let furnitureResult;
      try {
        furnitureResult = await sheetsClient.spreadsheets.values.get({
          spreadsheetId,
          range: process.env.SHEET_FURNITURE || 'Furniture'
        });
        console.log('  ✅ Furniture 응답 받음');
        console.log('  Raw values:', JSON.stringify(furnitureResult.data.values, null, 2));
      } catch (e) {
        console.error('  ❌ Furniture 오류:', e.message);
        furnitureResult = { data: { values: [] } };
      }

      // Items 데이터 가져오기
      console.log('\n� [DEBUG] Items 시트 요청 중...');
      let itemsResult;
      try {
        itemsResult = await sheetsClient.spreadsheets.values.get({
          spreadsheetId,
          range: process.env.SHEET_ITEMS || 'Items'
        });
        console.log('  ✅ Items 응답 받음');
        console.log('  Raw values:', JSON.stringify(itemsResult.data.values, null, 2));
      } catch (e) {
        console.error('  ❌ Items 오류:', e.message);
        itemsResult = { data: { values: [] } };
      }

      // 데이터 파싱
      console.log('\n🔄 [DEBUG] 데이터 파싱 중...');
      const newSpaces = this.parseSheetData(spacesResult.data.values);
      const newFurniture = this.parseSheetData(furnitureResult.data.values);
      const newItems = this.parseSheetData(itemsResult.data.values);
      
      console.log('  파싱된 공간:', newSpaces.length, '개');
      console.log('  파싱된 가구:', newFurniture.length, '개');
      console.log('  파싱된 물건:', newItems.length, '개');
      
      if (newSpaces.length > 0) {
        console.log('  공간 샘플:', JSON.stringify(newSpaces[0], null, 2));
      }

      // 캐시 업데이트
      this.cache.spaces = newSpaces;
      this.cache.furniture = newFurniture;
      this.cache.items = newItems;
      
      console.log('\n✅ [DEBUG] Google Sheets 로드 완료');
      console.log('  최종 캐시 상태:');
      console.log('    spaces:', this.cache.spaces.length);
      console.log('    furniture:', this.cache.furniture.length);
      console.log('    items:', this.cache.items.length);
      
      return true;
    } catch (error) {
      console.error('❌ [DEBUG] Google Sheets 로드 실패:', error.message);
      console.error('  스택:', error.stack);
      throw error;
    }
  }

  parseSheetData(values, defaultHeaders = null) {
    if (!values || values.length === 0) return [];
    
    // 헤더 감지: 첫 행이 데이터인지 헤더인지 확인
    // 데이터 패턴: ID 형식 (s..., f..., i...) 또는 숫자
    // 헤더 패턴: 'name', 'space_id', 'description' 등의 문자열
    const firstRow = values[0];
    const looksLikeData = firstRow.some(cell => 
      typeof cell === 'string' && 
      (cell.match(/^[sfi]\d+$/) || // s123, f123, i123 패턴
       cell.match(/^\d+$/) ||     // 숫자만
       cell.match(/^default$/))    // 특별한 값
    );
    
    let headers, rows;
    
    if (looksLikeData || values.length < 2) {
      // 헤더가 없는 경우: 기본 헤더 사용 또는 값 개수로 추정
      console.log('  ⚠️ 헤더 없음 감지, 기본 헤더 사용');
      if (defaultHeaders) {
        headers = defaultHeaders;
      } else {
        // 값 개수만큼 기본 헤더 생성
        headers = firstRow.map((_, i) => `col_${i}`);
      }
      rows = values; // 모든 행이 데이터
    } else {
      // 정상: 첫 행이 헤더
      headers = values[0];
      rows = values.slice(1);
    }
    
    console.log('  헤더:', headers.join(', '));
    console.log('  데이터 행 수:', rows.length);
    
    return rows.map((row, rowIndex) => {
      const obj = {};
      headers.forEach((header, index) => {
        const key = header.toLowerCase().replace(/\s+/g, '_');
        let value = row[index] || '';
        
        // 숫자 필드 자동 변환
        const numericFields = ['pos_x', 'pos_y', 'width', 'height', 'quantity'];
        if (numericFields.includes(key)) {
          value = parseInt(value) || 0;
        }
        
        obj[key] = value;
      });
      
      if (rowIndex === 0) {
        console.log('  첫 데이터行:', JSON.stringify(obj));
      }
      
      return obj;
    });
  }

  // 개발용 샘플 데이터
  loadSampleData() {
    this.cache.spaces = [
      { space_id: 's1', name: '3학년 2반', description: '교실 공간' },
      { space_id: 's2', name: '우리 집', description: '거실/서재 공간' }
    ];

    this.cache.furniture = [
      { furniture_id: 'f1', space_id: 's1', name: '앞 교구장', type: '교구장', pos_x: 20, pos_y: 40, width: 100, height: 60 },
      { furniture_id: 'f2', space_id: 's1', name: '교탁', type: '교탁', pos_x: 260, pos_y: 20, width: 140, height: 50 },
      { furniture_id: 'f3', space_id: 's2', name: 'TV 장식장', type: '서랍장', pos_x: 20, pos_y: 30, width: 180, height: 60 }
    ];

    this.cache.items = [
      { item_id: 'i1', name: '리코더 (학생용)', furniture_id: 'f1', category: '교구', quantity: 25, memo: '' },
      { item_id: 'i2', name: '수학 교구 세트', furniture_id: 'f1', category: '교구', quantity: 5, memo: '' },
      { item_id: 'i3', name: '리모컨', furniture_id: 'f3', category: '전자기기', quantity: 2, memo: '' }
    ];

    console.log('샘플 데이터 로드 완료');
  }

  // 검색 기능 (스펙 문서 5장 참조)
  searchItems(query) {
    const lowerQuery = query.toLowerCase();
    const results = [];

    this.cache.items.forEach(item => {
      let matchScore = 0;
      
      // 이름 완전 일치 (우선순위 1)
      if (item.name.toLowerCase() === lowerQuery) {
        matchScore = 100;
      }
      // 이름 부분 일치 (우선순위 2)
      else if (item.name.toLowerCase().includes(lowerQuery)) {
        matchScore = 80;
      }
      // 메모 포함 (우선순위 4)
      else if (item.memo && item.memo.toLowerCase().includes(lowerQuery)) {
        matchScore = 40;
      }

      if (matchScore > 0) {
        const furniture = this.cache.furniture.find(f => f.furniture_id === item.furniture_id);
        const space = this.cache.spaces.find(s => s.space_id === furniture?.space_id);
        
        results.push({
          ...item,
          matchScore,
          furniture: furniture?.name || '위치 미정',
          space: space?.name || '공간 미정',
          path: `${space?.name || '?'} > ${furniture?.name || '?'}`
        });
      }
    });

    return results.sort((a, b) => b.matchScore - a.matchScore);
  }

  // 공간별 데이터 조회
  getSpaceData(spaceId) {
    const space = this.cache.spaces.find(s => s.space_id === spaceId);
    if (!space) return null;

    const furniture = this.cache.furniture.filter(f => f.space_id === spaceId);
    const furnitureIds = furniture.map(f => f.furniture_id);
    const items = this.cache.items.filter(i => furnitureIds.includes(i.furniture_id));

    return {
      space,
      furniture: furniture.map(f => ({
        ...f,
        items: this.cache.items.filter(i => i.furniture_id === f.furniture_id),
        itemCount: this.cache.items.filter(i => i.furniture_id === f.furniture_id).length
      })),
      items
    };
  }

  // 모든 데이터 조회
  getAllData() {
    return this.cache;
  }
}

const storageService = new StorageMapService();

// API 라우트
app.get('/api/health', (req, res) => {
  res.json({ status: 'ok', timestamp: new Date().toISOString() });
});

app.get('/api/data/load', async (req, res) => {
  try {
    await storageService.loadFromSheets();
    res.json({ success: true, message: '데이터 로드 완료' });
  } catch (error) {
    res.status(500).json({ success: false, error: error.message });
  }
});

app.get('/api/data', (req, res) => {
  res.json(storageService.getAllData());
});

// 모든 공간 목록 조회 API
app.get('/api/spaces', (req, res) => {
  try {
    const spaces = storageService.cache.spaces.map(space => {
      const furnitureCount = storageService.cache.furniture.filter(
        f => f.space_id === space.space_id
      ).length;
      return { ...space, furnitureCount };
    });
    res.json(spaces);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// 공간별 가구 조회 API (벤치마크 참고)
app.get('/api/spaces/:spaceId/furniture', (req, res) => {
  const { spaceId } = req.params;
  try {
    const furniture = storageService.cache.furniture
      .filter(f => f.space_id === spaceId)
      .map(f => {
        const items = storageService.cache.items.filter(
          i => i.furniture_id === f.furniture_id
        );
        return { ...f, itemCount: items.length, items };
      });
    res.json(furniture);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

app.get('/api/spaces/:spaceId', (req, res) => {
  const data = storageService.getSpaceData(req.params.spaceId);
  if (!data) {
    return res.status(404).json({ error: '공간을 찾을 수 없습니다' });
  }
  res.json(data);
});

app.get('/api/search', (req, res) => {
  const { q } = req.query;
  if (!q) {
    return res.status(400).json({ error: '검색어가 필요합니다' });
  }
  
  const results = storageService.searchItems(q);
  res.json({ query: q, results });
});

// 2D 평면도 데이터 API
app.get('/api/floorplan/:spaceId', (req, res) => {
  const data = storageService.getSpaceData(req.params.spaceId);
  if (!data) {
    return res.status(404).json({ error: '공간을 찾을 수 없습니다' });
  }

  // 2D 평면도용 데이터 포맷
  const floorplanData = {
    space: data.space,
    furniture: data.furniture.map(f => ({
      id: f.furniture_id,
      name: f.name,
      type: f.type,
      x: f.pos_x || 0,
      y: f.pos_y || 0,
      width: f.width || 100,
      height: f.height || 60,
      itemCount: f.itemCount,
      items: f.items
    }))
  };

  res.json(floorplanData);
});

// 가구 위치 업데이트 API
app.put('/api/furniture/:furnitureId/position', checkAuth, async (req, res) => {
  const { furnitureId } = req.params;
  const { x, y, width, height } = req.body;
  
  console.log(`📝 가구 위치 업데이트 요청: ${furnitureId}`, { x, y, width, height });
  
  try {
    // 캐시 업데이트
    const furniture = storageService.cache.furniture.find(f => f.furniture_id === furnitureId);
    if (!furniture) {
      console.error(`❌ 가구를 찾을 수 없음: ${furnitureId}`);
      return res.status(404).json({ error: '가구를 찾을 수 없습니다' });
    }
    
    console.log(`✅ 가구 찾음: ${furniture.name}, 현재 위치: (${furniture.pos_x}, ${furniture.pos_y})`);
    
    if (x !== undefined) furniture.pos_x = parseInt(x) || 0;
    if (y !== undefined) furniture.pos_y = parseInt(y) || 0;
    if (width !== undefined) furniture.width = parseInt(width) || 100;
    if (height !== undefined) furniture.height = parseInt(height) || 60;
    
    console.log(`🔄 업데이트된 위치: (${furniture.pos_x}, ${furniture.pos_y})`);
    
    // 항상 Google Sheets에 저장
    try {
      await updateFurnitureInSheets(furnitureId, { pos_x: furniture.pos_x, pos_y: furniture.pos_y, width: furniture.width, height: furniture.height });
      console.log('✅ Google Sheets 저장 완료');
    } catch (sheetsError) {
      console.error('⚠️ Google Sheets 저장 실패:', sheetsError.message);
      // Sheets 저장 실패해도 API는 성공 응답 (캐시는 이미 업데이트됨)
    }
    
    res.json({ 
      success: true, 
      message: '위치 업데이트됨',
      furniture: {
        id: furnitureId,
        x: furniture.pos_x,
        y: furniture.pos_y,
        width: furniture.width,
        height: furniture.height
      }
    });
  } catch (error) {
    console.error('❌ 위치 업데이트 실패:', error);
    res.status(500).json({ error: '위치 업데이트 실패: ' + error.message });
  }
});

// Google Sheets에 가구 위치 업데이트
async function updateFurnitureInSheets(furnitureId, updates) {
  console.log(`🔄 Google Sheets 업데이트 시작: ${furnitureId}`, updates);
  
  try {
    // Furniture 시트에서 해당 가구 찾기
    const response = await sheets.spreadsheets.values.get({
      spreadsheetId,
      range: process.env.SHEET_FURNITURE || 'Furniture'
    });
    
    const rows = response.data.values;
    if (!rows || rows.length === 0) {
      throw new Error('Furniture 시트가 비어있습니다');
    }
    
    const headers = rows[0];
    const furnitureIdIndex = headers.indexOf('furniture_id');
    
    if (furnitureIdIndex === -1) {
      throw new Error('furniture_id 컬럼을 찾을 수 없습니다');
    }
    
    const rowIndex = rows.findIndex(row => row[furnitureIdIndex] === furnitureId);
    
    if (rowIndex === -1) {
      throw new Error(`가구 ${furnitureId}를 찾을 수 없습니다`);
    }
    
    console.log(`✅ 가구 찾음: ${furnitureId}, 행: ${rowIndex + 1}`);
    
    // 업데이트할 값들
    const posXIndex = headers.indexOf('pos_x');
    const posYIndex = headers.indexOf('pos_y');
    const widthIndex = headers.indexOf('width');
    const heightIndex = headers.indexOf('height');
    
    // 업데이트 요청 생성
    const updates2 = [];
    
    if (updates.pos_x !== undefined && posXIndex !== -1) {
      const colLetter = String.fromCharCode(65 + posXIndex);
      updates2.push({
        range: `${process.env.SHEET_FURNITURE || 'Furniture'}!${colLetter}${rowIndex + 1}`,
        values: [[updates.pos_x]]
      });
    }
    
    if (updates.pos_y !== undefined && posYIndex !== -1) {
      const colLetter = String.fromCharCode(65 + posYIndex);
      updates2.push({
        range: `${process.env.SHEET_FURNITURE || 'Furniture'}!${colLetter}${rowIndex + 1}`,
        values: [[updates.pos_y]]
      });
    }
    
    if (updates.width !== undefined && widthIndex !== -1) {
      const colLetter = String.fromCharCode(65 + widthIndex);
      updates2.push({
        range: `${process.env.SHEET_FURNITURE || 'Furniture'}!${colLetter}${rowIndex + 1}`,
        values: [[updates.width]]
      });
    }
    
    if (updates.height !== undefined && heightIndex !== -1) {
      const colLetter = String.fromCharCode(65 + heightIndex);
      updates2.push({
        range: `${process.env.SHEET_FURNITURE || 'Furniture'}!${colLetter}${rowIndex + 1}`,
        values: [[updates.height]]
      });
    }
    
    if (updates2.length > 0) {
      console.log(`📝 ${updates2.length}개 셀 업데이트:`, updates2.map(u => u.range).join(', '));
      
      await sheets.spreadsheets.values.batchUpdate({
        spreadsheetId,
        resource: {
          valueInputOption: 'USER_ENTERED',
          data: updates2
        }
      });
      
      console.log(`✅ Google Sheets 업데이트 완료: ${furnitureId}`);
    } else {
      console.log('⚠️ 업데이트할 내용이 없습니다');
    }
  } catch (error) {
    console.error('❌ Google Sheets 업데이트 실패:', error.message);
    throw error;
  }
}

// 테스트: Google Sheets 진단 API
app.get('/api/debug/sheets', checkAuth, async (req, res) => {
  try {
    oauth2Client.setCredentials(req.session.tokens);
    const sheetsClient = google.sheets({ version: 'v4', auth: oauth2Client });
    
    const results = {
      spreadsheetId,
      timestamp: new Date().toISOString(),
      tests: {}
    };
    
    // Test 1: Spaces 시트
    try {
      const spacesData = await sheetsClient.spreadsheets.values.get({
        spreadsheetId,
        range: process.env.SHEET_SPACES || 'Spaces'
      });
      results.tests.spaces = {
        success: true,
        rowCount: spacesData.data.values?.length || 0,
        headers: spacesData.data.values?.[0] || [],
        sampleRow: spacesData.data.values?.[1] || null,
        allRows: spacesData.data.values || []
      };
    } catch (e) {
      results.tests.spaces = { success: false, error: e.message };
    }
    
    // Test 2: Furniture 시트
    try {
      const furnitureData = await sheetsClient.spreadsheets.values.get({
        spreadsheetId,
        range: process.env.SHEET_FURNITURE || 'Furniture'
      });
      results.tests.furniture = {
        success: true,
        rowCount: furnitureData.data.values?.length || 0,
        headers: furnitureData.data.values?.[0] || [],
        sampleRow: furnitureData.data.values?.[1] || null
      };
    } catch (e) {
      results.tests.furniture = { success: false, error: e.message };
    }
    
    // Test 3: Items 시트
    try {
      const itemsData = await sheetsClient.spreadsheets.values.get({
        spreadsheetId,
        range: process.env.SHEET_ITEMS || 'Items'
      });
      results.tests.items = {
        success: true,
        rowCount: itemsData.data.values?.length || 0,
        headers: itemsData.data.values?.[0] || [],
        sampleRow: itemsData.data.values?.[1] || null
      };
    } catch (e) {
      results.tests.items = { success: false, error: e.message };
    }
    
    res.json(results);
  } catch (error) {
    res.status(500).json({
      error: error.message,
      stack: error.stack
    });
  }
});

// 인증된 사용자용 데이터 로드 API
app.get('/api/data/reload', checkAuth, async (req, res) => {
  try {
    console.log('🔄 /api/data/reload 요청 받음');
    console.log('  세션 토큰:', req.session.tokens ? '있음' : '없음');
    console.log('  서버 자동 인증:', serverAutoAuth ? '사용 중' : '미사용');
    
    // 이미 checkAuth 미들웨어에서 oauth2Client에 credentials 설정됨
    // 추가 설정 필요 없음
    
    // Google Sheets에서 데이터 로드
    await storageService.loadFromSheetsWithAuth(oauth2Client);
    
    const data = storageService.getAllData();
    
    console.log('✅ /api/data/reload 응답:');
    console.log('  공간:', data.spaces.length, '개');
    console.log('  가구:', data.furniture.length, '개');
    console.log('  물건:', data.items.length, '개');
    
    res.json({ 
      success: true, 
      message: 'Google Sheets 데이터 로드 완료',
      stats: {
        spaces: data.spaces.length,
        furniture: data.furniture.length,
        items: data.items.length
      },
      data: data
    });
  } catch (error) {
    console.error('❌ 데이터 로드 실패:', error);
    res.status(500).json({ 
      success: false, 
      error: error.message,
      stack: error.stack 
    });
  }
});

// Google Sheets 연결 테스트 API
app.get('/api/test/sheets', checkAuth, async (req, res) => {
  try {
    oauth2Client.setCredentials(req.session.tokens);
    const sheetsClient = google.sheets({ version: 'v4', auth: oauth2Client });
    
    // 스프레드시트 메타데이터 가져오기
    const spreadsheet = await sheetsClient.spreadsheets.get({
      spreadsheetId
    });
    
    const sheetNames = spreadsheet.data.sheets?.map(s => s.properties?.title) || [];
    
    // Spaces 시트 데이터 샘플 가져오기
    let sampleData = null;
    try {
      const spacesData = await sheetsClient.spreadsheets.values.get({
        spreadsheetId,
        range: process.env.SHEET_SPACES || 'Spaces'
      });
      sampleData = {
        rowCount: spacesData.data.values?.length || 0,
        headers: spacesData.data.values?.[0] || [],
        firstRow: spacesData.data.values?.[1] || null
      };
    } catch (e) {
      sampleData = { error: e.message };
    }
    
    res.json({
      success: true,
      spreadsheetId,
      spreadsheetTitle: spreadsheet.data.properties?.title,
      availableSheets: sheetNames,
      expectedSheets: [
        process.env.SHEET_SPACES || 'Spaces',
        process.env.SHEET_FURNITURE || 'Furniture',
        process.env.SHEET_ITEMS || 'Items'
      ],
      spacesSample: sampleData
    });
  } catch (error) {
    console.error('Sheets test failed:', error);
    res.status(500).json({
      success: false,
      error: error.message,
      spreadsheetId
    });
  }
});
app.post('/api/items', checkAuth, async (req, res) => {
  const { name, furniture_id, category, quantity, memo } = req.body;
  
  if (!name || !furniture_id) {
    return res.status(400).json({ error: '물건 이름과 가구 ID가 필요합니다' });
  }
  
  try {
    const newItem = {
      item_id: 'i' + Date.now(),
      name,
      furniture_id,
      category: category || '기타',
      quantity: quantity || 1,
      memo: memo || ''
    };
    
    // 캐시에 추가 (항상 성공)
    storageService.cache.items.push(newItem);
    
    // Google Sheets에 추가 시도 (실패해도 캐시에는 있음)
    // checkAuth 미들웨어에서 이미 oauth2Client.setCredentials() 호출됨
    try {
      // 토큰 유효성 확인 및 필요시 refresh
      if (!oauth2Client.credentials.access_token) {
        console.log('🔄 Items: Access token 없음, refresh 시도...');
        const { credentials } = await oauth2Client.refreshAccessToken();
        oauth2Client.setCredentials(credentials);
        // serverAutoAuth 업데이트 (refresh_token 유지)
        if (serverAutoAuth) {
          serverAutoAuth.credentials = {
            ...serverAutoAuth.credentials,
            ...credentials
          };
        }
      }
      await addItemToSheets(oauth2Client, newItem);
      console.log('✅ Google Sheets에 물건 추가 완료:', newItem.name);
    } catch (sheetsError) {
      console.error('⚠️ Google Sheets 물건 추가 실패 (캐시에는 저장됨):', sheetsError.message);
      // Sheets 실패해도 API는 성공 응답 - 클라이언트에서 나중에 동기화
    }
    
    res.json({ success: true, item: newItem });
  } catch (error) {
    console.error('물건 추가 실패:', error);
    res.status(500).json({ error: '물건 추가 실패: ' + error.message });
  }
});

// 가구 추가 API
app.post('/api/furniture', checkAuth, async (req, res) => {
  const { name, space_id, type, pos_x, pos_y, width, height, notes } = req.body;
  
  if (!name || !space_id) {
    return res.status(400).json({ error: '가구 이름과 공간 ID가 필요합니다' });
  }
  
  try {
    const newFurniture = {
      furniture_id: 'f' + Date.now(),
      name,
      space_id,
      type: type || '',
      pos_x: pos_x || 50,
      pos_y: pos_y || 50,
      width: width || 120,
      height: height || 80,
      notes: notes || ''
    };
    
    // 캐시에 먼저 추가 (항상 성공)
    storageService.cache.furniture.push(newFurniture);
    
    // Google Sheets에 추가 시도 (실패해도 캐시에는 있음)
    // checkAuth 미들웨어에서 이미 oauth2Client.setCredentials() 호출됨
    try {
      // 토큰 유효성 확인 및 필요시 refresh
      console.log('🔑 토큰 확인:', oauth2Client.credentials.access_token ? '있음' : '없음');
      if (!oauth2Client.credentials.access_token) {
        console.log('🔄 Access token 없음, refresh 시도...');
        const { credentials } = await oauth2Client.refreshAccessToken();
        console.log('✅ 토큰 refresh 성공, 새 access_token:', credentials.access_token ? '발급됨' : '실패');
        oauth2Client.setCredentials(credentials);
        // serverAutoAuth 업데이트 (refresh_token 유지)
        if (serverAutoAuth) {
          serverAutoAuth.credentials = {
            ...serverAutoAuth.credentials,
            ...credentials
          };
        }
      }
      await addFurnitureToSheets(oauth2Client, newFurniture);
      console.log('✅ Google Sheets에 가구 추가 완료:', newFurniture.name);
    } catch (sheetsError) {
      console.error('⚠️ Google Sheets 가구 추가 실패 (캐시에는 저장됨):', sheetsError.message);
      // Sheets 실패해도 API는 성공 응답 - 클라이언트에서 나중에 동기화
    }
    
    res.json({ success: true, furniture: newFurniture });
  } catch (error) {
    console.error('가구 추가 실패:', error);
    res.status(500).json({ error: '가구 추가 실패: ' + error.message });
  }
});

// 공간 추가 API
app.post('/api/spaces', checkAuth, async (req, res) => {
  const { name, description } = req.body;
  
  if (!name) {
    return res.status(400).json({ error: '공간 이름이 필요합니다' });
  }
  
  try {
    const newSpace = {
      space_id: 's' + Date.now(),
      name,
      description: description || ''
    };
    
    // 캐시에 추가 (항상 성공)
    storageService.cache.spaces.push(newSpace);
    
    // Google Sheets에 추가 시도 (실패해도 캐시에는 있음)
    // checkAuth 미들웨어에서 이미 oauth2Client.setCredentials() 호출됨
    try {
      // 토큰 유효성 확인 및 필요시 refresh
      if (!oauth2Client.credentials.access_token) {
        console.log('🔄 Spaces: Access token 없음, refresh 시도...');
        const { credentials } = await oauth2Client.refreshAccessToken();
        oauth2Client.setCredentials(credentials);
        // serverAutoAuth 업데이트 (refresh_token 유지)
        if (serverAutoAuth) {
          serverAutoAuth.credentials = {
            ...serverAutoAuth.credentials,
            ...credentials
          };
        }
      }
      await addSpaceToSheets(oauth2Client, newSpace);
      console.log('✅ Google Sheets에 공간 추가 완료:', newSpace.name);
    } catch (sheetsError) {
      console.error('⚠️ Google Sheets 공간 추가 실패 (캐시에는 저장됨):', sheetsError.message);
      // Sheets 실패해도 API는 성공 응답 - 클라이언트에서 나중에 동기화
    }
    
    res.json({ success: true, space: newSpace });
  } catch (error) {
    console.error('공간 추가 실패:', error);
    res.status(500).json({ error: '공간 추가 실패: ' + error.message });
  }
});

// 시트에 헤더가 있는지 확인하고 없으면 추가하는 헬퍼 함수
async function ensureSheetHeaders(auth, sheetName, headers) {
  try {
    const sheetsClient = google.sheets({ version: 'v4', auth });
    
    // 현재 시트 데이터 확인
    const response = await sheetsClient.spreadsheets.values.get({
      spreadsheetId,
      range: sheetName
    });
    
    const values = response.data.values;
    
    // 시트가 비어있거나 헤더가 없으면 헤더 추가
    if (!values || values.length === 0) {
      console.log(`📋 ${sheetName} 시트가 비어있음 - 헤더 추가 중...`);
      await sheetsClient.spreadsheets.values.update({
        spreadsheetId,
        range: `${sheetName}!A1`,
        valueInputOption: 'USER_ENTERED',
        resource: {
          values: [headers]
        }
      });
      console.log(`✅ ${sheetName} 헤더 추가 완료`);
      return true;
    }
    
    // 첫 행이 헤더인지 확인 (첫 셀이 ID 패턴이면 데이터)
    const firstRow = values[0];
    const firstCell = firstRow[0] || '';
    const looksLikeData = firstCell.match(/^[sfi]\d+$/) || firstCell.match(/^\d+$/);
    
    if (looksLikeData) {
      console.log(`⚠️ ${sheetName}에 헤더 없음 - 헤더 삽입 중...`);
      // 헤더 삽입: 기존 데이터를 아래로 밀고 헤더를 첫 행에 추가
      await sheetsClient.spreadsheets.values.batchUpdate({
        spreadsheetId,
        resource: {
          valueInputOption: 'USER_ENTERED',
          data: [
            {
              range: `${sheetName}!A1`,
              values: [headers]
            },
            {
              range: `${sheetName}!A2`,
              values: values
            }
          ]
        }
      });
      console.log(`✅ ${sheetName} 헤더 삽입 완료`);
      return true;
    }
    
    console.log(`✅ ${sheetName}에 이미 헤더 있음`);
    return false;
  } catch (error) {
    console.error(`❌ ${sheetName} 헤더 확인 실패:`, error.message);
    throw error;
  }
}

// Google Sheets에 공간 추가
async function addSpaceToSheets(auth, space) {
  const sheetName = process.env.SHEET_SPACES || 'Spaces';
  const headers = ['space_id', 'name', 'description'];
  
  try {
    const sheetsClient = google.sheets({ version: 'v4', auth });
    
    // 먼저 헤더 확인 및 추가
    await ensureSheetHeaders(auth, sheetName, headers);
    
    // 데이터 추가
    await sheetsClient.spreadsheets.values.append({
      spreadsheetId,
      range: sheetName,
      valueInputOption: 'USER_ENTERED',
      resource: {
        values: [[
          space.space_id,
          space.name,
          space.description
        ]]
      }
    });
    
    console.log(`✅ Google Sheets에 공간 추가: ${space.name}`);
  } catch (error) {
    console.error('❌ Google Sheets 공간 추가 실패:', error.message);
    throw error;
  }
}

// Google Sheets에 물건 추가
async function addItemToSheets(auth, item) {
  const sheetName = process.env.SHEET_ITEMS || 'Items';
  const headers = ['item_id', 'name', 'furniture_id', 'category', 'quantity', 'memo'];
  
  try {
    const sheetsClient = google.sheets({ version: 'v4', auth });
    
    // 먼저 헤더 확인 및 추가
    await ensureSheetHeaders(auth, sheetName, headers);
    
    // 데이터 추가
    await sheetsClient.spreadsheets.values.append({
      spreadsheetId,
      range: sheetName,
      valueInputOption: 'USER_ENTERED',
      resource: {
        values: [[
          item.item_id,
          item.name,
          item.furniture_id,
          item.category,
          item.quantity,
          item.memo
        ]]
      }
    });
    
    console.log(`✅ Google Sheets에 물건 추가: ${item.name}`);
  } catch (error) {
    console.error('❌ Google Sheets 물건 추가 실패:', error.message);
    throw error;
  }
}

// Google Sheets에 가구 추가
async function addFurnitureToSheets(auth, furniture) {
  const sheetName = process.env.SHEET_FURNITURE || 'Furniture';
  const headers = ['furniture_id', 'space_id', 'name', 'type', 'pos_x', 'pos_y', 'width', 'height', 'notes'];
  
  try {
    const sheetsClient = google.sheets({ version: 'v4', auth });
    
    // 먼저 헤더 확인 및 추가
    await ensureSheetHeaders(auth, sheetName, headers);
    
    // 데이터 추가
    await sheetsClient.spreadsheets.values.append({
      spreadsheetId,
      range: sheetName,
      valueInputOption: 'USER_ENTERED',
      resource: {
        values: [[
          furniture.furniture_id,
          furniture.space_id,
          furniture.name,
          furniture.type,
          furniture.pos_x,
          furniture.pos_y,
          furniture.width,
          furniture.height,
          furniture.notes
        ]]
      }
    });
    
    console.log(`✅ Google Sheets에 가구 추가: ${furniture.name}`);
  } catch (error) {
    console.error('❌ Google Sheets 가구 추가 실패:', error.message);
    throw error;
  }
}
// ─── 물건 수정 API ───
app.put('/api/items/:itemId', checkAuth, async (req, res) => {
  const { itemId } = req.params;
  const updates = req.body;
  
  try {
    const item = storageService.cache.items.find(i => i.item_id === itemId);
    if (!item) {
      return res.status(404).json({ error: '물건을 찾을 수 없습니다' });
    }
    
    // History 기록 (가구 변경 시)
    if (updates.furniture_id && updates.furniture_id !== item.furniture_id) {
      const historyEntry = {
        history_id: 'h' + Date.now(),
        item_id: itemId,
        from_furniture: item.furniture_id,
        to_furniture: updates.furniture_id,
        moved_at: new Date().toISOString(),
        note: ''
      };
      storageService.cache.history.push(historyEntry);
    }
    
    // 캐시 업데이트
    Object.assign(item, updates);
    
    res.json({ success: true, item });
  } catch (error) {
    res.status(500).json({ error: '물건 수정 실패: ' + error.message });
  }
});

// ─── 물건 삭제 API ───
app.delete('/api/items/:itemId', checkAuth, async (req, res) => {
  const { itemId } = req.params;
  
  try {
    const index = storageService.cache.items.findIndex(i => i.item_id === itemId);
    if (index === -1) {
      return res.status(404).json({ error: '물건을 찾을 수 없습니다' });
    }
    
    const deleted = storageService.cache.items.splice(index, 1)[0];
    
    // Google Sheets에서도 삭제 시도
    try {
      await deleteRowFromSheet(process.env.SHEET_ITEMS || 'Items', 'item_id', itemId);
    } catch (e) {
      console.error('⚠️ Sheets 삭제 실패 (캐시에서는 삭제됨):', e.message);
    }
    
    res.json({ success: true, deleted });
  } catch (error) {
    res.status(500).json({ error: '물건 삭제 실패: ' + error.message });
  }
});

// ─── 가구 삭제 API ───
app.delete('/api/furniture/:furnitureId', checkAuth, async (req, res) => {
  const { furnitureId } = req.params;
  
  try {
    // 물건이 있는지 확인
    const hasItems = storageService.cache.items.some(i => i.furniture_id === furnitureId);
    if (hasItems) {
      return res.status(400).json({ error: '가구 안에 물건이 있습니다. 먼저 물건을 비워주세요.' });
    }
    
    const index = storageService.cache.furniture.findIndex(f => f.furniture_id === furnitureId);
    if (index === -1) {
      return res.status(404).json({ error: '가구를 찾을 수 없습니다' });
    }
    
    const deleted = storageService.cache.furniture.splice(index, 1)[0];
    
    try {
      await deleteRowFromSheet(process.env.SHEET_FURNITURE || 'Furniture', 'furniture_id', furnitureId);
    } catch (e) {
      console.error('⚠️ Sheets 삭제 실패:', e.message);
    }
    
    res.json({ success: true, deleted });
  } catch (error) {
    res.status(500).json({ error: '가구 삭제 실패: ' + error.message });
  }
});

// ─── 공간 수정 API ───
app.put('/api/spaces/:spaceId', checkAuth, async (req, res) => {
  const { spaceId } = req.params;
  const { name, description } = req.body;
  
  try {
    const space = storageService.cache.spaces.find(s => s.space_id === spaceId);
    if (!space) {
      return res.status(404).json({ error: '공간을 찾을 수 없습니다' });
    }
    
    if (name) space.name = name;
    if (description !== undefined) space.description = description;
    
    res.json({ success: true, space });
  } catch (error) {
    res.status(500).json({ error: '공간 수정 실패: ' + error.message });
  }
});

// ─── 공간 삭제 API ───
app.delete('/api/spaces/:spaceId', checkAuth, async (req, res) => {
  const { spaceId } = req.params;
  
  try {
    const hasFurniture = storageService.cache.furniture.some(f => f.space_id === spaceId);
    if (hasFurniture) {
      return res.status(400).json({ error: '공간에 가구가 있습니다. 먼저 가구를 삭제해주세요.' });
    }
    
    const index = storageService.cache.spaces.findIndex(s => s.space_id === spaceId);
    if (index === -1) {
      return res.status(404).json({ error: '공간을 찾을 수 없습니다' });
    }
    
    const deleted = storageService.cache.spaces.splice(index, 1)[0];
    
    try {
      await deleteRowFromSheet(process.env.SHEET_SPACES || 'Spaces', 'space_id', spaceId);
    } catch (e) {
      console.error('⚠️ Sheets 삭제 실패:', e.message);
    }
    
    res.json({ success: true, deleted });
  } catch (error) {
    res.status(500).json({ error: '공간 삭제 실패: ' + error.message });
  }
});

// ─── Google Sheets 행 삭제 헬퍼 ───
async function deleteRowFromSheet(sheetName, idColumn, idValue) {
  try {
    const response = await sheets.spreadsheets.values.get({
      spreadsheetId,
      range: sheetName
    });
    
    const rows = response.data.values;
    if (!rows || rows.length === 0) return;
    
    const headers = rows[0];
    const idIndex = headers.indexOf(idColumn);
    if (idIndex === -1) return;
    
    const rowIndex = rows.findIndex(row => row[idIndex] === idValue);
    if (rowIndex <= 0) return; // 0 is header
    
    // Get sheet ID for batchUpdate
    const spreadsheet = await sheets.spreadsheets.get({ spreadsheetId });
    const sheet = spreadsheet.data.sheets.find(s => s.properties.title === sheetName);
    if (!sheet) return;
    
    await sheets.spreadsheets.batchUpdate({
      spreadsheetId,
      resource: {
        requests: [{
          deleteDimension: {
            range: {
              sheetId: sheet.properties.sheetId,
              dimension: 'ROWS',
              startIndex: rowIndex,
              endIndex: rowIndex + 1
            }
          }
        }]
      }
    });
    
    console.log(`✅ ${sheetName}에서 행 삭제 완료: ${idValue}`);
  } catch (error) {
    console.error(`❌ ${sheetName} 행 삭제 실패:`, error.message);
    throw error;
  }
}

// refresh_token 가져오는 API (한 번 로그인 후 토큰 저장용)
app.get('/api/auth/token', checkAuth, (req, res) => {
  res.json({
    refresh_token: req.session.tokens?.refresh_token,
    message: '이 refresh_token을 .env 파일의 GOOGLE_REFRESH_TOKEN에 저장하세요'
  });
});

// React Router SPA fallback
const path = require('path');
app.get('*', (req, res) => {
  res.sendFile(path.join(__dirname, 'public', 'index.html'));
});

app.listen(PORT, async () => {
  console.log(`StorageMap 서버가 http://localhost:${PORT} 에서 시작되었습니다`);
  
  // 샘플 데이터로 초기화 (기본값)
  storageService.loadSampleData();
  
  // 자동 인증 시도 (GOOGLE_REFRESH_TOKEN이 설정된 경우)
  if (process.env.GOOGLE_REFRESH_TOKEN) {
    console.log('🔑 GOOGLE_REFRESH_TOKEN 감지됨 - 자동 인증 시도 중...');
    try {
      // refresh token으로 인증
      oauth2Client.setCredentials({
        refresh_token: process.env.GOOGLE_REFRESH_TOKEN
      });
      
      // 새로운 access token 요청
      const { credentials } = await oauth2Client.refreshAccessToken();
      // refresh_token이 없으면 기존 것 유지
      const newCredentials = {
        refresh_token: process.env.GOOGLE_REFRESH_TOKEN,  // 원본 refresh token 유지
        ...credentials  // 새 access_token 등
      };
      oauth2Client.setCredentials(newCredentials);
      
      // 서버 자동 인증 상태 저장 (API에서 사용)
      serverAutoAuth = { credentials: newCredentials };
      
      console.log('✅ Google 자동 인증 성공 (서버 및 API 사용 가능)');
      
      // Google Sheets에서 데이터 로드
      await storageService.loadFromSheetsWithAuth(oauth2Client);
      console.log('✅ Google Sheets 데이터 자동 로드 완료');
      console.log(`   공간: ${storageService.cache.spaces.length}개`);
      console.log(`   가구: ${storageService.cache.furniture.length}개`);
      console.log(`   물건: ${storageService.cache.items.length}개`);
      
    } catch (error) {
      console.error('❌ 자동 인증 실패:', error.message);
      console.log('   수동 로그인이 필요합니다: /auth/google');
    }
  } else {
    console.log('ℹ️ GOOGLE_REFRESH_TOKEN이 설정되지 않음');
    console.log('   수동 로그인이 필요합니다: /auth/google');
    console.log('   (한 번 로그인 후 받은 refresh_token을 .env에 저장하면 자동 로그인됩니다)');
  }
});

module.exports = app;
