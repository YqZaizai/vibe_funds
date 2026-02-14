from __future__ import annotations

import datetime as dt

from .data_sources import (
    DataSourceError,
    fetch_fund_holdings,
    fetch_fund_last_nav,
    fetch_realtime_quote_change_percent,
    fetch_tracking_index_candidates,
)
from .models import FundEstimate


def estimate_fund(fund_code: str, min_coverage: float = 35.0) -> FundEstimate:
    ts = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    try:
        last_nav, nav_date = fetch_fund_last_nav(fund_code)
    except Exception as exc:
        return FundEstimate(
            fund_code=fund_code,
            timestamp=ts,
            last_nav=0.0,
            estimated_nav=0.0,
            estimated_change_percent=0.0,
            method="unavailable",
            coverage_percent=0.0,
            detail=f"净值读取失败: {exc}",
        )

    holdings = fetch_fund_holdings(fund_code, topn=10)
    if holdings:
        quote_map = fetch_realtime_quote_change_percent(h.code for h in holdings)
        weighted_change = 0.0
        coverage = 0.0
        used = 0
        for h in holdings:
            if h.code in quote_map:
                w = h.weight_percent / 100.0
                weighted_change += w * (quote_map[h.code] / 100.0)
                coverage += h.weight_percent
                used += 1

        if coverage >= min_coverage:
            est_nav = last_nav * (1 + weighted_change)
            return FundEstimate(
                fund_code=fund_code,
                timestamp=ts,
                last_nav=last_nav,
                estimated_nav=est_nav,
                estimated_change_percent=(est_nav / last_nav - 1) * 100,
                method="holdings",
                coverage_percent=coverage,
                detail=f"基于前10大持仓估值，命中{used}/{len(holdings)}，净值日期{nav_date}",
            )

    # Fallback: index-driven estimate (useful for many QDII/index funds)
    idx_candidates = fetch_tracking_index_candidates(fund_code)
    if idx_candidates:
        idx_change = fetch_realtime_quote_change_percent(idx_candidates)
        if idx_change:
            avg_change = sum(idx_change.values()) / len(idx_change)
            est_nav = last_nav * (1 + avg_change / 100.0)
            return FundEstimate(
                fund_code=fund_code,
                timestamp=ts,
                last_nav=last_nav,
                estimated_nav=est_nav,
                estimated_change_percent=avg_change,
                method="index",
                coverage_percent=100.0,
                detail=f"基于跟踪指数估值（{','.join(idx_change.keys())}），净值日期{nav_date}",
            )

    return FundEstimate(
        fund_code=fund_code,
        timestamp=ts,
        last_nav=last_nav,
        estimated_nav=last_nav,
        estimated_change_percent=0.0,
        method="unavailable",
        coverage_percent=0.0,
        detail=f"缺少可用持仓/指数行情，净值日期{nav_date}",
    )


def estimate_many(fund_codes: list[str], min_coverage: float = 35.0) -> list[FundEstimate]:
    results: list[FundEstimate] = []
    for code in fund_codes:
        try:
            results.append(estimate_fund(code, min_coverage=min_coverage))
        except DataSourceError as exc:
            now = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            results.append(
                FundEstimate(
                    fund_code=code,
                    timestamp=now,
                    last_nav=0.0,
                    estimated_nav=0.0,
                    estimated_change_percent=0.0,
                    method="unavailable",
                    coverage_percent=0.0,
                    detail=f"数据源异常: {exc}",
                )
            )
    return results
