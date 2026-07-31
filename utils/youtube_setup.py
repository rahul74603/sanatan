"""
📺 YouTube Setup Helper
Yeh script YouTube channel ID nikalne aur setup verify karne me madad karta hai.

Usage:
    python utils/youtube_setup.py
"""

import os
import re
import json
from pathlib import Path


def extract_channel_id_from_url(url):
    """
    YouTube URL se channel ID nikalta hai.

    Supported formats:
    - https://www.youtube.com/channel/UCxxxxxxxxxxxxx
    - https://www.youtube.com/@username
    - https://www.youtube.com/c/CustomName
    - https://www.youtube.com/user/username
    """
    url = url.strip()

    # Format 1: Direct channel ID
    match = re.search(r'youtube\.com/channel/([UC][A-Za-z0-9_-]{22})', url)
    if match:
        return match.group(1)

    # Format 2: @handle
    match = re.search(r'youtube\.com/(@[A-Za-z0-9_-]+)', url)
    if match:
        return f"@{match.group(1)}"  # API call se resolve karna padega

    # Format 3: /c/ custom URL
    match = re.search(r'youtube\.com/c/([A-Za-z0-9_-]+)', url)
    if match:
        return f"c/{match.group(1)}"  # API call se resolve karna padega

    # Format 4: /user/ old format
    match = re.search(r'youtube\.com/user/([A-Za-z0-9_-]+)', url)
    if match:
        return f"user/{match.group(1)}"  # API call se resolve karna padega

    return None


