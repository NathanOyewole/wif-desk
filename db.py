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
    CREATE TABLE IF NOT EXISTS wallets (chat_id INTEGER PRIMARY KEY, cash REAL);
    CREATE TABLE IF NOT EXISTS trades (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      chat_id INTEGER,
      mint TEXT,
      name TEXT,
      entry_price REAL,
      qty REAL,
      size_usd REAL,
      mode TEXT,
      status TEXT,
      ts INTEGER,
      exit_price REAL,
      pnl REAL,
      closed_ts INTEGER
    );
    """)
    for stmt in ["ALTER TABLE trades ADD COLUMN exit_price REAL;",
                 "ALTER TABLE trades ADD COLUMN pnl REAL;",
                 "ALTER TABLE trades ADD COLUMN closed_ts INTEGER;"]:
        try:
            conn.execute(stmt)
        except Exception:
            pass
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

# ---- wallets ----
def get_wallet(chat_id, default=1000.0):
    conn = get_db()
    row = conn.execute("SELECT cash FROM wallets WHERE chat_id=?", (chat_id,)).fetchone()
    conn.close()
    if row is None:
        conn = get_db()
        conn.execute("INSERT INTO wallets (chat_id, cash) VALUES (?,?)", (chat_id, default))
        conn.commit(); conn.close()
        return default
    return row["cash"]

def set_wallet(chat_id, cash):
    conn = get_db()
    conn.execute("INSERT INTO wallets (chat_id, cash) VALUES (?,?) ON CONFLICT(chat_id) DO UPDATE SET cash=?", (chat_id, cash, cash))
    conn.commit(); conn.close()

def adjust_wallet(chat_id, delta):
    cash = get_wallet(chat_id)
    set_wallet(chat_id, cash + delta)

# ---- trades ----
def open_trade(chat_id, mint, name, entry_price, qty, size_usd, mode="PAPER"):
    conn = get_db()
    cur = conn.execute("INSERT INTO trades (chat_id, mint, name, entry_price, qty, size_usd, mode, status, ts) VALUES (?,?,?,?,?,?,?,?,?)",
                       (chat_id, mint, name, entry_price, qty, size_usd, mode, "open", int(time.time())))
    tid = cur.lastrowid
    conn.commit(); conn.close()
    return tid

def close_trade(trade_id, exit_price):
    conn = get_db()
    row = conn.execute("SELECT * FROM trades WHERE id=? AND status='open'", (trade_id,)).fetchone()
    if not row:
        conn.close(); return None
    pnl = (exit_price - row["entry_price"]) * row["qty"]
    conn.execute("UPDATE trades SET status='closed', exit_price=?, pnl=?, closed_ts=? WHERE id=?",
                 (exit_price, pnl, int(time.time()), trade_id))
    conn.commit(); conn.close()
    adjust_wallet(row["chat_id"], row["size_usd"] + pnl)
    return {"trade": dict(row), "exit_price": exit_price, "pnl": pnl}

def partial_close_trade(trade_id, fraction, exit_price):
    """Close a fraction (0-1) of an open trade at exit_price. Returns result dict."""
    fraction = min(max(fraction, 0.0), 1.0)
    conn = get_db()
    row = conn.execute("SELECT * FROM trades WHERE id=? AND status='open'", (trade_id,)).fetchone()
    if not row:
        conn.close(); return None
    qty_closed = row["qty"] * fraction
    size_closed = row["size_usd"] * fraction
    pnl = (exit_price - row["entry_price"]) * qty_closed
    remaining_qty = row["qty"] - qty_closed
    remaining_size = row["size_usd"] - size_closed
    prev_pnl = row["pnl"] or 0
    if fraction >= 0.999:
        conn.execute("UPDATE trades SET status='closed', exit_price=?, pnl=?, closed_ts=? WHERE id=?",
                     (exit_price, prev_pnl + pnl, int(time.time()), trade_id))
    else:
        conn.execute("UPDATE trades SET qty=?, size_usd=?, pnl=? WHERE id=?",
                     (remaining_qty, remaining_size, prev_pnl + pnl, trade_id))
    conn.commit(); conn.close()
    adjust_wallet(row["chat_id"], size_closed + pnl)
    return {"trade": dict(row), "fraction": fraction, "qty_closed": qty_closed,
            "size_closed": size_closed, "exit_price": exit_price, "pnl": pnl}

def get_trades(chat_id=None, status="open"):
    conn = get_db()
    if chat_id is None:
        rows = conn.execute("SELECT * FROM trades WHERE status=? ORDER BY ts DESC", (status,)).fetchall()
    else:
        rows = conn.execute("SELECT * FROM trades WHERE chat_id=? AND status=? ORDER BY ts DESC", (chat_id, status)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_open_trade(chat_id, mint):
    conn = get_db()
    row = conn.execute("SELECT * FROM trades WHERE chat_id=? AND mint=? AND status='open'", (chat_id, mint)).fetchone()
    conn.close()
    return dict(row) if row else None
