"""
Video Builder - MAIN ORCHESTRATOR for Reel Video Generation

This is the master function that combines everything:

Pipeline:
1. Render each scene image as video clip (Ken Burns effect)
2. Apply transitions (crossfade between scenes)
3. Add fade in/out at video ends
4. Mix voice + BG music
5. Overlay subtitles
6. Export final MP4

Uses:
- clip_renderer (image → clip)
- effects (transitions, fades)
- music_manager (BG music selection + mixing)
- concat_engine (merge + audio + subs + export)

Output: memory.reel_video_bytes (final MP4)
"""

# ═══════════════════════════════════════════════════════════
# 🔧 PIL/Pillow 10.x Compatibility Shim (MUST be before other imports!)
# MoviePy 1.0.3 uses old PIL.Image.ANTIALIAS which was removed in Pillow 10
# ═══════════════════════════════════════════════════════════
import PIL.Image
if not hasattr(PIL.Image, 'ANTIALIAS'):
    PIL.Image.ANTIALIAS = PIL.Image.Resampling.LANCZOS
    
import io
import os
import time
from pathlib import Path

from core.memory import AgentMemory
from config.settings import (
    REEL_WIDTH,
    REEL_HEIGHT,
    REEL_FPS,
    REEL_MUSIC_ENABLED,
)
from utils.logger import get_logger

# Import our video engine modules
from video_engine.clip_renderer import render_all_scenes
from video_engine.effects import apply_all_effects
from video_engine.music_manager import mix_voice_with_music
from video_engine.concat_engine import build_final_video
from video_engine.thumbnail_card import generate_thumbnail_card

logger = get_logger("video_builder")


# ============================================================
# CONFIGURATION
# ============================================================

# Output folder for videos
OUTPUT_FOLDER = Path("logs/videos")

# Video filename pattern
VIDEO_FILENAME_PATTERN = "reel_{session_id}_{timestamp}.mp4"


# ============================================================
# HELPERS
# ============================================================

def _generate_output_path(session_id: str = "") -> str:
    """Generate output path for video file"""
    OUTPUT_FOLDER.mkdir(parents=True, exist_ok=True)

    timestamp = int(time.time())
    filename = VIDEO_FILENAME_PATTERN.format(
        session_id=session_id[:8] if session_id else "reel",
        timestamp=timestamp
    )

    return str(OUTPUT_FOLDER / filename)


def _validate_scenes(scenes: list) -> tuple:
    """
    Validate scenes have required data.

    Returns: (is_valid, reason)
    """
    if not scenes:
        return False, "No scenes provided"

    if len(scenes) < 2:
        return False, f"Need at least 2 scenes, got {len(scenes)}"

    # Check each scene has image_bytes
    scenes_with_images = 0
    for scene in scenes:
        if scene.get("image_bytes"):
            scenes_with_images += 1

    if scenes_with_images < 2:
        return False, f"Only {scenes_with_images}/{len(scenes)} scenes have images"

    return True, f"Valid ({scenes_with_images} scenes with images)"


def _read_video_bytes(video_path: str) -> bytes:
    """Read video file into bytes"""
    with open(video_path, 'rb') as f:
        return f.read()


def _ensure_thumbnail_card(memory: AgentMemory) -> AgentMemory:
    """Generate local branded thumbnail/CTA card if not already present."""
    if getattr(memory, "reel_thumbnail_bytes", None):
        return memory

    try:
        card = generate_thumbnail_card(
            topic=memory.topic,
            category=memory.category,
            session_id=memory.session_id,
        )
        memory.reel_thumbnail_bytes = card["bytes"]
        memory.reel_thumbnail_path = card["path"]
        memory.reel_thumbnail_title = card["title"]
    except Exception as e:
        logger.warning(f"⚠️  Branded thumbnail card generation failed: {e}")

    return memory


