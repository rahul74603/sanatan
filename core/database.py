"""
SQLite Database - Memory, History, Analytics

V2 UPDATE:
- Added post_type, video_url, yt_post_id columns
- Added reel_analytics table
- Backward-compatible migration for existing databases

V2.1 UPDATE:
- 🆕 Added weekly_schedule table (smart carousel scheduling)
- 🆕 get_todays_content_type() helper
- 🆕 generate_weekly_schedule() - random carousel day picker
- 🆕 get_carousel_days_this_week()
"""
import sqlite3
import random
from datetime import datetime, timedelta
from config.settings import DB_PATH
from utils.logger import get_logger

logger = get_logger("database")


def get_connection():
    return sqlite3.connect(DB_PATH)


def _safe_add_column(cursor, table: str, column: str, definition: str):
    """Safely add column to existing table"""
    try:
        cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
        logger.info(f"✅ Added column: {table}.{column}")
    except sqlite3.OperationalError as e:
        if "duplicate column" in str(e).lower():
            pass
        else:
            logger.warning(f"⚠️  Column add failed for {table}.{column}: {e}")


def initialize_database():
    """Create/migrate all tables"""
    conn = get_connection()
    cursor = conn.cursor()

    # ═══════════════════════════════════════════
    # EXISTING TABLES
    # ═══════════════════════════════════════════

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS post_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            post_date TEXT NOT NULL,
            topic TEXT NOT NULL,
            category TEXT,
            image_style TEXT,
            image_url TEXT,
            caption TEXT,
            hashtags TEXT,
            ig_post_id TEXT,
            fb_post_id TEXT,
            ig_success INTEGER DEFAULT 0,
            fb_success INTEGER DEFAULT 0,
            duration_seconds REAL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # V2 columns
    _safe_add_column(cursor, "post_history", "post_type", "TEXT DEFAULT 'image'")
    _safe_add_column(cursor, "post_history", "video_url", "TEXT DEFAULT ''")
    _safe_add_column(cursor, "post_history", "yt_post_id", "TEXT DEFAULT ''")
    _safe_add_column(cursor, "post_history", "yt_success", "INTEGER DEFAULT 0")
    _safe_add_column(cursor, "post_history", "reel_duration_seconds", "REAL DEFAULT 0")
    _safe_add_column(cursor, "post_history", "reel_scenes_count", "INTEGER DEFAULT 0")

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS analytics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            post_id INTEGER,
            platform TEXT,
            likes INTEGER DEFAULT 0,
            comments INTEGER DEFAULT 0,
            shares INTEGER DEFAULT 0,
            reach INTEGER DEFAULT 0,
            impressions INTEGER DEFAULT 0,
            fetched_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (post_id) REFERENCES post_history(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS style_performance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            image_style TEXT UNIQUE,
            total_posts INTEGER DEFAULT 0,
            total_reach INTEGER DEFAULT 0,
            total_likes INTEGER DEFAULT 0,
            avg_reach REAL DEFAULT 0,
            last_updated TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS used_content (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content_type TEXT,
            content_value TEXT,
            used_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # V2: Reel analytics
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS reel_analytics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            post_id INTEGER,
            platform TEXT,
            plays INTEGER DEFAULT 0,
            reach INTEGER DEFAULT 0,
            avg_watch_time REAL DEFAULT 0,
            total_interactions INTEGER DEFAULT 0,
            saves INTEGER DEFAULT 0,
            shares INTEGER DEFAULT 0,
            comments INTEGER DEFAULT 0,
            likes INTEGER DEFAULT 0,
            completion_rate REAL DEFAULT 0,
            fetched_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (post_id) REFERENCES post_history(id)
        )
    """)

    # ═══════════════════════════════════════════
    # 🆕 V2.1: WEEKLY SCHEDULE TABLE
    # ═══════════════════════════════════════════
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS weekly_schedule (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            week_start_date TEXT UNIQUE NOT NULL,
            week_end_date TEXT NOT NULL,
            carousel_day_1 INTEGER NOT NULL,
            carousel_day_2 INTEGER NOT NULL,
            generated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            notes TEXT DEFAULT ''
        )
    """)

    conn.commit()
    conn.close()
    logger.info("Database initialized successfully")


# ============================================================
# EXISTING FUNCTIONS (Preserved)
# ============================================================

