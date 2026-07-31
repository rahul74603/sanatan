# 🖥️ Local Fetch Commands - Sanatan Auto-Poster

Yeh guide tumhe **local me sab kuch fetch/test karne** ke commands degi — image, post status, YouTube data, analytics, sab!

---

## 🎯 Quick Start (Sabse Important Commands)

PowerShell ya VS Code Terminal me yeh run karo:

```powershell
# 1. Project folder me jao
cd C:\Users\Rahul\Desktop\sanatannn

# 2. Virtual environment activate karo
.\venv\Scripts\Activate.ps1

# 3. Check karo sab installed hai
pip list | findstr -i "google requests pillow"
```

---

## 📦 1. Database Se Data Fetch Karo

### Latest post dekho (jo abhi publish hua):

```powershell
# SQLite database open karo
sqlite3 data\database.db

# Ya Windows me direct:
python -c "import sqlite3; conn=sqlite3.connect('data/database.db'); c=conn.cursor(); c.execute('SELECT * FROM post_history ORDER BY id DESC LIMIT 5'); [print(row) for row in c.fetchall()]"
```

### Python script banao `fetch_posts.py`:

```python
"""
📊 Database se posts fetch karo
"""
import sqlite3
from datetime import datetime

def fetch_recent_posts(limit=10):
    conn = sqlite3.connect('data/database.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    c.execute(f'''
        SELECT 
            id, 
            topic, 
            category,
            post_type,
            ig_post_id,
            fb_post_id,
            yt_post_id,
            ig_success,
            fb_success,
            yt_success,
            created_at
        FROM post_history 
        ORDER BY id DESC 
        LIMIT {limit}
    ''')
    
    print("="*80)
    print(f"📊 LAST {limit} POSTS")
    print("="*80)
    
    for row in c.fetchall():
        print(f"\n🆔 ID: {row['id']}")
        print(f"📌 Topic: {row['topic']}")
        print(f"📂 Category: {row['category']}")
        print(f"📸 Type: {row['post_type']}")
        print(f"📱 IG: {'✅' if row['ig_success'] else '❌'} {row['ig_post_id'] or 'N/A'}")
        print(f"📘 FB: {'✅' if row['fb_success'] else '❌'} {row['fb_post_id'] or 'N/A'}")
        print(f"📺 YT: {'✅' if row['yt_success'] else '❌'} {row['yt_post_id'] or 'N/A'}")
        print(f"📅 Created: {row['created_at']}")
        print("-"*80)
    
    conn.close()

if __name__ == "__main__":
    fetch_recent_posts(10)
```

**Run:**
```powershell
python fetch_posts.py
```

---

## 🖼️ 2. Image Fetch / Download Karo

### Latest image GCS se download karo:

```python
"""
🖼️ GCS se image download karo
"""
import os
from google.cloud import storage

def fetch_latest_images(count=5):
    os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = 'config/gcp-service-account.json'
    
    client = storage.Client()
    bucket = client.bucket(os.getenv('GCS_BUCKET_NAME'))
    
    blobs = list(bucket.list_blobs(prefix='posts/', delimiter='/'))
    blobs.sort(key=lambda b: b.time_created, reverse=True)
    
    print(f"📸 Last {count} images:\n")
    
    for i, blob in enumerate(blobs[:count]):
        local_path = f"downloads/{blob.name.split('/')[-1]}"
        os.makedirs('downloads', exist_ok=True)
        blob.download_to_filename(local_path)
        
        print(f"✅ {i+1}. {blob.name}")
        print(f"   📁 Saved: {local_path}")
        print(f"   🔗 URL: {blob.public_url}")
        print(f"   📏 Size: {blob.size/1024:.1f} KB")
        print(f"   📅 Created: {blob.time_created}")
        print()

if __name__ == "__main__":
    fetch_latest_images(5)
```

**Run:**
```powershell
python fetch_latest_images.py
```

---

## 📱 3. Instagram Post Status Fetch Karo

### Specific post ki info lao:

