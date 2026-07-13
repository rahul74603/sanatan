"""
Central Configuration - Single Source of Truth
Production-grade config management with validation, categorization, and safe defaults
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
# 🎯 FEATURE FLAGS
# ═══════════════════════════════════════════════════════════
FEATURES = {
    "vertex_ai": USE_VERTEX_AI,
    "pollinations_fallback": POLLINATIONS_ENABLED,
    "analytics": ANALYTICS_ENABLED,
    "humanizer": os.getenv("ENABLE_HUMANIZER", "true").lower() == "true",
    "duplicate_check": os.getenv("ENABLE_DUPLICATE_CHECK", "true").lower() == "true",
    "self_learning": os.getenv("ENABLE_SELF_LEARNING", "true").lower() == "true",
    "festival_detection": os.getenv("ENABLE_FESTIVAL_DETECTION", "true").lower() == "true",
    "smart_scheduling": os.getenv("ENABLE_SMART_SCHEDULING", "true").lower() == "true",
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