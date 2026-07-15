"""
Effects - Video transitions and fades

Features:
- Crossfade transitions between scenes (smooth blend)
- Fade in at video start
- Fade out at video end
- Intro/outro clip attachment (optional)
- Compatible with clip_renderer output

Uses MoviePy's built-in effects.

V2 FIX: MoviePy 1.0.3 import paths corrected
- crossfadein/crossfadeout are METHODS on clips, not standalone imports
- fadein/fadeout imported from moviepy.video.fx module
"""
# ═══════════════════════════════════════════════════════════
# 🔧 PIL/Pillow 10.x Compatibility Shim (MUST be before other imports!)
# MoviePy 1.0.3 uses old PIL.Image.ANTIALIAS which was removed in Pillow 10
# ═══════════════════════════════════════════════════════════
import PIL.Image
if not hasattr(PIL.Image, 'ANTIALIAS'):
    PIL.Image.ANTIALIAS = PIL.Image.Resampling.LANCZOS

from moviepy.editor import (
    CompositeVideoClip,
    concatenate_videoclips,
    VideoFileClip,
    ColorClip,
)

# ✅ CORRECT MoviePy 1.0.3 imports
# fadein/fadeout are direct functions
from moviepy.video.fx.fadein import fadein
from moviepy.video.fx.fadeout import fadeout

# ✅ crossfadein/crossfadeout are methods on VideoClip class
# We use them like: clip.crossfadein(duration) or clip.crossfadeout(duration)

from config.settings import (
    REEL_TRANSITION_DURATION,
    REEL_TRANSITION_TYPE,
    REEL_WIDTH,
    REEL_HEIGHT,
)
from utils.logger import get_logger

logger = get_logger("effects")


# ============================================================
# CONFIGURATION
# ============================================================

DEFAULT_TRANSITION_DURATION = REEL_TRANSITION_DURATION  # 0.5s
DEFAULT_FADE_IN_DURATION = 0.5    # Fade in at video start
DEFAULT_FADE_OUT_DURATION = 0.7   # Fade out at video end


# ============================================================
# CROSSFADE TRANSITIONS
# ============================================================

def apply_crossfade(clips: list, transition_duration: float = DEFAULT_TRANSITION_DURATION) -> list:
    """
    Apply crossfade transitions between consecutive clips.

    Each clip fades OUT while the next fades IN, creating smooth blend.

    Args:
        clips: List of VideoClip objects
        transition_duration: Duration of crossfade in seconds

    Returns:
        List of clips with crossfades applied (ready for concatenation)

    Note:
        In MoviePy 1.0.3, crossfadein/crossfadeout are METHODS on VideoClip:
        - clip.crossfadein(duration)
        - clip.crossfadeout(duration)
    """
    if len(clips) < 2:
        logger.info("ℹ️  Less than 2 clips, no crossfade needed")
        return clips

    logger.info(f"🎞️  Applying crossfade transitions ({transition_duration}s)")

    result = []

    for i, clip in enumerate(clips):
        try:
            # First clip: only fade OUT at end
            if i == 0:
                clip = clip.crossfadeout(transition_duration)

            # Last clip: only fade IN at beginning
            elif i == len(clips) - 1:
                clip = clip.crossfadein(transition_duration)

            # Middle clips: both fade IN and OUT
            else:
                clip = clip.crossfadein(transition_duration)
                clip = clip.crossfadeout(transition_duration)

            result.append(clip)

        except Exception as e:
            logger.warning(f"⚠️  Crossfade failed for clip {i+1}: {e}")
            # Use original clip if transition fails
            result.append(clip)

    logger.info(f"✅ Applied crossfades to {len(result)} clips")

    return result


# ============================================================
# FADE IN / FADE OUT
# ============================================================

def apply_fade_in(clip, duration: float = DEFAULT_FADE_IN_DURATION):
    """
    Fade in from black at the start of clip.

    Args:
        clip: VideoClip
        duration: Fade in duration in seconds

    Returns:
        Clip with fade in effect
    """
    try:
        result = fadein(clip, duration)
        logger.debug(f"✅ Applied fade in ({duration}s)")
        return result
    except Exception as e:
        logger.warning(f"⚠️  Fade in failed: {e}")
        return clip


