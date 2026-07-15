# AI Language Learning System — Project Documentation

**B.Tech Final Year Project | Computer Science & Engineering | 2024–2025**

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [System Requirements](#2-system-requirements)
3. [Installation Guide](#3-installation-guide)
4. [Project Structure](#4-project-structure)
5. [Database Design](#5-database-design)
6. [Module Documentation](#6-module-documentation)
   - 6.1 Authentication
   - 6.2 Dashboard
   - 6.3 Grammar Checker
   - 6.4 Vocabulary Builder
   - 6.5 Quiz Generator
   - 6.6 REST API Endpoints
7. [Gemini AI Integration](#7-gemini-ai-integration)
8. [Security Measures](#8-security-measures)
9. [Testing Guide](#9-testing-guide)
10. [Deployment Notes](#10-deployment-notes)
11. [Limitations & Future Work](#11-limitations--future-work)
12. [References](#12-references)

---

## 1. Project Overview

**LinguaAI** is an AI-powered English Language Learning System built as a B.Tech final year project. It leverages Google's Gemini 1.5 Flash large language model to provide real-time, personalized language learning assistance through three core modules: Grammar Checking, Vocabulary Building, and Quiz Generation.

### 1.1 Goals

- Democratize English language learning using generative AI
- Deliver instant, context-aware grammar feedback without human tutors
- Build an interactive vocabulary system with etymology and memory aids
- Auto-generate customizable quizzes on any English topic
- Track learner progress via a personalized analytics dashboard

### 1.2 Technologies Used

| Layer      | Technology                          |
|------------|-------------------------------------|
| Backend    | Python 3.11, Flask 3.0              |
| AI Engine  | Google Gemini 1.5 Flash API         |
| Database   | SQLite 3                            |
| Frontend   | HTML5, Bootstrap 5.3, Jinja2, JS    |
| Auth       | Flask sessions, SHA-256 hashing     |
| DevTools   | Git, pip, python-dotenv, VS Code    |

---

## 2. System Requirements

### Hardware
- Processor: Intel Core i3 or equivalent (1 GHz+)
- RAM: 4 GB minimum (8 GB recommended)
- Storage: 500 MB free disk space
- Internet connection (required for Gemini API calls)

### Software
- Python 3.9 or higher
- pip (Python package manager)
- Modern web browser (Chrome, Firefox, Edge)
- A valid Google Gemini API key

---

## 3. Installation Guide

### Step 1 — Clone or Extract the Project

```bash
git clone https://github.com/yourname/lingua-ai.git
cd lingua-ai
```

### Step 2 — Create a Virtual Environment

```bash
python -m venv venv
# Windows
venv\Scripts\activate
# macOS / Linux
source venv/bin/activate
```

### Step 3 — Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 4 — Configure Environment Variables

Copy `.env.example` to `.env` and fill in your values:

```bash
cp .env.example .env
```

Edit `.env`:

```
GEMINI_API_KEY=your_actual_gemini_api_key_here
SECRET_KEY=a_long_random_secret_string
FLASK_ENV=development
FLASK_DEBUG=1
```

> **Obtaining a Gemini API Key:** Visit https://aistudio.google.com, sign in with a Google account, and create an API key under "Get API Key".

### Step 5 — Run the Application

```bash
python app.py
```

Open your browser at: **http://127.0.0.1:5000**

The SQLite database (`instance/language_learning.db`) is created automatically on first run.

---

## 4. Project Structure

```
lingua-ai/
│
├── app.py                    # Main Flask application
├── requirements.txt          # Python dependencies
├── .env.example              # Environment variable template
│
├── instance/
│   └── language_learning.db  # SQLite database (auto-generated)
│
├── templates/
│   ├── base.html             # Master layout with navbar
│   ├── login.html            # Login page
│   ├── register.html         # Registration page
│   ├── dashboard.html        # User dashboard with analytics
│   ├── grammar.html          # Grammar checker UI
│   ├── vocabulary.html       # Vocabulary builder UI
│   ├── quiz.html             # Quiz generator & history
│   ├── take_quiz.html        # Interactive quiz interface
│   └── quiz_result.html      # Quiz result & review
│
└── static/
    ├── css/
    │   └── style.css         # Custom stylesheet
    └── js/
        └── main.js           # Client-side JavaScript
```

---

## 5. Database Design

The application uses four SQLite tables.

### 5.1 `users`

| Column     | Type    | Description                            |
|------------|---------|----------------------------------------|
| id         | INTEGER | Primary key (auto-increment)           |
| username   | TEXT    | Unique username                        |
| email      | TEXT    | Unique email address                   |
| password   | TEXT    | SHA-256 hashed password                |
| created_at | TEXT    | Account creation timestamp             |

### 5.2 `grammar_checks`

| Column     | Type    | Description                            |
|------------|---------|----------------------------------------|
| id         | INTEGER | Primary key                            |
| user_id    | INTEGER | Foreign key → users.id                 |
| input_text | TEXT    | Original text submitted                |
| result     | TEXT    | JSON string with AI analysis           |
| created_at | TEXT    | Check timestamp                        |

**Result JSON structure:**
```json
{
  "corrected_text": "...",
  "errors": [{ "original": "...", "corrected": "...", "explanation": "..." }],
  "suggestions": ["..."],
  "score": 8,
  "summary": "..."
}
```

### 5.3 `vocabulary`

| Column     | Type    | Description                            |
|------------|---------|----------------------------------------|
| id         | INTEGER | Primary key                            |
| user_id    | INTEGER | Foreign key → users.id                 |
| word       | TEXT    | The looked-up word                     |
| definition | TEXT    | Word definition                        |
| examples   | TEXT    | JSON array of example sentences        |
| synonyms   | TEXT    | JSON array of synonyms                 |
| created_at | TEXT    | Lookup timestamp                       |

### 5.4 `quizzes`

| Column     | Type    | Description                            |
|------------|---------|----------------------------------------|
| id         | INTEGER | Primary key                            |
| user_id    | INTEGER | Foreign key → users.id                 |
| topic      | TEXT    | Quiz topic                             |
| questions  | TEXT    | JSON array of MCQ objects              |
| score      | INTEGER | Score after attempt (NULL if pending)  |
| total      | INTEGER | Total number of questions              |
| created_at | TEXT    | Generation timestamp                   |

---

## 6. Module Documentation

### 6.1 Authentication

**Routes:** `GET/POST /register`, `GET/POST /login`, `GET /logout`

Registration validates uniqueness of username and email before storing a SHA-256 hashed password. Login compares submitted credentials against the stored hash. On success, `user_id` and `username` are stored in the Flask server-side session. The `@login_required` decorator protects all non-auth routes.

### 6.2 Dashboard

**Route:** `GET /dashboard`

Queries four aggregate statistics for the logged-in user: total grammar checks, total vocabulary lookups, total quizzes generated, and average quiz score percentage. Also fetches the five most recent entries from each activity table for display in the Recent Activity section.

### 6.3 Grammar Checker

**Route:** `GET/POST /grammar`

On POST, the submitted text is packaged into a structured Gemini prompt requesting:
- Corrected version of the text
- List of errors with before/after comparison and explanation
- Style improvement suggestions
- An integer grammar score out of 10
- A plain-language summary

The response is parsed from JSON and stored in `grammar_checks`. The template renders the score as a Bootstrap progress bar, errors as annotated diff cards, and suggestions as a bulleted list.

### 6.4 Vocabulary Builder

**Route:** `GET/POST /vocabulary`

On POST, a detailed prompt requests a full word profile including: definition, pronunciation, part of speech, detailed explanation, three example sentences, synonyms, antonyms, word family forms, etymology, difficulty level, and a memory tip. The result is rendered in a styled word card. The word, definition, examples, and synonyms are persisted to the `vocabulary` table.

### 6.5 Quiz Generator

**Routes:** `GET/POST /quiz`, `GET/POST /quiz/<quiz_id>`

`/quiz` (POST) generates a set of multiple-choice questions at the chosen difficulty level for the given topic. Questions are stored as a JSON array in the `quizzes` table and the user is redirected to the take-quiz view.

`/quiz/<quiz_id>` (GET) renders a step-by-step quiz interface with a progress bar. On POST submission, each answer is validated against the stored correct answer, a score is computed and saved, and the user is shown the detailed result view with per-question explanations.

### 6.6 REST API Endpoints

| Method | URL              | Description                           |
|--------|------------------|---------------------------------------|
| POST   | /api/translate   | Translate text to a target language   |
| GET    | /api/word_of_day | Get an AI-generated word of the day   |

**`/api/translate` request body:**
```json
{ "text": "Hello world", "target_language": "Spanish" }
```

**`/api/word_of_day` response:**
```json
{
  "word": "ephemeral",
  "part_of_speech": "adjective",
  "definition": "Lasting for a very short time",
  "example": "The ephemeral beauty of cherry blossoms...",
  "tip": "Think of 'ephemera' — items meant to be short-lived."
}
```

---

## 7. Gemini AI Integration

The application uses the `google-generativeai` Python SDK with the `gemini-1.5-flash` model, which provides a good balance of speed, cost, and accuracy for language tasks.

### Prompt Engineering Strategy

All prompts follow a structured pattern:
1. **Role assignment** — "You are an expert English grammar checker…"
2. **Task specification** — Clear description of what to produce
3. **Output format** — "Respond in JSON format: { ... }"
4. **Input injection** — The user's text or word at the end

JSON responses are cleaned of markdown code fences before parsing to handle cases where Gemini wraps output in ` ```json ` blocks.

### Error Handling

All Gemini API calls are wrapped in `try/except`. On failure, an error flash message is shown to the user and no database write occurs. This ensures a graceful degradation if the API is unavailable.

---

## 8. Security Measures

| Threat                | Mitigation                                              |
|-----------------------|---------------------------------------------------------|
| Password exposure     | SHA-256 hashing; passwords never stored in plaintext    |
| Unauthorized access   | `@login_required` decorator on all protected routes     |
| Session hijacking     | Flask's cryptographically signed cookie via `SECRET_KEY`|
| SQL injection         | Parameterized queries via `sqlite3` placeholders (`?`)  |
| XSS                   | Jinja2 auto-escapes all template variables by default   |

> **Note:** For production deployment, use `bcrypt` or `argon2` for password hashing and set `SESSION_COOKIE_SECURE=True` with HTTPS.

---

## 9. Testing Guide

### Manual Test Scenarios

| Scenario                 | Steps                                                        | Expected Result                          |
|--------------------------|--------------------------------------------------------------|------------------------------------------|
| Register new user        | Fill form → Submit                                           | Redirect to login with success message   |
| Login with wrong password| Enter correct username, wrong password                       | "Invalid credentials" flash message      |
| Grammar check            | Enter misspelled text → Check Grammar                        | Corrected text + errors + score displayed|
| Vocabulary lookup        | Enter "serendipity" → Explore                                | Full word card with all fields populated |
| Generate quiz            | Enter topic "Idioms", Intermediate, 5 questions              | Redirected to interactive quiz           |
| Submit quiz              | Answer all questions → Submit Quiz                           | Score shown with per-question review     |
| Word of Day              | Click "Word of the Day" on dashboard                         | Inline card with word, definition, tip   |

### Running the App in Debug Mode

```bash
FLASK_DEBUG=1 python app.py
```

Flask's debugger provides a browser-based interactive traceback for any unhandled exceptions.

---

## 10. Deployment Notes

### Option A — Local Development
```bash
python app.py  # http://127.0.0.1:5000
```

### Option B — Render / Railway (Cloud)

1. Push code to GitHub
2. Set environment variables in the dashboard: `GEMINI_API_KEY`, `SECRET_KEY`
3. Set start command: `gunicorn app:app`
4. Add `gunicorn` to `requirements.txt`

### Option C — Docker

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 5000
CMD ["python", "app.py"]
```

---

## 11. Limitations & Future Work

### Current Limitations
- Gemini API rate limits may slow response under high concurrency
- SHA-256 without salt is adequate for demos; production needs bcrypt
- No email verification on registration
- Single-language support (English only)

### Planned Enhancements
- **Speech recognition** for pronunciation practice (Web Speech API)
- **Multi-language support** — Spanish, French, Hindi
- **Gamification** — streaks, badges, leaderboard
- **AI Conversation Bot** — multi-turn dialogue practice
- **Mobile app** — React Native with offline vocabulary cache
- **Advanced analytics** — learning curve charts, spaced repetition

---

## 12. References

1. Google Generative AI Python SDK — https://github.com/google/generative-ai-python
2. Flask Documentation 3.0 — https://flask.palletsprojects.com
3. Bootstrap 5.3 — https://getbootstrap.com/docs/5.3
4. SQLite Documentation — https://www.sqlite.org/docs.html
5. Gemini API Quickstart — https://ai.google.dev/tutorials/python_quickstart
6. OWASP Top 10 Web Security Risks — https://owasp.org/www-project-top-ten/

---

*Document prepared for B.Tech Final Year Project submission — Department of Computer Science & Engineering*
