---
description: Create a spec file and feature branch for the next WhatsApp Trading Agent step
argument-hint: "Step number and feature name e.g. 2 authentication"
allowed-tools: Read, Write, Glob, Bash(git:*)
---

You are a senior developer spinning up a new feature for the WhatsApp Trading Agent (trading_pAIsa). Always follow the rules in CLAUDE.md.

User input: $ARGUMENTS

## Step 1 — Check working directory is clean
Run `git status` and check for uncommitted, unstaged, or
untracked files. If any exist, stop immediately and tell
the user to commit or stash changes before proceeding.
DO NOT CONTINUE until the working directory is clean.

## Step 2 — Parse the arguments
From $ARGUMENTS extract:

1. `step_number` — zero-padded to 2 digits: 2 → 02, 11 → 11

2. `feature_title` — human readable title in Title Case
   - Example: "Signal Backtesting" or "Live Order Execution"

3. `feature_slug` — git and file safe slug
   - Lowercase, kebab-case
   - Only a-z, 0-9 and -
   - Maximum 40 characters
   - Example: signal-backtesting, live-orders

4. `branch_name` — format: `feature/<feature_slug>`
   - Example: `feature/signal-backtesting`

If you cannot infer these from $ARGUMENTS, ask the user
to clarify before proceeding.

## Step 3 — Check branch name is not taken
Run `git branch` to list existing branches.
If `branch_name` is already taken, append a number:
`feature/feature-slug-01`, `feature/feature-slug-02` etc.

## Step 4 — Switch to main and pull latest
Run:
```
git checkout main
git pull origin main
```

## Step 5 — Create and switch to the feature branch
Run:
```
git checkout -b <branch_name>
```

## Step 6 — Research the codebase
Read these files before writing the spec:
- `CLAUDE.md` — architecture and conventions
- `trading_pAIsa/main.py` — core FastAPI app and analysis logic
- `trading_pAIsa/database/market_repo.py` — SQLite repository operations
- `templates/frontend_upstox.html` — existing frontend
- All files in `.claude/specs/` (if it exists) — avoid duplicating existing specs

## Step 7 — Write the spec
Generate a spec document with this exact structure:

---
# Spec: <feature_title>

## Overview
One paragraph describing what this feature does and why
it exists at this stage of the trading bot roadmap.

## Depends on
Which previous components this feature requires.

## Routes
Every new FastAPI route needed:
- `METHOD /path` — description

If no new routes: state "No new routes".

## Database changes
Any new SQLite tables or columns needed in `market_db.sqlite3`.
Always verify against `trading_pAIsa/database/market_repo.py` before writing this.
If none: state "No database changes".

## Templates
- **Create:** list new templates in `templates/`
- **Modify:** list existing templates and what changes

## Files to change
Every file that will be modified.

## Files to create
Every new file that will be created.

## New dependencies
Any new pip packages. If none: state "No new dependencies".

## Rules for implementation
Specific constraints Claude must follow. Always include:
- Use FastAPI for web endpoints
- Use the repository pattern in `market_repo.py` for data access
- No SQLAlchemy (use raw sqlite3 as established)
- Use CSS variables for styling
- Follow the "premium" design aesthetics mentioned in system instructions
---

## Step 8 — Save the spec
Save to: `.claude/specs/<step_number>-<feature_slug>.md`

## Step 9 — Report to the user
Print a short summary in this exact format:
```
Branch:    <branch_name>
Spec file: .claude/specs/<step_number>-<feature_slug>.md
Title:     <feature_title>
```

Then tell the user:
"Review the spec at `.claude/specs/<step_number>-<feature_slug>.md`
then enter Plan Mode with Shift+Tab twice to begin implementation."
