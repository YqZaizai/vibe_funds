from __future__ import annotations

import datetime as dt
import json
import re
from html import unescape
from typing import Iterable
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import ProxyHandler, Request, build_opener, install_opener, urlopen

from .models import Holding

REQUEST_TIMEOUT = 12
UA = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)


class DataSourceError(RuntimeError):
    pass


def configure_proxy(proxy_url: str | None) -> None:
    """Configure process-wide HTTP(S) proxy for urllib.

    Example: http://127.0.0.1:7890 or socks5://127.0.0.1:1080
    """
    if not proxy_url:
        return
    parsed = urlparse(proxy_url)
    if not parsed.scheme or not parsed.netloc:
        raise ValueError(f"无效代理地址: {proxy_url}")

    opener = build_opener()
    opener.add_handler(ProxyHandler({"http": proxy_url, "https": proxy_url}))
    install_opener(opener)


def _http_get(url: str, referer: str | None = None) -> str:
    headers = {"User-Agent": UA}
    if referer:
        headers["Referer"] = referer
    req = Request(url, headers=headers)
    try:
        with urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
            return resp.read().decode("utf-8", errors="ignore")
    except (HTTPError, URLError, TimeoutError) as exc:
        raise DataSourceError(f"HTTP请求失败: {url} -> {exc}") from exc


def fetch_fund_last_nav(fund_code: str) -> tuple[float, str]:
    url = f"https://fundgz.1234567.com.cn/js/{fund_code}.js"
    text = _http_get(url)
    m = re.search(r"jsonpgz\((\{.*\})\)", text)
    if not m:
        raise DataSourceError(f"无法解析基金净值数据: {fund_code}")
    payload = json.loads(m.group(1))
    last_nav = float(payload["dwjz"])
    date = payload.get("jzrq") or dt.date.today().isoformat()
    return last_nav, date


def fetch_fund_holdings(fund_code: str, topn: int = 10) -> list[Holding]:
    url = (
        "https://fundf10.eastmoney.com/FundArchivesDatas.aspx"
        f"?type=jjcc&code={fund_code}&topline={topn}&year=&month="
    )
    text = _http_get(url)

    m = re.search(r"content:\"(.*)\",arryear", text, flags=re.S)
    if not m:
        return []

    html = unescape(m.group(1)).replace("\\/", "/")
    rows = re.findall(r"<tr>(.*?)</tr>", html, flags=re.S)

    holdings: list[Holding] = []
    for row in rows:
        tds = re.findall(r"<td[^>]*>(.*?)</td>", row, flags=re.S)
        if len(tds) < 7:
            continue
        code = _clean_html_text(tds[1])
        name = _clean_html_text(tds[2])
        weight_text = _clean_html_text(tds[6]).replace("%", "")
        if not code:
            continue
        try:
            weight = float(weight_text)
        except ValueError:
            continue
        holdings.append(Holding(code=code, name=name, weight_percent=weight))
    return holdings


def _clean_html_text(s: str) -> str:
    s = re.sub(r"<[^>]+>", "", s)
    return unescape(s).strip()


def _to_sina_symbol(code: str) -> str | None:
    c = code.strip().upper()
    if not c:
        return None

    if re.fullmatch(r"\d{6}", c):
        if c.startswith(("5", "6", "9")):
            return f"sh{c}"
        return f"sz{c}"

    if re.fullmatch(r"\d{5}", c):
        return f"hk{c}"

    if re.fullmatch(r"[A-Z]{1,5}", c):
        return f"us{c}"

    if c.startswith(("SH", "SZ", "HK", "US")) and len(c) > 2:
        return c.lower()

    return None


def fetch_realtime_quote_change_percent(raw_codes: Iterable[str]) -> dict[str, float]:
    symbol_pairs: list[tuple[str, str]] = []
    for code in raw_codes:
        symbol = _to_sina_symbol(code)
        if symbol:
            symbol_pairs.append((code, symbol))

    if not symbol_pairs:
        return {}

    symbols = ",".join(sym for _, sym in symbol_pairs)
    url = f"https://hq.sinajs.cn/list={symbols}"
    text = _http_get(url, referer="https://finance.sina.com.cn")
    lines = text.splitlines()

    by_symbol: dict[str, float] = {}
    for line in lines:
        if '="";' in line:
            continue
        lhs_rhs = line.split("=", 1)
        if len(lhs_rhs) != 2:
            continue
        lhs, rhs = lhs_rhs
        m = re.search(r"hq_str_(\w+)", lhs)
        if not m:
            continue
        symbol = m.group(1)
        data = rhs.strip().strip('";')
        fields = data.split(",")
        change = _parse_sina_change_percent(symbol, fields)
        if change is not None:
            by_symbol[symbol] = change

    result: dict[str, float] = {}
    for raw, symbol in symbol_pairs:
        if symbol in by_symbol:
            result[raw] = by_symbol[symbol]
    return result


def _parse_sina_change_percent(symbol: str, fields: list[str]) -> float | None:
    try:
        if symbol.startswith(("sh", "sz")):
            prev_close = float(fields[2])
            price = float(fields[3])
            if prev_close == 0:
                return None
            return (price / prev_close - 1.0) * 100

        if symbol.startswith("hk"):
            prev_close = float(fields[3])
            price = float(fields[6])
            if prev_close == 0:
                return None
            return (price / prev_close - 1.0) * 100

        if symbol.startswith("us"):
            prev_close = float(fields[26])
            price = float(fields[1])
            if prev_close == 0:
                return None
            return (price / prev_close - 1.0) * 100
    except (ValueError, IndexError):
        return None
    return None


def fetch_tracking_index_candidates(fund_code: str) -> list[str]:
    url = f"https://fundf10.eastmoney.com/jbgk_{fund_code}.html"
    text = _http_get(url)

    candidates: list[str] = []
    mapping = {
        "沪深300": "sh000300",
        "中证500": "sh000905",
        "中证1000": "sh000852",
        "恒生指数": "hkHSI",
        "纳斯达克": "usIXIC",
        "标普500": "usINX",
    }
    for key, sym in mapping.items():
        if key in text:
            candidates.append(sym)
    return candidates
