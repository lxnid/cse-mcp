<!-- mcp-name: io.github.lxnid/cse-mcp -->

<p align="center">
  <img src="https://raw.githubusercontent.com/lxnid/cse-mcp/main/assets/icon.png" width="112" alt="cse-mcp icon">
</p>

<h1 align="center">cse-mcp</h1>

<p align="center">
  <b>Give Claude (or any AI) live Colombo Stock Exchange data.</b><br>
  No more copy-pasting prices into chat.
</p>

<p align="center">
  <a href="https://pypi.org/project/cse-mcp/"><img src="https://img.shields.io/pypi/v/cse-mcp.svg" alt="PyPI"></a>
  <a href="https://github.com/lxnid/cse-mcp/actions/workflows/tests.yml"><img src="https://github.com/lxnid/cse-mcp/actions/workflows/tests.yml/badge.svg" alt="tests"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-green.svg" alt="MIT"></a>
  <img src="https://img.shields.io/badge/python-3.10+-blue.svg" alt="Python 3.10+">
</p>

```
You:    How did banks do today vs the ASPI? Anything interesting from COMB?
Claude: *checks get_market_overview, get_sector_indices, get_stock, get_announcements*
        The ASPI closed +2.75% at 22,123. Banks did even better (+3.7%).
        COMB ended at LKR 225.25 (+4.3%) on 1.5M shares...
```

`cse-mcp` is an [MCP](https://modelcontextprotocol.io) server. MCP is a standard "plug" that lets AI apps use tools. This one connects your AI to the public data behind [cse.lk](https://www.cse.lk), so its answers use **current** prices, indices and announcements.

---

## ⚡ Install (pick your app)

### Claude Desktop: one click, nothing else to install

1. Download **`cse-mcp-<version>.mcpb`** from the [latest release](https://github.com/lxnid/cse-mcp/releases/latest).
2. Double-click it (or drag it into Claude Desktop) and click **Install**.
3. Ask: *"How's the CSE today?"* 🎉

Claude Desktop sets up Python and everything else for you.

### Claude Code

```bash
claude mcp add cse -- uvx cse-mcp
```

Or install it as a plugin, which adds a market-analyst skill too:

```
/plugin install cse-mcp --marketplace lxnid/cse-mcp
```

### Cursor, VS Code, Windsurf, Claude Desktop (manual), and other MCP apps

Add this to the app's MCP config:

```json
{
  "mcpServers": {
    "cse": { "command": "uvx", "args": ["cse-mcp"] }
  }
}
```

This needs [uv](https://docs.astral.sh/uv/getting-started/installation/), the fast Python package manager (`brew install uv`, or see the link for Windows). Python itself is downloaded automatically.

It's also listed in the [official MCP Registry](https://registry.modelcontextprotocol.io) as `io.github.lxnid/cse-mcp`, so apps that browse the registry can find it.

### claude.ai on the web or phone?

Not yet. Web and mobile apps can only reach servers hosted on the internet, and this one runs on your computer. You can host it yourself with `uvx cse-mcp --http` behind an HTTPS URL (see Development below), then add that URL as a custom connector.

---

## 🧰 What your AI can do with it

| Tool | What it gives you |
|---|---|
| `get_market_overview` | Market open/closed, ASPI & S&P SL20, today's turnover/volume/trades |
| `get_top_movers` | Top gainers, losers or most active stocks today |
| `list_stocks` | Search all listed stocks by name/ticker and sort by turnover, % change, market cap… |
| `get_stock` | Full profile of one stock: price, ranges (week → all-time), market cap, foreign holding, beta |
| `get_price_history` | Price history: today (15-min bars), 1w, 1m, 3m or 1y |
| `get_trades_by_price` | Today's volume at each price level, plus VWAP |
| `get_sector_indices` | Every S&P/CSE sector index, best to worst |
| `get_index_history` | ASPI / S&P SL20 / any sector index over time |
| `get_market_daily_summary` | Foreign vs local buying (net foreign flow), market P/E, P/BV, dividend yield |
| `get_announcements` | Dividends, financial statements (PDF links), circulars, non-compliance notices… |

All tools are **read-only**. They can't place trades or change anything.

**Things to ask:**
- *"Give me a market wrap for today."*
- *"Were foreigners net buyers or sellers today?"*
- *"Show me the top 10 most active stocks and which sectors they're in."*
- *"How has HNB done over the past year vs the Banks index?"*
- *"Any new quarterly results out today? Summarise the ones from plantations."*
- *"Where did most of JKH's volume trade today?"*

> 💡 Tickers are forgiving: `jkh`, `JKH` and `JKH.N0000` all work. Non-voting shares use `X0000` (e.g. `JKH.X0000`).

---

## 🧠 How it works

```
 Your AI ──MCP──▶ cse-mcp (on your computer) ──HTTPS──▶ www.cse.lk/api/*
                   │
                   └─ tidies the JSON: readable names, rounded numbers,
                      Sri Lanka time, 15-min bars, PDF links, 30s cache
```

- `src/cse_mcp/client.py`: talks to cse.lk (timeouts, errors, a 30-second cache)
- `src/cse_mcp/server.py`: the MCP tools (one function each, easy to read)
- `tests/`: offline tests with fake API responses, plus an opt-in live test

Endpoint reference: the community [CSE API documentation](https://gh0sth4cker.github.io/Colombo-Stock-Exchange-CSE-API-Documentation/).

---

## ⚠️ Good to know

- **Unofficial.** Not affiliated with or endorsed by the Colombo Stock Exchange. The cse.lk API is public but undocumented, so it can change without notice. If a tool breaks, [open an issue](https://github.com/lxnid/cse-mcp/issues).
- **Private.** It collects nothing. Requests go straight from your computer to cse.lk. See [PRIVACY.md](PRIVACY.md).
- **Be gentle.** Responses are cached for 30 seconds so cse.lk isn't spammed. Please keep it that way.
- **Not financial advice.** Data can be delayed or wrong, and AIs can misread numbers. Double-check before you trade.
- Prices are in **LKR**. Times are **Sri Lanka time (UTC+05:30)**. Trading runs Mon–Fri, 09:30–14:30.

---

## 🛠️ Development

```bash
git clone https://github.com/lxnid/cse-mcp.git && cd cse-mcp
uv sync
uv run pytest                  # offline tests (fast, no internet)
uv run pytest -m live          # hit the real cse.lk API
uv run cse-mcp --http          # serve over HTTP at http://127.0.0.1:8000/mcp
uv run mcp dev src/cse_mcp/server.py   # poke the tools in the MCP Inspector (needs Node.js)
```

To run your local copy in Claude Desktop, use `"command": "uv", "args": ["--directory", "/ABSOLUTE/PATH/TO/cse-mcp", "run", "cse-mcp"]`.

Ideas, bug reports and PRs are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md).

## 📄 License

[MIT](LICENSE): use it, fork it, build on it.
