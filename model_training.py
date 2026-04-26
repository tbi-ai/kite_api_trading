import pandas as pd
import numpy as np
import pandas_ta as ta
from datetime import datetime, timedelta
from sklearn.preprocessing import MinMaxScaler
import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Dropout
from tensorflow.keras.optimizers import Adam
import os

# Note: In a production environment, you would use get_kite_session() from config.
# For simplicity in this standalone script, we import the helper here.
from config import get_kite_session

def fetch_historical_training_data(kite, spot_inst_token, days=180):
    """Fetch larger dataset for training."""
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    
    data = kite.historical_data(
        spot_inst_token, 
        start_date.strftime("%Y-%m-%d"), 
        end_date.strftime("%Y-%m-%d"), 
        '15minute'
    )
    df = pd.DataFrame(data)
    if not df.empty:
        df['date'] = pd.to_datetime(df['date'])
        df.set_index('date', inplace=True)
    return df

def add_training_indicators(df):
    """Add indicators needed for LSTM features."""
    df['EMA9'] = ta.ema(df['close'], length=9)
    df['EMA21'] = ta.ema(df['close'], length=21)
    df['RSI14'] = ta.rsi(df['close'], length=14)
    df['RSI6'] = ta.rsi(df['close'], length=6)

    macd = ta.macd(df['close'])
    if macd is not None and not macd.empty:
        df['MACD'] = macd['MACD_12_26_9']
        df['MACD_signal'] = macd['MACDs_12_26_9']

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

    st = ta.supertrend(df['high'], df['low'], df['close'], length=10, multiplier=3)
    if st is not None and not st.empty:
        df['SuperTrend'] = st[st.columns[0]]
    else:
        df['SuperTrend'] = df['close']

    df.dropna(inplace=True)
    return df

def train_lstm_model():
    print("Initializing Kite session for data download...")
    kite = get_kite_session()
    
    spot_symbol = "NSE:NIFTY 50"
    quote = kite.quote(spot_symbol)
    spot_inst_token = quote[spot_symbol]['instrument_token']

    print("Fetching 180 days of historical data...")
    df = fetch_historical_training_data(kite, spot_inst_token, days=180)
    
    if df.empty:
        print("Error: No data fetched.")
        return

    print("Adding indicators...")
    df = add_training_indicators(df)

    # Set up regression target (points change)
    df['target_points'] = df['close'].shift(-1) - df['close']
    df = df[:-1] # Drop last row which has NaN target

    features = ['close', 'EMA9', 'EMA21', 'RSI14', 'RSI6',
                'MACD', 'MACD_signal', 'SuperTrend',
                'BB_upper', 'BB_lower', 'BB_width', 'BB_pct']
                
    X = df[features].values
    y = df['target_points'].values

    # Scale features
    scaler = MinMaxScaler()
    X_scaled = scaler.fit_transform(X)

    # Create sequences
    timesteps = 60
    X_seq, y_seq = [], []
    for i in range(timesteps, len(X_scaled)):
        X_seq.append(X_scaled[i-timesteps:i])
        y_seq.append(y[i])

    X_seq = np.array(X_seq)
    y_seq = np.array(y_seq)

    # Train/Val Split (80/20)
    split = int(0.8 * len(X_seq))
    X_train, y_train = X_seq[:split], y_seq[:split]
    X_val, y_val = X_seq[split:], y_seq[split:]

    print(f"Training on {len(X_train)} samples, validating on {len(X_val)} samples.")

    # Build Model
    model = Sequential([
        LSTM(64, return_sequences=True, input_shape=(timesteps, len(features))),
        Dropout(0.3),
        LSTM(64, return_sequences=False),
        Dropout(0.3),
        Dense(32, activation='relu'),
        Dense(1) # Linear output
    ])

    model.compile(optimizer=Adam(learning_rate=0.001), loss='mse', metrics=['mae'])
    
    print("Starting training...")
    model.fit(X_train, y_train, epochs=20, batch_size=32, validation_data=(X_val, y_val), verbose=1)

    # Save Model
    model_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "nifty_lstm.keras")
    model.save(model_path)
    print(f"✅ Model training complete and saved to {model_path}")

if __name__ == "__main__":
    train_lstm_model()
