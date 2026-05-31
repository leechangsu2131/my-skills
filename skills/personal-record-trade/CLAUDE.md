# CLAUDE.md

이 저장소를 다른 IDE나 에이전트가 이어받을 때 가장 먼저 읽어야 하는 인수인계 문서입니다. 사용자는 한국어로 작업하며, 이 프로젝트는 투자 판단을 대신하는 도구가 아니라 현재 주가에 담긴 가정과 계산 과정을 투명하게 보여주는 학습형 가치분석 도구입니다.

## 작업 원칙

- 한국어로 설명합니다. 단, 코드, 명령어, 파일명, 공식명은 기존 표기를 유지합니다.
- 결론보다 과정이 중요합니다. 모든 숫자는 `출처 -> 정규화 -> 계산식 -> 결과 -> 초보자용 해석` 순서로 보여야 합니다.
- 투자 권유처럼 쓰지 않습니다. "매수/매도"가 아니라 "현재 가격이 요구하는 가정"과 "검증해야 할 질문"으로 표현합니다.
- 사용자는 대화 과정도 제품 설계의 일부로 봅니다. 중요한 결정은 `docs/superpowers/notes/2026-05-23-implied-valuation-conversation.md` 또는 새 문서에 남깁니다.
- 공식이 직관적으로 들어오지 않는다는 사용자 피드백이 핵심입니다. 공식만 던지지 말고 왜 그 공식을 쓰는지, 어떤 분모/분자를 보는지, 결과가 크면 무슨 뜻인지 설명합니다.
- 현재 중심 사례는 삼성전기, KRX `009150`입니다. NVIDIA 예시는 더 이상 중심 사례가 아닙니다.
- 현재 앱은 Streamlit 기반입니다. 이유는 빠른 반복과 분석 화면 검증이 목적이기 때문이며, 장기적으로 다른 UI로 이전할 수 있습니다.

## 현재 앱 실행

```powershell
pip install -r requirements-valuation.txt
python -m streamlit run valuation_app/dashboard.py --server.port 8501
```

브라우저 URL:

```text
http://localhost:8501/
```

헬스 체크:

```powershell
Invoke-WebRequest -Uri 'http://localhost:8501/_stcore/health' -UseBasicParsing
```

## 검증 명령

변경 후 최소한 아래를 실행합니다.

```powershell
python -m pytest tests/test_valuation_models.py tests/test_valuation_calculations.py tests/test_valuation_repository.py tests/test_valuation_audit.py tests/test_valuation_formatting.py tests/test_reverse_dcf.py tests/test_value_attribution.py tests/test_margin_scenario.py tests/test_roic_reinvestment.py tests/test_relative_valuation.py tests/test_cap_duration.py tests/test_risk_downside.py tests/test_narrative_consistency.py tests/test_synthesis.py tests/test_advanced_reverse.py -q
python -m py_compile valuation_app/dashboard.py valuation_app/relative_valuation.py valuation_app/reverse_dcf.py valuation_app/roic_reinvestment.py valuation_app/cap_duration.py valuation_app/risk_downside.py valuation_app/narrative_consistency.py valuation_app/synthesis.py valuation_app/advanced_reverse.py
```

프론트 화면을 바꿨다면 브라우저에서 직접 확인합니다. 특히 ImportError, Traceback, 탭 미표시, 숫자 포맷 깨짐을 봅니다.

## 자격증명 및 환경 설정 (.env + credentials.json)

프로젝트 루트에 아래 설정 파일들이 필요하며, 자격증명 정보는 절대 Git에 커밋하지 않습니다.

**1. `.env` 파일 구성:**
```env
DART_API_KEY=발급받은키        # opendart.fss.or.kr (무료 발급)
ANTHROPIC_API_KEY=sk-ant-...  # Claude API 연동용 키
GOOGLE_SHEET_ID=12csrOj-6xgW45JSjbh8O9okxmA34eaatszvio6hQlmc # 기본 구글 시트 ID (또는 sheet_id.txt 파일 내 ID)
```

**2. `credentials.json` 파일:**
- Google Cloud Console -> IAM -> 서비스 계정 -> 키 생성(JSON)을 통해 발급받은 서비스 계정 키 파일입니다. 구글 시트 API 읽기/쓰기 권한 인증에 사용됩니다.

