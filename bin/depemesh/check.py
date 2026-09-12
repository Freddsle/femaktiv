#!/usr/bin/env python3
"""Check specification links and Depmesh behavior without changing the repository."""

import argparse
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
from urllib.parse import unquote, urlsplit


ROOT = Path(__file__).resolve().parents[2]
INVERSES = {
    "governed_by": "governs",
    "governs": "governed_by",
    "tested_by": "tests",
    "tests": "tested_by",
}
EXCLUDED_DIRS = {
    ".git", ".session", ".agents", ".codex", "node_modules", ".next",
    "dist", "build", "coverage", "playwright-report", "test-results",
    ".venv", "__pycache__", ".cache", ".local", ".ruff_cache",
    ".pytest_cache", "staticfiles",
}
META = "@/specs/meta/general.md"
RELATIONS = "@/specs/behavior/files_relations.md"
WORKFLOWS = "@/specs/general/workflows.md"
HISTORICAL = "@/00_initial/FEMAKTIV_BUILD_SPEC.md"
PRODUCT = "@/specs/behavior/platform.md"
LIVE = "@/specs/behavior/live_chat.md"


def require(condition, message):
    if not condition:
        raise ValueError(message)


def excluded(artifact):
    path = Path(artifact.removeprefix("@/"))
    return (
        bool(EXCLUDED_DIRS.intersection(path.parts))
        or path.name == ".env"
        or path.name.startswith(".env.")
        or path.suffix in {".pyc", ".pem", ".key", ".mo", ".sqlite", ".sqlite3", ".db"}
        or path.name.endswith(tuple(extension + ending for extension in (".sqlite", ".sqlite3", ".db") for ending in ("-wal", "-shm", "-journal")))
    )


def records(root, *args):
    result = subprocess.run(
        ["depmesh", "-p", "automation", "--config", str(root / "depmesh.toml"), *args],
        cwd=root, capture_output=True, text=True, timeout=30,
    )
    require(result.returncode == 0, f"Depmesh {' '.join(args)} failed:\n{result.stderr}{result.stdout}")
    rows = [json.loads(line) for line in result.stdout.splitlines() if line.strip()]
    require(not result.stderr.strip(), f"Depmesh diagnostics: {result.stderr}")
    require(all(row.get("type") in {"relation", "dependency"} for row in rows), f"Unexpected Depmesh output: {rows}")
    return rows


class Graph:
    def __init__(self, root):
        self.root = root
        self.cache = {}
        names = {row["id"] for row in records(root, "relations")}
        require(names == set(INVERSES), f"Unexpected relation vocabulary: {names}")

    def query(self, artifact):
        if artifact not in self.cache:
            edges = {name: set() for name in INVERSES}
            for row in records(self.root, "dependencies", artifact):
                require(row["relation"] in edges, f"Unknown relation in {row}")
                edges[row["relation"]].add(row["dependency"])
            self.cache[artifact] = edges
        return self.cache[artifact]

    def expect(self, artifact, relation, expected):
        actual = self.query(artifact)[relation]
        require(actual == set(expected), f"{artifact} {relation}: expected {sorted(expected)}, got {sorted(actual)}")

    def verify(self, artifacts):
        edge_count = 0
        for artifact in artifacts:
            for relation, targets in self.query(artifact).items():
                require(not excluded(artifact) or not targets, f"Excluded input has edges: {artifact}")
                for target in targets:
                    require(target.startswith("@/") and not excluded(target), f"Invalid target: {target}")
                    path = (self.root / target[2:]).resolve()
                    require(path.is_relative_to(self.root) and path.is_file(), f"Target is missing or outside the repo: {target}")
                    require(artifact != target, f"Self-edge: {artifact}")
                    require(artifact in self.query(target)[INVERSES[relation]], f"Missing inverse: {artifact} {relation} {target}")
                    edge_count += 1
        return edge_count


def inventory(root):
    result = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
        cwd=root, capture_output=True, text=True, check=True, timeout=30,
    )
    return sorted({"@/" + name for name in result.stdout.split("\0") if name and (root / name).is_file() and not excluded("@/" + name)})


