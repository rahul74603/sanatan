"""
Branded Thumbnail / CTA Card Generator (Emoji-Free, Brand-Safe)

This composes a 9:16 (1080x1920) branded thumbnail/CTA card. The background is
an extra AI-generated image (9:16), while every visible glyph is drawn locally
with PIL using NotoSansDevanagari so nothing renders as a tofu / black-box on
GitHub-Actions / Linux servers.

Design principles (brand-safe):
- NO emoji glyphs (❤️ 🔄 ➕ 🔔 📸 📘 ▶ 🙏 etc). Icons are drawn as PIL shapes.
- Only safe glyphs: Latin A-Z / 0-9, Hindi (Devanagari), '@', '_', '.', space.
- Title is placed in the Instagram square-crop safe zone (visible when IG
  grid crops the 9:16 image to 1:1). Roughly the center 1080x1080 band, i.e.
  y ∈ [420, 1500]. So the title lives around y = 700..1100.
- Dark translucent panels behind every text row for readability.
- Uses NotoSansDevanagari fonts if available; falls back to system Devanagari.

Used as:
- Reel cover / thumbnail (IG cover_url, YouTube custom thumbnail)
- Short CTA end-card scene inside the final reel video
"""
import io
import os
import textwrap
from pathlib import Path
from typing import Tuple, List

from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance

from config.settings import REEL_WIDTH, REEL_HEIGHT
from utils.logger import get_logger

logger = get_logger("thumbnail_card")


# ============================================================
# BRAND / STYLE CONFIG
# ============================================================

INSTAGRAM_HANDLE = os.getenv("BRAND_INSTAGRAM_HANDLE", "@sanatanii_soch")
FACEBOOK_HANDLE  = os.getenv("BRAND_FACEBOOK_HANDLE",  "सनातन सोच")
YOUTUBE_HANDLE   = os.getenv("BRAND_YOUTUBE_HANDLE",   "@Official_Sanatan_Soch")

CATEGORY_TITLES = {
    "krishna":         "श्री कृष्ण की अद्भुत कथा",
    "shiva":           "महादेव की दिव्य कथा",
    "hanuman":         "हनुमान जी की प्रेरक कथा",
    "ganesha":         "गणेश जी की शुभ कथा",
    "durga":           "मां दुर्गा की शक्ति कथा",
    "ram":             "श्री राम की अद्भुत कथा",
    "motivational":    "जीवन बदलने वाली सीख",
    "spiritual_nature":"आध्यात्मिक शांति की सीख",
    "temple":          "मंदिर की दिव्य कथा",
    "daily_wisdom":    "आज की आध्यात्मिक सीख",
}


# ============================================================
# FONT / TEXT HELPERS
# ============================================================

def _font_devanagari(size: int, bold: bool = True):
    candidates = []
    if bold:
        candidates.extend([
            "fonts/NotoSansDevanagari-Bold.ttf",
            "assets/fonts/NotoSansDevanagari-Bold.ttf",
            "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Bold.ttf",
            "C:/Windows/Fonts/NirmalaB.ttf",
        ])
    candidates.extend([
        "fonts/NotoSansDevanagari-Regular.ttf",
        "assets/fonts/NotoSansDevanagari-Regular.ttf",
        "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Regular.ttf",
        "C:/Windows/Fonts/Nirmala.ttf",
    ])
    for path in candidates:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    return ImageFont.load_default()


def _font_latin(size: int, bold: bool = True):
    """Latin (A-Z, digits, @, _) capable font. NotoSansDevanagari doesn't
    include Latin glyphs — using it for English text produces tofu boxes."""
    candidates = []
    if bold:
        candidates.extend([
            "fonts/DejaVuSans-Bold.ttf",
            "assets/fonts/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf",
            "fonts/NotoSans-Bold.ttf",
            "assets/fonts/NotoSans-Bold.ttf",
            "/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
            "C:/Windows/Fonts/arialbd.ttf",
        ])
    candidates.extend([
        "fonts/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "fonts/NotoSans-Regular.ttf",
        "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "C:/Windows/Fonts/arial.ttf",
    ])
    for path in candidates:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    return ImageFont.load_default()


def _has_devanagari(text: str) -> bool:
    return any('\u0900' <= c <= '\u097F' for c in (text or ""))


def _font(size: int, bold: bool = True, text: str = ""):
    """Backward-compatible font picker.

    Picks Devanagari font when the given text contains any Devanagari
    codepoint, otherwise a Latin-capable font. Passing no text keeps the
    previous Devanagari default (safe for legacy callers).
    """
    if text and not _has_devanagari(text):
        return _font_latin(size, bold=bold)
    return _font_devanagari(size, bold=bold)


