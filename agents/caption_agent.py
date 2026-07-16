"""
Caption Agent - Intelligent Spiritual Caption Generator
Features:
- Image-context aware captions
- Multi-style variety with specific templates
- SEO + Engagement optimization
- Category-specific tone
- Strategy-driven (from planner)
- Rich fallback library (50+ captions)
- Emoji intelligence
- Length optimization

V2 UPDATE: Added reel_hook style + post_type awareness
"""
import random
import re
import google.generativeai as genai

from core.memory import AgentMemory
from config.settings import GEMINI_API_KEY, GEMINI_MODEL
from utils.humanizer import humanize_caption
from utils.logger import get_logger

genai.configure(api_key=GEMINI_API_KEY)
logger = get_logger("caption_agent")


# ============================================================
# CAPTION STYLE TEMPLATES
# Each style has: description, structure, example, best_for
# ============================================================

CAPTION_STYLES = {
    "short_powerful": {
        "description": "1-2 line ka punch statement",
        "length": "15-30 words",
        "structure": "Ek powerful line + emoji",
        "example": "Mahadev ke bhakt kabhi haar nahi maante 🕉️\nBas vishwas bana rahe.",
        "best_for": ["shiva", "hanuman", "motivational"],
        "engagement_type": "quick_impact"
    },
    "storytelling": {
        "description": "Chota sa emotional scene ya kahani",
        "length": "40-60 words",
        "structure": "Setup → Moment → Message",
        "example": "Ek shishya ne guru se pucha 'shanti kahan hai?'\nGuru muskuraye, bole - 'jab tu khudko dhundhna band karega'...\nAaj samajh aaya, sach me. 🙏",
        "best_for": ["krishna", "ram", "spiritual_nature", "daily_wisdom"],
        "engagement_type": "emotional_connection"
    },
    "question_engaging": {
        "description": "Thought + Question for comments",
        "length": "25-40 words",
        "structure": "Statement → Reflection → Question",
        "example": "Zindagi me sab kuch mil jaye, par sukoon na ho...\nToh kya faayda?\nBatao, aapke liye asli sukoon kya hai? 💭",
        "best_for": ["motivational", "daily_wisdom"],
        "engagement_type": "comments_driver"
    },
    "shayari_style": {
        "description": "Poetic 4-line shayari with divine touch",
        "length": "30-50 words",
        "structure": "4 poetic lines with flow",
        "example": "Duniya ki bheed me kho gaye hum,\nKhud se hi door ho gaye hum,\nJab mila Mahadev ka sahara,\nApne aap ko paa liye hum 🕉️",
        "best_for": ["shiva", "krishna", "ram"],
        "engagement_type": "saveable"
    },
    "personal_thought": {
        "description": "Diary-style personal reflection",
        "length": "35-55 words",
        "structure": "Kabhi kabhi lagta hai... → Realization → Sharing",
        "example": "Kabhi kabhi lagta hai...\nBhagwan ko mandir me dhundhte hain hum,\nAur wo toh humare andar hi hai.\nBas ankhein band karke mehsoos karo. ✨",
        "best_for": ["spiritual_nature", "daily_wisdom", "motivational"],
        "engagement_type": "relatable"
    },
    "conversational": {
        "description": "Dost se baat karne wala friendly tone",
        "length": "30-45 words",
        "structure": "Dost-jaisa hook → Advice → Positive close",
        "example": "Suno yaar...\nTension lene se problems nahi jaati.\nBas Mahadev pe chhod ke dekho ek baar.\nSab handle ho jaata hai. 🕉️✨",
        "best_for": ["motivational", "shiva", "hanuman"],
        "engagement_type": "relatable"
    },
    "gratitude_style": {
        "description": "Thankfulness aur small blessings",
        "length": "30-45 words",
        "structure": "Small realization → Gratitude → Blessing",
        "example": "Aaj subah bas itna socha -\nSaans le raha hun, chal sakta hun, apno ke saath hun...\nAur kya chahiye?\nShukriya prabhu 🙏🌸",
        "best_for": ["daily_wisdom", "spiritual_nature", "festival_moments"],
        "engagement_type": "wholesome"
    },
    "festival_special": {
        "description": "Festival ke liye special wishes",
        "length": "35-55 words",
        "structure": "Wishes → Meaning → Blessing",
        "example": "Diwali ka asli matlab -\nAndhere se ujaale ki taraf.\nDil me ek diya jalao,\nSab kuch roshan ho jayega ✨\nHappy Diwali 🪔",
        "best_for": ["festival", "festival_moments"],
        "engagement_type": "shareable"
    },
    "reminder_style": {
        "description": "Motivational reminder/wake-up call",
        "length": "20-35 words",
        "structure": "Yaad rakhna... → Powerful message",
        "example": "Yaad rakhna...\nJo tumhe tod raha hai aaj,\nWahi tumhe banayega kal.\nBas himmat mat harna 💪🕉️",
        "best_for": ["motivational", "hanuman"],
        "engagement_type": "shareable"
    },
    "devotional_deep": {
        "description": "Deep devotional connection",
        "length": "40-60 words",
        "structure": "Devotion → Divine feeling → Surrender",
        "example": "Kanha ki basuri ki dhun me kuch aisa hai...\nJo dil ko chhoo jaati hai,\nAankhein khud band ho jati hain,\nAur bas ek hi shabd nikalta hai...\nRadhe Radhe 🌸🙏",
        "best_for": ["krishna", "shiva", "ram", "durga"],
        "engagement_type": "emotional"
    },
    # 🆕 REEL-SPECIFIC STYLE (V2)
    "reel_hook": {
        "description": "Reel के लिए hook + engaging body + CTA",
        "length": "80-120 words",
        "structure": "Hook question → Story teaser → Save/Share CTA",
        "example": "क्या आप जानते हैं...\n\nजब भगवान श्री कृष्ण ने अर्जुन से कहा था 'कर्म कर, फल की चिंता मत कर'... इस एक वाक्य में पूरा जीवन का सत्य छुपा है।\n\nपूरी कहानी video में देखिए 🎬\n\n💾 Save करें | 🔄 Share करें\n🙏 Follow @sanatanii_soch",
        "best_for": ["reel"],
        "engagement_type": "video_hook"
    }
}


