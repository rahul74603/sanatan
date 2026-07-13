"""
Research Agent - Collects deep information about the topic
Enhanced version with better error handling, caching, and richer fallbacks
"""
import json
import re
import hashlib
import google.generativeai as genai
from core.memory import AgentMemory
from config.settings import GEMINI_API_KEY, GEMINI_MODEL
from utils.logger import get_logger

genai.configure(api_key=GEMINI_API_KEY)
logger = get_logger("research_agent")


# ============================================
# COMPREHENSIVE FALLBACK DATABASE
# ============================================
FALLBACK_RESEARCH = {
    "krishna": {
        "keywords":        ["divine flute", "Vrindavan", "peacock feather", "blue skin", "Radha love"],
        "mood":            "devotional, romantic, playful, peaceful",
        "visual_elements": ["bansuri flute", "peacock feather crown", "cows", "lotus", "yellow dhoti"],
        "colors":          ["deep blue", "golden yellow", "green", "gold"],
        "symbols":         ["flute", "peacock", "lotus", "sudarshan chakra", "cow"],
        "time_of_day":     "sunrise",
        "setting":         "Vrindavan forest with Yamuna river"
    },
    "shiva": {
        "keywords":        ["Kailash", "trishul", "meditation", "cosmic energy", "third eye"],
        "mood":            "powerful, mystical, serene, transcendent",
        "visual_elements": ["trishul", "damru", "snake around neck", "crescent moon", "matted hair"],
        "colors":          ["deep blue", "white", "silver", "ash grey", "orange"],
        "symbols":         ["trishul", "om", "shivling", "third eye", "rudraksha"],
        "time_of_day":     "night",
        "setting":         "snow-covered Himalayas at Mount Kailash"
    },
    "hanuman": {
        "keywords":        ["strength", "devotion", "Ram bhakt", "flying", "mace"],
        "mood":            "powerful, devotional, courageous, loyal",
        "visual_elements": ["gada mace", "orange body", "flying pose", "sanjeevani mountain"],
        "colors":          ["orange", "red", "saffron", "gold"],
        "symbols":         ["gada", "flag", "Ram naam", "sanjeevani"],
        "time_of_day":     "sunrise",
        "setting":         "flying across sky or in forest"
    },
    "ganesha": {
        "keywords":        ["wisdom", "obstacle remover", "modak", "elephant head", "beginnings"],
        "mood":            "joyful, wise, auspicious, welcoming",
        "visual_elements": ["modak sweet", "mouse vahana", "broken tusk", "lotus throne"],
        "colors":          ["red", "gold", "yellow", "orange"],
        "symbols":         ["modak", "lotus", "swastika", "om", "elephant"],
        "time_of_day":     "morning",
        "setting":         "temple with flowers and lotus"
    },
    "durga": {
        "keywords":        ["shakti", "divine feminine", "lion", "weapons", "warrior goddess"],
        "mood":            "powerful, protective, fierce, motherly",
        "visual_elements": ["lion vahana", "ten arms with weapons", "red saree", "golden crown"],
        "colors":          ["red", "gold", "orange", "pink"],
        "symbols":         ["trishul", "lotus", "conch", "sword", "chakra"],
        "time_of_day":     "sunrise",
        "setting":         "battlefield or temple with lions"
    },
    "ram": {
        "keywords":        ["dharma", "ideal king", "bow arrow", "Ayodhya", "maryada"],
        "mood":            "noble, righteous, calm, dignified",
        "visual_elements": ["bow and arrow", "royal crown", "yellow dhoti", "tilak"],
        "colors":          ["yellow", "gold", "green", "saffron"],
        "symbols":         ["bow", "arrow", "crown", "lotus", "Ram naam"],
        "time_of_day":     "morning",
        "setting":         "forest or royal court of Ayodhya"
    },
    "motivational": {
        "keywords":        ["strength", "courage", "sunrise", "victory", "determination"],
        "mood":            "inspiring, energetic, hopeful, powerful",
        "visual_elements": ["mountain peak", "sunrise", "eagle", "warrior silhouette", "light rays"],
        "colors":          ["orange", "gold", "red", "yellow", "deep blue"],
        "symbols":         ["sun", "mountain", "eagle", "lotus", "flame"],
        "time_of_day":     "sunrise",
        "setting":         "mountain peak or vast landscape"
    },
    "temple": {
        "keywords":        ["sacred", "ancient", "divine architecture", "spiritual", "peaceful"],
        "mood":            "sacred, peaceful, mystical, timeless",
        "visual_elements": ["stone carvings", "diyas", "flowers", "bells", "flags"],
        "colors":          ["gold", "orange", "white", "cream", "red"],
        "symbols":         ["om", "swastika", "lotus", "kalash", "trishul"],
        "time_of_day":     "morning aarti or evening",
        "setting":         "ancient Indian temple architecture"
    },
    "festival": {
        "keywords":        ["celebration", "devotion", "colors", "joy", "tradition"],
        "mood":            "festive, joyful, celebratory, sacred",
        "visual_elements": ["diyas", "rangoli", "flowers", "lights", "decorations"],
        "colors":          ["gold", "red", "orange", "yellow", "pink"],
        "symbols":         ["diya", "rangoli", "kalash", "flowers", "flag"],
        "time_of_day":     "evening or night",
        "setting":         "decorated temple or home"
    }
}


