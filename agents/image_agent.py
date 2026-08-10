"""
Image Agent - Production-grade image generation
Features:
- PRIMARY: Gemini Imagen 4.0 (best quality, ₹0.50/image)
- FALLBACK: Pollinations AI (FREE, always available)
- Smart model selection based on category
- Quality-first approach with detailed retry logic
- Prompt optimization per category
- Performance tracking
"""
import requests
import random
import time
import hashlib
from urllib.parse import quote
from io import BytesIO
from PIL import Image

from core.memory import AgentMemory
from core.mode_manager import is_free_mode
from utils.gcs_helper import upload_image
from utils.humanizer import humanize_image
from utils.vertex_ai import generate_image_vertex
from utils.logger import get_logger
from utils.watermark import apply_branding

logger = get_logger("image_agent")


# ============================================================
# PROVIDER CONFIG
# ============================================================

# Primary: Gemini Imagen 4.0 via vertex_ai.py fallback chain
USE_GEMINI_PRIMARY = True   # ✅ Set False to use Pollinations as primary

# Pollinations models with characteristics
POLLINATIONS_MODELS = {
    "flux": {
        "best_for": ["portrait", "deity", "detailed", "realistic"],
        "quality":  "high",
        "speed":    "medium",
        "priority": 1
    },
    "flux-realism": {
        "best_for": ["photorealistic", "cinematic", "temple", "nature"],
        "quality":  "very_high",
        "speed":    "slow",
        "priority": 2
    },
    "flux-3d": {
        "best_for": ["fantasy", "cosmic", "divine", "abstract"],
        "quality":  "high",
        "speed":    "medium",
        "priority": 3
    },
    "flux-anime": {
        "best_for": ["stylized", "artistic"],
        "quality":  "medium",
        "speed":    "fast",
        "priority": 4
    },
    "turbo": {
        "best_for": ["quick", "fallback"],
        "quality":  "medium",
        "speed":    "very_fast",
        "priority": 5
    }
}

# Category → Best Pollinations model mapping
CATEGORY_MODEL_PREFERENCE = {
    "krishna":          ["flux",         "flux-realism"],
    "shiva":            ["flux-realism", "flux"],
    "hanuman":          ["flux",         "flux-3d"],
    "ganesha":          ["flux",         "flux-realism"],
    "durga":            ["flux",         "flux-realism"],
    "ram":              ["flux-realism", "flux"],
    "motivational":     ["flux-realism", "flux"],
    "temple":           ["flux-realism", "flux"],
    "spiritual_nature": ["flux-realism", "flux"],
    "festival_moments": ["flux",         "flux-realism"],
    "daily_wisdom":     ["flux",         "flux-realism"],
    "festival":         ["flux",         "flux-realism"],
}

# Image dimensions
IMAGE_DIMENSIONS = {
    "square":   (1024, 1024),
    "portrait": (1024, 1280),
    "story":    (1080, 1920),
}

# Quality thresholds
MIN_FILE_SIZE  = 30_000    # 30 KB minimum
MAX_RETRIES    = 4
BASE_TIMEOUT   = 120       # seconds

# Prompt quality boosters
QUALITY_BOOSTERS = [
    "highly detailed",
    "professional quality",
    "8k resolution",
    "sharp focus",
    "masterpiece",
    "cinematic composition"
]

# Category-specific style enhancers for Gemini Imagen
CATEGORY_STYLE_ENHANCERS = {
    "krishna":      "divine blue skin, golden ornaments, Vrindavan atmosphere, devotional art style",
    "shiva":        "cosmic energy, Himalayan setting, third eye glowing, ash smeared, mystical aura",
    "hanuman":      "powerful physique, saffron clothing, divine strength, Ram devotee, epic pose",
    "ganesha":      "elephant head, modak, lotus throne, auspicious golden light, joyful atmosphere",
    "durga":        "fierce goddess, ten arms, lion mount, divine weapons, warrior power",
    "ram":          "royal bearing, bow and arrow, dharmic warrior, noble expression, forest setting",
    "motivational": "dramatic lighting, epic landscape, human triumph, sunrise glory, powerful composition",
    "temple":       "ancient stone architecture, sacred atmosphere, divine light, intricate carvings",
    "festival":     "celebration lights, colorful decorations, joyful atmosphere, traditional elements",
    "default":      "spiritual atmosphere, divine light, sacred energy, photorealistic"
}


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def _get_style_enhancer(category: str) -> str:
    """Get category-specific style enhancer for prompts"""
    return CATEGORY_STYLE_ENHANCERS.get(
        category, CATEGORY_STYLE_ENHANCERS["default"]
    )


