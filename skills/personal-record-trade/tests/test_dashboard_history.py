import sys
import os
# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
import pandas as pd
from valuation_app.models import MetricObservation
from valuation_app.dashboard import generate_history_dataframe, _get_attr_or_key

def test_get_attr_or_key():
    # 1. Pydantic 객체 검증
    obs = MetricObservation(
        metric_key="revenue",
        label="Revenue",
        value=1000.0,
        unit="KRW",
        period="2025A",
        source_method="rule",
        report_year="2025",
        statement_name="DART",
        original_account_name="매출액",
        original_amount=1000.0,
        confidence=1.0
    )
    assert _get_attr_or_key(obs, "metric_key") == "revenue"
    assert _get_attr_or_key(obs, "value") == 1000.0
    assert _get_attr_or_key(obs, "non_existent", "default") == "default"

    # 2. 딕셔너리 검증
    dct = {"metric_key": "operating_income", "value": 500.0}
    assert _get_attr_or_key(dct, "metric_key") == "operating_income"
    assert _get_attr_or_key(dct, "value") == 500.0
    assert _get_attr_or_key(dct, "non_existent", "default") == "default"


def test_generate_history_dataframe():
    # 모의(Mock) 관측치 데이터
    obs_list = [
        MetricObservation(
            metric_key="revenue",
            label="Revenue",
            value=200000000000.0,  # 2000억원
            unit="KRW",
            period="2024A",
            source_method="rule",
            report_year="2024",
            statement_name="DART",
            original_account_name="매출액",
            original_amount=200000000000.0,
            confidence=1.0
        ),
        # 딕셔너리 형태의 데이터가 포함된 경우도 대응 검증
        {
            "metric_key": "revenue",
            "label": "Revenue",
            "value": 300000000000.0,  # 3000억원
            "period": "2025A"
        },
        {
            "metric_key": "operating_income",
            "label": "Operating Income",
            "value": 50000000000.0,  # 500억원
            "period": "2025A"
        }
    ]

    # 원화(KRW) 기준 변환 검증 (1억 원 단위로 나누어야 함)
    df, cols, is_usd, divider = generate_history_dataframe(obs_list, "KRW")
    
    assert df is not None
    assert "2024A" in cols
    assert "2025A" in cols
    assert not is_usd
    assert divider == 100_000_000 # 1억
    
    # 변환된 값 포맷 검증
    assert df.loc["Revenue", "2024A"] == "2,000.0"
    assert df.loc["Revenue", "2025A"] == "3,000.0"
    assert df.loc["Operating Income", "2025A"] == "500.0"
    assert df.loc["Operating Income", "2024A"] == "-" # 결측치 처리
