# 삼성전기 시장내포 가치분석 도구 설계

작성일: 2026-05-24  
대상 종목: 삼성전기, KRX `009150`  
승인된 방향: B안, 앱 내부 감사 데이터층 중심

## 1. 목적

이 도구는 현재 주가가 암묵적으로 요구하는 성장률, 현금흐름, ROIC, 마진, 경쟁우위 기간을 여러 방법으로 역산하고, 그 가정이 현실적인지 사용자가 차근차근 판단하도록 돕는다.

핵심 목표는 “정답 가격”을 제시하는 것이 아니다. 사용자가 다음 질문에 스스로 답할 수 있게 만드는 것이다.

- 현재 주가는 어떤 미래를 가격에 반영하고 있는가?
- 그 미래를 만들려면 매출, 마진, FCF, ROIC가 어느 정도여야 하는가?
- 그 가정은 과거 실적, 최근 분기, 산업 구조, 경쟁우위와 맞는가?
- 어떤 가정이 틀리면 주가 하락 위험이 커지는가?

## 2. 설계 원칙

1. 결론보다 계산 과정을 먼저 보여준다.
2. 모든 핵심 숫자는 출처, 계산식, 사용처를 함께 가진다.
3. LLM은 최종 판단자가 아니라 재무제표 계정명 해석 보조자다.
4. DART 원문, 시장 데이터, 수동 수정값, 계산값을 구분한다.
5. 하나의 모형을 믿지 않고 여러 렌즈의 결론이 수렴하는지 본다.
6. 초보자 모드와 고급 모드를 함께 둔다.
7. 삼성전기 한 종목으로 먼저 깊게 검증한 뒤 다른 종목으로 확장한다.

## 3. 범위

### 포함

- 삼성전기 연간 재무제표 수집
- 삼성전기 최신 분기 재무제표 수집
- 시장 데이터 수집: 주가, 주식수, 시가총액, EV 계산 입력
- DART 원문 보관
- LLM 기반 계정과목 매핑
- 계산값 검산
- 출처 및 감사 로그 표시
- 다중 가치평가 렌즈:
  - Source Integrity
  - FCFF / Reverse DCF
  - Value Attribution
  - Margin and Revenue Scenario
  - ROIC / Reinvestment Quality
  - Relative Valuation
  - CAP / Moat Duration
  - Risk and Downside
  - Narrative Consistency
  - Synthesis
- 사용자가 추출값을 수동 수정하고 수정 사유를 남기는 기능
- Google Sheets 또는 Damodaran 엑셀 템플릿으로 선택적 내보내기

### 제외

- 처음부터 모든 국내 종목을 지원하지 않는다.
- 처음부터 해외주식 SEC, GuruFocus, 회사채 스프레드 자동화를 포함하지 않는다.
- 금융업 전용 가치평가 모델은 이번 범위에서 제외한다.
- 자동 매수/매도 추천이나 투자 자문 문구는 제공하지 않는다.

## 4. 시스템 구조

전체 구조는 다음 순서로 흐른다.

```text
DART 원문
시장 데이터
사용자 수동 입력
        ↓
데이터 정규화 및 LLM 계정 매핑
        ↓
검산 및 감사 로그
        ↓
공통 재무 입력값
        ↓
다중 가치평가 렌즈
        ↓
초보자 친화 설명 화면
        ↓
선택적 엑셀/Google Sheets 내보내기
```

## 5. 주요 컴포넌트

### 5.1 Data Collector

역할:

- OpenDART에서 삼성전기 보고서를 가져온다.
- 사업보고서와 최신 분기보고서를 구분한다.
- 원문 JSON을 변형하지 않고 저장한다.
- 시장 데이터에서 주가, 주식수, 시가총액, 현금, 부채 등 보조 데이터를 가져온다.

DART 보고서 코드:

- 사업보고서: `11011`
- 1분기보고서: `11013`
- 반기보고서: `11012`
- 3분기보고서: `11014`

### 5.2 Financial Statement Mapper

역할:

- DART 계정과목을 핵심 재무 지표 후보로 매핑한다.
- 먼저 규칙 기반 매핑을 적용한다.
- 애매한 계정명이나 회사별 표현 차이는 LLM으로 해석한다.
- LLM 결과는 숫자만 반환하지 않고 근거를 함께 반환한다.

