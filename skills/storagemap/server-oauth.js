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

// OAuth 2.0 설정
const oauth2Client = new google.auth.OAuth2(
  process.env.GOOGLE_CLIENT_ID,
  process.env.GOOGLE_CLIENT_SECRET,
  process.env.REDIRECT_URI || 'http://localhost:3000/auth/callback'
);

// Google Sheets API
const sheets = google.sheets({ version: 'v4', auth: oauth2Client });

// 스프레드시트 ID
const spreadsheetId = process.env.GOOGLE_SHEETS_SPREADSHEET_ID;

// 인증 URL 생성
app.get('/auth/google', (req, res) => {
  const scopes = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/userinfo.email'
  ];
  
  const url = oauth2Client.generateAuthUrl({
    access_type: 'offline',
    scope: scopes,
    prompt: 'consent'
  });
  
  res.redirect(url);
});

// OAuth 콜백 처리
app.get('/auth/callback', async (req, res) => {
  const { code } = req.query;
  
  try {
    const { tokens } = await oauth2Client.getToken(code);
    oauth2Client.setCredentials(tokens);
    
    // 토큰을 세션에 저장 (실제로는 DB나 세션 스토어 사용)
    req.session = req.session || {};
    req.session.tokens = tokens;
    
    res.redirect('/');
  } catch (error) {
    console.error('OAuth 콜백 오류:', error);
    res.status(500).send('인증 실패');
  }
});

// 인증 확인 미들웨어
function checkAuth(req, res, next) {
  if (!req.session || !req.session.tokens) {
    return res.status(401).json({ error: '인증이 필요합니다' });
  }
  oauth2Client.setCredentials(req.session.tokens);
  next();
}

// 데이터 모델 (OAuth 버전)
class StorageMapOAuthService {
  constructor() {
    this.cache = {
      spaces: [],
      furniture: [],
      zones: [],
      items: [],
      history: []
    };
  }

  // Google Sheets에서 데이터 로드 (읽기/쓰기)
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

      // 데이터 파싱
      this.cache.spaces = this.parseSheetData(results[0].data.values);
      this.cache.furniture = this.parseSheetData(results[1].data.values);
      this.cache.zones = this.parseSheetData(results[2].data.values);
      this.cache.items = this.parseSheetData(results[3].data.values);
      this.cache.history = this.parseSheetData(results[4].data.values);

