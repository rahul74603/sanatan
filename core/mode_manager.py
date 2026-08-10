"""
Mode Manager — FREE / PRO / AUTO switching
===========================================

Ye module ek "FREE / PRO mode" system provide karta hai taaki aap bina paise
(khali FREE providers) aur paise waale (PRO) dono modes ke beech switch kar
sako — chahe budget khatam ho jaye.

Modes:
------
FREE  (₹0):
    - Images sirf FREE providers (Pollinations.ai) se banti hain.
    - Paid Vertex AI Imagen kabhi call nahi hota → koi paisa nahi lagta.
    - Reels / video DISABLED. Agar reel command chalao to uski jagah
      ek picture (image) generate hoti hai — "kam se kam pic to bane".

PRO   (paid):
    - Premium Vertex AI Imagen images (behtar quality).
    - Reels / video (TTS, music, subtitles) enabled.
    - Paise lagte hain.

AUTO  (default):
    - PRO se shuru hota hai.
    - Agar daily/monthly budget exhausted ho jaye (ya paid generation fail
      ho) to automatically FREE mode mein degrade ho jata hai — taaki kam se
      kam picture to ban hi jaye.

Config / switching:
-------------------
- .env:  APP_MODE=free | APP_MODE=pro | APP_MODE=auto
- CLI:   python main.py mode free|pro|auto|status
- Runtime override persistent `logs/mode_state.json` mein save hota hai,
  taaki `python main.py mode free` ke baad bhi server restart par bana rahe.
"""

import json
from datetime import datetime, date
from pathlib import Path

from config.settings import (
    APP_MODE,
    MODE_STATE_FILE,
    FREE_MODE_DISABLES_REELS,
    FREE_MODE_ALLOWS_VIDEO,
    VIDEO_EVERY_DAYS,
)
from utils.logger import get_logger

logger = get_logger("mode_manager")

MODE_FREE = "free"
MODE_PRO = "pro"
MODE_AUTO = "auto"

VALID_MODES = (MODE_FREE, MODE_PRO, MODE_AUTO)
RESOLVED_MODES = (MODE_FREE, MODE_PRO)

_MODE_LABELS = {
    MODE_FREE: "FREE (₹0 — sirf Pollinations images, reels off)",
    MODE_PRO:  "PRO (paid — premium images + reels)",
    MODE_AUTO: "AUTO (PRO, budget khatam → FREE fallback)",
}


# ============================================================
# PERSISTENT STATE
# ============================================================

def _state_path() -> Path:
    return Path(MODE_STATE_FILE)


