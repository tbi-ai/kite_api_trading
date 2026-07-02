import os
import subprocess
import asyncio
from fastapi import FastAPI, Request, Query, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from kiteconnect import KiteConnect
import uvicorn
from fastapi.responses import StreamingResponse, JSONResponse, FileResponse
from config import API_KEY, API_SECRET, set_current_expiry, get_current_expiry
from dashboard_prices import get_market_overview, fetch_upcoming_expiries
import database
from strategies.sixty_second_momentum import SixtySecondMomentum
from model_inference import get_lstm_prediction
import json
from datetime import datetime

app = FastAPI(title="NiftyVerse Modular API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

current_dir = os.path.dirname(os.path.abspath(__file__))

class TokenRequest(BaseModel):
    request_token: str

@app.get("/api/login_url")
async def get_login_url():
    login_url = f"https://kite.zerodha.com/connect/login?v=3&api_key={API_KEY}"
    return {"login_url": login_url}

@app.post("/api/generate_token")
async def generate_token(payload: TokenRequest):
    request_token = payload.request_token
    if not request_token or not request_token.strip():
        return JSONResponse(status_code=400, content={"error": "Request token cannot be empty."})
        
    kite = KiteConnect(api_key=API_KEY)
    try:
        data = kite.generate_session(request_token.strip(), api_secret=API_SECRET)
        access_token = data["access_token"]
        
        credentials_path = os.path.join(current_dir, "credentials.json")
        with open(credentials_path, "w") as f:
            json.dump({
                "access_token": access_token,
                "user_id": data.get("user_id"),
                "login_time": str(datetime.now())
            }, f)
            
        return {"success": True, "message": "Access token securely saved to JSON."}
    except Exception as e:
        return JSONResponse(status_code=400, content={"error": f"Failed to generate session: {e}"})

@app.get("/api/session_status")
async def session_status():
    credentials_path = os.path.join(current_dir, "credentials.json")
    if os.path.exists(credentials_path):
        try:
            with open(credentials_path, "r") as f:
                creds = json.load(f)
                if creds.get("access_token"):
                    # Optionally ping kite to see if it's 24h expired
                    return {"success": True, "authenticated": True}
        except:
            pass
    return {"success": True, "authenticated": False}

@app.get("/api/dashboard")
async def dashboard(expiry: str = Query(None)):
    try:
        active_expiry = expiry or get_current_expiry()
        data = get_market_overview(active_expiry)
        return {"success": True, "data": data}
    except Exception as e:
        return JSONResponse(status_code=400, content={"error": str(e)})

@app.get("/api/expiries")
async def get_expiries():
    try:
        expiries = fetch_upcoming_expiries()
        return {"success": True, "data": expiries}
    except Exception as e:
        return JSONResponse(status_code=400, content={"error": str(e)})

@app.get("/api/set_expiry")
async def set_expiry(expiry: str = Query(None)):
    try:
        if expiry:
            set_current_expiry(expiry)
        return {"success": True}
    except Exception as e:
        return JSONResponse(status_code=400, content={"error": str(e)})

@app.get("/api/ml_prediction")
async def ml_prediction(force_refresh: bool = Query(False)):
    try:
        from config import get_kite_session
        kite = get_kite_session()
        strategy = SixtySecondMomentum(kite)
        
        quote = kite.quote("NSE:NIFTY 50")
        inst_token = quote["NSE:NIFTY 50"]['instrument_token']
        lstm_pred = get_lstm_prediction(kite, inst_token, force_refresh)
        
        data = strategy.evaluate(lstm_prediction=lstm_pred)
        data['lstm_prediction'] = lstm_pred
        return {"success": True, "data": data}
    except Exception as e:
        return JSONResponse(status_code=400, content={"error": str(e)})

async def manual_trade_stream():
    import asyncio
    def sse_message(log_text, status="running", pnl=0):
        return f"data: {json.dumps({'log': log_text, 'status': status, 'pnl': pnl})}\n\n"

    yield sse_message("Initializing manual trade stream...")
    await asyncio.sleep(1)

    try:
        from config import get_kite_session
        from execution_engine import execute_trade, _TRADE_LOCKS
        kite = get_kite_session()
        strategy = SixtySecondMomentum(kite)
        signal_data = strategy.evaluate()

        signal = signal_data.get("signal")
        confidence_pct = signal_data.get("confidence_pct", "?")
        yield sse_message(
            f"Signal: {signal} | Confidence: {confidence_pct}% | "
            f"Bull score: {signal_data.get('bullish_score','?')} | "
            f"Bear score: {signal_data.get('bearish_score','?')}"
        )
        await asyncio.sleep(1)

        if signal in ["BULL", "BEAR"]:
            # Guard: prevent firing a second trade while the bot already has one running for this strategy
            active_strat = database.get_setting("active_strategy").split(",")[0] # Use the primary strategy for manual trades
            strategy_lock = _TRADE_LOCKS.get(active_strat)
            if strategy_lock and strategy_lock.locked():
                yield sse_message(
                    f"Trade already in progress for {active_strat}. "
                    "Skipping to prevent duplicate ghost trade.",
                    status="done", pnl=0
                )
                return

            yield sse_message(f"Valid {signal} signal found. Dispatching to execution engine...")

            import threading
            t = threading.Thread(target=execute_trade, args=(signal_data, active_strat), daemon=True)
            t.start()

            yield sse_message(
                "Trade dispatched successfully! Running in the background. "
                "Check Stats to see PnL after 60s.",
                status="done", pnl=0
            )
        else:
            # Only here if strategy hit an API/data exception
            reason = signal_data.get("reason", "unknown error")
            yield sse_message(f"Strategy could not generate a signal ({reason}). Aborting.", status="done", pnl=0)
    except Exception as e:
        yield sse_message(f"Failed to execute manual trade: {str(e)}", status="error")

@app.get("/api/execute_trade")
async def execute_trade_endpoint(expiry: str = Query(None)):
    return StreamingResponse(manual_trade_stream(), media_type="text/event-stream")

# --- NEW PORTFOLIO & SETTINGS ENDPOINTS ---

@app.get("/api/portfolio")
async def get_portfolio_status():
    return {"success": True, "data": database.get_portfolio()}

class CapitalRequest(BaseModel):
    capital: float

@app.post("/api/portfolio/reset")
async def reset_portfolio(payload: CapitalRequest):
    # This just adds a new entry or updates today's starting capital
    today = str(datetime.now().date())
    conn = database.get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE portfolio SET capital = ?, starting_capital = ? WHERE date = ?", 
                   (payload.capital, payload.capital, today))
    conn.commit()
    conn.close()
    return {"success": True, "message": "Capital reset."}

