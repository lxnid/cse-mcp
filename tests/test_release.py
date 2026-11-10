"""Release safety checks: every place that names a version must agree.

A mismatch here would publish a PyPI package that the MCP Registry,
the Claude plugin or the .mcpb bundle doesn't point to.
"""

import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent


def project_version() -> str:
    return re.search(r'^version = "([^"]+)"', (ROOT / "pyproject.toml").read_text(), re.M).group(1)


def load(name: str) -> dict:
    return json.loads((ROOT / name).read_text())


def test_versions_match():
    version = project_version()
    server = load("server.json")
    assert load("manifest.json")["version"] == version
    assert server["version"] == version
    assert all(p["version"] == version for p in server["packages"])
    assert load("plugin/.claude-plugin/plugin.json")["version"] == version
    assert load("plugin/.mcp.json")["mcpServers"]["cse"]["args"] == [f"cse-mcp=={version}"]


def test_registry_ownership_line_in_readme():
    # The MCP Registry checks the PyPI README for this exact token.
    name = load("server.json")["name"]
    assert f"<!-- mcp-name: {name} -->" in (ROOT / "README.md").read_text()


@pytest.mark.parametrize("path", ["assets/icon.png", "plugin/icon.png"])
def test_icons_exist(path):
    assert (ROOT / path).read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"
