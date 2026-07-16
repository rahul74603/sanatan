"""
Clip Renderer - Convert single image to video clip with Ken Burns effect

Features:
- Convert scene image (bytes) → MoviePy VideoClip
- Apply Ken Burns effect (subtle zoom/pan for cinematic feel)
- 5 effect types: zoom_in, zoom_out, pan_left, pan_right, static
- Auto-resize to 1080x1920 (9:16 portrait for reels)
- Handles aspect ratio conversion (square → portrait)
- Blur background for images that don't fill frame

Ken Burns effect makes static images feel cinematic
by slowly zooming or panning during playback.
"""

# ═══════════════════════════════════════════════════════════
# 🔧 PIL/Pillow 10.x Compatibility Shim (MUST be before other imports!)
# MoviePy 1.0.3 uses old PIL.Image.ANTIALIAS which was removed in Pillow 10
# ═══════════════════════════════════════════════════════════
import PIL.Image
if not hasattr(PIL.Image, 'ANTIALIAS'):
    PIL.Image.ANTIALIAS = PIL.Image.Resampling.LANCZOS


import io
import numpy as np
from PIL import Image, ImageFilter

from moviepy.editor import ImageClip, CompositeVideoClip, ColorClip
from moviepy.video.fx import resize

from config.settings import (
    REEL_WIDTH,
    REEL_HEIGHT,
    REEL_FPS,
    REEL_KEN_BURNS_ENABLED,
    REEL_KEN_BURNS_ZOOM,
)
from utils.logger import get_logger

logger = get_logger("clip_renderer")


# ============================================================
# CONFIGURATION
# ============================================================

# Default target dimensions (9:16 portrait)
TARGET_WIDTH = REEL_WIDTH
TARGET_HEIGHT = REEL_HEIGHT
TARGET_ASPECT = TARGET_WIDTH / TARGET_HEIGHT  # 0.5625

# Ken Burns settings
ZOOM_MAX = REEL_KEN_BURNS_ZOOM  # e.g., 1.15 = 15% zoom
PAN_DISTANCE_RATIO = 0.10  # Pan up to 10% of image width/height

# Background blur for aspect-mismatch images
BACKGROUND_BLUR_RADIUS = 40

# Minimum clip duration
MIN_CLIP_DURATION = 1.0
DEFAULT_CLIP_DURATION = 10.0


# ============================================================
# IMAGE PREPARATION
# ============================================================

def _bytes_to_pil(image_bytes: bytes) -> Image.Image:
    """Convert image bytes to PIL Image (RGB mode)"""
    img = Image.open(io.BytesIO(image_bytes))

    # Convert RGBA/P/other modes to RGB
    if img.mode != 'RGB':
        if img.mode == 'RGBA':
            # White background for transparency
            bg = Image.new('RGB', img.size, (0, 0, 0))
            bg.paste(img, mask=img.split()[3])
            img = bg
        else:
            img = img.convert('RGB')

    return img


def _resize_for_ken_burns(img: Image.Image, target_w: int, target_h: int) -> Image.Image:
    """
    Resize image to be slightly larger than target for Ken Burns zoom.
    We need extra pixels around edges for zoom animation without black bars.

    Strategy:
    1. Scale to cover target with 15% extra
    2. Center crop to slightly larger than target
    """
    img_w, img_h = img.size
    img_aspect = img_w / img_h
    target_aspect = target_w / target_h

    # Scale factor for zoom room
    zoom_extra = ZOOM_MAX + 0.05  # 5% safety margin

    # Determine which dimension is limiting
    if img_aspect > target_aspect:
        # Image wider than target - scale to target height * zoom_extra
        new_h = int(target_h * zoom_extra)
        new_w = int(new_h * img_aspect)
    else:
        # Image taller than target - scale to target width * zoom_extra
        new_w = int(target_w * zoom_extra)
        new_h = int(new_w / img_aspect)

    # Ensure minimum size
    if new_w < target_w:
        new_w = int(target_w * zoom_extra)
        new_h = int(new_w / img_aspect)
    if new_h < target_h:
        new_h = int(target_h * zoom_extra)
        new_w = int(new_h * img_aspect)

    # Resize using LANCZOS for quality
    resized = img.resize((new_w, new_h), Image.LANCZOS)

    return resized


