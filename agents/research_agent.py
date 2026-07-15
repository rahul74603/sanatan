"""
Research Agent - Collects deep information about the topic

V2.1 FIXES:
- Bulletproof JSON parsing (5 strategies)
- Auto-repair malformed JSON
- Better error recovery
- Always returns valid data
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


# ============================================================
# COMPREHENSIVE FALLBACK DATABASE
# ============================================================

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


# In-memory cache
_research_cache = {}


def _get_cache_key(topic: str, category: str) -> str:
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


# ============================================================
# V2.1: BULLETPROOF JSON PARSING (5 Strategies)
# ============================================================

def _strategy_1_direct_parse(raw: str) -> dict:
    """Strategy 1: Direct parse"""
    return json.loads(raw)


def _strategy_2_remove_markdown(raw: str) -> dict:
    """Strategy 2: Remove markdown code blocks"""
    cleaned = re.sub(r'```json\s*', '', raw, flags=re.IGNORECASE)
    cleaned = re.sub(r'```\s*', '', cleaned)
    return json.loads(cleaned.strip())


def _strategy_3_extract_braces(raw: str) -> dict:
    """Strategy 3: Extract content between first { and last }"""
    start = raw.find('{')
    end = raw.rfind('}')

    if start == -1 or end == -1 or end <= start:
        raise ValueError("No braces found")

    extracted = raw[start:end + 1]
    return json.loads(extracted)


def _strategy_4_fix_common_errors(raw: str) -> dict:
    """Strategy 4: Auto-fix common JSON errors"""

    # Extract braces first
    start = raw.find('{')
    end = raw.rfind('}')
    if start == -1 or end == -1:
        raise ValueError("No braces")

    text = raw[start:end + 1]

    # Fix 1: Remove trailing commas before } or ]
    text = re.sub(r',(\s*[}\]])', r'\1', text)

    # Fix 2: Fix single quotes to double quotes (careful - only for keys/values)
    # Match: 'key': or : 'value'
    text = re.sub(r"'(\w+)':", r'"\1":', text)  # Keys
    text = re.sub(r":\s*'([^']*)'", r': "\1"', text)  # Values

    # Fix 3: Remove control characters
    text = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', text)

    # Fix 4: Fix unterminated strings by escaping quotes inside values
    # This is tricky - try to fix by removing lines with issues
    lines = text.split('\n')
    fixed_lines = []
    for line in lines:
        # Count unescaped quotes
        quotes = len(re.findall(r'(?<!\\)"', line))
        if quotes % 2 != 0:
            # Odd number of quotes - unterminated string
            # Try to close it
            if line.rstrip().endswith(','):
                line = line.rstrip(',').rstrip() + '",'
            else:
                line = line.rstrip() + '"'
        fixed_lines.append(line)

    text = '\n'.join(fixed_lines)

    return json.loads(text)


def _strategy_5_extract_fields_manually(raw: str) -> dict:
    """Strategy 5: Extract fields manually with regex (last resort)"""
    result = {}

    # Extract each field using regex patterns
    patterns = {
        'mood': r'"mood"\s*:\s*"([^"]+)"',
        'time_of_day': r'"time_of_day"\s*:\s*"([^"]+)"',
        'setting': r'"setting"\s*:\s*"([^"]+)"',
    }

    for field, pattern in patterns.items():
        match = re.search(pattern, raw)
        if match:
            result[field] = match.group(1)

    # Extract arrays
    array_fields = ['keywords', 'visual_elements', 'colors', 'symbols']
    for field in array_fields:
        # Try to find array content
        pattern = rf'"{field}"\s*:\s*\[([^\]]+)\]'
        match = re.search(pattern, raw)
        if match:
            # Extract items
            items_str = match.group(1)
            # Split by comma and clean
            items = re.findall(r'"([^"]+)"', items_str)
            if items:
                result[field] = items

    if not result:
        raise ValueError("Could not extract any fields")

    return result


def _parse_json_bulletproof(raw: str) -> dict:
    """
    Try 5 strategies to parse JSON.
    Returns dict or raises exception.
    """
    strategies = [
        ("Direct parse", _strategy_1_direct_parse),
        ("Remove markdown", _strategy_2_remove_markdown),
        ("Extract braces", _strategy_3_extract_braces),
        ("Fix common errors", _strategy_4_fix_common_errors),
        ("Manual extraction", _strategy_5_extract_fields_manually),
    ]

    last_error = None
    for name, strategy_func in strategies:
        try:
            result = strategy_func(raw)
            if result and isinstance(result, dict) and len(result) > 0:
                logger.info(f"✅ JSON parsed via: {name}")
                return result
        except Exception as e:
            last_error = f"{name}: {str(e)[:60]}"
            continue

    raise Exception(f"All JSON strategies failed. Last: {last_error}")


# ============================================================
# VALIDATION
# ============================================================

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


# ============================================================
# GEMINI CALL
# ============================================================

def _call_gemini(prompt: str) -> dict:
    """Call Gemini with bulletproof parsing"""

    model = genai.GenerativeModel(GEMINI_MODEL)

    generation_config = {
        "temperature":      0.8,
        "max_output_tokens": 800,  # V2.1: Increased from 600
        "top_p":            0.95,
    }

    response = model.generate_content(
        prompt,
        generation_config=generation_config
    )

    raw = _extract_response_text(response)

    # V2.1: Use bulletproof parser
    data = _parse_json_bulletproof(raw)

    return data


# ============================================================
# MAIN AGENT
# ============================================================

def run(memory: AgentMemory) -> AgentMemory:
    """
    Research topic and fill visual details.
    Uses cache → Gemini (bulletproof) → fallback database.
    """
    logger.info("=== RESEARCH AGENT V2.1 STARTED ===")
    logger.info(f"Topic: {memory.topic}")

    # Cache check
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

    # Build prompt
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

Return ONLY a valid JSON object. No markdown, no explanations, no code blocks.
Use SIMPLE double-quoted strings only. No line breaks inside string values.

Exact format:

{{
    "keywords": ["keyword1", "keyword2", "keyword3", "keyword4", "keyword5"],
    "mood": "5-8 words describing emotional atmosphere",
    "visual_elements": ["element1", "element2", "element3", "element4", "element5"],
    "colors": ["color1", "color2", "color3"],
    "symbols": ["symbol1", "symbol2", "symbol3"],
    "time_of_day": "sunrise",
    "setting": "detailed location description in 10-15 words"
}}

Rules:
1. All values must be simple strings (no nested quotes)
2. Arrays must have items in double quotes
3. No trailing commas
4. No comments
5. Return ONLY the JSON object

Use authentic Indian spiritual context."""

    # Gemini attempts with bulletproof parsing
    max_retries = 3  # V2.1: Increased from 2

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

        except Exception as e:
            logger.warning(
                f"Gemini failed (attempt {attempt}): "
                f"{type(e).__name__}: {str(e)[:100]}"
            )

    # Fallback
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


# ============================================================
# STANDALONE TEST
# ============================================================

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("RESEARCH AGENT V2.1 - TEST")
    print("=" * 60 + "\n")

    memory = AgentMemory()
    memory.topic = "Ganesha blessing devotees removing obstacles vighnaharta"
    memory.category = "ganesha"
    memory.is_festival = False

    result = run(memory)

    print(f"\n📊 Results:")
    print(f"   Mood       : {result.mood}")
    print(f"   Keywords   : {result.keywords}")
    print(f"   Visuals    : {result.visual_elements}")
    print(f"   Colors     : {result.colors}")
    print(f"   Symbols    : {result.symbols}")