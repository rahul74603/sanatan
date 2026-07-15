"""
Publisher Agent - Meta Platform Publisher (Production Grade)

Features:
- Single image posting (unchanged flow)
- Instagram Carousel + Facebook Album
- 🆕 V2: Reels (Instagram + Facebook + YouTube Shorts)
- 🆕 Recovery checkpoints (हर critical step पर save)
- 🆕 पूरी तरह हिंदी logs
- 🆕 URL reuse (images फिर upload नहीं) — media_id हमेशा fresh
- 🔧 FIX: Recovery में media_id reuse बंद (error 2207032 fix)
"""
import requests
import time
import random
import json as json_lib
from datetime import datetime
from typing import Optional

from core.memory import AgentMemory
from core.recovery_manager import save_checkpoint, delete_checkpoint
from utils.gcs_helper import upload_image
from config.settings import (
    INSTAGRAM_ACCOUNT_ID,
    FACEBOOK_PAGE_ID,
    ACCESS_TOKEN,
    META_API_VERSION,
    MAX_CAPTION_LENGTH,
    DELAY_BETWEEN_PLATFORMS_MIN,
    DELAY_BETWEEN_PLATFORMS_MAX,
    YOUTUBE_ENABLED,
)
from utils.logger import get_logger

logger = get_logger("publisher_agent")

META_BASE_URL = f"https://graph.facebook.com/{META_API_VERSION}"

MAX_RETRIES               = 3
INITIAL_RETRY_DELAY       = 3
MAX_RETRY_DELAY           = 30
REQUEST_TIMEOUT           = 30
INSTAGRAM_PROCESSING_WAIT = 5
CAROUSEL_ITEM_WAIT        = 3
RATE_LIMIT_CODES          = [4, 17, 32, 613]

# Instagram child media container expiry (seconds)
IG_CONTAINER_EXPIRY_SECONDS = 30 * 60  # 30 minutes

# 🆕 V2: Reel-specific settings
REEL_PROCESSING_WAIT_MIN  = 30   # IG needs longer for videos
REEL_PROCESSING_WAIT_MAX  = 120  # Sometimes 2 min for large videos
REEL_STATUS_CHECK_INTERVAL = 5   # Check every 5s
REEL_MAX_STATUS_CHECKS    = 30   # Max 30 checks (2.5 min total)


# ============================================================
# UTILITY FUNCTIONS
# ============================================================

def _validate_token() -> tuple:
    """Token valid है या नहीं check करो"""
    try:
        url = f"{META_BASE_URL}/me"
        response = requests.get(
            url,
            params={'access_token': ACCESS_TOKEN, 'fields': 'id,name'},
            timeout=REQUEST_TIMEOUT
        )
        if response.status_code == 200:
            data = response.json()
            logger.info(f"✅ Token सही है: {data.get('name', 'अज्ञात')}")
            return True, ""
        elif response.status_code == 401:
            return False, "Token expired या invalid है"
        else:
            return False, f"Token check विफल: HTTP {response.status_code}"
    except Exception as e:
        return False, f"Token check में error: {e}"


def _verify_image_url(image_url: str) -> bool:
    """Image URL accessible है या नहीं"""
    try:
        response = requests.head(image_url, timeout=10, allow_redirects=True)
        if response.status_code == 200:
            content_type = response.headers.get('Content-Type', '')
            if 'image' in content_type:
                logger.info(f"✅ Image URL सही है ({content_type})")
                return True
        return False
    except Exception as e:
        logger.warning(f"⚠️  Image URL check विफल: {e}")
        return False


def _verify_video_url(video_url: str) -> bool:
    """🆕 Video URL accessible है या नहीं"""
    try:
        response = requests.head(video_url, timeout=10, allow_redirects=True)
        if response.status_code == 200:
            content_type = response.headers.get('Content-Type', '')
            if 'video' in content_type:
                logger.info(f"✅ Video URL सही है ({content_type})")
                return True
        return False
    except Exception as e:
        logger.warning(f"⚠️  Video URL check विफल: {e}")
        return False


def _parse_meta_error(response: requests.Response) -> dict:
    try:
        error_data = response.json().get('error', {})
        return {
            "code":       error_data.get('code', 0),
            "type":       error_data.get('type', 'Unknown'),
            "message":    error_data.get('message', 'अज्ञात error'),
            "fbtrace_id": error_data.get('fbtrace_id', '')
        }
    except Exception:
        return {
            "code":    response.status_code,
            "type":    "HTTPError",
            "message": response.text[:200]
        }


def _is_rate_limited(error: dict) -> bool:
    return error.get('code') in RATE_LIMIT_CODES


def _human_like_delay(min_sec: int, max_sec: int, label: str = "रुक रहे हैं"):
    delay = random.randint(min_sec, max_sec)
    logger.info(f"⏳ {label}: {delay}s")
    time.sleep(delay)


def _is_media_id_expired(slide: dict) -> bool:
    """Check if saved media_id is expired"""
    media_id = slide.get("media_id", "")

    if not media_id or len(str(media_id)) < 5:
        return True

    created_at_str = slide.get("media_id_created_at", "")
    if not created_at_str:
        logger.warning(f"   ⚠️  media_id {media_id} का creation time नहीं पता → expire माना जाएगा")
        return True

    try:
        created_at = datetime.fromisoformat(created_at_str)
        age_seconds = (datetime.now() - created_at).total_seconds()

        if age_seconds > IG_CONTAINER_EXPIRY_SECONDS:
            logger.warning(f"   ⚠️  media_id {media_id} पुराना है ({age_seconds/60:.1f} मिनट) → fresh बनाएंगे")
            return True
        else:
            logger.info(f"   ✅ media_id {media_id} fresh है ({age_seconds/60:.1f} मिनट पुराना)")
            return False

    except Exception as e:
        logger.warning(f"   ⚠️  Creation time parse error: {e} → expire माना")
        return True


# ============================================================
# SINGLE IMAGE — INSTAGRAM (EXISTING - UNCHANGED)
# ============================================================

def _post_instagram_container(image_url: str, caption: str) -> dict:
    url = f"{META_BASE_URL}/{INSTAGRAM_ACCOUNT_ID}/media"
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            logger.info(f"📦 IG container बना रहे हैं (कोशिश {attempt}/{MAX_RETRIES})")
            response = requests.post(
                url,
                params={
                    'image_url':    image_url,
                    'caption':      caption,
                    'access_token': ACCESS_TOKEN
                },
                timeout=REQUEST_TIMEOUT
            )
            if response.status_code == 200:
                creation_id = response.json().get('id')
                if creation_id:
                    logger.info(f"✅ Container तैयार: {creation_id}")
                    return {"success": True, "creation_id": creation_id}
                raise Exception("Response में creation_id नहीं आया")

            error = _parse_meta_error(response)
            logger.warning(f"⚠️  Container विफल: {error['message']}")

            if _is_rate_limited(error):
                wait = min(MAX_RETRY_DELAY, INITIAL_RETRY_DELAY * (2 ** attempt))
                time.sleep(wait)
            elif attempt < MAX_RETRIES:
                time.sleep(INITIAL_RETRY_DELAY * attempt)
            else:
                return {"success": False, "error": error}

        except requests.Timeout:
            if attempt < MAX_RETRIES:
                time.sleep(5)
        except Exception as e:
            if attempt < MAX_RETRIES:
                time.sleep(INITIAL_RETRY_DELAY * attempt)
            else:
                return {"success": False, "error": {"message": str(e)}}

    return {"success": False, "error": {"message": "अधिकतम retries पार हुए"}}


