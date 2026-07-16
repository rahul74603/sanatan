"""
Engagement Agent - MAIN ORCHESTRATOR for auto comment replies

V3 Features:
- Runs every 30 minutes via GitHub Actions
- Fetches → Generates → Posts replies
- Rate limited (max 20 replies per run)
- Full logging and tracking
- Works on all 3 platforms
"""
import time
from datetime import datetime

from engagement.comment_fetcher import fetch_all_new_comments
from engagement.reply_generator import generate_replies_batch
from engagement.reply_poster import post_replies

from core.database import initialize_database, get_connection
from utils.logger import get_logger

logger = get_logger("engagement_agent")

# Config
MAX_REPLIES_PER_RUN = 20  # Rate limit


# ============================================================
# STATS
# ============================================================

def get_engagement_stats() -> dict:
    """Get engagement statistics"""
    try:
        conn = get_connection()
        cursor = conn.cursor()

        # Total replies
        cursor.execute("SELECT COUNT(*) FROM comment_replies WHERE reply_posted = 1")
        total_replied = cursor.fetchone()[0] or 0

        # Today's replies
        today = datetime.now().strftime("%Y-%m-%d")
        cursor.execute(
            "SELECT COUNT(*) FROM comment_replies WHERE reply_posted = 1 AND replied_at LIKE ?",
            (f"{today}%",)
        )
        today_replied = cursor.fetchone()[0] or 0

        # Pending (fetched but not replied)
        cursor.execute("SELECT COUNT(*) FROM comment_replies WHERE reply_posted = 0")
        pending = cursor.fetchone()[0] or 0

        # Per platform
        cursor.execute("""
            SELECT platform, COUNT(*)
            FROM comment_replies
            WHERE reply_posted = 1
            GROUP BY platform
        """)
        platform_counts = {}
        for row in cursor.fetchall():
            platform_counts[row[0]] = row[1]

        conn.close()

        return {
            "total_replied": total_replied,
            "today_replied": today_replied,
            "pending": pending,
            "platforms": platform_counts
        }

    except Exception as e:
        logger.warning(f"⚠️  Stats fetch failed: {e}")
        return {"total_replied": 0, "today_replied": 0, "pending": 0, "platforms": {}}


# ============================================================
# MAIN AGENT
# ============================================================

def run() -> dict:
    """
    Main engagement agent — full pipeline.

    Flow:
    1. Initialize DB
    2. Fetch new comments from IG + FB + YT
    3. Generate AI replies for each
    4. Post replies to platforms
    5. Log stats

    Returns:
        Result dict with counts
    """
    start_time = time.time()

    logger.info("")
    logger.info("═" * 55)
    logger.info("🤖 === ENGAGEMENT AGENT V3 शुरू ===")
    logger.info("═" * 55)
    logger.info(f"📅 Time   : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"📊 Limit  : Max {MAX_REPLIES_PER_RUN} replies per run")
    logger.info("═" * 55)

    # Step 0: Initialize DB
    try:
        initialize_database()
    except Exception as e:
        logger.error(f"❌ DB init failed: {e}")

    # Step 1: Fetch comments
    logger.info("\n━━━ Step 1/3: Comments Fetch करना ━━━")
    try:
        new_comments = fetch_all_new_comments(max_total=MAX_REPLIES_PER_RUN)
    except Exception as e:
        logger.error(f"❌ Comment fetch failed: {e}")
        new_comments = []

    if not new_comments:
        logger.info("✅ कोई नए comments नहीं मिले — कुछ करने की ज़रूरत नहीं")

        elapsed = round(time.time() - start_time, 2)
        logger.info(f"\n⏱️  Total time: {elapsed}s")
        logger.info("═" * 55)

        return {
            "status": "no_comments",
            "comments_found": 0,
            "replies_posted": 0,
            "duration": elapsed
        }

    logger.info(f"📬 {len(new_comments)} नए comments मिले!")

    # Step 2: Generate replies
    logger.info("\n━━━ Step 2/3: AI Replies Generate करना ━━━")
    try:
        comment_reply_pairs = generate_replies_batch(new_comments)
    except Exception as e:
        logger.error(f"❌ Reply generation failed: {e}")
        comment_reply_pairs = []

    if not comment_reply_pairs:
        logger.warning("⚠️  कोई reply generate नहीं हुई")

        elapsed = round(time.time() - start_time, 2)
        return {
            "status": "no_replies",
            "comments_found": len(new_comments),
            "replies_posted": 0,
            "duration": elapsed
        }

    # Step 3: Post replies
    logger.info("\n━━━ Step 3/3: Replies Post करना ━━━")
    try:
        post_result = post_replies(comment_reply_pairs)
    except Exception as e:
        logger.error(f"❌ Reply posting failed: {e}")
        post_result = {"success": 0, "failed": len(comment_reply_pairs)}

    # Summary
    elapsed = round(time.time() - start_time, 2)
    stats = get_engagement_stats()

    logger.info("")
    logger.info("═" * 55)
    logger.info("🤖 === ENGAGEMENT AGENT SUMMARY ===")
    logger.info("═" * 55)
    logger.info(f"📬 Comments found    : {len(new_comments)}")
    logger.info(f"💬 Replies generated : {len(comment_reply_pairs)}")
    logger.info(f"✅ Posted success    : {post_result.get('success', 0)}")
    logger.info(f"❌ Posted failed     : {post_result.get('failed', 0)}")
    logger.info(f"⏱️  Total time        : {elapsed}s")
    logger.info("")
    logger.info(f"📊 ALL TIME STATS:")
    logger.info(f"   Total replied     : {stats['total_replied']}")
    logger.info(f"   Today replied     : {stats['today_replied']}")
    logger.info(f"   Pending           : {stats['pending']}")
    logger.info("═" * 55)

    return {
        "status": "success",
        "comments_found": len(new_comments),
        "replies_generated": len(comment_reply_pairs),
        "replies_posted": post_result.get("success", 0),
        "replies_failed": post_result.get("failed", 0),
        "duration": elapsed,
        "stats": stats
    }


# ============================================================
# STANDALONE TEST
# ============================================================

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("🤖 ENGAGEMENT AGENT V3 - FULL TEST")
    print("=" * 60 + "\n")

    print("⚠️  This will:")
    print("   1. Fetch real comments from IG/FB/YT")
    print("   2. Generate AI replies via Gemini")
    print("   3. POST real replies to platforms")
    print("")

    proceed = input("Continue? (yes/no): ").strip().lower()
    if proceed != "yes":
        print("Test cancelled.")
        exit(0)

    result = run()

    print(f"\n📊 Result: {result}")