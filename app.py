"""Seahawks Connect: an educational university-club activities application.

Run locally with: python app.py
The application creates a sample SQLite database on its first run.
"""

from __future__ import annotations

import os
import secrets
import sqlite3
from datetime import datetime, timedelta
from functools import wraps
from pathlib import Path

from flask import (
    Flask, abort, flash, g, redirect, render_template, request, session, url_for
)
from werkzeug.security import check_password_hash, generate_password_hash

BASE_DIR = Path(__file__).resolve().parent
app = Flask(__name__)
app.config.update(
    SECRET_KEY=os.environ.get("SECRET_KEY", "development-only-secret-change-before-deployment"),
    DATABASE=str(os.environ.get("DATABASE_PATH", BASE_DIR / "instance" / "campusconnect.sqlite3")),
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
)

SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    full_name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE COLLATE NOCASE,
    password_hash TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS clubs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    category TEXT NOT NULL,
    description TEXT NOT NULL,
    icon TEXT NOT NULL DEFAULT '🎓'
);

CREATE TABLE IF NOT EXISTS club_leaders (
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    club_id INTEGER NOT NULL REFERENCES clubs(id) ON DELETE CASCADE,
    PRIMARY KEY (user_id, club_id)
);

CREATE TABLE IF NOT EXISTS club_memberships (
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    club_id INTEGER NOT NULL REFERENCES clubs(id) ON DELETE CASCADE,
    joined_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, club_id)
);

CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    club_id INTEGER NOT NULL REFERENCES clubs(id),
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    location TEXT NOT NULL,
    start_at TEXT NOT NULL,
    capacity INTEGER NOT NULL CHECK (capacity BETWEEN 1 AND 10000),
    is_cancelled INTEGER NOT NULL DEFAULT 0 CHECK (is_cancelled IN (0,1)),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS registrations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id INTEGER NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    registered_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    attended_at TEXT,
    UNIQUE (event_id, user_id)
);

