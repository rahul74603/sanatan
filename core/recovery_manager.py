"""
Recovery Manager - अधूरे कामों को दोबारा शुरू करने वाला सिस्टम

Features:
- हर स्टेज पर checkpoint save करता है
- अगली बार run पर पुराने अधूरे काम detect करता है
- Image bytes local save (दोबारा AI se नहीं बनाना पड़ता)
- 🆕 Voice bytes + SRT save (reel के लिए)
- 24 घंटे बाद auto-cleanup
- Token/Time/Money बचाता है

Recovery Stages (Carousel):
1. TOPIC_SELECTED       - Planner हो चुका
2. SLIDES_STRUCTURED    - Gemini ने 5 slide structure दे दिया
3. IMAGES_GENERATED     - सभी images बन गयीं (bytes locally saved)
4. IMAGES_UPLOADED      - GCS URLs मिल गए
5. IG_CONTAINERS_READY  - IG media_ids मिल गए
6. FB_UPLOADED          - FB photo_ids मिल गए
7. PUBLISHED            - Complete (recovery delete)

🆕 Recovery Stages (Reel):
10. REEL_STORY_WRITTEN     - Hindi story तैयार
11. REEL_SCENES_SPLIT      - 6 scenes में divide हुआ
12. REEL_IMAGES_GENERATED  - सभी 6 scene images बनी
13. REEL_VOICE_GENERATED   - TTS voice तैयार
14. REEL_SUBTITLES_MADE    - SRT subtitles बने
15. REEL_VIDEO_BUILT       - Final video local बना
16. REEL_VIDEO_UPLOADED    - GCS पर upload हुआ
17. REEL_IG_PUBLISHED      - Instagram पर publish
18. REEL_FB_PUBLISHED      - Facebook पर publish
19. REEL_YT_PUBLISHED      - YouTube पर publish
"""
import json
import time
import shutil
import math
from pathlib import Path
from datetime import date, datetime, timedelta
from typing import Optional, List

from utils.logger import get_logger

logger = get_logger("recovery")


# ============================================================
# CONFIGURATION
# ============================================================

RECOVERY_DIR = Path("logs/recovery")
RECOVERY_EXPIRY_HOURS = 24    # 24 घंटे बाद पुराने recovery delete
MAX_RECOVERY_SESSIONS = 5     # ज़्यादा से ज़्यादा 5 pending sessions

# Cost estimates (per unit)
COST_PER_IMAGE_INR = 2.5      # Imagen cost
COST_PER_GEMINI_CALL_INR = 0.5
COST_PER_TTS_CALL_INR = 0.5   # 🆕 TTS cost

# Recovery stages (Carousel + Reel)
STAGES = {
    # Carousel/Image stages
    "TOPIC_SELECTED":       1,
    "SLIDES_STRUCTURED":    2,
    "IMAGES_GENERATED":     3,
    "IMAGES_UPLOADED":      4,
    "IG_CONTAINERS_READY":  5,
    "FB_UPLOADED":          6,
    "PUBLISHED":            7,

    # 🆕 Reel stages (10-19)
    "REEL_STORY_WRITTEN":     10,
    "REEL_SCENES_SPLIT":      11,
    "REEL_IMAGES_GENERATED":  12,
    "REEL_VOICE_GENERATED":   13,
    "REEL_SUBTITLES_MADE":    14,
    "REEL_VIDEO_BUILT":       15,
    "REEL_VIDEO_UPLOADED":    16,
    "REEL_IG_PUBLISHED":      17,
    "REEL_FB_PUBLISHED":      18,
    "REEL_YT_PUBLISHED":      19,
}

