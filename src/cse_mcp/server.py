"""CSE MCP server: live Colombo Stock Exchange data as MCP tools.

Each tool calls one or two cse.lk endpoints and reshapes the response into
something compact and readable for an AI: friendly field names, rounded numbers,
Sri Lanka timestamps, and no logo/ID noise unless it's useful.
"""

from __future__ import annotations

import argparse
import asyncio
from datetime import datetime, timedelta, timezone
from typing import Any, Literal

from mcp.server.mcpserver import MCPServer
from mcp.types import ToolAnnotations

from cse_mcp.client import CDN_URL, CSEClient, CSEError, document_url, normalize_symbol

SL_TZ = timezone(timedelta(hours=5, minutes=30), "Asia/Colombo")  # Sri Lanka has no DST

Period = Literal["today", "1w", "1m", "3m", "1y"]
PERIOD_CODES: dict[str, int] = {"today": 1, "1w": 2, "1m": 3, "3m": 4, "1y": 5}

INSTRUCTIONS = """\
Live data from the Colombo Stock Exchange (CSE), Sri Lanka, via the public cse.lk API.
- Prices and values are in Sri Lankan Rupees (LKR). Times are Sri Lanka time (UTC+05:30).
- Regular trading: Monday-Friday 09:30-14:30, excluding market holidays.
- Symbols look like JKH.N0000 (N = voting, X = non-voting). Bare tickers like "JKH" are treated as JKH.N0000.
- If you don't know a symbol, use list_stocks with a name fragment (e.g. "bank", "keells").
- Start with get_market_overview for "how's the market?" questions.
- This is market data, not investment advice. Mention the data timestamp when it matters.
"""

mcp = MCPServer("cse-mcp", instructions=INSTRUCTIONS)
client = CSEClient()

READ_ONLY = ToolAnnotations(read_only_hint=True, destructive_hint=False, idempotent_hint=True, open_world_hint=True)


# --------------------------------------------------------------------------- helpers


def _time(ms: float | int | None, with_time: bool = True) -> str | None:
    """Epoch milliseconds -> 'YYYY-MM-DD HH:MM' in Sri Lanka time."""
    if not ms:
        return None
    moment = datetime.fromtimestamp(ms / 1000, SL_TZ)
    return moment.strftime("%Y-%m-%d %H:%M" if with_time else "%Y-%m-%d")


def _num(value: Any, digits: int = 2) -> Any:
    """Round floats for readability; turn whole floats (1.0E9) into ints."""
    if isinstance(value, float):
        value = round(value, digits)
        return int(value) if value.is_integer() and abs(value) >= 1000 else value
    return value


def _clean(d: dict[str, Any]) -> dict[str, Any]:
    """Round numbers and drop empty fields."""
    return {k: _num(v) for k, v in d.items() if v is not None and v != ""}


def _sample(rows: list[Any], max_points: int) -> list[Any]:
    """Evenly thin a series down to max_points, always keeping the last point."""
    if max_points <= 0 or len(rows) <= max_points:
        return rows
    step = (len(rows) - 1) / (max_points - 1)
    return [rows[round(i * step)] for i in range(max_points)]


def _summary(first: float | None, last: float | None, highs: list[float], lows: list[float]) -> dict[str, Any]:
    change = last - first if first and last is not None else None
    return _clean(
        {
            "start": first,
            "end": last,
            "change": change,
            "change_pct": change / first * 100 if change is not None else None,
            "high": max(highs) if highs else None,
            "low": min(lows) if lows else None,
        }
    )


async def _company(symbol: str) -> dict[str, Any]:
    return await client.post("companyInfoSummery", symbol=normalize_symbol(symbol))


# --------------------------------------------------------------------------- market-wide tools