def _add_thumbnail_cta_card_scene(memory: AgentMemory) -> AgentMemory:
    """
    Add the branded thumbnail card as an end-card scene.

    The card duration is adjustable and usually replaces part of the last CTA
    scene, so the total video length stays balanced while the thumbnail/handles
    are visible in the video. Audio is later padded to this final target.
    """
    if not getattr(memory, "reel_thumbnail_bytes", None):
        return memory

    if not memory.reel_scenes:
        return memory

    # Avoid duplicate card in recovery/rebuild.
    if any(s.get("scene_type") == "thumbnail_cta" for s in memory.reel_scenes):
        return memory

    base_total = sum(float(s.get("duration_seconds", 0) or 0) for s in memory.reel_scenes)
    voice_target = float(memory.reel_voice_duration or 0) + 0.5  # same padding philosophy as music_manager

    # Default visible end-card duration. If voice is longer than visuals, use
    # the gap (capped) to fill it. If visuals are already longer, replace part
    # of the last scene to keep total duration stable.
    min_card = 1.2
    default_card = 2.0
    max_card = 4.0

    if voice_target > base_total:
        card_duration = max(min_card, min(max_card, voice_target - base_total))
        reduce_last = 0.0
    else:
        card_duration = default_card
        reduce_last = card_duration

    # Take duration from the last normal scene when possible, keeping it readable.
    if reduce_last > 0:
        for scene in reversed(memory.reel_scenes):
            if scene.get("scene_type") != "thumbnail_cta":
                old_duration = float(scene.get("duration_seconds", 0) or 0)
                min_last_scene = 3.0
                actual_reduce = min(reduce_last, max(0.0, old_duration - min_last_scene))
                if actual_reduce > 0:
                    scene["duration_seconds"] = round(old_duration - actual_reduce, 2)
                    card_duration = round(actual_reduce, 2)
                    logger.info(
                        f"🖼️  CTA card duration balanced: last scene "
                        f"{old_duration:.1f}s → {scene['duration_seconds']:.1f}s, "
                        f"card={card_duration:.1f}s"
                    )
                break

    if card_duration < min_card:
        card_duration = min_card

    card_scene = {
        "scene_number": len(memory.reel_scenes) + 1,
        "scene_type": "thumbnail_cta",
        "narration": "",
        "visual_description": "Branded thumbnail CTA card with title and social handles",
        "image_bytes": memory.reel_thumbnail_bytes,
        "duration_seconds": round(card_duration, 2),
        "effect": "static",
        "is_thumbnail_card": True,
    }
    memory.reel_scenes.append(card_scene)
    memory.reel_cta_card_duration = round(card_duration, 2)

    final_total = sum(float(s.get("duration_seconds", 0) or 0) for s in memory.reel_scenes)
    logger.info(
        f"🖼️  Branded thumbnail CTA card added: {card_duration:.1f}s | "
        f"final visual target: {final_total:.1f}s"
    )

    return memory


# ============================================================
# MAIN BUILD FUNCTION
# ============================================================

