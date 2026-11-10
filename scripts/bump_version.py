"""Set a new version everywhere it's written down.

    uv run scripts/bump_version.py 0.2.0

Then add a CHANGELOG entry, commit, and tag:  git tag v0.2.0 && git push --tags
"""

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# file -> regex whose group 1 is the text right before the version
FILES = {
    "manifest.json": r'("version": ")[^"]+',
    "server.json": r'("version": ")[^"]+',
    "plugin/.claude-plugin/plugin.json": r'("version": ")[^"]+',
    "plugin/.mcp.json": r"(cse-mcp==)[\w.]+",
}


def main() -> None:
    if len(sys.argv) != 2 or not re.fullmatch(r"\d+\.\d+\.\d+", sys.argv[1]):
        sys.exit("usage: uv run scripts/bump_version.py X.Y.Z")
    new = sys.argv[1]

    subprocess.run(["uv", "version", new], cwd=ROOT, check=True)  # pyproject.toml + uv.lock
    for name, pattern in FILES.items():
        path = ROOT / name
        text, count = re.subn(pattern, rf"\g<1>{new}", path.read_text())
        if not count:
            sys.exit(f"no version found in {name}")
        path.write_text(text)
        print(f"updated {name}")


if __name__ == "__main__":
    main()
