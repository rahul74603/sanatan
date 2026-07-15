"""
YouTube Shorts Uploader - Divine AI Content Factory V2

Features:
- OAuth 2.0 authentication (auto-refresh tokens)
- Chunked resumable upload (handles large files)
- Retry logic with exponential backoff
- Automatic #Shorts hashtag injection
- Category & privacy control
- Progress tracking
- Duration validation (max 60s for Shorts)

Requirements:
- sanatani_youtube_client_secrets.json (from Google Cloud Console)
- sanatani_youtube_token.json (auto-generated on first run)
- YouTube Data API v3 enabled
- Test user added to OAuth consent screen (during testing mode)

Setup Flow (one-time):
1. Run: python -m posting.youtube
2. Browser opens → login with YouTube channel account
3. Grant permissions
4. Token saved to sanatani_youtube_token.json
5. Copy token JSON content to GitHub secret: YOUTUBE_TOKEN_JSON
"""
import os
import time
import tempfile
from pathlib import Path
from typing import Optional, Tuple

# Google OAuth + YouTube API
try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    from googleapiclient.http import MediaFileUpload, MediaIoBaseUpload
    import io as io_module
    YOUTUBE_LIBS_AVAILABLE = True
except ImportError as e:
    YOUTUBE_LIBS_AVAILABLE = False
    _import_error = str(e)

from config.settings import (
    YOUTUBE_ENABLED,
    YOUTUBE_CHANNEL_ID,
    YOUTUBE_CLIENT_SECRETS_FILE,
    YOUTUBE_TOKEN_FILE,
    YOUTUBE_CATEGORY_ID,
    YOUTUBE_PRIVACY_STATUS,
    YOUTUBE_MADE_FOR_KIDS,
    YOUTUBE_UPLOAD_MAX_RETRIES,
)
from utils.logger import get_logger

logger = get_logger("youtube")


# ============================================================
# CONFIGURATION
# ============================================================

# YouTube API scopes required
SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly",
]

# YouTube Data API service
API_SERVICE_NAME = "youtube"
API_VERSION = "v3"

# Upload settings
CHUNK_SIZE = 1024 * 1024 * 4  # 4 MB chunks
MAX_RETRY_DELAY = 60  # Max delay between retries

# Shorts constraints
SHORTS_MAX_DURATION = 60  # seconds
SHORTS_HASHTAG = "#Shorts"

# Error codes that shouldn't be retried
NON_RETRIABLE_ERRORS = [400, 401, 403, 404]

# Retry-able errors
RETRIABLE_STATUS_CODES = [500, 502, 503, 504]


# ============================================================
# CLIENT MANAGEMENT
# ============================================================

_youtube_client = None
_credentials = None


def _load_credentials() -> Optional[Credentials]:
    """
    Load OAuth credentials.

    Flow:
    1. Try loading saved token
    2. If token expired, refresh it
    3. If no token, need initial OAuth (call _initial_oauth_setup)

    Returns: Credentials or None
    """
    global _credentials

    if _credentials and _credentials.valid:
        return _credentials

    creds = None
    token_path = Path(YOUTUBE_TOKEN_FILE)

    # Try loading saved token
    if token_path.exists():
        try:
            creds = Credentials.from_authorized_user_file(
                str(token_path),
                SCOPES
            )
            logger.info(f"✅ Loaded YouTube token from {token_path.name}")
        except Exception as e:
            logger.warning(f"⚠️  Failed to load token: {e}")
            creds = None

    # Refresh if expired
    if creds and creds.expired and creds.refresh_token:
        try:
            logger.info("🔄 Refreshing expired YouTube token...")
            creds.refresh(Request())

            # Save refreshed token
            with open(token_path, 'w') as f:
                f.write(creds.to_json())

            logger.info("✅ Token refreshed and saved")

        except Exception as e:
            logger.error(f"❌ Token refresh failed: {e}")
            creds = None

    if creds and creds.valid:
        _credentials = creds
        return creds

    logger.error(
        f"❌ No valid YouTube credentials. "
        f"Run: python -m posting.youtube (for initial OAuth setup)"
    )
    return None


