from config import get_kite_session
import pandas as pd
from datetime import datetime

def get_upcoming_expiries():
    try:
        kite = get_kite_session()
        instruments = kite.instruments("NFO")
        df = pd.DataFrame(instruments)
        
        # Filter for NIFTY weekly/monthly options
        nifty_options = df[(df['name'] == 'NIFTY') & (df['segment'] == 'NFO-OPT')]
        
        # Get unique expiries
        expiries = sorted(nifty_options['expiry'].unique())
        
        # Convert to datetime for sorting
        expiry_dates = [e for e in expiries if e]
        
        print(f"Total NIFTY expiries found: {len(expiry_dates)}")
        for e in expiry_dates[:5]:
            # Find the tradingsymbol for a strike to see the format
            sample = nifty_options[nifty_options['expiry'] == e].iloc[0]
            print(f"Expiry: {e}, Sample Symbol: {sample['tradingsymbol']}")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    get_upcoming_expiries()
