"""
Music Manager V2 - Fixed Voice Duration Bug

CRITICAL FIX (V2):
- Voice duration ab correctly detect hoti hai (was using pydub's unreliable len())
- Falls back to passed voice_duration parameter (from TTS engine)
- Validates duration before mixing
- Music duration always matches actual voice length

FEATURES (ALL PRESERVED FROM V1):
- Auto-select BG music from assets/music/ folder
- Category/mood-based selection (matches file names)
- Voice + Music mixing (voice dominant, music at 15%)
- Auto-loop music if shorter than voice
- Auto-truncate music if longer than voice
- Fade in/out for music (2s each)
- Graceful fallback if no music files present
- V4: Dynamic volume per category

User provides music in assets/music/ folder.
Recommended naming:
- peaceful_1.mp3, peaceful_2.mp3 (for peaceful moods)
- powerful_1.mp3 (for powerful moods)
- devotional_1.mp3 (general devotional)
- festive_1.mp3 (festivals)
"""
import io
import random
from pathlib import Path
from typing import Optional, Tuple

from pydub import AudioSegment

from config.settings import (
    REEL_MUSIC_ENABLED,
    REEL_MUSIC_VOLUME,
    REEL_MUSIC_FOLDER,
)
from utils.logger import get_logger

logger = get_logger("music_manager")


# ============================================================
# CONFIGURATION
# ============================================================

MUSIC_FOLDER = Path(REEL_MUSIC_FOLDER)

# Volume settings (in dB)
# Voice: 0 dB (unchanged)
# Music: -20 dB roughly = 10% volume, -14 dB = ~20%
MUSIC_VOLUME_DB = -20  # 10% volume (music quiet, voice dominant)

# Fade settings
MUSIC_FADE_IN_MS = 2000   # 2 seconds fade in
MUSIC_FADE_OUT_MS = 2000  # 2 seconds fade out

# Supported audio formats
SUPPORTED_FORMATS = ['.mp3', '.wav', '.m4a', '.ogg', '.aac']

# 🆕 V4: Category → Music keyword mapping + mood intensity
CATEGORY_MUSIC_KEYWORDS = {
    "krishna": {
        "keywords": ["peaceful", "devotional", "melodic", "flute", "soft"],
        "mood": "soft",
        "volume_adjust": -22  # Softer for Krishna (voice dominant)
    },
    "shiva": {
        "keywords": ["powerful", "mystical", "cosmic", "meditation", "deep"],
        "mood": "intense",
        "volume_adjust": -18  # Slightly louder for Shiva (dramatic)
    },
    "hanuman": {
        "keywords": ["powerful", "energetic", "devotional", "heroic"],
        "mood": "energetic",
        "volume_adjust": -18
    },
    "ganesha": {
        "keywords": ["auspicious", "festive", "devotional", "joyful"],
        "mood": "joyful",
        "volume_adjust": -20
    },
    "durga": {
        "keywords": ["powerful", "energetic", "festive", "warrior"],
        "mood": "intense",
        "volume_adjust": -18
    },
    "ram": {
        "keywords": ["devotional", "peaceful", "royal", "noble"],
        "mood": "noble",
        "volume_adjust": -20
    },
    "spiritual_nature": {
        "keywords": ["peaceful", "meditation", "ambient", "nature"],
        "mood": "calm",
        "volume_adjust": -24  # Very soft (meditation feel)
    },
    "motivational": {
        "keywords": ["energetic", "uplifting", "powerful", "triumph"],
        "mood": "energetic",
        "volume_adjust": -16  # Louder for motivation
    },
    "temple": {
        "keywords": ["devotional", "peaceful", "sacred", "bells"],
        "mood": "sacred",
        "volume_adjust": -22
    },
    "daily_wisdom": {
        "keywords": ["peaceful", "contemplative", "ambient", "soft"],
        "mood": "calm",
        "volume_adjust": -24
    },
    "festival": {
        "keywords": ["festive", "celebration", "joyful", "dhol"],
        "mood": "festive",
        "volume_adjust": -16  # Louder for festivals
    },
    "festival_moments": {
        "keywords": ["festive", "celebration", "joyful"],
        "mood": "festive",
        "volume_adjust": -16
    },
}


# ============================================================
# MUSIC FILE DISCOVERY
# ============================================================