def _publish_instagram_container(creation_id: str) -> dict:
    url = f"{META_BASE_URL}/{INSTAGRAM_ACCOUNT_ID}/media_publish"
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            logger.info(f"📤 IG पर publish कर रहे हैं (कोशिश {attempt}/{MAX_RETRIES})")
            response = requests.post(
                url,
                params={
                    'creation_id':  creation_id,
                    'access_token': ACCESS_TOKEN
                },
                timeout=REQUEST_TIMEOUT
            )
            if response.status_code == 200:
                post_id = response.json().get('id')
                if post_id:
                    logger.info(f"✅ IG पब्लिश हो गया: {post_id}")
                    return {"success": True, "post_id": post_id}

            error = _parse_meta_error(response)
            logger.warning(f"⚠️  Publish विफल: {error['message']}")

            if _is_rate_limited(error):
                wait = min(MAX_RETRY_DELAY, INITIAL_RETRY_DELAY * (2 ** attempt))
                time.sleep(wait)
            elif attempt < MAX_RETRIES:
                time.sleep(INITIAL_RETRY_DELAY * attempt)
            else:
                return {"success": False, "error": error}

        except Exception as e:
            if attempt < MAX_RETRIES:
                time.sleep(INITIAL_RETRY_DELAY * attempt)

    return {"success": False, "error": {"message": "अधिकतम retries पार"}}


def post_to_instagram(image_url: str, caption: str) -> dict:
    """Single image IG posting"""
    try:
        container_result = _post_instagram_container(image_url, caption)
        if not container_result["success"]:
            return {
                "success": False,
                "post_id": "",
                "error":   container_result["error"].get("message", "Container विफल")
            }

        logger.info(f"⏳ IG processing के लिए {INSTAGRAM_PROCESSING_WAIT}s रुकते हैं...")
        time.sleep(INSTAGRAM_PROCESSING_WAIT)

        publish_result = _publish_instagram_container(container_result["creation_id"])
        if publish_result["success"]:
            return {
                "success":      True,
                "post_id":      publish_result["post_id"],
                "container_id": container_result["creation_id"]
            }
        return {
            "success": False,
            "post_id": "",
            "error":   publish_result["error"].get("message", "Publish विफल")
        }
    except Exception as e:
        return {"success": False, "post_id": "", "error": str(e)}


# ============================================================
# SINGLE IMAGE — FACEBOOK (EXISTING - UNCHANGED)
# ============================================================

def post_to_facebook(image_url: str, caption: str) -> dict:
    """Facebook single photo post"""
    url = f"{META_BASE_URL}/{FACEBOOK_PAGE_ID}/photos"
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            logger.info(f"📤 Facebook पर पोस्ट कर रहे हैं (कोशिश {attempt}/{MAX_RETRIES})")
            response = requests.post(
                url,
                params={
                    'url':          image_url,
                    'caption':      caption,
                    'access_token': ACCESS_TOKEN
                },
                timeout=REQUEST_TIMEOUT
            )
            if response.status_code == 200:
                data    = response.json()
                post_id = data.get('post_id') or data.get('id')
                if post_id:
                    logger.info(f"✅ FB पब्लिश हो गया: {post_id}")
                    return {"success": True, "post_id": post_id}

            error = _parse_meta_error(response)
            logger.warning(f"⚠️  FB विफल: {error['message']}")

            if _is_rate_limited(error):
                time.sleep(min(MAX_RETRY_DELAY, INITIAL_RETRY_DELAY * (2 ** attempt)))
            elif attempt < MAX_RETRIES:
                time.sleep(INITIAL_RETRY_DELAY * attempt)
            else:
                return {"success": False, "post_id": "", "error": error["message"]}

        except requests.Timeout:
            if attempt < MAX_RETRIES:
                time.sleep(5)
        except Exception as e:
            if attempt < MAX_RETRIES:
                time.sleep(INITIAL_RETRY_DELAY * attempt)
            else:
                return {"success": False, "post_id": "", "error": str(e)}

    return {"success": False, "post_id": "", "error": "अधिकतम retries पार"}


# ============================================================
# CAPTION PREPARATION
# ============================================================

def _prepare_caption(caption: str, hashtags: str) -> str:
    separator    = "\n\n.\n.\n.\n\n"
    full_caption = f"{caption}{separator}{hashtags}"
    if len(full_caption) > MAX_CAPTION_LENGTH:
        available = MAX_CAPTION_LENGTH - len(hashtags) - len(separator) - 3
        if available > 100:
            full_caption = f"{caption[:available]}...{separator}{hashtags}"
        else:
            full_caption = full_caption[:MAX_CAPTION_LENGTH - 3] + "..."
        logger.warning(f"⚠️  Caption छोटा किया गया: {len(full_caption)} chars")
    return full_caption


def _log_publishing_report(memory: AgentMemory, ig_result: dict, fb_result: dict, duration: float):
    logger.info("┌─────────────────────────────────────────────┐")
    logger.info("│         पब्लिशिंग रिपोर्ट                    │")
    logger.info("├─────────────────────────────────────────────┤")
    logger.info(f"│ ⏱️  समय       : {duration:.1f}s")
    logger.info("├─────────────────────────────────────────────┤")
    ig_ok = ig_result["success"]
    fb_ok = fb_result["success"]
    logger.info(f"│ 📸 INSTAGRAM: {'✅ पब्लिश' if ig_ok else '❌ विफल'}")
    if ig_ok:
        logger.info(f"│    Post ID  : {ig_result['post_id']}")
    else:
        logger.info(f"│    Error    : {ig_result.get('error', 'अज्ञात')[:35]}")
    logger.info(f"│ 📘 FACEBOOK : {'✅ पब्लिश' if fb_ok else '❌ विफल'}")
    if fb_ok:
        logger.info(f"│    Post ID  : {fb_result['post_id']}")
    else:
        logger.info(f"│    Error    : {fb_result.get('error', 'अज्ञात')[:35]}")
    logger.info("└─────────────────────────────────────────────┘")


# ============================================================
# 🎠 CAROUSEL — INSTAGRAM HELPERS (EXISTING - UNCHANGED)
# ============================================================

