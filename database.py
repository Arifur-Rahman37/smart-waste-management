import hashlib
import os
import secrets
import sqlite3
from datetime import datetime

import pandas as pd

from config import DEFAULT_ADMIN_EMAIL, DEFAULT_ADMIN_PASSWORD

DB_PATH = os.environ.get("WASTE_DB", os.path.join(os.path.dirname(os.path.abspath(__file__)), "waste.db"))


def _now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def conn():
    c = sqlite3.connect(DB_PATH, check_same_thread=False)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys = ON")
    return c


# ---------- security ----------
def hash_password(password: str, salt: str | None = None):
    salt = salt or secrets.token_hex(16)
    h = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 120_000).hex()
    return h, salt


# ---------- setup ----------
def init_db():
    with conn() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS users(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL, email TEXT UNIQUE NOT NULL, phone TEXT,
            password_hash TEXT NOT NULL, salt TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'citizen', created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS teams(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL, area TEXT, members INTEGER DEFAULT 3);
        CREATE TABLE IF NOT EXISTS reports(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id),
            title TEXT NOT NULL, description TEXT, category TEXT NOT NULL,
            address TEXT NOT NULL, lat REAL, lon REAL,
            priority TEXT NOT NULL DEFAULT 'Low', status TEXT NOT NULL DEFAULT 'Pending',
            photo BLOB, photo_name TEXT,
            team_id INTEGER REFERENCES teams(id), admin_note TEXT,
            created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS status_log(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            report_id INTEGER NOT NULL REFERENCES reports(id),
            status TEXT NOT NULL, note TEXT, changed_at TEXT NOT NULL);
        """)
        if not c.execute("SELECT 1 FROM users WHERE role='admin'").fetchone():
            h, s = hash_password(DEFAULT_ADMIN_PASSWORD)
            c.execute("INSERT INTO users(name,email,phone,password_hash,salt,role,created_at) VALUES(?,?,?,?,?,?,?)",
                      ("Municipal Admin", DEFAULT_ADMIN_EMAIL, "", h, s, "admin", _now()))
        if not c.execute("SELECT 1 FROM teams").fetchone():
            for n, a in [("Team Alpha", "North Zone"), ("Team Bravo", "South Zone"), ("Team Charlie", "East Zone")]:
                c.execute("INSERT INTO teams(name,area) VALUES(?,?)", (n, a))


# ---------- users ----------
def create_user(name, email, phone, password):
    h, s = hash_password(password)
    try:
        with conn() as c:
            c.execute("INSERT INTO users(name,email,phone,password_hash,salt,role,created_at) VALUES(?,?,?,?,?,'citizen',?)",
                      (name.strip(), email.strip().lower(), phone.strip(), h, s, _now()))
        return True, "Registration successful. Please log in."
    except sqlite3.IntegrityError:
        return False, "This email is already registered."


def authenticate(email, password):
    with conn() as c:
        row = c.execute("SELECT * FROM users WHERE email=?", (email.strip().lower(),)).fetchone()
    if not row:
        return None
    h, _ = hash_password(password, row["salt"])
    return dict(row) if secrets.compare_digest(h, row["password_hash"]) else None


# ---------- reports ----------
def add_report(user_id, title, description, category, address, lat, lon, priority, photo, photo_name):
    now = _now()
    with conn() as c:
        cur = c.execute("""INSERT INTO reports(user_id,title,description,category,address,lat,lon,priority,
                           status,photo,photo_name,created_at,updated_at)
                           VALUES(?,?,?,?,?,?,?,?, 'Pending',?,?,?,?)""",
                        (user_id, title, description, category, address, lat, lon, priority, photo, photo_name, now, now))
        rid = cur.lastrowid
        c.execute("INSERT INTO status_log(report_id,status,note,changed_at) VALUES(?,?,?,?)",
                  (rid, "Pending", "Report submitted", now))
    return rid


def get_reports(user_id=None, search="", status=None, category=None, priority=None,
                team_id=None, date_from=None, date_to=None) -> pd.DataFrame:
    q = """SELECT r.id, r.title, r.description, r.category, r.address, r.lat, r.lon, r.priority, r.status,
                  r.team_id, t.name AS team, r.admin_note, r.created_at, r.updated_at,
                  u.name AS citizen, u.email AS citizen_email, (r.photo IS NOT NULL) AS has_photo
           FROM reports r JOIN users u ON u.id=r.user_id LEFT JOIN teams t ON t.id=r.team_id WHERE 1=1"""
    p = []
    if user_id:
        q += " AND r.user_id=?"; p.append(user_id)
    if search:
        like = f"%{search.strip()}%"
        q += " AND (r.title LIKE ? OR r.description LIKE ? OR r.address LIKE ? OR CAST(r.id AS TEXT)=? OR u.name LIKE ?)"
        p += [like, like, like, search.strip(), like]
    for col, val in (("r.status", status), ("r.category", category), ("r.priority", priority)):
        if val:
            q += f" AND {col} IN ({','.join('?' * len(val))})"; p += list(val)
    if team_id:
        q += " AND r.team_id=?"; p.append(team_id)
    if date_from:
        q += " AND date(r.created_at)>=date(?)"; p.append(str(date_from))
    if date_to:
        q += " AND date(r.created_at)<=date(?)"; p.append(str(date_to))
    q += " ORDER BY r.id DESC"
    with conn() as c:
        return pd.read_sql_query(q, c, params=p)


def get_photo(report_id):
    with conn() as c:
        row = c.execute("SELECT photo FROM reports WHERE id=?", (report_id,)).fetchone()
    return row["photo"] if row else None


def update_report(report_id, status, priority, team_id, note):
    now = _now()
    with conn() as c:
        old = c.execute("SELECT status, team_id FROM reports WHERE id=?", (report_id,)).fetchone()
        # assigning a team to a pending report moves it to 'Assigned'
        if team_id and old["team_id"] != team_id and status == "Pending":
            status = "Assigned"
        c.execute("UPDATE reports SET status=?, priority=?, team_id=?, admin_note=?, updated_at=? WHERE id=?",
                  (status, priority, team_id, note, now, report_id))
        if old["status"] != status or note:
            c.execute("INSERT INTO status_log(report_id,status,note,changed_at) VALUES(?,?,?,?)",
                      (report_id, status, note or "Status updated", now))
    return status


def get_status_log(report_id) -> pd.DataFrame:
    with conn() as c:
        return pd.read_sql_query("SELECT status, note, changed_at FROM status_log WHERE report_id=? ORDER BY id",
                                 c, params=[report_id])


# ---------- teams ----------
def get_teams() -> pd.DataFrame:
    with conn() as c:
        return pd.read_sql_query("SELECT * FROM teams ORDER BY id", c)


def add_team(name, area, members):
    try:
        with conn() as c:
            c.execute("INSERT INTO teams(name,area,members) VALUES(?,?,?)", (name.strip(), area.strip(), members))
        return True
    except sqlite3.IntegrityError:
        return False


# ---------- demo data ----------
def seed_demo():
    import random
    from datetime import timedelta
    from classifier import classify_priority
    from config import CATEGORIES
    h, s = hash_password("demo123")
    with conn() as c:
        c.execute("INSERT OR IGNORE INTO users(name,email,phone,password_hash,salt,role,created_at) VALUES(?,?,?,?,?,'citizen',?)",
                  ("Demo Citizen", "citizen@demo.com", "01700000000", h, s, _now()))
        uid = c.execute("SELECT id FROM users WHERE email='citizen@demo.com'").fetchone()["id"]
        tids = [r["id"] for r in c.execute("SELECT id FROM teams")]
    samples = [
        ("Bin overflowing near market", "Garbage not collected for 5 days, bad smell near the market", "Overflowing Bin", "Savar Bazar"),
        ("Illegal dumping behind school", "Construction waste dumped near the school gate", "Illegal Dumping", "Savar, near Govt School"),
        ("Medical waste on roadside", "Syringes and medical waste found, children play nearby", "Hazardous Waste", "Ashulia Road"),
        ("Delayed pickup", "Collection delayed for a week in our lane", "Delayed Collection", "Genda, Savar"),
        ("Drain blocked with plastic", "Waste blocking drain, flooding risk", "Blocked Drain / Waste in Drain", "Nabinagar"),
        ("Dead animal on road", "Rotten smell, dead animal on the road", "Dead Animal", "Dhamrai Road"),
        ("Pile of debris", "Debris pile on footpath", "Construction Debris", "Hemayetpur"),
    ]
    for i in range(18):
        t, d, cat, addr = random.choice(samples)
        pr, _, _ = classify_priority(t, d, cat)
        rid = add_report(uid, t, d, cat, addr, 23.84 + random.uniform(-0.04, 0.04),
                         90.26 + random.uniform(-0.05, 0.05), pr, None, None)
        when = datetime.now() - timedelta(days=random.randint(0, 200), hours=random.randint(0, 23))
        st = random.choice(["Pending", "Assigned", "In Progress", "Collected", "Collected", "Rejected"])
        tid = random.choice(tids) if st != "Pending" else None
        upd = when + timedelta(hours=random.randint(2, 90))
        with conn() as c:
            c.execute("UPDATE reports SET created_at=?, updated_at=?, status=?, team_id=? WHERE id=?",
                      (when.strftime("%Y-%m-%d %H:%M:%S"), upd.strftime("%Y-%m-%d %H:%M:%S"), st, tid, rid))
            c.execute("UPDATE status_log SET changed_at=? WHERE report_id=?", (when.strftime("%Y-%m-%d %H:%M:%S"), rid))
            if st != "Pending":
                c.execute("INSERT INTO status_log(report_id,status,note,changed_at) VALUES(?,?,?,?)",
                          (rid, st, "Demo update", upd.strftime("%Y-%m-%d %H:%M:%S")))
