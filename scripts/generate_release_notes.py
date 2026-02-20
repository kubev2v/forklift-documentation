#!/usr/bin/env python3
"""
Release Notes Generator for Forklift/MTV Documentation

This script automates the generation of release notes from JIRA ticket exports.
It prompts for branch selection, MTV version, and processes CSV files containing
known issues and resolved issues. It creates a new git branch and generates all
necessary release notes files.
"""

import os
import sys
import csv
import re
import subprocess
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from datetime import datetime


class ReleaseNotesGenerator:
    """Generates release notes from JIRA ticket exports."""
    
    def __init__(self, repo_path: str):
        self.repo_path = Path(repo_path)
        self.docs_path = self.repo_path / "documentation"
        self.modules_path = self.docs_path / "modules"
        self.release_notes_path = self.docs_path / "doc-Release_notes"
        self.master_adoc_path = self.release_notes_path / "master.adoc"
        self.base_branch = None
        self.new_branch = None
        self.version = None
        
    def get_git_branches(self) -> List[str]:
        """Get list of available git branches."""
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
        """Prompt user to select a base git branch."""
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
        """Create a new git branch for release notes."""
        branch_name = f"MTV-RN-{version}"
        
        print(f"\nCreating new branch: {branch_name} from {base_branch}")
        
        try:
            # Checkout base branch first
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
                response = input(f"Branch {branch_name} already exists. Use it? (y/n): ").strip().lower()
                if response == 'y':
                    subprocess.run(
                        ["git", "checkout", branch_name],
                        cwd=self.repo_path,
                        check=True
                    )
                    return branch_name
            raise
    
    def select_version(self) -> str:
        """Prompt user to enter MTV version."""
        while True:
            version = input("\nEnter MTV version (e.g., 2.11.0): ").strip()
            if re.match(r'^\d+\.\d+(\.\d+)?$', version):
                return version
            else:
                print("Invalid version format. Please use format like '2.11.0' or '2.11'")
    
    def parse_jira_csv(self, csv_path: str) -> List[Dict[str, str]]:
        """
        Parse JIRA CSV export file.
        
        Expected CSV format (columns may vary, script will auto-detect):
        - Issue key (e.g., MTV-3915)
        - Summary/Title
        - Description
        - Status
        - For known issues: Workaround (optional)
        
        The script will try to detect common column names.
        """
        tickets = []
        
        with open(csv_path, 'r', encoding='utf-8') as f:
            # Try to detect delimiter
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
        """Format issue text for AsciiDoc."""
        # Clean up text
        summary = summary.strip()
        description = description.strip()
        
        # Remove HTML tags if present
        description = re.sub(r'<[^>]+>', '', description)
        
        # Format the issue entry
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
        """Generate resolved issues AsciiDoc content."""
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
        """Generate known issues AsciiDoc content."""
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
        """Generate the main release notes header file."""
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
        """Update master.adoc to include new release notes modules."""
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
            response = input("Continue anyway? (y/n): ").strip().lower()
            if response != 'y':
                return False
        
        lines = content.split('\n')
        new_lines = []
        
        # Track what we've inserted
        header_inserted = False
        resolved_inserted = False
        known_inserted = False
        
        i = 0
        while i < len(lines):
            line = lines[i]
            
            # Insert release notes header right after common-attributes
            if not header_inserted and line.strip() == 'include::modules/common-attributes.adoc[]':
                new_lines.append(line)
                # Skip to the first rn- include and insert before it
                j = i + 1
                while j < len(lines) and not lines[j].strip().startswith('include::modules/rn-'):
                    new_lines.append(lines[j])
                    j += 1
                # Insert new header
                new_lines.append("")
                new_lines.append(f"include::modules/rn-{version_major_safe}.adoc[leveloffset=+1]")
                header_inserted = True
                i = j
                continue
            
            # Insert resolved issues after the last resolved issues include
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
            
            # Replace known issues include
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
        
        # Fallback: if we didn't find insertion points, try simpler approach
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
    
    def save_file(self, content: str, filename: str):
        """Save content to file in modules directory."""
        filepath = self.modules_path / filename
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"✓ Generated: {filepath}")
    
    def run(self):
        """Main execution flow."""
        print("=" * 60)
        print("Forklift/MTV Release Notes Generator")
        print("=" * 60)
        
        # Step 1: Select base branch
        print("\n[Step 1] Base Branch Selection")
        self.base_branch = self.select_branch()
        print(f"Selected base branch: {self.base_branch}")
        
        # Step 2: Select version
        print("\n[Step 2] Version Selection")
        self.version = self.select_version()
        print(f"Selected version: {self.version}")
        
        # Step 3: Create release branch
        print("\n[Step 3] Creating Release Branch")
        self.new_branch = self.create_release_branch(self.base_branch, self.version)
        
        # Step 4: Upload resolved issues
        print("\n[Step 4] Resolved Issues")
        resolved_file = input("Enter path to resolved issues CSV file (or press Enter to skip): ").strip()
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
        known_file = input("Enter path to known issues CSV file (or press Enter to skip): ").strip()
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
        
        # Generate release notes header
        version_major = '.'.join(self.version.split('.')[:2])  # e.g., 2.11
        header_content = self.generate_release_notes_header(self.version)
        header_filename = f"rn-{version_major.replace('.', '-')}.adoc"
        self.save_file(header_content, header_filename)
        
        # Generate resolved issues
        if resolved_tickets:
            version_safe = self.version.replace('.', '-')
            resolved_content = self.generate_resolved_issues(resolved_tickets, self.version)
            resolved_filename = f"rn-{version_safe}-resolved-issues.adoc"
            self.save_file(resolved_content, resolved_filename)
        
        # Generate known issues
        if known_tickets:
            known_content = self.generate_known_issues(known_tickets, version_major)
            known_filename = f"known-issues-{version_major.replace('.', '-')}.adoc"
            self.save_file(known_content, known_filename)
        
        # Step 7: Update master.adoc
        print("\n[Step 7] Updating master.adoc")
        self.update_master_adoc(self.version, bool(resolved_tickets), bool(known_tickets))
        
        print("\n" + "=" * 60)
        print("Release notes generation complete!")
        print("=" * 60)
        print(f"\nBranch: {self.new_branch}")
        print("\nGenerated files:")
        print(f"  - documentation/modules/{header_filename}")
        if resolved_tickets:
            print(f"  - documentation/modules/rn-{self.version.replace('.', '-')}-resolved-issues.adoc")
        if known_tickets:
            print(f"  - documentation/modules/known-issues-{version_major.replace('.', '-')}.adoc")
        print(f"  - documentation/doc-Release_notes/master.adoc (updated)")
        print("\nNext steps:")
        print("1. Review the generated files")
        print("2. Add any additional content (e.g., new features) if needed")
        print(f"3. Commit your changes: git add . && git commit -m 'Add release notes for MTV {self.version}'")
        print(f"4. Push the branch: git push origin {self.new_branch}")


def main():
    """Entry point."""
    # Get repository path (script location's parent)
    script_path = Path(__file__).resolve()
    repo_path = script_path.parent.parent
    
    generator = ReleaseNotesGenerator(str(repo_path))
    
    try:
        generator.run()
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