def save_post(data: dict) -> int:
    """Save post to history"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO post_history (
            post_date, topic, category, image_style,
            image_url, caption, hashtags,
            ig_post_id, fb_post_id,
            ig_success, fb_success, duration_seconds,
            post_type, video_url, yt_post_id, yt_success,
            reel_duration_seconds, reel_scenes_count
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        data.get("post_date", datetime.now().isoformat()),
        data.get("topic", ""),
        data.get("category", ""),
        data.get("image_style", ""),
        data.get("image_url", ""),
        data.get("caption", ""),
        data.get("hashtags", ""),
        data.get("ig_post_id", ""),
        data.get("fb_post_id", ""),
        1 if data.get("ig_success") else 0,
        1 if data.get("fb_success") else 0,
        data.get("duration_seconds", 0),
        data.get("post_type", "image"),
        data.get("video_url", ""),
        data.get("yt_post_id", ""),
        1 if data.get("yt_success") else 0,
        data.get("reel_duration_seconds", 0),
        data.get("reel_scenes_count", 0),
    ))

    post_id = cursor.lastrowid
    conn.commit()
    conn.close()

    logger.info(f"Post saved with ID: {post_id}")
    return post_id


def get_recent_topics(limit=20) -> list:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT topic FROM post_history 
        ORDER BY created_at DESC 
        LIMIT ?
    """, (limit,))
    topics = [row[0] for row in cursor.fetchall()]
    conn.close()
    return topics


def save_analytics(post_id: int, platform: str, data: dict):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO analytics (
            post_id, platform, likes, comments,
            shares, reach, impressions
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        post_id, platform,
        data.get("likes", 0), data.get("comments", 0),
        data.get("shares", 0), data.get("reach", 0),
        data.get("impressions", 0)
    ))

    conn.commit()
    conn.close()


def save_reel_analytics(post_id: int, platform: str, data: dict):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO reel_analytics (
            post_id, platform, plays, reach,
            avg_watch_time, total_interactions,
            saves, shares, comments, likes,
            completion_rate
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        post_id, platform,
        data.get("plays", 0), data.get("reach", 0),
        data.get("avg_watch_time", 0),
        data.get("total_interactions", 0),
        data.get("saves", 0), data.get("shares", 0),
        data.get("comments", 0), data.get("likes", 0),
        data.get("completion_rate", 0)
    ))

    conn.commit()
    conn.close()


def update_style_performance(image_style: str, reach: int, likes: int):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO style_performance (image_style, total_posts, total_reach, total_likes)
        VALUES (?, 1, ?, ?)
        ON CONFLICT(image_style) DO UPDATE SET
            total_posts = total_posts + 1,
            total_reach = total_reach + ?,
            total_likes = total_likes + ?,
            avg_reach = (total_reach + ?) / (total_posts + 1),
            last_updated = CURRENT_TIMESTAMP
    """, (image_style, reach, likes, reach, likes, reach))

    conn.commit()
    conn.close()


def get_best_performing_styles(limit=3) -> list:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT image_style, avg_reach, total_posts 
        FROM style_performance 
        WHERE total_posts >= 3
        ORDER BY avg_reach DESC 
        LIMIT ?
    """, (limit,))
    rows = cursor.fetchall()
    conn.close()
    return [{"style": r[0], "avg_reach": r[1], "posts": r[2]} for r in rows]


def mark_content_used(content_type: str, content_value: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO used_content (content_type, content_value)
        VALUES (?, ?)
    """, (content_type, content_value))
    conn.commit()
    conn.close()


def is_content_used(content_type: str, content_value: str) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id FROM used_content 
        WHERE content_type = ? AND content_value = ?
        LIMIT 1
    """, (content_type, content_value))
    result = cursor.fetchone()
    conn.close()
    return result is not None


def get_recent_reels(limit=10) -> list:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, topic, category, reel_duration_seconds,
               ig_success, fb_success, yt_success, created_at
        FROM post_history
        WHERE post_type = 'reel'
        ORDER BY created_at DESC
        LIMIT ?
    """, (limit,))
    rows = cursor.fetchall()
    conn.close()
    return [
        {
            "id": r[0], "topic": r[1], "category": r[2],
            "duration": r[3],
            "ig_success": bool(r[4]), "fb_success": bool(r[5]),
            "yt_success": bool(r[6]), "created_at": r[7]
        }
        for r in rows
    ]


def get_reel_success_rate() -> dict:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT 
            COUNT(*) as total,
            SUM(ig_success) as ig_success_count,
            SUM(fb_success) as fb_success_count,
            SUM(yt_success) as yt_success_count
        FROM post_history
        WHERE post_type = 'reel'
    """)
    row = cursor.fetchone()
    conn.close()

    total = row[0] or 0
    if total == 0:
        return {"total_reels": 0, "ig_success_rate": 0, "fb_success_rate": 0, "yt_success_rate": 0}

    return {
        "total_reels": total,
        "ig_success_rate": round((row[1] or 0) / total * 100, 1),
        "fb_success_rate": round((row[2] or 0) / total * 100, 1),
        "yt_success_rate": round((row[3] or 0) / total * 100, 1)
    }