STAGE_NAMES_HINDI = {
    # Carousel
    "TOPIC_SELECTED":       "विषय चुना गया",
    "SLIDES_STRUCTURED":    "स्लाइड्स का ढांचा तैयार",
    "IMAGES_GENERATED":     "तस्वीरें बन गयीं",
    "IMAGES_UPLOADED":      "GCS पर अपलोड हुआ",
    "IG_CONTAINERS_READY":  "इंस्टाग्राम कंटेनर तैयार",
    "FB_UPLOADED":          "फेसबुक पर अपलोड हुआ",
    "PUBLISHED":            "पूरी तरह पब्लिश हुआ",

    # 🆕 Reel
    "REEL_STORY_WRITTEN":     "रील की कहानी तैयार",
    "REEL_SCENES_SPLIT":      "6 दृश्यों में बंटा",
    "REEL_IMAGES_GENERATED":  "रील की तस्वीरें बनी",
    "REEL_VOICE_GENERATED":   "आवाज़ तैयार",
    "REEL_SUBTITLES_MADE":    "सबटाइटल बने",
    "REEL_VIDEO_BUILT":       "वीडियो बना",
    "REEL_VIDEO_UPLOADED":    "वीडियो अपलोड हुआ",
    "REEL_IG_PUBLISHED":      "इंस्टाग्राम पर पब्लिश",
    "REEL_FB_PUBLISHED":      "फेसबुक पर पब्लिश",
    "REEL_YT_PUBLISHED":      "यूट्यूब पर पब्लिश",
}

# Stages that mean "fully complete" (delete checkpoint)
COMPLETED_STAGES = {"PUBLISHED", "REEL_YT_PUBLISHED"}


# ============================================================
# FOLDER MANAGEMENT
# ============================================================

def _ensure_recovery_dir():
    """Recovery folder बनाओ अगर नहीं है तो"""
    RECOVERY_DIR.mkdir(parents=True, exist_ok=True)


def _get_session_dir(session_id: str) -> Path:
    """किसी session का folder path लो"""
    return RECOVERY_DIR / session_id


def _make_json_serializable(value, _seen: Optional[set] = None):
    """
    Recovery JSON को robust बनाओ.

    कुछ video/analytics libraries numpy scalar values (जैसे np.int64,
    np.float64) return करती हैं। Python का default json.dump उन्हें serialize
    नहीं कर पाता और checkpoint टूट जाता है। यह helper nested dict/list के अंदर
    ऐसे values को normal Python types में बदल देता है।
    """
    if _seen is None:
        _seen = set()

    # Primitive values
    if value is None or isinstance(value, (str, bool)):
        return value

    if isinstance(value, int):
        return int(value)

    if isinstance(value, float):
        return value if math.isfinite(value) else None

    if isinstance(value, (datetime, date)):
        return value.isoformat()

    if isinstance(value, Path):
        return str(value)

    if isinstance(value, (bytes, bytearray, memoryview)):
        return f"<bytes:{len(value)}>"

    # Avoid infinite recursion on self-referential containers
    value_id = id(value)
    if value_id in _seen:
        return "<recursive>"

    # numpy scalar support without requiring numpy as a hard import here
    if hasattr(value, "item") and callable(getattr(value, "item", None)):
        try:
            return _make_json_serializable(value.item(), _seen)
        except Exception:
            pass

    # numpy arrays / pandas-like objects
    if hasattr(value, "tolist") and callable(getattr(value, "tolist", None)):
        try:
            return _make_json_serializable(value.tolist(), _seen)
        except Exception:
            pass

    if isinstance(value, dict):
        _seen.add(value_id)
        try:
            return {
                str(_make_json_serializable(k, _seen)): _make_json_serializable(v, _seen)
                for k, v in value.items()
            }
        finally:
            _seen.discard(value_id)

    if isinstance(value, (list, tuple, set)):
        _seen.add(value_id)
        try:
            return [_make_json_serializable(item, _seen) for item in value]
        finally:
            _seen.discard(value_id)

    # Last chance: if json can handle it, keep as-is; otherwise stringify.
    try:
        json.dumps(value, ensure_ascii=False, allow_nan=False)
        return value
    except (TypeError, ValueError):
        return str(value)


# ============================================================
# CHECKPOINT SAVE
# ============================================================