```python
"""
📱 Instagram Graph API se post status fetch karo
"""
import os
import requests
from dotenv import load_dotenv

load_dotenv()

def fetch_ig_post(post_id):
    access_token = os.getenv('INSTAGRAM_ACCESS_TOKEN')
    api_version = os.getenv('META_API_VERSION', 'v18.0')
    
    url = f"https://graph.facebook.com/{api_version}/{post_id}"
    params = {
        'fields': 'id,caption,media_type,media_url,permalink,thumbnail_url,timestamp,like_count,comments_count',
        'access_token': access_token
    }
    
    response = requests.get(url, params=params)
    data = response.json()
    
    if 'error' in data:
        print(f"❌ Error: {data['error']['message']}")
        return None
    
    print("="*60)
    print("📱 INSTAGRAM POST INFO")
    print("="*60)
    print(f"🆔 ID: {data.get('id')}")
    print(f"📸 Type: {data.get('media_type')}")
    print(f"📝 Caption: {data.get('caption', '')[:100]}...")
    print(f"🔗 URL: {data.get('permalink')}")
    print(f"🖼️ Media: {data.get('media_url', data.get('thumbnail_url'))}")
    print(f"❤️ Likes: {data.get('like_count', 0)}")
    print(f"💬 Comments: {data.get('comments_count', 0)}")
    print(f"📅 Posted: {data.get('timestamp')}")
    print("="*60)
    
    return data

def fetch_my_recent_posts(count=5):
    """Apne saare recent IG posts fetch karo"""
    access_token = os.getenv('INSTAGRAM_ACCESS_TOKEN')
    ig_user_id = os.getenv('INSTAGRAM_USER_ID')
    api_version = os.getenv('META_API_VERSION', 'v18.0')
    
    url = f"https://graph.facebook.com/{api_version}/{ig_user_id}/media"
    params = {
        'fields': 'id,caption,media_type,permalink,timestamp,like_count,comments_count',
        'access_token': access_token,
        'limit': count
    }
    
    response = requests.get(url, params=params)
    data = response.json()
    
    if 'error' in data:
        print(f"❌ Error: {data['error']['message']}")
        return
    
    print(f"\n📱 Last {count} Instagram Posts:\n")
    for post in data.get('data', []):
        print(f"🆔 {post['id']} | ❤️ {post.get('like_count', 0)} | 💬 {post.get('comments_count', 0)}")
        print(f"   📝 {(post.get('caption') or '')[:80]}...")
        print(f"   🔗 {post.get('permalink')}")
        print(f"   📅 {post.get('timestamp')}\n")

if __name__ == "__main__":
    # Last post ID database se lo, ya manually enter karo
    post_id = input("Enter IG Post ID (ya press Enter for recent posts): ").strip()
    
    if post_id:
        fetch_ig_post(post_id)
    else:
        fetch_my_recent_posts(5)
```

**Run:**
```powershell
python fetch_ig_post.py
```

---

## 📘 4. Facebook Post Status Fetch Karo

```python
"""
📘 Facebook Graph API se post status fetch karo
"""
import os
import requests
from dotenv import load_dotenv

load_dotenv()

def fetch_fb_post(post_id):
    access_token = os.getenv('FACEBOOK_ACCESS_TOKEN')
    api_version = os.getenv('META_API_VERSION', 'v18.0')
    
    url = f"https://graph.facebook.com/{api_version}/{post_id}"
    params = {
        'fields': 'id,message,full_picture,permalink_url,created_time,likes.summary(true),comments.summary(true),shares',
        'access_token': access_token
    }
    
    response = requests.get(url, params=params)
    data = response.json()
    
    if 'error' in data:
        print(f"❌ Error: {data['error']['message']}")
        return None
    
    likes = data.get('likes', {}).get('summary', {}).get('total_count', 0)
    comments = data.get('comments', {}).get('summary', {}).get('total_count', 0)
    shares = data.get('shares', {}).get('count', 0)
    
    print("="*60)
    print("📘 FACEBOOK POST INFO")
    print("="*60)
    print(f"🆔 ID: {data.get('id')}")
    print(f"📝 Message: {(data.get('message') or '')[:100]}...")
    print(f"🖼️ Image: {data.get('full_picture')}")
    print(f"🔗 URL: {data.get('permalink_url')}")
    print(f"❤️ Likes: {likes}")
    print(f"💬 Comments: {comments}")
    print(f"🔄 Shares: {shares}")
    print(f"📅 Posted: {data.get('created_time')}")
    print("="*60)
    
    return data

if __name__ == "__main__":
    post_id = input("Enter FB Post ID: ").strip()
    if post_id:
        fetch_fb_post(post_id)
```

