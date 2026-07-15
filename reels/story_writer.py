"""
Story Writer - Generate 150-180 word Hindi story for Reels

V2.1 FIXES:
- Stronger prompt with explicit word count enforcement
- Retry with progressive prompts (softer → stricter)
- Better validation (accepts 130-220 word range)
- Prompt asks Gemini to COUNT words itself
- SIMPLE Hindi language (सरल भाषा) - 8yr to 80yr can understand
- No complex Sanskrit words
- Village-city both audience
"""
import re
import time
import hashlib
import google.generativeai as genai

from core.memory import AgentMemory
from config.settings import (
    GEMINI_API_KEY,
    GEMINI_MODEL,
    REEL_STORY_MIN_WORDS,
    REEL_STORY_MAX_WORDS
)
from utils.logger import get_logger

genai.configure(api_key=GEMINI_API_KEY)
logger = get_logger("story_writer")


# Cache (same session)
_story_cache = {}


# ============================================================
# CATEGORY GUIDANCE
# ============================================================

CATEGORY_STORY_STYLE = {
    "krishna": {"tone": "प्यार भरा, खेल भरा, भक्ति वाला", "themes": ["वृंदावन", "बांसुरी", "राधा"]},
    "shiva": {"tone": "ताकतवर, रहस्यमयी", "themes": ["कैलाश", "त्रिशूल", "तांडव"]},
    "hanuman": {"tone": "हिम्मत वाला, भक्ति वाला", "themes": ["राम", "गदा", "संजीवनी"]},
    "ganesha": {"tone": "शुभ, समझदार", "themes": ["मोदक", "चूहा", "मुसीबतें हरने वाले"]},
    "durga": {"tone": "ताकत, मां जैसा प्यार", "themes": ["शेर", "हथियार", "महिषासुर"]},
    "ram": {"tone": "आदर्श, धर्म वाला", "themes": ["अयोध्या", "सीता", "रावण"]},
    "spiritual_nature": {"tone": "शांत", "themes": ["हिमालय", "गंगा", "ध्यान"]},
    "motivational": {"tone": "जोश भरने वाला", "themes": ["संघर्ष", "जीत", "हिम्मत"]},
    "temple": {"tone": "पवित्र", "themes": ["पुराना", "पूजा", "आरती"]},
    "daily_wisdom": {"tone": "गहरी सीख", "themes": ["गीता", "गुरु"]},
}


# ============================================================
# SIMPLE HINDI DICTIONARY (Hard → Easy)
# ============================================================

# Ye examples prompt mein use honge to Gemini samjhe
SIMPLE_HINDI_EXAMPLES = """
मुश्किल शब्द → आसान शब्द:
- विघ्नहर्ता → मुसीबतें दूर करने वाले
- आराधना → पूजा
- साक्षात्कार → दर्शन (मिलना)
- प्रलय → बहुत बड़ी तबाही
- समस्त / सम्पूर्ण → सारे / पूरे
- श्रद्धेय → आदरणीय / सच्चे
- मोक्ष प्राप्ति → जीवन में शांति मिलना
- वंदन → नमस्कार
- स्वरूप → रूप
- प्रकटीकरण → दिखाई देना / प्रकट होना
- असीम कृपा → बहुत बड़ी दया
- कनिष्ठ पुत्र → छोटा बेटा
- ज्येष्ठ पुत्र → बड़ा बेटा
- लोकिक → दुनियादारी वाला
- आलौकिक → अद्भुत / अजीब
- पारंगत → माहिर
- प्रज्ञा → समझदारी
- तत्पर → तैयार
- व्याप्त → फैला हुआ
- निर्वाण → मोक्ष / शांति
- स्थापित → रखा गया
"""


# ============================================================
# HELPERS
# ============================================================

def _get_cache_key(topic: str, category: str) -> str:
    return hashlib.md5(f"{topic}|{category}".encode()).hexdigest()


def _extract_response_text(response) -> str:
    try:
        return response.text.strip()
    except Exception:
        pass
    try:
        parts = response.candidates[0].content.parts
        return " ".join([p.text for p in parts if hasattr(p, 'text')]).strip()
    except Exception:
        pass
    raise Exception("Cannot extract response text")


