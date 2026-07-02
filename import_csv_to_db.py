import csv
import sqlite3
import os

DB_PATH = "trading.db"

def import_csv(file_path):
    if not os.path.exists(file_path):
        print(f"File {file_path} not found.")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    with open(file_path, "r") as f:
        reader = csv.DictReader(f)
        count = 0
        for row in reader:
            cursor.execute('''
                INSERT INTO trades (timestamp, date, symbol, direction, entry_price, exit_price, pnl, is_paper, strategy, status, qty, exit_timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                row['timestamp'], 
                row['date'],
                row['symbol'],
                row['direction'],
                float(row['entry_price']),
                float(row['exit_price']),
                float(row['net_pnl']), # Using net PnL after taxes
                True,
                row['strategy'],
                row['status'],
                int(row['qty']),
                row['exit_timestamp']
            ))
            count += 1
            
        # Update portfolio with cumulative PnL for the specific date
        cursor.execute("SELECT SUM(pnl) FROM trades WHERE date = ?", (row['date'],))
        total_pnl = cursor.fetchone()[0] or 0.0
        
        # Upsert portfolio
        cursor.execute("SELECT id FROM portfolio WHERE date = ?", (row['date'],))
        if cursor.fetchone():
             cursor.execute("UPDATE portfolio SET capital = starting_capital + ? WHERE date = ?", (total_pnl, row['date']))
        else:
             cursor.execute("INSERT INTO portfolio (capital, starting_capital, date) VALUES (?, ?, ?)", (100000.0 + total_pnl, 100000.0, row['date']))
             
    conn.commit()
    conn.close()
    print(f"Imported {count} trades from {file_path} into SQLite database.")

# Note: The 07_01 data is in the current dir CSV. The 06_30 data is in the CSV we copied.
import_csv("backtest_results_tax_optimized_2026_07_01.csv")
import_csv("backtest_results_tax_optimized_2026_06_30.csv")

