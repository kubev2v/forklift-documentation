#!/usr/bin/env python3
"""
replace_shared_snippets.py - Process shared snippets in MTV/Forklift documentation

This script finds snippet files (snip_*.adoc or snip-*.adoc) and can:
1. List all snippet files and their usage
2. Inline snippet content directly into including documents
3. Validate that all snippets are properly referenced

Adapted for MTV (Migration Toolkit for Virtualization) documentation structure.
"""

import argparse
import logging
import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple

# Configure logging
logging.basicConfig(
    format='%(levelname)s: %(message)s',
    level=logging.INFO,
    stream=sys.stdout
)
log = logging.getLogger(__name__)

# Regular expressions for AsciiDoc processing
INCLUDE_RE = re.compile(r'^include::([^\[]+)\[(.*?)\]', re.MULTILINE)
SNIPPET_FILE_PATTERN = re.compile(r'^snip[_-].*\.adoc$')
SNIPPET_CONTENT_TYPE_RE = re.compile(r'^:_mod-docs-content-type:\s*SNIPPET', re.MULTILINE)

# Default paths
DEFAULT_DOC_DIR = "documentation"
DEFAULT_MODULES_DIR = "modules"


def find_snippet_files(base_dir: Path) -> List[Path]:
    """
    Find all snippet files in the documentation directory.
    Snippets are identified by:
    - Filename starting with 'snip_' or 'snip-'
    - Or containing ':_mod-docs-content-type: SNIPPET' header
    """
    snippets = []
    
    for root, _, files in os.walk(base_dir):
        for filename in files:
            if filename.endswith('.adoc'):
                filepath = Path(root) / filename
                
                # Check if filename matches snippet pattern
                if SNIPPET_FILE_PATTERN.match(filename):
                    snippets.append(filepath)
                    continue
                
                # Check if file contains SNIPPET content type
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read(500)  # Read first 500 chars for header check
                        if SNIPPET_CONTENT_TYPE_RE.search(content):
                            snippets.append(filepath)
                except Exception as e:
                    log.warning(f"Could not read {filepath}: {e}")
    
    return sorted(snippets)


def find_snippet_usage(base_dir: Path, snippets: List[Path]) -> Dict[Path, List[Tuple[Path, str]]]:
    """
    Find where each snippet is used (included) in the documentation.
    Returns a dict mapping snippet path to list of (including_file, include_line) tuples.
    """
    usage = {snippet: [] for snippet in snippets}
    snippet_names = {snippet.name: snippet for snippet in snippets}
    
    for root, _, files in os.walk(base_dir):
        for filename in files:
            if not filename.endswith('.adoc'):
                continue
                
            filepath = Path(root) / filename
            
            # Skip snippet files themselves
            if filepath in snippets:
                continue
            
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                for match in INCLUDE_RE.finditer(content):
                    include_path = match.group(1)
                    include_name = Path(include_path).name
                    
                    if include_name in snippet_names:
                        snippet = snippet_names[include_name]
                        usage[snippet].append((filepath, match.group(0)))
                        
            except Exception as e:
                log.warning(f"Could not read {filepath}: {e}")
    
    return usage