@mcp.tool(annotations=READ_ONLY)
async def get_market_overview() -> dict[str, Any]:
    """Snapshot of the whole market right now: open/closed status, the ASPI and
    S&P SL20 indices (value, change, day range) and today's turnover, volume and trades.
    Best first call for "how is the market doing?"."""
    status, aspi, snp, totals = await asyncio.gather(
        client.post("marketStatus"),
        client.post("aspiData"),
        client.post("snpData"),
        client.post("marketSummery"),
    )

    def index(d: dict[str, Any]) -> dict[str, Any]:
        return _clean(
            {
                "value": d.get("value"),
                "change": d.get("change"),
                "change_pct": d.get("percentage"),
                "day_high": d.get("highValue"),
                "day_low": d.get("lowValue"),
                "as_of": _time(d.get("timestamp")),
            }
        )

    return {
        "market_status": status.get("status"),
        "aspi": index(aspi),
        "sp_sl20": index(snp),
        "today": _clean(
            {
                "turnover_lkr": totals.get("tradeVolume"),  # cse.lk names this field oddly; it is LKR turnover
                "share_volume": totals.get("shareVolume"),
                "trades": totals.get("trades"),
                "as_of": _time(totals.get("tradeDate")),
            }
        ),
    }


@mcp.tool(annotations=READ_ONLY)
async def get_top_movers(
    kind: Literal["gainers", "losers", "most_active"] = "gainers",
    limit: int = 10,
) -> dict[str, Any]:
    """Today's biggest gainers, biggest losers, or most actively traded stocks."""
    endpoint = {"gainers": "topGainers", "losers": "topLooses", "most_active": "mostActiveTrades"}[kind]
    rows = await client.post(endpoint)
    stocks = [
        _clean(
            {
                "symbol": r.get("symbol"),
                "price": r.get("price"),
                "change": r.get("change"),
                "change_pct": r.get("changePercentage"),
                "trades": r.get("tradeVolume"),
                "share_volume": r.get("shareVolume"),
                "turnover_lkr": r.get("turnover"),
                "pct_of_market_volume": r.get("percentageShareVolume"),
            }
        )
        for r in rows[: max(limit, 1)]
    ]
    return {"kind": kind, "stocks": stocks}


@mcp.tool(annotations=READ_ONLY)
async def list_stocks(
    query: str = "",
    sort_by: Literal["turnover", "change_pct", "market_cap", "volume", "symbol"] = "turnover",
    limit: int = 25,
) -> dict[str, Any]:
    """Search and rank every listed stock with today's prices.

    Use `query` to find symbols by company name or ticker (e.g. "bank", "hayleys", "JKH").
    Sort by turnover, change_pct (best first), market_cap, volume or symbol.
    Set limit=0 to return every match."""
    data = await client.post("tradeSummary")
    rows = data.get("reqTradeSummery", [])

    q = query.strip().lower()
    if q:
        rows = [r for r in rows if q in (r.get("symbol") or "").lower() or q in (r.get("name") or "").lower()]

    sort_keys = {
        "turnover": ("turnover", True),
        "change_pct": ("percentageChange", True),
        "market_cap": ("marketCap", True),
        "volume": ("sharevolume", True),
        "symbol": ("symbol", False),
    }
    field, descending = sort_keys[sort_by]
    rows = sorted(rows, key=lambda r: r.get(field) or 0 if descending else r.get(field) or "", reverse=descending)

    stocks = [
        _clean(
            {
                "symbol": r.get("symbol"),
                "name": r.get("name"),
                "price": r.get("price"),
                "change": r.get("change"),
                "change_pct": r.get("percentageChange"),
                "previous_close": r.get("previousClose"),
                "open": r.get("open"),
                "high": r.get("high"),
                "low": r.get("low"),
                "share_volume": r.get("sharevolume"),
                "trades": r.get("tradevolume"),
                "turnover_lkr": r.get("turnover"),
                "market_cap_lkr": r.get("marketCap"),
                "last_traded": _time(r.get("lastTradedTime")),
            }
        )
        for r in (rows[:limit] if limit > 0 else rows)
    ]
    return {"matches": len(rows), "returned": len(stocks), "stocks": stocks}


