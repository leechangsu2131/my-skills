# Valuation App 고도화 작업 인수인계 (Handover)

**일시**: 2026-05-25  
**목표**: `valuation_app`의 12번 탭(PEG), 13번 탭(TAM) 가치평가 철학 고도화 및 데이터 파이프라인 자동화 모듈 신설

---

## 1. 달성한 작업 (Completed Work)

### A. 가치평가 철학의 완벽한 UI/UX 구현 (`dashboard.py`)
기존의 기계적이고 단방향적인 계산기를 **"현재 주가에 내포된 시장의 기대를 역산(Reverse Engineering)하여 현실성을 검증하는 시뮬레이터"**로 전면 개조했습니다.

1. **12번 탭 (PEG 역산 샌드박스)**
   - 목표: "과연 향후 5년 동안 시장의 기대를 충족하려면 회사가 매년 몇 %씩 성장해야 하는가?"
   - 멀티플 수축(Multiple Contraction) 로직 반영: 고성장기(n년) 이후에는 피어 그룹 평균이나 역사적 평균 수준으로 PER이 회귀한다는 가정을 바탕으로 요구 성장률을 역추산함.
   - 고성장이 요구하는 과도한 재투자율(Reinvestment Rate)의 비현실성을 경고하는 시나리오 매트릭스 구현.

2. **13번 탭 (TAM 역산 샌드박스)**
   - 목표: "현재 주가를 정당화하려면 미래에 글로벌 시장 점유율을 몇 %나 쟁탈해야 하는가?"
   - 슬라이더: 투자기간, TAM 성장률, 투자자 목표 수익률, 미래 OPM, 타겟 PER.
   - **수식 투명화**: 수식의 블랙박스를 없애기 위해 결과창 하단에 [요구 순이익 -> 요구 영업이익 -> 요구 매출액 -> 요구 점유율]로 이어지는 4단계 계산 과정을 Expander로 투명하게 공개함.

### B. 데이터 파이프라인 자동화 구축 (`pipeline/` 모듈 신설)
수작업에 의존하던 `market.json` 및 `metrics.json` 갱신 작업을 완전 자동화하는 백엔드 코어를 구현했습니다.
- **`dart_fetcher.py`**: `OpenDartReader`를 활용한 DART 재무제표 Raw XBRL 수집.
- **`market_fetcher.py`**: `pykrx`를 활용한 시가총액, 주가, 발행주식수 수집.
- **`llm_mapper.py`**: Gemini 2.5 Flash API를 활용하여, 방대한 DART 계정과목을 16개 표준 핵심 지표 포맷으로 자동 변환(Mapping/Parsing).
- **`cli.py`**: 터미널에서 `python pipeline/cli.py [종목코드] [연도]` 명령어로 전 과정 일괄 수행 후 JSON 파일 저장 기능.

---

## 2. 다음 IDE 환경에서의 Next Steps (To-Do)

다른 IDE(VS Code, Cursor 등)에서 이어서 작업하실 때 다음 사항들을 진행하시면 됩니다.

1. **파이프라인 환경변수 세팅 및 구동 테스트**
   - `.env` 파일 또는 시스템 환경변수에 `DART_API_KEY`, `GEMINI_API_KEY` 설정.
   - `pip install OpenDartReader pykrx google-genai` 등 의존성 설치 후 `python pipeline/cli.py 009150 2024` 테스트 실행.
2. **과거 데이터(Historical) 연동 강화**
   - 현재 `market_fetcher.py` 내의 `historical_average_per`와 `peer_average_per`는 API에서 동적으로 가져오는 로직(TODO)이 비어있어 임시 고정값(15.0)이 적용되어 있습니다. 이를 네이버 금융이나 기타 API에서 동적으로 긁어오도록 로직 보강이 필요합니다.
3. **대시보드 종합 결론(Phase 10) 탭 보강**
   - 12번, 13번 탭에서 도출된 "내포 기대치"의 버블 여부를 10번 탭(종합 결론)에 요약하여 뿌려주는 연동 작업.

---

## 3. 핵심 파일 위치 (File Paths)
- 대시보드 로직: `valuation_app/dashboard.py` (render_peg_tab, render_tam_tab 함수)
- 파이프라인 엔트리: `pipeline/cli.py`
- 데이터 매핑 로직: `pipeline/llm_mapper.py`
- 데이터 저장 위치: `data/valuation/<ticker>/normalized/`
