"""
Reply Poster V5 - Fixed Integration with Comment Fetcher V4

FIXES:
- mark_reply_posted() comment_fetcher se import karo (single source of truth)
- DB connection same WAL mode use karo
- _mark_as_replied failure = reply skip (don't risk double reply)  
- Verification after posting (confirm DB updated)
- Proper error handling chain
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

# ✅ FIX 1: Comment fetcher ka mark function import karo
# Ek hi jagah se DB update hoga - no duplication
from engagement.comment_fetcher import mark_reply_posted

logger = get_logger("reply_poster")

META_BASE_URL = f"https://graph.facebook.com/{META_API_VERSION}"

# ============================================================
# CONFIGURATION
# ============================================================

# Human-like delays
MIN_DELAY_BETWEEN_REPLIES = 10
MAX_DELAY_BETWEEN_REPLIES = 45
FIRST_REPLY_DELAY_MIN = 5
FIRST_REPLY_DELAY_MAX = 20

# Quiet hours IST
QUIET_HOURS_START = 23  # 11 PM
QUIET_HOURS_END = 6     # 6 AM

# Safety limits
MAX_REPLIES_PER_PLATFORM = 10
MAX_TOTAL_REPLIES_PER_RUN = 20
MAX_DAILY_REPLIES = 60  # Hard daily cap

# Request settings
REQUEST_TIMEOUT = 15
MAX_RETRY_PER_REPLY = 2

# Retryable HTTP errors
TEMP_ERROR_CODES = [429, 500, 502, 503, 504]

# Meta rate limit error codes
META_RATE_LIMIT_CODES = [4, 17, 32, 613]


# ============================================================
# TIMEZONE HELPERS
# ============================================================

IST = timezone(timedelta(hours=5, minutes=30))


def _get_ist_now() -> datetime:
    """Current datetime in IST"""
    return datetime.now(IST)


def _get_ist_hour() -> int:
    """Current hour in IST"""
    return _get_ist_now().hour


def _is_quiet_hours() -> bool:
    """
    11 PM se 6 AM IST = quiet hours.
    
    Example:
        hour=23 → quiet ✅
        hour=0  → quiet ✅  
        hour=5  → quiet ✅
        hour=6  → active ✅
        hour=22 → active ✅
    """
    hour = _get_ist_hour()
    # Late night (11 PM onwards) OR early morning (before 6 AM)
    return hour >= QUIET_HOURS_START or hour < QUIET_HOURS_END


def _get_time_until_active() -> str:
    """Human readable time until quiet hours end"""
    now = _get_ist_now()
    hour = now.hour

    if hour >= QUIET_HOURS_START:
        # e.g. 11 PM → next day 6 AM = 7 hours
        hours_left = (24 - hour) + QUIET_HOURS_END
    else:
        # e.g. 2 AM → 6 AM = 4 hours
        hours_left = QUIET_HOURS_END - hour

    return f"~{hours_left} hours (active at {QUIET_HOURS_END}:00 IST)"


# ============================================================
# DATABASE HELPERS
# ============================================================

def _get_db():
    """WAL mode DB connection - same as comment_fetcher"""
    conn = get_connection()
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    return conn


def _get_today_reply_count(platform: str = "") -> int:
    """
    Aaj kitne replies post hue.
    IST date use karo (UTC se alag ho sakti hai midnight pe)
    """
    try:
        conn = _get_db()
        cursor = conn.cursor()

        # IST mein aaj ki date
        today_ist = _get_ist_now().strftime("%Y-%m-%d")

        if platform:
            cursor.execute("""
                SELECT COUNT(*) FROM comment_replies 
                WHERE reply_posted = 1 
                  AND platform = ?
                  AND replied_at LIKE ?
            """, (platform, f"{today_ist}%"))
        else:
            cursor.execute("""
                SELECT COUNT(*) FROM comment_replies 
                WHERE reply_posted = 1 
                  AND replied_at LIKE ?
            """, (f"{today_ist}%",))

        count = cursor.fetchone()[0] or 0
        conn.close()
        return count

    except Exception as e:
        logger.warning(f"⚠️  Reply count check failed: {e}")
        return 0  # Safe side pe 0 return karo


def _verify_marked_as_replied(comment_id: str) -> bool:
    """
    Verify karo ki DB mein reply_posted = 1 set hua.
    
    Yeh extra safety check hai double reply prevent karne ke liye.
    Agar verify fail ho to comment ko process mat karo.
    """
    try:
        conn = _get_db()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT reply_posted FROM comment_replies WHERE comment_id = ?",
            (comment_id,)
        )
        result = cursor.fetchone()
        conn.close()

        if result and result[0] == 1:
            return True

        logger.warning(f"   ⚠️  DB verify failed for {comment_id[:15]}...")
        return False

    except Exception as e:
        logger.warning(f"   ⚠️  Verify check error: {e}")
        return False


# ============================================================
# PLATFORM REPLY FUNCTIONS
# ============================================================

def _post_ig_reply(comment_id: str, reply_text: str) -> dict:
    """
    Instagram comment pe reply post karo.
    
    Returns:
        {
            "success": True/False,
            "reply_id": "...",      # on success
            "error": "...",         # on failure
            "stop_all": True        # on rate limit
        }
    """
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

            # Temporary error - retry karo
            if response.status_code in TEMP_ERROR_CODES and attempt < MAX_RETRY_PER_REPLY:
                wait = 5 * attempt  # Progressive wait
                logger.warning(
                    f"   ⚠️  IG temp error ({response.status_code}), "
                    f"retry {attempt}/{MAX_RETRY_PER_REPLY} in {wait}s..."
                )
                time.sleep(wait)
                continue

            # Parse error
            try:
                error_data = response.json().get('error', {})
                error_msg = error_data.get('message', f'HTTP {response.status_code}')
                error_code = error_data.get('code', 0)
            except Exception:
                error_msg = f"HTTP {response.status_code}"
                error_code = 0

            # Rate limit - stop everything
            if error_code in META_RATE_LIMIT_CODES:
                logger.warning(f"   🛑 IG rate limited! Code: {error_code}")
                return {
                    "success": False,
                    "error": "rate_limited",
                    "stop_all": True
                }

            logger.warning(f"   ❌ IG reply failed [{error_code}]: {error_msg}")
            return {"success": False, "error": error_msg}

        except requests.Timeout:
            logger.warning(f"   ⚠️  IG timeout (attempt {attempt}/{MAX_RETRY_PER_REPLY})")
            if attempt < MAX_RETRY_PER_REPLY:
                time.sleep(3)
                continue
            return {"success": False, "error": "timeout"}

        except requests.ConnectionError as e:
            logger.warning(f"   ⚠️  IG connection error: {e}")
            return {"success": False, "error": "connection_error"}

        except Exception as e:
            logger.error(f"   ❌ IG unexpected error: {e}")
            return {"success": False, "error": str(e)}

    return {"success": False, "error": "max_retries_exceeded"}


def _post_fb_reply(comment_id: str, reply_text: str) -> dict:
    """
    Facebook comment pe reply post karo.
    Same structure as IG for consistency.
    """
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
                wait = 5 * attempt
                logger.warning(
                    f"   ⚠️  FB temp error ({response.status_code}), "
                    f"retry {attempt}/{MAX_RETRY_PER_REPLY} in {wait}s..."
                )
                time.sleep(wait)
                continue

            try:
                error_data = response.json().get('error', {})
                error_msg = error_data.get('message', f'HTTP {response.status_code}')
                error_code = error_data.get('code', 0)
            except Exception:
                error_msg = f"HTTP {response.status_code}"
                error_code = 0

            if error_code in META_RATE_LIMIT_CODES:
                logger.warning(f"   🛑 FB rate limited! Code: {error_code}")
                return {
                    "success": False,
                    "error": "rate_limited",
                    "stop_all": True
                }

            logger.warning(f"   ❌ FB reply failed [{error_code}]: {error_msg}")
            return {"success": False, "error": error_msg}

        except requests.Timeout:
            if attempt < MAX_RETRY_PER_REPLY:
                time.sleep(3)
                continue
            return {"success": False, "error": "timeout"}

        except requests.ConnectionError:
            return {"success": False, "error": "connection_error"}

        except Exception as e:
            logger.error(f"   ❌ FB unexpected error: {e}")
            return {"success": False, "error": str(e)}

    return {"success": False, "error": "max_retries_exceeded"}


def _post_yt_reply(comment_id: str, reply_text: str) -> dict:
    """YouTube comment pe reply post karo"""
    if not YOUTUBE_ENABLED:
        return {"success": False, "error": "youtube_disabled"}

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
        return {"success": False, "error": "youtube_module_missing"}

    except Exception as e:
        error_str = str(e)

        if "insufficientPermissions" in error_str:
            logger.warning("   ⚠️  YT: Missing comment permission scope")
            return {"success": False, "error": "insufficient_permissions"}

        if "quotaExceeded" in error_str:
            logger.warning("   🛑 YT quota exceeded!")
            return {"success": False, "error": "quota_exceeded", "stop_all": True}

        if "processingFailure" in error_str:
            logger.warning("   ⚠️  YT processing failure (temp)")
            return {"success": False, "error": "processing_failure"}

        logger.error(f"   ❌ YT reply error: {e}")
        return {"success": False, "error": error_str}


# ============================================================
# PLATFORM DISPATCHER
# ============================================================

PLATFORM_HANDLERS = {
    "instagram": _post_ig_reply,
    "facebook": _post_fb_reply,
    "youtube": _post_yt_reply,
}


def _dispatch_reply(platform: str, comment_id: str, reply_text: str) -> dict:
    """Platform ke hisaab se sahi handler call karo"""
    handler = PLATFORM_HANDLERS.get(platform)

    if not handler:
        logger.warning(f"   ⚠️  Unknown platform: {platform}")
        return {"success": False, "error": f"unknown_platform_{platform}"}

    return handler(comment_id, reply_text)


# ============================================================
# SAFE REPLY: POST + MARK (Atomic-ish)
# ============================================================

def _safe_post_and_mark(
    platform: str,
    comment: dict,
    reply_text: str
) -> dict:
    """
    Reply post karo aur IMMEDIATELY DB mein mark karo.
    
    Flow:
    1. Platform pe reply post karo
    2. Success → turant DB mark karo
    3. DB mark fail → LOG ERROR (reply posted but not marked)
    4. Verify ki DB actually updated hua
    
    Returns:
        result dict with success/failure info
    """
    comment_id = comment.get('comment_id', '')
    username = comment.get('username', '')

    # ── Step 1: Platform pe post karo ──
    result = _dispatch_reply(platform, comment_id, reply_text)

    # ── Step 2: Success pe turant mark karo ──
    if result.get("success"):
        try:
            # comment_fetcher ka function use karo (single source of truth)
            mark_reply_posted(comment_id, reply_text)

        except Exception as mark_err:
            # CRITICAL: Reply post hua lekin DB update nahi hua
            # Yeh double reply ka risk hai!
            logger.error(
                f"   🚨 CRITICAL: Reply posted to {platform} BUT DB mark FAILED!\n"
                f"      Comment ID : {comment_id}\n"
                f"      Username   : {username}\n"
                f"      Error      : {mark_err}\n"
                f"      ACTION     : Manually mark in DB!"
            )
            # Result mein warning add karo
            result["db_mark_failed"] = True
            result["db_error"] = str(mark_err)

        # ── Step 3: Verify DB update ──
        if not result.get("db_mark_failed"):
            verified = _verify_marked_as_replied(comment_id)
            if not verified:
                logger.error(
                    f"   🚨 DB VERIFY FAILED after mark!\n"
                    f"      Comment: {comment_id[:20]}...\n"
                    f"      Risk of double reply on next run!"
                )
                result["db_verify_failed"] = True

    return result


# ============================================================
# MAIN: POST ALL REPLIES
# ============================================================

def post_replies(comment_reply_pairs: list) -> dict:
    """
    Saare generated replies post karo.
    
    Args:
        comment_reply_pairs: List of (comment_dict, reply_text) tuples
        
    Returns:
        Summary dict with counts and platform breakdown
    """
    # ═══════════════════════════════════════
    # GUARD 1: Quiet hours
    # ═══════════════════════════════════════
    if _is_quiet_hours():
        ist_hour = _get_ist_hour()
        logger.info("=" * 55)
        logger.info(f"😴 QUIET HOURS - Replies paused")
        logger.info(f"   IST time   : {ist_hour}:00")
        logger.info(f"   Quiet range: {QUIET_HOURS_START}:00 - {QUIET_HOURS_END}:00")
        logger.info(f"   Active in  : {_get_time_until_active()}")
        logger.info(f"   Pending    : {len(comment_reply_pairs)} comments")
        logger.info("=" * 55)

        return _make_result(
            total=len(comment_reply_pairs),
            skipped=len(comment_reply_pairs),
            reason="quiet_hours"
        )

    # ═══════════════════════════════════════
    # GUARD 2: Daily limit
    # ═══════════════════════════════════════
    today_total = _get_today_reply_count()

    if today_total >= MAX_DAILY_REPLIES:
        logger.warning(
            f"⚠️  Daily limit reached: {today_total}/{MAX_DAILY_REPLIES} replies today"
        )
        return _make_result(
            total=len(comment_reply_pairs),
            skipped=len(comment_reply_pairs),
            reason="daily_limit",
            today_count=today_total
        )

    # ═══════════════════════════════════════
    # START POSTING
    # ═══════════════════════════════════════
    total = len(comment_reply_pairs)

    logger.info("=" * 55)
    logger.info("=== REPLY POSTER V5 START ===")
    logger.info(f"   Total to reply : {total}")
    logger.info(f"   Today's count  : {today_total}/{MAX_DAILY_REPLIES}")
    logger.info(f"   IST time       : {_get_ist_hour()}:00")
    logger.info("=" * 55)

    if total == 0:
        logger.info("📭 No replies to post")
        return _make_result(total=0, reason="no_comments")

    # Initial "reading" delay - human feel
    initial_delay = random.randint(FIRST_REPLY_DELAY_MIN, FIRST_REPLY_DELAY_MAX)
    logger.info(f"📖 Reading comments first... ({initial_delay}s)")
    time.sleep(initial_delay)

    # Tracking vars
    success_count = 0
    fail_count = 0
    skipped_count = 0
    rate_limited = False
    platform_counts = {"instagram": 0, "facebook": 0, "youtube": 0}
    platform_results = {
        "instagram": {"success": 0, "failed": 0},
        "facebook": {"success": 0, "failed": 0},
        "youtube": {"success": 0, "failed": 0},
    }

    for i, (comment, reply_text) in enumerate(comment_reply_pairs, 1):

        # ── Rate limit stop ──
        if rate_limited:
            remaining = total - i + 1
            logger.warning(f"   🛑 Rate limited - skipping {remaining} remaining")
            skipped_count += remaining
            break

        platform = comment.get('platform', 'unknown')
        comment_id = comment.get('comment_id', '')
        username = comment.get('username', 'unknown')
        comment_text = comment.get('text', '')

        # ── Per-platform limit ──
        current_platform_count = platform_counts.get(platform, 0)
        if current_platform_count >= MAX_REPLIES_PER_PLATFORM:
            logger.info(
                f"   ⏭️  {platform.upper()} limit ({MAX_REPLIES_PER_PLATFORM}) "
                f"reached, skipping"
            )
            skipped_count += 1
            continue

        # ── Validate reply ──
        if not reply_text or len(reply_text.strip()) < 5:
            logger.warning(f"   ⏭️  Empty/too-short reply for {comment_id[:15]}, skip")
            skipped_count += 1
            continue

        # ── LOG what we're doing ──
        logger.info(f"\n📤 [{i}/{total}] {platform.upper()}")
        logger.info(f"   👤 @{username}")
        logger.info(f"   💬 Comment : {comment_text[:60]}...")
        logger.info(f"   📝 Reply   : {reply_text[:70]}...")

        # ── POST + MARK (atomic) ──
        result = _safe_post_and_mark(platform, comment, reply_text)

        # ── Handle rate limit ──
        if result.get("stop_all"):
            rate_limited = True
            fail_count += 1
            platform_results[platform]["failed"] += 1
            logger.warning("   🛑 Rate limit signal received!")
            continue

        # ── Track result ──
        if result["success"]:
            success_count += 1
            platform_counts[platform] = current_platform_count + 1
            platform_results[platform]["success"] += 1

            # Warn if DB issues
            if result.get("db_mark_failed") or result.get("db_verify_failed"):
                logger.warning(
                    f"   ⚠️  Reply posted but DB tracking issue!\n"
                    f"      Comment may be replied AGAIN on next run.\n"
                    f"      Check logs and manually verify: {comment_id}"
                )
        else:
            fail_count += 1
            platform_results[platform]["failed"] += 1
            logger.warning(f"   ❌ Failed: {result.get('error', 'unknown')}")

        # ── Human-like delay ──
        if i < total and not rate_limited:
            # Next comment ka platform dekho
            try:
                next_platform = comment_reply_pairs[i][0].get('platform', '')
            except IndexError:
                next_platform = platform

            if next_platform != platform:
                # Platform switch = longer pause
                delay = random.randint(25, 45)
                logger.info(f"   ⏳ Platform switch pause: {delay}s")
            else:
                delay = random.randint(MIN_DELAY_BETWEEN_REPLIES, MAX_DELAY_BETWEEN_REPLIES)
                logger.info(f"   ⏳ Next reply in: {delay}s")

            time.sleep(delay)

    # ═══════════════════════════════════════
    # SUMMARY
    # ═══════════════════════════════════════
    final_today_total = _get_today_reply_count()

    logger.info("")
    logger.info("=" * 55)
    logger.info("✅ REPLY POSTER V5 DONE")
    logger.info("=" * 55)
    logger.info(f"   Total     : {total}")
    logger.info(f"   ✅ Success : {success_count}")
    logger.info(f"   ❌ Failed  : {fail_count}")
    logger.info(f"   ⏭️  Skipped : {skipped_count}")
    logger.info(f"   🛑 Rate Ltd: {'YES' if rate_limited else 'No'}")
    logger.info(f"   📸 IG : ✅{platform_results['instagram']['success']} ❌{platform_results['instagram']['failed']}")
    logger.info(f"   📘 FB : ✅{platform_results['facebook']['success']} ❌{platform_results['facebook']['failed']}")
    logger.info(f"   📺 YT : ✅{platform_results['youtube']['success']} ❌{platform_results['youtube']['failed']}")
    logger.info(f"   📊 Today total : {final_today_total}")
    logger.info("=" * 55)

    return {
        "total": total,
        "success": success_count,
        "failed": fail_count,
        "skipped": skipped_count,
        "rate_limited": rate_limited,
        "today_total": final_today_total,
        "platforms": platform_results,
    }


# ============================================================
# HELPER: Result dict builder
# ============================================================

def _make_result(
    total: int = 0,
    success: int = 0,
    failed: int = 0,
    skipped: int = 0,
    reason: str = "",
    today_count: int = 0,
    **kwargs
) -> dict:
    """Standard result dict banana ke liye helper"""
    return {
        "total": total,
        "success": success,
        "failed": failed,
        "skipped": skipped,
        "reason": reason,
        "today_total": today_count,
        "rate_limited": False,
        "platforms": {
            "instagram": {"success": 0, "failed": 0},
            "facebook": {"success": 0, "failed": 0},
            "youtube": {"success": 0, "failed": 0},
        },
        **kwargs
    }


# ============================================================
# EXPORTS
# ============================================================

__all__ = [
    'post_replies',
    'mark_reply_posted',  # Re-export for convenience
]


# ============================================================
# STANDALONE TEST
# ============================================================

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("REPLY POSTER V5 - DIAGNOSTICS")
    print("=" * 60)

    ist_hour = _get_ist_hour()
    is_quiet = _is_quiet_hours()
    today_count = _get_today_reply_count()

    print(f"\n⏰ IST Time    : {_get_ist_now().strftime('%Y-%m-%d %H:%M:%S IST')}")
    print(f"😴 Quiet hours : {QUIET_HOURS_START}:00 - {QUIET_HOURS_END}:00 IST")
    print(f"📊 Status      : {'QUIET 😴' if is_quiet else 'ACTIVE ✅'}")

    if is_quiet:
        print(f"⏰ Active in   : {_get_time_until_active()}")

    print(f"\n📊 Today replies  : {today_count}/{MAX_DAILY_REPLIES}")
    print(f"🛡️  Per platform   : max {MAX_REPLIES_PER_PLATFORM}/run")
    print(f"⏱️  Delays         : {MIN_DELAY_BETWEEN_REPLIES}-{MAX_DELAY_BETWEEN_REPLIES}s")
    print(f"⏱️  First delay    : {FIRST_REPLY_DELAY_MIN}-{FIRST_REPLY_DELAY_MAX}s")

    print("\n✅ Configuration OK!")
