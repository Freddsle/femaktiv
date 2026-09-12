#!/usr/bin/env python3
"""List existing in-repository files for constant Depmesh source roots."""

import argparse
import os
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
EXCLUDED_DIRS = {
    ".git", ".session", ".agents", ".codex", "node_modules", ".next",
    "dist", "build", "coverage", "playwright-report", "test-results",
    ".venv", "__pycache__", ".cache", ".local", ".ruff_cache",
    ".pytest_cache", "staticfiles",
}


def eligible(path):
    relative = path.relative_to(ROOT)
    return (
        not EXCLUDED_DIRS.intersection(relative.parts)
        and path.name != ".env"
        and not path.name.startswith(".env.")
        and path.suffix not in {".pyc", ".pem", ".key", ".mo", ".sqlite", ".sqlite3", ".db"}
        and not path.name.endswith(tuple(extension + ending for extension in (".sqlite", ".sqlite3", ".db") for ending in ("-wal", "-shm", "-journal")))
        and path.is_file()
        and path.resolve().is_relative_to(ROOT)
    )


def discover(arguments, root_files=False):
    found = set()

    def add(path):
        if eligible(path):
            found.add("@/" + path.relative_to(ROOT).as_posix())

    if root_files:
        for path in ROOT.iterdir():
            add(path)
    for argument in arguments:
        path = ROOT / argument
        if Path(argument).is_absolute() or ".." in Path(argument).parts:
            raise ValueError(f"Expected a relative discovery root: {argument}")
        if not path.resolve().is_relative_to(ROOT):
            raise ValueError(f"Discovery root is outside the repository: {argument}")
        if EXCLUDED_DIRS.intersection(path.relative_to(ROOT).parts):
            continue
        if path.is_dir():
            if path.is_symlink():
                raise ValueError(f"Discovery roots must not be directory symlinks: {argument}")
            for directory, dirs, filenames in os.walk(path, onerror=raise_walk_error):
                dirs[:] = [name for name in dirs if name not in EXCLUDED_DIRS and not (Path(directory) / name).is_symlink()]
                for name in filenames:
                    add(Path(directory) / name)
        else:
            add(path)
    return sorted(found)


def raise_walk_error(error):
    raise error


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root-files", action="store_true", help="Include eligible files directly in the repository root.")
    parser.add_argument("paths", nargs="*", help="Literal repository-relative files or directories; missing paths return no results.")
    args = parser.parse_args()
    for artifact in discover(args.paths, args.root_files):
        print(artifact)


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError) as error:
        print(f"File discovery failed: {error}", file=sys.stderr)
        sys.exit(1)