def save_checkpoint(
    session_id: str,
    stage: str,
    data: dict,
    slides_bytes: Optional[dict] = None,
    voice_bytes: Optional[bytes] = None,
    subtitle_srt: Optional[str] = None
) -> bool:
    """
    Checkpoint save करो — किसी भी stage पर

    Args:
        session_id: Unique session ID
        stage: Current stage (STAGES में से एक)
        data: सब metadata (topic, slides info, media_ids etc.)
        slides_bytes: Dict with keys:
            - int (1, 2, 3...) for carousel slides → saves as slide_N.jpg
            - str ("reel_scene_1", "reel_scene_2"...) for reel → saves as reel_scene_N.jpg
        voice_bytes: 🆕 Reel voice MP3 bytes → saves as voice.mp3
        subtitle_srt: 🆕 Reel SRT content → saves as subtitles.srt

    Returns:
        True अगर save हो गया
    """
    if stage not in STAGES:
        logger.warning(f"⚠️  अमान्य stage: {stage}")
        return False

    try:
        _ensure_recovery_dir()
        session_dir = _get_session_dir(session_id)
        session_dir.mkdir(parents=True, exist_ok=True)

        # Save image bytes (अगर दिया है तो)
        if slides_bytes:
            for key, img_bytes in slides_bytes.items():
                if img_bytes:
                    # Handle both carousel (int) and reel (string) keys
                    if isinstance(key, int):
                        filename = f"slide_{key}.jpg"
                    else:
                        # e.g., "reel_scene_1" → reel_scene_1.jpg
                        filename = f"{key}.jpg"

                    img_path = session_dir / filename
                    with open(img_path, 'wb') as f:
                        f.write(img_bytes)

        # 🆕 Save voice bytes (for reels)
        if voice_bytes:
            voice_path = session_dir / "voice.mp3"
            with open(voice_path, 'wb') as f:
                f.write(voice_bytes)
            logger.info(f"💾 Voice saved: {len(voice_bytes):,} bytes")

        # 🆕 Save subtitle SRT (for reels)
        if subtitle_srt:
            srt_path = session_dir / "subtitles.srt"
            with open(srt_path, 'w', encoding='utf-8') as f:
                f.write(subtitle_srt)
            logger.info(f"💾 Subtitles saved: {len(subtitle_srt)} chars")

        # Save state.json
        state = {
            "session_id":     session_id,
            "stage":          stage,
            "stage_number":   STAGES[stage],
            "stage_hindi":    STAGE_NAMES_HINDI.get(stage, stage),
            "timestamp":      datetime.now().isoformat(),
            "last_updated":   datetime.now().isoformat(),
            "data":           _make_json_serializable(data),
        }

        state_path = session_dir / "state.json"
        with open(state_path, 'w', encoding='utf-8') as f:
            json.dump(
                _make_json_serializable(state),
                f,
                indent=2,
                ensure_ascii=False,
                allow_nan=False,
            )

        stage_name = STAGE_NAMES_HINDI.get(stage, stage)
        logger.info(f"💾 Checkpoint सहेजा गया: {stage_name} (सेशन: {session_id[:8]})")
        return True

    except Exception as e:
        logger.error(f"❌ Checkpoint save नहीं हो पाया: {e}")
        return False


# ============================================================
# CHECKPOINT LOAD
# ============================================================

