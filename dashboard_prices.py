from config import get_kite_session
import pandas as pd
from datetime import datetime

def fetch_upcoming_expiries():
    """
    Fetches the next 3 weekly/monthly expiries for NIFTY from Kite API.
    Returns a list of dictionaries with 'display' and 'value' (Kite format).
    """
    try:
        kite = get_kite_session()
        instruments = kite.instruments("NFO")
        df = pd.DataFrame(instruments)
        
        # Filter for NIFTY options
        nifty_options = df[(df['name'] == 'NIFTY') & (df['segment'] == 'NFO-OPT')]
        
        # Get unique expiries and sort them
        all_expiries = sorted(nifty_options['expiry'].unique())
        expiry_dates = [e for e in all_expiries if e]
        
        results = []
        for e in expiry_dates[:3]:
            # Convert string date to object
            date_obj = e if isinstance(e, datetime) else datetime.strptime(str(e), "%Y-%m-%d").date()
            
            # Find a sample symbol to extract the Kite prefix (NIFTY26505 etc)
            # Kite symbols are like NIFTY2650518500CE
            # We want the prefix NIFTY26505
            sample_symbols = nifty_options[nifty_options['expiry'] == e]['tradingsymbol'].tolist()
            if not sample_symbols:
                continue
                
            # Extract prefix by removing strike and CE/PE (last 7 characters usually, e.g. 18500CE)
            # Actually better to just take the first few chars until the strike starts.
            # But Kite prefix for weekly is NIFTY + YY + M + DD
            # For monthly is NIFTY + YY + MMM
            
            # Let's find the shortest symbol for this expiry as it likely has the prefix clearly
            sample = min(sample_symbols, key=len)
            # Prefix is usually everything before the strike (which is numeric)
            # Example: NIFTY2650519000CE -> Prefix: NIFTY26505
            # We want just '26505'
            prefix = sample[:-7] if len(sample) > 7 else sample
            date_code = prefix.replace("NIFTY", "")
            
            results.append({
                "display": date_obj.strftime("%d %b %Y"),
                "value": date_code
            })
            
        return results
    except Exception as e:
        print(f"Error fetching expiries: {e}")
        return []

def get_market_overview(expiry="26MAY"):
    """
    Fetches the current spot price, future price, and tracking options range.
    Uses the provided expiry (e.g. '26MAY') to build the symbols and calculates
    strike range (1000 below to 1000 above spot).
    """
    kite = get_kite_session()
    
    spot_symbol = "NSE:NIFTY 50"
    fut_symbol = f"NFO:NIFTY{expiry}FUT"
    
    try:
        quote = kite.quote([spot_symbol, fut_symbol])
        
        spot_price = quote[spot_symbol]['last_price']
        fut_price = quote[fut_symbol]['last_price']
        
        rounded_spot = round(spot_price / 100) * 100
        
        lower_bound = rounded_spot - 1000
        upper_bound = rounded_spot + 1000
        
        strikes = list(range(lower_bound, upper_bound + 100, 100))
        
        return {
            "spot_price": spot_price,
            "fut_price": fut_price,
            "rounded_spot": rounded_spot,
            "strikes": strikes,
            "lower_range": lower_bound,
            "upper_range": upper_bound
        }
    except Exception as e:
        raise Exception(f"Failed to fetch market data from Kite: {str(e)}")
