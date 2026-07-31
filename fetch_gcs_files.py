"""
☁️ GCS se files list/download karo
Usage: python fetch_gcs_files.py
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

def get_gcs_client():
    """GCS client setup karo"""
    try:
        from google.cloud import storage
    except ImportError:
        print("❌ google-cloud-storage not installed!")
        print("💡 Run: pip install google-cloud-storage")
        return None
    
    creds_path = os.getenv('GCS_CREDENTIALS_PATH', 'config/gcp-service-account.json')
    bucket_name = os.getenv('GCS_BUCKET_NAME')
    
    if not bucket_name:
        print("❌ GCS_BUCKET_NAME not set in .env!")
        return None, None
    
    if not Path(creds_path).exists():
        print(f"❌ Service account file not found: {creds_path}")
        return None, None
    
    os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = creds_path
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    
    return client, bucket

def list_files(prefix='posts/', limit=20):
    """Files list karo"""
    client, bucket = get_gcs_client()
    if not bucket:
        return
    
    print(f"\n☁️  GCS Bucket: {os.getenv('GCS_BUCKET_NAME')}")
    print(f"📂 Prefix: {prefix}\n")
    
    try:
        blobs = sorted(
            bucket.list_blobs(prefix=prefix),
            key=lambda b: b.time_created,
            reverse=True
        )
        
        if not blobs:
            print(f"⚠️ No files found with prefix '{prefix}'")
            return
        
        for i, blob in enumerate(blobs[:limit], 1):
            size_kb = blob.size / 1024
            print(f"{i:3d}. 📄 {blob.name}")
            print(f"      📏 {size_kb:>8.1f} KB | 📅 {blob.time_created}")
            print(f"      🔗 {blob.public_url}\n")
        
        if len(blobs) > limit:
            print(f"... and {len(blobs) - limit} more files")
            print(f"Total files with prefix '{prefix}': {len(blobs)}")
            
    except Exception as e:
        print(f"❌ Error: {e}")

def download_file(blob_name, local_dir='downloads/'):
    """Specific file download karo"""
    client, bucket = get_gcs_client()
    if not bucket:
        return
    
    try:
        blob = bucket.blob(blob_name)
        os.makedirs(local_dir, exist_ok=True)
        local_path = os.path.join(local_dir, blob_name.split('/')[-1])
        
        print(f"⏳ Downloading: {blob_name}")
        blob.download_to_filename(local_path)
        print(f"✅ Saved to: {local_path}")
        print(f"📏 Size: {os.path.getsize(local_path)/1024:.1f} KB")
        
    except Exception as e:
        print(f"❌ Error: {e}")

def download_recent(count=5, local_dir='downloads/'):
    """Latest N files download karo"""
    client, bucket = get_gcs_client()
    if not bucket:
        return
    
    try:
        blobs = sorted(
            bucket.list_blobs(prefix='posts/'),
            key=lambda b: b.time_created,
            reverse=True
        )[:count]
        
        os.makedirs(local_dir, exist_ok=True)
        
        print(f"⏳ Downloading {len(blobs)} latest files...\n")
        for blob in blobs:
            local_path = os.path.join(local_dir, blob.name.split('/')[-1])
            blob.download_to_filename(local_path)
            print(f"✅ {blob.name} → {local_path}")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    print("☁️  GCS FETCH TOOL")
    print("-"*60)
    print("1. List recent files (posts/)")
    print("2. List files with custom prefix")
    print("3. Download specific file")
    print("4. Download latest N files")
    
    choice = input("\n👉 Choice (1-4): ").strip()
    
    if choice == '1':
        limit = input("Kitne files? (default 20): ").strip()
        limit = int(limit) if limit.isdigit() else 20
        list_files('posts/', limit)
    elif choice == '2':
        prefix = input("Enter prefix (e.g., posts/, reels/): ").strip() or 'posts/'
        limit = input("Kitne files? (default 20): ").strip()
        limit = int(limit) if limit.isdigit() else 20
        list_files(prefix, limit)
    elif choice == '3':
        blob_name = input("Enter full blob name (e.g., posts/2026-07-31/abc.jpg): ").strip()
        if blob_name:
            download_file(blob_name)
        else:
            print("❌ Blob name required!")
    elif choice == '4':
        count = input("Kitne download karne hain? (default 5): ").strip()
        count = int(count) if count.isdigit() else 5
        download_recent(count)
    else:
        print("Invalid choice!")