# ============================================================
# CATEGORY-SPECIFIC ELEMENTS
# ============================================================

DEITY_SPECIFIC = {
    "krishna": {
        "names": ["Kanha", "Krishna", "Govind", "Murali Manohar", "Nand Lala", "Madhav"],
        "phrases": ["Radhe Radhe", "Jai Shri Krishna", "Hare Krishna"],
        "emotions": ["divine love", "playful joy", "peaceful bhakti"],
        "closings": ["🌸", "🎵", "🦚", "💙", "🌺"]
    },
    "shiva": {
        "names": ["Mahadev", "Shiva", "Bholenath", "Shankar", "Mahakal", "Neelkanth"],
        "phrases": ["Har Har Mahadev", "Om Namah Shivaya", "Bum Bum Bhole"],
        "emotions": ["powerful bhakti", "mystical peace", "cosmic connection"],
        "closings": ["🕉️", "🔱", "🌙", "⚡", "🚩"]
    },
    "hanuman": {
        "names": ["Hanuman ji", "Bajrangbali", "Sankat Mochan", "Pawan Putra", "Maruti"],
        "phrases": ["Jai Bajrangbali", "Jai Hanuman", "Ram Ram"],
        "emotions": ["courage", "strength", "unwavering devotion"],
        "closings": ["🚩", "💪", "🙏", "🔥", "🧡"]
    },
    "ganesha": {
        "names": ["Ganpati Bappa", "Ganesha", "Gajanan", "Vighnaharta", "Ekdanta"],
        "phrases": ["Ganpati Bappa Morya", "Jai Ganesh", "Vakratunda Mahakaya"],
        "emotions": ["wisdom", "auspicious beginning", "obstacle removal"],
        "closings": ["🐘", "🙏", "🌺", "🍯", "✨"]
    },
    "durga": {
        "names": ["Maa Durga", "Sherawali", "Ambe Maa", "Bhavani", "Jagdamba"],
        "phrases": ["Jai Mata Di", "Jai Ambe Maa", "Jai Sherawali"],
        "emotions": ["divine feminine power", "protection", "motherly love"],
        "closings": ["🌺", "🚩", "🔴", "🙏", "✨"]
    },
    "ram": {
        "names": ["Ram", "Raghav", "Shri Ram", "Ramchandra", "Maryada Purushottam"],
        "phrases": ["Jai Shri Ram", "Siya Ram", "Ram Ram"],
        "emotions": ["dharma", "righteousness", "noble courage"],
        "closings": ["🚩", "🏹", "🙏", "🌼", "☀️"]
    },
    "motivational": {
        "names": [],
        "phrases": ["Jai Hind", "Har Har Mahadev", "Jai Shri Krishna"],
        "emotions": ["strength", "hope", "determination"],
        "closings": ["💪", "🔥", "⚡", "🌅", "🚀"]
    },
    "spiritual_nature": {
        "names": [],
        "phrases": ["Om Shanti", "Namaste", "Har Har Mahadev"],
        "emotions": ["peace", "calm", "connection with nature"],
        "closings": ["🌸", "🕉️", "🙏", "☘️", "🌿"]
    }
}


