import sys
sys.path.append("/Users/aple/Documents/Trading Project/V3/kite_api_trading")
from config import get_kite_session, get_current_expiry
kite = get_kite_session()
sym = "NFO:NIFTY2670724200CE"
try:
    q = kite.quote(sym)
    print(q)
except Exception as e:
    print("Quote failed:", e)

from datetime import datetime, timedelta
target = datetime.now()
target = target.replace(hour=9, minute=20, second=0)
try:
    data = kite.historical_data(
        q[sym]['instrument_token'],
        target.strftime("%Y-%m-%d %H:%M:%S"),
        (target + timedelta(minutes=5)).strftime("%Y-%m-%d %H:%M:%S"),
        'second'
    )
    print("Data length:", len(data))
except Exception as e:
    print("Hist failed:", e)
