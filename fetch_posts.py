"""
📊 Database se posts fetch karo
Usage: python fetch_posts.py
"""

import sqlite3
import os
import sys
from pathlib import Path

def find_database():
    """Database file dhundho (multiple possible paths)"""
    possible_paths = [
        'data/database.db',
        'data/sanatan.db',
        'data/posts.db',
        'sanatan.db',
        'database.db',
        'data/app.db'
    ]
    
    for path in possible_paths:
        if Path(path).exists():
            return path
    
    return None

def fetch_recent_posts(limit=10):
    db_path = find_database()
    if not db_path:
        print("❌ Database file nahi mili! Check karo:")
        print("   - data/database.db")
        print("   - data/sanatan.db")
        print("   - ya koi bhi .db file project me")
        return
    
    print(f"📁 Database: {db_path}\n")
    
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        
        # Pehle tables dekho
        c.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in c.fetchall()]
        print(f"📋 Available tables: {tables}\n")
        
        # post_history table try karo
        if 'post_history' not in tables:
            print(f"⚠️ 'post_history' table not found!")
            print(f"   Available: {tables}")
            return
        
        # Columns check karo
        c.execute("PRAGMA table_info(post_history)")
        columns = [row[1] for row in c.fetchall()]
        print(f"📊 Columns: {columns}\n")
        
        # Safe query (existing columns only)
        select_cols = [col for col in [
            'id', 'topic', 'category', 'post_type',
            'ig_post_id', 'fb_post_id', 'yt_post_id',
            'ig_success', 'fb_success', 'yt_success',
            'image_url', 'caption', 'created_at'
        ] if col in columns]
        
        query = f'''
            SELECT {', '.join(select_cols)}
            FROM post_history 
            ORDER BY id DESC 
            LIMIT {limit}
        '''
        
        c.execute(query)
        rows = c.fetchall()
        
        if not rows:
            print("⚠️ No posts found in database!")
            return
        
        print("="*80)
        print(f"📊 LAST {len(rows)} POSTS")
        print("="*80)
        
        for row in rows:
            row_dict = dict(row)
            print(f"\n🆔 ID: {row_dict.get('id', 'N/A')}")
            print(f"📌 Topic: {row_dict.get('topic', 'N/A')[:60]}...")
            print(f"📂 Category: {row_dict.get('category', 'N/A')}")
            print(f"📸 Type: {row_dict.get('post_type', 'N/A')}")
            
            if 'ig_post_id' in row_dict:
                print(f"📱 IG: {'✅' if row_dict.get('ig_success') else '❌'} {row_dict.get('ig_post_id') or 'N/A'}")
            if 'fb_post_id' in row_dict:
                print(f"📘 FB: {'✅' if row_dict.get('fb_success') else '❌'} {row_dict.get('fb_post_id') or 'N/A'}")
            if 'yt_post_id' in row_dict:
                print(f"📺 YT: {'✅' if row_dict.get('yt_success') else '❌'} {row_dict.get('yt_post_id') or 'N/A'}")
            
            if 'image_url' in row_dict and row_dict.get('image_url'):
                print(f"🖼️ Image: {row_dict['image_url'][:60]}...")
            
            if 'created_at' in row_dict:
                print(f"📅 Created: {row_dict['created_at']}")
            
            print("-"*80)
        
        # Summary
        print(f"\n📈 Total posts in DB: {c.execute('SELECT COUNT(*) FROM post_history').fetchone()[0]}")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("📊 SANATAN DATABASE FETCH TOOL")
    print("-"*60)
    
    limit = input("Kitne posts chahiye? (default 10): ").strip()
    try:
        limit = int(limit) if limit else 10
    except ValueError:
        limit = 10
    
    fetch_recent_posts(limit)
