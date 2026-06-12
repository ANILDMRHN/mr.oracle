import sqlite3
import os
from config import STARTING_BALANCE

DB_PATH = os.path.join(os.path.dirname(__file__), "data.db")


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            guild_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            balance INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY (guild_id, user_id)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS predictions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id INTEGER NOT NULL,
            channel_id INTEGER,
            message_id INTEGER,
            question TEXT NOT NULL,
            option_a TEXT NOT NULL,
            option_b TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'open',
            winner TEXT,
            created_by INTEGER NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS bets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            prediction_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            option TEXT NOT NULL,
            amount INTEGER NOT NULL,
            FOREIGN KEY (prediction_id) REFERENCES predictions (id)
        )
    """)

    conn.commit()
    conn.close()


# ---------------- Kullanıcı / Bakiye ----------------

def ensure_user(guild_id: int, user_id: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT OR IGNORE INTO users (guild_id, user_id, balance) VALUES (?, ?, ?)",
        (guild_id, user_id, STARTING_BALANCE),
    )
    conn.commit()
    conn.close()


def get_balance(guild_id: int, user_id: int) -> int:
    ensure_user(guild_id, user_id)
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT balance FROM users WHERE guild_id = ? AND user_id = ?",
        (guild_id, user_id),
    )
    row = cur.fetchone()
    conn.close()
    return row["balance"] if row else 0


def change_balance(guild_id: int, user_id: int, amount: int) -> int:
    """Bakiyeyi değiştirir (pozitif veya negatif), yeni bakiyeyi döndürür."""
    ensure_user(guild_id, user_id)
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "UPDATE users SET balance = balance + ? WHERE guild_id = ? AND user_id = ?",
        (amount, guild_id, user_id),
    )
    conn.commit()
    cur.execute(
        "SELECT balance FROM users WHERE guild_id = ? AND user_id = ?",
        (guild_id, user_id),
    )
    new_balance = cur.fetchone()["balance"]
    conn.close()
    return new_balance


def get_leaderboard(guild_id: int, limit: int = 10):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT user_id, balance FROM users WHERE guild_id = ? ORDER BY balance DESC LIMIT ?",
        (guild_id, limit),
    )
    rows = cur.fetchall()
    conn.close()
    return rows


# ---------------- Tahmin / Bahis ----------------

def create_prediction(guild_id: int, question: str, option_a: str, option_b: str, created_by: int) -> int:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """INSERT INTO predictions (guild_id, question, option_a, option_b, status, created_by)
           VALUES (?, ?, ?, ?, 'open', ?)""",
        (guild_id, question, option_a, option_b, created_by),
    )
    conn.commit()
    pred_id = cur.lastrowid
    conn.close()
    return pred_id


def set_prediction_message(prediction_id: int, channel_id: int, message_id: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "UPDATE predictions SET channel_id = ?, message_id = ? WHERE id = ?",
        (channel_id, message_id, prediction_id),
    )
    conn.commit()
    conn.close()


def get_prediction(prediction_id: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM predictions WHERE id = ?", (prediction_id,))
    row = cur.fetchone()
    conn.close()
    return row


def get_open_predictions(guild_id: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT * FROM predictions WHERE guild_id = ? AND status = 'open' ORDER BY id DESC",
        (guild_id,),
    )
    rows = cur.fetchall()
    conn.close()
    return rows


def close_prediction(prediction_id: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE predictions SET status = 'closed' WHERE id = ?", (prediction_id,))
    conn.commit()
    conn.close()


def set_prediction_winner(prediction_id: int, winner: str):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "UPDATE predictions SET status = 'resolved', winner = ? WHERE id = ?",
        (winner, prediction_id),
    )
    conn.commit()
    conn.close()


def add_bet(prediction_id: int, user_id: int, option: str, amount: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO bets (prediction_id, user_id, option, amount) VALUES (?, ?, ?, ?)",
        (prediction_id, user_id, option, amount),
    )
    conn.commit()
    conn.close()


def get_user_bet(prediction_id: int, user_id: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT * FROM bets WHERE prediction_id = ? AND user_id = ?",
        (prediction_id, user_id),
    )
    row = cur.fetchone()
    conn.close()
    return row


def get_bets(prediction_id: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM bets WHERE prediction_id = ?", (prediction_id,))
    rows = cur.fetchall()
    conn.close()
    return rows


def get_pool_totals(prediction_id: int):
    bets = get_bets(prediction_id)
    total_a = sum(b["amount"] for b in bets if b["option"] == "A")
    total_b = sum(b["amount"] for b in bets if b["option"] == "B")
    return total_a, total_b
