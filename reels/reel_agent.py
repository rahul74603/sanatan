"""
Reel Agent - Orchestrator for reel content generation

Similar to carousel_agent.py but for reels.

Currently orchestrates (Phase 2):
1. story_writer → Generate Hindi story
2. fact_checker → Verify accuracy
3. scene_splitter → Split into 6 scenes
4. prompt_builder → Build image prompts

Phase 3+ additions (later):
- Call reel_engine for images generation
- Call tts_engine for voice
- Call video_builder for final video

Reuses existing agent pattern.
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

    Currently handles:
    - Story generation
    - Fact checking
    - Scene splitting
    - Prompt building

    Future (Phase 3+):
    - Image generation (6 scenes)
    - TTS voice generation
    - Subtitle generation
    - Video building
    - Upload to GCS

    Note: Full reel_engine.py will handle heavier orchestration later.
    For now, this agent handles Phase 2 (text layer only).
    """
    logger.info("=" * 55)
    logger.info("=== REEL AGENT शुरू ===")
    logger.info("=" * 55)

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
        logger.info("--- चरण 1: कहानी लिख रहे हैं ---")

        if memory.reel_story and memory.is_recovery:
            logger.info("⏭️  Story already exists (recovery), skipping")
        else:
            memory = story_writer.run(memory)

            if not memory.reel_story:
                raise Exception("Story writer failed to generate story")

        # ═══════════════════════════════════════════
        # STEP 2: FACT CHECKER
        # ═══════════════════════════════════════════
        logger.info("")
        logger.info("--- चरण 2: तथ्य जांच ---")

        if memory.reel_fact_checked and memory.is_recovery:
            logger.info("⏭️  Already fact-checked (recovery), skipping")
        else:
            memory = fact_checker.run(memory)

        # ═══════════════════════════════════════════
        # STEP 3: SCENE SPLITTER
        # ═══════════════════════════════════════════
        logger.info("")
        logger.info("--- चरण 3: 6 दृश्यों में विभाजन ---")

        if memory.reel_scenes and memory.is_recovery:
            logger.info(f"⏭️  {len(memory.reel_scenes)} scenes already exist, skipping")
        else:
            memory = scene_splitter.run(memory)

            if not memory.reel_scenes or len(memory.reel_scenes) < 6:
                raise Exception(
                    f"Scene splitter failed: got {len(memory.reel_scenes)} scenes, need 6"
                )

        # ═══════════════════════════════════════════
        # STEP 4: PROMPT BUILDER
        # ═══════════════════════════════════════════
        logger.info("")
        logger.info("--- चरण 4: प्रॉम्प्ट निर्माण ---")

        # Check if prompts already built
        has_prompts = all(
            scene.get("image_prompt") for scene in memory.reel_scenes
        )

        if has_prompts and memory.is_recovery:
            logger.info("⏭️  All prompts already built, skipping")
        else:
            memory = prompt_builder.run(memory)

        # ═══════════════════════════════════════════
        # SET DEFAULT HASHTAGS (if not set)
        # ═══════════════════════════════════════════
        if not memory.hashtags:
            memory.hashtags = REEL_HASHTAGS_DEFAULT
            logger.info(f"📌 Default reel hashtags set ({len(memory.hashtags.split())} tags)")

        # ═══════════════════════════════════════════
        # SUCCESS SUMMARY
        # ═══════════════════════════════════════════
        elapsed = round(time.time() - start_time, 2)

        logger.info("=" * 55)
        logger.info("✅ REEL AGENT PHASE 2 पूर्ण")
        logger.info("=" * 55)
        logger.info(f"📖 Story words     : {len(memory.reel_story.split())}")
        logger.info(f"✅ Fact checked    : {memory.reel_fact_checked}")
        logger.info(f"🎬 Scenes created  : {len(memory.reel_scenes)}")

        total_duration = sum(
            s.get("duration_seconds", 0) for s in memory.reel_scenes
        )
        logger.info(f"⏱️  Video duration  : {total_duration}s")

        prompts_ready = sum(
            1 for s in memory.reel_scenes if s.get("image_prompt")
        )
        logger.info(f"🎨 Prompts ready   : {prompts_ready}/{len(memory.reel_scenes)}")
        logger.info(f"🎨 Art style       : {memory.image_style}")
        logger.info(f"⏱️  Total time      : {elapsed}s")
        logger.info("")
        logger.info("⏸️  NOTE: Phase 3+ (images, voice, video) not yet implemented")
        logger.info("=" * 55)

    except Exception as e:
        logger.error(f"❌ Reel Agent विफल: {e}")
        memory.add_error("reel_agent", str(e))
        raise

    logger.info("=== REEL AGENT पूर्ण ===\n")
    return memory


# ============================================================
# STANDALONE TESTING
# ============================================================

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("REEL AGENT - STANDALONE TEST (Phase 2)")
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

    print(f"\n📖 Story:\n{result.reel_story}")
    print(f"\n🎬 Total scenes: {len(result.reel_scenes)}")

    for scene in result.reel_scenes:
        print(f"\n━━━ Scene {scene['scene_number']} ({scene['scene_type']}) ━━━")
        print(f"Duration: {scene.get('duration_seconds')}s | Effect: {scene.get('effect')}")
        print(f"Narration: {scene['narration']}")
        print(f"Prompt: {scene.get('image_prompt', 'N/A')[:100]}...")