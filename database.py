import sqlite3
import datetime
from config import ADMINS, DEFAULT_WELCOME, WARN_THRESHOLD

DB_PATH = "chatroom.db"

def init_db():
    with sqlite3.connect(DB_PATH) as con:
        con.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            name TEXT,
            is_admin INTEGER DEFAULT 0,
            banned_until INTEGER,
            muted_until INTEGER,
            warns INTEGER DEFAULT 0,
            joined INTEGER DEFAULT 0,
            join_time INTEGER,
            pending INTEGER DEFAULT 0,
            is_vendor INTEGER DEFAULT 0
        )""")
        con.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            content TEXT,
            media_type TEXT,
            media_id TEXT,
            reply_to INTEGER,
            timestamp INTEGER
        )""")
        con.execute("""
        CREATE TABLE IF NOT EXISTS adminlog (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            admin_id INTEGER,
            target_id INTEGER,
            action TEXT,
            details TEXT,
            timestamp INTEGER
        )""")
        con.execute("""
        CREATE TABLE IF NOT EXISTS telegram_map (
            telegram_message_id INTEGER,
            db_message_id INTEGER,
            user_id INTEGER
        )""")
        con.execute("""
        CREATE TABLE IF NOT EXISTS pinned (msg_id INTEGER)
        """)
        con.execute("""
        CREATE TABLE IF NOT EXISTS user_pinned_msgs (
            user_id INTEGER PRIMARY KEY,
            telegram_message_id INTEGER
        )
        """)
        con.execute("""
        CREATE TABLE IF NOT EXISTS toggles (
            key TEXT PRIMARY KEY,
            value INTEGER
        )
        """)
        con.execute("""
        CREATE TABLE IF NOT EXISTS welcome_msg (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            text TEXT
        )
        """)
        con.execute("INSERT OR IGNORE INTO toggles (key, value) VALUES ('ban_links', 0)")
        con.execute("INSERT OR IGNORE INTO toggles (key, value) VALUES ('ban_media', 0)")
        con.execute("INSERT OR IGNORE INTO welcome_msg (id, text) VALUES (1, ?)", (DEFAULT_WELCOME,))

def add_user(user_id, username, name, approval_mode=False):
    ts = int(datetime.datetime.now().timestamp())
    pending = 1 if approval_mode else 0
    joined = 0 if approval_mode else 1
    with sqlite3.connect(DB_PATH) as con:
        con.execute(
            """
            INSERT INTO users (user_id, username, name, joined, join_time, pending)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                username=excluded.username,
                name=excluded.name,
                joined=?,
                pending=?
            """,
            (user_id, username, name, joined, ts, pending, joined, pending),
        )

def approve_user(user_id):
    with sqlite3.connect(DB_PATH) as con:
        con.execute("UPDATE users SET joined=1, pending=0 WHERE user_id=?", (user_id,))

def reject_user(user_id):
    with sqlite3.connect(DB_PATH) as con:
        con.execute("UPDATE users SET pending=0, joined=0 WHERE user_id=?", (user_id,))

def remove_user(user_id):
    with sqlite3.connect(DB_PATH) as con:
        con.execute("UPDATE users SET joined=0, pending=0 WHERE user_id=?", (user_id,))

def is_joined(user_id):
    with sqlite3.connect(DB_PATH) as con:
        cur = con.execute("SELECT joined FROM users WHERE user_id=?", (user_id,))
        row = cur.fetchone()
        return row and row[0] == 1

def is_pending(user_id):
    with sqlite3.connect(DB_PATH) as con:
        cur = con.execute("SELECT pending FROM users WHERE user_id=?", (user_id,))
        row = cur.fetchone()
        return row and row[0] == 1


def set_admin(user_id):
    with sqlite3.connect(DB_PATH) as con:
        con.execute("UPDATE users SET is_admin=1 WHERE user_id=?", (user_id,))

def remove_admin(user_id):
    with sqlite3.connect(DB_PATH) as con:
        con.execute("UPDATE users SET is_admin=0 WHERE user_id=?", (user_id,))

def is_admin(user_id):
    return int(user_id) in ADMINS

def get_user(user_id):
    with sqlite3.connect(DB_PATH) as con:
        cur = con.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
        return cur.fetchone()

def get_user_by_username(username):
    username = username.lstrip('@').lower()
    with sqlite3.connect(DB_PATH) as con:
        cur = con.execute(
            "SELECT * FROM users WHERE LOWER(username)=?", (username,))
        return cur.fetchone()

def get_all_joined_users():
    with sqlite3.connect(DB_PATH) as con:
        cur = con.execute("SELECT user_id FROM users WHERE joined=1")
        return [row[0] for row in cur.fetchall()]

def get_all_pending_users():
    with sqlite3.connect(DB_PATH) as con:
        cur = con.execute("SELECT user_id, username, name FROM users WHERE pending=1")
        return cur.fetchall()