def _clean_story(raw: str) -> str:
    """Clean AI artifacts from story"""

    # Remove common AI prefixes
    prefixes = [
        "here is your story:", "here is the story:", "story:",
        "यहाँ है", "यह रही कहानी", "कहानी:",
        "sure!", "of course", "**story:**", "```",
        "here's", "here is a", "certainly",
        "word count:", "words:", "total words:"
    ]

    raw_lower = raw.lower()
    for prefix in prefixes:
        if raw_lower.startswith(prefix):
            for sep in [':', '\n']:
                if sep in raw:
                    raw = raw.split(sep, 1)[1].strip()
                    break
            break

    # Remove wrapping quotes
    raw = raw.strip('"\'`')

    # Remove markdown
    raw = re.sub(r'\*\*(.*?)\*\*', r'\1', raw)
    raw = re.sub(r'\*(.*?)\*', r'\1', raw)
    raw = re.sub(r'```[\w]*\n?', '', raw)
    raw = raw.replace('```', '')

    # Remove position markers like (1), (32), etc.
    raw = re.sub(r'\(\d+\)', '', raw)

    # Remove word count annotations
    raw = re.sub(r'\[.*?word.*?\]', '', raw, flags=re.IGNORECASE)
    raw = re.sub(r'\(word count.*?\)', '', raw, flags=re.IGNORECASE)

    # Normalize whitespace
    raw = re.sub(r'\n{3,}', '\n\n', raw)
    raw = re.sub(r' +', ' ', raw)

    return raw.strip()


def _count_hindi_words(text: str) -> int:
    """Count words in Hindi text"""
    words = [w for w in text.split() if w.strip()]
    return len(words)


def _validate_story(story: str) -> tuple:
    """
    RELAXED validation (accepts wider range).
    V2.1: 130-220 words acceptable
    """
    if not story or len(story) < 50:
        return False, f"Story too short: {len(story)} chars"

    word_count = _count_hindi_words(story)

    if word_count < 130:
        return False, f"Too few words: {word_count} (need 130+)"

    if word_count > 220:
        return False, f"Too many words: {word_count} (max 220)"

    # AI phrase check
    ai_phrases = ["as an ai", "language model", "i cannot", "i am unable"]
    if any(phrase in story.lower() for phrase in ai_phrases):
        return False, "Contains AI phrases"

    # Devanagari check
    devanagari_count = sum(1 for c in story if '\u0900' <= c <= '\u097F')
    if devanagari_count < len(story) * 0.5:
        return False, "Not enough Hindi (need 50%+ Devanagari)"

    return True, f"Valid ({word_count} words)"


# ============================================================
# V2.1: PROMPT BUILDERS (Simple Hindi + Progressive Strictness)
# ============================================================

def _build_prompt_attempt_1(memory: AgentMemory) -> str:
    """Attempt 1: Simple language, detailed"""
    style = CATEGORY_STORY_STYLE.get(memory.category, {})

    festival_context = ""
    if memory.is_festival:
        festival_context = f"\n🎉 आज {memory.festival_name} है।"

    return f"""तुम एक कहानीकार हो जो YouTube/Instagram Reels के लिए कहानियां लिखते हो।

📌 विषय: {memory.topic}
📂 श्रेणी: {memory.category}
🎭 भाव: {memory.mood}
{festival_context}

═══════════════════════════════════════════
🎯 सबसे ज़रूरी बात: भाषा एकदम आसान होनी चाहिए
═══════════════════════════════════════════

तुम्हारी कहानी ऐसी हो कि:
✅ 8 साल का बच्चा भी समझ जाए
✅ 80 साल के बुजुर्ग भी समझ जाएं  
✅ पढ़े-लिखे और अनपढ़ दोनों समझ जाएं
✅ गांव और शहर दोनों के लोग समझ जाएं

❌ ये मुश्किल शब्द मत लिखो:
{SIMPLE_HINDI_EXAMPLES}

═══════════════════════════════════════════
📏 EXACTLY 150-180 शब्दों की कहानी लिखो
═══════════════════════════════════════════

STRUCTURE (3 हिस्से):
━━━━━━━━━━━━━━━━━━━━━━━
Part 1: शुरुआत (20-30 शब्द)
- ऐसा सवाल या बात जो सुनने वाले को रोक दे
- "क्या आप जानते हैं...?"
- Example: "क्या आप जानते हैं भगवान गणेश को मोदक क्यों पसंद है?"

Part 2: कहानी (100-130 शब्द)
- मुख्य कहानी (5-6 sentences)
- घटना, पात्र, क्या हुआ
- सरल शब्दों में
- जैसे आप किसी को बात बता रहे हो

Part 3: सीख + Call to Action (20-30 शब्द)
- कहानी से क्या सीखा
- "अगर पसंद आई तो Save करें, Share करें 🙏"
━━━━━━━━━━━━━━━━━━━━━━━

⚠️ IMPORTANT RULES:
1. HINDI (देवनागरी) में लिखो
2. Words: 150-180 (गिनकर लिखो)
3. एकदम आसान भाषा (जैसे घर में बात करते हैं)
4. Small sentences (5-8 words each)
5. Real कहानी सुनाने जैसा tone

❌ NO:
- Complex Sanskrit words
- English words (except: Save, Share, Follow, Comment)
- Poetry/shayari style
- Preachy tone
- Meta text ("Here is the story")

✅ YES:
- Conversational tone (बातचीत जैसा)
- Simple everyday words
- Short punchy sentences
- Emotional connection

अब {memory.topic} पर एक आसान सी Hindi कहानी लिखो।
150-180 शब्दों में। सीधे कहानी से शुरू करो।"""


