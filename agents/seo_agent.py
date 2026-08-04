"""
SEO Agent - Dedicated Search Engine Optimization for ALL Platforms

V4 Features:
- 🔍 Gemini-powered trending keyword detection (niche-specific)
- 📸 Instagram SEO (hashtags + caption hooks + alt text)
- 📘 Facebook SEO (description + keywords + tags)
- 📺 YouTube SEO (title + description + tags + chapters)
- 🎯 Per-post UNIQUE keywords (no repetition)
- 📊 Category-specific keyword banks
- 🔄 Trending keyword injection
- 🌐 Bilingual SEO (Hindi + English)
- 📈 Analytics-driven optimization

This agent runs AFTER caption_agent and BEFORE publisher_agent.
It enhances caption, hashtags, and creates platform-specific metadata.
"""
import re
import time
import random
import json
import google.generativeai as genai

from core.memory import AgentMemory
from config.settings import GEMINI_API_KEY, GEMINI_MODEL
from utils.logger import get_logger

genai.configure(api_key=GEMINI_API_KEY)
logger = get_logger("seo_agent")


# ============================================================
# CATEGORY-SPECIFIC SEO KEYWORD BANKS
# ============================================================

CATEGORY_SEO_KEYWORDS = {
    "krishna": {
        "hindi": [
            "श्री कृष्ण", "कान्हा", "राधा कृष्ण", "गीता ज्ञान", "वृंदावन",
            "बांसुरी", "मोर पंख", "गोविंद", "माखन चोर", "यमुना",
            "भगवद गीता", "कृष्ण लीला", "द्वारका", "कृष्ण भक्ति"
        ],
        "english": [
            "Lord Krishna", "Krishna story", "Bhagavad Gita", "Vrindavan",
            "Radha Krishna", "Hindu mythology", "Krishna wisdom",
            "spiritual story", "divine love", "Krishna flute"
        ],
        "youtube_tags": [
            "krishna story hindi", "bhagavad gita", "krishna bhajan",
            "vrindavan", "radha krishna", "hindu god", "spiritual video",
            "krishna teaching", "gita updesh", "krishna leela"
        ]
    },
    "shiva": {
        "hindi": [
            "महादेव", "भोलेनाथ", "शिव शंकर", "कैलाश", "त्रिशूल",
            "ॐ नमः शिवाय", "सावन", "शिवलिंग", "नीलकंठ", "महाकाल",
            "शिव तांडव", "गंगा", "नंदी", "शिव भक्ति"
        ],
        "english": [
            "Lord Shiva", "Mahadev", "Shiva story", "Kailash mountain",
            "Om Namah Shivaya", "Hindu god", "Shiva meditation",
            "cosmic dance", "third eye", "Shiva power"
        ],
        "youtube_tags": [
            "shiva story hindi", "mahadev", "om namah shivaya",
            "shiv tandav", "kailash", "bholenath", "shiva bhajan",
            "har har mahadev", "shiva meditation", "mahakaal"
        ]
    },
    "hanuman": {
        "hindi": [
            "हनुमान जी", "बजरंगबली", "पवन पुत्र", "संकट मोचन",
            "राम भक्त", "हनुमान चालीसा", "लंका दहन", "संजीवनी",
            "मारुति", "महाबली", "हनुमान शक्ति"
        ],
        "english": [
            "Hanuman", "Bajrangbali", "Hanuman Chalisa", "Ram devotee",
            "flying god", "monkey god", "Hanuman story",
            "strength devotion", "Lanka", "Sanjeevani"
        ],
        "youtube_tags": [
            "hanuman story hindi", "bajrangbali", "hanuman chalisa",
            "jai hanuman", "sankat mochan", "hanuman power",
            "ram bhakt hanuman", "lanka dahan", "hanuman ji"
        ]
    },
    "ganesha": {
        "hindi": [
            "गणेश जी", "गणपति बाप्पा", "विघ्नहर्ता", "मोदक",
            "गजानन", "एकदंत", "लंबोदर", "गणेश चतुर्थी",
            "प्रथम पूज्य", "मंगल मूर्ति", "गणपति"
        ],
        "english": [
            "Lord Ganesha", "Ganpati", "elephant god", "obstacle remover",
            "Ganesha story", "wisdom god", "Ganesh Chaturthi",
            "Hindu festival", "modak", "auspicious"
        ],
        "youtube_tags": [
            "ganesha story hindi", "ganpati bappa", "ganesh chaturthi",
            "lord ganesha", "vighnaharta", "ganpati morya",
            "ganesha wisdom", "elephant god", "modak story"
        ]
    },
    "durga": {
        "hindi": [
            "मां दुर्गा", "शेरावाली", "नवरात्रि", "शक्ति",
            "काली मां", "अंबे मां", "जगदंबा", "नवदुर्गा",
            "दुर्गा पूजा", "महिषासुर मर्दिनी"
        ],
        "english": [
            "Maa Durga", "goddess Durga", "Navratri", "divine feminine",
            "Shakti", "warrior goddess", "Durga Puja",
            "nine forms", "lion goddess", "mother goddess"
        ],
        "youtube_tags": [
            "durga story hindi", "maa durga", "navratri",
            "durga puja", "jai mata di", "shakti",
            "devi story", "goddess durga", "navdurga"
        ]
    },
    "ram": {
        "hindi": [
            "श्री राम", "अयोध्या", "राम मंदिर", "सीता राम",
            "रामायण", "मर्यादा पुरुषोत्तम", "वनवास",
            "लक्ष्मण", "हनुमान", "रावण वध", "राम राज्य"
        ],
        "english": [
            "Lord Ram", "Ayodhya", "Ramayana", "Sita Ram",
            "Ram Mandir", "ideal king", "dharma",
            "Hindu epic", "Ram story", "righteousness"
        ],
        "youtube_tags": [
            "ram story hindi", "jai shri ram", "ayodhya",
            "ramayana", "ram mandir", "sita ram",
            "ram bhajan", "ram rajya", "maryada purushottam"
        ]
    },
    "motivational": {
        "hindi": [
            "प्रेरणा", "हिम्मत", "सफलता", "जीवन की सीख",
            "सकारात्मक सोच", "आत्मविश्वास", "संघर्ष",
            "जीत", "मेहनत", "विश्वास"
        ],
        "english": [
            "motivation", "inspiration", "life lessons", "success",
            "positive thinking", "self confidence", "struggle",
            "never give up", "believe", "spiritual motivation"
        ],
        "youtube_tags": [
            "motivation hindi", "life lessons", "inspirational story",
            "success story", "positive vibes", "spiritual motivation",
            "daily motivation", "motivational video", "hindi motivation"
        ]
    },
    "temple": {
        "hindi": [
            "मंदिर", "प्राचीन मंदिर", "तीर्थ यात्रा", "दर्शन",
            "पूजा", "आरती", "भारत के मंदिर"
        ],
        "english": [
            "temple", "ancient temple", "Indian temple", "pilgrimage",
            "sacred place", "Hindu architecture", "temple tour"
        ],
        "youtube_tags": [
            "temple tour", "indian temple", "ancient temple",
            "mandir", "pilgrimage india", "temple architecture"
        ]
    },
    "spiritual_nature": {
        "hindi": [
            "आध्यात्मिक", "ध्यान", "शांति", "प्रकृति",
            "हिमालय", "गंगा", "योग", "साधना"
        ],
        "english": [
            "spiritual", "meditation", "peace", "nature",
            "Himalaya", "yoga", "inner peace", "mindfulness"
        ],
        "youtube_tags": [
            "spiritual hindi", "meditation", "inner peace",
            "yoga", "himalaya", "spiritual journey", "mindfulness"
        ]
    }
}