def get_all_admins():
    with sqlite3.connect(DB_PATH) as con:
        cur = con.execute("SELECT user_id, name FROM users WHERE is_admin=1")
        return cur.fetchall()

def ban_user(user_id):
    until_ts = int(datetime.datetime(2100, 1, 1).timestamp())
    with sqlite3.connect(DB_PATH) as con:
        con.execute("UPDATE users SET banned_until=? WHERE user_id=?", (until_ts, user_id))

def unban_user(user_id):
    with sqlite3.connect(DB_PATH) as con:
        con.execute("UPDATE users SET banned_until=NULL WHERE user_id=?", (user_id,))

def mute_user(user_id, until_ts):
    with sqlite3.connect(DB_PATH) as con:
        con.execute("UPDATE users SET muted_until=? WHERE user_id=?", (until_ts, user_id))

def unmute_user(user_id):
    with sqlite3.connect(DB_PATH) as con:
        con.execute("UPDATE users SET muted_until=NULL WHERE user_id=?", (user_id,))

def warn_user(user_id):
    with sqlite3.connect(DB_PATH) as con:
        con.execute("UPDATE users SET warns = warns + 1 WHERE user_id=?", (user_id,))
    u = get_user(user_id)
    return u[6]

def reset_warns(user_id):
    with sqlite3.connect(DB_PATH) as con:
        con.execute("UPDATE users SET warns=0 WHERE user_id=?", (user_id,))

def get_warns(user_id):
    u = get_user(user_id)
    return u[6] if u else 0

def kick_user(user_id):
    with sqlite3.connect(DB_PATH) as con:
        con.execute("UPDATE users SET joined=0, pending=0 WHERE user_id=?", (user_id,))

def set_welcome(text):
    with sqlite3.connect(DB_PATH) as con:
        con.execute("INSERT OR REPLACE INTO welcome_msg (id, text) VALUES (1, ?)", (text,))

def get_welcome():
    with sqlite3.connect(DB_PATH) as con:
        cur = con.execute("SELECT text FROM welcome_msg WHERE id=1")
        r = cur.fetchone()
        return r[0] if r else DEFAULT_WELCOME

def set_pinned(msg_id):
    with sqlite3.connect(DB_PATH) as con:
        con.execute("DELETE FROM pinned")
        con.execute("INSERT INTO pinned (msg_id) VALUES (?)", (msg_id,))

def clear_pinned():
    with sqlite3.connect(DB_PATH) as con:
        con.execute("DELETE FROM pinned")

def get_pinned():
    with sqlite3.connect(DB_PATH) as con:
        cur = con.execute("SELECT msg_id FROM pinned").fetchone()
        return cur[0] if cur else None

def set_user_pinned_msg(user_id, telegram_message_id):
    with sqlite3.connect(DB_PATH) as con:
        con.execute("INSERT OR REPLACE INTO user_pinned_msgs (user_id, telegram_message_id) VALUES (?, ?)", (user_id, telegram_message_id))

def get_user_pinned_msg(user_id):
    with sqlite3.connect(DB_PATH) as con:
        cur = con.execute("SELECT telegram_message_id FROM user_pinned_msgs WHERE user_id=?", (user_id,))
        r = cur.fetchone()
        return r[0] if r else None

def clear_all_user_pinned_msgs():
    with sqlite3.connect(DB_PATH) as con:
        con.execute("DELETE FROM user_pinned_msgs")

def add_message(user_id, content, media_type, media_id, reply_to):
    ts = int(datetime.datetime.now().timestamp())
    with sqlite3.connect(DB_PATH) as con:
        cur = con.execute(
            "INSERT INTO messages (user_id, content, media_type, media_id, reply_to, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, content, media_type, media_id, reply_to, ts),
        )
        return cur.lastrowid

def get_message_by_id(msg_id):
    with sqlite3.connect(DB_PATH) as con:
        cur = con.execute(
            "SELECT m.*, u.username, u.name FROM messages m LEFT JOIN users u ON m.user_id = u.user_id WHERE m.id=?",
            (msg_id,))
        return cur.fetchone()

def get_messages(offset=0, limit=20):
    with sqlite3.connect(DB_PATH) as con:
        cur = con.execute(
            """
            SELECT m.id, m.user_id, u.username, u.name, m.content, m.media_type, m.media_id, m.reply_to, m.timestamp
            FROM messages m
            LEFT JOIN users u ON m.user_id = u.user_id
            ORDER BY m.timestamp ASC
            LIMIT ? OFFSET ?
            """, (limit, offset)
        )
        return cur.fetchall()

def delete_message(msg_id):
    with sqlite3.connect(DB_PATH) as con:
        con.execute("DELETE FROM messages WHERE id=?", (msg_id,))

