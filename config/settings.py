"""
Central Configuration - Single Source of Truth
Production-grade config management with validation, categorization, and safe defaults

V2 UPDATE: Added TTS, Reel Video, YouTube configs
"""
import os
from dotenv import load_dotenv

load_dotenv()


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
GEMINI_TEMPERATURE = float(os.getenv("GEMINI_TEMPERATURE", "0.9"))
GEMINI_MAX_TOKENS = int(os.getenv("GEMINI_MAX_TOKENS", "1000"))
GEMINI_TOP_P = float(os.getenv("GEMINI_TOP_P", "0.95"))


# ═══════════════════════════════════════════════════════════
# 🎨 VERTEX AI IMAGEN (Premium Image Generation)
#
# Available models (best to fastest):
#   • imagen-4.0-generate-preview-06-06  → BEST quality (~₹2.5/image)
#   • imagen-3.0-generate-002            → BALANCED (~₹1.5/image) [DEFAULT]
#   • imagen-3.0-fast-generate-001       → FASTEST (~₹1/image)
# ═══════════════════════════════════════════════════════════
USE_VERTEX_AI = os.getenv("USE_VERTEX_AI", "true").lower() == "true"
VERTEX_MODEL = os.getenv("VERTEX_MODEL", "imagen-3.0-generate-002").strip()
VERTEX_MAX_RETRIES = int(os.getenv("VERTEX_MAX_RETRIES", "3"))
VERTEX_RETRY_DELAY = int(os.getenv("VERTEX_RETRY_DELAY", "5"))  # seconds
VERTEX_ASPECT_RATIO = os.getenv("VERTEX_ASPECT_RATIO", "1:1")

# Cost tracking thresholds (INR)
VERTEX_DAILY_BUDGET = float(os.getenv("VERTEX_DAILY_BUDGET", "100.0"))
VERTEX_MONTHLY_BUDGET = float(os.getenv("VERTEX_MONTHLY_BUDGET", "2000.0"))


# ═══════════════════════════════════════════════════════════
# 🖼️ POLLINATIONS.AI (Free Fallback)
# ═══════════════════════════════════════════════════════════
POLLINATIONS_ENABLED = os.getenv("POLLINATIONS_ENABLED", "true").lower() == "true"
POLLINATIONS_MAX_RETRIES = int(os.getenv("POLLINATIONS_MAX_RETRIES", "3"))
POLLINATIONS_TIMEOUT = int(os.getenv("POLLINATIONS_TIMEOUT", "120"))


# ═══════════════════════════════════════════════════════════
# 📱 META - INSTAGRAM & FACEBOOK
# ═══════════════════════════════════════════════════════════
INSTAGRAM_ACCOUNT_ID = os.getenv("INSTAGRAM_ACCOUNT_ID")
FACEBOOK_PAGE_ID = os.getenv("FACEBOOK_PAGE_ID")
ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")
META_APP_ID = os.getenv("META_APP_ID")
META_APP_SECRET = os.getenv("META_APP_SECRET")

# Meta API version
META_API_VERSION = os.getenv("META_API_VERSION", "v18.0")

# Publishing delays (seconds)
DELAY_BEFORE_POST_MIN = int(os.getenv("DELAY_BEFORE_POST_MIN", "0"))
DELAY_BEFORE_POST_MAX = int(os.getenv("DELAY_BEFORE_POST_MAX", "180"))
DELAY_BETWEEN_PLATFORMS_MIN = int(os.getenv("DELAY_BETWEEN_PLATFORMS_MIN", "30"))
DELAY_BETWEEN_PLATFORMS_MAX = int(os.getenv("DELAY_BETWEEN_PLATFORMS_MAX", "90"))


# ═══════════════════════════════════════════════════════════
# ⏰ POSTING SCHEDULE (IST)
# ═══════════════════════════════════════════════════════════
POSTING_HOURS = [
    int(h.strip())
    for h in os.getenv("POSTING_HOURS", "8,13,20").split(",")
]
TIME_VARIATION_MINUTES = int(os.getenv("TIME_VARIATION_MINUTES", "45"))
POSTS_PER_DAY = int(os.getenv("POSTS_PER_DAY", "3"))


# ═══════════════════════════════════════════════════════════
# 📝 CONTENT SETTINGS
# ═══════════════════════════════════════════════════════════
MAX_CAPTION_LENGTH = int(os.getenv("MAX_CAPTION_LENGTH", "2200"))
MIN_CAPTION_LENGTH = int(os.getenv("MIN_CAPTION_LENGTH", "50"))
MAX_HASHTAGS = int(os.getenv("MAX_HASHTAGS", "25"))
IMAGE_ASPECT_RATIO = os.getenv("IMAGE_ASPECT_RATIO", "1:1")


