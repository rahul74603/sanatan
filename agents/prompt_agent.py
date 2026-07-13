"""
Prompt Engineer Agent - AI-Powered Image Prompt Creator
Features:
- Category-specific prompt templates
- Vertex AI-optimized prompts (different than Pollinations)
- Learning from analytics (best performing styles)
- Multi-attempt with progressive enhancement
- Deity-specific artistic references
- Composition intelligence
- Lighting expertise
- Anti-repetition system
- Prompt validation
- Beautiful reporting
"""
import random
import re
import google.generativeai as genai

from core.memory import AgentMemory
from core.database import get_best_performing_styles
from config.settings import GEMINI_API_KEY, GEMINI_MODEL, USE_VERTEX_AI
from utils.logger import get_logger

genai.configure(api_key=GEMINI_API_KEY)
logger = get_logger("prompt_agent")


# ============================================================
# ART STYLES - Categorized & Detailed
# ============================================================

ART_STYLES = {
    "cinematic": {
        "name": "cinematic_photography",
        "prompt": "cinematic photography, shot on Sony A7III, 85mm f/1.4 lens, shallow depth of field, golden hour lighting, film grain, professional color grading, dramatic composition",
        "best_for": ["motivational", "temple", "spiritual_nature", "ram"],
        "quality_boost": "8K resolution, ultra sharp focus"
    },
    "oil_painting": {
        "name": "oil_painting_masterpiece",
        "prompt": "oil painting masterpiece in the style of Raja Ravi Varma, classical Indian art, detailed brushstrokes, rich vibrant colors, museum quality, romantic realism",
        "best_for": ["krishna", "ram", "durga", "festival"],
        "quality_boost": "highly detailed, ornate, gallery-worthy"
    },
    "hyperrealistic": {
        "name": "hyperrealistic_digital_art",
        "prompt": "hyperrealistic digital art, ultra detailed, ArtStation trending, Unreal Engine 5, ray tracing, volumetric lighting, photorealistic rendering",
        "best_for": ["shiva", "hanuman", "durga", "motivational"],
        "quality_boost": "4K resolution, next-gen graphics"
    },
    "moody_atmospheric": {
        "name": "moody_atmospheric",
        "prompt": "moody atmospheric photography, dramatic chiaroscuro lighting, Rembrandt-style shadows, misty ethereal atmosphere, deep contrasts, mysterious sacred vibes",
        "best_for": ["shiva", "ram", "spiritual_nature"],
        "quality_boost": "cinematic mood, deep shadows"
    },
    "divine_golden": {
        "name": "divine_golden_light",
        "prompt": "divine golden light illumination, ethereal celestial glow, heavenly rays, spiritual awakening atmosphere, radiant halo, sacred aura, warm golden tones",
        "best_for": ["krishna", "ganesha", "durga", "festival"],
        "quality_boost": "luminous, transcendent quality"
    },
    "temple_photography": {
        "name": "temple_photography",
        "prompt": "professional temple photography, natural warm lighting, oil lamps glowing, incense smoke, sacred ambience, National Geographic quality, documentary style",
        "best_for": ["temple", "festival_moments", "daily_wisdom"],
        "quality_boost": "authentic, timeless, deeply spiritual"
    },
    "traditional_indian": {
        "name": "traditional_indian_art",
        "prompt": "traditional Indian miniature painting, Mughal art style, intricate gold leaf details, decorative borders, jewel-toned colors, ancient manuscript aesthetic",
        "best_for": ["krishna", "ram", "durga", "ganesha"],
        "quality_boost": "ornate, culturally rich, museum quality"
    },
    "epic_fantasy": {
        "name": "epic_fantasy",
        "prompt": "epic fantasy artwork, cosmic scale, magical atmosphere, powerful divine energy visible, mythological grandeur, celestial background",
        "best_for": ["shiva", "hanuman", "durga"],
        "quality_boost": "awe-inspiring, otherworldly"
    }
}


# ============================================================
# CATEGORY-SPECIFIC ARTISTIC REFERENCES
# ============================================================

