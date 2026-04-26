import json
import os
from datetime import datetime

DB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "trade_history.json")

def init_db():
    if not os.path.exists(DB_FILE):
        with open(DB_FILE, "w") as f:
            json.dump([], f)

def record_trade(trade_data):
    init_db()
    with open(DB_FILE, "r") as f:
        data = json.load(f)
    
    trade_data['timestamp'] = datetime.now().isoformat()
    data.append(trade_data)
    
    with open(DB_FILE, "w") as f:
        json.dump(data, f, indent=4)

def get_trade_stats():
    init_db()
    with open(DB_FILE, "r") as f:
        data = json.load(f)
        
    total_trades = len(data)
    if total_trades == 0:
        return {
            "total_trades": 0,
            "net_pnl": 0,
            "win_rate": 0,
            "avg_win": 0,
            "avg_loss": 0,
            "history": []
        }
        
    wins = [t for t in data if t['pnl'] > 0]
    losses = [t for t in data if t['pnl'] <= 0]
    
    net_pnl = sum(t['pnl'] for t in data)
    win_rate = (len(wins) / total_trades) * 100
    
    avg_win = sum(t['pnl'] for t in wins) / len(wins) if wins else 0
    avg_loss = sum(t['pnl'] for t in losses) / len(losses) if losses else 0
    
    # Sort history newest first
    data.sort(key=lambda x: x['timestamp'], reverse=True)
    
    return {
        "total_trades": total_trades,
        "net_pnl": round(net_pnl, 2),
        "win_rate": round(win_rate, 2),
        "avg_win": round(avg_win, 2),
        "avg_loss": round(avg_loss, 2),
        "history": data[:20]  # Last 20 trades
    }
