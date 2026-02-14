from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass(slots=True)
class Holding:
    code: str
    name: str
    weight_percent: float


@dataclass(slots=True)
class Quote:
    symbol: str
    change_percent: float


@dataclass(slots=True)
class FundEstimate:
    fund_code: str
    timestamp: str
    last_nav: float
    estimated_nav: float
    estimated_change_percent: float
    method: Literal["holdings", "index", "unavailable"]
    coverage_percent: float
    detail: str
