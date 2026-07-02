import time
import threading
from apscheduler.schedulers.blocking import BlockingScheduler
from config import get_kite_session, get_current_expiry
import database
from execution_engine import execute_trade, force_close_trade, _TRADE_LOCKS
from model_inference import get_lstm_prediction
from strategies.sixty_second_momentum import SixtySecondMomentum
from strategies.tax_optimized_momentum import TaxOptimizedMomentum

from datetime import datetime

def bot_loop():
    print("--- 1 Minute Cron Triggered ---")
    
    # Check if time is past 3:15 PM (15:15)
    now = datetime.now()
    if now.hour > 15 or (now.hour == 15 and now.minute >= 15):
        print("Market is closed or past 3:15 PM cutoff. Halting trading.")
        return
    
    # 1. Auth Check
    try:
        kite = get_kite_session()
        # Ping kite to ensure token is still valid
        quote = kite.quote("NSE:NIFTY 50")
        if "NSE:NIFTY 50" not in quote:
            print("Auth Error: Could not fetch NIFTY 50 quote.")
            return
    except Exception as e:
        print(f"Auth Error: Token may be expired. Please login again. Details: {e}")
        return
        
    # 2. Risk Check
    max_trades = database.get_setting("max_trades_per_day")
    daily_trades = database.get_daily_trade_count()
    if daily_trades >= max_trades:
        print(f"Risk Limit: Max daily trades ({max_trades}) reached. Stopping for the day.")
        return
        
    portfolio = database.get_portfolio()
    starting_cap = portfolio['starting_capital']
    current_cap = portfolio['capital']
    
    if current_cap <= starting_cap * 0.8:
        print(f"Risk Limit: 20% drawdown reached. Capital: {current_cap}. Stopping for the day.")
        return

    # 3. Fetch Model Prediction
    print("Fetching LSTM Prediction...")
    try:
        quote = kite.quote("NSE:NIFTY 50")
        inst_token = quote["NSE:NIFTY 50"]['instrument_token']
        lstm_pred = get_lstm_prediction(kite, inst_token)
    except Exception as e:
        print(f"Error fetching LSTM prediction: {e}")
        lstm_pred = None

    # 4. Strategy Evaluation
    active_strategies_str = database.get_setting("active_strategy")
    strategy_names = [s.strip() for s in active_strategies_str.split(",") if s.strip()]
    
    for strategy_name in strategy_names:
        print(f"\n--- Evaluating Strategy: {strategy_name} ---")
        if strategy_name == "sixty_second_momentum":
            strategy = SixtySecondMomentum(kite)
        elif strategy_name == "tax_optimized_momentum":
            strategy = TaxOptimizedMomentum(kite)
        else:
            print(f"Unknown strategy: {strategy_name}")
            continue
            
        signal_data = strategy.evaluate(lstm_prediction=lstm_pred)
        direction = signal_data.get('signal')
        
        print(f"Signal: {direction}, Confidence: {signal_data.get('confidence')}")

        # 5. Position Check & Execution
        bullish_score = signal_data.get('bullish_score', 0)
        bearish_score = signal_data.get('bearish_score', 0)
        score_gap = abs(bullish_score - bearish_score)

        if direction in ["BULL", "BEAR"]:
            if score_gap >= getattr(strategy, "min_score_gap", 2):
                
                if getattr(strategy, "requires_volatility", False) and signal_data.get('squeeze_active', False):
                    print(f"Signal rejected: Strategy requires volatility, but market is squeezing (BB width low).")
                    continue
                    
                # Check open trades and close any lingering position for THIS strategy (Option B)
                open_trades = database.get_open_trades()
                strategy_open_trades = [t for t in open_trades if t.get('strategy') == strategy_name]
                if strategy_open_trades:
                    print(f"Option B: Closing {len(strategy_open_trades)} open trades immediately to take new signal for {strategy_name}.")
                    for trade in strategy_open_trades:
                        force_close_trade(trade, kite)

                # Guard: if a trade is already mid-flight for this strategy
                strategy_lock = _TRADE_LOCKS.get(strategy_name)
                if strategy_lock is None or not strategy_lock.locked():
                    print(f"Spawning execution thread for {strategy_name} -> {direction} (confidence={signal_data.get('confidence_pct', '?')}%, gap={score_gap})...")
                    t = threading.Thread(target=execute_trade, args=(signal_data, strategy_name), daemon=True)
                    t.start()
                else:
                    print(f"[Bot] Cron tick skipped for {strategy_name} — previous trade still in 60s/25s monitoring window.")
            else:
                print(f"Signal {direction} rejected: Conviction score gap too low ({score_gap} < {getattr(strategy, 'min_score_gap', 2)}).")
        else:
            # This branch only reached if the strategy hit an API exception
            print(f"No executable signal (reason: {signal_data.get('reason', 'unknown')}).")


if __name__ == "__main__":
    print("Starting Trading Bot Scheduler...")
    scheduler = BlockingScheduler()
    # Run every minute
    scheduler.add_job(bot_loop, 'interval', minutes=1)
    
    # Run once immediately on startup
    bot_loop()
    
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        print("Scheduler stopped.")