def _get_available_music_files() -> list:
    """
    Get list of all available music files in music folder.

    Returns:
        List of Path objects for all supported audio files
    """
    if not MUSIC_FOLDER.exists():
        logger.warning(f"⚠️  Music folder not found: {MUSIC_FOLDER}")
        return []

    music_files = []
    for ext in SUPPORTED_FORMATS:
        music_files.extend(MUSIC_FOLDER.glob(f"*{ext}"))
        music_files.extend(MUSIC_FOLDER.glob(f"*{ext.upper()}"))

    return music_files


def _select_music_file(category: str = "", mood: str = "") -> Optional[Path]:
    """
    Select appropriate music file based on category/mood.

    Strategy:
    1. Get keywords for category
    2. Find files matching keywords
    3. If no match, use random music file
    4. If no music files at all, return None

    Args:
        category: Content category
        mood: Optional mood hint

    Returns:
        Path to selected music file, or None if no music available
    """
    music_files = _get_available_music_files()

    if not music_files:
        logger.warning("⚠️  No music files found in assets/music/")
        return None

    logger.info(f"🎵 Found {len(music_files)} music files")

    # 🆕 V4: Get keywords from new dict structure
    cat_config = CATEGORY_MUSIC_KEYWORDS.get(category, {})
    if isinstance(cat_config, dict):
        keywords = cat_config.get("keywords", [])
    else:
        keywords = cat_config  # Backward compat if old format

    # Also include mood keywords
    if mood:
        mood_lower = mood.lower()
        for mood_word in ["peaceful", "powerful", "festive", "devotional", "energetic"]:
            if mood_word in mood_lower:
                keywords.append(mood_word)

    # Filter files matching keywords
    matching_files = []
    for music_file in music_files:
        filename_lower = music_file.stem.lower()
        for keyword in keywords:
            if keyword.lower() in filename_lower:
                matching_files.append(music_file)
                break

    # Select from matches, or random if no matches
    if matching_files:
        selected = random.choice(matching_files)
        logger.info(f"🎵 Selected matching music: {selected.name} (category: {category})")
    else:
        selected = random.choice(music_files)
        logger.info(f"🎵 Selected random music: {selected.name} (no category match)")

    return selected


# ============================================================
# AUDIO LOADING
# ============================================================

def _load_audio_from_file(file_path: Path) -> Optional[AudioSegment]:
    """
    Load audio file as AudioSegment.

    Args:
        file_path: Path to audio file

    Returns:
        AudioSegment or None if loading fails
    """
    try:
        file_ext = file_path.suffix.lower()

        # Map extension to pydub format
        format_map = {
            '.mp3': 'mp3',
            '.wav': 'wav',
            '.m4a': 'mp4',
            '.ogg': 'ogg',
            '.aac': 'aac',
        }

        fmt = format_map.get(file_ext, 'mp3')

        audio = AudioSegment.from_file(str(file_path), format=fmt)

        logger.debug(f"✅ Loaded audio: {file_path.name} ({audio.duration_seconds:.1f}s)")

        return audio

    except Exception as e:
        logger.error(f"❌ Failed to load audio {file_path.name}: {e}")
        return None


def _load_audio_from_bytes(audio_bytes: bytes, format: str = "mp3") -> Optional[AudioSegment]:
    """Load audio from bytes as AudioSegment"""
    try:
        audio = AudioSegment.from_file(io.BytesIO(audio_bytes), format=format)
        return audio
    except Exception as e:
        logger.error(f"❌ Failed to load audio from bytes: {e}")
        return None


# ============================================================
# 🆕 V2: DURATION VALIDATION (Critical Fix)
# ============================================================

