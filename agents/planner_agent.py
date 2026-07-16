"""
Planner Agent - Strategic Content Decision Maker
Not just picks topic - decides:
- What to post (topic)
- When (best time)
- For whom (target audience)
- Why (SEO + reach strategy)
- How (content angle)
"""
from datetime import datetime, timedelta
from core.memory import AgentMemory
from core.database import (
    get_recent_topics,
    mark_content_used,
    get_best_performing_styles,
    get_connection
)
from config.topics import (
    get_smart_topic,
    get_upcoming_festivals,
    get_current_time_slot,
    get_current_season,
    get_festival_today,
    TIME_PREFERENCES,
    SEASONAL_PREFERENCES
)
from utils.logger import get_logger

logger = get_logger("planner_agent")


# ============================================================
# CONTENT STRATEGY CONFIG
# ============================================================

# Best posting times for different audiences (IST)
PEAK_ENGAGEMENT_HOURS = {
    "morning_worship": (5, 8),      # 5-8 AM: Devotional peak
    "office_break": (12, 14),        # 12-2 PM: Motivational peak
    "evening_prayer": (18, 21),      # 6-9 PM: Family/festival peak
    "night_reflection": (21, 23),    # 9-11 PM: Deep spiritual peak
}

# Day-of-week special preferences
WEEKDAY_PREFERENCES = {
    0: {"day": "Monday",    "deity": "shiva",    "reason": "Shiva's day"},
    1: {"day": "Tuesday",   "deity": "hanuman",  "reason": "Hanuman's day"},
    2: {"day": "Wednesday", "deity": "ganesha",  "reason": "Ganesha's day"},
    3: {"day": "Thursday",  "deity": "krishna",  "reason": "Guru + Krishna's day"},
    4: {"day": "Friday",    "deity": "durga",    "reason": "Devi's day"},
    5: {"day": "Saturday",  "deity": "hanuman",  "reason": "Shani + Hanuman's day"},
    6: {"day": "Sunday",    "deity": "ram",      "reason": "Surya + Ram's day"},
}

# Content variety rules (avoid same category back-to-back)
MIN_CATEGORY_GAP = 2  # Don't repeat category for last 2 posts

# SEO Focus Areas (rotating themes for reach)
SEO_THEMES = [
    "trending_devotional",
    "viral_spiritual",
    "high_engagement_hindi",
    "festival_special",
    "motivational_reels_style",
    "aesthetic_spiritual",
]


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def _get_recent_categories(limit: int = 5) -> list:
    """Get categories from last N posts to avoid repetition"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT category FROM post_history 
            ORDER BY created_at DESC 
            LIMIT ?
        """, (limit,))
        categories = [row[0] for row in cursor.fetchall()]
        conn.close()
        return categories
    except Exception as e:
        logger.warning(f"Failed to fetch recent categories: {e}")
        return []


def _get_todays_post_count() -> int:
    """Count how many posts we've done today"""
    try:
        today = datetime.now().strftime("%Y-%m-%d")
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT COUNT(*) FROM post_history 
            WHERE post_date LIKE ?
        """, (f"{today}%",))
        count = cursor.fetchone()[0]
        conn.close()
        return count
    except Exception:
        return 0


def _get_weekday_deity() -> dict:
    """Get today's weekday deity preference"""
    weekday = datetime.now().weekday()
    return WEEKDAY_PREFERENCES.get(weekday, {})


def _is_peak_engagement_time() -> tuple:
    """Check if current time is peak engagement window"""
    hour = datetime.now().hour
    for slot_name, (start, end) in PEAK_ENGAGEMENT_HOURS.items():
        if start <= hour < end:
            return True, slot_name
    return False, "off_peak"


def _select_seo_theme(post_count_today: int) -> str:
    """Rotate SEO themes to maximize different keyword reach"""
    # Rotate based on post count to hit different themes
    theme_index = (post_count_today + datetime.now().day) % len(SEO_THEMES)
    return SEO_THEMES[theme_index]


