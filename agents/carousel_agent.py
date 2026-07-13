"""
Carousel Agent - Orchestrates full carousel creation
Updated: session_id + recovery support
"""
from core.memory import AgentMemory
from core.carousel_engine import build_carousel
from utils.logger import get_logger

logger = get_logger("carousel_agent")

CAROUSEL_HASHTAGS = """#SanatanSoch #HinduDharma #Sanatan #BharatiyaSanskriti
#SpiritualIndia #HinduismIsWayOfLife #VedicWisdom #DivineIndia
#SanatanDharma #IndianSpirituality #HinduCarousel #SwipeLeft
#StoriesOfGods #HinduMythology #DivineStories #BharatMata
#JaiShriRam #HarHarMahadev #JaiMataKi #Spirituality
#CarouselPost #LearnWithCarousel #SwipeRight #SaveThis
#DivineKnowledge #AncientWisdom"""


def run(memory: AgentMemory) -> AgentMemory:
    """
    Carousel Agent:
    1. session_id + recovery state pass karo
    2. Build karo
    3. Memory me store
    """
    logger.info("=" * 55)
    logger.info("=== CAROUSEL AGENT शुरू ===")
    logger.info("=" * 55)

    if not memory.topic:
        memory.add_error("carousel_agent", "Memory में topic नहीं")
        logger.error("❌ Topic नहीं मिला")
        return memory

    try:
        # ✅ Session ID + recovery state pass karo
        resume_state = None

        if memory.is_recovery:
            logger.info(f"♻️  Recovery mode — memory से data use कर रहे हैं")
            resume_state = {
                "stage": memory.resumed_from_stage,
                "data": {
                    "carousel_slides":  memory.carousel_slides,
                    "carousel_caption": memory.carousel_caption,
                    "carousel_ig_success": memory.carousel_ig_success,
                    "carousel_fb_success": memory.carousel_fb_success,
                },
                "slides_bytes": {
                    s["slide_number"]: s["image_bytes"]
                    for s in memory.carousel_slides
                    if s.get("image_bytes")
                }
            }

        # Build carousel
        result = build_carousel(
            topic=memory.topic,
            category=memory.category,
            session_id=memory.session_id,
            resume_state=resume_state
        )

        if not result["success"]:
            raise Exception(
                f"Carousel build विफल। "
                f"सिर्फ {result['successful_slides']}/5 slides बनी"
            )

        # Store in memory
        memory.post_type        = "carousel"
        memory.carousel_slides  = result["slides"]
        memory.carousel_caption = result["caption"]
        memory.hashtags         = CAROUSEL_HASHTAGS

        logger.info("✅ Carousel Agent पूर्ण")
        logger.info(f"   स्लाइड्स   : {result['successful_slides']}/5")
        logger.info(f"   Caption   : {len(result['caption'])} chars")
        logger.info(f"   समय       : {result['build_time']}s")

        if result.get("images_reused", 0) > 0:
            logger.info(f"   ♻️  पुनः उपयोग: {result['images_reused']} slides")
            logger.info(f"   💰 पैसे बचे : ~₹{result['images_reused'] * 2.5:.2f}")

    except Exception as e:
        logger.error(f"❌ Carousel Agent विफल: {e}")
        memory.add_error("carousel_agent", str(e))
        raise

    logger.info("=== CAROUSEL AGENT पूर्ण ===\n")
    return memory