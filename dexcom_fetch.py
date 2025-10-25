import os
import requests
import pandas as pd
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

# Dexcom API credentials
CLIENT_ID = os.getenv("DEXCOM_CLIENT_ID")
CLIENT_SECRET = os.getenv("DEXCOM_CLIENT_SECRET")
REDIRECT_URI = os.getenv("DEXCOM_REDIRECT_URI")
ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")
REFRESH_TOKEN = os.getenv("REFRESH_TOKEN")

DEXCOM_BASE_URL = "https://api.dexcom.com/v2"  # Production endpoint
CSV_FILE = "glucose_data.csv"


def refresh_access_token():
    """Refresh Dexcom access token using refresh token"""
    url = f"{DEXCOM_BASE_URL}/oauth2/token"
    data = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "refresh_token": REFRESH_TOKEN,
        "grant_type": "refresh_token",
        "redirect_uri": REDIRECT_URI,
    }
    r = requests.post(url, data=data)
    if r.status_code == 200:
        tokens = r.json()
        print("✅ Access token refreshed")
        return tokens["access_token"], tokens["refresh_token"]
    else:
        raise Exception(f"Failed to refresh token: {r.text}")


def fetch_glucose_data(access_token, hours=6):
    """Fetch glucose readings from Dexcom API"""
    now = datetime.utcnow()
    start = (now - timedelta(hours=hours)).isoformat() + "Z"
    end = now.isoformat() + "Z"

    url = f"{DEXCOM_BASE_URL}/users/self/egvs?startDate={start}&endDate={end}"
    headers = {"Authorization": f"Bearer {access_token}"}
    r = requests.get(url, headers=headers)

    if r.status_code == 200:
        return r.json().get("egvs", [])
    else:
        raise Exception(f"Failed to fetch data: {r.text}")


def save_to_csv(data):
    """Save Dexcom data to local CSV"""
    if not data:
        print("⚠️ No new data to save.")
        return

    df = pd.DataFrame(data)
    if os.path.exists(CSV_FILE):
        df.to_csv(CSV_FILE, mode="a", header=False, index=False)
    else:
        df.to_csv(CSV_FILE, index=False)

    print(f"✅ Saved {len(data)} records to {CSV_FILE}")


if __name__ == "__main__":
    try:
        # refresh tokens before fetching
        ACCESS_TOKEN, REFRESH_TOKEN = refresh_access_token()

        # fetch last 6 hours of data
        records = fetch_glucose_data(ACCESS_TOKEN, hours=6)

        # store locally
        save_to_csv(records)

    except Exception as e:
        print(f"❌ Error: {e}")
