# Contributing 🙌

Thanks for helping! This project aims to stay **small, readable and reliable**.

## Quick start

```bash
git clone https://github.com/<your-username>/cse-mcp.git
cd cse-mcp
uv sync
uv run pytest            # must pass before you open a PR
```

## Adding a new tool

1. Find the endpoint in the [CSE API docs](https://gh0sth4cker.github.io/Colombo-Stock-Exchange-CSE-API-Documentation/), or in your browser's DevTools → Network tab on cse.lk.
2. Try it with curl first:
   ```bash
   curl -X POST https://www.cse.lk/api/<endpoint> -d "symbol=JKH.N0000"
   ```
3. Add a function in `src/cse_mcp/server.py` with `@mcp.tool(annotations=READ_ONLY)`.
   - Write a clear docstring. **The AI reads it** to decide when to call your tool.
   - Rename cryptic fields (`tdyShareVolume` → `share_volume`) and run results through `_clean()`.
   - Keep outputs small: AIs pay for every token.
4. Add an offline test in `tests/test_server.py` using the fake API.

## Ground rules

- Be kind to cse.lk: no polling loops, and keep the cache.
- Don't add heavy dependencies without a good reason.
- Spotted a cse.lk API change? Open an issue with the endpoint and the new response. That's super helpful.
