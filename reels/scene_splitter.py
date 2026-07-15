"""
Scene Splitter - Split reel story into 6 cinematic scenes

Each scene has:
- scene_number (1-6)
- scene_type (hook | context | climax | lesson | reflection | cta)
- narration (Hindi text - what TTS will speak)
- visual_description (English - for image prompt building)
- duration_seconds (target duration)
- start_time / end_time (video timeline placeholders)
- effect (ken_burns effect type)

Total video: 60-90 seconds
Each scene: 10-15 seconds avg

V2.1 FIXES:
- Better simple Hindi enforcement
- adjust_scene_durations() function for voice sync
- Handles voice-shorter-than-expected case
- Handles voice-longer-than-expected case
"""
import re
import time
import json
import google.generativeai as genai

from core.memory import AgentMemory
from config.settings import (
    GEMINI_API_KEY,
    GEMINI_MODEL,
    REEL_NUM_SCENES,
    REEL_DURATION_MIN,
    REEL_DURATION_MAX
)
from utils.logger import get_logger

genai.configure(api_key=GEMINI_API_KEY)
logger = get_logger("scene_splitter")


# ============================================================
# SCENE STRUCTURE TEMPLATES
# ============================================================

SCENE_ARC = [
    {
        "scene_number": 1,
        "scene_type": "hook",
        "purpose": "Grab attention in first 3 seconds",
        "duration_hint": 8,
        "effect": "zoom_in",
        "weight": 8   # Relative weight for duration distribution
    },
    {
        "scene_number": 2,
        "scene_type": "context",
        "purpose": "Set up the story background",
        "duration_hint": 12,
        "effect": "pan_left",
        "weight": 12
    },
    {
        "scene_number": 3,
        "scene_type": "climax",
        "purpose": "Peak moment / turning point",
        "duration_hint": 15,
        "effect": "zoom_out",
        "weight": 15
    },
    {
        "scene_number": 4,
        "scene_type": "lesson",
        "purpose": "The wisdom / teaching",
        "duration_hint": 12,
        "effect": "zoom_in",
        "weight": 12
    },
    {
        "scene_number": 5,
        "scene_type": "reflection",
        "purpose": "How this applies to viewer's life",
        "duration_hint": 10,
        "effect": "pan_right",
        "weight": 10
    },
    {
        "scene_number": 6,
        "scene_type": "cta",
        "purpose": "Call to action - Save/Share/Follow",
        "duration_hint": 8,
        "effect": "zoom_in",
        "weight": 8
    }
]


# ============================================================
# EFFECTS
# ============================================================

EFFECTS = ["zoom_in", "zoom_out", "pan_left", "pan_right", "static"]


# ============================================================
# HELPER FUNCTIONS
# ============================================================

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


def _clean_json_response(raw: str) -> str:
    """Clean and extract JSON array"""
    raw = re.sub(r'```json\s*', '', raw)
    raw = re.sub(r'```\s*', '', raw)

    # Find outermost brackets
    start = raw.find('[')
    end = raw.rfind(']')

    if start != -1 and end != -1 and end > start:
        raw = raw[start:end + 1]

    return raw.strip()


def _validate_scenes(scenes: list) -> tuple:
    """Validate scenes structure"""
    if not isinstance(scenes, list):
        return False, "Not a list"

    if len(scenes) != REEL_NUM_SCENES:
        return False, f"Expected {REEL_NUM_SCENES} scenes, got {len(scenes)}"

    required_fields = ["scene_number", "scene_type", "narration", "visual_description"]

    for i, scene in enumerate(scenes):
        if not isinstance(scene, dict):
            return False, f"Scene {i+1} is not a dict"

        for field in required_fields:
            if field not in scene or not scene[field]:
                return False, f"Scene {i+1} missing/empty field: {field}"

        # Validate narration has Hindi
        narration = scene.get("narration", "")
        devanagari_count = sum(1 for c in narration if '\u0900' <= c <= '\u097F')
        if devanagari_count < len(narration) * 0.4:
            return False, f"Scene {i+1} narration not in Hindi"

        # Validate visual_description has English
        visual = scene.get("visual_description", "")
        if len(visual) < 20:
            return False, f"Scene {i+1} visual_description too short"

    return True, "Valid"


def _calculate_timeline(scenes: list) -> list:
    """Add start_time and end_time based on duration_seconds"""
    current_time = 0.0

    for scene in scenes:
        duration = scene.get("duration_seconds", 10.0)
        scene["start_time"] = round(current_time, 2)
        scene["end_time"] = round(current_time + duration, 2)
        current_time += duration

    return scenes