def _text_size(draw: ImageDraw.ImageDraw, text: str, font) -> Tuple[int, int]:
    try:
        bbox = draw.textbbox((0, 0), text, font=font)
        return bbox[2] - bbox[0], bbox[3] - bbox[1]
    except Exception:
        try:
            return draw.textsize(text, font=font)
        except Exception:
            return (len(text) * (font.size if hasattr(font, "size") else 12), 20)


def _wrap_text(draw: ImageDraw.ImageDraw, text: str, font, max_width: int, max_lines: int = 3) -> List[str]:
    """Pixel-width based wrap. Works better for Hindi than char-count wrap."""
    text = " ".join((text or "").split())
    if not text:
        return []

    words = text.split()
    lines: List[str] = []
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

    # Last-resort hard wrap.
    if len(lines) == 1:
        w, _ = _text_size(draw, lines[0], font)
        if w > max_width:
            lines = textwrap.wrap(text, width=18)[:max_lines]

    return lines[:max_lines]


def _draw_centered_text(
    draw: ImageDraw.ImageDraw,
    lines: List[str],
    font,
    y: int,
    fill=(255, 232, 150, 255),
    stroke_fill=(20, 6, 0, 255),
    stroke_width: int = 3,
    line_gap: int = 16,
    x_center: int = None,
    width: int = REEL_WIDTH,
) -> int:
    if x_center is None:
        x_center = width // 2
    for line in lines:
        w, h = _text_size(draw, line, font)
        x = x_center - w // 2
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
    """Choose a strong Hindi title, prefer the topic if it is already Hindi."""
    title = CATEGORY_TITLES.get(category, "सनातन की दिव्य कथा")

    hindi_chars = ''.join(
        c for c in (topic or "")
        if '\u0900' <= c <= '\u097F' or c == ' '
    ).strip()
    if len(hindi_chars.split()) >= 3:
        return ' '.join(hindi_chars.split()[:7])

    return title


# ============================================================
# BACKGROUND HELPERS
# ============================================================

