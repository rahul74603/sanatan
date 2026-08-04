"""
Central Configuration - Single Source of Truth
Production-grade config management with validation, categorization, and safe defaults

V2 UPDATE: Added TTS, Reel Video, YouTube configs
"""
import os
from dotenv import load_dotenv

load_dotenv()


# ═══════════════════════════════════════════════════════════
# SAFE ENVIRONMENT PARSING
# ═══════════════════════════════════════════════════════════
# A malformed/empty GitHub secret must not crash the whole application while
# importing settings.  Keep all defaults in one place and log only at runtime
# (settings is imported by almost every module).
def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None or not value.strip():
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def _env_int(name: str, default: int, minimum: int = None) -> int:
    value = os.getenv(name)
    try:
        parsed = int(value) if value is not None and value.strip() else default
    except (TypeError, ValueError):
        parsed = default
    return max(parsed, minimum) if minimum is not None else parsed


def _env_float(name: str, default: float, minimum: float = None) -> float:
    value = os.getenv(name)
    try:
        parsed = float(value) if value is not None and value.strip() else default
    except (TypeError, ValueError):
        parsed = default
    return max(parsed, minimum) if minimum is not None else parsed


def _env_hours(name: str, default: str) -> list:
    raw = os.getenv(name, default)
    hours = []
    for item in (raw or "").split(","):
        try:
            hour = int(item.strip())
        except (TypeError, ValueError):
            continue
        if 0 <= hour <= 23:
            hours.append(hour)
    return hours or [int(item) for item in default.split(",")]


# ═══════════════════════════════════════════════════════════
# 🌐 GOOGLE CLOUD PLATFORM
# ═══════════════════════════════════════════════════════════
PROJECT_ID = os.getenv("PROJECT_ID")
LOCATION = os.getenv("LOCATION", "us-central1")
BUCKET_NAME = os.getenv("BUCKET_NAME")
GOOGLE_APPLICATION_CREDENTIALS = os.getenv(
    "GOOGLE_APPLICATION_CREDENTIALS",
    "spiritual-service-account.json"
)


# ═══════════════════════════════════════════════════════════
# 🤖 GEMINI AI (Text Generation)
# Change model in .env → GEMINI_MODEL=xxx
# ═══════════════════════════════════════════════════════════
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-flash-latest")

# Gemini generation defaults
GEMINI_TEMPERATURE = _env_float("GEMINI_TEMPERATURE", 0.9)
GEMINI_MAX_TOKENS = _env_int("GEMINI_MAX_TOKENS", 1000, minimum=1)
GEMINI_TOP_P = _env_float("GEMINI_TOP_P", 0.95, minimum=0.0)


# ═══════════════════════════════════════════════════════════
# 🎨 VERTEX AI IMAGEN (Premium Image Generation)
#
# Available models (best to fastest):
#   • imagen-4.0-generate-preview-06-06  → BEST quality (~₹2.5/image)
#   • imagen-3.0-generate-002            → BALANCED (~₹1.5/image) [DEFAULT]
#   • imagen-3.0-fast-generate-001       → FASTEST (~₹1/image)
# ═══════════════════════════════════════════════════════════
USE_VERTEX_AI = _env_bool("USE_VERTEX_AI", True)
VERTEX_MODEL = os.getenv("VERTEX_MODEL", "imagen-3.0-generate-002").strip()
VERTEX_MAX_RETRIES = _env_int("VERTEX_MAX_RETRIES", 3, minimum=1)
VERTEX_RETRY_DELAY = _env_int("VERTEX_RETRY_DELAY", 5, minimum=0)  # seconds
VERTEX_ASPECT_RATIO = os.getenv("VERTEX_ASPECT_RATIO", "1:1")

# Cost tracking thresholds (INR)
VERTEX_DAILY_BUDGET = _env_float("VERTEX_DAILY_BUDGET", 100.0, minimum=0.0)
VERTEX_MONTHLY_BUDGET = _env_float("VERTEX_MONTHLY_BUDGET", 2000.0, minimum=0.0)