def load_checkpoint(session_id: str) -> Optional[dict]:
    """
    किसी session का checkpoint load करो
    Returns: full state dict या None

    Loads:
    - state.json (metadata)
    - slide_*.jpg (carousel images)
    - reel_scene_*.jpg (reel scene images)
    - voice.mp3 (reel voice)
    - subtitles.srt (reel subtitles)
    """
    try:
        session_dir = _get_session_dir(session_id)
        state_path = session_dir / "state.json"

        if not state_path.exists():
            return None

        with open(state_path, 'r', encoding='utf-8') as f:
            state = json.load(f)

        # Load image bytes back
        slides_bytes = {}

        # Carousel slides (slide_N.jpg)
        for slide_file in session_dir.glob("slide_*.jpg"):
            try:
                slide_num = int(slide_file.stem.split("_")[1])
                with open(slide_file, 'rb') as f:
                    slides_bytes[slide_num] = f.read()
            except Exception as e:
                logger.warning(f"⚠️  स्लाइड {slide_file.name} load नहीं हुई: {e}")

        # 🆕 Reel scenes (reel_scene_N.jpg)
        for scene_file in session_dir.glob("reel_scene_*.jpg"):
            try:
                # Key = full stem name (e.g., "reel_scene_1")
                key = scene_file.stem
                with open(scene_file, 'rb') as f:
                    slides_bytes[key] = f.read()
            except Exception as e:
                logger.warning(f"⚠️  Scene {scene_file.name} load नहीं हुई: {e}")

        state["slides_bytes"] = slides_bytes

        # 🆕 Load voice bytes
        voice_path = session_dir / "voice.mp3"
        if voice_path.exists():
            with open(voice_path, 'rb') as f:
                state["voice_bytes"] = f.read()
            # Also add to slides_bytes with special key
            state["slides_bytes"]["voice_bytes"] = state["voice_bytes"]
            logger.info(f"♻️  Voice loaded: {len(state['voice_bytes']):,} bytes")

        # 🆕 Load subtitle SRT
        srt_path = session_dir / "subtitles.srt"
        if srt_path.exists():
            with open(srt_path, 'r', encoding='utf-8') as f:
                state["subtitle_srt"] = f.read()
            logger.info(f"♻️  Subtitles loaded: {len(state['subtitle_srt'])} chars")

        return state

    except Exception as e:
        logger.error(f"❌ Checkpoint load नहीं हुआ: {e}")
        return None


# ============================================================
# CHECKPOINT DELETE
# ============================================================

def delete_checkpoint(session_id: str) -> bool:
    """
    Session का सारा data delete करो (successful publish के बाद)
    """
    try:
        session_dir = _get_session_dir(session_id)
        if session_dir.exists():
            shutil.rmtree(session_dir)
            logger.info(f"🗑️  पुराना checkpoint हटाया: {session_id[:8]}")
            return True
        return False
    except Exception as e:
        logger.warning(f"⚠️  Checkpoint delete नहीं हुआ: {e}")
        return False


# ============================================================
# PENDING RECOVERY DETECTION
# ============================================================

def find_pending_recovery(post_type: str = "carousel") -> Optional[dict]:
    """
    सबसे नया pending session ढूंढो जो अभी complete नहीं हुआ

    Args:
        post_type: "carousel" | "image" | "reel"

    Returns: state dict या None

    Logic:
    - सभी session folders scan करो
    - 24 घंटे से पुराने skip करो
    - Completed stages वालों को skip करो (PUBLISHED, REEL_YT_PUBLISHED)
    - Post type match करो
    - सबसे नया pending return करो
    """
    try:
        _ensure_recovery_dir()

        if not RECOVERY_DIR.exists():
            return None

        pending_sessions = []
        now = datetime.now()
        expiry_cutoff = now - timedelta(hours=RECOVERY_EXPIRY_HOURS)

        for session_dir in RECOVERY_DIR.iterdir():
            if not session_dir.is_dir():
                continue

            state_path = session_dir / "state.json"
            if not state_path.exists():
                continue

            try:
                with open(state_path, 'r', encoding='utf-8') as f:
                    state = json.load(f)

                # Check if too old
                timestamp = datetime.fromisoformat(state["timestamp"])
                if timestamp < expiry_cutoff:
                    logger.info(
                        f"⏰ पुराना session मिला "
                        f"({state['session_id'][:8]}) — auto-cleanup कर रहे हैं"
                    )
                    shutil.rmtree(session_dir)
                    continue

                # Check post type match
                if state.get("data", {}).get("post_type") != post_type:
                    continue

                # Check if already completed
                if state.get("stage") in COMPLETED_STAGES:
                    logger.info(
                        f"✅ Completed session मिला "
                        f"({state['session_id'][:8]}) — cleanup कर रहे हैं"
                    )
                    shutil.rmtree(session_dir)
                    continue

                pending_sessions.append(state)

            except Exception as e:
                logger.warning(f"⚠️  Session {session_dir.name} पढ़ नहीं पाए: {e}")
                continue

        if not pending_sessions:
            return None

        # Sort by timestamp — latest पहले
        pending_sessions.sort(
            key=lambda s: s["timestamp"],
            reverse=True
        )

        # सबसे नया return करो
        latest = pending_sessions[0]

        # Load images back
        session_id = latest["session_id"]
        session_dir = _get_session_dir(session_id)

        slides_bytes = {}

        # Carousel slides
        for slide_file in session_dir.glob("slide_*.jpg"):
            try:
                slide_num = int(slide_file.stem.split("_")[1])
                with open(slide_file, 'rb') as f:
                    slides_bytes[slide_num] = f.read()
            except Exception:
                pass

        # 🆕 Reel scenes
        for scene_file in session_dir.glob("reel_scene_*.jpg"):
            try:
                key = scene_file.stem
                with open(scene_file, 'rb') as f:
                    slides_bytes[key] = f.read()
            except Exception:
                pass

        # 🆕 Voice bytes
        voice_path = session_dir / "voice.mp3"
        if voice_path.exists():
            with open(voice_path, 'rb') as f:
                voice_data = f.read()
                slides_bytes["voice_bytes"] = voice_data
                latest["voice_bytes"] = voice_data

        # 🆕 Subtitles
        srt_path = session_dir / "subtitles.srt"
        if srt_path.exists():
            with open(srt_path, 'r', encoding='utf-8') as f:
                latest["subtitle_srt"] = f.read()

        latest["slides_bytes"] = slides_bytes
        return latest

    except Exception as e:
        logger.error(f"❌ Recovery search error: {e}")
        return None