def _load_state() -> dict:
    """Load persistent mode state JSON (safe)."""
    try:
        if _state_path().exists():
            with open(_state_path(), "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        logger.warning(f"Mode state load fail hua: {e}")
    return {"override": None, "updated_at": None, "last_reason": None}


def _save_state(state: dict):
    """Persist mode state JSON."""
    try:
        _state_path().parent.mkdir(parents=True, exist_ok=True)
        with open(_state_path(), "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.warning(f"Mode state save fail hua: {e}")


# ============================================================
# CONFIGURED / OVERRIDE MODE
# ============================================================

def get_configured_mode() -> str:
    """Mode from .env / settings (free|pro|auto)."""
    mode = (APP_MODE or MODE_AUTO).strip().lower()
    if mode not in VALID_MODES:
        mode = MODE_AUTO
    return mode


def get_override_mode():
    """Persisted override from `python main.py mode ...` (or None)."""
    return _load_state().get("override")


def set_override_mode(mode: str) -> bool:
    """
    Set a persistent override (free|pro|auto).
    auto → override clear karke automatic decision allow hota hai.
    Returns True agar sahi mode set hua.
    """
    mode = (mode or "").strip().lower()
    if mode not in VALID_MODES:
        logger.error(f"❌ Invalid mode '{mode}'. Valid: free | pro | auto")
        return False

    state = _load_state()
    # `auto` = koi override nahi — pure .env / budget decision
    state["override"] = None if mode == MODE_AUTO else mode
    state["mode"] = mode
    state["updated_at"] = datetime.now().isoformat()
    if mode == MODE_AUTO:
        state["last_reason"] = "override cleared → auto (budget-based)"
    _save_state(state)
    logger.info(f"🎛️  Mode override → {mode.upper()}")
    return True


def clear_override():
    """Clear any persistent override (back to APP_MODE logic)."""
    state = _load_state()
    state["override"] = None
    state["updated_at"] = datetime.now().isoformat()
    state["last_reason"] = "override cleared"
    _save_state(state)


# ============================================================
# BUDGET CHECK (AUTO mode)
# ============================================================

def _budget_allows_paid() -> bool:
    """
    Check whether paid (Vertex Imagen) generation is still within budget.
    Lazy import taaki vertex_ai dependency fail hone par bhi mode kaam kare.
    """
    try:
        from utils.vertex_ai import estimate_images_remaining
        remaining = estimate_images_remaining()
        daily = remaining.get("daily_budget_left_inr", 0)
        monthly = remaining.get("monthly_budget_left_inr", 0)
        if daily <= 0 or monthly <= 0:
            return False
        return True
    except Exception as e:
        # Budget nahi pata → conservative: paid allow karo (PRO default)
        logger.warning(f"Budget check unavailable ({e}). Proceeding as PRO.")
        return True


# ============================================================
# RESOLVED MODE
# ============================================================

def get_resolved_mode() -> str:
    """
    Current effective mode: 'free' ya 'pro'.

    Order:
      1. Runtime override (persisted) → free|pro
      2. APP_MODE=free → free
      3. APP_MODE=pro  → pro
      4. APP_MODE=auto → budget-based decision
    """
    override = get_override_mode()
    if override in RESOLVED_MODES:
        return override

    cfg = get_configured_mode()
    if cfg == MODE_FREE:
        return MODE_FREE
    if cfg == MODE_PRO:
        return MODE_PRO

    # AUTO
    if _budget_allows_paid():
        return MODE_PRO
    return MODE_FREE


def is_free_mode() -> bool:
    return get_resolved_mode() == MODE_FREE


def is_pro_mode() -> bool:
    return get_resolved_mode() == MODE_PRO


# ============================================================
# CAPABILITY HELPERS
# ============================================================

def can_use_paid_images() -> bool:
    """
    True → paid Vertex Imagen use ho sakta hai (PRO / AUTO-with-budget).
    False → sirf FREE Pollinations (FREE mode ya budget khatam).
    """
    return is_pro_mode()


def can_use_video() -> bool:
    """
    True → reels/video ban sakte hain (mode ke hisaab se).
    False → reels disabled; uski jagah picture banegi.

    - PRO mode → hamesha True (paid premium video).
    - FREE mode → True sirf agar free video path available ho
      (FREE_MODE_ALLOWS_VIDEO + video pipeline dependencies present).
    """
    if is_free_mode():
        return can_make_video_free()
    return True


def can_make_video_free() -> bool:
    """
    FREE mode mein bhi video bana sakte hain kya?

    Free video = Pollinations free images + ffmpeg render (₹0 images).
    TTS/caption/Gemini ke paise negligible hain (~₹1/video).

    Returns False agar:
      - FREE_MODE_ALLOWS_VIDEO=false (band kar diya ho), ya
      - FREE_MODE_DISABLES_REELS=true (reels completely off), ya
      - video pipeline modules available nahi hain (install nahi hue).
    """
    if not FREE_MODE_ALLOWS_VIDEO:
        return False
    if FREE_MODE_DISABLES_REELS:
        return False
    # Video pipeline dependencies available honi chahiye
    try:
        import reels.reel_agent          # noqa: F401
        import video_engine.video_builder  # noqa: F401
        import video_engine.tts_engine   # noqa: F401
        import video_engine.subtitle_generator  # noqa: F401
        import core.reel_engine          # noqa: F401
        from utils.gcs_helper import upload_video  # noqa: F401
        return True
    except Exception:
        return False


def _get_last_video_date():
    """
    DB se last video/reel ka date nikaalo (post_type IN 'reel','video').
    Circular import se bachne ke liye lazy import. Failure par None.
    """
    try:
        from core.database import get_connection
        conn = get_connection()
        c = conn.cursor()
        c.execute(
            "SELECT post_date FROM post_history "
            "WHERE post_type IN ('reel','video') "
            "AND post_date IS NOT NULL "
            "ORDER BY post_date DESC LIMIT 1"
        )
        row = c.fetchone()
        conn.close()
        if not row or not row[0]:
            return None
        raw = str(row[0]).strip()
        try:
            return datetime.fromisoformat(raw.replace("Z", "+00:00")).date()
        except Exception:
            try:
                return date.fromisoformat(raw[:10])
            except Exception:
                return None
    except Exception:
        return None


def is_video_day(reference_date=None) -> bool:
    """
    Aaj video wala din hai kya? (har VIDEO_EVERY_DAYS din mein 1 video)

    Robust logic — DB mein last video ki date dekhkar:
      - Koi video abhi nahi bana → stable day-parity se alternate karte hain.
      - Video ban chuki hai → last video ke baad se VIDEO_EVERY_DAYS din ho
        gaye hain to aaj video day.
    Isse agar ek run skip/miss ho jaye to bhi gap garanteed rehta hai.
    """
    ref = reference_date or datetime.now().date()
    last = _get_last_video_date()

    if last is None:
        # Abhi tak koi video nahi — day parity se alternate (har N din)
        return ref.toordinal() % VIDEO_EVERY_DAYS == 0

    diff = (ref - last).days
    return diff >= VIDEO_EVERY_DAYS


def should_make_video(reference_date=None) -> bool:
    """
    Abhi video banana chahiye kya?
    = video day ho AND current mode video allow karta ho
      (PRO → yes; FREE → yes sirf agar free video possible ho).
    """
    if not is_video_day(reference_date):
        return False
    return can_use_video()


def degrade_to_free(reason: str):
    """
    AUTO mode mein paid generation fail / budget exhausted hone par
    effective mode ko is run ke liye FREE kar do.
    (Sirf in-memory override set karta hai — persistent nahi, taaki
    budget bharne ke baad pro wapas aa sake.)
    """
    # Agar already free hai to kuch nahi karna
    if is_free_mode():
        return
    logger.warning(
        f"⬇️  Auto-degrade PRO → FREE: {reason} "
        f"(is run ke liye sirf FREE providers use honge, pic to bane hi)"
    )


def get_mode_status() -> dict:
    """Full status dict for `python main.py mode status` / health / cost."""
    configured = get_configured_mode()
    resolved = get_resolved_mode()
    override = get_override_mode()
    state = _load_state()

    return {
        "configured": configured,
        "configured_label": _MODE_LABELS.get(configured, configured),
        "override": override,
        "resolved": resolved,
        "resolved_label": _MODE_LABELS.get(resolved, resolved),
        "free_mode": resolved == MODE_FREE,
        "pro_mode": resolved == MODE_PRO,
        "can_use_paid_images": resolved == MODE_PRO,
        "can_use_video": can_use_video(),
        "can_make_video_free": can_make_video_free(),
        "video_every_days": VIDEO_EVERY_DAYS,
        "is_video_day": is_video_day(),
        "reels_disabled_in_free": bool(FREE_MODE_DISABLES_REELS),
        "free_allows_video": bool(FREE_MODE_ALLOWS_VIDEO),
        "state_file": str(_state_path()),
        "updated_at": state.get("updated_at"),
        "last_reason": state.get("last_reason"),
    }


# ============================================================
# DISPLAY
# ============================================================

def display_mode_status():
    """Print beautiful mode status box."""
    s = get_mode_status()

    logger.info("")
    logger.info("┌────────────────────────────────────────────┐")
    logger.info("│      🎛️  APP MODE STATUS                    │")
    logger.info("├────────────────────────────────────────────┤")
    logger.info(f"│ Configured : {s['configured'].upper():<10}")
    logger.info(f"│ Override   : {(s['override'] or '—').upper():<10}")
    logger.info(f"│ Active     : {s['resolved'].upper():<10}")
    logger.info("├────────────────────────────────────────────┤")
    logger.info(f"│ Paid images: {'✅ ALLOWED' if s['can_use_paid_images'] else '❌ FREE only'}")
    logger.info(f"│ Reels/video: {'✅ ENABLED' if s['can_use_video'] else '❌ DISABLED → pic banegi'}")
    logger.info(f"│ Video freq : har {s['video_every_days']} din mein 1 video "
                f"({'🗓️ aaj video day' if s['is_video_day'] else '🗓️ aaj video day nahi'})")
    if s["last_reason"]:
        logger.info(f"│ Reason     : {s['last_reason']}")
    logger.info("└────────────────────────────────────────────┘")

    print("")
    print("🎛️  APP MODE STATUS")
    print(f"   Configured : {s['configured'].upper()}  ({s['configured_label']})")
    print(f"   Override   : {s['override'] or '— (none, .env APP_MODE decide karta hai)'}")
    print(f"   Active     : {s['resolved'].upper()}  ({s['resolved_label']})")
    print(f"   Paid images: {'✅ ALLOWED' if s['can_use_paid_images'] else '❌ FREE only (Pollinations)'}")
    print(f"   Reels/video: {'✅ ENABLED' if s['can_use_video'] else '❌ DISABLED → picture generate hogi'}")
    print(f"   Video freq : har {s['video_every_days']} din mein 1 video "
          f"({'🗓️ aaj video day hai' if s['is_video_day'] else '🗓️ aaj video day nahi'})")
    if s["last_reason"]:
        print(f"   Reason     : {s['last_reason']}")
    print("")
    print("   Switch karo:  python main.py mode free | pro | auto")
    print("   Video freq:    VIDEO_EVERY_DAYS=n (.env mein) → har n din mein 1 video")
    print("")


# ============================================================
# STANDALONE TEST
# ============================================================

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        cmd = sys.argv[1].lower()
        if cmd in VALID_MODES:
            set_override_mode(cmd)
        elif cmd == "status":
            pass
        else:
            print(f"❌ Usage: python -m core.mode_manager free|pro|auto|status")
            sys.exit(2)
    display_mode_status()
