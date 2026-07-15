"""
Prompt Builder - Build cinematic Imagen prompts for each scene

For each of the 6 scenes:
- Takes visual_description (English)
- Reuses ART_STYLES from prompt_agent.py
- Reuses CATEGORY_ART_REFERENCES from prompt_agent.py
- Adds Ken Burns-friendly composition
- Adds 9:16 portrait framing hints
- Generates complete image_prompt
- Sets negative_prompt

Reuses existing prompt_agent logic - no duplicate code!
"""
import random

from core.memory import AgentMemory
from utils.logger import get_logger

# Reuse existing prompt_agent constants
from agents.prompt_agent import (
    ART_STYLES,
    CATEGORY_ART_REFERENCES,
    COMPOSITIONS,
    LIGHTING_STYLES,
    NEGATIVE_PROMPT as BASE_NEGATIVE_PROMPT
)

logger = get_logger("prompt_builder")


# ============================================================
# REEL-SPECIFIC ADDITIONS
# ============================================================

# 9:16 vertical composition (reels-specific)
REEL_COMPOSITIONS = [
    "vertical portrait composition, subject centered, ample headroom",
    "9:16 aspect ratio, subject filling frame vertically",
    "cinematic vertical framing, rule of thirds vertical",
    "portrait orientation, subject prominent in upper two-thirds",
    "vertical cinematic shot, mobile-optimized framing",
]

# Scene-type specific mood
SCENE_TYPE_MOOD = {
    "hook": {
        "extra_prompt": "dramatic opening shot, powerful first impression, attention-grabbing",
        "lighting": "dramatic side lighting, high contrast",
    },
    "context": {
        "extra_prompt": "establishing shot, wider view, setting the scene",
        "lighting": "soft ambient lighting, warm golden hour",
    },
    "climax": {
        "extra_prompt": "peak dramatic moment, intense emotion, powerful visual",
        "lighting": "divine golden light rays, ethereal glow",
    },
    "lesson": {
        "extra_prompt": "contemplative moment, wisdom-conveying atmosphere",
        "lighting": "warm meditation lighting, soft halo effect",
    },
    "reflection": {
        "extra_prompt": "peaceful reflective mood, introspective visual",
        "lighting": "soft diffused morning light, tranquil atmosphere",
    },
    "cta": {
        "extra_prompt": "divine blessing scene, uplifting positive ending",
        "lighting": "bright divine light, welcoming warm tones",
    },
}

# Reel-specific negative prompt (stronger for videos)
REEL_NEGATIVE_PROMPT = (
    BASE_NEGATIVE_PROMPT +
    ", horizontal composition, landscape orientation, "
    "wide angle distortion, subject too small, empty space, "
    "text, letters, words, watermark, signature, logo, "
    "captions, subtitles, symbols, numbers"
)


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def _get_category_references(category: str) -> dict:
    """Get category-specific art references (reused from prompt_agent)"""
    return CATEGORY_ART_REFERENCES.get(
        category,
        CATEGORY_ART_REFERENCES.get("spiritual_nature", {})
    )


def _select_style_for_scenes(category: str) -> dict:
    """
    Select ONE consistent art style for all 6 scenes.
    This ensures visual consistency across the reel.
    """
    # Filter styles suitable for category
    suitable = [
        (key, info) for key, info in ART_STYLES.items()
        if category in info.get("best_for", [])
    ]

    if suitable:
        # Pick one and use for all scenes (consistency!)
        chosen_key, chosen_style = random.choice(suitable)
        logger.info(f"🎨 Selected style for all scenes: {chosen_key}")
        return chosen_style

    # Fallback to first available
    chosen_key = list(ART_STYLES.keys())[0]
    return ART_STYLES[chosen_key]


def _build_scene_prompt(
    scene: dict,
    category: str,
    style_info: dict,
    references: dict
) -> str:
    """
    Build complete image prompt for one scene.

    Combines:
    - Scene's visual_description (from scene_splitter)
    - Selected art style (consistent across all scenes)
    - Category-specific artistic references
    - Scene-type mood
    - Vertical composition hints
    - Ken Burns friendly framing
    """

    scene_type = scene.get("scene_type", "context")
    visual_desc = scene.get("visual_description", "")
    effect = scene.get("effect", "zoom_in")

    # Scene-type specific additions
    scene_mood = SCENE_TYPE_MOOD.get(scene_type, SCENE_TYPE_MOOD["context"])
    scene_extra = scene_mood["extra_prompt"]
    scene_lighting = scene_mood["lighting"]

    # Vertical composition
    composition = random.choice(REEL_COMPOSITIONS)

    # Get key elements from category
    elements = references.get("elements", [])
    setting = ""
    if references.get("settings"):
        setting = random.choice(references["settings"])

    # Ken Burns friendly hints (don't want subject too tight to edges)
    if "zoom" in effect:
        framing_hint = "subject with breathing room for zoom animation"
    elif "pan" in effect:
        framing_hint = "wide composition suitable for panning"
    else:
        framing_hint = "static composition, well-balanced"

    # Build final prompt
    prompt_parts = [
        # Main subject (from scene splitter)
        visual_desc,

        # Setting
        f"set in {setting}" if setting else "",

        # Scene mood
        scene_extra,

        # Composition (9:16 vertical)
        composition,
        framing_hint,

        # Lighting
        scene_lighting,

        # Art style (consistent across reel)
        style_info["prompt"],

        # Quality boost
        style_info.get("quality_boost", "highly detailed"),

        # Category elements (if any)
        f"featuring {', '.join(elements[:3])}" if elements else "",

        # Final quality tags
        "cinematic quality, 8K resolution, professional photography, "
        "highly detailed, masterpiece, no text, no watermark"
    ]

    # Clean and join
    prompt = ", ".join([p.strip() for p in prompt_parts if p.strip()])

    # Remove duplicate commas
    prompt = re.sub(r',\s*,+', ',', prompt)
    prompt = re.sub(r'\s+', ' ', prompt).strip()

    return prompt