---

## Google Sheets 구조 및 설계 규칙

### 1. 📒 "기업분석" 탭 (종목 목록 + 분석 결과)
- **헤더행**: 4행
- **데이터 범위**: 5행 ~ 약 30행 (보유 및 관심 종목 목록)

| 컬럼 | 이름 | 설명 | 읽기/쓰기 |
| :---: | :--- | :--- | :---: |
| A | 포지션ID | P001~P053, 없으면 "-" | 읽기 |
| B | 티커 | 한국: 6자리 숫자, 미국: 영문 | 읽기 |
| C | 종목명 | 기업명 | 읽기 |
| D | 상태 | "보유" or "관심" | 읽기 |
| E | 현재가 | `GOOGLEFINANCE` 수식으로 자동 계산 | 읽기 |
| F | 시총(억) | `GOOGLEFINANCE` 수식으로 자동 계산 | 읽기 |
| G | PER | `GOOGLEFINANCE` 수식으로 자동 계산 | 읽기 |
| H | EV/FCF | 계산 완료된 EV/FCF 배수 | **쓰기** |
| I | PBR | 계산 완료된 PBR 배수 | **쓰기** |
| J | Implied성장률% | 수식 (PER/적정PEG) 자동 | 읽기 |
| K | 섹터PER대비% | 현재 PER / 섹터 PER (%) 수식 자동 | **쓰기** |
| L | PER변화1Y | 최근 1년간 PER 변화량 | **쓰기** |
| M | 매출성장률% | 추정 매출성장률 | **쓰기** |
| N | 영업마진% | 추정 영업이익률(OPM) | **쓰기** |
| O | ROIC% | 계산된 ROIC 수치 | **쓰기** |
| P | FCF성장률% | 추정 FCF 성장률 | **쓰기** |
| Q | 성장괴리%p | 수식 (Implied성장률 - 매출성장률) 자동 | 읽기 |
| R | 한줄판단 | 투자 아이디어 및 요약 | **쓰기** |
| S | 기대현실적 | Y / 일부 / N (기대치의 현실성 판정) | **쓰기** |
| T | 비중판단 | 확대 / 유지 / 축소 / 청산고려 | **쓰기** |
| U | 매도트리거 | 매도 조건 및 한계점 | **쓰기** |
| V | 업데이트일 | 기록 갱신일 (YYYY-MM-DD) | **쓰기** |
| W | 애널목표가 | 리포트에서 추출한 증권사 목표 주가 | **쓰기** |
| X | 투자의견 | 리포트 투자의견 (예: Buy, Hold) | **쓰기** |
| Y | 업사이드% | 목표가 대비 상승 여력 (%) | **쓰기** |

- **보조 셀 (수식용)**: X1: "price", X2: "marketcap", X3: "pe", X4: "pb", Y1: "KRX:" (한국 주식 GOOGLEFINANCE용), C2: 적정PEG 기준값 (기본 2)
- **종목 목록 읽기 규칙**: 상태가 "보유" 또는 "관심"인 행만 필터링하여 스캔합니다. (예: `🔬 기업분석!A5:D35`)

### 2. 📐 "밸류계산" 탭 (종목별 상세 역산 데이터)
분석 대상 종목의 세부 밸류에이션 역산 결과가 기록되며, 매 분석 시점에 덮어씌워집니다.

| 셀 | 항목 | 소스 / 설명 |
| :---: | :--- | :--- |
| **A3** | 종목명 | 자동으로 주입 |
| **B3** | 티커 | 자동으로 주입 |
| **C3** | 분석일 | 자동으로 주입 |
| **B5** | WACC(%) | 할인율 (기본값 10) |
| **B6** | 요구수익률r(%) | 투자자 목표 수익률 (기본값 10) |
| **B7** | 영구성장률g(%) | 영구성장률 (기본값 3) |
| **B8** | 법인세율(%) | 유효세율 (미국: 21, 한국: 22 등) |
| **B12** | 시가총액(억) | DART 또는 yfinance 연동값 |
| **B13** | 순부채(억) | 재무제표 추출값 (단기+장기차입금 - 현금) |
| **B14** | FCF(억) | 재무제표 추출값 (영업CF - CAPEX) |
| **B20** | EBIT(억) | 재무제표 추출값 (영업이익) |
| **B27** | PBR | PBR 수치 |
| **B36** | 청산가치(억) | 자본총계 (Book Value) |
| **B37** | 투자자본(억) | 투하자본 (자본총계 + 순부채) |

