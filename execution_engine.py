import time
import threading
import database
from config import get_kite_session, get_current_expiry

# ---------------------------------------------------------------------------
# Execution lock — prevents concurrent trades from the bot cron AND the
# manual terminal firing simultaneously (the root cause of ghost qty=0 trades)
# ---------------------------------------------------------------------------
_TRADE_LOCKS = {}

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Strict option price bounds — no trade is allowed outside this range
STRICT_MIN_PREMIUM = 40.0
STRICT_MAX_PREMIUM = 70.0

NIFTY_LOT_SIZE = 65  # Nifty option lot size — quantity must always be a multiple of this

# Paper trading capital constants (hard-coded until live trading is enabled)
# Total simulated margin available in the paper account
PAPER_TOTAL_MARGIN = 500_000.0
# Capital allocated per trade session during paper trading
PAPER_ALLOCATED_CAPITAL = 100_000.0


# ---------------------------------------------------------------------------
# Market price helper (bid/ask aware)
# ---------------------------------------------------------------------------

def calculate_taxes(entry, exit_p, qty):
    if entry <= 0 or exit_p <= 0 or qty <= 0:
        return 0.0
    sell_value = exit_p * qty
    buy_value = entry * qty
    turnover = sell_value + buy_value
    
    brokerage = 40.0
    stt = sell_value * 0.00125
    exc = turnover * 0.0003503
    gst = (brokerage + exc) * 0.18
    stamp = buy_value * 0.00003
    sebi = turnover * 0.000001
    
    return round(brokerage + stt + exc + gst + stamp + sebi, 2)


def get_market_price(kite, symbol, side="buy"):
    """
    Returns a realistic execution price by reading market depth.

    - side="buy"  → returns the best ASK price (lowest ask), i.e. what you
                    actually pay when buying the option.
    - side="sell" → returns the best BID price (highest bid), i.e. what you
                    actually receive when selling the option.

    Falls back to LTP if depth data is unavailable or the relevant side of
    the book is empty.
    """
    try:
        data = kite.quote(symbol)
        quote = data[symbol]
        depth = quote.get("depth", {})

        if side == "buy":
            asks = depth.get("sell", [])   # Kite depth: 'sell' side = asks
            # Filter out zero-price/zero-qty entries
            valid_asks = [a for a in asks if a.get("price", 0) > 0 and a.get("quantity", 0) > 0]
            if valid_asks:
                ask_price = valid_asks[0]["price"]   # best (lowest) ask
                print(f"[MarketDepth] {symbol} ASK={ask_price} (LTP={quote['last_price']})")
                return ask_price

        elif side == "sell":
            bids = depth.get("buy", [])    # Kite depth: 'buy' side = bids
            valid_bids = [b for b in bids if b.get("price", 0) > 0 and b.get("quantity", 0) > 0]
            if valid_bids:
                bid_price = valid_bids[0]["price"]   # best (highest) bid
                print(f"[MarketDepth] {symbol} BID={bid_price} (LTP={quote['last_price']})")
                return bid_price

        # Depth unavailable — fall back to LTP
        ltp = quote["last_price"]
        print(f"[MarketDepth] {symbol} depth unavailable, using LTP={ltp}")
        return ltp

    except Exception as e:
        print(f"[MarketDepth] Error fetching depth for {symbol}: {e}. Falling back to LTP.")
        try:
            return kite.quote(symbol)[symbol]["last_price"]
        except Exception:
            return 0.0


# ---------------------------------------------------------------------------
# Option selection
# ---------------------------------------------------------------------------

