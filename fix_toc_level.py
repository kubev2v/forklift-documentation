#!/usr/bin/env python3
"""
Fix TOC (table of contents) depth in MTV/forklift-documentation so that no heading
exceeds the CQA-recommended maximum (3 levels), without changing any leveloffset
in assemblies or masters. The published structure (e.g. docs.redhat.com) is preserved.

Strategy:
- Do NOT modify leveloffset in any include:: directives.
- Traverse from each master.adoc, resolve include:: paths (same as check_toc_level.py),
  and record the maximum level_offset at which each module under documentation/modules/
  is included.
- In each module, cap heading levels so that max_offset + heading_level <= 3.
  Headings deeper than max_allowed are promoted (e.g. ==== -> === or ==) so the
  effective TOC level never exceeds 3. Shared modules use the strictest constraint
  (deepest inclusion).

Usage:
  python fix_toc_level.py [--dry-run] [path]
  path: optional; limit to documentation/doc-<name> or all documentation if omitted.

Reference: CQA 2.4, PREVIEW MTVTOCChecker, kubev2v/forklift-documentation.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

DOCS_DIR = "documentation"
MODULES_DIR = "documentation/modules"
DOCUMENT_ATTRIBUTES = "documentation/modules/common-attributes.adoc"
MAX_TOC_LEVEL = 3


def find_repo_root(start: Path) -> Path | None:
    """Find repo root: directory containing documentation/ with doc-*/master.adoc."""
    current = start.resolve()
    for _ in range(30):
        docs = current / DOCS_DIR
        if docs.is_dir() and any(docs.glob("doc-*/master.adoc")):
            return current
        parent = current.parent
        if parent == current:
            break
        current = parent
    return None


def resolve_include_path(repo_root: Path, inc_path: str, from_file: Path) -> Path | None:
    """Resolve include path relative to the including file."""
    path = inc_path.strip()
    if not path:
        return None
    candidate = (from_file.parent / path).resolve()
    if not candidate.is_file():
        return None
    try:
        candidate.relative_to(repo_root)
    except ValueError:
        return None
    return candidate


def get_toclevels_from_master(content: str, default: int) -> int:
    """Parse :toclevels: from master content; return default if not set."""
    for line in content.splitlines():
        m = re.match(r":toclevels:\s*(\d+)", line.strip())
        if m:
            return int(m.group(1))
    return default


def get_toclevels_default(repo_root: Path) -> int:
    """Read :toclevels: from common-attributes or upstream; default 3."""
    for rel in (DOCUMENT_ATTRIBUTES, "documentation/upstream-attributes.adoc"):
        p = repo_root / rel
        if p.is_file():
            try:
                for line in p.read_text(encoding="utf-8", errors="replace").splitlines():
                    m = re.match(r":toclevels:\s*(\d+)", line.strip())
                    if m:
                        return int(m.group(1))
            except OSError:
                pass
    return MAX_TOC_LEVEL


def extract_includes(content: str) -> list[tuple[str, int]]:
    """Return list of (include_path, leveloffset). Skips // commented lines."""
    out = []
    for line in content.splitlines():
        if line.strip().startswith("//"):
            continue
        m = re.search(r"include::([^\]\[]+)\[(.*?)\]", line)
        if not m:
            continue
        path = m.group(1).strip()
        opts = (m.group(2) or "").strip()
        offset = 0
        for part in re.split(r"[, \t]+", opts):
            if part.startswith("leveloffset="):
                val = part.split("=", 1)[1].strip()
                if val.startswith("+") and val[1:].isdigit():
                    offset = int(val[1:])
                elif val.startswith("-") and val[1:].isdigit():
                    offset = -int(val[1:])
                elif val.isdigit():
                    offset = int(val)
                break
        out.append((path, offset))
    return out


