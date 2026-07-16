"""
Comment Fetcher V4 - Fixed Double Reply Bug
- Persistent comment tracking with proper DB handling
- Timestamp-based filtering (only last 24h comments)  
- Single DB connection per operation
- Proper reply_posted flag checking
"""
import time
import re
import requests
from datetime import datetime, timedelta, timezone
from typing import Optional

from config.settings import (
    INSTAGRAM_ACCOUNT_ID,
    FACEBOOK_PAGE_ID,
    ACCESS_TOKEN,
    META_API_VERSION,
    YOUTUBE_ENABLED,
    YOUTUBE_CHANNEL_ID,
)
from core.database import get_connection
from utils.logger import get_logger

logger = get_logger("comment_fetcher")

META_BASE_URL = f"https://graph.facebook.com/{META_API_VERSION}"

# Config
MAX_POSTS_TO_CHECK = 5
MAX_COMMENTS_PER_POST = 20
REQUEST_TIMEOUT = 15
SPAM_KEYWORDS = [
    "follow me", "check my", "visit my", "dm me",
    "click link", "free money", "earn money",
    "whatsapp", "telegram group", "join now",
    "s3x", "adult", "dating"
]

# ============================================================
# DATABASE - SINGLE CONNECTION MANAGER
# ============================================================

def _get_db():
    """Get DB connection with WAL mode for reliability"""
    conn = get_connection()
    conn.execute("PRAGMA journal_mode=WAL")   # Better concurrent access
    conn.execute("PRAGMA synchronous=NORMAL") # Balance speed/safety
    return conn


def _ensure_comment_table():
    """Create comment tracking table - call once at startup"""
    try:
        conn = _get_db()
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS comment_replies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                platform TEXT NOT NULL,
                post_id TEXT NOT NULL,
                comment_id TEXT UNIQUE NOT NULL,
                comment_text TEXT,
                commenter_name TEXT,
                reply_text TEXT,
                reply_posted INTEGER DEFAULT 0,
                replied_at TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        # Index for fast lookups
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_comment_id 
            ON comment_replies(comment_id)
        """)
        conn.commit()
        conn.close()
        logger.debug("✅ Comment table ready")
    except Exception as e:
        logger.error(f"❌ Comment table setup failed: {e}")
        raise  # Yeh critical hai, fail hona chahiye


# ============================================================
# CORE FIX: ATOMIC CHECK + INSERT
# ============================================================

def _check_and_save_comment(
    platform: str,
    post_id: str,
    comment_id: str,
    comment_text: str,
    commenter_name: str
) -> bool:
    """
    ATOMIC operation: Check if new + Save if new.
    
    Single transaction mein check aur save karo - 
    race condition bilkul nahi hoga.
    
    Returns:
        True  = Comment naya hai, process karo
        False = Already seen/replied, skip karo
    """
    try:
        conn = _get_db()
        cursor = conn.cursor()
        
        try:
            # BEGIN EXCLUSIVE TRANSACTION - koi race condition nahi
            cursor.execute("BEGIN EXCLUSIVE")
            
            # Check karo already exists?
            cursor.execute(
                "SELECT id, reply_posted FROM comment_replies WHERE comment_id = ?",
                (comment_id,)
            )
            existing = cursor.fetchone()
            
            if existing is not None:
                # Already in DB = already processed
                row_id, reply_posted = existing
                logger.debug(
                    f"   ⏭️  Skip [{comment_id[:12]}...] "
                    f"reply_posted={reply_posted}"
                )
                conn.execute("ROLLBACK")
                conn.close()
                return False
            
            # Naya hai - INSERT karo
            cursor.execute("""
                INSERT INTO comment_replies
                    (platform, post_id, comment_id, comment_text, 
                     commenter_name, reply_posted, created_at)
                VALUES (?, ?, ?, ?, ?, 0, ?)
            """, (
                platform,
                post_id, 
                comment_id,
                comment_text,
                commenter_name,
                datetime.now(timezone.utc).isoformat()
            ))
            
            conn.execute("COMMIT")
            conn.close()
            logger.debug(f"   💾 Saved new comment [{comment_id[:12]}...]")
            return True
            
        except Exception as e:
            conn.execute("ROLLBACK")
            conn.close()
            logger.error(f"❌ Transaction failed for {comment_id}: {e}")
            return False  # Safe side pe skip karo
            
    except Exception as e:
        logger.error(f"❌ DB connection failed: {e}")
        return False


def mark_reply_posted(comment_id: str, reply_text: str):
    """
    Reply post hone ke BAAD call karo.
    Yeh function reply_poster.py mein call hona chahiye.
    """
    try:
        conn = _get_db()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE comment_replies 
            SET reply_posted = 1,
                reply_text = ?,
                replied_at = ?
            WHERE comment_id = ?
        """, (
            reply_text,
            datetime.now(timezone.utc).isoformat(),
            comment_id
        ))
        conn.commit()
        
        if cursor.rowcount > 0:
            logger.info(f"✅ Marked replied: {comment_id[:15]}...")
        else:
            logger.warning(f"⚠️  Comment not found to mark: {comment_id[:15]}...")
            
        conn.close()
    except Exception as e:
        logger.error(f"❌ Mark reply failed for {comment_id}: {e}")


