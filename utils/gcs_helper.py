"""
Google Cloud Storage Helper - Production Grade
Features:
- Retry logic with exponential backoff
- Multiple upload strategies (public/signed URL)
- File organization by date
- Automatic cleanup of old files
- Metadata attachment
- Content type detection
- Upload progress tracking
- Bucket management utilities

V2 UPDATE: Added upload_video() for MP4 reel uploads
"""
import uuid
import time
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Tuple
from pathlib import Path

from google.cloud import storage
from google.api_core.exceptions import GoogleAPIError

from config.settings import BUCKET_NAME, PROJECT_ID
from utils.logger import get_logger

logger = get_logger("gcs")


# ============================================================
# CONFIGURATION
# ============================================================

MAX_UPLOAD_RETRIES = 3
RETRY_BASE_DELAY = 2  # seconds
DEFAULT_CACHE_CONTROL = "public, max-age=86400"  # 24 hours

# Video upload settings
VIDEO_UPLOAD_TIMEOUT = 300  # 5 minutes (videos are bigger)
MIN_VIDEO_SIZE = 100_000  # 100 KB minimum
MAX_VIDEO_SIZE = 500_000_000  # 500 MB maximum

# Content type mapping
CONTENT_TYPES = {
    # Images
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
    ".gif": "image/gif",
    # 🆕 Videos
    ".mp4": "video/mp4",
    ".mov": "video/quicktime",
    ".avi": "video/x-msvideo",
    ".webm": "video/webm",
    # 🆕 Audio
    ".mp3": "audio/mpeg",
    ".wav": "audio/wav",
    ".m4a": "audio/mp4",
}


# ============================================================
# CLIENT MANAGEMENT
# ============================================================

_storage_client = None


def _get_client():
    """Get GCS client (singleton pattern)"""
    global _storage_client

    if _storage_client is None:
        try:
            _storage_client = storage.Client(project=PROJECT_ID)
            logger.info(f"✅ GCS client initialized (project: {PROJECT_ID})")
        except Exception as e:
            logger.error(f"❌ GCS client init failed: {e}")
            raise

    return _storage_client


def _get_bucket():
    """Get bucket object"""
    client = _get_client()
    return client.bucket(BUCKET_NAME)


# ============================================================
# UPLOAD HELPERS
# ============================================================

def _generate_filename(folder: str, extension: str = "jpg", use_date_folder: bool = True) -> str:
    """
    Generate organized filename
    Format: folder/YYYY-MM-DD/uuid.ext
    """
    unique_id = uuid.uuid4().hex[:12]  # Shorter than full UUID

    # Ensure extension has no leading dot
    extension = extension.lstrip('.')

    if use_date_folder:
        date_str = datetime.now().strftime("%Y-%m-%d")
        return f"{folder}/{date_str}/{unique_id}.{extension}"

    return f"{folder}/{unique_id}.{extension}"


def _get_content_hash(data: bytes) -> str:
    """Get MD5 hash of data for integrity check"""
    return hashlib.md5(data).hexdigest()


def _detect_content_type(image_bytes: bytes) -> str:
    """Auto-detect image content type from bytes"""
    # Check magic bytes
    if image_bytes[:3] == b'\xff\xd8\xff':
        return "image/jpeg"
    elif image_bytes[:8] == b'\x89PNG\r\n\x1a\n':
        return "image/png"
    elif image_bytes[:4] == b'RIFF' and image_bytes[8:12] == b'WEBP':
        return "image/webp"
    elif image_bytes[:6] in (b'GIF87a', b'GIF89a'):
        return "image/gif"

    # Default
    return "image/jpeg"


def _detect_video_type(video_bytes: bytes) -> str:
    """
    🆕 Auto-detect video content type from bytes.

    Checks magic bytes for common video formats.
    """
    # MP4 (most common) - check for ftyp box
    if len(video_bytes) >= 12:
        if video_bytes[4:8] == b'ftyp':
            return "video/mp4"

    # QuickTime MOV
    if len(video_bytes) >= 12:
        if video_bytes[4:8] == b'moov':
            return "video/quicktime"

    # WebM (Matroska)
    if video_bytes[:4] == b'\x1a\x45\xdf\xa3':
        return "video/webm"

    # AVI
    if video_bytes[:4] == b'RIFF' and video_bytes[8:12] == b'AVI ':
        return "video/x-msvideo"

    # Default to MP4 (most common output from our video builder)
    return "video/mp4"