# ============================================================
# PLATFORM-SPECIFIC SEO TEMPLATES
# ============================================================

IG_HOOK_TEMPLATES = [
    "ये बात {percentage}% लोग नहीं जानते... 🤯",
    "क्या आपको पता है {deity} ने क्या कहा था? 😲",
    "रुको! ये {topic_short} की कहानी ज़रूर सुनो 🙏",
    "अगर आप {deity} भक्त हैं तो ये देखो 🔥",
    "इस कहानी ने मेरी ज़िंदगी बदल दी... ✨",
    "{deity} का ये रहस्य जानकर हैरान हो जाओगे 😱",
    "ये {topic_short} का सबसे बड़ा सच है 🙏",
]

IG_CTA_TEMPLATES = [
    "❤️ अगर आप भी {deity} भक्त हैं तो Like करो\n💬 Comment में 🙏 लिखो\n💾 Save करो बाद में देखने के लिए\n🔄 अपने परिवार को भेजो",
    "💬 कौन-कौन मानता है? ✋ Comment करो\n❤️ Like ज़रूर करो\n💾 Save करो\n📤 Share करो अपनों के साथ",
    "🙏 Comment में 'जय {deity_short}' लिखो\n❤️ Double tap करो\n💾 बाद में देखना हो तो Save करो\n🔄 माँ-बाप को भेजो ये video",
]

