"""
🎬 YouTube OAuth Token Generator
Yeh script client_secrets.json se OAuth flow run karke
token.json file banayegi jisme access_token + refresh_token hoga.

Usage: python get_youtube_token.py
"""

import os
import json
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

# YouTube API scopes (jitne chahiye utne add karo)
SCOPES = [
    'https://www.googleapis.com/auth/youtube.upload',
    'https://www.googleapis.com/auth/youtube.force-ssl',
    'https://www.googleapis.com/auth/youtube.readonly',
]

CLIENT_SECRETS_FILE = "client_secrets.json"  # Google se download ki hui file
TOKEN_FILE = "sanatani_youtube_token.json"   # Yeh file generate hogi


def get_authenticated_service():
    """OAuth flow run karke token return karta hai"""
    creds = None

    # Agar pehle se token file hai toh use karo
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
        print(f"[INFO] Existing token found: {TOKEN_FILE}")

    # Agar token valid nahi hai ya nahi hai toh naya generate karo
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("[INFO] Token expired, refreshing...")
            creds.refresh(Request())
        else:
            print("[INFO] Starting OAuth flow... Browser khulega.")
            flow = InstalledAppFlow.from_client_secrets_file(
                CLIENT_SECRETS_FILE, SCOPES)
            # run_local_server port 8080 pe browser open karega
            creds = flow.run_local_server(port=8080)
            print("[OK] Login successful! Token mil gaya.")

        # Token ko file me save karo
        with open(TOKEN_FILE, 'w') as token:
            token.write(creds.to_json())
        print(f"[OK] Token saved: {TOKEN_FILE}")

    return creds


def print_token_info(creds):
    """Token ki details print karta hai"""
    print("\n" + "=" * 60)
    print("YOUTUBE TOKEN SUCCESSFULLY GENERATED!")
    print("=" * 60)
    print(f"File: {os.path.abspath(TOKEN_FILE)}")
    print(f"Access Token: {creds.token[:30]}...")
    print(f"Expires At: {creds.expiry}")
    print(f"Refresh Token: {'Available' if creds.refresh_token else 'Not available'}")
    print(f"Scopes: {len(creds.scopes)} scopes granted")
    print("=" * 60)

    # Full token details dikhao
    token_data = {
        "access_token": creds.token,
        "refresh_token": creds.refresh_token,
        "token_uri": creds.token_uri,
        "client_id": creds.client_id,
        "client_secret": creds.client_secret,
        "scopes": creds.scopes,
        "expiry": str(creds.expiry) if creds.expiry else None
    }

    print("\nFull Token Data:")
    print(json.dumps(token_data, indent=2))


if __name__ == "__main__":
    print("Sanatan YouTube Token Generator")
    print("-" * 40)

    # Check karo ki client_secrets.json exist karti hai
    if not os.path.exists(CLIENT_SECRETS_FILE):
        print(f"[ERROR] {CLIENT_SECRETS_FILE} not found!")
        print("Google Cloud Console se download karo aur yahan paste karo.")
        exit(1)

    try:
        creds = get_authenticated_service()
        print_token_info(creds)
        print("\n[OK] Ab YouTube API use kar sakte ho!")
    except Exception as e:
        print(f"\n[ERROR] {e}")
        print("Tip: Check karo ki client_secrets.json sahi jagah hai.")