@mcp.tool(annotations=READ_ONLY)
async def get_sector_indices() -> dict[str, Any]:
    """All CSE sector indices (S&P/CSE industry groups such as Banks, Energy,
    Capital Goods) with today's value, change and activity, best performers first.
    The `index_id` can be passed to get_index_history."""
    rows = await client.post("allSectors")
    sectors = [
        _clean(
            {
                "name": r.get("name"),
                "symbol": r.get("symbol"),
                "index_id": r.get("sectorId"),
                "index_name": r.get("indexName"),
                "value": r.get("indexValue"),
                "change": r.get("change"),
                "change_pct": r.get("percentage"),
                "previous_close": r.get("sectorPreviousClose"),
                "trades": r.get("sectorTradeToday"),
                "share_volume": r.get("sectorVolumeToday"),
                "turnover_lkr": r.get("sectorTurnoverToday"),
                "as_of": _time(r.get("transactionTime")),
            }
        )
        for r in rows
    ]
    sectors.sort(key=lambda s: s.get("change_pct", 0), reverse=True)
    return {"sectors": sectors}


@mcp.tool(annotations=READ_ONLY)
async def get_market_daily_summary() -> dict[str, Any]:
    """End-of-day style market statistics: turnover, foreign vs domestic buying
    and selling (net foreign flow), market cap, market P/E, P/BV and dividend
    yield, number of companies traded."""
    data = await client.post("dailyMarketSummery")
    days = [d for group in data for d in (group if isinstance(group, list) else [group])]
    summaries = []
    for d in days:
        foreign_buy, foreign_sell = d.get("equityForeignPurchase"), d.get("equityForeignSales")
        summaries.append(
            _clean(
                {
                    "date": _time(d.get("tradeDate"), with_time=False),
                    "turnover_lkr": d.get("marketTurnover"),
                    "trades": d.get("tradesNo"),
                    "trades_domestic": d.get("tradesNoDomestic"),
                    "trades_foreign": d.get("tradesNoForeign"),
                    "share_volume": d.get("volumeOfTurnOverNumber"),
                    "foreign_purchases_lkr": foreign_buy,
                    "foreign_sales_lkr": foreign_sell,
                    "net_foreign_flow_lkr": (foreign_buy or 0) - (foreign_sell or 0)
                    if foreign_buy is not None or foreign_sell is not None
                    else None,
                    "domestic_purchases_lkr": d.get("equityDomesticPurchase"),
                    "domestic_sales_lkr": d.get("equityDomesticSales"),
                    "market_cap_lkr": d.get("marketCap"),
                    "listed_companies": d.get("listedCompanyNumber"),
                    "companies_traded": d.get("tradeCompanyNumber"),
                    "market_pe": d.get("per"),
                    "market_pbv": d.get("pbv"),
                    "market_dividend_yield_pct": d.get("dy"),
                    "aspi": d.get("asi"),
                    "sp_sl20": d.get("spp"),
                }
            )
        )
    return {"days": summaries}


# --------------------------------------------------------------------------- single-stock tools


