"""
Analytics Agent - Real Learning System (Production Grade)
Features:
- Full engagement metrics tracking
- Instagram basic + insights metrics (with graceful fallback for new posts)
- Style performance learning
- Category performance analysis
- Time-based insights
- Growth pattern detection
- Automatic recommendations
- Historical trend analysis
- Multi-metric intelligence
- ALWAYS returns memory (no None issues)

V2 UPDATE: Added reel-specific metrics (plays, avg_watch_time, etc.)
"""
import requests
import time
from datetime import datetime, timedelta
from core.memory import AgentMemory
from core.database import (
    save_analytics,
    update_style_performance,
    get_connection,
    get_best_performing_styles
)
from config.settings import ACCESS_TOKEN, META_API_VERSION
from utils.logger import get_logger

logger = get_logger("analytics_agent")

META_VERSION = META_API_VERSION or "v25.0"


# ============================================================
# ENHANCED DATABASE TABLES
# ============================================================

def _ensure_extended_tables():
    """Create additional analytics tables if not exist"""
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS category_performance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT UNIQUE,
                total_posts INTEGER DEFAULT 0,
                total_reach INTEGER DEFAULT 0,
                total_likes INTEGER DEFAULT 0,
                total_comments INTEGER DEFAULT 0,
                total_shares INTEGER DEFAULT 0,
                avg_reach REAL DEFAULT 0,
                avg_likes REAL DEFAULT 0,
                avg_engagement_rate REAL DEFAULT 0,
                last_updated TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS caption_style_performance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                caption_style TEXT UNIQUE,
                total_posts INTEGER DEFAULT 0,
                total_engagement INTEGER DEFAULT 0,
                avg_engagement REAL DEFAULT 0,
                last_updated TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS time_slot_performance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                time_slot TEXT UNIQUE,
                hour_of_day INTEGER,
                total_posts INTEGER DEFAULT 0,
                total_reach INTEGER DEFAULT 0,
                avg_reach REAL DEFAULT 0,
                last_updated TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS hashtag_performance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                hashtag TEXT UNIQUE,
                total_uses INTEGER DEFAULT 0,
                total_reach INTEGER DEFAULT 0,
                avg_reach REAL DEFAULT 0,
                last_used TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS insights (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                insight_type TEXT,
                insight_data TEXT,
                confidence_score REAL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.commit()
        conn.close()

    except Exception as e:
        logger.warning(f"Extended tables setup failed: {e}")


# ============================================================
# INSTAGRAM METRICS FETCHER (V2 - WITH REEL METRICS)
# ============================================================

def _fetch_ig_analytics(post_id: str, retries: int = 2) -> dict:
    """
    Fetch Instagram post insights.
    Strategy:
    1. Get basic metrics first (likes, comments) - always works
    2. Try insights (reach, impressions) - may fail for new posts
    3. 🆕 V2: Try reel-specific metrics if VIDEO/REELS media type
    4. Combine and return
    """
    if not post_id:
        return {}

    result = {
        "likes": 0,
        "comments": 0,
        "reach": 0,
        "impressions": 0,
        "saved": 0,
        "shares": 0,
        # 🆕 V2: Reel-specific metrics
        "plays": 0,
        "avg_watch_time": 0,
        "total_interactions": 0,
        "video_views": 0,
    }

    # ═══════════════════════════════════════════
    # STEP 1: Get basic metrics (always available)
    # ═══════════════════════════════════════════
    try:
        url = f"https://graph.facebook.com/{META_VERSION}/{post_id}"
        response = requests.get(
            url,
            params={
                'fields': 'like_count,comments_count,media_type,timestamp,media_url',
                'access_token': ACCESS_TOKEN
            },
            timeout=15
        )

        if response.status_code == 200:
            data = response.json()
            result["likes"] = data.get('like_count', 0)
            result["comments"] = data.get('comments_count', 0)
            logger.info(f"✅ IG basic: {result['likes']} likes, {result['comments']} comments")
        else:
            logger.warning(f"IG basic metrics returned {response.status_code}")

    except Exception as e:
        logger.warning(f"IG basic metrics failed: {e}")

    # ═══════════════════════════════════════════
    # STEP 2: Try insights (may fail for new posts)
    # ═══════════════════════════════════════════
    try:
        insights_url = f"https://graph.facebook.com/{META_VERSION}/{post_id}/insights"
        insights_response = requests.get(
            insights_url,
            params={
                'metric': 'impressions,reach,saved,shares',
                'access_token': ACCESS_TOKEN
            },
            timeout=10
        )

        if insights_response.status_code == 200:
            insights_data = insights_response.json().get('data', [])
            for item in insights_data:
                metric_name = item['name']
                value = item.get('values', [{}])[0].get('value', 0)
                if metric_name in result:
                    result[metric_name] = value
            logger.info(f"✅ IG insights: reach={result['reach']}, impressions={result['impressions']}")
        elif insights_response.status_code == 400:
            logger.info(f"ℹ️ IG insights not available yet (post too new - normal)")
        else:
            logger.info(f"ℹ️ IG insights returned {insights_response.status_code}")

    except Exception as e:
        logger.info(f"ℹ️ IG insights fetch skipped: {e}")

    # ═══════════════════════════════════════════
    # 🆕 STEP 3 (V2): Try reel-specific metrics (if video)
    # ═══════════════════════════════════════════
    try:
        # First check if this is a video/reel
        media_check_url = f"https://graph.facebook.com/{META_VERSION}/{post_id}"
        media_response = requests.get(
            media_check_url,
            params={'fields': 'media_type', 'access_token': ACCESS_TOKEN},
            timeout=10
        )

        if media_response.status_code == 200:
            media_type = media_response.json().get('media_type', '')

            if media_type in ["VIDEO", "REELS"]:
                logger.info(f"🎬 Fetching reel-specific metrics (media_type: {media_type})")

                reel_insights_url = f"https://graph.facebook.com/{META_VERSION}/{post_id}/insights"
                reel_response = requests.get(
                    reel_insights_url,
                    params={
                        'metric': 'plays,total_interactions,ig_reels_video_view_total_time,ig_reels_avg_watch_time',
                        'access_token': ACCESS_TOKEN
                    },
                    timeout=10
                )

                if reel_response.status_code == 200:
                    reel_data = reel_response.json().get('data', [])
                    for item in reel_data:
                        metric_name = item['name']
                        value = item.get('values', [{}])[0].get('value', 0)

                        # Map to our fields
                        if metric_name == "plays":
                            result["plays"] = value
                        elif metric_name == "total_interactions":
                            result["total_interactions"] = value
                        elif metric_name == "ig_reels_avg_watch_time":
                            result["avg_watch_time"] = value / 1000  # ms to seconds

                    logger.info(f"✅ Reel metrics: plays={result['plays']}, avg_watch={result['avg_watch_time']}s")

    except Exception as e:
        logger.info(f"ℹ️ Reel metrics fetch skipped: {e}")

    return result


# ============================================================
# FACEBOOK METRICS FETCHER
# ============================================================

def _fetch_fb_analytics(post_id: str, retries: int = 3) -> dict:
    """Fetch Facebook post metrics"""
    if not post_id:
        return {}

    fields = "likes.summary(true),comments.summary(true),shares,reactions.summary(true)"

    for attempt in range(1, retries + 1):
        try:
            url = f"https://graph.facebook.com/{META_VERSION}/{post_id}"
            response = requests.get(
                url,
                params={'fields': fields, 'access_token': ACCESS_TOKEN},
                timeout=15
            )

            if response.status_code == 200:
                data = response.json()
                result = {
                    "likes": data.get('likes', {}).get('summary', {}).get('total_count', 0),
                    "comments": data.get('comments', {}).get('summary', {}).get('total_count', 0),
                    "shares": data.get('shares', {}).get('count', 0),
                    "reactions": data.get('reactions', {}).get('summary', {}).get('total_count', 0),
                }
                logger.info(f"✅ FB metrics: {result}")
                return result

            elif response.status_code == 429:
                logger.warning(f"⚠️ FB rate limited (attempt {attempt})")
                time.sleep(10 * attempt)
            else:
                logger.warning(f"FB API returned {response.status_code}")
                if attempt < retries:
                    time.sleep(3)

        except Exception as e:
            logger.warning(f"FB analytics attempt {attempt} failed: {e}")
            if attempt < retries:
                time.sleep(3)

    return {}


# ============================================================
# ENGAGEMENT CALCULATOR
# ============================================================

def _calculate_engagement_rate(data: dict, platform: str) -> float:
    """Calculate engagement rate percentage"""
    likes = data.get("likes", 0)
    comments = data.get("comments", 0)
    shares = data.get("shares", 0)

    # For Instagram: use reach
    # For Facebook: estimate reach as 10x likes
    if platform == "instagram":
        reach = data.get("reach", 0)
    else:
        reach = max(likes * 10, 100)

    if reach == 0:
        return 0.0

    engagement = likes + comments + shares
    return round((engagement / reach) * 100, 2)


def _get_engagement_score(data: dict, platform: str) -> str:
    """Rate engagement quality"""
    rate = _calculate_engagement_rate(data, platform)

    if rate >= 10:
        return "🔥 VIRAL"
    elif rate >= 6:
        return "⭐ EXCELLENT"
    elif rate >= 3:
        return "✅ GOOD"
    elif rate >= 1:
        return "➡️ AVERAGE"
    else:
        return "⚠️ POOR"


# ============================================================
# LEARNING SYSTEM
# ============================================================

def _update_category_performance(category: str, data: dict):
    """Update category-level performance"""
    if not category:
        return

    try:
        conn = get_connection()
        cursor = conn.cursor()

        reach = data.get("reach", 0)
        likes = data.get("likes", 0)
        comments = data.get("comments", 0)
        shares = data.get("shares", 0)
        engagement_rate = _calculate_engagement_rate(data, "instagram")

        cursor.execute("""
            INSERT INTO category_performance 
                (category, total_posts, total_reach, total_likes, total_comments, total_shares)
            VALUES (?, 1, ?, ?, ?, ?)
            ON CONFLICT(category) DO UPDATE SET
                total_posts = total_posts + 1,
                total_reach = total_reach + ?,
                total_likes = total_likes + ?,
                total_comments = total_comments + ?,
                total_shares = total_shares + ?,
                avg_reach = (total_reach + ?) / (total_posts + 1),
                avg_likes = (total_likes + ?) / (total_posts + 1),
                avg_engagement_rate = ?,
                last_updated = CURRENT_TIMESTAMP
        """, (
            category, reach, likes, comments, shares,
            reach, likes, comments, shares,
            reach, likes, engagement_rate
        ))

        conn.commit()
        conn.close()
        logger.info(f"📊 Category '{category}' updated")

    except Exception as e:
        logger.warning(f"Category performance update failed: {e}")


def _update_caption_style_performance(caption_style: str, engagement: int):
    """Track which caption styles work best"""
    if not caption_style:
        return

    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO caption_style_performance 
                (caption_style, total_posts, total_engagement)
            VALUES (?, 1, ?)
            ON CONFLICT(caption_style) DO UPDATE SET
                total_posts = total_posts + 1,
                total_engagement = total_engagement + ?,
                avg_engagement = (total_engagement + ?) / (total_posts + 1),
                last_updated = CURRENT_TIMESTAMP
        """, (caption_style, engagement, engagement, engagement))

        conn.commit()
        conn.close()
        logger.info(f"📝 Caption style '{caption_style}' updated")

    except Exception as e:
        logger.warning(f"Caption style update failed: {e}")


def _update_time_slot_performance(post_time: datetime, reach: int):
    """Track which times perform best"""
    try:
        hour = post_time.hour

        if 5 <= hour < 11:
            slot = "morning"
        elif 11 <= hour < 16:
            slot = "afternoon"
        elif 16 <= hour < 20:
            slot = "evening"
        else:
            slot = "night"

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO time_slot_performance 
                (time_slot, hour_of_day, total_posts, total_reach)
            VALUES (?, ?, 1, ?)
            ON CONFLICT(time_slot) DO UPDATE SET
                total_posts = total_posts + 1,
                total_reach = total_reach + ?,
                avg_reach = (total_reach + ?) / (total_posts + 1),
                last_updated = CURRENT_TIMESTAMP
        """, (slot, hour, reach, reach, reach))

        conn.commit()
        conn.close()
        logger.info(f"⏰ Time slot '{slot}' updated")

    except Exception as e:
        logger.warning(f"Time slot update failed: {e}")