# ============================================================
# SPAM DETECTION
# ============================================================

def _is_spam(comment_text: str) -> bool:
    """Detect spam/bot comments"""
    if not comment_text:
        return True

    text_lower = comment_text.lower().strip()

    # Spam keywords check
    for keyword in SPAM_KEYWORDS:
        if keyword in text_lower:
            logger.debug(f"   🚫 Spam keyword '{keyword}' found")
            return True

    # Multiple URLs
    if text_lower.count("http") > 1:
        return True

    # Repeated characters (aaaaaaa)
    for i in range(len(text_lower) - 5):
        if len(set(text_lower[i:i+6])) == 1 and text_lower[i].isalpha():
            return True

    return False


def _is_worth_replying(comment_text: str) -> bool:
    """
    Check if comment deserves a reply.
    
    Skip: Empty, single emoji, single word
    Reply: Questions, 2+ words, Hindi text, mentions
    """
    if not comment_text or not comment_text.strip():
        return False

    # Emojis hata ke clean text dekho
    clean = re.sub(
        r'[\U0001F300-\U0001FFFF\U00002600-\U000027BF]',
        '', comment_text
    ).strip()

    # Pure emoji comment - skip
    if len(clean) < 2:
        return False

    # Question = always reply
    if '?' in comment_text:
        return True

    # Hindi/Devanagari text = engaged user
    devanagari_count = sum(1 for c in comment_text if '\u0900' <= c <= '\u097F')
    if devanagari_count > 3:
        return True

    # 2+ words = engaged
    words = clean.split()
    if len(words) >= 2:
        return True

    return False


def _parse_timestamp(ts_string: str) -> Optional[datetime]:
    """Parse ISO timestamp from APIs"""
    if not ts_string:
        return None
    try:
        # Handle both formats
        ts_string = ts_string.replace('Z', '+00:00')
        return datetime.fromisoformat(ts_string)
    except Exception:
        return None


def _is_recent(timestamp_str: str, hours: int = 48) -> bool:
    """
    Check if comment is from last N hours.
    48 hours window use karo (24h too tight for some timezones)
    """
    if not timestamp_str:
        return True  # Agar timestamp nahi hai to process karo

    comment_time = _parse_timestamp(timestamp_str)
    if not comment_time:
        return True

    # Timezone aware comparison
    now = datetime.now(timezone.utc)
    if comment_time.tzinfo is None:
        comment_time = comment_time.replace(tzinfo=timezone.utc)

    cutoff = now - timedelta(hours=hours)
    return comment_time > cutoff


# ============================================================
# INSTAGRAM
# ============================================================

def _get_recent_ig_posts(limit: int = MAX_POSTS_TO_CHECK) -> list:
    """Get recent IG posts"""
    try:
        url = f"{META_BASE_URL}/{INSTAGRAM_ACCOUNT_ID}/media"
        response = requests.get(
            url,
            params={
                'fields': 'id,caption,timestamp,media_type',
                'limit': limit,
                'access_token': ACCESS_TOKEN
            },
            timeout=REQUEST_TIMEOUT
        )

        if response.status_code == 200:
            posts = response.json().get('data', [])
            logger.info(f"📸 Found {len(posts)} recent IG posts")
            return posts
        else:
            logger.warning(
                f"⚠️  IG posts fetch failed: "
                f"{response.status_code} - {response.text[:100]}"
            )
            return []

    except Exception as e:
        logger.error(f"❌ IG posts error: {e}")
        return []


def _get_ig_comments(post_id: str) -> list:
    """Get comments for one IG post"""
    try:
        url = f"{META_BASE_URL}/{post_id}/comments"
        response = requests.get(
            url,
            params={
                'fields': 'id,text,username,timestamp',
                'limit': MAX_COMMENTS_PER_POST,
                'access_token': ACCESS_TOKEN
            },
            timeout=REQUEST_TIMEOUT
        )

        if response.status_code == 200:
            return response.json().get('data', [])
        else:
            logger.warning(f"⚠️  IG comments failed for {post_id}: {response.status_code}")
            return []

    except Exception as e:
        logger.error(f"❌ IG comments error: {e}")
        return []


