import os
import subprocess
import asyncio
from fastapi import FastAPI, Request, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from kiteconnect import KiteConnect
import uvicorn
from fastapi.responses import StreamingResponse, JSONResponse
from config import API_KEY, API_SECRET
from dashboard_prices import get_market_overview, fetch_upcoming_expiries
from model_inference import get_ml_signals
from trade_db import get_trade_stats
from trading_execution import execute_trade_stream
import json
from datetime import datetime

app = FastAPI(title="NiftyVerse Modular API")

@app.get("/api/expiries")
async def get_expiries():
    """Return the next 3 NIFTY expiries."""
    expiries = fetch_upcoming_expiries()
    return {"success": True, "data": expiries}

@app.get("/api/session_status")
async def session_status():
    """Check if a valid session exists in credentials.json."""
    credentials_path = os.path.join(current_dir, "credentials.json")
    if os.path.exists(credentials_path):
        try:
            with open(credentials_path, "r") as f:
                creds = json.load(f)
                if creds.get("access_token"):
                    return {"success": True, "authenticated": True}
        except:
            pass
    return {"success": True, "authenticated": False}

# Add CORS middleware to allow React frontend to communicate with this backend
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
    """Return the Kite Login URL."""
    login_url = f"https://kite.zerodha.com/connect/login?v=3&api_key={API_KEY}"
    return {"login_url": login_url}

@app.post("/api/generate_token")
async def generate_token(payload: TokenRequest):
    """Handle the request token submission and generate access token."""
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

@app.get("/api/dashboard")
async def dashboard(expiry: str = Query("26MAY", description="Expiry date for options/futures")):
    """Return live spot prices, future prices, and calculated strikes."""
    try:
        data = get_market_overview(expiry)
        return {"success": True, "data": data}
    except FileNotFoundError:
        return JSONResponse(status_code=401, content={"error": "Session not found. Please login first."})
    except Exception as e:
        return JSONResponse(status_code=400, content={"error": str(e)})

@app.get("/api/ml_prediction")
async def ml_prediction(force_refresh: bool = Query(False)):
    """Return the ML indicators and trading signal from model_inference module."""
    try:
        data = get_ml_signals(force_refresh)
        return {"success": True, "data": data}
    except FileNotFoundError:
        return JSONResponse(status_code=401, content={"error": "Session not found. Please login first."})
    except Exception as e:
        return JSONResponse(status_code=400, content={"error": str(e)})

@app.get("/api/execute_trade")
async def execute_trade(expiry: str = Query("26MAY", description="Expiry date for options")):
    """SSE endpoint to stream live execution logs from trading_execution."""
    return StreamingResponse(execute_trade_stream(expiry), media_type="text/event-stream")

async def train_model_stream():
    """Run model_training.py as a subprocess and stream its output."""
    script_path = os.path.join(os.path.dirname(__file__), "model_training.py")
    process = await asyncio.create_subprocess_exec(
        "python3", script_path,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT
    )
    
    while True:
        line = await process.stdout.readline()
        if not line:
            break
        decoded_line = line.decode('utf-8').strip()
        if decoded_line:
            yield f"data: {{\"log\": \"{decoded_line}\"}}\n\n"
    
    await process.wait()
    yield f"data: {{\"log\": \"Training process completed.\", \"status\": \"done\"}}\n\n"

@app.get("/api/train_model")
async def train_model():
    """SSE endpoint to trigger and stream model training."""
    return StreamingResponse(train_model_stream(), media_type="text/event-stream")

@app.get("/api/stats")
async def trade_stats():
    """Returns the historical trade statistics from trade_db."""
    stats = get_trade_stats()
    return {"success": True, "data": stats}

if __name__ == "__main__":
    print(f"Starting API server on http://127.0.0.1:8000")
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
