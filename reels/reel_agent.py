"""
Reel Agent V2 - Orchestrator for reel content generation

Orchestrates Phase 2 (text layer):
1. story_writer  → Generate Hindi story (130-180 words)
2. fact_checker  → Verify accuracy (Gemini-based)
3. scene_splitter → Split into 6 scenes with durations
4. prompt_builder → Build Imagen prompts per scene

Note: Full video pipeline (images, TTS, video builder) 
is handled by reel_engine.py which calls this agent.

Agent pattern: receives AgentMemory, processes, returns AgentMemory
"""
import time

from core.memory import AgentMemory
from utils.logger import get_logger

from reels import (
    story_writer,
    fact_checker,
    scene_splitter,
    prompt_builder
)

logger = get_logger("reel_agent")


# ============================================================
# REEL CONTENT DEFAULTS (hashtags & caption fallback)
# ============================================================

REEL_HASHTAGS_DEFAULT = """#SanatanSoch #HinduDharma #Reels #ReelsInstagram
#SpiritualReels #DevotionalReels #ReelsIndia #Sanatan
#VedicWisdom #DivineIndia #JaiShriRam #HarHarMahadev
#JaiMataKi #Spirituality #ReelsFeed #ShortsIndia
#TrendingReels #ViralReels #HinduReels #IndianReels
#DailyBhakti #ShortVideo #Reel #ReelKaroFeelKaro
#SanataniSooch"""


# ============================================================
# MAIN AGENT FUNCTION
# ============================================================

def run(memory: AgentMemory) -> AgentMemory:
    """
    Reel Agent - Phase 2 orchestration

    Handles text content layer:
    - Story generation (Hindi, 130-180 words)
    - Fact checking (accuracy verification)
    - Scene splitting (6 scenes with timing)
    - Prompt building (Imagen-ready prompts)

    Full video pipeline (Phase 3+) handled by reel_engine.py:
    - Image generation (6 scenes via Imagen/Gemini)
    - TTS voice generation (Google Cloud TTS)
    - Subtitle generation
    - Video building (MoviePy)
    - Watermarking
    - Upload to GCS
    """
    logger.info("=" * 55)
    logger.info("=== REEL AGENT V2 शुरू ===")
    logger.info("=" * 55)

    # ── Validate input ──────────────────────────────────────
    if not memory.topic:
        memory.add_error("reel_agent", "Memory में topic नहीं")
        logger.error("❌ Topic नहीं मिला")
        return memory

    if memory.post_type != "reel":
        logger.warning(f"⚠️  Post type is '{memory.post_type}', setting to 'reel'")
        memory.post_type = "reel"

    start_time = time.time()

    try:
        # ═══════════════════════════════════════════
        # STEP 1: STORY WRITER
        # ═══════════════════════════════════════════
        logger.info("")
        logger.info("━━━ चरण 1/4: कहानी लिख रहे हैं (Story Writer) ━━━")

        if memory.reel_story and memory.is_recovery:
            logger.info("⏭️  Story already exists (recovery), skipping")
        else:
            memory = story_writer.run(memory)

            if not memory.reel_story:
                raise Exception("Story writer failed to generate story")

            logger.info(f"✅ Story ready: {len(memory.reel_story.split())} words")

        # ═══════════════════════════════════════════
        # STEP 2: FACT CHECKER
        # ═══════════════════════════════════════════
        logger.info("")
        logger.info("━━━ चरण 2/4: तथ्य जांच (Fact Checker) ━━━")

        if memory.reel_fact_checked and memory.is_recovery:
            logger.info("⏭️  Already fact-checked (recovery), skipping")
        else:
            memory = fact_checker.run(memory)

            if memory.reel_fact_checked:
                logger.info("✅ Facts verified")
            else:
                logger.warning("⚠️  Fact check had issues (continuing anyway)")

        # ═══════════════════════════════════════════
        # STEP 3: SCENE SPLITTER
        # ═══════════════════════════════════════════
        logger.info("")
        logger.info("━━━ चरण 3/4: 6 दृश्यों में विभाजन (Scene Splitter) ━━━")

        if memory.reel_scenes and memory.is_recovery:
            logger.info(f"⏭️  {len(memory.reel_scenes)} scenes already exist, skipping")
        else:
            memory = scene_splitter.run(memory)

            if not memory.reel_scenes or len(memory.reel_scenes) < 6:
                scene_count = len(memory.reel_scenes) if memory.reel_scenes else 0
                raise Exception(
                    f"Scene splitter failed: got {scene_count} scenes, need 6"
                )

            logger.info(f"✅ {len(memory.reel_scenes)} scenes created")

        # ═══════════════════════════════════════════
        # STEP 4: PROMPT BUILDER
        # ═══════════════════════════════════════════
        logger.info("")
        logger.info("━━━ चरण 4/4: प्रॉम्प्ट निर्माण (Prompt Builder) ━━━")

        # Check if prompts already built
        has_prompts = all(
            scene.get("image_prompt") for scene in memory.reel_scenes
        )

        if has_prompts and memory.is_recovery:
            logger.info("⏭️  All prompts already built, skipping")
        else:
            memory = prompt_builder.run(memory)

            # Verify prompts were built
            prompts_built = sum(
                1 for s in memory.reel_scenes if s.get("image_prompt")
            )
            logger.info(f"✅ {prompts_built}/{len(memory.reel_scenes)} prompts built")

        # ═══════════════════════════════════════════
        # SET DEFAULT HASHTAGS (if not set by hashtag_agent)
        # ═══════════════════════════════════════════
        if not memory.hashtags:
            memory.hashtags = REEL_HASHTAGS_DEFAULT
            logger.info(f"📌 Default reel hashtags set ({len(memory.hashtags.split())} tags)")

        # ═══════════════════════════════════════════
        # SUCCESS SUMMARY
        # ═══════════════════════════════════════════
        elapsed = round(time.time() - start_time, 2)

        total_duration = sum(
            s.get("duration_seconds", 0) for s in memory.reel_scenes
        )

        prompts_ready = sum(
            1 for s in memory.reel_scenes if s.get("image_prompt")
        )

        logger.info("")
        logger.info("=" * 55)
        logger.info("✅ REEL AGENT V2 पूर्ण")
        logger.info("=" * 55)
        logger.info(f"📖 Story words     : {len(memory.reel_story.split())}")
        logger.info(f"✅ Fact checked    : {memory.reel_fact_checked}")
        logger.info(f"🎬 Scenes created  : {len(memory.reel_scenes)}")
        logger.info(f"⏱️  Est. duration   : {total_duration}s (will adjust to voice)")
        logger.info(f"🎨 Prompts ready   : {prompts_ready}/{len(memory.reel_scenes)}")
        logger.info(f"🎨 Art style       : {memory.image_style}")
        logger.info(f"⏱️  Agent time      : {elapsed}s")
        logger.info("=" * 55)

    except Exception as e:
        logger.error(f"❌ Reel Agent विफल: {e}")
        memory.add_error("reel_agent", str(e))
        raise

    logger.info("=== REEL AGENT V2 पूर्ण ===\n")
    return memory