def _calculate_content_priority() -> dict:
    """
    Master decision logic - decides overall content strategy
    Returns strategy dict with all decisions
    """
    now = datetime.now()

    # Check factors
    festival = get_festival_today()
    upcoming_festivals = get_upcoming_festivals(days_ahead=3)
    is_peak, peak_slot = _is_peak_engagement_time()
    weekday_info = _get_weekday_deity()
    time_slot = get_current_time_slot()
    season = get_current_season()
    post_count = _get_todays_post_count()
    seo_theme = _select_seo_theme(post_count)

    # Priority scoring
    strategy = {
        "priority_level": "normal",
        "content_angle": "general",
        "target_audience": "spiritual_seekers",
        "seo_theme": seo_theme,
        "time_slot": time_slot,
        "season": season,
        "is_peak_time": is_peak,
        "peak_slot": peak_slot,
        "weekday": weekday_info.get("day", ""),
        "weekday_deity": weekday_info.get("deity", ""),
        "post_count_today": post_count,
        "reasons": []
    }

    # HIGHEST PRIORITY: Today is festival
    if festival:
        strategy["priority_level"] = "critical"
        strategy["content_angle"] = "festival_special"
        strategy["target_audience"] = "festival_devotees"
        strategy["reasons"].append(f"TODAY IS {festival['festival'].upper()}")

    # HIGH PRIORITY: Festival in next 3 days (build anticipation)
    elif upcoming_festivals and upcoming_festivals[0]["days_away"] <= 2:
        strategy["priority_level"] = "high"
        strategy["content_angle"] = "festival_anticipation"
        strategy["target_audience"] = "festival_devotees"
        next_fest = upcoming_festivals[0]
        strategy["reasons"].append(
            f"{next_fest['festival']} in {next_fest['days_away']} days"
        )

    # MEDIUM PRIORITY: Peak engagement time
    elif is_peak:
        strategy["priority_level"] = "high"
        strategy["content_angle"] = "peak_engagement"
        strategy["reasons"].append(f"Peak time: {peak_slot}")

    # Weekday deity boost
    if weekday_info:
        strategy["reasons"].append(
            f"{weekday_info['day']} = {weekday_info['reason']}"
        )

    return strategy


def _select_topic_with_strategy(strategy: dict, recent_topics: list, recent_categories: list) -> dict:
    """
    Select topic based on strategy + avoid repetition
    """
    # If festival today - use festival topic
    if strategy["content_angle"] == "festival_special":
        festival = get_festival_today()
        return {
            "topic": festival["topic"],
            "category": festival.get("category", "festival"),
            "is_festival": True,
            "festival_name": festival["festival"],
            "selection_reason": "festival_today"
        }

    # If festival in 1-2 days - preview/anticipation content
    if strategy["content_angle"] == "festival_anticipation":
        upcoming = get_upcoming_festivals(days_ahead=3)
        if upcoming:
            next_fest = upcoming[0]
            return {
                "topic": f"{next_fest['topic']} - upcoming celebration preparation",
                "category": next_fest.get("category", "festival_moments"),
                "is_festival": False,
                "festival_name": "",
                "selection_reason": f"anticipation_{next_fest['festival']}"
            }

    # Try weekday deity first (if not recently used)
    weekday_deity = strategy.get("weekday_deity", "")
    if weekday_deity and weekday_deity not in recent_categories[:MIN_CATEGORY_GAP]:
        from config.topics import get_topics_by_category
        deity_topics = get_topics_by_category(weekday_deity)
        available_deity = [t for t in deity_topics if t not in recent_topics]

        if available_deity:
            import random
            selected_topic = random.choice(available_deity)
            return {
                "topic": selected_topic,
                "category": weekday_deity,
                "is_festival": False,
                "festival_name": "",
                "selection_reason": f"weekday_deity_{strategy['weekday']}"
            }

       # Fallback: Use smart topic selection (time + season based)
    smart = get_smart_topic(exclude_topics=recent_topics)

    # 🆕 V4: Stronger duplicate prevention — try up to 5 times for variety
    max_variety_attempts = 5
    for variety_attempt in range(max_variety_attempts):
        if smart["category"] not in recent_categories[:MIN_CATEGORY_GAP]:
            break  # Good — different category

        logger.info(
            f"🔄 Category '{smart['category']}' recently used "
            f"(attempt {variety_attempt + 1}/{max_variety_attempts})"
        )
        smart = get_smart_topic(exclude_topics=recent_topics)

    # 🆕 V4: Log final diversity status
    if smart["category"] in recent_categories[:2]:
        logger.warning(f"⚠️  Could not avoid repeat category: {smart['category']}")
    else:
        logger.info(f"✅ Category variety maintained: {smart['category']}")

    return smart


