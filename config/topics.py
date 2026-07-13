"""
Topic Pool + Festival Calendar + Smart Selection
Production-grade content database for Divine Auto Poster
"""
from datetime import datetime
import random


# ============================================================
# MAIN TOPIC POOL - 200+ Rich Topics
# Each topic is DETAILED for better AI generation
# ============================================================

TOPIC_POOL = {

    # ==================== KRISHNA (25 topics) ====================
    "krishna": [
        "Young Krishna playing bansuri flute in Vrindavan forest at sunrise with peacocks",
        "Radha Krishna divine love scene by Yamuna river with lotus flowers",
        "Baby Krishna eating butter mischievously with mother Yashoda watching",
        "Krishna teaching Bhagavad Gita to Arjuna on Kurukshetra battlefield chariot",
        "Krishna lifting Govardhan mountain with little finger to protect villagers from rain",
        "Krishna dancing Ras Leela with gopis in moonlit Vrindavan forest",
        "Krishna showing Vishwaroop cosmic form to Arjuna in divine light",
        "Krishna and Sudama meeting emotional reunion of childhood friends",
        "Krishna killing demon Kaliya on serpent's hood in Yamuna river",
        "Krishna as charioteer with Arjuna in golden chariot with horses",
        "Krishna stealing butter from clay pots hanging from ceiling",
        "Krishna playing with cows in green Vrindavan pastures at golden hour",
        "Baby Krishna showing universe inside his mouth to mother Yashoda",
        "Krishna with peacock feather crown and yellow silk dhoti divine portrait",
        "Krishna Radha swinging on flower jhula in monsoon Vrindavan",
        "Krishna as young prince in Dwarka palace with golden throne",
        "Krishna eating simple food at Vidura's humble home devotional scene",
        "Krishna's tiny feet with lotus mark divine baby feet close up",
        "Krishna playing Holi with Radha and gopis colorful festival scene",
        "Krishna meditating under Kadamba tree in peaceful forest",
        "Krishna's Sudarshan Chakra spinning with divine energy and light",
        "Krishna teaching devotion to Meera Bai in temple divine vision",
        "Krishna helping Draupadi with endless saree miracle scene",
        "Krishna with Balram brother divine bond in Vrindavan",
        "Krishna's murli flute glowing with divine light on lotus"
    ],

    # ==================== SHIVA (25 topics) ====================
    "shiva": [
        "Lord Shiva meditating in Himalayas with snow peaks and cosmic aura",
        "Shiva performing Tandava dance with cosmic fire ring destruction creation",
        "Shiva family Parvati Ganesha Kartikeya together on Mount Kailash",
        "Neelkanth Shiva drinking poison with blue throat during samudra manthan",
        "Ardhanarishvara half Shiva half Parvati divine union form",
        "Shiva with trishul damru and tiger skin sitting in meditation",
        "Ganga flowing from Shiva's matted hair Bhagirath scene",
        "Shiva opening third eye burning Kamadeva to ashes",
        "Nataraja Shiva cosmic dancer with ring of fire bronze statue style",
        "Shiva Parvati wedding divine marriage ceremony celestial scene",
        "Bholenath Shiva with devotees blessing Kanwariyas during Sawan",
        "Shiva as Bhairav fierce protective form with dog vahana",
        "Rudra Shiva angry form with cosmic destructive energy",
        "Shiva meditating under banyan tree as first yogi Adiyogi",
        "Shivling worship with milk abhishek and bel patra offering",
        "Shiva with Nandi bull sitting outside Kailash temple",
        "Panchmukhi Shiva five faces form of cosmic creator",
        "Shiva blessing Ravana with divine boon and Atmalinga",
        "Kal Bhairav Shiva form with skulls and destructive power",
        "Shiva as Pashupatinath lord of all creatures Nepal temple",
        "Somnath Jyotirlinga temple with ocean waves sacred atmosphere",
        "Kedarnath Shiva temple in snow-covered Himalayas divine scene",
        "12 Jyotirlingas of Shiva sacred pilgrimage divine collage",
        "Shiva as Dakshinamurthy teaching four sages under banyan tree",
        "Shiva burning three cities Tripurantaka form with divine bow"
    ],

    # ==================== HANUMAN (20 topics) ====================
    "hanuman": [
        "Hanuman flying across ocean carrying Sanjeevani mountain to Lakshman",
        "Hanuman tearing chest revealing Ram Sita in his heart devotion",
        "Bal Hanuman trying to eat sun thinking it's a golden fruit",
        "Hanuman burning Lanka with fire on tail dramatic scene",
        "Hanuman meeting Ram first time in forest devotional moment",
        "Panchmukhi Hanuman five faced form with divine weapons",
        "Hanuman lifting entire mountain with one hand powerful pose",
        "Hanuman crossing ocean to Lanka in flying form dramatic sky",
        "Hanuman ji sitting in meditation with Ram naam chanting",
        "Hanuman with gada mace guarding Ram Lakshman sleeping",
        "Bajrangbali Hanuman defeating demons in Ashok Vatika Lanka",
        "Hanuman teaching devotion to devotees in temple scene",
        "Hanuman finding Sita in Ashok Vatika under tree",
        "Sankat Mochan Hanuman removing obstacles devotee prayer",
        "Hanuman with Ram Lakshman Sita after Lanka victory return",
        "Hanuman Chalisa recitation with divine glowing effect",
        "Hanuman ji at ancient temple with saffron flag",
        "Hanuman meeting Bhima his brother in Mahabharata forest",
        "Hanuman as guru teaching wisdom to Arjuna Mahabharata",
        "Ram Bhakt Hanuman touching Ram feet ultimate devotion scene"
    ],

    # ==================== GANESHA (18 topics) ====================
    "ganesha": [
        "Ganesha with modak and mouse vahana sitting on lotus throne",
        "Ganesha writing Mahabharata with broken tusk as pen Vyasa dictating",
        "Baby Ganesha with mother Parvati loving family scene",
        "Ganesha getting elephant head from Shiva after incident",
        "Ganesha and Kartikeya racing around parents for modak",
        "Ashtavinayaka eight forms of Ganesha divine collage",
        "Ganesha Chaturthi visarjan devotees carrying idol to sea",
        "Vakratunda Mahakaya Ganesha divine cosmic form",
        "Ganesha with 21 modaks feast lord of new beginnings",
        "Siddhi Vinayak Ganesha temple Mumbai divine scene",
        "Ganesha dancing joyfully with musical instruments",
        "Ballaleshwar Ganesha temple ancient Maharashtra atmosphere",
        "Ekdanta Ganesha with single tusk divine portrait",
        "Ganesha blessing devotees removing obstacles vighnaharta",
        "Ganpati Bappa Morya festival celebration streets of Mumbai",
        "Ganesha meditating peacefully under banyan tree forest",
        "Golden Ganesha with jewels and silk in royal temple",
        "Ganesha ji with lotus modak and abhaya mudra blessing"
    ],

    # ==================== DEVI / DURGA (22 topics) ====================
    "durga": [
        "Goddess Durga on lion with ten arms holding divine weapons",
        "Maa Kali fierce form with garland of skulls dancing on Shiva",
        "Saraswati playing veena on white lotus with swan companion",
        "Lakshmi seated on pink lotus with gold coins and elephants",
        "Durga killing Mahishasura demon buffalo dramatic battle scene",
        "Navadurga nine forms of goddess collage divine mothers",
        "Vaishno Devi three pindis form in mountain cave temple",
        "Chamunda Devi fierce form protecting devotees",
        "Meenakshi goddess with parrot South Indian temple style",
        "Kamakhya Devi temple Assam divine feminine energy",
        "Santoshi Maa peaceful blessing form with gud chana",
        "Radha as divine goddess with Krishna eternal love",
        "Sita Mata pure and divine in Ashok Vatika Lanka",
        "Parvati doing tapasya to marry Shiva ancient forest",
        "Bhagwati Durga entering with lion during Navratri",
        "Kanya Puja worship of young girls Ashtami tradition",
        "Kali Puja Bengal traditional divine mother worship",
        "Ambe Maa in golden temple with devotees jyot",
        "Sherawali Mata with lion in Jammu mountain temple",
        "Annapurna Devi feeding Shiva divine food goddess",
        "Radha Rani in pink saree with Krishna divine consort",
        "Tulsi Mata sacred plant with Krishna worship scene"
    ],

    # ==================== RAM (18 topics) ====================
    "ram": [
        "Lord Ram with bow and arrow in forest exile with Sita Lakshman",
        "Ram coronation in Ayodhya golden throne royal ceremony",
        "Ram breaking Shiva Dhanush at Sita Swayamvar dramatic moment",
        "Ram crossing ocean to Lanka on stone bridge with vanar sena",
        "Ram killing Ravana ten headed demon king with divine arrow",
        "Ram Lakshman Sita in Panchvati forest peaceful cottage life",
        "Ram Sita wedding at Janakpur royal celebration divine union",
        "Ram meeting Hanuman first time in Kishkindha forest",
        "Ram returning to Ayodhya after 14 years Diwali celebration",
        "Ram giving darshan to Shabari eating her jhoothe ber",
        "Ram Darbar Ram Sita Lakshman Hanuman divine court scene",
        "Ram meditating on Rameshwaram before crossing to Lanka",
        "Ram teaching Ram Rajya ideal governance to Ayodhya people",
        "Ram Sita in Ashram peaceful spiritual life scene",
        "Ram killing Vali from behind tree Kishkindha episode",
        "Ram sending fire test agnipariksha for Sita return",
        "Bal Ram childhood scene playing in Ayodhya palace garden",
        "Ram Setu ancient bridge to Lanka stones with Ram naam"
    ],

    # ==================== SPIRITUAL NATURE (25 topics) ====================
    "spiritual_nature": [
        "Ganga aarti at Rishikesh with hundreds of diyas floating",
        "Old sadhu meditating in Himalayan cave with oil lamp",
        "Sacred lotus blooming in pond at sunrise divine symbol",
        "Ancient banyan tree with saffron flags spiritual atmosphere",
        "Peepal tree with om symbol and morning sun rays",
        "Cow grazing peacefully at ashram sacred gau mata",
        "Himalayan monastery with prayer flags fluttering in wind",
        "Sadhu bathing in Ganga at sunrise Varanasi ghat",
        "Kailash Mansarovar sacred lake with divine reflection",
        "Ancient rishi doing tapasya in deep forest meditation",
        "Sacred fire hawan yagna with sanskrit mantras",
        "Tulsi plant on temple courtyard with morning worship",
        "Om symbol carved in ancient rock with sun rising behind",
        "Divine light emanating from Himalayan peak sunrise scene",
        "Rudraksha mala with lotus and sandalwood spiritual items",
        "Sacred cave temple with natural shivling formation",
        "Yogic posture silhouette against sunrise mountains",
        "Ganga river flowing through mountains ancient wisdom",
        "Ashram at sunrise with sadhu doing morning prayers",
        "Sacred banyan grove with saints in deep meditation",
        "Divine peacock feather in sunlight symbolic beauty",
        "Ancient Sanskrit scriptures on wooden table with diya",
        "Sunset at Prayag confluence three sacred rivers meeting",
        "Sadhu with dhuni fire chillum in Himalayan cave",
        "Sacred lotus pond with rising sun temple in background"
    ],

    # ==================== TEMPLES (22 topics) ====================
    "temple": [
        "Kedarnath temple in snow-covered Himalayas divine atmosphere",
        "Kashi Vishwanath temple with Ganga ghats aarti scene",
        "Tirupati Balaji temple South Indian architecture divine",
        "Vaishno Devi cave temple mountain shrine devotees climbing",
        "Somnath temple with Arabian Sea waves ancient divine",
        "Meenakshi temple Madurai colorful Gopuram towers",
        "Golden Temple Amritsar with Amrit sarovar reflection",
        "Rameshwaram temple long corridors with pillars",
        "Jagannath Puri temple with sea beach devotional scene",
        "Ayodhya Ram Mandir grand new temple divine architecture",
        "Ancient rural temple with peepal tree evening aarti",
        "Konark Sun Temple stone chariot wheels architecture",
        "Khajuraho temple intricate carvings ancient art",
        "Badrinath temple Uttarakhand Himalayan divine setting",
        "Mahakaleshwar Ujjain Jyotirlinga bhasma aarti scene",
        "Amarnath cave temple ice shivling divine formation",
        "Dwarkadhish temple Gujarat coastal divine atmosphere",
        "Puri Jagannath rath yatra chariot festival divine",
        "Ranganathaswamy Srirangam grand South temple",
        "Kanchipuram thousand pillar temple ancient wisdom",
        "Modhera Sun temple Gujarat architectural marvel",
        "Small village temple with morning aarti bhakti scene"
    ],

    # ==================== MOTIVATIONAL (25 topics) ====================
    "motivational": [
        "Warrior standing on mountain peak at sunrise silhouette determination",
        "Single diya glowing in complete darkness hope symbol powerful",
        "Lotus blooming in muddy pond transformation and purity metaphor",
        "Eagle soaring high in Himalayan sky freedom and strength",
        "Person meditating on cliff edge at sunset peaceful contemplation",
        "Old wise sage with white beard looking at sunrise wisdom",
        "Hands folded in namaste with soft golden light gratitude",
        "Empty ancient path through misty Himalayan forest spiritual journey",
        "Warrior with sword facing rising sun ready for battle",
        "Small plant growing through concrete crack resilience symbol",
        "Sunrise over Himalayan peaks new beginning fresh start",
        "Silhouette of person on mountain top achievement success",
        "Diya lamp lighting many other diyas spreading light metaphor",
        "Bamboo growing straight and tall strength flexibility symbol",
        "Waves crashing against strong rock persistence metaphor",
        "River flowing to ocean journey of life spiritual meaning",
        "Butterfly emerging from cocoon transformation new self",
        "Boy climbing mountain with backpack young dreamer scene",
        "Tree with strong roots surviving storm resilience metaphor",
        "Candle burning through night dedication and sacrifice",
        "Runner at sunrise beach dedication morning motivation",
        "Book with rising sun knowledge is power spiritual wisdom",
        "Person planting seed hope and future growth metaphor",
        "Mountain climber reaching peak flag victory achievement",
        "Lonely tree in vast field standing tall alone strength"
    ],

    # ==================== FESTIVAL MOMENTS (15 topics) ====================
    "festival_moments": [
        "Diwali diyas glowing in traditional Indian home doorway",
        "Holi colorful powder celebration joy and love",
        "Navratri garba dance with women in colorful ghagra",
        "Ganesh Chaturthi visarjan procession with devotees",
        "Karva Chauth moon worship married women tradition",
        "Rakhi bhaiya bandhan brother sister love thread ceremony",
        "Janmashtami midnight Krishna birth celebration temple",
        "Guru Purnima devotees touching guru feet divine",
        "Basant Panchami Saraswati puja students blessing",
        "Chhath Puja devotees offering arghya to setting sun",
        "Maha Kumbh Mela millions of devotees at Ganga",
        "Mahashivratri night worship of Shiva devotees jagran",
        "Ram Navami temple decoration Ayodhya celebration",
        "Krishna Janmashtami dahi handi Mumbai celebration",
        "Onam Kerala boat race and Pookalam flower design"
    ],

    # ==================== DAILY WISDOM (15 topics) ====================
    "daily_wisdom": [
        "Morning sunrise with Om chanting spiritual awakening",
        "Book of Bhagavad Gita open with reading glasses wisdom",
        "Old man reading scriptures peaceful spiritual practice",
        "Cup of tea and Gita ancient wisdom morning ritual",
        "Sacred symbols om swastika trishul spiritual collage",
        "Handwritten shloka in Sanskrit devotional practice",
        "Beads mala prayer counting rudraksha spiritual",
        "Sadhak doing pranayama breathing exercise sunrise",
        "Yoga asana at sunrise beach spiritual practice",
        "Guru teaching disciples under tree ancient wisdom",
        "Meditation cushion with sacred symbols peace",
        "Journal with pen writing spiritual thoughts wisdom",
        "Family doing puja together traditional evening",
        "Grandmother teaching mantras to grandchild wisdom",
        "Sacred books stack with lamp knowledge tradition"
    ]
}