FB_SEO_FOOTER = """
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
👍 पसंद आया तो Like करें
💬 अपनी बात Comment में बताएं  
🔄 अपने दोस्तों को Share करें
📸 Instagram: @sanatanii_soch
🔔 Page Follow करें: सनातन सोच

🔍 Keywords: {keywords_hindi}, {keywords_english}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"""

YT_DESCRIPTION_TEMPLATE = """{caption}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📖 {english_description}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔔 Subscribe to सनातनी सोच for daily spiritual content!
👍 Like, Comment & Share this video
📸 Follow on Instagram: @sanatanii_soch
📘 Follow on Facebook: सनातन सोच

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔍 Keywords: {all_keywords}

{hashtags}"""

# Branded tag line — merged & deduped with the main hashtag block at build
# time so no tag appears twice in the description.
YT_BRAND_TAGS = "#Shorts #SanatanDharma #Spiritual #Hindu #Devotional #SanataniSoch"


def _build_yt_hashtag_block(memory_hashtags: str) -> str:
    """Combine memory hashtags + brand tags, deduped, preserving order."""
    seen = set()
    ordered = []
    for raw in (memory_hashtags or "").split() + YT_BRAND_TAGS.split():
        tag = raw.strip()
        if not tag:
            continue
        key = tag.lower()
        if key not in seen:
            seen.add(key)
            ordered.append(tag)
    return " ".join(ordered)


# ============================================================
# DEITY NAME MAPPING
# ============================================================

DEITY_NAMES = {
    "krishna": {"hindi": "श्री कृष्ण", "short": "कृष्ण", "english": "Krishna"},
    "shiva": {"hindi": "भगवान शिव", "short": "शिव", "english": "Shiva"},
    "hanuman": {"hindi": "हनुमान जी", "short": "हनुमान", "english": "Hanuman"},
    "ganesha": {"hindi": "गणेश जी", "short": "गणेश", "english": "Ganesha"},
    "durga": {"hindi": "मां दुर्गा", "short": "दुर्गा", "english": "Durga"},
    "ram": {"hindi": "श्री राम", "short": "राम", "english": "Ram"},
    "motivational": {"hindi": "प्रेरणा", "short": "प्रेरणा", "english": "Motivation"},
    "temple": {"hindi": "मंदिर", "short": "मंदिर", "english": "Temple"},
    "spiritual_nature": {"hindi": "आध्यात्मिक", "short": "आध्यात्मिक", "english": "Spiritual"},
}


