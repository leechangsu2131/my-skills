from __future__ import annotations


def get_samsung_electro_narratives() -> list[dict[str, str | list[str]]]:
    """삼성전기 핵심 사업 스토리와 밸류에이션 지표 간의 연결 고리를 반환합니다."""
    return [
        {
            "title": "AI 서버와 데이터센터용 고부가 MLCC 확대",
            "description": "AI 서버향 고용량/고내압 MLCC 수요가 폭발하며 믹스 개선 및 판가(ASP) 상승을 견인한다는 스토리입니다.",
            "metrics_to_watch": ["영업이익률 상승", "매출 성장률 가속", "투하자본이익률(ROIC) 개선"],
            "related_tabs": ["4. 매출·마진", "6. ROIC", "8. CAP"],
            "bull_signal": "서버용 비중 확대로 전사 영업이익률 15% 이상 돌파, CAP(초과수익 지속기간) 기대치 충족",
            "bear_signal": "IT 세트(PC/스마트폰) 부진을 상쇄하지 못하고 전체 가동률 및 마진 하락",
        },
        {
            "title": "FC-BGA (서버용 패키지 기판) 턴어라운드",
            "description": "수조 원을 투자한 베트남/국내 FC-BGA 라인이 주요 빅테크 고객사 확보와 함께 본격적인 이익 창출구로 변모한다는 스토리입니다.",
            "metrics_to_watch": ["투하자본 회수율(FCF 전환)", "기판 부문 매출/이익률", "자산회전율 향상"],
            "related_tabs": ["3. Reverse DCF", "6. ROIC", "9. 리스크"],
            "bull_signal": "대규모 CAPEX 종료 후 수율 안정화로 잉여현금흐름(FCF) 흑자 전환 및 ROIC 급등",
            "bear_signal": "PC용 기판 경쟁 심화 및 서버용 진입 지연으로 투하자본 대비 저조한 수익성 지속 (ROIC < WACC)",
        },
        {
            "title": "실리콘 캐패시터 등 차세대 부품 개화",
            "description": "AI 칩셋 고성능화에 따른 전력 효율 솔루션으로 실리콘 캐패시터와 글라스 기판 등의 신사업이 프리미엄 밸류에이션을 정당화한다는 스토리입니다.",
            "metrics_to_watch": ["미래 성장 기대치(Value Attribution)", "상대가치 멀티플(P/E, P/B 프리미엄)"],
            "related_tabs": ["4. Value Attribution", "7. 상대가치"],
            "bull_signal": "현재 수익력(Earnings Power) 대비 압도적으로 큰 미래 기대가치(Future Value) 비중이 유지됨",
            "bear_signal": "신규 폼팩터 도입이 늦어지거나 경쟁사에 밀리면서 P/E 등 상대가치 배수가 과거 평균 회귀",
        },
        {
            "title": "전장(Automotive) 부품 비중 확대",
            "description": "전기차/자율주행차 침투율 상승으로 차량당 탑재되는 고신뢰성 MLCC와 카메라 모듈이 폭발적으로 늘어난다는 스토리입니다.",
            "metrics_to_watch": ["전사 매출 성장률", "영업이익률 안정성(사이클 진폭 축소)"],
            "related_tabs": ["5. 매출·마진", "9. 리스크"],
            "bull_signal": "과거 스마트폰 사이클에 의존하던 실적 변동성이 줄어들고(베이스/불 시나리오), 안정적인 두 자릿수 성장 유지",
            "bear_signal": "전기차 캐즘(Chasm) 장기화로 전장 부품 단가 인하 압력 심화, 마진 하락 시나리오(베어) 현실화",
        },
        {
            "title": "카메라 모듈과 모바일 사이클 회복",
            "description": "온디바이스 AI 스마트폰 교체 수요와 갤럭시 S 시리즈 등 주요 플래그십 모델의 카메라 고사양화 수혜 스토리입니다.",
            "metrics_to_watch": ["단기 매출 및 FCF 창출력", "현금흐름 전환율"],
            "related_tabs": ["2. 입력값", "3. Reverse DCF"],
            "bull_signal": "현금 창출원(Cash Cow) 역할로 단기 FCF 서프라이즈 발생, 현재 요구 FCF(Reverse DCF) 거뜬히 달성",
            "bear_signal": "중화권 스마트폰 시장 침체 및 가격 경쟁 격화로 단기 수익성 악화",
        },
        {
            "title": "환율과 반도체/전자부품 매크로 사이클",
            "description": "원/달러 환율 상승(원화 약세)에 따른 수출 수혜와 글로벌 IT 부품 재고 축적(Restocking) 사이클의 타이밍에 관한 스토리입니다.",
            "metrics_to_watch": ["WACC (할인율/리스크 프리미엄)", "단기 영업이익률 변동"],
            "related_tabs": ["9. 리스크", "5. 매출·마진"],
            "bull_signal": "우호적 환율과 세트 업체의 재고 확충이 맞물리며 일시적 이익률 급등 (리스크 탭의 베이스/불 시나리오 상단)",
            "bear_signal": "매크로 침체 우려로 시장 WACC가 상승하여, 이익이 나더라도 할인율 인상으로 추정 EV 급감 (리스크 탭 민감도 표 악화)",
        },
    ]


def build_narrative_explanation() -> str:
    """내러티브 탭의 초보자용 안내 문구를 반환합니다."""
    return (
        "주식 시장은 종종 **'차가운 숫자'**보다 **'뜨거운 스토리(내러티브)'**에 의해 가격이 먼저 움직입니다. "
        "하지만 훌륭한 투자자는 그 스토리가 맞다면 재무제표의 **어떤 숫자가 반응해야 하는지**를 미리 알고 추적합니다.\n\n"
        "이 탭에서는 현재 삼성전기를 둘러싼 6가지 주요 사업 스토리를 요약하고, "
        "해당 스토리가 현실화되었을 때 앞서 우리가 살펴본 **가치평가 렌즈들의 어떤 지표가 좋아지거나 나빠져야 하는지**를 연결합니다."
    )