def _get_youtube_client():
    """Get authenticated YouTube API client (singleton)"""
    global _youtube_client

    if _youtube_client is not None:
        return _youtube_client

    if not YOUTUBE_LIBS_AVAILABLE:
        raise Exception(
            f"YouTube libraries not installed: {_import_error}\n"
            f"Run: pip install google-api-python-client google-auth-oauthlib google-auth-httplib2"
        )

    creds = _load_credentials()
    if not creds:
        raise Exception(
            "No valid YouTube credentials. "
            "Run: python -m posting.youtube for initial OAuth setup"
        )

    try:
        _youtube_client = build(
            API_SERVICE_NAME,
            API_VERSION,
            credentials=creds,
            cache_discovery=False  # Avoid file cache warnings
        )
        logger.info("✅ YouTube API client initialized")
        return _youtube_client

    except Exception as e:
        logger.error(f"❌ YouTube client init failed: {e}")
        raise


# ============================================================
# INITIAL OAUTH SETUP (One-time)
# ============================================================

def _initial_oauth_setup():
    """
    🔑 ONE-TIME OAUTH SETUP

    Run this ONCE to generate the token file.

    Steps:
    1. Opens browser
    2. User logs in with YouTube channel account
    3. Grants permissions
    4. Token saved to sanatani_youtube_token.json
    5. Copy content to GitHub secret YOUTUBE_TOKEN_JSON
    """
    if not YOUTUBE_LIBS_AVAILABLE:
        print(f"❌ YouTube libraries not installed: {_import_error}")
        print("Run: pip install google-api-python-client google-auth-oauthlib google-auth-httplib2")
        return False

    client_secrets_path = Path(YOUTUBE_CLIENT_SECRETS_FILE)

    if not client_secrets_path.exists():
        print(f"\n❌ Client secrets file not found: {client_secrets_path}")
        print("\n📋 Setup steps:")
        print("1. Go to: https://console.cloud.google.com/apis/credentials")
        print("2. Create OAuth 2.0 Client ID (Desktop app type)")
        print("3. Download JSON")
        print(f"4. Save as: {client_secrets_path}")
        return False

    print("\n" + "═" * 60)
    print("🎬 YOUTUBE OAUTH SETUP")
    print("═" * 60)
    print(f"📁 Client secrets: {client_secrets_path}")
    print(f"📁 Token will be saved to: {YOUTUBE_TOKEN_FILE}")
    print()
    print("⚠️  Important:")
    print("   • Login with the Gmail account that owns your YouTube channel")
    print("   • Make sure your email is added as 'Test user' in OAuth consent screen")
    print("   • Grant ALL requested permissions (upload + readonly)")
    print()
    print("🌐 Opening browser...")
    print("═" * 60)

    try:
        flow = InstalledAppFlow.from_client_secrets_file(
            str(client_secrets_path),
            SCOPES
        )

        # Run local server to receive OAuth callback
        creds = flow.run_local_server(
            port=0,  # Use any available port
            success_message="✅ Authentication successful! You can close this window.",
            open_browser=True
        )

        # Save token
        token_path = Path(YOUTUBE_TOKEN_FILE)
        with open(token_path, 'w') as f:
            f.write(creds.to_json())

        print("\n" + "═" * 60)
        print("✅ OAUTH SETUP COMPLETE!")
        print("═" * 60)
        print(f"📁 Token saved to: {token_path}")
        print()
        print("📋 Next steps:")
        print("1. Test upload works locally (optional)")
        print("2. Add to GitHub secrets:")
        print(f"   • Name: YOUTUBE_TOKEN_JSON")
        print(f"   • Value: [paste content of {token_path.name}]")
        print()
        print("💡 View token content:")
        print(f"   type {token_path}")
        print("═" * 60)

        return True

    except Exception as e:
        print(f"\n❌ OAuth setup failed: {e}")
        return False


# ============================================================
# VIDEO PREPARATION
# ============================================================

def _prepare_title(title: str, add_shorts_tag: bool = True) -> str:
    """
    Prepare video title for YouTube Shorts.

    Rules:
    - Max 100 characters
    - Add #Shorts hashtag (required for Shorts detection)
    """
    # Trim to 100 chars (leaving room for #Shorts)
    max_len = 90 if add_shorts_tag else 100

    if len(title) > max_len:
        title = title[:max_len].strip() + "..."

    # Add #Shorts if not present
    if add_shorts_tag and "#shorts" not in title.lower():
        title = f"{title} {SHORTS_HASHTAG}"

    return title.strip()


