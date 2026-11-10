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

## Releasing (maintainers)

```bash
uv run scripts/bump_version.py 0.2.0   # updates pyproject, manifest, server.json, plugin
# add a CHANGELOG entry, then:
git commit -am "Release 0.2.0" && git tag v0.2.0 && git push && git push --tags
```

The `release` workflow then tests, publishes to PyPI, attaches the `.mcpb` and wheel to a GitHub Release, and publishes to the MCP Registry. A test fails the release if any version number disagrees.

**One-time setup** (already done for this repo):
1. On PyPI, add a [trusted publisher](https://docs.pypi.org/trusted-publishers/adding-a-publisher/): owner `lxnid`, repo `cse-mcp`, workflow `release.yml`, environment `pypi`.
2. In GitHub, go to Settings → Environments → create `pypi` and add yourself as a required reviewer, so every release waits for your approval.

## Ground rules

- Be kind to cse.lk: no polling loops, and keep the cache.
- Don't add heavy dependencies without a good reason.
- Spotted a cse.lk API change? Open an issue with the endpoint and the new response. That's super helpful.
