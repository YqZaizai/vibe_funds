from realtime_fund_valuator.models import FundEstimate
from realtime_fund_valuator.runner import analyze_failure_reason, split_effective_and_failed


def _e(method: str, nav: float, detail: str) -> FundEstimate:
    return FundEstimate(
        fund_code="000001",
        timestamp="2026-01-01 00:00:00",
        last_nav=1.0,
        estimated_nav=nav,
        estimated_change_percent=0.0,
        method=method,
        coverage_percent=50.0,
        detail=detail,
    )


def test_split_effective_and_failed():
    records = [
        _e("holdings", 1.01, "ok"),
        _e("index", 1.02, "ok"),
        _e("unavailable", 0.0, "净值读取失败"),
    ]
    hits, fails = split_effective_and_failed(records)
    assert len(hits) == 2
    assert len(fails) == 1


def test_failure_reason_classification():
    assert analyze_failure_reason("净值读取失败: x") == "nav_fetch_failed"
    assert analyze_failure_reason("HTTP请求失败: y") == "upstream_http_failed"
    assert analyze_failure_reason("缺少可用持仓/指数行情") == "quote_or_index_unavailable"
    assert analyze_failure_reason("数据源异常: z") == "datasource_error"
    assert analyze_failure_reason("其他") == "other"