# ============================================================
# GEMINI-POWERED TRENDING KEYWORDS
# ============================================================

def _extract_response_text(response) -> str:
    """
    Gemini responses are not always a single text part. The response.text
    convenience accessor can raise for multi-part responses, so fall back to
    iterating over candidate parts safely.
    """
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

    raise Exception("Cannot extract text from Gemini response")


def _get_trending_keywords(topic: str, category: str) -> dict:
    """
    Use Gemini to find trending keywords for this specific topic.
    Returns Hindi + English keywords.

    V2: retries once, requests JSON mode, and tolerates flaky/empty
    responses without failing the whole SEO agent (recurring log noise).
    """
    empty_result = {
        "trending_hindi": [],
        "trending_english": [],
        "hook_line": "",
        "english_description": ""
    }

    model = genai.GenerativeModel(GEMINI_MODEL)

    prompt = f"""You are an SEO expert for Indian spiritual content.

Topic: {topic}
Category: {category}

Find 10 trending search keywords that people are searching RIGHT NOW related to this topic.

Return ONLY valid JSON (no markdown):
{{
    "trending_hindi": ["keyword1", "keyword2", "keyword3", "keyword4", "keyword5"],
    "trending_english": ["keyword1", "keyword2", "keyword3", "keyword4", "keyword5"],
    "hook_line": "एक catchy Hindi hook line for Instagram caption",
    "english_description": "2-3 line English SEO description for YouTube"
}}

Focus on: spiritual, devotional, Hindu mythology keywords.
Make keywords SEARCHABLE (what people actually type in search)."""

    last_error = None
    for attempt in range(1, 3):  # 2 attempts
        try:
            generation_config = {
                "temperature": 0.7,
                "max_output_tokens": 500,
                "response_mime_type": "application/json",
            }
            try:
                response = model.generate_content(
                    prompt,
                    generation_config=generation_config
                )
            except Exception as json_mode_error:
                # Model alias may not support JSON output mode → plain mode.
                logger.warning(f"⚠️  JSON mode unsupported, retrying plain: {json_mode_error}")
                response = model.generate_content(
                    prompt,
                    generation_config={
                        "temperature": 0.7,
                        "max_output_tokens": 500,
                    }
                )

            raw = _extract_response_text(response)
            if not raw or raw == "{}":
                raise ValueError("Gemini returned empty response")

            # Clean JSON
            raw = re.sub(r'```json\s*', '', raw)
            raw = re.sub(r'```\s*', '', raw)

            start = raw.find('{')
            end = raw.rfind('}')
            if start != -1 and end != -1:
                raw = raw[start:end + 1]

            result = json.loads(raw)
            if not isinstance(result, dict):
                raise ValueError("Response is not a JSON object")

            # Ensure all expected keys exist (Gemini sometimes omits fields)
            for key in empty_result:
                result.setdefault(key, [] if key.startswith("trending") else "")

            logger.info(f"✅ Gemini trending keywords fetched (attempt {attempt})")
            return result

        except Exception as e:
            last_error = e
            logger.warning(f"⚠️  Trending keywords attempt {attempt} failed: {e}")
            if attempt == 1:
                time.sleep(2)

    logger.warning(f"⚠️  Trending keywords failed after retries: {last_error}")
    return empty_result


# ============================================================
# PLATFORM-SPECIFIC SEO GENERATORS
# ============================================================

