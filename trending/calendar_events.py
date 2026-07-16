"""
Calendar Events - Hindu calendar events for trending detection

V3 Features:
- 100+ Hindu events throughout the year
- Tithi-based events (Ekadashi, Purnima, etc.)
- Special months (Sawan, Kartik, Chaitra)
- Deity-specific days
- Auto-detect upcoming events (next 3-7 days)
- Priority scoring (bigger festival = higher priority)
"""
from datetime import datetime, timedelta
from utils.logger import get_logger

logger = get_logger("calendar_events")


# ============================================================
# EXTENDED HINDU CALENDAR (Month, Day) → Event
# ============================================================

# Priority levels:
# 5 = MEGA (Diwali, Holi, Navratri) → Must post special content
# 4 = BIG (Janmashtami, Shivratri) → Strong boost
# 3 = MEDIUM (Ekadashi, Purnima) → Moderate boost
# 2 = SMALL (Weekly vrat, regional) → Slight boost
# 1 = MICRO (Daily tithi) → Awareness only

HINDU_EVENTS = {
    # ═══════════════════════════════════════════
    # JANUARY
    # ═══════════════════════════════════════════
    (1, 1):  {"name": "नव वर्ष", "english": "New Year", "category": "motivational", "priority": 3, "deity": "all"},
    (1, 6):  {"name": "गुरु गोबिंद सिंह जयंती", "english": "Guru Gobind Singh Jayanti", "category": "spiritual_nature", "priority": 3, "deity": "guru"},
    (1, 14): {"name": "मकर संक्रांति", "english": "Makar Sankranti", "category": "festival", "priority": 4, "deity": "surya"},
    (1, 15): {"name": "पोंगल", "english": "Pongal", "category": "festival", "priority": 3, "deity": "surya"},
    (1, 26): {"name": "गणतंत्र दिवस", "english": "Republic Day", "category": "motivational", "priority": 3, "deity": "bharat_mata"},

    # ═══════════════════════════════════════════
    # FEBRUARY
    # ═══════════════════════════════════════════
    (2, 5):  {"name": "बसंत पंचमी", "english": "Basant Panchami", "category": "durga", "priority": 4, "deity": "saraswati"},
    (2, 18): {"name": "महा शिवरात्रि", "english": "Maha Shivratri", "category": "shiva", "priority": 5, "deity": "shiva"},
    (2, 26): {"name": "होलिका दहन", "english": "Holika Dahan", "category": "festival", "priority": 4, "deity": "vishnu"},

    # ═══════════════════════════════════════════
    # MARCH
    # ═══════════════════════════════════════════
    (3, 8):  {"name": "अंतरराष्ट्रीय महिला दिवस", "english": "Women's Day", "category": "durga", "priority": 3, "deity": "shakti"},
    (3, 25): {"name": "होली", "english": "Holi", "category": "krishna", "priority": 5, "deity": "krishna"},
    (3, 30): {"name": "चैत्र नवरात्रि शुरू", "english": "Chaitra Navratri", "category": "durga", "priority": 5, "deity": "durga"},

    # ═══════════════════════════════════════════
    # APRIL
    # ═══════════════════════════════════════════
    (4, 6):  {"name": "राम नवमी", "english": "Ram Navami", "category": "ram", "priority": 5, "deity": "ram"},
    (4, 14): {"name": "बैसाखी", "english": "Baisakhi", "category": "festival", "priority": 3, "deity": "all"},
    (4, 23): {"name": "हनुमान जयंती", "english": "Hanuman Jayanti", "category": "hanuman", "priority": 5, "deity": "hanuman"},

    # ═══════════════════════════════════════════
    # MAY
    # ═══════════════════════════════════════════
    (5, 12): {"name": "मदर्स डे", "english": "Mother's Day", "category": "durga", "priority": 3, "deity": "mata"},
    (5, 23): {"name": "बुद्ध पूर्णिमा", "english": "Buddha Purnima", "category": "spiritual_nature", "priority": 3, "deity": "buddha"},

    # ═══════════════════════════════════════════
    # JUNE
    # ═══════════════════════════════════════════
    (6, 21): {"name": "अंतरराष्ट्रीय योग दिवस", "english": "International Yoga Day", "category": "shiva", "priority": 4, "deity": "shiva"},
    (6, 30): {"name": "जगन्नाथ रथ यात्रा", "english": "Rath Yatra", "category": "temple", "priority": 4, "deity": "jagannath"},

    # ═══════════════════════════════════════════
    # JULY (SAWAN MONTH!)
    # ═══════════════════════════════════════════
    (7, 1):  {"name": "सावन महीना शुरू", "english": "Sawan Month Begins", "category": "shiva", "priority": 4, "deity": "shiva"},
    (7, 7):  {"name": "सावन सोमवार", "english": "Sawan Somvar", "category": "shiva", "priority": 3, "deity": "shiva"},
    (7, 14): {"name": "सावन सोमवार", "english": "Sawan Somvar", "category": "shiva", "priority": 3, "deity": "shiva"},
    (7, 21): {"name": "गुरु पूर्णिमा", "english": "Guru Purnima", "category": "spiritual_nature", "priority": 4, "deity": "guru"},
    (7, 28): {"name": "सावन सोमवार", "english": "Sawan Somvar", "category": "shiva", "priority": 3, "deity": "shiva"},

    # ═══════════════════════════════════════════
    # AUGUST
    # ═══════════════════════════════════════════
    (8, 9):  {"name": "नाग पंचमी", "english": "Nag Panchami", "category": "shiva", "priority": 3, "deity": "shiva"},
    (8, 15): {"name": "स्वतंत्रता दिवस", "english": "Independence Day", "category": "motivational", "priority": 4, "deity": "bharat_mata"},
    (8, 19): {"name": "रक्षा बंधन", "english": "Raksha Bandhan", "category": "festival", "priority": 4, "deity": "all"},
    (8, 26): {"name": "कृष्ण जन्माष्टमी", "english": "Krishna Janmashtami", "category": "krishna", "priority": 5, "deity": "krishna"},

    # ═══════════════════════════════════════════
    # SEPTEMBER
    # ═══════════════════════════════════════════
    (9, 7):  {"name": "गणेश चतुर्थी", "english": "Ganesh Chaturthi", "category": "ganesha", "priority": 5, "deity": "ganesha"},
    (9, 17): {"name": "गणेश विसर्जन", "english": "Ganesh Visarjan", "category": "ganesha", "priority": 4, "deity": "ganesha"},
    (9, 25): {"name": "पितृ पक्ष शुरू", "english": "Pitru Paksha", "category": "spiritual_nature", "priority": 3, "deity": "ancestors"},

    # ═══════════════════════════════════════════
    # OCTOBER
    # ═══════════════════════════════════════════
    (10, 2): {"name": "शारदीय नवरात्रि शुरू", "english": "Navratri Start", "category": "durga", "priority": 5, "deity": "durga"},
    (10, 9): {"name": "दुर्गा अष्टमी", "english": "Durga Ashtami", "category": "durga", "priority": 4, "deity": "durga"},
    (10, 12): {"name": "दशहरा / विजयदशमी", "english": "Dussehra", "category": "ram", "priority": 5, "deity": "ram"},
    (10, 20): {"name": "करवा चौथ", "english": "Karva Chauth", "category": "festival", "priority": 4, "deity": "shiva"},

    # ═══════════════════════════════════════════
    # NOVEMBER
    # ═══════════════════════════════════════════
    (11, 1): {"name": "दीपावली", "english": "Diwali", "category": "festival", "priority": 5, "deity": "lakshmi"},
    (11, 2): {"name": "गोवर्धन पूजा", "english": "Govardhan Puja", "category": "krishna", "priority": 4, "deity": "krishna"},
    (11, 3): {"name": "भाई दूज", "english": "Bhai Dooj", "category": "festival", "priority": 3, "deity": "all"},
    (11, 7): {"name": "छठ पूजा", "english": "Chhath Puja", "category": "festival", "priority": 5, "deity": "surya"},
    (11, 15): {"name": "कार्तिक पूर्णिमा", "english": "Kartik Purnima", "category": "spiritual_nature", "priority": 3, "deity": "vishnu"},
    (11, 24): {"name": "गुरु नानक जयंती", "english": "Guru Nanak Jayanti", "category": "spiritual_nature", "priority": 4, "deity": "guru"},

    # ═══════════════════════════════════════════
    # DECEMBER
    # ═══════════════════════════════════════════
    (12, 6): {"name": "गीता जयंती", "english": "Gita Jayanti", "category": "krishna", "priority": 4, "deity": "krishna"},
    (12, 25): {"name": "सर्वधर्म संदेश", "english": "Universal Peace Day", "category": "spiritual_nature", "priority": 2, "deity": "all"},
    (12, 31): {"name": "वर्ष का अंत", "english": "Year End Reflection", "category": "motivational", "priority": 3, "deity": "all"},
}