@mcp.tool(annotations=READ_ONLY)
async def get_stock(symbol: str) -> dict[str, Any]:
    """Full live profile of one stock: price and change, today's range and
    volume, week/month/YTD/52-week/all-time highs and lows, market cap,
    foreign holding, beta. `symbol` like "JKH", "JKH.N0000" or "COMB.X0000"."""
    data = await _company(symbol)
    info = data.get("reqSymbolInfo") or {}
    beta = data.get("reqSymbolBetaInfo") or {}
    logo = (data.get("reqLogo") or {}).get("path")

    def hi_lo(prefix: str) -> dict[str, Any]:
        return _clean({"high": info.get(f"{prefix}HiPrice"), "low": info.get(f"{prefix}LowPrice")})

    return _clean(
        {
            "symbol": info.get("symbol"),
            "name": info.get("name"),
            "price": info.get("lastTradedPrice"),
            "change": info.get("change"),
            "change_pct": info.get("changePercentage"),
            "previous_close": info.get("previousClose"),
            "closing_price": info.get("closingPrice"),
            "today": _clean(
                {
                    "high": info.get("hiTrade"),
                    "low": info.get("lowTrade"),
                    "share_volume": info.get("tdyShareVolume"),
                    "trades": info.get("tdyTradeVolume"),
                    "turnover_lkr": info.get("tdyTurnover"),
                }
            ),
            "ranges": {
                "week": hi_lo("wtd"),
                "month": hi_lo("mtd"),
                "year_to_date": hi_lo("ytd"),
                "52_weeks": hi_lo("p12"),
                "all_time": _clean({"high": info.get("allHiPrice"), "low": info.get("allLowPrice")}),
            },
            "volume": _clean(
                {
                    "month_shares": info.get("mtdShareVolume"),
                    "ytd_shares": info.get("ytdShareVolume"),
                    "52_week_shares": info.get("p12ShareVolume"),
                    "ytd_turnover_lkr": info.get("ytdTurnover"),
                }
            ),
            "market_cap_lkr": info.get("marketCap"),
            "pct_of_total_market_cap": info.get("marketCapPercentage"),
            "shares_issued": info.get("quantityIssued"),
            "par_value": info.get("parValue"),
            "foreign_holding_shares": info.get("foreignHoldings"),
            "foreign_holding_pct": info.get("foreignPercentage"),
            "beta": _clean(
                {
                    "vs_aspi": beta.get("triASIBetaValue"),
                    "vs_sp_sl20": beta.get("betaValueSPSL"),
                    "period": beta.get("triASIBetaPeriod"),
                }
            )
            or None,
            "listed_since": info.get("issueDate"),
            "isin": info.get("isin"),
            "logo_url": CDN_URL + logo if logo else None,
        }
    )


@mcp.tool(annotations=READ_ONLY)
async def get_price_history(symbol: str, period: Period = "1m", max_points: int = 120) -> dict[str, Any]:
    """Price history for one stock. period: "today" (15-minute bars), "1w",
    "1m", "3m" or "1y" (daily bars). Includes a start/end/change/high/low
    summary. Long series are thinned to `max_points` rows (0 = no limit)."""
    info = (await _company(symbol)).get("reqSymbolInfo") or {}
    stock_id = info.get("id")
    if stock_id is None:
        raise CSEError(f"Couldn't find an internal id for {symbol}.")

    data = await client.post("companyChartDataByStock", stockId=stock_id, period=PERIOD_CODES[period])
    points = sorted((p for p in data.get("chartData", []) if p.get("p") is not None), key=lambda p: p["t"])

    if period == "today":
        bars = _intraday_bars(points, minutes=15)
        summary = _summary(
            info.get("previousClose"),
            bars[-1]["close"] if bars else None,
            [b["high"] for b in bars],
            [b["low"] for b in bars],
        )
    else:
        bars = [
            _clean(
                {
                    "date": _time(p["t"], with_time=False),
                    "close": p.get("p"),
                    "high": p.get("h"),
                    "low": p.get("l"),
                    "share_volume": p.get("q"),
                }
            )
            for p in points
        ]
        summary = _summary(
            bars[0].get("close") if bars else None,
            bars[-1].get("close") if bars else None,
            [b["high"] for b in bars if "high" in b],
            [b["low"] for b in bars if "low" in b],
        )

    return {
        "symbol": info.get("symbol"),
        "period": period,
        "summary": summary,
        "bars_total": len(bars),
        "bars": _sample(bars, max_points),
    }


