from kiteconnect import KiteConnect
import os
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("KITE_API_KEY")
access_token = os.getenv("KITE_ACCESS_TOKEN")

kite = KiteConnect(api_key=api_key)
kite.set_access_token(access_token)

try:
    profile = kite.profile()
    print("Token is valid! User:", profile.get("user_name"))
except Exception as e:
    print("Token is invalid or expired. Error:", e)
