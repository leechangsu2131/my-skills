from __future__ import annotations


def get_company_narratives(ticker: str) -> list[dict[str, str | list[str]]]:
    """종목코드(ticker)에 따른 핵심 사업 스토리와 밸류에이션 지표 간의 연결 고리를 반환합니다."""
    if ticker == "000660":
        return [
            {
                "title": "HBM(고대역폭 메모리) 시장 독점적 지위 유지",
                "description": "AI 서버향 HBM 수요 폭발이 전체 D램 믹스 개선 및 판가(ASP) 급등을 견인한다는 스토리입니다.",
                "metrics_to_watch": ["영업이익률 급상승", "매출 성장률 가속", "투하자본이익률(ROIC) 개선"],
                "related_tabs": ["4. 매출·마진", "6. ROIC", "8. CAP"],
                "bull_signal": "HBM 점유율 우위 유지로 전사 영업이익률 초격차 달성, CAP(초과수익 지속기간) 기대치 충족",
                "bear_signal": "경쟁사(삼성/마이크론)의 HBM 시장 본격 진입 및 단가 인하 경쟁으로 마진 훼손",
            },
            {
                "title": "NAND 사업부 턴어라운드 및 eSSD 수요 급증",
                "description": "AI 데이터센터의 전력 효율화를 위한 고용량 eSSD 수요 확대로 낸드 부문이 장기 적자에서 탈출한다는 스토리입니다.",
                "metrics_to_watch": ["투하자본 회수율(FCF 전환)", "낸드 부문 이익률"],
                "related_tabs": ["3. Reverse DCF", "6. ROIC"],
                "bull_signal": "솔리다임 시너지와 eSSD 고마진 달성으로 NAND 대규모 흑자 전환 및 FCF 급증",
                "bear_signal": "일반 소비자용 낸드 수요 부진 지속으로 수익성 회복 지연 (ROIC < WACC)",
            },
            {
                "title": "일반 D램(Legacy) 수요 회복 지연",
                "description": "PC 및 스마트폰 등 레거시 IT 세트 수요 침체로 일반 D램의 재고 소진이 지연되고 판가가 하락한다는 리스크 스토리입니다.",
                "metrics_to_watch": ["전사 매출 성장률", "재고자산회전율", "가동률"],
                "related_tabs": ["5. 매출·마진", "9. 리스크"],
                "bull_signal": "온디바이스 AI 탑재율 상승으로 스마트폰 교체 수요 발발, 레거시 D램 단가 반등 (베이스/불 시나리오 상단)",
                "bear_signal": "매크로 침체 장기화로 레거시 부문 적자 지속, HBM에서 번 이익을 갉아먹음 (베어 시나리오)",
            },
            {
                "title": "천문학적 CAPEX와 팹 인프라 투자",
                "description": "M15X, 용인 반도체 클러스터 등 막대한 인프라 투자가 잉여현금흐름(FCF)을 갉아먹지만 미래 패권을 좌우한다는 스토리입니다.",
                "metrics_to_watch": ["미래 성장 기대치(Value Attribution)", "단기 FCF 및 CAPEX 규모"],
                "related_tabs": ["3. Reverse DCF", "4. Value Attribution"],
                "bull_signal": "압도적인 현금 창출력으로 자체 조달 완료, 단기 FCF 서프라이즈로 시장 요구치(Reverse DCF) 상회",
                "bear_signal": "반도체 다운사이클과 대규모 투자가 겹치며 감가상각비 폭증, FCF 대규모 적자로 차입금 급증",
            },
            {
                "title": "매크로 침체 우려와 HBM 공급 과잉 리스크",
                "description": "빅테크들의 AI 인프라 투자가 주춤해지거나 HBM 공급이 수요를 초과할 때 밸류에이션이 급락한다는 내러티브입니다.",
                "metrics_to_watch": ["WACC (할인율)", "상대가치 멀티플(P/E, P/B 하락)"],
                "related_tabs": ["9. 리스크", "7. 상대가치"],
                "bull_signal": "현재 주가(Earnings Power) 대비 여전히 저평가된 밸류에이션 유지",
                "bear_signal": "피크아웃(Peak-out) 우려 확산으로 이익이 나더라도 멀티플 하락으로 주가 하방 압력 심화",
            }
        ]
        
    elif ticker == "009150":
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
            }
        ]
        
    # 기본(Fallback) 내러티브
    return [
        {
            "title": "핵심 캐시카우 사업의 지속가능성",
            "description": "회사의 주요 매출원이 성장을 유지하며 현금을 안정적으로 창출하는지 확인해야 합니다.",
            "metrics_to_watch": ["매출 성장률", "영업이익률", "현금흐름(FCF)"],
            "related_tabs": ["2. 입력값", "3. Reverse DCF", "5. 매출·마진"],
            "bull_signal": "핵심 사업의 점유율 확대 및 원가 절감으로 이익 레버리지 극대화",
            "bear_signal": "신규 진입자 등장이나 수요 둔화로 인한 판가 하락 및 마진 훼손",
        },
        {
            "title": "미래 성장 동력 확보 및 투하자본 효율성",
            "description": "기존 사업에서 번 돈(CAPEX)을 수익성 높은 신사업에 적절히 재투자하고 있는지 확인해야 합니다.",
            "metrics_to_watch": ["투하자본이익률(ROIC)", "CAPEX", "Value Attribution"],
            "related_tabs": ["4. Value Attribution", "6. ROIC", "8. CAP"],
            "bull_signal": "투하 자본 대비 압도적인 수익률을 기록하며 ROIC-WACC 스프레드 확대",
            "bear_signal": "무분별한 투자나 신사업 부진으로 ROIC가 WACC를 하회하며 가치 파괴 발생",
        }
    ]


def build_narrative_explanation(company_name: str) -> str:
    """내러티브 탭의 초보자용 안내 문구를 반환합니다."""
    return (
        f"주식 시장은 종종 **'차가운 숫자'**보다 **'뜨거운 스토리(내러티브)'**에 의해 가격이 먼저 움직입니다. "
        "하지만 훌륭한 투자자는 그 스토리가 맞다면 재무제표의 **어떤 숫자가 반응해야 하는지**를 미리 알고 추적합니다.\n\n"
        f"이 탭에서는 현재 {company_name}을(를) 둘러싼 주요 사업 스토리를 요약하고, "
        "해당 스토리가 현실화되었을 때 앞서 우리가 살펴본 **가치평가 렌즈들의 어떤 지표가 좋아지거나 나빠져야 하는지**를 연결합니다."
    )
