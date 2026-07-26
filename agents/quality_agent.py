"""
Quality Agent - Advanced Image Quality Analyzer
Features:
- Multi-dimensional quality scoring
- Pixel-level analysis (brightness, contrast, sharpness, colors)
- AI-based content validation (Gemini Vision)
- Duplicate detection via hashing
- Corruption detection
- Aesthetic scoring
- Detailed diagnostic report
- Smart regeneration triggers

V2 UPDATE: Added post_type awareness for reel (9:16) aspect ratio
"""
import io
import hashlib
import base64
from typing import Tuple
from PIL import Image, ImageStat, ImageFilter
import numpy as np

from core.memory import AgentMemory
from core.database import get_connection
from config.settings import (
    IMAGE_QUALITY_MIN_BYTES,
    IMAGE_MIN_DIMENSION,
    MAX_REGENERATION_ATTEMPTS,
    QUALITY_SCORE_THRESHOLD,
    GEMINI_API_KEY,
    GEMINI_MODEL
)
from utils.logger import get_logger

# Optional Gemini for AI-based validation
try:
    import google.generativeai as genai
    genai.configure(api_key=GEMINI_API_KEY)
    GEMINI_AVAILABLE = True
except Exception:
    GEMINI_AVAILABLE = False

logger = get_logger("quality_agent")


# ============================================================
# QUALITY THRESHOLDS
# ============================================================

# File size thresholds (bytes)
MIN_FILE_SIZE = IMAGE_QUALITY_MIN_BYTES  # 30KB
IDEAL_FILE_SIZE = 100_000                 # 100KB
MAX_FILE_SIZE = 8_000_000                 # 8MB (Instagram limit)

# Dimension thresholds
MIN_DIMENSION = IMAGE_MIN_DIMENSION       # 512px
IDEAL_DIMENSION = 1024                    # 1024px
MAX_DIMENSION = 4096                      # 4K

# Aspect ratio - Square posts (Instagram feed)
MIN_ASPECT_RATIO = 0.75
MAX_ASPECT_RATIO = 1.35
IDEAL_ASPECT_RATIO = 1.0                  # Square

# 🆕 Aspect ratio - Reels/Story (9:16 portrait)
REEL_MIN_ASPECT_RATIO = 0.50    # Slightly under 9:16 (0.5625)
REEL_MAX_ASPECT_RATIO = 0.65    # Slightly over 9:16
REEL_IDEAL_ASPECT_RATIO = 0.5625  # Exact 9:16

# Brightness (0-255)
MIN_BRIGHTNESS = 30                       # Too dark
MAX_BRIGHTNESS = 240                      # Too bright
IDEAL_BRIGHTNESS_RANGE = (80, 200)

# Contrast (0-127)
MIN_CONTRAST = 15                         # Too flat
IDEAL_CONTRAST = 40

# Color diversity (unique colors)
MIN_UNIQUE_COLORS = 100                   # Monochrome check

# Sharpness (variance of Laplacian)
MIN_SHARPNESS = 100                       # Blurry threshold

# Regeneration settings
MAX_REGENERATIONS = MAX_REGENERATION_ATTEMPTS
PASS_THRESHOLD = QUALITY_SCORE_THRESHOLD  # 60

# Duplicate detection
DUPLICATE_HASH_LENGTH = 16                # Longer = more strict


# ============================================================
# CORE IMAGE ANALYSIS
# ============================================================

def _check_file_size(image_bytes: bytes) -> Tuple[int, list, dict]:
    """Check file size"""
    size = len(image_bytes)
    issues = []
    score_deduction = 0
    metrics = {"file_size": size, "file_size_kb": round(size / 1024, 2)}

    if size < MIN_FILE_SIZE:
        issues.append(f"❌ File too small: {size} bytes (min: {MIN_FILE_SIZE})")
        score_deduction = 40
    elif size > MAX_FILE_SIZE:
        issues.append(f"⚠️ File very large: {size} bytes (may fail upload)")
        score_deduction = 10
    elif size < IDEAL_FILE_SIZE:
        issues.append(f"ℹ️ File below ideal: {size} bytes (ideal: {IDEAL_FILE_SIZE}+)")
        score_deduction = 5

    return score_deduction, issues, metrics


