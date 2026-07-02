# Machine Learning Models Memory

## LSTM Architecture details
- The `nifty_lstm.keras` model is trained as a **Regressor**, not a Classifier.
- It takes 60 timesteps of 15-minute data and outputs a single float value (predicted future price).
- **Misconception Corrected**: The model does NOT output probability percentages (e.g., "56% Bearish"). To determine direction, we must compare the model's predicted price to the current spot price.
