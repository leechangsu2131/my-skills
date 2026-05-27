import pytest
from pykrx import bond
import pandas as pd
import numpy as np
# pylint: disable-all
# flake8: noqa


class TestBondOtcTreasuryYiledByTicker:
    @pytest.mark.vcr
    def test_holiday(self):
        df = bond.get_otc_treasury_yields("20220202")
        assert len(df) != 0
        assert isinstance(df, pd.DataFrame)

    @pytest.mark.vcr
    def test_business_day(self):
        df = bond.get_otc_treasury_yields("20220204")
        #              수익률   대비
        # 채권종류
        # 국고채 1년    1.467  0.015
        # 국고채 2년    1.995  0.026
        # 국고채 3년    2.194  0.036
        # 국고채 5년    2.418  0.045
        # 국고채 10년   2.619  0.053
        assert df.iloc[0, 0] == pytest.approx(1.467)
        assert df.iloc[1, 0] == pytest.approx(1.995)


class TestBondOtcTreasuryYiledByDate:
    @pytest.mark.vcr
    def test_business_day(self):
        df = bond.get_otc_treasury_yields("20220104", "20220203", "국고채1년")
        assert len(df) != 0
        assert isinstance(df, pd.DataFrame)
