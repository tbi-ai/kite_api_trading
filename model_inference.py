import pandas as pd
import numpy as np
import pandas_ta as ta
import os
import time
from datetime import datetime, timedelta

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
    X_scaled = scaler.fit_transform(X)
    
    return np.array([X_scaled]) # Shape (1, 60, 12)

_cached_model = None

def get_lstm_prediction(kite, spot_inst_token, force_refresh=False):
    """
    Returns the LSTM model's predicted next-15-minute close price for NIFTY 50.

    IMPORTANT — this is a REGRESSION output, NOT a probability:
      - The model was trained with a linear Dense(1) head and MSE loss.
      - Target was: next_close - current_close  (signed price delta in points).
      - The raw output is therefore a *predicted next close price* (after the
        MinMaxScaler inverse is approximated by comparing to current_price).
      - There is no softmax, no sigmoid, no percentage. Direction is determined
        by whether pred > current_price (BULL) or pred < current_price (BEAR).

    Use get_lstm_direction() for a pre-computed direction + confidence string.
    """
    global _lstm_cache, _cached_model
    import tensorflow as tf

    # Cache for 1 minute
    if not force_refresh and _lstm_cache["prediction"] is not None:
        if time.time() - _lstm_cache["timestamp"] < 60:
            return _lstm_cache["prediction"]

    try:
        if _cached_model is None:
            model_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "nifty_lstm.keras")
            if not os.path.exists(model_path):
                print("Model file not found. Returning None.")
                return None
            _cached_model = tf.keras.models.load_model(model_path)

        X_input = generate_features_from_recent(kite, spot_inst_token)

        if X_input is None:
            return None

        pred = _cached_model.predict(X_input, verbose=0)
        result = float(pred[0][0])

        _lstm_cache["prediction"] = result
        _lstm_cache["timestamp"] = time.time()
        return result
    except Exception as e:
        print(f"LSTM Prediction Error: {e}")
        return None


def get_lstm_direction(kite, spot_inst_token, current_price, force_refresh=False):
    """
    Converts the raw LSTM regression output into a directional signal.

    Returns a dict:
        {
          "direction":      "BULL" | "BEAR" | None,
          "predicted_price": float | None,
          "delta_points":    float | None,   # predicted_price - current_price
          "confidence_pct":  float | None,   # |delta| as % of current_price
        }

    confidence_pct reflects how far the model predicts price will move — a
    larger predicted move = higher confidence in that direction.
    None is returned for all fields if the model or data is unavailable.
    """
    predicted_price = get_lstm_prediction(kite, spot_inst_token, force_refresh=force_refresh)

    if predicted_price is None:
        return {"direction": None, "predicted_price": None, "delta_points": None, "confidence_pct": None}

    delta = predicted_price - current_price
    direction = "BULL" if delta > 0 else "BEAR"
    # Express the predicted move as a % of current price (e.g. 0.15% move)
    confidence_pct = round(abs(delta) / current_price * 100, 3)

    print(
        f"[LSTM] predicted={predicted_price:.2f} current={current_price:.2f} "
        f"delta={delta:+.2f}pts direction={direction} confidence={confidence_pct}%"
    )

    return {
        "direction": direction,
        "predicted_price": round(predicted_price, 2),
        "delta_points": round(delta, 2),
        "confidence_pct": confidence_pct,
    }