# ═══════════════════════════════════════════════════════════
# ✅ QUALITY THRESHOLDS
# ═══════════════════════════════════════════════════════════
IMAGE_QUALITY_MIN_BYTES = int(os.getenv("IMAGE_QUALITY_MIN_BYTES", "30000"))
IMAGE_MIN_DIMENSION = int(os.getenv("IMAGE_MIN_DIMENSION", "512"))
MAX_REGENERATION_ATTEMPTS = int(os.getenv("MAX_REGENERATION_ATTEMPTS", "3"))
QUALITY_SCORE_THRESHOLD = int(os.getenv("QUALITY_SCORE_THRESHOLD", "60"))


# ═══════════════════════════════════════════════════════════
# 💾 DATABASE
# ═══════════════════════════════════════════════════════════
DB_PATH = os.getenv("DB_PATH", "divine_poster.db")
DB_BACKUP_ENABLED = os.getenv("DB_BACKUP_ENABLED", "true").lower() == "true"


# ═══════════════════════════════════════════════════════════
# 📊 ANALYTICS
# ═══════════════════════════════════════════════════════════
ANALYTICS_ENABLED = os.getenv("ANALYTICS_ENABLED", "true").lower() == "true"
ANALYTICS_FETCH_DELAY_MINUTES = int(os.getenv("ANALYTICS_FETCH_DELAY_MINUTES", "60"))
INSIGHTS_MIN_POSTS = int(os.getenv("INSIGHTS_MIN_POSTS", "3"))


# ═══════════════════════════════════════════════════════════
# 📋 LOGGING
# ═══════════════════════════════════════════════════════════
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
LOG_DIR = os.getenv("LOG_DIR", "logs")
LOG_KEEP_DAYS = int(os.getenv("LOG_KEEP_DAYS", "30"))


# ═══════════════════════════════════════════════════════════
# 🚀 PERFORMANCE
# ═══════════════════════════════════════════════════════════
ENABLE_CACHING = os.getenv("ENABLE_CACHING", "true").lower() == "true"
PARALLEL_UPLOAD = os.getenv("PARALLEL_UPLOAD", "false").lower() == "true"


# ═══════════════════════════════════════════════════════════
# 🆕 V2 - GOOGLE CLOUD TEXT-TO-SPEECH (Reels Voice)
# ═══════════════════════════════════════════════════════════
TTS_ENABLED = os.getenv("TTS_ENABLED", "true").lower() == "true"
TTS_LANGUAGE = os.getenv("TTS_LANGUAGE", "hi-IN")

# Hindi Neural2 voices (best quality)
TTS_VOICE_MALE = os.getenv("TTS_VOICE_MALE", "hi-IN-Neural2-B")
TTS_VOICE_FEMALE = os.getenv("TTS_VOICE_FEMALE", "hi-IN-Neural2-A")

# Speech parameters
TTS_SPEAKING_RATE = float(os.getenv("TTS_SPEAKING_RATE", "0.95"))
TTS_PITCH = float(os.getenv("TTS_PITCH", "0.0"))
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
REEL_DURATION_MIN = int(os.getenv("REEL_DURATION_MIN", "60"))
REEL_DURATION_MAX = int(os.getenv("REEL_DURATION_MAX", "90"))

# Video specs (9:16 portrait for all platforms)
REEL_FPS = int(os.getenv("REEL_FPS", "30"))
REEL_WIDTH = 1080
REEL_HEIGHT = 1920
REEL_ASPECT_RATIO = "9:16"

# Story parameters (Hindi narration)
REEL_STORY_MIN_WORDS = int(os.getenv("REEL_STORY_MIN_WORDS", "150"))
REEL_STORY_MAX_WORDS = int(os.getenv("REEL_STORY_MAX_WORDS", "180"))
REEL_NUM_SCENES = int(os.getenv("REEL_NUM_SCENES", "6"))

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
REEL_POSTING_HOUR = int(os.getenv("REEL_POSTING_HOUR", "13"))


# ═══════════════════════════════════════════════════════════
# 🆕 V2 - YOUTUBE SHORTS
# ═══════════════════════════════════════════════════════════
YOUTUBE_ENABLED = os.getenv("YOUTUBE_ENABLED", "true").lower() == "true"
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
YOUTUBE_CATEGORY_ID = "22"  # People & Blogs
YOUTUBE_PRIVACY_STATUS = os.getenv("YOUTUBE_PRIVACY_STATUS", "public")
YOUTUBE_MADE_FOR_KIDS = False
YOUTUBE_UPLOAD_MAX_RETRIES = 3


# ═══════════════════════════════════════════════════════════
# 🎛️ APP MODE — FREE / PRO / AUTO
#
#   free  → ₹0 cost. Images via FREE providers (Pollinations) only.
#           No paid Vertex AI Imagen. Video/reels disabled →
#           degrades to generating a picture instead.
#
#   pro   → Paid mode. Premium Vertex AI Imagen images + video reels
#           (TTS, music, subtitles). Full quality.
#
#   auto  → Default. Start in PRO, but if the daily/monthly budget is
#           exhausted (or paid generation fails) → auto-degrade to FREE
#           so at least a picture always gets made.
#
# CLI se switch करो:  python main.py mode free|pro|auto
# .env में set करो:   APP_MODE=free  |  APP_MODE=pro  |  APP_MODE=auto
# ═══════════════════════════════════════════════════════════
APP_MODE = os.getenv("APP_MODE", "free").strip().lower()
if APP_MODE not in ("free", "pro", "auto"):
    APP_MODE = "free"