def collect_max_offset_per_file(
    repo_root: Path,
    masters: list[Path],
    default_toclevels: int,
) -> dict[Path, int]:
    """Traverse from each master; for each file, record the maximum level_offset at which it is included.
    Shared modules must satisfy the deepest inclusion."""
    max_offset: dict[Path, int] = {}

    def visit(file_path: Path, level_offset: int, visited: set[Path]) -> None:
        if file_path in visited:
            return
        try:
            content = file_path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return
        visited.add(file_path)
        max_offset[file_path] = max(max_offset.get(file_path, level_offset), level_offset)
        for inc_path, offset in extract_includes(content):
            resolved = resolve_include_path(repo_root, inc_path, file_path)
            if resolved is not None:
                visit(resolved, level_offset + offset, visited)
        visited.discard(file_path)

    for master in masters:
        try:
            c = master.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        # Master sets base; first include level is 0 at master
        visit(master, 0, set())
    return max_offset


def is_module_path(repo_root: Path, path: Path) -> bool:
    """True if path is under documentation/modules/."""
    try:
        rel = path.relative_to(repo_root)
        return len(rel.parts) >= 2 and rel.parts[0] == DOCS_DIR and rel.parts[1] == "modules" and path.suffix == ".adoc"
    except ValueError:
        return False


def apply_fixes(
    repo_root: Path,
    path_arg: str | None,
    dry_run: bool,
) -> int:
    """
    Apply TOC depth fixes by capping headings in modules only. No leveloffset changes.
    Returns number of heading lines capped.
    """
    docs_dir = repo_root / DOCS_DIR
    modules_dir = repo_root / MODULES_DIR
    if not modules_dir.is_dir():
        return 0

    default_toclevels = get_toclevels_default(repo_root)
    if path_arg:
        p = (repo_root / path_arg).resolve()
        if not p.exists():
            return 0
        if p.is_file():
            masters = [p] if p.name == "master.adoc" else []
        else:
            masters = sorted(p.rglob("master.adoc"))
    else:
        masters = sorted((repo_root / DOCS_DIR).rglob("master.adoc"))

    # Compute max_offset per file (using current leveloffsets; we do not change them)
    max_offset = collect_max_offset_per_file(repo_root, masters, default_toclevels)

    # Cap headings only in modules under documentation/modules/
    num_heading_caps = 0
    for mod_file in sorted(modules_dir.rglob("*.adoc")):
        try:
            mod_file.relative_to(repo_root)
        except ValueError:
            continue
        if not is_module_path(repo_root, mod_file):
            continue
        offset = max_offset.get(mod_file, 0)
        max_allowed = max(1, MAX_TOC_LEVEL - offset)
        try:
            content = mod_file.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        new_lines = []
        file_caps = 0
        for line in content.splitlines():
            m = re.match(r"^(=+)\s+(.+)$", line)
            if m:
                level = len(m.group(1))
                title = m.group(2)
                if level > max_allowed:
                    new_lines.append("=" * max_allowed + " " + title)
                    file_caps += 1
                else:
                    new_lines.append(line)
            else:
                new_lines.append(line)
        num_heading_caps += file_caps
        if file_caps and not dry_run:
            mod_file.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
    return num_heading_caps


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Fix TOC depth (heading caps in modules only; no leveloffset changes).",
        epilog="Optional path: documentation/doc-Planning_your_migration or documentation/",
    )
    parser.add_argument("path", nargs="?", default=None, help="Limit to this doc directory or all")
    parser.add_argument("--dry-run", action="store_true", help="Report changes only, do not write")
    args = parser.parse_args()

    repo_root = find_repo_root(Path(__file__).resolve().parent)
    if repo_root is None:
        print("Error: repo root not found (documentation/ with doc-*/master.adoc)", file=sys.stderr)
        return 2
    n_cap = apply_fixes(repo_root, args.path, args.dry_run)
    print(f"Heading caps (modules only, no offset changes): {n_cap}")
    if args.dry_run:
        print("(Dry run; no files written.)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
