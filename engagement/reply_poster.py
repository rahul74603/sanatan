"""
Reply Poster - Post generated replies to Instagram, Facebook, YouTube

V4 IMPROVEMENTS:
- 🆕 Quiet hours (11 PM - 6 AM no replies)
- 🆕 Smart human-like delays (10-45 seconds)
- 🆕 Random initial wait (feels natural)
- 🆕 Reply count safety limit per platform
- 🆕 Better error categorization
- 🆕 Retry on temporary errors
- 🆕 IST timezone awareness
"""
import time
import random
import requests
from datetime import datetime, timezone, timedelta

from config.settings import (
    ACCESS_TOKEN,
    META_API_VERSION,
    YOUTUBE_ENABLED,
)
from core.database import get_connection
from utils.logger import get_logger

logger = get_logger("reply_poster")

META_BASE_URL = f"https://graph.facebook.com/{META_API_VERSION}"

# ============================================================
# V4: SMART TIMING CONFIGURATION
# ============================================================

# Human-like delays between replies
MIN_DELAY_BETWEEN_REPLIES = 10   # Min 10 seconds
MAX_DELAY_BETWEEN_REPLIES = 45   # Max 45 seconds
FIRST_REPLY_DELAY_MIN = 5       # Wait before first reply
FIRST_REPLY_DELAY_MAX = 20      # Seems like reading comments first

# Quiet hours (IST) — no replies during sleep time
QUIET_HOURS_START = 23  # 11 PM IST
QUIET_HOURS_END = 6     # 6 AM IST

# Safety limits per run
MAX_REPLIES_PER_PLATFORM = 10   # Max 10 replies per platform per run
MAX_TOTAL_REPLIES_PER_RUN = 20  # Max 20 total per run

# Request settings
REQUEST_TIMEOUT = 15
MAX_RETRY_PER_REPLY = 2  # Retry once on temporary errors

# Temporary error codes (worth retrying)
TEMP_ERROR_CODES = [429, 500, 502, 503, 504]


# ============================================================
# TIMEZONE HELPER
# ============================================================

def _get_ist_hour() -> int:
    """Get current hour in IST (Indian Standard Time = UTC+5:30)"""
    ist = timezone(timedelta(hours=5, minutes=30))
    now_ist = datetime.now(ist)
    return now_ist.hour


def _is_quiet_hours() -> bool:
    """
    Check if current time is in quiet hours (IST).
    
    Quiet: 11 PM to 6 AM IST
    Active: 6 AM to 11 PM IST
    """
    hour = _get_ist_hour()

    if QUIET_HOURS_START <= hour or hour < QUIET_HOURS_END:
        return True
    return False


def _get_time_until_active() -> str:
    """Get human-readable time until quiet hours end"""
    ist = timezone(timedelta(hours=5, minutes=30))
    now = datetime.now(ist)
    hour = now.hour

    if hour >= QUIET_HOURS_START:
        # After 11 PM → active at 6 AM next day
        hours_left = (24 - hour) + QUIET_HOURS_END
    else:
        # Before 6 AM → active at 6 AM
        hours_left = QUIET_HOURS_END - hour

    return f"~{hours_left} hours"


# ============================================================
# DATABASE: Mark as Replied
# ============================================================

def _mark_as_replied(comment_id: str, reply_text: str, platform: str = ""):
    """Mark comment as replied in database"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE comment_replies
            SET reply_text = ?,
                reply_posted = 1,
                replied_at = ?
            WHERE comment_id = ?
        """, (reply_text, datetime.now().isoformat(), comment_id))
        conn.commit()
        conn.close()
        logger.debug(f"   💾 Marked as replied in DB")
    except Exception as e:
        logger.warning(f"   ⚠️  Mark replied failed: {e}")


