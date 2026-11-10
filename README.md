# 📈 cse-mcp

**Give Claude (or any AI) live Colombo Stock Exchange data.** No more copy-pasting prices into chat.

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)
![MCP](https://img.shields.io/badge/MCP-server-8A2BE2)

```
You:    How did banks do today vs the ASPI? Anything interesting from COMB?
Claude: *checks get_market_overview, get_sector_indices, get_stock, get_announcements*
        The ASPI closed +2.75% at 22,123. Banks did even better (+3.7%).
        COMB ended at LKR 225.25 (+4.3%) on 1.5M shares...
```

`cse-mcp` is an [MCP](https://modelcontextprotocol.io) server. MCP is a standard "plug" that lets AI apps call tools. This one connects your AI to the public data behind [cse.lk](https://www.cse.lk), so every answer uses **current** prices, indices and announcements.

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

**Things to ask:**
- *"Give me a market wrap for today."*
- *"Were foreigners net buyers or sellers today?"*
- *"Show me the top 10 most active stocks and which sectors they're in."*
- *"How has HNB done over the past year vs the Banks index?"*
- *"Any new quarterly results out today? Summarise the ones from plantations."*
- *"Where did most of JKH's volume trade today?"*

> 💡 Tickers are forgiving: `jkh`, `JKH` and `JKH.N0000` all work. Non-voting shares use `X0000` (e.g. `JKH.X0000`).

---

## 🚀 Setup (≈ 2 minutes)

**1. Install [uv](https://docs.astral.sh/uv/)**, the fast Python package manager:

```bash
# macOS / Linux
curl -LsSf https://astral.sh/uv/install.sh | sh      # or: brew install uv

# Windows (PowerShell)
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

**2. Get the code:**

```bash
git clone https://github.com/<your-username>/cse-mcp.git
cd cse-mcp
uv sync
```

**3. Check it works** (this pings the live API):

```bash
uv run pytest -m live
```

---

## 🔌 Connect it to Claude

### Claude Desktop (Mac / Windows)

1. Open **Claude Desktop → Settings → Developer → Edit Config**. This opens `claude_desktop_config.json`:
   - macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
   - Windows: `%APPDATA%\Claude\claude_desktop_config.json`
2. Add this, replacing the path with **your** folder (run `pwd` inside `cse-mcp` to get it):

   ```json
   {
     "mcpServers": {
       "cse": {
         "command": "uv",
         "args": ["--directory", "/ABSOLUTE/PATH/TO/cse-mcp", "run", "cse-mcp"]
       }
     }
   }
   ```

   Already have other servers? Just add the `"cse": {...}` block inside your existing `mcpServers`.
3. **Fully quit** Claude Desktop (⌘Q on Mac, not just close the window) and open it again.
4. Click the **🔧 tools / "+" menu** in a chat. You should see the `cse` tools. Ask *"How's the CSE today?"* 🎉

> **"spawn uv ENOENT" or the server won't start?** Claude can't find `uv`. Run `which uv` (Mac) or `where uv` (Windows) and use that full path as `"command"`, e.g. `"/opt/homebrew/bin/uv"`.

### Claude Code (terminal)

```bash
claude mcp add cse -- uv --directory /ABSOLUTE/PATH/TO/cse-mcp run cse-mcp
```

Then type `/mcp` in Claude Code to confirm it's connected.

### Other AI apps (Cursor, VS Code, Windsurf, ChatGPT desktop…)

Any app that supports MCP works. Point it at the same command:

```
command:  uv
args:     --directory /ABSOLUTE/PATH/TO/cse-mcp run cse-mcp
```

If an app wants a **URL** instead of a command, run the HTTP mode:

```bash
uv run cse-mcp --http --port 8000     # → http://127.0.0.1:8000/mcp
```

> Web apps like claude.ai's *custom connectors* need a public **https** URL. Host the HTTP mode on a server or behind a tunnel (e.g. Cloudflare Tunnel) first.

### ⚡ No-clone install (once it's on GitHub)

```json
"cse": {
  "command": "uvx",
  "args": ["--from", "git+https://github.com/<your-username>/cse-mcp", "cse-mcp"]
}
```

---

## 🧠 How it works

```
 Claude ──MCP──▶ cse-mcp ──HTTPS POST──▶ www.cse.lk/api/*
                  │
                  └─ cleans up the JSON: readable names, rounded numbers,
                     Sri Lanka time, 15-min bars, PDF links, 30s cache
```

- `src/cse_mcp/client.py`: talks to cse.lk (timeouts, errors, a 30-second cache)
- `src/cse_mcp/server.py`: the MCP tools (one function each, easy to read)
- `tests/`: offline tests with fake API responses, plus an opt-in live test

Endpoint reference: the community [CSE API documentation](https://gh0sth4cker.github.io/Colombo-Stock-Exchange-CSE-API-Documentation/).

---

## ⚠️ Good to know

- **Unofficial.** Not affiliated with or endorsed by the Colombo Stock Exchange. The cse.lk API is public but undocumented, so it can change without notice. If a tool breaks, open an issue!
- **Be gentle.** Responses are cached for 30 seconds so the API isn't spammed. Please keep it that way.
- **Not financial advice.** Data may be delayed or wrong. Always double-check before you trade. AIs can still misread numbers.
- Prices are in **LKR**. Times are **Sri Lanka time (UTC+05:30)**. Trading runs Mon–Fri, 09:30–14:30.

---

## 🛠️ Development

```bash
uv sync                   # install deps
uv run pytest             # offline tests (fast, no internet)
uv run pytest -m live     # hit the real cse.lk API
uv run mcp dev src/cse_mcp/server.py   # poke the tools in the MCP Inspector (needs Node.js)
```

Ideas, bug reports and PRs are very welcome. See [CONTRIBUTING.md](CONTRIBUTING.md).

## 📄 License

[MIT](LICENSE): use it, fork it, build on it.