def _validate_video_bytes(video_bytes: bytes) -> Tuple[bool, str]:
    """
    🆕 Validate video bytes before upload.

    Returns: (is_valid, reason)
    """
    if not video_bytes:
        return False, "No video bytes provided"

    size = len(video_bytes)

    if size < MIN_VIDEO_SIZE:
        return False, f"Video too small: {size} bytes (min: {MIN_VIDEO_SIZE})"

    if size > MAX_VIDEO_SIZE:
        return False, f"Video too large: {size} bytes (max: {MAX_VIDEO_SIZE})"

    # Check MP4 magic bytes (most common)
    if len(video_bytes) >= 12:
        # Standard MP4 signature check
        first_bytes = video_bytes[:12]
        # Valid MP4 has 'ftyp' at offset 4
        if b'ftyp' not in first_bytes and b'moov' not in first_bytes:
            # Could be other format, warn but allow
            logger.warning("⚠️  Video magic bytes unusual, but allowing upload")

    return True, f"Valid video ({size:,} bytes = {size/1024/1024:.1f} MB)"


# ============================================================
# MAIN UPLOAD FUNCTIONS (EXISTING - IMAGE)
# ============================================================

def upload_image(
    image_bytes: bytes,
    folder: str = "posts",
    use_date_folder: bool = True,
    metadata: Optional[dict] = None,
    make_public: bool = True
) -> str:
    """
    Upload image to GCS with retry logic

    Args:
        image_bytes: Image data
        folder: Base folder name
        use_date_folder: Add YYYY-MM-DD subfolder
        metadata: Custom metadata to attach
        make_public: Make publicly accessible

    Returns:
        Public URL of uploaded image
    """
    # Validate
    if not image_bytes:
        raise ValueError("No image bytes provided")

    if len(image_bytes) < 1000:
        raise ValueError(f"Image too small: {len(image_bytes)} bytes")

    # Detect content type
    content_type = _detect_content_type(image_bytes)
    extension = content_type.split('/')[-1].replace('jpeg', 'jpg')

    # Generate filename
    filename = _generate_filename(folder, extension, use_date_folder)

    # Log
    size_kb = len(image_bytes) / 1024
    logger.info(f"☁️  Uploading to GCS: {filename} ({size_kb:.1f} KB)")

    # Retry logic
    errors = []

    for attempt in range(1, MAX_UPLOAD_RETRIES + 1):
        try:
            start_time = time.time()

            bucket = _get_bucket()
            blob = bucket.blob(filename)

            # Set cache control for CDN
            blob.cache_control = DEFAULT_CACHE_CONTROL

            # Set metadata
            if metadata is None:
                metadata = {}

            metadata.update({
                "uploaded_at": datetime.now().isoformat(),
                "size_bytes": str(len(image_bytes)),
                "md5_hash": _get_content_hash(image_bytes)
            })
            blob.metadata = metadata

            # Upload
            blob.upload_from_string(
                image_bytes,
                content_type=content_type,
                timeout=60
            )

            # Make public if requested
            if make_public:
                blob.make_public()
                url = blob.public_url
            else:
                # Return signed URL (valid for 7 days)
                url = blob.generate_signed_url(
                    expiration=timedelta(days=7),
                    method='GET'
                )

            elapsed = round(time.time() - start_time, 2)
            logger.info(f"✅ Uploaded in {elapsed}s: {url}")

            return url

        except GoogleAPIError as e:
            error_msg = f"GCS API error (attempt {attempt}): {e}"
            errors.append(error_msg)
            logger.warning(f"⚠️ {error_msg}")

        except Exception as e:
            error_msg = f"Upload error (attempt {attempt}): {e}"
            errors.append(error_msg)
            logger.warning(f"⚠️ {error_msg}")

        # Exponential backoff
        if attempt < MAX_UPLOAD_RETRIES:
            wait_time = RETRY_BASE_DELAY * (2 ** (attempt - 1))
            logger.info(f"⏳ Retrying in {wait_time}s...")
            time.sleep(wait_time)

    # All retries failed
    error_summary = " | ".join(errors)
    logger.error(f"❌ All upload attempts failed: {error_summary}")
    raise Exception(f"Upload failed after {MAX_UPLOAD_RETRIES} attempts: {error_summary}")


