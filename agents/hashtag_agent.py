"""
Hashtag Agent - SEO-Optimized Intelligent Hashtag Generator
Features:
- Category-specific hashtag intelligence
- Instagram algorithm optimized (mix of reach tiers)
- Trending hashtag detection
- Anti-shadow-ban protection
- SEO keyword integration
- Regional targeting (India-specific)
- Auto-deduplication
- Length + count validation

V2 UPDATE: Added REEL_SPECIFIC_HASHTAGS + post_type awareness
"""
import random
import re
from core.memory import AgentMemory
from utils.logger import get_logger

logger = get_logger("hashtag_agent")


# ============================================================
# COMPREHENSIVE HASHTAG DATABASE
# Organized by: reach tier + category
# ============================================================

# ═══════════════════════════════════════════════════════════
# TIER 1: MASSIVE REACH (1M+ posts) - Use 2-3 max
# ═══════════════════════════════════════════════════════════
TIER_1_MASSIVE = [
    "#india", "#instagood", "#love", "#life", "#viral",
    "#trending", "#explore", "#explorepage", "#instadaily",
    "#photooftheday", "#reels", "#reelsinstagram"
]

# ═══════════════════════════════════════════════════════════
# TIER 2: HIGH REACH (500K-1M posts) - Use 4-5
# ═══════════════════════════════════════════════════════════
TIER_2_HIGH = {
    "spiritual": [
        "#spiritual", "#spirituality", "#meditation", "#yoga",
        "#hindu", "#hinduism", "#namaste", "#om", "#divine",
        "#bhakti", "#dharma", "#karma"
    ],
    "motivational": [
        "#motivation", "#motivational", "#inspiration",
        "#success", "#mindset", "#positivevibes", "#quotes",
        "#lifequotes", "#quoteoftheday"
    ],
    "cultural": [
        "#incredibleindia", "#indianculture", "#indianart",
        "#festivalsofindia", "#traditionalart"
    ]
}

# ═══════════════════════════════════════════════════════════
# TIER 3: MEDIUM REACH (100K-500K posts) - Use 6-8 (SWEET SPOT)
# ═══════════════════════════════════════════════════════════
TIER_3_MEDIUM = {
    "krishna": [
        "#krishna", "#lordkrishna", "#radhakrishna", "#krishnabhakt",
        "#jaishrikrishna", "#radheradhe", "#harekrishna", "#krishnalove",
        "#murlimanohar", "#kanhaiya", "#vrindavan", "#mathura"
    ],
    "shiva": [
        "#mahadev", "#shiva", "#lordshiva", "#shivbhakt",
        "#harharmahadev", "#omnamahshivaya", "#bholenath",
        "#bhole", "#mahakal", "#shivshankar", "#kailash", "#trishul"
    ],
    "hanuman": [
        "#hanuman", "#hanumanji", "#bajrangbali", "#jaihanuman",
        "#jaibajrangbali", "#hanumanbhakt", "#sankatmochan",
        "#pawanputra", "#ramnaam", "#hanumanchalisa"
    ],
    "ganesha": [
        "#ganesha", "#ganpati", "#ganpatibappa", "#ganpatibappamorya",
        "#jaiganesh", "#vinayak", "#lordganesha", "#ganeshji",
        "#modak", "#vighnaharta", "#mangalmurti"
    ],
    "durga": [
        "#durga", "#durgamaa", "#maadurga", "#jaimatadi", "#sherawali",
        "#navratri", "#navdurga", "#kalimaa", "#ambe", "#devi",
        "#shakti", "#jagatjanani", "#bhavani"
    ],
    "ram": [
        "#ram", "#lordram", "#jaishriram", "#ramayan", "#sitaram",
        "#siyaram", "#rambhakt", "#ayodhya", "#rammandir",
        "#raghukulriti", "#maryadapurushottam"
    ],
    "hindi_content": [
        "#hindiquotes", "#hindishayari", "#hindipoetry", "#hindilines",
        "#suvichar", "#anmolvachan", "#hindiwriting", "#hindithoughts",
        "#zindagiquotes", "#jeevanquotes", "#gyaan", "#hindivichar"
    ],
    "life_wisdom": [
        "#lifelessons", "#wisdom", "#lifelesson", "#truewords",
        "#truthoflife", "#realtalk", "#dailywisdom", "#morningthoughts",
        "#deepthoughts", "#positivevibesonly"
    ],
    "temple": [
        "#temple", "#mandir", "#templesofindia", "#ancienttemples",
        "#kashi", "#varanasi", "#tirupati", "#vaishnodevi",
        "#kedarnath", "#badrinath", "#jagannathpuri"
    ]
}