def _add_effects(scenes: list) -> list:
    """Assign Ken Burns effects to scenes (from template)"""
    for scene in scenes:
        scene_num = scene.get("scene_number", 1)
        arc_template = SCENE_ARC[scene_num - 1] if scene_num <= len(SCENE_ARC) else SCENE_ARC[-1]
        scene["effect"] = arc_template.get("effect", "zoom_in")

    return scenes


# ============================================================
# 🆕 V2.1: DYNAMIC DURATION ADJUSTMENT (Voice Sync)
# ============================================================

def adjust_scene_durations(scenes: list, voice_duration: float) -> list:
    """
    🆕 V2.1: Adjust scene durations to match voice duration.

    Strategy:
    - Distribute voice_duration proportionally across scenes
    - Use SCENE_ARC weights (hook shorter, climax longer, etc.)
    - Add small buffer (0.5s) at end for smooth ending

    Args:
        scenes: List of scene dicts
        voice_duration: Actual voice duration in seconds

    Returns:
        Updated scenes list with adjusted durations

    Example:
        Voice duration: 45s
        Weights: [8, 12, 15, 12, 10, 8] = 65 total
        Ratios: [0.123, 0.185, 0.231, 0.185, 0.154, 0.123]
        New durations: [5.5s, 8.3s, 10.4s, 8.3s, 6.9s, 5.5s] = 45s ✅
    """
    if not scenes or not voice_duration:
        logger.warning("⚠️  Cannot adjust — missing scenes or voice_duration")
        return scenes

    logger.info("=" * 55)
    logger.info(f"🎯 ADJUSTING SCENE DURATIONS")
    logger.info("=" * 55)
    logger.info(f"   Voice duration: {voice_duration:.1f}s")
    logger.info(f"   Scenes: {len(scenes)}")

    # Add 0.5s buffer at end for smooth ending
    target_duration = voice_duration + 0.5

    # Get total weight from SCENE_ARC (matching by scene_number)
    total_weight = 0
    scene_weights = []

    for scene in scenes:
        scene_num = scene.get("scene_number", 1)
        # Find matching template
        if 1 <= scene_num <= len(SCENE_ARC):
            weight = SCENE_ARC[scene_num - 1].get("weight", 10)
        else:
            weight = 10  # Default

        scene_weights.append(weight)
        total_weight += weight

    logger.info(f"   Total weight: {total_weight}")
    logger.info(f"   Target duration: {target_duration:.1f}s (voice + 0.5s buffer)")

    # Calculate new durations
    logger.info(f"")
    logger.info(f"📊 Duration adjustments:")

    current_time = 0.0
    for i, scene in enumerate(scenes):
        old_duration = scene.get("duration_seconds", 10)
        weight = scene_weights[i]
        ratio = weight / total_weight
        new_duration = round(target_duration * ratio, 2)

        # Ensure minimum 3 seconds per scene
        new_duration = max(new_duration, 3.0)

        # Update scene
        scene["duration_seconds"] = new_duration
        scene["start_time"] = round(current_time, 2)
        scene["end_time"] = round(current_time + new_duration, 2)
        current_time += new_duration

        change = "↑" if new_duration > old_duration else "↓" if new_duration < old_duration else "="
        logger.info(
            f"   Scene {scene['scene_number']} ({scene.get('scene_type', '?'):12}): "
            f"{old_duration:5.1f}s {change} {new_duration:5.1f}s"
        )

    final_total = sum(s["duration_seconds"] for s in scenes)
    logger.info(f"")
    logger.info(f"✅ New total: {final_total:.1f}s (target: {target_duration:.1f}s)")

    # If total is way off, do fine adjustment on last scene
    if abs(final_total - target_duration) > 0.5:
        diff = target_duration - final_total
        scenes[-1]["duration_seconds"] = round(
            scenes[-1]["duration_seconds"] + diff, 2
        )
        scenes[-1]["end_time"] = round(
            scenes[-1]["start_time"] + scenes[-1]["duration_seconds"], 2
        )
        logger.info(f"   Fine-tuned last scene by {diff:+.1f}s")

    logger.info("=" * 55)
    return scenes


# ============================================================
# PROMPT BUILDER (Simple Hindi)
# ============================================================

