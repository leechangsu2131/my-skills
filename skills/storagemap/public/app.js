// STORAGEMAP 2D - 물건 위치 관리 시스템
// 스펙 문서 기반 구현

class StorageMapApp {
    constructor() {
        this.apiBase = '/api';
        this.currentSpace = 'default';
        this.selectedFurniture = null;
        this.highlightedFurniture = null;
        this.zoom = 1;
        this.data = {
            spaces: [],
            furniture: [],
            items: []
        };

        this.init();
    }

    async init() {
        this.showLoading(true);
        try {
            await this.loadData();
            this.setupEventListeners();
            this.render();
            this.showToast('STORAGEMAP 2D가 시작되었습니다');
        } catch (error) {
            console.error('초기화 실패:', error);
            this.showToast('시스템 초기화에 실패했습니다', 'error');
        } finally {
            this.showLoading(false);
        }
    }

    // 데이터 로드 - localStorage 지속성 추가
    async loadData() {
        try {
            const response = await fetch(`${this.apiBase}/data`);
            if (!response.ok) throw new Error('데이터 로드 실패');

            const serverData = await response.json();

            // localStorage에서 로컬 데이터 로드
            const localData = this.loadLocalData();

            // 서버 데이터와 로컬 데이터 병합
            this.data = this.mergeData(serverData, localData);

            console.log('데이터 로드 완료 (병합):', this.data);

            // 현재 공간이 데이터에 없으면 첫 번째 공간으로 설정
            if (this.data.spaces.length > 0 && !this.data.spaces.find(s => s.space_id === this.currentSpace)) {
                this.currentSpace = this.data.spaces[0].space_id;
            }
        } catch (error) {
            console.error('데이터 로드 오류:', error);
            this.showToast('데이터를 서버에서 불러올 수 없습니다. 오프라인 모드로 동작합니다.', 'warning');
            // localStorage에서 로드 시도
            const localData = this.loadLocalData();
            if (localData && localData.spaces && localData.spaces.length > 0) {
                this.data = localData;
                this.currentSpace = this.data.spaces[0].space_id;
                console.log('로컬 데이터 로드 완료:', this.data);
            } else {
                // 샘플 데이터로 대체 (localStorage도 비어있을 때만)
                this.loadSampleData();
                console.log('샘플 데이터 로드 완료');
            }
        }
    }

    // localStorage에서 데이터 로드
    loadLocalData() {
        try {
            const saved = localStorage.getItem('storagemap_data');
            if (saved) {
                return JSON.parse(saved);
            }
        } catch (e) {
            console.error('localStorage 로드 실패:', e);
        }
        return { spaces: [], furniture: [], items: [] };
    }

    // localStorage에 데이터 저장
    saveLocalData() {
        try {
            localStorage.setItem('storagemap_data', JSON.stringify(this.data));
            console.log('localStorage 저장 완료');
        } catch (e) {
            console.error('localStorage 저장 실패:', e);
        }
    }

    // 서버 데이터와 로컬 데이터 병합
    mergeData(serverData, localData) {
        // ID 기준으로 중복 제거하며 병합
        const spaces = [...serverData.spaces];
        localData.spaces.forEach(localSpace => {
            if (!spaces.find(s => s.space_id === localSpace.space_id)) {
                spaces.push(localSpace);
            }
        });

        const furniture = [...serverData.furniture];
        localData.furniture.forEach(localFurniture => {
            if (!furniture.find(f => f.furniture_id === localFurniture.furniture_id)) {
                furniture.push(localFurniture);
            }
        });

        const items = [...serverData.items];
        localData.items.forEach(localItem => {
            if (!items.find(i => i.item_id === localItem.item_id)) {
                items.push(localItem);
            }
        });

        return { spaces, furniture, items };
    }

    // 샘플 데이터 (개발용)
    loadSampleData() {
        this.data = {
            spaces: [
                { space_id: 's1', name: '3학년 2반', description: '교실 공간' },
                { space_id: 's2', name: '우리 집', description: '거실/서재 공간' }
            ],
            furniture: [
                {
                    furniture_id: 'f1',
                    space_id: 's1',
                    name: '앞 교구장',
                    type: '교구장',
                    pos_x: 50,
                    pos_y: 80,
                    width: 120,
                    height: 80
                },
                {
                    furniture_id: 'f2',
                    space_id: 's1',
                    name: '교탁',
                    type: '교탁',
                    pos_x: 300,
                    pos_y: 40,
                    width: 160,
                    height: 60
                },
                {
                    furniture_id: 'f3',
                    space_id: 's2',
                    name: 'TV 장식장',
                    type: '서랍장',
                    pos_x: 80,
                    pos_y: 120,
                    width: 200,
                    height: 70
                }
            ],
            items: [
                {
                    item_id: 'i1',
                    name: '리코더 (학생용)',
                    furniture_id: 'f1',
                    category: '교구',
                    quantity: 25,
                    memo: '학생용 리코더'
                },
                {
                    item_id: 'i2',
                    name: '수학 교구 세트',
                    furniture_id: 'f1',
                    category: '교구',
                    quantity: 5,
                    memo: '기하 도형 포함'
                },
                {
                    item_id: 'i3',
                    name: '리모컨',
                    furniture_id: 'f3',
                    category: '전자기기',
                    quantity: 2,
                    memo: 'TV, 에어컨'
                },
                {
                    item_id: 'i4',
                    name: '출석부',
                    furniture_id: 'f2',
                    category: '서류',
                    quantity: 1,
                    memo: '3월분'
                }
            ]
        };
    }