def _topic_short_for_hook(topic: str, category: str) -> str:
    """Return a natural short topic for Hindi hooks (avoid raw English chunks)."""
    deity = DEITY_NAMES.get(category, DEITY_NAMES["motivational"])

    # If the topic already has Hindi, use the first few Hindi words.
    hindi_chars = ''.join(c for c in topic if '\u0900' <= c <= '\u097F' or c == ' ').strip()
    hindi_words = hindi_chars.split()
    if len(hindi_words) >= 2:
        return ' '.join(hindi_words[:4])

    category_topic = {
        "krishna": "कृष्ण लीला",
        "shiva": "महादेव की कथा",
        "hanuman": "हनुमान जी की कथा",
        "ganesha": "गणेश जी की कथा",
        "durga": "मां दुर्गा की कथा",
        "ram": "श्री राम की कथा",
        "temple": "मंदिर की कथा",
        "motivational": "जीवन की सीख",
        "spiritual_nature": "आध्यात्मिक सीख",
    }
    return category_topic.get(category, deity["hindi"])


def _generate_ig_seo(memory: AgentMemory, trending: dict) -> dict:
    """Generate Instagram-optimized SEO data"""

    category = memory.category
    deity = DEITY_NAMES.get(category, DEITY_NAMES["motivational"])
    cat_keywords = CATEGORY_SEO_KEYWORDS.get(category, {})

    # Hook line
    hook = trending.get("hook_line", "")
    if not hook:
        template = random.choice(IG_HOOK_TEMPLATES)
        topic_short = _topic_short_for_hook(memory.topic, category)
        hook = template.format(
            percentage=random.choice([90, 95, 99]),
            deity=deity["hindi"],
            topic_short=topic_short
        )

    # CTA
    cta_template = random.choice(IG_CTA_TEMPLATES)
    cta = cta_template.format(
        deity=deity["hindi"],
        deity_short=deity["short"]
    )

    # Enhanced caption
    enhanced_caption = f"{hook}\n\n{memory.caption}\n\n{cta}\n\n📿 Follow @sanatanii_soch 🙏"

    return {
        "caption": enhanced_caption,
        "hook": hook,
        "cta": cta,
    }


def _generate_fb_seo(memory: AgentMemory, trending: dict) -> dict:
    """Generate Facebook-optimized SEO data"""

    category = memory.category
    cat_keywords = CATEGORY_SEO_KEYWORDS.get(category, {})

    keywords_hindi = ', '.join(cat_keywords.get("hindi", [])[:5])
    keywords_english = ', '.join(cat_keywords.get("english", [])[:5])

    # Add trending keywords
    trending_hindi = trending.get("trending_hindi", [])
    trending_english = trending.get("trending_english", [])

    if trending_hindi:
        keywords_hindi += ', ' + ', '.join(trending_hindi[:3])
    if trending_english:
        keywords_english += ', ' + ', '.join(trending_english[:3])

    fb_footer = FB_SEO_FOOTER.format(
        keywords_hindi=keywords_hindi,
        keywords_english=keywords_english
    )

    deity = DEITY_NAMES.get(category, DEITY_NAMES["motivational"])

    # Category context
    category_context = {
        "krishna": f"🦚 {deity['hindi']} की कहानी — प्यार, भक्ति और ज्ञान से भरी।",
        "shiva": f"🕉️ {deity['hindi']} की कहानी — ताकत और शांति का संगम।",
        "hanuman": f"🚩 {deity['hindi']} की कहानी — हिम्मत और भक्ति की मिसाल।",
        "ganesha": f"🐘 {deity['hindi']} की कहानी — मुसीबतें दूर करने वाले बाप्पा।",
        "durga": f"🌺 {deity['hindi']} की कहानी — शक्ति और प्यार का रूप।",
        "ram": f"🏹 {deity['hindi']} की कहानी — धर्म और सच्चाई का रास्ता।",
    }

    context = category_context.get(category, f"🙏 {deity['hindi']} की दिव्य कहानी।")

    enhanced_description = f"{memory.caption}\n\n{context}\n{fb_footer}"

    return {
        "description": enhanced_description,
        "keywords_hindi": keywords_hindi,
        "keywords_english": keywords_english,
    }


