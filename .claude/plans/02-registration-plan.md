# Plan: Basic User Registration (pAIsa Web Dashboard)

## Overview
Implement a simple Login/Signup system for the pAIsa Web Dashboard using raw HTML/CSS/JS. Users can create an account and log in to save their preferences.

## Phase 1: Database Updates (`trading_pAIsa/database/market_repo.py`)
- Add a new function `init_user_db()` to create the `users` table:
    - `id`, `username`, `password_hash`, `default_amount`, `default_time`.
- Add `create_user(username, password_hash, amount, time)` to save new users.
- Add `get_user_by_username(username)` to fetch user data for login.

## Phase 2: Simple Templates (`templates/`)
- **`signup.html`**: A basic HTML form with:
    - Inputs for `username`, `password`, `amount`, and `time`.
- **`login.html`**: A basic HTML form for logging in.
- **`frontend_upstox.html`**: 
    - Add a "Login/Logout" link.
    - Update input values to use `{{ user.default_amount }}` and `{{ user.default_time }}` if logged in.

## Phase 3: Web Routes (`trading_pAIsa/main.py`)
- **Authentication Helpers**:
    - Use `passlib` to hash and verify passwords.
    - Use a simple cookie-based session to remember the logged-in user.
- **Routes**:
    - `GET /signup` / `POST /signup`: Handle user creation.
    - `GET /login` / `POST /login`: Handle authentication.
    - `GET /logout`: Clear the cookie and redirect to home.

## Phase 4: Integration
- Update the main analysis page to check if a user is logged in.
- Display "Welcome, [username]" if authenticated.

## Rules
- **No ORM**: Use `sqlite3` only.
- **Basic UI**: Standard HTML elements, basic CSS colors (no glassmorphism).
- **Security**: Always hash passwords before saving.
---