def _check_dimensions(img: Image.Image) -> Tuple[int, list, dict]:
    """Check image dimensions"""
    w, h = img.size
    issues = []
    score_deduction = 0
    metrics = {"width": w, "height": h, "megapixels": round((w * h) / 1_000_000, 2)}

    # Absolute minimum
    if w < MIN_DIMENSION or h < MIN_DIMENSION:
        issues.append(f"❌ Dimensions too small: {w}x{h} (min: {MIN_DIMENSION}px)")
        score_deduction = 30
    elif w < IDEAL_DIMENSION or h < IDEAL_DIMENSION:
        issues.append(f"ℹ️ Below ideal dimensions: {w}x{h} (ideal: {IDEAL_DIMENSION}px+)")
        score_deduction = 5

    # Maximum check
    if w > MAX_DIMENSION or h > MAX_DIMENSION:
        issues.append(f"⚠️ Dimensions very large: {w}x{h} (may compress)")
        score_deduction = 5

    return score_deduction, issues, metrics


def _check_aspect_ratio(img: Image.Image, post_type: str = "image") -> Tuple[int, list, dict]:
    """
    Check aspect ratio for Instagram compatibility

    Args:
        img: PIL Image
        post_type: "image" | "carousel" | "reel"
            - image/carousel → Square range (0.75-1.35)
            - reel → Portrait range (0.50-0.65) for 9:16
    """
    w, h = img.size
    ratio = w / h
    issues = []
    score_deduction = 0
    metrics = {"aspect_ratio": round(ratio, 3), "post_type": post_type}

    # 🆕 Choose ratio range based on post_type
    if post_type == "reel":
        min_ratio = REEL_MIN_ASPECT_RATIO
        max_ratio = REEL_MAX_ASPECT_RATIO
        ideal_ratio = REEL_IDEAL_ASPECT_RATIO
        format_name = "Reel/Story 9:16"
    else:
        min_ratio = MIN_ASPECT_RATIO
        max_ratio = MAX_ASPECT_RATIO
        ideal_ratio = IDEAL_ASPECT_RATIO
        format_name = "Feed square"

    if ratio < min_ratio or ratio > max_ratio:
        issues.append(
            f"❌ Bad aspect ratio: {ratio:.2f} "
            f"({format_name} needs {min_ratio}-{max_ratio})"
        )
        score_deduction = 20
    elif abs(ratio - ideal_ratio) > 0.1:
        issues.append(f"ℹ️ Not ideal ratio: {ratio:.2f} (ideal: {ideal_ratio})")
        score_deduction = 3

    return score_deduction, issues, metrics


def _check_brightness(img: Image.Image) -> Tuple[int, list, dict]:
    """Check image brightness"""
    try:
        # Convert to grayscale for brightness calculation
        gray = img.convert('L')
        stat = ImageStat.Stat(gray)
        brightness = stat.mean[0]

        issues = []
        score_deduction = 0
        metrics = {"brightness": round(brightness, 2)}

        if brightness < MIN_BRIGHTNESS:
            issues.append(f"❌ Too dark: brightness {brightness:.0f}/255")
            score_deduction = 25
        elif brightness > MAX_BRIGHTNESS:
            issues.append(f"❌ Too bright/washed out: {brightness:.0f}/255")
            score_deduction = 25
        elif not (IDEAL_BRIGHTNESS_RANGE[0] <= brightness <= IDEAL_BRIGHTNESS_RANGE[1]):
            issues.append(f"ℹ️ Brightness suboptimal: {brightness:.0f}")
            score_deduction = 5

        return score_deduction, issues, metrics

    except Exception as e:
        return 0, [f"⚠️ Brightness check failed: {e}"], {"brightness": 0}


def _check_contrast(img: Image.Image) -> Tuple[int, list, dict]:
    """Check image contrast"""
    try:
        gray = img.convert('L')
        stat = ImageStat.Stat(gray)
        contrast = stat.stddev[0]

        issues = []
        score_deduction = 0
        metrics = {"contrast": round(contrast, 2)}

        if contrast < MIN_CONTRAST:
            issues.append(f"❌ Low contrast (flat image): {contrast:.0f}")
            score_deduction = 15
        elif contrast < IDEAL_CONTRAST:
            issues.append(f"ℹ️ Contrast below ideal: {contrast:.0f}")
            score_deduction = 3

        return score_deduction, issues, metrics

    except Exception as e:
        return 0, [f"⚠️ Contrast check failed: {e}"], {"contrast": 0}


