---
name: cse-market-analyst
description: Use when the user asks about the Colombo Stock Exchange (CSE), Sri Lankan stocks, the ASPI or S&P SL20, CSE sectors, CSE company announcements or results, or wants a market wrap, stock deep dive or comparison of CSE-listed companies.
---

# CSE market analyst

Use the `cse` MCP tools to answer with live data, then explain it clearly.

## Ground rules

- Fetch before you answer. Don't quote CSE prices from memory.
- State the data time (`as_of`, Sri Lanka time) and whether the market is open. After 14:30 or on weekends the numbers are the last close.
- Prices are in LKR. Write large values readably (LKR 7.96bn, 1.5M shares).
- Don't know the ticker? Use `list_stocks` with part of the company name first.
- Be clear about what is data and what is your interpretation. This is market data, not personalised investment advice.

## Playbooks

**Market wrap** ("how was the market today?")
1. `get_market_overview` for indices, turnover and status.
2. `get_top_movers` for gainers, losers and most active (3–5 each).
3. `get_sector_indices` for the best and worst sectors.
4. `get_market_daily_summary` for net foreign flow and market P/E.
5. Summarise in about 6 lines: the headline move, breadth, sectors, foreign flow, and anything unusual.

**Stock deep dive** ("tell me about JKH")
1. `get_stock` for price, ranges, market cap, foreign holding and beta.
2. `get_price_history` with `1y` for the trend, plus `today` if the market is open.
3. `get_trades_by_price` to see where volume traded today and the VWAP.
4. `get_announcements` with `financial`, then `corporate`, using the ticker as `query`.
5. Give a snapshot, the trend, recent news, and the key levels (52-week high/low, VWAP).

**Compare stocks or a sector**
- Use `list_stocks` with a query (for example "bank") sorted by `market_cap` or `change_pct`.
- Use `get_index_history` for the matching sector index (by name, such as "Banks") over the same period.

**Results season**
- Use `get_announcements` with `financial`. Each item has a `document_url` PDF link the user can open.