def build_video(memory: AgentMemory) -> AgentMemory:
    """
    🏆 MAIN VIDEO BUILDER

    Takes memory with scenes + voice + subtitles → produces final MP4

    Pipeline:
    ┌──────────────────────────────────────────────────┐
    │ 1. Validate scenes have images                    │
    │ 2. Render each scene → VideoClip (Ken Burns)      │
    │ 3. Apply effects (crossfade, fade in/out)         │
    │ 4. Mix voice + BG music                           │
    │ 5. Concat + attach audio + burn subtitles         │
    │ 6. Export MP4                                     │
    │ 7. Read bytes into memory                         │
    └──────────────────────────────────────────────────┘

    Args:
        memory: AgentMemory with:
            - reel_scenes (with image_bytes, duration, effect)
            - reel_voice_bytes (MP3)
            - reel_voice_duration (float)
            - reel_subtitle_srt (SRT string, optional)
            - category, mood (for music selection)
            - session_id (for output filename)

    Returns:
        memory with:
            - reel_video_bytes (MP4 bytes)
            - reel_video_path (local file path)
            - reel_duration_seconds
            - reel_video_size_mb
            - reel_music_file (which BG music used)
    """
    logger.info("=" * 55)
    logger.info("=== VIDEO BUILDER शुरू ===")
    logger.info("=" * 55)

    start_time = time.time()

    # ═══════════════════════════════════════════
    # STEP 0: VALIDATION
    # ═══════════════════════════════════════════

    # Recovery check
    if memory.reel_video_bytes and memory.is_recovery:
        logger.info("⏭️  Video already built (recovery), skipping")
        return memory

    # Generate/append branded thumbnail CTA card before rendering.
    memory = _ensure_thumbnail_card(memory)
    memory = _add_thumbnail_cta_card_scene(memory)

    # Validate scenes
    is_valid, reason = _validate_scenes(memory.reel_scenes)
    if not is_valid:
        logger.error(f"❌ Scene validation failed: {reason}")
        memory.add_error("video_builder", f"Scene validation: {reason}")
        return memory

    final_visual_duration = sum(float(s.get('duration_seconds', 0) or 0) for s in memory.reel_scenes)

    logger.info(f"✅ Scene validation: {reason}")
    logger.info(f"🎬 Total scenes: {len(memory.reel_scenes)}")
    logger.info(f"⏱️  Target duration: {final_visual_duration}s")

    # ═══════════════════════════════════════════
    # STEP 1: RENDER SCENES TO CLIPS
    # ═══════════════════════════════════════════
    logger.info("")
    logger.info("--- STEP 1/6: Rendering scenes to clips ---")

    try:
        clips = render_all_scenes(
            scenes=memory.reel_scenes,
            target_size=(REEL_WIDTH, REEL_HEIGHT),
            fps=REEL_FPS
        )

        if not clips:
            raise Exception("No clips rendered successfully")

        if len(clips) < 2:
            raise Exception(f"Only {len(clips)} clip rendered, need at least 2")

        logger.info(f"✅ Rendered {len(clips)} clips")

    except Exception as e:
        logger.error(f"❌ Clip rendering failed: {e}")
        memory.add_error("video_builder", f"Clip rendering: {e}")
        return memory

    # ═══════════════════════════════════════════
    # STEP 2: APPLY EFFECTS (TRANSITIONS + FADES)
    # ═══════════════════════════════════════════
    logger.info("")
    logger.info("--- STEP 2/6: Applying effects (transitions + fades) ---")

    try:
        clips = apply_all_effects(
            clips=clips,
            add_transitions=True,
            add_fade_in_out=True,
        )

        logger.info(f"✅ Effects applied to {len(clips)} clips")

    except Exception as e:
        logger.warning(f"⚠️  Effects failed (continuing without): {e}")
        # Continue with original clips

    # ═══════════════════════════════════════════
    # STEP 3: MIX VOICE + BG MUSIC
    # ═══════════════════════════════════════════
    logger.info("")
    logger.info("--- STEP 3/6: Mixing voice + BG music ---")

    mixed_audio_bytes = memory.reel_voice_bytes
    music_file_used = ""

    if memory.reel_voice_bytes and REEL_MUSIC_ENABLED:
        try:
            mixed_audio_bytes, music_file_used = mix_voice_with_music(
                voice_bytes=memory.reel_voice_bytes,
                voice_duration=memory.reel_voice_duration,
                category=memory.category,
                mood=memory.mood,
                target_duration=final_visual_duration,
            )

            if music_file_used:
                memory.reel_music_file = music_file_used
                logger.info(f"✅ Audio mixed with music: {music_file_used}")
            else:
                logger.info("ℹ️  No music available, using voice only")

        except Exception as e:
            logger.warning(f"⚠️  Music mixing failed: {e}")
            logger.info("ℹ️  Falling back to voice-only")
            mixed_audio_bytes = memory.reel_voice_bytes
    else:
        if not memory.reel_voice_bytes:
            logger.warning("⚠️  No voice bytes - video will be SILENT")
        else:
            logger.info("ℹ️  Music disabled in config")

    # ═══════════════════════════════════════════
    # STEP 4: PREPARE OUTPUT PATH
    # ═══════════════════════════════════════════
    logger.info("")
    logger.info("--- STEP 4/6: Preparing output path ---")

    output_path = _generate_output_path(memory.session_id)
    memory.reel_video_path = output_path
    logger.info(f"📁 Output path: {output_path}")

    # ═══════════════════════════════════════════
    # STEP 5: BUILD FINAL VIDEO
    # ═══════════════════════════════════════════
    logger.info("")
    logger.info("--- STEP 5/6: Building final video (concat + audio + subs + export) ---")

    try:
        result = build_final_video(
            clips=clips,
            audio_bytes=mixed_audio_bytes,
            subtitle_srt=memory.reel_subtitle_srt,
            output_path=output_path,
        )

        # Save to memory
        memory.reel_video_path = result["path"]
        memory.reel_video_size_mb = result["size_mb"]
        memory.reel_duration_seconds = result["duration"]

        logger.info(f"✅ Video built: {result['size_mb']} MB, {result['duration']}s")

    except Exception as e:
        logger.error(f"❌ Video build failed: {e}")
        memory.add_error("video_builder", f"Build: {e}")
        raise

    # ═══════════════════════════════════════════
    # STEP 6: READ VIDEO BYTES
    # ═══════════════════════════════════════════
    logger.info("")
    logger.info("--- STEP 6/6: Loading video bytes into memory ---")

    try:
        video_bytes = _read_video_bytes(output_path)
        memory.reel_video_bytes = video_bytes

        logger.info(f"✅ Video bytes loaded: {len(video_bytes):,} bytes")

    except Exception as e:
        logger.error(f"❌ Failed to read video bytes: {e}")
        memory.add_error("video_builder", f"Read bytes: {e}")
        # Continue anyway - path is set, GCS can upload from path

    # ═══════════════════════════════════════════
    # SUCCESS SUMMARY
    # ═══════════════════════════════════════════
    total_elapsed = round(time.time() - start_time, 2)

    logger.info("")
    logger.info("=" * 55)
    logger.info("✅ VIDEO BUILDER SUCCESS")
    logger.info("=" * 55)
    logger.info(f"   📁 Output path    : {memory.reel_video_path}")
    logger.info(f"   ⏱️  Duration       : {memory.reel_duration_seconds}s")
    logger.info(f"   📏 File size      : {memory.reel_video_size_mb} MB")
    logger.info(f"   🎬 Resolution     : {REEL_WIDTH}x{REEL_HEIGHT} (9:16)")
    logger.info(f"   🎵 Music used     : {memory.reel_music_file or 'None'}")
    logger.info(f"   📝 Subtitles      : {'Yes' if memory.reel_subtitle_srt else 'No'}")
    logger.info(f"   🎤 Voice          : {'Yes' if memory.reel_voice_bytes else 'No'}")
    logger.info(f"   ⏱️  Build time     : {total_elapsed}s")
    logger.info("=" * 55)

    logger.info("=== VIDEO BUILDER पूर्ण ===\n")
    return memory