def _select_pollinations_model(category: str, attempt: int = 1) -> str:
    """Smart Pollinations model selection based on category and attempt"""
    preferred = CATEGORY_MODEL_PREFERENCE.get(
        category, ["flux", "flux-realism"]
    )
    if attempt <= len(preferred):
        model = preferred[attempt - 1]
        logger.info(f"🎯 Selected model: {model} (category: {category}, attempt: {attempt})")
        return model
    fallback = random.choice(list(POLLINATIONS_MODELS.keys()))
    logger.info(f"🔄 Fallback model: {fallback}")
    return fallback


def _enhance_prompt(prompt: str, boost_level: int = 1) -> str:
    """Add quality boosters to prompt"""
    if boost_level == 1:
        boosters = random.sample(QUALITY_BOOSTERS, 2)
    elif boost_level == 2:
        boosters = random.sample(QUALITY_BOOSTERS, 4)
    else:
        boosters = QUALITY_BOOSTERS

    enhanced = f"{prompt}, {', '.join(boosters)}"
    enhanced = ", ".join([p.strip() for p in enhanced.split(",") if p.strip()])
    return enhanced


def _build_pollinations_url(
    prompt: str, model: str, seed: int, size: tuple = (1024, 1024)
) -> str:
    """Build Pollinations.ai URL"""
    encoded_prompt = quote(prompt)
    width, height  = size
    return (
        f"https://image.pollinations.ai/prompt/{encoded_prompt}"
        f"?width={width}&height={height}"
        f"&seed={seed}&model={model}"
        f"&nologo=true&enhance=true&nofeed=true"
    )


def _validate_image(image_bytes: bytes) -> tuple:
    """
    Validate image bytes.
    Returns: (is_valid: bool, reason: str)
    """
    size = len(image_bytes)
    if size < MIN_FILE_SIZE:
        return False, f"Too small: {size} bytes"
    try:
        img  = Image.open(BytesIO(image_bytes))
        w, h = img.size
        if w < 512 or h < 512:
            return False, f"Bad dimensions: {w}x{h}"
        if img.mode not in ['RGB', 'RGBA', 'L']:
            return False, f"Bad mode: {img.mode}"
        return True, f"Valid ({size} bytes, {w}x{h})"
    except Exception as e:
        return False, f"Cannot decode: {e}"


def _get_image_hash(image_bytes: bytes) -> str:
    """Get short MD5 hash"""
    return hashlib.md5(image_bytes).hexdigest()[:12]


# ============================================================
# PROVIDER 1 — GEMINI IMAGEN 4.0 (Primary)
# ============================================================