# ═══════════════════════════════════════════════════════════
# TIER 4: NICHE REACH (10K-100K posts) - Use 5-7 (BEST FOR RANKING)
# ═══════════════════════════════════════════════════════════
TIER_4_NICHE = {
    "deep_spiritual": [
        "#spiritualawakening", "#spiritualjourney", "#soulfulquotes",
        "#innerpeace", "#soulawakening", "#spiritualwisdom",
        "#divinelove", "#divineenergy", "#sacredspace",
        "#consciousliving", "#higherconsciousness", "#awakening"
    ],
    "gita_wisdom": [
        "#bhagavadgita", "#gitawisdom", "#krishnasays",
        "#geetasaar", "#gitaquotes", "#krishnaquotes",
        "#krishnaupdesh", "#gitagyaan"
    ],
    "shiva_specific": [
        "#shivbhakti", "#mahakaal", "#adiyogi", "#natraj",
        "#tandav", "#neelkanth", "#rudra", "#shivalinga",
        "#kanwariyas", "#sawan", "#somvar"
    ],
    "krishna_specific": [
        "#krishnaconsciousness", "#krishnastories", "#gopal",
        "#krishnajanmashtami", "#dwarkadhish", "#nandalala",
        "#bansuriwale", "#pyare_kanha", "#krishnadarshan"
    ],
    "regional": [
        "#uttarakhand", "#himalayas", "#rishikesh", "#haridwar",
        "#varanasi", "#mathura_vrindavan", "#ayodhyadham",
        "#chardham", "#jyotirlinga", "#shaktipeeth"
    ],
    "daily_bhakti": [
        "#dailybhakti", "#morningbhakti", "#eveningprayer",
        "#dailyprayer", "#dailyshloka", "#morningmotivation",
        "#dailymotivation", "#morningthoughts"
    ],
    "aesthetic": [
        "#aestheticspiritual", "#spiritualaesthetic",
        "#peacefulvibes", "#calmvibes", "#zenaesthetic",
        "#mindfulmoments", "#soulaesthetic"
    ]
}

# ═══════════════════════════════════════════════════════════
# TIER 5: MICRO NICHE (< 10K posts) - Use 2-3 (LOW COMPETITION)
# ═══════════════════════════════════════════════════════════
TIER_5_MICRO = {
    "personal_brand": [
        "#sanatansooch", "#sanatan_sooch", "#dharmicthoughts",
        "#vedicgyan", "#hindugyan", "#sanatanivichar",
        "#sanatanithoughts", "#hindutradition"
    ],
    "specific_practices": [
        "#gayatrimantra", "#hanumanchalisapath", "#mahamrityunjaya",
        "#omnamoharayana", "#brahmamuhurta", "#pranayama",
        "#pujaathome", "#homemandir"
    ],
    "engagement_niche": [
        "#doublemtapifyoulove", "#tagafriend", "#saveforlater",
        "#shareitforward", "#spreadlove", "#spreadpositivity"
    ]
}

