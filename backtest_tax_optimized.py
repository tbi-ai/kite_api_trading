import pandas as pd
import pandas_ta as ta
import numpy as np
import tensorflow as tf
from datetime import datetime, timedelta
import csv
import sys
import os
import time

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from config import get_kite_session, get_current_expiry
from execution_engine import get_atm_option, calculate_qty
from model_inference import generate_features_from_recent

def calculate_lstm_series(kite, spot_token, end_date):
    start_date = end_date - timedelta(days=5)
    data = kite.historical_data(
        spot_token, 
        start_date.strftime("%Y-%m-%d"), 
        end_date.strftime("%Y-%m-%d"), 
        '15minute'
    )
    df = pd.DataFrame(data)
    df['date'] = pd.to_datetime(df['date'])
    df.set_index('date', inplace=True)
    
    df['EMA9'] = ta.ema(df['close'], length=9)
    df['EMA21'] = ta.ema(df['close'], length=21)
    df['RSI14'] = ta.rsi(df['close'], length=14)
    df['RSI6'] = ta.rsi(df['close'], length=6)

    macd = ta.macd(df['close'])
    if macd is not None and not macd.empty:
        df['MACD'] = macd['MACD_12_26_9']
        df['MACD_signal'] = macd['MACDs_12_26_9']
    else:
        df['MACD'] = 0
        df['MACD_signal'] = 0

    bb = ta.bbands(df['close'], length=20, std=2)
    if bb is not None and not bb.empty:
        df['BB_upper'] = bb[bb.columns[0]] # BBU
        df['BB_middle'] = bb[bb.columns[1]] # BBM
        df['BB_lower'] = bb[bb.columns[2]] # BBL
        df['BB_width'] = (df['BB_upper'] - df['BB_lower']) / df['BB_middle']
        df['BB_pct'] = (df['close'] - df['BB_lower']) / (df['BB_upper'] - df['BB_lower'])
    else:
        for c in ['BB_upper', 'BB_middle', 'BB_lower', 'BB_width', 'BB_pct']:
            df[c] = 0

    st = ta.supertrend(df['high'], df['low'], df['close'], length=10, multiplier=3)
    if st is not None and not st.empty:
        df['SuperTrend'] = st[st.columns[0]]
    else:
        df['SuperTrend'] = df['close']

    df.dropna(inplace=True)
    
    features = ['close', 'EMA9', 'EMA21', 'RSI14', 'RSI6',
                'MACD', 'MACD_signal', 'SuperTrend',
                'BB_upper', 'BB_lower', 'BB_width', 'BB_pct']
                
    X = df[features].values
    from sklearn.preprocessing import MinMaxScaler
    scaler = MinMaxScaler()
    X_scaled = scaler.fit_transform(X)
    
    timesteps = 60
    predictions = {}
    
    model_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "nifty_lstm.keras")
    if not os.path.exists(model_path):
        return predictions
    model = tf.keras.models.load_model(model_path)
    
    for i in range(timesteps, len(X_scaled)):
        x_input = np.array([X_scaled[i-timesteps:i]])
        pred = float(model.predict(x_input, verbose=0)[0][0])
        predictions[df.index[i]] = pred
        
    pred_series = pd.Series(predictions)
    return pred_series