def _get_today_reply_count(platform: str = "") -> int:
    """Get number of replies posted today (safety check)"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        today = datetime.now().strftime("%Y-%m-%d")

        if platform:
            cursor.execute(
                "SELECT COUNT(*) FROM comment_replies WHERE reply_posted = 1 AND replied_at LIKE ? AND platform = ?",
                (f"{today}%", platform)
            )
        else:
            cursor.execute(
                "SELECT COUNT(*) FROM comment_replies WHERE reply_posted = 1 AND replied_at LIKE ?",
                (f"{today}%",)
            )

        count = cursor.fetchone()[0] or 0
        conn.close()
        return count
    except Exception:
        return 0


# ============================================================
# INSTAGRAM REPLY
# ============================================================

def _post_ig_reply(comment_id: str, reply_text: str) -> dict:
    """Post reply to Instagram comment with retry"""
    url = f"{META_BASE_URL}/{comment_id}/replies"

    for attempt in range(1, MAX_RETRY_PER_REPLY + 1):
        try:
            response = requests.post(
                url,
                params={
                    'message': reply_text,
                    'access_token': ACCESS_TOKEN
                },
                timeout=REQUEST_TIMEOUT
            )

            if response.status_code == 200:
                reply_id = response.json().get('id', '')
                logger.info(f"   ✅ IG reply posted: {reply_id}")
                return {"success": True, "reply_id": reply_id}

            # Check if temporary error (worth retrying)
            if response.status_code in TEMP_ERROR_CODES and attempt < MAX_RETRY_PER_REPLY:
                logger.warning(f"   ⚠️  IG temporary error ({response.status_code}), retrying...")
                time.sleep(5)
                continue

            error = response.json().get('error', {})
            error_msg = error.get('message', 'Unknown error')
            error_code = error.get('code', 0)

            # Rate limit
            if error_code in [4, 17, 32, 613]:
                logger.warning(f"   ⚠️  IG rate limited! Stopping replies.")
                return {"success": False, "error": "rate_limited", "stop_all": True}

            logger.warning(f"   ⚠️  IG reply failed: {error_msg}")
            return {"success": False, "error": error_msg}

        except requests.Timeout:
            logger.warning(f"   ⚠️  IG timeout (attempt {attempt})")
            if attempt < MAX_RETRY_PER_REPLY:
                time.sleep(3)
                continue
            return {"success": False, "error": "timeout"}

        except Exception as e:
            logger.error(f"   ❌ IG reply error: {e}")
            return {"success": False, "error": str(e)}

    return {"success": False, "error": "max retries exceeded"}


# ============================================================
# FACEBOOK REPLY
# ============================================================

def _post_fb_reply(comment_id: str, reply_text: str) -> dict:
    """Post reply to Facebook comment with retry"""
    url = f"{META_BASE_URL}/{comment_id}/comments"

    for attempt in range(1, MAX_RETRY_PER_REPLY + 1):
        try:
            response = requests.post(
                url,
                params={
                    'message': reply_text,
                    'access_token': ACCESS_TOKEN
                },
                timeout=REQUEST_TIMEOUT
            )

            if response.status_code == 200:
                reply_id = response.json().get('id', '')
                logger.info(f"   ✅ FB reply posted: {reply_id}")
                return {"success": True, "reply_id": reply_id}

            if response.status_code in TEMP_ERROR_CODES and attempt < MAX_RETRY_PER_REPLY:
                logger.warning(f"   ⚠️  FB temporary error ({response.status_code}), retrying...")
                time.sleep(5)
                continue

            error = response.json().get('error', {})
            error_msg = error.get('message', 'Unknown error')
            error_code = error.get('code', 0)

            if error_code in [4, 17, 32, 613]:
                logger.warning(f"   ⚠️  FB rate limited!")
                return {"success": False, "error": "rate_limited", "stop_all": True}

            logger.warning(f"   ⚠️  FB reply failed: {error_msg}")
            return {"success": False, "error": error_msg}

        except requests.Timeout:
            if attempt < MAX_RETRY_PER_REPLY:
                time.sleep(3)
                continue
            return {"success": False, "error": "timeout"}

        except Exception as e:
            logger.error(f"   ❌ FB reply error: {e}")
            return {"success": False, "error": str(e)}

    return {"success": False, "error": "max retries exceeded"}


# ============================================================
# YOUTUBE REPLY
# ============================================================

def _post_yt_reply(comment_id: str, reply_text: str) -> dict:
    """Post reply to YouTube comment"""
    if not YOUTUBE_ENABLED:
        return {"success": False, "error": "YouTube disabled"}

    try:
        from posting.youtube import _get_youtube_client

        youtube = _get_youtube_client()

        response = youtube.comments().insert(
            part="snippet",
            body={
                "snippet": {
                    "parentId": comment_id,
                    "textOriginal": reply_text
                }
            }
        ).execute()

        reply_id = response.get('id', '')
        logger.info(f"   ✅ YT reply posted: {reply_id}")
        return {"success": True, "reply_id": reply_id}

    except ImportError:
        logger.warning("   ⚠️  YouTube module not available")
        return {"success": False, "error": "YouTube module not installed"}
    except Exception as e:
        error_str = str(e)

        # Check for specific YouTube errors
        if "insufficientPermissions" in error_str:
            logger.warning("   ⚠️  YT: Need comment scope — run: python -m posting.youtube")
            return {"success": False, "error": "insufficient_permissions"}

        if "quotaExceeded" in error_str:
            logger.warning("   ⚠️  YT quota exceeded!")
            return {"success": False, "error": "quota_exceeded", "stop_all": True}

        logger.error(f"   ❌ YT reply error: {e}")
        return {"success": False, "error": error_str}


# ============================================================
# MAIN: POST REPLIES
# ============================================================

def post_replies(comment_reply_pairs: list) -> dict:
    """
    Post all generated replies to their platforms.

    V4 Features:
    - Quiet hours check (11 PM - 6 AM IST)
    - Per-platform rate limits
    - Human-like random delays
    - Initial reading delay
    - Rate limit detection (auto-stop)
    - Daily limit safety check
    """
    # ═══════════════════════════════════════════
    # V4: QUIET HOURS CHECK
    # ═══════════════════════════════════════════
    if _is_quiet_hours():
        ist_hour = _get_ist_hour()
        active_in = _get_time_until_active()

        logger.info("=" * 55)
        logger.info(f"😴 QUIET HOURS (IST {QUIET_HOURS_START}:00 - {QUIET_HOURS_END}:00)")
        logger.info(f"   Current IST hour: {ist_hour}:00")
        logger.info(f"   Active again in : {active_in}")
        logger.info(f"   Replies paused  : {len(comment_reply_pairs)} comments saved for later")
        logger.info("=" * 55)

        return {
            "total": len(comment_reply_pairs),
            "success": 0,
            "failed": 0,
            "skipped": len(comment_reply_pairs),
            "reason": "quiet_hours",
            "quiet_until": f"{QUIET_HOURS_END}:00 IST",
            "platforms": {
                "instagram": {"success": 0, "failed": 0},
                "facebook": {"success": 0, "failed": 0},
                "youtube": {"success": 0, "failed": 0},
            }
        }

    # ═══════════════════════════════════════════
    # V4: DAILY LIMIT CHECK
    # ═══════════════════════════════════════════
    today_total = _get_today_reply_count()
    if today_total >= MAX_TOTAL_REPLIES_PER_RUN * 3:  # Max ~60 replies/day
        logger.warning(f"⚠️  Daily limit reached ({today_total} replies today). Pausing.")
        return {
            "total": len(comment_reply_pairs),
            "success": 0,
            "failed": 0,
            "skipped": len(comment_reply_pairs),
            "reason": "daily_limit",
            "today_count": today_total,
            "platforms": {
                "instagram": {"success": 0, "failed": 0},
                "facebook": {"success": 0, "failed": 0},
                "youtube": {"success": 0, "failed": 0},
            }
        }

    # ═══════════════════════════════════════════
    # START POSTING
    # ═══════════════════════════════════════════
    logger.info("=" * 55)
    logger.info("=== REPLY POSTER V4 शुरू ===")
    logger.info("=" * 55)
    logger.info(f"📊 Comments to reply : {len(comment_reply_pairs)}")
    logger.info(f"📊 Today's replies   : {today_total}")
    logger.info(f"⏰ IST hour          : {_get_ist_hour()}:00")
    logger.info("=" * 55)

    # V4: Initial "reading" delay (looks like we're reading comments first)
    initial_delay = random.randint(FIRST_REPLY_DELAY_MIN, FIRST_REPLY_DELAY_MAX)
    logger.info(f"📖 Reading comments... ({initial_delay}s)")
    time.sleep(initial_delay)

    total = len(comment_reply_pairs)
    success_count = 0
    fail_count = 0
    skipped_count = 0
    rate_limited = False  # Stop all if rate limited

    results = {
        "instagram": {"success": 0, "failed": 0},
        "facebook": {"success": 0, "failed": 0},
        "youtube": {"success": 0, "failed": 0},
    }

    # V4: Per-platform counters
    platform_counts = {"instagram": 0, "facebook": 0, "youtube": 0}

    for i, (comment, reply_text) in enumerate(comment_reply_pairs, 1):
        # Check if rate limited (stop all)
        if rate_limited:
            logger.warning(f"   ⏭️  Skipping remaining (rate limited)")
            skipped_count += (total - i + 1)
            break

        platform = comment.get('platform', 'unknown')
        comment_id = comment.get('comment_id', '')
        username = comment.get('username', '')

        # V4: Per-platform limit check
        if platform in platform_counts:
            if platform_counts[platform] >= MAX_REPLIES_PER_PLATFORM:
                logger.info(f"   ⏭️  {platform} limit reached ({MAX_REPLIES_PER_PLATFORM}), skipping")
                skipped_count += 1
                continue

        logger.info(f"\n📤 [{i}/{total}] Replying on {platform.upper()}")
        logger.info(f"   👤 To: @{username}")
        logger.info(f"   💬 Comment: {comment.get('text', '')[:50]}...")
        logger.info(f"   📝 Reply: {reply_text[:60]}...")

        # Skip if no valid reply
        if not reply_text or len(reply_text) < 5:
            logger.warning(f"   ⏭️  Empty reply, skipping")
            skipped_count += 1
            continue

        # Post reply based on platform
        result = {"success": False, "error": "Unknown platform"}

        if platform == "instagram":
            result = _post_ig_reply(comment_id, reply_text)
        elif platform == "facebook":
            result = _post_fb_reply(comment_id, reply_text)
        elif platform == "youtube":
            result = _post_yt_reply(comment_id, reply_text)
        else:
            logger.warning(f"   ⚠️  Unknown platform: {platform}")
            skipped_count += 1
            continue

        # Check for rate limit signal
        if result.get("stop_all"):
            rate_limited = True
            fail_count += 1
            results[platform]["failed"] += 1
            logger.warning(f"   🛑 Rate limited! Stopping all replies.")
            continue

        # Track results
        if result["success"]:
            success_count += 1
            results[platform]["success"] += 1
            platform_counts[platform] = platform_counts.get(platform, 0) + 1
            _mark_as_replied(comment_id, reply_text, platform)
        else:
            fail_count += 1
            results[platform]["failed"] += 1

        # V4: Smart human-like delay between replies
        if i < total and not rate_limited:
            # Vary delay based on platform switch
            next_platform = comment_reply_pairs[i][0].get('platform', '') if i < total else ''

            if next_platform != platform:
                # Different platform = longer pause (switching apps feel)
                delay = random.randint(20, 45)
                logger.info(f"   ⏳ Platform switch delay: {delay}s")
            else:
                # Same platform = shorter pause
                delay = random.randint(MIN_DELAY_BETWEEN_REPLIES, MAX_DELAY_BETWEEN_REPLIES)
                logger.info(f"   ⏳ Natural pace: {delay}s")

            time.sleep(delay)

    # ═══════════════════════════════════════════
    # SUMMARY
    # ═══════════════════════════════════════════
    logger.info("")
    logger.info("=" * 55)
    logger.info("✅ REPLY POSTER V4 COMPLETE")
    logger.info("=" * 55)
    logger.info(f"   📊 Total      : {total}")
    logger.info(f"   ✅ Success    : {success_count}")
    logger.info(f"   ❌ Failed     : {fail_count}")
    logger.info(f"   ⏭️  Skipped   : {skipped_count}")

    if rate_limited:
        logger.info(f"   🛑 Rate limit : YES (stopped early)")

    logger.info(f"   📸 IG         : ✅{results['instagram']['success']} ❌{results['instagram']['failed']}")
    logger.info(f"   📘 FB         : ✅{results['facebook']['success']} ❌{results['facebook']['failed']}")
    logger.info(f"   📺 YT         : ✅{results['youtube']['success']} ❌{results['youtube']['failed']}")
    logger.info(f"   📊 Today total: {today_total + success_count} replies")
    logger.info("=" * 55)

    return {
        "total": total,
        "success": success_count,
        "failed": fail_count,
        "skipped": skipped_count,
        "rate_limited": rate_limited,
        "today_total": today_total + success_count,
        "platforms": results
    }


# ============================================================
# STANDALONE TEST
# ============================================================

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("REPLY POSTER V4 - TEST")
    print("=" * 60 + "\n")

    # Test quiet hours
    is_quiet = _is_quiet_hours()
    ist_hour = _get_ist_hour()

    print(f"⏰ Current IST hour: {ist_hour}:00")
    print(f"😴 Quiet hours     : {QUIET_HOURS_START}:00 - {QUIET_HOURS_END}:00 IST")
    print(f"📊 Is quiet now    : {'YES 😴' if is_quiet else 'NO ✅ (Active)'}")

    if is_quiet:
        print(f"⏰ Active again in : {_get_time_until_active()}")
    else:
        print(f"✅ Ready to post replies!")

    # Test daily count
    today_count = _get_today_reply_count()
    print(f"\n📊 Today's replies : {today_count}")
    print(f"📊 Daily limit     : {MAX_TOTAL_REPLIES_PER_RUN * 3}")

    # Test timing config
    print(f"\n⏱️  Reply delays:")
    print(f"   First reply  : {FIRST_REPLY_DELAY_MIN}-{FIRST_REPLY_DELAY_MAX}s")
    print(f"   Between same : {MIN_DELAY_BETWEEN_REPLIES}-{MAX_DELAY_BETWEEN_REPLIES}s")
    print(f"   Platform switch: 20-45s")

    print(f"\n🛡️  Safety limits:")
    print(f"   Per platform : {MAX_REPLIES_PER_PLATFORM}/run")
    print(f"   Total per run: {MAX_TOTAL_REPLIES_PER_RUN}")
    print(f"   Daily max    : {MAX_TOTAL_REPLIES_PER_RUN * 3}")

    print("\n✅ All settings configured!")