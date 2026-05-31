"""
tests/test_sheet_updater.py
──────────────────────────
sheet_updater.py의 순수 함수 단위 테스트
(Google API 호출 없이 비즈니스 로직만 검증)
"""

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from unittest.mock import MagicMock, patch
from valuation_app.models import MetricObservation

# 테스트 대상 함수 임포트
from sheet_updater import (
    _sanitize_text,
    _to_eok,
    _safe_ratio,
    _yoy_growth,
    _find_ticker_row,
    SKIP_TICKERS,
)


class TestSanitizeText:
    def test_removes_ampersand(self):
        assert _sanitize_text("S&P500") == "SandP500"

    def test_handles_none(self):
        assert _sanitize_text(None) == ""

    def test_handles_number(self):
        assert _sanitize_text(123) == "123"

    def test_plain_text_unchanged(self):
        assert _sanitize_text("삼성전기") == "삼성전기"


class TestToEok:
    def test_krw_conversion(self):
        # 1조원 = 10000억
        assert _to_eok(1_000_000_000_000, "KRW") == 10000.0

    def test_usd_conversion(self):
        # 10억 달러 = 10억/1억 = 10 (억 달러)
        assert _to_eok(1_000_000_000, "USD") == 10.0

    def test_none_returns_empty(self):
        assert _to_eok(None) == ""

    def test_zero_returns_zero(self):
        assert _to_eok(0) == 0.0


class TestSafeRatio:
    def test_normal_division(self):
        assert _safe_ratio(100, 50) == 2.0

    def test_percentage(self):
        assert _safe_ratio(30, 100, pct=True) == 30.0

    def test_zero_denominator(self):
        assert _safe_ratio(100, 0) == ""

    def test_none_numerator(self):
        assert _safe_ratio(None, 100) == ""

    def test_none_denominator(self):
        assert _safe_ratio(100, None) == ""


class TestYoyGrowth:
    def _make_obs(self, metric_key, period, value):
        return MetricObservation(
            metric_key=metric_key,
            label=metric_key,
            value=value,
            unit="KRW",
            period=period,
            source_method="rule",
            confidence=1.0,
        )

    def test_positive_growth(self):
        obs = [
            self._make_obs("revenue", "2024A", 100),
            self._make_obs("revenue", "2025A", 120),
        ]
        result = _yoy_growth(obs, "revenue")
        assert result == 20.0

    def test_negative_growth(self):
        obs = [
            self._make_obs("revenue", "2024A", 100),
            self._make_obs("revenue", "2025A", 80),
        ]
        result = _yoy_growth(obs, "revenue")
        assert result == -20.0

    def test_single_year_returns_empty(self):
        obs = [self._make_obs("revenue", "2025A", 100)]
        assert _yoy_growth(obs, "revenue") == ""

    def test_no_matching_key(self):
        obs = [
            self._make_obs("fcf", "2024A", 100),
            self._make_obs("fcf", "2025A", 150),
        ]
        assert _yoy_growth(obs, "revenue") == ""

    def test_dict_observations(self):
        obs = [
            {"metric_key": "revenue", "period": "2024A", "value": 200},
            {"metric_key": "revenue", "period": "2025A", "value": 240},
        ]
        result = _yoy_growth(obs, "revenue")
        assert result == 20.0

    def test_uses_latest_two_years(self):
        obs = [
            self._make_obs("revenue", "2023A", 80),
            self._make_obs("revenue", "2024A", 100),
            self._make_obs("revenue", "2025A", 120),
        ]
        result = _yoy_growth(obs, "revenue")
        # Should use 2025 vs 2024: (120-100)/100 = 20%
        assert result == 20.0


class TestFindTickerRow:
    def test_exact_match(self):
        ws = MagicMock()
        ws.col_values.return_value = ["", "티커", "", "", "GOOG", "NVDA", "META"]
        assert _find_ticker_row(ws, "GOOG") == 5

    def test_korean_ticker_zero_stripped(self):
        """한국 주식 009150 → 시트에 9150으로 표기된 경우 대응"""
        ws = MagicMock()
        ws.col_values.return_value = ["", "티커", "", "", "9150"]
        assert _find_ticker_row(ws, "009150") == 5

    def test_not_found(self):
        ws = MagicMock()
        ws.col_values.return_value = ["", "티커", "", "", "GOOG"]
        assert _find_ticker_row(ws, "AAPL") is None


class TestSkipTickers:
    def test_etf_in_skip_list(self):
        assert "SOXX" in SKIP_TICKERS
        assert "QQQM" in SKIP_TICKERS
        assert "BTC" in SKIP_TICKERS

    def test_normal_ticker_not_in_skip(self):
        assert "NVDA" not in SKIP_TICKERS
        assert "009150" not in SKIP_TICKERS


class TestPerChange1Y:
    def _make_obs(self, metric_key, period, value):
        return MetricObservation(
            metric_key=metric_key,
            label=metric_key,
            value=value,
            unit="KRW",
            period=period,
            source_method="rule",
            confidence=1.0,
        )

    @patch("yfinance.Ticker")
    def test_per_change_calculation_success(self, mock_ticker):
        from sheet_updater import _per_change_1y
        
        # 1년 전 주가 모의 데이터
        mock_hist = MagicMock()
        mock_hist.empty = False
        mock_hist.iloc = [{"Close": 100.0}]
        mock_ticker.return_value.history.return_value = mock_hist
        
        market = {"price": 150.0}
        obs = [
            self._make_obs("eps", "2024A", 10.0),
            self._make_obs("eps", "2025A", 15.0),
        ]
        
        # 1년 전 PER = 100 / 10 = 10.0
        # 현재 PER = 150 / 15 = 10.0
        # 차이 = 10.0 - 10.0 = 0.0
        result = _per_change_1y("000660", market, obs)
        assert result == 0.0

    @patch("yfinance.Ticker")
    def test_per_change_calculation_negative(self, mock_ticker):
        from sheet_updater import _per_change_1y
        
        mock_hist = MagicMock()
        mock_hist.empty = False
        mock_hist.iloc = [{"Close": 100.0}]
        mock_ticker.return_value.history.return_value = mock_hist
        
        market = {"price": 120.0}
        obs = [
            self._make_obs("eps", "2024A", 10.0), # 1년 전 PER = 10.0
            self._make_obs("eps", "2025A", 15.0), # 현재 PER = 8.0
        ]
        
        result = _per_change_1y("000660", market, obs)
        assert result == -2.0
