"""
Niche Detector - Integrate trending topics into planner

V3 Features:
- Checks Hindu calendar for upcoming events
- Boosts planner priority for trending topics
- Override regular topic when big festival approaching
- Maintains niche focus (NEVER goes outside spiritual)
"""
from trending.calendar_events import (
    get_trending_niche_topics,
    get_todays_event,
    get_special_month_boost,
)
from utils.logger import get_logger

logger = get_logger("niche_detector")


def get_trending_override() -> dict:
    """
    🆕 V3: Check if today's content should be overridden by trending topic.

    Returns:
        {
            "should_override": True/False,
            "topic": "trending topic",
            "category": "category",
            "priority": 1-5,
            "reason": "why override"
        }
        
        or None if no override needed.
    """
    logger.info("🔍 Checking for niche trending override...")

    trending = get_trending_niche_topics(max_topics=1)

    if not trending:
        logger.info("✅ No trending override — regular rotation")
        return None

    top = trending[0]

    # Only override if priority >= 4 (BIG events)
    if top["priority"] >= 4:
        logger.info(f"🔥 TRENDING OVERRIDE: {top['topic']} (priority {top['priority']})")
        return {
            "should_override": True,
            "topic": top["topic"],
            "category": top["category"],
            "priority": top["priority"],
            "reason": top["reason"],
            "source": top["source"],
        }

    # Priority 3 = suggest but don't force
    if top["priority"] == 3:
        logger.info(f"📌 TRENDING SUGGESTION: {top['topic']} (priority {top['priority']})")
        return {
            "should_override": False,
            "topic": top["topic"],
            "category": top["category"],
            "priority": top["priority"],
            "reason": top["reason"],
            "source": top["source"],
        }

    return None


# ============================================================
# STANDALONE TEST
# ============================================================

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("NICHE DETECTOR V3 - TEST")
    print("=" * 60 + "\n")

    override = get_trending_override()

    if override:
        print(f"🔥 Result: {'OVERRIDE' if override['should_override'] else 'SUGGESTION'}")
        print(f"   Topic: {override['topic']}")
        print(f"   Category: {override['category']}")
        print(f"   Priority: {override['priority']}/5")
        print(f"   Reason: {override['reason']}")
    else:
        print("✅ No trending topic — use regular rotation")