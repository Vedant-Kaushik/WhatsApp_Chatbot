---
# Spec: Basic User Registration (pAIsa Web Dashboard)

## Overview
Add a basic account system so users can sign up and log in. This allows the bot to remember who the user is. The design will be simple HTML and basic CSS.

## Routes
- `GET /signup` — Simple HTML form to create a username and password.
- `POST /signup` — Save the new user to the SQLite database.
- `GET /login` — Simple HTML form to log in.
- `POST /login` — Verify password and start a session.
- `GET /logout` — Ends the session.

## Database changes
**New table:** `users`
- `id`: INTEGER PRIMARY KEY
- `username`: TEXT UNIQUE
- `password_hash`: TEXT
- `default_amount`: INTEGER (The user's preferred investment amount)
- `default_time`: INTEGER (The user's preferred time horizon)
- `created_at`: TIMESTAMP

## UI & Templates
- **Create `signup.html`**: A basic form with `username`, `password`, `default_amount`, and `default_time` inputs.
- **Create `login.html`**: A basic form for logging in.
- **Modify `frontend_upstox.html`**: 
    - Add "Login" / "Logout" link at the top.
    - **Crucial:** The form inputs for Amount and Time should automatically show the user's saved values if they are logged in.

## Rules for implementation
- Use **Basic HTML and CSS**. No fancy graphics or complex layouts.
- **Embedded JavaScript**: Keep any JS inside the HTML files (no external files).
- **Security**: Use a basic library like `passlib` to hash passwords (never store plain text passwords).
- **FastAPI Sessions**: Use a simple cookie-based session to remember if the user is logged in.
---