# ═══════════════════════════════════════════════════════════
# FESTIVAL SPECIFIC (Use ONLY on festival days)
# ═══════════════════════════════════════════════════════════
FESTIVAL_HASHTAGS = {
    "Diwali": ["#diwali", "#happydiwali", "#diwali2024", "#festivaloflights",
               "#deepavali", "#diwalicelebration", "#shubhdeepawali"],
    "Holi": ["#holi", "#happyholi", "#holi2024", "#festivalofcolors",
             "#holihai", "#rangbaraseholi", "#holicelebration"],
    "Janmashtami": ["#janmashtami", "#krishnajanmashtami", "#happyjanmashtami",
                    "#krishnajanm", "#gokulashtami", "#dahihandi"],
    "Ganesh Chaturthi": ["#ganeshchaturthi", "#ganeshotsav", "#ganpatifestival",
                         "#ganeshfestival", "#bappacoming", "#morya"],
    "Navratri": ["#navratri", "#navratrifestival", "#navratri2024",
                 "#navratrivibes", "#garba", "#dandiya", "#durgapuja"],
    "Dussehra": ["#dussehra", "#vijayadashami", "#ramvsravan",
                 "#raamlila", "#dussehra2024"],
    "Ram Navami": ["#ramnavami", "#ramnavmi", "#happyramnavami",
                   "#jaishriram", "#ramjanm"],
    "Hanuman Jayanti": ["#hanumanjayanti", "#hanumanjanamotsav",
                        "#jaihanuman", "#bajrangbali"],
    "Maha Shivratri": ["#mahashivratri", "#shivratri", "#shivratri2024",
                       "#harharmahadev", "#shivpuja", "#omnamahshivaya"],
    "Karva Chauth": ["#karvachauth", "#karwachauth", "#karvachauth2024"],
    "Raksha Bandhan": ["#rakshabandhan", "#rakhi", "#rakhi2024",
                       "#bhaibehen", "#brothersister"],
    "Makar Sankranti": ["#makarsankranti", "#uttarayan", "#pongal",
                        "#kites", "#tilgud"],
    "Basant Panchami": ["#basantpanchami", "#saraswatipuja", "#vasantpanchami"],
    "Guru Purnima": ["#gurupurnima", "#gurupoornima", "#guru", "#gurubhakti"],
    "Buddha Purnima": ["#buddhapurnima", "#buddhajayanti", "#gautamabuddha"],
    "Independence Day": ["#independenceday", "#15august", "#jaihind",
                        "#happyindependenceday", "#india75"],
    "Republic Day": ["#republicday", "#26january", "#jaihind",
                    "#happyrepublicday", "#indiafirst"]
}

# ═══════════════════════════════════════════════════════════
# TIME-BASED HASHTAGS (Morning / Evening / Night)
# ═══════════════════════════════════════════════════════════
TIME_HASHTAGS = {
    "morning": [
        "#morningmotivation", "#morningthoughts", "#sunrisevibes",
        "#morningprayer", "#morningblessing", "#morningpositivity"
    ],
    "evening": [
        "#eveningvibes", "#eveningprayer", "#eveningaarti",
        "#eveningthoughts", "#sunsetvibes"
    ],
    "night": [
        "#nightvibes", "#nightthoughts", "#nighttime",
        "#peacefulnight", "#latenightthoughts"
    ]
}

# ═══════════════════════════════════════════════════════════
# WEEKDAY HASHTAGS (Deity-specific days)
# ═══════════════════════════════════════════════════════════
WEEKDAY_HASHTAGS = {
    0: ["#mondaymotivation", "#mondaymahadev", "#somvar", "#shivsomvar"],
    1: ["#tuesdaymotivation", "#mangalvaar", "#hanumanmangalvar"],
    2: ["#wednesdaywisdom", "#buddhvaar", "#ganeshwednesday"],
    3: ["#thursdaythoughts", "#guruvaar", "#krishnathursday"],
    4: ["#fridayfeeling", "#shukravaar", "#devifriday"],
    5: ["#saturdaysunset", "#shanivaar", "#shanidev"],
    6: ["#sundayvibes", "#ravivaar", "#suryadev"]
}


# ═══════════════════════════════════════════════════════════
# 🆕 V2: REEL-SPECIFIC HASHTAGS (Instagram Reels + YT Shorts)
# ═══════════════════════════════════════════════════════════
REEL_SPECIFIC_HASHTAGS = [
    # Reel platform tags
    "#reels", "#reelsinstagram", "#reelitfeelit", "#reelkarofeelkaro",
    "#trendingreels", "#viralreels", "#instareels", "#reelsindia",

    # Short video tags
    "#shorts", "#youtubeshorts", "#shortsvideo", "#shortsindia",
    "#shortsfeed", "#shortvideo", "#shortsyoutube",

    # Content type
    "#spiritualreels", "#devotionalreels", "#storyreels",
    "#educationalreels", "#mythologyreels", "#reelsspiritual",
    "#dharmicreels", "#hindureels"
]


# ═══════════════════════════════════════════════════════════
# BLOCKED / SHADOW-BAN RISK (NEVER USE)
# ═══════════════════════════════════════════════════════════
BLOCKED_HASHTAGS = {
    "#follow", "#followme", "#follow4follow", "#f4f",
    "#like", "#like4like", "#l4l", "#instalike",
    "#sex", "#adult", "#nude", "#porn",
    "#instagram", "#instapic", "#instalike",
    "#tagsforlikes", "#likeforlike", "#followforfollow"
}