# ═══════════════════════════════════════════════════════════
# 🖼️ POLLINATIONS.AI (Free Fallback)
# ═══════════════════════════════════════════════════════════
POLLINATIONS_ENABLED = _env_bool("POLLINATIONS_ENABLED", True)
POLLINATIONS_MAX_RETRIES = _env_int("POLLINATIONS_MAX_RETRIES", 3, minimum=1)
POLLINATIONS_TIMEOUT = _env_int("POLLINATIONS_TIMEOUT", 120, minimum=1)


# ═══════════════════════════════════════════════════════════
# 📱 META - INSTAGRAM & FACEBOOK
# ═══════════════════════════════════════════════════════════
INSTAGRAM_ACCOUNT_ID = os.getenv("INSTAGRAM_ACCOUNT_ID")
FACEBOOK_PAGE_ID = os.getenv("FACEBOOK_PAGE_ID")
ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")
META_APP_ID = os.getenv("META_APP_ID")
META_APP_SECRET = os.getenv("META_APP_SECRET")

# Meta API version.  v18.0 is retired; keep this overrideable because Meta
# versions have a fixed sunset window.  v25.0 is the current stable version.
_configured_meta_version = os.getenv("META_API_VERSION", "").strip()
if not _configured_meta_version or _configured_meta_version.lower() == "v18.0":
    META_API_VERSION = "v25.0"
else:
    META_API_VERSION = _configured_meta_version

# Publishing delays (seconds)
DELAY_BEFORE_POST_MIN = _env_int("DELAY_BEFORE_POST_MIN", 0, minimum=0)
DELAY_BEFORE_POST_MAX = _env_int("DELAY_BEFORE_POST_MAX", 180, minimum=0)
DELAY_BETWEEN_PLATFORMS_MIN = _env_int("DELAY_BETWEEN_PLATFORMS_MIN", 30, minimum=0)
DELAY_BETWEEN_PLATFORMS_MAX = _env_int("DELAY_BETWEEN_PLATFORMS_MAX", 90, minimum=0)
if DELAY_BETWEEN_PLATFORMS_MAX < DELAY_BETWEEN_PLATFORMS_MIN:
    DELAY_BETWEEN_PLATFORMS_MAX = DELAY_BETWEEN_PLATFORMS_MIN


# ═══════════════════════════════════════════════════════════
# ⏰ POSTING SCHEDULE (IST)
# ═══════════════════════════════════════════════════════════
POSTING_HOURS = _env_hours("POSTING_HOURS", "8,13,20")
TIME_VARIATION_MINUTES = _env_int("TIME_VARIATION_MINUTES", 45, minimum=0)
POSTS_PER_DAY = _env_int("POSTS_PER_DAY", 3, minimum=1)


# ═══════════════════════════════════════════════════════════
# 📝 CONTENT SETTINGS
# ═══════════════════════════════════════════════════════════
MAX_CAPTION_LENGTH = _env_int("MAX_CAPTION_LENGTH", 2200, minimum=1)
MIN_CAPTION_LENGTH = _env_int("MIN_CAPTION_LENGTH", 50, minimum=0)
MAX_HASHTAGS = _env_int("MAX_HASHTAGS", 25, minimum=0)
IMAGE_ASPECT_RATIO = os.getenv("IMAGE_ASPECT_RATIO", "1:1")


# ═══════════════════════════════════════════════════════════
# ✅ QUALITY THRESHOLDS
# ═══════════════════════════════════════════════════════════
IMAGE_QUALITY_MIN_BYTES = _env_int("IMAGE_QUALITY_MIN_BYTES", 30000, minimum=0)
IMAGE_MIN_DIMENSION = _env_int("IMAGE_MIN_DIMENSION", 512, minimum=1)
MAX_REGENERATION_ATTEMPTS = _env_int("MAX_REGENERATION_ATTEMPTS", 3, minimum=1)
QUALITY_SCORE_THRESHOLD = _env_int("QUALITY_SCORE_THRESHOLD", 60, minimum=0)