def _log_strategy(strategy: dict):
    """Beautiful strategy logging"""
    logger.info("┌─────────────────────────────────────────────┐")
    logger.info("│         CONTENT STRATEGY DECISION           │")
    logger.info("├─────────────────────────────────────────────┤")
    logger.info(f"│ 🎯 Priority       : {strategy['priority_level']}")
    logger.info(f"│ 📐 Content Angle  : {strategy['content_angle']}")
    logger.info(f"│ 👥 Target         : {strategy['target_audience']}")
    logger.info(f"│ 🕐 Time Slot      : {strategy['time_slot']}")
    logger.info(f"│ 🌸 Season         : {strategy['season']}")
    logger.info(f"│ 📅 Weekday        : {strategy['weekday']}")
    logger.info(f"│ 🙏 Deity of day   : {strategy['weekday_deity']}")
    logger.info(f"│ ⚡ Peak Time      : {strategy['is_peak_time']} ({strategy['peak_slot']})")
    logger.info(f"│ 📊 Today's Posts  : {strategy['post_count_today']}")
    logger.info(f"│ 🔍 SEO Theme      : {strategy['seo_theme']}")
    logger.info("├─────────────────────────────────────────────┤")
    logger.info("│ 📋 Decision Reasons:")
    for reason in strategy['reasons']:
        logger.info(f"│    • {reason}")
    logger.info("└─────────────────────────────────────────────┘")


# ============================================================
# MAIN AGENT FUNCTION
# ============================================================

