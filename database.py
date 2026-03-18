# database.py
import sqlite3
import hashlib
import json
import os
from datetime import datetime

DB_PATH = "resume_ranker.db"


def get_connection():
    """Get SQLite database connection."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initialize database tables."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            full_name TEXT,
            company TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            session_name TEXT,
            job_description TEXT,
            results_json TEXT,
            candidate_count INTEGER,
            avg_score REAL,
            top_score REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS resumes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER,
            filename TEXT,
            email TEXT,
            phone TEXT,
            score REAL,
            skills TEXT,
            education TEXT,
            experience_years INTEGER,
            resume_text TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (session_id) REFERENCES sessions(id)
        );

        CREATE TABLE IF NOT EXISTS custom_skills (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            skill_name TEXT,
            category TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );
    """)

    conn.commit()
    conn.close()


# ─── Authentication ───
def hash_password(password):
    """Hash password with SHA-256."""
    return hashlib.sha256(password.encode()).hexdigest()


def create_user(username, password, full_name="", company=""):
    """Create a new user account."""
    conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO users (username, password_hash, full_name, company) VALUES (?, ?, ?, ?)",
            (username, hash_password(password), full_name, company)
        )
        conn.commit()
        return True, "Account created successfully!"
    except sqlite3.IntegrityError:
        return False, "Username already exists."
    finally:
        conn.close()


def verify_user(username, password):
    """Verify user credentials."""
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM users WHERE username = ? AND password_hash = ?",
        (username, hash_password(password))
    ).fetchone()
    conn.close()
    if row:
        return True, dict(row)
    return False, None


def get_user_by_id(user_id):
    """Get user by ID."""
    conn = get_connection()
    row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


# ─── Session Management ───
def save_session(user_id, session_name, job_description, ranked_results):
    """Save an analysis session to the database."""
    conn = get_connection()
    avg_score = sum(r['score'] for r in ranked_results) / len(ranked_results) if ranked_results else 0
    top_score = ranked_results[0]['score'] if ranked_results else 0

    # Serialize results to JSON (exclude large text fields for storage)
    results_json = json.dumps([
        {k: v for k, v in r.items() if k != 'text'}
        for r in ranked_results
    ])

    cursor = conn.execute(
        """INSERT INTO sessions (user_id, session_name, job_description, results_json,
           candidate_count, avg_score, top_score) VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (user_id, session_name, job_description, results_json,
         len(ranked_results), avg_score, top_score)
    )
    session_id = cursor.lastrowid

    # Save individual resumes
    for r in ranked_results:
        conn.execute(
            """INSERT INTO resumes (session_id, filename, email, phone, score, skills,
               education, experience_years, resume_text) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (session_id, r['filename'], r.get('email', ''), r.get('phone', ''),
             r['score'], json.dumps(r.get('skills', [])), r.get('education', ''),
             r.get('experience_years', 0), r.get('text', '')[:5000])
        )

    conn.commit()
    conn.close()
    return session_id


def get_user_sessions(user_id, limit=20):
    """Get recent sessions for a user."""
    conn = get_connection()
    rows = conn.execute(
        """SELECT id, session_name, candidate_count, avg_score, top_score, created_at
           FROM sessions WHERE user_id = ? ORDER BY created_at DESC LIMIT ?""",
        (user_id, limit)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def load_session(session_id):
    """Load a specific session with full results."""
    conn = get_connection()
    session = conn.execute("SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone()
    conn.close()
    if session:
        session_dict = dict(session)
        session_dict['results'] = json.loads(session_dict['results_json'])
        return session_dict
    return None


def get_all_sessions_for_trends(user_id=None):
    """Get all sessions for trend analysis."""
    conn = get_connection()
    if user_id:
        rows = conn.execute(
            "SELECT * FROM sessions WHERE user_id = ? ORDER BY created_at ASC",
            (user_id,)
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM sessions ORDER BY created_at ASC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def delete_session(session_id):
    """Delete a session and its resumes."""
    conn = get_connection()
    conn.execute("DELETE FROM resumes WHERE session_id = ?", (session_id,))
    conn.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
    conn.commit()
    conn.close()


# ─── Custom Skills ───
def save_custom_skills(user_id, skills):
    """Save custom skills for a user."""
    conn = get_connection()
    conn.execute("DELETE FROM custom_skills WHERE user_id = ?", (user_id,))
    for skill in skills:
        conn.execute(
            "INSERT INTO custom_skills (user_id, skill_name, category) VALUES (?, ?, ?)",
            (user_id, skill.get('name', ''), skill.get('category', 'general'))
        )
    conn.commit()
    conn.close()


def get_custom_skills(user_id):
    """Get custom skills for a user."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT skill_name, category FROM custom_skills WHERE user_id = ?",
        (user_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# Initialize on import
init_db()
