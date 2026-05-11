---
description: Generate a git commit message based on staged changes
allowed-tools: Bash(git diff:*), Bash(git status:*), Bash(git log:*), Bash(git ls-files:*)
---

Analyze the current git state and generate a commit message.

1. Run `git status` to get the full picture — staged, unstaged, and untracked files
2. Run `git diff --cached` for staged changes
3. Run `git diff` for unstaged changes in tracked files
4. Run `git ls-files --others --exclude-standard` to list untracked files
5. Run `git log --oneline -5` to understand commit style used in this repo

**Important**: Do NOT treat untracked files as "nothing to commit". If there are untracked files, read them and factor them into the commit message. Ask the user if they want to stage them first before generating the message.

Then produce a commit message following these rules:

- **One line only** — keep it short, tight, and direct. No body, no bullet points, no elaboration.
- 50 chars or less, imperative mood (e.g. "Add feature" not "Added feature"), no trailing period
- Follow Conventional Commits format if the repo already uses it (e.g. `feat:`, `fix:`, `chore:`, `refactor:`, `docs:`)

Output ONLY the final commit message, ready to copy-paste. Do not add any explanation around it.