def run_backtest():
    target_date = datetime.now()
    if len(sys.argv) > 1:
        try:
            target_date = datetime.strptime(sys.argv[1], "%Y-%m-%d")
        except ValueError:
            print("Invalid date format. Use YYYY-MM-DD")
            return
            
    target_date_str = target_date.strftime("%Y-%m-%d")

    kite = get_kite_session()
    quote = kite.quote("NSE:NIFTY 50")
    spot_token = quote["NSE:NIFTY 50"]['instrument_token']
    
    print("Fetching LSTM predictions...")
    lstm_preds = calculate_lstm_series(kite, spot_token, target_date + timedelta(days=1))
    
    print(f"Fetching NIFTY 1-min data for {target_date_str}...")
    start_date = target_date - timedelta(days=2) 
    data = kite.historical_data(
        spot_token, 
        start_date.strftime("%Y-%m-%d 09:15:00"), 
        target_date.strftime("%Y-%m-%d 15:30:00"), 
        'minute'
    )
    df = pd.DataFrame(data)
    df['date'] = pd.to_datetime(df['date']).dt.tz_localize(None)
    df.set_index('date', inplace=True)
    
    df["EMA9"] = ta.ema(df["close"], length=9)
    df["EMA21"] = ta.ema(df["close"], length=21)
    df["RSI14"] = ta.rsi(df["close"], length=14)
    df["RSI6"] = ta.rsi(df["close"], length=6)
    macd = ta.macd(df["close"])
    df["MACD"] = macd["MACD_12_26_9"] if (macd is not None and not macd.empty) else 0

    st = ta.supertrend(df["high"], df["low"], df["close"], length=10, multiplier=3)
    df["SuperTrend"] = st[st.columns[0]] if (st is not None and not st.empty) else df["close"]

    df['lstm_pred'] = np.nan
    for ts, pred in lstm_preds.items():
        if ts.tz_localize(None) in df.index:
            df.loc[ts.tz_localize(None), 'lstm_pred'] = pred
    df['lstm_pred'] = df['lstm_pred'].ffill()

    today_df = df[df.index.date == target_date.date()].copy()
    
    results = []
    trade_id_counter = 1
    
    print(f"Starting minute-by-minute simulation for {len(today_df)} minutes...")
    
    busy_until = target_date.replace(hour=0, minute=0, second=0)
    
    for i in range(len(today_df)):
        current_time = today_df.index[i]
        
        if current_time < busy_until:
            continue
            
        row = today_df.iloc[i]
        
        bullish_score = 0
        bearish_score = 0
        current_price = row['close']
        
        if current_price > row['EMA9']: bullish_score += 1
        else: bearish_score += 1
            
        if row['EMA9'] > row['EMA21']: bullish_score += 1
        else: bearish_score += 1
            
        if row['RSI14'] > 50: bullish_score += 1
        else: bearish_score += 1
            
        if row['MACD'] > 0: bullish_score += 1
        else: bearish_score += 1
            
        lstm_pred = row['lstm_pred']
        if pd.notna(lstm_pred):
            if lstm_pred > current_price: bullish_score += 2
            elif lstm_pred < current_price: bearish_score += 2
                
        signal = "NO_SIGNAL"
        winning_score = 0
        if bullish_score > bearish_score:
            signal = "BULL"
            winning_score = bullish_score
        elif bearish_score > bullish_score:
            signal = "BEAR"
            winning_score = bearish_score
        else:
            signal = "BULL" if current_price > row['EMA9'] else "BEAR"
            winning_score = bullish_score
            
        score_gap = abs(bullish_score - bearish_score)
        
        # Tax-Optimized Filter: Require a much stronger conviction gap and some volatility
        # Also, check BB width (skip trades if market is entirely flat to avoid fee drain)
        bb_width_ok = row['BB_width'] > 0.001 if 'BB_width' in row else True
        
        if signal in ["BULL", "BEAR"] and score_gap >= 4 and bb_width_ok:
            expiry = get_current_expiry()
            # MOCK get_atm_option: just pick the strict ATM strike to avoid 3000 API calls for live option chains
            strike_diff = 100
            atm_strike = int(round(current_price / strike_diff) * strike_diff)
            opt_type = "CE" if signal == "BULL" else "PE"
            tsymbol = f"NIFTY{expiry}{atm_strike}{opt_type}"
            
            if not tsymbol:
                continue
                
            try:
                # Need to use 'NFO:SYMBOL' to fetch token, but `get_atm_option` returns 'SYMBOL' or 'NFO:SYMBOL'
                sym = tsymbol if "NFO:" in tsymbol else "NFO:" + tsymbol
                opt_quote = kite.quote(sym)
                opt_token = opt_quote[sym]['instrument_token']
            except Exception as e:
                continue
                
            start_sec = current_time
            end_sec = current_time + timedelta(minutes=5)
            try:
                opt_data = kite.historical_data(
                    opt_token,
                    start_sec.strftime("%Y-%m-%d %H:%M:%S"),
                    end_sec.strftime("%Y-%m-%d %H:%M:%S"),
                    'minute'
                )
            except Exception as e:
                continue
                
            if not opt_data:
                continue
                
            opt_df = pd.DataFrame(opt_data)
            opt_df['date'] = pd.to_datetime(opt_df['date']).dt.tz_localize(None)
            
            consecutive_entries = 0
            current_sec_idx = 0
            
            while consecutive_entries < 1 and current_sec_idx < len(opt_df):
                consecutive_entries += 1
                
                # We only have minute data, so we can't do exact second-by-second ignition checks.
                # Just use the 'open' of the minute as the proxy for the entry ask price.
                ask = opt_df.iloc[current_sec_idx]['open']
                    
                entry_price = ask
                entry_time = opt_df.iloc[current_sec_idx]['date']
                
                hour_float = entry_time.hour + entry_time.minute / 60.0
                if 9.33 <= hour_float <= 10.0: target_pct = 3.0
                elif 10.0 < hour_float <= 14.5: target_pct = 2.0
                elif 14.5 < hour_float <= 15.0: target_pct = 2.5
                else: target_pct = 1.5
                    
                target_price = round(entry_price * (1 + (target_pct / 100.0)), 1)
                
                target_hit = False
                exit_price = entry_price
                exit_time = entry_time
                t = 0
                
                # Simulate monitoring for that 1 minute candle
                row_sec = opt_df.iloc[current_sec_idx]
                if row_sec['high'] >= target_price:
                    target_hit = True
                    exit_price = target_price 
                    duration = 15 # estimate 15 seconds to hit
                else:
                    target_hit = False
                    exit_price = row_sec['close'] # exit at minute close
                    duration = 25 # forced exit
                    
                qty = calculate_qty(kite, entry_price, is_paper=True)
                gross_pnl = (exit_price - entry_price) * qty
                status = "CLOSED" if target_hit else "FORCE_CLOSED"
                
                # --- Tax Calculation per Trade ---
                buy_premium = entry_price * qty
                sell_premium = exit_price * qty
                total_premium = buy_premium + sell_premium
                
                brokerage = 40.0
                stt = sell_premium * 0.0015
                exchange_txn = total_premium * 0.0003503
                sebi = total_premium * 0.0000005
                stamp = buy_premium * 0.00003
                gst = (brokerage + exchange_txn) * 0.18
                total_taxes = brokerage + stt + exchange_txn + sebi + stamp + gst
                
                net_pnl = gross_pnl - total_taxes
                
                results.append({
                    "id": trade_id_counter,
                    "timestamp": entry_time.isoformat(),
                    "date": entry_time.strftime("%Y-%m-%d"),
                    "symbol": tsymbol,
                    "direction": signal,
                    "entry_price": round(entry_price, 2),
                    "exit_price": round(exit_price, 2),
                    "gross_pnl": round(gross_pnl, 2),
                    "total_taxes": round(total_taxes, 2),
                    "net_pnl": round(net_pnl, 2),
                    "strategy": "tax_optimized",
                    "status": status,
                    "qty": qty,
                    "exit_timestamp": exit_time.isoformat(),
                    "duration_secs": duration
                })
                trade_id_counter += 1
                break
                    
            busy_until = exit_time
            
    print(f"Simulation complete. Total trades: {len(results)}")
    
    csv_file = f"backtest_results_tax_optimized_{target_date_str.replace('-', '_')}.csv"
    keys = results[0].keys() if results else []
    with open(csv_file, "w", newline='') as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(results)
        
    print(f"Results saved to {csv_file}")

if __name__ == "__main__":
    run_backtest()
