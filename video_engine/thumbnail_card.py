"""
Branded Thumbnail / CTA Card Generator

This composes a 9:16 thumbnail/CTA card. The background can be an extra
AI-generated thumbnail image, while all important text is overlaid locally with
PIL so spellings/handles remain accurate.

Used as:
- Reel cover/thumbnail
- Short CTA card inside the final video to absorb small audio/video duration gaps

The card contains:
- Topic/category title
- Like / Share / Follow / Subscribe CTA
- Instagram / Facebook / YouTube handles at the bottom
"""
import io
import os
import textwrap
from pathlib import Path
from typing import Tuple

from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance

from config.settings import REEL_WIDTH, REEL_HEIGHT
from utils.logger import get_logger

logger = get_logger("thumbnail_card")


# ============================================================
# BRAND / STYLE CONFIG
# ============================================================

INSTAGRAM_HANDLE = os.getenv("BRAND_INSTAGRAM_HANDLE", "@sanatanii_soch")
FACEBOOK_HANDLE = os.getenv("BRAND_FACEBOOK_HANDLE", "सनातन सोच")
YOUTUBE_HANDLE = os.getenv("BRAND_YOUTUBE_HANDLE", "@sanatanii_soch")

CATEGORY_TITLES = {
    "krishna": "श्री कृष्ण की अद्भुत कथा",
    "shiva": "महादेव की दिव्य कथा",
    "hanuman": "हनुमान जी की प्रेरक कथा",
    "ganesha": "गणेश जी की शुभ कथा",
    "durga": "मां दुर्गा की शक्ति कथा",
    "ram": "श्री राम की अद्भुत कथा",
    "motivational": "जीवन बदलने वाली सीख",
    "spiritual_nature": "आध्यात्मिक शांति की सीख",
    "temple": "मंदिर की दिव्य कथा",
    "daily_wisdom": "आज की आध्यात्मिक सीख",
}

CATEGORY_EMOJIS = {
    "krishna": "🦚",
    "shiva": "🕉️",
    "hanuman": "🚩",
    "ganesha": "🐘",
    "durga": "🌺",
    "ram": "🏹",
    "motivational": "💪",
    "spiritual_nature": "🙏",
    "temple": "🛕",
    "daily_wisdom": "✨",
}


# ============================================================
# HELPERS
# ============================================================

def _font(size: int, bold: bool = True):
    candidates = []
    if bold:
        candidates.extend([
            "fonts/NotoSansDevanagari-Bold.ttf",
            "assets/fonts/NotoSansDevanagari-Bold.ttf",
            "C:/Windows/Fonts/NirmalaB.ttf",
            "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Bold.ttf",
        ])
    candidates.extend([
        "fonts/NotoSansDevanagari-Regular.ttf",
        "assets/fonts/NotoSansDevanagari-Regular.ttf",
        "C:/Windows/Fonts/Nirmala.ttf",
        "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Regular.ttf",
    ])

    for path in candidates:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue

    return ImageFont.load_default()


def _text_size(draw: ImageDraw.ImageDraw, text: str, font) -> Tuple[int, int]:
    try:
        bbox = draw.textbbox((0, 0), text, font=font)
        return bbox[2] - bbox[0], bbox[3] - bbox[1]
    except Exception:
        return draw.textsize(text, font=font)


def _wrap_text(draw: ImageDraw.ImageDraw, text: str, font, max_width: int, max_lines: int = 3) -> list:
    """Pixel-width based text wrap, works better for Hindi than fixed chars."""
    text = " ".join((text or "").split())
    if not text:
        return []

    words = text.split()
    lines = []
    current = ""

    for word in words:
        test = f"{current} {word}".strip()
        w, _ = _text_size(draw, test, font)
        if w <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = word
            if len(lines) >= max_lines:
                break

    if current and len(lines) < max_lines:
        lines.append(current)

    # If the last line is still too long, hard wrap as fallback.
    if len(lines) == 1:
        w, _ = _text_size(draw, lines[0], font)
        if w > max_width:
            lines = textwrap.wrap(text, width=18)[:max_lines]

    return lines[:max_lines]


