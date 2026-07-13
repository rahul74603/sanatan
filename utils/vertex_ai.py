"""
Vertex AI Imagen Helper - Production Grade
Features:
- Auto-fallback between models (Vertex AI SDK → REST API → Gemini → Pollinations FREE)
- Per-day and per-month cost tracking
- Persistent usage stats (JSON file)
- Budget alerts
- Smart error handling
- Session-level access caching (skip known-failing providers instantly)
- Model auto-selection based on availability
- Retry with different models
- Detailed cost analytics
"""
import time
import json
import base64
import requests
import urllib.parse
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple

from config.settings import (
    PROJECT_ID,
    LOCATION,
    VERTEX_MODEL,
    VERTEX_MAX_RETRIES,
    VERTEX_RETRY_DELAY,
    VERTEX_ASPECT_RATIO,
    VERTEX_DAILY_BUDGET,
    VERTEX_MONTHLY_BUDGET
)
from utils.logger import get_logger

logger = get_logger("vertex_ai")


# ============================================================
# GRACEFUL IMPORTS
# ============================================================

try:
    import vertexai
    from vertexai.preview.vision_models import ImageGenerationModel
    VERTEX_AVAILABLE = True
    logger.info("✅ Vertex AI library loaded")
except ImportError:
    logger.warning("⚠️ vertexai not installed. Run: pip install google-cloud-aiplatform")
    VERTEX_AVAILABLE = False


# ============================================================
# QUICK-START CONFIG
# Set True to skip providers confirmed not working on your account.
# This saves time — no more waiting 16s on known-failing stages.
# ============================================================

SKIP_VERTEX_SDK  = True   # ← 403 confirmed on this account, skip immediately
SKIP_VERTEX_REST = True   # ← 404 confirmed on this account, skip immediately
SKIP_GEMINI      = False  # ← Keep trying (needs GEMINI_API_KEY in .env)


# ============================================================
# SESSION-LEVEL ACCESS CACHE
# ============================================================

_vertex_initialized    = False
_VERTEX_ACCESS_CHECKED = False
_VERTEX_HAS_ACCESS     = False
_REST_ACCESS_CHECKED   = False
_REST_HAS_ACCESS       = False


# ============================================================
# MODEL CONFIGURATION
# ============================================================

VERTEX_MODELS = {
    "imagegeneration@006": {
        "quality":     "high",
        "cost_inr":    1.50,
        "speed":       "medium",
        "description": "Stable Imagen 2 ⭐",
        "priority":    1,
        "provider":    "vertex"
    },
    "imagegeneration@005": {
        "quality":     "high",
        "cost_inr":    1.50,
        "speed":       "medium",
        "description": "Imagen 2 v005 (backup)",
        "priority":    2,
        "provider":    "vertex"
    },
    "imagen-4.0-generate-preview-06-06": {
        "quality":     "premium",
        "cost_inr":    2.50,
        "speed":       "medium",
        "description": "Best quality, latest model",
        "priority":    3,
        "provider":    "vertex"
    },
    "imagen-3.0-generate-002": {
        "quality":     "high",
        "cost_inr":    1.50,
        "speed":       "medium",
        "description": "Balanced quality/cost ⭐",
        "priority":    4,
        "provider":    "vertex"
    },
    "imagen-3.0-fast-generate-001": {
        "quality":     "good",
        "cost_inr":    1.00,
        "speed":       "fast",
        "description": "Fastest generation",
        "priority":    5,
        "provider":    "vertex"
    }
}

ASPECT_RATIOS = {
    "square":    "1:1",
    "portrait":  "3:4",
    "landscape": "4:3",
    "story":     "9:16",
    "wide":      "16:9"
}

POLLINATIONS_MODELS = [
    "flux",
    "flux-realism",
    "flux-anime",
    "turbo",
]


# ============================================================
# COST TRACKING (Persistent JSON)
# ============================================================

STATS_FILE = Path("logs") / "vertex_usage.json"


