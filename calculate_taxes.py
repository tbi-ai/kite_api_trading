import pandas as pd

df = pd.read_csv('backtest_results_2026_07_01.csv')

total_brokerage = 0
total_stt = 0
total_exchange_txn = 0
total_sebi = 0
total_stamp = 0
total_gst = 0
gross_pnl = 0

for index, row in df.iterrows():
    qty = row['qty']
    buy_price = row['entry_price']
    sell_price = row['exit_price']
    
    buy_premium = buy_price * qty
    sell_premium = sell_price * qty
    total_premium = buy_premium + sell_premium
    
    brokerage = 40
    stt = sell_premium * 0.0015
    exchange_txn = total_premium * 0.00053
    sebi = total_premium * 0.0000005
    stamp = buy_premium * 0.00003
    gst = (brokerage + exchange_txn) * 0.18
    
    total_brokerage += brokerage
    total_stt += stt
    total_exchange_txn += exchange_txn
    total_sebi += sebi
    total_stamp += stamp
    total_gst += gst
    
    gross_pnl += (sell_premium - buy_premium)

total_charges = total_brokerage + total_stt + total_exchange_txn + total_sebi + total_stamp + total_gst
net_pnl = gross_pnl - total_charges

print("=== TAX & BROKERAGE ESTIMATE ===")
print(f"Total Trades: {len(df)}")
print(f"Gross PnL: ₹{gross_pnl:,.2f}")
print("-" * 32)
print(f"Brokerage: ₹{total_brokerage:,.2f}")
print(f"STT: ₹{total_stt:,.2f}")
print(f"Exchange Txn: ₹{total_exchange_txn:,.2f}")
print(f"GST: ₹{total_gst:,.2f}")
print(f"SEBI Charges: ₹{total_sebi:,.2f}")
print(f"Stamp Duty: ₹{total_stamp:,.2f}")
print("-" * 32)
print(f"Total Charges: ₹{total_charges:,.2f}")
print(f"Net PnL: ₹{net_pnl:,.2f}")
print("================================")
