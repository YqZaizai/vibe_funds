from __future__ import annotations

import datetime as dt
from concurrent.futures import ThreadPoolExecutor, as_completed

from .data_sources import (
    DataSourceError,
    fetch_fund_holdings,
    fetch_fund_last_nav,
    fetch_realtime_quote_change_percent,
    fetch_tracking_index_candidates,
)
from .models import FundEstimate

HOLDINGS_SOURCE = "eastmoney_holdings+eastmoney_fundgz+sina_hq"
INDEX_SOURCE = "eastmoney_index_profile+eastmoney_fundgz+sina_hq"
UNAVAILABLE_SOURCE = "eastmoney_fundgz"


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
            source_api="eastmoney_fundgz",
        )

    holdings = fetch_fund_holdings(fund_code, topn=10)
    quote_map: dict[str, float] = {}
    holdings_snapshot: list[str] = []
    if holdings:
        quote_map = fetch_realtime_quote_change_percent(h.code for h in holdings)
        for h in holdings:
            if h.code in quote_map:
                chg = f"{quote_map[h.code]:+.3f}%"
            else:
                chg = "N/A"
            holdings_snapshot.append(
                f"{h.code}\t{h.name}\t{h.weight_percent:.2f}%\t{chg}"
            )

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
                source_api=HOLDINGS_SOURCE,
                holdings_snapshot=tuple(holdings_snapshot),
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
                source_api=INDEX_SOURCE,
                holdings_snapshot=tuple(holdings_snapshot),
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
        source_api=UNAVAILABLE_SOURCE,
        holdings_snapshot=tuple(holdings_snapshot),
    )


def _estimate_fund_safe(fund_code: str, min_coverage: float) -> FundEstimate:
    try:
        return estimate_fund(fund_code, min_coverage=min_coverage)
    except DataSourceError as exc:
        now = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return FundEstimate(
            fund_code=fund_code,
            timestamp=now,
            last_nav=0.0,
            estimated_nav=0.0,
            estimated_change_percent=0.0,
            method="unavailable",
            coverage_percent=0.0,
            detail=f"数据源异常: {exc}",
            source_api="unknown",
        )


def estimate_many(
    fund_codes: list[str],
    min_coverage: float = 35.0,
    max_workers: int = 8,
) -> list[FundEstimate]:
    if not fund_codes:
        return []

    workers = max(1, min(max_workers, len(fund_codes)))
    results_by_code: dict[str, FundEstimate] = {}

    with ThreadPoolExecutor(max_workers=workers) as executor:
        future_map = {
            executor.submit(_estimate_fund_safe, code, min_coverage): code
            for code in fund_codes
        }
        for future in as_completed(future_map):
            code = future_map[future]
            results_by_code[code] = future.result()

    return [results_by_code[code] for code in fund_codes]
