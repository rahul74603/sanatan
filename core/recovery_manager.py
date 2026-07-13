"""
Recovery Manager - अधूरे कामों को दोबारा शुरू करने वाला सिस्टम

Features:
- हर स्टेज पर checkpoint save करता है
- अगली बार run पर पुराने अधूरे काम detect करता है
- Image bytes local save (दोबारा AI se नहीं बनाना पड़ता)
- 24 घंटे बाद auto-cleanup
- Token/Time/Money बचाता है

Recovery Stages:
1. TOPIC_SELECTED       - Planner हो चुका
2. SLIDES_STRUCTURED    - Gemini ने 5 slide structure दे दिया
3. IMAGES_GENERATED     - सभी images बन गयीं (bytes locally saved)
4. IMAGES_UPLOADED      - GCS URLs मिल गए
5. IG_CONTAINERS_READY  - IG media_ids मिल गए
6. FB_UPLOADED          - FB photo_ids मिल गए
7. PUBLISHED            - Complete (recovery delete)
"""
import json
import time
import shutil
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, List

from utils.logger import get_logger

logger = get_logger("recovery")


# ============================================================
# CONFIGURATION
# ============================================================

RECOVERY_DIR = Path("logs/recovery")
RECOVERY_EXPIRY_HOURS = 24    # 24 घंटे बाद पुराने recovery delete
MAX_RECOVERY_SESSIONS = 5     # ज़्यादा से ज़्यादा 5 pending sessions

# Cost estimates (per slide)
COST_PER_IMAGE_INR = 2.5      # Imagen cost
COST_PER_GEMINI_CALL_INR = 0.5

# Recovery stages
STAGES = {
    "TOPIC_SELECTED":       1,
    "SLIDES_STRUCTURED":    2,
    "IMAGES_GENERATED":     3,
    "IMAGES_UPLOADED":      4,
    "IG_CONTAINERS_READY":  5,
    "FB_UPLOADED":          6,
    "PUBLISHED":            7,
}

STAGE_NAMES_HINDI = {
    "TOPIC_SELECTED":       "विषय चुना गया",
    "SLIDES_STRUCTURED":    "स्लाइड्स का ढांचा तैयार",
    "IMAGES_GENERATED":     "तस्वीरें बन गयीं",
    "IMAGES_UPLOADED":      "GCS पर अपलोड हुआ",
    "IG_CONTAINERS_READY":  "इंस्टाग्राम कंटेनर तैयार",
    "FB_UPLOADED":          "फेसबुक पर अपलोड हुआ",
    "PUBLISHED":            "पूरी तरह पब्लिश हुआ",
}


# ============================================================
# FOLDER MANAGEMENT
# ============================================================

def _ensure_recovery_dir():
    """Recovery folder बनाओ अगर नहीं है तो"""
    RECOVERY_DIR.mkdir(parents=True, exist_ok=True)


def _get_session_dir(session_id: str) -> Path:
    """किसी session का folder path लो"""
    return RECOVERY_DIR / session_id


# ============================================================
# CHECKPOINT SAVE
# ============================================================

