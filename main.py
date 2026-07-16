"""
Divine Auto Poster - Main Entry Point (Production Grade)

Features:
- Agent-level error isolation
- Detailed timing metrics
- Smart retry logic
- Health checks
- 🆕 Recovery detection (auto-resume अधूरे काम)
- 🆕 पूरी तरह हिंदी logs
- 🆕 Cost + Time savings tracker
- 🆕 `recover` CLI command
- 🆕 V2: Reel pipeline (60-90s video for IG + FB + YouTube)
"""
import time
import random
import uuid
import traceback
from datetime import datetime
from typing import Callable, Optional, Tuple

import functions_framework

from core.database import initialize_database, save_post
from core.memory import AgentMemory
from core.recovery_manager import (
    find_pending_recovery,
    display_pending_recovery,
    calculate_savings,
    cleanup_old_recoveries,
    display_recovery_stats,
    delete_checkpoint,
    save_checkpoint,
)
from config.settings import validate, get_config_summary
from utils.logger import (
    get_logger,
    log_header,
    log_separator,
    log_success,
    log_failure,
    log_dict
)

from agents import (
    planner_agent,
    research_agent,
    prompt_agent,
    image_agent,
    quality_agent,
    caption_agent,
    hashtag_agent,
    publisher_agent,
    analytics_agent
)

from agents import carousel_agent

# 🆕 V2: Reel imports (graceful — allows partial phase completion)
try:
    from reels import reel_agent
    REEL_AGENT_AVAILABLE = True
except ImportError as e:
    REEL_AGENT_AVAILABLE = False
    _reel_agent_error = str(e)

# 🆕 V2: Video builder import (Phase 5 — required for reel)
try:
    from video_engine import video_builder
    VIDEO_BUILDER_AVAILABLE = True
except ImportError as e:
    VIDEO_BUILDER_AVAILABLE = False
    _video_builder_error = str(e)

# 🆕 V2: TTS + Subtitles (Phase 4)
try:
    from video_engine import tts_engine, subtitle_generator
    TTS_AVAILABLE = True
except ImportError as e:
    TTS_AVAILABLE = False
    _tts_error = str(e)

# 🆕 V2: Reel engine (Phase 6 — MASTER orchestrator, may not exist yet)
try:
    from core import reel_engine
    REEL_ENGINE_AVAILABLE = True
except ImportError as e:
    REEL_ENGINE_AVAILABLE = False
    _reel_engine_error = str(e)

# 🆕 V2: GCS video upload (Phase 6)
try:
    from utils.gcs_helper import upload_video
    UPLOAD_VIDEO_AVAILABLE = True
except ImportError as e:
    UPLOAD_VIDEO_AVAILABLE = False
    _upload_video_error = str(e)

logger = get_logger("main")


# ============================================================
# PIPELINE CONFIGURATION
# ============================================================

MAX_IMAGE_QUALITY_RETRIES = 3

# 🆕 V4: Delay only before posting (after content is ready)
# No pre-delay — video/image builds immediately
# Random 1-5 min wait before actual posting (natural feel)
HUMAN_DELAY_MIN = 60    # 1 minute minimum
HUMAN_DELAY_MAX = 300   # 5 minutes maximum

AGENT_TIMEOUTS = {
    "planner":   30,
    "research":  60,
    "prompt":    30,
    "image":     300,
    "quality":   60,
    "caption":   60,
    "hashtag":   30,
    "publisher": 300,
    "analytics": 120,
    "carousel":  600,
    "reel":      1800,
}

# ============================================================
# AGENT EXECUTION WRAPPER
# ============================================================

class AgentExecutionResult:
    """एक agent की execution का result"""

    def __init__(self, agent_name: str):
        self.agent_name = agent_name
        self.success    = False
        self.duration   = 0.0
        self.error      = None
        self.retries    = 0


def _execute_agent(
    agent_name: str,
    agent_function: Callable,
    memory: AgentMemory,
    critical: bool = False,
    max_retries: int = 1,
    *args,
    **kwargs
) -> Tuple[AgentMemory, AgentExecutionResult]:
    """
    Agent execute करो — error handling, timing, retries के साथ
    """
    result        = AgentExecutionResult(agent_name)
    start_time    = time.time()
    memory_backup = memory

    for attempt in range(1, max_retries + 1):
        try:
            log_separator(logger, char="─")
            logger.info(
                f"▶️  {agent_name} agent चला रहे हैं "
                f"(कोशिश {attempt}/{max_retries})"
            )

            returned_memory = agent_function(memory, *args, **kwargs)

            if returned_memory is None:
                logger.warning(
                    f"⚠️  {agent_name} ने None return किया। "
                    f"Memory backup वापस ला रहे हैं।"
                )
                memory = memory_backup
            else:
                memory = returned_memory

            result.success  = True
            result.retries  = attempt - 1
            result.duration = round(time.time() - start_time, 2)

            log_success(logger, f"{agent_name} पूर्ण — {result.duration}s में")
            return memory, result

        except Exception as e:
            result.error   = str(e)
            result.retries = attempt

            logger.warning(f"⚠️  {agent_name} कोशिश {attempt} विफल: {e}")

            if attempt < max_retries:
                wait = 2 ** attempt
                logger.info(f"⏳ {wait}s बाद दोबारा कोशिश...")
                time.sleep(wait)
            else:
                result.duration = round(time.time() - start_time, 2)

                if critical:
                    log_failure(logger, f"{agent_name} में गंभीर विफलता: {e}")
                    logger.error(traceback.format_exc())
                    raise Exception(f"Critical agent {agent_name} failed: {e}")
                else:
                    log_failure(logger, f"{agent_name} विफल (non-critical): {e}")
                    memory_backup.add_error(agent_name, str(e))
                    memory = memory_backup

    return memory, result


# ============================================================
# QUALITY LOOP
# ============================================================

def _execute_image_quality_loop(
    memory: AgentMemory
) -> Tuple[AgentMemory, AgentExecutionResult, AgentExecutionResult]:
    """Image + Quality retry loop"""
    log_separator(logger, char="─")
    logger.info(
        f"▶️  Image + Quality loop "
        f"(अधिकतम {MAX_IMAGE_QUALITY_RETRIES} कोशिश)"
    )

    image_result   = AgentExecutionResult("image")
    quality_result = AgentExecutionResult("quality")
    memory_backup  = memory

    for attempt in range(1, MAX_IMAGE_QUALITY_RETRIES + 1):
        try:
            logger.info(
                f"🎨 Image बनाने की कोशिश "
                f"{attempt}/{MAX_IMAGE_QUALITY_RETRIES}"
            )

            img_start       = time.time()
            returned_memory = image_agent.run(memory)
            if returned_memory is None:
                logger.warning("Image agent ने None दिया, backup use।")
                memory = memory_backup
            else:
                memory = returned_memory
            image_result.duration = round(time.time() - img_start, 2)

            qual_start      = time.time()
            returned_memory = quality_agent.run(memory)
            if returned_memory is None:
                logger.warning("Quality agent ने None दिया, backup use।")
                memory = memory_backup
            else:
                memory = returned_memory
            quality_result.duration = round(time.time() - qual_start, 2)

            if memory.quality_passed:
                image_result.success   = True
                image_result.retries   = attempt - 1
                quality_result.success = True

                log_success(
                    logger,
                    f"Image + Quality पास कोशिश {attempt} में "
                    f"(score: {memory.quality_score}/100)"
                )
                return memory, image_result, quality_result

            if attempt < MAX_IMAGE_QUALITY_RETRIES:
                logger.warning(
                    f"⚠️  Quality {memory.quality_score}/100 कम है। "
                    f"दोबारा बना रहे हैं ({attempt}/{MAX_IMAGE_QUALITY_RETRIES})"
                )
                time.sleep(3)
            else:
                logger.warning(
                    f"⚠️  अधिकतम कोशिश। "
                    f"वही image accept कर रहे हैं (score: {memory.quality_score}/100)"
                )
                image_result.success   = True
                quality_result.success = True
                memory.quality_passed  = True

        except Exception as e:
            image_result.error = str(e)
            logger.error(f"❌ Image बनाने में विफलता: {e}")

            if attempt < MAX_IMAGE_QUALITY_RETRIES:
                wait = 5 * attempt
                logger.info(f"⏳ {wait}s बाद कोशिश...")
                time.sleep(wait)
            else:
                raise Exception(f"Image {attempt} कोशिश में नहीं बनी: {e}")

    return memory, image_result, quality_result