# ============================================================
# STANDALONE TESTING
# ============================================================

if __name__ == "__main__":
    """
    Test video builder with mock data.

    Requires:
    - fonts/NotoSansDevanagari-Bold.ttf (for subtitles)
    - assets/music/*.mp3 (optional, for music)
    - Google Cloud credentials (for TTS)
    """
    print("\n" + "=" * 60)
    print("VIDEO BUILDER - FULL PIPELINE TEST")
    print("=" * 60 + "\n")

    from PIL import Image as PILImage, ImageDraw

    print("🎨 Creating 3 mock scene images...")

    scenes = []
    colors = [
        ((255, 100, 50), "Scene 1 - Hook"),      # Orange
        ((50, 200, 100), "Scene 2 - Story"),     # Green
        ((100, 50, 200), "Scene 3 - Ending"),    # Purple
    ]

    for i, (color, label) in enumerate(colors, 1):
        # Create test image (portrait 1080x1920)
        img = PILImage.new("RGB", (1080, 1920), color)
        draw = ImageDraw.Draw(img)

        # Draw scene number in center
        try:
            from PIL import ImageFont
            font = ImageFont.truetype("arial.ttf", 200)
        except:
            font = None

        text = f"{i}"
        # Center text
        if font:
            bbox = draw.textbbox((0, 0), text, font=font)
            tw = bbox[2] - bbox[0]
            th = bbox[3] - bbox[1]
            draw.text(
                ((1080 - tw) // 2, (1920 - th) // 2),
                text,
                font=font,
                fill='white'
            )

        # Convert to bytes
        buf = io.BytesIO()
        img.save(buf, format='JPEG', quality=90)
        img_bytes = buf.getvalue()

        scenes.append({
            "scene_number": i,
            "scene_type": ["hook", "context", "cta"][i-1],
            "narration": f"यह दृश्य {i} है",
            "image_bytes": img_bytes,
            "duration_seconds": 3.0,
            "effect": ["zoom_in", "pan_left", "zoom_out"][i-1],
        })

    print(f"✅ Created {len(scenes)} scene images\n")

    # Create test memory
    memory = AgentMemory()
    memory.reel_scenes = scenes
    memory.category = "krishna"
    memory.mood = "peaceful"
    memory.topic = "Test topic"
    memory.post_type = "reel"

    # Try loading test voice + subtitles if available
    test_voice = Path("test_reel_voice.mp3")
    test_srt = Path("test_reel_subtitles_line.srt")

    if test_voice.exists():
        print(f"🎤 Loading test voice: {test_voice}")
        with open(test_voice, 'rb') as f:
            memory.reel_voice_bytes = f.read()
        memory.reel_voice_duration = 9.0
    else:
        print("⚠️  No test voice found, video will be silent")
        print("   Run: python -m video_engine.tts_engine")

    if test_srt.exists():
        print(f"📝 Loading test subtitles: {test_srt}")
        with open(test_srt, 'r', encoding='utf-8') as f:
            memory.reel_subtitle_srt = f.read()
    else:
        print("⚠️  No test subtitles found")
        print("   Run: python -m video_engine.subtitle_generator")

    print()

    # BUILD VIDEO
    try:
        result_memory = build_video(memory)

        print("\n" + "=" * 60)
        print("🎉 TEST SUCCESS!")
        print("=" * 60)
        print(f"   📁 Video path   : {result_memory.reel_video_path}")
        print(f"   ⏱️  Duration     : {result_memory.reel_duration_seconds}s")
        print(f"   📏 File size    : {result_memory.reel_video_size_mb} MB")
        print(f"   🎵 Music        : {result_memory.reel_music_file or 'None'}")
        print("=" * 60)
        print(f"\n💡 Play the video:")
        print(f"   start \"{result_memory.reel_video_path}\"")

    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()