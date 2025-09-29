#!/usr/bin/env python3
"""
Gmail Token Setup Script
Generates Gmail API token for headless containers
"""

import json
import os
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

def setup_gmail_token():
    """Set up Gmail API token."""
    credentials_file = 'gmail_credentials.json'
    token_file = 'gmail_token.json'
    
    if not os.path.exists(credentials_file):
        print(f"Error: {credentials_file} not found!")
        print("Please download your Gmail API credentials file from Google Cloud Console")
        return False
    
    try:
        flow = InstalledAppFlow.from_client_secrets_file(credentials_file, SCOPES)

        # Try browser flow first (will typically return a refresh token on first consent)
        try:
            # Note: Some versions of google-auth-oauthlib accept extra kwargs here and forward
            # them to authorization_url. If unsupported, they will be ignored.
            creds = flow.run_local_server(port=8080)
            print("✅ Browser authentication successful!")
            # If no refresh_token returned, immediately fall back to manual flow requesting offline access
            if not getattr(creds, 'refresh_token', None):
                print("⚠️ No refresh_token returned via browser flow. Falling back to manual flow for offline access…")
                # Recreate flow to clear any cached params
                flow = InstalledAppFlow.from_client_secrets_file(credentials_file, SCOPES)
                auth_url, _ = flow.authorization_url(
                    access_type='offline',
                    prompt='consent',
                    include_granted_scopes='true'
                )
                print(f"\nAuthorization URL:\n{auth_url}\n")
                auth_code = input("Enter the authorization code: ").strip()
                flow.fetch_token(code=auth_code)
                creds = flow.credentials
                print("✅ Manual authentication successful (offline)!\n")
        except Exception as e:
            print(f"Browser authentication failed: {e}")
            print("\n🔗 Manual authentication required:")
            print("1. Copy the URL below and open it in your browser")
            print("2. Complete the OAuth flow")
            print("3. Copy the authorization code and paste it here")

            # Build authorization URL requesting offline access and explicit consent
            auth_url, _ = flow.authorization_url(
                access_type='offline',
                prompt='consent',
                include_granted_scopes='true'
            )
            print(f"\nAuthorization URL:\n{auth_url}\n")

            # Get authorization code from user
            auth_code = input("Enter the authorization code: ").strip()

            # Exchange code for token
            flow.fetch_token(code=auth_code)
            creds = flow.credentials
            print("✅ Manual authentication successful!")
        
        # Save the token
        with open(token_file, 'w') as token:
            token.write(creds.to_json())
        
        print(f"✅ Token saved to {token_file}")
        print("You can now copy this file to your container!")
        print("\nℹ️ Important: To avoid 7-day refresh token expiry, set your OAuth consent screen status to 'In production' in Google Cloud Console.")
        return True
        
    except Exception as e:
        print(f"❌ Error setting up Gmail token: {e}")
        return False

if __name__ == "__main__":
    print("Gmail Token Setup")
    print("=================")
    setup_gmail_token()