def _check_color_diversity(img: Image.Image) -> Tuple[int, list, dict]:
    """Check if image has enough color variety (not monochrome/blank)"""
    try:
        # Sample to speed up
        small = img.resize((100, 100))

        # Convert to RGB
        if small.mode != 'RGB':
            small = small.convert('RGB')

        # Count unique colors
        colors = small.getcolors(maxcolors=100000)
        unique_count = len(colors) if colors else 0

        issues = []
        score_deduction = 0
        metrics = {"unique_colors": unique_count}

        if unique_count < MIN_UNIQUE_COLORS:
            issues.append(f"❌ Too monochrome: only {unique_count} unique colors")
            score_deduction = 20

        return score_deduction, issues, metrics

    except Exception as e:
        return 0, [f"⚠️ Color check failed: {e}"], {"unique_colors": 0}


def _check_sharpness(img: Image.Image) -> Tuple[int, list, dict]:
    """
    Detect blur using edge detection
    Higher variance = sharper image
    """
    try:
        # Resize for speed
        small = img.resize((256, 256)).convert('L')

        # Convert to numpy
        arr = np.array(small, dtype=np.float64)

        # Simple Laplacian-like edge detection
        # (approximation without scipy)
        dx = np.abs(np.diff(arr, axis=1)).mean()
        dy = np.abs(np.diff(arr, axis=0)).mean()

        sharpness = (dx + dy) * 50  # Scale up for readability

        issues = []
        score_deduction = 0
        metrics = {"sharpness": round(sharpness, 2)}

        if sharpness < MIN_SHARPNESS:
            issues.append(f"⚠️ Image may be blurry: sharpness {sharpness:.0f}")
            score_deduction = 15

        return score_deduction, issues, metrics

    except Exception as e:
        return 0, [f"⚠️ Sharpness check failed: {e}"], {"sharpness": 0}


def _check_corruption(image_bytes: bytes) -> Tuple[int, list, dict]:
    """Check if image is corrupted"""
    issues = []
    score_deduction = 0
    metrics = {"can_decode": False, "format": "unknown"}

    try:
        img = Image.open(io.BytesIO(image_bytes))

        # Verify integrity
        img.verify()

        # Reopen (verify() closes the file)
        img = Image.open(io.BytesIO(image_bytes))

        metrics["can_decode"] = True
        metrics["format"] = img.format or "unknown"
        metrics["mode"] = img.mode

        # Check mode
        if img.mode not in ['RGB', 'RGBA', 'L']:
            issues.append(f"⚠️ Unusual mode: {img.mode}")
            score_deduction = 10

    except Exception as e:
        issues.append(f"❌ CRITICAL: Corrupted image - {e}")
        score_deduction = 100  # Automatic fail

    return score_deduction, issues, metrics


# ============================================================
# DUPLICATE DETECTION
# ============================================================

def _get_perceptual_hash(image_bytes: bytes) -> str:
    """
    Generate perceptual hash to detect similar images
    Simple pHash-like implementation
    """
    try:
        img = Image.open(io.BytesIO(image_bytes))

        # Convert to small grayscale
        small = img.resize((8, 8)).convert('L')

        # Get pixel data
        pixels = list(small.getdata())

        # Calculate average
        avg = sum(pixels) / len(pixels)

        # Create binary hash
        bits = "".join(["1" if p >= avg else "0" for p in pixels])

        # Convert to hex
        return hex(int(bits, 2))[2:].zfill(16)

    except Exception as e:
        logger.warning(f"Hash generation failed: {e}")
        # Fallback to MD5
        return hashlib.md5(image_bytes).hexdigest()[:16]