def _generate_with_gemini(
    prompt:   str,
    category: str,
    aspect_ratio: str = "1:1"
) -> tuple:
    """
    Generate via Gemini Imagen 4.0 using vertex_ai.py fallback chain.
    Returns: (image_bytes, metadata)
    """
    logger.info("💎 Primary: Gemini Imagen 4.0")

    # Enhance prompt with category-specific style
    style_hint   = _get_style_enhancer(category)
    full_prompt  = f"{prompt}, {style_hint}"
    full_prompt  = ", ".join([p.strip() for p in full_prompt.split(",") if p.strip()])

    negative = (
        "blurry, low quality, distorted, watermark, text, logo, "
        "ugly, deformed, extra limbs, cartoon, anime"
    )

    logger.info(f"📝 Enhanced prompt: {full_prompt[:100]}...")

    start_time = time.time()

    # Use full fallback chain from vertex_ai.py
    # Stage 1: Gemini Imagen 4.0 (SKIP_VERTEX_SDK/REST=True, so goes straight here)
    # Stage 4: Pollinations (if Gemini fails)
    image_bytes, meta = generate_image_vertex(
        prompt          = full_prompt,
        negative_prompt = negative,
        aspect_ratio    = aspect_ratio,
        allow_free      = True   # Allow Pollinations as last resort
    )

    elapsed = round(time.time() - start_time, 2)

    # Validate
    is_valid, reason = _validate_image(image_bytes)
    if not is_valid:
        raise Exception(f"Invalid image from Gemini: {reason}")

    metadata = {
        "provider":      meta["provider"],
        "model":         meta["model"],
        "model_quality": meta.get("model_quality", "good"),
        "seed":          0,                          # Gemini doesn't use seeds
        "size_bytes":    len(image_bytes),
        "dimensions":    (1024, 1024),
        "generation_time": elapsed,
        "hash":          _get_image_hash(image_bytes),
        "attempt":       1,
        "boost_level":   1,
        "is_free":       meta.get("is_free", False),
        "cost_inr":      meta.get("estimated_cost_inr", 0.0),
        "fallback_stage": meta.get("fallback_position", 3)
    }

    logger.info(
        f"✅ Gemini generated in {elapsed}s | "
        f"{len(image_bytes):,} bytes | "
        f"provider: {meta['provider']}"
    )
    return image_bytes, metadata


# ============================================================
# PROVIDER 2 — POLLINATIONS AI (Fallback / Standalone)
# ============================================================

def _generate_with_pollinations(
    prompt:     str,
    category:   str,
    max_retries: int = MAX_RETRIES
) -> tuple:
    """
    Generate via Pollinations.ai with smart model selection.
    Returns: (image_bytes, metadata)
    """
    logger.info("🌸 Using Pollinations AI")

    errors           = []
    strategies_tried = []

    for attempt in range(1, max_retries + 1):
        logger.info(f"┌─── Attempt {attempt}/{max_retries} ───")

        try:
            model         = _select_pollinations_model(category, attempt)
            boost_level   = min(attempt, 3)
            enhanced      = _enhance_prompt(prompt, boost_level)
            timeout       = BASE_TIMEOUT + (attempt - 1) * 30
            seed          = random.randint(1, 999_999_999)
            url           = _build_pollinations_url(
                enhanced, model, seed, IMAGE_DIMENSIONS["square"]
            )

            logger.info(f"📝 Prompt: {enhanced[:100]}...")
            logger.info(
                f"🌐 Requesting: model={model}, "
                f"seed={seed}, size=1024x1024"
            )
            logger.info(f"⏱️  Timeout: {timeout}s")

            start_time = time.time()
            response   = requests.get(
                url, timeout=timeout,
                headers={"User-Agent": "Mozilla/5.0"}
            )
            elapsed = time.time() - start_time

            if response.status_code != 200:
                raise Exception(f"HTTP {response.status_code}")

            image_bytes = response.content
            is_valid, reason = _validate_image(image_bytes)
            if not is_valid:
                raise Exception(f"Invalid image: {reason}")

            metadata = {
                "provider":        "pollinations_ai",
                "model":           model,
                "model_quality":   POLLINATIONS_MODELS[model]["quality"],
                "seed":            seed,
                "size_bytes":      len(image_bytes),
                "dimensions":      IMAGE_DIMENSIONS["square"],
                "generation_time": round(elapsed, 2),
                "hash":            _get_image_hash(image_bytes),
                "attempt":         attempt,
                "boost_level":     boost_level,
                "is_free":         True,
                "cost_inr":        0.0,
                "strategies_tried": strategies_tried,
                "total_errors":    errors
            }

            logger.info(
                f"✅ Generated in {elapsed:.1f}s | "
                f"{len(image_bytes)} bytes | hash: {metadata['hash']}"
            )
            logger.info(f"└─── ✅ SUCCESS on attempt {attempt} ───")
            return image_bytes, metadata

        except Exception as e:
            err = f"Attempt {attempt}: {str(e)}"
            errors.append(err)
            strategies_tried.append(f"{model}_boost{boost_level}")
            logger.warning(f"└─── ❌ {err}")

            if attempt < max_retries:
                wait = 5 * attempt
                logger.info(f"⏳ Waiting {wait}s before retry...")
                time.sleep(wait)

    raise Exception(
        f"All {max_retries} Pollinations attempts failed. "
        f"Errors: {' | '.join(errors)}"
    )


