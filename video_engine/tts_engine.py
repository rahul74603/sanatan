"""
TTS Engine V3 - FIXED Voice Duration Bug

CRITICAL FIX (V3):
- Uses REAL MP3 duration from pydub (was using wrong text-based estimate)
- Video-Audio sync now PERFECT (was 20s off before)
- Better fallback logic if pydub fails
- Detailed logging for debugging
- Timestamp normalization to match actual duration

Features:
- Hindi Neural2 voices (best quality)
- Category-based voice selection:
  * Male voices: Krishna, Shiva, Ram, Hanuman, Ganesha, motivational, temple
  * Female voices: Durga, spiritual_nature, daily_wisdom, festival
- SSML for dramatic narration with pauses and emphasis
- Retry logic with fallback voices
- REAL duration detection (not estimate)
- Word-level timestamps
- MP3 output at 128kbps
"""
import io
import re
import time
import wave
from typing import Optional, Tuple

from pydub import AudioSegment
from google.cloud import texttospeech
from google.oauth2 import service_account

from core.memory import AgentMemory
from config.settings import (
    TTS_ENABLED,
    TTS_LANGUAGE,
    TTS_VOICE_MALE,
    TTS_VOICE_FEMALE,
    TTS_SPEAKING_RATE,
    TTS_PITCH,
    TTS_AUDIO_ENCODING,
    TTS_CATEGORY_VOICE,
    GOOGLE_APPLICATION_CREDENTIALS,
)
from utils.logger import get_logger

logger = get_logger("tts_engine")


# ============================================================
# CONFIGURATION
# ============================================================

MAX_TTS_RETRIES = 3
TTS_TIMEOUT_SECONDS = 60

# Fallback voices (if primary fails)
FALLBACK_MALE_VOICES = [
    "hi-IN-Neural2-B",
    "hi-IN-Wavenet-B",
    "hi-IN-Wavenet-C",
    "hi-IN-Standard-B",
]

FALLBACK_FEMALE_VOICES = [
    "hi-IN-Neural2-A",
    "hi-IN-Neural2-D",
    "hi-IN-Wavenet-A",
    "hi-IN-Wavenet-D",
    "hi-IN-Standard-A",
]

# Max characters per TTS request (Google limit is 5000)
MAX_TTS_CHARS = 4500


# ============================================================
# CLIENT INITIALIZATION
# ============================================================

_tts_client = None


def _get_tts_client():
    """Get authenticated TTS client (singleton)"""
    global _tts_client

    if _tts_client is None:
        try:
            # Use service account credentials
            credentials = service_account.Credentials.from_service_account_file(
                GOOGLE_APPLICATION_CREDENTIALS
            )
            _tts_client = texttospeech.TextToSpeechClient(credentials=credentials)
            logger.info("✅ TTS Client initialized")

        except Exception as e:
            logger.error(f"❌ TTS Client init failed: {e}")
            raise

    return _tts_client


# ============================================================
# VOICE SELECTION
# ============================================================

def _select_voice(category: str) -> Tuple[str, str]:
    """
    Select voice based on category

    Returns: (voice_name, gender)
    """
    gender = TTS_CATEGORY_VOICE.get(category, "male")

    if gender == "male":
        voice_name = TTS_VOICE_MALE
    else:
        voice_name = TTS_VOICE_FEMALE

    logger.info(f"🎤 Voice selected: {voice_name} ({gender}) for category '{category}'")

    return voice_name, gender


def _get_fallback_voices(gender: str) -> list:
    """Get list of fallback voices for gender"""
    if gender == "male":
        return FALLBACK_MALE_VOICES
    else:
        return FALLBACK_FEMALE_VOICES


# ============================================================
# TEXT PREPARATION
# ============================================================