def _upload_carousel_item(image_bytes: bytes) -> Optional[str]:
    try:
        url = upload_image(image_bytes)
        logger.info(f"   ☁️  Upload हुआ: {url[:60]}...")
        return url
    except Exception as e:
        logger.error(f"   ❌ Upload विफल: {e}")
        return None


def _create_ig_carousel_item(image_url: str) -> Optional[str]:
    url = f"{META_BASE_URL}/{INSTAGRAM_ACCOUNT_ID}/media"

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = requests.post(
                url,
                data={
                    'image_url':        image_url,
                    'is_carousel_item': 'true',
                    'access_token':     ACCESS_TOKEN
                },
                timeout=REQUEST_TIMEOUT
            )

            try:
                resp_json = response.json()
            except Exception:
                resp_json = {}

            if response.status_code == 200:
                media_id = resp_json.get('id')
                if media_id and media_id != "0" and len(str(media_id)) > 5:
                    logger.info(f"   ✅ Carousel item बना: {media_id}")
                    return media_id
                else:
                    logger.error(f"   ❌ गलत media_id मिला: '{media_id}'")

            error = _parse_meta_error(response)
            logger.warning(f"   ⚠️  Item नहीं बना: {error['message']} (code: {error.get('code')})")

            if attempt < MAX_RETRIES:
                time.sleep(INITIAL_RETRY_DELAY * attempt)

        except Exception as e:
            logger.warning(f"   ❌ कोशिश {attempt} विफल: {e}")
            if attempt < MAX_RETRIES:
                time.sleep(INITIAL_RETRY_DELAY * attempt)

    return None


def _wait_for_container_ready(container_id: str, max_wait: int = 60) -> bool:
    if not container_id or container_id == "0" or len(str(container_id)) < 5:
        logger.error(f"   ❌ गलत container_id: '{container_id}' — skip")
        return False

    url = f"{META_BASE_URL}/{container_id}"

    logger.info(f"   ⏳ Container प्रारंभिक wait 10s...")
    time.sleep(10)

    max_checks   = max_wait // 3
    error_count  = 0

    for attempt in range(max_checks):
        try:
            r = requests.get(
                url,
                params={'fields': 'status_code,status', 'access_token': ACCESS_TOKEN},
                timeout=REQUEST_TIMEOUT
            )

            if r.status_code == 200:
                data   = r.json()
                status = data.get('status_code', '')
                detail = data.get('status', '')
                logger.info(f"   ⏱️  Container स्थिति: {status} | {detail[:80]}")

                if status == 'FINISHED':
                    return True
                elif status == 'ERROR':
                    error_count += 1
                    if error_count >= 2:
                        logger.error(f"   ❌ Container ERROR (2 बार confirm)")
                        return False
                    logger.warning(f"   ⚠️  ERROR मिला, 5s बाद फिर check...")
                    time.sleep(5)
                    continue
                elif status == 'IN_PROGRESS':
                    logger.info(f"   ⏳ अभी process हो रहा है...")
            else:
                logger.warning(f"   ⚠️  Status HTTP {r.status_code}: {r.text[:150]}")

            time.sleep(3)

        except Exception as e:
            logger.warning(f"   Status check विफल: {e}")
            time.sleep(3)

    logger.warning(f"   ⚠️  {max_wait}s में container तैयार नहीं हुआ")
    return False


def _create_ig_carousel_container(media_ids: list, caption: str) -> Optional[str]:
    url = f"{META_BASE_URL}/{INSTAGRAM_ACCOUNT_ID}/media"
    MAX_CAROUSEL_RETRIES = 5

    for attempt in range(1, MAX_CAROUSEL_RETRIES + 1):
        try:
            logger.info(f"📦 Carousel container बना रहे हैं (कोशिश {attempt}/{MAX_CAROUSEL_RETRIES})...")
            logger.info(f"   Media IDs: {media_ids}")
            logger.info(f"   Caption length: {len(caption)} chars")

            if attempt > 1:
                wait = 20 * attempt
                logger.info(f"   ⏳ {wait}s wait (IG को process time चाहिए)...")
                time.sleep(wait)

            response = requests.post(
                url,
                data={
                    'media_type':   'CAROUSEL',
                    'children':     ",".join(media_ids),
                    'caption':      caption,
                    'access_token': ACCESS_TOKEN
                },
                timeout=REQUEST_TIMEOUT
            )

            logger.info(f"   Response status: {response.status_code}")

            try:
                resp_json = response.json()
                logger.info(f"   Response: {resp_json}")
            except Exception:
                logger.warning(f"   Raw response: {response.text[:300]}")
                resp_json = {}

            if response.status_code == 200:
                container_id = resp_json.get('id')

                if container_id and container_id != "0" and len(str(container_id)) > 5:
                    logger.info(f"✅ Carousel container: {container_id}")

                    time.sleep(8)
                    check_url = f"{META_BASE_URL}/{container_id}"
                    check_r = requests.get(
                        check_url,
                        params={'fields': 'status_code,status', 'access_token': ACCESS_TOKEN},
                        timeout=15
                    )

                    if check_r.status_code == 200:
                        status = check_r.json().get('status_code', '')
                        detail = check_r.json().get('status', '')
                        logger.info(f"   Quick check: {status} | {detail[:100]}")

                        if status == 'ERROR':
                            if '2207032' in str(detail):
                                logger.error(f"   ❌ Error 2207032 — Image format/expired issue, retry...")
                            else:
                                logger.error(f"   ❌ Container ERROR: {detail}")
                            continue

                    return container_id
                else:
                    logger.error(f"❌ गलत container ID: '{container_id}'")
                    continue

            error = _parse_meta_error(response)
            logger.warning(f"⚠️  Container विफल: {error['message']} (code: {error.get('code')})")

        except Exception as e:
            logger.warning(f"❌ कोशिश {attempt}: {e}")

    logger.error(f"❌ {MAX_CAROUSEL_RETRIES} कोशिशों के बाद भी carousel container नहीं बना")
    return None


# ============================================================
# 🎠 CAROUSEL — INSTAGRAM MAIN (EXISTING - UNCHANGED)
# ============================================================