def _create_blurred_background(img: Image.Image, target_w: int, target_h: int) -> Image.Image:
    """
    Create blurred background from image for aspect ratio mismatch.
    Used when image doesn't perfectly fit 9:16.

    Method:
    1. Scale image to cover target
    2. Blur heavily
    3. Use as background layer
    """
    # Scale to cover target completely
    img_aspect = img.size[0] / img.size[1]
    target_aspect = target_w / target_h

    if img_aspect > target_aspect:
        # Image wider - fit height, crop width
        new_h = target_h
        new_w = int(new_h * img_aspect)
    else:
        # Image taller - fit width, crop height
        new_w = target_w
        new_h = int(new_w / img_aspect)

    bg = img.resize((new_w, new_h), Image.LANCZOS)

    # Center crop to target
    left = (new_w - target_w) // 2
    top = (new_h - target_h) // 2
    bg = bg.crop((left, top, left + target_w, top + target_h))

    # Heavy blur
    bg = bg.filter(ImageFilter.GaussianBlur(radius=BACKGROUND_BLUR_RADIUS))

    # Darken slightly for foreground visibility
    from PIL import ImageEnhance
    enhancer = ImageEnhance.Brightness(bg)
    bg = enhancer.enhance(0.6)  # 60% brightness

    return bg


def _fit_image_to_target(img: Image.Image, target_w: int, target_h: int) -> Image.Image:
    """
    Fit image into target dimensions (9:16 portrait).

    If image is square (1:1), we composite it centered
    over a blurred background of itself.

    Returns image exactly at target_w x target_h
    """
    img_aspect = img.size[0] / img.size[1]
    target_aspect = target_w / target_h

    # Check if aspect ratios roughly match
    aspect_diff = abs(img_aspect - target_aspect)

    if aspect_diff < 0.1:
        # Aspects match - simple resize
        return img.resize((target_w, target_h), Image.LANCZOS)

    # Aspects don't match - create blurred background + centered foreground
    logger.debug(f"Aspect mismatch: image {img_aspect:.2f} vs target {target_aspect:.2f}")

    # Background: blurred version filling frame
    background = _create_blurred_background(img, target_w, target_h)

    # Foreground: image scaled to fit within frame
    if img_aspect > target_aspect:
        # Image wider - fit to width
        fg_w = target_w
        fg_h = int(fg_w / img_aspect)
    else:
        # Image taller - fit to height
        fg_h = target_h
        fg_w = int(fg_h * img_aspect)

    foreground = img.resize((fg_w, fg_h), Image.LANCZOS)

    # Composite foreground on background (centered)
    fg_x = (target_w - fg_w) // 2
    fg_y = (target_h - fg_h) // 2

    background.paste(foreground, (fg_x, fg_y))

    return background


# ============================================================
# KEN BURNS EFFECTS
# ============================================================

def _apply_zoom_in(clip: ImageClip, duration: float, zoom_factor: float = ZOOM_MAX):
    """V4: Smooth ease-in-out zoom (not linear — more cinematic)"""
    import math

    def zoom_func(t):
        # Ease-in-out curve (smooth start and end)
        progress = t / duration
        eased = 0.5 * (1 - math.cos(progress * math.pi))  # Smooth S-curve
        current_zoom = 1.0 + (zoom_factor - 1.0) * eased
        return current_zoom

    return clip.resize(zoom_func)


def _apply_zoom_out(clip: ImageClip, duration: float, zoom_factor: float = ZOOM_MAX):
    """V4: Smooth ease-in-out zoom out"""
    import math

    def zoom_func(t):
        progress = t / duration
        eased = 0.5 * (1 - math.cos(progress * math.pi))
        current_zoom = zoom_factor - (zoom_factor - 1.0) * eased
        return current_zoom

    return clip.resize(zoom_func)