**Run:**
```powershell
python fetch_fb_post.py
```

---

## 📺 5. YouTube Data Fetch Karo

### Channel stats lao:

```python
"""
📺 YouTube API se channel & video data fetch karo
"""
import os
import json
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from dotenv import load_dotenv

load_dotenv()

def get_youtube_service():
    """Authenticated YouTube service return karo"""
    token_file = os.getenv('YOUTUBE_TOKEN_FILE', 'sanatani_youtube_token.json')
    
    if not os.path.exists(token_file):
        print(f"❌ {token_file} not found! Run: python get_youtube_token.py")
        return None
    
    with open(token_file, 'r') as f:
        token_data = json.load(f)
    
    creds = Credentials(
        token=token_data['token'],
        refresh_token=token_data.get('refresh_token'),
        token_uri=token_data['token_uri'],
        client_id=token_data['client_id'],
        client_secret=token_data['client_secret'],
        scopes=token_data['scopes']
    )
    
    return build('youtube', 'v3', credentials=creds)

def fetch_channel_stats():
    youtube = get_youtube_service()
    if not youtube:
        return
    
    channel_id = os.getenv('YOUTUBE_CHANNEL_ID')
    
    request = youtube.channels().list(
        part='snippet,statistics,contentDetails',
        id=channel_id
    )
    response = request.execute()
    
    if not response.get('items'):
        print("❌ Channel not found!")
        return
    
    channel = response['items'][0]
    stats = channel['statistics']
    snippet = channel['snippet']
    
    print("="*60)
    print("📺 YOUTUBE CHANNEL STATS")
    print("="*60)
    print(f"📛 Name: {snippet['title']}")
    print(f"📝 Description: {(snippet.get('description') or '')[:100]}...")
    print(f"🆔 ID: {channel_id}")
    print(f"👥 Subscribers: {stats.get('subscriberCount', 'Hidden')}")
    print(f"🎥 Videos: {stats.get('videoCount', 0)}")
    print(f"👁️ Views: {stats.get('viewCount', 0)}")
    print(f"🔗 URL: https://youtube.com/channel/{channel_id}")
    print("="*60)

def fetch_recent_videos(count=10):
    youtube = get_youtube_service()
    if not youtube:
        return
    
    channel_id = os.getenv('YOUTUBE_CHANNEL_ID')
    
    # Channel ke uploads playlist ID lo
    request = youtube.channels().list(
        part='contentDetails',
        id=channel_id
    )
    response = request.execute()
    
    uploads_playlist = response['items'][0]['contentDetails']['relatedPlaylists']['uploads']
    
    # Playlist items fetch karo
    request = youtube.playlistItems().list(
        part='snippet,status,contentDetails',
        playlistId=uploads_playlist,
        maxResults=count
    )
    response = request.execute()
    
    print(f"\n📺 Last {count} YouTube Videos:\n")
    for i, item in enumerate(response.get('items', []), 1):
        title = item['snippet']['title']
        video_id = item['contentDetails']['videoId']
        privacy = item['status']['privacyStatus']
        published = item['snippet']['publishedAt']
        
        print(f"{i}. 🎬 {title}")
        print(f"   🆔 {video_id} | 🔒 {privacy}")
        print(f"   🔗 https://youtu.be/{video_id}")
        print(f"   📅 {published}\n")

if __name__ == "__main__":
    fetch_channel_stats()
    print()
    fetch_recent_videos(5)
```

