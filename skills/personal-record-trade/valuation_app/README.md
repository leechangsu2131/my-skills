# Valuation App

이 폴더(`valuation_app/`)는 종목의 내재 가치(Intrinsic Value)를 입체적으로 분석하고 시각화하는 **가치평가 대쉬보드 및 모델링 툴킷**입니다. 
Streamlit 기반의 웹 대쉬보드(`dashboard.py`)를 통해 직관적인 뷰를 제공합니다.

## 주요 기능 (Core Capabilities)
- **Streamlit 대쉬보드 (`dashboard.py`):** 로컬에서 `streamlit run dashboard.py` 명령어로 실행하여, 구글 시트에 연동된 종목들의 심층 가치평가 화면을 웹 UI로 띄웁니다.
- **고급 가치평가 모델 (Advanced Valuation Models):**
  - `reverse_dcf.py` / `advanced_reverse.py`: 현재 주가에 내포된 시장의 기대치(Implied Growth Rate)를 역산합니다.
  - `roic_reinvestment.py`: 기업의 자본수익률(ROIC)과 재투자율(Reinvestment Rate)을 기반으로 본질적인 성장을 진단합니다.
  - `margin_scenario.py`: 영업이익률 변동 시나리오에 따른 목표주가 민감도 분석을 수행합니다.
  - `relative_valuation.py`: 피어 그룹(경쟁사) 대비 상대 가치(PER, PBR 등)를 평가합니다.
- **리스크 및 서사 분석:**
  - `risk_downside.py`: 하방 리스크(Margin of Safety)를 시뮬레이션합니다.
  - `narrative_consistency.py`: 애널리스트의 '이야기(Narrative)'와 실제 '숫자(Numbers)'가 일치하는지 정량적으로 검증합니다.
  - `audit.py` / `synthesis.py`: 가치평가 과정의 오류를 감사하고, 종합적인 판단(Synthesis)을 도출합니다.

## 활용 방법 (Usage)
- 시각적인 대쉬보드 분석이 필요할 때 `streamlit run dashboard.py`를 실행하여 브라우저에서 접근합니다.
- 특정 밸류에이션 컴포넌트를 테스트하거나 개선할 때 해당 모듈(`.py`)을 개별적으로 수정 및 실행합니다.