# ============================================================
# RICH FALLBACK LIBRARY (10 per category)
# ============================================================

FALLBACK_CAPTIONS = {
    "krishna": [
        "Kanha ki basuri ki dhun me kuch aisa jaadu hai...\nJo dil ki har chinta bha deta hai.\nBas ankhein band karo aur unhe yaad karo.\n\nRadhe Radhe 🌸🎵",
        "Krishna kehte hain -\n'Jo hua accha hua, jo ho raha hai accha ho raha hai.'\nBas vishwas rakho, sab theek hoga.\n\nJai Shri Krishna 💙",
        "Vrindavan ki galiyon me abhi bhi Krishna ki khushbu hai...\nBas mehsoos karne wala dil chahiye.\n\nHare Krishna 🦚🌸",
        "Radha bina Krishna adhoore hain,\nBhakti bina jeevan adhoora hai.\nDono ek doosre ke poorak hain.\n\nRadhe Radhe 🌺",
        "Kanha ne Gita me kaha -\n'Karm kar, phal ki chinta mat kar.'\nItni simple baat, samajhne me pura jeevan lag jata hai.\n\nJai Shri Krishna 🙏"
    ],
    "shiva": [
        "Mahadev ke bhakt kabhi akele nahi hote 🕉️\nJab bhi dil ghabrae, bas ek baar 'Om Namah Shivaya' bol do.\nSab theek ho jata hai.\n\nHar Har Mahadev 🙏",
        "Bholenath sabki sunte hain,\nBas shraddha honi chahiye.\nDikhawa nahi, dil se pukaro.\n\nBum Bum Bhole 🚩⚡",
        "Kailash pe baithe Mahadev,\nHar bhakt ki pukar sunte hain.\nBas ek baar sacche dil se yaad karo.\n\nHar Har Mahadev 🕉️🌙",
        "Shiva matlab -\nJo hai wahi shanti hai.\nJo nahi hai uska gum mat karo.\n\nOm Namah Shivaya 🔱",
        "Mahakal ke charno me jhukne wala,\nDuniya me kabhi jhukta nahi.\n\nJai Mahakal 🕉️🔥"
    ],
    "hanuman": [
        "Bajrangbali ka naam lete hi,\nSare sankat door ho jate hain.\nBas vishwas ki kami nahi honi chahiye.\n\nJai Hanuman 🚩💪",
        "Hanuman ji sikhaate hain -\nSewa hi sabse badi bhakti hai.\nApne Ram ko dil me basao,\nSab kuch mil jayega.\n\nJai Bajrangbali 🙏",
        "Sankat me jab koi na dikhe,\nBas 'Sankat Mochan' pukar lo.\nBajrangbali zaroor aayenge.\n\nJai Hanuman 🚩🔥",
        "Hanuman Chalisa ki ek line me jitni shakti hai,\nWo poori duniya ki taakat me nahi.\n\nJai Bajrangbali 💪🙏",
        "Ram ka naam jinke roam roam me,\nUnhi ka naam Hanuman.\nBhakti aisi honi chahiye.\n\nJai Shri Ram 🚩"
    ],
    "ganesha": [
        "Ganpati Bappa Morya 🙏\nVighnaharta har sankat door karte hain.\nUnke charno me sab kuch samarpit kar do.\n\nMangal Murti Morya 🌺",
        "Bappa ke aane se ghar me,\nSukh, shanti, aur samriddhi aati hai.\nBas dil se bulao.\n\nGanpati Bappa Morya 🐘",
        "Ganesha ji ka naam lete hi,\nKoi bhi kaam shubh ho jata hai.\nIsliye har kaam se pehle unhe yaad karo.\n\nJai Ganesh 🙏✨",
        "Modak Bappa ko bahut priya hai,\nPar unhe sabse priya hai -\nSacche dil ki bhakti.\n\nGanpati Bappa Morya 🌺",
        "Ekdanta Vakratunda Gajanan,\nSab par kripa karo Bhagwan.\n\nJai Shri Ganesh 🐘🙏"
    ],
    "durga": [
        "Maa Durga apne bhakton ki har mushkil me saath deti hain.\nBas sacche dil se pukaro.\n\nJai Mata Di 🌺🚩",
        "Sherawali Maa ka aashirwaad hai,\nToh koi bhi taakat rok nahi sakti.\n\nJai Ambe Maa 🔴🙏",
        "Navratri ka har din,\nMaa ke ek roop ki mahima.\nBhakti me kami nahi honi chahiye.\n\nJai Mata Di 🌺",
        "Maa Durga stree shakti ka pratik hain,\nUnki bhakti karo, khud ko shakti do.\n\nJai Ambe 🚩",
        "Jab jab bhakton par sankat aaya,\nMaa ne apni god me utha liya.\nBas vishwas rakho.\n\nJai Mata Di 🙏"
    ],
    "ram": [
        "Jai Shri Ram 🚩\nRam naam se badi koi shakti nahi.\nJab bhi mushkil aaye, sirf 'Ram Ram' bolo.\n\nSiya Ram 🙏",
        "Ram sirf ek naam nahi,\nEk jeevan jeene ka tareeka hain.\nSatya, dharma, aur karm.\n\nJai Shri Ram 🏹",
        "Jinke dil me Ram basa ho,\nUn par sankat kabhi nahi aata.\n\nSiya Ram 🚩🙏",
        "Ram naam ki mahima ansankh hai,\nBas ek baar sacche dil se bolo.\nSab kuch badal jayega.\n\nJai Shri Ram 🌼",
        "Ram Rajya ka matlab hai -\nJahan dharm ka raj ho.\nHum sabhi mil kar wo Ram Rajya bana sakte hain.\n\nJai Shri Ram 🚩"
    ],
    "motivational": [
        "Zindagi me mushkil aati hai,\nToh yaad rakho -\nHeere ko bhi tarashne ke liye,\nPehle mushkil se guzarna padta hai.\n\n💪🔥",
        "Jo aaj tumhe tod raha hai,\nWahi kal tumhe banayega.\nBas himmat mat harna.\n\n🕉️💪",
        "Har subah ek nayi shuruwat hai,\nPurani baaton ko chhodo,\nAage badho aur jeeto.\n\n🌅✨",
        "Success ka koi shortcut nahi hota,\nBas mehnat ka lamba raasta hota hai.\nChalte raho.\n\n🚀🔥",
        "Vishwas karo apne aap par,\nKyunki agar tum khud pe nahi karoge,\nToh koi aur bhi nahi karega.\n\n💪⚡"
    ],
    "spiritual_nature": [
        "Kabhi kabhi shanti mandir me nahi,\nQuiet nature me milti hai.\nEk ped ke neeche baitho,\nSab kuch samajh aa jayega. 🌿",
        "Sunrise dekhna sirf ek pal nahi,\nEk saadhna hai.\nRoz karo, jeevan badal jayega.\n\n🌅🙏",
        "Prakriti sabse badi guru hai.\nWo bina bole sab sikha deti hai,\nBas dhyan se dekhna hai.\n\n🌿☘️",
        "Ganga ke kinare baithkar,\nApni pareshaniyan wahin chhod do.\nWo behke chali jaayengi.\n\n🌊🕉️",
        "Om ki dhwani me,\nBrahmand ka sara sangeet hai.\nBas ek baar mehsoos karo.\n\n🕉️✨"
    ],
    "daily_wisdom": [
        "Aaj ka sabse bada gyan -\nJo hai, uske liye shukriya karo.\nJo nahi hai, uske peeche mat bhaago.\n\n🙏✨",
        "Buzurgo ne kaha hai -\nSubah jaldi utho, sooryodaya dekho,\nDin achha hi guzarega.\n\n🌅",
        "Gita ka saar bas itna hai -\nKarm karo, phal chhodo,\nBhagwan pe vishwas rakho.\n\n📖🙏",
        "Sabse badi ameeri hai -\nContent hona jo hai usme.\nSabse badi garibi hai -\nHamesha aur chahna.\n\n💭🙏",
        "Sacchi khushi cheezo me nahi,\nRishton me milti hai.\nApno ke saath samay bitao.\n\n❤️✨"
    ],
    "festival_moments": [
        "Har festival humein sikhata hai -\nParivaar ke saath rehna,\nPyar baantna, aur khushi phailana.\n\n🌺🪔",
        "Tyohar ka matlab sirf mithai nahi,\nApno ke saath yaadein banana hai.\n\n🎉❤️",
        "Har tyohar ke peeche,\nEk deep spiritual message hota hai.\nUse samjho aur jio.\n\n🕉️🌺",
        "Rangoli, diye, aur muskurahat,\nYahi toh Bharat ki asli pehchaan hai.\n\n🪔🇮🇳",
        "Tyohar aate jaate rehte hain,\nPar unki khushi hamesha yaadon me rehti hai.\n\n✨🌺"
    ],
    "festival": [
        "Aaj ka din shubh hai,\nDil se prarthana karo,\nBhagwan aapki har manokamna poori karenge.\n\n🙏🌺",
        "Har tyohar ek naya sandesh laata hai.\nUse dil se apnao aur jio.\n\n✨🪔",
        "Festival ke saath aata hai -\nPyar, milap, aur bhakti.\nTeeno ki apni mahima hai.\n\n🌺❤️",
        "Aaj ka din bahut shubh hai,\nApne dil me bhakti ka diya jalao.\n\n🪔🙏",
        "Har festival humein yaad dilata hai -\nHum kaun hain, hamari sanskriti kya hai.\n\n🕉️🇮🇳"
    ]
}


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def _select_style_for_category(category: str, strategy: dict = None, post_type: str = "image") -> str:
    """Smart style selection based on category, strategy, and post_type"""

    # 🆕 Reel post → always use reel_hook style
    if post_type == "reel":
        return "reel_hook"

    # Festival day = festival_special style
    if strategy and strategy.get("content_angle") == "festival_special":
        return "festival_special"

    # Get styles best suited for this category
    suitable_styles = [
        style_name for style_name, style_data in CAPTION_STYLES.items()
        if category in style_data.get("best_for", [])
    ]

    if suitable_styles:
        selected = random.choice(suitable_styles)
        logger.info(f"🎨 Style matched for category: {selected}")
        return selected

    # Fallback to random popular style
    return random.choice(["storytelling", "conversational", "personal_thought"])


