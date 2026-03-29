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

// Google Sheets API 초기화
const sheets = google.sheets('v4');
const auth = new google.auth.GoogleAuth({
  apiKey: process.env.GOOGLE_SHEETS_API_KEY,
  scopes: ['https://www.googleapis.com/auth/spreadsheets.readonly'],
});

const spreadsheetId = process.env.GOOGLE_SHEETS_SPREADSHEET_ID;

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
            auth,
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

// 서버 시작
app.listen(PORT, async () => {
  console.log(`StorageMap 서버가 http://localhost:${PORT} 에서 시작되었습니다`);
  
  // 시작 시 데이터 로드
  await storageService.loadFromSheets();
});

module.exports = app;