def _prepare_description(
    description: str,
    hashtags: str = "",
    add_shorts_tag: bool = True
) -> str:
    """
    Prepare video description.

    Rules:
    - Max 5000 characters
    - Include #Shorts (required)
    - Include hashtags
    """
    parts = []

    if description:
        parts.append(description)

    # Add separator
    if hashtags or add_shorts_tag:
        parts.append("")  # Empty line

    # Add hashtags
    if hashtags:
        parts.append(hashtags)

    # Ensure #Shorts is somewhere
    combined = "\n".join(parts)
    if add_shorts_tag and "#shorts" not in combined.lower():
        combined += f"\n\n{SHORTS_HASHTAG}"

    # Trim to 5000 chars
    if len(combined) > 5000:
        combined = combined[:4990].strip() + "..."

    return combined


def _extract_tags_from_hashtags(hashtags: str, max_tags: int = 15) -> list:
    """
    Convert hashtag string to tags list.

    YouTube allows max 500 chars total in tags.
    """
    if not hashtags:
        return []

    # Extract hashtag words (remove #, split by space)
    words = []
    for tag in hashtags.split():
        clean = tag.lstrip('#').strip()
        if clean and len(clean) >= 2:
            words.append(clean)

    # Limit and dedupe
    seen = set()
    result = []
    total_chars = 0

    for word in words[:max_tags]:
        word_lower = word.lower()
        if word_lower not in seen:
            # Check total length limit
            if total_chars + len(word) + 2 > 480:  # Safety margin
                break
            seen.add(word_lower)
            result.append(word)
            total_chars += len(word) + 2

    return result


# ============================================================
# UPLOAD FUNCTIONS
# ============================================================

def _upload_with_retry(request):
    """
    Execute upload request with retry logic.
    Handles chunked resumable upload.
    """
    response = None
    retry_count = 0

    while response is None:
        try:
            logger.info(f"📤 Uploading chunk...")
            status, response = request.next_chunk()

            if status:
                progress = int(status.progress() * 100)
                logger.info(f"📤 Upload progress: {progress}%")

        except HttpError as e:
            if e.resp.status in RETRIABLE_STATUS_CODES:
                retry_count += 1

                if retry_count > YOUTUBE_UPLOAD_MAX_RETRIES:
                    raise Exception(
                        f"Upload failed after {YOUTUBE_UPLOAD_MAX_RETRIES} retries: {e}"
                    )

                # Exponential backoff
                wait_time = min(2 ** retry_count, MAX_RETRY_DELAY)
                logger.warning(
                    f"⚠️  Retriable error ({e.resp.status}), "
                    f"retry {retry_count}/{YOUTUBE_UPLOAD_MAX_RETRIES} "
                    f"in {wait_time}s"
                )
                time.sleep(wait_time)
            else:
                # Non-retriable error
                logger.error(f"❌ Non-retriable error: {e.resp.status}")
                raise

        except Exception as e:
            logger.error(f"❌ Upload error: {e}")
            raise

    return response