def _get_deity_context(category: str) -> dict:
    """Get category-specific deity information"""
    return DEITY_SPECIFIC.get(category, DEITY_SPECIFIC.get("spiritual_nature", {}))


def _build_smart_prompt(memory: AgentMemory, style_name: str) -> str:
    """
    Build intelligent prompt for Gemini
    Uses ALL available context: image, mood, category, strategy, deity
    """
    style = CAPTION_STYLES[style_name]
    deity = _get_deity_context(memory.category)

    # Get strategy from memory (planner sets this)
    strategy = memory.analytics_data.get("strategy", {})
    content_angle = strategy.get("content_angle", "general")
    weekday = strategy.get("weekday", "")

    # Build deity-specific hints
    deity_hints = ""
    if deity.get("names"):
        deity_hints = f"""
Deity references you can use:
- Names: {', '.join(deity['names'])}
- Phrases: {', '.join(deity['phrases'])}
- Emotional tone: {', '.join(deity['emotions'])}"""

    # Festival context
    festival_context = ""
    if memory.is_festival:
        festival_context = f"\n🎉 SPECIAL: Aaj {memory.festival_name} hai! Festival ke wishes shamil karo."

    # Image context (agar prompt available hai)
    image_context = ""
    if memory.image_prompt:
        image_context = f"\n\n📸 Image ka visual: {memory.image_prompt[:200]}"

    # Weekday context
    weekday_context = ""
    if weekday and weekday in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]:
        weekday_context = f"\n📅 Aaj {weekday} hai."

        # 🆕 V4: Platform-specific SEO context
    reel_context = ""
    if memory.post_type == "reel":
        reel_context = """

🎬 REEL CAPTION RULES:
- First line = HOOK (viewer ruke)
- "क्या आपको पता है..." ya "ये बात 99% लोग नहीं जानते..."
- Body = 2-3 emotional lines about video content
- End = STRONG CTA:
  "❤️ अगर आप भी [deity] भक्त हैं तो Like करो"
  "💬 Comment में 🙏 लिखो"
  "🔄 अपनी माँ को भेजो ये video"
  "💾 बाद में देखने के लिए Save करो"
- Last line: "Follow @sanatanii_soch 🙏"
"""
    elif memory.post_type == "carousel":
        reel_context = """

🎠 CAROUSEL CAPTION RULES:
- First line = curiosity hook
- "Swipe करो 👉 पूरी कहानी देखो"
- Body = carousel ka summary
- CTA = "Save करो बाद में पढ़ने के लिए 💾"
"""
    else:
        reel_context = """

📸 IMAGE CAPTION RULES:
- First line = powerful statement about image
- Body = 2-3 lines emotional/devotional
- CTA = "❤️ Double tap अगर agree करते हो"
- "Follow @sanatanii_soch for daily भक्ति content 🙏"
"""

    prompt = f"""Tu ek real Instagram spiritual content creator hai jo Hindi/Hinglish me dil-chhoo captions likhta hai.

═══════════════════════════════════
📌 TOPIC: {memory.topic}
📂 CATEGORY: {memory.category}
🎭 MOOD: {memory.mood}
✨ VISUAL ELEMENTS: {', '.join(memory.visual_elements[:5]) if memory.visual_elements else 'N/A'}
🎨 COLORS: {', '.join(memory.colors[:3]) if memory.colors else 'N/A'}
{festival_context}
{weekday_context}
{image_context}
{reel_context}
═══════════════════════════════════

🎯 CAPTION STYLE: {style_name}
📝 STYLE DESCRIPTION: {style['description']}
📏 LENGTH: {style['length']}
🏗️ STRUCTURE: {style['structure']}

Example of this style:
{style['example']}
{deity_hints}

═══════════════════════════════════
STRICT RULES:
═══════════════════════════════════

1. ✅ Hindi + Hinglish mix (Devanagari script)
2. ✅ Length: {style['length']}
3. ✅ Structure follow karo: {style['structure']}
4. ✅ Topic aur image se DIRECTLY relate ho
5. ✅ Deity ka naam use karo (agar applicable)
6. ✅ Emotion aur bhakti ho, preachy nahi
7. ✅ 2-3 emojis max, natural placement
8. ✅ Line breaks natural rakho
9. ✅ Real insaan jaisa likho, AI jaisa NAHI
10. ✅ Har line meaningful ho, filler nahi

❌ DO NOT:
- "Here is the caption" jaise phrases
- Excessive emojis (5+ galat hai)
- Hashtags (they come separately)
- Generic wisdom jo kisi bhi topic pe fit ho
- English-only sentences
- Explanation ya AI phrases

═══════════════════════════════════
🎯 IMPORTANT: Caption topic aur image ko match karna chahiye!
Agar topic Krishna hai, toh Krishna ki baat karo.
Agar Shiva hai, toh Shiva ki.
Generic mat likhna!
═══════════════════════════════════

Ab caption likho (sirf caption, koi extra text nahi):"""

    return prompt


