import asyncio
import json
import pandas as pd
from datetime import datetime
from config import get_kite_session
from model_inference import get_ml_signals
from trade_db import record_trade

# Strict option price bounds — no trade is allowed outside this range
STRICT_MIN_PREMIUM = 40.0
STRICT_MAX_PREMIUM = 70.0

def get_atm_option(kite, direction, spot_price, expiry):
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
            quote = kite.quote(symbol)
            premium = quote[symbol]['last_price']
            if STRICT_MIN_PREMIUM <= premium <= STRICT_MAX_PREMIUM:
                candidates_in_range.append((symbol, premium, strike))
        except Exception:
            pass

    if candidates_in_range:
        # Among valid candidates, prefer the one whose premium is closest to the midpoint (55)
        target_premium = (STRICT_MIN_PREMIUM + STRICT_MAX_PREMIUM) / 2.0
        candidates_in_range.sort(key=lambda x: abs(x[1] - target_premium))
        best = candidates_in_range[0]
        print(f"[Option Selection] Chosen strike {best[2]} with premium {best[1]:.2f} (target band: {STRICT_MIN_PREMIUM}–{STRICT_MAX_PREMIUM})")
        return best[0]

    # No option found in the 40–70 range — do NOT fall back to out-of-range options
    print(f"[Option Selection] No option found with premium in [{STRICT_MIN_PREMIUM}, {STRICT_MAX_PREMIUM}]. Trade skipped.")
    return None