def _build_scene_splitter_prompt(story: str, category: str, topic: str, mood: str) -> str:
    """Build prompt for Gemini to split story into 6 scenes"""

    return f"""तुम एक expert film editor हो जो Hindi Reels के लिए scenes बनाते हो।

═══════════════════════════════════════════
📌 विषय: {topic}
📂 श्रेणी: {category}
🎭 भाव: {mood}
═══════════════════════════════════════════

📖 STORY जिसे 6 scenes में divide करना है:
═══════════════════════════════════════════
🎬 REQUIRED: 6 SCENES निकालो
═══════════════════════════════════════════

Total video: {REEL_DURATION_MIN}-{REEL_DURATION_MAX} seconds
Each scene: 8-15 seconds

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Scene 1: HOOK (ध्यान खींचना)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- पहले 3 seconds में viewer रुक जाए
- Duration: 8 seconds
- Narration: Story का hook part (15-20 Hindi words)
- Visual: Dramatic opening

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Scene 2: CONTEXT (Background)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- Story का context set करना
- Duration: 12 seconds
- Narration: Setup (25-30 Hindi words)
- Visual: Setting establishment

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Scene 3: CLIMAX (Peak moment)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- Story का turning point
- Duration: 15 seconds
- Narration: Main event (30-40 Hindi words)
- Visual: Most dramatic scene

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Scene 4: LESSON (सीख)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- Story से मिलने वाली सीख
- Duration: 12 seconds
- Narration: Teaching (25-30 Hindi words)
- Visual: Symbolic imagery

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Scene 5: REFLECTION (Personal apply)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- Viewer के जीवन में कैसे लागू हो
- Duration: 10 seconds
- Narration: Application (20-25 Hindi words)
- Visual: Peaceful scene

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Scene 6: CTA (Call to Action)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- Save, Share, Follow
- Duration: 8 seconds
- Narration: CTA (15-20 Hindi words)
- Visual: Divine blessing scene

═══════════════════════════════════════════
🎯 IMPORTANT: भाषा एकदम आसान हो
═══════════════════════════════════════════

Narration में मुश्किल शब्द NOT allowed:
❌ विघ्नहर्ता (use: मुसीबतें दूर करने वाले)
❌ आराधना (use: पूजा)
❌ श्रद्धेय (use: सच्चे भक्त)
❌ प्रलय (use: बड़ी तबाही)
❌ समस्त (use: सारे)

Simple, conversational Hindi लिखो।

═══════════════════════════════════════════
📤 OUTPUT FORMAT (JSON array only):
═══════════════════════════════════════════

Return ONLY valid JSON. No markdown, no explanation.

[
    {{
        "scene_number": 1,
        "scene_type": "hook",
        "narration": "आसान Hindi text (Devanagari only)",
        "visual_description": "English detailed visual for AI image generation (30-50 words)",
        "duration_seconds": 8
    }},
    ... (6 scenes total)
]

═══════════════════════════════════════════
RULES:
═══════════════════════════════════════════

1. ✅ NARRATION: 100% आसान Hindi (Devanagari)
2. ✅ VISUAL_DESCRIPTION: 100% English (for AI image gen)
3. ✅ Divide story naturally (don't cut mid-sentence)
4. ✅ Each narration flows to next
5. ✅ Total = 6 scenes exactly
6. ✅ Visual descriptions: cinematic, detailed, specific

अब 6 scenes का JSON return करो:"""


# ============================================================
# FALLBACK SCENES
# ============================================================

def _get_fallback_scenes(memory: AgentMemory) -> list:
    """Create fallback scenes by manually splitting story"""

    story = memory.reel_story
    words = story.split()
    total_words = len(words)

    # Split into 6 chunks roughly proportional to scene durations
    ratios = [8/65, 12/65, 15/65, 12/65, 10/65, 8/65]

    fallback_scenes = []
    start_idx = 0

    for i, ratio in enumerate(ratios):
        chunk_size = int(total_words * ratio)
        end_idx = min(start_idx + chunk_size, total_words)

        if i == 5:
            end_idx = total_words

        narration = " ".join(words[start_idx:end_idx])
        start_idx = end_idx

        arc = SCENE_ARC[i]

        fallback_scenes.append({
            "scene_number": arc["scene_number"],
            "scene_type": arc["scene_type"],
            "narration": narration if narration else f"दृश्य {i+1}",
            "visual_description": (
                f"Spiritual scene depicting {memory.topic}, "
                f"cinematic {arc['scene_type']} moment, "
                f"divine atmosphere, {memory.mood}, highly detailed, 4k quality"
            ),
            "duration_seconds": arc["duration_hint"]
        })

    return fallback_scenes


# ============================================================
# MAIN AGENT FUNCTION
# ============================================================