# ============================================================
# STRATEGY: INSTAGRAM ALGORITHM OPTIMAL MIX
# ============================================================

OPTIMAL_MIX = {
    "tier_1_massive": 2,      # 2 huge hashtags
    "tier_2_high": 4,          # 4 high reach
    "tier_3_medium": 8,        # 8 medium (SWEET SPOT)
    "tier_4_niche": 6,         # 6 niche (RANKING BOOST)
    "tier_5_micro": 3,         # 3 micro (LOW COMPETITION)
    "festival": 2,             # 2 if festival day
    "time_weekday": 2,         # 2 time/weekday specific
    "keywords": 3,             # 3 from research keywords
    "reel_specific": 5,        # 🆕 5 reel tags (if post_type=reel)
}

# Total: ~28-30 hashtags → Trim to 25 (Instagram sweet spot)


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def _sanitize_hashtag(text: str) -> str:
    """Convert any string to valid hashtag"""
    # Remove special characters, keep only alphanumeric
    clean = re.sub(r'[^a-zA-Z0-9]', '', text)
    return f"#{clean.lower()}" if clean else ""


def _get_category_hashtags(category: str, tier_source: dict, count: int) -> list:
    """Get hashtags from specific tier for category"""
    # Direct match
    if category in tier_source:
        pool = tier_source[category]
    # Fuzzy match (e.g., "festival_moments" → try "festival")
    else:
        pool = []
        for key, values in tier_source.items():
            if key in category or category in key:
                pool.extend(values)

    if not pool:
        return []

    return random.sample(pool, min(count, len(pool)))


def _get_time_hashtags() -> list:
    """Get hashtags based on current time"""
    from datetime import datetime
    hour = datetime.now().hour

    if 5 <= hour < 12:
        return random.sample(TIME_HASHTAGS["morning"], 2)
    elif 12 <= hour < 18:
        return []  # Afternoon has no specific hashtags
    elif 18 <= hour < 22:
        return random.sample(TIME_HASHTAGS["evening"], 2)
    else:
        return random.sample(TIME_HASHTAGS["night"], 2)


def _get_weekday_hashtags() -> list:
    """Get today's weekday-specific hashtags"""
    from datetime import datetime
    weekday = datetime.now().weekday()
    day_tags = WEEKDAY_HASHTAGS.get(weekday, [])
    return random.sample(day_tags, min(2, len(day_tags))) if day_tags else []


def _get_festival_hashtags(festival_name: str) -> list:
    """Get festival-specific hashtags"""
    if festival_name in FESTIVAL_HASHTAGS:
        return FESTIVAL_HASHTAGS[festival_name][:4]

    # Fuzzy match
    for fest, tags in FESTIVAL_HASHTAGS.items():
        if fest.lower() in festival_name.lower() or festival_name.lower() in fest.lower():
            return tags[:4]

    return []


def _get_keyword_hashtags(keywords: list) -> list:
    """Convert research keywords to hashtags"""
    tags = []
    for kw in keywords[:5]:
        tag = _sanitize_hashtag(kw)
        if tag and len(tag) > 3 and tag not in BLOCKED_HASHTAGS:
            tags.append(tag)
    return tags


def _get_reel_hashtags(count: int = 5) -> list:
    """🆕 Get reel-specific hashtags"""
    return random.sample(
        REEL_SPECIFIC_HASHTAGS,
        min(count, len(REEL_SPECIFIC_HASHTAGS))
    )


def _remove_duplicates_preserve_order(hashtags: list) -> list:
    """Remove duplicates while preserving order (first occurrence wins)"""
    seen = set()
    result = []
    for tag in hashtags:
        tag_lower = tag.lower()
        if tag_lower not in seen and tag not in BLOCKED_HASHTAGS:
            seen.add(tag_lower)
            result.append(tag)
    return result


def _validate_hashtags(hashtags: list) -> list:
    """Final validation and cleanup"""
    valid = []
    for tag in hashtags:
        # Must start with #
        if not tag.startswith('#'):
            tag = '#' + tag

        # Must have text after #
        if len(tag) < 3:
            continue

        # No spaces, special chars
        clean_tag = re.sub(r'[^#a-zA-Z0-9_]', '', tag)
        if len(clean_tag) >= 3:
            valid.append(clean_tag.lower())

    return valid


