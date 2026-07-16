"""
Reply Generator - AI-powered contextual reply generation

V3 Features:
- Detects comment intent (praise/question/feedback/request)
- Generates personalized Hindi replies
- Uses commenter's name
- Matches brand voice (Sanatani Soch)
- Never sounds robotic
- Includes relevant emojis
- Rate limits Gemini calls
"""
import re
import time
import google.generativeai as genai

from config.settings import GEMINI_API_KEY, GEMINI_MODEL
from utils.logger import get_logger

genai.configure(api_key=GEMINI_API_KEY)
logger = get_logger("reply_generator")


# ============================================================
# INTENT DETECTION
# ============================================================

def _detect_intent(comment_text: str) -> str:
    """
    Detect comment intent.

    Returns:
    - "praise": Positive comment (Har Har Mahadev, Beautiful, etc.)
    - "question": Asking something
    - "request": Asking for specific content
    - "story": Sharing personal experience
    - "criticism": Negative feedback
    - "greeting": Simple greeting (Jai Shri Ram etc.)
    - "generic": Anything else
    """
    text_lower = comment_text.lower()

    # Question
    if '?' in comment_text or 'kya' in text_lower or 'kaise' in text_lower or 'kyun' in text_lower:
        return "question"

    # Greeting / Devotional phrases
    greetings = [
        "har har mahadev", "jai shri ram", "radhe radhe", "jai mata di",
        "om namah shivaya", "ganpati bappa", "jai hanuman", "jai shri krishna",
        "hare krishna", "jai bajrangbali", "jai ganesh", "🙏", "🕉️", "🚩"
    ]
    for greeting in greetings:
        if greeting in text_lower:
            return "greeting"

    # Praise
    praise_words = [
        "beautiful", "amazing", "wonderful", "great", "nice", "superb",
        "bahut achha", "bahut sundar", "bahut achhi", "kamaal", "zabardast",
        "shandar", "adbhut", "dil khush", "loved it", "❤️", "🔥", "👏"
    ]
    for word in praise_words:
        if word in text_lower:
            return "praise"

    # Request
    request_words = [
        "please make", "banao", "banaiye", "chahiye", "aur do",
        "next video", "agle video", "request", "topic"
    ]
    for word in request_words:
        if word in text_lower:
            return "request"

    # Personal story
    if any(word in text_lower for word in ["mera", "meri", "mere", "main", "humne", "hamne"]):
        if len(comment_text.split()) > 5:
            return "story"

    # Criticism
    if any(word in text_lower for word in ["galat", "wrong", "fake", "bekar", "bakwas"]):
        return "criticism"

    return "generic"


# ============================================================
# REPLY TEMPLATES (Fallback if Gemini fails)
# ============================================================

REPLY_TEMPLATES = {
    "greeting": [
        "🙏 {name} जी, आपका बहुत धन्यवाद! भगवान आपको सदा प्रसन्न रखें 🕉️",
        "🙏 {name} जी! आपका प्यार ही हमारी ताकत है ✨",
        "जय हो {name} जी! 🙏 भगवान की कृपा आप पर बनी रहे 🌸",
    ],
    "praise": [
        "🙏 {name} जी, आपके इतने प्यार के लिए बहुत बहुत धन्यवाद! ✨",
        "{name} जी, आपकी बात पढ़कर दिल खुश हो गया 🙏 ऐसे ही जुड़े रहिए 🌸",
        "बहुत शुक्रिया {name} जी! 🙏 आपका साथ हमें और बेहतर बनाता है ✨",
    ],
    "question": [
        "🙏 {name} जी, बहुत अच्छा सवाल है! हम जल्द इस पर detailed video बनाएंगे ✨",
        "{name} जी, इस बारे में हम अगले video में बताएंगे 🙏 Stay tuned! 🌸",
    ],
    "request": [
        "🙏 {name} जी, बहुत अच्छा suggestion है! हम जल्दी ही इस topic पर content लाएंगे ✨",
        "{name} जी, आपकी request note कर ली है 📝 जल्द ही आएगा! 🙏",
    ],
    "story": [
        "🙏 {name} जी, आपकी बात पढ़कर बहुत अच्छा लगा! भगवान की कृपा हमेशा आप पर बनी रहे ✨",
        "{name} जी, आपका अनुभव सुनकर मन भर आया 🙏 ऐसे ही भगवान से जुड़े रहिए 🌸",
    ],
    "criticism": [
        "🙏 {name} जी, आपकी बात सुनी। हम कोशिश करेंगे और बेहतर बनने की। आपका साथ चाहिए 🌸",
    ],
    "generic": [
        "🙏 {name} जी, धन्यवाद! भगवान की कृपा आप पर बनी रहे ✨",
        "{name} जी, शुक्रिया! 🙏 ऐसे ही हमारे साथ जुड़े रहिए 🌸",
    ]
}


# ============================================================
# AI REPLY GENERATION
# ============================================================