def _check_duplicate(image_bytes: bytes) -> Tuple[int, list, dict]:
    """Check if we've generated a similar image before"""
    try:
        current_hash = _get_perceptual_hash(image_bytes)

        conn = get_connection()
        cursor = conn.cursor()

        # Ensure table exists
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS image_hashes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                image_hash TEXT UNIQUE,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Check for exact duplicate
        cursor.execute(
            "SELECT id FROM image_hashes WHERE image_hash = ? LIMIT 1",
            (current_hash,)
        )
        duplicate = cursor.fetchone()

        issues = []
        score_deduction = 0
        metrics = {"hash": current_hash, "is_duplicate": False}

        if duplicate:
            issues.append(f"⚠️ Duplicate image detected (hash: {current_hash})")
            score_deduction = 30
            metrics["is_duplicate"] = True
        else:
            # Store new hash
            cursor.execute(
                "INSERT OR IGNORE INTO image_hashes (image_hash) VALUES (?)",
                (current_hash,)
            )
            conn.commit()

        conn.close()

        return score_deduction, issues, metrics

    except Exception as e:
        logger.warning(f"Duplicate check failed: {e}")
        return 0, [], {"hash": "unknown", "is_duplicate": False}


# ============================================================
# AI-BASED CONTENT VALIDATION (Gemini Vision)
# ============================================================

def _extract_response_text(response) -> str:
    """Safely extract text from Gemini responses (single or multi-part)."""
    try:
        text = response.text.strip()
        if text:
            return text
    except Exception:
        pass

    try:
        candidates = getattr(response, "candidates", []) or []
        texts = []
        for candidate in candidates:
            content = getattr(candidate, "content", None)
            parts = getattr(content, "parts", []) or []
            for part in parts:
                part_text = getattr(part, "text", "")
                if part_text:
                    texts.append(part_text)
        combined = "\n".join(texts).strip()
        if combined:
            return combined
    except Exception:
        pass

    raise Exception("Cannot extract response text")


def _ai_content_check(image_bytes: bytes, expected_topic: str) -> Tuple[int, list, dict]:
    """
    Use Gemini Vision to check if image matches the topic
    Only runs if Gemini is available (optional)
    """
    if not GEMINI_AVAILABLE:
        return 0, [], {"ai_validation": "skipped"}

    try:
        # Convert bytes to PIL image
        img = Image.open(io.BytesIO(image_bytes))

        # Resize for API efficiency
        img.thumbnail((512, 512))

        # Save to bytes
        buf = io.BytesIO()
        img.save(buf, format='JPEG', quality=85)
        buf.seek(0)

        # Prepare for Gemini
        model = genai.GenerativeModel(GEMINI_MODEL)

        prompt = f"""Analyze this image quickly (respond with JSON only):

Expected topic: {expected_topic}

Important: Ignore our intentional brand watermark/handle if visible, especially
"@sanatanii_soch", "sanatanii_soch", "सनातनी सोच", diagonal/corner/center
brand protection text. Count has_text_watermark=true ONLY for unwanted AI text,
garbled letters, random captions, logos, or unrelated watermarks.

Return this exact JSON format:
{{
    "matches_topic": true/false,
    "quality_rating": 1-10,
    "has_text_watermark": true/false,
    "has_distortions": true/false,
    "aesthetic_score": 1-10,
    "brief_description": "1-2 word description"
}}

Only return JSON, no other text."""

        # Send image + prompt
        response = model.generate_content([
            prompt,
            {"mime_type": "image/jpeg", "data": buf.getvalue()}
        ])

        # Parse response
        raw = _extract_response_text(response)

        # Clean/extract JSON
        import re
        raw = re.sub(r'```json\s*|\s*```', '', raw).strip()
        start = raw.find('{')
        end = raw.rfind('}')
        if start != -1 and end != -1 and end > start:
            raw = raw[start:end + 1]

        import json
        result = json.loads(raw)

        # Scoring
        issues = []
        score_deduction = 0
        metrics = {
            "ai_validation": "success",
            "matches_topic": result.get("matches_topic", True),
            "quality_rating": result.get("quality_rating", 5),
            "aesthetic_score": result.get("aesthetic_score", 5),
            "description": result.get("brief_description", "unknown")
        }

        # Check topic match
        if not result.get("matches_topic", True):
            issues.append(f"❌ AI says image doesn't match topic: {expected_topic}")
            score_deduction += 25

        # Check for watermark/text
        if result.get("has_text_watermark"):
            issues.append("❌ AI detected watermark or unwanted text")
            score_deduction += 15

        # Check for distortions
        if result.get("has_distortions"):
            issues.append("⚠️ AI detected distortions in image")
            score_deduction += 10

        # Low quality
        quality = result.get("quality_rating", 5)
        if quality < 5:
            issues.append(f"⚠️ AI quality rating low: {quality}/10")
            score_deduction += 10

        # Low aesthetics
        aesthetic = result.get("aesthetic_score", 5)
        if aesthetic < 5:
            issues.append(f"ℹ️ Aesthetic score low: {aesthetic}/10")
            score_deduction += 5

        return score_deduction, issues, metrics

    except Exception as e:
        logger.warning(f"AI content check failed: {e}")
        return 0, [], {"ai_validation": "failed", "error": str(e)}


