"""Offline tests: cse.lk is replaced by canned responses, so these run anywhere.

Run the optional live check against the real API with:  uv run pytest -m live
"""

from __future__ import annotations

import json

import httpx
import pytest
from mcp.server.mcpserver.exceptions import ToolError

from cse_mcp import server
from cse_mcp.client import CSEClient, CSEError, document_url, normalize_symbol

FAKE_API = {
    "marketStatus": {"status": "Market Open"},
    "aspiData": {"value": 22123.39, "change": 592.02, "percentage": 2.7495, "highValue": 22162.94, "lowValue": 21528.76, "timestamp": 1794302414031},
    "snpData": {"value": 6368.12, "change": 224.97, "percentage": 3.66, "timestamp": 1794301218967},
    "marketSummery": {"tradeVolume": 7.9595108889e9, "shareVolume": 253922597, "trades": 44300, "tradeDate": 1794302414031},
    "tradeSummary": {
        "reqTradeSummery": [
            {"symbol": "HNB.N0000", "name": "HATTON NATIONAL BANK PLC", "price": 415.0, "percentageChange": 3.81, "turnover": 4.5e8, "marketCap": 1.9e11},
            {"symbol": "COMB.N0000", "name": "COMMERCIAL BANK OF CEYLON PLC", "price": 225.25, "percentageChange": 4.28, "turnover": 3.4e8, "marketCap": 3.5e11},
            {"symbol": "JKH.N0000", "name": "JOHN KEELLS HOLDINGS PLC", "price": 19.7, "percentageChange": 2.6, "turnover": 2.7e8, "marketCap": 3.4e11},
        ]
    },
    "companyInfoSummery": {
        "reqSymbolInfo": {"id": 297, "symbol": "JKH.N0000", "name": "JOHN KEELLS HOLDINGS PLC", "lastTradedPrice": 19.7, "previousClose": 19.2, "ytdHiPrice": 23.4, "ytdLowPrice": 17.5},
        "reqSymbolBetaInfo": {"triASIBetaValue": 1.0031595},
        "reqLogo": {"path": "upload_logo/jkh.jpeg"},
    },
    "companyChartDataByStock": {
        "chartData": [
            # 09:30 and 09:40 fall in the same 15-minute bar; 09:50 starts the next one.
            {"t": 1794283200000, "p": 19.3, "q": 100},
            {"t": 1794283800000, "p": 19.6, "q": 50},
            {"t": 1794284400000, "p": 19.5, "q": 10},
        ]
    },
    "detailedTrades": {
        "reqDetailTrades": [
            {"symbol": "JKH.N0000", "name": "JOHN KEELLS HOLDINGS PLC", "price": 19.8, "qty": 100, "trades": 2},
            {"symbol": "JKH.N0000", "name": "JOHN KEELLS HOLDINGS PLC", "price": 19.6, "qty": 300, "trades": 3},
            {"symbol": "ABAN.N0000", "name": "ABANS ELECTRICALS PLC", "price": 1050.0, "qty": 9, "trades": 1},
        ]
    },
    "allSectors": [
        {"sectorId": 238, "symbol": "BNK", "name": "Banks", "indexName": "S&P/CSE Banks Industry Group Index", "indexValue": 1864.83, "percentage": 3.69},
        {"sectorId": 223, "symbol": "EGY", "name": "Energy", "indexName": "S&P/CSE Energy Industry Group Index", "indexValue": 2824.15, "percentage": 2.6},
    ],
    "chartData": [{"d": 1794283200000, "v": 100.0}, {"d": 1794369600000, "v": 110.0}],
    "getFinancialAnnouncement": {
        "reqFinancialAnnouncemnets": [
            {"uploadedDate": "10 Nov 2026", "name": "JOHN KEELLS HOLDINGS PLC", "symbol": "JKH", "fileText": "Interim Financial Statements", "path": "cmt/upload_report_file/1 a.pdf"},
            {"uploadedDate": "09 Nov 2026", "name": "AGALAWATTE PLANTATIONS PLC", "symbol": "AGAL", "fileText": "Interim Financial Statements", "path": "cmt/upload_report_file/2.pdf"},
        ]
    },
}


def fake_cse(request: httpx.Request) -> httpx.Response:
    endpoint = request.url.path.rsplit("/", 1)[-1]
    form = dict(httpx.QueryParams(request.content.decode()))
    if endpoint == "companyInfoSummery" and form.get("symbol") != "JKH.N0000":
        return httpx.Response(404)
    if endpoint == "chartData" and "period" not in form:
        return httpx.Response(400, json={"apierror": {"message": "period parameter is missing"}})
    if endpoint not in FAKE_API:
        return httpx.Response(404)
    return httpx.Response(200, content=json.dumps(FAKE_API[endpoint]))


