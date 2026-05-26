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
