# Release Notes Generator

This script automates the generation of release notes from JIRA ticket exports. It creates a new git branch and generates all necessary release notes files.

## Usage

```bash
python3 scripts/generate_release_notes.py
```

The script will prompt you for:
1. **Base branch selection**: Choose from available git branches or enter a custom branch name (the new branch will be created from this)
2. **MTV version**: Enter the version number (e.g., `2.11.0`)
3. **Resolved issues CSV**: Path to CSV file containing resolved JIRA tickets
4. **Known issues CSV**: Path to CSV file containing known issues JIRA tickets

## What the Script Does

1. **Creates a new git branch**: `MTV-RN-<version>` (e.g., `MTV-RN-2.11.0`)
2. **Generates release notes files**:
   - `rn-{major-version}.adoc` - Main release notes header (e.g., `rn-2-11.adoc`)
   - `rn-{version}-resolved-issues.adoc` - Resolved issues (e.g., `rn-2-11-0-resolved-issues.adoc`)
   - `known-issues-{major-version}.adoc` - Known issues (e.g., `known-issues-2-11.adoc`)
3. **Updates master.adoc**: Automatically updates `documentation/doc-Release_notes/master.adoc` to include the new modules

## JIRA CSV Export Format

### Recommended Format

When exporting from JIRA, include the following columns:

**For Resolved Issues:**
- `Issue Key` (e.g., MTV-3915)
- `Summary` or `Title`
- `Description`

**For Known Issues:**
- `Issue Key` (e.g., MTV-3116)
- `Summary` or `Title`
- `Description`
- `Workaround` (optional but recommended)

### CSV Column Names

The script automatically detects common column name variations:
- **Issue Key**: `Issue Key`, `Key`, `Issue`, `Ticket`, `JIRA Key`
- **Summary**: `Summary`, `Title`, `Subject`, `Name`
- **Description**: `Description`, `Details`, `Body`
- **Workaround**: `Workaround`, `Work Around`, `Resolution`, `Solution`

### Example CSV Structure

```csv
Issue Key,Summary,Description,Workaround
MTV-3915,Target cluster namespaces now visible,Before this update, during cross-cluster live migration...,""
MTV-3116,Forklift console plugin fails to load,When MTV 2.9.1 is deployed on an IPv6-only...,Deploy MTV on dual-stack or IPv4 clusters
```

## Output

The script:
- Creates a new git branch: `MTV-RN-<version>`
- Generates AsciiDoc files in `documentation/modules/`:
  - `rn-{major-version}.adoc` (e.g., `rn-2-11.adoc`)
  - `rn-{version}-resolved-issues.adoc` (e.g., `rn-2-11-0-resolved-issues.adoc`)
  - `known-issues-{major-version}.adoc` (e.g., `known-issues-2-11.adoc`)
- Updates `documentation/doc-Release_notes/master.adoc` automatically

## Next Steps

After running the script:

1. **Review the generated files** in `documentation/modules/`
2. **Add any additional content** if needed (e.g., new features section)
3. **Commit your changes**:
   ```bash
   git add .
   git commit -m "Add release notes for MTV {version}"
   ```
4. **Push the branch**:
   ```bash
   git push origin MTV-RN-{version}
   ```
5. **Create a pull request** with the new release notes branch

## Exporting from JIRA

### Steps to Export CSV from JIRA:

1. Navigate to your JIRA project (e.g., MTV)
2. Use the search/filter to find issues:
   - For resolved issues: Filter by `Status = Resolved` or `Status = Closed`
   - For known issues: Filter by `Labels = Known Issue` or similar
3. Click **Export** → **Export CSV (Current fields)**
4. Ensure the export includes:
   - Issue Key
   - Summary
   - Description
   - (For known issues) Workaround field if available

### Alternative: Using JIRA Query Language (JQL)

You can also export using JQL queries:
- Resolved issues: `project = MTV AND status = Resolved AND fixVersion = "2.11.0"`
- Known issues: `project = MTV AND labels = "known-issue" AND fixVersion = "2.11.0"`

## Troubleshooting

**Issue**: Script can't find issue keys
- **Solution**: Ensure your CSV has a column named `Issue Key`, `Key`, or `Issue`

**Issue**: Descriptions are empty
- **Solution**: Check that your CSV export includes the `Description` column

**Issue**: Workarounds not appearing
- **Solution**: Add a `Workaround` column to your known issues CSV, or manually edit the generated file

## Requirements

- Python 3.6+
- Git (for branch detection)
- CSV files exported from JIRA
