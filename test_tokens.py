import os
import requests
from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse, JSONResponse
from dotenv import load_dotenv

load_dotenv()

CLIENT_ID = os.getenv("DEXCOM_CLIENT_ID")
CLIENT_SECRET = os.getenv("DEXCOM_CLIENT_SECRET")

# Production Dexcom API endpoints only
BASE_URL = "https://api.dexcom.com/v2/oauth2"
REDIRECT_URI = os.getenv("DEXCOM_REDIRECT_URI", "https://localhost:8080/callback")

DEXCOM_AUTH_URL = f"{BASE_URL}/login"
DEXCOM_TOKEN_URL = f"{BASE_URL}/token"

# In-memory token store (demo only)
TOKENS = {}

app = FastAPI()


@app.get("/")
def home():
    return {
        "message": "Dexcom OAuth Demo - Production Mode",
        "environment": "production",
        "auth_url": DEXCOM_AUTH_URL,
        "redirect_uri": REDIRECT_URI,
        "endpoints": ["/login", "/callback", "/refresh"],
    }


@app.get("/login")
def login():
    """Redirect user to Dexcom OAuth login"""
    url = (
        f"{DEXCOM_AUTH_URL}"
        f"?client_id={CLIENT_ID}"
        f"&redirect_uri={REDIRECT_URI}"
        f"&response_type=code"
        f"&scope=offline_access egv calibration device statistics event"
    )
    return RedirectResponse(url)


@app.get("/callback")
def callback(request: Request, code: str):
    """Exchange code for tokens"""
    data = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": REDIRECT_URI,
    }
    r = requests.post(DEXCOM_TOKEN_URL, data=data)

    print("🔎 Callback response:", r.status_code, r.text)

    if r.status_code != 200:
        return JSONResponse({"error": r.text}, status_code=r.status_code)

    tokens = r.json()
    TOKENS.update(tokens)
    return {"message": "Tokens received!", "tokens": tokens}


@app.get("/refresh")
def refresh():
    """Refresh access_token using refresh_token"""
    if "refresh_token" not in TOKENS:
        return {"error": "No refresh_token found. Do /login first."}

    data = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "refresh_token": TOKENS["refresh_token"],
        "grant_type": "refresh_token",
        "redirect_uri": REDIRECT_URI,
    }
    r = requests.post(DEXCOM_TOKEN_URL, data=data)

    print("🔄 Refresh response:", r.status_code, r.text)

    if r.status_code != 200:
        return JSONResponse({"error": r.text}, status_code=r.status_code)

    tokens = r.json()
    TOKENS.update(tokens)
    return {"message": "Access token refreshed!", "tokens": tokens}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8080)