# Persistent mode override file (CLI `mode` command से update होता है)
MODE_STATE_FILE = os.getenv(
    "MODE_STATE_FILE",
    os.path.join(os.getenv("LOG_DIR", "logs"), "mode_state.json")
)

# FREE mode में video banane ki hard-off flag.
# 🆕 FULLY FREE (₹0) — Default TRUE: video/reels band → TTS paisa na lage.
# Paisa aaye to .env mein FREE_MODE_DISABLES_REELS=false ya GitHub vars se change karo.
FREE_MODE_DISABLES_REELS = os.getenv(
    "FREE_MODE_DISABLES_REELS", "true"
).lower() == "true"

# FREE mode mein video banane allow karo (agar free path available ho).
# 🆕 FULLY FREE (₹0) — Default FALSE: FREE mein video disabled → pic fallback.
FREE_MODE_ALLOWS_VIDEO = os.getenv(
    "FREE_MODE_ALLOWS_VIDEO", "false"
).lower() == "true"

# 🎬 VIDEO FREQUENCY — har N din mein 1 video (default: 2 din)
# Isko .env se badal sakte ho, e.g. VIDEO_EVERY_DAYS=3 → har 3 din mein 1 video.
VIDEO_EVERY_DAYS = int(os.getenv("VIDEO_EVERY_DAYS", "2"))


# ═══════════════════════════════════════════════════════════
# 🎯 FEATURE FLAGS
# ═══════════════════════════════════════════════════════════
FEATURES = {
    # Existing
    "vertex_ai": USE_VERTEX_AI,
    "pollinations_fallback": POLLINATIONS_ENABLED,
    "analytics": ANALYTICS_ENABLED,
    "humanizer": os.getenv("ENABLE_HUMANIZER", "true").lower() == "true",
    "duplicate_check": os.getenv("ENABLE_DUPLICATE_CHECK", "true").lower() == "true",
    "self_learning": os.getenv("ENABLE_SELF_LEARNING", "true").lower() == "true",
    "festival_detection": os.getenv("ENABLE_FESTIVAL_DETECTION", "true").lower() == "true",
    "smart_scheduling": os.getenv("ENABLE_SMART_SCHEDULING", "true").lower() == "true",

    # 🆕 V2
    "tts": TTS_ENABLED,
    "reels": True,
    "youtube": YOUTUBE_ENABLED,
    "video_watermark": True,

    # 🆕 V3 — Mode system
    "app_mode": APP_MODE,
    "free_mode_disables_reels": FREE_MODE_DISABLES_REELS,
    "free_mode_allows_video": FREE_MODE_ALLOWS_VIDEO,
    "video_every_days": VIDEO_EVERY_DAYS,
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

    # App Mode
    print("🎛️  APP MODE")
    print(f"   Mode          : {APP_MODE.upper()}")
    if APP_MODE == "free":
        print(f"   → FREE (₹0): Images via Pollinations only, reels disabled")
    elif APP_MODE == "pro":
        print(f"   → PRO (paid): Premium Imagen + reels enabled")
    else:
        print(f"   → AUTO: PRO, budget खत्म → FREE fallback (pic guaranteed)")

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

    if YOUTUBE_ENABLED and not os.path.exists(YOUTUBE_CLIENT_SECRETS_FILE):
        warnings.append(
            f"⚠️  YouTube client secrets file missing: {YOUTUBE_CLIENT_SECRETS_FILE}. "
            "Run OAuth setup first."
        )

    if YOUTUBE_ENABLED and not os.path.exists(YOUTUBE_TOKEN_FILE):
        warnings.append(
            f"⚠️  YouTube token file missing: {YOUTUBE_TOKEN_FILE}. "
            "YouTube uploads will fail. GitHub Actions में "
            "YOUTUBE_TOKEN_JSON secret set करें (python -m posting.youtube "
            "से token बनाएं)."
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
            "privacy": YOUTUBE_PRIVACY_STATUS
        },
        "features": FEATURES,
        "app_mode": {
            "configured": APP_MODE,
            "free_disables_reels": FREE_MODE_DISABLES_REELS,
            "free_allows_video": FREE_MODE_ALLOWS_VIDEO,
            "video_every_days": VIDEO_EVERY_DAYS,
            "state_file": MODE_STATE_FILE
        }
    }


# ═══════════════════════════════════════════════════════════
# CLI TESTING
# ═══════════════════════════════════════════════════════════

if __name__ == "__main__":
    validate()

    print("\n📄 CONFIG DICT:")
    import json
    print(json.dumps(get_config_summary(), indent=2))