def fetch_ig_new_comments() -> list:
    """Fetch new unreplied IG comments"""
    logger.info("📸 Fetching Instagram comments...")
    
    posts = _get_recent_ig_posts()
    new_comments = []

    for post in posts:
        post_id = post.get('id', '')
        post_time = post.get('timestamp', '')
        
        # 72 hour old posts ke comments skip karo
        if post_time and not _is_recent(post_time, hours=72):
            logger.debug(f"   ⏭️  Old post skip: {post_id}")
            continue
        
        comments = _get_ig_comments(post_id)
        logger.debug(f"   Post {post_id}: {len(comments)} comments fetched")

        for comment in comments:
            comment_id = comment.get('id', '')
            text = comment.get('text', '')
            username = comment.get('username', '')
            timestamp = comment.get('timestamp', '')

            if not comment_id:
                continue

            # Recent comments hi process karo (48h)
            if not _is_recent(timestamp, hours=48):
                continue

            # Spam check
            if _is_spam(text):
                logger.debug(f"   🚫 Spam: {text[:30]}")
                continue

            # Worth replying check
            if not _is_worth_replying(text):
                logger.debug(f"   ⏭️  Not worth: {text[:30]}")
                continue

            # ATOMIC: Check + Save ek saath
            # Yahi main fix hai - agar already hai to False return hoga
            is_new = _check_and_save_comment(
                "instagram", post_id, comment_id, text, username
            )
            
            if not is_new:
                continue  # Already processed

            new_comments.append({
                "platform": "instagram",
                "post_id": post_id,
                "comment_id": comment_id,
                "text": text,
                "username": username,
                "timestamp": timestamp
            })

        time.sleep(0.5)  # Rate limit

    logger.info(f"📸 IG: {len(new_comments)} new comments")
    return new_comments


# ============================================================
# FACEBOOK
# ============================================================

def _get_recent_fb_posts(limit: int = MAX_POSTS_TO_CHECK) -> list:
    """Get recent FB posts"""
    try:
        url = f"{META_BASE_URL}/{FACEBOOK_PAGE_ID}/posts"
        response = requests.get(
            url,
            params={
                'fields': 'id,message,created_time',
                'limit': limit,
                'access_token': ACCESS_TOKEN
            },
            timeout=REQUEST_TIMEOUT
        )

        if response.status_code == 200:
            posts = response.json().get('data', [])
            logger.info(f"📘 Found {len(posts)} recent FB posts")
            return posts
        else:
            logger.warning(f"⚠️  FB posts fetch failed: {response.status_code}")
            return []

    except Exception as e:
        logger.error(f"❌ FB posts error: {e}")
        return []


def _get_fb_comments(post_id: str) -> list:
    """Get comments for one FB post"""
    try:
        url = f"{META_BASE_URL}/{post_id}/comments"
        response = requests.get(
            url,
            params={
                'fields': 'id,message,from{name},created_time',
                'limit': MAX_COMMENTS_PER_POST,
                'access_token': ACCESS_TOKEN
            },
            timeout=REQUEST_TIMEOUT
        )

        if response.status_code == 200:
            return response.json().get('data', [])
        else:
            logger.warning(f"⚠️  FB comments failed for {post_id}: {response.status_code}")
            return []

    except Exception as e:
        logger.error(f"❌ FB comments error: {e}")
        return []


def fetch_fb_new_comments() -> list:
    """Fetch new unreplied FB comments"""
    logger.info("📘 Fetching Facebook comments...")

    posts = _get_recent_fb_posts()
    new_comments = []

    for post in posts:
        post_id = post.get('id', '')
        post_time = post.get('created_time', '')
        
        if post_time and not _is_recent(post_time, hours=72):
            logger.debug(f"   ⏭️  Old post skip: {post_id}")
            continue

        comments = _get_fb_comments(post_id)
        logger.debug(f"   Post {post_id}: {len(comments)} comments fetched")

        for comment in comments:
            comment_id = comment.get('id', '')
            text = comment.get('message', '')
            from_data = comment.get('from', {})
            username = from_data.get('name', 'Unknown')
            timestamp = comment.get('created_time', '')

            if not comment_id:
                continue

            if not _is_recent(timestamp, hours=48):
                continue

            if _is_spam(text):
                continue

            if not _is_worth_replying(text):
                continue

            # ATOMIC check + save
            is_new = _check_and_save_comment(
                "facebook", post_id, comment_id, text, username
            )
            
            if not is_new:
                continue

            new_comments.append({
                "platform": "facebook",
                "post_id": post_id,
                "comment_id": comment_id,
                "text": text,
                "username": username,
                "timestamp": timestamp
            })

        time.sleep(0.5)

    logger.info(f"📘 FB: {len(new_comments)} new comments")
    return new_comments


# ============================================================
# YOUTUBE
# ============================================================

