import os
import sqlite3

# ── Phát hiện môi trường: Railway dùng PostgreSQL, local dùng SQLite ──
DATABASE_URL = os.environ.get('DATABASE_URL')

if DATABASE_URL:
    # Railway/Production: dùng PostgreSQL
    import psycopg2
    import psycopg2.extras

    # Railway đôi khi cấp URL dạng postgres://, psycopg2 cần postgresql://
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

    def get_db():
        """Trả về connection đến PostgreSQL (production)."""
        conn = psycopg2.connect(DATABASE_URL)
        return conn

    def _execute(conn, sql, params=()):
        """Helper: tự động chuyển ? → %s cho PostgreSQL."""
        sql = sql.replace('?', '%s')
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(sql, params)
        return cur

    def init_db():
        """Khởi tạo bảng PostgreSQL."""
        conn = get_db()
        c = conn.cursor()

        c.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id            SERIAL PRIMARY KEY,
                username      TEXT UNIQUE NOT NULL,
                phone         TEXT UNIQUE,
                password_hash TEXT NOT NULL,
                balance       INTEGER DEFAULT 0,
                total_items   INTEGER DEFAULT 0,
                face_descriptor TEXT,
                created_at    TIMESTAMP DEFAULT NOW()
            )
        ''')

        c.execute('''
            CREATE TABLE IF NOT EXISTS transactions (
                id         SERIAL PRIMARY KEY,
                token      TEXT UNIQUE NOT NULL,
                user_id    INTEGER,
                amount     INTEGER NOT NULL,
                items_data TEXT NOT NULL,
                status     TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT NOW(),
                claimed_at TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        ''')

        conn.commit()
        conn.close()
        print("[DB] PostgreSQL database khoi tao thanh cong.")

else:
    # Local: dùng SQLite như cũ
    DB_PATH = 'eco_coin.db'

    def get_db():
        """Trả về connection đến SQLite database."""
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        return conn

    def _execute(conn, sql, params=()):
        """Helper (SQLite không cần đổi ?)."""
        cur = conn.cursor()
        cur.execute(sql, params)
        return cur

    def init_db():
        """Khởi tạo SQLite database."""
        conn = get_db()
        c = conn.cursor()

        c.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                username     TEXT UNIQUE NOT NULL,
                phone        TEXT UNIQUE,
                password_hash TEXT NOT NULL,
                balance      INTEGER DEFAULT 0,
                total_items  INTEGER DEFAULT 0,
                face_descriptor TEXT,
                created_at   TEXT DEFAULT (datetime('now', 'localtime'))
            )
        ''')

        # Thêm cột face_descriptor nếu chưa có (cho DB cũ)
        try:
            c.execute('ALTER TABLE users ADD COLUMN face_descriptor TEXT')
            conn.commit()
        except Exception:
            pass

        c.execute('''
            CREATE TABLE IF NOT EXISTS transactions (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                token       TEXT UNIQUE NOT NULL,
                user_id     INTEGER,
                amount      INTEGER NOT NULL,
                items_data  TEXT NOT NULL,
                status      TEXT DEFAULT 'pending',
                created_at  TEXT DEFAULT (datetime('now', 'localtime')),
                claimed_at  TEXT,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        ''')

        conn.commit()
        conn.close()
        print("[DB] SQLite database khoi tao thanh cong.")