# ═══════════════════════════════════════════════════════════
# 💾 DATABASE
# ═══════════════════════════════════════════════════════════
DB_PATH = os.getenv("DB_PATH", "divine_poster.db")
DB_BACKUP_ENABLED = _env_bool("DB_BACKUP_ENABLED", True)


# ═══════════════════════════════════════════════════════════
# 📊 ANALYTICS
# ═══════════════════════════════════════════════════════════
ANALYTICS_ENABLED = _env_bool("ANALYTICS_ENABLED", True)
ANALYTICS_FETCH_DELAY_MINUTES = _env_int("ANALYTICS_FETCH_DELAY_MINUTES", 60, minimum=0)
INSIGHTS_MIN_POSTS = _env_int("INSIGHTS_MIN_POSTS", 3, minimum=1)


# ═══════════════════════════════════════════════════════════
# 📋 LOGGING
# ═══════════════════════════════════════════════════════════
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
LOG_DIR = os.getenv("LOG_DIR", "logs")
LOG_KEEP_DAYS = _env_int("LOG_KEEP_DAYS", 30, minimum=1)


# ═══════════════════════════════════════════════════════════
# 🚀 PERFORMANCE
# ═══════════════════════════════════════════════════════════
ENABLE_CACHING = _env_bool("ENABLE_CACHING", True)
PARALLEL_UPLOAD = _env_bool("PARALLEL_UPLOAD", False)


# ═══════════════════════════════════════════════════════════
# 🆕 V2 - GOOGLE CLOUD TEXT-TO-SPEECH (Reels Voice)
# ═══════════════════════════════════════════════════════════
TTS_ENABLED = _env_bool("TTS_ENABLED", True)
TTS_LANGUAGE = os.getenv("TTS_LANGUAGE", "hi-IN")

# Hindi Neural2 voices (best quality)
TTS_VOICE_MALE = os.getenv("TTS_VOICE_MALE", "hi-IN-Neural2-B")
TTS_VOICE_FEMALE = os.getenv("TTS_VOICE_FEMALE", "hi-IN-Neural2-A")

# Speech parameters
TTS_SPEAKING_RATE = _env_float("TTS_SPEAKING_RATE", 0.95, minimum=0.25)
TTS_PITCH = _env_float("TTS_PITCH", 0.0)
TTS_AUDIO_ENCODING = "MP3"

# Category → Voice gender mapping (User's choice)
# Krishna/Ram/Shiva/Hanuman/Ganesha = Male
# Durga/Saraswati/Motherly = Female
TTS_CATEGORY_VOICE = {
    "krishna": "male",
    "shiva": "male",
    "ram": "male",
    "hanuman": "male",
    "ganesha": "male",
    "durga": "female",
    "spiritual_nature": "female",
    "motivational": "male",
    "temple": "male",
    "daily_wisdom": "female",
    "festival": "female",
    "festival_moments": "female",
}


# ═══════════════════════════════════════════════════════════
# 🆕 V2 - REEL VIDEO CONFIG
# ═══════════════════════════════════════════════════════════

# Duration (Instagram Reels max = 90s, YT Shorts max = 60s)
REEL_DURATION_MIN = _env_int("REEL_DURATION_MIN", 60, minimum=1)
REEL_DURATION_MAX = _env_int("REEL_DURATION_MAX", 90, minimum=1)

# Video specs (9:16 portrait for all platforms)
REEL_FPS = _env_int("REEL_FPS", 30, minimum=1)
REEL_WIDTH = 1080
REEL_HEIGHT = 1920
REEL_ASPECT_RATIO = "9:16"

# Story parameters (Hindi narration)
REEL_STORY_MIN_WORDS = _env_int("REEL_STORY_MIN_WORDS", 150, minimum=1)
REEL_STORY_MAX_WORDS = _env_int("REEL_STORY_MAX_WORDS", 180, minimum=1)
REEL_NUM_SCENES = _env_int("REEL_NUM_SCENES", 6, minimum=1)

