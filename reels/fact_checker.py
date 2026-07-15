"""
Fact Checker - Verify mythology accuracy in Hindi story

Purpose:
- Check historical/mythological accuracy
- Remove false information
- Correct Sanskrit terms
- Ensure respectful language
- Verify deity attributes

If story is 100% accurate → return as-is
If issues found → get corrected version from Gemini
If Gemini fails → return original with warning
"""
import re
import time
import json
import google.generativeai as genai

from core.memory import AgentMemory
from config.settings import GEMINI_API_KEY, GEMINI_MODEL
from utils.logger import get_logger

genai.configure(api_key=GEMINI_API_KEY)
logger = get_logger("fact_checker")


# ============================================================
# COMMON FACTUAL ERRORS TO WATCH FOR
# ============================================================

COMMON_ERRORS_HINDI = [
    # Wrong attributes
    ("श्रीकृष्ण की 8 पत्नियां", "श्रीकृष्ण की 8 पटरानी और 16108 रानियां"),
    ("शिव के 5 सिर", "शिव सामान्यतः 1 मुख वाले हैं, पंचमुखी विशेष रूप है"),
    ("राम ने 14 वर्ष का वनवास स्वेच्छा से चुना", "राम को कैकेयी के कारण 14 वर्ष का वनवास मिला"),

    # Wrong locations
    ("कृष्ण द्वारका में जन्मे", "कृष्ण का जन्म मथुरा में हुआ, द्वारका उनकी नगरी थी"),
    ("गंगा हिमालय से निकलती है", "गंगा गंगोत्री (हिमालय) से निकलती है"),

    # Wrong relationships
    ("कर्ण पांडवों का सबसे छोटा भाई", "कर्ण कुंती का पहला पुत्र था (सूर्य से जन्मा)"),
    ("बलराम कृष्ण के छोटे भाई", "बलराम कृष्ण के बड़े भाई थे"),
]


# ============================================================
# CATEGORY-SPECIFIC FACT-CHECK POINTS
# ============================================================

FACT_CHECK_FOCUS = {
    "krishna": [
        "जन्म स्थान: मथुरा (कारागार में)",
        "माता-पिता: देवकी और वसुदेव (जन्म), यशोदा और नंद (पालन)",
        "भाई-बहन: बलराम (बड़े भाई), सुभद्रा (बहन)",
        "पत्नियां: 8 पटरानी + 16108 रानियां",
        "मुख्य पत्नी: रुक्मिणी (पहली), सत्यभामा",
        "राधा: प्रेम, विवाह नहीं",
        "कर्मस्थली: वृंदावन, द्वारका, कुरुक्षेत्र",
        "गीता: कुरुक्षेत्र में अर्जुन को उपदेश",
    ],
    "shiva": [
        "निवास: कैलाश पर्वत",
        "पत्नी: पार्वती (सती के बाद पुनर्जन्म)",
        "पुत्र: गणेश, कार्तिकेय",
        "वाहन: नंदी (बैल)",
        "अस्त्र: त्रिशूल, डमरू",
        "गंगा: जटाओं में धारण की",
        "तीसरा नेत्र: प्रलय की शक्ति",
        "नीलकंठ: समुद्र मंथन में विष पीने से",
    ],
    "hanuman": [
        "जन्म: अंजना माता से, वायु देव के आशीर्वाद से",
        "पिता: केसरी (वानरराज), दिव्य पिता: वायु",
        "गुरु: सूर्य देव",
        "मुख्य कार्य: राम की सेवा, सीता खोज",
        "शक्तियां: अष्ट सिद्धि, नौ निधि के दाता",
        "चिरंजीवी: आज भी जीवित माने जाते हैं",
    ],
    "ram": [
        "जन्म: अयोध्या में, कौशल्या और दशरथ से",
        "भाई: लक्ष्मण, भरत, शत्रुघ्न",
        "पत्नी: सीता (जनक की पुत्री)",
        "वनवास: 14 वर्ष (कैकेयी के कारण)",
        "लंका विजय: रावण का वध",
        "पुत्र: लव और कुश",
    ],
    "durga": [
        "9 रूप (नवदुर्गा): शैलपुत्री, ब्रह्मचारिणी, चंद्रघंटा, कूष्मांडा, स्कंदमाता, कात्यायनी, कालरात्रि, महागौरी, सिद्धिदात्री",
        "वाहन: सिंह",
        "प्रमुख अस्त्र: त्रिशूल, चक्र, गदा, धनुष-बाण",
        "महिषासुर वध: दुर्गा सप्तशती में वर्णन",
    ],
    "ganesha": [
        "पिता: शिव, माता: पार्वती",
        "भाई: कार्तिकेय",
        "वाहन: मूषक (चूहा)",
        "प्रिय भोजन: मोदक",
        "एकदंत: परशुराम से युद्ध में एक दांत टूटा",
        "गजानन: शिव द्वारा हाथी का सिर लगाया गया",
    ],
}


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def _extract_response_text(response) -> str:
    """Extract text from Gemini response"""
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


