import pandas as pd
import pandas_ta as ta
from datetime import datetime, timedelta
from strategies.base_strategy import BaseStrategy


class TaxOptimizedMomentum(BaseStrategy):
    """
    Aggressive momentum strategy using EMA crossover, RSI, MACD, and LSTM.

    Signal philosophy — ALWAYS BULL or BEAR, never neutral:
      - Four rule-based indicators each cast a vote (1 point each).
      - LSTM price prediction adds 2 points to whichever direction it agrees with.
      - Maximum possible score is 6 (all indicators + LSTM aligned).
      - The direction with the higher score wins. In an exact tie (rare), LSTM
        breaks it; if LSTM is also unavailable the most recent 1-min close
        direction vs EMA9 is used as a final fallback.
      - NO_SIGNAL is only returned when live data cannot be fetched at all
        (API error / no bars), meaning there is genuinely nothing to trade on.
      - A Bollinger-Band squeeze flag is reported for informational purposes but
        no longer blocks trade execution.

    Confidence is reported as a percentage (0–100%) for clarity in logs/UI.
    """

    # Indicator weights
    _RULE_WEIGHT = 1   # each rule-based indicator
    _LSTM_WEIGHT = 2   # LSTM prediction
    
    # Strategy Filters
    min_score_gap = 4
    requires_volatility = True

    def evaluate(self, lstm_prediction=None):
        spot_symbol = "NSE:NIFTY 50"
        try:
            quote = self.kite.quote(spot_symbol)
            if spot_symbol not in quote:
                return {
                    "signal": "NO_SIGNAL",
                    "reason": "Failed to fetch spot quote — API error",
                    "confidence": 0.0,
                    "confidence_pct": 0,
                    "squeeze_active": False,
                    "indicators": {},
                }

            instrument_token = quote[spot_symbol]["instrument_token"]

            # Fetch last 2 days of 1-minute bars
            end_date = datetime.now()
            start_date = end_date - timedelta(days=2)
            data = self.kite.historical_data(
                instrument_token,
                start_date.strftime("%Y-%m-%d"),
                end_date.strftime("%Y-%m-%d"),
                "minute",
            )

            if not data:
                return {
                    "signal": "NO_SIGNAL",
                    "reason": "No 1-minute historical bars returned",
                    "confidence": 0.0,
                    "confidence_pct": 0,
                    "squeeze_active": False,
                    "indicators": {},
                }

            df = pd.DataFrame(data)
            df["date"] = pd.to_datetime(df["date"])
            df.set_index("date", inplace=True)

            # ----------------------------------------------------------------
            # Indicators
            # ----------------------------------------------------------------
            df["EMA9"] = ta.ema(df["close"], length=9)
            df["EMA21"] = ta.ema(df["close"], length=21)
            df["RSI14"] = ta.rsi(df["close"], length=14)
            df["RSI6"] = ta.rsi(df["close"], length=6)

            macd = ta.macd(df["close"])
            df["MACD"] = macd["MACD_12_26_9"] if (macd is not None and not macd.empty) else 0

            st = ta.supertrend(df["high"], df["low"], df["close"], length=10, multiplier=3)
            df["SuperTrend"] = st[st.columns[0]] if (st is not None and not st.empty) else df["close"]

            bb = ta.bbands(df["close"], length=20, std=2)
            squeeze_active = False
            if bb is not None and not bb.empty:
                bbu = next((c for c in bb.columns if "BBU" in c), None)
                bbl = next((c for c in bb.columns if "BBL" in c), None)
                df["BB_upper"] = bb[bbu]
                df["BB_lower"] = bb[bbl]
                df["BB_width"] = (df["BB_upper"] - df["BB_lower"]) / df["close"]
                squeeze_active = bool(df["BB_width"].iloc[-1] < 0.001)

            # Latest bar values
            current_price = float(df["close"].iloc[-1])
            rsi14 = float(df["RSI14"].iloc[-1]) if not pd.isna(df["RSI14"].iloc[-1]) else 50.0
            rsi6  = float(df["RSI6"].iloc[-1])  if not pd.isna(df["RSI6"].iloc[-1])  else 50.0
            ema9  = float(df["EMA9"].iloc[-1])   if not pd.isna(df["EMA9"].iloc[-1])  else current_price
            ema21 = float(df["EMA21"].iloc[-1])  if not pd.isna(df["EMA21"].iloc[-1]) else current_price
            macd_val      = float(df["MACD"].iloc[-1])       if not pd.isna(df["MACD"].iloc[-1])       else 0.0
            supertrend_val = float(df["SuperTrend"].iloc[-1]) if not pd.isna(df["SuperTrend"].iloc[-1]) else current_price

            # ----------------------------------------------------------------
            # Scoring — each indicator votes BULL or BEAR
            # ----------------------------------------------------------------
            bullish_score = 0
            bearish_score = 0

            # Rule 1: price vs EMA9
            if current_price > ema9:
                bullish_score += self._RULE_WEIGHT
            else:
                bearish_score += self._RULE_WEIGHT

            # Rule 2: EMA9 vs EMA21 (trend direction)
            if ema9 > ema21:
                bullish_score += self._RULE_WEIGHT
            else:
                bearish_score += self._RULE_WEIGHT

            # Rule 3: RSI14 relative to midpoint
            if rsi14 > 50:
                bullish_score += self._RULE_WEIGHT
            else:
                bearish_score += self._RULE_WEIGHT

            # Rule 4: MACD histogram sign
            if macd_val > 0:
                bullish_score += self._RULE_WEIGHT
            else:
                bearish_score += self._RULE_WEIGHT

            # LSTM price prediction (weighted 2x)
            # lstm_prediction is the model's predicted next-15m close price.
            # It is NOT a probability — direction is inferred by comparing to current_price.
            lstm_bullish = lstm_prediction is not None and lstm_prediction > current_price
            lstm_bearish = lstm_prediction is not None and lstm_prediction < current_price

            if lstm_bullish:
                bullish_score += self._LSTM_WEIGHT
            elif lstm_bearish:
                bearish_score += self._LSTM_WEIGHT
            # If lstm_prediction is None or exactly == current_price, no extra weight added

            # ----------------------------------------------------------------
            # Direction resolution — ALWAYS resolve to BULL or BEAR
            # ----------------------------------------------------------------
            max_score = (4 * self._RULE_WEIGHT) + self._LSTM_WEIGHT  # = 6

            if bullish_score > bearish_score:
                signal = "BULL"
                winning_score = bullish_score
            elif bearish_score > bullish_score:
                signal = "BEAR"
                winning_score = bearish_score
            else:
                # Exact tie — use LSTM as tiebreaker
                if lstm_bullish:
                    signal = "BULL"
                elif lstm_bearish:
                    signal = "BEAR"
                else:
                    # LSTM also unavailable or neutral — fall back to price vs EMA9
                    signal = "BULL" if current_price > ema9 else "BEAR"
                winning_score = bullish_score  # scores are equal

            # Confidence as a percentage of the maximum possible score
            confidence_pct = round((winning_score / max_score) * 100, 1)
            confidence = winning_score / max_score  # 0.0–1.0 for backward compat

            print(
                f"[Strategy] {signal} | bull={bullish_score} bear={bearish_score} "
                f"confidence={confidence_pct}% | "
                f"LSTM={'↑' if lstm_bullish else '↓' if lstm_bearish else 'N/A'} "
                f"squeeze={'YES' if squeeze_active else 'no'}"
            )

            return {
                "signal": signal,
                "squeeze_active": squeeze_active,
                "confidence": confidence,
                "confidence_pct": confidence_pct,
                "bullish_score": bullish_score,
                "bearish_score": bearish_score,
                "indicators": {
                    "current_price": round(current_price, 2),
                    "rsi14":         round(rsi14, 2),
                    "rsi6":          round(rsi6, 2),
                    "ema9":          round(ema9, 2),
                    "ema21":         round(ema21, 2),
                    "macd":          round(macd_val, 2),
                    "supertrend":    round(supertrend_val, 2),
                    "lstm_pred":     round(lstm_prediction, 2) if lstm_prediction is not None else None,
                },
            }

        except Exception as e:
            return {
                "signal": "NO_SIGNAL",
                "reason": f"Strategy Error: {e}",
                "confidence": 0.0,
                "confidence_pct": 0,
                "squeeze_active": False,
                "indicators": {},
            }