- **자동 계산 셀 (덮어쓰기 금지)**: B15(EV = B12 + B13), B17(Implied g), B21(NOPAT = B20 * (1 - B8/100)), B22(EV/NOPAT), B24(Implied ROIC), B28(Implied ROE), B31(No Growth Value), B33(성장가치 비중%), B38(연간 초과수익), B40(Implied CAP)

### 3. Google Sheets 연동 주요 규칙 (오류 방지)
- **`&` 기호 사용 금지**: Google Sheets API 호출 및 텍스트 렌더링 중 오류를 예방하기 위해, S&P500 등은 반드시 `SP500`과 같이 `&`를 제외하여 가공/입력합니다.
- **한글 분할 전송**: 한글 텍스트 전송 시 API 제한(시간 초과) 방지를 위해, 5행 이하의 단위로 나누어 순차적으로 업데이트합니다.
- **티커 포맷**: 한국 주식은 반드시 6자리 스트링(예: `000660`)을 그대로 유지하며(엑셀 자동 변환으로 0이 누락되는 현상 방지), 미국 주식은 대문자 영문(예: `NVDA`)으로 포맷합니다.

### 4. 🏢 "industry_context.json" 구조 및 규격 (산업 맥락 데이터)
각 종목의 산업적 배경 가정이 기록되며, 로컬의 `data/valuation/{ticker}/normalized/industry_context.json` 경로에 파일로 저장 및 관리됩니다. AI가 산업 분석을 하거나 JSON을 주고받을 때 반드시 아래 스키마를 준수해야 합니다.

| 키 (Key) | 타입 | 설명 | 단위 |
| :--- | :--- | :--- | :---: |
| `tam_current` | number \| null | 현재 글로벌 TAM (시장규모) | 미국: 10억 달러, 한국: 조 원 |
| `tam_5yr` | number \| null | 5년 뒤 예상 글로벌 TAM | 미국: 10억 달러, 한국: 조 원 |
| `tam_cagr` | number \| null | TAM 연평균 성장률 | % |
| `market_share_current` | number \| null | 현재 시장 점유율 | % |
| `peer_per` | number \| null | 글로벌 Peer(경쟁사) 평균 PER | 배 |
| `normal_per` | number \| null | 역사적 평균 PER (적정 PER 멀티플) | 배 |
| `wacc` | number \| null | 할인율 (WACC) | % |
| `competitive_note` | string | 경쟁 우위(Moat), 리스크 및 분석 요약 메모 | 텍스트 |

- **주의 사항**:
  - `tam_current`와 `tam_5yr`는 통화와 종목 국적에 따라 단위가 달라집니다. (미국 주식은 10억 달러, 한국 주식은 조 원 단위)
  - LLM이 이 파일을 생성하거나 수정할 때는 위 테이블의 8가지 필수 키를 모두 포함해야 하며, 값이 없는 필드는 `null`로 지정합니다.

### 5. 📄 "report_context/{ticker}.json" 구조 및 규격 (리포트 파싱 데이터)
각 종목의 외부 증권사/애널리스트 리포트를 파싱한 데이터가 기록되며, 로컬의 `data/report_context/{ticker}.json` 경로에 파일로 저장됩니다.

| 키 (Key) | 타입 | 설명 | 단위 |
| :--- | :--- | :--- | :---: |
| `target_price` | number \| null | 애널리스트 목표 주가 | 원/달러 |
| `investment_opinion` | string | 투자의견 (예: Buy, Hold) | 텍스트 |
| `metrics.peer_target_per` | number \| null | 리포트에 제시된 기준 PER | 배 |
| `summary` | string | 리포트 핵심 요약 및 투자 아이디어 | 텍스트 |

- **우선순위**: K열(섹터PER대비%) 계산 시, `report_context`의 `peer_target_per`가 `industry_context.json`의 `peer_per`보다 **우선적으로 적용**되어 수식이 업데이트됩니다.

---

## 전체 파이프라인 개념 흐름