def _build_prompt_attempt_2(memory: AgentMemory) -> str:
    """Attempt 2: STRICTER + Simple Hindi emphasis"""
    return f"""तुम्हारा काम: {memory.topic} पर 150-180 words की **आसान Hindi** कहानी लिखना।

🚨 पिछली कोशिश में कहानी बहुत छोटी थी। इस बार लंबी लिखो।

═══════════════════════════════════════════
🎯 भाषा नियम (सबसे ज़रूरी!)
═══════════════════════════════════════════

एकदम SIMPLE Hindi में लिखो:
- जैसे तुम अपनी दादी को कहानी सुना रहे हो
- जैसे तुम बच्चों को कहानी सुना रहे हो  
- कोई मुश्किल शब्द नहीं
- कोई शास्त्रीय भाषा नहीं

Example (Comparison):
❌ मुश्किल: "श्रद्धेय भक्तों ने विघ्नहर्ता की आराधना की"
✅ आसान: "भक्तों ने भगवान गणेश की पूजा की"

❌ मुश्किल: "प्रभु ने अपने भक्त को दर्शन देकर मुक्ति प्रदान की"
✅ आसान: "भगवान अपने भक्त को दिखाई दिए और उसकी परेशानी दूर की"

❌ मुश्किल: "उसकी असीम कृपा से समस्त कार्य सम्पन्न हुए"
✅ आसान: "उनकी दया से सारे काम अच्छे से हो गए"

देखा? आसान शब्द, छोटे sentences, सबको समझ आयेगा।

═══════════════════════════════════════════
📏 WORD COUNT (150-180 words)
═══════════════════════════════════════════

3 paragraphs चाहिए, हर paragraph में 50-60 words:

PARAGRAPH 1 (50-60 शब्द) - HOOK:
"क्या आप जानते हैं..." se शुरू करो
{memory.topic} की एक interesting बात बताओ
सुनने वाले को curious बनाओ
5-6 short sentences

PARAGRAPH 2 (60-70 शब्द) - मुख्य कहानी:
पूरी कहानी (कब, कहां, कौन, क्या, कैसे)
6-7 short sentences
जीवंत details
आसान words में

PARAGRAPH 3 (30-40 शब्द) - सीख + CTA:
कहानी से क्या समझा
जीवन में कैसे काम आयेगा
"पसंद आई? Save करें, Share करें 🙏"

═══════════════════════════════════════════

Category: {memory.category}
Topic: {memory.topic}

अब कहानी लिखो — 150-180 words, आसान Hindi में।
कोई मुश्किल शब्द नहीं। जैसे बच्चों को बता रहे हो।
सीधे कहानी शुरू करो।"""