def apply_fade_out(clip, duration: float = DEFAULT_FADE_OUT_DURATION):
    """
    Fade out to black at the end of clip.

    Args:
        clip: VideoClip
        duration: Fade out duration in seconds

    Returns:
        Clip with fade out effect
    """
    try:
        result = fadeout(clip, duration)
        logger.debug(f"✅ Applied fade out ({duration}s)")
        return result
    except Exception as e:
        logger.warning(f"⚠️  Fade out failed: {e}")
        return clip


def apply_fade_in_out(clip, fade_in_duration: float = None, fade_out_duration: float = None):
    """
    Apply both fade in and fade out to a clip.

    Args:
        clip: VideoClip
        fade_in_duration: Defaults to DEFAULT_FADE_IN_DURATION
        fade_out_duration: Defaults to DEFAULT_FADE_OUT_DURATION

    Returns:
        Clip with both fades applied
    """
    if fade_in_duration is None:
        fade_in_duration = DEFAULT_FADE_IN_DURATION
    if fade_out_duration is None:
        fade_out_duration = DEFAULT_FADE_OUT_DURATION

    clip = apply_fade_in(clip, fade_in_duration)
    clip = apply_fade_out(clip, fade_out_duration)

    return clip


# ============================================================
# INTRO / OUTRO ATTACHMENT
# ============================================================

def add_intro(
    main_clip,
    intro_path: str = None,
    default_intro_duration: float = 1.5
):
    """
    Attach intro clip at the beginning of main video.

    If intro_path is provided and exists, use that video file.
    Otherwise, creates a simple black intro (fallback).

    Args:
        main_clip: Main VideoClip
        intro_path: Path to intro video file (optional)
        default_intro_duration: Duration for fallback intro

    Returns:
        Combined clip: [intro] + [main_clip]
    """
    from pathlib import Path

    intro_clip = None

    # Try loading intro file
    if intro_path and Path(intro_path).exists():
        try:
            logger.info(f"🎬 Loading intro from: {intro_path}")
            intro_clip = VideoFileClip(intro_path)

            # Resize to match main clip if needed
            if intro_clip.size != main_clip.size:
                intro_clip = intro_clip.resize(main_clip.size)

        except Exception as e:
            logger.warning(f"⚠️  Failed to load intro: {e}")
            intro_clip = None

    # Fallback: black intro
    if intro_clip is None:
        logger.info("🎬 Using default black intro")
        intro_clip = ColorClip(
            size=(REEL_WIDTH, REEL_HEIGHT),
            color=(0, 0, 0),
            duration=default_intro_duration
        )

    # Concatenate intro + main
    combined = concatenate_videoclips([intro_clip, main_clip], method="compose")

    logger.info(f"✅ Added intro ({intro_clip.duration}s)")

    return combined


def add_outro(
    main_clip,
    outro_path: str = None,
    default_outro_duration: float = 2.0
):
    """
    Attach outro clip at the end of main video.

    Args:
        main_clip: Main VideoClip
        outro_path: Path to outro video file (optional)
        default_outro_duration: Duration for fallback outro

    Returns:
        Combined clip: [main_clip] + [outro]
    """
    from pathlib import Path

    outro_clip = None

    # Try loading outro file
    if outro_path and Path(outro_path).exists():
        try:
            logger.info(f"🎬 Loading outro from: {outro_path}")
            outro_clip = VideoFileClip(outro_path)

            if outro_clip.size != main_clip.size:
                outro_clip = outro_clip.resize(main_clip.size)

        except Exception as e:
            logger.warning(f"⚠️  Failed to load outro: {e}")
            outro_clip = None

    # Fallback: black outro
    if outro_clip is None:
        logger.info("🎬 Using default black outro")
        outro_clip = ColorClip(
            size=(REEL_WIDTH, REEL_HEIGHT),
            color=(0, 0, 0),
            duration=default_outro_duration
        )

    # Concatenate main + outro
    combined = concatenate_videoclips([main_clip, outro_clip], method="compose")

    logger.info(f"✅ Added outro ({outro_clip.duration}s)")

    return combined


# ============================================================
# COMBINED EFFECTS PIPELINE
# ============================================================

