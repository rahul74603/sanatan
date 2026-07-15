"""
Concat Engine - Merge clips + attach audio + burn subtitles

V2.1 FIXES:
- 🆕 UTF-8 explicit encoding for subtitles (Windows fix)
- 🆕 Fallback: read SRT with utf-8-sig for BOM handling
- 🆕 PIL-based text rendering (NO ImageMagick needed!)
- 🆕 Better error messages
- 🆕 Save temp SRT with explicit UTF-8 write

Features:
- Concatenate multiple video clips into single video
- Attach mixed audio (voice + BG music)
- Burn subtitles into video (word-by-word or line-mode)
- Handle Ken Burns effect clips properly
- Optimize for Instagram/YT compatibility
- Progress logging

Output: Final MP4 ready for social media upload
"""
import io
import os
import re
import tempfile
from pathlib import Path
from typing import Optional

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from moviepy.editor import (
    concatenate_videoclips,
    AudioFileClip,
    CompositeVideoClip,
    ImageClip,
    VideoFileClip,
)

# Try importing subtitle support
try:
    from moviepy.video.tools.subtitles import SubtitlesClip
    SUBTITLES_AVAILABLE = True
except ImportError:
    SUBTITLES_AVAILABLE = False

from config.settings import (
    REEL_WIDTH,
    REEL_HEIGHT,
    REEL_FPS,
    REEL_VIDEO_CODEC,
    REEL_VIDEO_CRF,
    REEL_VIDEO_PRESET,
    REEL_AUDIO_CODEC,
    REEL_AUDIO_BITRATE,
    REEL_SUBTITLE_ENABLED,
    REEL_SUBTITLE_FONT_SIZE,
    REEL_SUBTITLE_BASE_COLOR,
    REEL_SUBTITLE_STROKE_COLOR,
)
from utils.logger import get_logger

logger = get_logger("concat_engine")


# ============================================================
# CONFIGURATION
# ============================================================

# Font path (cross-platform)
FONT_PATHS = [
    "fonts/NotoSansDevanagari-Bold.ttf",     # Local (priority)
    "fonts/NotoSansDevanagari-Regular.ttf",  # Local fallback
    "C:/Windows/Fonts/NirmalaB.ttf",         # Windows Hindi Bold
    "C:/Windows/Fonts/mangal.ttf",           # Windows Hindi
    "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Bold.ttf",  # Linux
    "/System/Library/Fonts/Helvetica.ttc",   # macOS
]

# Subtitle position (from bottom)
SUBTITLE_BOTTOM_MARGIN_RATIO = 0.15  # 15% from bottom

# Subtitle text box width (percentage of video width)
SUBTITLE_WIDTH_RATIO = 0.85

# Stroke settings
SUBTITLE_STROKE_WIDTH = 4


# ============================================================
# HELPERS
# ============================================================

def _find_font_path() -> Optional[str]:
    """Find available Hindi font path"""
    for path in FONT_PATHS:
        if os.path.exists(path):
            return path

    logger.warning("⚠️  No Hindi font found. Subtitles may not render properly.")
    return None


def _save_audio_to_temp_file(audio_bytes: bytes) -> str:
    """Save audio bytes to temp file"""
    with tempfile.NamedTemporaryFile(
        delete=False,
        suffix='.mp3',
        prefix='reel_audio_'
    ) as f:
        f.write(audio_bytes)
        temp_path = f.name

    return temp_path


def _save_srt_to_temp_file(srt_content: str) -> str:
    """
    Save SRT content with EXPLICIT UTF-8 encoding.
    Windows charmap encoding will fail on Hindi text.
    """
    temp_fd, temp_path = tempfile.mkstemp(
        suffix='.srt',
        prefix='reel_subs_',
        text=False
    )

    try:
        os.close(temp_fd)

        with open(temp_path, 'w', encoding='utf-8', newline='') as f:
            f.write(srt_content)

        logger.debug(f"💾 SRT saved with UTF-8: {temp_path}")
        return temp_path

    except Exception as e:
        try:
            os.remove(temp_path)
        except Exception:
            pass
        raise Exception(f"Failed to save SRT: {e}")