def _generate_ai_reply(comment: dict, intent: str) -> str:
    """
    Generate contextual reply using Gemini.

    Args:
        comment: Comment dict with text, username, platform
        intent: Detected intent

    Returns:
        Reply text (Hindi)
    """
    username = comment.get('username', 'भक्त')
    text = comment.get('text', '')
    platform = comment.get('platform', 'instagram')

    prompt = f"""तुम एक spiritual Hindi page "सनातनी सोच" (@sanatanii_soch) के admin हो।

एक {platform} comment का reply लिखो:

Comment by @{username}: "{text}"
Intent: {intent}

═══════════════════════════════════════════
📏 REPLY RULES:
═══════════════════════════════════════════

1. ✅ Hindi में reply करो (आसान भाषा)
2. ✅ Maximum 2-3 lines (short aur sweet)
3. ✅ Commenter का naam use करो: "{username} जी"
4. ✅ 1-2 emojis add करो (🙏 ✨ 🕉️ 🌸 🚩)
5. ✅ Warm, personal, caring tone
6. ✅ Page ka naam mat likho (they already know)

❌ DO NOT:
- English sentences (except name)
- Long paragraphs
- Generic copy-paste replies
- Hashtags
- Links
- Promotional tone
- "AI generated" feel
- "As an AI" phrases

═══════════════════════════════════════════
EXAMPLE GOOD REPLIES:
═══════════════════════════════════════════

Comment: "Har Har Mahadev 🙏"
Reply: "🙏 भाई जी, हर हर महादेव! भोलेनाथ आपकी सारी मनोकामनाएं पूरी करें 🕉️"

Comment: "Beautiful video ❤️"
Reply: "बहुत शुक्रिया भाई! 🙏 आपका प्यार ही हमारी ताकत है ✨ ऐसे ही जुड़े रहिए"

Comment: "Krishna ka favourite colour kya tha?"
Reply: "बहुत अच्छा सवाल! 🙏 श्रीकृष्ण पीला रंग बहुत पसंद करते थे, इसलिए पीतांबर कहलाते हैं 🌸"

═══════════════════════════════════════════

अब reply लिखो — सिर्फ reply text, कुछ और नहीं:"""

    try:
        model = genai.GenerativeModel(GEMINI_MODEL)

        response = model.generate_content(
            prompt,
            generation_config={
                "temperature": 0.8,
                "max_output_tokens": 200,
                "top_p": 0.95,
            }
        )

        raw = response.text.strip()

        # Clean AI artifacts
        raw = raw.strip('"\'`')
        raw = re.sub(r'\*\*(.*?)\*\*', r'\1', raw)
        raw = re.sub(r'\*(.*?)\*', r'\1', raw)

        # Remove "Reply:" prefix
        if raw.lower().startswith("reply:"):
            raw = raw.split(":", 1)[1].strip()

        if len(raw) > 10 and len(raw) < 500:
            return raw

    except Exception as e:
        logger.warning(f"⚠️  Gemini reply failed: {e}")

    return None


def _get_fallback_reply(intent: str, username: str) -> str:
    """Get template reply when AI fails"""
    import random

    templates = REPLY_TEMPLATES.get(intent, REPLY_TEMPLATES["generic"])
    template = random.choice(templates)

    return template.format(name=username)


# ============================================================
# MAIN: GENERATE REPLY
# ============================================================

def generate_reply(comment: dict) -> str:
    """
    Generate contextual reply for a comment.

    Args:
        comment: {
            "platform": "instagram/facebook/youtube",
            "post_id": "...",
            "comment_id": "...",
            "text": "user comment text",
            "username": "username"
        }

    Returns:
        Reply text (Hindi) ready to post
    """
    text = comment.get('text', '')
    username = comment.get('username', 'भक्त')
    platform = comment.get('platform', 'unknown')

    logger.info(f"💬 Generating reply for @{username} ({platform})")
    logger.info(f"   Comment: {text[:60]}...")

    # Step 1: Detect intent
    intent = _detect_intent(text)
    logger.info(f"   Intent: {intent}")

    # Step 2: Try AI reply
    reply = _generate_ai_reply(comment, intent)

    if reply:
        logger.info(f"   ✅ AI reply: {reply[:60]}...")
        return reply

    # Step 3: Fallback to template
    logger.info(f"   ⚠️  Using template fallback")
    reply = _get_fallback_reply(intent, username)

    logger.info(f"   📝 Fallback reply: {reply[:60]}...")
    return reply


def generate_replies_batch(comments: list) -> list:
    """
    Generate replies for multiple comments.

    Args:
        comments: List of comment dicts

    Returns:
        List of (comment, reply) tuples
    """
    logger.info(f"💬 Generating {len(comments)} replies...")

    results = []

    for i, comment in enumerate(comments, 1):
        logger.info(f"   [{i}/{len(comments)}] Processing...")

        try:
            reply = generate_reply(comment)
            results.append((comment, reply))
        except Exception as e:
            logger.error(f"   ❌ Reply generation failed: {e}")
            # Use fallback
            username = comment.get('username', 'भक्त')
            fallback = _get_fallback_reply("generic", username)
            results.append((comment, fallback))

        # Rate limit: 1 second between Gemini calls
        if i < len(comments):
            time.sleep(1)

    logger.info(f"✅ Generated {len(results)} replies")
    return results


# ============================================================
# STANDALONE TEST
# ============================================================

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("REPLY GENERATOR V3 - TEST")
    print("=" * 60 + "\n")

    test_comments = [
        {"platform": "instagram", "post_id": "1", "comment_id": "c1",
         "text": "Har Har Mahadev 🙏", "username": "shiv_bhakt_123"},

        {"platform": "facebook", "post_id": "2", "comment_id": "c2",
         "text": "Beautiful video! Krishna bhagwan bahut sundar lagte hain ❤️",
         "username": "Radha Sharma"},

        {"platform": "youtube", "post_id": "3", "comment_id": "c3",
         "text": "Bhagwan Shiva ka favourite number kya hai?",
         "username": "Spiritual_Seeker"},

        {"platform": "instagram", "post_id": "4", "comment_id": "c4",
         "text": "Meri maa bahut bimar thi, maine Hanuman Chalisa padhi aur wo theek ho gayi 🙏",
         "username": "ram_bhakt_99"},
    ]

    for comment in test_comments:
        print(f"\n{'=' * 60}")
        print(f"Platform: {comment['platform']}")
        print(f"User: @{comment['username']}")
        print(f"Comment: {comment['text']}")

        reply = generate_reply(comment)

        print(f"\n💬 Reply:")
        print(f"   {reply}")