def run(memory: AgentMemory) -> AgentMemory:
    """
    Split story into 6 scenes
    """
    logger.info("=" * 55)
    logger.info("=== SCENE SPLITTER V2.1 शुरू ===")
    logger.info("=" * 55)

    if not memory.reel_story:
        logger.error("❌ कोई story नहीं है")
        memory.add_error("scene_splitter", "No story to split")
        return memory

    logger.info(f"📖 Story: {len(memory.reel_story.split())} words")
    logger.info(f"🎬 Target: {REEL_NUM_SCENES} scenes")

    # Build prompt
    prompt = _build_scene_splitter_prompt(
        story=memory.reel_story,
        category=memory.category,
        topic=memory.topic,
        mood=memory.mood
    )

    # Gemini call with retries
    max_attempts = 3
    scenes = None

    for attempt in range(1, max_attempts + 1):
        try:
            logger.info(f"🤖 Gemini कोशिश {attempt}/{max_attempts}")

            model = genai.GenerativeModel(GEMINI_MODEL)

            response = model.generate_content(
                prompt,
                generation_config={
                    "temperature": 0.7,
                    "max_output_tokens": 3000,
                    "top_p": 0.95,
                }
            )

            raw = _extract_response_text(response)
            cleaned = _clean_json_response(raw)

            parsed_scenes = json.loads(cleaned)

            is_valid, reason = _validate_scenes(parsed_scenes)

            if is_valid:
                scenes = parsed_scenes
                logger.info(f"✅ Valid scenes generated on attempt {attempt}")
                break
            else:
                logger.warning(f"⚠️  Attempt {attempt} invalid: {reason}")
                if attempt < max_attempts:
                    time.sleep(2)

        except json.JSONDecodeError as e:
            logger.warning(f"⚠️  JSON parse failed (attempt {attempt}): {e}")
            if attempt < max_attempts:
                time.sleep(2)
        except Exception as e:
            logger.warning(f"❌ Attempt {attempt} failed: {e}")
            if attempt < max_attempts:
                time.sleep(3)

    # Fallback if all attempts failed
    if scenes is None:
        logger.warning("⚠️  All Gemini attempts failed. Using manual split fallback.")
        scenes = _get_fallback_scenes(memory)

    # Add effects and timeline
    scenes = _add_effects(scenes)
    scenes = _calculate_timeline(scenes)

    # Save to memory
    memory.reel_scenes = scenes

    # Log summary
    total_duration = sum(s.get("duration_seconds", 0) for s in scenes)

    logger.info("=" * 55)
    logger.info("✅ SCENE SPLITTER SUCCESS")
    logger.info("=" * 55)
    logger.info(f"🎬 Total scenes: {len(scenes)}")
    logger.info(f"⏱️  Total duration: {total_duration}s (initial estimate)")
    logger.info(f"ℹ️  NOTE: Will be adjusted to voice duration in reel_engine")
    logger.info("")
    logger.info("📋 Scene breakdown:")

    for scene in scenes:
        logger.info(
            f"   Scene {scene['scene_number']} ({scene['scene_type']}): "
            f"{scene['duration_seconds']}s | {scene['effect']}"
        )
        logger.info(f"      📖 {scene['narration'][:60]}...")

    logger.info("=" * 55)
    logger.info("=== SCENE SPLITTER पूर्ण ===\n")
    return memory


# ============================================================
# STANDALONE TESTING
# ============================================================

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("SCENE SPLITTER V2.1 - TEST")
    print("=" * 60 + "\n")

    test_story = (
        "क्या आप जानते हैं कि कान्हा की बांसुरी में ऐसा क्या था? "
        "जब भी वो बांसुरी बजाते, तो सब कुछ रुक जाता था। "
        "पेड़ भी सुनते, पक्षी भी सुनते।\n\n"
        "वृंदावन में गोपियां अपना काम छोड़ देतीं। "
        "गायें अपने आप कान्हा के पास दौड़ी चली आतीं। "
        "राधा रानी तो बांसुरी सुनते ही सब कुछ भूल जाती थीं। "
        "वो बांसुरी सिर्फ लकड़ी का टुकड़ा नहीं थी। "
        "वो प्यार की आवाज़ थी।\n\n"
        "आज भी अगर आप शांत मन से बैठें और भगवान को याद करें, "
        "तो आपको भी कान्हा की बांसुरी सुनाई देगी।\n\n"
        "Save करें और Share करें 🙏"
    )

    memory = AgentMemory()
    memory.reel_story = test_story
    memory.topic = "Krishna playing flute in Vrindavan"
    memory.category = "krishna"
    memory.mood = "peaceful, divine"

    result = run(memory)

    print(f"\n📊 Initial scenes:")
    for scene in result.reel_scenes:
        print(f"  Scene {scene['scene_number']}: {scene['duration_seconds']}s - {scene['narration'][:50]}...")

    print(f"\n\n🧪 TEST: Adjusting for 45s voice...")
    adjusted = adjust_scene_durations(result.reel_scenes, voice_duration=45.0)

    print(f"\n📊 Adjusted scenes:")
    total = 0
    for scene in adjusted:
        print(f"  Scene {scene['scene_number']}: {scene['duration_seconds']}s")
        total += scene['duration_seconds']
    print(f"\n  TOTAL: {total}s (target: 45.5s)")