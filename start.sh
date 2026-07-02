#!/bin/bash
echo "Starting NiftyVerse Trading Bot System..."

# Start FastAPI Backend
echo "Starting FastAPI Backend..."
"/Users/aple/Documents/Trading Project/V2/kite_api_trading/venv/bin/python" main.py &
PID_FASTAPI=$!

# Start the trading bot scheduler (Cron)
echo "Starting Trading Bot Scheduler..."
"/Users/aple/Documents/Trading Project/V2/kite_api_trading/venv/bin/python" bot.py &
PID_BOT=$!

# Start Vite Frontend
echo "Starting Vite Frontend..."
cd frontend && npm run dev &
PID_FRONTEND=$!

echo "All systems running!"
echo "Frontend: http://localhost:5173"
echo "API Server: http://127.0.0.1:8000"
echo "Press Ctrl+C to stop all services."

wait $PID_FASTAPI $PID_BOT $PID_FRONTEND
