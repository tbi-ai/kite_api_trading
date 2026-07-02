from config import get_kite_session, get_current_expiry
from datetime import datetime, timedelta
import pandas as pd

kite = get_kite_session()
quote = kite.quote("NSE:NIFTY 50")
inst_token = quote["NSE:NIFTY 50"]['instrument_token']

end = datetime.now()
start = end.replace(hour=9, minute=15, second=0, microsecond=0)

try:
    data = kite.historical_data(inst_token, start.strftime("%Y-%m-%d %H:%M:%S"), end.strftime("%Y-%m-%d %H:%M:%S"), 'second')
    print("Second data points:", len(data))
    if len(data) > 0:
        print(data[0])
except Exception as e:
    print("Error:", e)
