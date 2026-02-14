from __future__ import annotations

import argparse
import time
from pathlib import Path

from .estimator import estimate_many


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


def run_once(funds_path: Path, out_path: Path, min_coverage: float) -> None:
    codes = load_fund_codes(funds_path)
    estimates = estimate_many(codes, min_coverage=min_coverage)
    rows = [
        "\t".join(
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
        for e in estimates
    ]
    append_results(out_path, rows)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="场外基金实时估值（每1分钟刷新）")
    p.add_argument("--funds-file", default="funds_list.txt", help="基金代码列表txt，每行一个")
    p.add_argument("--output-file", default="valuation_output.txt", help="估值输出txt（追加写入）")
    p.add_argument("--interval-seconds", type=int, default=60, help="刷新周期（默认固定60秒）")
    p.add_argument("--min-coverage", type=float, default=35.0, help="持仓估值最小覆盖率")
    p.add_argument("--once", action="store_true", help="只执行一次，便于联调")
    return p


def main() -> None:
    args = build_parser().parse_args()
    interval = 60 if args.interval_seconds != 60 else args.interval_seconds
    funds_path = Path(args.funds_file)
    out_path = Path(args.output_file)

    while True:
        run_once(funds_path, out_path, min_coverage=args.min_coverage)
        if args.once:
            break
        time.sleep(interval)


if __name__ == "__main__":
    main()