# ============================================================
# FESTIVAL CALENDAR - 50+ Festivals Throughout Year
# Format: (month, day): {festival, topic, category, mood}
# Note: Some festival dates change yearly (based on Hindu calendar)
# ============================================================

FESTIVAL_CALENDAR = {
    # JANUARY
    (1, 1):  {"festival": "New Year", "topic": "New year sunrise spiritual new beginnings blessings", "category": "motivational"},
    (1, 6):  {"festival": "Guru Gobind Singh Jayanti", "topic": "Guru Gobind Singh divine warrior saint", "category": "festival_moments"},
    (1, 14): {"festival": "Makar Sankranti", "topic": "Surya dev sunrise celebration with kites flying", "category": "festival_moments"},
    (1, 15): {"festival": "Pongal", "topic": "Pongal harvest festival South Indian celebration", "category": "festival_moments"},
    (1, 26): {"festival": "Republic Day", "topic": "Bharat mata patriotic spiritual tricolor", "category": "motivational"},

    # FEBRUARY
    (2, 5):  {"festival": "Basant Panchami", "topic": "Saraswati puja with veena yellow flowers", "category": "durga"},
    (2, 18): {"festival": "Maha Shivratri", "topic": "Lord Shiva night meditation cosmic worship", "category": "shiva"},
    (2, 26): {"festival": "Holi Dahan", "topic": "Holika Dahan bonfire spiritual purification", "category": "festival_moments"},

    # MARCH
    (3, 8):  {"festival": "Womens Day", "topic": "Divine feminine shakti goddess empowerment", "category": "durga"},
    (3, 25): {"festival": "Holi", "topic": "Krishna Radha playing Holi colorful festival", "category": "krishna"},
    (3, 30): {"festival": "Chaitra Navratri", "topic": "Nine forms of Durga Navratri worship", "category": "durga"},

    # APRIL
    (4, 6):  {"festival": "Ram Navami", "topic": "Lord Ram birth celebration Ayodhya divine", "category": "ram"},
    (4, 14): {"festival": "Baisakhi", "topic": "Baisakhi Punjabi harvest festival celebration", "category": "festival_moments"},
    (4, 23): {"festival": "Hanuman Jayanti", "topic": "Hanuman ji birth celebration devotion divine", "category": "hanuman"},

    # MAY
    (5, 12): {"festival": "Mothers Day", "topic": "Divine mother maa devotion love blessings", "category": "durga"},
    (5, 23): {"festival": "Buddha Purnima", "topic": "Lord Buddha meditation enlightenment wisdom", "category": "spiritual_nature"},

    # JUNE
    (6, 21): {"festival": "International Yoga Day", "topic": "Yoga meditation Adiyogi Shiva sunrise practice", "category": "shiva"},
    (6, 30): {"festival": "Jagannath Rath Yatra", "topic": "Jagannath Puri chariot festival Odisha", "category": "temple"},

    # JULY
    (7, 21): {"festival": "Guru Purnima", "topic": "Guru shishya tradition ancient wisdom", "category": "spiritual_nature"},
    (7, 30): {"festival": "Sawan Somvar", "topic": "Kanwariyas carrying Ganga jal for Shiva", "category": "shiva"},

    # AUGUST
    (8, 9):  {"festival": "Nag Panchami", "topic": "Snake worship Shiva Nag Devata tradition", "category": "shiva"},
    (8, 15): {"festival": "Independence Day", "topic": "Bharat mata patriotic spiritual freedom", "category": "motivational"},
    (8, 19): {"festival": "Raksha Bandhan", "topic": "Rakhi brother sister love thread ceremony", "category": "festival_moments"},
    (8, 26): {"festival": "Krishna Janmashtami", "topic": "Baby Krishna midnight birth Mathura divine", "category": "krishna"},

    # SEPTEMBER
    (9, 7):  {"festival": "Ganesh Chaturthi", "topic": "Ganpati Bappa Morya festival grand celebration", "category": "ganesha"},
    (9, 17): {"festival": "Ganesh Visarjan", "topic": "Ganesha visarjan procession emotional farewell", "category": "ganesha"},
    (9, 25): {"festival": "Pitru Paksha", "topic": "Ancestor worship shraddha divine tradition", "category": "spiritual_nature"},

    # OCTOBER
    (10, 2): {"festival": "Navratri Start", "topic": "Goddess Durga entering on lion Navratri begins", "category": "durga"},
    (10, 9): {"festival": "Durga Ashtami", "topic": "Kanya puja divine young girls worship", "category": "durga"},
    (10, 12):{"festival": "Dussehra", "topic": "Ram defeating Ravana divine victory over evil", "category": "ram"},
    (10, 20):{"festival": "Karva Chauth", "topic": "Moon worship married women love tradition", "category": "festival_moments"},

    # NOVEMBER
    (11, 1): {"festival": "Diwali", "topic": "Diya lamps glowing on Diwali night celebration", "category": "festival_moments"},
    (11, 2): {"festival": "Govardhan Puja", "topic": "Krishna lifting Govardhan mountain worship", "category": "krishna"},
    (11, 3): {"festival": "Bhai Dooj", "topic": "Brother sister tilak tradition love", "category": "festival_moments"},
    (11, 7): {"festival": "Chhath Puja", "topic": "Chhath devotees offering arghya to sun", "category": "festival_moments"},
    (11, 15):{"festival": "Kartik Purnima", "topic": "Ganga aarti Kashi ghat full moon divine", "category": "spiritual_nature"},
    (11, 24):{"festival": "Guru Nanak Jayanti", "topic": "Guru Nanak dev ji divine teachings", "category": "spiritual_nature"},

    # DECEMBER
    (12, 6): {"festival": "Gita Jayanti", "topic": "Krishna teaching Gita Arjuna divine wisdom", "category": "krishna"},
    (12, 25):{"festival": "Christmas", "topic": "Universal divine light peace and love", "category": "spiritual_nature"},
    (12, 31):{"festival": "Year End", "topic": "Sunset year end reflection gratitude divine", "category": "motivational"},
}