CATEGORY_ART_REFERENCES = {
    "krishna": {
        "artists": ["Raja Ravi Varma", "traditional Vrindavan art", "ISKCON style"],
        "elements": [
            "peacock feather crown",
            "bansuri flute at lips",
            "blue-purple skin with divine glow",
            "yellow silk dhoti",
            "lotus flowers",
            "sacred cows nearby",
            "gopis surrounding"
        ],
        "settings": [
            "Vrindavan forest at sunrise",
            "banks of Yamuna river",
            "Kadamba tree background",
            "flower garden"
        ],
        "mood": "divine love, playful, romantic bhakti"
    },
    "shiva": {
        "artists": ["classical Shaivite art", "cosmic realism style"],
        "elements": [
            "third eye with divine glow",
            "crescent moon on head",
            "snake around neck",
            "trishul in hand",
            "damru drum",
            "matted hair with Ganga flowing",
            "tiger skin around waist",
            "ash-smeared body"
        ],
        "settings": [
            "Mount Kailash covered in snow",
            "inside cosmic void with stars",
            "meditation posture on tiger skin",
            "Himalayan cave"
        ],
        "mood": "powerful, mystical, transcendent, cosmic"
    },
    "hanuman": {
        "artists": ["heroic devotional art", "Rajasthani style"],
        "elements": [
            "orange/saffron colored body",
            "gada (mace) in hand",
            "Ram Ram written on body",
            "strong muscular physique",
            "flying pose with wind effect",
            "mountain being carried"
        ],
        "settings": [
            "flying across sky",
            "in Ashok Vatika",
            "tearing open chest showing Ram",
            "mountain landscape"
        ],
        "mood": "powerful devotion, unwavering strength, humble"
    },
    "ganesha": {
        "artists": ["traditional Ganesha iconography", "Maharashtra folk art"],
        "elements": [
            "elephant head with kind eyes",
            "modak (sweet) in trunk",
            "mouse (mushak) at feet",
            "four arms with divine symbols",
            "lotus throne",
            "broken tusk",
            "large ears"
        ],
        "settings": [
            "sitting on lotus",
            "temple decorated with flowers",
            "festival celebration scene",
            "sacred meditation pose"
        ],
        "mood": "auspicious, wise, welcoming, joyful"
    },
    "durga": {
        "artists": ["Bengal school", "Kalighat painting style"],
        "elements": [
            "ten arms with divine weapons",
            "lion vahana beneath",
            "red saree with gold border",
            "third eye glowing",
            "crown with jewels",
            "lotus in hand",
            "trishul and chakra"
        ],
        "settings": [
            "battlefield with demon defeated",
            "temple with lions",
            "celestial mountain top",
            "cosmic space"
        ],
        "mood": "divine feminine power, protective mother, warrior"
    },
    "ram": {
        "artists": ["Ayodhya iconography", "classical Ramayana art"],
        "elements": [
            "bow and arrow (Kodanda)",
            "royal crown with jewels",
            "yellow silk dhoti",
            "tilak on forehead",
            "blue-green skin tone",
            "regal posture"
        ],
        "settings": [
            "ancient royal court of Ayodhya",
            "forest during exile",
            "banks of Sarayu river",
            "battlefield of Lanka"
        ],
        "mood": "noble, righteous, dignified, calm strength"
    },
    "motivational": {
        "artists": ["inspirational photography", "hero's journey aesthetic"],
        "elements": [
            "silhouette against sunrise",
            "warrior pose",
            "mountain peak conquest",
            "light rays breaking through",
            "spiritual symbols in background"
        ],
        "settings": [
            "mountain peak at dawn",
            "vast landscape",
            "cliff overlooking valley",
            "ancient path through forest"
        ],
        "mood": "inspiring, determined, hopeful, empowering"
    },
    "temple": {
        "artists": ["architectural photography", "sacred space photography"],
        "elements": [
            "intricate stone carvings",
            "oil lamps (diyas)",
            "flowers on altar",
            "priests in traditional dress",
            "bells hanging",
            "sacred fire"
        ],
        "settings": [
            "ancient stone temple",
            "morning aarti scene",
            "temple corridor with pillars",
            "outdoor mandap"
        ],
        "mood": "sacred, timeless, peaceful, devotional"
    },
    "spiritual_nature": {
        "artists": ["Ansel Adams style", "spiritual landscape photography"],
        "elements": [
            "Himalayan peaks",
            "sacred rivers",
            "banyan trees",
            "morning mist",
            "meditation setup",
            "lotus in pond"
        ],
        "settings": [
            "Himalayan mountains at sunrise",
            "riverbank at dawn",
            "ancient forest",
            "sacred lake"
        ],
        "mood": "serene, contemplative, connected with nature"
    },
    "festival": {
        "artists": ["Indian festival photography", "vibrant celebration art"],
        "elements": [
            "diyas everywhere",
            "colorful rangoli",
            "flower garlands",
            "traditional decorations",
            "families celebrating"
        ],
        "settings": [
            "decorated temple",
            "traditional Indian home",
            "festival procession",
            "grand celebration"
        ],
        "mood": "joyful, festive, communal, sacred celebration"
    }
}