def update_env_file(key, value, env_file=".env"):
    """.env file me key=value update/add karta hai"""
    env_path = Path(env_file)

    if not env_path.exists():
        print(f"❌ {env_file} not found!")
        return False

    # Read existing content
    with open(env_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    key_found = False
    for i, line in enumerate(lines):
        # Check if key exists
        if line.strip().startswith(f"{key}=") or line.strip().startswith(f"# {key}="):
            lines[i] = f"{key}={value}\n"
            key_found = True
            break

    # Key nahi mili toh append karo
    if not key_found:
        lines.append(f"\n{key}={value}\n")

    # Write back
    with open(env_path, 'w', encoding='utf-8') as f:
        f.writelines(lines)

    print(f"✅ {key}={value} set in .env")
    return True


def check_youtube_setup():
    """YouTube setup verify karta hai"""
    print("=" * 60)
    print("📺 YOUTUBE SETUP CHECKER")
    print("=" * 60)

    # 1. .env variables check
    print("\n1️⃣  Checking .env variables...")
    env_path = Path(".env")
    if not env_path.exists():
        print("   ❌ .env file not found!")
        return False

    env_vars = {}
    with open(env_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                env_vars[key.strip()] = value.strip()

    required_keys = [
        'YOUTUBE_ENABLED',
        'YOUTUBE_CHANNEL_ID',
        'YOUTUBE_CLIENT_SECRETS_FILE',
        'YOUTUBE_TOKEN_FILE'
    ]

    for key in required_keys:
        value = env_vars.get(key, 'NOT SET')
        if value == 'NOT SET' or not value:
            print(f"   ❌ {key}: NOT SET")
        else:
            # Mask sensitive values
            if 'SECRET' in key or 'TOKEN' in key:
                display = value[:20] + "..." if len(value) > 20 else value
            else:
                display = value
            print(f"   ✅ {key}: {display}")

    # 2. Client secrets file check
    print("\n2️⃣  Checking client secrets file...")
    secrets_file = env_vars.get('YOUTUBE_CLIENT_SECRETS_FILE', 'sanatani_youtube_client_secrets.json')
    if Path(secrets_file).exists():
        print(f"   ✅ {secrets_file} found")
        try:
            with open(secrets_file, 'r') as f:
                data = json.load(f)
                if 'installed' in data or 'web' in data:
                    print(f"   ✅ Valid OAuth client config")
                else:
                    print(f"   ⚠️ Unexpected format")
        except Exception as e:
            print(f"   ⚠️ Error reading: {e}")
    else:
        print(f"   ❌ {secrets_file} NOT FOUND")
        print(f"   💡 Download from: Google Cloud Console → APIs & Services → Credentials")

    # 3. Token file check
    print("\n3️⃣  Checking token file...")
    token_file = env_vars.get('YOUTUBE_TOKEN_FILE', 'sanatani_youtube_token.json')
    if Path(token_file).exists():
        print(f"   ✅ {token_file} found")
        try:
            with open(token_file, 'r') as f:
                data = json.load(f)
                has_access = 'token' in data
                has_refresh = 'refresh_token' in data and data['refresh_token']
                print(f"   {'✅' if has_access else '❌'} Access token: {'present' if has_access else 'missing'}")
                print(f"   {'✅' if has_refresh else '⚠️ '} Refresh token: {'present' if has_refresh else 'missing'}")
                if 'scopes' in data:
                    print(f"   📋 Scopes: {len(data['scopes'])} granted")
        except Exception as e:
            print(f"   ⚠️ Error reading: {e}")
    else:
        print(f"   ❌ {token_file} NOT FOUND")
        print(f"   💡 Run: python get_youtube_token.py")

    # 4. Python packages check
    print("\n4️⃣  Checking Python packages...")
    required_packages = [
        'google.auth',
        'google_auth_oauthlib',
        'googleapiclient'
    ]
    for package in required_packages:
        try:
            __import__(package)
            print(f"   ✅ {package}: installed")
        except ImportError:
            print(f"   ❌ {package}: NOT installed")
            print(f"   💡 Run: pip install {package.replace('_', '-')}")

    # Summary
    print("\n" + "=" * 60)
    print("📊 SUMMARY")
    print("=" * 60)
    print("\nNext steps:")
    if not Path(secrets_file).exists():
        print("1. Download client_secrets.json from Google Cloud Console")
    if not Path(token_file).exists():
        print("2. Run: python get_youtube_token.py")
    if env_vars.get('YOUTUBE_CHANNEL_ID') in [None, '', 'UCxxxxxxxxxxxxxxxxxxxxx']:
        print("3. Set real YOUTUBE_CHANNEL_ID in .env")
    print("4. Run: python test_youtube_token.py")
    print()


def interactive_setup():
    """Interactive setup wizard"""
    print("\n" + "=" * 60)
    print("🛠️  YOUTUBE SETUP WIZARD")
    print("=" * 60)

    # Channel ID input
    print("\n📺 Apna YouTube Channel URL ya ID do:")
    print("   Examples:")
    print("   - https://www.youtube.com/channel/UCxxxxxxxxxxxxx")
    print("   - https://www.youtube.com/@yourchannel")
    print("   - UCxxxxxxxxxxxxxxxxxxxxx (direct ID)")

    url = input("\n👉 URL/ID: ").strip()

    if not url:
        print("❌ URL required!")
        return

    # Extract or use direct
    if url.startswith('UC') and len(url) == 24:
        channel_id = url
        print(f"✅ Direct Channel ID: {channel_id}")
    else:
        channel_id = extract_channel_id_from_url(url)
        if channel_id and channel_id.startswith('UC'):
            print(f"✅ Extracted Channel ID: {channel_id}")
        else:
            print(f"⚠️ Handle/custom URL detected: {channel_id}")
            print("💡 Best to use direct UC... ID for API")
            # For @handle, we'll save it but warn
            channel_id = url  # Save as is

    # .env me save karo
    if channel_id:
        update_env_file('YOUTUBE_CHANNEL_ID', channel_id)
        update_env_file('YOUTUBE_ENABLED', 'True')

    # Token check
    if Path('sanatani_youtube_token.json').exists():
        print("\n✅ Token file already exists")
    else:
        print("\n⚠️ Token file missing")
        run_setup = input("Generate token now? (y/n): ").strip().lower()
        if run_setup == 'y':
            print("\n🚀 Running token generator...")
            os.system('python get_youtube_token.py')

    # Final check
    print("\n🔍 Running final check...")
    check_youtube_setup()


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == 'check':
        check_youtube_setup()
    elif len(sys.argv) > 1 and sys.argv[1] == 'wizard':
        interactive_setup()
    else:
        # Default: run wizard
        interactive_setup()