def _fit_background_from_bytes(background_bytes: bytes, width: int, height: int) -> Image.Image:
    """Load AI thumbnail background and center-crop to 9:16."""
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
    top  = max(0, (new_h - height) // 2)
    bg = bg.crop((left, top, left + width, top + height))

    # Slightly darker + a touch more contrast so text stays legible.
    bg = ImageEnhance.Brightness(bg).enhance(0.60)
    bg = ImageEnhance.Contrast(bg).enhance(1.10)
    return bg.convert("RGBA")


def _gradient_background(width: int, height: int) -> Image.Image:
    """Warm devotional fallback background (used when AI image missing)."""
    img = Image.new("RGB", (width, height), (40, 12, 4))
    draw = ImageDraw.Draw(img)

    for y in range(height):
        ratio = y / height
        r = int(30 + 95 * (1 - ratio) + 18 * ratio)
        g = int(10 + 58 * (1 - ratio) + 10 * ratio)
        b = int(8  + 12 * (1 - ratio) + 38 * ratio)
        draw.line([(0, y), (width, y)], fill=(r, g, b))

    return img.convert("RGBA")


# ============================================================
# PIL-DRAWN ICONS (no font glyphs)
# ============================================================

def _draw_play_triangle(draw: ImageDraw.ImageDraw, cx: int, cy: int, size: int,
                        fill=(255, 255, 255, 255), stroke=(0, 0, 0, 220)):
    """Draw a right-pointing play triangle centered at (cx, cy)."""
    h = size
    w = int(size * 0.86)
    pts = [
        (cx - w // 2, cy - h // 2),
        (cx - w // 2, cy + h // 2),
        (cx + w // 2, cy),
    ]
    draw.polygon(pts, fill=fill, outline=stroke)


def _draw_dot(draw: ImageDraw.ImageDraw, cx: int, cy: int, r: int, fill):
    draw.ellipse((cx - r, cy - r, cx + r, cy + r), fill=fill)


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

    Args:
        topic:            Reel topic (Hindi/English/Hinglish)
        category:         Category key (krishna, shiva, ram, ...)
        session_id:       For output filename
        hook_text:        Optional pre-computed hook (Hindi)
        output_dir:       Where to save the JPG
        background_bytes: Optional AI-generated 9:16 background image bytes

    Returns:
        {"bytes": jpg_bytes, "path": local_path, "title": title_used}
    """
    width, height = REEL_WIDTH, REEL_HEIGHT
    title = _topic_title(hook_text or topic, category)

    # ─── Background ────────────────────────────────────────
    if background_bytes:
        try:
            img = _fit_background_from_bytes(background_bytes, width, height)
            logger.info("✅ Using AI-generated thumbnail background")
        except Exception as e:
            logger.warning(f"⚠️  AI thumbnail background unusable, fallback gradient: {e}")
            img = _gradient_background(width, height)
    else:
        img = _gradient_background(width, height)

    # Global readability veil (dark).
    veil = Image.new("RGBA", (width, height), (0, 0, 0, 90))
    img = Image.alpha_composite(img, veil)

    # Soft warm glow accents.
    glow = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    gd.ellipse((-260, -220, 620, 660),   fill=(255, 145, 30, 85))
    gd.ellipse((500, 120, 1300, 940),    fill=(255, 215, 80, 45))
    gd.ellipse((110, 960, 970, 1820),    fill=(255, 95,  0, 40))
    glow = glow.filter(ImageFilter.GaussianBlur(55))
    img = Image.alpha_composite(img.convert("RGBA"), glow)
    draw = ImageDraw.Draw(img)

    # ─── Fonts ─────────────────────────────────────────────
    font_brand_hi   = _font_devanagari(48, bold=True)
    font_brand_en   = _font_latin(36,     bold=True)
    font_title      = _font_devanagari(92, bold=True)
    font_badge      = _font_devanagari(52, bold=True)
    font_cta        = _font_latin(46,     bold=True)  # LIKE / SHARE / FOLLOW / SUBSCRIBE
    font_platform   = _font_latin(38,     bold=True)  # INSTAGRAM / FACEBOOK / YOUTUBE
    font_handle_lat = _font_latin(36,     bold=True)  # @sanatanii_soch etc
    font_handle_hi  = _font_devanagari(36, bold=True) # सनातन सोच

    # ─── Top brand strip (Devanagari + Latin, mixed fonts) ─
    draw.rounded_rectangle(
        (60, 58, width - 60, 148),
        radius=40,
        fill=(0, 0, 0, 140),
        outline=(255, 210, 90, 180),
        width=2,
    )
    brand_hi = "सनातनी सोच"
    brand_sep = "  |  "
    brand_en = "Daily Divine Stories"

    hi_w, hi_h = _text_size(draw, brand_hi, font_brand_hi)
    sep_w, _   = _text_size(draw, brand_sep, font_brand_en)
    en_w, en_h = _text_size(draw, brand_en, font_brand_en)
    total_w    = hi_w + sep_w + en_w
    x0 = (width - total_w) // 2
    y_hi = 68
    y_en = 76  # slightly lower for optical alignment

    draw.text(
        (x0, y_hi),
        brand_hi,
        font=font_brand_hi,
        fill=(255, 230, 170, 255),
        stroke_width=2,
        stroke_fill=(30, 12, 0, 220),
    )
    draw.text(
        (x0 + hi_w, y_en),
        brand_sep,
        font=font_brand_en,
        fill=(255, 210, 120, 255),
        stroke_width=2,
        stroke_fill=(30, 12, 0, 220),
    )
    draw.text(
        (x0 + hi_w + sep_w, y_en),
        brand_en,
        font=font_brand_en,
        fill=(255, 230, 170, 255),
        stroke_width=2,
        stroke_fill=(30, 12, 0, 220),
    )

    # ─── Title (safe zone for Instagram 1:1 grid crop) ─────
    # IG crops the middle 1080x1080 of 1080x1920 → y ∈ [420, 1500] is visible.
    # Place title around y=560..1050 so it never gets cut top/bottom.
    title_lines = _wrap_text(draw, title, font_title, max_width=940, max_lines=3)

    # Title backdrop panel — dark translucent for high contrast.
    if title_lines:
        panel_top    = 540
        line_h_est   = font_title.size + 22
        panel_height = min(3, len(title_lines)) * line_h_est + 60
        draw.rounded_rectangle(
            (60, panel_top, width - 60, panel_top + panel_height),
            radius=42,
            fill=(0, 0, 0, 160),
            outline=(255, 210, 90, 150),
            width=2,
        )
        _draw_centered_text(
            draw,
            title_lines,
            font_title,
            panel_top + 30,
            fill=(255, 222, 82, 255),
            stroke_fill=(24, 8, 0, 255),
            stroke_width=4,
            line_gap=12,
        )

    # ─── "पूरी कहानी देखें" badge with PIL play triangle ──
    badge_text = "पूरी कहानी देखें"
    bw, bh = _text_size(draw, badge_text, font_badge)
    triangle_size = 46
    pad_x_left  = 40 + triangle_size + 24   # left padding + triangle + gap
    pad_x_right = 44
    badge_w = bw + pad_x_left + pad_x_right
    badge_h = bh + 40
    badge_x = (width - badge_w) // 2
    badge_y = 1110

    draw.rounded_rectangle(
        (badge_x, badge_y, badge_x + badge_w, badge_y + badge_h),
        radius=badge_h // 2,
        fill=(255, 102, 0, 235),
        outline=(255, 220, 140, 220),
        width=2,
    )
    _draw_play_triangle(
        draw,
        cx=badge_x + 40 + triangle_size // 2,
        cy=badge_y + badge_h // 2,
        size=triangle_size,
        fill=(255, 255, 255, 255),
        stroke=(80, 30, 0, 255),
    )
    draw.text(
        (badge_x + pad_x_left, badge_y + 18),
        badge_text,
        font=font_badge,
        fill=(255, 255, 255, 255),
        stroke_width=2,
        stroke_fill=(80, 30, 0, 220),
    )

    # ─── CTA row: LIKE / SHARE / FOLLOW / SUBSCRIBE ────────
    cta_panel_top    = 1230
    cta_panel_bottom = 1400
    draw.rounded_rectangle(
        (60, cta_panel_top, width - 60, cta_panel_bottom),
        radius=42,
        fill=(0, 0, 0, 155),
        outline=(255, 200, 90, 160),
        width=2,
    )

    ctas = ["LIKE", "SHARE", "FOLLOW", "SUBSCRIBE"]
    # Measure each label, then distribute across the panel with gaps between.
    label_sizes = [_text_size(draw, l, font_cta) for l in ctas]
    labels_total_w = sum(w for w, _ in label_sizes)
    dot_r  = 8
    gap_dot_text = 12         # gap between dot and its label
    dot_slot = dot_r * 2 + gap_dot_text  # width taken by dot+gap for one item

    panel_inner_left  = 90
    panel_inner_right = width - 90
    panel_inner_w     = panel_inner_right - panel_inner_left
    # 4 items: 4 dot-slots + 4 labels + 3 gaps between items
    n_items = len(ctas)
    inter_gap = max(
        14,
        (panel_inner_w - labels_total_w - dot_slot * n_items) // (n_items - 1),
    )

    row_y = cta_panel_top + (cta_panel_bottom - cta_panel_top) // 2
    x_cursor = panel_inner_left
    for label, (tw, th) in zip(ctas, label_sizes):
        # Dot
        _draw_dot(draw, x_cursor + dot_r, row_y, dot_r, fill=(255, 200, 80, 255))
        # Label
        draw.text(
            (x_cursor + dot_slot, row_y - th // 2 - 2),
            label,
            font=font_cta,
            fill=(255, 245, 225, 255),
            stroke_width=2,
            stroke_fill=(0, 0, 0, 230),
        )
        x_cursor += dot_slot + tw + inter_gap

    # ─── Bottom social handles panel ───────────────────────
    bottom_y = 1470
    draw.rounded_rectangle(
        (60, bottom_y, width - 60, height - 72),
        radius=42,
        fill=(0, 0, 0, 165),
        outline=(255, 215, 90, 140),
        width=2,
    )

    rows = [
        ("INSTAGRAM", INSTAGRAM_HANDLE),
        ("FACEBOOK",  FACEBOOK_HANDLE),
        ("YOUTUBE",   YOUTUBE_HANDLE),
    ]
    row_gap = 108
    left_label_x  = 110
    handle_x      = 470
    row_start_y   = bottom_y + 42

    for i, (platform, handle) in enumerate(rows):
        y = row_start_y + i * row_gap

        # Small filled bullet indicator
        _draw_dot(draw, left_label_x - 30, y + 22, 10, fill=(255, 200, 80, 255))

        draw.text(
            (left_label_x, y),
            platform,
            font=font_platform,
            fill=(255, 218, 120, 255),
            stroke_width=2,
            stroke_fill=(0, 0, 0, 220),
        )
        handle_font = font_handle_hi if _has_devanagari(handle) else font_handle_lat
        draw.text(
            (handle_x, y + 2),
            handle,
            font=handle_font,
            fill=(255, 255, 255, 245),
            stroke_width=2,
            stroke_fill=(0, 0, 0, 220),
        )

    # ─── Export ────────────────────────────────────────────
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
        "path":  str(file_path),
        "title": title,
    }