def _clean_json_response(raw: str) -> str:
    """Clean Gemini JSON response"""
    raw = re.sub(r'```json\s*', '', raw)
    raw = re.sub(r'```\s*', '', raw)

    start = raw.find('{')
    end = raw.rfind('}')

    if start != -1 and end != -1 and end > start:
        raw = raw[start:end + 1]

    return raw.strip()


def _clean_story(raw: str) -> str:
    """Clean AI artifacts from corrected story"""
    prefixes = [
        "here is the corrected story:", "corrected story:",
        "यहाँ है", "सुधारी हुई कहानी:", "correction:",
        "sure!", "here:", "**corrected story:**"
    ]

    raw_lower = raw.lower()
    for prefix in prefixes:
        if raw_lower.startswith(prefix):
            for sep in [':', '\n']:
                if sep in raw:
                    raw = raw.split(sep, 1)[1].strip()
                    break
            break

    # Remove quotes and markdown
    raw = raw.strip('"\'')
    raw = re.sub(r'\*\*(.*?)\*\*', r'\1', raw)
    raw = re.sub(r'\*(.*?)\*', r'\1', raw)
    raw = re.sub(r'\n{3,}', '\n\n', raw)

    return raw.strip()


def _build_fact_check_prompt(story: str, category: str, topic: str) -> str:
    """Build fact-check prompt for Gemini"""

    # Get category-specific facts
    facts = FACT_CHECK_FOCUS.get(category, [])
    facts_text = "\n".join([f"• {f}" for f in facts]) if facts else "General mythology facts"

    prompt = f"""तुम एक expert Hindu mythology fact-checker हो।

═══════════════════════════════════════════
📌 विषय: {topic}
📂 श्रेणी: {category}
═══════════════════════════════════════════

📖 STORY जो check करनी है:


═══════════════════════════════════════════
✅ IMPORTANT FACTS ({category}):
═══════════════════════════════════════════

{facts_text}

═══════════════════════════════════════════
🔍 CHECK FOR:
═══════════════════════════════════════════

1. Factual accuracy (नाम, स्थान, संबंध, घटनाएं)
2. Incorrect deity attributes
3. Wrong locations या timing
4. Misrepresented mythology
5. Disrespectful language
6. Sanskrit terms का सही उपयोग
7. Historical timeline accuracy

═══════════════════════════════════════════
📤 OUTPUT FORMAT (JSON only):
═══════════════════════════════════════════

Return ONLY valid JSON. No markdown, no explanation.

{{
    "is_accurate": true/false,
    "confidence": 0.0-1.0,
    "issues_found": ["issue 1", "issue 2"],
    "needs_correction": true/false,
    "corrected_story": "यदि needs_correction है तो पूरी corrected story यहां (same length, same style, sirf facts fix)"
}}

═══════════════════════════════════════════
RULES:
═══════════════════════════════════════════

- अगर story 100% accurate है:
  → is_accurate: true, needs_correction: false, corrected_story: ""

- अगर minor issues हैं (जैसे 1-2 fact wrong):
  → is_accurate: false, needs_correction: true, corrected_story: [FULL CORRECTED STORY]

- corrected_story same length रखो ({len(story.split())} words approx)
- Same tone, same flow, sirf facts fix करो
- Beginning और ending same style रखो

अब JSON return करो:"""

    return prompt


# ============================================================
# MAIN AGENT FUNCTION
# ============================================================