def _build_prompt_attempt_3(memory: AgentMemory) -> str:
    """Attempt 3: DESPERATE - simple language + explicit count"""
    return f"""URGENT: {memory.topic} पर लंबी और आसान Hindi कहानी लिखो।

⚠️ 2 सबसे ज़रूरी बातें:
1. कम से कम 160 शब्द होने चाहिए
2. भाषा एकदम आसान हो - सबको समझ आये

═══════════════════════════════════════════
📖 भाषा का Example
═══════════════════════════════════════════

❌ ऐसा MAT लिखो:
"विघ्नहर्ता प्रभु ने अपने श्रद्धेय भक्त की आराधना स्वीकार 
करते हुए उसे मोक्ष प्रदान किया।"

✅ ऐसा लिखो:
"भगवान गणेश ने अपने भक्त की पूजा को स्वीकार किया 
और उसकी सारी मुसीबतें दूर कर दीं।"

देखा? आसान शब्द, small sentence, सबको समझ आयेगा।

═══════════════════════════════════════════
📊 Sentence Length Guide
═══════════════════════════════════════════

- Short: "गणेश जी ने कहा।" = 3 words
- Medium: "एक गरीब भक्त बहुत परेशान था।" = 6 words  
- Long: "उसने रोते हुए भगवान से प्रार्थना की कि उसकी मदद करें।" = 11 words

Target: 20-25 medium sentences = 160-180 words ✅

═══════════════════════════════════════════

Topic: {memory.topic}
Category: {memory.category}

Requirements:
- **20-25 sentences** लिखो
- आसान Hindi (जैसे घर में बात करते हैं)
- Story format (कहानी की तरह)
- Beginning: Interesting hook (4-5 sentences)
- Middle: पूरी कहानी (12-15 sentences)
- End: सीख + Save/Share (3-5 sentences)

Avoid these hard words:
- विघ्नहर्ता (use: मुसीबतें दूर करने वाले)
- आराधना (use: पूजा)
- साक्षात्कार (use: दर्शन / मिलना)
- प्रलय (use: बहुत बड़ी तबाही)
- समस्त (use: सारे)
- श्रद्धेय (use: आदरणीय)
- असीम कृपा (use: बहुत बड़ी दया)

अब 20+ short sentences की आसान Hindi कहानी लिखो।
160-180 words। मुश्किल शब्द नहीं।
सीधे शुरू करो।"""


# ============================================================
# V2.1: SIMPLE HINDI FALLBACK STORIES (150+ words)
# ============================================================