# ============================================================
# SMART GENERATION  (Primary → Fallback)
# ============================================================

def _generate_image_smart(
    prompt:      str,
    category:    str = "spiritual",
    max_retries: int = MAX_RETRIES
) -> tuple:
    """
    Smart generation:
      1. Gemini Imagen 4.0  (via vertex_ai.py — best quality)
      2. Pollinations AI    (FREE — always available)

      🎛️ MODE AWARE:
      - FREE mode → sirf Pollinations (₹0), paid Vertex kabhi call nahi.
      - PRO / AUTO-with-budget → full paid chain with free fallback.
    """
    # ── 🎛️ FREE MODE: paid Vertex/Imagen bypass ──────────────
    if is_free_mode():
        logger.info(
            "🎛️  FREE MODE active → paid providers skip, sirf "
            "Pollinations (₹0) use hoga."
        )
        return _generate_with_pollinations(
            prompt=prompt, category=category, max_retries=max_retries
        )

    # ── Primary: Gemini Imagen 4.0 ────────────────────────────
    if USE_GEMINI_PRIMARY:
        try:
            logger.info("🚀 Trying primary provider: Gemini Imagen 4.0")
            image_bytes, metadata = _generate_with_gemini(
                prompt=prompt, category=category
            )
            return image_bytes, metadata
        except Exception as e:
            logger.warning(
                f"⚠️ Gemini primary failed: {e}. "
                f"Falling back to Pollinations..."
            )

    # ── Fallback: Pollinations AI ─────────────────────────────
    logger.info("🔄 Using Pollinations AI (fallback)")
    return _generate_with_pollinations(
        prompt=prompt, category=category, max_retries=max_retries
    )


# ============================================================
# UPLOAD WITH RETRY
# ============================================================

def _upload_with_retry(image_bytes: bytes, max_retries: int = 3) -> str:
    """Upload image to GCS with retry"""
    for attempt in range(1, max_retries + 1):
        try:
            logger.info(f"☁️  Upload attempt {attempt}/{max_retries}")
            url = upload_image(image_bytes)
            logger.info("✅ Uploaded successfully")
            return url
        except Exception as e:
            logger.warning(f"Upload attempt {attempt} failed: {e}")
            if attempt < max_retries:
                time.sleep(3)
    raise Exception(f"Upload failed after {max_retries} attempts")


# ============================================================
# MAIN AGENT FUNCTION
# ============================================================

