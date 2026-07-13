"""
Humanizer Utility - Anti-AI Detection System
Features:
- Multi-layer image humanization
- Random EXIF metadata injection
- Camera simulation effects
- Realistic compression artifacts
- Advanced caption humanization
- Emoji intelligence
- Natural language variations
- Punctuation randomization
"""
import random
import io
from datetime import datetime, timedelta
from PIL import Image, ImageEnhance, ImageFilter, ImageOps
from PIL.ExifTags import TAGS

from utils.logger import get_logger

logger = get_logger("humanizer")


# ============================================================
# CONFIGURATION
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

# JPEG quality range (like real phone cameras)
QUALITY_RANGE = (82, 96)

# Enhancement ranges
BRIGHTNESS_RANGE = (0.92, 1.08)
CONTRAST_RANGE = (0.94, 1.10)
COLOR_RANGE = (0.90, 1.15)
SHARPNESS_RANGE = (0.85, 1.20)

# Slight blur probability
BLUR_PROBABILITY = 0.25
BLUR_RADIUS_RANGE = (0.2, 0.6)

# Noise probability (for very old-photo feel)
NOISE_PROBABILITY = 0.15

# Slight rotation probability (perspective correction)
ROTATION_PROBABILITY = 0.10
ROTATION_RANGE = (-0.5, 0.5)  # degrees

# Vignette probability (natural lens vignetting)
VIGNETTE_PROBABILITY = 0.20


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
    """Apply natural lens vignetting effect"""
    if random.random() < VIGNETTE_PROBABILITY:
        try:
            # Create vignette mask
            width, height = img.size
            mask = Image.new('L', (width, height), 0)

            # Simple radial gradient using PIL
            center_x, center_y = width // 2, height // 2
            max_dist = ((center_x ** 2 + center_y ** 2) ** 0.5)

            # Slight darkening at edges
            for y in range(0, height, 4):  # Skip pixels for speed
                for x in range(0, width, 4):
                    dist = ((x - center_x) ** 2 + (y - center_y) ** 2) ** 0.5
                    intensity = int(255 * (1 - (dist / max_dist) * 0.15))
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
    """Generate realistic EXIF metadata"""
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
    Multi-layer humanization to avoid AI detection

    Techniques:
    1. Color/brightness/contrast variations (like phone camera)
    2. Slight blur (occasional)
    3. Vignette (occasional)
    4. Random JPEG quality (like phone compression)
    5. EXIF metadata (like real photo)
    """
    try:
        img = Image.open(io.BytesIO(image_bytes))
        original_size = len(image_bytes)

        # Convert to RGB
        img = _ensure_rgb(img)

        # Apply enhancement layers
        img = _apply_random_enhancements(img)
        img = _apply_slight_blur(img)
        img = _apply_vignette(img)

        # Save with random quality (like real phone)
        output = io.BytesIO()
        quality = random.randint(*QUALITY_RANGE)

        # Random JPEG optimization
        img.save(
            output,
            format='JPEG',
            quality=quality,
            optimize=True,
            progressive=random.choice([True, False])
        )

        result = output.getvalue()
        new_size = len(result)

        # Log
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
    Advanced caption humanization

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
    print("HUMANIZER - STANDALONE TEST")
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
    else:
        print(f"\n💡 No test image found. Run vertex_ai.py first.")