# ============================================================
# 🆕 V2.1: SMART SCHEDULING FUNCTIONS
# ============================================================

# Day names (Monday=0, Sunday=6 in Python)
DAY_NAMES = {
    0: "Monday",
    1: "Tuesday",
    2: "Wednesday",
    3: "Thursday",
    4: "Friday",
    5: "Saturday",
    6: "Sunday"
}


def _get_week_start_date(reference_date: datetime = None) -> datetime:
    """
    Get Monday of the week containing reference_date.
    Returns datetime at 00:00:00.
    """
    if reference_date is None:
        reference_date = datetime.now()

    # Python: Monday=0, Sunday=6
    days_since_monday = reference_date.weekday()
    monday = reference_date - timedelta(days=days_since_monday)

    # Reset time to midnight
    return monday.replace(hour=0, minute=0, second=0, microsecond=0)


def generate_weekly_schedule(week_start_date: datetime = None) -> dict:
    """
    🆕 Generate carousel days for a week.

    Picks 2 random days (Mon-Sun) for carousel posts.
    Saves to database.

    Args:
        week_start_date: Monday of the week (defaults to current week)

    Returns:
        {
            "week_start": "2026-01-20",
            "week_end": "2026-01-26",
            "carousel_days": [1, 4],  # Tuesday, Friday
            "carousel_day_names": ["Tuesday", "Friday"],
            "is_new": True  # True if newly generated, False if existed
        }
    """
    if week_start_date is None:
        week_start_date = _get_week_start_date()

    week_start_str = week_start_date.strftime("%Y-%m-%d")
    week_end_date = week_start_date + timedelta(days=6)
    week_end_str = week_end_date.strftime("%Y-%m-%d")

    conn = get_connection()
    cursor = conn.cursor()

    # Check if schedule already exists
    cursor.execute("""
        SELECT carousel_day_1, carousel_day_2
        FROM weekly_schedule
        WHERE week_start_date = ?
    """, (week_start_str,))

    existing = cursor.fetchone()

    if existing:
        # Already exists
        day1, day2 = existing[0], existing[1]
        conn.close()

        logger.info(f"📅 Schedule already exists for week {week_start_str}")

        return {
            "week_start": week_start_str,
            "week_end": week_end_str,
            "carousel_days": [day1, day2],
            "carousel_day_names": [DAY_NAMES[day1], DAY_NAMES[day2]],
            "is_new": False
        }

    # Generate new schedule - pick 2 random unique days from 0-6
    all_days = list(range(7))  # 0=Mon, 6=Sun
    carousel_days = sorted(random.sample(all_days, 2))

    # Save to database
    cursor.execute("""
        INSERT INTO weekly_schedule (
            week_start_date, week_end_date,
            carousel_day_1, carousel_day_2,
            notes
        ) VALUES (?, ?, ?, ?, ?)
    """, (
        week_start_str,
        week_end_str,
        carousel_days[0],
        carousel_days[1],
        f"Auto-generated: {DAY_NAMES[carousel_days[0]]} + {DAY_NAMES[carousel_days[1]]}"
    ))

    conn.commit()
    conn.close()

    logger.info(f"📅 Generated new schedule for week {week_start_str}")
    logger.info(f"   Carousel days: {DAY_NAMES[carousel_days[0]]} + {DAY_NAMES[carousel_days[1]]}")

    return {
        "week_start": week_start_str,
        "week_end": week_end_str,
        "carousel_days": carousel_days,
        "carousel_day_names": [DAY_NAMES[carousel_days[0]], DAY_NAMES[carousel_days[1]]],
        "is_new": True
    }


def is_today_carousel_day() -> bool:
    """
    🆕 Check if today should have carousel (instead of reel #2).

    Returns:
        True if today is one of the 2 random carousel days
        False if today is a regular reel day
    """
    today = datetime.now()
    today_weekday = today.weekday()  # 0=Mon, 6=Sun

    # Get current week schedule
    week_start = _get_week_start_date(today)
    schedule = generate_weekly_schedule(week_start)

    is_carousel = today_weekday in schedule["carousel_days"]

    logger.info(f"📅 Today: {DAY_NAMES[today_weekday]} (day {today_weekday})")
    logger.info(f"📅 Carousel days this week: {schedule['carousel_day_names']}")
    logger.info(f"📅 Today's content type: {'CAROUSEL 🎠' if is_carousel else 'REEL 🎬'}")

    return is_carousel


