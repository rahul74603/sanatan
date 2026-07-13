"""
Watermark/Branding Utility - ANTI-CROP EDITION
Multi-layer protection so watermark survives even after cropping.

Strategy:
- Diagonal repeating watermark across entire image (unremovable)
- Center subtle signature
- Multiple corner signatures
- Micro signatures scattered
- Never bottom-only (chor log crop kar dete hain)
"""
from PIL import Image, ImageDraw, ImageFont, ImageEnhance
from io import BytesIO
import os
import math
from utils.logger import get_logger

logger = get_logger("watermark")


# ============================================================
# BRANDING CONFIG
# ============================================================

BRANDING = {
    "instagram": "@sanatanii_soch",       # ✅ Confirmed handle
    "facebook":  "सनातनी सोच",             # ✅ FB page name
    "combined":  "सनातनी सोच",             # Main brand
    "handle":    "@sanatanii_soch",       # For diagonal use
    "tagline":   "sanatanii_soch",
}

# ============================================================
# STRATEGY CONFIG
# ============================================================

STRATEGIES = {
    "maximum": {
        # Full protection - hard to remove
        "diagonal_pattern":  True,
        "center_signature":  True,
        "corner_signatures": True,   # 3 corners
        "micro_signatures":  True,   # Scattered small ones
        "opacity":           45,     # Very subtle
    },
    "balanced": {
        # Good protection, less intrusive
        "diagonal_pattern":  True,
        "center_signature":  True,
        "corner_signatures": True,
        "micro_signatures":  False,
        "opacity":           55,
    },
    "minimal": {
        # Least visible but still protected
        "diagonal_pattern":  True,
        "center_signature":  False,
        "corner_signatures": True,
        "micro_signatures":  False,
        "opacity":           40,
    },
}

DEFAULT_STRATEGY = "balanced"

# Font paths (Hindi support priority)
FONT_PATHS = [
    "C:/Windows/Fonts/NirmalaUI.ttf",       # ✅ Hindi
    "C:/Windows/Fonts/mangal.ttf",          # ✅ Hindi
    "C:/Windows/Fonts/NirmalaB.ttf",        # ✅ Hindi Bold
    "C:/Windows/Fonts/Arial.ttf",
    "C:/Windows/Fonts/calibrib.ttf",
    "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Regular.ttf",
    "/System/Library/Fonts/Helvetica.ttc",
]


# ============================================================
# FONT LOADER (cached)
# ============================================================

_font_cache = {}

def _load_font(size: int) -> ImageFont.FreeTypeFont:
    """Load font with caching"""
    if size in _font_cache:
        return _font_cache[size]

    for font_path in FONT_PATHS:
        if os.path.exists(font_path):
            try:
                font = ImageFont.truetype(font_path, size)
                _font_cache[size] = font
                return font
            except Exception:
                continue

    logger.warning("⚠️ No TTF font found, using default")
    return ImageFont.load_default()


# ============================================================
# LAYER 1: DIAGONAL REPEATING PATTERN (CROP-PROOF!)
# ============================================================