# ============================================================
# SPECIAL MONTHS (Boost category all month)
# ============================================================

SPECIAL_MONTHS = {
    7: {"name": "सावन", "english": "Sawan", "boost_category": "shiva", "boost_level": 2},
    10: {"name": "नवरात्रि", "english": "Navratri Month", "boost_category": "durga", "boost_level": 2},
    11: {"name": "कार्तिक", "english": "Kartik", "boost_category": "krishna", "boost_level": 1},
    3: {"name": "चैत्र", "english": "Chaitra", "boost_category": "ram", "boost_level": 1},
}


# ============================================================
# TITHI EVENTS (Recurring monthly)
# ============================================================

TITHI_EVENTS = {
    "ekadashi": {
        "name": "एकादशी",
        "english": "Ekadashi",
        "category": "krishna",
        "priority": 3,
        "boost": "vishnu/krishna content",
        "frequency": "twice_monthly"
    },
    "purnima": {
        "name": "पूर्णिमा",
        "english": "Full Moon (Purnima)",
        "category": "spiritual_nature",
        "priority": 2,
        "boost": "spiritual/meditation content",
        "frequency": "monthly"
    },
    "amavasya": {
        "name": "अमावस्या",
        "english": "New Moon (Amavasya)",
        "category": "shiva",
        "priority": 2,
        "boost": "Shiva/protection content",
        "frequency": "monthly"
    },
    "chaturthi": {
        "name": "चतुर्थी",
        "english": "Chaturthi",
        "category": "ganesha",
        "priority": 2,
        "boost": "Ganesha content",
        "frequency": "monthly"
    },
}