def apply_all_effects(
    clips: list,
    add_transitions: bool = True,
    add_fade_in_out: bool = True,
    transition_duration: float = None,
    fade_in_duration: float = None,
    fade_out_duration: float = None,
) -> list:
    """
    Apply all standard effects to a list of clips.

    Order of operations:
    1. Add crossfades between clips
    2. Apply fade in on first clip
    3. Apply fade out on last clip

    Args:
        clips: List of VideoClip objects
        add_transitions: Enable crossfades between clips
        add_fade_in_out: Enable fade in/out at video ends
        transition_duration: Override default transition time
        fade_in_duration: Override default fade in time
        fade_out_duration: Override default fade out time

    Returns:
        List of clips with all effects applied
    """
    if not clips:
        logger.warning("⚠️  No clips to apply effects to")
        return []

    # Defaults
    if transition_duration is None:
        transition_duration = DEFAULT_TRANSITION_DURATION
    if fade_in_duration is None:
        fade_in_duration = DEFAULT_FADE_IN_DURATION
    if fade_out_duration is None:
        fade_out_duration = DEFAULT_FADE_OUT_DURATION

    logger.info("🎨 Applying video effects pipeline...")

    result = list(clips)  # Copy

    # Step 1: Crossfades
    if add_transitions and len(result) >= 2:
        result = apply_crossfade(result, transition_duration)

    # Step 2: Fade in on first clip
    if add_fade_in_out and result:
        result[0] = apply_fade_in(result[0], fade_in_duration)

    # Step 3: Fade out on last clip
    if add_fade_in_out and result:
        result[-1] = apply_fade_out(result[-1], fade_out_duration)

    logger.info(f"✅ Effects pipeline complete ({len(result)} clips)")

    return result


# ============================================================
# STANDALONE TESTING
# ============================================================

if __name__ == "__main__":
    """
    Test effects on simple color clips.
    Just verifies MoviePy effects work correctly.
    """
    print("\n" + "=" * 60)
    print("EFFECTS - STANDALONE TEST (V2 FIXED)")
    print("=" * 60 + "\n")

    # Create 3 color clips for testing
    print("🎨 Creating 3 test color clips...")

    clips = [
        ColorClip(size=(1080, 1920), color=(255, 100, 100), duration=2).set_fps(30),  # Red
        ColorClip(size=(1080, 1920), color=(100, 255, 100), duration=2).set_fps(30),  # Green
        ColorClip(size=(1080, 1920), color=(100, 100, 255), duration=2).set_fps(30),  # Blue
    ]

    print(f"✅ Created {len(clips)} clips (2s each)")

    # Test 1: Just crossfade
    print("\n🎬 Test 1: Crossfade only")
    faded_clips = apply_crossfade(clips, transition_duration=0.5)
    combined = concatenate_videoclips(faded_clips, method="compose")
    combined.write_videofile(
        "test_effects_crossfade.mp4",
        fps=30, codec='libx264',
        verbose=False, logger=None, audio=False
    )
    combined.close()
    print("✅ Saved: test_effects_crossfade.mp4")

    # Test 2: All effects
    print("\n🎬 Test 2: All effects (crossfade + fade in/out)")

    # Reset clips (they get modified by previous test)
    clips2 = [
        ColorClip(size=(1080, 1920), color=(255, 100, 100), duration=2).set_fps(30),
        ColorClip(size=(1080, 1920), color=(100, 255, 100), duration=2).set_fps(30),
        ColorClip(size=(1080, 1920), color=(100, 100, 255), duration=2).set_fps(30),
    ]

    all_effects_clips = apply_all_effects(
        clips2,
        add_transitions=True,
        add_fade_in_out=True,
        transition_duration=0.5,
        fade_in_duration=0.7,
        fade_out_duration=0.7,
    )

    combined2 = concatenate_videoclips(all_effects_clips, method="compose")
    combined2.write_videofile(
        "test_effects_all.mp4",
        fps=30, codec='libx264',
        verbose=False, logger=None, audio=False
    )
    combined2.close()
    print("✅ Saved: test_effects_all.mp4")

    print("\n" + "=" * 60)
    print("✅ Effects test complete!")
    print("=" * 60)
    print("\n💡 Play test videos to see transitions:")
    print("   start test_effects_crossfade.mp4")
    print("   start test_effects_all.mp4")