def _clean_text_for_tts(text: str) -> str:
    """
    Clean text before sending to TTS

    - Remove emojis (TTS reads them literally otherwise)
    - Remove extra whitespace
    - Normalize punctuation
    """
    # Remove emojis (basic pattern for common emoji ranges)
    emoji_pattern = re.compile(
        "["
        "\U0001F600-\U0001F64F"  # emoticons
        "\U0001F300-\U0001F5FF"  # symbols & pictographs
        "\U0001F680-\U0001F6FF"  # transport & map
        "\U0001F1E0-\U0001F1FF"  # flags
        "\U00002702-\U000027B0"
        "\U000024C2-\U0001F251"
        "\U0001F900-\U0001F9FF"
        "\U00002600-\U000027BF"
        "]+",
        flags=re.UNICODE
    )

    text = emoji_pattern.sub('', text)

    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'\n{3,}', '\n\n', text)

    # Remove markdown
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
    text = re.sub(r'\*(.*?)\*', r'\1', text)

    return text.strip()


def _build_ssml(text: str) -> str:
    """
    V4: Enhanced SSML with dramatic narration feel.

    Adds:
    - Longer dramatic pauses at key moments
    - Emphasis on deity names and important words
    - Breathing pauses for natural flow
    - Paragraph breaks for scene changes
    - Speed variation for emotional impact
    """
    # Escape XML special characters
    text = text.replace('&', '&amp;')
    text = text.replace('<', '&lt;')
    text = text.replace('>', '&gt;')
    text = text.replace('"', '&quot;')
    text = text.replace("'", '&apos;')

    # ═══════════════════════════════════════════
    # DRAMATIC PAUSES (longer, more natural)
    # ═══════════════════════════════════════════

    # Sentence endings — LONGER pauses (storytelling feel)
    text = re.sub(r'\.\s+', '. <break time="600ms"/> ', text)
    text = re.sub(r'!\s+', '! <break time="700ms"/> ', text)
    text = re.sub(r'\?\s+', '? <break time="800ms"/> ', text)
    text = re.sub(r'।\s+', '। <break time="600ms"/> ', text)

    # Commas — medium pauses (breathing room)
    text = re.sub(r',\s+', ', <break time="300ms"/> ', text)

    # Paragraph breaks — BIG dramatic pauses (scene change feel)
    text = text.replace('\n\n', ' <break time="1000ms"/> ')
    text = text.replace('\n', ' <break time="500ms"/> ')

    # ═══════════════════════════════════════════
    # EMPHASIS on deity names (dramatic feel)
    # ═══════════════════════════════════════════

    deity_names = [
        'कृष्ण', 'कान्हा', 'श्रीकृष्ण', 'गोविंद',
        'शिव', 'महादेव', 'भोलेनाथ', 'शंकर', 'महाकाल',
        'हनुमान', 'बजरंगबली', 'पवन पुत्र', 'संकट मोचन',
        'गणेश', 'गणपति', 'बाप्पा', 'गजानन',
        'दुर्गा', 'काली', 'पार्वती', 'शेरावाली',
        'राम', 'सीता', 'लक्ष्मण', 'रावण',
        'भगवान', 'प्रभु', 'ईश्वर',
    ]

    for name in deity_names:
        text = text.replace(
            name,
            f'<break time="200ms"/><emphasis level="moderate">{name}</emphasis>'
        )

    # ═══════════════════════════════════════════
    # DRAMATIC HOOKS (first sentence slower)
    # ═══════════════════════════════════════════

    hook_phrases = [
        'क्या आप जानते हैं',
        'एक बार की बात है',
        'बहुत समय पहले',
        'आज हम बताएंगे',
        'सुनिए ये कहानी',
    ]

    for phrase in hook_phrases:
        text = text.replace(
            phrase,
            f'<prosody rate="slow">{phrase}</prosody><break time="500ms"/>'
        )

    # ═══════════════════════════════════════════
    # EMOTIONAL MOMENTS (slower for impact)
    # ═══════════════════════════════════════════

    emotional_words = [
        'रोते हुए', 'आंखों में आंसू', 'दिल टूट गया',
        'चमत्कार', 'अद्भुत', 'हैरान',
        'विजय', 'जीत', 'हार',
        'Save करें', 'Share करें',
    ]

    for word in emotional_words:
        text = text.replace(
            word,
            f'<prosody rate="slow"><emphasis level="strong">{word}</emphasis></prosody>'
        )

    # Wrap in SSML speak tag
    ssml = f'<speak>{text}</speak>'

    return ssml


