#!/usr/bin/env python3
"""
Helper script to encode Google Sheets credentials for deployment.
Run this script to convert your credentials.json to base64 for environment variables.
"""

import base64
import sys
import os

def encode_credentials():
    """Encode credentials.json to base64 for environment variables"""
    
    # Check if credentials.json exists
    if not os.path.exists("credentials.json"):
        print("❌ Error: credentials.json not found in current directory")
        print("Please place your Google Sheets credentials.json file in this directory")
        sys.exit(1)
    
    try:
        # Read and encode the credentials file
        with open("credentials.json", "rb") as f:
            credentials_content = f.read()
        
        # Encode to base64
        encoded_credentials = base64.b64encode(credentials_content).decode('utf-8')
        
        print("✅ Successfully encoded credentials.json")
        print("\n📋 Copy this to your .env file or deployment platform:")
        print("=" * 50)
        print(f"GOOGLE_CREDENTIALS={encoded_credentials}")
        print("=" * 50)
        
        print("\n💡 Instructions:")
        print("1. Add this to your .env file for local development")
        print("2. Add as a secret in your deployment platform")
        print("3. For GitHub Actions, add as a repository secret")
        
    except Exception as e:
        print(f"❌ Error encoding credentials: {e}")
        sys.exit(1)

if __name__ == "__main__":
    encode_credentials()
