import os
import json
from kiteconnect import KiteConnect

# Centralized Kite API credentials
API_KEY = "wthlsr41oawqdeoz"
API_SECRET = "agvml7dbwicte27ijiswgpdqnlww2ho0"

def get_kite_session():
    """
    Reads the access_token from credentials.json and initializes
    the KiteConnect session.
    """
    current_dir = os.path.dirname(os.path.abspath(__file__))
    credentials_path = os.path.join(current_dir, "credentials.json")
    
    if not os.path.exists(credentials_path):
        raise FileNotFoundError(
            "credentials.json not found. Please log in through the UI first."
        )
        
    try:
        with open(credentials_path, "r") as f:
            creds = json.load(f)
            access_token = creds.get("access_token")
    except Exception as e:
        raise ValueError(f"Failed to read credentials.json: {str(e)}")
        
    if not access_token:
        raise ValueError("access_token missing in credentials.json. Please login again.")
        
    # Initialize Kite Connect and set the access token
    kite = KiteConnect(api_key=API_KEY)
    kite.set_access_token(access_token)
    
    return kite