def _get_reliable_voice_duration(
    voice_audio: AudioSegment,
    voice_duration_hint: float = 0
) -> int:
    """
    🆕 V2: Get reliable voice duration in milliseconds.
    
    pydub sometimes reports wrong duration for MP3 files (VBR issues).
    We use the passed hint from TTS engine (which knows real duration)
    as fallback if pydub's value seems suspicious.
    
    Args:
        voice_audio: AudioSegment from pydub
        voice_duration_hint: Actual duration from TTS engine (seconds)
    
    Returns:
        Reliable duration in milliseconds
    """
    pydub_duration_ms = len(voice_audio)
    pydub_duration_sec = pydub_duration_ms / 1000.0
    
    logger.info(f"🎤 pydub reports voice: {pydub_duration_sec:.1f}s")
    
    # If no hint provided, trust pydub
    if voice_duration_hint <= 0:
        logger.info(f"   ⚠️  No hint provided, using pydub value")
        return pydub_duration_ms
    
    logger.info(f"🎯 TTS engine says voice: {voice_duration_hint:.1f}s")
    
    # Check if pydub's value seems reliable
    # Voice should be within 15% of TTS engine's estimate
    hint_ms = int(voice_duration_hint * 1000)
    diff_ratio = abs(pydub_duration_ms - hint_ms) / hint_ms
    
    if diff_ratio > 0.15:
        # More than 15% difference — pydub is wrong (common MP3 VBR issue)
        logger.warning(
            f"⚠️  pydub duration seems wrong! "
            f"pydub={pydub_duration_sec:.1f}s vs TTS={voice_duration_hint:.1f}s "
            f"(diff: {diff_ratio*100:.0f}%). Using TTS engine value."
        )
        return hint_ms
    
    # Values are close enough, use pydub
    logger.info(f"   ✅ pydub value acceptable (diff: {diff_ratio*100:.0f}%)")
    return pydub_duration_ms


# ============================================================
# AUDIO MANIPULATION
# ============================================================