def _extract_response_text(response) -> str:
    """Safely extract text from Gemini response"""
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


def _clean_caption(caption: str) -> str:
    """
    Remove AI artifacts and clean caption.

    V3 FIXES:
    - Remove instruction leak text (Word Count Check, Structure Check, etc.)
    - Remove meta-analysis lines
    - Remove markdown headers
    - Remove position markers like (1), (32), (36
    - Remove numbered list prefixes 1) 2) etc.
    - Remove word count annotations
    - Better prefix removal
    """

    prefixes_to_remove = [
        "here is your caption", "here is the caption", "here's the caption",
        "here is your", "here's your", "caption:", "here's a", "here is a",
        "यहाँ है", "यहाँ", "नीचे", "sure!", "sure,", "of course",
        "**caption:**", "**caption**",
        "here is", "certainly", "definitely",
        "word count:", "words:", "total words:", "character count:"
    ]

    caption_lower = caption.lower()
    for prefix in prefixes_to_remove:
        if caption_lower.startswith(prefix):
            for sep in [':', '\n']:
                if sep in caption:
                    caption = caption.split(sep, 1)[1].strip()
                    break
            break

    # Remove wrapping quotes
    caption = caption.strip('"\'`')

    # Remove markdown bold/italic
    caption = re.sub(r'\*\*(.*?)\*\*', r'\1', caption)
    caption = re.sub(r'\*(.*?)\*', r'\1', caption)

    # Remove markdown code blocks
    caption = re.sub(r'```[\w]*\n?', '', caption)
    caption = caption.replace('```', '')

    # 🆕 V3: Remove AI meta-analysis lines (bahut common leak)
    # Removes lines like:
    #   "Word Count Check (Hindi words):"
    #   "Structure Check:"
    #   "Length Analysis:"
    #   "Emoji Count:"
    #   "Validation:"
    meta_patterns = [
        r'(?im)^.*word\s*count\s*check.*$',
        r'(?im)^.*structure\s*check.*$',
        r'(?im)^.*length\s*analysis.*$',
        r'(?im)^.*emoji\s*count.*$',
        r'(?im)^.*validation.*$',
        r'(?im)^.*character\s*count.*$',
        r'(?im)^.*hashtag\s*count.*$',
        r'(?im)^.*analysis.*:.*$',
        r'(?im)^\s*note:.*$',
        r'(?im)^\s*explanation:.*$',
        r'(?im)^\s*breakdown:.*$',
        r'(?im)^\s*[-•]\s*length:.*$',
        r'(?im)^\s*[-•]\s*words:.*$',
        r'(?im)^\s*[-•]\s*emojis:.*$',
    ]
    for pattern in meta_patterns:
        caption = re.sub(pattern, '', caption)

    # 🆕 V3: Remove markdown headers (###, ##, #)
    caption = re.sub(r'(?m)^#{1,6}\s+.*$', '', caption)

    # 🆕 V3: Remove separator lines (---, ===, ***)
    caption = re.sub(r'(?m)^\s*[-=*_]{3,}\s*$', '', caption)

    # 🆕 V2.1: Remove position markers like (1), (32), (36
    caption = re.sub(r'\(\d+\)', '', caption)        # (1), (32), (100)
    caption = re.sub(r'\s\(\d+\s', ' ', caption)     # ' (32 ' → ' '
    caption = re.sub(r'\s\(\d+$', '', caption)       # trailing '(36'
    caption = re.sub(r'\(\d+', '', caption)          # unclosed '(36'

    # 🆕 V2.1: Remove numbered list markers
    caption = re.sub(r'^\s*\d+[\.\):]\s*', '', caption)   # At start: "1) text"
    caption = re.sub(r'\n\s*\d+[\.\):]\s*', '\n', caption)  # After newline

    # 🆕 V2.1: Remove word count annotations
    caption = re.sub(r'\[.*?word.*?\]', '', caption, flags=re.IGNORECASE)
    caption = re.sub(r'\(word count.*?\)', '', caption, flags=re.IGNORECASE)
    caption = re.sub(r'\[\d+\s*chars?\]', '', caption, flags=re.IGNORECASE)

    # 🆕 V2.1: Remove meta annotations
    caption = re.sub(r'\[.*?caption.*?\]', '', caption, flags=re.IGNORECASE)
    caption = re.sub(r'\(.*?instagram.*?\)', '', caption, flags=re.IGNORECASE)

    # 🆕 V2.1: Remove hashtags at end (they come separately)
    caption = re.sub(r'\n+\s*(#\w+\s*)+$', '', caption)

    # Remove excessive newlines
    caption = re.sub(r'\n{3,}', '\n\n', caption)

    # Remove extra spaces
    caption = re.sub(r' +', ' ', caption)

    # Trim per line + remove empty lines that resulted from meta removal
    lines = caption.split('\n')
    lines = [line.strip() for line in lines]
    # Remove empty lines that appear at start
    while lines and not lines[0]:
        lines.pop(0)
    # Remove empty lines that appear at end
    while lines and not lines[-1]:
        lines.pop()
    caption = '\n'.join(lines)

    return caption.strip()

