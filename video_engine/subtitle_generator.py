"""
Subtitle Generator - Create SRT subtitles from TTS timestamps

Two modes:
1. LINE_MODE (default) - Groups 3-5 words per subtitle
   Best for readability, standard reel style

2. WORD_HIGHLIGHT_MODE - Each word gets own subtitle
   For karaoke-style word highlighting (Phase 5 will use this)

Output: Standard SRT format
Example:
    1
    00:00:00,000 --> 00:00:02,500
    क्या आप जानते हैं

    2
    00:00:02,500 --> 00:00:05,000
    श्रीकृष्ण की बांसुरी में
"""
import re
from typing import Optional

from core.memory import AgentMemory
from config.settings import REEL_SUBTITLE_ENABLED
from utils.logger import get_logger

logger = get_logger("subtitle_generator")


# ============================================================
# CONFIGURATION
# ============================================================

# Line mode settings
WORDS_PER_LINE_MIN = 2       # Min words per subtitle line
WORDS_PER_LINE_MAX = 5       # Max words per subtitle line (mobile readability)
MAX_CHARS_PER_LINE = 30      # Max characters per subtitle line

# Timing
MIN_SUBTITLE_DURATION = 0.8  # Minimum time a subtitle stays on screen
MAX_SUBTITLE_DURATION = 4.0  # Maximum time a subtitle stays on screen


# ============================================================
# TIME FORMATTING
# ============================================================