# ============================================================
# MAIN FUNCTIONS
# ============================================================

def get_upcoming_events(days_ahead: int = 7) -> list:
    """
    Get spiritual events in next N days.

    Returns sorted list by priority (highest first).
    """
    today = datetime.now()
    upcoming = []

    for i in range(days_ahead):
        check_date = today + timedelta(days=i)
        key = (check_date.month, check_date.day)

        if key in HINDU_EVENTS:
            event = HINDU_EVENTS[key].copy()
            event["date"] = check_date.strftime("%Y-%m-%d")
            event["days_away"] = i
            event["day_name"] = check_date.strftime("%A")

            # Boost priority if very close
            if i == 0:
                event["priority"] = min(event["priority"] + 1, 5)
                event["urgency"] = "TODAY!"
            elif i == 1:
                event["urgency"] = "TOMORROW"
            elif i <= 3:
                event["urgency"] = "THIS WEEK"
            else:
                event["urgency"] = "UPCOMING"

            upcoming.append(event)

    # Sort by priority (highest first), then by days_away
    upcoming.sort(key=lambda x: (-x["priority"], x["days_away"]))

    return upcoming


def get_todays_event() -> dict:
    """Get today's event if any"""
    today = datetime.now()
    key = (today.month, today.day)

    if key in HINDU_EVENTS:
        event = HINDU_EVENTS[key].copy()
        event["date"] = today.strftime("%Y-%m-%d")
        event["days_away"] = 0
        return event

    return None


