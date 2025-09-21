import os
import json
import requests
import pandas as pd
from datetime import datetime, timedelta
from fastapi import FastAPI
from fastapi.responses import RedirectResponse, JSONResponse
from dotenv import load_dotenv

load_dotenv()

# Dexcom API settings
CLIENT_ID = os.getenv("DEXCOM_CLIENT_ID")
CLIENT_SECRET = os.getenv("DEXCOM_CLIENT_SECRET")
REDIRECT_URI = os.getenv("DEXCOM_REDIRECT_URI")

DEXCOM_AUTH_URL = "https://api.dexcom.com/v2/oauth2/login"
DEXCOM_TOKEN_URL = "https://api.dexcom.com/v2/oauth2/token"
DEXCOM_EGVS_URL = "https://api.dexcom.com/v2/users/self/egvs"

# Local storage
TOKENS = {}
TOKEN_FILE = "tokens.json"
CSV_FILE = "dexcom_glucose_last30days.csv"

# --- Helpers for token persistence ---

def save_tokens(tokens: dict):
    """Save tokens to file and memory"""
    with open(TOKEN_FILE, "w") as f:
        json.dump(tokens, f)
    TOKENS.update(tokens)

def load_tokens():
    """Load tokens from file if available"""
    global TOKENS
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, "r") as f:
            TOKENS.update(json.load(f))

load_tokens()

def refresh_access_token():
    """Refresh access token using refresh_token"""
    if "refresh_token" not in TOKENS:
        return None

    data = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "refresh_token": TOKENS["refresh_token"],
        "grant_type": "refresh_token",
        "redirect_uri": REDIRECT_URI,
    }
    r = requests.post(DEXCOM_TOKEN_URL, data=data)

    if r.status_code != 200:
        print("⚠️ Token refresh failed:", r.text)
        return None

    new_tokens = r.json()
    save_tokens(new_tokens)
    print("✅ Access token refreshed")
    return new_tokens["access_token"]

# --- FastAPI app ---

app = FastAPI()

@app.get("/")
def home():
    return {"message": "Dexcom OAuth + CSV Demo", "endpoints": ["/login", "/callback", "/fetch-egvs"]}

@app.get("/login")
def login():
    """Redirect user to Dexcom OAuth login"""
    url = (
        f"{DEXCOM_AUTH_URL}"
        f"?client_id={CLIENT_ID}"
        f"&redirect_uri={REDIRECT_URI}"
        f"&response_type=code"
        f"&scope=offline_access"
    )
    return RedirectResponse(url)

@app.get("/callback")
def callback(code: str):
    """Exchange authorization code for tokens"""
    data = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": REDIRECT_URI,
    }
    r = requests.post(DEXCOM_TOKEN_URL, data=data)

    if r.status_code != 200:
        return JSONResponse({"error": r.text}, status_code=r.status_code)

    tokens = r.json()
    save_tokens(tokens)
    return {"message": "Tokens received and saved!", "tokens": tokens}

@app.get("/fetch-egvs")
def fetch_egvs():
    """Fetch glucose data for last 30 days and save as CSV"""
    access_token = TOKENS.get("access_token")

    # Refresh if missing
    if not access_token:
        access_token = refresh_access_token()
        if not access_token:
            return {"error": "No valid tokens. Please login first via /login"}

    end = datetime.utcnow()
    start = (end - timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%S")
    end_str = end.strftime("%Y-%m-%dT%H:%M:%S")

    params = {
    "startDate": start,
    "endDate": end_str
}
    headers = {"Authorization": f"Bearer {access_token}"}
    r = requests.get(DEXCOM_EGVS_URL, headers=headers, params=params)

    # Handle expired token
    if r.status_code == 401:
        access_token = refresh_access_token()
        if not access_token:
            return {"error": "Failed to refresh token. Login again via /login"}
        headers = {"Authorization": f"Bearer {access_token}"}
        r = requests.get(DEXCOM_EGVS_URL, headers=headers, params=params)

    if r.status_code != 200:
        return {"error": r.text}

    data = r.json().get("egvs", [])
    if not data:
        return {"message": "No data returned from Dexcom."}

    df = pd.DataFrame(data)
    df.to_csv(CSV_FILE, index=False)

    return {
        "message": f"Saved {len(df)} records to {CSV_FILE}",
        "file": CSV_FILE
    }
