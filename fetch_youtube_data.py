"""
📺 YouTube API se channel & video data fetch karo
Usage: python fetch_youtube_data.py
"""

import os
import sys
import json
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

def get_youtube_service():
    """Authenticated YouTube service return karo"""
    token_file = os.getenv('YOUTUBE_TOKEN_FILE', 'sanatani_youtube_token.json')
    
    if not Path(token_file).exists():
        print(f"❌ {token_file} not found!")
        print(f"💡 Pehle run karo: python get_youtube_token.py")
        return None
    
    try:
        with open(token_file, 'r') as f:
            token_data = json.load(f)
        
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build
        
        creds = Credentials(
            token=token_data['token'],
            refresh_token=token_data.get('refresh_token'),
            token_uri=token_data['token_uri'],
            client_id=token_data['client_id'],
            client_secret=token_data['client_secret'],
            scopes=token_data['scopes']
        )
        
        return build('youtube', 'v3', credentials=creds)
    except Exception as e:
        print(f"❌ Error loading token: {e}")
        return None

def fetch_channel_stats():
    youtube = get_youtube_service()
    if not youtube:
        return
    
    channel_id = os.getenv('YOUTUBE_CHANNEL_ID')
    if not channel_id or channel_id == 'UCxxxxxxxxxxxxxxxxxxxxx':
        print("❌ YOUTUBE_CHANNEL_ID not set in .env!")
        return
    
    try:
        request = youtube.channels().list(
            part='snippet,statistics,contentDetails,brandingSettings',
            id=channel_id
        )
        response = request.execute()
        
        if not response.get('items'):
            print(f"❌ Channel not found: {channel_id}")
            return
        
        channel = response['items'][0]
        stats = channel.get('statistics', {})
        snippet = channel.get('snippet', {})
        branding = channel.get('brandingSettings', {}).get('channel', {})
        
        print("\n" + "="*60)
        print("📺 YOUTUBE CHANNEL STATS")
        print("="*60)
        print(f"📛 Name: {snippet.get('title', 'N/A')}")
        print(f"📝 Description: {(snippet.get('description') or 'No description')[:150]}...")
        print(f"🆔 Channel ID: {channel_id}")
        print(f"🔗 Custom URL: {branding.get('customUrl', 'Not set')}")
        print(f"📅 Created: {snippet.get('publishedAt', 'N/A')}")
        print(f"🌍 Country: {snippet.get('country', 'Not set')}")
        print(f"\n📊 STATISTICS:")
        print(f"   👥 Subscribers: {stats.get('subscriberCount', 'Hidden')}")
        print(f"   🎥 Total Videos: {stats.get('videoCount', 0)}")
        print(f"   👁️ Total Views: {stats.get('viewCount', 0)}")
        print(f"\n🔗 URL: https://youtube.com/channel/{channel_id}")
        print("="*60)
        
    except Exception as e:
        print(f"❌ Error: {e}")

def fetch_recent_videos(count=10):
    youtube = get_youtube_service()
    if not youtube:
        return
    
    channel_id = os.getenv('YOUTUBE_CHANNEL_ID')
    if not channel_id:
        print("❌ YOUTUBE_CHANNEL_ID not set!")
        return
    
    try:
        # Channel uploads playlist ID lo
        request = youtube.channels().list(
            part='contentDetails',
            id=channel_id
        )
        response = request.execute()
        
        if not response.get('items'):
            print("❌ Channel not found!")
            return
        
        uploads_playlist = response['items'][0]['contentDetails']['relatedPlaylists']['uploads']
        
        # Playlist items fetch karo
        request = youtube.playlistItems().list(
            part='snippet,status,contentDetails',
            playlistId=uploads_playlist,
            maxResults=count
        )
        response = request.execute()
        
        items = response.get('items', [])
        if not items:
            print("⚠️ No videos found on channel!")
            return
        
        print(f"\n📺 Last {len(items)} YouTube Videos:\n")
        
        for i, item in enumerate(items, 1):
            title = item['snippet']['title']
            video_id = item['contentDetails']['videoId']
            privacy = item['status']['privacyStatus']
            published = item['snippet']['publishedAt']
            description = item['snippet'].get('description', '')[:80]
            
            print(f"{i}. 🎬 {title}")
            print(f"   🆔 {video_id} | 🔒 {privacy}")
            print(f"   🔗 https://youtu.be/{video_id}")
            print(f"   📝 {description}...")
            print(f"   📅 {published}\n")
        
    except Exception as e:
        print(f"❌ Error: {e}")

def fetch_video_stats(video_id):
    """Specific video ki detailed stats"""
    youtube = get_youtube_service()
    if not youtube:
        return
    
    try:
        request = youtube.videos().list(
            part='snippet,statistics,status,contentDetails',
            id=video_id
        )
        response = request.execute()
        
        if not response.get('items'):
            print(f"❌ Video not found: {video_id}")
            return
        
        video = response['items'][0]
        stats = video.get('statistics', {})
        snippet = video.get('snippet', {})
        status = video.get('status', {})
        content = video.get('contentDetails', {})
        
        print("\n" + "="*60)
        print(f"🎬 VIDEO: {snippet.get('title', 'N/A')}")
        print("="*60)
        print(f"🆔 Video ID: {video_id}")
        print(f"🔗 URL: https://youtu.be/{video_id}")
        print(f"📝 Description: {(snippet.get('description') or 'No description')[:200]}...")
        print(f"📅 Published: {snippet.get('publishedAt')}")
        print(f"🏷️ Tags: {', '.join(snippet.get('tags', []))[:100]}")
        print(f"⏱️ Duration: {content.get('duration')}")
        print(f"\n📊 STATS:")
        print(f"   👁️ Views: {stats.get('viewCount', 0)}")
        print(f"   ❤️ Likes: {stats.get('likeCount', 0)}")
        print(f"   💬 Comments: {stats.get('commentCount', 0)}")
        print(f"   🔒 Privacy: {status.get('privacyStatus')}")
        print(f"   📤 Upload status: {status.get('uploadStatus')}")
        print("="*60)
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    print("📺 YOUTUBE FETCH TOOL")
    print("-"*60)
    print("1. Channel stats")
    print("2. Recent videos")
    print("3. Specific video stats")
    
    choice = input("\n👉 Choice (1/2/3): ").strip()
    
    if choice == '1':
        fetch_channel_stats()
    elif choice == '2':
        count = input("Kitne videos? (default 10): ").strip()
        count = int(count) if count.isdigit() else 10
        fetch_recent_videos(count)
    elif choice == '3':
        video_id = input("Enter Video ID (e.g., dQw4w9WgXcQ): ").strip()
        if video_id:
            # URL se extract karo agar pura URL diya
            if 'youtube.com' in video_id or 'youtu.be' in video_id:
                if 'v=' in video_id:
                    video_id = video_id.split('v=')[1].split('&')[0]
                elif 'youtu.be/' in video_id:
                    video_id = video_id.split('youtu.be/')[1].split('?')[0]
            fetch_video_stats(video_id)
        else:
            print("❌ Video ID required!")
    else:
        print("Invalid choice!")
