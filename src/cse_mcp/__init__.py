"""cse-mcp: live Colombo Stock Exchange data for AI assistants, over MCP."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("cse-mcp")
except PackageNotFoundError:  # running from a source tree that isn't installed
    __version__ = "0.0.0"