# ============================================================
# NEGATIVE PROMPT (What to AVOID)
# ============================================================

NEGATIVE_PROMPT = (
    "cartoon, anime, low quality, blurry, distorted, deformed, ugly, "
    "extra limbs, extra fingers, mutated hands, poorly drawn face, "
    "poorly drawn hands, watermark, signature, text, logo, "
    "oversaturated, overexposed, underexposed, bad anatomy, "
    "disfigured, amateur, sketchy, unfinished, weird proportions, "
    "duplicate, cropped, out of frame, worst quality, low resolution, "
    "plastic looking, artificial, fake, uncanny valley, creepy, "
    "modern clothing, western elements, inappropriate content"
)


# ============================================================
# COMPOSITION & LIGHTING
# ============================================================

COMPOSITIONS = [
    "centered composition with divine figure prominent",
    "rule of thirds with sacred elements balanced",
    "symmetric composition emphasizing divinity",
    "portrait framing with soft background blur",
    "wide angle showing majestic setting",
    "close-up detail shot with intricate features",
    "low angle looking up creating majestic feel",
    "dramatic diagonal composition"
]

LIGHTING_STYLES = [
    "golden hour warm lighting with soft shadows",
    "divine glow emanating from within the subject",
    "dramatic side lighting creating strong contrasts",
    "soft diffused morning light",
    "temple lamp warm orange glow",
    "backlit silhouette with rim light halo",
    "cosmic celestial lighting with star field",
    "spotlight effect on main subject",
    "mystical fog with god rays breaking through",
    "sunset warm tones with long shadows"
]


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def _select_best_style(category: str) -> dict:
    """Smart style selection - learning from analytics"""

    # Check analytics for best performing styles
    best_styles = get_best_performing_styles(limit=3)

    if best_styles and len(best_styles) >= 2:
        # 70% use analytics winner, 30% explore
        if random.random() < 0.7:
            top_style_name = best_styles[0]["style"]
            logger.info(f"📊 Using analytics winner: {top_style_name}")

            # Find matching style in our library
            for style_key, style_info in ART_STYLES.items():
                if style_key in top_style_name or top_style_name in style_key:
                    return style_info

    # Filter styles best suited for category
    suitable = [
        (key, info) for key, info in ART_STYLES.items()
        if category in info["best_for"]
    ]

    if suitable:
        chosen_key, chosen_style = random.choice(suitable)
        logger.info(f"🎨 Selected style for {category}: {chosen_key}")
        return chosen_style

    # Random fallback
    chosen_key = random.choice(list(ART_STYLES.keys()))
    logger.info(f"🎲 Random style: {chosen_key}")
    return ART_STYLES[chosen_key]


def _get_category_references(category: str) -> dict:
    """Get detailed artistic references for category"""
    return CATEGORY_ART_REFERENCES.get(
        category,
        CATEGORY_ART_REFERENCES.get("spiritual_nature", {})
    )


def _extract_response_text(response) -> str:
    """Safely extract text from Gemini response"""
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


def _clean_prompt(prompt: str) -> str:
    """Clean AI artifacts from prompt"""

    # Remove common AI prefixes
    prefixes = [
        "here is your prompt:", "here's the prompt:", "prompt:",
        "here is a detailed", "here's a detailed", "sure!", "sure,",
        "of course", "**prompt:**", "**image prompt:**"
    ]

    prompt_lower = prompt.lower()
    for prefix in prefixes:
        if prompt_lower.startswith(prefix):
            for sep in [':', '\n']:
                if sep in prompt:
                    prompt = prompt.split(sep, 1)[1].strip()
                    break
            break

    # Remove wrapping quotes
    prompt = prompt.strip('"\'')

    # Remove markdown
    prompt = re.sub(r'\*\*(.*?)\*\*', r'\1', prompt)
    prompt = re.sub(r'\*(.*?)\*', r'\1', prompt)

    # Remove extra newlines
    prompt = re.sub(r'\n+', ' ', prompt)

    # Clean spaces
    prompt = re.sub(r'\s+', ' ', prompt).strip()

    return prompt