# ============================================================
# TIME-BASED TOPIC PREFERENCES
# Different topics for different times of day
# ============================================================

TIME_PREFERENCES = {
    "morning": {  # 5 AM - 11 AM
        "categories": ["krishna", "spiritual_nature", "daily_wisdom", "temple"],
        "mood": "peaceful, awakening, fresh"
    },
    "afternoon": {  # 11 AM - 4 PM
        "categories": ["motivational", "hanuman", "ram", "temple"],
        "mood": "energetic, powerful, active"
    },
    "evening": {  # 4 PM - 8 PM
        "categories": ["ganesha", "durga", "festival_moments", "temple"],
        "mood": "devotional, celebratory, warm"
    },
    "night": {  # 8 PM - 5 AM
        "categories": ["shiva", "spiritual_nature", "daily_wisdom"],
        "mood": "mystical, contemplative, deep"
    }
}


# ============================================================
# SEASONAL PREFERENCES
# ============================================================

SEASONAL_PREFERENCES = {
    "winter": {  # Dec, Jan, Feb
        "months": [12, 1, 2],
        "boost_categories": ["shiva", "temple", "spiritual_nature"],
        "themes": ["snow", "himalayas", "warmth", "diyas"]
    },
    "spring": {  # Mar, Apr, May
        "months": [3, 4, 5],
        "boost_categories": ["krishna", "durga", "ram"],
        "themes": ["flowers", "colors", "new life"]
    },
    "summer": {  # Jun, Jul, Aug
        "months": [6, 7, 8],
        "boost_categories": ["krishna", "shiva", "motivational"],
        "themes": ["sun", "sunrise", "vibrant"]
    },
    "monsoon": {  # Sep, Oct, Nov
        "months": [9, 10, 11],
        "boost_categories": ["ganesha", "durga", "festival_moments"],
        "themes": ["rain", "greenery", "festivals"]
    }
}


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def get_festival_today():
    """Check if today is a festival. Returns festival dict or None."""
    today = datetime.now()
    key = (today.month, today.day)
    return FESTIVAL_CALENDAR.get(key, None)


