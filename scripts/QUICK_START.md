# Quick Start Guide - Release Notes Generator

## Prerequisites

- Python 3.6+
- Git
- CSV files exported from JIRA

## Step-by-Step Usage

### 1. Export JIRA Tickets

Export your JIRA tickets to CSV format with these columns:

**Resolved Issues CSV:**
- `Issue Key` (e.g., MTV-3915)
- `Summary`
- `Description`

**Known Issues CSV:**
- `Issue Key` (e.g., MTV-3116)
- `Summary`
- `Description`
- `Workaround` (optional)

### 2. Run the Script

```bash
python3 scripts/generate_release_notes.py
```

### 3. Follow the Prompts

1. **Select base branch**: Choose the branch to create the release notes branch from
2. **Enter MTV version**: e.g., `2.11.1`
3. **Provide resolved issues CSV path**: Full path to your CSV file
4. **Provide known issues CSV path**: Full path to your CSV file

### 4. Review Generated Files

The script creates:
- New git branch: `MTV-RN-2.11.1`
- `documentation/modules/rn-2-11.adoc`
- `documentation/modules/rn-2-11-0-resolved-issues.adoc`
- `documentation/modules/known-issues-2-11.adoc`
- Updated `documentation/doc-Release_notes/master.adoc`

### 5. Commit and Push

```bash
git add .
git commit -m "Add release notes for MTV 2.11.1"
git push origin MTV-RN-2.11.1
```

## Example CSV Format

See `sample_resolved_issues.csv` and `sample_known_issues.csv` for examples.

## Troubleshooting

- **Branch already exists**: The script will ask if you want to use the existing branch
- **Version already in master.adoc**: The script will warn you and ask to continue
- **CSV parsing errors**: Check that your CSV has the required columns (Issue Key, Summary, Description)