@app.get("/api/settings")
async def get_settings():
    return {
        "success": True, 
        "data": {
            "paper_trading_mode": bool(database.get_setting("paper_trading_mode")),
            "active_strategy": database.get_setting("active_strategy"),
            "max_trades_per_day": database.get_setting("max_trades_per_day"),
            "target_percentage": float(database.get_setting("target_percentage")),
            "risk_percentage": float(database.get_setting("risk_percentage")),
            "min_premium": float(database.get_setting("min_premium")),
            "max_premium": float(database.get_setting("max_premium")),
            "use_fixed_quantity": bool(database.get_setting("use_fixed_quantity")),
            "fixed_quantity": database.get_setting("fixed_quantity")
        }
    }

class ToggleRequest(BaseModel):
    value: bool

@app.post("/api/settings/paper_trading")
async def set_paper_trading(payload: ToggleRequest):
    database.update_setting("paper_trading_mode", int(payload.value))
    return {"success": True}

class StrategyRequest(BaseModel):
    strategy_name: str

@app.post("/api/settings/strategy")
async def set_strategy(payload: StrategyRequest):
    database.update_setting("active_strategy", payload.strategy_name)
    return {"success": True}

class FloatValueRequest(BaseModel):
    value: float

@app.post("/api/settings/target_percentage")
async def set_target_percentage(payload: FloatValueRequest):
    database.update_setting("target_percentage", payload.value)
    return {"success": True}

