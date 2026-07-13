"""
Carousel Engine - Story-based 5-slide Instagram Carousel

Updates:
- ✅ Hindi titles + descriptions (Devanagari)
- ✅ Strong negative prompt (no text in images)
- ✅ Instagram-compatible JPEG (2207032 error fix)
- ✅ Informative + engaging caption
- ✅ Recovery support
"""
import json
import time
import textwrap
from io import BytesIO
from pathlib import Path
from typing import Optional

import google.generativeai as genai
from PIL import Image, ImageDraw, ImageFont

from config.settings import GEMINI_API_KEY, GEMINI_MODEL
from utils.logger import get_logger
from utils.vertex_ai import generate_image_vertex
from core.recovery_manager import save_checkpoint

logger = get_logger("carousel_engine")

genai.configure(api_key=GEMINI_API_KEY)


# ============================================================
# CONSTANTS
# ============================================================

SLIDE_SIZE = (1080, 1080)

SLIDE_TYPES = ["hook", "setup", "climax", "lesson", "cta"]

SLIDE_TYPE_LABELS = {
    "hook":    "🔥",
    "setup":   "📖",
    "climax":  "⚡",
    "lesson":  "💡",
    "cta":     "🙏",
}

BRAND_SAFFRON   = (255, 153, 51)
BRAND_GOLD      = (255, 215, 0)
BRAND_WHITE     = (255, 255, 255)
BRAND_BLACK     = (0, 0, 0)
BRAND_DARK      = (15, 15, 25)
OVERLAY_COLOR   = (0, 0, 0, 180)
HEADER_COLOR    = (20, 20, 20, 230)
FOOTER_COLOR    = (20, 20, 20, 210)

HEADER_FONT_SIZE  = 32
TITLE_FONT_SIZE   = 52
DESC_FONT_SIZE    = 34
FOOTER_FONT_SIZE  = 28
COUNTER_FONT_SIZE = 26

HEADER_HEIGHT   = 80
FOOTER_HEIGHT   = 70
GRADIENT_HEIGHT = 380

FONT_PATHS = {
    "bold": [
        # ✅ Windows Hindi (Nirmala) - Priority #1 (WORKS!)
        "C:/Windows/Fonts/NirmalaB.ttf",        # Nirmala Bold
        "C:/Windows/Fonts/Nirmala.ttf",         # Nirmala Regular (fallback)
        # Linux/Cloud fallbacks
        "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Bold.ttf",
        "/usr/share/fonts/truetype/lohit-devanagari/Lohit-Devanagari.ttf",
        # Local fallback (if properly downloaded)
        "fonts/NotoSansDevanagari-Bold.ttf",
        # Last resort (English only - Hindi will show boxes)
        "C:/Windows/Fonts/arialbd.ttf",
    ],
    "regular": [
        # ✅ Windows Hindi (Nirmala) - Priority #1 (WORKS!)
        "C:/Windows/Fonts/Nirmala.ttf",
        # Linux/Cloud fallbacks
        "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Regular.ttf",
        "/usr/share/fonts/truetype/lohit-devanagari/Lohit-Devanagari.ttf",
        # Local fallback
        "fonts/NotoSansDevanagari-Regular.ttf",
        # Last resort
        "C:/Windows/Fonts/arial.ttf",
    ]
}

HANDLE = "@sanatanii_soch"
PAGE_NAME = "SANATAN SOCH"


# ============================================================
# FONT LOADING
# ============================================================

def _load_font(style: str = "bold", size: int = 40) -> ImageFont.FreeTypeFont:
    """Font load करो — Hindi (Devanagari) support के साथ"""
    paths = FONT_PATHS.get(style, FONT_PATHS["regular"])
    
    for path in paths:
        try:
            if Path(path).exists():
                font = ImageFont.truetype(path, size)
                # ✅ Debug: पहली बार बताओ कौन सा font use हुआ
                if not hasattr(_load_font, '_logged_fonts'):
                    _load_font._logged_fonts = set()
                if path not in _load_font._logged_fonts:
                    logger.info(f"🔤 Font loaded ({style}): {path}")
                    _load_font._logged_fonts.add(path)
                return font
        except Exception as e:
            logger.warning(f"   Font failed: {path} → {e}")
            continue
    
    logger.error(f"❌ कोई Hindi font नहीं मिला! Default use कर रहे हैं (box दिखेंगे)")
    logger.error(f"   💡 Fix: fonts/NotoSansDevanagari-Bold.ttf download करें")
    return ImageFont.load_default()


