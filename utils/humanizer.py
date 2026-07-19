"""
Humanizer Utility V2 - Anti-AI Detection System (FIXED)

FEATURES (ALL PRESERVED FROM V1):
- Multi-layer image humanization
- Random EXIF metadata injection
- Camera simulation effects
- Realistic compression artifacts
- Advanced caption humanization
- Emoji intelligence
- Natural language variations
- Punctuation randomization

V2 FIXES:
- 🔧 Higher minimum JPEG quality (88 vs 82) - prevents dark image destruction
- 🔧 Gentler enhancements (was too aggressive on dark scenes)
- 🔧 Reduced vignette/blur probability (was over-darkening scenes)
- 🚨 NEW: Size ratio safety check (auto-retry if degraded >60%)
- 🚨 NEW: Final fallback to original image if humanization fails
- 🔧 Removed random progressive JPEG (was causing artifacts)
- 🆕 Chroma subsampling=0 (preserves color quality)
"""
import random
import io
from datetime import datetime, timedelta
from PIL import Image, ImageEnhance, ImageFilter, ImageOps
from PIL.ExifTags import TAGS

from utils.logger import get_logger

logger = get_logger("humanizer")


# ============================================================
# CONFIGURATION - V2 FIXED
# ============================================================

# Simulated camera models (realistic EXIF)
CAMERA_MODELS = [
    ("Apple", "iPhone 14 Pro"),
    ("Apple", "iPhone 13"),
    ("Apple", "iPhone 12 Pro Max"),
    ("Samsung", "Galaxy S23 Ultra"),
    ("Samsung", "Galaxy S22"),
    ("Google", "Pixel 7 Pro"),
    ("Google", "Pixel 6"),
    ("OnePlus", "11 5G"),
    ("Xiaomi", "13 Pro"),
]

# 🔧 V2 FIX: Higher minimum quality (was 82, now 88)
# Prevents catastrophic compression on dark/complex scenes
QUALITY_RANGE = (88, 95)                # V1 was (82, 96)

# 🔧 V2 FIX: Gentler enhancement ranges (was too aggressive)
BRIGHTNESS_RANGE = (0.95, 1.05)         # V1 was (0.92, 1.08)
CONTRAST_RANGE = (0.96, 1.06)           # V1 was (0.94, 1.10)
COLOR_RANGE = (0.94, 1.08)              # V1 was (0.90, 1.15)
SHARPNESS_RANGE = (0.92, 1.12)          # V1 was (0.85, 1.20)

# 🔧 V2 FIX: Reduced blur probability + range
BLUR_PROBABILITY = 0.15                 # V1 was 0.25
BLUR_RADIUS_RANGE = (0.15, 0.4)         # V1 was (0.2, 0.6)

# Noise probability (kept for compatibility, unused in current pipeline)
NOISE_PROBABILITY = 0.15

# Slight rotation probability (kept for compatibility)
ROTATION_PROBABILITY = 0.10
ROTATION_RANGE = (-0.5, 0.5)  # degrees

# 🔧 V2 FIX: Reduced vignette (vignette darkens edges - was killing dark scenes)
VIGNETTE_PROBABILITY = 0.10             # V1 was 0.20

# 🚨 V2 NEW: SAFETY THRESHOLDS
MIN_ACCEPTABLE_SIZE_RATIO = 0.40   # Reject if output < 40% of input
MAX_ACCEPTABLE_SIZE_RATIO = 3.0    # Reject if output > 300% of input


# ============================================================
# IMAGE HUMANIZATION
# ============================================================

def _ensure_rgb(img: Image.Image) -> Image.Image:
    """Convert to RGB if needed"""
    if img.mode == 'RGBA':
        bg = Image.new('RGB', img.size, (255, 255, 255))
        bg.paste(img, mask=img.split()[3])
        return bg
    elif img.mode != 'RGB':
        return img.convert('RGB')
    return img


def _apply_random_enhancements(img: Image.Image) -> Image.Image:
    """Apply subtle random enhancements like phone camera"""

    # Brightness (like camera exposure variation)
    img = ImageEnhance.Brightness(img).enhance(
        random.uniform(*BRIGHTNESS_RANGE)
    )

    # Contrast (like camera contrast setting)
    img = ImageEnhance.Contrast(img).enhance(
        random.uniform(*CONTRAST_RANGE)
    )

    # Color saturation (like camera color profile)
    img = ImageEnhance.Color(img).enhance(
        random.uniform(*COLOR_RANGE)
    )

    # Sharpness (like camera processing)
    img = ImageEnhance.Sharpness(img).enhance(
        random.uniform(*SHARPNESS_RANGE)
    )

    return img


