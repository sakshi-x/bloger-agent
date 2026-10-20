#!/usr/bin/env python3
"""
get_refresh_token.py - One-time helper to get Google OAuth refresh token.

Run this ONCE on your local machine to get a refresh token.
Then add the refresh token as GOOGLE_REFRESH_TOKEN in GitHub Secrets.

Prerequisites:
1. Go to Google Cloud Console (https://console.cloud.google.com/)
2. Create a project or select existing
3. Enable Blogger API v3
4. Create OAuth 2.0 Client ID (Desktop app)
5. Download credentials JSON as 'credentials.json' in this folder
6. Add your email as a test user in OAuth consent screen

Usage:
    pip install -r requirements.txt
    python get_refresh_token.py
"""

import os
import json
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials

# Scopes needed for Blogger API
SCOPES = ["https://www.googleapis.com/auth/blogger"]

CREDENTIALS_FILE = "credentials.json"
TOKEN_FILE = "token.json"


def main():
    print("=" * 60)
    print("Google OAuth Refresh Token Generator")
    print("=" * 60)

    # Check for credentials.json
    if not os.path.exists(CREDENTIALS_FILE):
        print(f"\nERROR: {CREDENTIALS_FILE} not found!")
        print("\nSteps to get credentials.json:")
        print("1. Go to https://console.cloud.google.com/")
        print("2. Create/select a project")
        print("3. Enable 'Blogger API v3' (APIs & Services > Library)")
        print("4. Go to APIs & Services > Credentials")
        print("5. Click 'Create Credentials' > 'OAuth client ID'")
        print("6. Select 'Desktop app' as application type")
        print("7. Download the JSON and save as 'credentials.json' here")
        print("8. In OAuth consent screen, add your email as test user")
        return

    # Load credentials
    with open(CREDENTIALS_FILE, "r") as f:
        creds_data = json.load(f)

    client_id = creds_data.get("installed", {}).get("client_id")
    client_secret = creds_data.get("installed", {}).get("client_secret")

    if not client_id or not client_secret:
        print("ERROR: Invalid credentials.json format")
        return

    print(f"\nClient ID: {client_id}")
    print(f"Client Secret: {client_secret[:10]}...")

    # Run OAuth flow
    print("\nStarting OAuth flow...")
    print("A browser window will open. Sign in with your Google account.")
    print("Grant permission to access Blogger.")

    flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
    creds = flow.run_local_server(port=0)

    # Save token
    token_data = {
        "token": creds.token,
        "refresh_token": creds.refresh_token,
        "token_uri": creds.token_uri,
        "client_id": creds.client_id,
        "client_secret": creds.client_secret,
        "scopes": creds.scopes
    }

    with open(TOKEN_FILE, "w") as f:
        json.dump(token_data, f, indent=2)

    print("\n" + "=" * 60)
    print("SUCCESS! Refresh token obtained.")
    print("=" * 60)
    print(f"\nRefresh Token: {creds.refresh_token}")
    print(f"\nSave these as GitHub Actions Secrets:")
    print(f"  GOOGLE_CLIENT_ID: {client_id}")
    print(f"  GOOGLE_CLIENT_SECRET: {client_secret}")
    print(f"  GOOGLE_REFRESH_TOKEN: {creds.refresh_token}")
    print(f"\nToken also saved to {TOKEN_FILE}")
    print("\nIMPORTANT: Keep these secrets safe! Never commit them.")


if __name__ == "__main__":
    main()