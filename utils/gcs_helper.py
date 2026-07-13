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

# Content type mapping
CONTENT_TYPES = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
    ".gif": "image/gif"
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
    Format: folder/YYYY-MM-DD/uuid.jpg
    """
    unique_id = uuid.uuid4().hex[:12]  # Shorter than full UUID

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


# ============================================================
# MAIN UPLOAD FUNCTIONS
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
    print("GCS HELPER - STANDALONE TEST")
    print("=" * 60 + "\n")

    # Show bucket stats
    log_bucket_stats()

    print("\n💡 To upload test image:")
    print("   from utils.gcs_helper import upload_image")
    print("   with open('test.jpg', 'rb') as f:")
    print("       url = upload_image(f.read())")