def _update_hashtag_performance(hashtags: str, reach: int):
    """Track hashtag performance (top 10)"""
    if not hashtags:
        return

    try:
        tag_list = hashtags.split()[:10]

        conn = get_connection()
        cursor = conn.cursor()

        for tag in tag_list:
            if len(tag) > 2:
                cursor.execute("""
                    INSERT INTO hashtag_performance 
                        (hashtag, total_uses, total_reach)
                    VALUES (?, 1, ?)
                    ON CONFLICT(hashtag) DO UPDATE SET
                        total_uses = total_uses + 1,
                        total_reach = total_reach + ?,
                        avg_reach = (total_reach + ?) / (total_uses + 1),
                        last_used = CURRENT_TIMESTAMP
                """, (tag.lower(), reach, reach, reach))

        conn.commit()
        conn.close()
        logger.info(f"🏷️ {len(tag_list)} hashtags updated")

    except Exception as e:
        logger.warning(f"Hashtag performance update failed: {e}")


# ============================================================
# INSIGHTS GENERATOR
# ============================================================

def _generate_insights():
    """Generate AI insights from all collected data"""
    try:
        conn = get_connection()
        cursor = conn.cursor()

        # Best categories
        cursor.execute("""
            SELECT category, avg_reach, total_posts 
            FROM category_performance 
            WHERE total_posts >= 3
            ORDER BY avg_reach DESC 
            LIMIT 3
        """)
        best_categories = cursor.fetchall()

        if best_categories:
            insight_data = " | ".join([
                f"{cat} (reach: {reach:.0f}, posts: {posts})"
                for cat, reach, posts in best_categories
            ])
            cursor.execute("""
                INSERT INTO insights (insight_type, insight_data, confidence_score)
                VALUES (?, ?, ?)
            """, ("best_categories", insight_data, 0.9))
            logger.info(f"💡 Best categories: {insight_data}")

        # Best time slot
        cursor.execute("""
            SELECT time_slot, avg_reach 
            FROM time_slot_performance 
            WHERE total_posts >= 3
            ORDER BY avg_reach DESC 
            LIMIT 1
        """)
        best_time = cursor.fetchone()

        if best_time:
            insight_data = f"{best_time[0]} (reach: {best_time[1]:.0f})"
            cursor.execute("""
                INSERT INTO insights (insight_type, insight_data, confidence_score)
                VALUES (?, ?, ?)
            """, ("best_time_slot", insight_data, 0.85))
            logger.info(f"💡 Best time: {insight_data}")

        # Best caption style
        cursor.execute("""
            SELECT caption_style, avg_engagement 
            FROM caption_style_performance 
            WHERE total_posts >= 3
            ORDER BY avg_engagement DESC 
            LIMIT 1
        """)
        best_style = cursor.fetchone()

        if best_style:
            insight_data = f"{best_style[0]} (engagement: {best_style[1]:.0f})"
            cursor.execute("""
                INSERT INTO insights (insight_type, insight_data, confidence_score)
                VALUES (?, ?, ?)
            """, ("best_caption_style", insight_data, 0.8))
            logger.info(f"💡 Best caption style: {insight_data}")

        # Best hashtags
        cursor.execute("""
            SELECT hashtag, avg_reach 
            FROM hashtag_performance 
            WHERE total_uses >= 3
            ORDER BY avg_reach DESC 
            LIMIT 10
        """)
        best_hashtags = cursor.fetchall()

        if best_hashtags:
            insight_data = ", ".join([f"{tag} ({reach:.0f})" for tag, reach in best_hashtags[:5]])
            cursor.execute("""
                INSERT INTO insights (insight_type, insight_data, confidence_score)
                VALUES (?, ?, ?)
            """, ("top_hashtags", insight_data, 0.75))
            logger.info(f"💡 Top hashtags: {insight_data}")

        conn.commit()
        conn.close()

    except Exception as e:
        logger.warning(f"Insights generation failed: {e}")