# ============================================================
# MAIN AGENT FUNCTION
# ============================================================

def run(memory: AgentMemory) -> AgentMemory:
    """
    Build cinematic prompts for all 6 scenes

    Flow:
    1. Validate scenes exist
    2. Select ONE art style (consistency)
    3. Get category references
    4. For each scene → build complete prompt
    5. Update each scene's image_prompt field
    """
    logger.info("=" * 55)
    logger.info("=== PROMPT BUILDER शुरू ===")
    logger.info("=" * 55)

    # Validate input
    if not memory.reel_scenes:
        logger.error("❌ कोई scenes नहीं हैं")
        memory.add_error("prompt_builder", "No scenes to build prompts for")
        return memory

    logger.info(f"🎬 Scenes to process: {len(memory.reel_scenes)}")
    logger.info(f"📂 Category: {memory.category}")

    # ── Select consistent art style ─────────────────────────
    style_info = _select_style_for_scenes(memory.category)

    # Store in memory for reference
    memory.image_style = style_info.get("name", "cinematic")

    # ── Get category references ─────────────────────────────
    references = _get_category_references(memory.category)

    # ── Build prompt for each scene ─────────────────────────
    for scene in memory.reel_scenes:
        try:
            image_prompt = _build_scene_prompt(
                scene=scene,
                category=memory.category,
                style_info=style_info,
                references=references
            )

            scene["image_prompt"] = image_prompt
            scene["negative_prompt"] = REEL_NEGATIVE_PROMPT

            logger.info(
                f"✅ Scene {scene['scene_number']} ({scene['scene_type']}): "
                f"prompt built ({len(image_prompt)} chars)"
            )

        except Exception as e:
            logger.error(f"❌ Scene {scene.get('scene_number')} prompt failed: {e}")
            # Set fallback prompt
            scene["image_prompt"] = (
                f"{scene.get('visual_description', 'spiritual scene')}, "
                f"cinematic, divine, 8k quality, no text, no watermark"
            )
            scene["negative_prompt"] = REEL_NEGATIVE_PROMPT

    # ── Summary ─────────────────────────────────────────────
    logger.info("=" * 55)
    logger.info("✅ PROMPT BUILDER SUCCESS")
    logger.info("=" * 55)
    logger.info(f"🎨 Style used: {style_info.get('name')}")
    logger.info(f"🎬 Prompts built: {len(memory.reel_scenes)}")
    logger.info("")
    logger.info("📋 Prompt previews:")

    for scene in memory.reel_scenes:
        prompt = scene.get("image_prompt", "")
        logger.info(
            f"   Scene {scene['scene_number']}: {prompt[:80]}..."
        )

    logger.info("=" * 55)

    logger.info("=== PROMPT BUILDER पूर्ण ===\n")
    return memory


# ============================================================
# IMPORT re AT MODULE LEVEL (was missing above)
# ============================================================
import re  # noqa: E402


# ============================================================
# STANDALONE TESTING
# ============================================================

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("PROMPT BUILDER - STANDALONE TEST")
    print("=" * 60 + "\n")

    # Sample scenes (from scene_splitter output)
    sample_scenes = [
        {
            "scene_number": 1,
            "scene_type": "hook",
            "narration": "क्या आप जानते हैं?",
            "visual_description": "Lord Krishna standing majestically with divine aura, holding flute",
            "duration_seconds": 8,
            "effect": "zoom_in"
        },
        {
            "scene_number": 2,
            "scene_type": "context",
            "narration": "वृंदावन के जंगल में...",
            "visual_description": "Peaceful Vrindavan forest with Yamuna river, cows grazing, morning mist",
            "duration_seconds": 12,
            "effect": "pan_left"
        },
        {
            "scene_number": 3,
            "scene_type": "climax",
            "narration": "कान्हा की बांसुरी की धुन...",
            "visual_description": "Krishna playing flute with divine light emanating, gopis mesmerized",
            "duration_seconds": 15,
            "effect": "zoom_out"
        }
    ]

    memory = AgentMemory()
    memory.reel_scenes = sample_scenes
    memory.category = "krishna"
    memory.topic = "Krishna's divine flute"
    memory.mood = "peaceful, divine, romantic"

    result = run(memory)

    for scene in result.reel_scenes:
        print(f"\n━━━ Scene {scene['scene_number']} ({scene['scene_type']}) ━━━")
        print(f"Visual desc: {scene['visual_description']}")
        print(f"\n📝 Full prompt:\n{scene['image_prompt']}")
        print(f"\n❌ Negative: {scene['negative_prompt'][:100]}...")