CREATE INDEX IF NOT EXISTS idx_events_club_date ON events(club_id, start_at);
CREATE INDEX IF NOT EXISTS idx_registrations_user ON registrations(user_id);
"""


def db() -> sqlite3.Connection:
    if "db" not in g:
        Path(app.config["DATABASE"]).parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(app.config["DATABASE"], timeout=10)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        g.db = conn
    return g.db


@app.teardown_appcontext
def close_db(exc: Exception | None = None) -> None:
    conn = g.pop("db", None)
    if conn is not None:
        conn.close()


def init_db(seed: bool = True) -> None:
    conn = db()
    conn.executescript(SCHEMA)
    if seed and conn.execute("SELECT COUNT(*) FROM clubs").fetchone()[0] == 0:
        seed_db(conn)
    conn.commit()


def seed_db(conn: sqlite3.Connection) -> None:
    """Insert harmless demonstration records into a new database only."""
    demo_password = generate_password_hash("Demo1234!")
    conn.executemany(
        "INSERT INTO users (full_name, email, password_hash) VALUES (?, ?, ?)",
        [
            ("Alex Rivera", "student@campusconnect.test", demo_password),
            ("Jordan Lee", "leader@campusconnect.test", demo_password),
        ],
    )
    conn.executemany(
        "INSERT INTO clubs (name, category, description, icon) VALUES (?, ?, ?, ?)",
        [
            ("Business Club", "Professional Development", "Networking, entrepreneurship, leadership, and practical business skills.", "💼"),
            ("Student Government Association", "Student Leadership", "Represent student voices and help create a stronger campus community.", "🏛️"),
            ("Coding & AI Club", "Technology", "Build projects, explore artificial intelligence, and learn together.", "💻"),
            ("Sports & Wellness Club", "Wellness", "Stay active through friendly sports, fitness, and wellness events.", "🏃"),
        ],
    )
    conn.executemany(
        "INSERT INTO club_leaders (user_id, club_id) VALUES (?, ?)", [(2, 1), (2, 2)]
    )
    conn.executemany(
        "INSERT INTO club_memberships (user_id, club_id) VALUES (?, ?)",
        [(1, 1), (1, 3), (2, 1), (2, 2)],
    )
    today = datetime.now().replace(hour=15, minute=0, second=0, microsecond=0)
    events = [
        (1, "Business & AI Networking Mixer", "Meet students interested in business intelligence, technology, and networking.", "Student Center", 3, 45),
        (2, "Campus Leadership Forum", "Share ideas to improve student activities and campus life.", "Main Auditorium", 5, 70),
        (3, "Introduction to Web Development", "A beginner-friendly workshop on building your first website.", "Computer Lab 2", 7, 30),
        (4, "Friday Fitness Meetup", "Join a group workout and connect with other active students.", "University Gym", 9, 40),
        (1, "Entrepreneurship Roundtable", "Discuss how to turn everyday problems into business opportunities.", "Room B204", 12, 25),
    ]
    conn.executemany(
        "INSERT INTO events (club_id, title, description, location, start_at, capacity) VALUES (?, ?, ?, ?, ?, ?)",
        [(club_id, title, desc, loc, (today + timedelta(days=offset)).isoformat(timespec="minutes"), cap)
         for club_id, title, desc, loc, offset, cap in events],
    )
    conn.execute("INSERT INTO registrations (event_id, user_id) VALUES (1, 1)")


def logged_in() -> bool:
    return "user_id" in session


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not logged_in():
            flash("Please log in to continue.", "warning")
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped


def is_leader(club_id: int) -> bool:
    return logged_in() and db().execute(
        "SELECT 1 FROM club_leaders WHERE club_id = ? AND user_id = ?",
        (club_id, session["user_id"]),
    ).fetchone() is not None


def leader_required_for_event(event_id: int):
    event = db().execute("SELECT * FROM events WHERE id = ?", (event_id,)).fetchone()
    if not event:
        abort(404)
    if not is_leader(event["club_id"]):
        abort(403)
    return event


@app.before_request
def csrf_protection():
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_hex(24)
    if request.method == "POST":
        if not secrets.compare_digest(session["csrf_token"], request.form.get("csrf_token", "")):
            abort(400, description="Invalid or missing form security token.")


@app.context_processor
def inject_common():
    current_user = None
    if logged_in():
        current_user = db().execute(
            "SELECT id, full_name, email FROM users WHERE id = ?", (session["user_id"],)
        ).fetchone()
    return {
        "current_user": current_user,
        "csrf_token": session.get("csrf_token"),
        "current_year": datetime.now().year,
        "now_iso": datetime.now().isoformat(timespec="minutes"),
    }


@app.template_filter("pretty_date")
def pretty_date(value: str) -> str:
    try:
        return datetime.fromisoformat(value).strftime("%b %d, %Y · %I:%M %p")
    except (TypeError, ValueError):
        return value


@app.route("/")
def index():
    events = db().execute("""
        SELECT e.*, c.name AS club_name, c.icon AS club_icon,
          (SELECT COUNT(*) FROM registrations r WHERE r.event_id = e.id) AS registered_count
        FROM events e JOIN clubs c ON c.id = e.club_id
        WHERE e.is_cancelled = 0 AND e.start_at >= ?
        ORDER BY e.start_at LIMIT 6
    """, (datetime.now().isoformat(timespec="minutes"),)).fetchall()
    metrics = {
        "clubs": db().execute("SELECT COUNT(*) FROM clubs").fetchone()[0],
        "events": db().execute("SELECT COUNT(*) FROM events WHERE is_cancelled = 0").fetchone()[0],
        "students": db().execute("SELECT COUNT(*) FROM users").fetchone()[0],
    }
    return render_template("index.html", events=events, metrics=metrics)


@app.route("/register", methods=["GET", "POST"])
def register():
    if logged_in():
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        name = request.form.get("full_name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        if not name or len(name) > 100 or not email or "@" not in email or len(email) > 254:
            flash("Enter a valid name and email address.", "error")
        elif len(password) < 8:
            flash("Your password must be at least 8 characters.", "error")
        else:
            try:
                cursor = db().execute(
                    "INSERT INTO users (full_name, email, password_hash) VALUES (?, ?, ?)",
                    (name, email, generate_password_hash(password)),
                )
                db().commit()
                session.clear()
                session["user_id"] = cursor.lastrowid
                flash("Welcome to Seahawks Connect!", "success")
                return redirect(url_for("dashboard"))
            except sqlite3.IntegrityError:
                db().rollback()
                flash("An account with this email already exists.", "error")
    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if logged_in():
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = db().execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        if user and check_password_hash(user["password_hash"], password):
            session.clear()
            session["user_id"] = user["id"]
            flash("You are now logged in.", "success")
            return redirect(url_for("dashboard"))
        flash("Incorrect email or password.", "error")
    return render_template("login.html")


@app.route("/logout", methods=["POST"])
@login_required
def logout():
    session.clear()
    flash("You have logged out.", "success")
    return redirect(url_for("index"))


@app.route("/clubs")
def clubs():
    rows = db().execute("""
        SELECT c.*, COUNT(cm.user_id) AS member_count,
          (SELECT COUNT(*) FROM events e WHERE e.club_id = c.id AND e.is_cancelled = 0) AS event_count
        FROM clubs c LEFT JOIN club_memberships cm ON cm.club_id = c.id
        GROUP BY c.id ORDER BY c.name
    """).fetchall()
    return render_template("clubs.html", clubs=rows)


@app.route("/clubs/<int:club_id>")
def club_detail(club_id: int):
    club = db().execute("""
        SELECT c.*, (SELECT COUNT(*) FROM club_memberships cm WHERE cm.club_id = c.id) AS member_count
        FROM clubs c WHERE c.id = ?
    """, (club_id,)).fetchone()
    if not club:
        abort(404)
    events = db().execute("""
        SELECT e.*, (SELECT COUNT(*) FROM registrations r WHERE r.event_id = e.id) AS registered_count
        FROM events e WHERE e.club_id = ? ORDER BY e.start_at DESC
    """, (club_id,)).fetchall()
    joined = bool(logged_in() and db().execute(
        "SELECT 1 FROM club_memberships WHERE club_id = ? AND user_id = ?",
        (club_id, session["user_id"]),
    ).fetchone())
    return render_template("club_detail.html", club=club, events=events,
                           joined=joined, leader=is_leader(club_id))


@app.route("/clubs/<int:club_id>/membership", methods=["POST"])
@login_required
def change_membership(club_id: int):
    club = db().execute("SELECT * FROM clubs WHERE id = ?", (club_id,)).fetchone()
    if not club:
        abort(404)
    existing = db().execute(
        "SELECT 1 FROM club_memberships WHERE club_id = ? AND user_id = ?",
        (club_id, session["user_id"]),
    ).fetchone()
    if existing:
        if is_leader(club_id):
            flash("A club leader cannot leave their assigned club.", "warning")
        else:
            db().execute("DELETE FROM club_memberships WHERE club_id = ? AND user_id = ?",
                         (club_id, session["user_id"]))
            db().commit()
            flash("You left this club.", "success")
    else:
        db().execute("INSERT INTO club_memberships (club_id, user_id) VALUES (?, ?)",
                     (club_id, session["user_id"]))
        db().commit()
        flash("You've joined this club!", "success")
    return redirect(url_for("club_detail", club_id=club_id))


@app.route("/events")
def events():
    rows = db().execute("""
        SELECT e.*, c.name AS club_name, c.icon AS club_icon,
          (SELECT COUNT(*) FROM registrations r WHERE r.event_id = e.id) AS registered_count
        FROM events e JOIN clubs c ON c.id = e.club_id
        ORDER BY e.is_cancelled, e.start_at
    """).fetchall()
    return render_template("events.html", events=rows)


@app.route("/events/<int:event_id>")
def event_detail(event_id: int):
    event = db().execute("""
        SELECT e.*, c.name AS club_name, c.icon AS club_icon,
          (SELECT COUNT(*) FROM registrations r WHERE r.event_id = e.id) AS registered_count
        FROM events e JOIN clubs c ON c.id = e.club_id WHERE e.id = ?
    """, (event_id,)).fetchone()
    if not event:
        abort(404)
    registration = None
    if logged_in():
        registration = db().execute(
            "SELECT * FROM registrations WHERE event_id = ? AND user_id = ?",
            (event_id, session["user_id"]),
        ).fetchone()
    return render_template("event_detail.html", event=event, registration=registration,
                           leader=is_leader(event["club_id"]),
                           in_past=event["start_at"] < datetime.now().isoformat(timespec="minutes"))


@app.route("/events/<int:event_id>/registration", methods=["POST"])
@login_required
def change_registration(event_id: int):
    conn = db()
    # Serialize concurrent registration requests before checking capacity.
    conn.execute("BEGIN IMMEDIATE")
    try:
        event = conn.execute("SELECT * FROM events WHERE id = ?", (event_id,)).fetchone()
        if not event:
            conn.rollback()
            abort(404)
        existing = conn.execute(
            "SELECT id, attended_at FROM registrations WHERE event_id = ? AND user_id = ?",
            (event_id, session["user_id"]),
        ).fetchone()
        if existing:
            if existing["attended_at"]:
                flash("Attendance has already been recorded; this registration cannot be removed.", "warning")
            else:
                conn.execute("DELETE FROM registrations WHERE id = ?", (existing["id"],))
                flash("Your event registration was cancelled.", "success")
        elif event["is_cancelled"] or event["start_at"] < datetime.now().isoformat(timespec="minutes"):
            flash("Registration is closed for this event.", "warning")
        elif conn.execute("SELECT COUNT(*) FROM registrations WHERE event_id = ?",
                          (event_id,)).fetchone()[0] >= event["capacity"]:
            flash("This event is full.", "warning")
        else:
            conn.execute("INSERT INTO registrations (event_id, user_id) VALUES (?, ?)",
                         (event_id, session["user_id"]))
            flash("You are registered for this event!", "success")
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    return redirect(url_for("event_detail", event_id=event_id))


def event_form_values(form):
    title = form.get("title", "").strip()
    desc = form.get("description", "").strip()
    location = form.get("location", "").strip()
    start_at = form.get("start_at", "").strip()
    try:
        cap = int(form.get("capacity", ""))
        start_dt = datetime.fromisoformat(start_at)
    except (ValueError, TypeError):
        return None, "Enter a valid start date and capacity."
    if not (3 <= len(title) <= 120) or not (5 <= len(desc) <= 1500) or not (2 <= len(location) <= 120):
        return None, "Please provide a title, description, and location within the limits."
    if not 1 <= cap <= 10000:
        return None, "Capacity must be between 1 and 10,000."
    if start_dt <= datetime.now():
        return None, "The event date must be in the future."
    return {"title": title, "description": desc, "location": location,
            "start_at": start_dt.isoformat(timespec="minutes"), "capacity": cap}, None


@app.route("/clubs/<int:club_id>/events/new", methods=["GET", "POST"])
@login_required
def event_new(club_id: int):
    club = db().execute("SELECT * FROM clubs WHERE id = ?", (club_id,)).fetchone()
    if not club:
        abort(404)
    if not is_leader(club_id):
        abort(403)
    if request.method == "POST":
        data, error = event_form_values(request.form)
        if error:
            flash(error, "error")
        else:
            cursor = db().execute("""
                INSERT INTO events (club_id, title, description, location, start_at, capacity)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (club_id, data["title"], data["description"], data["location"],
                  data["start_at"], data["capacity"]))
            db().commit()
            flash("Event published successfully.", "success")
            return redirect(url_for("event_detail", event_id=cursor.lastrowid))
    return render_template("event_form.html", club=club, event=None)