def _get_fallback_story(memory: AgentMemory) -> str:
    """Emergency fallback - simple Hindi stories (150+ words)"""

    category = memory.category
    topic = memory.topic

    fallback_templates = {
        "krishna": (
            f"क्या आप जानते हैं कि कान्हा की बांसुरी में ऐसा क्या था? "
            f"जब भी वो बांसुरी बजाते, तो सब कुछ रुक जाता था। "
            f"पेड़ भी सुनते, पक्षी भी सुनते, यहां तक कि यमुना का पानी भी शांत हो जाता।\n\n"
            f"वृंदावन में गोपियां अपना काम छोड़ देतीं। "
            f"गायें अपने आप कान्हा के पास दौड़ी चली आतीं। "
            f"राधा रानी तो बांसुरी सुनते ही सब कुछ भूल जाती थीं। "
            f"वो बांसुरी सिर्फ लकड़ी का टुकड़ा नहीं थी। "
            f"वो प्यार की आवाज़ थी। "
            f"जब भी कोई सच्चे दिल से भगवान को याद करता है, "
            f"वो आवाज़ आज भी सुनाई देती है। "
            f"बस दिल से सुनने वाला होना चाहिए।\n\n"
            f"आज भी अगर आप शांत मन से बैठें और भगवान को याद करें, "
            f"तो आपको भी कान्हा की बांसुरी सुनाई देगी। "
            f"बस विश्वास होना चाहिए।\n\n"
            f"पसंद आया तो Save करें, Share करें 🙏 राधे राधे 🌸"
        ),
        "shiva": (
            f"क्या आप जानते हैं महादेव का तांडव नृत्य क्या है? "
            f"जब भी दुनिया में गलत बहुत बढ़ जाता है, "
            f"तो शिव जी अपना नाच शुरू करते हैं।\n\n"
            f"कैलाश पर्वत पर बैठे भगवान शिव बहुत शांत रहते हैं। "
            f"पर जब बुराई हद से बाहर जाती है, तो उनका तीसरा नेत्र खुल जाता है। "
            f"वो अपना डमरू बजाते हैं और नाचना शुरू करते हैं। "
            f"पूरी दुनिया कांप उठती है। "
            f"पर ये नाच बर्बाद करने के लिए नहीं होता। "
            f"ये पुराना खत्म करके नया बनाने के लिए होता है। "
            f"जो पुरानी चीज़ें रोक रही थीं, वो हट जाती हैं।\n\n"
            f"हमारी ज़िंदगी में भी ऐसा होता है। "
            f"जब कुछ पुराना नहीं छूटता, तो नया आ नहीं पाता। "
            f"शिव जी सिखाते हैं - जो जाना है, उसे जाने दो।\n\n"
            f"Save करें, Share करें 🙏 हर हर महादेव 🕉️"
        ),
        "hanuman": (
            f"क्या आप जानते हैं हनुमान जी को अपनी ताकत का पता कैसे चला? "
            f"जब वो छोटे थे, तो उन्हें खुद अपनी शक्ति का पता नहीं था। "
            f"वो एक साधारण बंदर की तरह रहते थे।\n\n"
            f"जब भगवान राम की पत्नी सीता जी को रावण उठा ले गया, "
            f"तो सब मिलकर उन्हें ढूंढने निकले। "
            f"समुद्र किनारे पहुंचकर सब रुक गए। "
            f"इतना बड़ा समुद्र कोई कैसे पार करे? "
            f"तब जामवंत जी ने हनुमान जी को याद दिलाया - "
            f"'तुम पवन देवता के बेटे हो। तुम्हारे लिए कुछ भी मुश्किल नहीं।' "
            f"बस इतना सुनते ही हनुमान जी बड़े हो गए। "
            f"एक ही छलांग में समुद्र पार किया। "
            f"लंका जलाई और सीता माता को खोज लिया।\n\n"
            f"ये कहानी हमें सिखाती है - हमारे अंदर भी बहुत ताकत है। "
            f"बस अपने आप पर विश्वास होना चाहिए।\n\n"
            f"जय बजरंगबली! 🚩 Save करें 🙏"
        ),
        "ganesha": (
            f"क्या आप जानते हैं भगवान गणेश को 'मुसीबतें दूर करने वाले' क्यों कहते हैं? "
            f"क्योंकि जो भी सच्चे दिल से उन्हें याद करता है, "
            f"उसकी हर परेशानी दूर हो जाती है।\n\n"
            f"एक बार सारे देवताओं ने सोचा - सबसे पहले पूजा किसकी हो? "
            f"शर्त रखी - जो पहले पूरी दुनिया का चक्कर लगा कर आएगा, वो जीतेगा। "
            f"कार्तिकेय अपने मोर पर बैठकर तुरंत निकल पड़े। "
            f"गणेश जी के पास तो चूहा था, वो कैसे इतनी दूर जाते? "
            f"पर गणेश जी बहुत समझदार थे। "
            f"उन्होंने अपने मां-बाप शिव-पार्वती के चारों तरफ चक्कर लगाया। "
            f"बोले - 'मेरे लिए तो आप ही सारी दुनिया हो।' "
            f"उनकी ये बात सबको बहुत पसंद आई। "
            f"तब से हर शुभ काम में पहले गणेश जी की पूजा होती है।\n\n"
            f"ये कहानी सिखाती है - मां-बाप का सम्मान करो, "
            f"बाकी सब अपने आप ठीक हो जाएगा।\n\n"
            f"गणपति बाप्पा मोरया! 🐘 Save करें 🙏"
        ),
        "durga": (
            f"क्या आप जानते हैं मां दुर्गा ने महिषासुर को कैसे हराया था? "
            f"महिषासुर एक बहुत बड़ा राक्षस था। "
            f"उसने वरदान ले रखा था कि उसे कोई मर्द नहीं मार सकता।\n\n"
            f"वो राक्षस बहुत घमंडी हो गया था। "
            f"उसने देवताओं को भी परेशान करना शुरू कर दिया। "
            f"सब देवता मिलकर ब्रह्मा जी के पास गए। "
            f"तब सारे देवताओं ने अपनी शक्ति मिलाकर एक शक्ति बनाई। "
            f"वो शक्ति थी मां दुर्गा। "
            f"उन्हें शेर की सवारी दी गई। "
            f"हर हाथ में एक हथियार दिया गया। "
            f"मां दुर्गा ने 9 दिन तक महिषासुर से लड़ाई की। "
            f"आखिर में उसे मार गिराया।\n\n"
            f"ये कहानी सिखाती है - जब मिलजुल कर काम करते हैं, "
            f"तो बड़ी से बड़ी मुसीबत हार जाती है।\n\n"
            f"जय माता दी! 🚩 Save करें, Share करें 🙏"
        ),
        "ram": (
            f"क्या आप जानते हैं भगवान राम ने 14 साल का वनवास क्यों काटा? "
            f"अपने पिता के वचन को पूरा करने के लिए। "
            f"चाहे अपने आप को कितना भी नुकसान हो।\n\n"
            f"जब राजा दशरथ ने कैकेयी माता को वचन दिया था, "
            f"तो कैकेयी ने भरत को राजा बनाने और राम को वनवास भेजने को कहा। "
            f"राम जी को पता चला तो एक बार भी नहीं रोए। "
            f"बस मुस्कुरा कर बोले - पिता का वचन ही सब कुछ है। "
            f"वो अपनी पत्नी सीता और भाई लक्ष्मण के साथ जंगल चले गए। "
            f"14 साल तक जंगल में रहे। "
            f"राक्षसों से लड़ाई की। "
            f"रावण को मार कर सीता को वापस लाए।\n\n"
            f"ये कहानी सिखाती है - अपने मां-बाप की बात मानो, "
            f"अपना धर्म कभी मत छोड़ो।\n\n"
            f"जय श्री राम! 🚩 Save करें 🙏"
        ),
    }

    # Return category-specific or generic
    if category in fallback_templates:
        return fallback_templates[category]

    # Generic simple fallback
    return (
        f"क्या आप जानते हैं ज़िंदगी का सबसे बड़ा राज़ क्या है? "
        f"ये राज़ हमारे पुराने ग्रंथों में बहुत पहले बताया गया था। "
        f"पर आज की भागदौड़ में हम इसे भूल गए हैं।\n\n"
        f"{topic} इसी सच्चाई की एक अच्छी मिसाल है। "
        f"हमारे शास्त्रों में लिखा है कि जो भी सच्चे दिल से भगवान को याद करता है, "
        f"उसे कभी किसी चीज़ की कमी नहीं होती। "
        f"ज़िंदगी में सुख और दुख आते जाते रहते हैं। "
        f"पर जो अपने विश्वास पर टिका रहता है, वो हर तूफान पार कर लेता है। "
        f"भगवान श्री कृष्ण ने गीता में कहा है - 'काम करो, फल की चिंता मत करो।' "
        f"जब हम अपना काम अच्छे से करते हैं, तो नतीजा अपने आप अच्छा होता है।\n\n"
        f"आज से एक बदलाव लाइए। "
        f"हर सुबह भगवान को थैंक यू कहिए। "
        f"सब कुछ अच्छा होगा।\n\n"
        f"अगर ये बात दिल को छू गई, तो Save करें और Share करें 🙏"
    )