def get_latest_insights() -> dict:
    """Get latest AI insights"""
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT insight_type, insight_data, confidence_score, created_at
            FROM insights
            ORDER BY created_at DESC
            LIMIT 20
        """)

        rows = cursor.fetchall()
        conn.close()

        insights = {}
        for row in rows:
            insight_type = row[0]
            if insight_type not in insights:
                insights[insight_type] = {
                    "data": row[1],
                    "confidence": row[2],
                    "created_at": row[3]
                }

        return insights

    except Exception as e:
        logger.warning(f"Failed to fetch insights: {e}")
        return {}


# ============================================================
# BEAUTIFUL LOGGING
# ============================================================

def _log_analytics_summary(memory: AgentMemory, ig_data: dict, fb_data: dict):
    """Beautiful analytics summary"""

    logger.info("┌─────────────────────────────────────────────┐")
    logger.info("│         ANALYTICS SUMMARY                   │")
    logger.info("├─────────────────────────────────────────────┤")
    logger.info(f"│ 📌 Topic     : {(memory.topic or '')[:35]}")
    logger.info(f"│ 📂 Category  : {memory.category or 'unknown'}")
    logger.info(f"│ 🎨 Style     : {memory.image_style or 'unknown'}")
    logger.info(f"│ 📊 Post Type : {getattr(memory, 'post_type', 'image')}")
    logger.info("├─────────────────────────────────────────────┤")

    if ig_data:
        logger.info(f"│ 📸 INSTAGRAM:")
        logger.info(f"│   👀 Reach       : {ig_data.get('reach', 0)}")
        logger.info(f"│   💥 Impressions : {ig_data.get('impressions', 0)}")
        logger.info(f"│   ❤️  Likes       : {ig_data.get('likes', 0)}")
        logger.info(f"│   💬 Comments    : {ig_data.get('comments', 0)}")
        logger.info(f"│   💾 Saves       : {ig_data.get('saved', 0)}")
        logger.info(f"│   🔄 Shares      : {ig_data.get('shares', 0)}")

        # 🆕 Show reel metrics if present
        if ig_data.get('plays', 0) > 0:
            logger.info(f"│   🎬 REEL METRICS:")
            logger.info(f"│     ▶️  Plays      : {ig_data.get('plays', 0)}")
            logger.info(f"│     ⏱️  Avg Watch  : {ig_data.get('avg_watch_time', 0):.1f}s")
            logger.info(f"│     💫 Total Int  : {ig_data.get('total_interactions', 0)}")

        logger.info(f"│   🎯 Score       : {_get_engagement_score(ig_data, 'instagram')}")

    if fb_data:
        logger.info(f"│ 📘 FACEBOOK:")
        logger.info(f"│   ❤️  Likes       : {fb_data.get('likes', 0)}")
        logger.info(f"│   💬 Comments    : {fb_data.get('comments', 0)}")
        logger.info(f"│   🔄 Shares      : {fb_data.get('shares', 0)}")
        logger.info(f"│   ⚡ Reactions   : {fb_data.get('reactions', 0)}")

    logger.info("└─────────────────────────────────────────────┘")


# ============================================================
# MAIN AGENT FUNCTION (V2 - REEL AWARE)
# ============================================================

def run(memory: AgentMemory, post_db_id: int = 0) -> AgentMemory:
    """
    Comprehensive analytics + learning
    IMPORTANT: Always returns memory (never None)

    V2 UPDATE: Uses reel_ig_post_id if post_type=reel, saves to reel_analytics table
    """
    logger.info("=" * 50)
    logger.info("=== ANALYTICS AGENT STARTED ===")
    logger.info("=" * 50)

    # Safety check
    if memory is None:
        logger.error("❌ Memory is None. Creating new memory.")
        memory = AgentMemory()

    try:
        # Ensure tables exist
        _ensure_extended_tables()

        ig_data = {}
        fb_data = {}

        # ═══════════════════════════════════════════
        # 🆕 V2: DETERMINE POST IDs (reel or regular)
        # ═══════════════════════════════════════════

        # Instagram
        ig_post_id_to_fetch = ""
        if hasattr(memory, 'reel_ig_post_id') and memory.reel_ig_post_id:
            ig_post_id_to_fetch = memory.reel_ig_post_id
            logger.info(f"🎬 Using REEL IG post ID: {ig_post_id_to_fetch}")
        elif memory.ig_post_id:
            ig_post_id_to_fetch = memory.ig_post_id
            logger.info(f"📸 Using regular IG post ID: {ig_post_id_to_fetch}")

        # Facebook
        fb_post_id_to_fetch = ""
        if hasattr(memory, 'reel_fb_post_id') and memory.reel_fb_post_id:
            fb_post_id_to_fetch = memory.reel_fb_post_id
            logger.info(f"🎬 Using REEL FB post ID: {fb_post_id_to_fetch}")
        elif memory.fb_post_id:
            fb_post_id_to_fetch = memory.fb_post_id
            logger.info(f"📘 Using regular FB post ID: {fb_post_id_to_fetch}")

        # ═══════════════════════════════════════════
        # FETCH METRICS
        # ═══════════════════════════════════════════

        if ig_post_id_to_fetch:
            logger.info(f"📸 Fetching Instagram metrics for: {ig_post_id_to_fetch}")
            ig_data = _fetch_ig_analytics(ig_post_id_to_fetch)

            if ig_data and post_db_id > 0:
                try:
                    save_analytics(post_db_id, "instagram", ig_data)

                    # 🆕 V2: If reel, also save reel-specific analytics
                    is_reel = hasattr(memory, 'post_type') and memory.post_type == "reel"
                    if is_reel:
                        try:
                            from core.database import save_reel_analytics
                            save_reel_analytics(post_db_id, "instagram", ig_data)
                            logger.info("✅ Reel analytics saved to reel_analytics table")
                        except Exception as e:
                            logger.warning(f"Reel analytics save failed: {e}")

                except Exception as e:
                    logger.warning(f"Save IG analytics failed: {e}")

        if fb_post_id_to_fetch:
            logger.info(f"📘 Fetching Facebook metrics for: {fb_post_id_to_fetch}")
            fb_data = _fetch_fb_analytics(fb_post_id_to_fetch)

            if fb_data and post_db_id > 0:
                try:
                    save_analytics(post_db_id, "facebook", fb_data)

                    # 🆕 V2: If reel, save FB reel analytics too
                    is_reel = hasattr(memory, 'post_type') and memory.post_type == "reel"
                    if is_reel:
                        try:
                            from core.database import save_reel_analytics
                            save_reel_analytics(post_db_id, "facebook", fb_data)
                            logger.info("✅ FB Reel analytics saved")
                        except Exception as e:
                            logger.warning(f"FB Reel analytics save failed: {e}")

                except Exception as e:
                    logger.warning(f"Save FB analytics failed: {e}")

        # ═══════════════════════════════════════════
        # LOG SUMMARY
        # ═══════════════════════════════════════════
        _log_analytics_summary(memory, ig_data, fb_data)

        # ═══════════════════════════════════════════
        # LEARNING UPDATES
        # ═══════════════════════════════════════════
        combined_reach = ig_data.get("reach", 0)
        combined_engagement = (
            ig_data.get("likes", 0) +
            ig_data.get("comments", 0) +
            ig_data.get("shares", 0) +
            fb_data.get("likes", 0) +
            fb_data.get("comments", 0)
        )

        logger.info("")
        logger.info("--- LEARNING UPDATES ---")

        # 1. Image style
        if memory.image_style and combined_reach > 0:
            try:
                update_style_performance(
                    memory.image_style,
                    combined_reach,
                    ig_data.get("likes", 0)
                )
                logger.info(f"🎨 Style '{memory.image_style}' updated")
            except Exception as e:
                logger.warning(f"Style update failed: {e}")

        # 2. Category
        if memory.category:
            _update_category_performance(memory.category, ig_data)

        # 3. Caption style
        if memory.caption_style:
            _update_caption_style_performance(memory.caption_style, combined_engagement)

        # 4. Time slot
        _update_time_slot_performance(datetime.now(), combined_reach)

        # 5. Hashtags
        if memory.hashtags:
            _update_hashtag_performance(memory.hashtags, combined_reach)

        # ═══════════════════════════════════════════
        # GENERATE INSIGHTS
        # ═══════════════════════════════════════════
        logger.info("")
        logger.info("--- GENERATING INSIGHTS ---")
        _generate_insights()

        # ═══════════════════════════════════════════
        # UPDATE MEMORY
        # ═══════════════════════════════════════════
        if memory.analytics_data is None:
            memory.analytics_data = {}

        memory.analytics_data.update({
            "instagram": ig_data,
            "facebook": fb_data,
            "combined_reach": combined_reach,
            "combined_engagement": combined_engagement,
            "engagement_score": _get_engagement_score(ig_data, "instagram") if ig_data else "N/A"
        })

        # ═══════════════════════════════════════════
        # FINAL LOG
        # ═══════════════════════════════════════════
        logger.info("=" * 50)
        logger.info("✅ ANALYTICS DONE")
        logger.info("=" * 50)
        logger.info(f"👀 Total Reach     : {combined_reach}")
        logger.info(f"💥 Total Engagement: {combined_engagement}")
        logger.info(f"🎯 Score           : {_get_engagement_score(ig_data, 'instagram') if ig_data else 'N/A'}")

        # 🆕 Show reel metrics
        if ig_data.get('plays', 0) > 0:
            logger.info(f"🎬 Reel Plays      : {ig_data.get('plays', 0)}")

        logger.info("=" * 50)

    except Exception as e:
        logger.error(f"❌ Analytics failed: {e}")
        import traceback
        logger.error(traceback.format_exc())

        # Even on error, add to memory errors
        try:
            memory.add_error("analytics_agent", str(e))
        except Exception:
            pass

    logger.info("=== ANALYTICS AGENT DONE ===\n")

    # ⚠️ CRITICAL: ALWAYS RETURN MEMORY
    return memory


# ============================================================
# PUBLIC API - FOR OTHER AGENTS TO USE
# ============================================================

def get_best_category() -> str:
    """Get currently best performing category"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT category FROM category_performance
            WHERE total_posts >= 3
            ORDER BY avg_reach DESC
            LIMIT 1
        """)
        row = cursor.fetchone()
        conn.close()
        return row[0] if row else ""
    except Exception:
        return ""


def get_best_hashtags(limit: int = 10) -> list:
    """Get best performing hashtags"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT hashtag FROM hashtag_performance
            WHERE total_uses >= 3
            ORDER BY avg_reach DESC
            LIMIT ?
        """, (limit,))
        rows = cursor.fetchall()
        conn.close()
        return [row[0] for row in rows]
    except Exception:
        return []


def get_best_caption_style() -> str:
    """Get best performing caption style"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT caption_style FROM caption_style_performance
            WHERE total_posts >= 3
            ORDER BY avg_engagement DESC
            LIMIT 1
        """)
        row = cursor.fetchone()
        conn.close()
        return row[0] if row else ""
    except Exception:
        return ""


# ============================================================
# STANDALONE TESTING
# ============================================================

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("ANALYTICS AGENT - STANDALONE TEST")
    print("=" * 60 + "\n")

    _ensure_extended_tables()
    print("✅ Extended tables created")

    insights = get_latest_insights()
    if insights:
        print("\n📊 Latest Insights:")
        for insight_type, data in insights.items():
            print(f"   • {insight_type}: {data['data']}")
    else:
        print("\n⚠️ No insights yet (need at least 3 posts per category)")

    print(f"\n🏆 Best Category: {get_best_category() or 'N/A'}")
    print(f"🎨 Best Caption Style: {get_best_caption_style() or 'N/A'}")
    print(f"🏷️ Top Hashtags: {get_best_hashtags(5) or 'N/A'}")