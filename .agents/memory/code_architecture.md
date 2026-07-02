# Code Architecture & Bugs Memory

## Bug Fix: Ghost Trades and Race Conditions (2026-07-01)
- The bot was generating "Ghost Trades" (qty=0, no real execution) because multiple cron ticks were spawning `execute_trade` threads simultaneously while previous trades were still in their monitoring loop.
- **Solution**: Implemented `_TRADE_LOCK = threading.Lock()` in `execution_engine.py` as a singleton lock. The engine now refuses to spawn new trades if a previous trade holds the lock.

## Limitation: Kite API Rate Limits (2026-07-01)
- Iterating through live quotes (`kite.quote()`) or historical data for multiple option strikes simultaneously hits the API rate limits heavily (Too Many Requests).
- **Solution**: We mocked the `get_atm_option` dynamically in backtesting to calculate the strike mathematically instead of pinging the option chain. Always cache live quotes when possible.
