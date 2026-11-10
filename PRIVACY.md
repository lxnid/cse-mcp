# Privacy

**Short version: cse-mcp collects nothing.**

- It runs on **your** computer. There is no cse-mcp server, account, analytics or telemetry.
- When your AI calls a tool, cse-mcp sends a request **directly from your computer to `www.cse.lk`**. The request contains only the tool's inputs, such as a stock symbol like `JKH.N0000`. It never contains your chats, files or personal details.
- Responses are kept in memory for 30 seconds to avoid repeat requests, then discarded. Nothing is written to disk.
- cse.lk is run by the Colombo Stock Exchange, and its own policies apply to requests it receives (such as your IP address).
- Your AI app (Claude, Cursor, etc.) sees the tool results, as with any tool. Its privacy policy covers that.

Questions? [Open an issue](https://github.com/lxnid/cse-mcp/issues).