# ============================================================
# GEMINI CALL WITH SMART RETRIES
# ============================================================

def _try_generate(prompt: str, attempt_num: int) -> str:
    """Single Gemini call with proper settings"""

    model = genai.GenerativeModel(GEMINI_MODEL)

    # More tokens for longer stories
    max_tokens = 2000 + (attempt_num * 500)  # 2000, 2500, 3000

    # Higher temperature for creativity (but not too high)
    temperature = min(0.85 + (attempt_num * 0.05), 1.0)

    response = model.generate_content(
        prompt,
        generation_config={
            "temperature": temperature,
            "max_output_tokens": max_tokens,
            "top_p": 0.95,
            "top_k": 40,
        }
    )

    raw = _extract_response_text(response)
    return _clean_story(raw)


# ============================================================
# MAIN AGENT FUNCTION
# ============================================================

def run(memory: AgentMemory) -> AgentMemory:
    """
    Generate Hindi story with progressive prompts.

    V2.1 STRATEGY:
    - Attempt 1: Normal prompt (simple language)
    - Attempt 2: STRICTER prompt (word count emphasis)
    - Attempt 3-5: DESPERATE prompt (explicit sentence count)
    - Fallback: Category-specific 150+ word simple template
    """
    logger.info("=" * 55)
    logger.info("=== STORY WRITER V2.1 शुरू ===")
    logger.info("=" * 55)
    logger.info(f"📌 विषय: {memory.topic[:60]}")
    logger.info(f"📂 श्रेणी: {memory.category}")

    if not memory.topic:
        logger.error("❌ Topic missing")
        memory.add_error("story_writer", "Topic missing")
        memory.reel_story = _get_fallback_story(memory)
        return memory

    # Cache check
    cache_key = _get_cache_key(memory.topic, memory.category)
    if cache_key in _story_cache:
        logger.info("💾 Cache hit")
        memory.reel_story = _story_cache[cache_key]
        return memory

    # ══════════════════════════════════════════
    # PROGRESSIVE ATTEMPTS
    # ══════════════════════════════════════════
    max_attempts = 5
    story = None
    best_story = None  # Keep track of best attempt (even if short)
    best_word_count = 0

    for attempt in range(1, max_attempts + 1):
        try:
            # Choose prompt based on attempt
            if attempt == 1:
                prompt = _build_prompt_attempt_1(memory)
                strategy = "Normal (Simple Hindi)"
            elif attempt == 2:
                prompt = _build_prompt_attempt_2(memory)
                strategy = "Stricter (Simple + Longer)"
            else:
                # Attempt 3, 4, 5 use desperate prompt with variation
                prompt = _build_prompt_attempt_3(memory)
                strategy = f"Desperate (attempt {attempt})"

            logger.info(f"🤖 Gemini attempt {attempt}/{max_attempts} — {strategy}")

            cleaned = _try_generate(prompt, attempt)
            word_count = _count_hindi_words(cleaned)

            # Track best story so far
            if word_count > best_word_count:
                best_story = cleaned
                best_word_count = word_count

            # Validate
            is_valid, reason = _validate_story(cleaned)

            if is_valid:
                story = cleaned
                logger.info(f"✅ Story valid on attempt {attempt} — {reason}")
                break
            else:
                logger.warning(f"⚠️  Attempt {attempt} invalid: {reason}")

                # If close to valid (120-129 words), accept it
                if 120 <= word_count < 130 and attempt >= 3:
                    logger.info(f"✅ Accepting borderline story ({word_count} words)")
                    story = cleaned
                    break

                if attempt < max_attempts:
                    time.sleep(2)

        except Exception as e:
            logger.warning(f"❌ Attempt {attempt} failed: {e}")
            if attempt < max_attempts:
                time.sleep(3)

    # ══════════════════════════════════════════
    # FINAL DECISION
    # ══════════════════════════════════════════
    if story:
        # Success!
        memory.reel_story = story
        _story_cache[cache_key] = story

        word_count = _count_hindi_words(story)
        logger.info("=" * 55)
        logger.info(f"✅ STORY WRITER SUCCESS")
        logger.info("=" * 55)
        logger.info(f"📏 Words: {word_count}")
        logger.info(f"📄 Preview: {story[:100]}...")
        logger.info("=" * 55)

    elif best_story and best_word_count >= 100:
        # Use best attempt (even if slightly short)
        logger.warning(f"⚠️  Using best attempt ({best_word_count} words) instead of fallback")
        memory.reel_story = best_story
        _story_cache[cache_key] = best_story

    else:
        # All failed - use category fallback
        logger.warning("⚠️  All attempts failed. Using category fallback template.")
        memory.reel_story = _get_fallback_story(memory)
        logger.info(f"📄 Fallback words: {_count_hindi_words(memory.reel_story)}")

    logger.info("=== STORY WRITER पूर्ण ===\n")
    return memory