def get_todays_content_type(time_slot: str = "evening") -> str:
    """
    🆕 Get today's content type based on time slot.

    Args:
        time_slot: "morning" | "afternoon" | "evening"

    Returns:
        "image"    → For morning (8 AM)
        "reel"     → For afternoon (1 PM) OR evening on non-carousel days
        "carousel" → For evening on carousel days
    """
    if time_slot == "morning":
        return "image"

    if time_slot == "afternoon":
        return "reel"  # Always reel at 1 PM

    if time_slot == "evening":
        # Check if today is carousel day
        if is_today_carousel_day():
            return "carousel"
        else:
            return "reel"

    # Default fallback
    return "reel"


def get_carousel_days_this_week() -> dict:
    """
    🆕 Get info about current week's carousel schedule.

    Returns:
        Full week schedule dict
    """
    week_start = _get_week_start_date()
    return generate_weekly_schedule(week_start)


def get_schedule_history(weeks: int = 4) -> list:
    """
    🆕 Get past N weeks schedule history.

    Returns list of week schedules.
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT week_start_date, week_end_date,
               carousel_day_1, carousel_day_2, generated_at
        FROM weekly_schedule
        ORDER BY week_start_date DESC
        LIMIT ?
    """, (weeks,))

    rows = cursor.fetchall()
    conn.close()

    result = []
    for row in rows:
        day1, day2 = row[2], row[3]
        result.append({
            "week_start": row[0],
            "week_end": row[1],
            "carousel_days": [day1, day2],
            "carousel_day_names": [DAY_NAMES[day1], DAY_NAMES[day2]],
            "generated_at": row[4]
        })

    return result


def display_schedule():
    """🆕 Print beautiful schedule info"""
    schedule = get_carousel_days_this_week()

    logger.info("")
    logger.info("╔══════════════════════════════════════════════╗")
    logger.info("║       📅 THIS WEEK'S SCHEDULE                ║")
    logger.info("╠══════════════════════════════════════════════╣")
    logger.info(f"║ Week   : {schedule['week_start']} to {schedule['week_end']}")
    logger.info(f"║ Status : {'🆕 New' if schedule['is_new'] else '✅ Existing'}")
    logger.info("╠══════════════════════════════════════════════╣")
    logger.info("║ DAILY PATTERN:")
    logger.info("║ ")

    today_weekday = datetime.now().weekday()

    for day_num in range(7):
        day_name = DAY_NAMES[day_num]
        is_carousel = day_num in schedule['carousel_days']
        is_today = day_num == today_weekday

        marker = "👉" if is_today else "  "

        if is_carousel:
            logger.info(f"║ {marker} {day_name:10} → 📸 Image + 🎬 Reel + 🎠 Carousel")
        else:
            logger.info(f"║ {marker} {day_name:10} → 📸 Image + 🎬 Reel + 🎬 Reel")

    logger.info("╠══════════════════════════════════════════════╣")
    logger.info(f"║ Total Posts This Week: 21")
    logger.info(f"║   • Images:    7")
    logger.info(f"║   • Reels:     12 (5 days × 2 + 2 days × 1)")
    logger.info(f"║   • Carousels: 2")
    logger.info("╚══════════════════════════════════════════════╝")


# ============================================================
# 🆕 V4: AUTO-LEARN BEST POSTING TIME
# ============================================================