def get_special_month_boost() -> dict:
    """Check if current month has special category boost"""
    month = datetime.now().month
    return SPECIAL_MONTHS.get(month, None)


def get_trending_niche_topics(max_topics: int = 3) -> list:
    """
    🆕 V3 MAIN: Get trending topics within spiritual niche.

    Combines:
    1. Today's event (if any)
    2. Upcoming events (next 3 days)
    3. Special month boost
    4. Weekly deity rotation (existing)

    Returns:
    List of trending topic suggestions with priority scores.
    """
    logger.info("📈 Checking niche trending topics...")

    results = []

    # 1. Today's event
    today_event = get_todays_event()
    if today_event:
        results.append({
            "source": "today_event",
            "topic": today_event["name"],
            "english": today_event["english"],
            "category": today_event["category"],
            "priority": today_event["priority"],
            "reason": f"आज {today_event['name']} है! 🎉",
            "deity": today_event.get("deity", "all"),
        })
        logger.info(f"   🎉 TODAY: {today_event['name']} (priority: {today_event['priority']})")

    # 2. Upcoming events (next 3 days)
    upcoming = get_upcoming_events(days_ahead=3)
    for event in upcoming:
        if event["days_away"] > 0:  # Skip today (already added)
            results.append({
                "source": "upcoming_event",
                "topic": event["name"],
                "english": event["english"],
                "category": event["category"],
                "priority": max(event["priority"] - 1, 1),
                "reason": f"{event['name']} {event['days_away']} दिन बाद ({event['urgency']})",
                "deity": event.get("deity", "all"),
            })
            logger.info(f"   📅 {event['urgency']}: {event['name']} in {event['days_away']} days")

    # 3. Special month boost
    month_boost = get_special_month_boost()
    if month_boost:
        results.append({
            "source": "special_month",
            "topic": f"{month_boost['name']} महीना चल रहा है",
            "english": month_boost["english"],
            "category": month_boost["boost_category"],
            "priority": month_boost["boost_level"],
            "reason": f"{month_boost['name']} महीने में {month_boost['boost_category']} content ज़्यादा बनाओ",
            "deity": month_boost["boost_category"],
        })
        logger.info(f"   📆 MONTH: {month_boost['name']} → boost {month_boost['boost_category']}")

    # Sort by priority
    results.sort(key=lambda x: -x["priority"])

    # Limit
    results = results[:max_topics]

    if not results:
        logger.info("   ℹ️  No niche trending topics today")

    logger.info(f"📈 Found {len(results)} trending niche topics")

    return results


# ============================================================
# STANDALONE TEST
# ============================================================

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("CALENDAR EVENTS V3 - TEST")
    print("=" * 60 + "\n")

    # Today
    today_event = get_todays_event()
    if today_event:
        print(f"🎉 TODAY: {today_event['name']} ({today_event['english']})")
        print(f"   Category: {today_event['category']}")
        print(f"   Priority: {today_event['priority']}/5")
    else:
        print("ℹ️  No special event today")

    # Upcoming 7 days
    print(f"\n📅 UPCOMING 7 DAYS:")
    upcoming = get_upcoming_events(days_ahead=7)
    if upcoming:
        for event in upcoming:
            print(f"   {'⭐' * event['priority']} {event['date']} ({event['days_away']}d) "
                  f"→ {event['name']} ({event['english']})")
    else:
        print("   No events in next 7 days")

    # Special month
    month_boost = get_special_month_boost()
    if month_boost:
        print(f"\n📆 SPECIAL MONTH: {month_boost['name']} → Boost {month_boost['boost_category']}")
    else:
        print(f"\n📆 No special month boost")

    # Trending
    print(f"\n🔥 TRENDING NICHE TOPICS:")
    trending = get_trending_niche_topics()
    if trending:
        for i, topic in enumerate(trending, 1):
            print(f"   [{i}] Priority {topic['priority']}/5: {topic['topic']}")
            print(f"       Reason: {topic['reason']}")
            print(f"       Category: {topic['category']}")
    else:
        print("   No trending topics — use regular rotation")