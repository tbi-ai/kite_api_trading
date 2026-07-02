# Trading History & Strategy Memory

## Lesson: Micro-Scalping and Transaction Costs (2026-07-01)
- We discovered that executing high-frequency micro-trades (e.g., 300+ trades per day) with a tight 25-second timer and 2% target resulted in massive gross profits (₹92k) but was completely wiped out by transaction costs (₹99k in fees), resulting in a net loss.
- **Key Takeaway**: Any new strategy must account for exact Zerodha NSE Options taxes (0.15% STT on sell, 0.03503% Exchange Txn, 18% GST). We must filter trades for extremely high conviction or increase the target sizes to overcome the transaction tax drag.

## Lesson: Spread Quality Gates (2026-07-01)
- Trading in illiquid hours (e.g., after 3:20 PM) caused "Ghost Trades" due to 0 Bid/Ask depths.
- **Key Takeaway**: Always enforce a Spread Quality Gate (Bid > 0, Ask > 0, Spread < 2%) before entering any trade.

## Lesson: Simultaneous A/B Testing (2026-07-01)
- We discovered that running multiple trading strategies simultaneously requires careful lock management.
- **Key Takeaway**: The `_TRADE_LOCK` in `execution_engine.py` was refactored into a `_TRADE_LOCKS` dictionary. This allows independent strategies (e.g., `sixty_second_momentum` and `tax_optimized_momentum`) to run concurrently and hold separate paper trades open without blocking each other.
- **Caution**: While overlapping trades are safe for paper trading, deploying multiple concurrent strategies in a live account may lead to margin constraints or conflicting opposite positions.