def _intraday_bars(trades: list[dict[str, Any]], minutes: int) -> list[dict[str, Any]]:
    """Group individual trades (t=time, p=price, q=qty) into OHLC bars."""
    bars: dict[int, dict[str, Any]] = {}
    width = minutes * 60_000
    for trade in trades:
        bucket = trade["t"] // width * width
        price, qty = trade["p"], trade.get("q") or 0
        bar = bars.get(bucket)
        if bar is None:
            bars[bucket] = {"time": _time(bucket), "open": price, "high": price, "low": price, "close": price, "share_volume": qty}
        else:
            bar["high"] = max(bar["high"], price)
            bar["low"] = min(bar["low"], price)
            bar["close"] = price
            bar["share_volume"] += qty
    return [_clean(b) for b in bars.values()]


@mcp.tool(annotations=READ_ONLY)
async def get_trades_by_price(symbol: str) -> dict[str, Any]:
    """Today's trading in one stock broken down by price level: how many shares
    and trades went through at each price, plus the volume-weighted average
    price (VWAP). Useful for spotting where the real buying/selling happened."""
    sym = normalize_symbol(symbol)
    data = await client.post("detailedTrades", symbol=sym)
    # cse.lk ignores the symbol filter and returns every stock, so filter here.
    rows = [r for r in data.get("reqDetailTrades", []) if r.get("symbol") == sym]
    if not rows:
        return {"symbol": sym, "message": "No trades for this symbol today (or the market hasn't opened yet).", "levels": []}

    total_qty = sum(r.get("qty") or 0 for r in rows)
    vwap = sum((r.get("price") or 0) * (r.get("qty") or 0) for r in rows) / total_qty if total_qty else None
    levels = sorted(
        (_clean({"price": r.get("price"), "shares": r.get("qty"), "trades": r.get("trades"), "change_pct": r.get("changePercentage")}) for r in rows),
        key=lambda lv: lv["price"],
        reverse=True,
    )
    return {
        "symbol": sym,
        "name": rows[0].get("name"),
        "total_shares": total_qty,
        "total_trades": sum(r.get("trades") or 0 for r in rows),
        "vwap": _num(vwap),
        "levels": levels,
    }


# --------------------------------------------------------------------------- indices


@mcp.tool(annotations=READ_ONLY)
async def get_index_history(index: str = "ASPI", period: Period = "1m", max_points: int = 120) -> dict[str, Any]:
    """History of a market or sector index. `index` can be "ASPI", "S&P SL20",
    a sector name/symbol from get_sector_indices (e.g. "Banks", "BNK") or its
    numeric index_id. period: "today" (minute data), "1w", "1m", "3m", "1y"."""
    index_id, label = await _resolve_index(index)
    rows = await client.post("chartData", chartId=index_id, period=PERIOD_CODES[period])
    rows = sorted((r for r in rows if r.get("v") is not None), key=lambda r: r["d"])
    points = [{"time": _time(r["d"], with_time=period == "today"), "value": _num(r["v"])} for r in rows]
    values = [p["value"] for p in points]
    return {
        "index": label,
        "index_id": index_id,
        "period": period,
        "summary": _summary(values[0] if values else None, values[-1] if values else None, values, values),
        "points_total": len(points),
        "points": _sample(points, max_points),
    }


async def _resolve_index(index: str) -> tuple[int, str]:
    key = index.strip().lower().replace(" ", "").replace("&", "n").replace("/", "")
    if key in {"aspi", "asi", "allshare", "allshareprice", "1"}:
        return 1, "ASPI"
    if key in {"snpsl20", "spsl20", "sl20", "snp", "sp20", "40"}:
        return 40, "S&P SL20"
    sectors = await client.post("allSectors")
    wanted = index.strip().lower()
    for s in sectors:
        names = {str(s.get("sectorId")), (s.get("symbol") or "").lower(), (s.get("name") or "").lower()}
        if wanted in names:
            return int(s["sectorId"]), s.get("indexName") or s.get("name")
    for s in sectors:  # loose match, e.g. "bank" -> "Banks"
        if wanted in (s.get("name") or "").lower() or wanted in (s.get("indexName") or "").lower():
            return int(s["sectorId"]), s.get("indexName") or s.get("name")
    raise CSEError(f"Unknown index '{index}'. Use 'ASPI', 'S&P SL20', or a sector from get_sector_indices.")