def _add_diagonal_watermark(
    img:     Image.Image,
    text:    str,
    opacity: int = 40,
    angle:   int = -30,
    spacing: float = 1.5    # Distance multiplier between repetitions
) -> Image.Image:
    """
    Add diagonal repeating watermark across ENTIRE image.
    Chor log crop भी करें तो watermark किसी न किसी हिस्से में रहेगा।
    """
    img_w, img_h = img.size

    # Font size based on image
    font_size = max(int(img_w * 0.025), 16)
    font      = _load_font(font_size)

    # Measure text
    tmp_draw = ImageDraw.Draw(img)
    bbox     = tmp_draw.textbbox((0, 0), text, font=font)
    text_w   = bbox[2] - bbox[0]
    text_h   = bbox[3] - bbox[1]

    # Create transparent layer for rotated text
    # Make it big enough to fill image after rotation
    diagonal = int(math.sqrt(img_w**2 + img_h**2)) + 200

    # Spacing between watermarks
    dx = int(text_w * spacing) + 100
    dy = int(text_h * spacing * 2) + 60

    # Create pattern layer
    pattern = Image.new("RGBA", (diagonal, diagonal), (0, 0, 0, 0))
    p_draw  = ImageDraw.Draw(pattern)

    # Draw text in grid pattern
    for y in range(-dy, diagonal + dy, dy):
        # Offset every other row for staggered look
        x_offset = (dx // 2) if (y // dy) % 2 else 0

        for x in range(-dx + x_offset, diagonal + dx, dx):
            # Add subtle shadow for readability
            p_draw.text(
                (x + 1, y + 1),
                text,
                font = font,
                fill = (0, 0, 0, min(opacity + 20, 100))
            )
            # Main text (white, semi-transparent)
            p_draw.text(
                (x, y),
                text,
                font = font,
                fill = (255, 255, 255, opacity)
            )

    # Rotate the pattern
    rotated = pattern.rotate(angle, resample=Image.BICUBIC, expand=False)

    # Crop to image size (centered)
    left   = (diagonal - img_w) // 2
    top    = (diagonal - img_h) // 2
    right  = left + img_w
    bottom = top + img_h
    rotated_cropped = rotated.crop((left, top, right, bottom))

    # Composite onto image
    if img.mode != "RGBA":
        img = img.convert("RGBA")

    return Image.alpha_composite(img, rotated_cropped)


# ============================================================
# LAYER 2: CENTER SUBTLE SIGNATURE
# ============================================================

def _add_center_signature(
    img:     Image.Image,
    text:    str,
    opacity: int = 50
) -> Image.Image:
    """
    Add subtle centered signature.
    Chor बीच से crop नहीं कर सकते (image ruin हो जाएगी)।
    """
    img_w, img_h = img.size

    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw    = ImageDraw.Draw(overlay)

    # Font size
    font_size = max(int(img_w * 0.04), 22)
    font      = _load_font(font_size)

    # Measure
    bbox   = draw.textbbox((0, 0), text, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]

    # Position: center
    x = (img_w - text_w) // 2
    y = (img_h - text_h) // 2

    # Very subtle - just outline effect
    outline_color = (0, 0, 0, opacity + 30)
    for dx in [-1, 0, 1]:
        for dy in [-1, 0, 1]:
            draw.text((x + dx, y + dy), text, font=font, fill=outline_color)

    # Main text - low opacity
    draw.text((x, y), text, font=font, fill=(255, 255, 255, opacity))

    if img.mode != "RGBA":
        img = img.convert("RGBA")

    return Image.alpha_composite(img, overlay)


# ============================================================
# LAYER 3: MULTIPLE CORNER SIGNATURES
# ============================================================

def _add_corner_signatures(
    img:     Image.Image,
    text:    str,
    opacity: int = 90
) -> Image.Image:
    """
    Add signatures in 3 corners (top-right, mid-left, mid-right).
    Skip bottom (that's what chors crop).
    Multiple positions = harder to remove all.
    """
    img_w, img_h = img.size

    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw    = ImageDraw.Draw(overlay)

    # Small font for corners
    font_size = max(int(img_w * 0.022), 14)
    font      = _load_font(font_size)

    # Measure
    bbox   = draw.textbbox((0, 0), text, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]

    padding = int(img_w * 0.03)

    # Positions: NO BOTTOM (crop-proof!)
    # Focus on top and sides - hardest to crop without ruining image
    positions = [
        # Top-right corner
        (img_w - text_w - padding, padding),

        # Top-left corner
        (padding, padding),

        # Middle-right edge (vertical middle)
        (img_w - text_w - padding, (img_h - text_h) // 2),

        # Middle-left edge
        (padding, (img_h - text_h) // 2),
    ]

    for x, y in positions:
        # Background pill for readability
        bg_pad = int(font_size * 0.35)
        bg_rect = [
            x - bg_pad, y - bg_pad // 2,
            x + text_w + bg_pad, y + text_h + bg_pad // 2
        ]
        draw.rounded_rectangle(
            bg_rect,
            radius = int(font_size * 0.4),
            fill   = (0, 0, 0, min(opacity + 30, 140))
        )

        # Shadow
        draw.text((x + 1, y + 1), text, font=font, fill=(0, 0, 0, opacity + 40))

        # Text
        draw.text((x, y), text, font=font, fill=(255, 215, 0, opacity))  # Gold

    if img.mode != "RGBA":
        img = img.convert("RGBA")

    return Image.alpha_composite(img, overlay)


# ============================================================
# LAYER 4: MICRO SIGNATURES (Hidden scattered)
# ============================================================

def _add_micro_signatures(
    img:     Image.Image,
    text:    str,
    opacity: int = 35
) -> Image.Image:
    """
    Add very small signatures at random-ish positions.
    Blends into image - super hard to remove all of them.
    """
    img_w, img_h = img.size

    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw    = ImageDraw.Draw(overlay)

    # Very small font
    font_size = max(int(img_w * 0.015), 10)
    font      = _load_font(font_size)

    bbox   = draw.textbbox((0, 0), text, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]

    # 5 scattered positions (avoiding pure bottom)
    positions = [
        (int(img_w * 0.15), int(img_h * 0.25)),   # top-left area
        (int(img_w * 0.75), int(img_h * 0.35)),   # top-right area
        (int(img_w * 0.25), int(img_h * 0.65)),   # bottom-left area (not corner)
        (int(img_w * 0.70), int(img_h * 0.55)),   # right middle
        (int(img_w * 0.45), int(img_h * 0.85)),   # near bottom center
    ]

    for x, y in positions:
        draw.text((x, y), text, font=font, fill=(255, 255, 255, opacity))
        draw.text((x + 1, y + 1), text, font=font, fill=(0, 0, 0, opacity - 10))

    if img.mode != "RGBA":
        img = img.convert("RGBA")

    return Image.alpha_composite(img, overlay)


# ============================================================
# MAIN BRANDING FUNCTION
# ============================================================

def apply_branding(
    image_bytes: bytes,
    strategy:    str = DEFAULT_STRATEGY,
    format_type: str = "feed"    # Kept for backward compatibility
) -> bytes:
    """
    Apply anti-crop watermark to image.

    Args:
        image_bytes: Raw image bytes
        strategy:    "maximum" | "balanced" | "minimal"
        format_type: (unused, for compatibility)

    Returns:
        Watermarked image bytes
    """
    try:
        # Load image
        img = Image.open(BytesIO(image_bytes)).convert("RGBA")
        original_size = img.size

        # Get strategy config
        config = STRATEGIES.get(strategy, STRATEGIES[DEFAULT_STRATEGY])
        base_opacity = config["opacity"]

        logger.info(
            f"🏷️  Applying '{strategy}' watermark strategy "
            f"(opacity: {base_opacity})"
        )

        layers_applied = []

        # ── Layer 1: Diagonal pattern (MAIN PROTECTION) ──────
        if config["diagonal_pattern"]:
            img = _add_diagonal_watermark(
                img,
                text    = BRANDING["handle"],
                opacity = base_opacity,
                angle   = -30
            )
            layers_applied.append("diagonal")

        # ── Layer 2: Center signature ─────────────────────────
        if config["center_signature"]:
            img = _add_center_signature(
                img,
                text    = BRANDING["combined"],
                opacity = base_opacity + 15
            )
            layers_applied.append("center")

        # ── Layer 3: Corner signatures ────────────────────────
        if config["corner_signatures"]:
            img = _add_corner_signatures(
                img,
                text    = BRANDING["handle"],
                opacity = 100   # Slightly more visible
            )
            layers_applied.append("corners")

        # ── Layer 4: Micro signatures ────────────────────────
        if config["micro_signatures"]:
            img = _add_micro_signatures(
                img,
                text    = BRANDING["tagline"],
                opacity = 40
            )
            layers_applied.append("micro")

        # Convert back to RGB for JPEG
        final = img.convert("RGB")

        # Save
        output = BytesIO()
        final.save(output, format="JPEG", quality=95, optimize=True)
        output.seek(0)
        result = output.read()

        logger.info(
            f"✅ Watermark applied: layers={layers_applied} | "
            f"{len(image_bytes):,} → {len(result):,} bytes"
        )
        return result

    except Exception as e:
        logger.error(f"❌ Watermark failed: {e}", exc_info=True)
        return image_bytes  # Return original if fails


# ============================================================
# CONVENIENCE FUNCTIONS
# ============================================================

def add_maximum_protection(image_bytes: bytes) -> bytes:
    """Maximum anti-crop protection (all 4 layers)"""
    return apply_branding(image_bytes, strategy="maximum")


def add_balanced_watermark(image_bytes: bytes) -> bytes:
    """Balanced protection + aesthetics"""
    return apply_branding(image_bytes, strategy="balanced")


def add_minimal_watermark(image_bytes: bytes) -> bytes:
    """Least visible but still protected"""
    return apply_branding(image_bytes, strategy="minimal")


# ============================================================
# STANDALONE TEST
# ============================================================

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("ANTI-CROP WATERMARK TEST")
    print("=" * 60)
    print(f"Instagram: {BRANDING['instagram']}")
    print(f"Facebook : {BRANDING['facebook']}")
    print(f"Brand    : {BRANDING['combined']}")

    # Create test image (spiritual gradient)
    test_img = Image.new("RGB", (1024, 1024))
    pixels   = test_img.load()

    # Sunset gradient
    for y in range(1024):
        for x in range(1024):
            r = int(255 * (y / 1024))
            g = int(150 * (1 - y / 1024))
            b = int(100 * (x / 1024))
            pixels[x, y] = (r, g, b)

    # Add a circle (sun)
    draw = ImageDraw.Draw(test_img)
    draw.ellipse([362, 362, 662, 662], fill=(255, 220, 50))

    buf = BytesIO()
    test_img.save(buf, format="JPEG", quality=95)
    test_bytes = buf.getvalue()

    print(f"\n📷 Test image created: {len(test_bytes):,} bytes\n")

    # Test all strategies
    strategies = ["maximum", "balanced", "minimal"]

    for strategy in strategies:
        try:
            result = apply_branding(test_bytes, strategy=strategy)
            out_file = f"test_watermark_{strategy}.jpg"
            with open(out_file, "wb") as f:
                f.write(result)
            print(f"✅ {strategy:10s} → {out_file} ({len(result):,} bytes)")
        except Exception as e:
            print(f"❌ {strategy:10s} → Failed: {e}")

    print(f"\n🎉 Test complete!")
    print(f"📁 Check output files:")
    for s in strategies:
        print(f"   test_watermark_{s}.jpg")

    print(f"\n💡 Try to crop these images - watermark will still be visible!")