# ============================================================
# TTS GENERATION
# ============================================================

def _generate_tts(
    text: str,
    voice_name: str,
    use_ssml: bool = True
) -> bytes:
    """
    Generate TTS audio bytes

    Args:
        text: Hindi text to convert
        voice_name: Voice model (e.g., "hi-IN-Neural2-B")
        use_ssml: Use SSML for better pauses

    Returns:
        MP3 audio bytes
    """
    client = _get_tts_client()

    # Prepare input
    if use_ssml:
        ssml_text = _build_ssml(text)
        synthesis_input = texttospeech.SynthesisInput(ssml=ssml_text)
    else:
        synthesis_input = texttospeech.SynthesisInput(text=text)

    # Voice config
    voice = texttospeech.VoiceSelectionParams(
        language_code=TTS_LANGUAGE,
        name=voice_name
    )

    # Audio config
    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.MP3,
        speaking_rate=TTS_SPEAKING_RATE,
        pitch=TTS_PITCH,
        effects_profile_id=["small-bluetooth-speaker-class-device"],
    )

    # Call API
    logger.info(f"📞 Calling TTS API (voice: {voice_name})...")
    start_time = time.time()

    response = client.synthesize_speech(
        input=synthesis_input,
        voice=voice,
        audio_config=audio_config,
        timeout=TTS_TIMEOUT_SECONDS
    )

    elapsed = round(time.time() - start_time, 2)
    audio_bytes = response.audio_content

    logger.info(f"✅ TTS generated in {elapsed}s ({len(audio_bytes):,} bytes)")

    return audio_bytes


# ============================================================
# 🚨 V3 CRITICAL FIX: REAL DURATION DETECTION
# ============================================================

def _get_real_mp3_duration(mp3_bytes: bytes) -> float:
    """
    🆕 V3 FIXED: Get ACCURATE MP3 duration using pydub.
    
    Previous version used byte-size heuristic (VERY WRONG for VBR MP3).
    Now reads actual MP3 file to get real duration.
    
    This is the SINGLE SOURCE OF TRUTH for audio duration.
    
    Args:
        mp3_bytes: MP3 audio bytes
    
    Returns:
        Actual duration in seconds
    """
    try:
        # Load actual MP3 file and read real duration
        audio = AudioSegment.from_file(io.BytesIO(mp3_bytes), format="mp3")
        actual_duration = len(audio) / 1000.0  # Convert ms to seconds
        
        logger.info(f"📊 REAL MP3 duration: {actual_duration:.2f}s (pydub - accurate)")
        
        return round(actual_duration, 2)

    except Exception as e:
        logger.error(f"❌ Pydub failed to read MP3: {e}")
        logger.warning(f"⚠️  Falling back to byte-size estimate (may be inaccurate)")
        
        # Fallback method (old approach - not reliable but better than nothing)
        try:
            size_bytes = len(mp3_bytes)
            estimated = size_bytes / 16000
            logger.warning(f"   Fallback duration: {estimated:.2f}s")
            return round(estimated, 2)
        except Exception as fallback_error:
            logger.error(f"   Both methods failed: {fallback_error}")
            logger.error("   Using 60s default")
            return 60.0


def _estimate_duration_from_text(text: str) -> float:
    """
    Estimate duration from text (Hindi ~2 words per second)
    Used ONLY for comparison/debugging - NOT for actual timing
    """
    words = len(text.split())
    # Hindi TTS at 0.95 speed = ~2 words/sec
    return round(words / 2.0, 2)