# ============================================================
# COST SAVINGS CALCULATOR
# ============================================================

def calculate_savings(resumed_from_stage: str) -> dict:
    """
    गणना करो कि recovery से कितने पैसे और समय बचे
    Works for both carousel and reel stages
    """
    stage_num = STAGES.get(resumed_from_stage, 0)

    images_saved = 0
    gemini_saved = 0
    tts_saved = 0
    time_saved_min = 0

    # ═══════════════════════════════════════════
    # CAROUSEL SAVINGS
    # ═══════════════════════════════════════════
    if stage_num >= 3 and stage_num < 10:  # IMAGES_GENERATED (carousel)
        images_saved = 5
        gemini_saved = 2  # structure + caption
        time_saved_min = 5

    if stage_num >= 4 and stage_num < 10:  # IMAGES_UPLOADED
        time_saved_min = 6

    if stage_num >= 5 and stage_num < 10:  # IG_CONTAINERS_READY
        time_saved_min = 7

    # ═══════════════════════════════════════════
    # 🆕 REEL SAVINGS
    # ═══════════════════════════════════════════
    if stage_num >= 11:  # REEL_SCENES_SPLIT+ (story + fact_check + scenes done)
        gemini_saved = 3

    if stage_num >= 12:  # REEL_IMAGES_GENERATED+ (6 images saved)
        images_saved = 6
        gemini_saved = 4  # story + fact + scenes + prompts
        time_saved_min = 5

    if stage_num >= 13:  # REEL_VOICE_GENERATED+ (TTS done)
        tts_saved = 1
        time_saved_min = 6

    if stage_num >= 14:  # REEL_SUBTITLES_MADE+
        time_saved_min = 7

    if stage_num >= 15:  # REEL_VIDEO_BUILT+ (Video building takes 5-10 min)
        time_saved_min = 12

    if stage_num >= 16:  # REEL_VIDEO_UPLOADED+
        time_saved_min = 14

    # Calculate total money
    money_saved = (
        images_saved * COST_PER_IMAGE_INR +
        gemini_saved * COST_PER_GEMINI_CALL_INR +
        tts_saved * COST_PER_TTS_CALL_INR
    )

    return {
        "money_saved_inr":    round(money_saved, 2),
        "time_saved_min":     time_saved_min,
        "images_reused":      images_saved,
        "gemini_calls_saved": gemini_saved,
        "tts_calls_saved":    tts_saved,
    }


# ============================================================
# BEAUTIFUL RECOVERY DISPLAY
# ============================================================