def run(memory: AgentMemory) -> AgentMemory:
    """
    Fact-check the reel story

    Flow:
    1. If no story → skip (nothing to check)
    2. Call Gemini with fact-check prompt
    3. Parse JSON response
    4. If issues found → use corrected version
    5. If no issues → keep original
    6. Set reel_fact_checked = True
    """
    logger.info("=" * 55)
    logger.info("=== FACT CHECKER शुरू ===")
    logger.info("=" * 55)

    # Validate input
    if not memory.reel_story:
        logger.warning("⚠️  कोई story नहीं है - skip कर रहे हैं")
        memory.add_error("fact_checker", "No story to check")
        return memory

    if not memory.category:
        logger.warning("⚠️  Category नहीं है - basic check ही होगा")

    logger.info(f"📖 Story length: {len(memory.reel_story.split())} words")
    logger.info(f"📂 Category: {memory.category}")

    # ── Build prompt ─────────────────────────────────────────
    prompt = _build_fact_check_prompt(
        story=memory.reel_story,
        category=memory.category,
        topic=memory.topic
    )

    # ── Gemini call with retries ────────────────────────────
    max_attempts = 2  # Less retries - fact check is optional
    fact_check_result = None

    for attempt in range(1, max_attempts + 1):
        try:
            logger.info(f"🤖 Gemini fact-check कोशिश {attempt}/{max_attempts}")

            model = genai.GenerativeModel(GEMINI_MODEL)

            response = model.generate_content(
                prompt,
                generation_config={
                    "temperature": 0.3,  # Low temp for accuracy
                    "max_output_tokens": 2000,
                    "top_p": 0.9,
                }
            )

            raw = _extract_response_text(response)
            cleaned_json = _clean_json_response(raw)

            fact_check_result = json.loads(cleaned_json)
            logger.info(f"✅ Fact-check completed on attempt {attempt}")
            break

        except json.JSONDecodeError as e:
            logger.warning(f"⚠️  JSON parse failed (attempt {attempt}): {e}")
            if attempt < max_attempts:
                time.sleep(2)
        except Exception as e:
            logger.warning(f"❌ Attempt {attempt} failed: {e}")
            if attempt < max_attempts:
                time.sleep(3)

    # ── Process result ──────────────────────────────────────
    if fact_check_result is None:
        # All attempts failed - keep original story but mark as unchecked
        logger.warning("⚠️  Fact check failed. Story marked as unverified but keeping original.")
        memory.reel_fact_checked = False
        memory.add_error("fact_checker", "Gemini fact-check failed")
    else:
        is_accurate = fact_check_result.get("is_accurate", False)
        confidence = fact_check_result.get("confidence", 0.5)
        issues = fact_check_result.get("issues_found", [])
        needs_correction = fact_check_result.get("needs_correction", False)

        logger.info(f"📊 Accurate: {is_accurate}")
        logger.info(f"📊 Confidence: {confidence:.2f}")

        if issues:
            logger.warning(f"⚠️  Issues found: {len(issues)}")
            for issue in issues[:3]:
                logger.warning(f"   • {issue[:100]}")

        # Apply correction if needed
        if needs_correction and fact_check_result.get("corrected_story"):
            corrected = _clean_story(fact_check_result["corrected_story"])

            if len(corrected) > 100:  # Sanity check
                logger.info("✏️  Story corrected by fact-checker")
                logger.info(f"   Original: {len(memory.reel_story.split())} words")
                logger.info(f"   Corrected: {len(corrected.split())} words")

                memory.reel_story = corrected
                memory.reel_fact_checked = True
            else:
                logger.warning("⚠️  Corrected story too short, keeping original")
                memory.reel_fact_checked = False
        else:
            logger.info("✅ Story is accurate - no correction needed")
            memory.reel_fact_checked = True

    logger.info("=" * 55)
    logger.info(f"✅ FACT CHECKER पूर्ण (checked: {memory.reel_fact_checked})")
    logger.info("=" * 55)

    logger.info("=== FACT CHECKER पूर्ण ===\n")
    return memory


# ============================================================
# STANDALONE TESTING
# ============================================================

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("FACT CHECKER - STANDALONE TEST")
    print("=" * 60 + "\n")

    # Test with intentionally wrong story
    test_story_wrong = (
        "क्या आप जानते हैं कि श्रीकृष्ण द्वारका में जन्मे थे? "
        "उनके पिता वसुदेव और माता देवकी थीं। बलराम उनके छोटे भाई थे। "
        "उन्होंने 8 विवाह किए और सीता उनकी पत्नी थीं।"
    )

    memory = AgentMemory()
    memory.reel_story = test_story_wrong
    memory.topic = "Lord Krishna's birth"
    memory.category = "krishna"

    print(f"📖 Original story:\n{memory.reel_story}\n")

    result = run(memory)

    print(f"\n✅ Fact checked: {result.reel_fact_checked}")
    print(f"\n📖 Final story:\n{result.reel_story}\n")