def _count_emojis(text: str) -> int:
    """Count emojis in text"""
    emoji_pattern = re.compile(
        "["
        "\U0001F600-\U0001F64F"
        "\U0001F300-\U0001F5FF"
        "\U0001F680-\U0001F6FF"
        "\U0001F1E0-\U0001F1FF"
        "\U0001F900-\U0001F9FF"
        "\U00002600-\U000027BF"
        "\U0001F300-\U0001F5FF"
        "]+",
        flags=re.UNICODE
    )
    return len(emoji_pattern.findall(text))


def _validate_caption(caption: str, category: str) -> tuple:
    """
    Validate caption quality
    Returns: (is_valid, reason)
    """
    # Length check
    if len(caption) < 30:
        return False, f"Too short: {len(caption)} chars"

    if len(caption) > 800:
        return False, f"Too long: {len(caption)} chars"

    # Emoji check
    emoji_count = _count_emojis(caption)
    if emoji_count > 6:
        return False, f"Too many emojis: {emoji_count}"

    # AI phrase check
    ai_phrases = ["as an ai", "language model", "i cannot", "i am unable"]
    if any(phrase in caption.lower() for phrase in ai_phrases):
        return False, "Contains AI phrases"

    # Deity relevance check (soft check)
    if category in ["krishna", "shiva", "hanuman", "ganesha", "ram", "durga"]:
        deity = _get_deity_context(category)
        deity_words = deity.get("names", []) + deity.get("phrases", [])

        if deity_words:
            has_deity_ref = any(
                word.lower() in caption.lower()
                for word in deity_words
            )
            if not has_deity_ref:
                logger.warning(f"⚠️ Caption may not mention {category} directly")
                # Don't fail, just warn

    return True, "Valid"


