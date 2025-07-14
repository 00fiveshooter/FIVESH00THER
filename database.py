# database.py

import sqlite3
from datetime import datetime, timedelta

class Database:
    def __init__(self):
        self.conn = sqlite3.connect("bot.db", check_same_thread=False)
        self.create_tables()

    def create_tables(self):
        with self.conn:
            self.conn.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, balance REAL DEFAULT 0)")
            self.conn.execute("""CREATE TABLE IF NOT EXISTS cards (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                bin TEXT,
                balance REAL,
                price REAL,
                locked_until DATETIME
            )""")
            self.conn.execute("CREATE TABLE IF NOT EXISTS purchases (user_id INTEGER, card_id INTEGER, timestamp DATETIME)")

    def add_user(self, user_id):
        with self.conn:
            self.conn.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))

    def update_balance(self, user_id, amount):
        with self.conn:
            self.conn.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, user_id))

    def get_balance(self, user_id):
        cur = self.conn.cursor()
        cur.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
        row = cur.fetchone()
        return row[0] if row else 0

    def add_card(self, name, bin_code, balance, price):
        with self.conn:
            cur = self.conn.execute("INSERT INTO cards (name, bin, balance, price, locked_until) VALUES (?, ?, ?, ?, NULL)", 
                                    (name, bin_code, balance, price))
            return cur.lastrowid

    def get_available_cards(self):
        now = datetime.utcnow()
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM cards WHERE locked_until IS NULL OR locked_until < ?", (now,))
        rows = cur.fetchall()
        return [dict(id=row[0], name=row[1], bin=row[2], balance=row[3], price=row[4]) for row in rows]

    def get_random_card(self):
        cards = self.get_available_cards()
        import random
        return random.choice(cards) if cards else None

    def lock_card(self, card_id, minutes=15):
        lock_time = datetime.utcnow() + timedelta(minutes=minutes)
        with self.conn:
            self.conn.execute("UPDATE cards SET locked_until = ? WHERE id = ?", (lock_time, card_id))

    def get_card_lock_time(self, card_id):
        cur = self.conn.cursor()
        cur.execute("SELECT locked_until FROM cards WHERE id = ?", (card_id,))
        row = cur.fetchone()
        if row and row[0]:
            remaining = datetime.fromisoformat(row[0]) - datetime.utcnow()
            if remaining.total_seconds() > 0:
                mins, secs = divmod(int(remaining.total_seconds()), 60)
                return f"{mins}m {secs}s"
        return None

    def record_purchase(self, user_id, card_id, amount):
        with self.conn:
            self.conn.execute("INSERT INTO purchases (user_id, card_id, timestamp) VALUES (?, ?, ?)",
                              (user_id, card_id, datetime.utcnow()))