      console.log('Google Sheets 데이터 로드 완료 (OAuth)');
    } catch (error) {
      console.error('Google Sheets 로드 실패:', error.message);
      this.loadSampleData();
    }
  }

  parseSheetData(values) {
    if (!values || values.length < 2) return [];
    
    const headers = values[0];
    const rows = values.slice(1);
    
    return rows.map(row => {
      const obj = {};
      headers.forEach((header, index) => {
        obj[header.toLowerCase().replace(/\s+/g, '_')] = row[index] || '';
      });
      return obj;
    });
  }

  // 아이템 추가 (쓰기)
  async addItem(itemData) {
    try {
      const newItem = {
        item_id: uuidv4(),
        ...itemData,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString()
      };

      const values = [
        Object.keys(newItem).map(key => newItem[key])
      ];

      await sheets.spreadsheets.values.append({
        spreadsheetId,
        range: process.env.SHEET_ITEMS || 'Items',
        valueInputOption: 'USER_ENTERED',
        resource: { values }
      });

      console.log('아이템 추가 성공:', newItem.name);
      return newItem;
    } catch (error) {
      console.error('아이템 추가 실패:', error);
      throw error;
    }
  }

  // 가구 위치 업데이트 (쓰기)
  async updateFurniturePosition(furnitureId, x, y) {
    try {
      // 먼저 데이터를 읽어서 행 번호 찾기
      const response = await sheets.spreadsheets.values.get({
        spreadsheetId,
        range: process.env.SHEET_FURNITURE || 'Furniture'
      });

      const rows = response.data.values;
      const headers = rows[0];
      const xIndex = headers.indexOf('pos_x');
      const yIndex = headers.indexOf('pos_y');
      
      const rowIndex = rows.findIndex(row => row[0] === furnitureId);
      
      if (rowIndex > 0) {
        await sheets.spreadsheets.values.update({
          spreadsheetId,
          range: `${process.env.SHEET_FURNITURE || 'Furniture'}!${xIndex + 1}${rowIndex + 1}:${yIndex + 1}${rowIndex + 1}`,
          valueInputOption: 'USER_ENTERED',
          resource: {
            values: [[x, y]]
          }
        });
        
        console.log(`가구 ${furnitureId} 위치 업데이트: (${x}, ${y})`);
      }
    } catch (error) {
      console.error('가구 위치 업데이트 실패:', error);
      throw error;
    }
  }

  // 개발용 샘플 데이터
  loadSampleData() {
    this.cache.spaces = [
      { space_id: 's1', name: '3학년 2반', description: '교실 공간' },
      { space_id: 's2', name: '우리 집', description: '거실/서재 공간' }
    ];

    this.cache.furniture = [
      { furniture_id: 'f1', space_id: 's1', name: '앞 교구장', type: '교구장', pos_x: 50, pos_y: 80, width: 120, height: 80 },
      { furniture_id: 'f2', space_id: 's1', name: '교탁', type: '교탁', pos_x: 300, pos_y: 40, width: 160, height: 60 },
      { furniture_id: 'f3', space_id: 's2', name: 'TV 장식장', type: '서랍장', pos_x: 80, pos_y: 120, width: 200, height: 70 }
    ];

    this.cache.items = [
      { item_id: 'i1', name: '리코더 (학생용)', furniture_id: 'f1', category: '교구', quantity: 25, memo: '' },
      { item_id: 'i2', name: '수학 교구 세트', furniture_id: 'f1', category: '교구', quantity: 5, memo: '' },
      { item_id: 'i3', name: '리모컨', furniture_id: 'f3', category: '전자기기', quantity: 2, memo: '' }
    ];

    console.log('샘플 데이터 로드 완료 (OAuth)');
  }

  // 검색 기능
  searchItems(query) {
    const lowerQuery = query.toLowerCase();
    const results = [];

    this.cache.items.forEach(item => {
      let matchScore = 0;
      
      if (item.name.toLowerCase() === lowerQuery) {
        matchScore = 100;
      } else if (item.name.toLowerCase().includes(lowerQuery)) {
        matchScore = 80;
      } else if (item.memo && item.memo.toLowerCase().includes(lowerQuery)) {
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

  getAllData() {
    return this.cache;
  }
}

const storageService = new StorageMapOAuthService();

// API 라우트 (OAuth 버전)
app.get('/api/health', (req, res) => {
  res.json({ status: 'ok', timestamp: new Date().toISOString() });
});

app.get('/api/data/load', checkAuth, async (req, res) => {
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

app.post('/api/items', checkAuth, async (req, res) => {
  try {
    const item = await storageService.addItem(req.body);
    res.json({ success: true, item });
  } catch (error) {
    res.status(500).json({ success: false, error: error.message });
  }
});

app.put('/api/furniture/:id/position', checkAuth, async (req, res) => {
  try {
    const { x, y } = req.body;
    await storageService.updateFurniturePosition(req.params.id, x, y);
    res.json({ success: true });
  } catch (error) {
    res.status(500).json({ success: false, error: error.message });
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

// 세션 미들웨어 추가
app.use(require('express-session')({
  secret: process.env.SESSION_SECRET || 'your-secret-key',
  resave: false,
  saveUninitialized: true
}));

// 서버 시작
app.listen(PORT, async () => {
  console.log(`StorageMap OAuth 서버가 http://localhost:${PORT} 에서 시작되었습니다`);
  console.log('Google 인증: http://localhost:3000/auth/google');
  
  // 시작 시 데이터 로드
  await storageService.loadFromSheets();
});

module.exports = app;