def _cleanup_temp_files(*paths):
    """Delete temp files after use"""
    for path in paths:
        try:
            if path and os.path.exists(path):
                os.remove(path)
        except Exception:
            pass


def _read_srt_utf8(srt_path: str) -> str:
    """
    Read SRT file with UTF-8 encoding (multiple attempts).
    """
    encodings_to_try = ['utf-8', 'utf-8-sig', 'utf-16', 'cp1252']

    for encoding in encodings_to_try:
        try:
            with open(srt_path, 'r', encoding=encoding) as f:
                content = f.read()
            return content
        except (UnicodeDecodeError, UnicodeError):
            continue

    raise Exception(f"Could not read SRT with any encoding")


# ============================================================
# 🆕 V2.1: PIL-BASED SUBTITLE RENDERING (No ImageMagick!)
# ============================================================

def _hex_to_rgb(hex_color: str) -> tuple:
    """Convert hex color to RGB tuple"""
    hex_color = hex_color.lstrip('#')
    if len(hex_color) == 6:
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    return (255, 255, 255)  # Default white


def _wrap_text(text: str, font: ImageFont.FreeTypeFont, max_width: int) -> list:
    """
    Wrap text to fit within max_width.
    Returns list of lines.
    """
    if not text:
        return []

    words = text.split()
    lines = []
    current_line = []

    for word in words:
        # Try adding word to current line
        test_line = ' '.join(current_line + [word])
        # Use textbbox for accurate measurement
        try:
            bbox = font.getbbox(test_line)
            line_width = bbox[2] - bbox[0]
        except AttributeError:
            # Older PIL versions
            line_width = font.getsize(test_line)[0]

        if line_width <= max_width:
            current_line.append(word)
        else:
            if current_line:
                lines.append(' '.join(current_line))
                current_line = [word]
            else:
                # Word too long, keep as-is
                lines.append(word)
                current_line = []

    if current_line:
        lines.append(' '.join(current_line))

    return lines


