---
name: git-commit
description: Generate git commit messages following MTV project conventions. Use when the user asks to commit, create a commit, write a commit message, or stage and commit changes.
---

# Git Commit Message Skill

## Workflow

1. Run `git diff --staged` (and `git status`) to understand the changes.
2. Determine whether an MTV Jira issue applies. Ask the user for the MTV issue number if not already known.
3. **Always ask the user**: "Was AI used as a co-author for these changes?" If yes, append the AI co-author trailer.
4. Compose the commit message using the appropriate template below.
5. Commit using a HEREDOC so the multi-line message is preserved.

## Template A — With MTV Issue

Use when an MTV-xxx Jira issue is associated with the change.

```
MTV-xxx | short description of the change

Explain why this change is needed. Focus on intent, not mechanics.

Resolves: MTV-xxx
Ref: https://issues.redhat.com/browse/MTV-xxx

Co-authored-by: AI Assistant <ai-assistant@noreply.redhat.com>

Signed-off-by: {name} <{email}>
```

- The title line is: `MTV-xxx | short description` (imperative mood, lowercase after the pipe).
- The body paragraph explains **why**, not what.
- `Resolves` and `Ref` reference the same MTV issue.
- Omit the `Co-authored-by` line if AI was **not** a co-author.

## Template B — Without MTV Issue

Use for housekeeping work that has no Jira ticket (docs cleanup, CI tweaks, dependency bumps, etc.).

```
chore(type): short description of the change

Explain why this change is needed.

Resolves: none

Co-authored-by: AI Assistant <ai-assistant@noreply.redhat.com>

Signed-off-by: {name} <{email}>
```

- The title follows conventional-commit style: `chore(type): description`.
  Common types: `docs`, `ci`, `deps`, `lint`, `test`, `config`.
- `Resolves: none` — no Jira reference.
- `Ref` line is **omitted entirely**.
- Omit the `Co-authored-by` line if AI was **not** a co-author.

## Commit Command

Always use a HEREDOC to preserve formatting:

```bash
git commit -m "$(cat <<'EOF'
MTV-123 | add migration network performance guidance

Document the impact of dedicated migration networks on transfer
throughput so users can make informed network topology decisions.

Resolves: MTV-123
Ref: https://issues.redhat.com/browse/MTV-123

Signed-off-by: yaacov <kobi.zamir@gmail.com>
Co-authored-by: AI Assistant <ai-assistant@noreply.redhat.com>
EOF
)"
```

## Rules

- Get the signer identity from `git config user.name` / `git config user.email`.
- Never fabricate an MTV issue number — ask the user.
- Always ask whether AI co-authored before composing the message.
- Keep the title line under 72 characters.
- Use imperative mood in the title ("add", "fix", "update", not "added", "fixes").
