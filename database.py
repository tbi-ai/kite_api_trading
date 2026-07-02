import sqlite3
import os
from datetime import datetime, date

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "trading.db")

def get_connection():
    return sqlite3.connect(DB_PATH)

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    
    # Portfolio Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS portfolio (
            id INTEGER PRIMARY KEY,
            capital REAL DEFAULT 100000.0,
            starting_capital REAL DEFAULT 100000.0,
            date TEXT UNIQUE
        )
    ''')
    
    # Settings Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            paper_trading_mode BOOLEAN DEFAULT 1,
            active_strategy TEXT DEFAULT 'sixty_second_momentum',
            max_trades_per_day INTEGER DEFAULT 100,
            target_percentage REAL DEFAULT 5.0,
            risk_percentage REAL DEFAULT 10.0,
            min_premium REAL DEFAULT 50.0,
            max_premium REAL DEFAULT 70.0,
            use_fixed_quantity BOOLEAN DEFAULT 0,
            fixed_quantity INTEGER DEFAULT 250
        )
    ''')
    
    # Trades Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            date TEXT,
            symbol TEXT,
            direction TEXT,
            entry_price REAL,
            exit_price REAL,
            pnl REAL,
            is_paper BOOLEAN,
            strategy TEXT,
            status TEXT,
            qty INTEGER DEFAULT 0,
            exit_timestamp TEXT
        )
    ''')
    
    # Insert default settings if empty
    cursor.execute("SELECT COUNT(*) FROM settings")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO settings (paper_trading_mode, active_strategy, max_trades_per_day, target_percentage, risk_percentage, min_premium, max_premium, use_fixed_quantity, fixed_quantity) VALUES (1, 'sixty_second_momentum', 100, 5.0, 10.0, 50.0, 70.0, 0, 250)")
    else:
        # Migrate existing table if columns don't exist
        try:
            cursor.execute("ALTER TABLE settings ADD COLUMN target_percentage REAL DEFAULT 5.0")
            cursor.execute("ALTER TABLE settings ADD COLUMN risk_percentage REAL DEFAULT 10.0")
        except sqlite3.OperationalError:
            pass # Columns already exist
            
        try:
            cursor.execute("ALTER TABLE settings ADD COLUMN min_premium REAL DEFAULT 50.0")
            cursor.execute("ALTER TABLE settings ADD COLUMN max_premium REAL DEFAULT 70.0")
        except sqlite3.OperationalError:
            pass # Columns already exist
            
        try:
            cursor.execute("ALTER TABLE settings ADD COLUMN use_fixed_quantity BOOLEAN DEFAULT 0")
            cursor.execute("ALTER TABLE settings ADD COLUMN fixed_quantity INTEGER DEFAULT 250")
        except sqlite3.OperationalError:
            pass # Columns already exist
            
        try:
            cursor.execute("ALTER TABLE trades ADD COLUMN qty INTEGER DEFAULT 0")
        except sqlite3.OperationalError:
            pass
            
        try:
            cursor.execute("ALTER TABLE trades ADD COLUMN exit_timestamp TEXT")
        except sqlite3.OperationalError:
            pass
        
    # Insert default portfolio for today if empty
    today = str(date.today())
    cursor.execute("SELECT COUNT(*) FROM portfolio WHERE date = ?", (today,))
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO portfolio (capital, starting_capital, date) VALUES (100000.0, 100000.0, ?)", (today,))
        
    conn.commit()
    conn.close()

def get_setting(key):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(f"SELECT {key} FROM settings LIMIT 1")
    val = cursor.fetchone()[0]
    conn.close()
    return val

def update_setting(key, value):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(f"UPDATE settings SET {key} = ?", (value,))
    conn.commit()
    conn.close()

def get_portfolio():
    today = str(date.today())
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT capital, starting_capital FROM portfolio WHERE date = ?", (today,))
    row = cursor.fetchone()
    
    if not row:
        # Carry forward from last entry
        cursor.execute("SELECT capital FROM portfolio ORDER BY date DESC LIMIT 1")
        last = cursor.fetchone()
        current_cap = last[0] if last else 100000.0
        cursor.execute("INSERT INTO portfolio (capital, starting_capital, date) VALUES (?, ?, ?)", (current_cap, current_cap, today))
        conn.commit()
        row = (current_cap, current_cap)
        
    conn.close()
    return {"capital": row[0], "starting_capital": row[1]}

def update_portfolio(pnl_amount):
    today = str(date.today())
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE portfolio SET capital = capital + ? WHERE date = ?", (pnl_amount, today))
    conn.commit()
    conn.close()

def log_trade(trade_data):
    today = str(date.today())
    timestamp = datetime.now().isoformat()
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO trades (timestamp, date, symbol, direction, entry_price, exit_price, pnl, is_paper, strategy, status, qty)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        timestamp, today,
        trade_data.get('symbol'),
        trade_data.get('direction'),
        trade_data.get('entry_price'),
        trade_data.get('exit_price'),
        trade_data.get('pnl', 0.0),
        trade_data.get('is_paper', True),
        trade_data.get('strategy', 'unknown'),
        trade_data.get('status', 'CLOSED'),
        trade_data.get('qty', 0)
    ))
    
    trade_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return trade_id

def update_trade_status(trade_id, exit_price, pnl, status="CLOSED", **kwargs):
    """
    Updates an open trade with its exit price, PnL, and status.
    Also records the exact exit timestamp.
    Accepts taxes and gross_pnl via kwargs.
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Get optional kwargs
        taxes = kwargs.get("taxes", 0.0)
        gross_pnl = kwargs.get("gross_pnl", 0.0)
        
        cursor.execute('''
            UPDATE trades
            SET exit_price = ?,
                pnl = ?,
                status = ?,
                exit_timestamp = ?,
                taxes = ?,
                gross_pnl = ?
            WHERE id = ?
        ''', (exit_price, pnl, status, datetime.now().isoformat(), taxes, gross_pnl, trade_id))
        
        conn.commit()
    except Exception as e:
        print(f"DB Error updating trade: {e}")
    finally:
        if 'conn' in locals():
            conn.close()

def get_open_trades():
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM trades WHERE status = 'OPEN'")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_daily_trade_count():
    today = str(date.today())
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM trades WHERE date = ?", (today,))
    count = cursor.fetchone()[0]
    conn.close()
    return count

# Initialize on import
init_db()