# ============================================================
# HEALTH CHECK
# ============================================================

def _health_check() -> Tuple[bool, list]:
    """Pre-flight system check"""
    logger.info("🏥 सिस्टम health check कर रहे हैं...")
    issues = []

    try:
        validate()
    except Exception as e:
        issues.append(f"Config validation विफल: {e}")

    try:
        initialize_database()
    except Exception as e:
        issues.append(f"Database init विफल: {e}")

    try:
        import shutil
        free_bytes = shutil.disk_usage(".").free
        free_mb    = free_bytes / (1024 * 1024)
        if free_mb < 100:
            issues.append(f"कम disk space: {free_mb:.0f}MB free")
    except Exception:
        pass

    is_healthy = len(issues) == 0

    if is_healthy:
        log_success(logger, "Health check पास")
    else:
        logger.warning(f"⚠️  {len(issues)} समस्याएं मिलीं:")
        for issue in issues:
            logger.warning(f"   • {issue}")

    return is_healthy, issues


# ============================================================
# HUMAN-LIKE DELAY
# ============================================================

def _human_like_delay(
    min_seconds: int = HUMAN_DELAY_MIN,
    max_seconds: int = HUMAN_DELAY_MAX
):
    """इंसानी जैसा random delay"""
    delay = random.randint(min_seconds, max_seconds)
    if delay > 0:
        logger.info(f"⏳ इंसानी delay: {delay}s")
        time.sleep(delay)


# ============================================================
# PIPELINE REPORTING
# ============================================================

def _safe_get(obj, attr, default=None):
    if obj is None:
        return default
    return getattr(obj, attr, default)


def _generate_pipeline_report(
    session_id: str,
    memory: AgentMemory,
    results: dict,
    total_duration: float
) -> dict:
    """Full pipeline report बनाओ"""

    if memory is None:
        logger.error("❌ Memory None है!")
        memory = AgentMemory()

    successful_agents = sum(1 for r in results.values() if r.success)
    failed_agents     = sum(1 for r in results.values() if not r.success)

    ig_success = _safe_get(memory, 'ig_success', False)
    fb_success = _safe_get(memory, 'fb_success', False)

    if ig_success and fb_success:
        status = "success"
    elif ig_success or fb_success:
        status = "partial"
    else:
        status = "error"

    report = {
        "session_id":     session_id,
        "status":         status,
        "post_type":      _safe_get(memory, 'post_type', 'image'),
        "is_recovery":    _safe_get(memory, 'is_recovery', False),
        "total_duration_seconds": round(total_duration, 2),
        "topic":          _safe_get(memory, 'topic', ''),
        "category":       _safe_get(memory, 'category', ''),
        "is_festival":    _safe_get(memory, 'is_festival', False),
        "festival_name":  _safe_get(memory, 'festival_name', ''),

        "publishing": {
            "instagram": {
                "success": ig_success,
                "post_id": _safe_get(memory, 'ig_post_id', '')
            },
            "facebook": {
                "success": fb_success,
                "post_id": _safe_get(memory, 'fb_post_id', '')
            }
        },

        "image": {
            "url":           _safe_get(memory, 'image_url', ''),
            "quality_score": _safe_get(memory, 'quality_score', 0),
            "regenerations": _safe_get(memory, 'regeneration_count', 0),
            "provider": (
                _safe_get(memory, 'image_metadata', {}) or {}
            ).get("provider", "unknown"),
            "cost_inr": (
                _safe_get(memory, 'image_metadata', {}) or {}
            ).get("estimated_cost_inr", 0)
        },

        "content": {
            "caption_length": len(_safe_get(memory, 'caption', '') or ''),
            "caption_style":  _safe_get(memory, 'caption_style', ''),
            "hashtag_count":  len((_safe_get(memory, 'hashtags', '') or '').split())
        },

        "agents": {
            name: {
                "success":  r.success,
                "duration": r.duration,
                "retries":  r.retries,
                "error":    r.error
            }
            for name, r in results.items()
        },

        "stats": {
            "successful_agents": successful_agents,
            "failed_agents":     failed_agents,
            "total_agents":      len(results),
            "success_rate": round(
                (successful_agents / len(results)) * 100, 1
            ) if results else 0
        },

        "errors": _safe_get(memory, 'errors', []) or []
    }

    return report


def _log_pipeline_summary(report: dict):
    """सुंदर pipeline summary"""

    logger.info("")
    log_header(logger, "पाइपलाइन का अंतिम रिपोर्ट", char="═")

    status_emoji = {
        "success": "✅",
        "partial": "⚠️ ",
        "error":   "❌"
    }.get(report["status"], "❓")

    status_hindi = {
        "success": "पूर्ण सफल",
        "partial": "आंशिक सफल",
        "error":   "विफल"
    }.get(report["status"], "अज्ञात")

    logger.info(f"{status_emoji} स्थिति  : {status_hindi}")
    logger.info(f"📋 प्रकार  : {report.get('post_type', 'image').upper()}")
    if report.get('is_recovery'):
        logger.info(f"♻️  Recovery: हां")
    logger.info(f"🆔 सेशन   : {report['session_id']}")
    logger.info(f"⏱️  समय    : {report['total_duration_seconds']}s")
    logger.info("")

    logger.info("📌 CONTENT:")
    logger.info(f"   विषय     : {report['topic']}")
    logger.info(f"   श्रेणी    : {report['category']}")
    if report['is_festival']:
        logger.info(f"   त्यौहार  : {report['festival_name']} 🎉")
    logger.info("")

    img = report['image']
    logger.info("🎨 IMAGE:")
    logger.info(f"   Provider  : {img['provider']}")
    logger.info(f"   Quality   : {img['quality_score']}/100")
    logger.info(f"   Regenerate: {img['regenerations']}")
    logger.info(f"   Cost      : ₹{img['cost_inr']}")
    logger.info("")

    content = report['content']
    logger.info("📝 CONTENT:")
    logger.info(f"   Caption style : {content['caption_style']}")
    logger.info(f"   Caption length: {content['caption_length']} chars")
    logger.info(f"   Hashtags      : {content['hashtag_count']}")
    logger.info("")

    pub = report['publishing']
    logger.info("📱 PUBLISHING:")
    ig_status = "✅" if pub['instagram']['success'] else "❌"
    fb_status = "✅" if pub['facebook']['success'] else "❌"
    logger.info(f"   {ig_status} Instagram: {pub['instagram']['post_id'] or 'विफल'}")
    logger.info(f"   {fb_status} Facebook : {pub['facebook']['post_id'] or 'विफल'}")
    logger.info("")

    stats = report['stats']
    logger.info("🤖 AGENTS:")
    logger.info(
        f"   Success Rate: {stats['success_rate']}% "
        f"({stats['successful_agents']}/{stats['total_agents']})"
    )

    for name, agent_info in report['agents'].items():
        emoji      = "✅" if agent_info['success'] else "❌"
        retry_info = (
            f" (retries: {agent_info['retries']})"
            if agent_info['retries'] > 0 else ""
        )
        logger.info(f"   {emoji} {name:15} : {agent_info['duration']}s{retry_info}")

    if report['errors']:
        logger.info("")
        logger.info("⚠️  ERRORS:")
        for err in report['errors']:
            logger.info(f"   • [{err['agent']}] {err['error'][:80]}")

    log_header(logger, "रिपोर्ट पूर्ण", char="═")


# ============================================================
# 🆕 RECOVERY CHECK
# ============================================================

