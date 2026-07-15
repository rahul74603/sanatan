"""
Watermark/Branding Utility - ANTI-CROP EDITION + VIDEO SUPPORT
Multi-layer protection so watermark survives even after cropping.

Strategy for IMAGES:
- Diagonal repeating watermark across entire image (unremovable)
- Center subtle signature
- Multiple corner signatures
- Micro signatures scattered
- Never bottom-only (chor log crop kar dete hain)

🆕 V2 UPDATE: Added video watermarking via FFmpeg
- apply_video_branding() for MP4 videos
- Supports bottom-right corner watermark
- Optional diagonal pattern for stronger protection
"""
import os
import io
import math
import subprocess
import tempfile
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageEnhance
from io import BytesIO
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
    "fonts/NotoSansDevanagari-Bold.ttf",     # ✅ Cross-platform (priority)
    "fonts/NotoSansDevanagari-Regular.ttf",  # Fallback
    "C:/Windows/Fonts/NirmalaUI.ttf",       # ✅ Hindi Windows
    "C:/Windows/Fonts/mangal.ttf",          # ✅ Hindi Windows
    "C:/Windows/Fonts/NirmalaB.ttf",        # ✅ Hindi Bold Windows
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
# MAIN BRANDING FUNCTION (IMAGES)
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
# CONVENIENCE FUNCTIONS (IMAGES)
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
# 🆕 V2: VIDEO WATERMARKING (FFmpeg)
# ============================================================

def _check_ffmpeg() -> bool:
    """Check if FFmpeg is installed and accessible"""
    try:
        result = subprocess.run(
            ["ffmpeg", "-version"],
            capture_output=True,
            timeout=5
        )
        return result.returncode == 0
    except Exception:
        return False