# ============================================
# IN-MEMORY CACHE (for same session)
# ============================================
_research_cache = {}


def _get_cache_key(topic: str, category: str) -> str:
    """Generate unique cache key for topic"""
    key = f"{topic}|{category}"
    return hashlib.md5(key.encode()).hexdigest()


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
    try:
        return str(response.candidates[0].content).strip()
    except Exception:
        pass
    raise Exception("Cannot extract text from Gemini response")


def _clean_json_response(raw: str) -> str:
    """Clean AI response to get pure JSON"""
    raw = re.sub(r'```json\s*', '', raw)
    raw = re.sub(r'```\s*',     '', raw)
    start = raw.find('{')
    end   = raw.rfind('}')
    if start != -1 and end != -1 and end > start:
        raw = raw[start:end + 1]
    return raw.strip()


def _validate_research_data(data: dict) -> dict:
    """Validate and fill missing fields"""
    defaults = {
        "keywords":        [],
        "mood":            "divine and peaceful",
        "visual_elements": [],
        "colors":          ["gold", "orange"],
        "symbols":         [],
        "time_of_day":     "morning",
        "setting":         "spiritual atmosphere"
    }
    for key, default_val in defaults.items():
        if key not in data or not data[key]:
            data[key] = default_val

    for list_key in ["keywords", "visual_elements", "colors", "symbols"]:
        if not isinstance(data[list_key], list):
            data[list_key] = [str(data[list_key])]

    if len(data["keywords"])        < 3: data["keywords"].extend(["divine", "spiritual", "sacred"])
    if len(data["visual_elements"]) < 3: data["visual_elements"].extend(["light", "lotus", "aura"])
    if len(data["colors"])          < 2: data["colors"].extend(["gold", "orange"])

    return data


def _get_fallback(category: str) -> dict:
    """Get rich fallback data for category"""
    return FALLBACK_RESEARCH.get(
        category, FALLBACK_RESEARCH["motivational"]
    ).copy()


# ============================================
# GEMINI CALL  (no response_mime_type)
# ============================================

def _call_gemini(prompt: str) -> dict:
    """
    Call Gemini and return parsed JSON dict.
    Does NOT use response_mime_type (not supported in all SDK versions).
    """
    model = genai.GenerativeModel(GEMINI_MODEL)

    # ✅ Only use universally supported fields
    generation_config = {
        "temperature":      0.8,
        "max_output_tokens": 600,
        "top_p":            0.95,
    }

    response = model.generate_content(
        prompt,
        generation_config=generation_config
    )

    raw     = _extract_response_text(response)
    cleaned = _clean_json_response(raw)
    data    = json.loads(cleaned)          # raises json.JSONDecodeError if bad
    return data


