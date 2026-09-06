#!/usr/bin/env python3
"""
Release Notes Generator for Forklift/MTV Documentation

This script automates the generation of release notes from JIRA ticket exports.
It prompts for branch selection, MTV version, and processes CSV files containing
known issues and resolved issues. It creates a new git branch and generates all
necessary release notes files.

Outputs:
  - documentation/modules/rn-<x>-<y>.adoc          (x-stream header, e.g. 2.11)
  - documentation/modules/rn-<x>-<y>-<z>-resolved-issues.adoc (z-stream resolved)
  - documentation/modules/known-issues-<x>-<y>.adoc (known issues for x-stream)
  - documentation/doc-Release_notes/master.adoc    (updated to include new modules)

Usage:
  Interactive:  python generate_release_notes.py
  With options: python generate_release_notes.py --version 2.11.1 --base main \\
                  --resolved path/to/resolved.csv --known path/to/known.csv --yes
"""

import argparse
import os
import sys
import csv
import re
import subprocess
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from datetime import datetime


class ReleaseNotesGenerator:
    """
    Generates release notes from JIRA ticket exports.
    Handles branch creation, CSV parsing, AsciiDoc generation, and master.adoc updates.
    """

    def __init__(self, repo_path: str, non_interactive: bool = False):
        self.repo_path = Path(repo_path)
        self.docs_path = self.repo_path / "documentation"
        self.modules_path = self.docs_path / "modules"
        self.release_notes_path = self.docs_path / "doc-Release_notes"
        self.master_adoc_path = self.release_notes_path / "master.adoc"
        self.base_branch = None
        self.new_branch = None
        self.version = None
        # When True, skip interactive prompts (overwrite/continue/branch reuse)
        self.non_interactive = non_interactive

    def get_git_branches(self) -> List[str]:
        """Return sorted list of local and remote branch names (without remotes/ prefix)."""
        try:
            result = subprocess.run(
                ["git", "branch", "-a"],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=True
            )
            branches = []
            for line in result.stdout.split('\n'):
                branch = line.strip().replace('*', '').strip()
                if branch and not branch.startswith('remotes/origin/HEAD'):
                    # Remove 'remotes/origin/' prefix if present
                    if branch.startswith('remotes/origin/'):
                        branch = branch.replace('remotes/origin/', '')
                    if branch not in branches:
                        branches.append(branch)
            return sorted(branches)
        except subprocess.CalledProcessError:
            print("Warning: Could not fetch git branches. Continuing...")
            return []
    
    def select_branch(self) -> str:
        """Prompt user to select a base git branch (by number or by typing branch name)."""
        branches = self.get_git_branches()
        if not branches:
            branch = input("Enter base branch name: ").strip()
            return branch
        
        print("\nAvailable branches:")
        for i, branch in enumerate(branches, 1):
            print(f"  {i}. {branch}")
        
        while True:
            try:
                choice = input(f"\nSelect base branch (1-{len(branches)}) or enter custom branch name: ").strip()
                if choice.isdigit():
                    idx = int(choice) - 1
                    if 0 <= idx < len(branches):
                        return branches[idx]
                    else:
                        print(f"Invalid choice. Please enter a number between 1 and {len(branches)}")
                else:
                    # Custom branch name
                    return choice
            except ValueError:
                print("Invalid input. Please enter a number or branch name.")
    
    def create_release_branch(self, base_branch: str, version: str) -> str:
        """Create and checkout branch MTV-RN-<version> from base_branch. Reuses branch if it exists."""
        branch_name = f"MTV-RN-{version}"

        print(f"\nCreating new branch: {branch_name} from {base_branch}")

        try:
            # Checkout base branch first so new branch is created from it
            subprocess.run(
                ["git", "checkout", base_branch],
                cwd=self.repo_path,
                check=True,
                capture_output=True
            )
            
            # Fetch latest changes
            subprocess.run(
                ["git", "fetch", "origin", base_branch],
                cwd=self.repo_path,
                check=False,
                capture_output=True
            )
            
            # Create and checkout new branch
            subprocess.run(
                ["git", "checkout", "-b", branch_name],
                cwd=self.repo_path,
                check=True,
                capture_output=True
            )
            
            print(f"✓ Created and checked out branch: {branch_name}")
            return branch_name
            
        except subprocess.CalledProcessError as e:
            print(f"Error creating branch: {e.stderr.decode() if e.stderr else str(e)}")
            # Check if branch already exists
            result = subprocess.run(
                ["git", "branch", "--list", branch_name],
                cwd=self.repo_path,
                capture_output=True,
                text=True
            )
            if result.stdout.strip():
                response = 'y' if getattr(self, 'non_interactive', False) else input(f"Branch {branch_name} already exists. Use it? (y/n): ").strip().lower()
                if response == 'y':
                    subprocess.run(
                        ["git", "checkout", branch_name],
                        cwd=self.repo_path,
                        check=True
                    )
                    return branch_name
            raise
    
    def select_version(self) -> str:
        """Prompt user for MTV version; accepts X.Y or X.Y.Z (e.g. 2.11 or 2.11.1)."""
        while True:
            version = input("\nEnter MTV version (e.g., 2.11.1): ").strip()
            if re.match(r'^\d+\.\d+(\.\d+)?$', version):
                return version
            else:
                print("Invalid version format. Please use format like '2.11.1' or '2.11'")
    
    def parse_jira_csv(self, csv_path: str) -> List[Dict[str, str]]:
        """
        Parse JIRA CSV export into list of dicts with keys: key, summary, description, workaround.

        Expected CSV columns (names are matched case-insensitively):
          - Issue key (e.g. MTV-3915 or MTV-Test-1)
          - Summary/Title
          - Description
          - Workaround (optional; used for known issues)

        Delimiter is auto-detected. Returns list of ticket dicts; rows without a key are skipped.
        """
        tickets = []

        with open(csv_path, 'r', encoding='utf-8') as f:
            # Sniff delimiter (comma vs semicolon) from first 1KB
            sample = f.read(1024)
            f.seek(0)
            sniffer = csv.Sniffer()
            delimiter = sniffer.sniff(sample).delimiter
            
            reader = csv.DictReader(f, delimiter=delimiter)
            
            # Normalize column names (case-insensitive, strip whitespace)
            fieldnames = {name.lower().strip(): name for name in reader.fieldnames}
            
            for row in reader:
                ticket = {}
                
                # Find issue key
                key_fields = ['issue key', 'key', 'issue', 'ticket', 'jira key']
                ticket['key'] = None
                for field in key_fields:
                    if field in fieldnames:
                        ticket['key'] = row[fieldnames[field]].strip()
                        break
                
                if not ticket['key']:
                    print(f"Warning: Could not find issue key in row. Skipping row: {row}")
                    continue
                
                # Find summary/title
                summary_fields = ['summary', 'title', 'subject', 'name']
                ticket['summary'] = ""
                for field in summary_fields:
                    if field in fieldnames:
                        ticket['summary'] = row[fieldnames[field]].strip()
                        break
                
                # Find description
                desc_fields = ['description', 'details', 'body']
                ticket['description'] = ""
                for field in desc_fields:
                    if field in fieldnames:
                        ticket['description'] = row[fieldnames[field]].strip()
                        break
                
                # Find workaround (for known issues)
                workaround_fields = ['workaround', 'work around', 'resolution', 'solution']
                ticket['workaround'] = ""
                for field in workaround_fields:
                    if field in fieldnames:
                        ticket['workaround'] = row[fieldnames[field]].strip()
                        break
                
                tickets.append(ticket)
        
        return tickets
    
    def format_issue_text(self, summary: str, description: str, workaround: Optional[str] = None) -> str:
        """Format a single issue as AsciiDoc: title::, description, optional *Workaround:* block."""
        summary = summary.strip()
        description = description.strip()
        description = re.sub(r'<[^>]+>', '', description)
        lines = [f"{summary}::", ""]
        
        if description:
            # Capitalize first letter if needed
            if description and not description[0].isupper():
                description = description[0].upper() + description[1:]
            
            lines.append(description)
        
        if workaround:
            lines.append("")
            lines.append(f"*Workaround:* {workaround.strip()}")
        
        return "\n".join(lines)
    
    def generate_resolved_issues(self, tickets: List[Dict[str, str]], version: str) -> str:
        """Build AsciiDoc content for the resolved-issues module (z-stream, e.g. 2.11.1)."""
        version_safe = version.replace('.', '-')
        version_id = version.replace('.', '-')
        
        lines = [
            "// Module included in the following assemblies:",
            "//",
            "// * documentation/doc-Release_notes/master.adoc",
            "",
            ":_mod-docs-content-type: CONCEPT",
            f'[id="resolved-issues-{version_id}_{{context}}"]',
            f"= Resolved issues {version}",
            "",
            "[role=\"_abstract\"]",
            "Review the resolved issues in this release of {project-short}.",
            ""
        ]
        
        for ticket in tickets:
            issue_text = self.format_issue_text(
                ticket['summary'],
                ticket['description']
            )
            lines.append(issue_text)
            lines.append("+")
            lines.append(f"link:https://issues.redhat.com/browse/{ticket['key']}[{ticket['key']}]")
            lines.append("")
        
        return "\n".join(lines)
    
    def generate_known_issues(self, tickets: List[Dict[str, str]], version: str) -> str:
        """Build AsciiDoc content for known-issues module (version is x-stream, e.g. 2.11)."""
        version_id = version.split('.')[0] + '-' + version.split('.')[1]  # e.g., 2.11
        
        lines = [
            "// Module included in the following assemblies:",
            "//",
            "// * documentation/doc-Release_notes/master.adoc",
            "",
            ":_mod-docs-content-type: CONCEPT",
            f'[id="known-issues-{version_id}_{{context}}"]',
            "= Known issues",
            "",
            "[role=\"_abstract\"]",
            f"{{project-first}} {version} has the following known issues.",
            ""
        ]
        
        for ticket in tickets:
            issue_text = self.format_issue_text(
                ticket['summary'],
                ticket['description'],
                ticket.get('workaround', '')
            )
            lines.append(issue_text)
            lines.append("+")
            lines.append(f"link:https://issues.redhat.com/browse/{ticket['key']}[{ticket['key']}]")
            lines.append("")
        
        # Add comment about complete list
        lines.append("")
        lines.append("//For a complete list of all known issues in this release, see the list of link:https://issues.redhat.com/issues/?filter=12472621[Known Issues] in Jira.")
        lines.append("")
        
        return "\n".join(lines)
    
    def generate_release_notes_header(self, version: str) -> str:
        """Generate the x-stream release notes header (e.g. rn-2-11.adoc)."""
        version_major = '.'.join(version.split('.')[:2])  # e.g., 2.11
        version_id = version_major.replace('.', '-')
        
        lines = [
            "// Module included in the following assemblies:",
            "//",
            "// * documentation/doc-Release_notes/master.adoc",
            "",
            ":_mod-docs-content-type: CONCEPT",
            f'[id="rn-{version_id}_{{context}}"]',
            f"= {{project-full}} {version_major}",
            "",
            "[role=\"_abstract\"]",
            "The release notes describe technical changes, new features and enhancements, known issues, and resolved issues.",
            ""
        ]
        
        return "\n".join(lines)
    
    def update_master_adoc(self, version: str, has_resolved: bool, has_known: bool) -> bool:
        """
        Update documentation/doc-Release_notes/master.adoc to include:
        - x-stream header include (rn-<x>-<y>.adoc) if not already present (avoids duplicate)
        - z-stream resolved-issues include (rn-<x>-<y>-<z>-resolved-issues.adoc)
        - known-issues include (known-issues-<x>-<y>.adoc)
        """
        if not self.master_adoc_path.exists():
            print(f"Warning: master.adoc not found at {self.master_adoc_path}")
            return False
        
        version_major = '.'.join(version.split('.')[:2])  # e.g., 2.11
        version_safe = version.replace('.', '-')
        version_major_safe = version_major.replace('.', '-')
        
        # Read existing content
        with open(self.master_adoc_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check if this version already exists
        if f"rn-{version_major_safe}.adoc" in content:
            print(f"Warning: Release notes for version {version_major} already exist in master.adoc")
            response = 'y' if getattr(self, 'non_interactive', False) else input("Continue anyway? (y/n): ").strip().lower()
            if response != 'y':
                return False
        
        lines = content.split('\n')
        new_lines = []
        header_inserted = False
        resolved_inserted = False
        known_inserted = False
        i = 0
        while i < len(lines):
            line = lines[i]
            
            # Insert release notes header right after common-attributes (x-stream include, e.g. rn-2-11.adoc)
            if not header_inserted and line.strip() == 'include::modules/common-attributes.adoc[]':
                new_lines.append(line)
                j = i + 1
                while j < len(lines) and not lines[j].strip().startswith('include::modules/rn-'):
                    new_lines.append(lines[j])
                    j += 1
                # Avoid duplicate include (see e.g. PR #865): if rn-<x>-<y>.adoc is already
                # in master.adoc, copy it once and continue; do not insert a second include.
                if j < len(lines):
                    existing_include = lines[j].strip()
                    expected_include = f"include::modules/rn-{version_major_safe}.adoc[leveloffset=+1]"
                    if existing_include == expected_include:
                        new_lines.append(lines[j])
                        header_inserted = True
                        i = j + 1
                        continue
                # First rn- include is for an older version; insert our header before it
                new_lines.append("")
                new_lines.append(f"include::modules/rn-{version_major_safe}.adoc[leveloffset=+1]")
                header_inserted = True
                i = j
                continue
            
            # Insert z-stream resolved-issues include after the last existing resolved-issues include
            if has_resolved and not resolved_inserted:
                if '// Resolved issues by z-stream release' in line:
                    new_lines.append(line)
                    # Process until we find the last resolved issues include
                    j = i + 1
                    last_resolved_idx = -1
                    while j < len(lines):
                        if lines[j].strip().startswith('include::modules/rn-') and 'resolved-issues' in lines[j]:
                            last_resolved_idx = j
                        elif lines[j].strip().startswith('//') and 'Resolved' not in lines[j] and 'Security' not in lines[j]:
                            break
                        j += 1
                    
                    # Copy lines up to and including the last resolved issues include
                    k = i + 1
                    while k <= last_resolved_idx:
                        new_lines.append(lines[k])
                        k += 1
                    
                    # Insert new resolved issues
                    if last_resolved_idx >= 0:
                        new_lines.append("")
                        new_lines.append(f"include::modules/rn-{version_safe}-resolved-issues.adoc[leveloffset=+3]")
                        resolved_inserted = True
                    
                    i = k
                    continue
            
            # Ensure known-issues-<x>-<y>.adoc is included (replace or add)
            if has_known and not known_inserted:
                if '// Known issues by x-stream release' in line:
                    new_lines.append(line)
                    # Find and replace the known issues include
                    j = i + 1
                    while j < len(lines):
                        if lines[j].strip().startswith('include::modules/known-issues-'):
                            new_lines.append(f"include::modules/known-issues-{version_major_safe}.adoc[leveloffset=+2]")
                            known_inserted = True
                            j += 1
                            break
                        new_lines.append(lines[j])
                        j += 1
                    i = j
                    continue
            
            new_lines.append(line)
            i += 1
        
        # Fallback: insert resolved-issues include after any existing resolved-issues line
        if has_resolved and not resolved_inserted:
            # Find the resolved issues section and append
            for idx, line in enumerate(new_lines):
                if 'include::modules/rn-' in line and 'resolved-issues' in line:
                    # Insert after this line
                    new_lines.insert(idx + 1, "")
                    new_lines.insert(idx + 2, f"include::modules/rn-{version_safe}-resolved-issues.adoc[leveloffset=+3]")
                    resolved_inserted = True
                    break
        
        if has_known and not known_inserted:
            # Find and replace known issues
            for idx, line in enumerate(new_lines):
                if line.strip().startswith('include::modules/known-issues-'):
                    new_lines[idx] = f"include::modules/known-issues-{version_major_safe}.adoc[leveloffset=+2]"
                    known_inserted = True
                    break
        
        # Write updated content
        with open(self.master_adoc_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(new_lines))
            if new_lines and not new_lines[-1]:
                f.write('\n')
        
        print(f"✓ Updated: {self.master_adoc_path}")
        return True
    
    def extract_existing_issue_keys(self, filepath: Path) -> set:
        """Extract JIRA issue keys from AsciiDoc file (e.g. MTV-3915, MTV-Test-1) for deduplication."""
        issue_keys = set()
        if not filepath.exists():
            return issue_keys
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        # Match link:https://issues.redhat.com/browse/KEY[KEY]; KEY may be MTV-123 or MTV-Test-1
        pattern = r'link:https://issues\.redhat\.com/browse/([A-Z][A-Z0-9-]*-\d+)\['
        matches = re.findall(pattern, content)
        issue_keys.update(matches)
        
        return issue_keys
    
    def parse_existing_content(self, filepath: Path) -> tuple:
        """
        Parse existing AsciiDoc file to extract header and body.
        Returns (header_lines, body_lines, existing_issue_keys)
        """
        if not filepath.exists():
            return ([], [], set())
        
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # Extract issue keys
        existing_keys = self.extract_existing_issue_keys(filepath)
        
        # Find where the actual content starts (after abstract)
        header_end = 0
        for i, line in enumerate(lines):
            if '[role="_abstract"]' in line:
                # Header ends after the abstract line + 1
                header_end = i + 2
                break
        
        header_lines = [line.rstrip('\n') for line in lines[:header_end]]
        body_lines = [line.rstrip('\n') for line in lines[header_end:]]
        
        return (header_lines, body_lines, existing_keys)
    
    def merge_content(self, existing_header: List[str], existing_body: List[str], 
                     new_content: str, existing_keys: set) -> str:
        """
        Merge new content with existing content, avoiding duplicates.
        
        Args:
            existing_header: Header lines from existing file
            existing_body: Body lines from existing file
            new_content: New content to merge
            existing_keys: Set of existing issue keys to avoid duplicates
            
        Returns:
            Merged content as string
        """
        # Parse new content to extract issues
        new_lines = new_content.split('\n')
        
        # Find where issues start in new content (after abstract)
        new_issues_start = 0
        for i, line in enumerate(new_lines):
            if '[role="_abstract"]' in line:
                new_issues_start = i + 2
                break
        
        # Extract new issues (skip header)
        # Issue format: Title:: ... description ... + link:.../MTV-XXXX[MTV-XXXX]
        new_issues = []
        current_issue_lines = []
        current_issue_key = None
        
        i = new_issues_start
        while i < len(new_lines):
            line = new_lines[i]
            
            # Check if this line contains an issue key (end of an issue)
            issue_key_match = re.search(r'link:https://issues\.redhat\.com/browse/([A-Z][A-Z0-9-]*-\d+)\[', line)
            if issue_key_match:
                issue_key = issue_key_match.group(1)
                if issue_key not in existing_keys:
                    # This is a new issue - add all lines from start to this line
                    if current_issue_lines:
                        new_issues.extend(current_issue_lines)
                        new_issues.append(line)  # Add the link line
                        new_issues.append("")  # Add blank line after issue
                    current_issue_lines = []
                    current_issue_key = issue_key
                else:
                    # Duplicate issue, skip it - reset and continue
                    current_issue_lines = []
                    current_issue_key = None
                    # Skip until next issue (blank line or next title ending with ::)
                    i += 1
                    while i < len(new_lines) and not new_lines[i].strip().endswith('::'):
                        i += 1
                    i -= 1  # Back up one line
            else:
                # Check if this is the start of a new issue (title ending with ::)
                if line.strip().endswith('::') and current_issue_key is None:
                    # Start collecting a new issue
                    current_issue_lines = [line]
                elif current_issue_lines:
                    # Continue collecting current issue
                    current_issue_lines.append(line)
            
            i += 1
        
        # Add last issue if any (in case file doesn't end with link)
        if current_issue_lines and current_issue_key:
            new_issues.extend(current_issue_lines)
        
        # Merge: header + existing body + new issues
        merged_lines = existing_header.copy()
        if existing_body:
            # Remove trailing blank lines from existing body
            while existing_body and not existing_body[-1].strip():
                existing_body.pop()
            merged_lines.extend(existing_body)
            if new_issues:
                merged_lines.append("")  # Add spacing before new issues
        merged_lines.extend(new_issues)
        
        return '\n'.join(merged_lines)
    
    def append_to_file(self, filepath: Path, new_content: str, existing_keys: set) -> tuple:
        """
        Append new content to existing file, avoiding duplicates.
        
        Returns:
            (success: bool, new_count: int, existing_count: int)
        """
        # Parse existing content
        existing_header, existing_body, file_existing_keys = self.parse_existing_content(filepath)
        
        # Combine with provided existing_keys (in case we filtered before)
        all_existing_keys = existing_keys | file_existing_keys
        
        # Extract new issue keys from content
        new_keys = self.extract_existing_issue_keys_from_content(new_content)
        new_keys_to_add = new_keys - all_existing_keys
        
        if not new_keys_to_add:
            return (False, 0, len(all_existing_keys))
        
        # Merge content
        merged_content = self.merge_content(existing_header, existing_body, new_content, all_existing_keys)
        
        # Write merged content
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(merged_content)
        
        return (True, len(new_keys_to_add), len(all_existing_keys))
    
    def save_file(self, content: str, filename: str, append_mode: bool = True) -> bool:
        """
        Write content to documentation/modules/<filename>.
        If file exists and append_mode is True, merges new issues into existing (no duplicate keys).
        If append_mode is False and file exists, prompts to overwrite (or uses --yes).
        """
        filepath = self.modules_path / filename
        if filepath.exists():
            if append_mode:
                # Extract existing issue keys
                existing_keys = self.extract_existing_issue_keys(filepath)
                new_keys = self.extract_existing_issue_keys_from_content(content)
                new_keys_count = len(new_keys - existing_keys)
                existing_count = len(existing_keys)
                
                if new_keys_count > 0:
                    print(f"\n📄 File exists: {filepath}")
                    print(f"   Found {existing_count} existing issue(s), {new_keys_count} new issue(s)")
                    
                    # Append new content
                    success, added_count, total_existing = self.append_to_file(filepath, content, existing_keys)
                    
                    if success:
                        print(f"✓ Updated: {filepath} (appended {added_count} new issue(s))")
                        return True
                    else:
                        print(f"⚠️  No new issues to add to {filepath}")
                        return False
                else:
                    print(f"⚠️  File exists: {filepath}")
                    print(f"   All {len(new_keys)} issue(s) already exist in file. Skipping.")
                    return False
            else:
                # Overwrite mode
                print(f"\n⚠️  Warning: File already exists: {filepath}")
                response = 'y' if getattr(self, 'non_interactive', False) else input("Overwrite existing file? (y/n/backup): ").strip().lower()
                
                if response == 'n':
                    print(f"✗ Skipped: {filepath}")
                    return False
                elif response == 'backup' or response == 'b':
                    # Create backup
                    backup_path = filepath.with_suffix(filepath.suffix + '.backup')
                    import shutil
                    shutil.copy2(filepath, backup_path)
                    print(f"📋 Created backup: {backup_path}")
                elif response != 'y':
                    print(f"✗ Skipped: {filepath}")
                    return False
                
                # Write the file
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                print(f"✓ Updated: {filepath}")
                return True
        
        # File doesn't exist, create new
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"✓ Generated: {filepath}")
        return True
    
    def extract_existing_issue_keys_from_content(self, content: str) -> set:
        """Extract issue keys from content string."""
        issue_keys = set()
        pattern = r'link:https://issues\.redhat\.com/browse/([A-Z][A-Z0-9-]*-\d+)\['
        matches = re.findall(pattern, content)
        issue_keys.update(matches)
        return issue_keys
    
    def run(
        self,
        base_branch: Optional[str] = None,
        version: Optional[str] = None,
        resolved_csv: Optional[str] = None,
        known_csv: Optional[str] = None,
    ):
        """
        Run the full flow: branch selection, version, CSVs, then generate modules and update master.adoc.
        Pass base_branch, version, resolved_csv, known_csv to skip prompts (non-interactive).
        """
        print("=" * 60)
        print("Forklift/MTV Release Notes Generator")
        print("=" * 60)
        
        # Step 1: Select base branch
        print("\n[Step 1] Base Branch Selection")
        self.base_branch = base_branch if base_branch is not None else self.select_branch()
        print(f"Selected base branch: {self.base_branch}")
        
        # Step 2: Select version
        print("\n[Step 2] Version Selection")
        self.version = version if version is not None else self.select_version()
        print(f"Selected version: {self.version}")
        
        # Step 3: Create release branch
        print("\n[Step 3] Creating Release Branch")
        self.new_branch = self.create_release_branch(self.base_branch, self.version)
        
        # Step 4: Upload resolved issues
        print("\n[Step 4] Resolved Issues")
        if resolved_csv is None:
            resolved_file = input("Enter path to resolved issues CSV file (or press Enter to skip): ").strip()
        else:
            resolved_file = resolved_csv
        resolved_tickets = []
        if resolved_file:
            if os.path.exists(resolved_file):
                print(f"Processing resolved issues from: {resolved_file}")
                resolved_tickets = self.parse_jira_csv(resolved_file)
                print(f"Found {len(resolved_tickets)} resolved issues")
            else:
                print(f"Error: File not found: {resolved_file}")
        
        # Step 5: Upload known issues
        print("\n[Step 5] Known Issues")
        if known_csv is None:
            known_file = input("Enter path to known issues CSV file (or press Enter to skip): ").strip()
        else:
            known_file = known_csv
        known_tickets = []
        if known_file:
            if os.path.exists(known_file):
                print(f"Processing known issues from: {known_file}")
                known_tickets = self.parse_jira_csv(known_file)
                print(f"Found {len(known_tickets)} known issues")
            else:
                print(f"Error: File not found: {known_file}")
        
        if not resolved_tickets and not known_tickets:
            print("\nNo issues to process. Exiting.")
            print(f"You are now on branch: {self.new_branch}")
            return
        
        # Step 6: Generate files
        print("\n[Step 6] Generating Release Notes Files")
        
        files_saved = []
        
        # Generate release notes header (don't append, always overwrite if exists)
        version_major = '.'.join(self.version.split('.')[:2])  # e.g., 2.11
        header_content = self.generate_release_notes_header(self.version)
        header_filename = f"rn-{version_major.replace('.', '-')}.adoc"
        if self.save_file(header_content, header_filename, append_mode=False):
            files_saved.append(header_filename)
        
        # Generate resolved issues (append mode - merge with existing)
        if resolved_tickets:
            version_safe = self.version.replace('.', '-')
            resolved_content = self.generate_resolved_issues(resolved_tickets, self.version)
            resolved_filename = f"rn-{version_safe}-resolved-issues.adoc"
            if self.save_file(resolved_content, resolved_filename, append_mode=True):
                files_saved.append(resolved_filename)
        
        # Generate known issues (append mode - merge with existing)
        if known_tickets:
            known_content = self.generate_known_issues(known_tickets, version_major)
            known_filename = f"known-issues-{version_major.replace('.', '-')}.adoc"
            if self.save_file(known_content, known_filename, append_mode=True):
                files_saved.append(known_filename)
        
        if not files_saved:
            print("\n⚠️  No files were saved. Exiting.")
            return
        
        # Step 7: Update master.adoc
        print("\n[Step 7] Updating master.adoc")
        self.update_master_adoc(self.version, bool(resolved_tickets), bool(known_tickets))
        
        print("\n" + "=" * 60)
        print("Release notes generation complete!")
        print("=" * 60)
        print(f"\nBranch: {self.new_branch}")
        print("\nFiles saved:")
        for filename in files_saved:
            print(f"  - documentation/modules/{filename}")
        print(f"  - documentation/doc-Release_notes/master.adoc (updated)")
        print("\nNext steps:")
        print("1. Review the generated files")
        print("2. Add any additional content (e.g., new features) if needed")
        print(f"3. Commit your changes: git add . && git commit -m 'Add release notes for MTV {self.version}'")
        print(f"4. Push the branch: git push origin {self.new_branch}")


