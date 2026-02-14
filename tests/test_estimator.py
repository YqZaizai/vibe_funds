import realtime_fund_valuator.estimator as estimator
from realtime_fund_valuator.models import FundEstimate


def test_estimate_many_keeps_input_order(monkeypatch):
    def fake_estimate_fund(code: str, min_coverage: float = 35.0) -> FundEstimate:
        return FundEstimate(
            fund_code=code,
            timestamp="2026-01-01 00:00:00",
            last_nav=1.0,
            estimated_nav=1.0,
            estimated_change_percent=0.0,
            method="unavailable",
            coverage_percent=0.0,
            detail="ok",
            source_api="mock",
        )

    monkeypatch.setattr(estimator, "estimate_fund", fake_estimate_fund)
    codes = ["000003", "000001", "000002"]
    out = estimator.estimate_many(codes, max_workers=3)
    assert [x.fund_code for x in out] == codes


def test_estimate_fund_nav_failure_has_source(monkeypatch):
    def boom(_: str):
        raise RuntimeError("boom")

    monkeypatch.setattr(estimator, "fetch_fund_last_nav", boom)
    out = estimator.estimate_fund("000001")
    assert out.method == "unavailable"
    assert out.source_api == "eastmoney_fundgz"
