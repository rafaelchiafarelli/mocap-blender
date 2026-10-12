"""Shared start of every inblender script: the repository on sys.path, the arguments after `--`."""

import sys
from pathlib import Path


def args() -> list[str]:
    root = str(Path(__file__).resolve().parents[2])
    if root not in sys.path:
        sys.path.insert(0, root)
    return sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []


def result(key: str, value) -> None:
    print(f"RESULT {key}={value}", flush=True)