def display_pending_recovery(state: dict):
    """
    User को अच्छे से दिखाओ कि क्या पुराना काम मिला है
    """
    session_id = state["session_id"]
    stage = state["stage"]
    stage_hindi = STAGE_NAMES_HINDI.get(stage, stage)
    data = state.get("data", {})

    savings = calculate_savings(stage)

    logger.info("")
    logger.info("╔══════════════════════════════════════════════╗")
    logger.info("║   ♻️   पुराना अधूरा काम मिला!                 ║")
    logger.info("╠══════════════════════════════════════════════╣")
    logger.info(f"║ 🆔 सेशन        : {session_id[:8]}")
    logger.info(f"║ 📌 विषय        : {data.get('topic', 'अज्ञात')[:40]}")
    logger.info(f"║ 📂 श्रेणी       : {data.get('category', 'अज्ञात')}")
    logger.info(f"║ 📊 प्रकार       : {data.get('post_type', 'अज्ञात')}")
    logger.info(f"║ 📊 अंतिम स्टेज  : {stage_hindi}")
    logger.info(f"║ 🕐 कब बना था   : {state['timestamp'][:19]}")
    logger.info("╠══════════════════════════════════════════════╣")
    logger.info(f"║ 💰 पैसे बचेंगे  : ₹{savings['money_saved_inr']}")
    logger.info(f"║ ⏱️  समय बचेगा   : ~{savings['time_saved_min']} मिनट")
    logger.info(f"║ 🎨 तस्वीरें फिर से बनेंगी: नहीं ✅")

    if savings.get('tts_calls_saved', 0) > 0:
        logger.info(f"║ 🎤 आवाज़ फिर से बनेगी: नहीं ✅")

    logger.info("╚══════════════════════════════════════════════╝")
    logger.info("")


# ============================================================
# STATS
# ============================================================

def get_recovery_stats() -> dict:
    """सारे pending recoveries की स्थिति"""
    _ensure_recovery_dir()

    stats = {
        "total_pending":  0,
        "total_size_mb":  0,
        "oldest_hours":   0,
        "sessions":       []
    }

    if not RECOVERY_DIR.exists():
        return stats

    now = datetime.now()

    for session_dir in RECOVERY_DIR.iterdir():
        if not session_dir.is_dir():
            continue

        state_path = session_dir / "state.json"
        if not state_path.exists():
            continue

        try:
            with open(state_path, 'r', encoding='utf-8') as f:
                state = json.load(f)

            # Calculate folder size
            total_size = sum(
                f.stat().st_size for f in session_dir.rglob("*") if f.is_file()
            )

            # Calculate age
            timestamp = datetime.fromisoformat(state["timestamp"])
            age_hours = (now - timestamp).total_seconds() / 3600

            stats["sessions"].append({
                "session_id": state["session_id"][:8],
                "stage":      STAGE_NAMES_HINDI.get(state["stage"], state["stage"]),
                "post_type":  state.get("data", {}).get("post_type", "?"),
                "topic":      state.get("data", {}).get("topic", "अज्ञात")[:40],
                "age_hours":  round(age_hours, 1),
                "size_mb":    round(total_size / (1024*1024), 2),
            })

            stats["total_pending"] += 1
            stats["total_size_mb"] += total_size / (1024*1024)

            if age_hours > stats["oldest_hours"]:
                stats["oldest_hours"] = age_hours

        except Exception:
            continue

    stats["total_size_mb"] = round(stats["total_size_mb"], 2)
    stats["oldest_hours"] = round(stats["oldest_hours"], 1)

    return stats


def display_recovery_stats():
    """सारे pending recoveries का सुंदर display"""
    stats = get_recovery_stats()

    logger.info("")
    logger.info("╔══════════════════════════════════════════════╗")
    logger.info("║       ♻️   RECOVERY स्टेटस                    ║")
    logger.info("╠══════════════════════════════════════════════╣")
    logger.info(f"║ कुल pending  : {stats['total_pending']}")
    logger.info(f"║ कुल size     : {stats['total_size_mb']} MB")
    logger.info(f"║ सबसे पुराना  : {stats['oldest_hours']} घंटे")
    logger.info("╠══════════════════════════════════════════════╣")

    if stats["sessions"]:
        for s in stats["sessions"]:
            logger.info(f"║ 🆔 {s['session_id']} | {s['post_type']} | {s['stage']}")
            logger.info(f"║    विषय: {s['topic']}")
            logger.info(f"║    उम्र: {s['age_hours']}h | Size: {s['size_mb']}MB")
            logger.info("║")
    else:
        logger.info("║ कोई pending recovery नहीं है ✅")

    logger.info("╚══════════════════════════════════════════════╝")