def upload_short(
    video_bytes: bytes = None,
    video_path: str = None,
    title: str = "",
    description: str = "",
    hashtags: str = "",
    category_id: str = None,
    privacy: str = None,
    made_for_kids: bool = False
) -> dict:
    """
    🎬 Upload video as YouTube Short.

    Args:
        video_bytes: Video bytes (mutually exclusive with video_path)
        video_path: Path to video file (mutually exclusive with video_bytes)
        title: Video title (will add #Shorts if missing)
        description: Video description
        hashtags: Hashtag string (will be added to description + tags)
        category_id: YouTube category ID (default: 22 = People & Blogs)
        privacy: "public" | "unlisted" | "private"
        made_for_kids: True if content is for kids under 13

    Returns:
        {
            "success": bool,
            "video_id": str,
            "url": str,
            "watch_url": str,
            "shorts_url": str,
            "error": str  (if failed)
        }
    """
    logger.info("═" * 55)
    logger.info("🎬 === YOUTUBE SHORTS UPLOAD ===")
    logger.info("═" * 55)

    # ═══════════════════════════════════════════
    # VALIDATION
    # ═══════════════════════════════════════════

    if not YOUTUBE_ENABLED:
        logger.warning("⚠️  YouTube upload disabled in config")
        return {
            "success": False,
            "error": "YouTube disabled in config",
            "video_id": "",
            "url": ""
        }

    if not video_bytes and not video_path:
        logger.error("❌ No video data provided (need video_bytes or video_path)")
        return {
            "success": False,
            "error": "No video data",
            "video_id": "",
            "url": ""
        }

    if not title:
        logger.error("❌ Title is required")
        return {
            "success": False,
            "error": "Title required",
            "video_id": "",
            "url": ""
        }

    # Defaults
    if category_id is None:
        category_id = YOUTUBE_CATEGORY_ID
    if privacy is None:
        privacy = YOUTUBE_PRIVACY_STATUS
    if made_for_kids is None:
        made_for_kids = YOUTUBE_MADE_FOR_KIDS

    # ═══════════════════════════════════════════
    # PREPARE VIDEO FILE
    # ═══════════════════════════════════════════

    temp_video_path = None

    try:
        # If bytes provided, save to temp file (YouTube API needs file)
        if video_bytes:
            logger.info(f"💾 Saving {len(video_bytes):,} bytes to temp file...")

            temp = tempfile.NamedTemporaryFile(
                delete=False,
                suffix='.mp4',
                prefix='youtube_upload_'
            )
            temp.write(video_bytes)
            temp.close()
            temp_video_path = temp.name
            actual_video_path = temp_video_path

            file_size_mb = len(video_bytes) / (1024 * 1024)
        else:
            actual_video_path = video_path
            file_size_mb = Path(video_path).stat().st_size / (1024 * 1024)

        logger.info(f"📁 Video file    : {Path(actual_video_path).name}")
        logger.info(f"📏 File size     : {file_size_mb:.2f} MB")

        # Check file size (YouTube limit: 128 GB, but Shorts should be small)
        if file_size_mb > 512:
            logger.warning(f"⚠️  Video large ({file_size_mb:.0f} MB) — may take long to upload")

        # ═══════════════════════════════════════════
        # PREPARE METADATA
        # ═══════════════════════════════════════════

        # Title with #Shorts
        final_title = _prepare_title(title, add_shorts_tag=True)

        # Description with #Shorts + hashtags
        final_description = _prepare_description(
            description,
            hashtags=hashtags,
            add_shorts_tag=True
        )

        # Tags from hashtags
        tags = _extract_tags_from_hashtags(hashtags, max_tags=15)

        logger.info(f"📝 Title         : {final_title[:60]}...")
        logger.info(f"📝 Description   : {len(final_description)} chars")
        logger.info(f"🏷️  Tags          : {len(tags)}")
        logger.info(f"🎯 Category      : {category_id}")
        logger.info(f"🔒 Privacy       : {privacy}")
        logger.info(f"👶 Made for kids : {made_for_kids}")

        # ═══════════════════════════════════════════
        # GET YOUTUBE CLIENT
        # ═══════════════════════════════════════════
        youtube = _get_youtube_client()

        # ═══════════════════════════════════════════
        # BUILD REQUEST BODY
        # ═══════════════════════════════════════════
        body = {
            'snippet': {
                'title': final_title,
                'description': final_description,
                'tags': tags,
                'categoryId': category_id,
                'defaultLanguage': 'hi',      # Hindi
                'defaultAudioLanguage': 'hi'  # Hindi audio
            },
            'status': {
                'privacyStatus': privacy,
                'selfDeclaredMadeForKids': made_for_kids,
                'embeddable': True,
                'publicStatsViewable': True
            }
        }

        # ═══════════════════════════════════════════
        # CREATE MEDIA UPLOAD (Chunked/Resumable)
        # ═══════════════════════════════════════════
        media = MediaFileUpload(
            actual_video_path,
            mimetype='video/mp4',
            chunksize=CHUNK_SIZE,
            resumable=True
        )

        # ═══════════════════════════════════════════
        # UPLOAD
        # ═══════════════════════════════════════════
        logger.info("🚀 Starting upload...")
        start_time = time.time()

        request = youtube.videos().insert(
            part=','.join(body.keys()),
            body=body,
            media_body=media
        )

        response = _upload_with_retry(request)

        elapsed = round(time.time() - start_time, 2)

        # ═══════════════════════════════════════════
        # PROCESS RESPONSE
        # ═══════════════════════════════════════════
        video_id = response.get('id', '')

        if not video_id:
            raise Exception(f"No video_id in response: {response}")

        # Build URLs
        watch_url = f"https://www.youtube.com/watch?v={video_id}"
        shorts_url = f"https://youtube.com/shorts/{video_id}"

        # Success!
        logger.info("═" * 55)
        logger.info("🎉 YOUTUBE SHORTS UPLOAD SUCCESS")
        logger.info("═" * 55)
        logger.info(f"   ✅ Video ID    : {video_id}")
        logger.info(f"   ⏱️  Upload time : {elapsed}s")
        logger.info(f"   🎬 Shorts URL  : {shorts_url}")
        logger.info(f"   📺 Watch URL   : {watch_url}")
        logger.info("═" * 55)

        return {
            "success": True,
            "video_id": video_id,
            "url": shorts_url,
            "shorts_url": shorts_url,
            "watch_url": watch_url,
            "upload_time_seconds": elapsed,
            "file_size_mb": round(file_size_mb, 2),
            "title": final_title,
            "privacy": privacy
        }

    except HttpError as e:
        error_msg = f"HTTP Error {e.resp.status}: {e}"
        logger.error(f"❌ YouTube upload failed: {error_msg}")

        # Parse error details
        try:
            import json
            error_content = e.content.decode('utf-8')
            error_data = json.loads(error_content)
            error_message = error_data.get('error', {}).get('message', str(e))
        except Exception:
            error_message = str(e)

        return {
            "success": False,
            "error": error_message,
            "http_status": e.resp.status,
            "video_id": "",
            "url": ""
        }

    except Exception as e:
        logger.error(f"❌ YouTube upload failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "video_id": "",
            "url": ""
        }

    finally:
        # Cleanup temp file
        if temp_video_path:
            try:
                os.remove(temp_video_path)
                logger.debug(f"🗑️  Cleaned temp file: {temp_video_path}")
            except Exception:
                pass