# ============================================================
# STANDALONE TESTING
# ============================================================

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("REEL AGENT V2 - STANDALONE TEST")
    print("=" * 60 + "\n")

    memory = AgentMemory()
    memory.topic = "Lord Krishna teaching Bhagavad Gita to Arjuna"
    memory.category = "krishna"
    memory.mood = "divine, powerful, wise"
    memory.visual_elements = ["chariot", "battlefield", "krishna", "arjuna"]
    memory.post_type = "reel"

    print(f"📌 Topic: {memory.topic}")
    print(f"📂 Category: {memory.category}")
    print()

    result = run(memory)

    if result.reel_story:
        print(f"\n📖 Story Preview:")
        print(f"   {result.reel_story[:200]}...")
        print(f"\n📊 Stats:")
        print(f"   Words: {len(result.reel_story.split())}")
        print(f"   Fact checked: {result.reel_fact_checked}")
        print(f"   Scenes: {len(result.reel_scenes)}")

        print(f"\n🎬 Scene Breakdown:")
        for scene in result.reel_scenes:
            print(f"\n   ━━━ Scene {scene['scene_number']} ({scene['scene_type']}) ━━━")
            print(f"   Duration : {scene.get('duration_seconds')}s")
            print(f"   Effect   : {scene.get('effect')}")
            print(f"   Narration: {scene['narration'][:80]}...")
            
            if scene.get('image_prompt'):
                print(f"   Prompt   : {scene['image_prompt'][:80]}...")
            else:
                print(f"   Prompt   : ❌ Not built")

        total_duration = sum(s.get("duration_seconds", 0) for s in result.reel_scenes)
        print(f"\n⏱️  Total estimated duration: {total_duration}s")
        print(f"   (Will be adjusted to actual voice duration by reel_engine)")
    else:
        print("❌ No story generated")

    print("\n" + "=" * 60)
    print("REEL AGENT handles Phase 2 (text layer)")
    print("Full video pipeline → reel_engine.py")
    print("=" * 60)