@app.route("/events/<int:event_id>/edit", methods=["GET", "POST"])
@login_required
def event_edit(event_id: int):
    event = leader_required_for_event(event_id)
    club = db().execute("SELECT * FROM clubs WHERE id = ?", (event["club_id"],)).fetchone()
    if event["is_cancelled"]:
        abort(400, description="Cancelled events cannot be edited.")
    if request.method == "POST":
        data, error = event_form_values(request.form)
        if error:
            flash(error, "error")
        elif data["capacity"] < db().execute(
            "SELECT COUNT(*) FROM registrations WHERE event_id = ?", (event_id,)
        ).fetchone()[0]:
            flash("Capacity cannot be smaller than current registrations.", "error")
        else:
            db().execute("""
                UPDATE events SET title=?, description=?, location=?, start_at=?, capacity=? WHERE id=?
            """, (data["title"], data["description"], data["location"],
                  data["start_at"], data["capacity"], event_id))
            db().commit()
            flash("Event updated.", "success")
            return redirect(url_for("event_detail", event_id=event_id))
    return render_template("event_form.html", club=club, event=event)


@app.route("/events/<int:event_id>/cancel", methods=["POST"])
@login_required
def event_cancel(event_id: int):
    leader_required_for_event(event_id)
    db().execute("UPDATE events SET is_cancelled = 1 WHERE id = ?", (event_id,))
    db().commit()
    flash("Event cancelled. Registration and attendance history was preserved.", "success")
    return redirect(url_for("event_detail", event_id=event_id))