# ============================================================
# 🆕 GEMINI SLIDE STRUCTURE — HINDI TITLES + DESC
# ============================================================

def generate_slide_structure(topic: str, category: str) -> list:
    """Gemini से 5-slide story structure — Hindi में!"""
    logger.info(f"🧠 स्लाइड का ढांचा बना रहे हैं: {topic[:60]}")

    prompt = f"""
You are a viral Instagram content creator for a spiritual Hindu page "Sanatan Soch".

Create a 5-slide Instagram Carousel story about this topic:
TOPIC: {topic}
CATEGORY: {category}

⚠️ CRITICAL LANGUAGE RULES:
- title: MUST be in HINDI (Devanagari script) — जैसे "क्या आप जानते हैं?"
- description: MUST be in HINDI (Devanagari script)
- image_prompt: MUST be in ENGLISH (for AI image generator)
- NO English text in title or description
- Use pure Hindi with occasional Sanskrit words

Each slide must have:
1. title: Short punchy HINDI (max 6 words in Devanagari)
2. description: 2 lines HINDI (max 15 words, engaging + informative)
3. image_prompt: DETAILED ENGLISH prompt (50-80 words)

SLIDE STRUCTURE:
- Slide 1 (hook): चौंकाने वाला सवाल या तथ्य - user को रोकने के लिए
- Slide 2 (setup): कहानी की शुरुआत, context
- Slide 3 (climax): मुख्य घटना, चरम पल - सबसे powerful moment
- Slide 4 (lesson): आध्यात्मिक सीख जो जीवन में काम आए
- Slide 5 (cta): शक्तिशाली निष्कर्ष + "Save & Share" appeal

IMAGE PROMPT RULES (ENGLISH ONLY):
⚠️ CRITICAL: Add "NO TEXT, NO WORDS, NO LETTERS, NO WRITING, NO SIGNS" 
- Always mention deity/subject clearly
- Include: divine light, detailed, cinematic, 8k, spiritual art
- Style: oil painting meets photorealism
- Specific visual scene

EXAMPLE HINDI TITLES:
- "क्या आप जानते हैं?"
- "यह रहस्य जानिए"
- "एक चमत्कार हुआ"
- "जीवन का सत्य"
- "अभी शेयर करें 🙏"
- "शिव का यह रूप"
- "कृष्ण की सीख"

EXAMPLE HINDI DESCRIPTIONS:
- "एक ऐसी कहानी जो आपकी सोच बदल देगी"
- "भगवान का यह रूप देखकर सब हैरान थे"
- "जीवन में कभी हार मत मानिए"
- "यह ज्ञान आपकी आत्मा को छू लेगा"

Return ONLY valid JSON array, no extra text:
[
  {{
    "slide_number": 1,
    "slide_type": "hook",
    "title": "HINDI TITLE IN DEVANAGARI",
    "description": "HINDI DESCRIPTION IN DEVANAGARI",
    "image_prompt": "ENGLISH IMAGE PROMPT - NO TEXT NO WORDS NO LETTERS NO WRITING"
  }},
  {{
    "slide_number": 2,
    "slide_type": "setup",
    "title": "HINDI TITLE",
    "description": "HINDI DESCRIPTION",
    "image_prompt": "ENGLISH prompt with NO TEXT NO WORDS"
  }},
  {{
    "slide_number": 3,
    "slide_type": "climax",
    "title": "HINDI TITLE",
    "description": "HINDI DESCRIPTION",
    "image_prompt": "ENGLISH prompt with NO TEXT NO WORDS"
  }},
  {{
    "slide_number": 4,
    "slide_type": "lesson",
    "title": "HINDI TITLE",
    "description": "HINDI DESCRIPTION",
    "image_prompt": "ENGLISH prompt with NO TEXT NO WORDS"
  }},
  {{
    "slide_number": 5,
    "slide_type": "cta",
    "title": "HINDI TITLE",
    "description": "HINDI DESCRIPTION",
    "image_prompt": "ENGLISH prompt with NO TEXT NO WORDS"
  }}
]
"""

    model = genai.GenerativeModel(GEMINI_MODEL)

    for attempt in range(1, 4):
        try:
            logger.info(f"   Gemini कोशिश {attempt}/3...")
            response = model.generate_content(prompt)
            text = response.text.strip()

            if "```json" in text:
                text = text.split("```json")[1].split("```")[0].strip()
            elif "```" in text:
                text = text.split("```")[1].split("```")[0].strip()

            slides = json.loads(text)

            if not isinstance(slides, list) or len(slides) != 5:
                raise ValueError(f"5 स्लाइड चाहिए, मिले {len(slides)}")

            for slide in slides:
                required = ["slide_number", "slide_type", "title", "description", "image_prompt"]
                for field in required:
                    if field not in slide:
                        raise ValueError(f"Field missing: {field}")

            logger.info(f"✅ स्लाइड ढांचा तैयार ({len(slides)} slides)")

            # Log preview
            for s in slides:
                logger.info(f"   {s['slide_number']}. {s['title'][:50]}")

            return slides

        except Exception as e:
            logger.warning(f"   कोशिश {attempt} विफल: {e}")
            if attempt < 3:
                time.sleep(3)

    logger.warning("⚠️  Backup ढांचा उपयोग कर रहे हैं")
    return _get_fallback_structure(topic, category)