def get_atm_option(kite, direction, spot_price, expiry):
    """
    Scans strikes around the spot price and returns the symbol whose ASK price
    falls strictly within [STRICT_MIN_PREMIUM, STRICT_MAX_PREMIUM] (40–70).
    Uses the ask price for evaluation so that selection mirrors actual entry cost.
    """
    option_type = "CE" if direction == "BULL" else "PE"
    base_strike = round(spot_price / 100) * 100
    lower_range = base_strike - 1500
    upper_range = base_strike + 1500
    strikes = list(range(lower_range, upper_range + 100, 100))

    # Enforce strict price band: only options priced between 40 and 70 are eligible.
    # Options priced above 70 (e.g. 130-136) are explicitly excluded — no fallback.
    candidates_in_range = []

    for strike in strikes:
        symbol = f"NFO:NIFTY{expiry}{strike}{option_type}"
        try:
            # Use ASK price for selection — this is the real entry cost
            ask_price = get_market_price(kite, symbol, side="buy")
            if STRICT_MIN_PREMIUM <= ask_price <= STRICT_MAX_PREMIUM:
                candidates_in_range.append((symbol, ask_price, strike))
        except Exception:
            pass

    if candidates_in_range:
        # Among valid candidates, prefer the one whose ask is closest to the midpoint (₹55)
        target_premium = (STRICT_MIN_PREMIUM + STRICT_MAX_PREMIUM) / 2.0
        candidates_in_range.sort(key=lambda x: abs(x[1] - target_premium))
        best = candidates_in_range[0]
        print(
            f"[Option Selection] Chosen strike {best[2]} with ASK={best[1]:.2f} "
            f"(target band: {STRICT_MIN_PREMIUM}–{STRICT_MAX_PREMIUM})"
        )
        return best[0]

    # No option found in the 40–70 range — do NOT fall back to out-of-range options
    print(f"[Option Selection] No option found with ask in [{STRICT_MIN_PREMIUM}, {STRICT_MAX_PREMIUM}]. Trade skipped.")
    return None


# ---------------------------------------------------------------------------
# Quantity calculation
# ---------------------------------------------------------------------------