def save_checkpoint(
    session_id: str,
    stage: str,
    data: dict,
    slides_bytes: Optional[dict] = None
) -> bool:
    """
    Checkpoint save करो — किसी भी stage पर

    Args:
        session_id: Unique session ID
        stage: Current stage (STAGES में से एक)
        data: सब metadata (topic, slides info, media_ids etc.)
        slides_bytes: {slide_num: bytes} — actual image bytes save करने के लिए

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
            for slide_num, img_bytes in slides_bytes.items():
                if img_bytes:
                    img_path = session_dir / f"slide_{slide_num}.jpg"
                    with open(img_path, 'wb') as f:
                        f.write(img_bytes)

        # Save state.json
        state = {
            "session_id":     session_id,
            "stage":          stage,
            "stage_number":   STAGES[stage],
            "stage_hindi":    STAGE_NAMES_HINDI.get(stage, stage),
            "timestamp":      datetime.now().isoformat(),
            "last_updated":   datetime.now().isoformat(),
            "data":           data,
        }

        state_path = session_dir / "state.json"
        with open(state_path, 'w', encoding='utf-8') as f:
            json.dump(state, f, indent=2, ensure_ascii=False)

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
        for slide_file in session_dir.glob("slide_*.jpg"):
            try:
                slide_num = int(slide_file.stem.split("_")[1])
                with open(slide_file, 'rb') as f:
                    slides_bytes[slide_num] = f.read()
            except Exception as e:
                logger.warning(f"⚠️  स्लाइड {slide_file.name} load नहीं हुई: {e}")

        state["slides_bytes"] = slides_bytes
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
    Returns: state dict या None

    Logic:
    - सभी session folders scan करो
    - 24 घंटे से पुराने skip करो
    - PUBLISHED stage वालों को skip करो
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

                # Check if already published
                if state.get("stage") == "PUBLISHED":
                    logger.info(
                        f"✅ Published session मिला "
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
        for slide_file in session_dir.glob("slide_*.jpg"):
            try:
                slide_num = int(slide_file.stem.split("_")[1])
                with open(slide_file, 'rb') as f:
                    slides_bytes[slide_num] = f.read()
            except Exception:
                pass

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
    """
    stage_num = STAGES.get(resumed_from_stage, 0)

    # Kitne API calls skip हुए
    if stage_num >= 3:  # IMAGES_GENERATED से आगे
        images_saved = 5
        gemini_saved = 2  # structure + caption
    elif stage_num >= 2:  # SLIDES_STRUCTURED से आगे
        images_saved = 0
        gemini_saved = 1
    else:
        images_saved = 0
        gemini_saved = 0

    money_saved = (
        images_saved * COST_PER_IMAGE_INR +
        gemini_saved * COST_PER_GEMINI_CALL_INR
    )

    # Time savings estimate
    if stage_num >= 3:
        time_saved_min = 5  # पूरी image generation skip
    elif stage_num >= 4:
        time_saved_min = 6  # + upload skip
    elif stage_num >= 5:
        time_saved_min = 7  # + IG containers skip
    else:
        time_saved_min = 2

    return {
        "money_saved_inr": round(money_saved, 2),
        "time_saved_min":  time_saved_min,
        "images_reused":   images_saved,
        "gemini_calls_saved": gemini_saved,
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
    logger.info(f"║ 📊 अंतिम स्टेज  : {stage_hindi}")
    logger.info(f"║ 🕐 कब बना था   : {state['timestamp'][:19]}")
    logger.info("╠══════════════════════════════════════════════╣")
    logger.info(f"║ 💰 पैसे बचेंगे  : ₹{savings['money_saved_inr']}")
    logger.info(f"║ ⏱️  समय बचेगा   : ~{savings['time_saved_min']} मिनट")
    logger.info(f"║ 🎨 तस्वीरें फिर से बनेंगी: नहीं ✅")
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
            logger.info(f"║ 🆔 {s['session_id']} | {s['stage']}")
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

    # Test save
    print("\n💾 Test checkpoint save...")
    save_checkpoint(
        session_id="test123",
        stage="IMAGES_GENERATED",
        data={
            "topic":    "Test topic",
            "category": "test",
            "post_type": "carousel",
            "slides":   [
                {"slide_number": i, "title": f"Slide {i}"}
                for i in range(1, 6)
            ]
        }
    )

    # Test load
    print("\n📂 Test checkpoint load...")
    loaded = load_checkpoint("test123")
    if loaded:
        print(f"✅ Loaded: {loaded['data']['topic']}")

    # Test find
    print("\n🔍 Test find pending...")
    pending = find_pending_recovery("carousel")
    if pending:
        display_pending_recovery(pending)

    # Cleanup test
    print("\n🗑️  Test delete...")
    delete_checkpoint("test123")

    print("\n✅ सारे tests हो गए!")