# ============================================================
# CLEANUP
# ============================================================

def cleanup_old_recoveries():
    """24 घंटे से पुराने सारे recoveries delete करो"""
    _ensure_recovery_dir()

    if not RECOVERY_DIR.exists():
        return 0

    now = datetime.now()
    expiry_cutoff = now - timedelta(hours=RECOVERY_EXPIRY_HOURS)
    deleted = 0

    for session_dir in RECOVERY_DIR.iterdir():
        if not session_dir.is_dir():
            continue

        state_path = session_dir / "state.json"
        if not state_path.exists():
            # Empty folder — delete
            shutil.rmtree(session_dir)
            deleted += 1
            continue

        try:
            with open(state_path, 'r', encoding='utf-8') as f:
                state = json.load(f)

            timestamp = datetime.fromisoformat(state["timestamp"])
            if timestamp < expiry_cutoff:
                shutil.rmtree(session_dir)
                deleted += 1

        except Exception:
            continue

    if deleted > 0:
        logger.info(f"🧹 {deleted} पुराने recoveries हटाए गए")

    return deleted


# ============================================================
# STANDALONE TESTING
# ============================================================

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("RECOVERY MANAGER - STANDALONE TEST")
    print("=" * 60 + "\n")

    # Show current recoveries
    display_recovery_stats()

    # Test cleanup
    print("\n🧹 Cleanup पुराने files...")
    cleanup_old_recoveries()

    # Test save (carousel)
    print("\n💾 Test carousel checkpoint save...")
    save_checkpoint(
        session_id="test_carousel_123",
        stage="IMAGES_GENERATED",
        data={
            "topic":    "Test carousel topic",
            "category": "test",
            "post_type": "carousel",
            "slides":   [
                {"slide_number": i, "title": f"Slide {i}"}
                for i in range(1, 6)
            ]
        }
    )

    # 🆕 Test save (reel)
    print("\n💾 Test reel checkpoint save...")
    save_checkpoint(
        session_id="test_reel_456",
        stage="REEL_VOICE_GENERATED",
        data={
            "topic":    "Test reel topic",
            "category": "krishna",
            "post_type": "reel",
            "reel_story": "Test story text",
            "reel_scenes": [
                {"scene_number": i, "narration": f"Scene {i} narration"}
                for i in range(1, 7)
            ]
        },
        voice_bytes=b"fake_mp3_data_for_testing",
        subtitle_srt="1\n00:00:00,000 --> 00:00:02,000\nTest subtitle\n\n"
    )

    # Test load
    print("\n📂 Test checkpoint load...")
    loaded = load_checkpoint("test_reel_456")
    if loaded:
        print(f"✅ Loaded reel: {loaded['data']['topic']}")
        print(f"   Voice bytes: {len(loaded.get('voice_bytes', b''))} bytes")
        print(f"   Subtitles: {len(loaded.get('subtitle_srt', ''))} chars")

    # Test savings calculation
    print("\n💰 Test savings calculation...")
    savings = calculate_savings("REEL_VOICE_GENERATED")
    print(f"   Money saved: ₹{savings['money_saved_inr']}")
    print(f"   Time saved: {savings['time_saved_min']} min")
    print(f"   Images reused: {savings['images_reused']}")
    print(f"   TTS reused: {savings['tts_calls_saved']}")

    # Test find (reel)
    print("\n🔍 Test find pending reel...")
    pending = find_pending_recovery("reel")
    if pending:
        display_pending_recovery(pending)

    # Cleanup test
    print("\n🗑️  Test delete...")
    delete_checkpoint("test_carousel_123")
    delete_checkpoint("test_reel_456")

    print("\n✅ सारे tests हो गए!")