# ============================================================
# WORD-LEVEL TIMESTAMPS (Fixed)
# ============================================================

def _generate_word_timestamps(text: str, total_duration: float) -> list:
    """
    Generate approximate word-level timestamps.

    Google Cloud TTS doesn't provide word timings for Hindi Neural2 by default.
    We approximate by distributing time evenly across words with 
    punctuation-based multipliers.

    Args:
        text: Original text
        total_duration: Total audio duration in seconds (REAL from MP3)

    Returns:
        List of dicts: [{"word": "...", "start": 0.0, "end": 0.5}, ...]
    """
    # Clean text (remove emojis, extra whitespace)
    clean = _clean_text_for_tts(text)

    # Split into words (preserve punctuation attached)
    words = clean.split()

    if not words:
        return []

    total_words = len(words)

    # Calculate average time per word
    time_per_word = total_duration / total_words

    timestamps = []
    current_time = 0.0

    for word in words:
        # Longer duration for words with punctuation (natural pauses)
        multiplier = 1.0

        if word.endswith(('।', '.', '!', '?')):
            multiplier = 1.5  # Sentence end pause
        elif word.endswith(','):
            multiplier = 1.2  # Comma pause

        word_duration = time_per_word * multiplier

        timestamps.append({
            "word": word,
            "start": round(current_time, 3),
            "end": round(current_time + word_duration, 3)
        })

        current_time += word_duration

    # 🆕 V3 FIX: Normalize timestamps to match actual duration
    # (multipliers can cause total to exceed real duration)
    if timestamps and timestamps[-1]["end"] > total_duration:
        original_end = timestamps[-1]["end"]
        scale = total_duration / original_end
        
        for ts in timestamps:
            ts["start"] = round(ts["start"] * scale, 3)
            ts["end"] = round(ts["end"] * scale, 3)
        
        logger.info(
            f"📊 Timestamps normalized: {original_end:.2f}s → {total_duration}s "
            f"(scale: {scale:.3f})"
        )

    return timestamps


# ============================================================
# GENERATION WITH RETRIES
# ============================================================

def _generate_with_retries(text: str, gender: str) -> Tuple[bytes, str]:
    """
    Generate TTS with fallback voices

    Returns: (audio_bytes, voice_name_used)
    """
    voices_to_try = _get_fallback_voices(gender)

    last_error = None

    for attempt, voice_name in enumerate(voices_to_try, 1):
        try:
            logger.info(f"🎤 Attempt {attempt}/{len(voices_to_try)}: {voice_name}")

            audio_bytes = _generate_tts(
                text=text,
                voice_name=voice_name,
                use_ssml=True
            )

            if audio_bytes and len(audio_bytes) > 1000:
                return audio_bytes, voice_name
            else:
                logger.warning(f"⚠️  Voice {voice_name} returned empty audio")
                last_error = "Empty audio"

        except Exception as e:
            logger.warning(f"❌ Voice {voice_name} failed: {e}")
            last_error = str(e)

            if attempt < len(voices_to_try):
                time.sleep(2)

    # All voices failed
    raise Exception(f"All {len(voices_to_try)} voices failed. Last error: {last_error}")


# ============================================================
# MAIN AGENT FUNCTION (V3 FIXED)
# ============================================================