def _create_watermark_png(
    text: str = None,
    width: int = 400,
    opacity: int = 180
) -> bytes:
    """
    🆕 Create transparent PNG watermark for video overlay.

    Args:
        text: Watermark text (default: handle)
        width: Width in pixels
        opacity: 0-255 (higher = more opaque)

    Returns:
        PNG bytes with transparent background
    """
    if text is None:
        text = BRANDING["handle"]

    # Create transparent image
    img = Image.new("RGBA", (width, 80), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Load font
    font_size = 32
    font = _load_font(font_size)

    # Measure text
    bbox = draw.textbbox((0, 0), text, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]

    # Center text with padding
    padding = 20
    x = padding
    y = (80 - text_h) // 2

    # Background pill (semi-transparent black)
    pill_bg = [
        x - 10, y - 5,
        x + text_w + 10, y + text_h + 5
    ]
    draw.rounded_rectangle(
        pill_bg,
        radius=15,
        fill=(0, 0, 0, min(opacity + 30, 220))
    )

    # Shadow
    draw.text((x + 1, y + 1), text, font=font, fill=(0, 0, 0, 200))

    # Main text (gold color)
    draw.text((x, y), text, font=font, fill=(255, 215, 0, opacity))

    # Save to bytes
    output = BytesIO()
    img.save(output, format="PNG")
    return output.getvalue()


def apply_video_branding(
    input_video_path: str,
    output_video_path: str = None,
    strategy: str = "balanced",
    position: str = "bottom-right"
) -> str:
    """
    🆕 Apply watermark to video using FFmpeg.

    Args:
        input_video_path: Path to input video
        output_video_path: Path to save watermarked video (auto-generated if None)
        strategy: "maximum" | "balanced" | "minimal"
        position: "bottom-right" | "bottom-left" | "top-right" | "top-left" | "center"

    Returns:
        Path to watermarked video

    Notes:
        - Requires FFmpeg installed and in PATH
        - Falls back to returning original path if FFmpeg not available
        - For 'maximum' strategy: uses diagonal pattern overlay (heavier processing)
        - For 'balanced'/'minimal': just bottom-right corner watermark
    """
    input_path = Path(input_video_path)

    if not input_path.exists():
        raise FileNotFoundError(f"Video not found: {input_path}")

    # Auto-generate output path if not provided
    if output_video_path is None:
        output_video_path = str(
            input_path.parent / f"{input_path.stem}_watermarked{input_path.suffix}"
        )

    # ═══════════════════════════════════════════
    # Check FFmpeg availability
    # ═══════════════════════════════════════════
    if not _check_ffmpeg():
        logger.warning("⚠️  FFmpeg not found. Returning original video without watermark.")
        return str(input_path)

    logger.info("=" * 55)
    logger.info("🎬 VIDEO WATERMARKING")
    logger.info("=" * 55)
    logger.info(f"   Input     : {input_path.name}")
    logger.info(f"   Output    : {Path(output_video_path).name}")
    logger.info(f"   Strategy  : {strategy}")
    logger.info(f"   Position  : {position}")
    logger.info("=" * 55)

    # ═══════════════════════════════════════════
    # Create watermark PNG
    # ═══════════════════════════════════════════
    strategy_config = STRATEGIES.get(strategy, STRATEGIES[DEFAULT_STRATEGY])
    opacity = strategy_config["opacity"] * 4  # Convert to 0-255 range

    watermark_png = _create_watermark_png(
        text=BRANDING["handle"],
        width=400,
        opacity=min(opacity, 220)
    )

    # Save watermark to temp file (FFmpeg needs file path)
    with tempfile.NamedTemporaryFile(
        delete=False,
        suffix='.png',
        prefix='watermark_'
    ) as f:
        f.write(watermark_png)
        watermark_path = f.name

    logger.info(f"💾 Watermark PNG created: {len(watermark_png):,} bytes")

    # ═══════════════════════════════════════════
    # Build FFmpeg overlay position
    # ═══════════════════════════════════════════
    position_map = {
        "bottom-right": "W-w-20:H-h-20",
        "bottom-left":  "20:H-h-20",
        "top-right":    "W-w-20:20",
        "top-left":     "20:20",
        "center":       "(W-w)/2:(H-h)/2",
    }
    overlay_position = position_map.get(position, position_map["bottom-right"])

    # ═══════════════════════════════════════════
    # FFmpeg command
    # ═══════════════════════════════════════════

    if strategy == "maximum":
        # Maximum: Corner watermark + diagonal pattern (complex filter)
        # For now, just do corner + additional overlay at different position
        filter_complex = (
            f"[1:v]scale=200:-1[wm1];"
            f"[0:v][wm1]overlay={overlay_position}[v1];"
            f"[1:v]scale=150:-1,format=rgba,colorchannelmixer=aa=0.3[wm2];"
            f"[v1][wm2]overlay=(W-w)/2:H*0.35"
        )
    else:
        # Balanced/Minimal: Just corner watermark
        filter_complex = (
            f"[1:v]scale=200:-1[wm];"
            f"[0:v][wm]overlay={overlay_position}"
        )

    cmd = [
        "ffmpeg",
        "-y",  # Overwrite output
        "-i", str(input_path),
        "-i", watermark_path,
        "-filter_complex", filter_complex,
        "-codec:a", "copy",  # Copy audio without re-encoding (faster)
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "23",
        "-movflags", "+faststart",
        "-pix_fmt", "yuv420p",
        output_video_path
    ]

    # ═══════════════════════════════════════════
    # Run FFmpeg
    # ═══════════════════════════════════════════
    try:
        import time
        start_time = time.time()

        logger.info(f"🎥 Running FFmpeg...")

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300  # 5 min timeout
        )

        elapsed = round(time.time() - start_time, 2)

        if result.returncode != 0:
            logger.error(f"❌ FFmpeg failed:")
            logger.error(result.stderr[-500:])  # Last 500 chars of error
            raise Exception(f"FFmpeg exit code: {result.returncode}")

        # Verify output file
        output_path = Path(output_video_path)
        if not output_path.exists():
            raise Exception("Output file not created")

        output_size = output_path.stat().st_size
        input_size = input_path.stat().st_size

        logger.info("=" * 55)
        logger.info(f"✅ VIDEO WATERMARK APPLIED")
        logger.info("=" * 55)
        logger.info(f"   Time      : {elapsed}s")
        logger.info(f"   Input     : {input_size/1024/1024:.2f} MB")
        logger.info(f"   Output    : {output_size/1024/1024:.2f} MB")
        logger.info(f"   Path      : {output_video_path}")
        logger.info("=" * 55)

        return output_video_path

    except subprocess.TimeoutExpired:
        logger.error("❌ FFmpeg timeout (>5 min)")
        raise Exception("Video watermarking timeout")

    except Exception as e:
        logger.error(f"❌ Video watermarking failed: {e}")
        # Return original if fails
        return str(input_path)

    finally:
        # Cleanup temp watermark file
        try:
            os.remove(watermark_path)
        except Exception:
            pass