def post_carousel_to_instagram(slides: list, caption: str, memory: Optional[AgentMemory] = None) -> dict:
    """Carousel IG publishing (existing logic preserved)"""
    logger.info("🎠 Instagram Carousel publish शुरू...")
    logger.info(f"   कुल slides: {len(slides)}")

    expired_cleared = 0
    for slide in slides:
        if slide.get("media_id"):
            if _is_media_id_expired(slide):
                old_id = slide.pop("media_id", None)
                slide.pop("media_id_created_at", None)
                expired_cleared += 1
                logger.info(f"   🗑️  Slide {slide.get('slide_number','?')}: Expired media_id {old_id} हटाया")

    if expired_cleared > 0:
        logger.info(f"   ♻️  {expired_cleared} expired media_ids साफ किए → fresh containers बनेंगे")
    else:
        logger.info(f"   ✅ सभी slides fresh हैं")

    media_ids  = []
    failed     = []
    session_id = memory.session_id if memory else ""

    for slide in slides:
        slide_num = slide.get("slide_number", "?")
        logger.info(f"\n   📸 स्लाइड {slide_num}/{len(slides)} process...")

        image_bytes = slide.get("image_bytes")

        image_url = slide.get("image_url", "")
        if image_url:
            logger.info(f"   ♻️  पुराना URL reuse: {image_url[:60]}...")
        else:
            if not image_bytes:
                logger.warning(f"   ⚠️  Slide {slide_num}: bytes और URL दोनों नहीं → skip")
                failed.append(slide_num)
                continue

            logger.info(f"   ☁️  GCS पर upload हो रहा है...")
            image_url = _upload_carousel_item(image_bytes)
            if not image_url:
                logger.warning(f"   ⚠️  Slide {slide_num} upload विफल → skip")
                failed.append(slide_num)
                continue
            slide["image_url"] = image_url
            logger.info(f"   ✅ Upload हुआ: {image_url[:60]}...")

        logger.info(f"   🔄 Fresh IG container बना रहे हैं (reuse बंद — expiry fix)...")
        time.sleep(CAROUSEL_ITEM_WAIT)
        media_id = _create_ig_carousel_item(image_url)

        if not media_id:
            logger.warning(f"   ⚠️  Slide {slide_num} IG item विफल → skip")
            failed.append(slide_num)
            continue

        logger.info(f"   ⏳ Slide {slide_num} container तैयार होने का wait...")
        if not _wait_for_container_ready(media_id, max_wait=30):
            logger.warning(f"   ⚠️  Slide {slide_num} container तैयार नहीं → skip")
            failed.append(slide_num)
            continue

        slide["media_id"]             = media_id
        slide["media_id_created_at"]  = datetime.now().isoformat()
        media_ids.append(media_id)
        logger.info(f"   ✅ Slide {slide_num} ready: {media_id}")

    if session_id and memory:
        clean_slides = [{k: v for k, v in s.items() if k != "image_bytes"} for s in slides]
        slides_bytes_map = {s["slide_number"]: s["image_bytes"] for s in slides if s.get("image_bytes")}
        save_checkpoint(
            session_id=session_id,
            stage="IG_CONTAINERS_READY",
            data={
                "topic":            memory.topic,
                "category":         memory.category,
                "post_type":        "carousel",
                "carousel_slides":  clean_slides,
                "carousel_caption": caption,
            },
            slides_bytes=slides_bytes_map
        )
        logger.info("💾 Checkpoint: IG_CONTAINERS_READY")

    if len(media_ids) < 2:
        return {
            "success":   False,
            "post_id":   "",
            "error":     f"सिर्फ {len(media_ids)} slides upload हुए, कम से कम 2 चाहिए",
            "media_ids": media_ids
        }

    logger.info(f"\n✅ {len(media_ids)} slides carousel के लिए तैयार")

    time.sleep(3)
    container_id = _create_ig_carousel_container(media_ids, caption)

    if not container_id:
        return {
            "success":   False,
            "post_id":   "",
            "error":     "Carousel container नहीं बना",
            "media_ids": media_ids
        }

    logger.info("⏳ Carousel container FINISHED wait...")
    if not _wait_for_container_ready(container_id, max_wait=90):
        return {
            "success":   False,
            "post_id":   "",
            "error":     "Carousel container FINISHED नहीं हुआ",
            "media_ids": media_ids
        }

    publish_result = _publish_instagram_container(container_id)

    if publish_result["success"]:
        logger.info(f"🎉 Carousel पब्लिश! Post ID: {publish_result['post_id']}")
        return {
            "success":       True,
            "post_id":       publish_result["post_id"],
            "container_id":  container_id,
            "media_ids":     media_ids,
            "slides_used":   len(media_ids),
            "slides_failed": failed
        }

    return {
        "success":   False,
        "post_id":   "",
        "error":     publish_result["error"].get("message", "Publish विफल"),
        "media_ids": media_ids
    }


def post_carousel_to_facebook(slides: list, caption: str, memory: Optional[AgentMemory] = None) -> dict:
    """FB Album publishing (existing)"""
    logger.info("📘 Facebook Album post शुरू...")
    logger.info(f"   कुल slides: {len(slides)}")

    photo_ids = []
    failed    = []

    for slide in slides:
        slide_num = slide.get("slide_number", "?")
        image_url = slide.get("image_url")

        if not image_url:
            logger.warning(f"   ⚠️  Slide {slide_num} में URL नहीं → skip")
            failed.append(slide_num)
            continue

        existing_photo_id = slide.get("fb_photo_id", "")
        if existing_photo_id and len(str(existing_photo_id)) > 5:
            logger.info(f"   ♻️  Slide {slide_num}: पुराना FB photo_id reuse: {existing_photo_id}")
            photo_ids.append(existing_photo_id)
            continue

        try:
            logger.info(f"   📸 FB Slide {slide_num}/{len(slides)} upload...")

            url = f"{META_BASE_URL}/{FACEBOOK_PAGE_ID}/photos"
            response = requests.post(
                url,
                params={
                    'url':          image_url,
                    'published':    'false',
                    'access_token': ACCESS_TOKEN
                },
                timeout=REQUEST_TIMEOUT
            )

            if response.status_code == 200:
                photo_id = response.json().get('id')
                if photo_id:
                    photo_ids.append(photo_id)
                    slide["fb_photo_id"] = photo_id
                    logger.info(f"   ✅ FB Slide {slide_num}: {photo_id}")
                else:
                    logger.warning(f"   ⚠️  Slide {slide_num}: photo_id नहीं मिला")
                    failed.append(slide_num)
            else:
                error = _parse_meta_error(response)
                logger.warning(f"   ⚠️  FB Slide {slide_num} विफल: {error['message']}")
                failed.append(slide_num)

            time.sleep(1)

        except Exception as e:
            logger.warning(f"   ❌ FB Slide {slide_num} error: {e}")
            failed.append(slide_num)

    if memory and memory.session_id:
        clean_slides = [{k: v for k, v in s.items() if k != "image_bytes"} for s in slides]
        slides_bytes_map = {s["slide_number"]: s["image_bytes"] for s in slides if s.get("image_bytes")}
        save_checkpoint(
            session_id=memory.session_id,
            stage="FB_UPLOADED",
            data={
                "topic":               memory.topic,
                "category":            memory.category,
                "post_type":           "carousel",
                "carousel_slides":     clean_slides,
                "carousel_caption":    caption,
                "carousel_ig_post_id": memory.carousel_ig_post_id,
                "carousel_ig_success": memory.carousel_ig_success,
            },
            slides_bytes=slides_bytes_map
        )
        logger.info("💾 Checkpoint: FB_UPLOADED")

    if not photo_ids:
        return {
            "success":   False,
            "post_id":   "",
            "error":     "FB पर कोई slide upload नहीं हुई",
            "photo_ids": []
        }

    logger.info(f"\n✅ {len(photo_ids)} photos FB पर ready, album बना रहे हैं...")

    try:
        attached_media = [{"media_fbid": pid} for pid in photo_ids]
        url = f"{META_BASE_URL}/{FACEBOOK_PAGE_ID}/feed"

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                logger.info(f"📤 FB album post (कोशिश {attempt}/{MAX_RETRIES})...")
                response = requests.post(
                    url,
                    params={
                        'message':        caption,
                        'attached_media': json_lib.dumps(attached_media),
                        'access_token':   ACCESS_TOKEN
                    },
                    timeout=REQUEST_TIMEOUT
                )

                if response.status_code == 200:
                    data    = response.json()
                    post_id = data.get('id') or data.get('post_id')
                    if post_id:
                        logger.info(f"✅ FB Album पब्लिश: {post_id}")
                        return {
                            "success":       True,
                            "post_id":       post_id,
                            "photo_ids":     photo_ids,
                            "slides_used":   len(photo_ids),
                            "slides_failed": failed
                        }

                error = _parse_meta_error(response)
                logger.warning(f"⚠️  FB album विफल: {error['message']}")

                if _is_rate_limited(error):
                    time.sleep(min(MAX_RETRY_DELAY, INITIAL_RETRY_DELAY * (2 ** attempt)))
                elif attempt < MAX_RETRIES:
                    time.sleep(INITIAL_RETRY_DELAY * attempt)
                else:
                    return {"success": False, "post_id": "", "error": error["message"], "photo_ids": photo_ids}

            except requests.Timeout:
                if attempt < MAX_RETRIES:
                    time.sleep(5)
            except Exception as e:
                if attempt < MAX_RETRIES:
                    time.sleep(INITIAL_RETRY_DELAY * attempt)
                else:
                    return {"success": False, "post_id": "", "error": str(e), "photo_ids": photo_ids}

        return {"success": False, "post_id": "", "error": "अधिकतम retries पार", "photo_ids": photo_ids}

    except Exception as e:
        return {"success": False, "post_id": "", "error": str(e), "photo_ids": photo_ids}


