"""Account store: PostgreSQL for hosted play, SQLite for local development.

Passwords use PBKDF2-HMAC-SHA256 with per-user random salts. Sessions are
opaque random tokens stored only as SHA256 hashes.
"""
from __future__ import annotations

from contextlib import contextmanager
import hashlib
import hmac
import os
import re
import secrets
import sqlite3
import time
import unicodedata
from pathlib import Path

DB = Path(os.environ.get('DATA_DIR', str(Path(__file__).parent / 'data'))) / 'accounts.sqlite3'
SESSION_TTL = 60 * 60 * 24 * 30
USERNAME_PATTERN = re.compile(r'^[A-Za-z0-9_]{3,20}$')


class Database:
    def __init__(self, conn, postgres=False):
        self.conn, self.postgres = conn, postgres

    def execute(self, sql, params=()):
        if self.postgres:
            sql = sql.replace('?', '%s')
        return self.conn.execute(sql, params)


@contextmanager
def _connection():
    uri = os.environ.get('DATABASE_URL')
    if uri:
        import psycopg
        from psycopg.rows import dict_row
        conn = psycopg.connect(uri, row_factory=dict_row, connect_timeout=10)
        db = Database(conn, True)
    else:
        DB.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(DB, timeout=10)
        conn.row_factory = sqlite3.Row
        conn.execute('PRAGMA journal_mode=WAL')
        db = Database(conn)
    try:
        db.execute('CREATE TABLE IF NOT EXISTS users (id TEXT PRIMARY KEY, username TEXT NOT NULL, username_key TEXT NOT NULL UNIQUE, salt TEXT NOT NULL, password_hash TEXT NOT NULL, created_at BIGINT NOT NULL)')
        db.execute('CREATE TABLE IF NOT EXISTS sessions (token_hash TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users(id), expires_at BIGINT NOT NULL)')
        yield db
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _username_key(username):
    return unicodedata.normalize('NFKC', username).casefold()


def _password_hash(password: str, salt: str):
    return hashlib.pbkdf2_hmac('sha256', password.encode(), bytes.fromhex(salt), 310_000).hex()


def register(username: str, password: str):
    username = username.strip()
    if not USERNAME_PATTERN.fullmatch(username):
        raise ValueError('Kullanıcı adı 3–20 karakter olmalı; yalnızca harf, rakam ve _ kullanılabilir.')
    if not 8 <= len(password) <= 128:
        raise ValueError('Şifre 8–128 karakter olmalı.')
    import uuid
    uid = uuid.uuid4().hex
    salt = secrets.token_hex(16)
    try:
        with _connection() as conn:
            conn.execute('INSERT INTO users VALUES (?,?,?,?,?,?)',
                         (uid, username, _username_key(username), salt, _password_hash(password, salt), int(time.time())))
    except Exception as exc:
        if isinstance(exc, sqlite3.IntegrityError) or getattr(exc, 'sqlstate', None) == '23505':
            raise ValueError('Bu kullanıcı adı zaten alınmış.') from None
        raise
    return new_session(uid)


def login(username: str, password: str):
    with _connection() as conn:
        user = conn.execute('SELECT * FROM users WHERE username_key=?', (_username_key(username.strip()),)).fetchone()
    if not user or not hmac.compare_digest(_password_hash(password, user['salt']), user['password_hash']):
        raise ValueError('Kullanıcı adı veya şifre hatalı.')
    return new_session(user['id'])


def new_session(uid: str):
    token = secrets.token_urlsafe(32)
    with _connection() as conn:
        conn.execute('INSERT INTO sessions VALUES (?,?,?)',
                     (hashlib.sha256(token.encode()).hexdigest(), uid, int(time.time()) + SESSION_TTL))
        row = conn.execute('SELECT username FROM users WHERE id=?', (uid,)).fetchone()
    return {'token': token, 'username': row['username'], 'user_id': uid}


def identify(token: str | None):
    if not token:
        return None
    digest = hashlib.sha256(token.encode()).hexdigest()
    with _connection() as conn:
        row = conn.execute('''SELECT users.id, users.username FROM sessions
                   JOIN users ON users.id = sessions.user_id
                   WHERE token_hash=? AND expires_at>?''', (digest, int(time.time()))).fetchone()
    return dict(row) if row else None


def logout(token: str | None):
    if token:
        with _connection() as conn:
            conn.execute('DELETE FROM sessions WHERE token_hash=?', (hashlib.sha256(token.encode()).hexdigest(),))