# ============================================
# MAIN AGENT
# ============================================

def run(memory: AgentMemory) -> AgentMemory:
    """
    Research topic and fill visual details.
    Uses cache → Gemini → fallback database.
    """
    logger.info("=== RESEARCH AGENT STARTED ===")
    logger.info(f"Topic: {memory.topic}")

    # ── Cache check ───────────────────────────────────────────
    cache_key = _get_cache_key(memory.topic, memory.category)
    if cache_key in _research_cache:
        logger.info("💾 Cache hit - using cached research")
        data = _research_cache[cache_key]
        memory.keywords        = data["keywords"]
        memory.mood            = data["mood"]
        memory.visual_elements = data["visual_elements"]
        memory.colors          = data["colors"]
        memory.symbols         = data["symbols"]
        logger.info("=== RESEARCH AGENT DONE ===")
        return memory

    # ── Build prompt ──────────────────────────────────────────
    festival_context = ""
    if memory.is_festival:
        festival_context = (
            f"\nSpecial Context: This is for {memory.festival_name} festival "
            f"- make it festive and celebratory."
        )

    prompt = f"""You are a spiritual art director for Indian devotional content.

Research this topic for creating a stunning spiritual Instagram post:

Topic: {memory.topic}
Category: {memory.category}{festival_context}

Return ONLY a valid JSON object. No markdown, no explanations.
Exact format:

{{
    "keywords": ["keyword1", "keyword2", "keyword3", "keyword4", "keyword5"],
    "mood": "5-8 words describing emotional atmosphere",
    "visual_elements": ["specific element 1", "element 2", "element 3", "element 4", "element 5"],
    "colors": ["primary color", "secondary color", "accent color"],
    "symbols": ["sacred symbol 1", "symbol 2", "symbol 3"],
    "time_of_day": "sunrise/morning/midday/sunset/night",
    "setting": "detailed description of location and atmosphere in 10-15 words"
}}

Use authentic Indian spiritual context and specific details."""

    # ── Gemini attempts ───────────────────────────────────────
    max_retries = 2

    for attempt in range(1, max_retries + 1):
        try:
            logger.info(f"Gemini attempt {attempt}/{max_retries}")

            data = _call_gemini(prompt)
            data = _validate_research_data(data)

            # Save to memory
            memory.keywords        = data["keywords"]
            memory.mood            = data["mood"]
            memory.visual_elements = data["visual_elements"]
            memory.colors          = data["colors"]
            memory.symbols         = data["symbols"]

            # Cache it
            _research_cache[cache_key] = data

            logger.info(f"✅ Research successful")
            logger.info(f"   Mood    : {memory.mood}")
            logger.info(f"   Keywords: {memory.keywords[:3]}...")
            logger.info(f"   Setting : {data.get('setting', 'N/A')}")
            logger.info("=== RESEARCH AGENT DONE ===")
            return memory

        except json.JSONDecodeError as e:
            logger.warning(f"JSON parse failed (attempt {attempt}): {e}")
        except Exception as e:
            logger.warning(
                f"Gemini failed (attempt {attempt}): "
                f"{type(e).__name__}: {e}"
            )

    # ── Fallback ──────────────────────────────────────────────
    logger.warning(
        f"⚠️ All Gemini attempts failed. Using fallback for '{memory.category}'"
    )
    fallback               = _get_fallback(memory.category)
    memory.keywords        = fallback["keywords"]
    memory.mood            = fallback["mood"]
    memory.visual_elements = fallback["visual_elements"]
    memory.colors          = fallback["colors"]
    memory.symbols         = fallback["symbols"]

    logger.info(f"Fallback mood: {memory.mood}")
    logger.info("=== RESEARCH AGENT DONE ===")
    return memory