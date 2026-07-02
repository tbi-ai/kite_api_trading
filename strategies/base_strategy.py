class BaseStrategy:
    """
    Base class for all trading strategies.
    All custom strategies must inherit from this and implement the evaluate method.
    """
    def __init__(self, kite):
        self.kite = kite

    def evaluate(self, lstm_prediction=None):
        """
        Evaluate the market and return a trading signal.
        Returns:
            dict: {
                "signal": "BULL" | "BEAR" | "NO_SIGNAL",
                "indicators": dict,
                "confidence": float
            }
        """
        raise NotImplementedError("Strategy must implement evaluate()")
