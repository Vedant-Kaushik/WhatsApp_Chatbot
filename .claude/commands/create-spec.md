---
description: Create a spec file and feature branch for the pAIsa Web Dashboard
argument-hint: "Step number and feature name e.g. 2 user-profiles"
allowed-tools: Read, Write, Glob, Bash(git:*)
---

You are a senior developer building the **pAIsa Web Dashboard** (the FastAPI + Jinja2 trading analysis tool). Always follow the rules in CLAUDE.md but focus ONLY on the `trading_pAIsa/` directory and its related templates.

User input: $ARGUMENTS

## Step 1 — Check working directory is clean
Run `git status`. If there are uncommitted changes, stop and tell the user to commit first.

## Step 2 — Parse the arguments
From $ARGUMENTS extract:
1. `step_number` — zero-padded to 2 digits (e.g., 02)
2. `feature_title` — Human readable (e.g., "User Profiles")
3. `feature_slug` — kebab-case (e.g., "user-profiles")
4. `branch_name` — `feature/<feature_slug>`

## Step 3 — Branch Management
Check `git branch`. If `branch_name` exists, add a suffix (e.g., `-01`).
Switch to `main`, pull latest, then create and switch to the new branch.

## Step 4 — Research the pAIsa Codebase
Read these files to understand the current web app state:
- `CLAUDE.md` — Focus on the "pAIsa" section
- `trading_pAIsa/main.py` — The web app's entry point and routes
- `trading_pAIsa/database/market_repo.py` — Database logic
- `templates/frontend_upstox.html` — The main UI template
- `.env` — For any new keys needed

## Step 5 — Write the Web-Focused Spec
Generate a spec document in `.claude/specs/` with this structure:

---
# Spec: <feature_title> (pAIsa Web Dashboard)

## Overview
Describe the feature and its value to the **Web UI** user.

## Routes
Every new **FastAPI** route needed in `trading_pAIsa/main.py`.

## Database changes
Any new SQLite tables/columns in `market_db.sqlite3`.
Update `trading_pAIsa/database/market_repo.py`.

## UI & Templates
- **Modify:** Specific changes to `templates/frontend_upstox.html`.
- **Create:** Any new Jinja2 templates in `templates/`.

## Logic Changes
Changes to technical analysis or AI logic in `trading_pAIsa/main.py`.

## Rules for implementation
- Use **FastAPI** for endpoints.
- Use **Basic HTML, Basic CSS, and Basic JS** (keep JS embedded in templates).
- **NO fancy designs:** No gradients, no glassmorphism. Keep it clean and simple.
- Use **Jinja2** templates (Python fills in the `{{ variables }}`).
- Use raw **SQLite3** via the repository pattern (no ORM).
- Ensure reloads work (avoid POST-only pages where possible).
---

## Step 6 — Save and Report
Save to `.claude/specs/<step_number>-<feature_slug>.md` and print the summary.