    // 이벤트 리스너 설정
    setupEventListeners() {
        // 검색
        const searchInput = document.getElementById('searchInput');
        const searchResults = document.getElementById('searchResults');

        searchInput.addEventListener('input', this.debounce(() => {
            this.handleSearch(searchInput.value.trim());
        }, 300));

        // 검색 결과 외 클릭 시 닫기
        document.addEventListener('click', (e) => {
            if (!e.target.closest('.search-box')) {
                searchResults.style.display = 'none';
            }
        });

        // 공간 탭
        document.getElementById('addSpaceBtn').addEventListener('click', () => {
            this.openSpaceModal();
        });

        // 버튼들
        document.getElementById('addItemBtn').addEventListener('click', () => {
            this.openItemModal();
        });

        document.getElementById('addFurnitureBtn').addEventListener('click', () => {
            this.openAddFurnitureModal();
        });

        document.getElementById('manageSpaceBtn').addEventListener('click', () => {
            this.openSpaceManager();
        });

        document.getElementById('exportDataBtn').addEventListener('click', () => {
            this.exportData();
        });

        // 인증 상태 체크
        document.getElementById('authStatus').addEventListener('click', () => {
            this.checkAuthStatus();
        });

        // 초기 인증 상태 체크
        this.checkAuthStatus();

        // 확대/축소
        document.getElementById('zoomIn').addEventListener('click', () => {
            this.setZoom(this.zoom + 0.1);
        });

        document.getElementById('zoomOut').addEventListener('click', () => {
            this.setZoom(this.zoom - 0.1);
        });

        document.getElementById('zoomReset').addEventListener('click', () => {
            this.setZoom(1);
        });

        // 이 가구에 물건 추가 버튼 - 이벤트 위임 사용 (버튼이 초기에 DOM에 없음)
        document.addEventListener('click', (e) => {
            const btn = e.target.closest('#addItemToFurnitureBtn');
            if (btn) {
                console.log('🖱️ 버튼 클릭! selectedFurniture:', this.selectedFurniture);
                if (this.selectedFurniture) {
                    this.openItemModal(this.selectedFurniture);
                }
            }
        });

        // 키보드 단축키
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                this.closeModal();
            }
            if (e.ctrlKey && e.key === 'f') {
                e.preventDefault();
                searchInput.focus();
            }
        });
    }

    // 데이터 내보내기 (JSON 백업)
    exportData() {
        try {
            const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(this.data, null, 2));
            const downloadAnchorNode = document.createElement('a');
            downloadAnchorNode.setAttribute("href", dataStr);
            downloadAnchorNode.setAttribute("download", "storagemap_backup_" + new Date().toISOString().slice(0, 10) + ".json");
            document.body.appendChild(downloadAnchorNode);
            downloadAnchorNode.click();
            downloadAnchorNode.remove();
            this.showToast('✅ 데이터 백업이 완료되었습니다. (JSON)', 'success');
        } catch (error) {
            console.error('데이터 내보내기 실패:', error);
            this.showToast('❌ 데이터 백업에 실패했습니다.', 'error');
        }
    }

    // 검색 처리 (스펙 문서 5장 참조)
    async handleSearch(query) {
        const searchResults = document.getElementById('searchResults');

        if (!query) {
            searchResults.style.display = 'none';
            return;
        }

        try {
            const response = await fetch(`${this.apiBase}/search?q=${encodeURIComponent(query)}`);
            const data = await response.json();

            this.displaySearchResults(data.results);
        } catch (error) {
            console.error('검색 실패:', error);
            this.displaySearchResults(this.localSearch(query));
        }
    }

    // 로컬 검색 (API 실패 시)
    localSearch(query) {
        const lowerQuery = query.toLowerCase();
        const results = [];

        this.data.items.forEach(item => {
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
                const furniture = this.data.furniture.find(f => f.furniture_id === item.furniture_id);
                const space = this.data.spaces.find(s => s.space_id === furniture?.space_id);

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

    // 검색 결과 표시
    displaySearchResults(results) {
        const searchResults = document.getElementById('searchResults');

        if (results.length === 0) {
            searchResults.innerHTML = `
                <div class="search-result-item">
                    <div class="search-result-name">검색 결과 없음</div>
                    <div class="search-result-path">다른 키워드로 시도해보세요</div>
                </div>
            `;
        } else {
            searchResults.innerHTML = results.map(item => `
                <div class="search-result-item" onclick="app.goToItem('${item.item_id}')">
                    <div class="search-result-name">${item.name}</div>
                    <div class="search-result-path">📍 ${item.path}</div>
                    <div class="search-result-category">${item.category}</div>
                </div>
            `).join('');
        }

        searchResults.style.display = 'block';
    }

    // 아이템으로 이동
    goToItem(itemId) {
        const item = this.data.items.find(i => i.item_id === itemId);
        if (!item) return;

        const furniture = this.data.furniture.find(f => f.furniture_id === item.furniture_id);
        if (!furniture) return;

        // 해당 공간으로 전환
        this.currentSpace = furniture.space_id;

        // 가구 선택 및 하이라이트
        this.selectedFurniture = furniture.furniture_id;
        this.highlightedFurniture = furniture.furniture_id;

        this.render();
        this.selectFurniture(furniture.furniture_id);

        // 검색 결과 닫기
        document.getElementById('searchResults').style.display = 'none';
        document.getElementById('searchInput').value = '';

        this.showToast(`📍 ${item.name} - ${furniture.name}`);

        // 3초 후 하이라이트 자동 해제
        setTimeout(() => {
            this.highlightedFurniture = null;
            this.render();
        }, 3000);
    }

    // 렌더링
    render() {
        this.renderSpaceTabs();
        this.renderFloorPlan();
        this.renderSidebar();
    }

    // 공간 탭 렌더링 - 개선된 버전 (이벤트 위임 사용)
    renderSpaceTabs() {
        const spaceTabs = document.getElementById('spaceTabs');
        const addButton = document.getElementById('addSpaceBtn');

        // 기존 탭 제거 (추가 버튼은 제외)
        spaceTabs.querySelectorAll('.space-tab:not(.add-tab)').forEach(tab => tab.remove());

        // 새 탭 추가
        this.data.spaces.forEach(space => {
            const tab = document.createElement('div');
            const isActive = space.space_id === this.currentSpace;
            tab.className = `space-tab ${isActive ? 'active' : ''}`;
            tab.dataset.space = space.space_id;
            tab.innerHTML = `
                <span class="tab-icon">🏠</span>
                <span class="tab-name">${space.name}</span>
            `;

            // 클릭 이벤트 직접 바인딩
            tab.onclick = () => {
                console.log('공간 탭 클릭:', space.space_id, space.name);
                this.switchSpace(space.space_id);
            };

            spaceTabs.insertBefore(tab, addButton);
        });

        console.log('공간 탭 렌더링 완료:', this.data.spaces.length, '개');
    }

    // 공간 전환
    switchSpace(spaceId) {
        this.currentSpace = spaceId;
        this.selectedFurniture = null;
        this.render();
    }

    // 2D 평면도 렌더링 - 완전히 새로운 드래그 구현
    renderFloorPlan() {
        const floorPlan = document.getElementById('floorPlan');
        const emptyState = document.getElementById('emptyState');

        const spaceFurniture = this.data.furniture.filter(f => f.space_id === this.currentSpace);

        if (spaceFurniture.length === 0) {
            floorPlan.style.display = 'none';
            emptyState.style.display = 'block';
            return;
        }

        floorPlan.style.display = 'block';
        emptyState.style.display = 'none';

        // 평면도 크기 계산
        const planWidth = 800;
        const planHeight = 500;
        floorPlan.style.width = `${planWidth * this.zoom}px`;
        floorPlan.style.height = `${planHeight * this.zoom}px`;

        // 가구 마커 렌더링
        floorPlan.innerHTML = spaceFurniture.map(furniture => {
            const items = this.data.items.filter(item => item.furniture_id === furniture.furniture_id);
            const isSelected = this.selectedFurniture === furniture.furniture_id;
            const isHighlighted = this.highlightedFurniture === furniture.furniture_id;

            return `
                <div class="furniture-marker ${isSelected ? 'selected' : ''} ${isHighlighted ? 'highlighted' : ''}"
                     style="left: ${furniture.pos_x * this.zoom}px; 
                            top: ${furniture.pos_y * this.zoom}px; 
                            width: ${furniture.width * this.zoom}px; 
                            height: ${furniture.height * this.zoom}px;"
                     data-furniture-id="${furniture.furniture_id}">
                    ${isHighlighted ? '<div class="pin-icon">📍</div>' : ''}
                    <div class="furniture-name">${furniture.name}</div>
                    ${items.length > 0 ? `<div class="furniture-count">${items.length}개</div>` : ''}
                    <div class="resize-handle"></div>
                </div>
            `;
        }).join('');

        // 각 마커에 직접 이벤트 리스너 연결
        this.attachMarkerListeners();
    }

    // 각 마커에 개별 이벤트 리스너 연결
    attachMarkerListeners() {
        const markers = document.querySelectorAll('.furniture-marker');
        markers.forEach(marker => {
            const furnitureId = marker.dataset.furnitureId;

            // mousedown - 드래그 시작
            marker.addEventListener('mousedown', (e) => {
                console.log('🖱️ 마커 mousedown:', e.target.className);

                // 리사이즈 핸들 클릭 체크 (closest 사용 for robust detection)
                if (e.target.closest('.resize-handle')) {
                    console.log('✅ 리사이즈 핸들 클릭 감지!');
                    e.stopPropagation();
                    e.preventDefault();
                    this.beginDrag(e, furnitureId, 'resize');
                    return;
                }

                // 가구 본체 클릭
                if (e.button === 0) { // 좌클릭만
                    e.stopPropagation();
                    e.preventDefault();
                    this.beginDrag(e, furnitureId, 'move');
                }
            });

            // click - 선택 (드래그가 아닌 경우)
            marker.addEventListener('click', (e) => {
                if (!this.hasDragged) {
                    this.selectFurniture(furnitureId);
                }
            });
        });
    }

    // 드래그 시작 (새로운 구현)
    beginDrag(e, furnitureId, type) {
        e.preventDefault();

        const furniture = this.data.furniture.find(f => f.furniture_id === furnitureId);
        if (!furniture) return;

        // 좌표를 숫자로 확실히 변환
        furniture.pos_x = parseInt(furniture.pos_x) || 0;
        furniture.pos_y = parseInt(furniture.pos_y) || 0;
        furniture.width = parseInt(furniture.width) || 100;
        furniture.height = parseInt(furniture.height) || 60;

        console.log('🖱️ 드래그 시작:', furniture.name, '타입:', type, '현재크기:', furniture.width, 'x', furniture.height);

        // 드래그 상태 초기화
        this.hasDragged = false;
        this.isDragging = true;
        this.dragType = type; // 드래그 타입 저장

        // 초기 위치 저장 (픽셀 좌표)
        const startX = e.clientX;
        const startY = e.clientY;
        const startPosX = furniture.pos_x;
        const startPosY = furniture.pos_y;
        const startWidth = furniture.width;
        const startHeight = furniture.height;

        // 마커 DOM 참조
        const marker = document.querySelector(`[data-furniture-id="${furnitureId}"]`);
        if (marker) {
            marker.classList.add('dragging');
            if (type === 'resize') {
                marker.style.cursor = 'se-resize';
                console.log('✅ 리사이즈 커서 적용');
            }
        }

        // 마우스 이동 핸들러
        const onMouseMove = (ev) => {
            if (!this.isDragging) return;

            const deltaX = ev.clientX - startX;
            const deltaY = ev.clientY - startY;

            // 이동 거리 체크 (클릭과 드래그 구분)
            if (Math.abs(deltaX) > 3 || Math.abs(deltaY) > 3) {
                this.hasDragged = true;
            }

            if (type === 'move') {
                // 줌 고려한 좌표 계산
                const rawX = startPosX + (deltaX / this.zoom);
                const rawY = startPosY + (deltaY / this.zoom);

                // 그리드 스냅
                const newX = Math.max(0, Math.round(rawX / 10) * 10);
                const newY = Math.max(0, Math.round(rawY / 10) * 10);

                // 데이터 업데이트
                furniture.pos_x = newX;
                furniture.pos_y = newY;

                // DOM 직접 업데이트
                if (marker) {
                    marker.style.left = `${newX * this.zoom}px`;
                    marker.style.top = `${newY * this.zoom}px`;
                }
            } else if (type === 'resize') {
                const rawWidth = startWidth + (deltaX / this.zoom);
                const rawHeight = startHeight + (deltaY / this.zoom);

                const newWidth = Math.max(50, Math.round(rawWidth / 10) * 10);
                const newHeight = Math.max(30, Math.round(rawHeight / 10) * 10);

                furniture.width = newWidth;
                furniture.height = newHeight;

                if (marker) {
                    marker.style.width = `${newWidth * this.zoom}px`;
                    marker.style.height = `${newHeight * this.zoom}px`;
                }

                console.log('📐 리사이즈 중:', newWidth, 'x', newHeight);
            }
        };

        // 마우스 업 핸들러
        const onMouseUp = () => {
            console.log('🖱️ 드래그 종료, 타입:', type);
            this.isDragging = false;

            if (marker) {
                marker.classList.remove('dragging');
                marker.style.cursor = ''; // 커서 초기화
            }

            // 위치 저장
            if (this.hasDragged) {
                console.log('💾 위치 저장:', furnitureId, '타입:', type);
                this.saveFurniturePosition(furnitureId);
            }

            document.removeEventListener('mousemove', onMouseMove);
            document.removeEventListener('mouseup', onMouseUp);
        };

        document.addEventListener('mousemove', onMouseMove);
        document.addEventListener('mouseup', onMouseUp);
    }

    // 가구 위치 저장
    async saveFurniturePosition(furnitureId) {
        const furniture = this.data.furniture.find(f => f.furniture_id === furnitureId);
        if (!furniture) return;

        // 숫자로 변환하여 저장
        const x = parseInt(furniture.pos_x) || 0;
        const y = parseInt(furniture.pos_y) || 0;
        const w = parseInt(furniture.width) || 100;
        const h = parseInt(furniture.height) || 60;

        console.log('💾 저장 시도:', furniture.name, 'x:', x, 'y:', y, 'w:', w, 'h:', h);

        // 데이터 정리 (숫자로 확실히 변환)
        furniture.pos_x = x;
        furniture.pos_y = y;
        furniture.width = w;
        furniture.height = h;

        try {
            const response = await fetch('/api/furniture/' + furnitureId + '/position', {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ x, y, width: w, height: h })
            });

            const result = await response.json();
            console.log('📥 서버 응답:', result);

            if (response.ok && result.success) {
                this.showToast('📍 위치 저장됨 (Google Sheets 동기화)');
                this.saveLocalData();
                console.log('✅ 저장 완료');
            } else if (response.status === 404) {
                // 가구가 서버에 없음 - 먼저 가구를 생성
                console.log('🔄 가구가 서버에 없음, 가구 생성 시도...');
                await this.createFurnitureOnServer(furniture);
                // 생성 후 다시 위치 저장 시도
                await this.retrySavePosition(furnitureId, x, y, w, h);
            } else {
                console.error('❌ 서버 저장 실패:', result.error);
                this.saveLocalData();
                this.showToast('⚠️ 로컬에만 저장됨: ' + (result.error || '알 수 없는 오류'), 'warning');
            }
        } catch (error) {
            console.error('❌ 저장 오류:', error);
            this.saveLocalData();
            this.showToast('⚠️ 로컬에만 저장됨 (연결 오류)', 'error');
        }
    }

    // 서버에 가구 생성
    async createFurnitureOnServer(furniture) {
        try {
            const response = await fetch('/api/furniture', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    name: furniture.name,
                    space_id: furniture.space_id,
                    type: furniture.type,
                    pos_x: furniture.pos_x,
                    pos_y: furniture.pos_y,
                    width: furniture.width,
                    height: furniture.height,
                    notes: furniture.notes
                })
            });

            if (response.ok) {
                console.log('✅ 서버에 가구 생성 완료:', furniture.name);
                return true;
            } else {
                const error = await response.json();
                throw new Error(error.error || '가구 생성 실패');
            }
        } catch (error) {
            console.error('❌ 서버에 가구 생성 실패:', error);
            this.showToast('서버에 가구를 생성하지 못했습니다.', 'error');
            throw error;
        }
    }

    // 위치 저장 재시도
    async retrySavePosition(furnitureId, x, y, w, h) {
        try {
            const response = await fetch('/api/furniture/' + furnitureId + '/position', {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ x, y, width: w, height: h })
            });

            if (response.ok) {
                this.showToast('📍 위치 저장됨 (Google Sheets 동기화)');
                this.saveLocalData();
                console.log('✅ 재시도 저장 완료');
            } else {
                const result = await response.json();
                throw new Error(result.error || '저장 실패');
            }
        } catch (error) {
            console.error('❌ 재시도 저장 실패:', error);
            this.saveLocalData();
            this.showToast('⚠️ 로컬에만 저장됨', 'warning');
        }
    }

    // 가구 선택
    selectFurniture(furnitureId) {
        // 드래그 중에는 선택하지 않음
        if (this.isDragging || this.hasDragged) {
            console.log('드래그 중에는 가구 선택을 건너뜁니다');
            return;
        }

        this.selectedFurniture = furnitureId;

        // 검색이 아닌 직접 클릭 시 하이라이트 제거
        this.highlightedFurniture = null;

        this.render(); // render() 내부에서 renderSidebar() 호출됨

        // 시각적 선택 상태 업데이트
        document.querySelectorAll('.furniture-marker').forEach(marker => {
            marker.classList.remove('selected');
        });

        const selectedMarker = document.querySelector(`[data-furniture-id="${furnitureId}"]`);
        if (selectedMarker) {
            selectedMarker.classList.add('selected');
        }
    }

    // 사이드바 렌더링
    renderSidebar() {
        const sidebarEmpty = document.getElementById('sidebarEmpty');
        const sidebarContent = document.getElementById('sidebarContent');

        if (!this.selectedFurniture) {
            sidebarEmpty.style.display = 'flex';
            sidebarContent.style.display = 'none';
            document.getElementById('sidebar').classList.add('is-empty');
            return;
        }

        const furniture = this.data.furniture.find(f => f.furniture_id === this.selectedFurniture);
        if (!furniture) {
            sidebarEmpty.style.display = 'flex';
            sidebarContent.style.display = 'none';
            document.getElementById('sidebar').classList.add('is-empty');
            return;
        }

        const space = this.data.spaces.find(s => s.space_id === furniture.space_id);
        const items = this.data.items.filter(item => item.furniture_id === furniture.furniture_id);

        sidebarEmpty.style.display = 'none';
        sidebarContent.style.display = 'flex';
        document.getElementById('sidebar').classList.remove('is-empty');

        // 사이드바 내용 업데이트
        document.getElementById('furnitureName').textContent = furniture.name;
        document.getElementById('locationPath').textContent = `${space?.name || '?'} > ${furniture.name}`;
        document.getElementById('itemCount').textContent = `물건 ${items.length}개`;

        // 물건 목록
        const itemsList = document.getElementById('itemsList');
        if (items.length === 0) {
            itemsList.innerHTML = `
                <div class="empty-state">
                    <p>아직 등록된 물건이 없습니다</p>
                </div>
            `;
        } else {
            itemsList.innerHTML = items.map(item => `
                <div class="item-card" onclick="app.highlightItem('${item.item_id}')">
                    <div class="item-name">${item.name}</div>
                    <div class="item-meta">
                        <span class="item-category">${item.category}</span>
                        ${item.quantity > 1 ? `<span class="item-quantity">${item.quantity}개</span>` : ''}
                    </div>
                    ${item.memo ? `<div class="item-meta">${item.memo}</div>` : ''}
                </div>
            `).join('');
        }

        // 사이드바 액션 버튼들
        document.getElementById('closeSidebarBtn').onclick = () => {
            this.selectedFurniture = null;
            this.renderSidebar();
        };

        document.getElementById('editFurnitureBtn').onclick = () => {
            this.openEditFurnitureModal(furniture.furniture_id);
        };

        document.getElementById('deleteFurnitureBtn').onclick = () => {
            this.deleteFurniture(furniture.furniture_id);
        };
    }

    // 아이템 하이라이트
    highlightItem(itemId) {
        const item = this.data.items.find(i => i.item_id === itemId);
        if (!item) return;

        const furniture = this.data.furniture.find(f => f.furniture_id === item.furniture_id);
        if (!furniture) return;

        this.highlightedFurniture = furniture.furniture_id;
        this.selectedFurniture = furniture.furniture_id;

        this.render(); // 딱 한 번만 렌더링

        this.showToast(`📍 ${item.name} - ${furniture.name}`);

        // 3초 후 하이라이트 자동 해제
        setTimeout(() => {
            this.highlightedFurniture = null;
            this.renderFloorPlan(); // 평면도만 재렌더 (사이드바는 유지)
        }, 3000);
    }

    // 확대/축소
    setZoom(newZoom) {
        this.zoom = Math.max(0.5, Math.min(2, newZoom));
        this.renderFloorPlan();
    }

    // 모달 관련
    openItemModal(furnitureId = null) {
        const modal = document.getElementById('modalContainer');
        modal.innerHTML = `
            <div class="modal-overlay" onclick="app.closeModal(event)">
                <div class="modal" onclick="event.stopPropagation()">
                    <h2>📦 물건 추가</h2>
                    <form id="itemForm">
                        <div class="form-group">
                            <label>물건 이름 *</label>
                            <input type="text" name="name" required placeholder="예: 가위, 리코더, 출석부">
                        </div>
                        <div class="form-group">
                            <label>위치 (가구) *</label>
                            <select name="furniture_id" required>
                                ${this.data.furniture.map(f => {
            const space = this.data.spaces.find(s => s.space_id === f.space_id);
            const spaceName = space ? space.name : '위치 미정';
            const isCurrentSpace = f.space_id === this.currentSpace;
            const label = isCurrentSpace
                ? `${f.name} (${spaceName}) [현재공간]`
                : `${f.name} (${spaceName})`;
            return `
                                    <option value="${f.furniture_id}" ${f.furniture_id === furnitureId ? 'selected' : ''}>
                                        ${label}
                                    </option>
                                    `;
        }).join('')}
                            </select>
                        </div>
                        <div class="form-group">
                            <label>분류</label>
                            <select name="category">
                                <option value="교구">교구</option>
                                <option value="문구">문구</option>
                                <option value="전자기기">전자기기</option>
                                <option value="서류">서류</option>
                                <option value="생활용품">생활용품</option>
                                <option value="의류">의류</option>
                                <option value="공구">공구</option>
                                <option value="기타">기타</option>
                            </select>
                        </div>
                        <div class="form-group">
                            <label>수량</label>
                            <input type="number" name="quantity" min="1" value="1">
                        </div>
                        <div class="form-group">
                            <label>메모 (선택)</label>
                            <textarea name="memo" placeholder="색상, 형태, 위치 힌트 등"></textarea>
                        </div>
                        <div class="modal-actions">
                            <button type="button" class="btn btn-secondary" onclick="app.closeModal()">취소</button>
                            <button type="submit" class="btn btn-primary">추가</button>
                        </div>
                    </form>
                </div>
            </div>
        `;

        // 폼 제출 처리
        document.getElementById('itemForm').addEventListener('submit', (e) => {
            e.preventDefault();
            this.saveItem(e.target);
        });
    }

    async saveItem(form) {
        const formData = new FormData(form);
        const item = {
            name: formData.get('name'),
            furniture_id: formData.get('furniture_id'),
            category: formData.get('category'),
            quantity: parseInt(formData.get('quantity')) || 1,
            memo: formData.get('memo') || ''
        };

        try {
            const response = await fetch('/api/items', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(item)
            });

            if (response.ok) {
                const data = await response.json();
                // 로컬 데이터에 추가
                this.data.items.push(data.item);
                this.saveLocalData();
                this.closeModal();
                this.selectFurniture(item.furniture_id);
                this.render();
                this.showToast(`✅ ${item.name} 추가됨`);
            } else {
                throw new Error('API 호출 실패');
            }
        } catch (error) {
            console.error('물건 추가 실패:', error);
            // API 실패 시 로컬에만 추가
            this.data.items.push({
                item_id: 'i' + Date.now(),
                ...item
            });
            this.saveLocalData(); // localStorage 저장
            this.closeModal();
            this.selectFurniture(item.furniture_id);
            this.render();
            this.showToast(`⚠️ ${item.name} 로컬에만 추가됨 (로그인 필요)`);
        }
    }

    openSpaceManager() {
        // 공간 관리 모달 구현
        const modal = document.getElementById('modalContainer');

        const spaceListHtml = this.data.spaces.map(space => {
            const furnitureCount = this.data.furniture.filter(f => f.space_id === space.space_id).length;
            return `
                <div class="space-manage-item" style="display: flex; justify-content: space-between; align-items: center; padding: 12px; border: 1px solid var(--border); border-radius: 8px; margin-bottom: 8px;">
                    <div>
                        <div style="font-weight: 500;">${space.name}</div>
                        <div style="font-size: 12px; color: var(--text-muted);">${space.description || '설명 없음'} | 가구 ${furnitureCount}개</div>
                    </div>
                    <div style="display: flex; gap: 8px;">
                        <button class="btn-icon" onclick="app.switchSpace('${space.space_id}'); app.closeModal();" title="이 공간으로 이동">
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"></path><polyline points="9 22 9 12 15 12 15 22"></polyline></svg>
                        </button>
                    </div>
                </div>
            `;
        }).join('');

        modal.innerHTML = `
            <div class="modal-overlay" onclick="app.closeModal(event)">
                <div class="modal" onclick="event.stopPropagation()" style="width: 500px; max-height: 600px; overflow-y: auto;">
                    <h2>🏠 공간 관리</h2>
                    <div style="margin-bottom: 20px;">
                        <p style="color: var(--text-secondary); margin-bottom: 16px;">총 ${this.data.spaces.length}개의 공간</p>
                        ${spaceListHtml || '<p style="color: var(--text-muted); text-align: center;">등록된 공간이 없습니다</p>'}
                    </div>
                    <div class="modal-actions">
                        <button type="button" class="btn btn-secondary" onclick="app.closeModal()">닫기</button>
                        <button type="button" class="btn btn-primary" onclick="app.closeModal(); setTimeout(() => app.openSpaceModal(), 100);">+ 새 공간 추가</button>
                    </div>
                </div>
            </div>
        `;
    }

    openSpaceModal() {
        const modal = document.getElementById('modalContainer');
        modal.innerHTML = `
            <div class="modal-overlay" onclick="app.closeModal(event)">
                <div class="modal" onclick="event.stopPropagation()">
                    <h2>🏠 공간 추가</h2>
                    <form id="addSpaceForm">
                        <div class="form-group">
                            <label>공간 이름 *</label>
                            <input type="text" name="name" required placeholder="예: 3학년 2반, 우리 집 거실">
                        </div>
                        <div class="form-group">
                            <label>설명</label>
                            <textarea name="description" placeholder="공간에 대한 설명 (선택)"></textarea>
                        </div>
                        <div class="modal-actions">
                            <button type="button" class="btn btn-secondary" onclick="app.closeModal()">취소</button>
                            <button type="submit" class="btn btn-primary">추가</button>
                        </div>
                    </form>
                </div>
            </div>
        `;

        document.getElementById('addSpaceForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            const formData = new FormData(e.target);

            const newSpace = {
                name: formData.get('name'),
                description: formData.get('description') || ''
            };

            try {
                const response = await fetch('/api/spaces', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(newSpace)
                });

                if (response.ok) {
                    const data = await response.json();
                    // 로컬 데이터에 추가
                    this.data.spaces.push(data.space);
                    this.saveLocalData();
                    this.closeModal();
                    this.currentSpace = data.space.space_id;
                    this.render();
                    this.showToast(`✅ ${newSpace.name} 공간 추가됨`);
                } else {
                    throw new Error('API 호출 실패');
                }
            } catch (error) {
                console.error('공간 추가 실패:', error);
                // API 실패 시 로컬에만 추가
                const space = {
                    space_id: 's' + Date.now(),
                    ...newSpace
                };
                this.data.spaces.push(space);
                this.currentSpace = space.space_id;
                this.saveLocalData(); // localStorage 저장
                this.closeModal();
                this.render();
                this.showToast(`⚠️ ${newSpace.name} 로컬에만 추가됨 (로그인 필요)`, 'warning');
            }
        });
    }

    // 인증 상태 체크
    async checkAuthStatus() {
        try {
            const response = await fetch('/api/auth/status');
            const data = await response.json();

            const indicator = document.getElementById('authIndicator');
            const text = document.getElementById('authText');

            if (data.authenticated) {
                indicator.textContent = '🟢';
                indicator.className = 'auth-indicator authenticated';
                text.textContent = '로그인됨';

                // 로그인 성공 시 Google Sheets 데이터 로드
                await this.loadGoogleSheetsData();
            } else {
                indicator.textContent = '⚪';
                indicator.className = 'auth-indicator unauthenticated';
                text.textContent = '로그인 필요';

                // 로그인 필요 시 클릭하면 로그인 페이지로
                document.getElementById('authStatus').onclick = () => {
                    window.location.href = '/auth/google';
                };
            }
        } catch (error) {
            console.error('인증 상태 체크 실패:', error);
            this.showToast('인증 상태를 확인할 수 없습니다.', 'error');
        }
    }

    // Google Sheets 데이터 로드 - 로그인 시 Google Sheets 데이터 우선
    async loadGoogleSheetsData() {
        try {
            this.showLoading(true);
            console.log('🔄 Google Sheets 데이터 로드 시작...');

            const response = await fetch('/api/data/reload');
            console.log('📥 서버 응답 상태:', response.status);

            const result = await response.json();
            console.log('📥 서버 응답 데이터:', result);

            if (result.success) {
                // 로그인된 경우 Google Sheets 데이터를 우선 사용
                this.data = result.data;

                console.log('✅ Google Sheets 데이터 적용됨:');
                console.log('  공간:', this.data.spaces?.length || 0, '개');
                console.log('  가구:', this.data.furniture?.length || 0, '개');
                console.log('  물건:', this.data.items?.length || 0, '개');

                if (this.data.spaces?.length > 0) {
                    console.log('  공간 목록:', this.data.spaces.map(s => s.name).join(', '));
                }

                // Google Sheets 데이터를 localStorage에 저장
                this.saveLocalData();

                // 현재 공간 재설정
                if (this.data.spaces?.length > 0) {
                    const currentSpaceExists = this.data.spaces.find(s => s.space_id === this.currentSpace);
                    if (!currentSpaceExists) {
                        this.currentSpace = this.data.spaces[0].space_id;
                        console.log('  현재 공간 설정:', this.currentSpace);
                    }
                }

                this.render();
                this.showToast(`✅ Google Sheets 데이터 로드 완료 (${this.data.spaces?.length || 0}개 공간)`);

                // 데이터 관계 검증
                this.validateDataRelations();
            } else {
                console.error('❌ 서버 응답 실패:', result.error);
                this.showToast('❌ Google Sheets 데이터 로드 실패: ' + result.error, 'error');
            }
        } catch (error) {
            console.error('❌ Google Sheets 데이터 로드 실패:', error);
            this.showToast('⚠️ Google Sheets 통신 실패. 재로그인이 필요할 수 있습니다.', 'error');
            // localStorage에서 로드
            const localData = this.loadLocalData();
            if (localData.spaces.length > 0) {
                this.data = localData;
                this.render();
            }
        } finally {
            this.showLoading(false);
        }
    }

    // 가구 추가 모달
    openAddFurnitureModal() {
        const modal = document.getElementById('modalContainer');
        modal.innerHTML = `
            <div class="modal-overlay" onclick="app.closeModal(event)">
                <div class="modal" onclick="event.stopPropagation()">
                    <h2>🗄️ 가구 추가</h2>
                    <form id="addFurnitureForm">
                        <div class="form-group">
                            <label>가구 이름 *</label>
                            <input type="text" name="name" required placeholder="예: 앞 교구장, 책상">
                        </div>
                        <div class="form-group">
                            <label>유형</label>
                            <select name="type">
                                <option value="">선택 안함</option>
                                <option value="교구장">교구장</option>
                                <option value="서랍장">서랍장</option>
                                <option value="책상">책상</option>
                                <option value="교탁">교탁</option>
                                <option value="선반">선반</option>
                                <option value="기타">기타</option>
                            </select>
                        </div>
                        <div class="form-group">
                            <label>초기 위치 X</label>
                            <input type="number" name="pos_x" value="50" min="0">
                        </div>
                        <div class="form-group">
                            <label>초기 위치 Y</label>
                            <input type="number" name="pos_y" value="50" min="0">
                        </div>
                        <div class="form-group">
                            <label>너비</label>
                            <input type="number" name="width" value="120" min="50">
                        </div>
                        <div class="form-group">
                            <label>높이</label>
                            <input type="number" name="height" value="80" min="30">
                        </div>
                        <div class="form-group">
                            <label>메모</label>
                            <textarea name="notes" placeholder="가구에 대한 메모"></textarea>
                        </div>
                        <div class="modal-actions">
                            <button type="button" class="btn btn-secondary" onclick="app.closeModal()">취소</button>
                            <button type="submit" class="btn btn-primary">추가</button>
                        </div>
                    </form>
                </div>
            </div>
        `;

        document.getElementById('addFurnitureForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            const formData = new FormData(e.target);

            // 현재 공간이 없으면 첫 번째 공간으로 설정
            if (!this.currentSpace && this.data.spaces.length > 0) {
                this.currentSpace = this.data.spaces[0].space_id;
                console.log('⚠️ currentSpace 없음, 첫 번째 공간으로 설정:', this.currentSpace);
            }

            const newFurniture = {
                name: formData.get('name'),
                space_id: this.currentSpace,
                type: formData.get('type') || null,
                pos_x: parseInt(formData.get('pos_x')) || 50,
                pos_y: parseInt(formData.get('pos_y')) || 50,
                width: parseInt(formData.get('width')) || 120,
                height: parseInt(formData.get('height')) || 80,
                notes: formData.get('notes') || null
            };

            console.log('📝 가구 추가 요청:', newFurniture.name, '공간:', this.currentSpace);

            try {
                const response = await fetch('/api/furniture', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(newFurniture)
                });

                if (response.ok) {
                    const data = await response.json();
                    // 로컬 데이터에 추가
                    this.data.furniture.push(data.furniture);
                    this.saveLocalData();
                    this.closeModal();
                    this.render();
                    this.showToast(`✅ ${newFurniture.name} 가구 추가됨`);
                } else {
                    throw new Error('API 호출 실패');
                }
            } catch (error) {
                console.error('가구 추가 실패:', error);
                // API 실패 시 로컬에만 추가
                this.data.furniture.push({
                    furniture_id: 'f' + Date.now(),
                    ...newFurniture
                });
                this.saveLocalData(); // localStorage 저장
                this.closeModal();
                this.render();
                this.showToast(`⚠️ ${newFurniture.name} 로컬에만 추가됨 (로그인 필요)`);
            }
        });
    }

    // 가구 수정 모달
    openEditFurnitureModal(furnitureId) {
        const furniture = this.data.furniture.find(f => f.furniture_id === furnitureId);
        if (!furniture) return;

        const modal = document.getElementById('modalContainer');
        modal.innerHTML = `
            <div class="modal-overlay" onclick="app.closeModal(event)">
                <div class="modal" onclick="event.stopPropagation()">
                    <h2>🗄️ 가구 수정</h2>
                    <form id="editFurnitureForm">
                        <div class="form-group">
                            <label>가구 이름 *</label>
                            <input type="text" name="name" value="${furniture.name}" required>
                        </div>
                        <div class="form-group">
                            <label>유형</label>
                            <select name="type">
                                <option value="" ${!furniture.type ? 'selected' : ''}>선택 안함</option>
                                <option value="교구장" ${furniture.type === '교구장' ? 'selected' : ''}>교구장</option>
                                <option value="서랍장" ${furniture.type === '서랍장' ? 'selected' : ''}>서랍장</option>
                                <option value="책상" ${furniture.type === '책상' ? 'selected' : ''}>책상</option>
                                <option value="교탁" ${furniture.type === '교탁' ? 'selected' : ''}>교탁</option>
                                <option value="선반" ${furniture.type === '선반' ? 'selected' : ''}>선반</option>
                                <option value="기타" ${furniture.type === '기타' ? 'selected' : ''}>기타</option>
                            </select>
                        </div>
                        <div class="form-group">
                            <label>메모</label>
                            <textarea name="notes" placeholder="가구에 대한 메모">${furniture.notes || ''}</textarea>
                        </div>
                        <div class="modal-actions">
                            <button type="button" class="btn btn-secondary" onclick="app.closeModal()">취소</button>
                            <button type="submit" class="btn btn-primary">저장</button>
                        </div>
                    </form>
                </div>
            </div>
        `;

        document.getElementById('editFurnitureForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            const formData = new FormData(e.target);

            furniture.name = formData.get('name');
            furniture.type = formData.get('type') || null;
            furniture.notes = formData.get('notes') || null;

            this.closeModal();
            this.render();
            this.renderSidebar();
            this.showToast('✅ 가구 수정됨');
        });
    }

    // 가구 삭제
    deleteFurniture(furnitureId) {
        const furniture = this.data.furniture.find(f => f.furniture_id === furnitureId);
        if (!furniture) return;

        // 물건이 있는지 확인
        const items = this.data.items.filter(i => i.furniture_id === furnitureId);
        if (items.length > 0) {
            alert(`이 가구 안에 ${items.length}개의 물건이 있습니다.\n먼저 물건을 이동하거나 삭제해주세요.`);
            return;
        }

        if (!confirm(`"${furniture.name}" 가구를 삭제하시겠습니까?`)) {
            return;
        }

        this.data.furniture = this.data.furniture.filter(f => f.furniture_id !== furnitureId);
        this.selectedFurniture = null;
        this.render();
        this.renderSidebar();
        this.showToast('🗑️ 가구 삭제됨');
    }

    closeModal(event) {
        if (event && event.target !== event.currentTarget) return;
        document.getElementById('modalContainer').innerHTML = '';
    }

    // 디버그 도구: 현재 상태 확인
    debugStatus() {
        console.log('=== 현재 앱 상태 ===');
        console.log('currentSpace:', this.currentSpace);
        console.log('data.spaces:', this.data.spaces);
        console.log('data.furniture:', this.data.furniture?.length || 0, '개');
        console.log('data.items:', this.data.items?.length || 0, '개');
        console.log('===================');
        return {
            currentSpace: this.currentSpace,
            spaces: this.data.spaces,
            furnitureCount: this.data.furniture?.length || 0,
            itemsCount: this.data.items?.length || 0
        };
    }

    // 디버그 도구: Google Sheets 직접 테스트
    async debugGoogleSheets() {
        console.log('🔍 Google Sheets 직접 테스트 시작...');
        try {
            const response = await fetch('/api/debug/sheets');
            const result = await response.json();
            console.log('📊 Google Sheets 진단 결과:', result);
            return result;
        } catch (error) {
            console.error('❌ Google Sheets 테스트 실패:', error);
            return { error: error.message };
        }
    }
    validateDataRelations() {
        const issues = [];

        // 1. 가구의 space_id가 존재하는 공간을 참조하는지 확인
        this.data.furniture.forEach(f => {
            const spaceExists = this.data.spaces.find(s => s.space_id === f.space_id);
            if (!spaceExists) {
                issues.push(`가구 "${f.name}" (${f.furniture_id})가 존재하지 않는 공간 (${f.space_id})를 참조합니다`);
            }
        });

        // 2. 물건의 furniture_id가 존재하는 가구를 참조하는지 확인
        this.data.items.forEach(item => {
            const furnitureExists = this.data.furniture.find(f => f.furniture_id === item.furniture_id);
            if (!furnitureExists) {
                issues.push(`물건 "${item.name}" (${item.item_id})가 존재하지 않는 가구 (${item.furniture_id})를 참조합니다`);
            }
        });

        // 3. 고립된 공간 확인 (가구가 없는 공간)
        this.data.spaces.forEach(space => {
            const furnitureCount = this.data.furniture.filter(f => f.space_id === space.space_id).length;
            console.log(`공간 "${space.name}": 가구 ${furnitureCount}개`);
        });

        // 4. 통계 출력
        console.log('=== 데이터 관계 검증 결과 ===');
        console.log(`공간: ${this.data.spaces.length}개`);
        console.log(`가구: ${this.data.furniture.length}개`);
        console.log(`물건: ${this.data.items.length}개`);

        if (issues.length > 0) {
            console.warn('발견된 문제:');
            issues.forEach(issue => console.warn('  - ' + issue));
        } else {
            console.log('✅ 모든 데이터 관계가 정상입니다');
        }

        return issues;
    }

    // localStorage 데이터 초기화
    clearLocalData() {
        try {
            localStorage.removeItem('storagemap_data');
            console.log('localStorage 데이터 초기화 완료');
            this.showToast('로컬 데이터가 초기화되었습니다');
        } catch (e) {
            console.error('localStorage 초기화 실패:', e);
        }
    }

    // 유틸리티 함수
    showToast(message, type = 'success') {
        const toast = document.getElementById('toast');
        toast.textContent = message;
        toast.className = `toast show ${type}`;

        setTimeout(() => {
            toast.classList.remove('show');
        }, 3000);
    }

    showLoading(show) {
        const overlay = document.getElementById('loadingOverlay');
        overlay.style.display = show ? 'flex' : 'none';
    }

    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }
}