필수 반환 항목:

- metric key
- normalized value
- unit
- statement name
- original account name
- original amount
- report year
- report code
- fiscal period
- extraction method: `dart_direct`, `rule`, `llm`, `calculated`, `manual`
- confidence
- note

### 5.3 Audit Engine

역할:

- 핵심 계산식을 재계산한다.
- LLM 추출값과 계산값이 맞는지 확인한다.
- 이상치와 누락값을 표시한다.
- 사용자가 결론을 보기 전에 데이터 신뢰도를 판단하게 한다.

기본 검산:

```text
FCF = 영업활동현금흐름 - CAPEX
순부채 = 단기차입금 + 장기차입금 - 현금및현금성자산
EV = 시가총액 + 순부채 + 비지배지분 - 비영업자산
NOPAT = 영업이익 × (1 - 세율)
투하자본 = 자본총계 + 순부채
ROIC = NOPAT / 투하자본
```

검산 결과 상태:

- `pass`: 허용 오차 안에서 일치
- `warning`: 값은 있으나 계정 매핑 또는 단위 확인 필요
- `fail`: 계산 불일치 또는 필수 입력 누락
- `manual_override`: 사용자가 값을 수정함

### 5.4 Common Valuation Inputs

각 가치평가 렌즈는 같은 공통 입력값을 공유한다.

필수 입력:

- valuation date
- price
- shares outstanding
- market cap
- total debt
- cash and marketable securities
- net debt
- enterprise value
- revenue
- operating income
- EBIT
- tax rate
- NOPAT
- operating cash flow
- capex
- FCF
- equity
- invested capital
- ROIC
- latest quarter revenue
- latest quarter operating profit

각 입력값은 출처 추적이 가능해야 한다.

### 5.5 Valuation Lens Engine

각 렌즈는 독립된 질문, 공식, 입력값, 결과, 해석을 가진다.

#### Lens 1. Source Integrity

질문:

- 이 분석에 쓰이는 숫자는 어디서 왔는가?
- 연간 자료와 최신 분기 자료가 충돌하지 않는가?
- 자동 추출값 중 검산이 필요한 값은 무엇인가?

출력:

- 데이터 상태표
- 누락값
- 검산 통과 여부
- 수동 수정 기록

#### Lens 2. FCFF / Reverse DCF

질문:

- 현재 EV를 정당화하려면 어느 정도의 FCF가 필요한가?

핵심 공식:

```text
EV = FCF1 / (WACC - g)
필요 FCF1 = EV × (WACC - g)
```

초보자 설명:

- EV는 시장이 회사 전체에 붙인 가격이다.
- WACC와 영구성장률의 차이가 작을수록 같은 FCF의 가치가 커진다.
- 현재 FCF가 낮다면 시장은 정상화된 미래 FCF를 기대하고 있을 수 있다.

#### Lens 3. Value Attribution

질문:

- 현재 수익력만으로 설명되는 가치와 미래 기대 가치의 비중은 얼마인가?

핵심 공식:

```text
No Growth Value = NOPAT / WACC
Future Expectation Value = EV - No Growth Value
Future Expectation Ratio = Future Expectation Value / EV
```

#### Lens 4. Margin and Revenue Scenario

질문:

- 어떤 매출과 영업이익률 조합이면 시장 가격이 설명되는가?

핵심 공식:

```text
Normalized FCF = Revenue × Operating Margin × (1 - Tax Rate) × FCF Conversion
```

출력:

- 매출 성장률별 필요 마진 테이블
- 마진별 필요 매출 테이블
- 최신 분기 run-rate와 비교

#### Lens 5. ROIC / Reinvestment Quality

질문:

- 필요한 성장은 좋은 자본수익률로 만들어지는가?

핵심 공식:

```text
ROIC = NOPAT / Invested Capital
Reinvestment Rate = g / ROIC
```

#### Lens 6. Relative Valuation

질문:

- 시장은 삼성전기를 유사 기업 대비 어떤 프리미엄 또는 할인으로 보고 있는가?

포함 지표:

- P/E
- P/B
- EV/EBIT
- EV/Sales
- EV/FCF
- PEG

상대가치는 보조 렌즈이며 단독 결론으로 사용하지 않는다.

#### Lens 7. CAP / Moat Duration

질문:

- 초과수익이 몇 년 지속되어야 현재 가격이 설명되는가?

핵심 공식:

```text
Economic Profit = (ROIC - WACC) × Invested Capital
Excess Value = EV - No Growth Value
CAP ≈ Excess Value / Present Value of Annual Economic Profit
```

#### Lens 8. Risk and Downside

질문:

- 성장률, 마진, WACC, ROIC가 기대에 못 미치면 가치가 얼마나 흔들리는가?

출력:

- 민감도 테이블
- 베어/베이스/불 시나리오
- 가장 큰 가치 동인 순위

#### Lens 9. Narrative Consistency

질문:

- AI 서버, MLCC, FC-BGA, 실리콘 캐패시터, 전장 부품 스토리가 숫자와 맞는가?

출력:

- 스토리별 필요한 숫자
- 확인해야 할 다음 지표
- 분기 실적에서 추적할 항목

#### Lens 10. Synthesis

질문:

- 어떤 렌즈들이 같은 결론으로 모이는가?
- 어떤 렌즈들이 충돌하는가?
- 다음 분기에서 무엇을 확인해야 하는가?

출력:

- 수렴/발산 요약
- 핵심 가정 3개
- 주가에 가장 민감한 변수
- 다음 업데이트 체크리스트

## 6. 화면 설계

### 6.1 전체 내비게이션

좌측 또는 상단에 렌즈 진행 바를 둔다.

```text
1 출처검증 → 2 Reverse DCF → 3 현재/미래 가치 → 4 마진/매출
→ 5 ROIC → 6 상대가치 → 7 CAP → 8 리스크 → 9 스토리 → 10 종합
```

현재 위치, 완료된 렌즈, 아직 보지 않은 렌즈가 시각적으로 구분되어야 한다.

### 6.2 각 렌즈 화면 공통 구조

각 렌즈는 같은 구조를 따른다.

1. 이 렌즈가 답하려는 질문
2. 사용한 공식
3. 공식에 들어간 입력값과 출처
4. 계산 과정
5. 결과
6. 초보자용 해석
7. 고급 세부사항
8. 다음 렌즈로 넘어가기 전 확인 질문

### 6.3 입력값 표시 방식

입력값에는 네 가지 배지를 붙인다.

- `DART`: 공식 보고서에서 직접 추출
- `CALC`: 공식으로 계산
- `MARKET`: 시장 데이터에서 가져옴
- `MANUAL`: 사용자가 수정

사용자가 입력값을 클릭하면 다음을 보여준다.

- 원문 보고서
- 원문 계정명
- 원문 금액
- 단위 변환
- 계산식
- 이 값이 쓰인 렌즈 목록

## 7. 데이터 저장 모델

초기 구현은 가벼운 로컬 저장소를 사용한다. 저장 형식은 JSON 또는 SQLite 중 하나로 시작할 수 있다. 첫 구현에서는 사람이 읽기 쉬운 JSON 파일을 우선한다.

권장 파일 구조:

```text
data/
  raw/
    dart/009150/2025-11011.json
    dart/009150/2026-11013.json
    market/009150-latest.json
  normalized/
    009150-metrics.json
  audit/
    009150-audit-log.json
  scenarios/
    009150-user-assumptions.json
```

주요 객체:

- `RawReport`
- `MetricObservation`
- `AuditCheck`
- `ValuationInput`
- `ValuationLensResult`
- `UserOverride`

## 8. 오류 처리

### DART 수집 실패

- 에러 메시지와 요청 정보를 표시한다.
- 이전에 저장된 원문이 있으면 “이전 데이터 사용” 상태로 표시한다.
- 사용자가 수동으로 값을 입력할 수 있게 한다.

### LLM 추출 실패

- 규칙 기반 매핑 결과만 먼저 보여준다.
- 누락된 계정을 사용자가 선택하거나 입력할 수 있게 한다.
- LLM 실패는 가치평가 실행 전체를 막지 않는다.

### 검산 불일치