# --------------------------------------------------------------------------- announcements

ANNOUNCEMENTS: dict[str, tuple[str, str]] = {
    # category: (endpoint, response key)
    "corporate": ("approvedAnnouncement", "approvedAnnouncements"),
    "financial": ("getFinancialAnnouncement", "reqFinancialAnnouncemnets"),
    "non_compliance": ("getNonComplianceAnnouncements", "nonComplianceAnnouncements"),
    "new_listings": ("getNewListingsRelatedNoticesAnnouncements", "newListingRelatedAnnouncements"),
    "buy_in_board": ("getBuyInBoardAnnouncements", "buyInBoardAnnouncements"),
    "circulars": ("circularAnnouncement", "reqCircularAnnouncement"),
    "directives": ("directiveAnnouncement", "reqDirectiveAnnouncement"),
}


@mcp.tool(annotations=READ_ONLY)
async def get_announcements(
    category: Literal["corporate", "financial", "non_compliance", "new_listings", "buy_in_board", "circulars", "directives"] = "corporate",
    query: str = "",
    limit: int = 15,
) -> dict[str, Any]:
    """Latest CSE announcements, newest first.

    - corporate: dividends, rights issues, AGMs, board changes, XD/payment dates
    - financial: quarterly/annual financial statements (with PDF links)
    - non_compliance, new_listings, buy_in_board: regulatory notices
    - circulars, directives: CSE/SEC rule circulars and directives

    `query` filters by company name, ticker or text (e.g. "JKH", "dividend")."""
    endpoint, key = ANNOUNCEMENTS[category]
    data = await client.post(endpoint)
    rows = data.get(key, []) if isinstance(data, dict) else []
    items = [_announcement(r) for r in rows]

    q = query.strip().lower().split(".")[0]  # "JKH.N0000" -> "jkh"
    if q:
        items = [i for i in items if any(q in str(v).lower() for v in i.values())]
    return {"category": category, "matches": len(items), "announcements": items[: max(limit, 1)]}


def _announcement(r: dict[str, Any]) -> dict[str, Any]:
    return _clean(
        {
            "date": r.get("dateOfAnnouncement") or r.get("uploadedDate") or r.get("createdDate"),
            "company": r.get("company") or r.get("name") or r.get("companyName"),
            "symbol": r.get("symbol"),
            "category": r.get("announcementCategory"),
            "title": r.get("fileText") or r.get("title"),
            "remarks": (r.get("remarks") or "").strip() or None,
            "record_date": r.get("recordDate"),
            "xd_date": r.get("xd"),
            "xr_date": r.get("xr"),
            "payment_date": r.get("paymentDate"),
            "agm_date": r.get("agmDate"),
            "trading_commencement": r.get("tradingCommencement"),
            "trading_suspended": r.get("tradingSuspended"),
            "document_url": document_url(r.get("path")),
        }
    )


# --------------------------------------------------------------------------- entry point


def main() -> None:
    parser = argparse.ArgumentParser(description="CSE MCP server: live Colombo Stock Exchange data for AI assistants.")
    parser.add_argument("--http", action="store_true", help="serve over Streamable HTTP instead of stdio")
    parser.add_argument("--host", default="127.0.0.1", help="HTTP host (default 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8000, help="HTTP port (default 8000)")
    args = parser.parse_args()

    if args.http:
        mcp.run("streamable-http", host=args.host, port=args.port)
    else:
        mcp.run()


if __name__ == "__main__":
    main()