def _get_fallback_caption(category: str) -> str:
    """Get category-specific fallback caption"""
    # Try exact category match
    if category in FALLBACK_CAPTIONS:
        return random.choice(FALLBACK_CAPTIONS[category])

    # Fallback to motivational
    return random.choice(FALLBACK_CAPTIONS["motivational"])


# ============================================================
# MAIN AGENT FUNCTION
# ============================================================

def run(memory: AgentMemory) -> AgentMemory:
    """
    Generate intelligent spiritual caption
    with full context awareness
    """
    logger.info("=" * 50)
    logger.info("=== CAPTION AGENT STARTED ===")
    logger.info("=" * 50)

    # ========== STEP 1: SELECT STYLE ==========
    strategy = memory.analytics_data.get("strategy", {})
    style_name = _select_style_for_category(
        memory.category,
        strategy,
        post_type=memory.post_type  # 🆕 Pass post_type for reel detection
    )

    style_info = CAPTION_STYLES[style_name]
    logger.info(f"🎨 Style: {style_name}")
    logger.info(f"📏 Target length: {style_info['length']}")
    logger.info(f"🎯 Engagement type: {style_info['engagement_type']}")
    logger.info(f"📊 Post type: {memory.post_type}")

    # ========== STEP 2: BUILD SMART PROMPT ==========
    prompt = _build_smart_prompt(memory, style_name)
    logger.info(f"📝 Prompt built ({len(prompt)} chars)")

    # ========== STEP 3: GENERATE WITH RETRIES ==========
    max_attempts = 3
    caption = None

    for attempt in range(1, max_attempts + 1):
        try:
            logger.info(f"🤖 Gemini attempt {attempt}/{max_attempts}")

            model = genai.GenerativeModel(GEMINI_MODEL)

            response = model.generate_content(
                prompt,
                generation_config={
                    "temperature": 0.85 + (attempt * 0.05),  # More creative on retries
                    "max_output_tokens": 800,
                    "top_p": 0.95,
                    "top_k": 40,
                }
            )

            # Extract text safely
            raw_caption = _extract_response_text(response)
            logger.debug(f"Raw caption: {raw_caption[:100]}")

            # Clean AI artifacts
            cleaned = _clean_caption(raw_caption)

            # Validate
            is_valid, reason = _validate_caption(cleaned, memory.category)

            if is_valid:
                caption = cleaned
                logger.info(f"✅ Caption valid on attempt {attempt}")
                break
            else:
                logger.warning(f"⚠️ Attempt {attempt} invalid: {reason}")

        except Exception as e:
            logger.warning(f"❌ Attempt {attempt} failed: {e}")

    # ========== STEP 4: HUMANIZE OR FALLBACK ==========
    if caption:
        # Success - humanize
        try:
            caption = humanize_caption(caption)
        except Exception as e:
            logger.warning(f"Humanization failed: {e}")

        memory.caption = caption
        memory.caption_style = style_name

        # Success log
        logger.info("=" * 50)
        logger.info("✅ CAPTION GENERATED")
        logger.info("=" * 50)
        logger.info(f"📝 Style: {style_name}")
        logger.info(f"📏 Length: {len(caption)} chars")
        logger.info(f"😊 Emojis: {_count_emojis(caption)}")
        logger.info(f"📄 Preview: {caption[:100]}...")
        logger.info("=" * 50)

    else:
        # All attempts failed - use fallback
        logger.warning("⚠️ All Gemini attempts failed. Using fallback.")

        fallback = _get_fallback_caption(memory.category)
        memory.caption = fallback
        memory.caption_style = "fallback"

        logger.info(f"📄 Fallback caption used (category: {memory.category})")

    logger.info("=== CAPTION AGENT DONE ===\n")
    return memory