**Run:**
```powershell
python fetch_youtube_data.py
```

---

## ☁️ 6. Google Cloud Storage (GCS) Fetch Karo

```python
"""
☁️ GCS se files list/download karo
"""
import os
from google.cloud import storage
from dotenv import load_dotenv

load_dotenv()

def list_gcs_files(prefix='posts/', limit=20):
    os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = os.getenv('GCS_CREDENTIALS_PATH', 'config/gcp-service-account.json')
    
    client = storage.Client()
    bucket_name = os.getenv('GCS_BUCKET_NAME')
    bucket = client.bucket(bucket_name)
    
    print(f"☁️  GCS Bucket: {bucket_name}")
    print(f"📂 Prefix: {prefix}\n")
    
    blobs = sorted(
        bucket.list_blobs(prefix=prefix),
        key=lambda b: b.time_created,
        reverse=True
    )
    
    for i, blob in enumerate(blobs[:limit]):
        print(f"{i+1}. 📄 {blob.name}")
        print(f"   📏 {blob.size/1024:.1f} KB | 📅 {blob.time_created}")
        print(f"   🔗 {blob.public_url}\n")

def download_blob(blob_name, local_path):
    os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = os.getenv('GCS_CREDENTIALS_PATH')
    client = storage.Client()
    bucket = client.bucket(os.getenv('GCS_BUCKET_NAME'))
    blob = bucket.blob(blob_name)
    blob.download_to_filename(local_path)
    print(f"✅ Downloaded: {blob_name} → {local_path}")

if __name__ == "__main__":
    list_gcs_files(prefix='posts/', limit=10)
```

**Run:**
```powershell
python fetch_gcs_files.py
```

---

## 📊 7. Analytics Fetch Karo

```python
"""
📊 Saare platforms ka analytics ek jagah fetch karo
"""
import os
import sqlite3
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

def get_analytics_summary(days=7):
    """Last N days ka analytics summary"""
    conn = sqlite3.connect('data/database.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    since_date = (datetime.now() - timedelta(days=days)).isoformat()
    
    c.execute('''
        SELECT 
            COUNT(*) as total_posts,
            SUM(CASE WHEN ig_success=1 THEN 1 ELSE 0 END) as ig_success_count,
            SUM(CASE WHEN fb_success=1 THEN 1 ELSE 0 END) as fb_success_count,
            SUM(CASE WHEN yt_success=1 THEN 1 ELSE 0 END) as yt_success_count,
            category,
            AVG(engagement_rate) as avg_engagement
        FROM post_history 
        WHERE created_at > ?
        GROUP BY category
        ORDER BY total_posts DESC
    ''', (since_date,))
    
    print("="*60)
    print(f"📊 ANALYTICS SUMMARY (Last {days} days)")
    print("="*60)
    
    for row in c.fetchall():
        print(f"\n📂 Category: {row['category']}")
        print(f"   📝 Total posts: {row['total_posts']}")
        print(f"   📱 IG success: {row['ig_success_count']}")
        print(f"   📘 FB success: {row['fb_success_count']}")
        print(f"   📺 YT success: {row['yt_success_count']}")
        if row['avg_engagement']:
            print(f"   📈 Avg engagement: {row['avg_engagement']:.2f}%")
    
    conn.close()

if __name__ == "__main__":
    days = input("Enter days (default 7): ").strip() or "7"
    get_analytics_summary(int(days))
```

**Run:**
```powershell
python fetch_analytics.py
```

---

## 🔍 8. Logs Se Info Fetch Karo

```powershell
# Latest error logs dekho
Get-Content logs\error_log.txt -Tail 50

# Ya Python se:
python -c "with open('logs/error_log.txt') as f: print(f.read()[-2000:])"

# Specific date ke logs
Get-ChildItem logs\ -Filter "*.log" | Sort-Object LastWriteTime -Descending | Select-Object -First 5

# Search for errors
Select-String -Path "logs\*.log" -Pattern "ERROR" -CaseSensitive:$false | Select-Object -Last 20
```

---

## 🚀 9. Complete Fetch Script (All-in-One)