def _apply_pan_left(clip: ImageClip, duration: float, distance_ratio: float = PAN_DISTANCE_RATIO):
    """V4: Smooth pan left with ease curve"""
    import math
    w, h = clip.size
    clip = clip.resize(1.12)  # V4: Slightly more zoom for smoother pan
    pan_distance = int(w * distance_ratio)

    def position_func(t):
        progress = t / duration
        eased = 0.5 * (1 - math.cos(progress * math.pi))
        x_offset = pan_distance / 2 - (pan_distance * eased)
        return (x_offset, 'center')

    return clip.set_position(position_func)


def _apply_pan_right(clip: ImageClip, duration: float, distance_ratio: float = PAN_DISTANCE_RATIO):
    """V4: Smooth pan right with ease curve"""
    import math
    w, h = clip.size
    clip = clip.resize(1.12)
    pan_distance = int(w * distance_ratio)

    def position_func(t):
        progress = t / duration
        eased = 0.5 * (1 - math.cos(progress * math.pi))
        x_offset = -pan_distance / 2 + (pan_distance * eased)
        return (x_offset, 'center')

    return clip.set_position(position_func)


def _apply_static(clip: ImageClip, duration: float):
    """V4: Very subtle slow zoom (barely noticeable but adds life)"""
    import math

    def zoom_func(t):
        progress = t / duration
        # Super subtle: 1.0 → 1.03 (3% zoom over entire duration)
        eased = 0.5 * (1 - math.cos(progress * math.pi))
        return 1.0 + 0.03 * eased

    return clip.resize(zoom_func)


# ============================================================
# MAIN RENDER FUNCTION
# ============================================================

def render_clip(
    image_bytes: bytes,
    duration: float = DEFAULT_CLIP_DURATION,
    effect: str = "zoom_in",
    target_size: tuple = None,
    fps: int = None
):
    """
    Convert image bytes to video clip with Ken Burns effect

    Args:
        image_bytes: Image data (JPEG/PNG)
        duration: Clip duration in seconds
        effect: "zoom_in" | "zoom_out" | "pan_left" | "pan_right" | "static"
        target_size: (width, height) tuple, defaults to (1080, 1920)
        fps: Frames per second, defaults to REEL_FPS (30)

    Returns:
        MoviePy VideoClip object ready for concatenation
    """
    # Defaults
    if target_size is None:
        target_size = (TARGET_WIDTH, TARGET_HEIGHT)
    if fps is None:
        fps = REEL_FPS

    target_w, target_h = target_size

    # Validate duration
    if duration < MIN_CLIP_DURATION:
        logger.warning(f"⚠️  Duration too short ({duration}s), setting to {MIN_CLIP_DURATION}s")
        duration = MIN_CLIP_DURATION

    logger.info(
        f"🎬 Rendering clip: duration={duration}s, effect={effect}, "
        f"target={target_w}x{target_h}"
    )

    try:
        # Step 1: Load image as PIL
        pil_img = _bytes_to_pil(image_bytes)
        orig_w, orig_h = pil_img.size

        logger.debug(f"   Original image: {orig_w}x{orig_h}")

        # Step 2: Fit to target dimensions
        if REEL_KEN_BURNS_ENABLED and effect != "static":
            # For Ken Burns, we need larger image with zoom room
            fitted = _resize_for_ken_burns(pil_img, target_w, target_h)
        else:
            fitted = _fit_image_to_target(pil_img, target_w, target_h)

        fitted_w, fitted_h = fitted.size
        logger.debug(f"   Fitted image: {fitted_w}x{fitted_h}")

        # Step 3: Convert PIL to numpy for MoviePy
        img_array = np.array(fitted)

        # Step 4: Create ImageClip
        clip = ImageClip(img_array, duration=duration)

        # Step 5: Apply Ken Burns effect
        if REEL_KEN_BURNS_ENABLED:
            if effect == "zoom_in":
                clip = _apply_zoom_in(clip, duration)
            elif effect == "zoom_out":
                clip = _apply_zoom_out(clip, duration)
            elif effect == "pan_left":
                clip = _apply_pan_left(clip, duration)
            elif effect == "pan_right":
                clip = _apply_pan_right(clip, duration)
            else:  # static or unknown
                clip = _apply_static(clip, duration)
        else:
            # No Ken Burns - just fit and hold
            pass

        # Step 6: Composite over black background at exact target size
        # This ensures final output is exactly target_w x target_h
        bg = ColorClip(
            size=(target_w, target_h),
            color=(0, 0, 0),
            duration=duration
        )

        final_clip = CompositeVideoClip(
            [bg, clip.set_position('center')],
            size=(target_w, target_h)
        ).set_duration(duration)

        final_clip = final_clip.set_fps(fps)

        logger.info(f"✅ Clip rendered: {duration}s, {effect}")

        return final_clip

    except Exception as e:
        logger.error(f"❌ Clip render failed: {e}")
        raise