def count_messages():
    with sqlite3.connect(DB_PATH) as con:
        cur = con.execute("SELECT COUNT(*) FROM messages")
        return cur.fetchone()[0]

def get_last_messages(n=20):
    with sqlite3.connect(DB_PATH) as con:
        cur = con.execute(
            """
            SELECT m.id, m.user_id, u.username, u.name, m.content, m.media_type, m.media_id, m.reply_to, m.timestamp
            FROM messages m
            LEFT JOIN users u ON m.user_id = u.user_id
            ORDER BY m.timestamp DESC
            LIMIT ?
            """, (n,)
        )
        return cur.fetchall()[::-1]

def map_telegram_to_db(telegram_message_id, db_message_id, user_id):
    with sqlite3.connect(DB_PATH) as con:
        con.execute(
            "INSERT INTO telegram_map (telegram_message_id, db_message_id, user_id) VALUES (?, ?, ?)",
            (telegram_message_id, db_message_id, user_id),
        )

def get_db_id_from_telegram(telegram_message_id):
    with sqlite3.connect(DB_PATH) as con:
        cur = con.execute(
            "SELECT db_message_id FROM telegram_map WHERE telegram_message_id=?",
            (telegram_message_id,)
        )
        row = cur.fetchone()
        return row[0] if row else None

def get_telegram_message_ids_for_db_message(db_message_id):
    with sqlite3.connect(DB_PATH) as con:
        cur = con.execute("SELECT user_id, telegram_message_id FROM telegram_map WHERE db_message_id=?", (db_message_id,))
        return cur.fetchall()

def log_admin_action(admin_id, target_id, action, details=""):
    ts = int(datetime.datetime.now().timestamp())
    with sqlite3.connect(DB_PATH) as con:
        con.execute(
            "INSERT INTO adminlog (admin_id, target_id, action, details, timestamp) VALUES (?, ?, ?, ?, ?)",
            (admin_id, target_id, action, details, ts)
        )

def get_admin_log(limit=20):
    with sqlite3.connect(DB_PATH) as con:
        cur = con.execute(
            """
            SELECT a.action, a.details, a.timestamp, u.name
            FROM adminlog a
            LEFT JOIN users u ON a.target_id = u.user_id
            ORDER BY a.timestamp DESC
            LIMIT ?
            """, (limit,))
        return cur.fetchall()

def get_modhistory(user_id, limit=20):
    with sqlite3.connect(DB_PATH) as con:
        cur = con.execute(
            "SELECT action, details, timestamp FROM adminlog WHERE target_id=? ORDER BY timestamp DESC LIMIT ?",
            (user_id, limit)
        )
        return cur.fetchall()

def get_toggle(key):
    with sqlite3.connect(DB_PATH) as con:
        cur = con.execute("SELECT value FROM toggles WHERE key=?", (key,))
        r = cur.fetchone()
        return r[0] if r else 0

def set_toggle(key, value):
    with sqlite3.connect(DB_PATH) as con:
        con.execute("INSERT OR REPLACE INTO toggles (key, value) VALUES (?, ?)", (key, value))

def add_name_history(user_id, name, username):
    ts = int(datetime.datetime.now().timestamp())
    with sqlite3.connect(DB_PATH) as con:
        last = con.execute(
            "SELECT name, username FROM name_history WHERE user_id=? ORDER BY id DESC LIMIT 1",
            (user_id,)
        ).fetchone()
        if last is None or last[0] != name or (last[1] or "") != (username or ""):
            con.execute(
                "INSERT INTO name_history (user_id, name, username, timestamp) VALUES (?, ?, ?, ?)",
                (user_id, name, username, ts)
            )

def get_name_history(user_id, limit=20):
    with sqlite3.connect(DB_PATH) as con:
        cur = con.execute(
            "SELECT name, username, timestamp FROM name_history WHERE user_id=? ORDER BY id DESC LIMIT ?",
            (user_id, limit)
        )
        return cur.fetchall()

# ---- VENDOR ROLE ----

def set_vendor(user_id):
    with sqlite3.connect(DB_PATH) as con:
        con.execute("UPDATE users SET is_vendor=1 WHERE user_id=?", (user_id,))

def remove_vendor(user_id):
    with sqlite3.connect(DB_PATH) as con:
        con.execute("UPDATE users SET is_vendor=0 WHERE user_id=?", (user_id,))

def is_vendor(user_id):
    with sqlite3.connect(DB_PATH) as con:
        r = con.execute("SELECT is_vendor FROM users WHERE user_id=?", (user_id,)).fetchone()
        return r and r[0] == 1

def get_all_vendors():
    with sqlite3.connect(DB_PATH) as con:
        cur = con.execute("SELECT user_id, username, name FROM users WHERE is_vendor=1")
        return cur.fetchall()

