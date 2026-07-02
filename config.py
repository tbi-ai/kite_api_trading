import os
import json
from kiteconnect import KiteConnect
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

API_KEY = os.getenv("API_KEY", "")
API_SECRET = os.getenv("API_SECRET", "")

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

def set_current_expiry(expiry_val):
    """Saves the selected expiry globally in credentials.json."""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    credentials_path = os.path.join(current_dir, "credentials.json")
    if os.path.exists(credentials_path):
        with open(credentials_path, "r") as f:
            data = json.load(f)
        data["selected_expiry"] = expiry_val
        with open(credentials_path, "w") as f:
            json.dump(data, f)

def get_current_expiry():
    """Fetches the globally selected expiry from credentials.json."""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    credentials_path = os.path.join(current_dir, "credentials.json")
    if os.path.exists(credentials_path):
        with open(credentials_path, "r") as f:
            data = json.load(f)
            return data.get("selected_expiry", "26MAY")
    return "26MAY"