# ============================================================
# MAIN QUALITY CHECKER
# ============================================================

def _comprehensive_quality_check(
    image_bytes: bytes,
    topic: str = "",
    post_type: str = "image"
) -> dict:
    """
    Run all quality checks and compile results

    Args:
        image_bytes: Image data
        topic: Topic (for AI validation)
        post_type: "image" | "carousel" | "reel" (for aspect ratio check)
    """
    score = 100
    all_issues = []
    all_metrics = {}

    # ═══════════════════════════════════════════
    # CHECK 1: File size
    # ═══════════════════════════════════════════
    logger.debug("Checking file size...")
    deduction, issues, metrics = _check_file_size(image_bytes)
    score -= deduction
    all_issues.extend(issues)
    all_metrics.update(metrics)

    # ═══════════════════════════════════════════
    # CHECK 2: Corruption (CRITICAL)
    # ═══════════════════════════════════════════
    logger.debug("Checking corruption...")
    deduction, issues, metrics = _check_corruption(image_bytes)
    score -= deduction
    all_issues.extend(issues)
    all_metrics.update(metrics)

    # If corrupted, stop here
    if not metrics.get("can_decode"):
        return {
            "passed": False,
            "score": 0,
            "issues": all_issues,
            "metrics": all_metrics,
            "checks_performed": ["file_size", "corruption"]
        }

    # Open image for further checks
    try:
        img = Image.open(io.BytesIO(image_bytes))
    except Exception as e:
        return {
            "passed": False,
            "score": 0,
            "issues": [f"❌ Cannot open image: {e}"],
            "metrics": all_metrics,
            "checks_performed": ["file_size", "corruption"]
        }

    checks_performed = ["file_size", "corruption"]

    # ═══════════════════════════════════════════
    # CHECK 3: Dimensions
    # ═══════════════════════════════════════════
    logger.debug("Checking dimensions...")
    deduction, issues, metrics = _check_dimensions(img)
    score -= deduction
    all_issues.extend(issues)
    all_metrics.update(metrics)
    checks_performed.append("dimensions")

    # ═══════════════════════════════════════════
    # CHECK 4: Aspect ratio (post_type aware)
    # ═══════════════════════════════════════════
    logger.debug("Checking aspect ratio...")
    deduction, issues, metrics = _check_aspect_ratio(img, post_type=post_type)
    score -= deduction
    all_issues.extend(issues)
    all_metrics.update(metrics)
    checks_performed.append("aspect_ratio")

    # ═══════════════════════════════════════════
    # CHECK 5: Brightness
    # ═══════════════════════════════════════════
    logger.debug("Checking brightness...")
    deduction, issues, metrics = _check_brightness(img)
    score -= deduction
    all_issues.extend(issues)
    all_metrics.update(metrics)
    checks_performed.append("brightness")

    # ═══════════════════════════════════════════
    # CHECK 6: Contrast
    # ═══════════════════════════════════════════
    logger.debug("Checking contrast...")
    deduction, issues, metrics = _check_contrast(img)
    score -= deduction
    all_issues.extend(issues)
    all_metrics.update(metrics)
    checks_performed.append("contrast")

    # ═══════════════════════════════════════════
    # CHECK 7: Color diversity
    # ═══════════════════════════════════════════
    logger.debug("Checking color diversity...")
    deduction, issues, metrics = _check_color_diversity(img)
    score -= deduction
    all_issues.extend(issues)
    all_metrics.update(metrics)
    checks_performed.append("color_diversity")

    # ═══════════════════════════════════════════
    # CHECK 8: Sharpness (blur detection)
    # ═══════════════════════════════════════════
    logger.debug("Checking sharpness...")
    deduction, issues, metrics = _check_sharpness(img)
    score -= deduction
    all_issues.extend(issues)
    all_metrics.update(metrics)
    checks_performed.append("sharpness")

    # ═══════════════════════════════════════════
    # CHECK 9: Duplicate detection
    # ═══════════════════════════════════════════
    logger.debug("Checking duplicates...")
    deduction, issues, metrics = _check_duplicate(image_bytes)
    score -= deduction
    all_issues.extend(issues)
    all_metrics.update(metrics)
    checks_performed.append("duplicate")

    # ═══════════════════════════════════════════
    # CHECK 10: AI content validation (optional)
    # ═══════════════════════════════════════════
    if topic and GEMINI_AVAILABLE:
        logger.debug("Running AI content validation...")
        deduction, issues, metrics = _ai_content_check(image_bytes, topic)
        score -= deduction
        all_issues.extend(issues)
        all_metrics.update(metrics)
        checks_performed.append("ai_validation")

    # ═══════════════════════════════════════════
    # FINAL SCORE
    # ═══════════════════════════════════════════
    score = max(0, min(100, score))
    passed = score >= PASS_THRESHOLD

    return {
        "passed": passed,
        "score": score,
        "issues": all_issues,
        "metrics": all_metrics,
        "checks_performed": checks_performed
    }