def main():
    """Parse CLI, create generator, and run. Exits on Ctrl+C or exception."""
    parser = argparse.ArgumentParser(
        description="Generate Forklift/MTV release notes from JIRA CSV exports.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  Interactive:
    python generate_release_notes.py

  Non-interactive (e.g. test PR):
    python generate_release_notes.py --version 2.11.1 --base main \\
      --resolved scripts/test_data/resolved_issues.csv \\
      --known scripts/test_data/known_issues.csv --yes
        """,
    )
    parser.add_argument("--version", metavar="X.Y.Z", help="MTV version (e.g., 2.11.1)")
    parser.add_argument("--base", dest="base_branch", metavar="BRANCH", help="Base git branch")
    parser.add_argument("--resolved", metavar="CSV", help="Path to resolved issues CSV")
    parser.add_argument("--known", metavar="CSV", help="Path to known issues CSV")
    parser.add_argument("--yes", "-y", action="store_true", help="Non-interactive: overwrite/use existing without prompting")
    args = parser.parse_args()

    non_interactive = args.yes or any([args.version, args.base_branch, args.resolved, args.known])

    # Get repository path (script location's parent)
    script_path = Path(__file__).resolve()
    repo_path = script_path.parent.parent

    generator = ReleaseNotesGenerator(str(repo_path), non_interactive=non_interactive)

    try:
        generator.run(
            base_branch=args.base_branch,
            version=args.version,
            resolved_csv=args.resolved,
            known_csv=args.known,
        )
    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\nError: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