# ============================================================
# STANDALONE TESTING
# ============================================================

if __name__ == "__main__":
    """Test caption agent independently"""
    print("\n" + "=" * 60)
    print("CAPTION AGENT - STANDALONE TEST")
    print("=" * 60 + "\n")

    # Test with different categories
    test_cases = [
        {
            "topic": "Lord Krishna playing flute in Vrindavan with cows",
            "category": "krishna",
            "mood": "peaceful, divine, romantic",
            "visual_elements": ["flute", "peacock feather", "cows", "yellow dhoti"],
            "colors": ["blue", "yellow", "green"],
            "post_type": "image"
        },
        {
            "topic": "Lord Shiva meditating in Himalayas",
            "category": "shiva",
            "mood": "powerful, mystical, serene",
            "visual_elements": ["trishul", "snake", "moon"],
            "colors": ["blue", "white", "silver"],
            "post_type": "image"
        },
        {
            "topic": "Krishna teaching Gita to Arjuna",
            "category": "krishna",
            "mood": "divine, powerful, wise",
            "visual_elements": ["chariot", "battlefield"],
            "colors": ["blue", "gold"],
            "post_type": "reel"  # 🆕 Test reel style
        }
    ]

    for test in test_cases:
        print(f"\n{'=' * 60}")
        print(f"Topic: {test['topic']}")
        print(f"Category: {test['category']}")
        print(f"Post Type: {test['post_type']}")
        print("=" * 60)

        memory = AgentMemory()
        memory.topic = test["topic"]
        memory.category = test["category"]
        memory.mood = test["mood"]
        memory.visual_elements = test["visual_elements"]
        memory.colors = test["colors"]
        memory.image_prompt = f"Image of {test['topic']}"
        memory.post_type = test["post_type"]

        result = run(memory)

        print(f"\n📝 CAPTION:\n{result.caption}\n")
        print(f"📊 Style: {result.caption_style}")
        print(f"📏 Length: {len(result.caption)} chars")