def calculate_qty(kite, entry_price, is_paper=False):
    """
    Returns the trade quantity as a strict multiple of NIFTY_LOT_SIZE (65).

    Paper mode (is_paper=True):
        Uses hard-coded PAPER_ALLOCATED_CAPITAL (₹1,00,000) and the ask-based
        entry price to compute affordable lots. No Kite API call is made.

    Fixed Quantity mode (use_fixed_quantity=True, live only):
        Uses the fixed_quantity DB setting, snapped down to the nearest
        multiple of 65 (minimum 1 lot = 65).

    Dynamic mode (use_fixed_quantity=False, live only):
        Fetches real available margin from Kite's NFO segment and applies
        the configured risk_percentage. Minimum is always 1 lot (65 units).
    """
    # --- Paper trading: hard-coded capital, no Kite margin API call ---
    if is_paper:
        lots = int(PAPER_ALLOCATED_CAPITAL / (entry_price * NIFTY_LOT_SIZE))
        qty = max(NIFTY_LOT_SIZE, lots * NIFTY_LOT_SIZE)
        print(
            f"[Qty] Paper mode: allocated=₹{PAPER_ALLOCATED_CAPITAL:.0f}, "
            f"entry(ask)={entry_price:.2f}, lots={lots}, qty={qty}"
        )
        return qty

    # --- Live: fixed quantity mode ---
    use_fixed_qty = bool(database.get_setting("use_fixed_quantity"))
    if use_fixed_qty:
        raw_qty = int(database.get_setting("fixed_quantity"))
        # Snap to the nearest lower multiple of 65; ensure at least 1 lot
        qty = max(NIFTY_LOT_SIZE, (raw_qty // NIFTY_LOT_SIZE) * NIFTY_LOT_SIZE)
        print(f"[Qty] Fixed mode: raw={raw_qty}, snapped to {qty} (lot size {NIFTY_LOT_SIZE})")
        return qty

    # --- Live: dynamic margin-based mode ---
    available_margin = None
    try:
        margins = kite.margins("commodity")   # NFO segment key is 'commodity' in Kite API
        available_margin = float(margins.get("net", 0) or 0)
    except Exception:
        pass

    if not available_margin or available_margin <= 0:
        # Fallback: use the portfolio capital stored in DB
        try:
            portfolio = database.get_portfolio()
            available_margin = float(portfolio.get("capital", 100_000.0))
        except Exception:
            available_margin = 100_000.0

    risk_percentage = float(database.get_setting("risk_percentage"))
    allocated_capital = available_margin * (risk_percentage / 100.0)

    # One lot costs: entry_price × NIFTY_LOT_SIZE
    lots = int(allocated_capital / (entry_price * NIFTY_LOT_SIZE))
    qty = max(NIFTY_LOT_SIZE, lots * NIFTY_LOT_SIZE)

    print(
        f"[Qty] Dynamic mode: margin=₹{available_margin:.0f}, risk={risk_percentage}%, "
        f"allocated=₹{allocated_capital:.0f}, entry(ask)={entry_price:.2f}, "
        f"lots={lots}, qty={qty}"
    )
    return qty


# ---------------------------------------------------------------------------
# Trade execution
# ---------------------------------------------------------------------------

def execute_trade(signal_data, active_strategy):
    """
    Executes the trade (Paper or Live) and monitors for up to 60 seconds.

    Price conventions:
      - Entry  → ASK price  (cost to buy the option)
      - Exit   → BID price  (proceeds from selling the option)
      - Target → based on ASK at entry; exit confirmed against BID

    Thread safety:
      Protected by _TRADE_LOCK so the bot cron and the manual terminal
      cannot both spawn an execution simultaneously. The second caller
      is rejected immediately — no trade is logged, no ghost entry created.
    """
    strategy_lock = _TRADE_LOCKS.setdefault(active_strategy, threading.Lock())
    if not strategy_lock.acquire(blocking=False):
        print(
            f"[ExecutionEngine] BLOCKED ({active_strategy}): another trade is already running. "
            "Skipping this signal to prevent duplicate/ghost trades."
        )
        return
    try:
        is_paper = bool(database.get_setting("paper_trading_mode"))
        kite = get_kite_session()
        expiry = get_current_expiry()

        direction = signal_data["signal"]
        spot_price = signal_data["indicators"]["current_price"]

        tsymbol = get_atm_option(kite, direction, spot_price, expiry)
        if tsymbol is None:
            print("No valid option found in the 40–70 range. Skipping trade.")
            return

        consecutive_entries = 0

        # Loop for Momentum Continuation
        while consecutive_entries < 3:
            consecutive_entries += 1

            # --- Spread Quality Gate ---
            ask = get_market_price(kite, tsymbol, side="buy")
            bid = get_market_price(kite, tsymbol, side="sell")

            if ask <= 0 or bid <= 0 or ask == bid:
                print(f"[{tsymbol}] Spread Quality Gate: Stale or zero depth (bid={bid}, ask={ask}). Skipping.")
                break

            spread_pct = ((ask - bid) / ask) * 100
            if spread_pct > 2.0:
                print(f"[{tsymbol}] Spread Quality Gate: Spread too wide ({spread_pct:.1f}% > 2%). Skipping.")
                break

            # --- Ignition Tick Filter ---
            print(f"[{tsymbol}] Checking ignition tick filter (wait up to 5s)...")
            ignition_passed = False
            last_price = ask
            for _ in range(5):
                time.sleep(1)
                new_ask = get_market_price(kite, tsymbol, side="buy")
                if new_ask > last_price:
                    ignition_passed = True
                    ask = new_ask
                    break
                last_price = new_ask

            if not ignition_passed:
                print(f"[{tsymbol}] Ignition filter: no momentum in 5s. Entering anyway...")
                ask = get_market_price(kite, tsymbol, side="buy")
            
            entry_price = ask
            
            print(f"[{'PAPER' if is_paper else 'LIVE'}] Opening {direction} trade on {tsymbol} | ASK={entry_price:.2f}")

            qty = calculate_qty(kite, entry_price, is_paper=is_paper)

            trade_id = database.log_trade({
                "symbol": tsymbol,
                "direction": direction,
                "entry_price": entry_price,
                "exit_price": 0.0,
                "pnl": 0.0,
                "is_paper": is_paper,
                "strategy": active_strategy,
                "status": "OPEN",
                "qty": qty,
            })

            # --- Time-Adaptive Target ---
            now = datetime.now()
            hour_float = now.hour + now.minute / 60.0
            if 9.33 <= hour_float <= 10.0:
                target_pct = 3.0
            elif 10.0 < hour_float <= 14.5:
                target_pct = 2.0
            elif 14.5 < hour_float <= 15.0:
                target_pct = 2.5
            else:
                target_pct = 1.5

            target_price = round(entry_price * (1 + (target_pct / 100.0)), 1)
            print(f"[{tsymbol}] Time-Adaptive Target set to {target_pct}% | Target Price={target_price:.2f}")

            if not is_paper:
                # LIVE EXECUTION — place real orders
                try:
                    buy_order_id = kite.place_order(
                        tradingsymbol=tsymbol,
                        exchange=kite.EXCHANGE_NFO,
                        transaction_type=kite.TRANSACTION_TYPE_BUY,
                        quantity=qty,
                        variety=kite.VARIETY_REGULAR,
                        order_type=kite.ORDER_TYPE_MARKET,
                        product=kite.PRODUCT_MIS,
                    )
                    # Place limit sell target order
                    sell_order_id = kite.place_order(
                        tradingsymbol=tsymbol,
                        exchange=kite.EXCHANGE_NFO,
                        transaction_type=kite.TRANSACTION_TYPE_SELL,
                        quantity=qty,
                        price=target_price,
                        variety=kite.VARIETY_REGULAR,
                        order_type=kite.ORDER_TYPE_LIMIT,
                        product=kite.PRODUCT_MIS,
                    )
                except Exception as e:
                    print(f"Live execution failed: {e}")
                    database.update_trade_status(trade_id, entry_price, 0.0, status="ERROR")
                    break

            # -------------------------------------------------------------------
            # 25-second monitoring loop
            # -------------------------------------------------------------------
            t = 0
            target_hit = False
            exit_price = entry_price

            while t < 25:
                # Check if another signal closed this trade in the DB (Option B logic)
                open_trades = database.get_open_trades()
                if not any(tr["id"] == trade_id for tr in open_trades):
                    print(f"Trade {trade_id} was closed by another process. Exiting monitor loop.")
                    return

                try:
                    if is_paper:
                        # Paper: use BID price to check if target is reachable
                        current_bid = get_market_price(kite, tsymbol, side="sell")
                        if current_bid >= target_price:
                            target_hit = True
                            exit_price = current_bid   # exit at what the market will actually pay
                            print(f"[Paper] Target hit! BID={current_bid:.2f} >= target={target_price:.2f} at t={t}s")
                            break
                    else:
                        # Live: check order status
                        orders = kite.orders()
                        target_order = next(
                            (o for o in reversed(orders) if o["order_id"] == sell_order_id), None
                        )
                        if target_order and target_order["status"] == "COMPLETE":
                            target_hit = True
                            exit_price = target_order["average_price"]
                            break

                except Exception as e:
                    print(f"Error during monitoring loop (t={t}s): {e}")

                time.sleep(1)
                t += 1

            # -------------------------------------------------------------------
            # Time-based stop-loss (25 seconds elapsed without target)
            # -------------------------------------------------------------------
            if not target_hit:
                if is_paper:
                    # Paper: exit at the BID price (realistic sell price)
                    exit_price = get_market_price(kite, tsymbol, side="sell")
                    print(f"[Paper] 25s Time SL: exiting at BID={exit_price:.2f}")
                else:
                    # Live: convert the open limit sell order to a market order
                    try:
                        orders = kite.orders()
                        active_sell_order = next(
                            (
                                o for o in reversed(orders)
                                if o["tradingsymbol"] == tsymbol.split(":")[-1]
                                and o["transaction_type"] == "SELL"
                                and o["status"] in ["OPEN", "TRIGGER PENDING"]
                            ),
                            None,
                        )
                        if active_sell_order:
                            kite.modify_order(
                                variety=kite.VARIETY_REGULAR,
                                order_id=active_sell_order["order_id"],
                                order_type=kite.ORDER_TYPE_MARKET,
                            )
                        else:
                            kite.place_order(
                                tradingsymbol=tsymbol.split(":")[-1],
                                exchange=kite.EXCHANGE_NFO,
                                transaction_type=kite.TRANSACTION_TYPE_SELL,
                                quantity=qty,
                                variety=kite.VARIETY_REGULAR,
                                order_type=kite.ORDER_TYPE_MARKET,
                                product=kite.PRODUCT_MIS,
                            )
                        # Fetch final executed price for live SL
                        exit_price = get_market_price(kite, tsymbol, side="sell")
                    except Exception as e:
                        print(f"Error executing live time SL: {e}")

            gross_pnl = (exit_price - entry_price) * qty
            taxes = calculate_taxes(entry_price, exit_price, qty)
            net_pnl = gross_pnl - taxes
            
            status_val = "CLOSED" if target_hit else "FORCE_CLOSED"
            database.update_trade_status(trade_id, exit_price, net_pnl, status=status_val, taxes=taxes, gross_pnl=gross_pnl)
            database.update_portfolio(net_pnl)
            print(f"Trade {trade_id} {status_val} | entry(ask)={entry_price:.2f} exit(bid)={exit_price:.2f} qty={qty} NetPnL=₹{net_pnl:.2f} Taxes=₹{taxes:.2f}")

            # --- Momentum Continuation ---
            if target_hit and t < 5 and consecutive_entries < 3:
                print(f"[{tsymbol}] Target hit in {t}s! Momentum continuation triggered. Re-entering immediately...")
                time.sleep(0.5) # Slight pause to let order books settle
                continue
            else:
                break

    finally:
        # Always release the lock — even on early returns or exceptions
        if strategy_lock.locked():
            strategy_lock.release()


def force_close_trade(trade, kite):
    """
    Closes an open trade immediately (Option B logic).
    Exit price uses the BID side of the book — the realistic sell price.
    """
    tsymbol = trade["symbol"]
    is_paper = trade["is_paper"]

    # Reconstruct quantity using the same logic as at entry
    qty = calculate_qty(kite, trade["entry_price"], is_paper=is_paper)

    # Exit at BID — what the market will actually pay when we sell
    exit_price = get_market_price(kite, tsymbol, side="sell")
    if exit_price <= 0:
        exit_price = trade["entry_price"]   # last-resort fallback

    if not is_paper:
        try:
            kite.place_order(
                tradingsymbol=tsymbol.split(":")[-1],
                exchange=kite.EXCHANGE_NFO,
                transaction_type=kite.TRANSACTION_TYPE_SELL,
                quantity=qty,
                variety=kite.VARIETY_REGULAR,
                order_type=kite.ORDER_TYPE_MARKET,
                product=kite.PRODUCT_MIS,
            )
        except Exception as e:
            print(f"Failed to force close live trade: {e}")

    gross_pnl = (exit_price - trade["entry_price"]) * qty
    taxes = calculate_taxes(trade["entry_price"], exit_price, qty)
    net_pnl = gross_pnl - taxes
    
    database.update_trade_status(trade["id"], exit_price, net_pnl, status="FORCE_CLOSED", taxes=taxes, gross_pnl=gross_pnl)
    database.update_portfolio(net_pnl)
    print(
        f"Force closed trade {trade['id']} | "
        f"entry(ask)={trade['entry_price']:.2f} exit(bid)={exit_price:.2f} "
        f"qty={qty} NetPnL=₹{net_pnl:.2f} Taxes=₹{taxes:.2f}"
    )