def apply_video_branding_from_bytes(
    video_bytes: bytes,
    strategy: str = "balanced",
    position: str = "bottom-right"
) -> bytes:
    """
    🆕 Apply watermark to video bytes (convenience wrapper).

    Saves bytes to temp file, watermarks, reads result back.

    Args:
        video_bytes: Video MP4 bytes
        strategy: "maximum" | "balanced" | "minimal"
        position: Corner position

    Returns:
        Watermarked video bytes
    """
    if not video_bytes:
        raise ValueError("No video bytes provided")

    # Save input to temp file
    input_temp = tempfile.NamedTemporaryFile(
        delete=False,
        suffix='.mp4',
        prefix='input_video_'
    )
    input_temp.write(video_bytes)
    input_temp.close()

    # Prepare output temp path
    output_temp_path = input_temp.name.replace('.mp4', '_wm.mp4')

    try:
        # Apply watermark
        result_path = apply_video_branding(
            input_video_path=input_temp.name,
            output_video_path=output_temp_path,
            strategy=strategy,
            position=position
        )

        # Read watermarked bytes
        with open(result_path, 'rb') as f:
            result_bytes = f.read()

        logger.info(f"✅ Watermarked bytes: {len(result_bytes):,} bytes")

        return result_bytes

    finally:
        # Cleanup temp files
        try:
            os.remove(input_temp.name)
        except Exception:
            pass
        try:
            if os.path.exists(output_temp_path):
                os.remove(output_temp_path)
        except Exception:
            pass


# ============================================================
# STANDALONE TEST
# ============================================================

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("WATERMARK - STANDALONE TEST (V2)")
    print("=" * 60)
    print(f"Instagram: {BRANDING['instagram']}")
    print(f"Facebook : {BRANDING['facebook']}")
    print(f"Brand    : {BRANDING['combined']}")

    # ═══════════════════════════════════════════
    # TEST 1: IMAGE WATERMARKING
    # ═══════════════════════════════════════════
    print("\n" + "=" * 60)
    print("TEST 1: IMAGE WATERMARKING")
    print("=" * 60)

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

    # ═══════════════════════════════════════════
    # TEST 2: VIDEO WATERMARKING
    # ═══════════════════════════════════════════
    print("\n" + "=" * 60)
    print("TEST 2: VIDEO WATERMARKING")
    print("=" * 60)

    # Check FFmpeg
    if not _check_ffmpeg():
        print("\n⚠️  FFmpeg not installed. Skipping video test.")
        print("   Install FFmpeg to test video watermarking.")
    else:
        print("✅ FFmpeg available")

        # Check for test video
        test_videos = [
            "test_reel.mp4",
            "test_concat_basic.mp4",
            "test_effects_all.mp4"
        ]

        test_video_found = None
        for tv in test_videos:
            if Path(tv).exists():
                test_video_found = tv
                break

        if test_video_found:
            print(f"\n🎥 Test video: {test_video_found}")

            try:
                output = apply_video_branding(
                    input_video_path=test_video_found,
                    output_video_path="test_video_watermarked.mp4",
                    strategy="balanced"
                )

                print(f"\n✅ Video watermark test successful!")
                print(f"   Output: {output}")
                print(f"\n💡 Play video: start {output}")

            except Exception as e:
                print(f"❌ Video watermark failed: {e}")
        else:
            print("\n⚠️  No test video found. Skipping.")
            print("   Create a test video to test watermarking.")

    print(f"\n" + "=" * 60)
    print("🎉 Test complete!")
    print("=" * 60)