# ============================================================
# 🆕 V2: VIDEO UPLOAD FUNCTION
# ============================================================

def upload_video(
    video_bytes: bytes,
    folder: str = "reels",
    use_date_folder: bool = True,
    metadata: Optional[dict] = None,
    make_public: bool = True
) -> str:
    """
    🆕 Upload video (MP4) to GCS with retry logic.

    Optimized for social media video uploads (Instagram Reels, YT Shorts, FB Reels).

    Args:
        video_bytes: Video data (MP4 preferred)
        folder: Base folder (default: reels)
        use_date_folder: Add YYYY-MM-DD subfolder
        metadata: Custom metadata to attach
        make_public: Make publicly accessible (REQUIRED for social media)

    Returns:
        Public URL of uploaded video (usable by IG/FB/YT APIs)

    Raises:
        ValueError: Invalid video bytes
        Exception: Upload failed after retries
    """
    # ═══════════════════════════════════════════
    # VALIDATION
    # ═══════════════════════════════════════════
    is_valid, reason = _validate_video_bytes(video_bytes)
    if not is_valid:
        logger.error(f"❌ Video validation failed: {reason}")
        raise ValueError(reason)

    logger.info(f"✅ {reason}")

    # ═══════════════════════════════════════════
    # PREPARE UPLOAD
    # ═══════════════════════════════════════════

    # Detect content type
    content_type = _detect_video_type(video_bytes)
    extension = content_type.split('/')[-1]

    # Handle special extensions
    if extension == "quicktime":
        extension = "mov"
    elif extension == "x-msvideo":
        extension = "avi"

    # Generate filename
    filename = _generate_filename(folder, extension, use_date_folder)

    size_mb = len(video_bytes) / (1024 * 1024)
    logger.info(f"☁️  Uploading VIDEO to GCS: {filename} ({size_mb:.2f} MB)")
    logger.info(f"   Content type: {content_type}")

    # ═══════════════════════════════════════════
    # UPLOAD WITH RETRIES
    # ═══════════════════════════════════════════
    errors = []

    for attempt in range(1, MAX_UPLOAD_RETRIES + 1):
        try:
            start_time = time.time()

            logger.info(f"📤 Video upload attempt {attempt}/{MAX_UPLOAD_RETRIES}")

            bucket = _get_bucket()
            blob = bucket.blob(filename)

            # Cache control (longer for videos - they don't change)
            blob.cache_control = "public, max-age=604800"  # 7 days

            # Prepare metadata
            if metadata is None:
                metadata = {}

            metadata.update({
                "uploaded_at": datetime.now().isoformat(),
                "size_bytes": str(len(video_bytes)),
                "size_mb": f"{size_mb:.2f}",
                "md5_hash": _get_content_hash(video_bytes),
                "content_type": content_type,
                "media_type": "video"
            })
            blob.metadata = metadata

            # Upload with extended timeout for videos
            blob.upload_from_string(
                video_bytes,
                content_type=content_type,
                timeout=VIDEO_UPLOAD_TIMEOUT
            )

            # Make public (REQUIRED for social media APIs)
            if make_public:
                blob.make_public()
                url = blob.public_url
                logger.info(f"🌐 Made public")
            else:
                # Signed URL valid for 30 days (longer for videos)
                url = blob.generate_signed_url(
                    expiration=timedelta(days=30),
                    method='GET'
                )
                logger.info(f"🔗 Generated signed URL (30 days)")

            elapsed = round(time.time() - start_time, 2)
            speed_mbps = round((size_mb * 8) / elapsed, 2) if elapsed > 0 else 0

            logger.info("=" * 55)
            logger.info(f"✅ VIDEO UPLOADED SUCCESSFULLY")
            logger.info("=" * 55)
            logger.info(f"   📁 Path      : {filename}")
            logger.info(f"   📏 Size      : {size_mb:.2f} MB")
            logger.info(f"   ⏱️  Time      : {elapsed}s")
            logger.info(f"   🚀 Speed     : {speed_mbps} Mbps")
            logger.info(f"   🌐 URL       : {url}")
            logger.info("=" * 55)

            return url

        except GoogleAPIError as e:
            error_msg = f"GCS API error (attempt {attempt}): {e}"
            errors.append(error_msg)
            logger.warning(f"⚠️ {error_msg}")

        except Exception as e:
            error_msg = f"Upload error (attempt {attempt}): {e}"
            errors.append(error_msg)
            logger.warning(f"⚠️ {error_msg}")

        # Exponential backoff (longer for videos)
        if attempt < MAX_UPLOAD_RETRIES:
            wait_time = RETRY_BASE_DELAY * (3 ** (attempt - 1))  # 2s, 6s, 18s
            logger.info(f"⏳ Retrying in {wait_time}s...")
            time.sleep(wait_time)

    # All retries failed
    error_summary = " | ".join(errors)
    logger.error(f"❌ All video upload attempts failed: {error_summary}")
    raise Exception(f"Video upload failed after {MAX_UPLOAD_RETRIES} attempts: {error_summary}")


