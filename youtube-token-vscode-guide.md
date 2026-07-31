# 🎬 YouTube Token Setup - VS Code + Command Line Method

Bhai, **JSON file directly run nahi hoti** Python ya Node se. JSON sirf data store karta hai. Isko chalane ke liye ek **Python script** chahiye jo JSON ko read kare aur YouTube API se baat kare.

Chalo step-by-step karte hain 👇

---

## 📋 Pre-requisites (Pehle se check karo)

1. **Python 3.10+** installed ho (tumhare paas hai - Python 3.11.1)
2. **VS Code** installed ho ✅
3. **Google Cloud Project** bana ho (YouTube Data API v3 enabled)

---

## 🚀 Step 1: VS Code me Project Open Karo

VS Code me apna folder kholo:

```bash
cd C:\Users\Rahul\Desktop\sanatannn
code .
```

---

## 📦 Step 2: Python Libraries Install Karo

VS Code me **Terminal** kholo (`` Ctrl+`  ``) aur yeh commands run karo:

```bash
# Virtual environment banao (recommended)
python -m venv venv

# Activate karo (PowerShell)
.\venv\Scripts\Activate.ps1

# Agar permission error aaye toh:
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned

# Required libraries install karo
pip install google-auth-oauthlib
pip install google-auth-httplib2
pip install google-api-python-client
```

Ya phir ek hi command me:

```bash
pip install -r requirements.txt
```

---

## 🔑 Step 3: OAuth Credentials Download Karo

1. **Google Cloud Console** kholein: [https://console.cloud.google.com/](https://console.cloud.google.com/)
2. Apna project select karo.
3. **APIs & Services → OAuth consent screen** → Setup karo:
   - User Type: **External**
   - App name: `Sanatan YouTube Uploader`
   - Support email, developer email daal do
   - **Scopes** me add karo:
     - `https://www.googleapis.com/auth/youtube.upload`
     - `https://www.googleapis.com/auth/youtube.force-ssl`
4. **APIs & Services → Credentials** → **+ Create Credentials → OAuth 2.0 Client IDs**
5. Application type: **Desktop app** select karo
6. Name: `Sanatan Desktop Client`
7. **Create** par click karo
8. **Download JSON** par click karo
9. File ka naam change karke `client_secrets.json` rakho
10. Isse apne project folder me paste karo (`C:\Users\Rahul\Desktop\sanatannn\`)

---

## 🐍 Step 4: Python Script Banao - `get_youtube_token.py`

VS Code me naya file banao: **`get_youtube_token.py`**

```python
"""
🎬 YouTube OAuth Token Generator
Yeh script client_secrets.json se OAuth flow run karke 
token.json file banayegi jisme access_token + refresh_token hoga.
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
        print(f"✅ Existing token found: {TOKEN_FILE}")
    
    # Agar token valid nahi hai ya nahi hai toh naya generate karo
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("🔄 Token expired, refreshing...")
            creds.refresh(Request())
        else:
            print("🌐 Starting OAuth flow... Browser khulega.")
            flow = InstalledAppFlow.from_client_secrets_file(
                CLIENT_SECRETS_FILE, SCOPES)
            # run_local_server port 8080 pe browser open karega
            creds = flow.run_local_server(port=8080)
            print("✅ Login successful! Token mil gaya.")
        
        # Token ko file me save karo
        with open(TOKEN_FILE, 'w') as token:
            token.write(creds.to_json())
        print(f"💾 Token saved: {TOKEN_FILE}")
    
    return creds

def print_token_info(creds):
    """Token ki details print karta hai"""
    print("\n" + "="*60)
    print("🎉 YOUTUBE TOKEN SUCCESSFULLY GENERATED!")
    print("="*60)
    print(f"📁 File: {os.path.abspath(TOKEN_FILE)}")
    print(f"🔑 Access Token: {creds.token[:30]}...")
    print(f"⏰ Expires At: {creds.expiry}")
    print(f"🔄 Refresh Token: {'Available ✅' if creds.refresh_token else 'Not available ❌'}")
    print(f"📋 Scopes: {len(creds.scopes)} scopes granted")
    print("="*60)
    
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
    
    print("\n📦 Full Token Data:")
    print(json.dumps(token_data, indent=2))

if __name__ == "__main__":
    print("🚀 Sanatan YouTube Token Generator")
    print("-" * 40)
    
    # Check karo ki client_secrets.json exist karti hai
    if not os.path.exists(CLIENT_SECRETS_FILE):
        print(f"❌ ERROR: {CLIENT_SECRETS_FILE} not found!")
        print("📥 Google Cloud Console se download karo aur yahan paste karo.")
        exit(1)
    
    try:
        creds = get_authenticated_service()
        print_token_info(creds)
        print("\n✅ Ab YouTube API use kar sakte ho! Jaise upload, comment, etc.")
    except Exception as e:
        print(f"\n❌ Error aaya: {e}")
        print("💡 Tip: Check karo ki client_secrets.json sahi jagah hai.")
```

---

## ▶️ Step 5: Script Run Karo

VS Code terminal me:

```bash
python get_youtube_token.py
```

**Kya hoga:**
1. 🌐 Browser automatically khulega
2. 🔐 Google account se login karo
3. ✅ "Allow" par click karo
4. 📄 Token save ho jayega: `sanatani_youtube_token.json`

---

## 🧪 Step 6: Token Test Karo

Naya file banao: **`test_youtube_token.py`**

```python
"""
🧪 YouTube Token Test Script
Check karta hai ki token kaam kar raha hai ya nahi.
"""

import json
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

TOKEN_FILE = "sanatani_youtube_token.json"
SCOPES = ["https://www.googleapis.com/auth/youtube.readonly"]

def test_token():
    # Token file read karo
    with open(TOKEN_FILE, 'r') as f:
        token_data = json.load(f)
    
    print(f"📖 Reading token from: {TOKEN_FILE}")
    print(f"🔑 Access Token: {token_data['token'][:30]}...")
    
    # Credentials object banao
    creds = Credentials(
        token=token_data['token'],
        refresh_token=token_data.get('refresh_token'),
        token_uri=token_data['token_uri'],
        client_id=token_data['client_id'],
        client_secret=token_data['client_secret'],
        scopes=token_data['scopes']
    )
    
    # YouTube API client banao
    youtube = build('youtube', 'v3', credentials=creds)
    
    # Channel info fetch karo
    print("\n🔍 Fetching your channel info...")
    request = youtube.channels().list(
        part="snippet,statistics",
        mine=True
    )
    response = request.execute()
    
    if response.get('items'):
        channel = response['items'][0]
        print("\n" + "="*60)
        print("✅ TOKEN KAAM KAR RAHA HAI!")
        print("="*60)
        print(f"📺 Channel Name: {channel['snippet']['title']}")
        print(f"👥 Subscribers: {channel['statistics'].get('subscriberCount', 'Hidden')}")
        print(f"🎥 Total Videos: {channel['statistics'].get('videoCount', 0)}")
        print(f"👁️  Total Views: {channel['statistics'].get('viewCount', 0)}")
        print("="*60)
    else:
        print("⚠️ Channel info nahi mili. Kya tumhara YouTube channel hai?")

if __name__ == "__main__":
    try:
        test_token()
    except FileNotFoundError:
        print(f"❌ {TOKEN_FILE} not found. Pehle get_youtube_token.py run karo.")
    except Exception as e:
        print(f"❌ Error: {e}")
        print("💡 Token expired ho sakta hai. Refresh karo.")
```

Run karo:

```bash
python test_youtube_token.py
```

Agar sahi hai toh **tumhare YouTube channel ki info** dikhegi! 🎉

---

## 📤 Step 7: Token se Video Upload Karo (Bonus)

File: **`upload_video.py`**

```python
"""
📤 YouTube Video Upload Example
Token use karke video upload karta hai.
"""

import json
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

TOKEN_FILE = "sanatani_youtube_token.json"

def upload_video(video_file, title, description, tags=[]):
    with open(TOKEN_FILE, 'r') as f:
        token_data = json.load(f)
    
    creds = Credentials(
        token=token_data['token'],
        refresh_token=token_data.get('refresh_token'),
        token_uri=token_data['token_uri'],
        client_id=token_data['client_id'],
        client_secret=token_data['client_secret'],
        scopes=token_data['scopes']
    )
    
    youtube = build('youtube', 'v3', credentials=creds)
    
    body = {
        'snippet': {
            'title': title,
            'description': description,
            'tags': tags,
            'categoryId': '22'  # People & Blogs
        },
        'status': {
            'privacyStatus': 'private',  # private, public, ya unlisted
            'selfDeclaredMadeForKids': False
        }
    }
    
    # Video file upload karo
    media = MediaFileUpload(video_file, chunksize=-1, resumable=True)
    
    print(f"📤 Uploading: {video_file}")
    request = youtube.videos().insert(
        part=','.join(body.keys()),
        body=body,
        media_body=media
    )
    
    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            print(f"⏳ Upload progress: {int(status.progress() * 100)}%")
    
    print(f"\n✅ Video uploaded successfully!")
    print(f"🆔 Video ID: {response['id']}")
    print(f"🔗 URL: https://youtu.be/{response['id']}")
    return response

if __name__ == "__main__":
    # Example use
    upload_video(
        video_file="my_video.mp4",
        title="My First YouTube Video",
        description="Uploaded via Python! 🚀",
        tags=["python", "youtube", "api"]
    )
```

Run:

```bash
python upload_video.py
```

---

## 🔄 Token Refresh Kaise Hota Hai?

Token **1 ghante** ke baad expire hota hai. Refresh token **lifetime** chalta hai (jab tak revoke na karo).

Automatic refresh ke liye, apni script me yeh function add karo:

```python
from google.auth.transport.requests import Request

def refresh_token_if_needed(creds):
    if creds.expired and creds.refresh_token:
        print("🔄 Refreshing expired token...")
        creds.refresh(Request())
        # Naya token save karo
        with open(TOKEN_FILE, 'w') as token:
            token.write(creds.to_json())
        print("✅ Token refreshed and saved!")
    return creds
```

---

## 📁 Final Project Structure

```
sanatannn/
├── client_secrets.json              ← Google se download ki hui file
├── sanatani_youtube_token.json      ← Auto-generated (token yahan save hoga)
├── get_youtube_token.py             ← Token generate karne wala script
├── test_youtube_token.py            ← Token test karne wala
├── upload_video.py                  ← Video upload karne wala
├── main.py                          ← Tumhara existing project
└── requirements.txt                 ← Dependencies
```

---

## ⚠️ Common Errors & Solutions

### ❌ Error: "File 'client_secrets.json' not found"
**Fix:** Google Cloud Console se file download karke project folder me paste karo.

### ❌ Error: "redirect_uri_mismatch"
**Fix:** OAuth Client ID edit karo aur **Authorized redirect URIs** me `http://localhost:8080/` add karo.

### ❌ Error: "Access blocked: This app's request is invalid"
**Fix:** OAuth consent screen me apna email add karo (Test users section me).

### ❌ Error: "insufficient authentication scopes"
**Fix:** Purana token delete karo (`sanatani_youtube_token.json`), phir se `get_youtube_token.py` run karo.

### ❌ Error: "Token has been expired or revoked"
**Fix:** Token file delete karo aur fresh OAuth flow run karo:
```bash
del sanatani_youtube_token.json
python get_youtube_token.py
```

---

## 🔐 Security Tips

1. **Token file ko `.gitignore` me daal do:**
   ```
   sanatani_youtube_token.json
   client_secrets.json
   ```
2. **Token share mat karo** GitHub pe ya kisi ke saath.
3. **Production me Environment Variables use karo:**
   ```python
   import os
   CLIENT_ID = os.getenv('YOUTUBE_CLIENT_ID')
   CLIENT_SECRET = os.getenv('YOUTUBE_CLIENT_SECRET')
   ```
4. **Agar token leak ho jaye toh** Google Cloud Console → Credentials → **RESET** karo.

---

## 📚 Useful Commands

```bash
# Token file dekhna (PowerShell)
Get-Content sanatani_youtube_token.json

# Ya VS Code me file open karo
code sanatani_youtube_token.json

# Check Python version
python --version

# Check installed packages
pip list | findstr google
```

---

## 🎯 Quick Summary

| Step | Command / Action |
|------|------------------|
| 1 | VS Code me project open karo |
| 2 | `pip install google-auth-oauthlib google-auth-httplib2 google-api-python-client` |
| 3 | Google Cloud se `client_secrets.json` download karo |
| 4 | `get_youtube_token.py` banao aur run karo |
| 5 | Browser me login karo, Allow karo |
| 6 | `sanatani_youtube_token.json` auto-generate ho jayega ✅ |
| 7 | `test_youtube_token.py` se test karo |

---

## 🆘 Help Chahiye?

- Google Cloud Console: [https://console.cloud.google.com/](https://console.cloud.google.com/)
- YouTube API Docs: [https://developers.google.com/youtube/v3](https://developers.google.com/youtube/v3)
- Python Quickstart: [https://developers.google.com/youtube/v3/quickstart/python](https://developers.google.com/youtube/v3/quickstart/python)

---

**🙏 Jai Shri Ram! Jai Sanatan!**

Ab tumhara token ready ho jayega aur YouTube API use kar sakte ho! 🚀