def read_snippet_content(snippet_path: Path) -> str:
    """
    Read snippet file content, stripping the metadata header.
    """
    with open(snippet_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Remove the :_mod-docs-content-type: SNIPPET line if present
    content = SNIPPET_CONTENT_TYPE_RE.sub('', content)
    
    # Strip leading/trailing whitespace but preserve internal formatting
    return content.strip()


def inline_snippet(including_file: Path, snippet_path: Path, snippet_content: str, 
                   dry_run: bool = False) -> bool:
    """
    Replace an include directive with the actual snippet content.
    Returns True if replacement was made.
    """
    try:
        with open(including_file, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        log.error(f"Could not read {including_file}: {e}")
        return False
    
    snippet_name = snippet_path.name
    
    # Find and replace the include directive
    # Match include::path/to/snip_file.adoc[options]
    pattern = re.compile(
        rf'^include::([^\[]*{re.escape(snippet_name)})\[(.*?)\]',
        re.MULTILINE
    )
    
    def replace_include(match):
        options = match.group(2)
        # Handle leveloffset if present
        leveloffset_match = re.search(r'leveloffset=\+?(\d+)', options)
        if leveloffset_match:
            offset = int(leveloffset_match.group(1))
            # Adjust heading levels in snippet content
            adjusted_content = adjust_heading_levels(snippet_content, offset)
            return adjusted_content
        return snippet_content
    
    new_content = pattern.sub(replace_include, content)
    
    if new_content != content:
        if dry_run:
            log.info(f"Would inline {snippet_name} in {including_file}")
        else:
            with open(including_file, 'w', encoding='utf-8') as f:
                f.write(new_content)
            log.info(f"Inlined {snippet_name} in {including_file}")
        return True
    
    return False


def adjust_heading_levels(content: str, offset: int) -> str:
    """
    Adjust AsciiDoc heading levels by the given offset.
    """
    if offset == 0:
        return content
    
    def adjust_heading(match):
        equals = match.group(1)
        rest = match.group(2)
        new_level = '=' * (len(equals) + offset)
        return f"{new_level}{rest}"
    
    # Match headings at the start of a line
    return re.sub(r'^(=+)(.*)$', adjust_heading, content, flags=re.MULTILINE)


def list_snippets_command(args):
    """Handle the 'list' subcommand."""
    base_dir = Path(args.doc_dir)
    
    if not base_dir.exists():
        log.error(f"Documentation directory not found: {base_dir}")
        return 1
    
    snippets = find_snippet_files(base_dir)
    
    if not snippets:
        log.info("No snippet files found.")
        return 0
    
    print(f"\nFound {len(snippets)} snippet file(s):\n")
    
    if args.show_usage:
        usage = find_snippet_usage(base_dir, snippets)
        for snippet in snippets:
            uses = usage[snippet]
            relative_path = snippet.relative_to(base_dir.parent) if base_dir.parent in snippet.parents else snippet
            print(f"  {relative_path}")
            if uses:
                print(f"    Used in {len(uses)} file(s):")
                for including_file, _ in uses:
                    rel_inc = including_file.relative_to(base_dir.parent) if base_dir.parent in including_file.parents else including_file
                    print(f"      - {rel_inc}")
            else:
                print("    ⚠ Not used in any files")
            print()
    else:
        for snippet in snippets:
            relative_path = snippet.relative_to(base_dir.parent) if base_dir.parent in snippet.parents else snippet
            print(f"  {relative_path}")
    
    return 0


def inline_command(args):
    """Handle the 'inline' subcommand."""
    base_dir = Path(args.doc_dir)
    
    if not base_dir.exists():
        log.error(f"Documentation directory not found: {base_dir}")
        return 1
    
    snippets = find_snippet_files(base_dir)
    
    if not snippets:
        log.info("No snippet files found.")
        return 0
    
    usage = find_snippet_usage(base_dir, snippets)
    
    # Filter to specific snippet if provided
    if args.snippet:
        target_snippets = [s for s in snippets if args.snippet in s.name]
        if not target_snippets:
            log.error(f"Snippet not found: {args.snippet}")
            return 1
    else:
        target_snippets = snippets
    
    replaced_count = 0
    for snippet in target_snippets:
        uses = usage[snippet]
        if not uses:
            continue
            
        snippet_content = read_snippet_content(snippet)
        
        for including_file, _ in uses:
            if inline_snippet(including_file, snippet, snippet_content, args.dry_run):
                replaced_count += 1
    
    if args.dry_run:
        print(f"\nWould replace {replaced_count} include(s)")
    else:
        print(f"\nReplaced {replaced_count} include(s)")
    
    return 0


def validate_command(args):
    """Handle the 'validate' subcommand."""
    base_dir = Path(args.doc_dir)
    
    if not base_dir.exists():
        log.error(f"Documentation directory not found: {base_dir}")
        return 1
    
    snippets = find_snippet_files(base_dir)
    usage = find_snippet_usage(base_dir, snippets)
    
    errors = []
    warnings = []
    
    # Check for unused snippets
    for snippet, uses in usage.items():
        if not uses:
            warnings.append(f"Unused snippet: {snippet.name}")
    
    # Check for broken snippet includes
    for root, _, files in os.walk(base_dir):
        for filename in files:
            if not filename.endswith('.adoc'):
                continue
            
            filepath = Path(root) / filename
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                for match in INCLUDE_RE.finditer(content):
                    include_path = match.group(1)
                    include_name = Path(include_path).name
                    
                    if SNIPPET_FILE_PATTERN.match(include_name):
                        # This looks like a snippet include, check if it exists
                        full_path = (filepath.parent / include_path).resolve()
                        if not full_path.exists():
                            errors.append(f"Broken snippet include in {filepath.name}: {include_path}")
                            
            except Exception as e:
                log.warning(f"Could not read {filepath}: {e}")
    
    # Print results
    print(f"\nValidation Results for {base_dir}:")
    print(f"  Snippets found: {len(snippets)}")
    print(f"  Errors: {len(errors)}")
    print(f"  Warnings: {len(warnings)}")
    
    if errors:
        print("\nErrors:")
        for error in errors:
            print(f"  ❌ {error}")
    
    if warnings:
        print("\nWarnings:")
        for warning in warnings:
            print(f"  ⚠ {warning}")
    
    return 1 if errors else 0


def setup_parser() -> argparse.ArgumentParser:
    """Set up command-line argument parser."""
    parser = argparse.ArgumentParser(
        description="Process shared snippets in MTV/Forklift documentation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # List all snippet files
  python replace_shared_snippets.py list
  
  # List snippets with usage information
  python replace_shared_snippets.py list --show-usage
  
  # Inline all snippets (dry run)
  python replace_shared_snippets.py inline --dry-run
  
  # Inline a specific snippet
  python replace_shared_snippets.py inline --snippet snip_qemu-guest-agent.adoc
  
  # Validate snippet references
  python replace_shared_snippets.py validate
"""
    )
    
    parser.add_argument(
        '--doc-dir',
        default=DEFAULT_DOC_DIR,
        help=f'Documentation directory (default: {DEFAULT_DOC_DIR})'
    )
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Enable verbose output'
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # List command
    list_parser = subparsers.add_parser('list', help='List all snippet files')
    list_parser.add_argument(
        '--show-usage', '-u',
        action='store_true',
        help='Show where each snippet is used'
    )
    
    # Inline command
    inline_parser = subparsers.add_parser('inline', help='Inline snippets into including files')
    inline_parser.add_argument(
        '--dry-run', '-n',
        action='store_true',
        help='Show what would be done without making changes'
    )
    inline_parser.add_argument(
        '--snippet', '-s',
        help='Process only the specified snippet file'
    )
    
    # Validate command
    validate_parser = subparsers.add_parser('validate', help='Validate snippet references')
    
    return parser


def main():
    parser = setup_parser()
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    if args.command == 'list':
        return list_snippets_command(args)
    elif args.command == 'inline':
        return inline_command(args)
    elif args.command == 'validate':
        return validate_command(args)
    else:
        parser.print_help()
        return 0


if __name__ == "__main__":
    sys.exit(main())
