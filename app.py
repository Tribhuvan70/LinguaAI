import os
import json
import sqlite3
import hashlib
from datetime import datetime
from functools import wraps
from flask import (Flask, render_template, request, redirect,
                   url_for, session, jsonify, flash, g)
import google.generativeai as genai

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-production")

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "YOUR_GEMINI_API_KEY_HERE")
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-2.5-flash")

DATABASE = os.path.join(app.instance_path, "language_learning.db")


# ─── DB helpers ─────────────────────────────────────────────────────────────

def get_db():
    if "db" not in g:
        os.makedirs(app.instance_path, exist_ok=True)
        g.db = sqlite3.connect(DATABASE, detect_types=sqlite3.PARSE_DECLTYPES)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(e=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    db = get_db()
    db.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email    TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS grammar_checks (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id    INTEGER NOT NULL,
            input_text TEXT NOT NULL,
            result     TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS vocabulary (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id    INTEGER NOT NULL,
            word       TEXT NOT NULL,
            definition TEXT NOT NULL,
            examples   TEXT,
            synonyms   TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS quizzes (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id    INTEGER NOT NULL,
            topic      TEXT NOT NULL,
            questions  TEXT NOT NULL,
            score      INTEGER,
            total      INTEGER,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS quiz_attempts (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id    INTEGER NOT NULL,
            quiz_id    INTEGER NOT NULL,
            score      INTEGER NOT NULL,
            total      INTEGER NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (quiz_id) REFERENCES quizzes(id)
        );
    """)
    db.commit()


# ─── Auth helpers ────────────────────────────────────────────────────────────

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in to continue.", "warning")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated


# ─── Auth routes ─────────────────────────────────────────────────────────────

@app.route("/")
def index():
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"].strip()
        email    = request.form["email"].strip()
        password = request.form["password"]
        db = get_db()
        if db.execute("SELECT id FROM users WHERE username=? OR email=?",
                      (username, email)).fetchone():
            flash("Username or email already exists.", "danger")
            return render_template("register.html")
        db.execute("INSERT INTO users (username,email,password) VALUES (?,?,?)",
                   (username, email, hash_password(password)))
        db.commit()
        flash("Registration successful! Please log in.", "success")
        return redirect(url_for("login"))
    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"]
        db  = get_db()
        row = db.execute("SELECT * FROM users WHERE username=? AND password=?",
                         (username, hash_password(password))).fetchone()
        if row:
            session["user_id"]  = row["id"]
            session["username"] = row["username"]
            return redirect(url_for("dashboard"))
        flash("Invalid credentials.", "danger")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("Logged out successfully.", "info")
    return redirect(url_for("login"))


# ─── Dashboard ───────────────────────────────────────────────────────────────

@app.route("/dashboard")
@login_required
def dashboard():
    db = get_db()
    uid = session["user_id"]
    grammar_count = db.execute(
        "SELECT COUNT(*) FROM grammar_checks WHERE user_id=?", (uid,)).fetchone()[0]
    vocab_count   = db.execute(
        "SELECT COUNT(*) FROM vocabulary    WHERE user_id=?", (uid,)).fetchone()[0]
    quiz_count    = db.execute(
        "SELECT COUNT(*) FROM quizzes       WHERE user_id=?", (uid,)).fetchone()[0]
    avg_score     = db.execute(
        "SELECT AVG(CAST(score AS REAL)/total*100) FROM quizzes "
        "WHERE user_id=? AND score IS NOT NULL", (uid,)).fetchone()[0]
    avg_score = round(avg_score, 1) if avg_score else 0

    recent_grammar = db.execute(
        "SELECT * FROM grammar_checks WHERE user_id=? ORDER BY created_at DESC LIMIT 5",
        (uid,)).fetchall()
    recent_vocab   = db.execute(
        "SELECT * FROM vocabulary    WHERE user_id=? ORDER BY created_at DESC LIMIT 5",
        (uid,)).fetchall()
    recent_quizzes = db.execute(
        "SELECT * FROM quizzes       WHERE user_id=? ORDER BY created_at DESC LIMIT 5",
        (uid,)).fetchall()

    return render_template("dashboard.html",
        grammar_count=grammar_count, vocab_count=vocab_count,
        quiz_count=quiz_count,       avg_score=avg_score,
        recent_grammar=recent_grammar, recent_vocab=recent_vocab,
        recent_quizzes=recent_quizzes)


# ─── Grammar checker ─────────────────────────────────────────────────────────

@app.route("/grammar", methods=["GET", "POST"])
@login_required
def grammar():
    result = None
    if request.method == "POST":
        text   = request.form["text"].strip()
        prompt = f"""You are an expert English grammar checker.
Analyze the following text and provide:
1. Corrected version of the text
2. List of grammar errors found (with explanations)
3. Style suggestions
4. Overall score out of 10

Text: {text}

Respond in JSON format:
{{
  "corrected_text": "...",
  "errors": [{{"original": "...", "corrected": "...", "explanation": "..."}}],
  "suggestions": ["..."],
  "score": 8,
  "summary": "..."
}}"""
        try:
            response = model.generate_content(prompt)
            raw = response.text.strip()
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            result = json.loads(raw)
            db = get_db()
            db.execute(
                "INSERT INTO grammar_checks (user_id,input_text,result) VALUES (?,?,?)",
                (session["user_id"], text, json.dumps(result)))
            db.commit()
        except Exception as e:
            flash(f"Error: {e}", "danger")

    history = get_db().execute(
        "SELECT * FROM grammar_checks WHERE user_id=? ORDER BY created_at DESC LIMIT 10",
        (session["user_id"],)).fetchall()
    return render_template("grammar.html", result=result, history=history)


# ─── Vocabulary generator ────────────────────────────────────────────────────

@app.route("/vocabulary", methods=["GET", "POST"])
@login_required
def vocabulary():
    word_data = None
    if request.method == "POST":
        word   = request.form["word"].strip()
        prompt = f"""Provide comprehensive vocabulary information for the word: "{word}"

Respond in JSON:
{{
  "word": "...",
  "pronunciation": "...",
  "part_of_speech": "...",
  "definition": "...",
  "detailed_explanation": "...",
  "examples": ["sentence1", "sentence2", "sentence3"],
  "synonyms": ["w1","w2","w3"],
  "antonyms": ["w1","w2"],
  "word_family": ["forms..."],
  "etymology": "...",
  "difficulty_level": "Beginner/Intermediate/Advanced",
  "memory_tip": "..."
}}"""
        try:
            response = model.generate_content(prompt)
            raw = response.text.strip()
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            word_data = json.loads(raw)
            db = get_db()
            db.execute(
                "INSERT INTO vocabulary (user_id,word,definition,examples,synonyms) "
                "VALUES (?,?,?,?,?)",
                (session["user_id"], word_data["word"], word_data["definition"],
                 json.dumps(word_data.get("examples", [])),
                 json.dumps(word_data.get("synonyms", []))))
            db.commit()
        except Exception as e:
            flash(f"Error: {e}", "danger")

    saved = get_db().execute(
        "SELECT * FROM vocabulary WHERE user_id=? ORDER BY created_at DESC LIMIT 12",
        (session["user_id"],)).fetchall()
    return render_template("vocabulary.html", word_data=word_data, saved=saved)


# ─── Quiz generator ──────────────────────────────────────────────────────────

@app.route("/quiz", methods=["GET", "POST"])
@login_required
def quiz():
    if request.method == "POST":
        topic  = request.form["topic"].strip()
        level  = request.form.get("level", "Intermediate")
        count  = int(request.form.get("count", 5))
        prompt = f"""Generate {count} multiple-choice English language quiz questions on: "{topic}"
Difficulty: {level}

Respond ONLY in JSON:
{{
  "topic": "...",
  "questions": [
    {{
      "id": 1,
      "question": "...",
      "options": {{"A": "...", "B": "...", "C": "...", "D": "..."}},
      "correct": "A",
      "explanation": "..."
    }}
  ]
}}"""
        try:
            response = model.generate_content(prompt)
            raw = response.text.strip()
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            data = json.loads(raw)
            db = get_db()
            cur = db.execute(
                "INSERT INTO quizzes (user_id,topic,questions) VALUES (?,?,?)",
                (session["user_id"], topic, json.dumps(data["questions"])))
            db.commit()
            return redirect(url_for("take_quiz", quiz_id=cur.lastrowid))
        except Exception as e:
            flash(f"Error generating quiz: {e}", "danger")

    history = get_db().execute(
        "SELECT * FROM quizzes WHERE user_id=? ORDER BY created_at DESC LIMIT 10",
        (session["user_id"],)).fetchall()
    return render_template("quiz.html", history=history)


@app.route("/quiz/<int:quiz_id>", methods=["GET", "POST"])
@login_required
def take_quiz(quiz_id):
    db  = get_db()
    row = db.execute("SELECT * FROM quizzes WHERE id=? AND user_id=?",
                     (quiz_id, session["user_id"])).fetchone()
    if not row:
        flash("Quiz not found.", "danger")
        return redirect(url_for("quiz"))

    questions = json.loads(row["questions"])

    if request.method == "POST":
        score = 0
        results = []
        for q in questions:
            qid     = str(q["id"])
            answer  = request.form.get(f"q{qid}", "")
            correct = q["correct"]
            is_ok   = answer == correct
            if is_ok:
                score += 1
            results.append({**q, "user_answer": answer, "is_correct": is_ok})

        db.execute("UPDATE quizzes SET score=?, total=? WHERE id=?",
                   (score, len(questions), quiz_id))
        db.commit()
        return render_template("quiz_result.html",
                               results=results, score=score,
                               total=len(questions), topic=row["topic"])

    return render_template("take_quiz.html", quiz=row, questions=questions)


# ─── API endpoints ───────────────────────────────────────────────────────────

@app.route("/api/translate", methods=["POST"])
@login_required
def api_translate():
    data = request.json
    text, target = data.get("text",""), data.get("target_language","Spanish")
    prompt = f'Translate to {target}: "{text}"\nRespond with ONLY the translation.'
    try:
        resp = model.generate_content(prompt)
        return jsonify({"translation": resp.text.strip()})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/word_of_day")
@login_required
def word_of_day():
    prompt = """Generate a word of the day for English learners.
Respond in JSON:
{"word":"...","part_of_speech":"...","definition":"...","example":"...","tip":"..."}"""
    try:
        resp = model.generate_content(prompt)
        raw  = resp.text.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        return jsonify(json.loads(raw))
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ─── Jinja filters ───────────────────────────────────────────────────────────

@app.template_filter("from_json")
def from_json_filter(value):
    try:
        return json.loads(value)
    except Exception:
        return {}


# ─── Bootstrap ───────────────────────────────────────────────────────────────

with app.app_context():
    init_db()

if __name__ == "__main__":
    app.run(debug=True, port=5000)