def _draw_centered_text(
    draw: ImageDraw.ImageDraw,
    lines: list,
    font,
    y: int,
    fill=(255, 232, 150, 255),
    stroke_fill=(35, 18, 0, 255),
    stroke_width: int = 3,
    line_gap: int = 16,
):
    for line in lines:
        w, h = _text_size(draw, line, font)
        x = (REEL_WIDTH - w) // 2
        draw.text(
            (x, y),
            line,
            font=font,
            fill=fill,
            stroke_width=stroke_width,
            stroke_fill=stroke_fill,
        )
        y += h + line_gap
    return y


def _topic_title(topic: str, category: str) -> str:
    # Prefer category-specific Hindi title. Raw English topics look weak on cover.
    title = CATEGORY_TITLES.get(category, "सनातन की दिव्य कथा")

    # If topic is already Hindi, use a short first phrase.
    hindi_chars = ''.join(c for c in (topic or "") if '\u0900' <= c <= '\u097F' or c == ' ').strip()
    if len(hindi_chars.split()) >= 3:
        return ' '.join(hindi_chars.split()[:7])

    return title


def _fit_background_from_bytes(background_bytes: bytes, width: int, height: int) -> Image.Image:
    """Load AI-generated background and fit/crop it to 9:16."""
    bg = Image.open(io.BytesIO(background_bytes))
    if bg.mode != "RGB":
        bg = bg.convert("RGB")

    bg_w, bg_h = bg.size
    bg_aspect = bg_w / bg_h
    target_aspect = width / height

    if bg_aspect > target_aspect:
        new_h = height
        new_w = int(new_h * bg_aspect)
    else:
        new_w = width
        new_h = int(new_w / bg_aspect)

    bg = bg.resize((new_w, new_h), Image.LANCZOS)
    left = max(0, (new_w - width) // 2)
    top = max(0, (new_h - height) // 2)
    bg = bg.crop((left, top, left + width, top + height))

    # Darken and slightly blur behind CTA text for readability.
    bg = ImageEnhance.Brightness(bg).enhance(0.62)
    bg = ImageEnhance.Contrast(bg).enhance(1.08)
    return bg.convert("RGBA")


def _gradient_background(width: int, height: int) -> Image.Image:
    """Fallback warm spiritual background when AI image fails."""
    img = Image.new("RGB", (width, height), (40, 12, 4))
    draw = ImageDraw.Draw(img)

    for y in range(height):
        ratio = y / height
        r = int(30 + 95 * (1 - ratio) + 18 * ratio)
        g = int(10 + 58 * (1 - ratio) + 10 * ratio)
        b = int(8 + 12 * (1 - ratio) + 38 * ratio)
        draw.line([(0, y), (width, y)], fill=(r, g, b))

    return img.convert("RGBA")


# ============================================================
# PUBLIC API
# ============================================================

def generate_thumbnail_card(
    topic: str,
    category: str,
    session_id: str = "",
    hook_text: str = "",
    output_dir: str = "logs/thumbnails",
    background_bytes: bytes = None,
) -> dict:
    """
    Generate a 1080x1920 branded thumbnail/CTA image locally.

    Returns:
        {
            "bytes": jpg bytes,
            "path": local path,
            "title": title used,
        }
    """
    width, height = REEL_WIDTH, REEL_HEIGHT
    title = _topic_title(hook_text or topic, category)
    emoji = CATEGORY_EMOJIS.get(category, "🙏")

    # Base background: extra AI-generated thumbnail image if available,
    # otherwise local gradient fallback.
    if background_bytes:
        try:
            img = _fit_background_from_bytes(background_bytes, width, height)
            logger.info("✅ Using AI-generated thumbnail background")
        except Exception as e:
            logger.warning(f"⚠️  AI thumbnail background unusable, fallback gradient: {e}")
            img = _gradient_background(width, height)
    else:
        img = _gradient_background(width, height)

    # Readability veil.
    veil = Image.new("RGBA", (width, height), (0, 0, 0, 85))
    img = Image.alpha_composite(img, veil)

    # Soft radial glow circles.
    glow = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    gd.ellipse((-260, -220, 620, 660), fill=(255, 145, 30, 85))
    gd.ellipse((500, 120, 1300, 940), fill=(255, 215, 80, 45))
    gd.ellipse((110, 960, 970, 1820), fill=(255, 95, 0, 40))
    glow = glow.filter(ImageFilter.GaussianBlur(55))
    img = Image.alpha_composite(img.convert("RGBA"), glow)
    draw = ImageDraw.Draw(img)

    # Fonts.
    font_brand = _font(42, bold=True)
    font_title = _font(88, bold=True)
    font_badge = _font(48, bold=True)
    font_cta = _font(62, bold=True)
    font_small = _font(36, bold=True)
    font_handles = _font(34, bold=True)

    # Top brand strip.
    draw.rounded_rectangle((60, 58, width - 60, 138), radius=38, fill=(0, 0, 0, 105), outline=(255, 210, 90, 170), width=2)
    brand_line = "सनातनी सोच  •  Daily Divine Stories"
    bw, bh = _text_size(draw, brand_line, font_brand)
    draw.text(((width - bw) // 2, 75), brand_line, font=font_brand, fill=(255, 230, 170, 255))

    # Big emoji / category marker.
    draw.text((width // 2 - 55, 210), emoji, font=_font(105, bold=True), fill=(255, 255, 255, 255))

    # Title.
    title_lines = _wrap_text(draw, title, font_title, max_width=940, max_lines=3)
    y = _draw_centered_text(
        draw,
        title_lines,
        font_title,
        365,
        fill=(255, 222, 82, 255),
        stroke_fill=(28, 8, 0, 255),
        stroke_width=4,
        line_gap=14,
    )

    # Watch now badge.
    badge_text = "▶ पूरी कहानी देखें"
    bw, bh = _text_size(draw, badge_text, font_badge)
    badge_x = (width - bw - 90) // 2
    badge_y = max(y + 45, 700)
    draw.rounded_rectangle((badge_x, badge_y, badge_x + bw + 90, badge_y + bh + 34), radius=36, fill=(255, 102, 0, 230))
    draw.text((badge_x + 45, badge_y + 14), badge_text, font=font_badge, fill=(255, 255, 255, 255))

    # CTA panel.
    panel_y = 1010
    draw.rounded_rectangle((70, panel_y, width - 70, panel_y + 360), radius=44, fill=(0, 0, 0, 125), outline=(255, 200, 90, 150), width=2)

    ctas = [
        "❤️ LIKE",
        "🔄 SHARE",
        "➕ FOLLOW",
        "🔔 SUBSCRIBE",
    ]
    x_positions = [120, 565, 120, 565]
    y_positions = [panel_y + 62, panel_y + 62, panel_y + 205, panel_y + 205]
    for text, x, yy in zip(ctas, x_positions, y_positions):
        draw.text((x, yy), text, font=font_cta, fill=(255, 245, 225, 255), stroke_width=2, stroke_fill=(0, 0, 0, 220))

    # Bottom social handles.
    bottom_y = 1530
    draw.rounded_rectangle((60, bottom_y, width - 60, height - 72), radius=38, fill=(0, 0, 0, 135), outline=(255, 215, 90, 120), width=2)
    draw.text((105, bottom_y + 48), "📸 Instagram", font=font_small, fill=(255, 218, 120, 255))
    draw.text((430, bottom_y + 48), INSTAGRAM_HANDLE, font=font_handles, fill=(255, 255, 255, 245))

    draw.text((105, bottom_y + 148), "📘 Facebook", font=font_small, fill=(255, 218, 120, 255))
    draw.text((430, bottom_y + 148), FACEBOOK_HANDLE, font=font_handles, fill=(255, 255, 255, 245))

    draw.text((105, bottom_y + 248), "▶ YouTube", font=font_small, fill=(255, 218, 120, 255))
    draw.text((430, bottom_y + 248), YOUTUBE_HANDLE, font=font_handles, fill=(255, 255, 255, 245))

    # Export.
    final = img.convert("RGB")
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    file_path = output_path / f"thumb_card_{session_id or 'reel'}.jpg"

    buf = io.BytesIO()
    final.save(buf, format="JPEG", quality=92, optimize=True)
    data = buf.getvalue()

    with open(file_path, "wb") as f:
        f.write(data)

    logger.info(f"✅ Branded thumbnail card generated: {len(data):,} bytes")
    logger.info(f"   📁 Path : {file_path}")
    logger.info(f"   📝 Title: {title}")

    return {
        "bytes": data,
        "path": str(file_path),
        "title": title,
    }
