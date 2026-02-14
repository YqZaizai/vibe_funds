from realtime_fund_valuator.data_sources import _parse_sina_change_percent, _to_sina_symbol


def test_to_sina_symbol():
    assert _to_sina_symbol("600000") == "sh600000"
    assert _to_sina_symbol("000001") == "sz000001"
    assert _to_sina_symbol("00700") == "hk00700"
    assert _to_sina_symbol("AAPL") == "usAAPL"


def test_parse_a_share_quote():
    fields = ["name", "open", "10.00", "10.50"]
    pct = _parse_sina_change_percent("sh600000", fields)
    assert round(pct, 3) == 5.0


def test_parse_hk_quote():
    fields = ["name", "", "", "200.0", "", "", "210.0"]
    pct = _parse_sina_change_percent("hk00700", fields)
    assert round(pct, 3) == 5.0