@pytest.fixture(autouse=True)
def offline_client(monkeypatch):
    monkeypatch.setattr(server, "client", CSEClient(transport=httpx.MockTransport(fake_cse)))


# ---------------------------------------------------------------- helpers


def test_normalize_symbol():
    assert normalize_symbol(" jkh ") == "JKH.N0000"
    assert normalize_symbol("comb.x0000") == "COMB.X0000"
    with pytest.raises(CSEError):
        normalize_symbol("  ")


def test_document_url():
    assert document_url("cmt/upload_report_file/a b.pdf") == "https://cdn.cse.lk/cmt/upload_report_file/a%20b.pdf"
    assert document_url("upload_report_file/x.pdf") == "https://cdn.cse.lk/cmt/upload_report_file/x.pdf"
    assert document_url(None) is None


def test_cse_error_is_shown_to_the_ai():
    # ToolErrors keep their message when sent back to the model.
    assert issubclass(CSEError, ToolError)


# ---------------------------------------------------------------- tools


async def test_market_overview():
    result = await server.get_market_overview()
    assert result["market_status"] == "Market Open"
    assert result["aspi"]["change_pct"] == 2.75
    assert result["today"]["trades"] == 44300
    assert result["aspi"]["as_of"].startswith("2026-11-10")


async def test_list_stocks_search_and_sort():
    result = await server.list_stocks(query="bank", sort_by="change_pct")
    assert result["matches"] == 2
    assert [s["symbol"] for s in result["stocks"]] == ["COMB.N0000", "HNB.N0000"]

    by_symbol = await server.list_stocks(sort_by="symbol", limit=0)
    assert [s["symbol"] for s in by_symbol["stocks"]] == ["COMB.N0000", "HNB.N0000", "JKH.N0000"]


async def test_get_stock():
    result = await server.get_stock("jkh")
    assert result["symbol"] == "JKH.N0000"
    assert result["ranges"]["year_to_date"] == {"high": 23.4, "low": 17.5}
    assert result["beta"]["vs_aspi"] == 1.0
    assert result["logo_url"] == "https://cdn.cse.lk/cmt/upload_logo/jkh.jpeg"


async def test_get_stock_unknown_symbol():
    with pytest.raises(CSEError, match="not found"):
        await server.get_stock("NOPE")


async def test_intraday_history_is_bucketed():
    result = await server.get_price_history("JKH", period="today")
    bars = result["bars"]
    assert len(bars) == 2
    assert bars[0] == {"time": "2026-11-10 09:30", "open": 19.3, "high": 19.6, "low": 19.3, "close": 19.6, "share_volume": 150}
    assert result["summary"]["start"] == 19.2  # previous close
    assert result["summary"]["end"] == 19.5


async def test_trades_by_price_filters_other_symbols():
    result = await server.get_trades_by_price("JKH")
    assert result["total_shares"] == 400
    assert result["vwap"] == 19.65
    assert [lv["price"] for lv in result["levels"]] == [19.8, 19.6]


async def test_index_history_resolves_names():
    aspi = await server.get_index_history("ASPI", period="1w")
    assert aspi["index_id"] == 1
    assert aspi["summary"]["change_pct"] == 10.0

    assert (await server.get_index_history("S&P SL20"))["index_id"] == 40
    assert (await server.get_index_history("bank"))["index_id"] == 238
    assert (await server.get_index_history("EGY"))["index_id"] == 223
    with pytest.raises(CSEError):
        await server.get_index_history("not-an-index")


async def test_announcements_filter():
    result = await server.get_announcements("financial", query="JKH.N0000")
    assert result["matches"] == 1
    item = result["announcements"][0]
    assert item["company"] == "JOHN KEELLS HOLDINGS PLC"
    assert item["document_url"].endswith("1%20a.pdf")


async def test_sample_keeps_first_and_last():
    rows = list(range(100))
    sampled = server._sample(rows, 5)
    assert sampled[0] == 0 and sampled[-1] == 99 and len(sampled) == 5


async def test_all_tools_registered():
    names = {t.name for t in await server.mcp.list_tools()}
    assert names == {
        "get_market_overview", "get_top_movers", "list_stocks", "get_sector_indices",
        "get_market_daily_summary", "get_stock", "get_price_history", "get_trades_by_price",
        "get_index_history", "get_announcements",
    }


# ---------------------------------------------------------------- live (opt-in)


@pytest.mark.live
async def test_live_api(monkeypatch):
    monkeypatch.setattr(server, "client", CSEClient())
    overview = await server.get_market_overview()
    assert overview["aspi"]["value"] > 0
    stock = await server.get_stock("JKH")
    assert stock["name"] == "JOHN KEELLS HOLDINGS PLC"