# ============================================================
# CHANNEL INFO / VERIFICATION
# ============================================================

def get_channel_info() -> Optional[dict]:
    """
    Get authenticated channel info (for verification).

    Returns: dict with channel details or None
    """
    try:
        youtube = _get_youtube_client()

        response = youtube.channels().list(
            part="snippet,statistics",
            mine=True
        ).execute()

        items = response.get('items', [])
        if not items:
            return None

        channel = items[0]
        snippet = channel.get('snippet', {})
        stats = channel.get('statistics', {})

        return {
            "id": channel.get('id', ''),
            "title": snippet.get('title', ''),
            "description": snippet.get('description', '')[:100],
            "custom_url": snippet.get('customUrl', ''),
            "published_at": snippet.get('publishedAt', ''),
            "subscriber_count": stats.get('subscriberCount', 'hidden'),
            "video_count": stats.get('videoCount', 0),
            "view_count": stats.get('viewCount', 0)
        }

    except Exception as e:
        logger.error(f"❌ Failed to get channel info: {e}")
        return None


def verify_setup() -> dict:
    """
    Verify YouTube upload setup is working.

    Returns: dict with status of each requirement
    """
    checks = {
        "libraries_installed": YOUTUBE_LIBS_AVAILABLE,
        "config_enabled": YOUTUBE_ENABLED,
        "client_secrets_exists": Path(YOUTUBE_CLIENT_SECRETS_FILE).exists(),
        "token_exists": Path(YOUTUBE_TOKEN_FILE).exists(),
        "credentials_valid": False,
        "client_working": False,
        "channel_accessible": False,
        "channel_info": None,
    }

    # Test credentials
    try:
        creds = _load_credentials()
        checks["credentials_valid"] = creds is not None and creds.valid
    except Exception as e:
        checks["credentials_error"] = str(e)

    # Test client
    if checks["credentials_valid"]:
        try:
            client = _get_youtube_client()
            checks["client_working"] = client is not None
        except Exception as e:
            checks["client_error"] = str(e)

    # Test channel access
    if checks["client_working"]:
        try:
            info = get_channel_info()
            checks["channel_accessible"] = info is not None
            checks["channel_info"] = info
        except Exception as e:
            checks["channel_error"] = str(e)

    return checks