def fetch_yt_new_comments() -> list:
    """Fetch new unreplied YouTube comments"""
    if not YOUTUBE_ENABLED:
        logger.info("📺 YouTube disabled, skipping")
        return []

    logger.info("📺 Fetching YouTube comments...")

    try:
        from posting.youtube import _get_youtube_client

        youtube = _get_youtube_client()

        search_response = youtube.search().list(
            part="id",
            channelId=YOUTUBE_CHANNEL_ID,
            maxResults=MAX_POSTS_TO_CHECK,
            order="date",
            type="video"
        ).execute()

        video_ids = [
            item['id']['videoId']
            for item in search_response.get('items', [])
            if item.get('id', {}).get('videoId')
        ]

        if not video_ids:
            logger.info("📺 No recent YT videos found")
            return []

        new_comments = []

        for video_id in video_ids:
            try:
                comment_response = youtube.commentThreads().list(
                    part="snippet",
                    videoId=video_id,
                    maxResults=MAX_COMMENTS_PER_POST,
                    order="time"
                ).execute()

                for item in comment_response.get('items', []):
                    snippet = item['snippet']['topLevelComment']['snippet']
                    comment_id = item['id']
                    text = snippet.get('textDisplay', '')
                    username = snippet.get('authorDisplayName', 'Unknown')
                    timestamp = snippet.get('publishedAt', '')

                    if not _is_recent(timestamp, hours=48):
                        continue

                    if _is_spam(text):
                        continue

                    if not _is_worth_replying(text):
                        continue

                    # ATOMIC check + save
                    is_new = _check_and_save_comment(
                        "youtube", video_id, comment_id, text, username
                    )
                    
                    if not is_new:
                        continue

                    new_comments.append({
                        "platform": "youtube",
                        "post_id": video_id,
                        "comment_id": comment_id,
                        "text": text,
                        "username": username,
                        "timestamp": timestamp
                    })

                time.sleep(0.5)

            except Exception as e:
                logger.warning(f"⚠️  YT video {video_id} failed: {e}")
                continue

        logger.info(f"📺 YT: {len(new_comments)} new comments")
        return new_comments

    except ImportError:
        logger.warning("⚠️  YouTube module not available")
        return []
    except Exception as e:
        logger.error(f"❌ YouTube comments error: {e}")
        return []


# ============================================================
# MAIN
# ============================================================

def fetch_all_new_comments(max_total: int = 20) -> list:
    """Fetch new comments from ALL platforms"""
    logger.info("=" * 55)
    logger.info("=== COMMENT FETCHER START ===")
    logger.info("=" * 55)

    # Ek baar table ensure karo - sab fetch functions se pehle
    _ensure_comment_table()

    all_comments = []

    try:
        ig_comments = fetch_ig_new_comments()
        all_comments.extend(ig_comments)
    except Exception as e:
        logger.error(f"❌ IG fetch failed: {e}")

    try:
        fb_comments = fetch_fb_new_comments()
        all_comments.extend(fb_comments)
    except Exception as e:
        logger.error(f"❌ FB fetch failed: {e}")

    try:
        yt_comments = fetch_yt_new_comments()
        all_comments.extend(yt_comments)
    except Exception as e:
        logger.error(f"❌ YT fetch failed: {e}")

    # Limit
    if len(all_comments) > max_total:
        logger.info(f"📊 Limiting: {len(all_comments)} → {max_total}")
        all_comments = all_comments[:max_total]

    logger.info("=" * 55)
    logger.info(f"✅ TOTAL NEW: {len(all_comments)}")
    logger.info(f"   📸 IG:  {sum(1 for c in all_comments if c['platform'] == 'instagram')}")
    logger.info(f"   📘 FB:  {sum(1 for c in all_comments if c['platform'] == 'facebook')}")
    logger.info(f"   📺 YT:  {sum(1 for c in all_comments if c['platform'] == 'youtube')}")
    logger.info("=" * 55)

    return all_comments


# ============================================================
# REPLY POSTER KE LIYE - IMPORT KARKE USE KARO
# ============================================================

__all__ = [
    'fetch_all_new_comments',
    'fetch_ig_new_comments', 
    'fetch_fb_new_comments',
    'fetch_yt_new_comments',
    'mark_reply_posted',        # ← Reply poster mein call karo
    '_ensure_comment_table',
]


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("COMMENT FETCHER V4 - TEST")
    print("=" * 60 + "\n")

    comments = fetch_all_new_comments(max_total=10)

    print(f"\n📊 Found {len(comments)} new comments:")
    for i, comment in enumerate(comments, 1):
        print(f"\n  [{i}] {comment['platform'].upper()}")
        print(f"      User: @{comment['username']}")
        print(f"      Text: {comment['text'][:80]}")
        print(f"      Time: {comment['timestamp']}")