# ============================================================
# 🆕 V2: REEL — INSTAGRAM
# ============================================================

def _wait_for_reel_container_ready(container_id: str, max_wait: int = 180) -> bool:
    """
    🆕 Wait for Instagram Reel container to be FINISHED.
    Reels need longer wait than images (video processing).
    """
    if not container_id or len(str(container_id)) < 5:
        logger.error(f"   ❌ Invalid container_id: '{container_id}'")
        return False

    url = f"{META_BASE_URL}/{container_id}"

    # Initial wait (video processing takes time)
    logger.info(f"   ⏳ Reel container initial wait 15s...")
    time.sleep(15)

    max_checks = max_wait // REEL_STATUS_CHECK_INTERVAL
    error_count = 0

    for attempt in range(max_checks):
        try:
            r = requests.get(
                url,
                params={'fields': 'status_code,status', 'access_token': ACCESS_TOKEN},
                timeout=REQUEST_TIMEOUT
            )

            if r.status_code == 200:
                data = r.json()
                status = data.get('status_code', '')
                detail = data.get('status', '')
                logger.info(f"   ⏱️  Reel status: {status} | {detail[:80]}")

                if status == 'FINISHED':
                    logger.info(f"   ✅ Reel container ready!")
                    return True
                elif status == 'ERROR':
                    error_count += 1
                    if error_count >= 2:
                        logger.error(f"   ❌ Reel container ERROR")
                        return False
                    time.sleep(5)
                    continue
                elif status == 'IN_PROGRESS' or status == 'PUBLISHED':
                    if status == 'PUBLISHED':
                        return True
                    logger.info(f"   ⏳ Reel processing...")

            time.sleep(REEL_STATUS_CHECK_INTERVAL)

        except Exception as e:
            logger.warning(f"   Status check error: {e}")
            time.sleep(REEL_STATUS_CHECK_INTERVAL)

    logger.warning(f"   ⚠️  Reel container not ready after {max_wait}s")
    return False


def post_reel_to_instagram(video_url: str, caption: str, memory: Optional[AgentMemory] = None) -> dict:
    """
    🆕 V2: Post Reel to Instagram.

    Uses IG Reels API:
    1. POST /media with media_type=REELS + video_url
    2. Wait for FINISHED status (video processing)
    3. POST /media_publish with container_id

    Args:
        video_url: Public URL of MP4 (from GCS)
        caption: Full caption with hashtags
        memory: For checkpoints

    Returns:
        {"success": bool, "post_id": str, "container_id": str, "error": str}
    """
    logger.info("🎬 Instagram Reel publish शुरू...")
    logger.info(f"   Video URL: {video_url[:80]}...")

    if not _verify_video_url(video_url):
        logger.warning("⚠️  Video URL verify नहीं हुआ, आगे बढ़ रहे हैं...")

    # ═══════════════════════════════════════════
    # STEP 1: Create Reel Container
    # ═══════════════════════════════════════════
    url = f"{META_BASE_URL}/{INSTAGRAM_ACCOUNT_ID}/media"

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            logger.info(f"📦 IG Reel container बना रहे हैं (कोशिश {attempt}/{MAX_RETRIES})")

            response = requests.post(
                url,
                data={
                    'media_type':    'REELS',
                    'video_url':     video_url,
                    'caption':       caption,
                    'share_to_feed': 'true',  # Also show in main feed
                    'access_token':  ACCESS_TOKEN
                },
                timeout=REQUEST_TIMEOUT
            )

            if response.status_code == 200:
                creation_id = response.json().get('id')
                if creation_id:
                    logger.info(f"✅ Reel container तैयार: {creation_id}")

                    # ═══════════════════════════════════════════
                    # STEP 2: Wait for FINISHED (video processing)
                    # ═══════════════════════════════════════════
                    logger.info("⏳ Reel processing (video takes 30-120s)...")

                    if not _wait_for_reel_container_ready(creation_id, max_wait=180):
                        return {
                            "success": False,
                            "post_id": "",
                            "container_id": creation_id,
                            "error": "Reel container FINISHED नहीं हुआ (video processing timeout)"
                        }

                    # ═══════════════════════════════════════════
                    # STEP 3: Publish Reel
                    # ═══════════════════════════════════════════
                    logger.info(f"📤 Publishing reel...")

                    publish_result = _publish_instagram_container(creation_id)

                    if publish_result["success"]:
                        logger.info(f"🎉 Reel पब्लिश हो गया! Post ID: {publish_result['post_id']}")
                        return {
                            "success":      True,
                            "post_id":      publish_result["post_id"],
                            "container_id": creation_id
                        }
                    else:
                        return {
                            "success": False,
                            "post_id": "",
                            "container_id": creation_id,
                            "error": publish_result["error"].get("message", "Reel publish विफल")
                        }

                raise Exception("No creation_id in response")

            error = _parse_meta_error(response)
            logger.warning(f"⚠️  Reel container विफल: {error['message']}")

            # Check for specific error codes
            if error.get('code') == 2207028:
                logger.error("❌ Video format not supported. Must be MP4, H.264, AAC")
                return {"success": False, "post_id": "", "error": error["message"]}

            if _is_rate_limited(error):
                wait = min(MAX_RETRY_DELAY, INITIAL_RETRY_DELAY * (2 ** attempt))
                time.sleep(wait)
            elif attempt < MAX_RETRIES:
                time.sleep(INITIAL_RETRY_DELAY * attempt)
            else:
                return {"success": False, "post_id": "", "error": error["message"]}

        except requests.Timeout:
            logger.warning(f"⚠️  Timeout on attempt {attempt}")
            if attempt < MAX_RETRIES:
                time.sleep(5)
        except Exception as e:
            logger.error(f"❌ Reel post error: {e}")
            if attempt < MAX_RETRIES:
                time.sleep(INITIAL_RETRY_DELAY * attempt)
            else:
                return {"success": False, "post_id": "", "error": str(e)}

    return {"success": False, "post_id": "", "error": "Max retries exceeded"}