def _get_fallback_structure(topic: str, category: str) -> list:
    """Emergency Hindi fallback"""
    base_prompt = f"{topic}, divine light, cinematic, 8k, spiritual art, NO TEXT NO WORDS NO LETTERS"
    return [
        {
            "slide_number": 1,
            "slide_type": "hook",
            "title": "क्या आप जानते हैं?",
            "description": "एक ऐसी कहानी जो आपकी सोच बदल देगी",
            "image_prompt": f"{base_prompt}, dramatic opening moment"
        },
        {
            "slide_number": 2,
            "slide_type": "setup",
            "title": "यह कैसे शुरू हुआ",
            "description": "कहानी की शुरुआत एक अनोखे मोड़ से हुई",
            "image_prompt": f"{base_prompt}, peaceful beginning scene"
        },
        {
            "slide_number": 3,
            "slide_type": "climax",
            "title": "फिर हुआ चमत्कार",
            "description": "वो पल जिसने सब कुछ बदल दिया",
            "image_prompt": f"{base_prompt}, dramatic climax powerful moment"
        },
        {
            "slide_number": 4,
            "slide_type": "lesson",
            "title": "जीवन की सीख",
            "description": "हर मुश्किल में छुपी है दिव्य सीख",
            "image_prompt": f"{base_prompt}, wisdom enlightenment scene"
        },
        {
            "slide_number": 5,
            "slide_type": "cta",
            "title": "Save करें, Share करें 🙏",
            "description": "इस ज्ञान को सबतक पहुंचाइए",
            "image_prompt": f"{base_prompt}, divine blessing final scene"
        }
    ]


# ============================================================
# 🆕 IMAGE GENERATION — STRONGER NEGATIVE
# ============================================================