def run(memory: AgentMemory) -> AgentMemory:
    """
    Main image agent execution.

    Flow:
      1. Validate input
      2. Generate (Gemini Imagen 4.0 → Pollinations fallback)
      3. Humanize (anti-AI detection)
      4. Upload to GCS
      5. Store metadata in memory
    """
    logger.info("=" * 50)
    logger.info("=== IMAGE AGENT STARTED ===")
    logger.info("=" * 50)

    start_time = time.time()

    try:
        # ── Validate input ────────────────────────────────────
        if not memory.image_prompt:
            raise Exception("No image prompt in memory")

        logger.info(f"📌 Category: {memory.category}")
        logger.info(f"🎨 Style: {memory.image_style}")
        logger.info(
            f"🔧 Primary provider: "
            f"{'Gemini Imagen 4.0' if USE_GEMINI_PRIMARY else 'Pollinations AI'}"
        )

        # ── Phase 1: Generation ───────────────────────────────
        logger.info("\n--- PHASE 1: GENERATION ---")
        image_bytes, gen_metadata = _generate_image_smart(
            prompt   = memory.image_prompt,
            category = memory.category,
        )

        # ── Phase 2: Humanization ─────────────────────────────
        logger.info("\n--- PHASE 2: HUMANIZATION ---")
        try:
            original_size = len(image_bytes)
            image_bytes   = humanize_image(image_bytes)
            new_size      = len(image_bytes)
            logger.info(f"🎭 Humanized: {original_size} → {new_size} bytes")
        except Exception as e:
            logger.warning(f"Humanization failed (using original): {e}")

                 # ── Phase 2.5: ANTI-CROP BRANDING ─────────────────────
        logger.info("\n--- PHASE 2.5: BRANDING (Anti-Crop) ---")
        try:
            pre_brand   = len(image_bytes)
            image_bytes = apply_branding(image_bytes, strategy="balanced")
            logger.info(
                f"🛡️  Protected: {pre_brand:,} → {len(image_bytes):,} bytes | "
                f"handle: @sanatanii_soch"
            )
        except Exception as e:
            logger.warning(f"Branding failed (using unbranded): {e}")

        # ── Phase 3: Upload ───────────────────────────────────
        logger.info("\n--- PHASE 3: UPLOAD ---")
        image_url = _upload_with_retry(image_bytes)

        # ── Phase 4: Store in memory ──────────────────────────
        memory.image_bytes = image_bytes
        memory.image_url   = image_url

        total_time = round(time.time() - start_time, 2)

        memory.image_metadata = {
            "prompt":            memory.image_prompt,
            "style":             memory.image_style,
            "category":          memory.category,
            "url":               image_url,
            "provider":          gen_metadata.get("provider", "unknown"),
            "model":             gen_metadata.get("model", "unknown"),
            "model_quality":     gen_metadata.get("model_quality", "good"),
            "is_free":           gen_metadata.get("is_free", True),
            "cost_inr":          gen_metadata.get("cost_inr", 0.0),
            "final_size_bytes":  len(image_bytes),
            "total_time_seconds": total_time,
            **gen_metadata
        }

        # ── Success log ───────────────────────────────────────
        logger.info("\n" + "=" * 50)
        logger.info("✅ IMAGE AGENT SUCCESS")
        logger.info("=" * 50)
        logger.info(f"🖼️  URL       : {image_url}")
        logger.info(f"🏭 Provider  : {gen_metadata.get('provider', 'unknown')}")
        logger.info(f"📊 Model     : {gen_metadata.get('model', 'unknown')}")
        logger.info(f"⭐ Quality   : {gen_metadata.get('model_quality', '?')}")
        logger.info(f"💰 Cost      : ₹{gen_metadata.get('cost_inr', 0.0)} "
                    f"({'FREE' if gen_metadata.get('is_free') else 'paid'})")
        logger.info(f"⏱️  Total time: {total_time}s")
        logger.info(f"📏 Size      : {len(image_bytes):,} bytes")
        logger.info(f"#️⃣  Hash      : {gen_metadata.get('hash', 'N/A')}")
        logger.info(f"🔢 Attempts  : {gen_metadata.get('attempt', 1)}")
        logger.info("=" * 50)

    except Exception as e:
        logger.error("\n" + "=" * 50)
        logger.error("❌ IMAGE AGENT FAILED")
        logger.error("=" * 50)
        logger.error(f"Error: {e}")
        logger.error("=" * 50)
        memory.add_error("image_agent", str(e))
        raise

    logger.info("=== IMAGE AGENT DONE ===\n")
    return memory


# ============================================================
# STANDALONE TEST
# ============================================================

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("IMAGE AGENT - STANDALONE TEST")
    print("=" * 60 + "\n")

    print(f"Primary provider: {'Gemini Imagen 4.0' if USE_GEMINI_PRIMARY else 'Pollinations AI'}")

    test_memory = AgentMemory()
    test_memory.image_prompt = (
        "Lord Krishna playing bansuri flute in Vrindavan forest at sunrise, "
        "peacock feather crown, blue skin, yellow silk dhoti, "
        "surrounded by cows and lotus flowers, divine golden light, "
        "cinematic photography, oil painting masterpiece style"
    )
    test_memory.category    = "krishna"
    test_memory.image_style = "cinematic oil painting"

    result = run(test_memory)

    print(f"\n✅ Image URL : {result.image_url}")
    print(f"🏭 Provider  : {result.image_metadata.get('provider')}")
    print(f"📊 Model     : {result.image_metadata.get('model')}")
    print(f"💰 Cost      : ₹{result.image_metadata.get('cost_inr', 0)}")
    print(f"📏 Size      : {result.image_metadata.get('final_size_bytes', 0):,} bytes")