def get_best_posting_times(min_posts: int = 5) -> dict:
    """
    🆕 V4: Analyze engagement data to find best posting times.

    Returns:
        {
            "best_hour": 8,
            "best_slot": "morning",
            "hourly_engagement": {8: 150, 13: 120, 20: 200},
            "recommendation": "8 PM gets 2x more engagement than 1 PM",
            "data_points": 25,
            "confidence": "high"  # high if 20+ posts, medium if 10+, low if <10
        }
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()

        # Get engagement per posting hour
        cursor.execute("""
            SELECT 
                CAST(strftime('%H', post_date) AS INTEGER) as hour,
                COUNT(*) as post_count,
                AVG(CASE WHEN ig_success = 1 THEN 1 ELSE 0 END) as success_rate
            FROM post_history
            WHERE post_date IS NOT NULL
            GROUP BY hour
            HAVING post_count >= ?
            ORDER BY success_rate DESC
        """, (min_posts,))

        rows = cursor.fetchall()
        conn.close()

        if not rows:
            return {
                "best_hour": 8,
                "best_slot": "morning",
                "hourly_engagement": {},
                "recommendation": "Not enough data yet. Need 5+ posts per time slot.",
                "data_points": 0,
                "confidence": "low"
            }

        # Build hourly map
        hourly = {}
        total_posts = 0
        for hour, count, rate in rows:
            hourly[hour] = {
                "posts": count,
                "success_rate": round(rate * 100, 1)
            }
            total_posts += count

        # Find best hour
        best_row = rows[0]
        best_hour = best_row[0]

        # Determine slot name
        if 5 <= best_hour < 11:
            best_slot = "morning"
        elif 11 <= best_hour < 16:
            best_slot = "afternoon"
        elif 16 <= best_hour < 21:
            best_slot = "evening"
        else:
            best_slot = "night"

        # Confidence
        if total_posts >= 20:
            confidence = "high"
        elif total_posts >= 10:
            confidence = "medium"
        else:
            confidence = "low"

        # Recommendation
        if len(rows) >= 2:
            best = rows[0]
            worst = rows[-1]
            recommendation = (
                f"{best[0]}:00 has {best[2]*100:.0f}% success rate "
                f"(best). {worst[0]}:00 has {worst[2]*100:.0f}% (worst). "
                f"Post more at {best[0]}:00!"
            )
        else:
            recommendation = f"Best time: {best_hour}:00 ({best_slot})"

        result = {
            "best_hour": best_hour,
            "best_slot": best_slot,
            "hourly_engagement": hourly,
            "recommendation": recommendation,
            "data_points": total_posts,
            "confidence": confidence
        }

        logger.info(f"📊 Best posting time: {best_hour}:00 ({best_slot}) — {confidence} confidence")

        return result

    except Exception as e:
        logger.warning(f"⚠️  Posting time analysis failed: {e}")
        return {
            "best_hour": 8,
            "best_slot": "morning",
            "hourly_engagement": {},
            "recommendation": f"Analysis failed: {e}",
            "data_points": 0,
            "confidence": "low"
        }


def display_posting_insights():
    """🆕 V4: Display posting time insights"""
    result = get_best_posting_times()

    logger.info("")
    logger.info("╔══════════════════════════════════════════════╗")
    logger.info("║       📊 POSTING TIME INSIGHTS               ║")
    logger.info("╠══════════════════════════════════════════════╣")
    logger.info(f"║ Best hour    : {result['best_hour']}:00 ({result['best_slot']})")
    logger.info(f"║ Confidence   : {result['confidence']}")
    logger.info(f"║ Data points  : {result['data_points']} posts analyzed")
    logger.info("╠══════════════════════════════════════════════╣")
    logger.info(f"║ 💡 {result['recommendation']}")
    logger.info("╠══════════════════════════════════════════════╣")

    if result['hourly_engagement']:
        logger.info("║ Per-hour breakdown:")
        for hour, data in sorted(result['hourly_engagement'].items()):
            bar = "█" * int(data['success_rate'] / 10)
            logger.info(f"║   {hour:02d}:00 → {bar} {data['success_rate']}% ({data['posts']} posts)")

    logger.info("╚══════════════════════════════════════════════╝")


# ============================================================
# STANDALONE TESTING
# ============================================================

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("DATABASE V2.1 - SMART SCHEDULING TEST")
    print("=" * 60 + "\n")

    # Initialize DB
    initialize_database()
    print("✅ Database initialized\n")

    # Test 1: Generate schedule
    print("🧪 TEST 1: Generate this week's schedule")
    schedule = get_carousel_days_this_week()
    print(f"   Week: {schedule['week_start']} to {schedule['week_end']}")
    print(f"   Carousel days: {schedule['carousel_day_names']}")
    print(f"   Is new: {schedule['is_new']}")

    # Test 2: Check today's content type
    print("\n🧪 TEST 2: Today's content types")
    for slot in ["morning", "afternoon", "evening"]:
        content = get_todays_content_type(slot)
        print(f"   {slot:10} → {content}")

    # Test 3: Is today carousel day?
    print("\n🧪 TEST 3: Is today carousel day?")
    is_carousel = is_today_carousel_day()
    print(f"   Result: {'YES 🎠' if is_carousel else 'NO 🎬'}")

    # Test 4: Display full schedule
    print("\n🧪 TEST 4: Full weekly schedule display")
    display_schedule()

    # Test 5: Schedule history
    print("\n🧪 TEST 5: Recent schedule history")
    history = get_schedule_history(weeks=5)
    if history:
        for i, week in enumerate(history, 1):
            print(f"   Week {i}: {week['week_start']} → {week['carousel_day_names']}")
    else:
        print("   No history yet (first week)")

    print("\n" + "=" * 60)
    print("✅ All tests complete!")
    print("=" * 60)