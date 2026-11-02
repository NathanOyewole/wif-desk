import sqlite3, json, time, os

DB_PATH = os.path.join(os.path.dirname(__file__), "wif_desk.db")

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS coins (address TEXT PRIMARY KEY, name TEXT, symbol TEXT, liquidity_usd REAL, price_usd TEXT, ts INTEGER);
    CREATE TABLE IF NOT EXISTS activity (id INTEGER PRIMARY KEY AUTOINCREMENT, agent TEXT, mint TEXT, action TEXT, detail TEXT, ts INTEGER);
    CREATE TABLE IF NOT EXISTS positions (id INTEGER PRIMARY KEY AUTOINCREMENT, mint TEXT, name TEXT, entry_price REAL, size_usd REAL, mode TEXT, status TEXT, ts INTEGER);
    CREATE TABLE IF NOT EXISTS signals (id INTEGER PRIMARY KEY AUTOINCREMENT, mint TEXT, name TEXT, price_usd REAL, size_usd REAL, link TEXT, ts INTEGER);
    """)
    conn.commit()
    conn.close()

def save_coin(address, name, symbol, liq, price):
    conn = get_db()
    conn.execute("INSERT OR IGNORE INTO coins (address, name, symbol, liquidity_usd, price_usd, ts) VALUES (?,?,?,?,?,?)",
                 (address, name, symbol, liq, price, int(time.time())))
    conn.commit()
    conn.close()

def log_activity(agent, mint, action, detail=None):
    conn = get_db()
    conn.execute("INSERT INTO activity (agent, mint, action, detail, ts) VALUES (?,?,?,?,?)",
                 (agent, mint, action, detail, int(time.time())))
    conn.commit()
    conn.close()