def check_current_relations():
    graph = Graph(ROOT)
    artifacts = inventory(ROOT)
    edges = graph.verify(artifacts)
    expected = {
        "@/README.md": {PRODUCT},
        "@/depmesh.toml": {RELATIONS},
        "@/donna.toml": {WORKFLOWS},
        "@/AGENTS.md": {META, RELATIONS, WORKFLOWS},
        "@/bin/depemesh/check.py": {RELATIONS},
        "@/bin/depemesh/files.py": {RELATIONS},
    }
    for artifact, owners in expected.items():
        # During setup, the workflow catalogue is written after configuration.
        existing_owners = {owner for owner in owners if (ROOT / owner[2:]).is_file()}
        graph.expect(artifact, "governed_by", existing_owners)
    for artifact in artifacts:
        if artifact.startswith("@/specs/") and artifact.endswith(".md"):
            graph.expect(artifact, "governed_by", set() if artifact == META else {META})
        if artifact.startswith("@/workflows/") and artifact.endswith(".donna.md"):
            graph.expect(artifact, "governed_by", {WORKFLOWS} if (ROOT / WORKFLOWS[2:]).is_file() else set())
    print(f"PASS: current graph ({len(artifacts)} files, {edges} directed edges)")


def check_fixtures():
    with tempfile.TemporaryDirectory(prefix="femaktiv-depmesh-") as directory:
        root = Path(directory).resolve()
        shutil.copyfile(ROOT / "depmesh.toml", root / "depmesh.toml")
        pairs = [
            ("lib/contracts.ts", "tests/unit/lib/contracts.test.ts"),
            ("components/question-form.tsx", "tests/unit/components/question-form.test.tsx"),
            ("src/app/api/intake/route.ts", "tests/unit/src/app/api/intake/route.test.ts"),
            ("app/(demo)/page.tsx", "tests/unit/app/(demo)/page.test.tsx"),
            ("app/[slug]/page.tsx", "tests/unit/app/[slug]/page.test.tsx"),
            ("src/lib/meal ideas.ts", "tests/unit/src/lib/meal ideas.test.ts"),
            ("src/.internal.ts", "tests/unit/src/.internal.test.ts"),
            ("src/.helpers/meal.ts", "tests/unit/src/.helpers/meal.test.ts"),
            ("accounts/models.py", "tests/unit/accounts/test_models.py"),
            ("chats/services.py", "tests/unit/chats/test_services.py"),
            ("chats/management/commands/evaluate_live_chat.py", "tests/unit/chats/management/commands/test_evaluate_live_chat.py"),
            ("notes/forms.py", "tests/unit/notes/test_forms.py"),
            ("config/settings.py", "tests/unit/config/test_settings.py"),
            ("pages/nested/[slug]/content.py", "tests/unit/pages/nested/[slug]/test_content.py"),
            ("bin/depemesh/check.py", "tests/unit/bin/depemesh/test_check.py"),
            ("manage.py", "tests/unit/test_manage.py"),
        ]
        excluded_paths = [f"src/{name}/hidden.ts" for name in EXCLUDED_DIRS]
        excluded_paths += ["src/.env", "src/.env.local", "src/private.pem", "src/private.key", "src/cache.pyc", "accounts/db.sqlite3", "accounts/db.sqlite3-wal", "accounts/db.db-journal", "locale/de/LC_MESSAGES/django.mo"]
        names = [
            META[2:], RELATIONS[2:], WORKFLOWS[2:], PRODUCT[2:], LIVE[2:], HISTORICAL[2:],
            "content/evidence.json", "tests/e2e/test_live_chat.py", "templates/chats/live_context.html", "templates/chats/cited_reply.html", "static/css/site.css",
            "specs/intro.md", "README.md", "AGENTS.md", "donna.toml",
            "workflows/example.donna.md", "bin/depemesh/check.py", "bin/depemesh/files.py",
            "tests/unit/bin/depemesh/test_check.py", "00_initial/unstructured_overview.md",
            "app/s/page.tsx", "tests/unit/app/s/page.test.tsx",  # A glob decoy for [slug].
            "src/no-test.ts", "tests/unit/src/orphan.test.ts", "lib/local.test.ts",
            "tests/unit/lib/local.test.test.ts", "tests/e2e/demo.spec.ts",
            "package.json", "vitest.config.ts", "src/data/example.json", "content/examples.json",
            "pyproject.toml", "uv.lock", ".python-version", "Makefile", "bin/check",
            "pages/views.py", "accounts/views.py", "notes/views.py", "chats/views.py",
            "templates/base.html", "static/js/chat.js", "locale/de/LC_MESSAGES/django.po",
            "docs/VALIDATION.md", "tests/e2e/test_platform.py", "tests/unit/pages/test_orphan.py",
            "accounts/test_helper.py", "tests/unit/accounts/test_test_helper.py",
        ] + excluded_paths + [name for pair in pairs for name in pair]
        for name in names:
            path = root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("fixture\n", encoding="utf-8")
        shutil.copyfile(ROOT / "bin/depemesh/files.py", root / "bin/depemesh/files.py")
        graph = Graph(root)
        for source, test in pairs:
            graph.expect("@/" + source, "tested_by", {"@/" + test})
            graph.expect("@/" + test, "tests", {"@/" + source})
        graph.expect("@/src/no-test.ts", "tested_by", set())
        graph.expect("@/tests/unit/src/orphan.test.ts", "tests", set())
        graph.expect("@/src/orphan.ts", "governed_by", {HISTORICAL})
        graph.expect("@/src/orphan.ts", "tested_by", {"@/tests/unit/src/orphan.test.ts"})
        graph.expect("@/lib/local.test.ts", "tested_by", set())
        graph.expect("@/tests/unit/lib/local.test.test.ts", "tests", set())
        graph.expect("@/tests/e2e/demo.spec.ts", "tests", set())
        graph.expect("@/tests/unit/bin/depemesh/test_check.py", "governed_by", {RELATIONS})
        graph.expect("@/00_initial/unstructured_overview.md", "governed_by", set())
        for name in ["src/no-test.ts", "package.json", "vitest.config.ts", "src/data/example.json"]:
            graph.expect("@/" + name, "governed_by", {HISTORICAL})
        for name in ["README.md", "manage.py", "pyproject.toml", "uv.lock", ".python-version", "Makefile", "bin/check", "accounts/models.py", "chats/services.py", "notes/forms.py", "config/settings.py", "content/examples.json", "templates/base.html", "static/js/chat.js", "locale/de/LC_MESSAGES/django.po", "docs/VALIDATION.md", "tests/e2e/test_platform.py"]:
            graph.expect("@/" + name, "governed_by", {PRODUCT, LIVE} if name in {"accounts/models.py", "chats/services.py", "config/settings.py", "static/js/chat.js"} else {PRODUCT})
        browser_sources = {"@/" + name for name in ["accounts/views.py", "notes/views.py", "chats/views.py", "pages/views.py", "static/js/chat.js", "templates/base.html"]}
        for name in ["content/evidence.json", "templates/chats/live_context.html", "templates/chats/cited_reply.html", "static/css/site.css", "chats/management/commands/evaluate_live_chat.py", "tests/e2e/test_live_chat.py"]:
            graph.expect("@/" + name, "governed_by", {PRODUCT, LIVE})
        graph.expect("@/chats/future_adapter.py", "governed_by", {PRODUCT, LIVE})
        graph.expect("@/tests/e2e/test_platform.py", "tests", browser_sources)
        for artifact in browser_sources:
            graph.expect(artifact, "tested_by", {"@/tests/e2e/test_platform.py", "@/tests/e2e/test_live_chat.py"} if artifact in {"@/chats/views.py", "@/static/js/chat.js"} else {"@/tests/e2e/test_platform.py"})
        graph.expect("@/accounts/test_helper.py", "tested_by", set())
        graph.expect("@/tests/unit/accounts/test_test_helper.py", "tests", set())
        graph.expect("@/pages/orphan.py", "governed_by", {PRODUCT})
        graph.expect("@/pages/orphan.py", "tested_by", {"@/tests/unit/pages/test_orphan.py"})
        graph.expect("@/tests/unit/pages/test_orphan.py", "tests", set())
        for name in excluded_paths:
            require(not any(graph.query("@/" + name).values()), f"Excluded fixture has edges: {name}")
        graph.verify(["@/" + name for name in names] + ["@/depmesh.toml"])
        require("@/src/orphan.ts" not in graph.query(HISTORICAL)["governs"], "Reverse lookup included a missing file")
        require("@/pages/orphan.py" not in graph.query(PRODUCT)["governs"], "Reverse lookup included a missing Python file")
        # Discovery must work from another cwd without changing path identity.
        discovery = subprocess.run([sys.executable, str(root / "bin/depemesh/files.py"), "accounts"], cwd="/tmp", capture_output=True, text=True, timeout=30)
        require(discovery.returncode == 0 and "@/accounts/models.py" in discovery.stdout.splitlines(), "Discovery failed outside the repository root")
        require(not any(excluded(line) for line in discovery.stdout.splitlines()), "Discovery emitted excluded files")
        # Requery after deletion: existing-path output must not retain stale targets.
        (root / pairs[0][1]).unlink()
        Graph(root).expect("@/" + pairs[0][0], "tested_by", set())
        result = subprocess.run(
            ["depmesh", "-p", "automation", "--config", str(root / "depmesh.toml"), "dependencies", "--relation", "unknown_relation", "@/README.md"],
            cwd=root, capture_output=True, text=True, timeout=30,
        )
        require(result.returncode != 0, "Unknown relation was accepted")
        print(f"PASS: isolated relation fixtures ({len(pairs)} source/test pairs, exclusions, missing/deleted targets, unknown relation)")


