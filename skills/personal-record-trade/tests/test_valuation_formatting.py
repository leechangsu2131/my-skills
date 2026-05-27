from valuation_app.formatting import format_krw, format_ratio, source_label, status_label


def test_format_krw_uses_trillion_and_billion_units():
    assert format_krw(101_233_310_302_208) == "101.2조원"
    assert format_krw(913_331_178_230) == "9,133억원"
    assert format_krw(-424_015_036_416) == "-4,240억원"


def test_format_ratio():
    assert format_ratio(0.0819) == "8.2%"
    assert format_ratio(None) == "-"


def test_status_label():
    assert status_label("pass") == "통과"
    assert status_label("warning") == "확인 필요"
    assert status_label("fail") == "실패"


def test_source_label():
    assert source_label("dart_direct") == "DART"
    assert source_label("calculated") == "CALC"
    assert source_label("market") == "MARKET"
    assert source_label("manual") == "MANUAL"