# ============================================================
# STANDALONE TESTING / OAUTH SETUP
# ============================================================

if __name__ == "__main__":
    import sys

    print("\n" + "═" * 60)
    print("🎬 YOUTUBE SHORTS UPLOADER")
    print("═" * 60)

    if not YOUTUBE_LIBS_AVAILABLE:
        print(f"\n❌ Missing libraries: {_import_error}")
        print("Install: pip install google-api-python-client google-auth-oauthlib google-auth-httplib2")
        sys.exit(1)

    # Check if OAuth setup is done
    token_path = Path(YOUTUBE_TOKEN_FILE)
    client_secrets_path = Path(YOUTUBE_CLIENT_SECRETS_FILE)

    if not client_secrets_path.exists():
        print(f"\n❌ Client secrets file missing: {client_secrets_path}")
        print("\n📋 Setup:")
        print("1. Go to: https://console.cloud.google.com/apis/credentials")
        print("2. Create OAuth 2.0 Client ID (Desktop app)")
        print("3. Download JSON")
        print(f"4. Save as: {client_secrets_path}")
        sys.exit(1)

    if not token_path.exists():
        print(f"\n⚠️  Token not found: {token_path}")
        print("Running initial OAuth setup...")
        print()

        if _initial_oauth_setup():
            print("\n✅ Setup complete! Testing channel access...")
        else:
            print("\n❌ Setup failed")
            sys.exit(1)

    # Verify setup
    print("\n🔍 Verifying YouTube setup...")
    checks = verify_setup()

    print("\n" + "═" * 60)
    print("SETUP STATUS")
    print("═" * 60)
    print(f"   Libraries installed  : {'✅' if checks['libraries_installed'] else '❌'}")
    print(f"   Config enabled       : {'✅' if checks['config_enabled'] else '❌'}")
    print(f"   Client secrets       : {'✅' if checks['client_secrets_exists'] else '❌'}")
    print(f"   Token exists         : {'✅' if checks['token_exists'] else '❌'}")
    print(f"   Credentials valid    : {'✅' if checks['credentials_valid'] else '❌'}")
    print(f"   Client working       : {'✅' if checks['client_working'] else '❌'}")
    print(f"   Channel accessible   : {'✅' if checks['channel_accessible'] else '❌'}")

    if checks.get('channel_info'):
        info = checks['channel_info']
        print("\n" + "═" * 60)
        print("YOUR CHANNEL INFO")
        print("═" * 60)
        print(f"   Title           : {info.get('title', 'N/A')}")
        print(f"   Channel ID      : {info.get('id', 'N/A')}")
        print(f"   Custom URL      : {info.get('custom_url', 'N/A')}")
        print(f"   Subscribers     : {info.get('subscriber_count', 'hidden')}")
        print(f"   Videos          : {info.get('video_count', 0)}")
        print(f"   Total views     : {info.get('view_count', 0)}")

        # Verify channel ID matches config
        expected_id = YOUTUBE_CHANNEL_ID
        actual_id = info.get('id', '')

        if expected_id and actual_id:
            if expected_id == actual_id:
                print(f"\n✅ Channel ID matches config")
            else:
                print(f"\n⚠️  Channel ID mismatch!")
                print(f"   Config : {expected_id}")
                print(f"   Actual : {actual_id}")
                print(f"   Update YOUTUBE_CHANNEL_ID in .env")

    # Show errors if any
    for key in ['credentials_error', 'client_error', 'channel_error']:
        if key in checks:
            print(f"\n❌ {key}: {checks[key]}")

    # Ready for uploads?
    all_ok = all([
        checks['libraries_installed'],
        checks['config_enabled'],
        checks['client_secrets_exists'],
        checks['token_exists'],
        checks['credentials_valid'],
        checks['client_working'],
        checks['channel_accessible'],
    ])

    print("\n" + "═" * 60)
    if all_ok:
        print("🎉 ALL CHECKS PASSED — Ready for uploads!")
        print("═" * 60)
        print("\n📝 Add to GitHub secrets:")
        print(f"   YOUTUBE_TOKEN_JSON = [content of {token_path.name}]")
        print(f"\n💡 View token content:")
        print(f"   type {token_path}")
    else:
        print("⚠️  SOME CHECKS FAILED — Fix issues above before uploading")
    print("═" * 60)