def get_upcoming_festivals(days_ahead: int = 7) -> list:
    """Get festivals in next N days"""
    from datetime import timedelta
    today = datetime.now()
    upcoming = []

    for i in range(days_ahead):
        check_date = today + timedelta(days=i)
        key = (check_date.month, check_date.day)
        if key in FESTIVAL_CALENDAR:
            festival = FESTIVAL_CALENDAR[key].copy()
            festival["date"] = check_date.strftime("%Y-%m-%d")
            festival["days_away"] = i
            upcoming.append(festival)

    return upcoming


def get_current_time_slot() -> str:
    """Get current time slot: morning/afternoon/evening/night"""
    hour = datetime.now().hour
    if 5 <= hour < 11:
        return "morning"
    elif 11 <= hour < 16:
        return "afternoon"
    elif 16 <= hour < 20:
        return "evening"
    else:
        return "night"


def get_current_season() -> str:
    """Get current season based on month"""
    month = datetime.now().month
    for season, data in SEASONAL_PREFERENCES.items():
        if month in data["months"]:
            return season
    return "spring"


def get_all_topics_flat() -> list:
    """Return flat list of all topics with category"""
    all_topics = []
    for category, topics in TOPIC_POOL.items():
        for topic in topics:
            all_topics.append({
                "topic": topic,
                "category": category
            })
    return all_topics