async def execute_trade_stream(expiry="26MAY"):
    """
    Async Generator for Server-Sent Events (SSE).
    Executes a trade and streams the live status back to the frontend.
    """
    def sse_message(log_text, status="running", pnl=0):
        data = {"log": log_text, "status": status, "pnl": pnl}
        return f"data: {json.dumps(data)}\n\n"

    try:
        kite = get_kite_session()
        yield sse_message("Session initialized. Fetching signals...")
        await asyncio.sleep(1)

        signal_data = get_ml_signals()
        direction = signal_data['signal']
        spot_price = signal_data['indicators']['current_price']
        
        yield sse_message(f"Direction is {direction} at spot price {spot_price}")
        await asyncio.sleep(1)

        if direction == "NO_SIGNAL":
            yield sse_message("No valid signal generated (NO_SIGNAL or Squeeze Active). Trade aborted.", status="done", pnl=0)
            return

        tsymbol = get_atm_option(kite, direction, spot_price, expiry)
        if tsymbol is None:
            yield sse_message("No option found with premium in [40, 70]. Trade skipped.", status="done", pnl=0)
            return
        yield sse_message(f"Selected Option Symbol: {tsymbol}")
        await asyncio.sleep(1)

        yield sse_message("Placing BUY order for 500 quantity (Market, MIS)...")
        
        try:
            # LIVE TRADING EXECUTION
            buy_order_id = kite.place_order(
                tradingsymbol=tsymbol,
                exchange=kite.EXCHANGE_NFO,
                transaction_type=kite.TRANSACTION_TYPE_BUY,
                quantity=650,
                variety=kite.VARIETY_REGULAR,
                order_type=kite.ORDER_TYPE_MARKET,
                product=kite.PRODUCT_MIS
            )
        except Exception as e:
            yield sse_message(f"Order Placement Failed: {str(e)}", status="done", pnl=0)
            return

        yield sse_message(f"BUY order placed! ID: {buy_order_id}")
        await asyncio.sleep(1)

        # Get average price
        try:
            orders = kite.orders()
            buy_order = next((o for o in reversed(orders) if o['order_id'] == buy_order_id), None)
            avg_price = buy_order['average_price'] if buy_order and buy_order.get('average_price') else kite.quote(tsymbol)[tsymbol]['last_price']
        except Exception:
            avg_price = kite.quote(tsymbol)[tsymbol]['last_price']

        yield sse_message(f"Buy Order executed at approx: {avg_price}")
        await asyncio.sleep(1)

        # Place Target Limit Order
        target_price = round(avg_price * 1.05, 1) # 5% target
        yield sse_message(f"Placing SELL Limit Target order at: {target_price}")
        
        try:
            sell_order_id = kite.place_order(
                tradingsymbol=tsymbol,
                exchange=kite.EXCHANGE_NFO,
                transaction_type=kite.TRANSACTION_TYPE_SELL,
                quantity=650,
                price=target_price,
                variety=kite.VARIETY_REGULAR,
                order_type=kite.ORDER_TYPE_LIMIT,
                product=kite.PRODUCT_MIS
            )
        except Exception as e:
             yield sse_message(f"Failed to place Target order: {str(e)}", status="done", pnl=0)
             return

        # 60 Second Wait Loop
        t = 0
        target_hit = False
        target_exec_price = 0
        
        while t < 60:
            try:
                orders = kite.orders()
                target_order = next((o for o in reversed(orders) if o['order_id'] == sell_order_id), None)
                
                if target_order and target_order['status'] == 'COMPLETE':
                    target_exec_price = target_order['average_price']
                    target_hit = True
                    break
            except Exception:
                pass
                
            yield sse_message(f"[{t}/60s] Waiting for target to execute...")
            await asyncio.sleep(1)
            t += 1

        if target_hit:
            pnl_amount = (target_exec_price - avg_price) * 650
            yield sse_message(f"🎯 Target hit at {target_exec_price}! Realised PnL: ₹{pnl_amount:.2f}")
            record_trade({"type": "Target", "symbol": tsymbol, "direction": direction, "entry": avg_price, "exit": target_exec_price, "pnl": pnl_amount})
            yield sse_message("Trade iteration completed successfully.", status="done", pnl=pnl_amount)
        else:
            yield sse_message("⏱️ 60s elapsed. Fetching latest order to hit Stop Loss...")
            try:
                # Robust Order ID Retrieval: Find the current OPEN sell order for this symbol
                orders = kite.orders()
                active_sell_order = next((o for o in reversed(orders) if o['tradingsymbol'] == tsymbol.split(':')[-1] and o['transaction_type'] == 'SELL' and o['status'] in ['OPEN', 'TRIGGER PENDING']), None)
                
                if not active_sell_order:
                    yield sse_message("Could not find an open sell order to modify. Attempting manual market exit...")
                    # Fallback: Just place a fresh market sell
                    exit_order_id = kite.place_order(
                        tradingsymbol=tsymbol.split(':')[-1],
                        exchange=kite.EXCHANGE_NFO,
                        transaction_type=kite.TRANSACTION_TYPE_SELL,
                        quantity=650,
                        variety=kite.VARIETY_REGULAR,
                        order_type=kite.ORDER_TYPE_MARKET,
                        product=kite.PRODUCT_MIS
                    )
                else:
                    exit_order_id = active_sell_order['order_id']
                    yield sse_message(f"Modifying Order {exit_order_id} to Market...")
                    kite.modify_order(
                        variety=kite.VARIETY_REGULAR,
                        order_id=exit_order_id,
                        order_type=kite.ORDER_TYPE_MARKET
                    )
                
                await asyncio.sleep(1)
                
                # Verify SL exit
                orders = kite.orders()
                sl_order = next((o for o in reversed(orders) if o['order_id'] == exit_order_id), None)
                sl_price = sl_order['average_price'] if sl_order and sl_order.get('average_price') else kite.quote(tsymbol)[tsymbol]['last_price']
                
                pnl_amount = (sl_price - avg_price) * 650
                yield sse_message(f"🛑 Stop Loss executed at {sl_price}. Realised PnL: ₹{pnl_amount:.2f}")
                record_trade({"type": "Time_SL", "symbol": tsymbol, "direction": direction, "entry": avg_price, "exit": sl_price, "pnl": pnl_amount})
                yield sse_message("Trade iteration completed via SL.", status="done", pnl=pnl_amount)

            except Exception as e:
                yield sse_message(f"Failed to execute SL: {str(e)}", status="done", pnl=0)

    except Exception as e:
        yield sse_message(f"Fatal Error in execution loop: {str(e)}", status="error", pnl=0)
