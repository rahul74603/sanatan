"""
Publisher Agent - Meta Platform Publisher (Production Grade)

Features:
- Single image posting (unchanged flow)
- Instagram Carousel + Facebook Album
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
    DELAY_BETWEEN_PLATFORMS_MAX
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
# IG containers expire in ~24h, but to be safe we treat
# anything saved > 30 minutes ago as expired.
IG_CONTAINER_EXPIRY_SECONDS = 30 * 60  # 30 minutes


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
    """
    🔧 FIX: Check करो कि saved media_id expire हुआ है या नहीं।

    Instagram child containers expire हो जाते हैं।
    अगर media_id_created_at नहीं है, या बहुत पुराना है,
    तो fresh container बनाओ।

    Returns:
        True  = expired है, fresh बनाओ
        False = fresh है, reuse कर सकते हैं
    """
    media_id = slide.get("media_id", "")

    # media_id है ही नहीं
    if not media_id or len(str(media_id)) < 5:
        return True  # नया बनाओ

    # Creation time check
    created_at_str = slide.get("media_id_created_at", "")
    if not created_at_str:
        # Time नहीं पता → safe नहीं → fresh बनाओ
        logger.warning(
            f"   ⚠️  media_id {media_id} का creation time नहीं पता "
            f"→ expire माना जाएगा"
        )
        return True

    try:
        created_at = datetime.fromisoformat(created_at_str)
        age_seconds = (datetime.now() - created_at).total_seconds()

        if age_seconds > IG_CONTAINER_EXPIRY_SECONDS:
            logger.warning(
                f"   ⚠️  media_id {media_id} पुराना है "
                f"({age_seconds/60:.1f} मिनट) → fresh बनाएंगे"
            )
            return True
        else:
            logger.info(
                f"   ✅ media_id {media_id} fresh है "
                f"({age_seconds/60:.1f} मिनट पुराना)"
            )
            return False

    except Exception as e:
        logger.warning(f"   ⚠️  Creation time parse error: {e} → expire माना")
        return True


# ============================================================
# SINGLE IMAGE — INSTAGRAM
# ============================================================

def _post_instagram_container(image_url: str, caption: str) -> dict:
    url = f"{META_BASE_URL}/{INSTAGRAM_ACCOUNT_ID}/media"
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            logger.info(
                f"📦 IG container बना रहे हैं (कोशिश {attempt}/{MAX_RETRIES})"
            )
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
            logger.info(
                f"📤 IG पर publish कर रहे हैं (कोशिश {attempt}/{MAX_RETRIES})"
            )
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

        logger.info(
            f"⏳ IG processing के लिए {INSTAGRAM_PROCESSING_WAIT}s रुकते हैं..."
        )
        time.sleep(INSTAGRAM_PROCESSING_WAIT)

        publish_result = _publish_instagram_container(
            container_result["creation_id"]
        )
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
# SINGLE IMAGE — FACEBOOK
# ============================================================

def post_to_facebook(image_url: str, caption: str) -> dict:
    """Facebook single photo post"""
    url = f"{META_BASE_URL}/{FACEBOOK_PAGE_ID}/photos"
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            logger.info(
                f"📤 Facebook पर पोस्ट कर रहे हैं (कोशिश {attempt}/{MAX_RETRIES})"
            )
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
                time.sleep(
                    min(MAX_RETRY_DELAY, INITIAL_RETRY_DELAY * (2 ** attempt))
                )
            elif attempt < MAX_RETRIES:
                time.sleep(INITIAL_RETRY_DELAY * attempt)
            else:
                return {
                    "success": False,
                    "post_id": "",
                    "error":   error["message"]
                }

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
        logger.warning(
            f"⚠️  Caption छोटा किया गया: {len(full_caption)} chars"
        )
    return full_caption


def _log_publishing_report(
    memory: AgentMemory,
    ig_result: dict,
    fb_result: dict,
    duration: float
):
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
# 🎠 CAROUSEL — INSTAGRAM HELPERS
# ============================================================

def _upload_carousel_item(image_bytes: bytes) -> Optional[str]:
    """GCS पर एक slide upload करो"""
    try:
        url = upload_image(image_bytes)
        logger.info(f"   ☁️  Upload हुआ: {url[:60]}...")
        return url
    except Exception as e:
        logger.error(f"   ❌ Upload विफल: {e}")
        return None


def _create_ig_carousel_item(image_url: str) -> Optional[str]:
    """एक carousel item का IG container बनाओ"""
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
            logger.warning(
                f"   ⚠️  Item नहीं बना: {error['message']} "
                f"(code: {error.get('code')})"
            )

            if attempt < MAX_RETRIES:
                time.sleep(INITIAL_RETRY_DELAY * attempt)

        except Exception as e:
            logger.warning(f"   ❌ कोशिश {attempt} विफल: {e}")
            if attempt < MAX_RETRIES:
                time.sleep(INITIAL_RETRY_DELAY * attempt)

    return None


def _wait_for_container_ready(container_id: str, max_wait: int = 60) -> bool:
    """Container FINISHED होने तक wait करो"""
    if not container_id or container_id == "0" or len(str(container_id)) < 5:
        logger.error(f"   ❌ गलत container_id: '{container_id}' — skip")
        return False

    url = f"{META_BASE_URL}/{container_id}"

    # प्रारंभिक wait
    logger.info(f"   ⏳ Container प्रारंभिक wait 10s...")
    time.sleep(10)

    checks_done  = 0
    max_checks   = max_wait // 3
    error_count  = 0

    for attempt in range(max_checks):
        try:
            r = requests.get(
                url,
                params={
                    'fields':       'status_code,status',
                    'access_token': ACCESS_TOKEN
                },
                timeout=REQUEST_TIMEOUT
            )

            if r.status_code == 200:
                data   = r.json()
                status = data.get('status_code', '')
                detail = data.get('status', '')
                logger.info(
                    f"   ⏱️  Container स्थिति: {status} | {detail[:80]}"
                )

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
                logger.warning(
                    f"   ⚠️  Status HTTP {r.status_code}: {r.text[:150]}"
                )

            time.sleep(3)

        except Exception as e:
            logger.warning(f"   Status check विफल: {e}")
            time.sleep(3)

    logger.warning(f"   ⚠️  {max_wait}s में container तैयार नहीं हुआ")
    return False


def _verify_ig_container_alive(container_id: str) -> bool:
    """
    🔧 FIX: Check करो कि saved container_id अभी भी valid है।
    अगर FINISHED नहीं या ERROR है → expired माना जाएगा।

    Returns:
        True  = container valid है
        False = container expire/invalid है
    """
    if not container_id or len(str(container_id)) < 5:
        return False

    try:
        url = f"{META_BASE_URL}/{container_id}"
        r = requests.get(
            url,
            params={
                'fields':       'status_code,status',
                'access_token': ACCESS_TOKEN
            },
            timeout=15
        )

        if r.status_code == 200:
            status = r.json().get('status_code', '')
            logger.info(f"   🔍 Container {container_id[:15]} status: {status}")
            return status == 'FINISHED'
        else:
            logger.warning(
                f"   ⚠️  Container check HTTP {r.status_code} → expired माना"
            )
            return False

    except Exception as e:
        logger.warning(f"   ⚠️  Container check error: {e} → expired माना")
        return False


def _create_ig_carousel_container(media_ids: list, caption: str) -> Optional[str]:
    """
    Carousel container बनाओ।
    5 retries + longer waits + ERROR detection।
    """
    url = f"{META_BASE_URL}/{INSTAGRAM_ACCOUNT_ID}/media"
    MAX_CAROUSEL_RETRIES = 5

    for attempt in range(1, MAX_CAROUSEL_RETRIES + 1):
        try:
            logger.info(
                f"📦 Carousel container बना रहे हैं "
                f"(कोशिश {attempt}/{MAX_CAROUSEL_RETRIES})..."
            )
            logger.info(f"   Media IDs: {media_ids}")
            logger.info(f"   Caption length: {len(caption)} chars")

            if attempt > 1:
                wait = 20 * attempt
                logger.info(
                    f"   ⏳ {wait}s wait (IG को process time चाहिए)..."
                )
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

                if (container_id
                        and container_id != "0"
                        and len(str(container_id)) > 5):

                    logger.info(f"✅ Carousel container: {container_id}")

                    # Quick ERROR check
                    time.sleep(8)
                    check_url = f"{META_BASE_URL}/{container_id}"
                    check_r = requests.get(
                        check_url,
                        params={
                            'fields':       'status_code,status',
                            'access_token': ACCESS_TOKEN
                        },
                        timeout=15
                    )

                    if check_r.status_code == 200:
                        status = check_r.json().get('status_code', '')
                        detail = check_r.json().get('status', '')
                        logger.info(
                            f"   Quick check: {status} | {detail[:100]}"
                        )

                        if status == 'ERROR':
                            if '2207032' in str(detail):
                                logger.error(
                                    f"   ❌ Error 2207032 — "
                                    f"Image format/expired issue, retry..."
                                )
                            else:
                                logger.error(
                                    f"   ❌ Container ERROR: {detail}"
                                )
                            continue  # अगली retry

                    return container_id
                else:
                    logger.error(f"❌ गलत container ID: '{container_id}'")
                    continue

            error = _parse_meta_error(response)
            logger.warning(
                f"⚠️  Container विफल: {error['message']} "
                f"(code: {error.get('code')})"
            )

        except Exception as e:
            logger.warning(f"❌ कोशिश {attempt}: {e}")

    logger.error(
        f"❌ {MAX_CAROUSEL_RETRIES} कोशिशों के बाद भी carousel container नहीं बना"
    )
    return None


# ============================================================
# 🎠 CAROUSEL — INSTAGRAM MAIN
# ============================================================

def post_carousel_to_instagram(
    slides: list,
    caption: str,
    memory: Optional[AgentMemory] = None
) -> dict:
    """
    पूरा Instagram Carousel publish flow।

    🔧 FIX (Error 2207032):
    - image_url → REUSE (GCS URL expire नहीं होता)
    - media_id  → हमेशा FRESH बनाओ (IG containers expire होते हैं)

    Recovery में:
    - अगर image_url saved है → फिर upload नहीं होगा ✅
    - media_id हमेशा fresh बनेगा → Error 2207032 नहीं आएगा ✅
    """
    logger.info("🎠 Instagram Carousel publish शुरू...")
    logger.info(f"   कुल slides: {len(slides)}")

    # 🔧 FIX: Recovery में media_ids को साफ करो
    # पुराने expired media_ids से Error 2207032 आता था
    expired_cleared = 0
    for slide in slides:
        if slide.get("media_id"):
            if _is_media_id_expired(slide):
                old_id = slide.pop("media_id", None)
                slide.pop("media_id_created_at", None)
                expired_cleared += 1
                logger.info(
                    f"   🗑️  Slide {slide.get('slide_number','?')}: "
                    f"Expired media_id {old_id} हटाया"
                )

    if expired_cleared > 0:
        logger.info(
            f"   ♻️  {expired_cleared} expired media_ids साफ किए "
            f"→ fresh containers बनेंगे"
        )
    else:
        logger.info(f"   ✅ सभी slides fresh हैं")

    media_ids  = []
    failed     = []
    session_id = memory.session_id if memory else ""

    # ── हर slide process करो ──────────────────────────────────
    for slide in slides:
        slide_num = slide.get("slide_number", "?")
        logger.info(f"\n   📸 स्लाइड {slide_num}/{len(slides)} process...")

        image_bytes = slide.get("image_bytes")

        # ── Step 1: Image URL (GCS) ──────────────────────────
        # ✅ URL reuse करो — GCS URL expire नहीं होता
        image_url = slide.get("image_url", "")
        if image_url:
            logger.info(f"   ♻️  पुराना URL reuse: {image_url[:60]}...")
        else:
            # Fresh upload
            if not image_bytes:
                logger.warning(
                    f"   ⚠️  Slide {slide_num}: bytes और URL दोनों नहीं → skip"
                )
                failed.append(slide_num)
                continue

            logger.info(f"   ☁️  GCS पर upload हो रहा है...")
            image_url = _upload_carousel_item(image_bytes)
            if not image_url:
                logger.warning(
                    f"   ⚠️  Slide {slide_num} upload विफल → skip"
                )
                failed.append(slide_num)
                continue
            slide["image_url"] = image_url
            logger.info(f"   ✅ Upload हुआ: {image_url[:60]}...")

        # ── Step 2: IG Media Container (हमेशा fresh) ──────────
        # 🔧 FIX: media_id कभी reuse नहीं होगा
        # (expired containers → Error 2207032)
        logger.info(
            f"   🔄 Fresh IG container बना रहे हैं "
            f"(reuse बंद — expiry fix)..."
        )
        time.sleep(CAROUSEL_ITEM_WAIT)
        media_id = _create_ig_carousel_item(image_url)

        if not media_id:
            logger.warning(
                f"   ⚠️  Slide {slide_num} IG item विफल → skip"
            )
            failed.append(slide_num)
            continue

        # Container ready होने का wait
        logger.info(f"   ⏳ Slide {slide_num} container तैयार होने का wait...")
        if not _wait_for_container_ready(media_id, max_wait=30):
            logger.warning(
                f"   ⚠️  Slide {slide_num} container तैयार नहीं → skip"
            )
            failed.append(slide_num)
            continue

        # ✅ नया media_id save करो (timestamp के साथ)
        slide["media_id"]             = media_id
        slide["media_id_created_at"]  = datetime.now().isoformat()
        media_ids.append(media_id)
        logger.info(f"   ✅ Slide {slide_num} ready: {media_id}")

    # ─────────────────────────────────────────────────────────
    # Checkpoint: IG_CONTAINERS_READY
    # ─────────────────────────────────────────────────────────
    if session_id and memory:
        clean_slides = [
            {k: v for k, v in s.items() if k != "image_bytes"}
            for s in slides
        ]
        slides_bytes_map = {
            s["slide_number"]: s["image_bytes"]
            for s in slides if s.get("image_bytes")
        }
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

    # ── कम से कम 2 slides चाहिए ──────────────────────────────
    if len(media_ids) < 2:
        return {
            "success":   False,
            "post_id":   "",
            "error":     (
                f"सिर्फ {len(media_ids)} slides upload हुए, "
                f"कम से कम 2 चाहिए"
            ),
            "media_ids": media_ids
        }

    logger.info(f"\n✅ {len(media_ids)} slides carousel के लिए तैयार")

    # ── Carousel container बनाओ ──────────────────────────────
    time.sleep(3)
    container_id = _create_ig_carousel_container(media_ids, caption)

    if not container_id:
        return {
            "success":   False,
            "post_id":   "",
            "error":     "Carousel container नहीं बना",
            "media_ids": media_ids
        }

    # ── Container FINISHED wait ──────────────────────────────
    logger.info("⏳ Carousel container FINISHED wait...")
    if not _wait_for_container_ready(container_id, max_wait=90):
        return {
            "success":   False,
            "post_id":   "",
            "error":     "Carousel container FINISHED नहीं हुआ",
            "media_ids": media_ids
        }

    # ── Publish ──────────────────────────────────────────────
    publish_result = _publish_instagram_container(container_id)

    if publish_result["success"]:
        logger.info(
            f"🎉 Carousel पब्लिश! Post ID: {publish_result['post_id']}"
        )
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


# ============================================================
# 🎠 CAROUSEL — FACEBOOK ALBUM
# ============================================================

def post_carousel_to_facebook(
    slides: list,
    caption: str,
    memory: Optional[AgentMemory] = None
) -> dict:
    """
    Facebook Album Post।

    🔧 FIX:
    - fb_photo_id reuse करो (FB photos expire नहीं होते जल्दी)
    - अगर fb_photo_id नहीं है → fresh upload
    """
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

        # ✅ FB photo_id reuse (FB IDs expire नहीं होते जल्दी)
        existing_photo_id = slide.get("fb_photo_id", "")
        if existing_photo_id and len(str(existing_photo_id)) > 5:
            logger.info(
                f"   ♻️  Slide {slide_num}: पुराना FB photo_id reuse: "
                f"{existing_photo_id}"
            )
            photo_ids.append(existing_photo_id)
            continue

        # Fresh FB upload
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
                    logger.warning(
                        f"   ⚠️  Slide {slide_num}: photo_id नहीं मिला"
                    )
                    failed.append(slide_num)
            else:
                error = _parse_meta_error(response)
                logger.warning(
                    f"   ⚠️  FB Slide {slide_num} विफल: {error['message']}"
                )
                failed.append(slide_num)

            time.sleep(1)

        except Exception as e:
            logger.warning(f"   ❌ FB Slide {slide_num} error: {e}")
            failed.append(slide_num)

    # ─────────────────────────────────────────────────────────
    # Checkpoint: FB_UPLOADED
    # ─────────────────────────────────────────────────────────
    if memory and memory.session_id:
        clean_slides = [
            {k: v for k, v in s.items() if k != "image_bytes"}
            for s in slides
        ]
        slides_bytes_map = {
            s["slide_number"]: s["image_bytes"]
            for s in slides if s.get("image_bytes")
        }
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

    logger.info(
        f"\n✅ {len(photo_ids)} photos FB पर ready, album बना रहे हैं..."
    )

    # ── FB Feed Post ─────────────────────────────────────────
    try:
        attached_media = [{"media_fbid": pid} for pid in photo_ids]
        url = f"{META_BASE_URL}/{FACEBOOK_PAGE_ID}/feed"

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                logger.info(
                    f"📤 FB album post (कोशिश {attempt}/{MAX_RETRIES})..."
                )
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
                    time.sleep(
                        min(MAX_RETRY_DELAY,
                            INITIAL_RETRY_DELAY * (2 ** attempt))
                    )
                elif attempt < MAX_RETRIES:
                    time.sleep(INITIAL_RETRY_DELAY * attempt)
                else:
                    return {
                        "success":   False,
                        "post_id":   "",
                        "error":     error["message"],
                        "photo_ids": photo_ids
                    }

            except requests.Timeout:
                if attempt < MAX_RETRIES:
                    time.sleep(5)
            except Exception as e:
                if attempt < MAX_RETRIES:
                    time.sleep(INITIAL_RETRY_DELAY * attempt)
                else:
                    return {
                        "success":   False,
                        "post_id":   "",
                        "error":     str(e),
                        "photo_ids": photo_ids
                    }

        return {
            "success":   False,
            "post_id":   "",
            "error":     "अधिकतम retries पार",
            "photo_ids": photo_ids
        }

    except Exception as e:
        return {
            "success":   False,
            "post_id":   "",
            "error":     str(e),
            "photo_ids": photo_ids
        }


# ============================================================
# MAIN AGENT FUNCTION
# ============================================================

def run(memory: AgentMemory) -> AgentMemory:
    """
    Publisher Agent:
    - post_type == "image"    → single image flow
    - post_type == "carousel" → IG carousel + FB album

    🔧 Recovery Fix:
    - image_url  → REUSE ✅ (GCS URL permanent)
    - fb_photo_id → REUSE ✅ (FB photos stay)
    - media_id   → NEVER REUSE ❌ (IG containers expire → Error 2207032)
    """
    logger.info("=" * 55)
    logger.info("=== PUBLISHER AGENT शुरू ===")
    logger.info(f"=== Post Type: {memory.post_type.upper()} ===")
    if memory.is_recovery:
        logger.info(
            f"=== ♻️  RECOVERY MODE (from {memory.resumed_from_stage}) ==="
        )
    logger.info("=" * 55)

    start_time = time.time()

    # Token validation
    is_valid, token_error = _validate_token()
    if not is_valid:
        logger.error(f"❌ Token invalid: {token_error}")
        memory.add_error("publisher", token_error)

    # ═══════════════════════════════════
    # 🎠 CAROUSEL FLOW
    # ═══════════════════════════════════
    if memory.post_type == "carousel":
        logger.info("🎠 CAROUSEL PUBLISH मोड")

        if not memory.carousel_slides:
            memory.add_error("publisher", "Memory में कोई slide नहीं")
            return memory

        # Recovery status log
        if memory.is_recovery:
            if memory.carousel_ig_success:
                logger.info("♻️  IG पहले से publish हो चुका — skip")
            if memory.carousel_fb_success:
                logger.info("♻️  FB पहले से publish हो चुका — skip")

        full_caption = _prepare_caption(
            memory.carousel_caption,
            memory.hashtags or ""
        )
        logger.info(f"📝 Caption: {len(full_caption)} chars")

        # ── Instagram Carousel ────────────────────────────────
        if memory.is_recovery and memory.carousel_ig_success:
            logger.info("\n⏭️  Instagram पहले से publish हो चुका, skip")
            ig_result = {
                "success": True,
                "post_id": memory.carousel_ig_post_id or ""
            }
        else:
            logger.info("\n--- INSTAGRAM पर CAROUSEL पोस्ट ---")
            ig_result = post_carousel_to_instagram(
                slides=memory.carousel_slides,
                caption=full_caption,
                memory=memory
            )
            memory.carousel_ig_success = ig_result["success"]
            memory.carousel_ig_post_id = ig_result.get("post_id", "")
            memory.ig_success          = ig_result["success"]
            memory.ig_post_id          = ig_result.get("post_id", "")

            if not ig_result["success"]:
                memory.add_error(
                    "publisher_ig_carousel",
                    ig_result.get("error", "अज्ञात")
                )

        # ── Facebook Album ────────────────────────────────────
        if memory.is_recovery and memory.carousel_fb_success:
            logger.info("\n⏭️  Facebook पहले से publish हो चुका, skip")
            fb_result = {
                "success": True,
                "post_id": memory.carousel_fb_post_id or ""
            }
        else:
            logger.info("\n--- FACEBOOK पर CAROUSEL ALBUM पोस्ट ---")
            slides_with_urls = [
                s for s in memory.carousel_slides if s.get("image_url")
            ]

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
                memory.fb_success          = fb_result["success"]
                memory.fb_post_id          = fb_result.get("post_id", "")

                if not fb_result["success"]:
                    memory.add_error(
                        "publisher_fb_album",
                        fb_result.get("error", "अज्ञात")
                    )
            else:
                logger.warning("⚠️  Facebook के लिए कोई URL नहीं → skip")
                memory.fb_success = False
                fb_result = {
                    "success": False,
                    "post_id": "",
                    "error":   "URL नहीं मिला"
                }

        # ═══════════════════════════════════════════
        # Recovery Cleanup Logic
        # ═══════════════════════════════════════════
        ig_ok = memory.ig_success or (
            memory.is_recovery and memory.carousel_ig_success
        )
        fb_ok = memory.fb_success or (
            memory.is_recovery and memory.carousel_fb_success
        )

        if ig_ok and fb_ok:
            # ✅ दोनों सफल → checkpoint delete
            logger.info("")
            logger.info("🎉 दोनों platforms सफल — checkpoint delete")
            if memory.session_id:
                delete_checkpoint(memory.session_id)
                logger.info("✅ Recovery data साफ किया")

        elif fb_ok and not ig_ok:
            # FB सफल, IG pending
            logger.info("")
            logger.info("⚠️  सिर्फ FB सफल — IG retry के लिए recovery रख रहे हैं")
            logger.info("💡 Instagram दोबारा try: python main.py recover")
            if memory.session_id:
                clean_slides = [
                    {k: v for k, v in s.items() if k != "image_bytes"}
                    for s in memory.carousel_slides
                ]
                slides_bytes_map = {
                    s["slide_number"]: s["image_bytes"]
                    for s in memory.carousel_slides if s.get("image_bytes")
                }
                save_checkpoint(
                    session_id=memory.session_id,
                    stage="FB_UPLOADED",
                    data={
                        "topic":               memory.topic,
                        "category":            memory.category,
                        "post_type":           "carousel",
                        "carousel_slides":     clean_slides,
                        "carousel_caption":    memory.carousel_caption,
                        "carousel_fb_post_id": memory.carousel_fb_post_id,
                        "carousel_fb_success": True,
                        "carousel_ig_success": False,
                    },
                    slides_bytes=slides_bytes_map
                )
                logger.info("💾 IG retry checkpoint saved")

        elif ig_ok and not fb_ok:
            # IG सफल, FB pending
            logger.info("")
            logger.info("⚠️  सिर्फ IG सफल — FB retry के लिए recovery रख रहे हैं")
            if memory.session_id:
                clean_slides = [
                    {k: v for k, v in s.items() if k != "image_bytes"}
                    for s in memory.carousel_slides
                ]
                slides_bytes_map = {
                    s["slide_number"]: s["image_bytes"]
                    for s in memory.carousel_slides if s.get("image_bytes")
                }
                save_checkpoint(
                    session_id=memory.session_id,
                    stage="IG_CONTAINERS_READY",
                    data={
                        "topic":               memory.topic,
                        "category":            memory.category,
                        "post_type":           "carousel",
                        "carousel_slides":     clean_slides,
                        "carousel_caption":    memory.carousel_caption,
                        "carousel_ig_post_id": memory.carousel_ig_post_id,
                        "carousel_ig_success": True,
                        "carousel_fb_success": False,
                    },
                    slides_bytes=slides_bytes_map
                )

        else:
            # दोनों विफल
            logger.info("")
            logger.info("❌ दोनों विफल — recovery रख रहे हैं")
            logger.info("💡 दोबारा try: python main.py recover")

        duration = time.time() - start_time
        logger.info(f"\n⏱️  Carousel publish में {duration:.1f}s लगे")
        logger.info(
            f"📸 Instagram: {'✅' if ig_ok else '❌'} "
            f"{memory.ig_post_id or 'विफल'}"
        )
        logger.info(
            f"📘 Facebook : {'✅' if fb_ok else '❌'} "
            f"{memory.fb_post_id or 'विफल'}"
        )

    # ═══════════════════════════════════
    # SINGLE IMAGE FLOW
    # ═══════════════════════════════════
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
            memory.add_error(
                "publisher_instagram",
                ig_result.get("error", "अज्ञात")
            )

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
            memory.add_error(
                "publisher_facebook",
                fb_result.get("error", "अज्ञात")
            )

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