def _render_subtitle_pil(
    text: str,
    font_path: Optional[str] = None,
    font_size: int = None,
    color: str = None,
    stroke_color: str = None,
    stroke_width: int = None,
    max_width: int = None
) -> np.ndarray:
    """
    🆕 V2.1: Render subtitle text using PIL (no ImageMagick needed).

    Returns numpy array (RGBA) for use as ImageClip.
    """
    # Defaults
    if font_size is None:
        font_size = REEL_SUBTITLE_FONT_SIZE
    if color is None:
        color = REEL_SUBTITLE_BASE_COLOR
    if stroke_color is None:
        stroke_color = REEL_SUBTITLE_STROKE_COLOR
    if stroke_width is None:
        stroke_width = SUBTITLE_STROKE_WIDTH
    if max_width is None:
        max_width = int(REEL_WIDTH * SUBTITLE_WIDTH_RATIO)

    # Load font
    try:
        if font_path and os.path.exists(font_path):
            font = ImageFont.truetype(font_path, font_size)
        else:
            font = ImageFont.load_default()
            logger.warning("⚠️  Using default font (may not support Hindi)")
    except Exception as e:
        logger.warning(f"⚠️  Font load failed: {e}, using default")
        font = ImageFont.load_default()

    # Wrap text
    lines = _wrap_text(text, font, max_width)

    if not lines:
        # Return empty transparent image
        img = Image.new('RGBA', (100, 100), (0, 0, 0, 0))
        return np.array(img)

    # Calculate total height needed
    line_height = font_size + 8  # Small padding
    total_height = line_height * len(lines) + stroke_width * 2

    # Find widest line
    max_line_width = 0
    for line in lines:
        try:
            bbox = font.getbbox(line)
            width = bbox[2] - bbox[0]
        except AttributeError:
            width = font.getsize(line)[0]

        if width > max_line_width:
            max_line_width = width

    # Add padding for stroke
    img_width = max_line_width + stroke_width * 4 + 20
    img_height = total_height + 20

    # Create transparent image
    img = Image.new('RGBA', (img_width, img_height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Convert colors
    text_rgb = _hex_to_rgb(color)
    stroke_rgb = _hex_to_rgb(stroke_color)

    # Draw each line
    y_offset = 10
    for line in lines:
        # Get line width for centering
        try:
            bbox = font.getbbox(line)
            line_width = bbox[2] - bbox[0]
        except AttributeError:
            line_width = font.getsize(line)[0]

        x_offset = (img_width - line_width) // 2

        # Draw stroke (outline) by drawing text multiple times with offsets
        for dx in range(-stroke_width, stroke_width + 1):
            for dy in range(-stroke_width, stroke_width + 1):
                if dx == 0 and dy == 0:
                    continue
                # Only draw stroke on edges (skip inner)
                if abs(dx) < stroke_width and abs(dy) < stroke_width:
                    continue
                draw.text(
                    (x_offset + dx, y_offset + dy),
                    line,
                    font=font,
                    fill=(*stroke_rgb, 255)
                )

        # Draw main text on top
        draw.text(
            (x_offset, y_offset),
            line,
            font=font,
            fill=(*text_rgb, 255)
        )

        y_offset += line_height

    return np.array(img)


def _create_subtitle_generator(font_path: Optional[str] = None):
    """
    🆕 V2.1: Create subtitle generator using PIL (no ImageMagick).

    Returns a function that creates ImageClip for each subtitle.
    """

    def make_subtitle_clip(txt: str):
        """Create ImageClip for one subtitle using PIL"""
        try:
            if not txt or not txt.strip():
                return None

            # Render text with PIL
            img_array = _render_subtitle_pil(
                text=txt.strip(),
                font_path=font_path,
                font_size=REEL_SUBTITLE_FONT_SIZE,
                color=REEL_SUBTITLE_BASE_COLOR,
                stroke_color=REEL_SUBTITLE_STROKE_COLOR,
                stroke_width=SUBTITLE_STROKE_WIDTH,
            )

            # Create ImageClip (no ImageMagick needed!)
            clip = ImageClip(img_array, transparent=True)

            return clip

        except Exception as e:
            logger.warning(f"⚠️  Subtitle render failed for '{txt[:30]}': {e}")
            return None

    return make_subtitle_clip


# ============================================================
# SUBTITLE OVERLAY
# ============================================================

def _add_subtitles_to_video(video_clip, srt_path: str):
    """
    🆕 V2.1: Overlay subtitles using PIL rendering.
    """
    if not SUBTITLES_AVAILABLE:
        logger.warning("⚠️  SubtitlesClip not available")
        return video_clip

    try:
        # Read SRT with UTF-8
        try:
            srt_content = _read_srt_utf8(srt_path)
            logger.debug(f"✅ SRT read ({len(srt_content)} chars)")
        except Exception as e:
            logger.error(f"❌ SRT read failed: {e}")
            return video_clip

        # Load font
        font_path = _find_font_path()
        if font_path:
            logger.info(f"🔤 Using font: {Path(font_path).name}")
        else:
            logger.warning("⚠️  No Hindi font — subtitles may not render")
            return video_clip

        subtitle_maker = _create_subtitle_generator(font_path)

        logger.info(f"📝 Parsing subtitles...")

        # Parse SRT manually (more reliable than MoviePy's parser)
        subtitles = _parse_srt_content(srt_content, video_clip.duration)

        if not subtitles:
            logger.warning("⚠️  No subtitles parsed")
            return video_clip

        logger.info(f"✅ Parsed {len(subtitles)} subtitle blocks")

        # Create SubtitlesClip from parsed list
        try:
            subs = SubtitlesClip(subtitles, subtitle_maker)
        except Exception as e:
            logger.error(f"❌ SubtitlesClip creation failed: {e}")
            return video_clip

        # Position at bottom
        bottom_margin = int(REEL_HEIGHT * SUBTITLE_BOTTOM_MARGIN_RATIO)
        subs = subs.set_position(('center', REEL_HEIGHT - bottom_margin))

        # Composite with video
        result = CompositeVideoClip(
            [video_clip, subs],
            size=(REEL_WIDTH, REEL_HEIGHT)
        )

        result = result.set_duration(video_clip.duration)

        logger.info("✅ Subtitles overlaid successfully (PIL-based)")

        return result

    except Exception as e:
        logger.error(f"❌ Subtitle overlay failed: {e}")
        logger.warning("⚠️  Returning video without subtitles")
        return video_clip


def _parse_srt_content(srt_content: str, video_duration: float) -> list:
    """
    Parse SRT content manually.
    Returns list of ((start, end), text) tuples.
    """
    try:
        # SRT format regex
        pattern = re.compile(
            r'(\d+)\s*\n'
            r'(\d{2}:\d{2}:\d{2}[,.]\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2}[,.]\d{3})\s*\n'
            r'(.*?)(?=\n\s*\n|\Z)',
            re.DOTALL
        )

        def time_to_seconds(time_str: str) -> float:
            time_str = time_str.replace(',', '.')
            parts = time_str.split(':')
            hours = int(parts[0])
            minutes = int(parts[1])
            seconds = float(parts[2])
            return hours * 3600 + minutes * 60 + seconds

        subtitles = []
        for match in pattern.finditer(srt_content):
            start_time = time_to_seconds(match.group(2))
            end_time = time_to_seconds(match.group(3))
            text = match.group(4).strip()

            if text and start_time < video_duration:
                end_time = min(end_time, video_duration)
                subtitles.append(((start_time, end_time), text))

        return subtitles

    except Exception as e:
        logger.error(f"❌ SRT parse error: {e}")
        return []


# ============================================================
# MAIN CONCATENATION
# ============================================================

def concatenate_clips(clips: list, method: str = "compose"):
    """Merge multiple video clips into single clip"""
    if not clips:
        raise ValueError("No clips to concatenate")

    if len(clips) == 1:
        logger.info("ℹ️  Only 1 clip, no concatenation needed")
        return clips[0]

    logger.info(f"🎞️  Concatenating {len(clips)} clips (method: {method})")

    try:
        result = concatenate_videoclips(clips, method=method)
        logger.info(f"✅ Concatenated: {result.duration:.1f}s total")
        return result

    except Exception as e:
        logger.error(f"❌ Concatenation failed with '{method}': {e}")

        alt_method = "chain" if method == "compose" else "compose"
        logger.warning(f"⚠️  Retrying with method: {alt_method}")

        try:
            result = concatenate_videoclips(clips, method=alt_method)
            logger.info(f"✅ Concatenated with alt method: {result.duration:.1f}s")
            return result
        except Exception as e2:
            logger.error(f"❌ Both methods failed: {e2}")
            raise


# ============================================================
# AUDIO ATTACHMENT
# ============================================================

def attach_audio_to_video(video_clip, audio_bytes: bytes):
    """Attach audio track to video clip"""
    audio_temp_path = None

    try:
        audio_temp_path = _save_audio_to_temp_file(audio_bytes)
        audio_clip = AudioFileClip(audio_temp_path)

        logger.info(f"🔊 Audio loaded: {audio_clip.duration:.1f}s")
        logger.info(f"🎥 Video duration: {video_clip.duration:.1f}s")

        video_duration = video_clip.duration
        audio_duration = audio_clip.duration

        if abs(audio_duration - video_duration) > 0.5:
            logger.warning(
                f"⚠️  Audio-video duration mismatch: "
                f"{audio_duration:.1f}s vs {video_duration:.1f}s"
            )

            if audio_duration > video_duration:
                audio_clip = audio_clip.subclip(0, video_duration)
                logger.info(f"✂️  Trimmed audio to {video_duration:.1f}s")
            else:
                video_clip = video_clip.subclip(0, audio_duration)
                logger.info(f"✂️  Trimmed video to {audio_duration:.1f}s")

        video_with_audio = video_clip.set_audio(audio_clip)

        logger.info("✅ Audio attached to video")

        return video_with_audio, audio_temp_path

    except Exception as e:
        logger.error(f"❌ Audio attachment failed: {e}")
        _cleanup_temp_files(audio_temp_path)
        raise


# ============================================================
# VIDEO EXPORT
# ============================================================

def export_video(
    video_clip,
    output_path: str,
    fps: int = None,
    codec: str = None,
    audio_codec: str = None,
    preset: str = None,
    crf: int = None,
    threads: int = 4,
    verbose: bool = False,
) -> dict:
    """Export final video to MP4 file"""
    if fps is None:
        fps = REEL_FPS
    if codec is None:
        codec = REEL_VIDEO_CODEC
    if audio_codec is None:
        audio_codec = REEL_AUDIO_CODEC
    if preset is None:
        preset = REEL_VIDEO_PRESET
    if crf is None:
        crf = REEL_VIDEO_CRF

    logger.info("=" * 55)
    logger.info("🎬 EXPORTING FINAL VIDEO")
    logger.info("=" * 55)
    logger.info(f"   Output    : {output_path}")
    logger.info(f"   Duration  : {video_clip.duration:.1f}s")
    logger.info(f"   FPS       : {fps}")
    logger.info(f"   Codec     : {codec}")
    logger.info(f"   Preset    : {preset}")
    logger.info(f"   CRF       : {crf}")
    logger.info(f"   Threads   : {threads}")
    logger.info("=" * 55)

    try:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        ffmpeg_params = [
            "-crf", str(crf),
            "-pix_fmt", "yuv420p",
            "-movflags", "+faststart",
            "-profile:v", "high",
        ]

        video_clip.write_videofile(
            output_path,
            fps=fps,
            codec=codec,
            audio_codec=audio_codec,
            audio_bitrate=REEL_AUDIO_BITRATE,
            preset=preset,
            threads=threads,
            ffmpeg_params=ffmpeg_params,
            verbose=verbose,
            logger='bar' if verbose else None,
            temp_audiofile=None,
            remove_temp=True,
        )

        file_size_bytes = os.path.getsize(output_path)
        file_size_mb = round(file_size_bytes / (1024 * 1024), 2)

        result = {
            "path": output_path,
            "size_bytes": file_size_bytes,
            "size_mb": file_size_mb,
            "duration": round(video_clip.duration, 2),
            "resolution": f"{REEL_WIDTH}x{REEL_HEIGHT}",
            "fps": fps,
            "codec": codec,
        }

        logger.info("=" * 55)
        logger.info(f"✅ VIDEO EXPORT SUCCESS")
        logger.info("=" * 55)
        logger.info(f"   File size : {file_size_mb} MB")
        logger.info(f"   Duration  : {result['duration']}s")
        logger.info(f"   Resolution: {result['resolution']}")
        logger.info("=" * 55)

        if file_size_mb > 100:
            logger.warning(f"⚠️  File > 100MB, may fail on Instagram!")
        elif file_size_mb > 50:
            logger.info(f"ℹ️  File size OK for social media")
        else:
            logger.info(f"✅ Optimal file size")

        return result

    except Exception as e:
        logger.error(f"❌ Video export failed: {e}")
        raise


# ============================================================
# MAIN BUILD FUNCTION
# ============================================================

def build_final_video(
    clips: list,
    audio_bytes: Optional[bytes] = None,
    subtitle_srt: Optional[str] = None,
    output_path: str = "output_reel.mp4",
    concat_method: str = "compose",
) -> dict:
    """Build final video from clips + audio + subtitles"""
    logger.info("=" * 55)
    logger.info("=== BUILDING FINAL VIDEO ===")
    logger.info("=" * 55)

    if not clips:
        raise ValueError("No clips provided")

    audio_temp_path = None
    srt_temp_path = None

    try:
        # STEP 1: Concatenate
        logger.info(f"\n🎞️  Step 1/4: Concatenating {len(clips)} clips...")
        merged_video = concatenate_clips(clips, method=concat_method)

        # STEP 2: Audio
        if audio_bytes:
            logger.info("\n🔊 Step 2/4: Attaching audio...")
            merged_video, audio_temp_path = attach_audio_to_video(
                merged_video, audio_bytes
            )
        else:
            logger.warning("\n⚠️  Step 2/4: No audio, video will be silent")

        # STEP 3: Subtitles (PIL-based, no ImageMagick)
        if subtitle_srt and REEL_SUBTITLE_ENABLED:
            logger.info("\n📝 Step 3/4: Adding subtitles (PIL rendering)...")
            try:
                srt_temp_path = _save_srt_to_temp_file(subtitle_srt)
                merged_video = _add_subtitles_to_video(merged_video, srt_temp_path)
            except Exception as e:
                logger.error(f"❌ Subtitle step failed: {e}")
                logger.warning("⚠️  Continuing without subtitles")
        else:
            logger.info("\n📝 Step 3/4: Subtitles skipped")

        # STEP 4: Export
        logger.info("\n💾 Step 4/4: Exporting final MP4...")
        result = export_video(merged_video, output_path)

        # Close clips
        try:
            merged_video.close()
            for clip in clips:
                clip.close()
        except Exception:
            pass

        return result

    except Exception as e:
        logger.error(f"❌ Build failed: {e}")
        raise

    finally:
        _cleanup_temp_files(audio_temp_path, srt_temp_path)


# ============================================================
# STANDALONE TESTING
# ============================================================

if __name__ == "__main__":
    from moviepy.editor import ColorClip

    print("\n" + "=" * 60)
    print("CONCAT ENGINE V2.1 - PIL SUBTITLE TEST (No ImageMagick!)")
    print("=" * 60 + "\n")

    # Check font
    font = _find_font_path()
    if font:
        print(f"✅ Font found: {font}")
    else:
        print(f"❌ No Hindi font — subtitles won't render properly")
        print(f"   Download: fonts/NotoSansDevanagari-Bold.ttf")

    # Create test clips
    print("\n🎨 Creating 3 test color clips...")
    clips = [
        ColorClip(size=(1080, 1920), color=(200, 50, 50), duration=3).set_fps(30),
        ColorClip(size=(1080, 1920), color=(50, 200, 50), duration=3).set_fps(30),
        ColorClip(size=(1080, 1920), color=(50, 50, 200), duration=3).set_fps(30),
    ]

    # Test SRT with Hindi
    test_srt = """1
00:00:00,000 --> 00:00:03,000
भगवान गणेश की जय

2
00:00:03,000 --> 00:00:06,000
मुसीबतें दूर करने वाले

3
00:00:06,000 --> 00:00:09,000
जय गणपति बाप्पा 🙏
"""

    print("\n🎬 Test: Hindi subtitles (PIL rendering)")

    try:
        result = build_final_video(
            clips=clips,
            audio_bytes=None,
            subtitle_srt=test_srt,
            output_path="test_subtitle_pil.mp4"
        )
        print(f"\n✅ Success: {result}")
        print(f"\n💡 Play: start test_subtitle_pil.mp4")
        print(f"   Hindi subtitles should be visible!")

    except Exception as e:
        print(f"\n❌ Failed: {e}")
        import traceback
        traceback.print_exc()