def run(memory: AgentMemory) -> AgentMemory:
    """
    STRATEGIC content planning:
    1. Analyze current context (time, day, season, festivals)
    2. Calculate content strategy
    3. Select optimal topic
    4. Set SEO focus
    5. Avoid duplicates
    """
    logger.info("=== PLANNER AGENT STARTED ===")

    # ========== STEP 1: ANALYZE CONTEXT ==========
    logger.info("🔍 Analyzing content context...")

    strategy = _calculate_content_priority()
    _log_strategy(strategy)

        # ========== STEP 2: FETCH HISTORY ==========
    recent_topics = get_recent_topics(limit=30)  # 🆕 V4: Check more history
    recent_categories = _get_recent_categories(limit=7)  # 🆕 V4: Check more categories

    logger.info(f"📚 Recent topics to avoid: {len(recent_topics)}")
    logger.info(f"📁 Recent categories: {recent_categories[:5]}")

    # 🆕 V4: Category balance check
    if recent_categories:
        from collections import Counter
        cat_counts = Counter(recent_categories[:7])
        most_common = cat_counts.most_common(1)[0] if cat_counts else ("none", 0)

        if most_common[1] >= 3:
            logger.warning(
                f"⚠️  Category imbalance: '{most_common[0]}' used {most_common[1]} times in last 7 posts!"
            )
            logger.info(f"   🔄 Will try to pick different category for variety")

        # ========== 🆕 V3: CHECK TRENDING NICHE TOPICS ==========
    trending_override = None
    try:
        from trending.niche_detector import get_trending_override
        trending_override = get_trending_override()

        if trending_override and trending_override.get("should_override"):
            logger.info(f"🔥 TRENDING OVERRIDE: {trending_override['topic']}")
            selected = {
                "topic": trending_override["topic"],
                "category": trending_override["category"],
                "is_festival": True,
                "festival_name": trending_override["topic"],
                "selection_reason": f"trending_{trending_override['source']}"
            }
            # Skip normal selection — go directly to Step 4
            memory.topic = selected["topic"]
            memory.category = selected["category"]
            memory.is_festival = selected.get("is_festival", False)
            memory.festival_name = selected.get("festival_name", "")
            memory.analytics_data["strategy"] = strategy
            memory.analytics_data["selection_reason"] = selected["selection_reason"]
            mark_content_used("topic", memory.topic)

            logger.info("┌─────────────────────────────────────────────┐")
            logger.info("│        🔥 TRENDING TOPIC SELECTED            │")
            logger.info("├─────────────────────────────────────────────┤")
            logger.info(f"│ 📌 Topic    : {memory.topic[:50]}")
            logger.info(f"│ 📂 Category : {memory.category}")
            logger.info(f"│ 🔥 Reason   : {trending_override['reason'][:50]}")
            logger.info("└─────────────────────────────────────────────┘")
            logger.info("=== PLANNER AGENT DONE ===")
            return memory

    except ImportError:
        pass  # trending module not installed yet
    except Exception as e:
        logger.warning(f"⚠️  Trending check failed (using normal): {e}")

    # ========== STEP 3: SELECT TOPIC (Normal) ==========
    logger.info("🎯 Selecting optimal topic...")

    selected = _select_topic_with_strategy(
        strategy=strategy,
        recent_topics=recent_topics,
        recent_categories=recent_categories
    )

    # ========== STEP 4: UPDATE MEMORY ==========
    memory.topic = selected["topic"]
    memory.category = selected["category"]
    memory.is_festival = selected.get("is_festival", False)
    memory.festival_name = selected.get("festival_name", "")

    # Store strategy in memory for other agents to use
    memory.analytics_data["strategy"] = strategy
    memory.analytics_data["selection_reason"] = selected["selection_reason"]

    # ========== STEP 5: MARK AS USED ==========
    mark_content_used("topic", memory.topic)

    # ========== STEP 6: LOG DECISION ==========
    logger.info("┌─────────────────────────────────────────────┐")
    logger.info("│           FINAL TOPIC DECISION              │")
    logger.info("├─────────────────────────────────────────────┤")
    logger.info(f"│ 📌 Topic    : {memory.topic[:60]}")
    logger.info(f"│ 📂 Category : {memory.category}")
    logger.info(f"│ 🎉 Festival : {memory.is_festival}")
    if memory.is_festival:
        logger.info(f"│ 🎊 Name     : {memory.festival_name}")
    logger.info(f"│ 💡 Reason   : {selected['selection_reason']}")
    logger.info("└─────────────────────────────────────────────┘")

    logger.info("=== PLANNER AGENT DONE ===")
    return memory


# ============================================================
# STANDALONE TESTING
# ============================================================

if __name__ == "__main__":
    """Test planner independently"""
    from core.database import initialize_database

    print("\n" + "=" * 60)
    print("PLANNER AGENT - STANDALONE TEST")
    print("=" * 60 + "\n")

    initialize_database()

    test_memory = AgentMemory()
    result = run(test_memory)

    print(f"\n✅ Selected Topic: {result.topic}")
    print(f"📂 Category: {result.category}")
    print(f"🎉 Festival: {result.is_festival}")
    print(f"📊 Strategy: {result.analytics_data.get('strategy', {}).get('content_angle')}")