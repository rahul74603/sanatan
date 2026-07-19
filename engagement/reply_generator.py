"""
Reply Generator V4 - Fixed prompt-echoing bug

FIXES:
- Prompt echo detection (rejects reply if it contains prompt text)
- Better validation (Hindi/emoji required)
- Cleaner prompt (less confusion)
- Auto-fallback on suspicious reply
"""
import re
import time
import random
import google.generativeai as genai

from config.settings import GEMINI_API_KEY, GEMINI_MODEL
from utils.logger import get_logger

genai.configure(api_key=GEMINI_API_KEY)
logger = get_logger("reply_generator")


# ============================================================
# INTENT DETECTION
# ============================================================

def _detect_intent(comment_text: str) -> str:
    """Detect comment intent"""
    text_lower = comment_text.lower()

    if '?' in comment_text or 'kya' in text_lower or 'kaise' in text_lower or 'kyun' in text_lower:
        return "question"

    greetings = [
        "har har mahadev", "jai shri ram", "radhe radhe", "jai mata di",
        "om namah shivaya", "ganpati bappa", "jai hanuman", "jai shri krishna",
        "hare krishna", "jai bajrangbali", "jai ganesh", "jai ho",
        "jai shree krishna", "jai shree ram", "🙏", "🕉️", "🚩"
    ]
    for greeting in greetings:
        if greeting in text_lower:
            return "greeting"

    praise_words = [
        "beautiful", "amazing", "wonderful", "great", "nice", "superb",
        "bahut achha", "bahut sundar", "bahut achhi", "kamaal", "zabardast",
        "shandar", "adbhut", "dil khush", "loved it", "❤️", "🔥", "👏"
    ]
    for word in praise_words:
        if word in text_lower:
            return "praise"

    request_words = [
        "please make", "banao", "banaiye", "chahiye", "aur do",
        "next video", "agle video", "request", "topic"
    ]
    for word in request_words:
        if word in text_lower:
            return "request"

    if any(word in text_lower for word in ["mera", "meri", "mere", "main", "humne", "hamne"]):
        if len(comment_text.split()) > 5:
            return "story"

    if any(word in text_lower for word in ["galat", "wrong", "fake", "bekar", "bakwas"]):
        return "criticism"

    return "generic"


# ============================================================
# REPLY TEMPLATES (Fallback)
# ============================================================

REPLY_TEMPLATES = {
    "greeting": [
        "🙏 {name} जी, आपका बहुत धन्यवाद! भगवान आपको सदा प्रसन्न रखें 🕉️",
        "🙏 {name} जी! आपका प्यार ही हमारी ताकत है ✨",
        "जय हो {name} जी! 🙏 भगवान की कृपा आप पर बनी रहे 🌸",
        "🙏 {name} जी, जय श्री कृष्ण! भगवान आपके साथ हैं 🌸",
        "🕉️ {name} जी, हर हर महादेव! शिवजी की कृपा बनी रहे ✨",
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
        "🙏 {name} जी, आपका प्यार बना रहे! जय श्री कृष्ण ✨",
    ]
}


# ============================================================
# 🆕 V4: REPLY VALIDATION (Detects Prompt Echo)
# ============================================================

# Words that should NEVER appear in a real reply (indicate prompt echo)
PROMPT_ECHO_MARKERS = [
    "output only", "reply text", "generate", "instruction",
    "rules:", "example", "do not", "as an ai", "language model",
    "here is", "here's your", "sure!", "of course",
    "reply:", "comment:", "user:", "assistant:",
    "spiritual hindi page", "admin ho", "intent:",
    "प्रॉम्प्ट", "instructions", "```",
]


def _is_valid_reply(reply: str, original_comment: str = "") -> tuple[bool, str]:
    """
    Validate AI-generated reply.
    
    Returns:
        (is_valid, reason)
    """
    if not reply or not reply.strip():
        return False, "empty"
    
    reply_lower = reply.lower().strip()
    
    # Too short
    if len(reply.strip()) < 15:
        return False, f"too_short ({len(reply)} chars)"
    
    # Too long (probably prompt echo)
    if len(reply.strip()) > 400:
        return False, f"too_long ({len(reply)} chars)"
    
    # 🚨 Prompt echo detection
    for marker in PROMPT_ECHO_MARKERS:
        if marker.lower() in reply_lower:
            return False, f"prompt_echo (contains '{marker}')"
    
    # Must contain either Hindi/Devanagari OR emoji
    has_hindi = any('\u0900' <= c <= '\u097F' for c in reply)
    has_emoji = bool(re.search(
        r'[\U0001F300-\U0001FFFF\U00002600-\U000027BF\U0001F600-\U0001F9FF]',
        reply
    ))
    
    if not has_hindi and not has_emoji:
        return False, "no_hindi_no_emoji (looks like English instruction)"
    
    # Reply should NOT be same as comment (echo)
    if original_comment and reply.strip().lower() == original_comment.strip().lower():
        return False, "identical_to_comment"
    
    return True, "valid"


# ============================================================
# AI REPLY GENERATION (Fixed Prompt)
# ============================================================