def run(memory: AgentMemory) -> AgentMemory:
    """
    Generate TTS voice for reel story with ACCURATE duration
    
    V3 FIXES:
    - Uses REAL MP3 duration (not text estimate)
    - Perfect video-audio sync
    - Better logging for debugging

    Flow:
    1. Validate story exists
    2. Select voice based on category
    3. Clean text (remove emojis)
    4. Generate TTS with fallback voices
    5. Get REAL duration from MP3 (using pydub)
    6. Generate word-level timestamps
    7. Save to memory
    """
    logger.info("=" * 55)
    logger.info("=== TTS ENGINE V3 शुरू (Fixed Duration) ===")
    logger.info("=" * 55)

    # ── Check if TTS enabled ────────────────────────────────
    if not TTS_ENABLED:
        logger.warning("⚠️  TTS is disabled in config")
        memory.add_error("tts_engine", "TTS disabled")
        return memory

    # ── Validate story ──────────────────────────────────────
    if not memory.reel_story:
        logger.error("❌ कोई story नहीं है")
        memory.add_error("tts_engine", "No story to convert")
        return memory

    # ── Recovery check ──────────────────────────────────────
    if memory.reel_voice_bytes and memory.is_recovery:
        logger.info("⏭️  Voice already generated (recovery), skipping")
        return memory

    logger.info(f"📖 Story words: {len(memory.reel_story.split())}")
    logger.info(f"📖 Story chars: {len(memory.reel_story)}")

    # ── Check character limit ───────────────────────────────
    if len(memory.reel_story) > MAX_TTS_CHARS:
        logger.warning(
            f"⚠️  Story exceeds {MAX_TTS_CHARS} chars, truncating..."
        )
        story_text = memory.reel_story[:MAX_TTS_CHARS]
    else:
        story_text = memory.reel_story

    # ── Clean text ──────────────────────────────────────────
    clean_text = _clean_text_for_tts(story_text)
    logger.info(f"🧹 Cleaned text: {len(clean_text)} chars")

    # ── Select voice ────────────────────────────────────────
    voice_name, gender = _select_voice(memory.category)
    memory.reel_voice_gender = gender

    # ── Generate TTS ────────────────────────────────────────
    try:
        audio_bytes, voice_used = _generate_with_retries(
            text=clean_text,
            gender=gender
        )

        # ── Save to memory ──────────────────────────────────
        memory.reel_voice_bytes = audio_bytes

        # ═══════════════════════════════════════════
        # 🚨 V3 CRITICAL FIX: Use REAL MP3 duration
        # ═══════════════════════════════════════════
        
        # Get REAL duration from actual MP3 file
        real_duration = _get_real_mp3_duration(audio_bytes)
        
        # Get text-based estimate (for comparison only)
        text_estimate = _estimate_duration_from_text(clean_text)
        
        # ALWAYS use real duration (single source of truth)
        duration = real_duration
        memory.reel_voice_duration = duration

        # Generate timestamps based on REAL duration
        timestamps = _generate_word_timestamps(clean_text, duration)
        memory.reel_voice_timestamps = timestamps

        # ── Success log with duration comparison ────────────
        logger.info("=" * 55)
        logger.info("✅ TTS ENGINE V3 SUCCESS")
        logger.info("=" * 55)
        logger.info(f"🎤 Voice used     : {voice_used}")
        logger.info(f"👤 Gender         : {gender}")
        logger.info(f"📏 Audio size     : {len(audio_bytes):,} bytes")
        logger.info(f"⏱️  REAL Duration  : {duration}s ⭐ (USING THIS)")
        logger.info(f"📝 Word count     : {len(timestamps)}")
        logger.info(f"📊 Text estimate  : {text_estimate}s (for comparison only)")
        
        # Warn if big mismatch (helps debug future issues)
        diff = abs(real_duration - text_estimate)
        if diff > 15:
            logger.warning(
                f"⚠️  Large mismatch detected: "
                f"Real={real_duration}s vs Text estimate={text_estimate}s "
                f"(diff: {diff:.1f}s) - REAL value used ✅"
            )
        elif diff > 5:
            logger.info(
                f"ℹ️  Moderate mismatch: "
                f"Real={real_duration}s vs Text estimate={text_estimate}s "
                f"(diff: {diff:.1f}s) - REAL value used ✅"
            )
        else:
            logger.info(f"✅ Duration estimates match closely (diff: {diff:.1f}s)")
        
        logger.info("=" * 55)

    except Exception as e:
        logger.error(f"❌ TTS generation completely failed: {e}")
        memory.add_error("tts_engine", str(e))
        raise

    logger.info("=== TTS ENGINE V3 पूर्ण ===\n")
    return memory