def upload_video_from_file(
    video_path: str,
    folder: str = "reels",
    use_date_folder: bool = True,
    metadata: Optional[dict] = None,
    make_public: bool = True
) -> str:
    """
    🆕 Upload video from local file path.

    Convenience function for uploading video files directly from disk.
    """
    video_path = Path(video_path)

    if not video_path.exists():
        raise FileNotFoundError(f"Video file not found: {video_path}")

    file_size = video_path.stat().st_size
    logger.info(f"📁 Reading video file: {video_path.name} ({file_size/1024/1024:.2f} MB)")

    with open(video_path, "rb") as f:
        video_bytes = f.read()

    # Add original filename to metadata
    if metadata is None:
        metadata = {}
    metadata["original_filename"] = video_path.name
    metadata["original_size"] = str(file_size)

    return upload_video(
        video_bytes=video_bytes,
        folder=folder,
        use_date_folder=use_date_folder,
        metadata=metadata,
        make_public=make_public
    )


# ============================================================
# UPLOAD FILE (GENERIC - EXISTING)
# ============================================================

def upload_file(
    file_path: str,
    folder: str = "files",
    use_date_folder: bool = True
) -> str:
    """Upload a file from disk"""
    file_path = Path(file_path)

    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    with open(file_path, "rb") as f:
        file_bytes = f.read()

    return upload_image(
        image_bytes=file_bytes,
        folder=folder,
        use_date_folder=use_date_folder,
        metadata={"original_filename": file_path.name}
    )


# ============================================================
# DELETE / CLEANUP
# ============================================================

def delete_blob(blob_name: str) -> bool:
    """Delete a single blob"""
    try:
        bucket = _get_bucket()
        blob = bucket.blob(blob_name)
        blob.delete()
        logger.info(f"🗑️  Deleted: {blob_name}")
        return True
    except Exception as e:
        logger.warning(f"Delete failed for {blob_name}: {e}")
        return False


def cleanup_old_files(folder: str = "posts", days_old: int = 30) -> int:
    """
    Delete files older than X days
    Returns count of deleted files
    """
    logger.info(f"🧹 Cleaning up {folder}/ files older than {days_old} days")

    try:
        bucket = _get_bucket()
        cutoff = datetime.now().replace(tzinfo=None) - timedelta(days=days_old)

        deleted_count = 0

        for blob in bucket.list_blobs(prefix=f"{folder}/"):
            if blob.time_created:
                # Remove timezone for comparison
                blob_time = blob.time_created.replace(tzinfo=None)

                if blob_time < cutoff:
                    try:
                        blob.delete()
                        deleted_count += 1
                        logger.debug(f"Deleted old file: {blob.name}")
                    except Exception as e:
                        logger.warning(f"Failed to delete {blob.name}: {e}")

        logger.info(f"✅ Cleanup complete: {deleted_count} files deleted")
        return deleted_count

    except Exception as e:
        logger.error(f"Cleanup failed: {e}")
        return 0


