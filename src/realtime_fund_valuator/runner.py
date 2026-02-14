from __future__ import annotations

import argparse
import time
from collections import Counter
from pathlib import Path

from .data_sources import configure_proxy
from .estimator import estimate_many
from .models import FundEstimate


def load_fund_codes(path: Path) -> list[str]:
    return [
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]


def append_results(path: Path, rows: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        for row in rows:
            f.write(row + "\n")


def _format_record(e: FundEstimate) -> str:
    return "\t".join(
        [
            e.timestamp,
            e.fund_code,
            f"{e.last_nav:.4f}",
            f"{e.estimated_nav:.4f}",
            f"{e.estimated_change_percent:.3f}%",
            e.method,
            f"coverage={e.coverage_percent:.2f}%",
            e.detail,
        ]
    )


def _format_holding_rows(e: FundEstimate) -> list[str]:
    if not e.holdings_snapshot:
        return [f"{e.timestamp}	{e.fund_code}	-	-	-	N/A	no_holdings"]

    rows: list[str] = []
    for item in e.holdings_snapshot:
        code, name, weight, change = item.split("\t")
        rows.append(
            f"{e.timestamp}\t{e.fund_code}\t{code}\t{name}\t{weight}\t{change}\t{e.method}"
        )
    return rows


def analyze_failure_reason(detail: str) -> str:
    if "净值读取失败" in detail:
        return "nav_fetch_failed"
    if "HTTP请求失败" in detail:
        return "upstream_http_failed"
    if "缺少可用持仓/指数行情" in detail:
        return "quote_or_index_unavailable"
    if "数据源异常" in detail:
        return "datasource_error"
    return "other"


def split_effective_and_failed(estimates: list[FundEstimate]) -> tuple[list[FundEstimate], list[FundEstimate]]:
    hits: list[FundEstimate] = []
    fails: list[FundEstimate] = []
    for e in estimates:
        if e.method in {"holdings", "index"} and e.estimated_nav > 0:
            hits.append(e)
        else:
            fails.append(e)
    return hits, fails


def build_fail_analysis_rows(fails: list[FundEstimate]) -> list[str]:
    c = Counter(analyze_failure_reason(x.detail) for x in fails)
    return [f"{k}\t{v}" for k, v in sorted(c.items(), key=lambda x: x[0])]


def run_once(
    funds_path: Path,
    output_file: Path,
    hit_output_file: Path,
    miss_output_file: Path,
    miss_analysis_file: Path,
    holdings_output_file: Path,
    min_coverage: float,
) -> None:
    codes = load_fund_codes(funds_path)
    estimates = estimate_many(codes, min_coverage=min_coverage)
    hits, fails = split_effective_and_failed(estimates)

    append_results(output_file, [_format_record(e) for e in estimates])
    append_results(hit_output_file, [_format_record(e) for e in hits])
    append_results(miss_output_file, [_format_record(e) for e in fails])

    holding_rows: list[str] = []
    for e in estimates:
        holding_rows.extend(_format_holding_rows(e))
    append_results(holdings_output_file, holding_rows)

    ts = estimates[0].timestamp if estimates else time.strftime("%Y-%m-%d %H:%M:%S")
    analysis_header = [f"{ts}\ttotal={len(estimates)}\thit={len(hits)}\tfail={len(fails)}"]
    append_results(miss_analysis_file, analysis_header + build_fail_analysis_rows(fails) + ["-"])


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="场外基金实时估值（每1分钟刷新）")
    p.add_argument("--funds-file", default="funds_list.txt", help="基金代码列表txt，每行一个")
    p.add_argument("--output-file", default="valuation_output.txt", help="全部估值结果txt（追加）")
    p.add_argument("--hit-output-file", default="valuation_hits.txt", help="有效命中结果txt（追加）")
    p.add_argument("--miss-output-file", default="valuation_misses.txt", help="未命中结果txt（追加）")
    p.add_argument("--miss-analysis-file", default="valuation_miss_analysis.txt", help="未命中分析txt（追加）")
    p.add_argument("--holdings-output-file", default="valuation_holdings.txt", help="基金重仓股占比和涨跌明细txt（追加）")
    p.add_argument("--interval-seconds", type=int, default=60, help="刷新周期（固定60秒）")
    p.add_argument("--min-coverage", type=float, default=35.0, help="持仓估值最小覆盖率")
    p.add_argument("--proxy", default="", help="可选代理地址，例如 http://127.0.0.1:7890")
    p.add_argument("--once", action="store_true", help="只执行一次，便于联调")
    return p


def main() -> None:
    args = build_parser().parse_args()
    interval = 60 if args.interval_seconds != 60 else args.interval_seconds
    configure_proxy(args.proxy.strip() or None)

    while True:
        run_once(
            funds_path=Path(args.funds_file),
            output_file=Path(args.output_file),
            hit_output_file=Path(args.hit_output_file),
            miss_output_file=Path(args.miss_output_file),
            miss_analysis_file=Path(args.miss_analysis_file),
            holdings_output_file=Path(args.holdings_output_file),
            min_coverage=args.min_coverage,
        )
        if args.once:
            break
        time.sleep(interval)


if __name__ == "__main__":
    main()