@app.route("/events/<int:event_id>/attendance", methods=["GET", "POST"])
@login_required
def attendance(event_id: int):
    event = leader_required_for_event(event_id)
    if request.method == "POST":
        registration_id = request.form.get("registration_id", "")
        if not registration_id.isdigit():
            abort(400)
        # Restrict mutation to registrations that belong to this event.
        result = db().execute("""
            UPDATE registrations SET attended_at = COALESCE(attended_at, CURRENT_TIMESTAMP)
            WHERE id = ? AND event_id = ?
        """, (int(registration_id), event_id))
        db().commit()
        if result.rowcount == 0:
            abort(404)
        flash("Attendance marked successfully.", "success")
        return redirect(url_for("attendance", event_id=event_id))
    registrations = db().execute("""
        SELECT r.id, r.registered_at, r.attended_at, u.full_name, u.email
        FROM registrations r JOIN users u ON u.id = r.user_id
        WHERE r.event_id = ? ORDER BY u.full_name
    """, (event_id,)).fetchall()
    return render_template("attendance.html", event=event, registrations=registrations)


@app.route("/dashboard")
@login_required
def dashboard():
    my_events = db().execute("""
        SELECT e.*, c.name AS club_name, c.icon AS club_icon, r.attended_at
        FROM registrations r JOIN events e ON e.id = r.event_id
        JOIN clubs c ON c.id = e.club_id
        WHERE r.user_id = ? ORDER BY e.start_at
    """, (session["user_id"],)).fetchall()
    my_clubs = db().execute("""
        SELECT c.* FROM club_memberships m JOIN clubs c ON c.id = m.club_id
        WHERE m.user_id = ? ORDER BY c.name
    """, (session["user_id"],)).fetchall()
    led_clubs = db().execute("""
        SELECT c.* FROM club_leaders l JOIN clubs c ON c.id = l.club_id
        WHERE l.user_id = ? ORDER BY c.name
    """, (session["user_id"],)).fetchall()
    return render_template("dashboard.html", my_events=my_events, my_clubs=my_clubs,
                           led_clubs=led_clubs)


if __name__ == "__main__":
    with app.app_context():
        init_db()
    # Debug mode is for local coursework development only.
    app.run(debug=True)
