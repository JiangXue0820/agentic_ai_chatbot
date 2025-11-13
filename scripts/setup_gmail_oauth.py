#!/usr/bin/env python3
"""
Gmail OAuth Setup - Interactive wizard
Run this after setting GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in .env
"""

import os
import sys
import webbrowser
from pathlib import Path
from urllib.parse import urlparse, parse_qs

sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    import requests
except ImportError:
    print("❌ Install requests: pip install requests")
    sys.exit(1)

# Check .env file
def check_env_config():
    """Check if Google credentials are configured."""
    try:
        from dotenv import load_dotenv
        env_path = Path(__file__).parent.parent / ".env"
        load_dotenv(env_path)
    except ImportError:
        print("❌ Install python-dotenv: pip install python-dotenv")
        sys.exit(1)
    
    client_id = os.getenv("GOOGLE_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
    
    if not client_id or not client_secret:
        print("❌ GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET not found in .env")
        print("\n📝 Quick setup:")
        print("1. Get credentials from: https://console.cloud.google.com/")
        print("   - Create project → Enable Gmail API → Create OAuth 2.0 Client ID")
        print("   - Add redirect URI: http://127.0.0.1:8000/gmail/oauth/callback")
        print("2. Add to .env:")
        print("   GOOGLE_CLIENT_ID=your_id")
        print("   GOOGLE_CLIENT_SECRET=your_secret")
        return False
    return True

API_BASE = os.getenv("API_BASE", "http://127.0.0.1:8000")
REDIRECT_URI = f"{API_BASE}/gmail/oauth/callback"

def main():
    print("🔐 Gmail OAuth Setup\n")
    
    # Check config
    if not check_env_config():
        sys.exit(1)
    
    # Check server
    print("1. Checking server...")
    try:
        requests.get(f"{API_BASE}/health", timeout=2)
        print("   ✓ Server is running")
    except:
        print(f"   ❌ Server not running at {API_BASE}")
        print("   Start it: uvicorn app.main:app --reload")
        sys.exit(1)
    
    # Check if already authorized
    print("2. Checking authorization status...")
    try:
        r = requests.get(f"{API_BASE}/gmail/oauth/status", timeout=2)
        if r.json().get("authorized"):
            print("   ✓ Already authorized!")
            return
        print("   ⚠ Not authorized yet")
    except:
        print("   ⚠ Could not check status")
    
    # Get auth URL
    print("3. Getting authorization URL...")
    try:
        r = requests.get(f"{API_BASE}/gmail/oauth/start", 
                        params={"redirect_uri": REDIRECT_URI}, timeout=5)
        auth_url = r.json()["authorization_url"]
        print("   ✓ URL generated")
    except Exception as e:
        print(f"   ❌ Error: {e}")
        print("   Make sure GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET are correct")
        sys.exit(1)
    
    # Open browser
    print("4. Opening browser...")
    try:
        webbrowser.open(auth_url)
        print("   ✓ Browser opened")
    except:
        print(f"   ⚠ Please open manually: {auth_url[:80]}...")
    
    # Get code
    print("\n5. After authorizing in browser, paste the callback URL or code:")
    code = input("   > ").strip()
    
    if code.startswith("http"):
        parsed = urlparse(code)
        params = parse_qs(parsed.query)
        code = params.get("code", [None])[0]
        if not code:
            print("   ❌ Could not extract code from URL")
            sys.exit(1)
    
    if not code:
        print("   ❌ No code provided")
        sys.exit(1)
    
    # Complete
    print("6. Completing authorization...")
    try:
        r = requests.get(f"{API_BASE}/gmail/oauth/callback",
                        params={"code": code, "redirect_uri": REDIRECT_URI}, timeout=5)
        r.raise_for_status()
        print("   ✓ Authorization complete!")
        
        # Verify
        r = requests.get(f"{API_BASE}/gmail/oauth/status", timeout=2)
        if r.json().get("authorized"):
            print("\n✅ Gmail OAuth setup successful! You can now use Gmail features.")
        else:
            print("\n⚠ Authorization may not have completed correctly")
    except Exception as e:
        print(f"   ❌ Failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n⚠ Cancelled")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