def _adjust_music_to_duration(
    music: AudioSegment,
    target_duration_ms: int
) -> AudioSegment:
    """
    Adjust music to match target duration.

    - If music shorter than target → loop
    - If music longer than target → truncate

    Args:
        music: Music AudioSegment
        target_duration_ms: Target duration in milliseconds

    Returns:
        AudioSegment matching target duration
    """
    music_duration_ms = len(music)

    if music_duration_ms >= target_duration_ms:
        # Music longer - truncate
        return music[:target_duration_ms]

    # Music shorter - loop until we exceed target
    loops_needed = (target_duration_ms // music_duration_ms) + 1
    looped = music * loops_needed

    # Truncate to exact target
    return looped[:target_duration_ms]


def _apply_music_fades(music: AudioSegment) -> AudioSegment:
    """Apply fade in and fade out to music"""
    return music.fade_in(MUSIC_FADE_IN_MS).fade_out(MUSIC_FADE_OUT_MS)


def _lower_music_volume(music: AudioSegment, volume_db: int = MUSIC_VOLUME_DB, category: str = "") -> AudioSegment:
    """
    🆕 V4: Dynamic volume based on category.
    
    Krishna/meditation = softer music (voice dominant)
    Motivational/festival = louder music (energy)
    """
    # V4: Category-specific volume
    if category:
        cat_config = CATEGORY_MUSIC_KEYWORDS.get(category, {})
        if isinstance(cat_config, dict) and "volume_adjust" in cat_config:
            volume_db = cat_config["volume_adjust"]
            logger.info(f"🔊 Dynamic volume for {category}: {volume_db} dB")

    return music + volume_db


# ============================================================
# 🆕 V2: EXTEND VOICE TO MATCH DURATION (Critical Fix)
# ============================================================

def _extend_voice_if_needed(
    voice_audio: AudioSegment,
    target_duration_ms: int
) -> AudioSegment:
    """
    🆕 V2: If voice is shorter than target duration,
    pad with silence at the end (natural pause).
    
    This ensures video-voice sync doesn't fail.
    """
    voice_duration_ms = len(voice_audio)
    
    if voice_duration_ms >= target_duration_ms:
        return voice_audio  # Already long enough
    
    # Add silence to extend voice
    silence_needed_ms = target_duration_ms - voice_duration_ms
    logger.info(
        f"🔧 Extending voice with {silence_needed_ms/1000:.1f}s silence "
        f"({voice_duration_ms/1000:.1f}s → {target_duration_ms/1000:.1f}s)"
    )
    
    silence = AudioSegment.silent(duration=silence_needed_ms)
    return voice_audio + silence


# ============================================================
# MAIN MIXING FUNCTION (V2 FIXED)
# ============================================================

def mix_voice_with_music(
    voice_bytes: bytes,
    voice_duration: float,
    category: str = "",
    mood: str = ""
) -> Tuple[bytes, str]:
    """
    Mix TTS voice with BG music.

    Voice dominant, music at ~10% volume in background.
    
    V2 FIXES:
    - Reliable voice duration (uses TTS engine hint as source of truth)
    - Voice extension if pydub reports wrong duration
    - Better logging for debugging

    Args:
        voice_bytes: TTS voice MP3 bytes
        voice_duration: Voice duration in seconds (from TTS engine - RELIABLE)
        category: For music selection
        mood: For music selection (optional)

    Returns:
        Tuple of (mixed_audio_mp3_bytes, music_file_name_used)

    If music disabled or unavailable, returns voice as-is.
    """
    logger.info("=" * 55)
    logger.info("=== MUSIC MANAGER V2 - MIX ===")
    logger.info("=" * 55)
    logger.info(f"📥 Voice bytes: {len(voice_bytes):,}")
    logger.info(f"📥 Voice duration hint: {voice_duration:.1f}s")

    # Check if music enabled
    if not REEL_MUSIC_ENABLED:
        logger.info("ℹ️  BG music disabled in config")
        return voice_bytes, ""

    # Load voice
    voice_audio = _load_audio_from_bytes(voice_bytes, format="mp3")

    if voice_audio is None:
        logger.error("❌ Failed to load voice audio")
        return voice_bytes, ""

    # 🚨 V2 CRITICAL FIX: Get reliable voice duration
    voice_duration_ms = _get_reliable_voice_duration(
        voice_audio=voice_audio,
        voice_duration_hint=voice_duration
    )
    
    logger.info(f"✅ Final voice duration: {voice_duration_ms/1000:.1f}s")

    # 🚨 V2 CRITICAL FIX: Extend voice if pydub loaded less than expected
    voice_audio = _extend_voice_if_needed(voice_audio, voice_duration_ms)

    # Select music file
    music_file = _select_music_file(category=category, mood=mood)

    if music_file is None:
        logger.warning("⚠️  No music available - returning voice only")
        # Still export the (possibly extended) voice
        try:
            buf = io.BytesIO()
            voice_audio.export(buf, format="mp3", bitrate="128k")
            return buf.getvalue(), ""
        except Exception:
            return voice_bytes, ""

    # Load music
    music_audio = _load_audio_from_file(music_file)

    if music_audio is None:
        logger.warning("⚠️  Failed to load music - returning voice only")
        return voice_bytes, ""

    # Adjust music duration to match voice (now using RELIABLE duration)
    music_audio = _adjust_music_to_duration(music_audio, voice_duration_ms)
    logger.info(f"🎵 Music adjusted to: {len(music_audio)/1000:.1f}s")

    # Apply fades
    music_audio = _apply_music_fades(music_audio)

    # 🆕 V4: Dynamic volume based on category
    music_audio = _lower_music_volume(music_audio, category=category)
    logger.info(f"🔉 Music volume applied for category: {category}")

    # Mix voice + music (overlay)
    try:
        logger.info("🎚️  Mixing voice + music...")
        mixed = voice_audio.overlay(music_audio)

        # Export to MP3 bytes
        buf = io.BytesIO()
        mixed.export(
            buf,
            format="mp3",
            bitrate="128k",
            parameters=["-ac", "2"]  # Stereo
        )
        mixed_bytes = buf.getvalue()

        logger.info(f"✅ Mixed audio: {len(mixed_bytes):,} bytes")
        logger.info(f"   Final duration: {len(mixed)/1000:.1f}s")
        logger.info(f"   Music file used: {music_file.name}")
        logger.info("=" * 55)

        return mixed_bytes, music_file.name

    except Exception as e:
        logger.error(f"❌ Mixing failed: {e}")
        return voice_bytes, ""


# ============================================================
# UTILITY: LIST AVAILABLE MUSIC
# ============================================================

def list_available_music() -> list:
    """
    Get list of all available music files with details.

    Returns:
        List of dicts: [{"name": "...", "path": "...", "size_mb": ...}]
    """
    files = _get_available_music_files()

    music_list = []
    for f in files:
        try:
            size_bytes = f.stat().st_size
            music_list.append({
                "name": f.name,
                "path": str(f),
                "size_mb": round(size_bytes / (1024 * 1024), 2),
            })
        except Exception:
            continue

    return music_list


def check_music_folder() -> dict:
    """
    Check music folder status and available files.

    Returns:
        Status dict with counts and warnings
    """
    status = {
        "folder_exists": MUSIC_FOLDER.exists(),
        "folder_path": str(MUSIC_FOLDER.absolute()),
        "total_files": 0,
        "total_size_mb": 0.0,
        "categories_covered": [],
        "missing_categories": [],
        "files": [],
    }

    if not status["folder_exists"]:
        return status

    files = _get_available_music_files()
    status["total_files"] = len(files)

    total_bytes = sum(f.stat().st_size for f in files)
    status["total_size_mb"] = round(total_bytes / (1024 * 1024), 2)

    # Check which categories have matching files
    for category, config in CATEGORY_MUSIC_KEYWORDS.items():
        # Handle both new dict format and old list format
        if isinstance(config, dict):
            keywords = config.get("keywords", [])
        else:
            keywords = config
        
        has_match = False
        for f in files:
            if any(kw.lower() in f.stem.lower() for kw in keywords):
                has_match = True
                break

        if has_match:
            status["categories_covered"].append(category)
        else:
            status["missing_categories"].append(category)

    # Add file details
    for f in files:
        status["files"].append({
            "name": f.name,
            "size_mb": round(f.stat().st_size / (1024 * 1024), 2)
        })

    return status


# ============================================================
# STANDALONE TESTING
# ============================================================

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("MUSIC MANAGER V2 - STANDALONE TEST")
    print("=" * 60 + "\n")

    # Check music folder
    print("📁 Checking music folder...")
    status = check_music_folder()

    print(f"   Folder: {status['folder_path']}")
    print(f"   Exists: {status['folder_exists']}")
    print(f"   Total files: {status['total_files']}")
    print(f"   Total size: {status['total_size_mb']} MB")

    if status['total_files'] == 0:
        print("\n⚠️  NO MUSIC FILES FOUND!")
        print(f"   Please add MP3 files to: {status['folder_path']}")
        print("\n   Recommended files:")
        print("   - peaceful_1.mp3 (for Krishna, peaceful topics)")
        print("   - powerful_1.mp3 (for Shiva, motivational)")
        print("   - devotional_1.mp3 (general devotional)")
        print("   - festive_1.mp3 (for festivals)")
        print("\n   Where to get free devotional music:")
        print("   - YouTube Audio Library")
        print("   - Pixabay Music")
        print("   - Free Music Archive")
        exit(0)

    print("\n📋 Available music files:")
    for f in status['files']:
        print(f"   • {f['name']} ({f['size_mb']} MB)")

    print(f"\n✅ Categories covered ({len(status['categories_covered'])}):")
    for cat in status['categories_covered']:
        print(f"   • {cat}")

    if status['missing_categories']:
        print(f"\n⚠️  Categories without matching music ({len(status['missing_categories'])}):")
        for cat in status['missing_categories']:
            print(f"   • {cat}")

    # Test mixing if we have a test voice file
    test_voice_file = Path("test_reel_voice.mp3")
    if test_voice_file.exists():
        print(f"\n🎤 Test mixing with {test_voice_file.name}...")

        with open(test_voice_file, 'rb') as f:
            voice_bytes = f.read()

        # Estimate duration (very rough)
        voice_duration = len(voice_bytes) / 16000  # ~128kbps

        mixed_bytes, music_used = mix_voice_with_music(
            voice_bytes=voice_bytes,
            voice_duration=voice_duration,
            category="krishna"
        )

        if music_used:
            output_file = "test_mixed_audio.mp3"
            with open(output_file, 'wb') as f:
                f.write(mixed_bytes)
            print(f"\n✅ Mixed audio saved: {output_file}")
            print(f"   Music used: {music_used}")
            print(f"   Original voice: {len(voice_bytes):,} bytes")
            print(f"   Mixed audio: {len(mixed_bytes):,} bytes")
            print(f"\n💡 Play mixed audio: start {output_file}")
        else:
            print("\n⚠️  Mixing skipped (no music available)")
    else:
        print(f"\nℹ️  No test voice file found: {test_voice_file}")
        print("   Run tts_engine.py first to generate test_reel_voice.mp3")

    print("\n" + "=" * 60)
    print("V2 CRITICAL FIXES:")
    print("=" * 60)
    print("   1. Reliable voice duration (uses TTS engine hint)")
    print("   2. Voice extension with silence if pydub reports wrong duration")
    print("   3. Better logging for debugging")
    print("   4. Fixes 20s video-voice cut bug")
    print("=" * 60)