def _check_and_load_recovery(post_type: str = "carousel") -> Optional[AgentMemory]:
    """
    पुराने अधूरे session को detect करो और memory में load करो।
    Returns: Memory object अगर recovery मिली, None अगर नहीं।

    Args:
        post_type: "image" | "carousel" | "reel"
    """
    logger.info("")
    logger.info("🔍 पुराने अधूरे काम की जांच कर रहे हैं...")

    # पहले पुराने cleanup
    cleanup_old_recoveries()

    # Pending session ढूंढो
    state = find_pending_recovery(post_type=post_type)

    if not state:
        logger.info("✅ कोई अधूरा काम नहीं है, नया शुरू करते हैं")
        return None

    # Display करो
    display_pending_recovery(state)

    # Memory में restore करो
    memory = AgentMemory()
    memory.restore_from_recovery(
        state=state,
        slides_bytes=state.get("slides_bytes", {})
    )

    logger.info(f"♻️  पुराने डेटा से आगे बढ़ रहे हैं...")
    logger.info(f"    Session: {memory.session_id}")
    logger.info(f"    Stage  : {memory.resumed_from_stage}")

    return memory


# ============================================================
# MAIN PIPELINE — SINGLE IMAGE (Morning)
# ============================================================

def run_pipeline() -> dict:
    """
    Single-image pipeline (Morning 8AM)
    """
    memory        = AgentMemory()
    memory.post_type = "image"
    session_id    = memory.session_id
    start_time    = datetime.now()

    logger.info("")
    log_header(logger, "🚀 DIVINE AUTO POSTER — SINGLE IMAGE", char="═")
    logger.info(f"📅 समय    : {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"🆔 सेशन   : {session_id}")
    log_header(logger, "", char="═")
    logger.info("")

    agent_results = {}

    try:
        # Health check
        is_healthy, issues = _health_check()
        if not is_healthy and len(issues) > 3:
            raise Exception(f"System health खराब: {len(issues)} समस्याएं")

        # Planner
        memory, result = _execute_agent(
            "planner", planner_agent.run, memory,
            critical=True, max_retries=2
        )
        agent_results["planner"] = result

        # Research
        memory, result = _execute_agent(
            "research", research_agent.run, memory,
            critical=False, max_retries=2
        )
        agent_results["research"] = result

        # Prompt
        memory, result = _execute_agent(
            "prompt", prompt_agent.run, memory,
            critical=False, max_retries=2
        )
        agent_results["prompt"] = result

        # Image + Quality
        memory, img_result, qual_result = _execute_image_quality_loop(memory)
        agent_results["image"]   = img_result
        agent_results["quality"] = qual_result

        # Caption
        memory, result = _execute_agent(
            "caption", caption_agent.run, memory,
            critical=False, max_retries=2
        )
        agent_results["caption"] = result

        # Hashtag
        memory, result = _execute_agent(
            "hashtag", hashtag_agent.run, memory,
            critical=False, max_retries=1
        )
        agent_results["hashtag"] = result

        # Human delay
        _human_like_delay()

        # Publisher
        memory, result = _execute_agent(
            "publisher", publisher_agent.run, memory,
            critical=False, max_retries=1
        )
        agent_results["publisher"] = result

        if not memory.ig_success and not memory.fb_success:
            logger.error("❌ CRITICAL: दोनों platforms विफल!")
            memory.add_error("publisher", "दोनों platforms विफल")

        # Save to DB
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        memory.duration_seconds = duration

        try:
            post_db_id = save_post({
                "post_date":        start_time.isoformat(),
                "topic":            memory.topic,
                "category":         memory.category,
                "image_style":      memory.image_style,
                "image_url":        memory.image_url,
                "caption":          memory.caption,
                "hashtags":         memory.hashtags,
                "ig_post_id":       memory.ig_post_id,
                "fb_post_id":       memory.fb_post_id,
                "ig_success":       memory.ig_success,
                "fb_success":       memory.fb_success,
                "duration_seconds": duration,
                "post_type":        "image"
            })
            memory.post_id = post_db_id
            log_success(logger, f"DB में save (ID: {post_db_id})")
        except Exception as e:
            logger.error(f"❌ DB save विफल: {e}")
            post_db_id = 0

        # Analytics
        if post_db_id > 0:
            memory, result = _execute_agent(
                "analytics", analytics_agent.run, memory,
                critical=False, max_retries=1,
                post_db_id=post_db_id
            )
            agent_results["analytics"] = result

        # Report
        total_duration = (datetime.now() - start_time).total_seconds()
        report = _generate_pipeline_report(session_id, memory, agent_results, total_duration)
        _log_pipeline_summary(report)
        return report

    except Exception as e:
        logger.error("")
        log_header(logger, "💥 पाइपलाइन गंभीर विफलता", char="═")
        logger.error(f"Error: {e}")
        logger.error(traceback.format_exc())
        log_header(logger, "", char="═")

        total_duration = (datetime.now() - start_time).total_seconds()

        return {
            "session_id": session_id,
            "status":     "error",
            "post_type":  "image",
            "message":    str(e),
            "topic":      _safe_get(memory, 'topic', ''),
            "duration":   round(total_duration, 2),
            "errors":     _safe_get(memory, 'errors', []) or [],
        }


# ============================================================
# 🎠 CAROUSEL PIPELINE (Evening 8PM) — WITH RECOVERY
# ============================================================

def run_carousel_pipeline(force_new: bool = False) -> dict:
    """
    Carousel Pipeline (Evening 8PM)

    Args:
        force_new: True तो recovery skip करो, नया start करो
    """
    start_time = datetime.now()

    logger.info("")
    log_header(logger, "🎠 DIVINE AUTO POSTER — CAROUSEL", char="═")
    logger.info(f"📅 समय    : {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    log_header(logger, "", char="═")

    # ═══════════════════════════════════════════
    # 🆕 RECOVERY CHECK
    # ═══════════════════════════════════════════
    memory = None

    if not force_new:
        memory = _check_and_load_recovery(post_type="carousel")

    # अगर recovery नहीं मिली — नया memory
    if memory is None:
        memory = AgentMemory()
        memory.post_type = "carousel"

    session_id = memory.session_id
    logger.info(f"🆔 सेशन   : {session_id}")
    logger.info("")

    agent_results = {}

    try:
        # Health check
        is_healthy, issues = _health_check()
        if not is_healthy and len(issues) > 3:
            raise Exception(f"System health खराब: {len(issues)} समस्याएं")

        # ═══════════════════════════════════════════
        # STEP 1: PLANNER (recovery में skip)
        # ═══════════════════════════════════════════
        if memory.is_recovery and memory.topic:
            logger.info("⏭️  Planner skip — पुराना topic use कर रहे हैं")
            logger.info(f"   विषय: {memory.topic[:60]}")

            fake_result = AgentExecutionResult("planner")
            fake_result.success = True
            fake_result.duration = 0.0
            agent_results["planner"] = fake_result
        else:
            memory, result = _execute_agent(
                "planner", planner_agent.run, memory,
                critical=True, max_retries=2
            )
            agent_results["planner"] = result

            # Checkpoint after planner
            save_checkpoint(
                session_id=memory.session_id,
                stage="TOPIC_SELECTED",
                data={
                    "topic":       memory.topic,
                    "category":    memory.category,
                    "post_type":   "carousel",
                    "is_festival": memory.is_festival,
                    "festival_name": memory.festival_name,
                }
            )

        # ═══════════════════════════════════════════
        # STEP 2: CAROUSEL AGENT (auto-detects recovery)
        # ═══════════════════════════════════════════
        memory, result = _execute_agent(
            "carousel", carousel_agent.run, memory,
            critical=True, max_retries=1
        )
        agent_results["carousel"] = result

        # ═══════════════════════════════════════════
        # STEP 3: PUBLISHER (auto-detects recovery)
        # ═══════════════════════════════════════════
        _human_like_delay()

        memory, result = _execute_agent(
            "publisher", publisher_agent.run, memory,
            critical=False, max_retries=1
        )
        agent_results["publisher"] = result

        # ═══════════════════════════════════════════
        # STEP 4: SAVE TO DB
        # ═══════════════════════════════════════════
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        try:
            first_slide_url = ""
            if memory.carousel_slides:
                first_slide_url = memory.carousel_slides[0].get("image_url", "")

            post_db_id = save_post({
                "post_date":        start_time.isoformat(),
                "topic":            memory.topic,
                "category":         memory.category,
                "image_style":      "carousel_premium",
                "image_url":        first_slide_url,
                "caption":          memory.carousel_caption,
                "hashtags":         memory.hashtags,
                "ig_post_id":       memory.carousel_ig_post_id,
                "fb_post_id":       memory.carousel_fb_post_id,
                "ig_success":       memory.carousel_ig_success,
                "fb_success":       memory.carousel_fb_success,
                "duration_seconds": duration,
                "post_type":        "carousel"
            })
            log_success(logger, f"Carousel DB में save (ID: {post_db_id})")

        except Exception as e:
            logger.error(f"❌ DB save विफल: {e}")
            post_db_id = 0

        # ═══════════════════════════════════════════
        # STEP 5: ANALYTICS
        # ═══════════════════════════════════════════
        if post_db_id > 0:
            memory, result = _execute_agent(
                "analytics", analytics_agent.run, memory,
                critical=False, max_retries=1,
                post_db_id=post_db_id
            )
            agent_results["analytics"] = result

        # ═══════════════════════════════════════════
        # SUMMARY
        # ═══════════════════════════════════════════
        total_duration = (datetime.now() - start_time).total_seconds()

        successful_slides = sum(
            1 for s in (memory.carousel_slides or [])
            if s.get("image_bytes")
        )

        if memory.carousel_ig_success and memory.carousel_fb_success:
            status = "success"
        elif memory.carousel_ig_success or memory.carousel_fb_success:
            status = "partial"
        else:
            status = "error"

        status_hindi = {
            "success": "पूर्ण सफल ✅",
            "partial": "आंशिक सफल ⚠️",
            "error":   "विफल ❌"
        }.get(status, "अज्ञात")

        logger.info("")
        log_header(logger, "🎠 CAROUSEL पाइपलाइन का सारांश", char="═")
        logger.info(f"स्थिति       : {status_hindi}")
        if memory.is_recovery:
            savings = calculate_savings(memory.resumed_from_stage)
            logger.info(f"♻️  Recovery : हां (Stage: {memory.resumed_from_stage})")
            logger.info(f"💰 पैसे बचे  : ₹{savings['money_saved_inr']}")
            logger.info(f"⏱️  समय बचा  : ~{savings['time_saved_min']} मिनट")
        logger.info(f"📌 विषय      : {memory.topic[:60]}")
        logger.info(f"📂 श्रेणी     : {memory.category}")
        logger.info(f"🖼️  स्लाइड्स   : {successful_slides}/5 बनी")
        logger.info("")
        logger.info("📱 PUBLISHING:")
        logger.info(
            f"   {'✅' if memory.carousel_ig_success else '❌'} "
            f"Instagram Carousel: "
            f"{memory.carousel_ig_post_id or 'विफल'}"
        )
        logger.info(
            f"   {'✅' if memory.carousel_fb_success else '❌'} "
            f"Facebook Album    : "
            f"{memory.carousel_fb_post_id or 'विफल'}"
        )
        logger.info("")
        logger.info("🤖 AGENTS:")
        for name, r in agent_results.items():
            emoji = "✅" if r.success else "❌"
            logger.info(f"   {emoji} {name:15} : {r.duration}s")
        logger.info(f"⏱️  कुल समय    : {round(total_duration, 1)}s")
        log_header(logger, "सारांश पूर्ण", char="═")

        return {
            "session_id":       session_id,
            "status":           status,
            "post_type":        "carousel",
            "is_recovery":      memory.is_recovery,
            "topic":            memory.topic,
            "category":         memory.category,
            "slides_generated": successful_slides,
            "ig_success":       memory.carousel_ig_success,
            "ig_post_id":       memory.carousel_ig_post_id,
            "fb_success":       memory.carousel_fb_success,
            "fb_post_id":       memory.carousel_fb_post_id,
            "duration":         round(total_duration, 1),
            "agent_results": {
                name: {
                    "success":  r.success,
                    "duration": r.duration,
                    "error":    r.error
                }
                for name, r in agent_results.items()
            }
        }

    except Exception as e:
        logger.error("")
        log_header(logger, "💥 CAROUSEL पाइपलाइन विफल", char="═")
        logger.error(f"Error: {e}")
        logger.error(traceback.format_exc())
        log_header(logger, "", char="═")

        total_duration = (datetime.now() - start_time).total_seconds()

        return {
            "session_id": session_id,
            "status":     "error",
            "post_type":  "carousel",
            "message":    str(e),
            "topic":      _safe_get(memory, 'topic', ''),
            "duration":   round(total_duration, 2),
            "errors":     _safe_get(memory, 'errors', []) or []
        }


# ============================================================
# 🆕 V2: REEL PIPELINE (1 PM IST) — WITH RECOVERY
# ============================================================

def run_reel_pipeline(force_new: bool = False) -> dict:
    """
    🎬 Reel Pipeline (1 PM IST daily)

    Flow:
    1. Health check
    2. Recovery check (post_type="reel")
    3. Planner → Research (existing)
    4. Reel Agent (story + fact_check + scenes + prompts)
    5. Image generation for 6 scenes (quality checked)
    6. TTS voice generation
    7. Subtitle generation
    8. Video building (Ken Burns + transitions + music + subtitles)
    9. Upload to GCS
    10. Caption + Hashtag (existing agents with reel awareness)
    11. Publisher (IG Reel + FB Reel + YouTube Short)
    12. Analytics + DB save

    Args:
        force_new: True तो recovery skip करो

    Returns:
        Report dict with success status, IDs, timing
    """
    start_time = datetime.now()

    logger.info("")
    log_header(logger, "🎬 DIVINE AUTO POSTER — REEL", char="═")
    logger.info(f"📅 समय    : {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    log_header(logger, "", char="═")

    # ═══════════════════════════════════════════
    # 🚨 DEPENDENCY CHECK (Phase 4-7 modules)
    # ═══════════════════════════════════════════

    missing_modules = []

    if not REEL_AGENT_AVAILABLE:
        missing_modules.append("reel_agent (Phase 2)")

    if not TTS_AVAILABLE:
        missing_modules.append("tts_engine + subtitle_generator (Phase 4)")

    if not VIDEO_BUILDER_AVAILABLE:
        missing_modules.append("video_builder (Phase 5)")

    if not REEL_ENGINE_AVAILABLE:
        missing_modules.append("reel_engine (Phase 6)")

    if not UPLOAD_VIDEO_AVAILABLE:
        missing_modules.append("gcs_helper.upload_video (Phase 6)")

    if missing_modules:
        error_msg = (
            f"⚠️  Reel pipeline requires missing modules:\n" +
            "\n".join([f"   • {m}" for m in missing_modules]) +
            "\n\n📋 Complete missing phases before running reel pipeline."
        )
        logger.error(error_msg)
        return {
            "session_id": "",
            "status":     "error",
            "post_type":  "reel",
            "message":    "Missing dependencies",
            "missing_modules": missing_modules,
            "duration":   0,
        }

    # ═══════════════════════════════════════════
    # RECOVERY CHECK
    # ═══════════════════════════════════════════
    memory = None

    if not force_new:
        memory = _check_and_load_recovery(post_type="reel")

    # अगर recovery नहीं मिली — नया memory
    if memory is None:
        memory = AgentMemory()
        memory.post_type = "reel"

    session_id = memory.session_id
    logger.info(f"🆔 सेशन   : {session_id}")
    logger.info("")

    agent_results = {}

    try:
        # Health check
        is_healthy, issues = _health_check()
        if not is_healthy and len(issues) > 3:
            raise Exception(f"System health खराब: {len(issues)} समस्याएं")

        # ═══════════════════════════════════════════
        # STEP 1: PLANNER (existing, recovery aware)
        # ═══════════════════════════════════════════
        if memory.is_recovery and memory.topic:
            logger.info("⏭️  Planner skip — पुराना topic use कर रहे हैं")
            logger.info(f"   विषय: {memory.topic[:60]}")

            fake_result = AgentExecutionResult("planner")
            fake_result.success = True
            fake_result.duration = 0.0
            agent_results["planner"] = fake_result
        else:
            memory, result = _execute_agent(
                "planner", planner_agent.run, memory,
                critical=True, max_retries=2
            )
            agent_results["planner"] = result

            # Checkpoint after planner
            save_checkpoint(
                session_id=memory.session_id,
                stage="TOPIC_SELECTED",
                data={
                    "topic":       memory.topic,
                    "category":    memory.category,
                    "post_type":   "reel",
                    "is_festival": memory.is_festival,
                    "festival_name": memory.festival_name,
                }
            )

        # ═══════════════════════════════════════════
        # STEP 2: RESEARCH (existing)
        # ═══════════════════════════════════════════
        memory, result = _execute_agent(
            "research", research_agent.run, memory,
            critical=False, max_retries=2
        )
        agent_results["research"] = result

        # ═══════════════════════════════════════════
        # STEP 3: REEL ENGINE (MASTER — Phase 6)
        # ═══════════════════════════════════════════
        # This handles: story + fact_check + scenes + images + voice + subtitles + video
        logger.info("🎬 Running reel_engine.build_reel()...")

        try:
            reel_result = reel_engine.build_reel(
                topic=memory.topic,
                category=memory.category,
                session_id=memory.session_id,
                resume_state=None if not memory.is_recovery else {
                    "stage": memory.resumed_from_stage,
                    "data": memory.to_recovery_dict(),
                    "slides_bytes": {},
                    "voice_bytes": memory.reel_voice_bytes,
                    "subtitle_srt": memory.reel_subtitle_srt,
                }
            )

            if not reel_result.get("success"):
                raise Exception(
                    f"Reel engine failed: {reel_result.get('error', 'Unknown')}"
                )

            # Update memory with reel_engine results
            memory.reel_story = reel_result.get("story", memory.reel_story)
            memory.reel_scenes = reel_result.get("scenes", memory.reel_scenes)
            memory.reel_voice_bytes = reel_result.get("voice_bytes", memory.reel_voice_bytes)
            memory.reel_voice_duration = reel_result.get("voice_duration", memory.reel_voice_duration)
            memory.reel_subtitle_srt = reel_result.get("subtitle_srt", memory.reel_subtitle_srt)
            memory.reel_video_bytes = reel_result.get("video_bytes", memory.reel_video_bytes)
            memory.reel_video_path = reel_result.get("video_path", memory.reel_video_path)
            memory.reel_duration_seconds = reel_result.get("duration", memory.reel_duration_seconds)
            memory.reel_video_size_mb = reel_result.get("size_mb", memory.reel_video_size_mb)
            memory.reel_music_file = reel_result.get("music_file", memory.reel_music_file)

            fake_result = AgentExecutionResult("reel_engine")
            fake_result.success = True
            fake_result.duration = reel_result.get("build_time", 0)
            agent_results["reel_engine"] = fake_result

            logger.info(f"✅ Reel engine done: {memory.reel_duration_seconds}s video")

        except Exception as e:
            logger.error(f"❌ Reel engine failed: {e}")
            fake_result = AgentExecutionResult("reel_engine")
            fake_result.success = False
            fake_result.error = str(e)
            agent_results["reel_engine"] = fake_result
            raise

        # ═══════════════════════════════════════════
        # STEP 4: UPLOAD VIDEO TO GCS
        # ═══════════════════════════════════════════
        if not memory.reel_video_url:
            logger.info("☁️  Uploading video to GCS...")

            try:
                if not memory.reel_video_bytes and memory.reel_video_path:
                    # Read bytes from path
                    with open(memory.reel_video_path, 'rb') as f:
                        memory.reel_video_bytes = f.read()

                video_url = upload_video(
                    video_bytes=memory.reel_video_bytes,
                    folder="reels"
                )
                memory.reel_video_url = video_url
                logger.info(f"✅ Video uploaded: {video_url}")

                # Checkpoint
                save_checkpoint(
                    session_id=memory.session_id,
                    stage="REEL_VIDEO_UPLOADED",
                    data=memory.to_recovery_dict()
                )

            except Exception as e:
                logger.error(f"❌ Video upload failed: {e}")
                raise

              # ═══════════════════════════════════════════
        # STEP 5: CAPTION (existing agent, reel-aware)
        # ═══════════════════════════════════════════
        memory, result = _execute_agent(
            "caption", caption_agent.run, memory,
            critical=False, max_retries=2
        )
        agent_results["caption"] = result

        # ═══════════════════════════════════════════
        # 🆕 STEP 5.5: SEO AGENT (optimize for all platforms)
        # ═══════════════════════════════════════════
        try:
            from agents.seo_agent import run as run_seo
            memory, result = _execute_agent(
                "seo", run_seo, memory,
                critical=False, max_retries=1
            )
            agent_results["seo"] = result
        except ImportError:
            logger.warning("⚠️  SEO agent not available")

        # ═══════════════════════════════════════════
        # STEP 6: HASHTAG (existing agent, reel-aware)
        # ═══════════════════════════════════════════
        memory, result = _execute_agent(
            "hashtag", hashtag_agent.run, memory,
            critical=False, max_retries=1
        )
        agent_results["hashtag"] = result

        # ═══════════════════════════════════════════
        # STEP 7: PUBLISHER (extended for reels)
        # ═══════════════════════════════════════════
        _human_like_delay()

        memory, result = _execute_agent(
            "publisher", publisher_agent.run, memory,
            critical=False, max_retries=1
        )
        agent_results["publisher"] = result

        # ═══════════════════════════════════════════
        # STEP 8: SAVE TO DB
        # ═══════════════════════════════════════════
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        try:
            post_db_id = save_post({
                "post_date":              start_time.isoformat(),
                "topic":                  memory.topic,
                "category":               memory.category,
                "image_style":            memory.image_style,
                "image_url":              memory.reel_video_url,  # video URL as image_url for reel
                "caption":                memory.caption,
                "hashtags":               memory.hashtags,
                "ig_post_id":             memory.reel_ig_post_id or memory.ig_post_id,
                "fb_post_id":             memory.reel_fb_post_id or memory.fb_post_id,
                "ig_success":             memory.reel_ig_success or memory.ig_success,
                "fb_success":             memory.reel_fb_success or memory.fb_success,
                "duration_seconds":       duration,
                # 🆕 Reel-specific fields
                "post_type":              "reel",
                "video_url":              memory.reel_video_url,
                "yt_post_id":             memory.reel_yt_video_id,
                "yt_success":             memory.reel_yt_success,
                "reel_duration_seconds":  memory.reel_duration_seconds,
                "reel_scenes_count":      len(memory.reel_scenes)
            })
            memory.post_id = post_db_id
            log_success(logger, f"Reel DB में save (ID: {post_db_id})")

        except Exception as e:
            logger.error(f"❌ DB save विफल: {e}")
            post_db_id = 0

        # ═══════════════════════════════════════════
        # STEP 9: ANALYTICS
        # ═══════════════════════════════════════════
        if post_db_id > 0:
            memory, result = _execute_agent(
                "analytics", analytics_agent.run, memory,
                critical=False, max_retries=1,
                post_db_id=post_db_id
            )
            agent_results["analytics"] = result

        # ═══════════════════════════════════════════
        # SUMMARY
        # ═══════════════════════════════════════════
        total_duration = (datetime.now() - start_time).total_seconds()

        # Determine overall status (3 platforms now)
        ig_ok = memory.reel_ig_success
        fb_ok = memory.reel_fb_success
        yt_ok = memory.reel_yt_success

        success_count = sum([ig_ok, fb_ok, yt_ok])

        if success_count == 3:
            status = "success"
        elif success_count >= 1:
            status = "partial"
        else:
            status = "error"

        status_hindi = {
            "success": "पूर्ण सफल (3/3) ✅",
            "partial": f"आंशिक सफल ({success_count}/3) ⚠️",
            "error":   "विफल ❌"
        }.get(status, "अज्ञात")

        logger.info("")
        log_header(logger, "🎬 REEL पाइपलाइन का सारांश", char="═")
        logger.info(f"स्थिति       : {status_hindi}")
        if memory.is_recovery:
            savings = calculate_savings(memory.resumed_from_stage)
            logger.info(f"♻️  Recovery : हां (Stage: {memory.resumed_from_stage})")
            logger.info(f"💰 पैसे बचे  : ₹{savings['money_saved_inr']}")
            logger.info(f"⏱️  समय बचा  : ~{savings['time_saved_min']} मिनट")
        logger.info(f"📌 विषय      : {memory.topic[:60]}")
        logger.info(f"📂 श्रेणी     : {memory.category}")
        logger.info(f"🎬 Video      : {memory.reel_duration_seconds}s, {memory.reel_video_size_mb}MB")
        logger.info(f"🎵 Music      : {memory.reel_music_file or 'None'}")
        logger.info(f"🖼️  Scenes    : {len(memory.reel_scenes)}")
        logger.info("")
        logger.info("📱 PUBLISHING:")
        logger.info(
            f"   {'✅' if ig_ok else '❌'} Instagram Reel: "
            f"{memory.reel_ig_post_id or 'विफल'}"
        )
        logger.info(
            f"   {'✅' if fb_ok else '❌'} Facebook Reel : "
            f"{memory.reel_fb_post_id or 'विफल'}"
        )
        logger.info(
            f"   {'✅' if yt_ok else '❌'} YouTube Short : "
            f"{memory.reel_yt_video_id or 'विफल'}"
        )
        logger.info("")
        logger.info("🤖 AGENTS:")
        for name, r in agent_results.items():
            emoji = "✅" if r.success else "❌"
            logger.info(f"   {emoji} {name:15} : {r.duration}s")
        logger.info(f"⏱️  कुल समय    : {round(total_duration, 1)}s ({round(total_duration/60, 1)} min)")
        log_header(logger, "सारांश पूर्ण", char="═")

        return {
            "session_id":       session_id,
            "status":           status,
            "post_type":        "reel",
            "is_recovery":      memory.is_recovery,
            "topic":            memory.topic,
            "category":         memory.category,
            "video_url":        memory.reel_video_url,
            "video_size_mb":    memory.reel_video_size_mb,
            "video_duration":   memory.reel_duration_seconds,
            "ig_success":       ig_ok,
            "ig_post_id":       memory.reel_ig_post_id,
            "fb_success":       fb_ok,
            "fb_post_id":       memory.reel_fb_post_id,
            "yt_success":       yt_ok,
            "yt_video_id":      memory.reel_yt_video_id,
            "duration":         round(total_duration, 1),
            "agent_results": {
                name: {
                    "success":  r.success,
                    "duration": r.duration,
                    "error":    r.error
                }
                for name, r in agent_results.items()
            }
        }

    except Exception as e:
        logger.error("")
        log_header(logger, "💥 REEL पाइपलाइन विफल", char="═")
        logger.error(f"Error: {e}")
        logger.error(traceback.format_exc())
        log_header(logger, "", char="═")

        total_duration = (datetime.now() - start_time).total_seconds()

        return {
            "session_id": session_id,
            "status":     "error",
            "post_type":  "reel",
            "message":    str(e),
            "topic":      _safe_get(memory, 'topic', ''),
            "duration":   round(total_duration, 2),
            "errors":     _safe_get(memory, 'errors', []) or []
        }


# ============================================================
# 🆕 MANUAL RECOVERY COMMAND
# ============================================================

def run_recovery_only() -> dict:
    """
    सिर्फ pending recovery पूरी करो, नई कुछ मत करो

    V2 FIX: Reels के लिए pipeline call करता है (जो अंदर से recovery detect करता है),
    न कि सीधे publisher को — क्योंकि reels में video build + upload भी बचा हो सकता है।
    """
    logger.info("")
    log_header(logger, "♻️  RECOVERY ONLY MODE", char="═")
    logger.info("")

    # First check for reel recovery (video pipeline)
    reel_memory = _check_and_load_recovery(post_type="reel")

    if reel_memory is not None:
        logger.info(f"♻️  Reel recovery मिली — full pipeline चला रहे हैं...")
        logger.info(f"    Session: {reel_memory.session_id}")
        logger.info(f"    Stage  : {reel_memory.resumed_from_stage}")
        logger.info("")

        # Call full reel pipeline (it will auto-detect recovery and skip completed stages)
        try:
            result = run_reel_pipeline(force_new=False)

            status = result.get("status", "unknown")
            if status in ["success", "partial"]:
                return {
                    "status":       status,
                    "session_id":   result.get("session_id", ""),
                    "post_type":    "reel",
                    "ig_post_id":   result.get("ig_post_id", ""),
                    "fb_post_id":   result.get("fb_post_id", ""),
                    "yt_video_id":  result.get("yt_video_id", ""),
                    "video_url":    result.get("video_url", ""),
                    "topic":        result.get("topic", ""),
                    "duration":     result.get("duration", 0),
                }
            else:
                return {
                    "status":     "failed",
                    "session_id": result.get("session_id", ""),
                    "post_type":  "reel",
                    "message":    result.get("message", "Reel recovery विफल"),
                }
        except Exception as e:
            logger.error(f"Reel recovery विफल: {e}")
            return {
                "status": "error",
                "post_type": "reel",
                "message": str(e)
            }

    # Then check for carousel recovery
    carousel_memory = _check_and_load_recovery(post_type="carousel")

    if carousel_memory is not None:
        logger.info(f"♻️  Carousel recovery मिली — publisher directly call कर रहे हैं...")
        logger.info(f"    Session: {carousel_memory.session_id}")
        logger.info(f"    Stage  : {carousel_memory.resumed_from_stage}")
        logger.info("")

        # For carousel, publisher can handle it directly (existing behavior)
        try:
            carousel_memory = publisher_agent.run(carousel_memory)

            if carousel_memory.ig_success or carousel_memory.fb_success:
                return {
                    "status":     "success",
                    "session_id": carousel_memory.session_id,
                    "post_type":  "carousel",
                    "ig_post_id": carousel_memory.carousel_ig_post_id or carousel_memory.ig_post_id,
                    "fb_post_id": carousel_memory.carousel_fb_post_id or carousel_memory.fb_post_id,
                    "topic":      carousel_memory.topic,
                }
            else:
                return {
                    "status":     "failed",
                    "session_id": carousel_memory.session_id,
                    "post_type":  "carousel",
                    "message":    "Recovery भी विफल"
                }
        except Exception as e:
            logger.error(f"Carousel recovery विफल: {e}")
            return {
                "status": "error",
                "post_type": "carousel",
                "message": str(e)
            }

    # No recovery found
    logger.info("✅ कोई pending recovery नहीं")
    return {
        "status":  "no_recovery",
        "message": "कोई अधूरा काम नहीं मिला"
    }


# ============================================================
# 🆕 V2.1: SMART EVENING POST (Auto Reel OR Carousel)
# ============================================================

def run_evening_smart() -> dict:
    """
    🆕 V2.1: Smart evening post — automatically decides Reel OR Carousel.

    Logic:
    - Checks database: is today one of the 2 random carousel days?
    - If YES → runs carousel pipeline
    - If NO  → runs reel pipeline (Reel #2)

    Used by auto_evening.yml workflow (8 PM daily).
    """
    from core.database import (
        initialize_database,
        get_todays_content_type,
        get_carousel_days_this_week,
        DAY_NAMES
    )

    # 🆕 FIX: Initialize DB first (GitHub Actions has fresh environment)
    initialize_database()


    logger.info("")
    log_header(logger, "🌙 SMART EVENING POST (8 PM)", char="═")
    logger.info("")

    # Get current day info
    today = datetime.now()
    today_name = DAY_NAMES[today.weekday()]

    # Get this week's schedule
    schedule = get_carousel_days_this_week()

    logger.info(f"📅 आज का दिन    : {today_name}")
    logger.info(f"📅 इस हफ्ते के carousel दिन: {schedule['carousel_day_names']}")
    logger.info("")

    # Get content type for evening
    content_type = get_todays_content_type(time_slot="evening")

    logger.info(f"🎯 आज का content: {content_type.upper()}")
    logger.info("")

    # Route to appropriate pipeline
    if content_type == "carousel":
        logger.info("🎠 आज carousel का दिन है — carousel pipeline चला रहे हैं")
        logger.info("")

        result = run_carousel_pipeline(force_new=True)

        # Add smart routing info
        result["smart_routing"] = {
            "decision": "carousel",
            "reason": f"Today ({today_name}) is a carousel day",
            "carousel_days_this_week": schedule['carousel_day_names']
        }

        return result

    else:
        logger.info("🎬 आज reel का दिन है — reel #2 pipeline चला रहे हैं")
        logger.info("")

        result = run_reel_pipeline(force_new=True)

        # Add smart routing info
        result["smart_routing"] = {
            "decision": "reel",
            "reason": f"Today ({today_name}) is NOT a carousel day",
            "carousel_days_this_week": schedule['carousel_day_names']
        }

        return result
    
# ============================================================
# CLOUD FUNCTION ENTRY POINT
# ============================================================

@functions_framework.http
def auto_post(request):
    """
    Cloud Function HTTP entry point
    ?type=carousel → carousel pipeline
    ?type=reel     → 🆕 reel pipeline
    ?type=recover  → sirf recovery
    ?type=image    → single image (default)
    """
    try:
        post_type = "image"
        if request and hasattr(request, 'args'):
            post_type = request.args.get("type", "image").lower()

        if post_type == "carousel":
            result = run_carousel_pipeline()
        elif post_type == "reel":
            result = run_reel_pipeline()  # 🆕 V2
        elif post_type == "recover":
            result = run_recovery_only()
        else:
            result = run_pipeline()

        if result.get("status") == "success":
            status_code = 200
        elif result.get("status") == "partial":
            status_code = 206
        elif result.get("status") == "no_recovery":
            status_code = 204
        else:
            status_code = 500

        return result, status_code

    except Exception as e:
        logger.error(f"Cloud function crash: {e}")
        return {"status": "crash", "error": str(e)}, 500


# ============================================================
# CLI ENTRY POINT
# ============================================================

def _run_cli():
    """CLI mode"""
    import sys

    if len(sys.argv) > 1:
        command = sys.argv[1].lower()

        # ── TEST ─────────────────────────────────────────────
        if command == "test":
            logger.info("🧪 TEST MODE - Config Only")
            validate()
            config = get_config_summary()
            log_dict(logger, config.get("posting", {}), title="Posting Config")
            return

        # ── HEALTH ───────────────────────────────────────────
        elif command == "health":
            logger.info("🏥 HEALTH CHECK MODE")
            is_healthy, issues = _health_check()
            print(f"\n{'✅ HEALTHY' if is_healthy else '⚠️  ISSUES FOUND'}")
            if issues:
                for issue in issues:
                    print(f"   • {issue}")

            # 🆕 V2: Check reel dependencies
            print("\n🎬 REEL DEPENDENCIES:")
            print(f"   {'✅' if REEL_AGENT_AVAILABLE else '❌'} reel_agent (Phase 2)")
            print(f"   {'✅' if TTS_AVAILABLE else '❌'} tts_engine + subtitles (Phase 4)")
            print(f"   {'✅' if VIDEO_BUILDER_AVAILABLE else '❌'} video_builder (Phase 5)")
            print(f"   {'✅' if REEL_ENGINE_AVAILABLE else '❌'} reel_engine (Phase 6)")
            print(f"   {'✅' if UPLOAD_VIDEO_AVAILABLE else '❌'} upload_video (Phase 6)")
            return

        # ── CAROUSEL ─────────────────────────────────────────
        elif command == "carousel":
            logger.info("🎠 MANUAL CAROUSEL MODE")
            result = run_carousel_pipeline()

            status = result.get('status', 'unknown')
            status_hindi = {
                "success": "पूर्ण सफल",
                "partial": "आंशिक सफल",
                "error":   "विफल"
            }.get(status, status.upper())

            print(f"\n{'✅' if status == 'success' else '⚠️' if status == 'partial' else '❌'} "
                  f"Carousel: {status_hindi}")

            if result.get("is_recovery"):
                print("♻️  Recovery से पूरा हुआ!")

            if result.get("ig_post_id"):
                print(f"📸 IG Post: {result['ig_post_id']}")
            if result.get("fb_post_id"):
                print(f"📘 FB Post: {result['fb_post_id']}")

            sys.exit(0 if status in ["success", "partial"] else 2)

        # ── CAROUSEL FORCE NEW ───────────────────────────────
        elif command == "carousel-new":
            logger.info("🎠 FORCE NEW CAROUSEL (recovery skip)")
            result = run_carousel_pipeline(force_new=True)
            sys.exit(0 if result.get("status") in ["success", "partial"] else 2)

        # ── 🆕 V2: REEL ──────────────────────────────────────
        elif command == "reel":
            logger.info("🎬 MANUAL REEL MODE")
            result = run_reel_pipeline()

            status = result.get('status', 'unknown')
            status_hindi = {
                "success": "पूर्ण सफल",
                "partial": "आंशिक सफल",
                "error":   "विफल"
            }.get(status, status.upper())

            print(f"\n{'✅' if status == 'success' else '⚠️' if status == 'partial' else '❌'} "
                  f"Reel: {status_hindi}")

            if result.get("missing_modules"):
                print(f"\n⚠️  Missing modules:")
                for mod in result["missing_modules"]:
                    print(f"   • {mod}")

            if result.get("is_recovery"):
                print("♻️  Recovery से पूरा हुआ!")

            if result.get("video_url"):
                print(f"🎥 Video URL: {result['video_url']}")
            if result.get("ig_post_id"):
                print(f"📸 IG Reel: {result['ig_post_id']}")
            if result.get("fb_post_id"):
                print(f"📘 FB Reel: {result['fb_post_id']}")
            if result.get("yt_video_id"):
                print(f"📺 YT Short: https://youtube.com/shorts/{result['yt_video_id']}")

            sys.exit(0 if status in ["success", "partial"] else 2)

               # ── 🆕 V2: REEL FORCE NEW ────────────────────────────
        elif command == "reel-new":
            logger.info("🎬 FORCE NEW REEL (recovery skip)")
            result = run_reel_pipeline(force_new=True)
            sys.exit(0 if result.get("status") in ["success", "partial"] else 2)

        # ── 🆕 V2.1: SMART EVENING (Auto Reel OR Carousel) ───
        elif command == "evening-smart":
            logger.info("🌙 SMART EVENING MODE (Auto-detects Reel or Carousel)")
            result = run_evening_smart()

            status = result.get('status', 'unknown')
            routing = result.get('smart_routing', {})
            decision = routing.get('decision', 'unknown')

            print(f"\n🌙 Evening Decision: {decision.upper()}")
            print(f"📅 Reason: {routing.get('reason', 'N/A')}")

            if decision == "carousel":
                print(f"\n{'✅' if status == 'success' else '⚠️' if status == 'partial' else '❌'} "
                      f"Carousel: {status}")
                if result.get("ig_post_id"):
                    print(f"📸 IG: {result['ig_post_id']}")
                if result.get("fb_post_id"):
                    print(f"📘 FB: {result['fb_post_id']}")
            else:
                print(f"\n{'✅' if status == 'success' else '⚠️' if status == 'partial' else '❌'} "
                      f"Reel: {status}")
                if result.get("video_url"):
                    print(f"🎥 Video: {result['video_url']}")
                if result.get("ig_post_id"):
                    print(f"📸 IG Reel: {result['ig_post_id']}")
                if result.get("fb_post_id"):
                    print(f"📘 FB Reel: {result['fb_post_id']}")
                if result.get("yt_video_id"):
                    print(f"📺 YT Short: https://youtube.com/shorts/{result['yt_video_id']}")

            sys.exit(0 if status in ["success", "partial"] else 2)
        # ── 🆕 V3: ENGAGEMENT (Auto Comment Reply) ───────────
        elif command == "engage":
            logger.info("🤖 ENGAGEMENT MODE (Auto Comment Reply)")

            try:
                from engagement.engagement_agent import run as run_engagement
                result = run_engagement()

                status = result.get('status', 'unknown')
                print(f"\n🤖 Engagement: {status}")
                print(f"   Comments found : {result.get('comments_found', 0)}")
                print(f"   Replies posted : {result.get('replies_posted', 0)}")
                print(f"   Duration       : {result.get('duration', 0)}s")

                sys.exit(0 if status in ["success", "no_comments"] else 2)

            except ImportError as e:
                logger.error(f"❌ Engagement module not installed: {e}")
                print(f"\n❌ Missing module: {e}")
                sys.exit(2)
            except Exception as e:
                logger.error(f"❌ Engagement failed: {e}")
                print(f"\n❌ Error: {e}")
                sys.exit(2)

        # ── 🆕 V3: ENGAGEMENT STATS ──────────────────────────
        elif command == "engage-stats":
            logger.info("📊 ENGAGEMENT STATS")

            try:
                from engagement.engagement_agent import get_engagement_stats
                stats = get_engagement_stats()

                print(f"\n📊 ENGAGEMENT STATS:")
                print(f"   Total replied : {stats['total_replied']}")
                print(f"   Today replied : {stats['today_replied']}")
                print(f"   Pending       : {stats['pending']}")
                print(f"   Platforms     : {stats['platforms']}")

            except Exception as e:
                print(f"❌ Stats failed: {e}")
            return

               # ── 🆕 V4: POSTING INSIGHTS ──────────────────────────
        elif command == "insights":
            logger.info("📊 POSTING TIME INSIGHTS")
            from core.database import display_posting_insights
            display_posting_insights()
            return

        # ── 🆕 V2.1: SCHEDULE INFO ───────────────────────────
        elif command == "schedule":
    
            logger.info("📅 WEEKLY SCHEDULE INFO")
            from core.database import display_schedule
            display_schedule()
            return

        # ── RECOVERY ONLY ─────────────────────────────────────
        elif command == "recover":
            logger.info("♻️  RECOVERY ONLY MODE")
            result = run_recovery_only()

            status = result.get('status', 'unknown')
            if status == "success":
                print(f"\n✅ Recovery पूर्ण!")
                if result.get("ig_post_id"):
                    print(f"📸 IG: {result['ig_post_id']}")
                if result.get("fb_post_id"):
                    print(f"📘 FB: {result['fb_post_id']}")
                if result.get("yt_video_id"):
                    print(f"📺 YT: {result['yt_video_id']}")
            elif status == "no_recovery":
                print(f"\n✅ कोई pending recovery नहीं")
            else:
                print(f"\n❌ {result.get('message', 'Recovery विफल')}")

            sys.exit(0 if status in ["success", "no_recovery"] else 2)

        # ── RECOVERY STATS ────────────────────────────────────
        elif command == "recovery-stats":
            logger.info("📊 RECOVERY STATS")
            display_recovery_stats()
            return

        # ── RECOVERY CLEANUP ──────────────────────────────────
        elif command == "recovery-cleanup":
            logger.info("🧹 RECOVERY CLEANUP")
            deleted = cleanup_old_recoveries()
            print(f"\n🗑️  {deleted} पुराने recoveries हटाए गए")
            return

        # ── IMAGE ────────────────────────────────────────────
        elif command == "image":
            logger.info("🖼️  MANUAL IMAGE MODE")
            result = run_pipeline()
            sys.exit(0 if result["status"] == "success" else 2)

        # ── COST STATS ────────────────────────────────────────
        elif command == "cost":
            logger.info("💰 COST STATS")
            try:
                from utils.vertex_ai import log_session_stats, estimate_images_remaining

                print("\n" + "═" * 55)
                print("  💰 आज का खर्च और उपयोग")
                print("═" * 55)

                log_session_stats()

                remaining = estimate_images_remaining()
                print(f"\n💵 आज बचा हुआ बजट : ₹{remaining['daily_budget_left_inr']}")
                print(f"💵 महीने का बचा   : ₹{remaining['monthly_budget_left_inr']}")

                print(f"\n📷 आज कितनी images और बना सकते हैं:")
                print(f"   Premium (₹2.5): {remaining['images_remaining_today']['premium_2_5rs']}")
                print(f"   Balanced (₹1.5): {remaining['images_remaining_today']['balanced_1_5rs']}")
                print(f"   Fast (₹1.0)   : {remaining['images_remaining_today']['fast_1rs']}")

                # Read JSON directly for detailed breakdown
                import json
                from pathlib import Path
                from datetime import datetime as dt

                stats_file = Path("logs/vertex_usage.json")
                if stats_file.exists():
                    with open(stats_file, 'r') as f:
                        stats = json.load(f)

                    today = dt.now().strftime("%Y-%m-%d")
                    this_month = dt.now().strftime("%Y-%m")

                    print("\n" + "═" * 55)
                    print("  📊 विस्तृत रिपोर्ट")
                    print("═" * 55)

                    today_data = stats.get("daily", {}).get(today, {})
                    print(f"\n📅 आज ({today}):")
                    print(f"   ✅ सफल images  : {today_data.get('images', 0)}")
                    print(f"   ❌ विफल        : {today_data.get('failed', 0)}")
                    print(f"   💰 कुल खर्च    : ₹{today_data.get('cost', 0):.2f}")

                    month_data = stats.get("monthly", {}).get(this_month, {})
                    print(f"\n📆 इस महीने ({this_month}):")
                    print(f"   ✅ सफल images  : {month_data.get('images', 0)}")
                    print(f"   ❌ विफल        : {month_data.get('failed', 0)}")
                    print(f"   💰 कुल खर्च    : ₹{month_data.get('cost', 0):.2f}")

                    all_time = stats.get("all_time", {})
                    print(f"\n🏆 अब तक कुल:")
                    print(f"   ✅ सफल images  : {all_time.get('successful', 0)}")
                    print(f"   ❌ विफल        : {all_time.get('failed', 0)}")
                    print(f"   💰 कुल खर्च    : ₹{all_time.get('total_cost_inr', 0):.2f}")

                    if all_time.get('successful', 0) > 0:
                        avg = all_time.get('total_cost_inr', 0) / all_time.get('successful', 1)
                        print(f"   📊 Avg per image: ₹{avg:.2f}")

                print("\n" + "═" * 55 + "\n")

            except Exception as e:
                print(f"❌ Cost fetch विफल: {e}")
            return

        # ── HELP ─────────────────────────────────────────────
        elif command == "help":
            print("""
╔═══════════════════════════════════════════════════╗
║       DIVINE AUTO POSTER V2 — HELP                ║
╠═══════════════════════════════════════════════════╣
║  IMAGE COMMANDS:                                  ║
║  python main.py                → Single image     ║
║  python main.py image          → Single image     ║
║                                                   ║
║  CAROUSEL COMMANDS:                               ║
║  python main.py carousel       → With recovery    ║
║  python main.py carousel-new   → Skip recovery    ║
║                                                   ║
║  🆕 REEL COMMANDS (V2):                           ║
║  python main.py reel           → With recovery    ║
║  python main.py reel-new       → Skip recovery    ║
║                                                   ║
║  RECOVERY COMMANDS:                               ║
║  python main.py recover        → Complete pending ║
║  python main.py recovery-stats → Show status      ║
║  python main.py recovery-cleanup → Clean old      ║
║                                                   ║
║  🆕 V3 ENGAGEMENT (Auto Reply):                   ║
║  python main.py engage         → Auto reply bot   ║
║  python main.py engage-stats   → Reply stats      ║
║                                                   ║
║  🆕 V2.1 SMART SCHEDULING:                        ║
║  python main.py evening-smart  → 8PM auto route   ║
║  python main.py schedule       → Week's schedule  ║
║                                                   ║
║  UTILITIES:                                       ║
║  python main.py test           → Config test      ║
║  python main.py health         → Health + deps    ║
║  python main.py cost           → Cost stats       ║
║  python main.py help           → This screen      ║
╚═══════════════════════════════════════════════════╝
            """)
            return

    # Default: Single image
    result = run_pipeline()

    if result["status"] == "success":
        exit_code = 0
    elif result["status"] == "partial":
        exit_code = 1
    else:
        exit_code = 2

    import sys
    sys.exit(exit_code)


if __name__ == "__main__":
    _run_cli()