def _seconds_to_srt_time(seconds: float) -> str:
    """
    Convert seconds to SRT time format

    Examples:
        0 → "00:00:00,000"
        2.5 → "00:00:02,500"
        75.123 → "00:01:15,123"
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds - int(seconds)) * 1000)

    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


# ============================================================
# LINE-MODE SUBTITLES (Grouped words)
# ============================================================

def _group_words_into_lines(timestamps: list) -> list:
    """
    Group word timestamps into subtitle lines.

    Strategy:
    - Group 2-5 words per line
    - Break at natural pauses (punctuation)
    - Respect character limit for mobile readability

    Returns:
        List of dicts: [
            {"text": "...", "start": 0.0, "end": 2.5},
            ...
        ]
    """
    if not timestamps:
        return []

    lines = []
    current_line_words = []
    current_line_start = None

    for i, word_data in enumerate(timestamps):
        word = word_data["word"]
        word_start = word_data["start"]
        word_end = word_data["end"]

        # Start new line if this is first word
        if current_line_start is None:
            current_line_start = word_start

        # Add word to current line
        current_line_words.append(word)

        # Check if we should end this line
        should_break = False

        # Reason 1: Natural sentence end
        if word.endswith(('।', '.', '!', '?')):
            should_break = True

        # Reason 2: Comma with enough words
        elif word.endswith(',') and len(current_line_words) >= WORDS_PER_LINE_MIN:
            should_break = True

        # Reason 3: Max words reached
        elif len(current_line_words) >= WORDS_PER_LINE_MAX:
            should_break = True

        # Reason 4: Character limit
        else:
            current_text = " ".join(current_line_words)
            if len(current_text) >= MAX_CHARS_PER_LINE:
                should_break = True

        # Reason 5: Last word
        if i == len(timestamps) - 1:
            should_break = True

        # Save line if breaking
        if should_break:
            line_text = " ".join(current_line_words).strip()

            if line_text:  # Only add non-empty lines
                lines.append({
                    "text": line_text,
                    "start": current_line_start,
                    "end": word_end
                })

            # Reset for next line
            current_line_words = []
            current_line_start = None

    return lines


def _adjust_line_timings(lines: list) -> list:
    """
    Ensure minimum/maximum duration for each subtitle
    Prevents subtitles from flashing too fast or lingering too long
    """
    adjusted = []

    for i, line in enumerate(lines):
        duration = line["end"] - line["start"]

        # Enforce minimum duration
        if duration < MIN_SUBTITLE_DURATION:
            # Extend the end time
            new_end = line["start"] + MIN_SUBTITLE_DURATION

            # But don't overlap with next line
            if i < len(lines) - 1:
                next_start = lines[i + 1]["start"]
                new_end = min(new_end, next_start - 0.05)

            line["end"] = new_end

        # Enforce maximum duration
        elif duration > MAX_SUBTITLE_DURATION:
            line["end"] = line["start"] + MAX_SUBTITLE_DURATION

        adjusted.append(line)

    return adjusted


def _generate_line_mode_srt(lines: list) -> str:
    """
    Generate SRT format from line list

    Format:
        1
        00:00:00,000 --> 00:00:02,500
        Text here

        2
        00:00:02,500 --> 00:00:05,000
        More text
    """
    srt_content = []

    for i, line in enumerate(lines, 1):
        start_time = _seconds_to_srt_time(line["start"])
        end_time = _seconds_to_srt_time(line["end"])

        srt_block = f"{i}\n{start_time} --> {end_time}\n{line['text']}\n"
        srt_content.append(srt_block)

    return "\n".join(srt_content)


# ============================================================
# WORD-HIGHLIGHT MODE (Karaoke-style)
# ============================================================

def _generate_word_highlight_srt(timestamps: list) -> str:
    """
    Generate SRT where each word is a separate subtitle.
    Used for karaoke-style word highlighting in Phase 5.

    Each word: min 0.3 sec duration
    """
    if not timestamps:
        return ""

    srt_content = []
    counter = 1

    for word_data in timestamps:
        word = word_data["word"].strip()

        if not word:
            continue

        # Ensure minimum word display time
        duration = word_data["end"] - word_data["start"]
        if duration < 0.3:
            end_time = word_data["start"] + 0.3
        else:
            end_time = word_data["end"]

        start_str = _seconds_to_srt_time(word_data["start"])
        end_str = _seconds_to_srt_time(end_time)

        srt_block = f"{counter}\n{start_str} --> {end_str}\n{word}\n"
        srt_content.append(srt_block)
        counter += 1

    return "\n".join(srt_content)


# ============================================================
# FALLBACK: Generate from text (if no timestamps)
# ============================================================

def _generate_srt_from_text(text: str, total_duration: float) -> str:
    """
    Emergency fallback: generate SRT from text alone (no timestamps)
    Splits text into rough chunks and distributes time evenly
    """
    logger.warning("⚠️  No timestamps available, generating approximate SRT")

    # Split into sentences (rough)
    sentences = re.split(r'[।.!?]\s+', text)
    sentences = [s.strip() for s in sentences if s.strip()]

    if not sentences:
        return ""

    time_per_sentence = total_duration / len(sentences)

    srt_content = []
    current_time = 0.0

    for i, sentence in enumerate(sentences, 1):
        # Break long sentences into smaller chunks
        words = sentence.split()
        chunks = []

        for j in range(0, len(words), WORDS_PER_LINE_MAX):
            chunk = " ".join(words[j:j + WORDS_PER_LINE_MAX])
            chunks.append(chunk)

        # Time per chunk within sentence
        chunk_duration = time_per_sentence / len(chunks) if chunks else 0

        for chunk in chunks:
            start_str = _seconds_to_srt_time(current_time)
            end_str = _seconds_to_srt_time(current_time + chunk_duration)

            srt_block = f"{i}\n{start_str} --> {end_str}\n{chunk}\n"
            srt_content.append(srt_block)

            current_time += chunk_duration

    return "\n".join(srt_content)


# ============================================================
# VALIDATION
# ============================================================

def _validate_srt(srt_content: str) -> tuple:
    """
    Validate SRT content
    Returns: (is_valid, reason)
    """
    if not srt_content or len(srt_content) < 20:
        return False, "SRT too short or empty"

    # Check basic structure (must have arrow)
    if "-->" not in srt_content:
        return False, "SRT missing timing arrows"

    # Check block count
    blocks = srt_content.strip().split("\n\n")
    if len(blocks) < 2:
        return False, f"Too few subtitle blocks: {len(blocks)}"

    return True, f"Valid ({len(blocks)} subtitles)"


# ============================================================
# MAIN AGENT FUNCTION
# ============================================================

def run(memory: AgentMemory, mode: str = "line") -> AgentMemory:
    """
    Generate SRT subtitles from voice timestamps

    Args:
        memory: AgentMemory
        mode: "line" (grouped words) or "word_highlight" (karaoke)

    Flow:
    1. Validate inputs
    2. Group words into lines (or keep as individual words)
    3. Adjust timings
    4. Generate SRT format
    5. Validate
    6. Save to memory.reel_subtitle_srt
    """
    logger.info("=" * 55)
    logger.info("=== SUBTITLE GENERATOR शुरू ===")
    logger.info("=" * 55)

    # ── Check if enabled ────────────────────────────────────
    if not REEL_SUBTITLE_ENABLED:
        logger.warning("⚠️  Subtitles disabled in config")
        memory.add_error("subtitle_generator", "Subtitles disabled")
        return memory

    # ── Recovery check ──────────────────────────────────────
    if memory.reel_subtitle_srt and memory.is_recovery:
        logger.info("⏭️  Subtitles already exist (recovery), skipping")
        return memory

    # ── Set mode ────────────────────────────────────────────
    memory.reel_subtitle_style = mode
    logger.info(f"🎨 Mode: {mode}")

    # ── Check if we have timestamps ─────────────────────────
    if not memory.reel_voice_timestamps:
        logger.warning("⚠️  No word timestamps available, using fallback")

        if memory.reel_story and memory.reel_voice_duration:
            srt_content = _generate_srt_from_text(
                text=memory.reel_story,
                total_duration=memory.reel_voice_duration
            )
        else:
            logger.error("❌ Not enough data to generate subtitles")
            memory.add_error("subtitle_generator", "No timestamps or story text")
            return memory
    else:
        logger.info(f"📊 Word timestamps: {len(memory.reel_voice_timestamps)}")

        # ── Generate based on mode ─────────────────────────
        if mode == "word_highlight":
            logger.info("🎤 Generating word-by-word highlight subtitles")
            srt_content = _generate_word_highlight_srt(memory.reel_voice_timestamps)

        else:  # Default: line mode
            logger.info("📝 Generating line-grouped subtitles")

            # Group words into lines
            lines = _group_words_into_lines(memory.reel_voice_timestamps)
            logger.info(f"📊 Generated {len(lines)} subtitle lines")

            # Adjust timings
            lines = _adjust_line_timings(lines)

            # Generate SRT
            srt_content = _generate_line_mode_srt(lines)

    # ── Validate ────────────────────────────────────────────
    is_valid, reason = _validate_srt(srt_content)

    if not is_valid:
        logger.error(f"❌ Generated SRT invalid: {reason}")
        memory.add_error("subtitle_generator", f"Invalid SRT: {reason}")
        return memory

    # ── Save to memory ──────────────────────────────────────
    memory.reel_subtitle_srt = srt_content

    # ── Summary ─────────────────────────────────────────────
    blocks = srt_content.strip().split("\n\n")

    logger.info("=" * 55)
    logger.info("✅ SUBTITLE GENERATOR SUCCESS")
    logger.info("=" * 55)
    logger.info(f"🎨 Style       : {mode}")
    logger.info(f"📊 Subtitles   : {len(blocks)}")
    logger.info(f"📏 SRT chars   : {len(srt_content)}")
    logger.info("")
    logger.info("📋 First 3 subtitles preview:")

    for block in blocks[:3]:
        # Show just the text lines
        block_lines = block.strip().split("\n")
        if len(block_lines) >= 3:
            logger.info(f"   [{block_lines[1]}] {block_lines[2]}")

    logger.info("=" * 55)

    logger.info("=== SUBTITLE GENERATOR पूर्ण ===\n")
    return memory


# ============================================================
# UTILITY FUNCTIONS
# ============================================================

def save_srt_to_file(srt_content: str, filepath: str) -> bool:
    """Save SRT content to .srt file (for testing/debugging)"""
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(srt_content)
        logger.info(f"💾 SRT saved: {filepath}")
        return True
    except Exception as e:
        logger.error(f"❌ SRT save failed: {e}")
        return False


# ============================================================
# STANDALONE TESTING
# ============================================================

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("SUBTITLE GENERATOR - STANDALONE TEST")
    print("=" * 60 + "\n")

    # Create mock timestamps (simulating TTS output)
    test_timestamps = [
        {"word": "क्या", "start": 0.0, "end": 0.5},
        {"word": "आप", "start": 0.5, "end": 0.9},
        {"word": "जानते", "start": 0.9, "end": 1.5},
        {"word": "हैं?", "start": 1.5, "end": 2.2},

        {"word": "श्रीकृष्ण", "start": 2.5, "end": 3.3},
        {"word": "की", "start": 3.3, "end": 3.6},
        {"word": "बांसुरी", "start": 3.6, "end": 4.4},
        {"word": "में", "start": 4.4, "end": 4.8},
        {"word": "एक", "start": 4.8, "end": 5.2},
        {"word": "रहस्य", "start": 5.2, "end": 6.0},
        {"word": "छिपा", "start": 6.0, "end": 6.5},
        {"word": "है।", "start": 6.5, "end": 7.2},

        {"word": "वृंदावन", "start": 7.5, "end": 8.3},
        {"word": "के", "start": 8.3, "end": 8.6},
        {"word": "जंगल", "start": 8.6, "end": 9.2},
        {"word": "में,", "start": 9.2, "end": 9.7},
    ]

    memory = AgentMemory()
    memory.reel_voice_timestamps = test_timestamps
    memory.reel_voice_duration = 10.0
    memory.reel_story = " ".join([t["word"] for t in test_timestamps])
    memory.post_type = "reel"

    # ── Test 1: Line mode (default) ────────────────────────
    print("=" * 60)
    print("TEST 1: Line Mode (Default)")
    print("=" * 60)

    result1 = run(memory, mode="line")
    print(f"\n📄 Generated SRT:\n")
    print(result1.reel_subtitle_srt)

    # Save to file
    save_srt_to_file(result1.reel_subtitle_srt, "test_reel_subtitles_line.srt")

    # ── Test 2: Word highlight mode ─────────────────────────
    print("\n" + "=" * 60)
    print("TEST 2: Word Highlight Mode")
    print("=" * 60)

    # Reset memory
    memory2 = AgentMemory()
    memory2.reel_voice_timestamps = test_timestamps
    memory2.reel_voice_duration = 10.0
    memory2.reel_story = memory.reel_story
    memory2.post_type = "reel"

    result2 = run(memory2, mode="word_highlight")
    print(f"\n📄 Generated SRT (first 500 chars):\n")
    print(result2.reel_subtitle_srt[:500])

    # Save to file
    save_srt_to_file(result2.reel_subtitle_srt, "test_reel_subtitles_word.srt")

    print("\n✅ Both tests complete!")