`fetch_all.py` banao:

```python
"""
🚀 One-click sab kuch fetch karo
"""
import subprocess
import sys

def run_script(name, description):
    print(f"\n{'='*60}")
    print(f"▶️  {description}")
    print('='*60)
    try:
        subprocess.run([sys.executable, name], check=True)
    except FileNotFoundError:
        print(f"⚠️ {name} not found, skipping...")
    except Exception as e:
        print(f"❌ Error: {e}")

def main():
    print("🚀 SANATAN LOCAL FETCH TOOL")
    print("="*60)
    print("\nKya fetch karna hai?")
    print("1. Database posts")
    print("2. Instagram posts")
    print("3. Facebook posts")
    print("4. YouTube data")
    print("5. GCS files")
    print("6. Analytics summary")
    print("7. ALL (sab kuch)")
    print("0. Exit")
    
    choice = input("\n👉 Choice: ").strip()
    
    if choice == '1':
        run_script('fetch_posts.py', '📊 Database Posts')
    elif choice == '2':
        run_script('fetch_ig_post.py', '📱 Instagram Posts')
    elif choice == '3':
        run_script('fetch_fb_post.py', '📘 Facebook Posts')
    elif choice == '4':
        run_script('fetch_youtube_data.py', '📺 YouTube Data')
    elif choice == '5':
        run_script('fetch_gcs_files.py', '☁️ GCS Files')
    elif choice == '6':
        run_script('fetch_analytics.py', '📊 Analytics')
    elif choice == '7':
        # Sab run karo
        for script, desc in [
            ('fetch_posts.py', '📊 Database Posts'),
            ('fetch_ig_post.py', '📱 Instagram Posts'),
            ('fetch_fb_post.py', '📘 Facebook Posts'),
            ('fetch_youtube_data.py', '📺 YouTube Data'),
            ('fetch_gcs_files.py', '☁️ GCS Files'),
            ('fetch_analytics.py', '📊 Analytics')
        ]:
            run_script(script, desc)
    elif choice == '0':
        print("👋 Bye!")
    else:
        print("❌ Invalid choice")

if __name__ == "__main__":
    main()
```

**Run:**
```powershell
python fetch_all.py
```

---

## 📋 Quick Command Cheatsheet

```powershell
# 🔧 Setup
cd C:\Users\Rahul\Desktop\sanatannn
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt

# 🎬 Main pipeline run karo
python main.py

# 📊 Local fetch tools
python fetch_posts.py            # Database posts
python fetch_ig_post.py          # Instagram status
python fetch_fb_post.py          # Facebook status
python fetch_youtube_data.py     # YouTube channel/videos
python fetch_gcs_files.py        # GCS files list
python fetch_analytics.py        # Analytics summary
python fetch_all.py              # Sab kuch ek saath

# 🔍 Quick checks
python -c "import sqlite3; print(sqlite3.connect('data/database.db').execute('SELECT COUNT(*) FROM post_history').fetchone())"
python -c "import os; print('IG Token:', 'OK' if os.getenv('INSTAGRAM_ACCESS_TOKEN') else 'MISSING')"

# 📁 Useful paths
explorer .                       # Project folder open
explorer downloads\              # Downloaded images
explorer logs\                   # Logs folder
explorer data\                   # Database folder

# 🧹 Cleanup
del downloads\*.jpg /q          # Old images delete
del logs\*.log /q               # Old logs delete
```

---

## 🆘 Common Issues & Fixes

| Issue | Command to Fix |
|-------|----------------|
| `ModuleNotFoundError` | `pip install -r requirements.txt` |
| `.env not loaded` | Check file exists in project root |
| `IG token expired` | Re-run OAuth flow |
| `GCS permission denied` | Check service account JSON path |
| `YouTube quota exceeded` | Wait 24 hours, daily quota reset |

---

**🎉 Bas! Ab tumhare paas sab kuch locally fetch karne ke commands hain!**

Bhai, ab bata — kaunsa fetch karna hai? Main specific script bana ke de sakta hoon! 🚀