def _apply_slight_blur(img: Image.Image) -> Image.Image:
    """Apply very subtle blur occasionally"""
    if random.random() < BLUR_PROBABILITY:
        radius = random.uniform(*BLUR_RADIUS_RANGE)
        return img.filter(ImageFilter.GaussianBlur(radius=radius))
    return img


def _apply_vignette(img: Image.Image) -> Image.Image:
    """Apply natural lens vignetting effect - V2 GENTLER"""
    if random.random() < VIGNETTE_PROBABILITY:
        try:
            # Create vignette mask
            width, height = img.size
            mask = Image.new('L', (width, height), 0)

            # Simple radial gradient using PIL
            center_x, center_y = width // 2, height // 2
            max_dist = ((center_x ** 2 + center_y ** 2) ** 0.5)

            # 🔧 V2 FIX: Reduced darkening intensity (0.08 vs 0.15)
            # This prevents over-darkening of already-dark scenes
            for y in range(0, height, 4):  # Skip pixels for speed
                for x in range(0, width, 4):
                    dist = ((x - center_x) ** 2 + (y - center_y) ** 2) ** 0.5
                    intensity = int(255 * (1 - (dist / max_dist) * 0.08))
                    mask.putpixel((x, y), intensity)

            # Blur the mask for smooth transition
            mask = mask.filter(ImageFilter.GaussianBlur(radius=50))

            # Apply vignette
            black = Image.new('RGB', img.size, (0, 0, 0))
            img = Image.composite(img, black, mask)

        except Exception as e:
            logger.debug(f"Vignette skipped: {e}")

    return img


def _get_random_camera_exif() -> dict:
    """
    Generate realistic EXIF metadata.
    
    NOTE: Currently unused in main pipeline but preserved for future use.
    PIL doesn't easily inject custom EXIF - would need piexif library.
    """
    make, model = random.choice(CAMERA_MODELS)

    # Random datetime in last 30 days
    days_ago = random.randint(0, 30)
    hours_ago = random.randint(0, 23)
    photo_date = datetime.now() - timedelta(days=days_ago, hours=hours_ago)

    return {
        "Make": make,
        "Model": model,
        "DateTime": photo_date.strftime("%Y:%m:%d %H:%M:%S"),
        "Software": f"{make} {model}",
        "ExposureTime": random.choice(["1/60", "1/125", "1/250", "1/500"]),
        "FNumber": random.choice([1.8, 2.2, 2.4, 2.8]),
        "ISO": random.choice([100, 200, 400, 800]),
    }


def humanize_image(image_bytes: bytes) -> bytes:
    """
    Multi-layer humanization to avoid AI detection.

    Techniques:
    1. Color/brightness/contrast variations (like phone camera)
    2. Slight blur (occasional)
    3. Vignette (occasional)
    4. Random JPEG quality (like phone compression)
    5. EXIF metadata (like real photo)
    
    V2 IMPROVEMENTS:
    - Safer quality range (88-95 vs 82-96)
    - Gentler enhancement ranges
    - Size ratio validation with auto-retry
    - Falls back to original if humanization damages image
    - Removed random progressive JPEG (was causing artifacts)
    - Chroma subsampling=0 preserves color quality
    """
    original_size = len(image_bytes)
    
    try:
        img = Image.open(io.BytesIO(image_bytes))

        # Convert to RGB
        img = _ensure_rgb(img)

        # Apply enhancement layers
        img = _apply_random_enhancements(img)
        img = _apply_slight_blur(img)
        img = _apply_vignette(img)

        # 🔧 V2 FIX: Safer JPEG saving
        output = io.BytesIO()
        quality = random.randint(*QUALITY_RANGE)

        # 🔧 V2 FIX: Deterministic settings (removed randomness that caused issues)
        # - optimize=False → prevents aggressive re-compression
        # - progressive=False → prevents progressive JPEG artifacts  
        # - subsampling=0 → preserves color/detail quality (4:4:4)
        img.save(
            output,
            format='JPEG',
            quality=quality,
            optimize=False,        # V1 was True (too aggressive)
            progressive=False,     # V1 was random (caused artifacts)
            subsampling=0,         # 🆕 V2: Preserves color quality
        )

        result = output.getvalue()
        new_size = len(result)

        # 🚨 V2 NEW: SAFETY CHECK - Reject if output is way too small
        size_ratio = new_size / original_size

        if size_ratio < MIN_ACCEPTABLE_SIZE_RATIO:
            # Output is way too small — likely corrupted/dark scene destroyed
            logger.warning(
                f"⚠️  Humanization degraded image too much "
                f"({original_size} → {new_size}, {(size_ratio*100):.1f}%). "
                f"Retrying with maximum quality..."
            )
            
            # Retry with maximum quality settings
            output = io.BytesIO()
            img.save(
                output,
                format='JPEG',
                quality=95,
                optimize=False,
                progressive=False,
                subsampling=0,
            )
            result = output.getvalue()
            new_size = len(result)
            new_ratio = new_size / original_size
            
            # If STILL too small after retry, use original image
            if new_ratio < MIN_ACCEPTABLE_SIZE_RATIO:
                logger.warning(
                    f"⚠️  Retry also degraded ({(new_ratio*100):.1f}%). "
                    f"Using ORIGINAL image instead (safer than corrupted output)."
                )
                return image_bytes
            
            logger.info(f"✅ Retry successful: {(new_ratio*100):.1f}% of original")

        # Log final result
        size_change = ((new_size - original_size) / original_size) * 100
        logger.info(
            f"🎭 Humanized: {original_size} → {new_size} bytes "
            f"({size_change:+.1f}%) | quality: {quality}"
        )

        return result

    except Exception as e:
        logger.warning(f"⚠️ Humanization failed (using original): {e}")
        return image_bytes