# ============================================================
# BEAUTIFUL LOGGING
# ============================================================

def _log_quality_report(result: dict):
    """Beautiful quality report logging"""

    score = result["score"]
    passed = result["passed"]
    metrics = result["metrics"]

    # Score bar visualization
    filled = "█" * (score // 5)
    empty = "░" * (20 - (score // 5))
    bar = f"{filled}{empty}"

    # Grade
    if score >= 90:
        grade = "A+ EXCELLENT 🏆"
    elif score >= 80:
        grade = "A GREAT ⭐"
    elif score >= 70:
        grade = "B GOOD ✅"
    elif score >= 60:
        grade = "C ACCEPTABLE ➡️"
    elif score >= 40:
        grade = "D POOR ⚠️"
    else:
        grade = "F FAILED ❌"

    logger.info("┌─────────────────────────────────────────────┐")
    logger.info("│         IMAGE QUALITY REPORT                │")
    logger.info("├─────────────────────────────────────────────┤")
    logger.info(f"│ Score : [{bar}] {score}/100")
    logger.info(f"│ Grade : {grade}")
    logger.info(f"│ Status: {'✅ PASSED' if passed else '❌ FAILED'}")
    logger.info("├─────────────────────────────────────────────┤")
    logger.info("│ 📊 METRICS:")
    logger.info(f"│   📁 File Size    : {metrics.get('file_size_kb', 0)} KB")
    logger.info(f"│   📐 Dimensions   : {metrics.get('width', 0)}x{metrics.get('height', 0)}")
    logger.info(f"│   📷 Megapixels   : {metrics.get('megapixels', 0)} MP")
    logger.info(f"│   ⚖️  Aspect Ratio : {metrics.get('aspect_ratio', 0)} ({metrics.get('post_type', 'image')})")
    logger.info(f"│   💡 Brightness   : {metrics.get('brightness', 0)}/255")
    logger.info(f"│   🎨 Contrast     : {metrics.get('contrast', 0)}")
    logger.info(f"│   🌈 Unique Colors: {metrics.get('unique_colors', 0)}")
    logger.info(f"│   🔍 Sharpness    : {metrics.get('sharpness', 0)}")
    logger.info(f"│   #️⃣  Hash         : {metrics.get('hash', 'N/A')}")

    if "quality_rating" in metrics:
        logger.info(f"│   🤖 AI Quality   : {metrics.get('quality_rating', 0)}/10")
        logger.info(f"│   🎨 AI Aesthetic : {metrics.get('aesthetic_score', 0)}/10")
        logger.info(f"│   🎯 Topic Match  : {metrics.get('matches_topic', 'N/A')}")

    logger.info("├─────────────────────────────────────────────┤")
    logger.info(f"│ ✅ Checks: {len(result['checks_performed'])}")

    if result["issues"]:
        logger.info("│ ⚠️  ISSUES FOUND:")
        for issue in result["issues"]:
            logger.info(f"│   • {issue}")
    else:
        logger.info("│ ✨ No issues detected!")

    logger.info("└─────────────────────────────────────────────┘")


# ============================================================
# MAIN AGENT FUNCTION
# ============================================================

def run(memory: AgentMemory) -> AgentMemory:
    """
    Comprehensive image quality analysis
    """
    logger.info("=" * 55)
    logger.info("=== QUALITY AGENT STARTED ===")
    logger.info("=" * 55)

    # ═══════════════════════════════════════════
    # VALIDATE INPUT
    # ═══════════════════════════════════════════
    if not memory.image_bytes:
        logger.error("❌ No image bytes in memory")
        memory.quality_passed = False
        memory.quality_score = 0
        memory.quality_issues = ["No image provided"]
        return memory

    logger.info(f"🖼️  Analyzing image ({len(memory.image_bytes)} bytes)")
    logger.info(f"📊 Post type: {memory.post_type}")

    # ═══════════════════════════════════════════
    # RUN COMPREHENSIVE ANALYSIS
    # ═══════════════════════════════════════════
    result = _comprehensive_quality_check(
        image_bytes=memory.image_bytes,
        topic=memory.topic,
        post_type=memory.post_type  # 🆕 Pass post_type for correct aspect ratio check
    )

    # ═══════════════════════════════════════════
    # UPDATE MEMORY
    # ═══════════════════════════════════════════
    memory.quality_passed = result["passed"]
    memory.quality_score = result["score"]
    memory.quality_issues = result["issues"]

    # Store detailed metrics
    memory.image_metadata.update({
        "quality_score": result["score"],
        "quality_metrics": result["metrics"],
        "quality_checks": result["checks_performed"],
        "quality_issues_count": len(result["issues"])
    })

    # ═══════════════════════════════════════════
    # LOG BEAUTIFUL REPORT
    # ═══════════════════════════════════════════
    _log_quality_report(result)

    # ═══════════════════════════════════════════
    # REGENERATION DECISION
    # ═══════════════════════════════════════════
    if not result["passed"]:
        logger.warning(f"\n⚠️ Quality FAILED (Score: {result['score']}/100)")

        if memory.regeneration_count < MAX_REGENERATIONS:
            memory.regeneration_count += 1
            logger.info(
                f"🔄 Regeneration triggered "
                f"({memory.regeneration_count}/{MAX_REGENERATIONS})"
            )
        else:
            logger.error(
                f"❌ Max regenerations reached ({MAX_REGENERATIONS}). "
                "Accepting current image."
            )
            memory.quality_passed = True  # Force accept to prevent infinite loop
    else:
        logger.info(f"\n✅ Quality PASSED (Score: {result['score']}/100)")

    logger.info("=== QUALITY AGENT DONE ===\n")
    return memory


# ============================================================
# PUBLIC UTILITIES
# ============================================================

def quick_check(image_bytes: bytes, post_type: str = "image") -> bool:
    """Quick pass/fail check without full analysis"""
    result = _comprehensive_quality_check(image_bytes, post_type=post_type)
    return result["passed"]


def get_image_score(image_bytes: bytes, topic: str = "", post_type: str = "image") -> int:
    """Get just the quality score (0-100)"""
    result = _comprehensive_quality_check(image_bytes, topic, post_type=post_type)
    return result["score"]


# ============================================================
# STANDALONE TESTING
# ============================================================

if __name__ == "__main__":
    """Test with a sample image"""
    print("\n" + "=" * 60)
    print("QUALITY AGENT - STANDALONE TEST")
    print("=" * 60 + "\n")

    import sys

    if len(sys.argv) > 1:
        # Test with provided image
        image_path = sys.argv[1]
        post_type_arg = sys.argv[2] if len(sys.argv) > 2 else "image"

        print(f"Testing: {image_path}")
        print(f"Post type: {post_type_arg}")

        with open(image_path, "rb") as f:
            image_bytes = f.read()

        test_memory = AgentMemory()
        test_memory.image_bytes = image_bytes
        test_memory.topic = "Lord Krishna playing flute"
        test_memory.post_type = post_type_arg

        result = run(test_memory)

        print(f"\n📊 Final Score: {result.quality_score}/100")
        print(f"✅ Passed: {result.quality_passed}")
        print(f"📝 Issues: {len(result.quality_issues)}")

    else:
        print("Usage: python -m agents.quality_agent <image_path> [post_type]")
        print("Example: python -m agents.quality_agent test.jpg image")
        print("Example: python -m agents.quality_agent reel.jpg reel")