스프레드시트에서 종목을 읽어 분석을 실행하고 시트에 업데이트하는 파이프라인의 핵심 흐름입니다.

1. **`sheet_reader.py`**: "기업분석" 탭에서 분석할 종목(보유 및 관심 상태)의 목록 및 행 번호를 읽어옵니다.
2. **`dart_collector.py`** (한국): 한국 주식의 경우 corp_code 매핑을 통해 DART에서 다개년 재무제표 원천 JSON을 수집합니다.
3. **`industry_researcher.py`**: 수동/자동 수집을 기반으로 TAM, CAGR, Peer 멀티플 등 산업적 배경 데이터를 취합합니다.
4. **`llm_extractor.py`**: Claude API 등을 활용하여 수집된 재무 공시 원문 텍스트에서 핵심 지표(FCF, 순부채, 자본총계 등)를 정합성(FCF = 영업활동CF - CAPEX) 교차검증을 거쳐 추출합니다.
5. **`valuation_calculator.py`**: 추출 및 로드된 데이터셋을 통해 5가지 주요 가치평가 역산(Reverse DCF, Implied ROIC, ROE, Value Attribution, CAP, TAM 점유율)을 수행합니다.
6. **`sheet_updater.py`**: 계산 완료된 종합 요약 지표를 "기업분석" 탭의 H~V 열에 업데이트하고, 각 종목별 세부 계산 내역을 "밸류계산" 탭에 덮어써서 시트를 실시간 동기화합니다.

---

## 주요 파일

- `valuation_app/dashboard.py`: Streamlit 화면. 탭 구성, 초보자 설명, 출처 패널, 공식 표시가 여기에 있습니다.
- `valuation_app/models.py`: 데이터 모델. `MetricObservation`, `MarketSnapshot`, `AuditCheck` 등이 있습니다.
- `valuation_app/repository.py`: seed JSON 로딩.
- `valuation_app/audit.py`: 공통 입력값과 검산.
- `valuation_app/calculations.py`: FCF, EV, NOPAT, ROIC 등 기본 계산.
- `valuation_app/reverse_dcf.py`: Reverse DCF와 필요 FCF 민감도.
- `valuation_app/value_attribution.py`: 현재 수익력 가치와 미래 기대 가치 분해.
- `valuation_app/margin_scenario.py`: 매출/마진 조합 시나리오.
- `valuation_app/roic_reinvestment.py`: ROIC, 경제적 이익, 재투자율, 주가 내포 미래 ROIC.
- `valuation_app/relative_valuation.py`: P/E, P/B, EV/Sales, EV/NOPAT 등 상대가치 렌즈.
- `valuation_app/cap_duration.py`: 초과수익 지속기간과 ROIC별 경제적 이익 PV.
- `valuation_app/risk_downside.py`: WACC/g 민감도, 마진/WACC 민감도, 베어/베이스/불 시나리오, 가치 동인 순위.
- `valuation_app/narrative_consistency.py`: 6대 핵심 사업 스토리와 연결 지표.
- `valuation_app/synthesis.py`: 여러 렌즈의 분석 결과를 모아 수렴/발산 지점 요약 및 체크리스트.
- `valuation_app/advanced_reverse.py`: PEG, TAM, 기대수익률 등 Advanced 역산 방법론.
- `data/valuation/009150/normalized/metrics.json`: 삼성전기 정규화 재무 seed.
- `data/valuation/009150/normalized/market.json`: 삼성전기 시장 데이터 seed.
- `tests/`: 계산과 데이터 로딩 회귀 테스트.
- `docs/superpowers/notes/2026-05-23-implied-valuation-conversation.md`: 사용자와의 설계 대화 기록.
- `docs/superpowers/specs/2026-05-24-samsung-electro-implied-valuation-design.md`: 큰 설계 방향.
- `PLANS.md`: 현재 진행 상태와 다음 작업 계획.
- `TROUBLESHOOTING.md`: 흔한 문제 해결법.

## 현재 구현된 렌즈