# Video encoding quality
REEL_VIDEO_CODEC = "libx264"
REEL_VIDEO_CRF = 23  # 18-28 range (lower = better quality)
REEL_VIDEO_PRESET = "medium"
REEL_AUDIO_CODEC = "aac"
REEL_AUDIO_BITRATE = "128k"

# Ken Burns effect (subtle zoom animation)
REEL_KEN_BURNS_ENABLED = True
REEL_KEN_BURNS_ZOOM = 1.15  # 15% zoom over scene duration

# Transitions between scenes
REEL_TRANSITION_TYPE = "crossfade"
REEL_TRANSITION_DURATION = 0.5  # seconds

# Background music (user provides in assets/music/)
REEL_MUSIC_ENABLED = True
REEL_MUSIC_VOLUME = 0.15  # 15% (voice dominant)
REEL_MUSIC_FOLDER = "assets/music"

# Subtitles (word-by-word highlighted)
REEL_SUBTITLE_ENABLED = True
REEL_SUBTITLE_FONT_SIZE = 60
REEL_SUBTITLE_HIGHLIGHT_COLOR = "#FFD700"  # Gold
REEL_SUBTITLE_BASE_COLOR = "#FFFFFF"       # White
REEL_SUBTITLE_STROKE_COLOR = "#000000"     # Black outline

# Reel posting time (1 PM IST)
REEL_POSTING_HOUR = _env_int("REEL_POSTING_HOUR", 13, minimum=0)


# ═══════════════════════════════════════════════════════════
# 🆕 V2 - YOUTUBE SHORTS
# ═══════════════════════════════════════════════════════════
YOUTUBE_ENABLED = _env_bool("YOUTUBE_ENABLED", True)
YOUTUBE_CHANNEL_ID = os.getenv("YOUTUBE_CHANNEL_ID", "")

# OAuth credentials files (project-specific naming)
YOUTUBE_CLIENT_SECRETS_FILE = os.getenv(
    "YOUTUBE_CLIENT_SECRETS_FILE",
    "sanatani_youtube_client_secrets.json"
)
YOUTUBE_TOKEN_FILE = os.getenv(
    "YOUTUBE_TOKEN_FILE",
    "sanatani_youtube_token.json"
)

# Upload settings
YOUTUBE_CATEGORY_ID = os.getenv("YOUTUBE_CATEGORY_ID", "22")
YOUTUBE_PRIVACY_STATUS = os.getenv("YOUTUBE_PRIVACY_STATUS", "public").strip().lower()
if YOUTUBE_PRIVACY_STATUS not in {"public", "unlisted", "private"}:
    YOUTUBE_PRIVACY_STATUS = "public"
YOUTUBE_MADE_FOR_KIDS = _env_bool("YOUTUBE_MADE_FOR_KIDS", False)
YOUTUBE_UPLOAD_MAX_RETRIES = _env_int("YOUTUBE_UPLOAD_MAX_RETRIES", 3, minimum=1)

# YouTube's official Data API cannot create a Community image post.  For the
# morning image pipeline we therefore turn the generated image into a short,
# portrait MP4 and upload that Short.  This is enabled separately so a failed
# YouTube OAuth setup never prevents Instagram/Facebook publishing.
YOUTUBE_IMAGE_ENABLED = _env_bool("YOUTUBE_IMAGE_ENABLED", True)
YOUTUBE_IMAGE_DURATION_SECONDS = _env_int(
    "YOUTUBE_IMAGE_DURATION_SECONDS", 8, minimum=1
)