- 결과 화면으로 넘어가기 전에 경고를 보여준다.
- 불일치 항목은 값, 공식, 원천 계정 후보를 함께 표시한다.
- 사용자가 자동값, 계산값, 수동값 중 하나를 선택할 수 있다.

### 시장 데이터 기준일 문제

- 현재가, 전일종가, 거래일을 표시한다.
- 주말 또는 휴장일에는 “마지막 거래일 기준”으로 표시한다.

## 9. 보안 및 설정

환경변수 또는 설정 파일로 관리할 값:

- DART API key
- LLM API key
- Google Sheets credential path
- Google Sheets document id
- 시장 데이터 제공자 설정

금지:

- 코드 안에 API key를 직접 적지 않는다.
- 코드 안에 특정 Google Sheet id를 고정하지 않는다.
- LLM 프롬프트에 불필요한 개인 정보나 인증 정보를 넣지 않는다.

## 10. 테스트 전략

### 단위 테스트

- FCF 계산
- 순부채 계산
- EV 계산
- NOPAT 계산
- ROIC 계산
- Reverse DCF 필요 FCF 계산
- Value Attribution 계산
- CAP 계산

### 데이터 테스트

- DART 원문 샘플에서 핵심 계정 추출
- 단위 변환 확인
- 누락 계정 처리
- LLM 응답 스키마 검증
- 검산 불일치 탐지

### UI 테스트

- 초보자 모드에서 공식과 출처가 보이는지 확인
- 고급 모드에서 민감도 테이블이 보이는지 확인
- 모바일 화면에서 표와 설명이 겹치지 않는지 확인
- 입력값 클릭 시 출처 패널이 열리는지 확인

## 11. 구현 단계

### Phase 1. 삼성전기 데이터 무결성 화면

- DART 원문 또는 샘플 데이터 로딩
- 연간 및 최신 분기 입력값 표시
- FCF, 순부채, EV, ROIC 검산
- 출처 패널
- 수동 수정 기록

### Phase 2. FCFF / Reverse DCF 화면

- 현재 EV 기준 필요 FCF 계산
- WACC와 terminal growth 민감도 테이블
- 현재 FCF와 normalized FCF 비교
- 공식과 출처 표시

### Phase 3. Value Attribution 및 Scenario Lens

- No Growth Value 계산
- 미래 기대 가치 비중 계산
- 매출/마진 시나리오 테이블
- 최신 분기 run-rate 비교

### Phase 4. ROIC, Relative Valuation, CAP

- ROIC와 reinvestment rate 진단
- P/E, P/B, EV/EBIT, EV/Sales 렌즈
- CAP 진단
- 방법론 간 수렴/발산 표시

### Phase 5. Narrative Consistency 및 Synthesis

- 삼성전기 사업 스토리와 숫자 연결
- 다음 분기 추적 지표
- 종합 요약
- 선택적 Google Sheets 또는 엑셀 내보내기

## 12. 성공 기준

첫 버전은 다음 조건을 만족하면 성공이다.

- 사용자가 삼성전기의 핵심 입력값이 어디서 왔는지 확인할 수 있다.
- 사용자가 FCF, EV, NOPAT, ROIC 계산을 손으로 따라갈 수 있다.
- 현재 주가가 요구하는 FCF 또는 마진 수준이 시각적으로 보인다.
- 연간 실적과 최신 분기 실적이 나란히 비교된다.
- 자동 추출값과 수동 수정값이 구분된다.
- 여러 가치평가 렌즈가 같은 입력값을 공유한다.
- 결과는 투자 권유가 아니라 가정 검토와 질문 생성으로 표현된다.

## 13. 사용자 검토 포인트

구현 전 사용자가 확인할 사항:

- B안, 앱 내부 감사 데이터층 중심 구조가 맞는가?
- 삼성전기 한 종목으로 먼저 깊게 가는 범위가 맞는가?
- 데이터 무결성 화면을 첫 구현으로 삼는 순서가 맞는가?
- Google Sheets와 Damodaran 템플릿은 보조 내보내기로 두는 것이 맞는가?
- 초보자 모드에서 공식, 출처, 계산 과정을 항상 보이게 하는 방향이 맞는가?