def without_fences(text):
    return re.sub(r"^(`{3,}|~{3,})[^\n]*\n.*?^\1\s*$", "", text, flags=re.MULTILINE | re.DOTALL)


def local_links(path):
    text = without_fences(path.read_text(encoding="utf-8"))
    for destination in re.findall(r"\[[^\]\n]*\]\(([^\s)]+)\)", text):
        parsed = urlsplit(destination)
        if parsed.scheme or parsed.netloc or not parsed.path:
            continue
        target = (path.parent / unquote(parsed.path)).resolve()
        require(target.is_relative_to(ROOT) and target.is_file(), f"Broken or external local link in {path.relative_to(ROOT)}: {destination}")
        yield target


def check_specs():
    specs = sorted((ROOT / "specs").rglob("*.md"))
    expected = {"specs/behavior/live_chat.md", "specs/intro.md", "specs/meta/general.md", "specs/behavior/files_relations.md", "specs/behavior/platform.md", "specs/general/workflows.md"}
    require(expected <= {str(path.relative_to(ROOT)) for path in specs}, "A required specification is missing")
    for path in specs:
        content = without_fences(path.read_text(encoding="utf-8"))
        require(len(re.findall(r"^# [^\n]+$", content, re.MULTILINE)) == 1, f"Expected one H1 in {path}")
        headings = re.findall(r"^## ([^\n]+)$", content, re.MULTILINE)
        require(headings[:2] == ["Goal of the document", "Scope"], f"Incorrect opening sections in {path}")
        list(local_links(path))
    indexed = set(local_links(ROOT / "specs/intro.md"))
    require(set(specs) <= indexed, f"Unindexed specifications: {set(specs) - indexed}")
    require((ROOT / "AGENTS.md").is_file(), "AGENTS.md is missing")
    list(local_links(ROOT / "AGENTS.md"))
    for path in (ROOT / "workflows").rglob("*.donna.md"):
        list(local_links(path))
    print(f"PASS: specification structure, index, and local file links ({len(specs)} specifications)")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--relations-only", action="store_true", help="Check relations during setup before all specifications exist.")
    args = parser.parse_args()
    require(shutil.which("depmesh") is not None, "depmesh must be installed and on PATH")
    if not args.relations_only:
        check_specs()
    check_current_relations()
    check_fixtures()


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError, subprocess.SubprocessError) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        sys.exit(1)
