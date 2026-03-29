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

    // 데이터 로드
    async loadData() {
        try {
            const response = await fetch(`${this.apiBase}/data`);
            if (!response.ok) throw new Error('데이터 로드 실패');
            
            this.data = await response.json();
            console.log('데이터 로드 완료:', this.data);
        } catch (error) {
            console.error('데이터 로드 오류:', error);
            // 샘플 데이터로 대체
            this.loadSampleData();
        }
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

        document.getElementById('manageSpaceBtn').addEventListener('click', () => {
            this.openSpaceManager();
        });

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
        
        // 하이라이트 애니메이션
        setTimeout(() => {
            this.highlightedFurniture = null;
            this.render();
        }, 2000);
        
        this.showToast(`📍 ${item.name} - ${furniture.name}`);
    }

    // 렌더링
    render() {
        this.renderSpaceTabs();
        this.renderFloorPlan();
        this.renderSidebar();
    }

    // 공간 탭 렌더링
    renderSpaceTabs() {
        const spaceTabs = document.getElementById('spaceTabs');
        const currentTab = spaceTabs.querySelector('.space-tab.active');
        const addButton = document.getElementById('addSpaceBtn');
        
        // 기존 탭 제거 (추가 버튼은 제외)
        spaceTabs.querySelectorAll('.space-tab:not(.add-tab)').forEach(tab => tab.remove());
        
        // 새 탭 추가
        this.data.spaces.forEach(space => {
            const tab = document.createElement('div');
            tab.className = `space-tab ${space.space_id === this.currentSpace ? 'active' : ''}`;
            tab.dataset.space = space.space_id;
            tab.innerHTML = `
                <span class="tab-icon">🏠</span>
                <span class="tab-name">${space.name}</span>
            `;
            tab.addEventListener('click', () => this.switchSpace(space.space_id));
            
            spaceTabs.insertBefore(tab, addButton);
        });
    }

    // 공간 전환
    switchSpace(spaceId) {
        this.currentSpace = spaceId;
        this.selectedFurniture = null;
        this.render();
    }

    // 2D 평면도 렌더링
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
                     onclick="app.selectFurniture('${furniture.furniture_id}')"
                     data-furniture-id="${furniture.furniture_id}">
                    <div class="furniture-name">${furniture.name}</div>
                    ${items.length > 0 ? `<div class="furniture-count">${items.length}개</div>` : ''}
                </div>
            `;
        }).join('');
    }

    // 가구 선택
    selectFurniture(furnitureId) {
        this.selectedFurniture = furnitureId;
        this.renderSidebar();
        
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
            return;
        }
        
        const furniture = this.data.furniture.find(f => f.furniture_id === this.selectedFurniture);
        if (!furniture) {
            sidebarEmpty.style.display = 'flex';
            sidebarContent.style.display = 'none';
            return;
        }
        
        const space = this.data.spaces.find(s => s.space_id === furniture.space_id);
        const items = this.data.items.filter(item => item.furniture_id === furniture.furniture_id);
        
        sidebarEmpty.style.display = 'none';
        sidebarContent.style.display = 'flex';
        
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
        
        // 이 가구에 물건 추가 버튼
        document.getElementById('addItemToFurnitureBtn').onclick = () => {
            this.openItemModal(furniture.furniture_id);
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
        
        this.render();
        this.selectFurniture(furniture.furniture_id);
        
        this.showToast(`📍 ${item.name} - ${furniture.name}`);
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
                                ${this.data.furniture.map(f => `
                                    <option value="${f.furniture_id}" ${f.furniture_id === furnitureId ? 'selected' : ''}>
                                        ${f.name}
                                    </option>
                                `).join('')}
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
            item_id: 'i' + Date.now(),
            name: formData.get('name'),
            furniture_id: formData.get('furniture_id'),
            category: formData.get('category'),
            quantity: parseInt(formData.get('quantity')) || 1,
            memo: formData.get('memo') || ''
        };
        
        // 데이터 추가 (실제로는 API 호출)
        this.data.items.push(item);
        
        this.closeModal();
        this.selectFurniture(item.furniture_id);
        this.render();
        
        this.showToast(`✅ ${item.name} 추가됨`);
    }

    openSpaceManager() {
        this.showToast('공간 관리 기능은 준비 중입니다');
    }

    openSpaceModal() {
        this.showToast('공간 추가 기능은 준비 중입니다');
    }

    closeModal(event) {
        if (event && event.target !== event.currentTarget) return;
        document.getElementById('modalContainer').innerHTML = '';
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

// 앱 초기화
const app = new StorageMapApp();