def _validate_prompt(prompt: str) -> tuple:
    """Validate prompt quality"""

    # Length check
    if len(prompt) < 150:
        return False, f"Too short: {len(prompt)} chars"

    if len(prompt) > 1500:
        return False, f"Too long: {len(prompt)} chars"

    # Should have descriptive words
    descriptive_words = [
        "detailed", "beautiful", "divine", "sacred", "lighting",
        "composition", "atmosphere", "style", "quality", "master"
    ]

    word_count = sum(1 for w in descriptive_words if w in prompt.lower())
    if word_count < 2:
        return False, "Not descriptive enough"

    return True, "Valid"


def _build_smart_prompt(memory: AgentMemory, style_info: dict) -> str:
    """Build intelligent Gemini prompt"""

    references = _get_category_references(memory.category)
    composition = random.choice(COMPOSITIONS)
    lighting = random.choice(LIGHTING_STYLES)

    # Provider-specific optimization
    provider_note = ""
    if USE_VERTEX_AI:
        provider_note = "\n\nNote: This prompt will be used with Vertex AI Imagen (premium quality). Be specific and detailed."
    else:
        provider_note = "\n\nNote: This prompt will be used with Pollinations.ai. Keep it clear and vivid."

    festival_context = ""
    if memory.is_festival:
        festival_context = f"\n🎉 Special: This is for {memory.festival_name} festival - add festive elements!"

    prompt = f"""You are a world-class AI image prompt engineer specializing in spiritual Indian art.

═══════════════════════════════════════
🎯 TOPIC TO VISUALIZE
═══════════════════════════════════════
Topic: {memory.topic}
Category: {memory.category}
Mood: {memory.mood}
{festival_context}

═══════════════════════════════════════
🎨 ARTISTIC DIRECTION
═══════════════════════════════════════
Style: {style_info['name']}
Style details: {style_info['prompt']}
Composition: {composition}
Lighting: {lighting}

═══════════════════════════════════════
📚 CATEGORY REFERENCES
═══════════════════════════════════════
Artist inspiration: {', '.join(references.get('artists', []))}

Key visual elements to include:
{chr(10).join(['• ' + e for e in references.get('elements', [])[:5]])}

Suggested settings:
{chr(10).join(['• ' + s for s in references.get('settings', [])[:3]])}

Desired mood: {references.get('mood', memory.mood)}

═══════════════════════════════════════
🎯 FROM RESEARCH
═══════════════════════════════════════
Visual elements: {', '.join(memory.visual_elements[:5])}
Colors: {', '.join(memory.colors[:3])}
Symbols: {', '.join(memory.symbols[:3])}
{provider_note}

═══════════════════════════════════════
✅ REQUIREMENTS
═══════════════════════════════════════
1. Write ONE detailed prompt (3-5 sentences)
2. Start with the main subject clearly
3. Include specific pose/action
4. Describe setting/background in detail
5. Include exact lighting description
6. Add composition guidance
7. End with: "highly detailed, masterpiece, 8k quality"
8. Format: Instagram square (1:1)
9. NO text/watermarks in image
10. NO modern/western elements
11. Authentic Indian spiritual aesthetic

═══════════════════════════════════════
❌ AVOID
═══════════════════════════════════════
- Generic descriptions
- Adjective stacking without purpose
- Repetitive phrases
- Meta commentary ("beautiful image of...")

Now write the prompt (start directly, no preamble):"""

    return prompt


# ============================================================
# MAIN AGENT FUNCTION
# ============================================================