# ============================================================
# STANDALONE TEST
# ============================================================

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("STORY WRITER V2.1 - TEST (Simple Hindi)")
    print("=" * 60 + "\n")

    test_cases = [
        {
            "topic": "Ganesha blessing devotees removing obstacles vighnaharta",
            "category": "ganesha",
            "mood": "auspicious, joyful",
            "visual_elements": ["modak", "lotus"],
            "is_festival": False,
        },
        {
            "topic": "Krishna playing flute in Vrindavan",
            "category": "krishna",
            "mood": "peaceful, divine, romantic",
            "visual_elements": ["flute", "cows"],
            "is_festival": False,
        },
    ]

    for test in test_cases:
        print(f"\n{'=' * 60}")
        print(f"Topic: {test['topic']}")
        print("=" * 60)

        memory = AgentMemory()
        memory.topic = test["topic"]
        memory.category = test["category"]
        memory.mood = test["mood"]
        memory.visual_elements = test["visual_elements"]
        memory.is_festival = test["is_festival"]
        memory.post_type = "reel"

        result = run(memory)

        print(f"\n📝 STORY:\n{result.reel_story}\n")
        print(f"📊 Words: {_count_hindi_words(result.reel_story)}")
        print(f"📏 Chars: {len(result.reel_story)}")