def cleanup_old_reels(days_old: int = 7) -> int:
    """
    🆕 Cleanup old reels (shorter retention than images).
    Videos are larger, so we keep them for less time.
    """
    return cleanup_old_files(folder="reels", days_old=days_old)


# ============================================================
# STATISTICS
# ============================================================

def get_bucket_stats() -> dict:
    """Get bucket statistics"""
    try:
        bucket = _get_bucket()

        total_size = 0
        total_files = 0
        folders = {}

        for blob in bucket.list_blobs():
            total_files += 1
            total_size += blob.size or 0

            # Group by folder
            folder = blob.name.split('/')[0] if '/' in blob.name else 'root'
            if folder not in folders:
                folders[folder] = {"count": 0, "size": 0}
            folders[folder]["count"] += 1
            folders[folder]["size"] += blob.size or 0

        return {
            "bucket_name": BUCKET_NAME,
            "total_files": total_files,
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "total_size_gb": round(total_size / (1024 * 1024 * 1024), 3),
            "folders": folders
        }

    except Exception as e:
        logger.error(f"Stats fetch failed: {e}")
        return {}


def log_bucket_stats():
    """Print beautiful bucket stats"""
    stats = get_bucket_stats()

    if not stats:
        logger.warning("Could not fetch bucket stats")
        return

    logger.info("┌─────────────────────────────────────────┐")
    logger.info("│      ☁️  GCS BUCKET STATS               │")
    logger.info("├─────────────────────────────────────────┤")
    logger.info(f"│ Bucket : {stats['bucket_name']}")
    logger.info(f"│ Files  : {stats['total_files']}")
    logger.info(f"│ Size   : {stats['total_size_mb']} MB ({stats['total_size_gb']} GB)")
    logger.info("├─────────────────────────────────────────┤")
    logger.info("│ 📁 FOLDERS:")

    for folder, info in stats.get("folders", {}).items():
        size_mb = info["size"] / (1024 * 1024)
        logger.info(f"│   {folder:15} : {info['count']:5} files ({size_mb:.1f} MB)")

    logger.info("└─────────────────────────────────────────┘")


# ============================================================
# STANDALONE TESTING
# ============================================================

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("GCS HELPER - STANDALONE TEST (V2)")
    print("=" * 60 + "\n")

    # Show bucket stats
    log_bucket_stats()

    print("\n💡 UPLOAD FUNCTIONS AVAILABLE:")
    print("\n1. Upload image:")
    print("   from utils.gcs_helper import upload_image")
    print("   with open('test.jpg', 'rb') as f:")
    print("       url = upload_image(f.read())")

    print("\n2. 🆕 Upload video (MP4):")
    print("   from utils.gcs_helper import upload_video")
    print("   with open('reel.mp4', 'rb') as f:")
    print("       url = upload_video(f.read(), folder='reels')")

    print("\n3. 🆕 Upload video from file path:")
    print("   from utils.gcs_helper import upload_video_from_file")
    print("   url = upload_video_from_file('reel.mp4', folder='reels')")

    # Optional: Test with sample video if exists
    from pathlib import Path
    test_video_paths = [
        "test_reel.mp4",
        "test_concat_basic.mp4",
        "logs/videos/reel_test.mp4"
    ]

    for test_path in test_video_paths:
        if Path(test_path).exists():
            print(f"\n🧪 Test video found: {test_path}")
            print(f"   File size: {Path(test_path).stat().st_size / 1024 / 1024:.2f} MB")
            print(f"\n   To upload, run:")
            print(f"   python -c \"from utils.gcs_helper import upload_video_from_file; url = upload_video_from_file('{test_path}'); print(url)\"")
            break