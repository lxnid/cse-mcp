"""A small async client for the public cse.lk API.

Every endpoint is a POST to https://www.cse.lk/api/<name> with form-encoded
parameters. This module handles the HTTP side (timeouts, a short cache, error
messages); `server.py` turns the raw JSON into tidy MCP tool results.
"""

from __future__ import annotations

import logging
import time
from typing import Any

import httpx
from mcp.server.mcpserver.exceptions import ToolError

# httpx logs every request at INFO, which floods the AI app's MCP log.
logging.getLogger("httpx").setLevel(logging.WARNING)

BASE_URL = "https://www.cse.lk/api/"
CDN_URL = "https://cdn.cse.lk/cmt/"
USER_AGENT = "cse-mcp/0.1 (open-source MCP server)"


class CSEError(ToolError):
    """Raised when cse.lk can't be reached or rejects a request.

    It's a ToolError so the message reaches the AI (e.g. "check the symbol")
    instead of being hidden as a generic server crash.
    """


def normalize_symbol(symbol: str) -> str:
    """Turn user input like "jkh" or " JKH.n0000 " into "JKH.N0000".

    CSE symbols are TICKER.CLASS. Ordinary voting shares use N0000, so that's
    the default when no class is given (non-voting shares are X0000).
    """
    symbol = symbol.strip().upper()
    if not symbol:
        raise CSEError("Symbol is empty. Try something like 'JKH' or 'COMB.N0000'.")
    return symbol if "." in symbol else f"{symbol}.N0000"


def document_url(path: str | None) -> str | None:
    """Build a downloadable link for an announcement/report PDF."""
    if not path:
        return None
    path = path.removeprefix("cmt/").replace(" ", "%20")
    return CDN_URL + path


class CSEClient:
    """Async wrapper around the cse.lk API with a tiny in-memory cache.

    The cache (default 30s) keeps an AI that calls several tools in a row from
    hammering cse.lk, while still being "live" for any human purpose.
    """

    def __init__(
        self,
        base_url: str = BASE_URL,
        cache_ttl: float = 30.0,
        timeout: float = 20.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.cache_ttl = cache_ttl
        self._cache: dict[tuple, tuple[float, Any]] = {}
        self._http = httpx.AsyncClient(
            base_url=base_url,
            timeout=timeout,
            transport=transport,
            headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
        )

    async def post(self, endpoint: str, **params: Any) -> Any:
        """POST to an endpoint and return parsed JSON (cached briefly)."""
        key = (endpoint, tuple(sorted(params.items())))
        cached = self._cache.get(key)
        if cached and time.monotonic() - cached[0] < self.cache_ttl:
            return cached[1]

        try:
            response = await self._http.post(endpoint, data=params)
        except httpx.HTTPError as exc:
            raise CSEError(f"Couldn't reach cse.lk ({endpoint}): {exc!r}") from exc

        if response.status_code == 404:
            raise CSEError(f"cse.lk returned 'not found' for {endpoint} {params}. Check the symbol.")
        if response.status_code >= 400:
            raise CSEError(f"cse.lk returned HTTP {response.status_code} for {endpoint}: {_api_message(response)}")

        try:
            data = response.json()
        except ValueError as exc:
            raise CSEError(f"cse.lk sent a non-JSON response for {endpoint}.") from exc

        self._cache[key] = (time.monotonic(), data)
        return data

    async def aclose(self) -> None:
        await self._http.aclose()


def _api_message(response: httpx.Response) -> str:
    try:
        return response.json()["apierror"]["message"]
    except (ValueError, KeyError, TypeError):
        return response.text[:200]