# ============================================================
# 🆕 V2: REEL — FACEBOOK
# ============================================================

def post_reel_to_facebook(video_url: str, caption: str, memory: Optional[AgentMemory] = None) -> dict:
    """
    🆕 V2: Post Reel to Facebook.

    Uses FB Video Reels API:
    POST /{page_id}/video_reels with source URL

    Args:
        video_url: Public URL of MP4
        caption: Description

    Returns:
        {"success": bool, "post_id": str, "error": str}
    """
    logger.info("📘 Facebook Reel publish शुरू...")
    logger.info(f"   Video URL: {video_url[:80]}...")

    url = f"{META_BASE_URL}/{FACEBOOK_PAGE_ID}/video_reels"

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            logger.info(f"📤 FB Reel पोस्ट (कोशिश {attempt}/{MAX_RETRIES})")

            # Step 1: Initialize upload
            init_response = requests.post(
                url,
                params={
                    'upload_phase': 'start',
                    'access_token': ACCESS_TOKEN
                },
                timeout=REQUEST_TIMEOUT
            )

            if init_response.status_code == 200:
                init_data = init_response.json()
                video_id = init_data.get('video_id')
                upload_url = init_data.get('upload_url')

                if video_id and upload_url:
                    logger.info(f"   ✅ FB Reel upload initialized: {video_id}")

                    # Step 2: Upload video via file_url
                    upload_response = requests.post(
                        upload_url,
                        headers={
                            'Authorization': f'OAuth {ACCESS_TOKEN}',
                            'file_url': video_url
                        },
                        timeout=REQUEST_TIMEOUT * 2  # Longer for video
                    )

                    if upload_response.status_code == 200:
                        logger.info(f"   ✅ Video uploaded to FB")

                        # Step 3: Finish upload (publish)
                        finish_url = f"{META_BASE_URL}/{FACEBOOK_PAGE_ID}/video_reels"
                        finish_response = requests.post(
                            finish_url,
                            params={
                                'access_token': ACCESS_TOKEN,
                                'video_id': video_id,
                                'upload_phase': 'finish',
                                'video_state': 'PUBLISHED',
                                'description': caption
                            },
                            timeout=REQUEST_TIMEOUT
                        )

                        if finish_response.status_code == 200:
                            finish_data = finish_response.json()
                            if finish_data.get('success'):
                                logger.info(f"🎉 FB Reel पब्लिश: {video_id}")
                                return {
                                    "success": True,
                                    "post_id": video_id
                                }

                        # Fallback: Try alternate publish
                        logger.warning("⚠️  Publish step failed, trying alternate method...")

                    else:
                        logger.warning(f"⚠️  Upload failed: {upload_response.status_code}")

            # ═══════════════════════════════════════════
            # FALLBACK: Simple FB video post (feed post with video)
            # ═══════════════════════════════════════════
            logger.info(f"🔄 Fallback: FB videos endpoint...")

            fallback_url = f"{META_BASE_URL}/{FACEBOOK_PAGE_ID}/videos"
            fallback_response = requests.post(
                fallback_url,
                params={
                    'file_url':     video_url,
                    'description':  caption,
                    'access_token': ACCESS_TOKEN
                },
                timeout=REQUEST_TIMEOUT * 2
            )

            if fallback_response.status_code == 200:
                data = fallback_response.json()
                post_id = data.get('id') or data.get('video_id')
                if post_id:
                    logger.info(f"✅ FB Video पब्लिश (fallback): {post_id}")
                    return {"success": True, "post_id": post_id}

            error = _parse_meta_error(fallback_response)
            logger.warning(f"⚠️  FB Reel विफल: {error['message']}")

            if _is_rate_limited(error):
                time.sleep(min(MAX_RETRY_DELAY, INITIAL_RETRY_DELAY * (2 ** attempt)))
            elif attempt < MAX_RETRIES:
                time.sleep(INITIAL_RETRY_DELAY * attempt)
            else:
                return {"success": False, "post_id": "", "error": error["message"]}

        except requests.Timeout:
            if attempt < MAX_RETRIES:
                time.sleep(5)
        except Exception as e:
            logger.error(f"❌ FB Reel error: {e}")
            if attempt < MAX_RETRIES:
                time.sleep(INITIAL_RETRY_DELAY * attempt)
            else:
                return {"success": False, "post_id": "", "error": str(e)}

    return {"success": False, "post_id": "", "error": "Max retries exceeded"}


# ============================================================
# 🆕 V2: REEL — YOUTUBE SHORTS
# ============================================================

def post_reel_to_youtube(video_bytes: bytes, title: str, description: str, hashtags: str = "") -> dict:
    """
    🆕 V2: Upload Reel to YouTube Shorts.

    Delegates to posting/youtube.py module.

    Args:
        video_bytes: MP4 video bytes
        title: Video title
        description: Video description
        hashtags: Hashtag string

    Returns:
        {"success": bool, "video_id": str, "url": str, "error": str}
    """
    logger.info("📺 YouTube Shorts upload शुरू...")

    if not YOUTUBE_ENABLED:
        logger.warning("⚠️  YouTube upload disabled in config")
        return {
            "success": False,
            "video_id": "",
            "url": "",
            "error": "YouTube disabled"
        }

    try:
        # Import here to avoid startup issues if libraries not installed
        from posting.youtube import upload_short

        result = upload_short(
            video_bytes=video_bytes,
            title=title,
            description=description,
            hashtags=hashtags
        )

        if result.get("success"):
            logger.info(f"🎉 YouTube Short पब्लिश: {result.get('shorts_url', 'N/A')}")

        return result

    except ImportError as e:
        logger.error(f"❌ YouTube module not available: {e}")
        return {
            "success": False,
            "video_id": "",
            "url": "",
            "error": f"YouTube module not installed: {e}"
        }
    except Exception as e:
        logger.error(f"❌ YouTube upload error: {e}")
        return {
            "success": False,
            "video_id": "",
            "url": "",
            "error": str(e)
        }