def _generate_yt_seo(memory: AgentMemory, trending: dict) -> dict:
    """Generate YouTube-optimized SEO data"""

    category = memory.category
    deity = DEITY_NAMES.get(category, DEITY_NAMES["motivational"])
    cat_keywords = CATEGORY_SEO_KEYWORDS.get(category, {})

    # SEO Title (bilingual)
    import re as re_module
    hindi_chars = ''.join(c for c in memory.topic if '\u0900' <= c <= '\u097F' or c == ' ').strip()

    if hindi_chars and len(hindi_chars) > 5:
        title_hook = hindi_chars[:35]
    else:
        title_hook = f"{deity['hindi']} की अद्भुत कहानी"

    emoji = {"krishna": "🦚", "shiva": "🕉️", "hanuman": "🚩", "ganesha": "🐘",
             "durga": "🌺", "ram": "🏹"}.get(category, "🙏")

    yt_title = f"{title_hook} {emoji} {deity['english']} Story | सनातनी सोच #Shorts"

    if len(yt_title) > 100:
        yt_title = f"{deity['hindi']} {emoji} {deity['english']} | सनातनी सोच #Shorts"

    # SEO Description
    english_desc = trending.get("english_description", "")
    if not english_desc:
        english_desc = (
            f"Watch this beautiful story about {deity['english']}. "
            f"Learn about Hindu mythology and spiritual wisdom. "
            f"Daily devotional content in Hindi."
        )

    all_keywords = ', '.join(
        cat_keywords.get("hindi", [])[:5] +
        cat_keywords.get("english", [])[:5] +
        trending.get("trending_hindi", [])[:3] +
        trending.get("trending_english", [])[:3]
    )

    yt_description = YT_DESCRIPTION_TEMPLATE.format(
        caption=memory.caption or "",
        english_description=english_desc,
        all_keywords=all_keywords,
        hashtags=_build_yt_hashtag_block(memory.hashtags or "")
    )

    # SEO Tags
    yt_tags = list(cat_keywords.get("youtube_tags", []))

    # Add trending tags
    for tag in trending.get("trending_english", [])[:5]:
        clean = tag.strip().lower()
        if clean and clean not in [t.lower() for t in yt_tags]:
            yt_tags.append(clean)

    # Add base tags
    base_tags = ["Sanatan Dharma", "Hindu", "Spiritual", "Devotional",
                 "Hindi Story", "Shorts", "सनातन धर्म", "भक्ति", "सनातनी सोच"]
    for tag in base_tags:
        if tag.lower() not in [t.lower() for t in yt_tags]:
            yt_tags.append(tag)

    # Limit tags (YouTube max 500 chars)
    final_tags = []
    total_chars = 0
    for tag in yt_tags:
        if total_chars + len(tag) + 2 > 480:
            break
        final_tags.append(tag)
        total_chars += len(tag) + 2

    return {
        "title": yt_title,
        "description": yt_description,
        "tags": final_tags,
        "english_description": english_desc,
    }


# ============================================================
# MAIN SEO AGENT
# ============================================================