@app.post("/api/settings/risk_percentage")
async def set_risk_percentage(payload: FloatValueRequest):
    database.update_setting("risk_percentage", payload.value)
    return {"success": True}

@app.post("/api/settings/min_premium")
async def set_min_premium(payload: FloatValueRequest):
    database.update_setting("min_premium", payload.value)
    return {"success": True}

@app.post("/api/settings/max_premium")
async def set_max_premium(payload: FloatValueRequest):
    database.update_setting("max_premium", payload.value)
    return {"success": True}

class IntValueRequest(BaseModel):
    value: int

@app.post("/api/settings/max_trades_per_day")
async def set_max_trades_per_day(payload: IntValueRequest):
    database.update_setting("max_trades_per_day", payload.value)
    return {"success": True}

@app.post("/api/settings/use_fixed_quantity")
async def set_use_fixed_quantity(payload: ToggleRequest):
    database.update_setting("use_fixed_quantity", int(payload.value))
    return {"success": True}

class IntValueRequest(BaseModel):
    value: int

@app.post("/api/settings/fixed_quantity")
async def set_fixed_quantity(payload: IntValueRequest):
    database.update_setting("fixed_quantity", payload.value)
    return {"success": True}

# --- STATS ---

@app.get("/api/stats")
async def trade_stats(start_date: str = Query(None), end_date: str = Query(None), strategy: str = Query(None)):
    conn = database.get_connection()
    conn.row_factory = database.sqlite3.Row
    cursor = conn.cursor()
    
    query = "SELECT * FROM trades WHERE 1=1"
    params = []
    
    if start_date and end_date:
        query += " AND date(timestamp) BETWEEN ? AND ?"
        params.extend([start_date, end_date])
        
    if strategy and strategy != "All":
        query += " AND strategy = ?"
        params.append(strategy)
        
    query += " ORDER BY id DESC LIMIT 500"
    
    cursor.execute(query, tuple(params))
    rows = cursor.fetchall()
    conn.close()
    
    trades = [dict(row) for row in rows]
    
    # Calculate stats only for closed trades
    closed_trades = [t for t in trades if t['status'] != 'OPEN']
    
    total = len(closed_trades)
    wins = len([t for t in closed_trades if t['pnl'] > 0])
    losses = len([t for t in closed_trades if t['pnl'] <= 0])
    win_rate = (wins/total)*100 if total > 0 else 0
    net_pnl = sum([t['pnl'] for t in closed_trades])
    
    avg_win = sum([t['pnl'] for t in closed_trades if t['pnl'] > 0]) / wins if wins else 0
    avg_loss = sum([t['pnl'] for t in closed_trades if t['pnl'] <= 0]) / losses if losses else 0
    
    portfolio = database.get_portfolio()
    
    return {
        "success": True, 
        "data": {
            "total_trades": total,
            "net_pnl": net_pnl,
            "win_rate": round(win_rate, 2),
            "avg_win": avg_win,
            "avg_loss": avg_loss,
            "portfolio": portfolio,
            "history": trades[:50] # Display up to 50 in UI (including OPEN ones)
        }
    }

if __name__ == "__main__":
    print(f"Starting API server on http://127.0.0.1:8000")
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.getenv("PORT", 8000)), reload=True)
    
# --- FRONTEND STATIC SERVING (For Railway Deployment) ---
frontend_dist = os.path.join(current_dir, "frontend", "dist")
if os.path.exists(frontend_dist):
    app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="static")