# ============================================================
# MAIN AGENT FUNCTION (V2 EXTENDED)
# ============================================================

def run(memory: AgentMemory) -> AgentMemory:
    """
    Publisher Agent:
    - post_type == "image"    → single image flow
    - post_type == "carousel" → IG carousel + FB album
    - 🆕 post_type == "reel"  → IG Reel + FB Reel + YouTube Short

    Recovery Fix:
    - image_url  → REUSE ✅ (GCS URL permanent)
    - fb_photo_id → REUSE ✅ (FB photos stay)
    - media_id   → NEVER REUSE ❌ (IG containers expire → Error 2207032)
    """
    logger.info("=" * 55)
    logger.info("=== PUBLISHER AGENT शुरू ===")
    logger.info(f"=== Post Type: {memory.post_type.upper()} ===")
    if memory.is_recovery:
        logger.info(f"=== ♻️  RECOVERY MODE (from {memory.resumed_from_stage}) ===")
    logger.info("=" * 55)

    start_time = time.time()

    # Token validation
    is_valid, token_error = _validate_token()
    if not is_valid:
        logger.error(f"❌ Token invalid: {token_error}")
        memory.add_error("publisher", token_error)

    # ═══════════════════════════════════════
    # 🆕 V2: REEL FLOW
    # ═══════════════════════════════════════
    if memory.post_type == "reel":
        logger.info("🎬 REEL PUBLISH मोड")

        if not memory.reel_video_url:
            logger.error("❌ Reel video URL नहीं है")
            memory.add_error("publisher", "No reel video URL")
            return memory

        full_caption = _prepare_caption(memory.caption or "", memory.hashtags or "")
        logger.info(f"📝 Caption: {len(full_caption)} chars")

        # ── Instagram Reel ────────────────────────────────
        if memory.is_recovery and memory.reel_ig_success:
            logger.info("\n⏭️  Instagram Reel already published, skip")
            ig_result = {"success": True, "post_id": memory.reel_ig_post_id or ""}
        else:
            logger.info("\n--- 📸 INSTAGRAM REEL POSTING ---")
            ig_result = post_reel_to_instagram(
                video_url=memory.reel_video_url,
                caption=full_caption,
                memory=memory
            )
            memory.reel_ig_success = ig_result["success"]
            memory.reel_ig_post_id = ig_result.get("post_id", "")
            memory.ig_success = ig_result["success"]  # For backward compat
            memory.ig_post_id = ig_result.get("post_id", "")

            if not ig_result["success"]:
                memory.add_error("publisher_ig_reel", ig_result.get("error", "unknown"))
            else:
                # Checkpoint after IG success
                save_checkpoint(
                    session_id=memory.session_id,
                    stage="REEL_IG_PUBLISHED",
                    data=memory.to_recovery_dict()
                )

        # ── Facebook Reel ─────────────────────────────────
        if memory.is_recovery and memory.reel_fb_success:
            logger.info("\n⏭️  Facebook Reel already published, skip")
            fb_result = {"success": True, "post_id": memory.reel_fb_post_id or ""}
        else:
            logger.info("\n--- 📘 FACEBOOK REEL POSTING ---")

            _human_like_delay(
                DELAY_BETWEEN_PLATFORMS_MIN,
                DELAY_BETWEEN_PLATFORMS_MAX,
                "Facebook से पहले wait"
            )

            fb_result = post_reel_to_facebook(
                video_url=memory.reel_video_url,
                caption=full_caption,
                memory=memory
            )
            memory.reel_fb_success = fb_result["success"]
            memory.reel_fb_post_id = fb_result.get("post_id", "")
            memory.fb_success = fb_result["success"]
            memory.fb_post_id = fb_result.get("post_id", "")

            if not fb_result["success"]:
                memory.add_error("publisher_fb_reel", fb_result.get("error", "unknown"))
            else:
                save_checkpoint(
                    session_id=memory.session_id,
                    stage="REEL_FB_PUBLISHED",
                    data=memory.to_recovery_dict()
                )

        # ── YouTube Shorts ────────────────────────────────
        yt_result = {"success": False, "video_id": "", "url": ""}

        if YOUTUBE_ENABLED:
            if memory.is_recovery and memory.reel_yt_success:
                logger.info("\n⏭️  YouTube Short already published, skip")
                yt_result = {
                    "success": True,
                    "video_id": memory.reel_yt_video_id or "",
                    "url": f"https://youtube.com/shorts/{memory.reel_yt_video_id}"
                }
            else:
                logger.info("\n--- 📺 YOUTUBE SHORTS UPLOAD ---")

                _human_like_delay(30, 60, "YouTube से पहले wait")

                # Prepare YouTube-specific fields
                yt_title = memory.topic[:90] if memory.topic else "Spiritual Content"
                yt_description = memory.caption or ""

                yt_result = post_reel_to_youtube(
                    video_bytes=memory.reel_video_bytes,
                    title=yt_title,
                    description=yt_description,
                    hashtags=memory.hashtags or ""
                )

                memory.reel_yt_success = yt_result["success"]
                memory.reel_yt_video_id = yt_result.get("video_id", "")

                if not yt_result["success"]:
                    memory.add_error("publisher_yt", yt_result.get("error", "unknown"))
                else:
                    save_checkpoint(
                        session_id=memory.session_id,
                        stage="REEL_YT_PUBLISHED",
                        data=memory.to_recovery_dict()
                    )
        else:
            logger.info("\n⏭️  YouTube disabled in config, skipping")

        # ═══════════════════════════════════════════
        # Recovery Cleanup Logic
        # ═══════════════════════════════════════════
        ig_ok = memory.reel_ig_success
        fb_ok = memory.reel_fb_success
        yt_ok = memory.reel_yt_success

        # Count successes
        platforms_succeeded = sum([ig_ok, fb_ok, yt_ok])
        expected = 3 if YOUTUBE_ENABLED else 2

        if platforms_succeeded >= expected:
            # All platforms succeeded → delete checkpoint
            logger.info("")
            logger.info("🎉 सभी platforms सफल — checkpoint delete")
            if memory.session_id:
                delete_checkpoint(memory.session_id)
                logger.info("✅ Recovery data साफ किया")
        else:
            # Some failed → keep checkpoint for retry
            logger.info("")
            logger.info(f"⚠️  {platforms_succeeded}/{expected} platforms सफल — recovery रख रहे हैं")
            logger.info("💡 दोबारा try: python main.py recover")

        # ═══════════════════════════════════════════
        # SUMMARY
        # ═══════════════════════════════════════════
        duration = time.time() - start_time

        logger.info("")
        logger.info("┌─────────────────────────────────────────────┐")
        logger.info("│         🎬 REEL PUBLISHING रिपोर्ट           │")
        logger.info("├─────────────────────────────────────────────┤")
        logger.info(f"│ ⏱️  समय       : {duration:.1f}s")
        logger.info(f"│ 📸 Instagram : {'✅' if ig_ok else '❌'} {memory.reel_ig_post_id or 'विफल'}")
        logger.info(f"│ 📘 Facebook  : {'✅' if fb_ok else '❌'} {memory.reel_fb_post_id or 'विफल'}")
        if YOUTUBE_ENABLED:
            logger.info(f"│ 📺 YouTube   : {'✅' if yt_ok else '❌'} {memory.reel_yt_video_id or 'विफल'}")
        else:
            logger.info(f"│ 📺 YouTube   : ⏭️  Disabled")
        logger.info("└─────────────────────────────────────────────┘")

    # ═══════════════════════════════════════
    # 🎠 CAROUSEL FLOW (EXISTING - UNCHANGED)
    # ═══════════════════════════════════════
    elif memory.post_type == "carousel":
        logger.info("🎠 CAROUSEL PUBLISH मोड")

        if not memory.carousel_slides:
            memory.add_error("publisher", "Memory में कोई slide नहीं")
            return memory

        if memory.is_recovery:
            if memory.carousel_ig_success:
                logger.info("♻️  IG पहले से publish हो चुका — skip")
            if memory.carousel_fb_success:
                logger.info("♻️  FB पहले से publish हो चुका — skip")

        full_caption = _prepare_caption(memory.carousel_caption, memory.hashtags or "")
        logger.info(f"📝 Caption: {len(full_caption)} chars")

        # Instagram Carousel
        if memory.is_recovery and memory.carousel_ig_success:
            logger.info("\n⏭️  Instagram पहले से publish हो चुका, skip")
            ig_result = {"success": True, "post_id": memory.carousel_ig_post_id or ""}
        else:
            logger.info("\n--- INSTAGRAM पर CAROUSEL पोस्ट ---")
            ig_result = post_carousel_to_instagram(
                slides=memory.carousel_slides,
                caption=full_caption,
                memory=memory
            )
            memory.carousel_ig_success = ig_result["success"]
            memory.carousel_ig_post_id = ig_result.get("post_id", "")
            memory.ig_success = ig_result["success"]
            memory.ig_post_id = ig_result.get("post_id", "")

            if not ig_result["success"]:
                memory.add_error("publisher_ig_carousel", ig_result.get("error", "अज्ञात"))

        # Facebook Album
        if memory.is_recovery and memory.carousel_fb_success:
            logger.info("\n⏭️  Facebook पहले से publish हो चुका, skip")
            fb_result = {"success": True, "post_id": memory.carousel_fb_post_id or ""}
        else:
            logger.info("\n--- FACEBOOK पर CAROUSEL ALBUM पोस्ट ---")
            slides_with_urls = [s for s in memory.carousel_slides if s.get("image_url")]

            if slides_with_urls:
                _human_like_delay(
                    DELAY_BETWEEN_PLATFORMS_MIN,
                    DELAY_BETWEEN_PLATFORMS_MAX,
                    "Facebook से पहले wait"
                )
                fb_result = post_carousel_to_facebook(
                    slides=memory.carousel_slides,
                    caption=full_caption,
                    memory=memory
                )
                memory.carousel_fb_success = fb_result["success"]
                memory.carousel_fb_post_id = fb_result.get("post_id", "")
                memory.fb_success = fb_result["success"]
                memory.fb_post_id = fb_result.get("post_id", "")

                if not fb_result["success"]:
                    memory.add_error("publisher_fb_album", fb_result.get("error", "अज्ञात"))
            else:
                logger.warning("⚠️  Facebook के लिए कोई URL नहीं → skip")
                memory.fb_success = False
                fb_result = {"success": False, "post_id": "", "error": "URL नहीं मिला"}

        # Cleanup logic
        ig_ok = memory.ig_success or (memory.is_recovery and memory.carousel_ig_success)
        fb_ok = memory.fb_success or (memory.is_recovery and memory.carousel_fb_success)

        if ig_ok and fb_ok:
            logger.info("")
            logger.info("🎉 दोनों platforms सफल — checkpoint delete")
            if memory.session_id:
                delete_checkpoint(memory.session_id)
                logger.info("✅ Recovery data साफ किया")

        duration = time.time() - start_time
        logger.info(f"\n⏱️  Carousel publish में {duration:.1f}s लगे")

    # ═══════════════════════════════════════
    # SINGLE IMAGE FLOW (EXISTING - UNCHANGED)
    # ═══════════════════════════════════════
    else:
        logger.info("🖼️  SINGLE IMAGE PUBLISH मोड")

        if not memory.image_url:
            memory.add_error("publisher", "पोस्ट के लिए image URL नहीं")
            return memory

        if not memory.caption:
            memory.add_error("publisher", "पोस्ट के लिए caption नहीं")
            return memory

        if not _verify_image_url(memory.image_url):
            logger.warning("⚠️  Image URL verify नहीं हुआ, आगे बढ़ रहे हैं...")

        full_caption = _prepare_caption(memory.caption, memory.hashtags or "")
        logger.info(f"📝 Caption: {len(full_caption)} chars")

        # Instagram
        logger.info("\n--- INSTAGRAM पर पोस्ट ---")
        ig_result = post_to_instagram(memory.image_url, full_caption)
        memory.ig_success = ig_result["success"]
        memory.ig_post_id = ig_result.get("post_id", "")
        if not ig_result["success"]:
            memory.add_error("publisher_instagram", ig_result.get("error", "अज्ञात"))

        _human_like_delay(
            DELAY_BETWEEN_PLATFORMS_MIN,
            DELAY_BETWEEN_PLATFORMS_MAX,
            "Facebook से पहले wait"
        )

        # Facebook
        logger.info("\n--- FACEBOOK पर पोस्ट ---")
        fb_result = post_to_facebook(memory.image_url, full_caption)
        memory.fb_success = fb_result["success"]
        memory.fb_post_id = fb_result.get("post_id", "")
        if not fb_result["success"]:
            memory.add_error("publisher_facebook", fb_result.get("error", "अज्ञात"))

        duration = time.time() - start_time
        _log_publishing_report(memory, ig_result, fb_result, duration)

        if memory.ig_success and memory.fb_success:
            logger.info("✅ दोनों platforms पर सफल पब्लिश")
        elif memory.ig_success or memory.fb_success:
            logger.warning("⚠️  सिर्फ एक platform पर सफल")
        else:
            logger.error("❌ दोनों platforms विफल")

    logger.info("=== PUBLISHER AGENT पूर्ण ===\n")
    return memory