def run(memory: AgentMemory) -> AgentMemory:
    """
    SEO Agent — Optimize content for ALL platforms.

    Flow:
    1. Fetch trending keywords via Gemini
    2. Generate IG-specific SEO (hook + CTA + enhanced caption)
    3. Generate FB-specific SEO (description + keywords)
    4. Generate YT-specific SEO (title + description + tags)
    5. Store in memory.analytics_data for publisher to use
    """
    logger.info("=" * 55)
    logger.info("=== 🔍 SEO AGENT शुरू ===")
    logger.info("=" * 55)
    logger.info(f"📌 Topic    : {memory.topic[:50]}")
    logger.info(f"📂 Category : {memory.category}")
    logger.info(f"📊 Post Type: {memory.post_type}")

    start_time = time.time()

    # ═══════════════════════════════════════════
    # STEP 1: FETCH TRENDING KEYWORDS
    # ═══════════════════════════════════════════
    logger.info("\n━━━ Step 1: Trending Keywords (Gemini) ━━━")
    trending = _get_trending_keywords(memory.topic, memory.category)

    if trending.get("trending_hindi"):
        logger.info(f"   Hindi : {trending['trending_hindi'][:3]}")
    if trending.get("trending_english"):
        logger.info(f"   English: {trending['trending_english'][:3]}")

    # ═══════════════════════════════════════════
    # STEP 2: INSTAGRAM SEO
    # ═══════════════════════════════════════════
    logger.info("\n━━━ Step 2: Instagram SEO ━━━")
    ig_seo = _generate_ig_seo(memory, trending)

    # Update caption with SEO-enhanced version
    memory.caption = ig_seo["caption"]
    logger.info(f"   ✅ IG caption enhanced ({len(memory.caption)} chars)")
    logger.info(f"   🪝 Hook: {ig_seo['hook'][:50]}...")

    # ═══════════════════════════════════════════
    # STEP 3: FACEBOOK SEO
    # ═══════════════════════════════════════════
    logger.info("\n━━━ Step 3: Facebook SEO ━━━")
    fb_seo = _generate_fb_seo(memory, trending)
    logger.info(f"   ✅ FB description enhanced ({len(fb_seo['description'])} chars)")

    # ═══════════════════════════════════════════
    # STEP 4: YOUTUBE SEO
    # ═══════════════════════════════════════════
    logger.info("\n━━━ Step 4: YouTube SEO ━━━")
    yt_seo = _generate_yt_seo(memory, trending)
    logger.info(f"   ✅ YT title: {yt_seo['title'][:60]}...")
    logger.info(f"   ✅ YT tags: {len(yt_seo['tags'])} tags")

    # ═══════════════════════════════════════════
    # STORE SEO DATA IN MEMORY
    # ═══════════════════════════════════════════
    if memory.analytics_data is None:
        memory.analytics_data = {}

    memory.analytics_data["seo"] = {
        "instagram": ig_seo,
        "facebook": fb_seo,
        "youtube": yt_seo,
        "trending": trending,
    }

    # ═══════════════════════════════════════════
    # SUMMARY
    # ═══════════════════════════════════════════
    elapsed = round(time.time() - start_time, 2)

    logger.info("")
    logger.info("=" * 55)
    logger.info("✅ SEO AGENT COMPLETE")
    logger.info("=" * 55)
    logger.info(f"   ⏱️  Time: {elapsed}s")
    logger.info(f"   📸 IG: Enhanced caption + hook + CTA")
    logger.info(f"   📘 FB: SEO description + keywords")
    logger.info(f"   📺 YT: SEO title + {len(yt_seo['tags'])} tags + description")
    logger.info("=" * 55)

    logger.info("=== SEO AGENT पूर्ण ===\n")
    return memory


# ============================================================
# STANDALONE TEST
# ============================================================

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("SEO AGENT - STANDALONE TEST")
    print("=" * 60 + "\n")

    memory = AgentMemory()
    memory.topic = "Lord Krishna playing flute in Vrindavan"
    memory.category = "krishna"
    memory.mood = "peaceful, divine"
    memory.caption = "कान्हा की बांसुरी की धुन सुनकर सब कुछ रुक जाता था।"
    memory.hashtags = "#krishna #hindu #spiritual"
    memory.post_type = "reel"

    result = run(memory)

    seo = result.analytics_data.get("seo", {})

    print(f"\n📸 INSTAGRAM:")
    print(f"Caption:\n{result.caption[:200]}...")

    print(f"\n📘 FACEBOOK:")
    print(f"Description:\n{seo['facebook']['description'][:200]}...")

    print(f"\n📺 YOUTUBE:")
    print(f"Title: {seo['youtube']['title']}")
    print(f"Tags ({len(seo['youtube']['tags'])}): {seo['youtube']['tags'][:8]}")
    print(f"Description:\n{seo['youtube']['description'][:200]}...")