def get_time_appropriate_topics() -> list:
    """
    Smart selection based on current time.
    Morning gets peaceful topics, night gets mystical, etc.
    """
    time_slot = get_current_time_slot()
    preferred_categories = TIME_PREFERENCES[time_slot]["categories"]

    topics = []
    for category in preferred_categories:
        if category in TOPIC_POOL:
            for topic in TOPIC_POOL[category]:
                topics.append({
                    "topic": topic,
                    "category": category,
                    "time_slot": time_slot
                })

    return topics


def get_season_boosted_topics() -> list:
    """Get topics with seasonal preference boost"""
    season = get_current_season()
    boost_categories = SEASONAL_PREFERENCES[season]["boost_categories"]

    all_topics = get_all_topics_flat()
    boosted = []
    normal = []

    for topic in all_topics:
        if topic["category"] in boost_categories:
            boosted.extend([topic] * 3)  # 3x more likely
        else:
            normal.append(topic)

    return boosted + normal


def get_smart_topic(exclude_topics: list = None) -> dict:
    """
    SMART topic selection - combines all factors:
    1. Festival (highest priority)
    2. Time of day preference
    3. Seasonal preference
    4. Avoid recently used
    """
    if exclude_topics is None:
        exclude_topics = []

    # 1. Festival first
    festival = get_festival_today()
    if festival:
        return {
            "topic": festival["topic"],
            "category": festival.get("category", "festival"),
            "is_festival": True,
            "festival_name": festival["festival"],
            "selection_reason": "festival_today"
        }

    # 2. Get time + season boosted topics
    time_topics = get_time_appropriate_topics()
    season_topics = get_season_boosted_topics()

    # 3. Combine (time preference gets 2x weight)
    combined = time_topics * 2 + season_topics

    # 4. Filter out excluded
    available = [t for t in combined if t["topic"] not in exclude_topics]

    if not available:
        available = get_all_topics_flat()

    # 5. Random selection
    selected = random.choice(available)
    selected["is_festival"] = False
    selected["selection_reason"] = "time_season_based"

    return selected