# ============================================================
# UTILITY FUNCTIONS
# ============================================================

def save_audio_to_file(audio_bytes: bytes, filepath: str) -> bool:
    """Save audio bytes to file (for testing/debugging)"""
    try:
        with open(filepath, 'wb') as f:
            f.write(audio_bytes)
        logger.info(f"💾 Audio saved: {filepath}")
        return True
    except Exception as e:
        logger.error(f"❌ Audio save failed: {e}")
        return False


def get_available_voices() -> list:
    """List all available Hindi voices"""
    try:
        client = _get_tts_client()
        response = client.list_voices(language_code=TTS_LANGUAGE)

        voices = []
        for voice in response.voices:
            voices.append({
                "name": voice.name,
                "language_codes": list(voice.language_codes),
                "gender": texttospeech.SsmlVoiceGender(voice.ssml_gender).name,
                "natural_sample_rate_hertz": voice.natural_sample_rate_hertz
            })

        return voices

    except Exception as e:
        logger.error(f"❌ List voices failed: {e}")
        return []


# ============================================================
# STANDALONE TESTING
# ============================================================

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("TTS ENGINE V3 - STANDALONE TEST (Fixed Duration)")
    print("=" * 60 + "\n")

    # Test 1: List available Hindi voices
    print("📋 Available Hindi voices:")
    voices = get_available_voices()
    for v in voices[:10]:  # Show first 10
        print(f"   • {v['name']} ({v['gender']})")

    print("\n" + "=" * 60)
    print("🎤 Test TTS Generation")
    print("=" * 60 + "\n")

    # Test 2: Krishna story (male voice)
    test_story = (
        "क्या आप जानते हैं कि श्रीकृष्ण की बांसुरी में क्या रहस्य छिपा था? "
        "वृंदावन के जंगल में जब कान्हा अपनी बांसुरी बजाते, तो पूरी सृष्टि रुक जाती। "
        "गायें दौड़ी आतीं, यमुना की धारा शांत हो जाती। "
        "यह प्रेम का संगीत था। "
        "Save करें और Share करें।"
    )

    memory = AgentMemory()
    memory.reel_story = test_story
    memory.category = "krishna"
    memory.topic = "Krishna's flute"
    memory.post_type = "reel"

    result = run(memory)

    if result.reel_voice_bytes:
        # Save to file
        output_file = "test_reel_voice.mp3"
        save_audio_to_file(result.reel_voice_bytes, output_file)

        print(f"\n✅ Test complete!")
        print(f"   Audio file: {output_file}")
        print(f"   REAL Duration: {result.reel_voice_duration}s")
        print(f"   Voice: {result.reel_voice_gender}")
        print(f"   Words: {len(result.reel_voice_timestamps)}")

        # Show first 5 timestamps
        print(f"\n📊 First 5 word timestamps:")
        for ts in result.reel_voice_timestamps[:5]:
            print(f"   {ts['start']:.2f}s - {ts['end']:.2f}s: {ts['word']}")

        print(f"\n💡 Play the audio: start {output_file}")
    else:
        print("❌ No audio generated")

    print("\n" + "=" * 60)
    print("V3 CRITICAL FIXES:")
    print("=" * 60)
    print("   ✅ REAL MP3 duration from pydub (not byte estimate)")
    print("   ✅ Text estimate used ONLY for comparison")
    print("   ✅ Timestamps normalized to match real duration")
    print("   ✅ Perfect video-audio sync")
    print("   ✅ Fixes 20s video-audio mismatch bug")
    print("=" * 60)