import sqlite3

def calculate_tax(entry, exit, qty):
    if entry <= 0 or exit <= 0 or qty <= 0:
        return 0.0
    sell_value = exit * qty
    buy_value = entry * qty
    turnover = sell_value + buy_value
    
    brokerage = 40.0
    stt = sell_value * 0.00125
    exc = turnover * 0.0003503
    gst = (brokerage + exc) * 0.18
    stamp = buy_value * 0.00003
    sebi = turnover * 0.000001
    
    return round(brokerage + stt + exc + gst + stamp + sebi, 2)

conn = sqlite3.connect("trading.db")
cursor = conn.cursor()

# Add columns if they don't exist
try:
    cursor.execute("ALTER TABLE trades ADD COLUMN taxes REAL DEFAULT 0.0")
    cursor.execute("ALTER TABLE trades ADD COLUMN gross_pnl REAL DEFAULT 0.0")
except:
    pass # Already exists

cursor.execute("SELECT id, entry_price, exit_price, qty, strategy, pnl FROM trades")
rows = cursor.fetchall()

for row in rows:
    trade_id, entry, exit_p, qty, strategy, current_pnl = row
    taxes = calculate_tax(entry, exit_p, qty)
    gross_pnl = round((exit_p - entry) * qty, 2)
    
    # If it's a backtest strategy, current_pnl is already net_pnl
    if strategy == "tax_optimized" or strategy == "sixty_second_momentum":
        net_pnl = current_pnl
    else:
        # For live/paper manual trades, current_pnl was gross. Convert to net.
        net_pnl = round(gross_pnl - taxes, 2)
        
    cursor.execute("UPDATE trades SET taxes = ?, gross_pnl = ?, pnl = ? WHERE id = ?", (taxes, gross_pnl, net_pnl, trade_id))

conn.commit()
conn.close()
print("Database migrated successfully with taxes and gross_pnl.")