def get_topics_by_category(category: str) -> list:
    """Get all topics from specific category"""
    return TOPIC_POOL.get(category, [])


def get_stats() -> dict:
    """Get pool statistics"""
    total_topics = sum(len(topics) for topics in TOPIC_POOL.values())
    return {
        "total_categories": len(TOPIC_POOL),
        "total_topics": total_topics,
        "total_festivals": len(FESTIVAL_CALENDAR),
        "categories": {cat: len(topics) for cat, topics in TOPIC_POOL.items()}
    }


# ============================================================
# TESTING
# ============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("DIVINE AUTO POSTER - TOPIC POOL STATS")
    print("=" * 60)

    stats = get_stats()
    print(f"\n📊 Total Categories: {stats['total_categories']}")
    print(f"📊 Total Topics: {stats['total_topics']}")
    print(f"📊 Total Festivals: {stats['total_festivals']}")

    print(f"\n📁 Topics per Category:")
    for cat, count in stats['categories'].items():
        print(f"   • {cat}: {count} topics")

    print(f"\n🕐 Current Time Slot: {get_current_time_slot()}")
    print(f"🌸 Current Season: {get_current_season()}")

    festival = get_festival_today()
    if festival:
        print(f"\n🎉 Today's Festival: {festival['festival']}")
    else:
        print(f"\n✨ No festival today")

    upcoming = get_upcoming_festivals(7)
    if upcoming:
        print(f"\n📅 Upcoming Festivals (next 7 days):")
        for f in upcoming:
            print(f"   • {f['date']}: {f['festival']} (in {f['days_away']} days)")

    print(f"\n🎯 Smart Topic Selection:")
    smart = get_smart_topic()
    print(f"   Topic: {smart['topic']}")
    print(f"   Category: {smart['category']}")
    print(f"   Reason: {smart['selection_reason']}")