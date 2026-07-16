"""
Comment Fetcher - Fetch new comments from Instagram, Facebook, YouTube

V3 Features:
- Fetches comments from last 24 hours posts
- Filters out already-replied comments
- Detects spam/bot comments
- Returns clean list for reply generation
- Rate limit aware
"""
import time
import requests
from datetime import datetime, timedelta
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
MAX_POSTS_TO_CHECK = 5       # Check last 5 posts
MAX_COMMENTS_PER_POST = 20   # Max comments to fetch per post
REQUEST_TIMEOUT = 15
SPAM_KEYWORDS = [
    "follow me", "check my", "visit my", "dm me",
    "click link", "free money", "earn money",
    "whatsapp", "telegram group", "join now",
    "s3x", "adult", "dating"
]


# ============================================================
# COMMENT HISTORY (Prevent Double Reply)
# ============================================================

def _ensure_comment_table():
    """Create comment tracking table"""
    try:
        conn = get_connection()
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
        conn.commit()
        conn.close()
    except Exception as e:
        logger.warning(f"⚠️  Comment table setup failed: {e}")


def _is_already_replied(comment_id: str) -> bool:
    """Check if we already replied OR even FETCHED this comment before"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        # V4 FIX: Check if comment EXISTS in table at all (fetched = already processed)
        cursor.execute(
            "SELECT id, reply_posted FROM comment_replies WHERE comment_id = ? LIMIT 1",
            (comment_id,)
        )
        result = cursor.fetchone()
        conn.close()

        if result is not None:
            logger.debug(f"   ⏭️  Already processed: {comment_id[:15]}... (posted: {result[1]})")
            return True

        return False
    except Exception as e:
        logger.warning(f"   ⚠️  Reply check failed: {e}")
        return False  # If DB fails, allow (better than missing)


def _save_comment(platform: str, post_id: str, comment_id: str,
                  comment_text: str, commenter_name: str):
    """Save comment to tracking table"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR IGNORE INTO comment_replies
            (platform, post_id, comment_id, comment_text, commenter_name)
            VALUES (?, ?, ?, ?, ?)
        """, (platform, post_id, comment_id, comment_text, commenter_name))
        conn.commit()
        conn.close()
    except Exception as e:
        logger.warning(f"⚠️  Comment save failed: {e}")


# ============================================================
# SPAM DETECTION
# ============================================================

def _is_spam(comment_text: str) -> bool:
    """Detect spam/bot comments"""
    if not comment_text:
        return True

    text_lower = comment_text.lower()

    # Too short (just emojis or single word)
    clean_text = ''.join(c for c in text_lower if c.isalpha())
    if len(clean_text) < 2:
        return False  # Emoji-only = not spam, just skip reply

    # Spam keywords
    for keyword in SPAM_KEYWORDS:
        if keyword in text_lower:
            return True

    # Too many URLs
    if text_lower.count("http") > 1:
        return True

    # Repeated characters (like "aaaaaaa")
    for i in range(len(text_lower) - 5):
        if len(set(text_lower[i:i+6])) == 1:
            return True

    return False


def _is_worth_replying(comment_text: str) -> bool:
    """
    Check if comment deserves a reply.

    Skip:
    - Empty/very short
    - Just emojis (no text)
    - Single word like "nice"

    Reply to:
    - Questions
    - Praise (2+ words)
    - Deity names mentioned
    - Personal stories/experiences
    """
    if not comment_text:
        return False

    # Remove emojis for word count
    import re
    clean = re.sub(
        r'[\U0001F600-\U0001F9FF\U00002600-\U000027BF\U0001F300-\U0001F5FF]',
        '', comment_text
    ).strip()

    # Less than 2 meaningful characters = not worth
    if len(clean) < 2:
        return False

    # Questions always worth replying
    if '?' in comment_text:
        return True

    # Hindi text (Devanagari) = engaged audience
    devanagari = sum(1 for c in comment_text if '\u0900' <= c <= '\u097F')
    if devanagari > 3:
        return True

    # Multiple words = engaged
    words = clean.split()
    if len(words) >= 2:
        return True

    return False


# ============================================================
# INSTAGRAM COMMENTS
# ============================================================

def _get_recent_ig_posts(limit: int = MAX_POSTS_TO_CHECK) -> list:
    """Get recent IG posts (last 24-48 hours)"""
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
            logger.warning(f"⚠️  IG posts fetch failed: {response.status_code}")
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
            comments = response.json().get('data', [])
            return comments
        else:
            logger.warning(f"⚠️  IG comments fetch failed for {post_id}: {response.status_code}")
            return []

    except Exception as e:
        logger.error(f"❌ IG comments error: {e}")
        return []


def fetch_ig_new_comments() -> list:
    """
    Fetch all NEW (unreplied) comments from recent IG posts.

    Returns:
        List of comment dicts:
        [{
            "platform": "instagram",
            "post_id": "...",
            "comment_id": "...",
            "text": "...",
            "username": "...",
            "timestamp": "..."
        }]
    """
    logger.info("📸 Fetching Instagram comments...")

    _ensure_comment_table()

    posts = _get_recent_ig_posts()
    new_comments = []

    for post in posts:
        post_id = post.get('id', '')
        comments = _get_ig_comments(post_id)

        for comment in comments:
            comment_id = comment.get('id', '')
            text = comment.get('text', '')
            username = comment.get('username', '')

            # Skip if already replied
            if _is_already_replied(comment_id):
                continue

            # Skip spam
            if _is_spam(text):
                logger.debug(f"   🚫 Spam skipped: {text[:30]}")
                continue

            # Skip not worth replying
            if not _is_worth_replying(text):
                logger.debug(f"   ⏭️  Not worth reply: {text[:30]}")
                continue

            # Save and add to list
            _save_comment("instagram", post_id, comment_id, text, username)

            new_comments.append({
                "platform": "instagram",
                "post_id": post_id,
                "comment_id": comment_id,
                "text": text,
                "username": username,
                "timestamp": comment.get('timestamp', '')
            })

        time.sleep(0.5)  # Rate limit

    logger.info(f"📸 Found {len(new_comments)} new IG comments to reply")
    return new_comments


# ============================================================
# FACEBOOK COMMENTS
# ============================================================

def _get_recent_fb_posts(limit: int = MAX_POSTS_TO_CHECK) -> list:
    """Get recent FB page posts"""
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
            comments = response.json().get('data', [])
            return comments
        else:
            return []

    except Exception as e:
        logger.error(f"❌ FB comments error: {e}")
        return []


def fetch_fb_new_comments() -> list:
    """Fetch NEW unreplied FB comments"""
    logger.info("📘 Fetching Facebook comments...")

    _ensure_comment_table()

    posts = _get_recent_fb_posts()
    new_comments = []

    for post in posts:
        post_id = post.get('id', '')
        comments = _get_fb_comments(post_id)

        for comment in comments:
            comment_id = comment.get('id', '')
            text = comment.get('message', '')
            from_data = comment.get('from', {})
            username = from_data.get('name', 'Unknown')

            if _is_already_replied(comment_id):
                continue

            if _is_spam(text):
                continue

            if not _is_worth_replying(text):
                continue

            _save_comment("facebook", post_id, comment_id, text, username)

            new_comments.append({
                "platform": "facebook",
                "post_id": post_id,
                "comment_id": comment_id,
                "text": text,
                "username": username,
                "timestamp": comment.get('created_time', '')
            })

        time.sleep(0.5)

    logger.info(f"📘 Found {len(new_comments)} new FB comments to reply")
    return new_comments


# ============================================================
# YOUTUBE COMMENTS
# ============================================================

def fetch_yt_new_comments() -> list:
    """Fetch NEW unreplied YouTube comments"""
    if not YOUTUBE_ENABLED:
        logger.info("📺 YouTube disabled, skipping")
        return []

    logger.info("📺 Fetching YouTube comments...")

    _ensure_comment_table()

    try:
        from posting.youtube import _get_youtube_client

        youtube = _get_youtube_client()

        # Get recent videos (last 5)
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
                # Get comments for this video
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

                    if _is_already_replied(comment_id):
                        continue

                    if _is_spam(text):
                        continue

                    if not _is_worth_replying(text):
                        continue

                    _save_comment("youtube", video_id, comment_id, text, username)

                    new_comments.append({
                        "platform": "youtube",
                        "post_id": video_id,
                        "comment_id": comment_id,
                        "text": text,
                        "username": username,
                        "timestamp": snippet.get('publishedAt', '')
                    })

                time.sleep(0.5)

            except Exception as e:
                logger.warning(f"⚠️  YT video {video_id} comments failed: {e}")
                continue

        logger.info(f"📺 Found {len(new_comments)} new YT comments to reply")
        return new_comments

    except ImportError:
        logger.warning("⚠️  YouTube module not available")
        return []
    except Exception as e:
        logger.error(f"❌ YouTube comments error: {e}")
        return []


# ============================================================
# MAIN: FETCH ALL COMMENTS
# ============================================================

def fetch_all_new_comments(max_total: int = 20) -> list:
    """
    Fetch new comments from ALL platforms.

    Args:
        max_total: Maximum total comments to process (rate limit)

    Returns:
        List of comment dicts, sorted by timestamp (newest first)
    """
    logger.info("=" * 55)
    logger.info("=== COMMENT FETCHER शुरू ===")
    logger.info("=" * 55)

    all_comments = []

    # Instagram
    try:
        ig_comments = fetch_ig_new_comments()
        all_comments.extend(ig_comments)
    except Exception as e:
        logger.error(f"❌ IG fetch failed: {e}")

    # Facebook
    try:
        fb_comments = fetch_fb_new_comments()
        all_comments.extend(fb_comments)
    except Exception as e:
        logger.error(f"❌ FB fetch failed: {e}")

    # YouTube
    try:
        yt_comments = fetch_yt_new_comments()
        all_comments.extend(yt_comments)
    except Exception as e:
        logger.error(f"❌ YT fetch failed: {e}")

    # Limit total
    if len(all_comments) > max_total:
        logger.info(f"📊 Limiting to {max_total} comments (found {len(all_comments)})")
        all_comments = all_comments[:max_total]

    logger.info("=" * 55)
    logger.info(f"✅ TOTAL NEW COMMENTS: {len(all_comments)}")
    logger.info(f"   📸 Instagram: {sum(1 for c in all_comments if c['platform'] == 'instagram')}")
    logger.info(f"   📘 Facebook:  {sum(1 for c in all_comments if c['platform'] == 'facebook')}")
    logger.info(f"   📺 YouTube:   {sum(1 for c in all_comments if c['platform'] == 'youtube')}")
    logger.info("=" * 55)

    return all_comments


# ============================================================
# STANDALONE TEST
# ============================================================

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("COMMENT FETCHER V3 - TEST")
    print("=" * 60 + "\n")

    comments = fetch_all_new_comments(max_total=10)

    print(f"\n📊 Found {len(comments)} new comments:")
    for i, comment in enumerate(comments, 1):
        print(f"\n  [{i}] {comment['platform'].upper()}")
        print(f"      User: @{comment['username']}")
        print(f"      Text: {comment['text'][:80]}")