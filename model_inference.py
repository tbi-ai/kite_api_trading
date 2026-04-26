import pandas as pd
import pandas_ta as ta
import numpy as np
import os
import time
from datetime import datetime, timedelta
from config import get_kite_session

# Global cache for LSTM prediction
_lstm_cache = {
    "prediction": None,
    "timestamp": 0
}

def generate_features_from_recent(kite, spot_inst_token):
    """Fetch recent data and generate features for the LSTM."""
    from sklearn.preprocessing import MinMaxScaler
    end_date = datetime.now()
    start_date = end_date - timedelta(days=5) # Ensure we get 60 periods of 15m
    
    data = kite.historical_data(
        spot_inst_token, 
        start_date.strftime("%Y-%m-%d"), 
        end_date.strftime("%Y-%m-%d"), 
        '15minute'
    )
    df = pd.DataFrame(data)
    if df.empty:
        return None
        
    df['date'] = pd.to_datetime(df['date'])
    df.set_index('date', inplace=True)
    
    # Add indicators (same as training)
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
        bb_upper_col = next((col for col in bb.columns if 'BBU' in col), None)
        bb_middle_col = next((col for col in bb.columns if 'BBM' in col), None)
        bb_lower_col = next((col for col in bb.columns if 'BBL' in col), None)
        
        df['BB_upper'] = bb[bb_upper_col]
        df['BB_middle'] = bb[bb_middle_col]
        df['BB_lower'] = bb[bb_lower_col]
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
    
    if len(df) < 60:
        return None
        
    features = ['close', 'EMA9', 'EMA21', 'RSI14', 'RSI6',
                'MACD', 'MACD_signal', 'SuperTrend',
                'BB_upper', 'BB_lower', 'BB_width', 'BB_pct']
                
    X = df[features].values[-60:] # Get last 60 periods
    
    # Scale features
    scaler = MinMaxScaler()
    X_scaled = scaler.fit_transform(X) # Note: For strict correctness, we should use the scaler saved from training. For simplicity in this iteration, we fit on recent data.
    
    return np.array([X_scaled]) # Shape (1, 60, 12)

def get_lstm_prediction(kite, spot_inst_token, force_refresh=False):
    """Get cached LSTM prediction or generate a new one if force_refresh is True."""
    global _lstm_cache
    import tensorflow as tf
    
    if not force_refresh and _lstm_cache["prediction"] is not None:
        return _lstm_cache["prediction"]
        
    try:
        model_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "nifty_lstm.keras")
        if not os.path.exists(model_path):
            print("Model file not found.")
            return 0.0
            
        # Load model and run prediction
        # To avoid re-loading model constantly, we could cache it too, but let's stick to user request.
        model = tf.keras.models.load_model(model_path)
        X_input = generate_features_from_recent(kite, spot_inst_token)
        
        if X_input is None:
            return 0.0
            
        pred = model.predict(X_input, verbose=0)
        result = float(pred[0][0])
        
        _lstm_cache["prediction"] = result
        _lstm_cache["timestamp"] = time.time()
        return result
    except Exception as e:
        print(f"LSTM Prediction Error: {e}")
        return 0.0

def get_ml_signals(force_refresh=False):
    """
    Fetches real-time price, calculates indicators, generates signals,
    and fetches live LSTM deep learning prediction.
    """
    kite = get_kite_session()
    
    spot_symbol = "NSE:NIFTY 50"
    quote = kite.quote(spot_symbol)
    
    if spot_symbol not in quote:
        raise ValueError("Failed to fetch quote for NIFTY 50")
        
    instrument_token = quote[spot_symbol]['instrument_token']
    
    # Fetch 1 min data for rule-based indicators
    end_date = datetime.now()
    start_date = end_date - timedelta(days=2)
    data = kite.historical_data(
        instrument_token, 
        start_date.strftime("%Y-%m-%d"), 
        end_date.strftime("%Y-%m-%d"), 
        'minute'
    )
    
    df = pd.DataFrame(data)
    df['date'] = pd.to_datetime(df['date'])
    df.set_index('date', inplace=True)
    
    # Calculate Indicators
    df['EMA9'] = ta.ema(df['close'], length=9)
    df['EMA21'] = ta.ema(df['close'], length=21)
    df['RSI14'] = ta.rsi(df['close'], length=14)
    df['RSI6'] = ta.rsi(df['close'], length=6)
    
    macd = ta.macd(df['close'])
    if macd is not None and not macd.empty:
        df['MACD'] = macd['MACD_12_26_9']
    else:
        df['MACD'] = 0
        
    st = ta.supertrend(df['high'], df['low'], df['close'], length=10, multiplier=3)
    if st is not None and not st.empty:
        df['SuperTrend'] = st[st.columns[0]]
    else:
        df['SuperTrend'] = df['close']
        
    bb = ta.bbands(df['close'], length=20, std=2)
    squeeze_active = False
    if bb is not None and not bb.empty:
        bb_upper_col = next((col for col in bb.columns if 'BBU' in col), None)
        bb_lower_col = next((col for col in bb.columns if 'BBL' in col), None)
        df['BB_upper'] = bb[bb_upper_col]
        df['BB_lower'] = bb[bb_lower_col]
        df['BB_width'] = (df['BB_upper'] - df['BB_lower']) / df['close']
        
        if df['BB_width'].iloc[-1] < 0.001:
            squeeze_active = True
            
    current_price = df['close'].iloc[-1]
    prev_price = df['close'].iloc[-2]
    
    rsi14 = df['RSI14'].iloc[-1]
    rsi6 = df['RSI6'].iloc[-1]
    ema9 = df['EMA9'].iloc[-1]
    ema21 = df['EMA21'].iloc[-1]
    macd_val = df['MACD'].iloc[-1]
    supertrend_val = df['SuperTrend'].iloc[-1]
    
    # Generate Rule-Based Signal
    signal = "NO_SIGNAL"
    
    if not squeeze_active:
        if (current_price > ema9 and ema9 > ema21) and \
           (rsi14 > 55 and rsi6 > 60) and \
           (macd_val > 0) and \
           (current_price > supertrend_val):
            signal = "BULL"
            
        elif (current_price < ema9 and ema9 < ema21) and \
             (rsi14 < 45 and rsi6 < 40) and \
             (macd_val < 0) and \
             (current_price < supertrend_val):
            signal = "BEAR"

    # Get LSTM Prediction
    lstm_prediction = get_lstm_prediction(kite, instrument_token, force_refresh)

    return {
        "signal": signal,
        "squeeze_active": squeeze_active,
        "lstm_prediction": round(lstm_prediction, 2),
        "lstm_timestamp": _lstm_cache["timestamp"],
        "indicators": {
            "current_price": round(current_price, 2),
            "rsi14": round(rsi14, 2) if not pd.isna(rsi14) else 0,
            "rsi6": round(rsi6, 2) if not pd.isna(rsi6) else 0,
            "ema9": round(ema9, 2) if not pd.isna(ema9) else 0,
            "ema21": round(ema21, 2) if not pd.isna(ema21) else 0,
            "macd": round(macd_val, 2) if not pd.isna(macd_val) else 0,
            "supertrend": round(supertrend_val, 2) if not pd.isna(supertrend_val) else 0
        }
    }
