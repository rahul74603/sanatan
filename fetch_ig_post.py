"""
📱 Instagram Graph API se post status fetch karo
Usage: python fetch_ig_post.py
"""

import os
import sys
import requests
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

def fetch_ig_post(post_id):
    access_token = os.getenv('INSTAGRAM_ACCESS_TOKEN')
    if not access_token:
        print("❌ INSTAGRAM_ACCESS_TOKEN not set in .env!")
        return None
    
    api_version = os.getenv('META_API_VERSION', 'v18.0')
    url = f"https://graph.facebook.com/{api_version}/{post_id}"
    params = {
        'fields': 'id,caption,media_type,media_url,permalink,thumbnail_url,timestamp,like_count,comments_count,insights.metric(impressions,reach,engagement)',
        'access_token': access_token
    }
    
    try:
        response = requests.get(url, params=params, timeout=30)
        data = response.json()
        
        if 'error' in data:
            err = data['error']
            print(f"❌ API Error: {err.get('message')}")
            print(f"   Type: {err.get('type')}")
            print(f"   Code: {err.get('code')}")
            return None
        
        print("\n" + "="*60)
        print("📱 INSTAGRAM POST INFO")
        print("="*60)
        print(f"🆔 ID: {data.get('id')}")
        print(f"📸 Type: {data.get('media_type')}")
        print(f"📝 Caption: {(data.get('caption') or 'No caption')[:150]}...")
        print(f"🔗 Permalink: {data.get('permalink')}")
        print(f"🖼️ Media URL: {(data.get('media_url') or data.get('thumbnail_url') or '')[:80]}...")
        print(f"❤️ Likes: {data.get('like_count', 0)}")
        print(f"💬 Comments: {data.get('comments_count', 0)}")
        print(f"📅 Posted: {data.get('timestamp')}")
        
        # Insights (if available)
        if 'insights' in data and 'data' in data['insights']:
            print(f"\n📊 INSIGHTS:")
            for insight in data['insights']['data']:
                name = insight.get('name', 'unknown')
                value = insight.get('values', [{}])[0].get('value', 0)
                print(f"   {name}: {value}")
        
        print("="*60)
        return data
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

def fetch_my_recent_posts(count=5):
    access_token = os.getenv('INSTAGRAM_ACCESS_TOKEN')
    ig_user_id = os.getenv('INSTAGRAM_USER_ID')
    
    if not access_token or not ig_user_id:
        print("❌ INSTAGRAM_ACCESS_TOKEN or INSTAGRAM_USER_ID not set in .env!")
        return
    
    api_version = os.getenv('META_API_VERSION', 'v18.0')
    url = f"https://graph.facebook.com/{api_version}/{ig_user_id}/media"
    params = {
        'fields': 'id,caption,media_type,permalink,timestamp,like_count,comments_count,thumbnail_url',
        'access_token': access_token,
        'limit': count
    }
    
    try:
        response = requests.get(url, params=params, timeout=30)
        data = response.json()
        
        if 'error' in data:
            print(f"❌ Error: {data['error']['message']}")
            return
        
        posts = data.get('data', [])
        if not posts:
            print("⚠️ No posts found!")
            return
        
        print(f"\n📱 Last {len(posts)} Instagram Posts:\n")
        for i, post in enumerate(posts, 1):
            print(f"{i}. 🆔 {post['id']}")
            print(f"   📝 {(post.get('caption') or 'No caption')[:80]}...")
            print(f"   📸 {post.get('media_type')} | ❤️ {post.get('like_count', 0)} | 💬 {post.get('comments_count', 0)}")
            print(f"   🔗 {post.get('permalink')}")
            print(f"   📅 {post.get('timestamp')}\n")
        
    except Exception as e:
        print(f"❌ Error: {e}")

def fetch_account_info():
    """Apne account ki info fetch karo"""
    access_token = os.getenv('INSTAGRAM_ACCESS_TOKEN')
    ig_user_id = os.getenv('INSTAGRAM_USER_ID')
    api_version = os.getenv('META_API_VERSION', 'v18.0')
    
    url = f"https://graph.facebook.com/{api_version}/{ig_user_id}"
    params = {
        'fields': 'id,username,name,biography,website,followers_count,follows_count,media_count,profile_picture_url,account_type',
        'access_token': access_token
    }
    
    try:
        response = requests.get(url, params=params, timeout=30)
        data = response.json()
        
        if 'error' in data:
            print(f"❌ Error: {data['error']['message']}")
            return
        
        print("\n" + "="*60)
        print("📱 INSTAGRAM ACCOUNT INFO")
        print("="*60)
        print(f"👤 Username: @{data.get('username', 'N/A')}")
        print(f"📛 Name: {data.get('name', 'N/A')}")
        print(f"📝 Bio: {data.get('biography', 'N/A')}")
        print(f"🌐 Website: {data.get('website', 'N/A')}")
        print(f"🆔 ID: {data.get('id')}")
        print(f"📊 Account Type: {data.get('account_type', 'N/A')}")
        print(f"👥 Followers: {data.get('followers_count', 0)}")
        print(f"➡️ Following: {data.get('follows_count', 0)}")
        print(f"📸 Posts: {data.get('media_count', 0)}")
        print(f"🖼️ Profile: {data.get('profile_picture_url', 'N/A')[:80]}...")
        print("="*60)
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    print("📱 INSTAGRAM FETCH TOOL")
    print("-"*60)
    print("1. Account info")
    print("2. Recent posts")
    print("3. Specific post by ID")
    
    choice = input("\n👉 Choice (1/2/3): ").strip()
    
    if choice == '1':
        fetch_account_info()
    elif choice == '2':
        count = input("Kitne posts? (default 5): ").strip()
        count = int(count) if count.isdigit() else 5
        fetch_my_recent_posts(count)
    elif choice == '3':
        post_id = input("Enter IG Post ID (e.g., 18149271742496554): ").strip()
        if post_id:
            fetch_ig_post(post_id)
        else:
            print("❌ Post ID required!")
    else:
        print("Invalid choice!")
