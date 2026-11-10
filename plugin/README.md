# CSE Market Data (unofficial)

![icon](icon.png)

This plugin gives Claude live data from the **Colombo Stock Exchange** (Sri Lanka), so you can ask about the market without pasting prices into chat.

It adds:

- **The `cse` MCP server** (10 read-only tools): market status, ASPI and S&P SL20, top movers, stock profiles and price history, sector indices, foreign flows, and company announcements with PDF links.
- **The `cse-market-analyst` skill**: a playbook for market wraps, stock deep dives and results-season checks.

## Install (Claude Code)

```
/plugin install cse-mcp --marketplace lxnid/cse-mcp
```

## Requirements

[uv](https://docs.astral.sh/uv/) must be installed, because the server runs with `uvx cse-mcp`. Python is downloaded automatically if needed.

## What it runs and sends

- It runs the [`cse-mcp`](https://pypi.org/project/cse-mcp/) package from PyPI (pinned version) on your machine.
- It sends requests only to the public `https://www.cse.lk/api/` endpoints, containing just the tool inputs (for example a stock symbol).
- It collects nothing. See [PRIVACY.md](https://github.com/lxnid/cse-mcp/blob/main/PRIVACY.md).

Unofficial, and not affiliated with the Colombo Stock Exchange. Market data, not investment advice.

Source, docs and issues: https://github.com/lxnid/cse-mcp. MIT licensed.