# ═══════════════════════════════════════════════════════════
# 🎯 FEATURE FLAGS
# ═══════════════════════════════════════════════════════════
FEATURES = {
    # Existing
    "vertex_ai": USE_VERTEX_AI,
    "pollinations_fallback": POLLINATIONS_ENABLED,
    "analytics": ANALYTICS_ENABLED,
    "humanizer": _env_bool("ENABLE_HUMANIZER", True),
    "duplicate_check": _env_bool("ENABLE_DUPLICATE_CHECK", True),
    "self_learning": _env_bool("ENABLE_SELF_LEARNING", True),
    "festival_detection": _env_bool("ENABLE_FESTIVAL_DETECTION", True),
    "smart_scheduling": _env_bool("ENABLE_SMART_SCHEDULING", True),

    # 🆕 V2
    "tts": TTS_ENABLED,
    "reels": True,
    "youtube": YOUTUBE_ENABLED,
    "youtube_image_short": YOUTUBE_ENABLED and YOUTUBE_IMAGE_ENABLED,
    "video_watermark": True,
}


# ═══════════════════════════════════════════════════════════
# VALIDATION
# ═══════════════════════════════════════════════════════════

def validate():
    """
    Validate all required configs exist and are valid.
    Prints colorful status report.
    """
    print("\n" + "═" * 60)
    print("  🚀 DIVINE AUTO POSTER - CONFIG VALIDATION")
    print("═" * 60)

    # ═══════════════════════════════════════════
    # REQUIRED FIELDS CHECK
    # ═══════════════════════════════════════════
    required = {
        "PROJECT_ID": PROJECT_ID,
        "GEMINI_API_KEY": GEMINI_API_KEY,
        "INSTAGRAM_ACCOUNT_ID": INSTAGRAM_ACCOUNT_ID,
        "FACEBOOK_PAGE_ID": FACEBOOK_PAGE_ID,
        "ACCESS_TOKEN": ACCESS_TOKEN,
        "BUCKET_NAME": BUCKET_NAME,
    }

    missing = [k for k, v in required.items() if not v]

    if missing:
        print("\n❌ MISSING REQUIRED CONFIGS:")
        for key in missing:
            print(f"   • {key}")
        raise ValueError(f"Missing configs: {', '.join(missing)}")

    # ═══════════════════════════════════════════
    # DISPLAY CONFIGURATION SUMMARY
    # ═══════════════════════════════════════════
    print("\n✅ ALL REQUIRED CONFIGS PRESENT\n")

    # Google Cloud
    print("📁 GOOGLE CLOUD")
    print(f"   Project ID    : {PROJECT_ID}")
    print(f"   Location      : {LOCATION}")
    print(f"   Bucket        : {BUCKET_NAME}")

    # Gemini
    print("\n🤖 GEMINI AI (Text)")
    print(f"   Model         : {GEMINI_MODEL}")
    print(f"   Temperature   : {GEMINI_TEMPERATURE}")
    print(f"   Max Tokens    : {GEMINI_MAX_TOKENS}")

    # Vertex AI
    print("\n🎨 VERTEX AI IMAGEN (Image)")
    print(f"   Enabled       : {'✅ YES' if USE_VERTEX_AI else '❌ NO'}")
    print(f"   Model         : {VERTEX_MODEL}")
    print(f"   Max Retries   : {VERTEX_MAX_RETRIES}")
    print(f"   Retry Delay   : {VERTEX_RETRY_DELAY}s")
    print(f"   Aspect Ratio  : {VERTEX_ASPECT_RATIO}")

    # Estimated cost per image
    cost_map = {
        "imagen-4.0-generate-preview-06-06": "₹2.50 (Best quality)",
        "imagen-3.0-generate-002": "₹1.50 (Balanced) ⭐",
        "imagen-3.0-fast-generate-001": "₹1.00 (Fastest)",
        "imagegeneration@006": "₹1.50 (Stable Imagen 2)",
    }
    est_cost = cost_map.get(VERTEX_MODEL, "Unknown")
    print(f"   Cost/Image    : {est_cost}")

    # Pollinations
    print("\n🖼️  POLLINATIONS.AI (Fallback)")
    print(f"   Enabled       : {'✅ YES' if POLLINATIONS_ENABLED else '❌ NO'}")
    print(f"   Max Retries   : {POLLINATIONS_MAX_RETRIES}")

    # Meta
    print("\n📱 META (Instagram + Facebook)")
    print(f"   API Version   : {META_API_VERSION}")
    print(f"   IG Account    : {INSTAGRAM_ACCOUNT_ID}")
    print(f"   FB Page       : {FACEBOOK_PAGE_ID}")

    # 🆕 TTS
    print("\n🎤 GOOGLE CLOUD TTS (Reels Voice)")
    print(f"   Enabled       : {'✅ YES' if TTS_ENABLED else '❌ NO'}")
    print(f"   Language      : {TTS_LANGUAGE}")
    print(f"   Male Voice    : {TTS_VOICE_MALE}")
    print(f"   Female Voice  : {TTS_VOICE_FEMALE}")
    print(f"   Speaking Rate : {TTS_SPEAKING_RATE}")

    # 🆕 Reel Video
    print("\n🎬 REEL VIDEO")
    print(f"   Duration      : {REEL_DURATION_MIN}-{REEL_DURATION_MAX}s")
    print(f"   Resolution    : {REEL_WIDTH}x{REEL_HEIGHT} (9:16)")
    print(f"   FPS           : {REEL_FPS}")
    print(f"   Scenes        : {REEL_NUM_SCENES}")
    print(f"   Story Words   : {REEL_STORY_MIN_WORDS}-{REEL_STORY_MAX_WORDS}")
    print(f"   BG Music Vol  : {int(REEL_MUSIC_VOLUME*100)}%")
    print(f"   Posting Time  : {REEL_POSTING_HOUR}:00 IST")

    # 🆕 YouTube
    print("\n📺 YOUTUBE SHORTS")
    print(f"   Enabled       : {'✅ YES' if YOUTUBE_ENABLED else '❌ NO'}")
    print(f"   Channel ID    : {YOUTUBE_CHANNEL_ID or '⚠️  NOT SET'}")
    print(f"   Client Secret : {YOUTUBE_CLIENT_SECRETS_FILE}")
    print(f"   Token File    : {YOUTUBE_TOKEN_FILE}")
    print(f"   Privacy       : {YOUTUBE_PRIVACY_STATUS}")
    print(
        f"   Image → Short : "
        f"{'✅ YES' if YOUTUBE_ENABLED and YOUTUBE_IMAGE_ENABLED else '❌ NO'}"
    )
    print(f"   Image duration: {YOUTUBE_IMAGE_DURATION_SECONDS}s")

    # Schedule
    print("\n⏰ POSTING SCHEDULE")
    print(f"   Posts/Day     : {POSTS_PER_DAY}")
    print(f"   Hours (IST)   : {POSTING_HOURS}")
    print(f"   Time Variance : ±{TIME_VARIATION_MINUTES} min")

    # Content
    print("\n📝 CONTENT LIMITS")
    print(f"   Caption Range : {MIN_CAPTION_LENGTH} - {MAX_CAPTION_LENGTH} chars")
    print(f"   Max Hashtags  : {MAX_HASHTAGS}")
    print(f"   Aspect Ratio  : {IMAGE_ASPECT_RATIO}")

    # Features
    print("\n🎯 ENABLED FEATURES")
    for feature, enabled in FEATURES.items():
        status = "✅" if enabled else "❌"
        print(f"   {status} {feature.replace('_', ' ').title()}")

    # ═══════════════════════════════════════════
    # WARNINGS & RECOMMENDATIONS
    # ═══════════════════════════════════════════
    warnings = []

    if USE_VERTEX_AI and VERTEX_MODEL == "imagen-4.0-generate-preview-06-06":
        warnings.append(
            "⚠️  Using premium Imagen 4.0 (₹2.50/image). "
            "Consider imagen-3.0-generate-002 for balance."
        )

    if not POLLINATIONS_ENABLED and not USE_VERTEX_AI:
        warnings.append(
            "❌ CRITICAL: Both Vertex AI and Pollinations disabled! "
            "No image provider available."
        )

    if GEMINI_TEMPERATURE > 1.0:
        warnings.append(
            f"⚠️  Gemini temperature {GEMINI_TEMPERATURE} is very high. "
            "May cause weird outputs."
        )

    if POSTS_PER_DAY > 5:
        warnings.append(
            f"⚠️  {POSTS_PER_DAY} posts/day is aggressive. "
            "Instagram may flag as spam."
        )

    if not os.path.exists(GOOGLE_APPLICATION_CREDENTIALS):
        warnings.append(
            f"⚠️  Service account file not found: {GOOGLE_APPLICATION_CREDENTIALS}"
        )

    # 🆕 V2 warnings
    if YOUTUBE_ENABLED and not YOUTUBE_CHANNEL_ID:
        warnings.append(
            "⚠️  YouTube enabled but YOUTUBE_CHANNEL_ID not set in .env. "
            "YouTube uploads will fail."
        )

    if YOUTUBE_ENABLED and not os.path.exists(YOUTUBE_TOKEN_FILE):
        warnings.append(
            f"⚠️  YouTube token file missing: {YOUTUBE_TOKEN_FILE}. "
            "Uploads need an OAuth token; run `python -m posting.youtube` first."
        )

    if YOUTUBE_ENABLED and not os.path.exists(YOUTUBE_CLIENT_SECRETS_FILE):
        warnings.append(
            f"ℹ️  YouTube client secrets file missing: {YOUTUBE_CLIENT_SECRETS_FILE}. "
            "Only needed for first-time OAuth setup; an existing token is enough to upload."
        )

    if warnings:
        print("\n" + "─" * 60)
        print("⚠️  WARNINGS:")
        print("─" * 60)
        for w in warnings:
            print(f"   {w}")

    print("\n" + "═" * 60)
    print("  ✅ CONFIG VALIDATION COMPLETE")
    print("═" * 60 + "\n")

    return True