1. 검산: 재무/시장 데이터 출처와 계산값 점검.
2. Reverse DCF: 현재 EV가 요구하는 FCF와 WACC/g 민감도.
3. Value Attribution: 현재 수익력 가치와 미래 기대 가치 분해.
4. 매출/마진 시나리오: 필요 FCF를 만족시키는 매출 성장률과 영업이익률 조합.
5. ROIC: 현재 ROIC, 경제적 이익, 주가 내포 미래 ROIC, 필요 재투자율.
6. 상대가치: P/E, EPS 기준 P/E, P/B 내포 ROE, EV/Sales 필요 마진, EV/NOPAT.
7. CAP: 초과가치, 현재/정상화 경제적 이익, 단순 CAP, 할인 CAP, ROIC별 초과수익 PV.
8. Risk/Downside: WACC/g 민감도, 마진/WACC 민감도, 베어/베이스/불 시나리오, 가치 동인 순위.
9. Narrative Consistency: 핵심 사업 스토리와 재무 지표 연결.
10. Synthesis: 수렴/발산 종합 및 다음 분기 체크리스트.
11. Advanced 역산: 기대수익률 분해, PEG 역산, 점유율/TAM 버블 진단.

다음 큰 렌즈는 없으며, 다음 작업은 **데이터 파이프라인 (DART 수집 자동화 및 매핑 보조)**입니다.

## 데이터 원칙

- 공식 보고서와 시장 데이터는 구분합니다.
- 삼성전기 2025 순이익과 EPS는 2025 감사보고서 Note 23에서 보강했습니다.
- 현재 seed에는 시가총액 기준 P/E와 EPS 기준 P/E가 다릅니다. 이는 현재가, 주식수, 시가총액 기준 시점 또는 보통주/우선주 처리 차이일 수 있으므로 경고로 표시합니다.
- yfinance나 편의 데이터가 공식 공시와 충돌하면 공식 회사 자료를 우선합니다. 편의 데이터는 보조 검산 자료입니다.
- 숫자를 새로 넣을 때는 `metric_key`, `unit`, `period`, `source_method`, `report_year`, `report_code`, `statement_name`, `original_account_name`, `original_amount`, `confidence`, `note`를 가능한 한 채웁니다.
- 원문 단위가 천원, 백만원 등일 때 정규화 단위를 명시합니다.

## 데이터 검증 및 이상치 감지 (Audit)

앱 파이프라인(`valuation_app/audit.py` 및 `sheet_updater.py`)에는 자동 데이터 정합성 검증 로직이 포함되어 있습니다.

- **통화 단위 교차 검증 (`currency_unit_consistency`)**: 주식 정보의 통화(예: `USD`)와 재무 지표 단위가 다를 경우(예: 한국 주식인데 달러가 섞인 경우) 치명적 에러(`fail`)로 차단합니다.
- **현재 PER 이상치 검증 (`current_per_anomaly`)**:
  - PER < 0 : 적자 상태 경고 (`warning`)
  - PER > 300 : 극단적 초성장 멀티플 또는 EPS 단위 입력 에러 경고 (`warning`)
- **PER변화1Y 분석 (`_per_change_1y`)**: 실적(EPS) 급증으로 인해 멀티플이 압축되는 정상적인 상황(예: 팔란티어의 PER -399배 변화)에서, 시스템이 당황하지 않도록 "원인 분석 가이드 로그"를 콘솔에 상세히 출력합니다.

## UI 원칙

- 각 탭은 먼저 "이 렌즈가 답하는 질문"을 보여야 합니다.
- 공식은 숨기지 않되, 공식만 앞세우지 않습니다.
- `st.metric` 값에는 초보자가 바로 읽을 수 있는 단위가 있어야 합니다. 예: `149.0배`, `8.2%`, `2,438억원`.
- 민감도는 전형적인 valuation sensitivity table처럼 행/열이 명확해야 합니다.
- 결과가 `해 없음`, `데이터 필요`, `N/A`라면 왜 그런지 바로 옆에 설명합니다.
- 사용자가 질문한 내용은 앱 안의 설명으로 되돌려 넣습니다. 예: ROIC 탭의 "숫자 읽는 법", PER 데이터 보강.

## Git 주의

- 현재 작업 브랜치 예시는 `codex/samsung-electro-data-integrity`입니다.
- `.superpowers/`는 로컬 작업 흔적이므로 사용자가 명시하지 않으면 커밋하지 않습니다.
- 사용자 변경을 되돌리지 않습니다.
- 문서나 앱을 바꾼 뒤 테스트와 브라우저 확인을 하고 작게 커밋합니다.