def _load_stats() -> dict:
    """Load persistent usage stats from JSON file"""
    try:
        if STATS_FILE.exists():
            with open(STATS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        logger.warning(f"Could not load stats: {e}")

    return {
        "all_time": {
            "total_images":   0,
            "total_cost_inr": 0.0,
            "successful":     0,
            "failed":         0
        },
        "daily":         {},
        "monthly":       {},
        "session_start": datetime.now().isoformat()
    }


def _save_stats(stats: dict):
    """Save usage stats to JSON file"""
    try:
        STATS_FILE.parent.mkdir(exist_ok=True)
        with open(STATS_FILE, 'w', encoding='utf-8') as f:
            json.dump(stats, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.warning(f"Could not save stats: {e}")


def track_usage(cost_inr: float, success: bool = True, model: str = ""):
    """Track a generation attempt in persistent storage"""
    stats      = _load_stats()
    today      = datetime.now().strftime("%Y-%m-%d")
    this_month = datetime.now().strftime("%Y-%m")

    if today not in stats["daily"]:
        stats["daily"][today] = {"images": 0, "cost": 0.0, "failed": 0}
    if this_month not in stats["monthly"]:
        stats["monthly"][this_month] = {"images": 0, "cost": 0.0, "failed": 0}

    stats["all_time"]["total_images"] += 1

    if success:
        stats["all_time"]["successful"]          += 1
        stats["all_time"]["total_cost_inr"]      += cost_inr
        stats["daily"][today]["images"]           += 1
        stats["daily"][today]["cost"]             += cost_inr
        stats["monthly"][this_month]["images"]    += 1
        stats["monthly"][this_month]["cost"]      += cost_inr
    else:
        stats["all_time"]["failed"]               += 1
        stats["daily"][today]["failed"]           += 1
        stats["monthly"][this_month]["failed"]    += 1

    _save_stats(stats)
    _check_budget_alerts(stats)


def _check_budget_alerts(stats: dict):
    """Warn if approaching or exceeding budget limits"""
    today      = datetime.now().strftime("%Y-%m-%d")
    this_month = datetime.now().strftime("%Y-%m")

    daily_cost   = stats["daily"].get(today, {}).get("cost", 0)
    monthly_cost = stats["monthly"].get(this_month, {}).get("cost", 0)

    if daily_cost >= VERTEX_DAILY_BUDGET:
        logger.warning(f"🚨 DAILY BUDGET EXCEEDED: ₹{daily_cost:.2f} / ₹{VERTEX_DAILY_BUDGET}")
    elif daily_cost >= VERTEX_DAILY_BUDGET * 0.8:
        logger.warning(f"⚠️  Daily budget 80% used: ₹{daily_cost:.2f} / ₹{VERTEX_DAILY_BUDGET}")

    if monthly_cost >= VERTEX_MONTHLY_BUDGET:
        logger.warning(f"🚨 MONTHLY BUDGET EXCEEDED: ₹{monthly_cost:.2f} / ₹{VERTEX_MONTHLY_BUDGET}")
    elif monthly_cost >= VERTEX_MONTHLY_BUDGET * 0.8:
        logger.warning(f"⚠️  Monthly budget 80% used: ₹{monthly_cost:.2f} / ₹{VERTEX_MONTHLY_BUDGET}")


def get_stats() -> dict:
    """Return current usage stats dict"""
    return _load_stats()


def log_session_stats():
    """Print nicely formatted usage stats to logger"""
    stats      = _load_stats()
    today      = datetime.now().strftime("%Y-%m-%d")
    this_month = datetime.now().strftime("%Y-%m")

    all_time    = stats["all_time"]
    today_stats = stats["daily"].get(today,       {"images": 0, "cost": 0.0, "failed": 0})
    month_stats = stats["monthly"].get(this_month, {"images": 0, "cost": 0.0, "failed": 0})

    logger.info("┌─────────────────────────────────────────┐")
    logger.info("│      💰 VERTEX AI USAGE STATS           │")
    logger.info("├─────────────────────────────────────────┤")
    logger.info(f"│ 📅 TODAY ({today})")
    logger.info(f"│    Images    : {today_stats['images']}")
    logger.info(f"│    Cost      : ₹{today_stats['cost']:.2f} / ₹{VERTEX_DAILY_BUDGET}")
    logger.info(f"│    Failed    : {today_stats['failed']}")
    logger.info("├─────────────────────────────────────────┤")
    logger.info(f"│ 📆 THIS MONTH ({this_month})")
    logger.info(f"│    Images    : {month_stats['images']}")
    logger.info(f"│    Cost      : ₹{month_stats['cost']:.2f} / ₹{VERTEX_MONTHLY_BUDGET}")
    logger.info(f"│    Failed    : {month_stats['failed']}")
    logger.info("├─────────────────────────────────────────┤")
    logger.info("│ 🏆 ALL TIME")
    logger.info(f"│    Images    : {all_time['total_images']}")
    logger.info(f"│    Cost      : ₹{all_time['total_cost_inr']:.2f}")
    logger.info(f"│    Success   : {all_time['successful']}")
    logger.info(f"│    Failed    : {all_time['failed']}")

    if all_time["total_images"] > 0:
        success_rate = (all_time["successful"] / all_time["total_images"]) * 100
        avg_cost     = all_time["total_cost_inr"] / max(all_time["successful"], 1)
        logger.info(f"│    Success % : {success_rate:.1f}%")
        logger.info(f"│    Avg cost  : ₹{avg_cost:.2f}/image")

    logger.info("└─────────────────────────────────────────┘")


# ============================================================
# BUDGET CHECK
# ============================================================

def _can_afford_generation(model_name: str) -> Tuple[bool, str]:
    """Return (True, 'OK') or (False, reason) based on remaining budget"""
    cost       = VERTEX_MODELS.get(model_name, {}).get("cost_inr", 2.0)
    stats      = _load_stats()
    today      = datetime.now().strftime("%Y-%m-%d")
    this_month = datetime.now().strftime("%Y-%m")

    daily_cost   = stats["daily"].get(today, {}).get("cost", 0)
    monthly_cost = stats["monthly"].get(this_month, {}).get("cost", 0)

    if daily_cost + cost > VERTEX_DAILY_BUDGET:
        return False, (
            f"Daily budget exceeded "
            f"(₹{daily_cost:.2f} + ₹{cost} > ₹{VERTEX_DAILY_BUDGET})"
        )
    if monthly_cost + cost > VERTEX_MONTHLY_BUDGET:
        return False, (
            f"Monthly budget exceeded "
            f"(₹{monthly_cost:.2f} + ₹{cost} > ₹{VERTEX_MONTHLY_BUDGET})"
        )
    return True, "OK"


# ============================================================
# INITIALIZATION
# ============================================================

def _init_vertex():
    """Initialize Vertex AI SDK once per session"""
    global _vertex_initialized

    if _vertex_initialized:
        return True

    if not VERTEX_AVAILABLE:
        raise Exception("vertexai library not installed")

    project_id = PROJECT_ID or "strategic-well-501911-f3"
    location   = LOCATION   or "us-central1"

    if not project_id:
        raise Exception("PROJECT_ID not set in config/settings.py or .env")

    vertexai.init(project=project_id, location=location)
    _vertex_initialized = True

    logger.info("✅ Vertex AI initialized")
    logger.info(f"   Project : {project_id}")
    logger.info(f"   Location: {location}")
    return True


# ============================================================
# ACCESS CHECKERS (cached per session)
# ============================================================

def _check_vertex_sdk_access() -> bool:
    """Test Vertex SDK access once, cache result for session"""
    global _VERTEX_ACCESS_CHECKED, _VERTEX_HAS_ACCESS

    if _VERTEX_ACCESS_CHECKED:
        return _VERTEX_HAS_ACCESS

    _VERTEX_ACCESS_CHECKED = True

    if not VERTEX_AVAILABLE:
        _VERTEX_HAS_ACCESS = False
        return False

    try:
        _init_vertex()
        test_model = ImageGenerationModel.from_pretrained("imagen-3.0-fast-generate-001")
        resp = test_model.generate_images(
            prompt="red circle",
            number_of_images=1,
            aspect_ratio="1:1"
        )
        _VERTEX_HAS_ACCESS = bool(resp.images)
        if _VERTEX_HAS_ACCESS:
            logger.info("✅ Vertex AI SDK access confirmed!")
        else:
            logger.warning("⚠️  Vertex SDK returned no images on test call")

    except Exception as e:
        if "403" in str(e):
            logger.warning(
                "⚠️  Vertex SDK: 403 Imagen access denied. "
                "Skipping SDK for rest of session."
            )
        else:
            logger.warning(f"⚠️  Vertex SDK test failed: {e}")
        _VERTEX_HAS_ACCESS = False

    return _VERTEX_HAS_ACCESS


def _check_vertex_rest_access() -> bool:
    """Test Vertex REST credentials once, cache result"""
    global _REST_ACCESS_CHECKED, _REST_HAS_ACCESS

    if _REST_ACCESS_CHECKED:
        return _REST_HAS_ACCESS

    _REST_ACCESS_CHECKED = True

    try:
        import google.auth
        import google.auth.transport.requests

        credentials, _ = google.auth.default(
            scopes=["https://www.googleapis.com/auth/cloud-platform"]
        )
        auth_req = google.auth.transport.requests.Request()
        credentials.refresh(auth_req)
        _REST_HAS_ACCESS = bool(credentials.token)
        if _REST_HAS_ACCESS:
            logger.info("✅ Vertex REST API credentials available")
    except Exception as e:
        logger.warning(f"⚠️  Vertex REST credentials check failed: {e}")
        _REST_HAS_ACCESS = False

    return _REST_HAS_ACCESS


# ============================================================
# PROVIDER 1 — VERTEX AI SDK
# ============================================================

def _generate_vertex_sdk(
    prompt:          str,
    negative_prompt: str,
    aspect_ratio:    str,
    model_name:      str
) -> Tuple[bytes, dict]:
    """Generate image via Vertex AI Imagen Python SDK"""

    model_info = VERTEX_MODELS.get(model_name, {})
    logger.info(f"🎨 Model: {model_name} ({model_info.get('quality', '?')} quality)")
    logger.info(f"💰 Est. cost: ₹{model_info.get('cost_inr', 2.0)}")

    start_time = time.time()
    model      = ImageGenerationModel.from_pretrained(model_name)

    params = {
        "prompt":              prompt,
        "number_of_images":    1,
        "aspect_ratio":        aspect_ratio,
        "safety_filter_level": "block_only_high",
        "person_generation":   "allow_adult",
    }
    if negative_prompt:
        params["negative_prompt"] = negative_prompt

    response = model.generate_images(**params)

    if not response.images:
        raise Exception("No images returned by Vertex AI SDK")

    image_bytes = response.images[0]._image_bytes

    if not image_bytes or len(image_bytes) < 10_000:
        raise Exception(f"Invalid image bytes: {len(image_bytes) if image_bytes else 0}")

    elapsed = round(time.time() - start_time, 2)
    cost    = model_info.get("cost_inr", 2.0)

    metadata = {
        "provider":           "vertex_ai_sdk",
        "model":              model_name,
        "model_quality":      model_info.get("quality", "unknown"),
        "aspect_ratio":       aspect_ratio,
        "size_bytes":         len(image_bytes),
        "generation_time":    elapsed,
        "estimated_cost_inr": cost,
        "prompt_length":      len(prompt),
        "is_free":            False,
        "fallback_used":      False,
        "fallback_position":  1
    }

    logger.info(f"✅ SDK generated in {elapsed}s | {len(image_bytes):,} bytes")
    return image_bytes, metadata


# ============================================================
# PROVIDER 2 — VERTEX AI REST API
# ============================================================

def _generate_vertex_rest(
    prompt:       str,
    aspect_ratio: str,
    model_name:   str = "imagen-3.0-fast-generate-001"
) -> Tuple[bytes, dict]:
    """Generate via Vertex AI REST API using google-auth (no gcloud subprocess)"""
    logger.info(f"🌐 Trying Vertex REST API: {model_name}")

    try:
        import google.auth
        import google.auth.transport.requests

        credentials, _ = google.auth.default(
            scopes=["https://www.googleapis.com/auth/cloud-platform"]
        )
        auth_req = google.auth.transport.requests.Request()
        credentials.refresh(auth_req)
        token = credentials.token

        if not token:
            raise Exception("Empty token returned by google.auth")

    except Exception as e:
        raise Exception(f"Auth failed for REST API: {e}")

    project_id = PROJECT_ID or "strategic-well-501911-f3"
    location   = LOCATION   or "us-central1"

    url = (
        f"https://{location}-aiplatform.googleapis.com/v1/"
        f"projects/{project_id}/locations/{location}/"
        f"publishers/google/models/{model_name}:predict"
    )

    headers = {
        "Authorization":       f"Bearer {token}",
        "Content-Type":        "application/json",
        "x-goog-user-project": project_id
    }

    payload = {
        "instances": [{"prompt": prompt}],
        "parameters": {
            "sampleCount":       1,
            "aspectRatio":       aspect_ratio,
            "safetyFilterLevel": "block_only_high",
            "personGeneration":  "allow_adult"
        }
    }

    start_time = time.time()
    response   = requests.post(url, json=payload, headers=headers, timeout=120)
    elapsed    = round(time.time() - start_time, 2)

    if response.status_code != 200:
        raise Exception(f"REST API HTTP {response.status_code}: {response.text[:300]}")

    data        = response.json()
    predictions = data.get("predictions", [])

    if not predictions:
        raise Exception("No predictions in Vertex REST response")

    b64_image = predictions[0].get("bytesBase64Encoded", "")
    if not b64_image:
        raise Exception("No bytesBase64Encoded in prediction")

    image_bytes = base64.b64decode(b64_image)

    if len(image_bytes) < 10_000:
        raise Exception(f"Image too small: {len(image_bytes)} bytes")

    metadata = {
        "provider":           "vertex_ai_rest",
        "model":              model_name,
        "model_quality":      "good",
        "aspect_ratio":       aspect_ratio,
        "size_bytes":         len(image_bytes),
        "generation_time":    elapsed,
        "estimated_cost_inr": 1.0,
        "prompt_length":      len(prompt),
        "is_free":            False,
        "fallback_used":      True,
        "fallback_position":  2
    }

    logger.info(f"✅ REST generated in {elapsed}s | {len(image_bytes):,} bytes")
    return image_bytes, metadata


# ============================================================
# PROVIDER 3 — GEMINI API
# ============================================================

def _extract_gemini_image(data: dict) -> bytes:
    """Extract inline image bytes from a Gemini generateContent response"""
    for candidate in data.get("candidates", []):
        for part in candidate.get("content", {}).get("parts", []):
            if "inlineData" in part:
                b64 = part["inlineData"].get("data", "")
                if b64:
                    return base64.b64decode(b64)
    raise Exception("No inlineData image found in Gemini response")


def _generate_gemini_imagen(
    prompt:       str,
    aspect_ratio: str = "1:1"
) -> Tuple[bytes, dict]:
    """Generate via Gemini API with dynamic model discovery"""
    import os

    api_key = (
        os.environ.get("GEMINI_API_KEY") or
        os.environ.get("GOOGLE_API_KEY")
    )

    if not api_key:
        raise Exception(
            "No GEMINI_API_KEY found. Add GEMINI_API_KEY=your_key to .env"
        )

    logger.info("💎 Trying Gemini API...")

    BASE = "https://generativelanguage.googleapis.com"

    # ── Step 1: Discover available models dynamically ─────────
    image_models = []
    try:
        list_resp = requests.get(
            f"{BASE}/v1beta/models?key={api_key}",
            timeout=10
        )
        if list_resp.status_code == 200:
            all_models = [
                m["name"].replace("models/", "")
                for m in list_resp.json().get("models", [])
            ]
            image_models = [
                m for m in all_models
                if any(x in m.lower() for x in ["imagen", "flash", "gemini-2"])
            ]
            logger.info(f"   Discovered image-capable models: {image_models[:6]}")
    except Exception as e:
        logger.warning(f"   Model discovery failed: {e}")

    # ── Step 2: Build endpoint list ───────────────────────────
    endpoints = []

    # Add dynamically discovered Imagen models first
    for m in image_models:
        if "imagen" in m.lower():
            endpoints.append({
                "name":             m,
                "url":              f"{BASE}/v1beta/models/{m}:predict?key={api_key}",
                "payload": {
                    "instances":  [{"prompt": prompt}],
                    "parameters": {"sampleCount": 1, "aspectRatio": aspect_ratio}
                },
                "is_gemini_format": False
            })

    # Static fallbacks
    endpoints += [
        {
            "name": "gemini-2.0-flash-exp",
            "url":  f"{BASE}/v1beta/models/gemini-2.0-flash-exp:generateContent?key={api_key}",
            "payload": {
                "contents": [{"parts": [{"text": f"Generate an image: {prompt}"}]}],
                "generationConfig": {"responseModalities": ["TEXT", "IMAGE"]}
            },
            "is_gemini_format": True
        },
        {
            "name": "gemini-2.0-flash",
            "url":  f"{BASE}/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}",
            "payload": {
                "contents": [{"parts": [{"text": f"Generate an image of: {prompt}"}]}],
                "generationConfig": {"responseModalities": ["TEXT", "IMAGE"]}
            },
            "is_gemini_format": True
        },
        {
            "name": "imagen-3.0-generate-002-v1",
            "url":  f"{BASE}/v1/models/imagen-3.0-generate-002:predict?key={api_key}",
            "payload": {
                "instances":  [{"prompt": prompt}],
                "parameters": {"sampleCount": 1, "aspectRatio": aspect_ratio}
            },
            "is_gemini_format": False
        },
    ]

    # Remove duplicates (keep order)
    seen = set()
    unique_endpoints = []
    for ep in endpoints:
        if ep["name"] not in seen:
            seen.add(ep["name"])
            unique_endpoints.append(ep)
    endpoints = unique_endpoints

    # ── Step 3: Try each endpoint ─────────────────────────────
    last_error = None
    for ep in endpoints:
        try:
            logger.info(f"   Trying: {ep['name']}")
            start_time = time.time()
            resp       = requests.post(ep["url"], json=ep["payload"], timeout=60)
            elapsed    = round(time.time() - start_time, 2)

            if resp.status_code == 404:
                logger.warning(f"   ❌ {ep['name']}: Not found (404)")
                last_error = "404"
                continue
            if resp.status_code == 403:
                logger.warning(f"   ❌ {ep['name']}: Access denied (403)")
                last_error = "403"
                continue
            if resp.status_code != 200:
                logger.warning(
                    f"   ❌ {ep['name']}: HTTP {resp.status_code}: "
                    f"{resp.text[:100]}"
                )
                last_error = f"HTTP {resp.status_code}"
                continue

            data = resp.json()

            if ep["is_gemini_format"]:
                image_bytes = _extract_gemini_image(data)
            else:
                predictions = data.get("predictions", [])
                if not predictions:
                    logger.warning(f"   ❌ {ep['name']}: No predictions")
                    last_error = "No predictions"
                    continue
                b64 = predictions[0].get("bytesBase64Encoded", "")
                if not b64:
                    logger.warning(f"   ❌ {ep['name']}: No image data")
                    last_error = "No image data"
                    continue
                image_bytes = base64.b64decode(b64)

            if len(image_bytes) < 5_000:
                logger.warning(
                    f"   ❌ {ep['name']}: Too small ({len(image_bytes)} bytes)"
                )
                last_error = "Too small"
                continue

            metadata = {
                "provider":           "gemini_api",
                "model":              ep["name"],
                "model_quality":      "good",
                "aspect_ratio":       aspect_ratio,
                "size_bytes":         len(image_bytes),
                "generation_time":    elapsed,
                "estimated_cost_inr": 0.50,
                "prompt_length":      len(prompt),
                "is_free":            False,
                "fallback_used":      True,
                "fallback_position":  3
            }

            logger.info(
                f"✅ Gemini '{ep['name']}' in {elapsed}s | {len(image_bytes):,} bytes"
            )
            return image_bytes, metadata

        except Exception as e:
            logger.warning(f"   ❌ {ep['name']}: {e}")
            last_error = str(e)
            continue

    raise Exception(f"All Gemini endpoints failed. Last: {last_error}")


# ============================================================
# PROVIDER 4 — POLLINATIONS AI (FREE, No API Key)
# ============================================================

def _generate_pollinations(
    prompt:       str,
    aspect_ratio: str = "1:1"
) -> Tuple[bytes, dict]:
    """
    Generate via Pollinations AI — completely FREE, no API key required.
    Best fallback for spiritual/artistic content.
    """
    logger.info("🌸 Trying Pollinations AI (FREE)...")

    dimension_map = {
        "1:1":  (1024, 1024),
        "3:4":  (768,  1024),
        "4:3":  (1024, 768),
        "9:16": (576,  1024),
        "16:9": (1024, 576),
    }
    width, height = dimension_map.get(aspect_ratio, (1024, 1024))

    last_error = None

    for poll_model in POLLINATIONS_MODELS:
        try:
            encoded_prompt = urllib.parse.quote(prompt[:500])

            url = (
                f"https://image.pollinations.ai/prompt/{encoded_prompt}"
                f"?model={poll_model}"
                f"&width={width}"
                f"&height={height}"
                f"&nologo=true"
                f"&enhance=true"
                f"&seed={int(time.time())}"
            )

            logger.info(f"   Model: {poll_model} ({width}x{height})")

            start_time = time.time()
            response   = requests.get(url, timeout=120, stream=True)
            elapsed    = round(time.time() - start_time, 2)

            if response.status_code != 200:
                raise Exception(f"HTTP {response.status_code}")

            image_bytes = response.content

            if len(image_bytes) < 5_000:
                raise Exception(f"Response too small: {len(image_bytes)} bytes")

            is_jpeg = image_bytes[:3] == b'\xff\xd8\xff'
            is_png  = image_bytes[:8] == b'\x89PNG\r\n\x1a\n'
            if not is_jpeg and not is_png:
                raise Exception("Response is not a valid JPEG or PNG image")

            metadata = {
                "provider":           "pollinations_ai",
                "model":              f"pollinations/{poll_model}",
                "model_quality":      "good",
                "aspect_ratio":       aspect_ratio,
                "size_bytes":         len(image_bytes),
                "generation_time":    elapsed,
                "estimated_cost_inr": 0.0,
                "prompt_length":      len(prompt),
                "is_free":            True,
                "dimensions":         f"{width}x{height}",
                "fallback_used":      True,
                "fallback_position":  4
            }

            logger.info(
                f"✅ Pollinations '{poll_model}' in {elapsed}s | "
                f"{len(image_bytes):,} bytes | FREE"
            )
            return image_bytes, metadata

        except Exception as e:
            logger.warning(f"   ❌ {poll_model}: {e}")
            last_error = e
            time.sleep(2)

    raise Exception(f"All Pollinations models failed. Last: {last_error}")


# ============================================================
# MAIN GENERATION FUNCTION (Multi-Provider Fallback Chain)
# ============================================================

def generate_image_vertex(
    prompt:          str,
    negative_prompt: str           = "",
    aspect_ratio:    Optional[str] = None,
    model_name:      Optional[str] = None,
    enable_fallback: bool          = True,
    allow_free:      bool          = True
) -> Tuple[bytes, dict]:
    """
    Generate an image using a 4-stage fallback chain:

        Stage 1 → Vertex AI SDK   (paid, best quality)
        Stage 2 → Vertex REST API (paid, bypasses SDK issues)
        Stage 3 → Gemini API      (paid, needs GEMINI_API_KEY in .env)
        Stage 4 → Pollinations AI (FREE, always available)

    Control which stages run via the config flags at top of file:
        SKIP_VERTEX_SDK  = True/False
        SKIP_VERTEX_REST = True/False
        SKIP_GEMINI      = True/False

    Args:
        prompt:          Image description
        negative_prompt: What to avoid in the image
        aspect_ratio:    "1:1" | "3:4" | "4:3" | "9:16" | "16:9"
        model_name:      Override the default Vertex model
        enable_fallback: If False, only attempt the primary model
        allow_free:      If False, skip Pollinations (paid-only mode)

    Returns:
        (image_bytes: bytes, metadata: dict)
    """
    if not model_name:
        model_name   = VERTEX_MODEL or "imagen-3.0-fast-generate-001"
    if not aspect_ratio:
        aspect_ratio = VERTEX_ASPECT_RATIO or "1:1"

    logger.info("═══ IMAGE GENERATION (4-stage fallback) ═══")
    logger.info(f"📝 Prompt: {prompt[:80]}...")
    logger.info(f"📐 Aspect: {aspect_ratio}")

    can_afford, reason = _can_afford_generation(model_name)
    if not can_afford:
        logger.warning(f"⚠️  Budget check: {reason}")

    errors = []

    # ══════════════════════════════════════════════════════════
    # STAGE 1 — Vertex AI Python SDK
    # ══════════════════════════════════════════════════════════
    if SKIP_VERTEX_SDK:
        logger.info("⏭️  Stage 1 skipped (SKIP_VERTEX_SDK=True)")

    elif VERTEX_AVAILABLE and _check_vertex_sdk_access():
        vertex_models = list(VERTEX_MODELS.keys())
        if model_name in vertex_models:
            vertex_models.remove(model_name)
            vertex_models.insert(0, model_name)

        for idx, v_model in enumerate(vertex_models, 1):
            try:
                if idx > 1:
                    logger.warning(
                        f"🔄 Vertex SDK fallback {idx}/{len(vertex_models)}: {v_model}"
                    )
                    time.sleep(VERTEX_RETRY_DELAY)

                image_bytes, metadata = _generate_vertex_sdk(
                    prompt=prompt, negative_prompt=negative_prompt,
                    aspect_ratio=aspect_ratio, model_name=v_model
                )
                track_usage(
                    metadata["estimated_cost_inr"], success=True, model=v_model
                )
                return image_bytes, metadata

            except Exception as e:
                err = f"vertex_sdk/{v_model}: {str(e)[:120]}"
                errors.append(err)
                logger.warning(f"❌ {err}")
                track_usage(0, success=False, model=v_model)
                if not enable_fallback:
                    break
    else:
        logger.info("⏭️  Stage 1 skipped — no Imagen access on this project")

    # ══════════════════════════════════════════════════════════
    # STAGE 2 — Vertex AI REST API
    # ══════════════════════════════════════════════════════════
    if SKIP_VERTEX_REST:
        logger.info("⏭️  Stage 2 skipped (SKIP_VERTEX_REST=True)")

    elif _check_vertex_rest_access():
        logger.info("🔄 Stage 2: Vertex REST API...")
        rest_models = [
            "imagen-3.0-fast-generate-001",
            "imagen-3.0-generate-002",
            "imagegeneration@006",
        ]
        for rest_model in rest_models:
            try:
                image_bytes, metadata = _generate_vertex_rest(
                    prompt=prompt, aspect_ratio=aspect_ratio,
                    model_name=rest_model
                )
                track_usage(
                    metadata["estimated_cost_inr"], success=True, model=rest_model
                )
                return image_bytes, metadata
            except Exception as e:
                err = f"vertex_rest/{rest_model}: {str(e)[:120]}"
                errors.append(err)
                logger.warning(f"❌ {err}")
    else:
        logger.info("⏭️  Stage 2 skipped — REST credentials not available")

    # ══════════════════════════════════════════════════════════
    # STAGE 3 — Gemini API
    # ══════════════════════════════════════════════════════════
    if SKIP_GEMINI:
        logger.info("⏭️  Stage 3 skipped (SKIP_GEMINI=True)")
    else:
        logger.info("🔄 Stage 3: Gemini API...")
        try:
            image_bytes, metadata = _generate_gemini_imagen(
                prompt=prompt, aspect_ratio=aspect_ratio
            )
            track_usage(
                metadata["estimated_cost_inr"], success=True, model="gemini_api"
            )
            return image_bytes, metadata
        except Exception as e:
            err = f"gemini_api: {str(e)[:120]}"
            errors.append(err)
            logger.warning(f"❌ {err}")

    # ══════════════════════════════════════════════════════════
    # STAGE 4 — Pollinations AI (FREE, Always Works)
    # ══════════════════════════════════════════════════════════
    if allow_free:
        logger.info("🔄 Stage 4: Pollinations AI (FREE)...")
        try:
            image_bytes, metadata = _generate_pollinations(
                prompt=prompt, aspect_ratio=aspect_ratio
            )
            track_usage(0.0, success=True, model="pollinations")
            logger.info("✅ Image generated via FREE Pollinations AI")
            return image_bytes, metadata
        except Exception as e:
            err = f"pollinations: {str(e)[:120]}"
            errors.append(err)
            logger.warning(f"❌ {err}")
    else:
        logger.info("⏭️  Stage 4 skipped — allow_free=False")

    # ALL FAILED
    error_summary = "\n  • ".join(errors)
    logger.error(f"❌ All image providers failed:\n  • {error_summary}")
    raise Exception(f"All image providers failed:\n  • {error_summary}")


# ============================================================
# UTILITIES
# ============================================================

def get_recommended_model() -> str:
    """Suggest best Vertex model based on remaining daily budget"""
    stats      = _load_stats()
    today      = datetime.now().strftime("%Y-%m-%d")
    daily_cost = stats["daily"].get(today, {}).get("cost", 0)
    remaining  = VERTEX_DAILY_BUDGET - daily_cost

    if remaining > 50:
        return "imagen-4.0-generate-preview-06-06"
    elif remaining > 20:
        return "imagen-3.0-generate-002"
    else:
        return "imagen-3.0-fast-generate-001"


def estimate_images_remaining() -> dict:
    """Return how many images can still be generated within budget"""
    stats      = _load_stats()
    today      = datetime.now().strftime("%Y-%m-%d")
    this_month = datetime.now().strftime("%Y-%m")

    daily_remaining   = (
        VERTEX_DAILY_BUDGET -
        stats["daily"].get(today, {}).get("cost", 0)
    )
    monthly_remaining = (
        VERTEX_MONTHLY_BUDGET -
        stats["monthly"].get(this_month, {}).get("cost", 0)
    )

    return {
        "daily_budget_left_inr":   round(daily_remaining, 2),
        "monthly_budget_left_inr": round(monthly_remaining, 2),
        "images_remaining_today": {
            "premium_2_5rs":  int(daily_remaining / 2.5),
            "balanced_1_5rs": int(daily_remaining / 1.5),
            "fast_1rs":       int(daily_remaining / 1.0)
        },
        "images_remaining_this_month": {
            "premium_2_5rs":  int(monthly_remaining / 2.5),
            "balanced_1_5rs": int(monthly_remaining / 1.5),
            "fast_1rs":       int(monthly_remaining / 1.0)
        }
    }


def reset_failed_count():
    """Reset failed counters (useful after fixing config issues)"""
    stats      = _load_stats()
    today      = datetime.now().strftime("%Y-%m-%d")
    this_month = datetime.now().strftime("%Y-%m")

    if today in stats["daily"]:
        stats["daily"][today]["failed"] = 0
    if this_month in stats["monthly"]:
        stats["monthly"][this_month]["failed"] = 0

    _save_stats(stats)
    logger.info("✅ Failed counters reset")


# ============================================================
# STANDALONE TEST
# ============================================================

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("VERTEX AI IMAGEN - STANDALONE TEST")
    print("=" * 60 + "\n")

    if not VERTEX_AVAILABLE:
        print("⚠️  vertexai not installed — will use fallback providers\n")

    print("📊 Current Usage:")
    log_session_stats()

    remaining = estimate_images_remaining()
    print(f"\n💰 Budget Remaining:")
    print(f"   Today  : ₹{remaining['daily_budget_left_inr']}")
    print(f"   Month  : ₹{remaining['monthly_budget_left_inr']}")

    print(f"\n📷 Images Left Today:")
    print(f"   Premium : {remaining['images_remaining_today']['premium_2_5rs']}")
    print(f"   Balanced: {remaining['images_remaining_today']['balanced_1_5rs']}")
    print(f"   Fast    : {remaining['images_remaining_today']['fast_1rs']}")

    print(f"\n🎯 Recommended Model: {get_recommended_model()}")

    print(f"\n⚙️  Active Config:")
    print(f"   SKIP_VERTEX_SDK  : {SKIP_VERTEX_SDK}")
    print(f"   SKIP_VERTEX_REST : {SKIP_VERTEX_REST}")
    print(f"   SKIP_GEMINI      : {SKIP_GEMINI}")

    print("\n🎨 Testing generation (4-stage fallback chain)...\n")

    test_prompt = (
        "Lord Krishna playing bansuri flute in Vrindavan forest at sunrise, "
        "divine blue skin, peacock feather crown, yellow silk dhoti, "
        "surrounded by cows and lotus flowers, golden ethereal light, "
        "cinematic photography, masterpiece, 8k quality"
    )
    test_negative = "cartoon, anime, low quality, blurry, text, watermark, deformed"

    try:
        image_bytes, metadata = generate_image_vertex(
            prompt          = test_prompt,
            negative_prompt = test_negative,
            aspect_ratio    = "1:1",
            allow_free      = True
        )

        out_file = "test_vertex.jpg"
        with open(out_file, "wb") as f:
            f.write(image_bytes)

        print(f"\n✅ SUCCESS!")
        print(f"   Provider  : {metadata['provider']}")
        print(f"   Model     : {metadata['model']}")
        print(f"   Quality   : {metadata['model_quality']}")
        print(f"   Size      : {metadata['size_bytes']:,} bytes")
        print(f"   Time      : {metadata['generation_time']}s")
        print(
            f"   Cost      : ₹{metadata['estimated_cost_inr']} "
            f"({'FREE' if metadata['is_free'] else 'paid'})"
        )
        print(f"   Stage     : {metadata['fallback_position']}")
        print(f"   Saved to  : {out_file}")

        print("\n📊 Updated Stats:")
        log_session_stats()

    except Exception as e:
        print(f"\n❌ All providers failed: {e}")
        print("\n💡 Troubleshooting:")
        print("   1. Check internet connection")
        print("   2. Add GEMINI_API_KEY=... to .env")
        print("   3. Run: gcloud auth application-default login")