def get_config_summary() -> dict:
    """Get config as dict (for logging/debugging)"""
    return {
        "gcp": {
            "project": PROJECT_ID,
            "location": LOCATION,
            "bucket": BUCKET_NAME
        },
        "gemini": {
            "model": GEMINI_MODEL,
            "temperature": GEMINI_TEMPERATURE
        },
        "vertex_ai": {
            "enabled": USE_VERTEX_AI,
            "model": VERTEX_MODEL,
            "retries": VERTEX_MAX_RETRIES
        },
        "pollinations": {
            "enabled": POLLINATIONS_ENABLED,
            "retries": POLLINATIONS_MAX_RETRIES
        },
        "posting": {
            "hours": POSTING_HOURS,
            "posts_per_day": POSTS_PER_DAY
        },
        # 🆕 V2 additions
        "tts": {
            "enabled": TTS_ENABLED,
            "language": TTS_LANGUAGE,
            "male_voice": TTS_VOICE_MALE,
            "female_voice": TTS_VOICE_FEMALE
        },
        "reels": {
            "duration_range": f"{REEL_DURATION_MIN}-{REEL_DURATION_MAX}s",
            "resolution": f"{REEL_WIDTH}x{REEL_HEIGHT}",
            "scenes": REEL_NUM_SCENES,
            "posting_hour": REEL_POSTING_HOUR
        },
        "youtube": {
            "enabled": YOUTUBE_ENABLED,
            "channel_id": YOUTUBE_CHANNEL_ID,
            "privacy": YOUTUBE_PRIVACY_STATUS,
            "image_enabled": YOUTUBE_IMAGE_ENABLED,
            "image_duration_seconds": YOUTUBE_IMAGE_DURATION_SECONDS,
        },
        "features": FEATURES
    }


# ═══════════════════════════════════════════════════════════
# CLI TESTING
# ═══════════════════════════════════════════════════════════

if __name__ == "__main__":
    validate()

    print("\n📄 CONFIG DICT:")
    import json
    print(json.dumps(get_config_summary(), indent=2))