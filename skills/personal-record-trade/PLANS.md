# PLANS.md

이 문서는 다른 IDE나 에이전트가 현재 작업을 바로 이어받기 위한 진행 계획입니다.

## 현재 목표

삼성전기 `009150`을 실제 사례로 삼아, 현재 주가에 담긴 시장의 기대를 여러 가치평가 렌즈로 역산하는 초보자 친화형 대시보드를 만든다.

핵심 제품 질문:

- 현재 가격이 어떤 미래 실적을 요구하는가?
- 그 요구조건은 매출, 마진, FCF, ROIC, 경쟁우위 기간으로 번역하면 어느 정도인가?
- 여러 모형의 결론이 서로 수렴하는가, 아니면 충돌하는가?
- 사용자가 공식과 출처를 따라가며 직접 판단할 수 있는가?

## 완료된 작업

- 삼성전기 분석용 `valuation_app` 패키지 생성.
- Pydantic 기반 데이터 모델 작성.
- 정규화 seed 데이터와 시장 데이터 로딩.
- FCF, EV, NOPAT, ROIC 검산 엔진.
- Streamlit 대시보드 기본 구조.
- 탭 1: 데이터 검산과 출처 패널.
- 탭 2: Reverse DCF와 필요 FCF 민감도.
- 탭 3: Value Attribution.
- 탭 4: 매출/마진 시나리오.
- 탭 6: ROIC/재투자 품질, 경제적 이익, 주가 내포 미래 ROIC 설명.
- 탭 7: 상대가치. P/E, EPS 기준 P/E, P/B 내포 ROE, EV/Sales 필요 마진, EV/NOPAT.
- 사용자 대화 기록 보존.
- PER 누락 문제 수정. 2025 감사보고서 Note 23 기반 순이익과 EPS 추가.

## 현재 의도된 분석 순서

1. 검산: 데이터가 믿을 만한가?
2. Reverse DCF: 현재 가격은 얼마의 FCF를 요구하는가?
3. Value Attribution: 현재 수익력과 미래 기대의 비중은?
4. 매출/마진: 어떤 영업 조건이 필요 FCF를 만드는가?
5. ROIC/재투자: 그 성장을 좋은 자본수익률로 만들 수 있는가?
6. 상대가치: 시장이 이 회사를 어떤 분모 대비 몇 배로 가격 매기는가?
7. CAP: 초과수익이 몇 년 지속되어야 현재 가격이 설명되는가?
8. Risk/Downside: 핵심 가정이 빗나가면 가치가 얼마나 흔들리는가?
9. Narrative Consistency: AI 서버, MLCC, FC-BGA, 전장, 사이클 회복 스토리가 숫자와 맞는가?
10. Synthesis: 수렴/발산 지점과 다음 분기 체크리스트.

## 다음 작업 1: CAP 렌즈

목적:

- 현재 가격이 요구하는 초과수익 지속기간을 보여준다.
- 사용자가 "높은 ROIC가 몇 년이나 유지되어야 하나"를 직관적으로 보게 한다.

권장 구현 파일:

- 새 파일: `valuation_app/cap_duration.py`
- 새 테스트: `tests/test_cap_duration.py`
- 수정: `valuation_app/dashboard.py`
- 수정: `README.md` 또는 이 문서

핵심 공식:

```text
Economic Profit = (ROIC - WACC) * Invested Capital
Excess Value = EV - No Growth Value
No Growth Value = NOPAT / WACC
CAP years = years needed for discounted economic profit to explain Excess Value
```

주의:

- 현재 ROIC가 WACC보다 낮으면 CAP 공식이 직관적으로 깨집니다. 이 경우 "현재 수익력 기준 초과수익이 없으므로, 시장은 미래 ROIC 회복을 먼저 요구한다"라고 설명해야 합니다.
- 단순 perpetuity 식만 쓰지 말고 5년, 10년, 15년, 20년 기간 표를 같이 보여주는 편이 초보자에게 낫습니다.

## 다음 작업 2: Risk/Downside 렌즈

목적:

- WACC, 정상화 영업이익률, 매출 성장률, FCF conversion이 조금 달라질 때 가치가 어떻게 움직이는지 보여준다.
- 민감도 표를 전형적인 valuation table처럼 보이게 한다.

권장 구현:

- 새 파일: `valuation_app/risk_downside.py`
- 새 테스트: `tests/test_risk_downside.py`
- 민감도 표는 행/열 레이블을 명확히 표시합니다.
- `현재 가격 대비 괴리율 = (추정 가치 - 현재 EV) / 현재 EV`를 같이 표시합니다.

## 다음 작업 3: Narrative Consistency

목적:

- 숫자를 삼성전기 사업 스토리와 연결한다.

초기 스토리 축:

- AI 서버와 데이터센터용 고부가 MLCC
- FC-BGA
- 실리콘 캐패시터
- 전장 부품
- 카메라 모듈과 모바일 사이클
- 환율과 반도체/전자부품 사이클

화면은 문장형이어도 됩니다. 다만 각 스토리는 확인해야 할 숫자와 연결되어야 합니다.

예:

```text
스토리: AI 서버용 고부가 MLCC 확대
확인할 숫자: 영업이익률, 매출 성장률, 재고/수주 신호, ROIC 개선
현재 앱에서 연결되는 렌즈: 매출/마진, ROIC, CAP
```

## 다음 작업 4: 데이터 파이프라인

목적:

- 현재 seed JSON을 넘어서 DART와 공식 IR 자료를 자동/반자동으로 수집한다.
- LLM은 최종 판단자가 아니라 계정 매핑 보조자로 사용한다.

원칙:

- raw DART를 보존합니다.
- 정규화 metric에는 반드시 source lineage를 붙입니다.
- 결정론적 규칙을 먼저 쓰고, 애매한 계정명만 LLM에 맡깁니다.
- Google Sheets 또는 Damodaran template export는 나중 단계입니다.

## 완료 기준

각 렌즈는 다음을 만족해야 합니다.

- 질문이 먼저 보인다.
- 선택한 모델의 이유가 보인다.
- 공식과 대입값이 보인다.
- 입력값 출처가 보인다.
- 결과를 초보자가 읽는 법이 보인다.
- 계산 실패나 `해 없음`이 나올 때 이유가 보인다.
- 테스트가 있다.
- 브라우저에서 Traceback 없이 표시된다.