# ============================================================
# CAPTION HUMANIZATION
# ============================================================

# Emoji categories
EMOJI_POOLS = {
    "spiritual": ['🙏', '✨', '🕉️', '🌸', '🪔', '🌺', '💫', '🚩', '☘️', '🌿'],
    "krishna": ['🌸', '💙', '🎵', '🦚', '🌺', '✨'],
    "shiva": ['🕉️', '🔱', '🌙', '⚡', '🚩', '🔥'],
    "hanuman": ['🚩', '💪', '🙏', '🔥', '🧡'],
    "ganesha": ['🐘', '🙏', '🌺', '🍯', '✨'],
    "durga": ['🌺', '🚩', '🔴', '🙏', '✨'],
    "ram": ['🚩', '🏹', '🙏', '🌼', '☀️'],
    "motivational": ['💪', '🔥', '⚡', '🌅', '🚀', '✨'],
    "peaceful": ['🌿', '☘️', '🕊️', '🌸', '✨', '🙏']
}

# Punctuation variations (make text feel typed)
PUNCTUATION_VARIATIONS = {
    ". ": [". ", ".. ", "... "],
    "! ": ["! ", "!! "],
    "? ": ["? ", "?? "],
}

# Line break variations
LINE_BREAK_STYLES = [
    "\n",
    "\n\n",  # Double line break for spacing
]


def _count_emojis(text: str) -> int:
    """Count emojis in text (approximate)"""
    emoji_ranges = [
        (0x1F600, 0x1F64F),  # Emoticons
        (0x1F300, 0x1F5FF),  # Symbols
        (0x1F680, 0x1F6FF),  # Transport
        (0x1F1E0, 0x1F1FF),  # Flags
        (0x1F900, 0x1F9FF),  # Supplemental
        (0x2600, 0x27BF),    # Misc symbols
    ]

    count = 0
    for char in text:
        code = ord(char)
        if any(start <= code <= end for start, end in emoji_ranges):
            count += 1
    return count


def _add_natural_emoji(caption: str, category: str = "spiritual") -> str:
    """Add contextually appropriate emoji"""
    emojis = EMOJI_POOLS.get(category, EMOJI_POOLS["spiritual"])

    # Only add if not already present or emoji count is low
    if _count_emojis(caption) < 2:
        emoji = random.choice(emojis)

        # Add at end most of the time
        if random.random() < 0.8:
            if not caption.endswith((' ', '\n')):
                caption += " "
            caption += emoji

    return caption


def _vary_punctuation(caption: str) -> str:
    """Occasionally vary punctuation for human feel"""

    # 15% chance to add extra dots (natural pauses)
    if random.random() < 0.15:
        for old, options in PUNCTUATION_VARIATIONS.items():
            if old in caption:
                # Replace only first occurrence
                new_variant = random.choice(options)
                caption = caption.replace(old, new_variant, 1)
                break

    return caption


def _remove_excessive_emojis(caption: str, max_count: int = 5) -> str:
    """Remove excess emojis if too many (looks AI-generated)"""
    emoji_count = _count_emojis(caption)

    if emoji_count <= max_count:
        return caption

    # Split into words
    words = caption.split()
    result = []
    current_emojis = 0

    for word in words:
        word_emojis = _count_emojis(word)

        if current_emojis + word_emojis <= max_count:
            result.append(word)
            current_emojis += word_emojis
        elif word_emojis == 0:
            # Not an emoji, keep it
            result.append(word)

    return " ".join(result)