def generate_slide_image(slide: dict, category: str) -> Optional[bytes]:
    """एक slide के लिए image बनाओ — कोई text नहीं!"""
    slide_num = slide["slide_number"]
    prompt = slide["image_prompt"]

    logger.info(f"🎨 स्लाइड {slide_num}/5 की तस्वीर बना रहे हैं...")
    logger.info(f"   Prompt: {prompt[:80]}...")

    # ✅ MUCH STRONGER negative prompt
    negative = (
        "text, words, letters, alphabets, writing, captions, subtitles, "
        "signs, billboards, watermark, logo, signature, book text, "
        "readable text, english text, hindi text, sanskrit text, "
        "typography, fonts, characters, symbols, numbers, digits, "
        "labels, tags, stamps, seals, "
        "blurry, low quality, distorted, cartoon, anime, extra limbs, "
        "deformed, ugly, bad anatomy, mutated hands, disfigured"
    )

    try:
        image_bytes, metadata = generate_image_vertex(
            prompt=prompt,
            negative_prompt=negative,
            aspect_ratio="1:1",
            enable_fallback=True
        )
        logger.info(
            f"   ✅ स्लाइड {slide_num} तस्वीर तैयार "
            f"({len(image_bytes):,} bytes, "
            f"provider: {metadata.get('provider', 'unknown')})"
        )
        return image_bytes

    except Exception as e:
        logger.error(f"   ❌ स्लाइड {slide_num} तस्वीर विफल: {e}")
        return None


# ============================================================
# 🆕 PREMIUM OVERLAY — INSTAGRAM COMPATIBLE JPEG
# ============================================================