def _generate_ai_reply(comment: dict, intent: str) -> str:
    """Generate contextual reply using Gemini"""
    username = comment.get('username', 'भक्त')
    text = comment.get('text', '')

    # 🆕 V4: Simpler, cleaner prompt (less confusion for AI)
    prompt = f"""तुम "सनातनी सोच" spiritual page के admin हो। एक Hindi reply लिखो।

User @{username} ने comment किया: "{text}"

Reply लिखने के नियम:
- सिर्फ Hindi में (आसान भाषा)
- 2-3 lines maximum
- {username} जी का नाम use करो
- 1-2 emoji: 🙏 ✨ 🕉️ 🌸 🚩 ❤️
- Warm, personal tone
- कोई English वाक्य नहीं
- कोई hashtag नहीं
- कोई link नहीं

Examples:
User: "Har Har Mahadev 🙏"
Reply: 🙏 भाई जी, हर हर महादेव! भोलेनाथ आपकी सारी मनोकामनाएं पूरी करें 🕉️

User: "Beautiful video"
Reply: बहुत शुक्रिया! 🙏 आपका प्यार ही हमारी ताकत है ✨

अब @{username} के लिए reply लिखो (सिर्फ reply, कुछ और नहीं):"""

    try:
        model = genai.GenerativeModel(GEMINI_MODEL)

        response = model.generate_content(
            prompt,
            generation_config={
                "temperature": 0.8,
                "max_output_tokens": 150,
                "top_p": 0.95,
            }
        )

        # Extract text safely
        try:
            raw = response.text.strip()
        except Exception as e:
            logger.warning(f"⚠️  Response.text failed: {e}")
            return None

        if not raw:
            logger.warning("⚠️  Empty response from Gemini")
            return None

        # Clean AI artifacts
        raw = raw.strip('"\'`')
        raw = re.sub(r'\*\*(.*?)\*\*', r'\1', raw)
        raw = re.sub(r'\*(.*?)\*', r'\1', raw)
        raw = re.sub(r'```[\s\S]*?```', '', raw)  # Remove code blocks

        # Remove common prefixes
        prefixes_to_remove = [
            "reply:", "Reply:", "REPLY:",
            "answer:", "Answer:",
            "response:", "Response:",
            "output:", "Output:",
        ]
        for prefix in prefixes_to_remove:
            if raw.startswith(prefix):
                raw = raw[len(prefix):].strip()

        # Take only first paragraph if multiple
        if '\n\n' in raw:
            raw = raw.split('\n\n')[0].strip()

        # 🆕 V4: STRICT VALIDATION
        is_valid, reason = _is_valid_reply(raw, text)
        
        if not is_valid:
            logger.warning(f"⚠️  Reply rejected: {reason}")
            logger.warning(f"   Rejected text: '{raw[:80]}...'")
            return None

        return raw

    except Exception as e:
        logger.warning(f"⚠️  Gemini reply failed: {e}")
        return None


def _get_fallback_reply(intent: str, username: str) -> str:
    """Get template reply when AI fails"""
    templates = REPLY_TEMPLATES.get(intent, REPLY_TEMPLATES["generic"])
    template = random.choice(templates)
    return template.format(name=username)


# ============================================================
# MAIN: GENERATE REPLY
# ============================================================

def generate_reply(comment: dict) -> str:
    """Generate contextual reply for a comment"""
    text = comment.get('text', '')
    username = comment.get('username', 'भक्त')
    platform = comment.get('platform', 'unknown')

    logger.info(f"💬 Generating reply for @{username} ({platform})")
    logger.info(f"   Comment: {text[:60]}...")

    intent = _detect_intent(text)
    logger.info(f"   Intent: {intent}")

    # Try AI (with retry)
    reply = None
    for attempt in range(2):  # 2 attempts
        reply = _generate_ai_reply(comment, intent)
        if reply:
            break
        if attempt == 0:
            logger.info(f"   🔄 Retry Gemini...")
            time.sleep(1)

    if reply:
        logger.info(f"   ✅ AI reply: {reply[:60]}...")
        return reply

    # Fallback to template
    logger.info(f"   ⚠️  Using template fallback")
    reply = _get_fallback_reply(intent, username)
    logger.info(f"   📝 Fallback reply: {reply[:60]}...")
    return reply


def generate_replies_batch(comments: list) -> list:
    """Generate replies for multiple comments"""
    logger.info(f"💬 Generating {len(comments)} replies...")

    results = []

    for i, comment in enumerate(comments, 1):
        logger.info(f"   [{i}/{len(comments)}] Processing...")

        try:
            reply = generate_reply(comment)
            results.append((comment, reply))
        except Exception as e:
            logger.error(f"   ❌ Reply generation failed: {e}")
            username = comment.get('username', 'भक्त')
            fallback = _get_fallback_reply("generic", username)
            results.append((comment, fallback))

        if i < len(comments):
            time.sleep(1)

    logger.info(f"✅ Generated {len(results)} replies")
    return results


# ============================================================
# STANDALONE TEST
# ============================================================

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("REPLY GENERATOR V4 - VALIDATION TEST")
    print("=" * 60 + "\n")

    # Test validation function
    test_replies = [
        ("Output ONLY the reply...", False),
        ("🙏 भाई जी, हर हर महादेव!", True),
        ("Reply: Beautiful post!", False),  # English + prefix
        ("बहुत शुक्रिया! 🙏 ऐसे ही जुड़े रहिए ✨", True),
        ("Sure! Here is your reply", False),
        ("", False),
        ("ok", False),
    ]

    print("🧪 Validation Test:")
    for reply, expected in test_replies:
        valid, reason = _is_valid_reply(reply, "")
        status = "✅" if valid == expected else "❌"
        print(f"   {status} '{reply[:40]}...' → valid={valid} ({reason})")

    print("\n" + "=" * 60)
    print("Real Gemini test:")
    print("=" * 60)

    test_comments = [
        {"platform": "instagram", "text": "jai ho prabhu", "username": "0o0_rahul"},
        {"platform": "instagram", "text": "Har Har Mahadev 🙏", "username": "shiv_bhakt"},
    ]

    for comment in test_comments:
        print(f"\nComment: {comment['text']}")
        reply = generate_reply(comment)
        print(f"Reply  : {reply}")