# ============================================================
# HELPER: RENDER MULTIPLE SCENES
# ============================================================

def render_all_scenes(scenes: list, target_size: tuple = None, fps: int = None) -> list:
    """
    Render all reel scenes to clips.

    Args:
        scenes: List of scene dicts (with image_bytes, duration_seconds, effect)
        target_size: (width, height) - defaults to reel size
        fps: Frame rate

    Returns:
        List of rendered VideoClip objects
    """
    clips = []
    failed_scenes = []

    logger.info(f"🎞️  Rendering {len(scenes)} scenes to clips...")

    for i, scene in enumerate(scenes, 1):
        scene_num = scene.get("scene_number", i)

        try:
            image_bytes = scene.get("image_bytes")
            if not image_bytes:
                logger.warning(f"⚠️  Scene {scene_num}: no image bytes, skipping")
                failed_scenes.append(scene_num)
                continue

            duration = scene.get("duration_seconds", DEFAULT_CLIP_DURATION)
            effect = scene.get("effect", "zoom_in")

            logger.info(f"   Scene {scene_num}: {effect}, {duration}s")

            clip = render_clip(
                image_bytes=image_bytes,
                duration=duration,
                effect=effect,
                target_size=target_size,
                fps=fps
            )

            clips.append(clip)

        except Exception as e:
            logger.error(f"❌ Scene {scene_num} render failed: {e}")
            failed_scenes.append(scene_num)

    if failed_scenes:
        logger.warning(f"⚠️  {len(failed_scenes)} scenes failed: {failed_scenes}")

    logger.info(f"✅ Rendered {len(clips)}/{len(scenes)} clips successfully")

    return clips


# ============================================================
# STANDALONE TESTING
# ============================================================

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("CLIP RENDERER - STANDALONE TEST")
    print("=" * 60 + "\n")

    # Create a test image
    from PIL import Image as PILImage, ImageDraw, ImageFont

    print("📷 Creating test image (1024x1024 with gradient)...")

    test_img = PILImage.new("RGB", (1024, 1024))
    pixels = test_img.load()

    # Sunset gradient
    for y in range(1024):
        for x in range(1024):
            r = int(255 * (y / 1024))
            g = int(150 * (1 - y / 1024))
            b = int(100 * (x / 1024))
            pixels[x, y] = (r, g, b)

    # Add sun circle
    draw = ImageDraw.Draw(test_img)
    draw.ellipse([362, 362, 662, 662], fill=(255, 220, 50))

    # Convert to bytes
    buf = io.BytesIO()
    test_img.save(buf, format='JPEG', quality=90)
    test_bytes = buf.getvalue()

    print(f"✅ Test image ready: {len(test_bytes):,} bytes\n")

    # Test all effects
    effects_to_test = ["zoom_in", "zoom_out", "pan_left", "pan_right", "static"]

    for effect in effects_to_test:
        print(f"\n🎬 Testing effect: {effect}")

        try:
            clip = render_clip(
                image_bytes=test_bytes,
                duration=3.0,  # Short for testing
                effect=effect
            )

            output_file = f"test_clip_{effect}.mp4"
            clip.write_videofile(
                output_file,
                fps=30,
                codec='libx264',
                audio=False,
                verbose=False,
                logger=None
            )
            print(f"✅ Saved: {output_file}")

            # Cleanup
            clip.close()

        except Exception as e:
            print(f"❌ Failed: {e}")

    print("\n" + "=" * 60)
    print("✅ Test complete!")
    print("=" * 60)
    print("\n💡 Play test clips:")
    for effect in effects_to_test:
        print(f"   start test_clip_{effect}.mp4")