def apply_premium_overlay(
    image_bytes: bytes,
    slide: dict,
    slide_number: int,
    total_slides: int = 5
) -> bytes:
    """Premium Card Style overlay + Instagram-compatible JPEG"""
    try:
        # ✅ Load image
        img = Image.open(BytesIO(image_bytes))

        # ✅ Convert to RGB first (handle any mode)
        if img.mode != 'RGB':
            if img.mode == 'RGBA':
                # White background for RGBA
                background = Image.new('RGB', img.size, (255, 255, 255))
                background.paste(img, mask=img.split()[3])
                img = background
            else:
                img = img.convert('RGB')

        # ✅ Exact 1080x1080 for Instagram
        img = img.resize(SLIDE_SIZE, Image.LANCZOS)

        # ✅ Convert to RGBA for overlay composition
        img = img.convert("RGBA")

        # Load fonts
        font_header  = _load_font("bold",    HEADER_FONT_SIZE)
        font_title   = _load_font("bold",    TITLE_FONT_SIZE)
        font_desc    = _load_font("regular", DESC_FONT_SIZE)
        font_footer  = _load_font("regular", FOOTER_FONT_SIZE)
        font_counter = _load_font("bold",    COUNTER_FONT_SIZE)

        overlay = Image.new("RGBA", SLIDE_SIZE, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        w, h = SLIDE_SIZE

        # ── HEADER BAR ───────────────────────────────────────
        draw.rectangle([(0, 0), (w, HEADER_HEIGHT)], fill=HEADER_COLOR)

        header_text = f"══  {PAGE_NAME}  ══"
        try:
            hb = draw.textbbox((0, 0), header_text, font=font_header)
            header_tw = hb[2] - hb[0]
            header_th = hb[3] - hb[1]
        except Exception:
            header_tw, header_th = 300, 30

        header_x = (w - header_tw) // 2
        header_y = (HEADER_HEIGHT - header_th) // 2
        draw.text((header_x, header_y), header_text, font=font_header, fill=BRAND_SAFFRON)

        # ── BOTTOM GRADIENT ──────────────────────────────────
        gradient_top = h - GRADIENT_HEIGHT
        for i in range(GRADIENT_HEIGHT):
            alpha = int(200 * (i / GRADIENT_HEIGHT))
            y_pos = gradient_top + i
            draw.rectangle(
                [(0, y_pos), (w, y_pos + 1)],
                fill=(0, 0, 0, alpha)
            )

        # ── TITLE + DESCRIPTION ──────────────────────────────
        slide_type = slide.get("slide_type", "hook")
        type_emoji = SLIDE_TYPE_LABELS.get(slide_type, "✨")
        title_text = slide.get("title", "")
        desc_text  = slide.get("description", "")

        content_start_y = h - GRADIENT_HEIGHT + 40
        full_title = f"{type_emoji}  {title_text}"

        # Title
        wrapped_title = textwrap.fill(full_title, width=22)
        title_lines = wrapped_title.split("\n")
        title_y = content_start_y + 30

        for line in title_lines:
            draw.text((40 + 2, title_y + 2), line, font=font_title, fill=(0, 0, 0, 200))
            draw.text((40, title_y), line, font=font_title, fill=BRAND_GOLD)
            title_y += TITLE_FONT_SIZE + 8

        # Description
        desc_y = title_y + 15
        wrapped_desc = textwrap.fill(desc_text, width=32)
        desc_lines = wrapped_desc.split("\n")[:2]

        for line in desc_lines:
            draw.text((42, desc_y + 1), line, font=font_desc, fill=(0, 0, 0, 180))
            draw.text((40, desc_y), line, font=font_desc, fill=BRAND_WHITE)
            desc_y += DESC_FONT_SIZE + 6

        # ── FOOTER ──────────────────────────────────────────
        footer_top = h - FOOTER_HEIGHT
        draw.rectangle([(0, footer_top), (w, h)], fill=FOOTER_COLOR)

        footer_y = footer_top + (FOOTER_HEIGHT - FOOTER_FONT_SIZE) // 2

        draw.text((30, footer_y), HANDLE, font=font_footer, fill=BRAND_SAFFRON)

        counter_text = f"{slide_number}/{total_slides}"
        try:
            cb = draw.textbbox((0, 0), counter_text, font=font_counter)
            c_w = cb[2] - cb[0]
        except Exception:
            c_w = 60
        draw.text((w - c_w - 30, footer_y), counter_text, font=font_counter, fill=BRAND_WHITE)

        # ── COMPOSE + CONVERT TO RGB ─────────────────────────
        final = Image.alpha_composite(img, overlay)
        final = final.convert("RGB")

        # ✅ Instagram-compatible JPEG save
        output = BytesIO()
        final.save(
            output,
            format="JPEG",
            quality=90,
            optimize=True,
            progressive=False,   # Instagram prefers non-progressive
            subsampling=0,       # 4:4:4 for best quality
        )
        result_bytes = output.getvalue()

        # ✅ Check size < 8MB (Instagram limit)
        if len(result_bytes) > 8_000_000:
            logger.warning(f"   ⚠️  Image बड़ी है ({len(result_bytes):,} bytes), quality कम कर रहे हैं")
            output = BytesIO()
            final.save(output, format="JPEG", quality=75, optimize=True)
            result_bytes = output.getvalue()

        logger.info(
            f"   🖼️  Overlay लगाया: स्लाइड {slide_number} "
            f"({len(result_bytes):,} bytes, 1080x1080 JPEG)"
        )
        return result_bytes

    except Exception as e:
        logger.error(f"   ❌ स्लाइड {slide_number} overlay विफल: {e}")
        return image_bytes


# ============================================================
# 🆕 CAROUSEL CAPTION — FULL HINDI + INFORMATIVE
# ============================================================

def generate_carousel_caption(topic: str, category: str, slides: list) -> str:
    """पूरी तरह Hindi + informative caption"""
    logger.info("📝 Caption बना रहे हैं...")

    slide_titles = "\n".join([
        f"Slide {s['slide_number']}: {s['title']}"
        for s in slides
    ])

    prompt = f"""
You are writing an Instagram caption for a spiritual Hindu page "Sanatan Soch".

TOPIC: {topic}
CATEGORY: {category}
CAROUSEL SLIDES:
{slide_titles}

⚠️ LANGUAGE: Write ENTIRE caption in HINDI (Devanagari script).
Only English words allowed: Save, Share, Follow, Comment, @sanatanii_soch

STRUCTURE (Hindi mein):
1. पहली line — ध्यान खींचने वाला सवाल या तथ्य
2. 3-4 lines — विषय के बारे में interesting/informative content
3. Empty line
4. "➡️ पूरी कहानी देखने के लिए Swipe करें →→→"
5. Empty line
6. 2-3 lines — गहरी आध्यात्मिक सीख
7. Empty line
8. Final line: "🔖 Save करें | 🙏 Share करें | ✅ Follow @sanatanii_soch"

WRITING STYLE:
- Emotional, spiritual, powerful Hindi
- Use श्रद्धा भरे शब्द
- 200-300 words total
- Use emojis: 🙏 🕉️ ✨ 🔱 📿 🪔 💫 🌸
- NO hashtags in caption body

EXAMPLE OPENINGS (चुनें एक जैसा):
- "क्या आप जानते हैं कि..."
- "यह बात 99% लोगों को नहीं पता..."
- "एक ऐसा रहस्य जो आपकी सोच बदल देगा..."
- "भगवान श्री कृष्ण ने कहा था..."
- "हमारे शास्त्रों में लिखा है..."

TONE:
- Informative (जानकारी वाला)
- Inspirational (प्रेरणादायक)
- Emotional (भावनात्मक)
- Spiritual (आध्यात्मिक)

Write ONLY the Hindi caption. Start directly with hook. No preamble.
"""

    try:
        model = genai.GenerativeModel(GEMINI_MODEL)
        response = model.generate_content(prompt)
        caption = response.text.strip()

        # Clean any markdown
        caption = caption.replace("**", "").replace("*", "")

        logger.info(f"✅ Caption तैयार ({len(caption)} chars)")
        return caption
    except Exception as e:
        logger.warning(f"Caption generation विफल: {e}")
        return (
            f"🕉️ {topic}\n\n"
            f"एक बहुत ही खास बात आपके सामने है।\n"
            f"यह जानकारी शायद आपकी सोच बदल दे।\n"
            f"हमारे धर्म में छुपे रहस्य अनमोल हैं।\n\n"
            f"➡️ पूरी कहानी देखने के लिए Swipe करें →→→\n\n"
            f"जीवन की सच्चाई इन 5 slides में छुपी है।\n"
            f"अपने प्रियजनों तक ज़रूर पहुंचाइए।\n\n"
            f"🔖 Save करें | 🙏 Share करें | ✅ Follow @sanatanii_soch"
        )


# ============================================================
# MAIN ENGINE (Recovery Support)
# ============================================================

def build_carousel(
    topic: str,
    category: str,
    session_id: str = "",
    resume_state: Optional[dict] = None
) -> dict:
    logger.info("=" * 55)
    logger.info("=== CAROUSEL ENGINE शुरू ===")
    logger.info("=" * 55)
    logger.info(f"📌 विषय   : {topic[:60]}")
    logger.info(f"📂 श्रेणी  : {category}")
    logger.info(f"🆔 सेशन   : {session_id[:8] if session_id else 'नया'}")

    start_time = time.time()
    failed_slides = []
    resumed_stage = None

    slides = None
    caption = None
    slides_bytes = {}

    # ── RECOVERY CHECK ───────────────────────────────────────
    if resume_state:
        stage = resume_state.get("stage", "")
        resumed_stage = stage
        data = resume_state.get("data", {})
        slides_bytes = resume_state.get("slides_bytes", {})

        logger.info(f"♻️  Recovery मोड — Stage: {stage}")

        if data.get("carousel_slides"):
            slides = data["carousel_slides"]
            logger.info(f"✅ पुराने {len(slides)} स्लाइड structure मिले")

        if data.get("carousel_caption"):
            caption = data["carousel_caption"]
            logger.info(f"✅ पुराना caption मिला ({len(caption)} chars)")

        if slides and slides_bytes:
            for slide in slides:
                sn = slide.get("slide_number")
                if sn in slides_bytes:
                    slide["image_bytes"] = slides_bytes[sn]

            has_images = sum(1 for s in slides if s.get("image_bytes"))
            logger.info(f"✅ {has_images} पुरानी तस्वीरें मिलीं")

    # ── STEP 1: SLIDE STRUCTURE ──────────────────────────────
    if not slides:
        logger.info("")
        logger.info("--- चरण 1: स्लाइड का ढांचा ---")
        slides = generate_slide_structure(topic, category)

        if session_id:
            save_checkpoint(
                session_id=session_id,
                stage="SLIDES_STRUCTURED",
                data={
                    "topic":            topic,
                    "category":         category,
                    "post_type":        "carousel",
                    "carousel_slides":  slides,
                }
            )
    else:
        logger.info("⏭️  स्लाइड ढांचा skip (पहले से है)")

    # ── STEP 2: IMAGE GENERATION ─────────────────────────────
    logger.info("")
    logger.info("--- चरण 2: तस्वीरें बना रहे हैं ---")

    images_regenerated = 0
    images_reused = 0

    for slide in slides:
        slide_num = slide["slide_number"]

        if slide.get("image_bytes"):
            logger.info(f"⏭️  स्लाइड {slide_num}: तस्वीर पहले से है (skip)")
            images_reused += 1
            continue

        raw_bytes = generate_slide_image(slide, category)

        if raw_bytes is None:
            logger.error(f"❌ स्लाइड {slide_num} तस्वीर विफल")
            failed_slides.append(slide_num)
            slide["image_bytes"] = None
            slide["image_url"] = ""
            slide["media_id"] = ""
            continue

        logger.info(f"🎨 स्लाइड {slide_num} पर overlay...")
        final_bytes = apply_premium_overlay(
            image_bytes=raw_bytes,
            slide=slide,
            slide_number=slide_num,
            total_slides=5
        )

        slide["image_bytes"] = final_bytes
        slide["image_url"]   = slide.get("image_url", "")
        slide["media_id"]    = slide.get("media_id", "")
        images_regenerated += 1

        if slide_num < 5:
            logger.info("⏳ 3s रुकते हैं...")
            time.sleep(3)

    # Checkpoint
    if session_id:
        slides_bytes_map = {}
        for slide in slides:
            if slide.get("image_bytes"):
                slides_bytes_map[slide["slide_number"]] = slide["image_bytes"]

        save_checkpoint(
            session_id=session_id,
            stage="IMAGES_GENERATED",
            data={
                "topic":            topic,
                "category":         category,
                "post_type":        "carousel",
                "carousel_slides":  [
                    {k: v for k, v in s.items() if k != "image_bytes"}
                    for s in slides
                ],
            },
            slides_bytes=slides_bytes_map
        )

    # ── STEP 3: CAPTION ──────────────────────────────────────
    if not caption:
        logger.info("")
        logger.info("--- चरण 3: Caption ---")
        caption = generate_carousel_caption(topic, category, slides)
    else:
        logger.info("⏭️  Caption skip (पहले से है)")

    # ── SUMMARY ──────────────────────────────────────────────
    total_time = round(time.time() - start_time, 2)
    successful = sum(1 for s in slides if s.get("image_bytes"))

    logger.info("")
    logger.info("=" * 55)
    logger.info("=== CAROUSEL ENGINE पूर्ण ===")
    logger.info(f"✅ सफल स्लाइड्स      : {successful}/5")
    logger.info(f"♻️  पुनः उपयोग        : {images_reused}")
    logger.info(f"🆕 नई बनी            : {images_regenerated}")
    logger.info(f"❌ विफल स्लाइड्स     : {failed_slides}")
    logger.info(f"⏱️  कुल समय           : {total_time}s")
    if resumed_stage:
        logger.info(f"♻️  Recovery से आगे  : {resumed_stage}")
    logger.info("=" * 55)

    return {
        "success":           successful >= 3,
        "slides":            slides,
        "caption":           caption,
        "total_slides":      5,
        "successful_slides": successful,
        "failed_slides":     failed_slides,
        "build_time":        total_time,
        "images_reused":     images_reused,
        "images_regenerated": images_regenerated,
        "resumed_from_stage": resumed_stage,
    }