// 2D 드래그 상태 관리
class DragHandler {
    constructor() {
        this.dragState = null;
        this.isDragging = false;
        this.isResizing = false;
        this.currentFurniture = null;
        this.startX = 0;
        this.startY = 0;
        this.startPosX = 0;
        this.startPosY = 0;
        this.startWidth = 0;
        this.startHeight = 0;
    }

    startDrag(e, furniture, type = 'move', zoom = 1) {
        e.preventDefault();
        e.stopPropagation();

        this.zoom = zoom; // 줌 레벨 저장
        this.dragState = {
            furnitureId: furniture.furniture_id,
            type: type,
            startX: e.clientX,
            startY: e.clientY,
            startPosX: furniture.pos_x || 0,
            startPosY: furniture.pos_y || 0,
            startWidth: furniture.width || 100,
            startHeight: furniture.height || 60
        };

        this.isDragging = type === 'move';
        this.isResizing = type === 'resize';
        this.currentFurniture = furniture;

        return this.dragState;
    }

    handleMove(e) {
        if (!this.dragState) return null;

        const deltaX = e.clientX - this.dragState.startX;
        const deltaY = e.clientY - this.dragState.startY;
        const zoom = this.zoom || 1;

        if (this.dragState.type === 'move') {
            // 줌 레벨을 고려하여 픽셀 델타를 가구 좌표로 변환
            const rawX = this.dragState.startPosX + (deltaX / zoom);
            const rawY = this.dragState.startPosY + (deltaY / zoom);

            return {
                x: Math.max(0, Math.round(rawX / 10) * 10),
                y: Math.max(0, Math.round(rawY / 10) * 10),
                type: 'move'
            };
        } else if (this.dragState.type === 'resize') {
            const newWidth = Math.max(50, this.dragState.startWidth + (deltaX / zoom));
            const newHeight = Math.max(30, this.dragState.startHeight + (deltaY / zoom));

            return {
                width: Math.round(newWidth / 10) * 10,
                height: Math.round(newHeight / 10) * 10,
                type: 'resize'
            };
        }

        return null;
    }

    endDrag() {
        const state = this.dragState;
        this.dragState = null;
        this.isDragging = false;
        this.isResizing = false;
        this.currentFurniture = null;
        return state;
    }
}

const dragHandler = new DragHandler();

// 앱 인스턴스 생성
const app = new StorageMapApp();