def run(memory: AgentMemory) -> AgentMemory:
    """
    Generate professional image prompt using AI
    """
    logger.info("=" * 55)
    logger.info("=== PROMPT AGENT STARTED ===")
    logger.info("=" * 55)

    # ═══════════════════════════════════════════
    # STEP 1: SELECT STYLE
    # ═══════════════════════════════════════════
    style_info = _select_best_style(memory.category)
    logger.info(f"🎨 Style: {style_info['name']}")

    # ═══════════════════════════════════════════
    # STEP 2: BUILD SMART PROMPT
    # ═══════════════════════════════════════════
    system_prompt = _build_smart_prompt(memory, style_info)
    logger.info(f"📝 System prompt built ({len(system_prompt)} chars)")

    # ═══════════════════════════════════════════
    # STEP 3: GENERATE WITH RETRIES
    # ═══════════════════════════════════════════
    max_attempts = 3
    generated_prompt = None

    for attempt in range(1, max_attempts + 1):
        try:
            logger.info(f"🤖 Gemini attempt {attempt}/{max_attempts}")

            model = genai.GenerativeModel(GEMINI_MODEL)

            # Progressive temperature (more creative on retries)
            temp = 0.75 + (attempt * 0.05)

            response = model.generate_content(
                system_prompt,
                generation_config={
                    "temperature": temp,
                    "max_output_tokens": 1000,
                    "top_p": 0.95,
                    "top_k": 40,
                }
            )

            # Extract and clean
            raw = _extract_response_text(response)
            cleaned = _clean_prompt(raw)

            # Validate
            is_valid, reason = _validate_prompt(cleaned)

            if is_valid:
                generated_prompt = cleaned
                logger.info(f"✅ Prompt generated on attempt {attempt}")
                break
            else:
                logger.warning(f"⚠️ Attempt {attempt} invalid: {reason}")

        except Exception as e:
            logger.warning(f"❌ Attempt {attempt} failed: {e}")

    # ═══════════════════════════════════════════
    # STEP 4: FALLBACK OR SUCCESS
    # ═══════════════════════════════════════════
    if generated_prompt:
        # Success - use Gemini-generated prompt
        memory.image_prompt = generated_prompt
        memory.image_style = style_info['name']

        logger.info("=" * 55)
        logger.info("✅ PROMPT AGENT SUCCESS")
        logger.info("=" * 55)
        logger.info(f"🎨 Style : {style_info['name']}")
        logger.info(f"📏 Length: {len(generated_prompt)} chars")
        logger.info(f"📄 Preview: {generated_prompt[:120]}...")
        logger.info("=" * 55)

    else:
        # Fallback - build prompt from templates
        logger.warning("⚠️ All Gemini attempts failed. Using template fallback.")

        references = _get_category_references(memory.category)
        elements = ', '.join(memory.visual_elements[:4]) if memory.visual_elements else ', '.join(references.get('elements', [])[:4])
        colors = ', '.join(memory.colors[:3]) if memory.colors else "warm golden, blue, orange"
        setting = random.choice(references.get('settings', ['divine spiritual setting']))
        composition = random.choice(COMPOSITIONS)
        lighting = random.choice(LIGHTING_STYLES)

        fallback_prompt = (
            f"{memory.topic}, {elements}, "
            f"set in {setting}, "
            f"{composition}, "
            f"{lighting}, "
            f"{colors} color palette, "
            f"{style_info['prompt']}, "
            f"{style_info['quality_boost']}, "
            f"highly detailed, masterpiece, 8k quality"
        )

        memory.image_prompt = fallback_prompt
        memory.image_style = style_info['name']

        logger.info(f"📄 Fallback prompt: {fallback_prompt[:120]}...")

    # Set negative prompt
    memory.negative_prompt = NEGATIVE_PROMPT

    logger.info("=== PROMPT AGENT DONE ===\n")
    return memory


# ============================================================
# STANDALONE TESTING
# ============================================================

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("PROMPT AGENT - STANDALONE TEST")
    print("=" * 60 + "\n")

    test_cases = [
        {
            "topic": "Lord Krishna playing flute in Vrindavan",
            "category": "krishna",
            "mood": "peaceful, divine, romantic",
            "visual_elements": ["flute", "peacock feather", "cows"],
            "colors": ["blue", "yellow", "green"],
            "symbols": ["flute", "peacock", "lotus"]
        },
        {
            "topic": "Lord Shiva meditating in Himalayas",
            "category": "shiva",
            "mood": "powerful, mystical, serene",
            "visual_elements": ["trishul", "snake", "moon"],
            "colors": ["blue", "white", "silver"],
            "symbols": ["trishul", "om", "third eye"]
        }
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
        memory.colors = test["colors"]
        memory.symbols = test["symbols"]

        result = run(memory)

        print(f"\n📝 GENERATED PROMPT:")
        print(f"{result.image_prompt}")
        print(f"\n🎨 Style: {result.image_style}")
        print(f"📏 Length: {len(result.image_prompt)} chars")