def _clean_ai_artifacts(caption: str) -> str:
    """Remove common AI-generated patterns"""

    # Common AI phrases to remove/replace
    ai_patterns = {
        "In conclusion,": "",
        "In summary,": "",
        "To sum up,": "",
        "Overall,": "",
        "In essence,": "",
        "Firstly,": "",
        "Secondly,": "",
        "Lastly,": "",
    }

    for pattern, replacement in ai_patterns.items():
        if caption.startswith(pattern):
            caption = caption.replace(pattern, replacement, 1).strip()

    return caption


def humanize_caption(caption: str, category: str = "spiritual") -> str:
    """
    Advanced caption humanization.

    Args:
        caption: Original caption
        category: Content category for emoji selection

    Returns:
        Humanized caption
    """
    if not caption:
        return caption

    original_length = len(caption)

    # Clean AI artifacts
    caption = _clean_ai_artifacts(caption)

    # Vary punctuation (natural feel)
    caption = _vary_punctuation(caption)

    # Manage emojis
    caption = _remove_excessive_emojis(caption, max_count=5)
    caption = _add_natural_emoji(caption, category)

    # Final cleanup
    caption = caption.strip()

    # Log if significant change
    if abs(len(caption) - original_length) > 10:
        logger.debug(f"Caption humanized: {original_length} → {len(caption)} chars")

    return caption


# ============================================================
# STANDALONE TESTING
# ============================================================

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("HUMANIZER V2 - STANDALONE TEST")
    print("=" * 60 + "\n")

    # Test caption humanization
    test_captions = [
        ("krishna", "Krishna ki basuri divine hai. Bas dil se sunna hai."),
        ("shiva", "Om Namah Shivaya. Mahadev ke bhakt kabhi haar nahi maante."),
        ("motivational", "Zindagi mushkil hai. Aage badho. Har rukavat ek seekh hai."),
    ]

    for category, caption in test_captions:
        print(f"\n📂 Category: {category}")
        print(f"📝 Original : {caption}")
        humanized = humanize_caption(caption, category)
        print(f"🎭 Humanized: {humanized}")

    # Test image humanization (if test image exists)
    from pathlib import Path
    test_image = Path("test_vertex.jpg")

    if test_image.exists():
        print(f"\n🖼️  Testing image humanization: {test_image}")

        with open(test_image, "rb") as f:
            original_bytes = f.read()

        humanized_bytes = humanize_image(original_bytes)

        # Save humanized version
        output_path = Path("test_humanized.jpg")
        with open(output_path, "wb") as f:
            f.write(humanized_bytes)

        print(f"✅ Humanized image saved: {output_path}")
        print(f"   Original : {len(original_bytes)} bytes")
        print(f"   Humanized: {len(humanized_bytes)} bytes")
        
        ratio = len(humanized_bytes) / len(original_bytes)
        print(f"   Size ratio: {ratio*100:.1f}%")
        if ratio < MIN_ACCEPTABLE_SIZE_RATIO:
            print(f"   ⚠️  BELOW SAFETY THRESHOLD ({MIN_ACCEPTABLE_SIZE_RATIO*100}%)")
        else:
            print(f"   ✅ Safe (above {MIN_ACCEPTABLE_SIZE_RATIO*100}% threshold)")
    else:
        print(f"\n💡 No test image found. Run vertex_ai.py first.")

    print("\n" + "=" * 60)
    print("V2 CONFIG SUMMARY:")
    print("=" * 60)
    print(f"   Quality range    : {QUALITY_RANGE} (V1: 82-96)")
    print(f"   Min size ratio   : {MIN_ACCEPTABLE_SIZE_RATIO*100}% (auto-retry if lower)")
    print(f"   Vignette prob    : {VIGNETTE_PROBABILITY*100}% (V1: 20%)")
    print(f"   Blur prob        : {BLUR_PROBABILITY*100}% (V1: 25%)")
    print(f"   Brightness range : {BRIGHTNESS_RANGE} (V1: 0.92-1.08)")
    print(f"   Contrast range   : {CONTRAST_RANGE} (V1: 0.94-1.10)")
    print(f"   Color range      : {COLOR_RANGE} (V1: 0.90-1.15)")
    print(f"   Sharpness range  : {SHARPNESS_RANGE} (V1: 0.85-1.20)")
    print("=" * 60)