def _log_hashtag_breakdown(breakdown: dict):
    """Beautiful hashtag stats logging"""
    logger.info("┌─────────────────────────────────────────┐")
    logger.info("│      HASHTAG STRATEGY BREAKDOWN         │")
    logger.info("├─────────────────────────────────────────┤")
    for tier, count in breakdown.items():
        logger.info(f"│ {tier:25} : {count} tags")
    logger.info("└─────────────────────────────────────────┘")


# ============================================================
# MAIN AGENT FUNCTION
# ============================================================

def run(memory: AgentMemory) -> AgentMemory:
    """
    Generate SEO-optimized hashtags using Instagram algorithm best practices
    """
    logger.info("=" * 50)
    logger.info("=== HASHTAG AGENT STARTED ===")
    logger.info("=" * 50)

    all_hashtags = []
    breakdown = {}

    category = memory.category
    post_type = getattr(memory, 'post_type', 'image')

    logger.info(f"📂 Category: {category}")
    logger.info(f"📊 Post type: {post_type}")

    # ═══════════════════════════════════════════════
    # TIER 1: MASSIVE REACH (2 tags)
    # ═══════════════════════════════════════════════
    tier1 = random.sample(TIER_1_MASSIVE, OPTIMAL_MIX["tier_1_massive"])
    all_hashtags.extend(tier1)
    breakdown["Tier 1 (Massive)"] = len(tier1)

    # ═══════════════════════════════════════════════
    # TIER 2: HIGH REACH (4 tags)
    # ═══════════════════════════════════════════════
    tier2 = []
    tier2.extend(random.sample(TIER_2_HIGH["spiritual"], 2))

    if category == "motivational":
        tier2.extend(random.sample(TIER_2_HIGH["motivational"], 2))
    else:
        tier2.extend(random.sample(TIER_2_HIGH["cultural"], 2))

    all_hashtags.extend(tier2)
    breakdown["Tier 2 (High)"] = len(tier2)

    # ═══════════════════════════════════════════════
    # TIER 3: MEDIUM REACH (8 tags - SWEET SPOT)
    # ═══════════════════════════════════════════════
    tier3 = _get_category_hashtags(category, TIER_3_MEDIUM, 6)

    # Always add Hindi content hashtags
    tier3.extend(random.sample(TIER_3_MEDIUM["hindi_content"], 2))

    all_hashtags.extend(tier3)
    breakdown["Tier 3 (Medium)"] = len(tier3)

    # ═══════════════════════════════════════════════
    # TIER 4: NICHE (6 tags - RANKING BOOST)
    # ═══════════════════════════════════════════════
    tier4 = []

    # Category-specific niche
    if category == "krishna":
        tier4.extend(random.sample(TIER_4_NICHE["krishna_specific"], 3))
        tier4.extend(random.sample(TIER_4_NICHE["gita_wisdom"], 2))
    elif category == "shiva":
        tier4.extend(random.sample(TIER_4_NICHE["shiva_specific"], 3))
        tier4.extend(random.sample(TIER_4_NICHE["deep_spiritual"], 2))
    else:
        tier4.extend(random.sample(TIER_4_NICHE["deep_spiritual"], 3))
        tier4.extend(random.sample(TIER_4_NICHE["daily_bhakti"], 2))

    # Add 1 aesthetic
    tier4.append(random.choice(TIER_4_NICHE["aesthetic"]))

    all_hashtags.extend(tier4)
    breakdown["Tier 4 (Niche)"] = len(tier4)

    # ═══════════════════════════════════════════════
    # TIER 5: MICRO NICHE (3 tags - LOW COMPETITION)
    # ═══════════════════════════════════════════════
    tier5 = []
    tier5.extend(random.sample(TIER_5_MICRO["personal_brand"], 2))
    tier5.append(random.choice(TIER_5_MICRO["specific_practices"]))

    all_hashtags.extend(tier5)
    breakdown["Tier 5 (Micro)"] = len(tier5)

    # ═══════════════════════════════════════════════
    # FESTIVAL HASHTAGS (if applicable)
    # ═══════════════════════════════════════════════
    if memory.is_festival and memory.festival_name:
        festival_tags = _get_festival_hashtags(memory.festival_name)
        all_hashtags.extend(festival_tags)
        breakdown[f"Festival ({memory.festival_name})"] = len(festival_tags)
        logger.info(f"🎉 Festival hashtags added: {len(festival_tags)}")

    # ═══════════════════════════════════════════════
    # TIME + WEEKDAY HASHTAGS
    # ═══════════════════════════════════════════════
    time_tags = _get_time_hashtags()
    weekday_tags = _get_weekday_hashtags()

    all_hashtags.extend(time_tags)
    all_hashtags.extend(weekday_tags)

    breakdown["Time-based"] = len(time_tags)
    breakdown["Weekday-based"] = len(weekday_tags)

    # ═══════════════════════════════════════════════
    # KEYWORD-BASED (from research)
    # ═══════════════════════════════════════════════
    if memory.keywords:
        keyword_tags = _get_keyword_hashtags(memory.keywords)
        all_hashtags.extend(keyword_tags[:3])
        breakdown["Keywords"] = len(keyword_tags[:3])

        # ═══════════════════════════════════════════════
    # 🆕 V4: PLATFORM-SPECIFIC SEO HASHTAGS
    # ═══════════════════════════════════════════════
    if post_type == "reel":
        reel_tags = _get_reel_hashtags(OPTIMAL_MIX["reel_specific"])
        all_hashtags.extend(reel_tags)
        breakdown["Reel-Specific"] = len(reel_tags)
        logger.info(f"🎬 Reel hashtags added: {len(reel_tags)}")

    # V4: SEO boost hashtags (always add for all post types)
    seo_tags = [
        "#sanatanisoch", "#sanataniisoch",     # Brand
        "#bhakti", "#sanatan", "#hindu",         # Core
        "#dailypost", "#viralpost",              # Reach
    ]
    all_hashtags.extend(seo_tags)
    breakdown["SEO-Brand"] = len(seo_tags)

    # ═══════════════════════════════════════════════
    # CLEANUP + VALIDATION
    # ═══════════════════════════════════════════════
    logger.info(f"📊 Raw hashtags: {len(all_hashtags)}")

    # Remove duplicates (preserve order)
    all_hashtags = _remove_duplicates_preserve_order(all_hashtags)
    logger.info(f"🔧 After dedup: {len(all_hashtags)}")

    # Validate
    all_hashtags = _validate_hashtags(all_hashtags)
    logger.info(f"✅ After validation: {len(all_hashtags)}")

    # Instagram limit: max 30, sweet spot 20-25
    final_hashtags = all_hashtags[:25]

    # Shuffle for natural appearance (Instagram doesn't like patterns)
    random.shuffle(final_hashtags)

    # ═══════════════════════════════════════════════
    # SAVE TO MEMORY
    # ═══════════════════════════════════════════════
    memory.hashtags = " ".join(final_hashtags)

    # ═══════════════════════════════════════════════
    # LOGGING
    # ═══════════════════════════════════════════════
    _log_hashtag_breakdown(breakdown)

    logger.info("=" * 50)
    logger.info("✅ HASHTAGS GENERATED")
    logger.info("=" * 50)
    logger.info(f"📊 Total: {len(final_hashtags)} hashtags")
    logger.info(f"📝 Preview: {' '.join(final_hashtags[:5])}...")
    logger.info("=" * 50)

    logger.info("=== HASHTAG AGENT DONE ===\n")
    return memory


# ============================================================
# STANDALONE TESTING
# ============================================================

if __name__ == "__main__":
    """Test hashtag agent"""
    print("\n" + "=" * 60)
    print("HASHTAG AGENT - STANDALONE TEST")
    print("=" * 60 + "\n")

    test_cases = [
        {"category": "krishna", "keywords": ["vrindavan", "flute", "peacock"], "post_type": "image"},
        {"category": "shiva", "keywords": ["kailash", "trishul", "meditation"], "post_type": "image"},
        {"category": "krishna", "keywords": ["gita", "arjuna"], "post_type": "reel"},  # 🆕 Reel test
    ]

    for test in test_cases:
        print(f"\n{'=' * 60}")
        print(f"Category: {test['category']}")
        print(f"Post Type: {test['post_type']}")
        print("=" * 60)

        memory = AgentMemory()
        memory.category = test["category"]
        memory.keywords = test["keywords"]
        memory.is_festival = False
        memory.post_type = test["post_type"]

        result = run(memory)

        print(f"\n🏷️ HASHTAGS:\n{result.hashtags}\n")
        print(f"📊 Count: {len(result.hashtags.split())}")