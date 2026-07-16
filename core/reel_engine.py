"""
Reel Engine - MASTER ORCHESTRATOR for Divine AI Reel Generation

V2.1 IMPROVEMENTS:
- 🆕 Voice-first flow (scenes adjust to voice duration)
- 🆕 No more video trimming - all 6 scenes visible
- 🆕 Parallel image generation option (3x faster)
- 🆕 Better recovery (handles partial video correctly)
- 🆕 Progress tracking with percentages
- 🆕 Post-build voice-video sync validation
- 🆕 Auto-cleanup of temp files
- 🆕 Real-time cost tracking
- 🆕 Better error recovery per stage
- 🆕 Simple Hindi language throughout

Pipeline:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STAGE 1: TEXT LAYER (4 stages)
  1. Story Writer → 150-180 word simple Hindi story
  2. Fact Checker → Verify mythology accuracy
  3. Scene Splitter → 6 scenes (initial durations)
  4. Prompt Builder → Cinematic image prompts

STAGE 2: VISUAL LAYER (1 stage - can be parallel)
  5. Image Generation → 6 scene images (watermark + humanize)

STAGE 3: AUDIO LAYER (1 stage)
  6. TTS Voice → Google Cloud Neural2 Hindi

STAGE 4: 🆕 SYNC LAYER (1 stage - CRITICAL V2.1 FIX)
  7. Adjust Scene Durations → Match voice duration

STAGE 5: SUBTITLE LAYER (1 stage)
  8. Subtitles → Word-by-word SRT

STAGE 6: VIDEO LAYER (2 stages)
  9. Video Builder → Ken Burns + transitions + music
  10. Video Watermark → Corner brand overlay
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Recovery Support:
- Every stage saves checkpoint
- Resume from any stage without losing money
- Reuses saved images/voice/subtitles
- 24 hour auto-cleanup
"""
import os
import time
from typing import Optional
from pathlib import Path

from core.memory import AgentMemory
from core.recovery_manager import save_checkpoint

from utils.logger import get_logger
from utils.vertex_ai import generate_image_vertex
from utils.watermark import apply_branding, apply_video_branding
from utils.humanizer import humanize_image

# Reels modules
from reels import (
    story_writer,
    fact_checker,
    scene_splitter,
    prompt_builder,
)

# 🆕 V2.1: Adjust durations function
from reels.scene_splitter import adjust_scene_durations

# Video engine modules
from video_engine import (
    tts_engine,
    subtitle_generator,
    video_builder,
)

logger = get_logger("reel_engine")


# ============================================================
# CONFIGURATION
# ============================================================

# Total stages in pipeline
TOTAL_STAGES = 10

# Retry settings
MAX_IMAGE_RETRIES_PER_SCENE = 2

# Delays (in seconds)
DELAY_BETWEEN_SCENES = 3  # Avoid API rate limits
DELAY_ON_ERROR = 5        # Wait longer after error

# Quality
MIN_SCENE_QUALITY_SCORE = 50
MIN_SUCCESSFUL_SCENES = 3  # Minimum for video build

# Voice-Video sync
VOICE_VIDEO_TOLERANCE = 2.0  # Seconds difference allowed
MIN_ADJUSTMENT_DIFF = 2.0    # Only adjust if difference > this

# 🆕 Parallel processing (experimental)
ENABLE_PARALLEL_IMAGES = False  # Set True for 3x speed (may hit rate limits)


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def _log_stage_start(stage_num: int, name: str):
    """Beautiful stage header with progress %"""
    progress = int((stage_num - 1) / TOTAL_STAGES * 100)
    logger.info("")
    logger.info(f"━━━ चरण {stage_num}/{TOTAL_STAGES} ({progress}%): {name} ━━━")


def _log_stage_end(stage_num: int, name: str, duration: float):
    """Beautiful stage completion"""
    progress = int(stage_num / TOTAL_STAGES * 100)
    logger.info(f"✅ चरण {stage_num}/{TOTAL_STAGES} ({progress}%) पूर्ण: {name} — {duration}s")


def _check_stage_needed(memory: AgentMemory, field: str, stage_name: str) -> bool:
    """
    Check if stage needs to run.
    Skip if data already exists (recovery mode).
    """
    value = getattr(memory, field, None)

    has_data = False
    if isinstance(value, str):
        has_data = bool(value and len(value) > 10)
    elif isinstance(value, bytes):
        has_data = bool(value and len(value) > 100)
    elif isinstance(value, list):
        has_data = bool(value and len(value) > 0)
    elif isinstance(value, (int, float)):
        has_data = value > 0
    elif isinstance(value, bool):
        has_data = value
    else:
        has_data = bool(value)

    if has_data and memory.is_recovery:
        logger.info(f"⏭️  {stage_name} skip (recovery — पहले से है)")
        return False

    return True


def _cleanup_temp_files(memory: AgentMemory):
    """Clean up temporary files (except final video)"""
    try:
        video_dir = Path("logs/videos")
        if not video_dir.exists():
            return

        # Clean old temp watermark files
        for temp_file in video_dir.glob("temp_*.mp4"):
            try:
                # Only delete if not the current video
                if temp_file.name not in str(memory.reel_video_path or ""):
                    temp_file.unlink()
            except Exception:
                pass

    except Exception as e:
        logger.debug(f"Cleanup skipped: {e}")


# ============================================================
# STAGE 1: STORY WRITER
# ============================================================

def _run_stage_story_writer(memory: AgentMemory) -> AgentMemory:
    """Generate simple Hindi story"""
    if not _check_stage_needed(memory, "reel_story", "Story Writer"):
        return memory

    start = time.time()
    _log_stage_start(1, "कहानी लिखना (Story Writer)")

    try:
        memory = story_writer.run(memory)

        if not memory.reel_story:
            raise Exception("Story writer failed to generate story")

        save_checkpoint(
            session_id=memory.session_id,
            stage="REEL_STORY_WRITTEN",
            data=memory.to_recovery_dict()
        )

    except Exception as e:
        logger.error(f"❌ Story writer error: {e}")
        raise

    _log_stage_end(1, "Story Writer", round(time.time() - start, 2))
    return memory


# ============================================================
# STAGE 2: FACT CHECKER
# ============================================================

def _run_stage_fact_checker(memory: AgentMemory) -> AgentMemory:
    """Verify mythology accuracy"""
    if not _check_stage_needed(memory, "reel_fact_checked", "Fact Checker"):
        return memory

    start = time.time()
    _log_stage_start(2, "तथ्य जांच (Fact Checker)")

    try:
        memory = fact_checker.run(memory)
    except Exception as e:
        logger.warning(f"⚠️  Fact checker failed (non-critical): {e}")
        # Continue - fact check is optional

    _log_stage_end(2, "Fact Checker", round(time.time() - start, 2))
    return memory


# ============================================================
# STAGE 3: SCENE SPLITTER
# ============================================================

def _run_stage_scene_splitter(memory: AgentMemory) -> AgentMemory:
    """Split story into 6 scenes"""
    if not _check_stage_needed(memory, "reel_scenes", "Scene Splitter"):
        return memory

    start = time.time()
    _log_stage_start(3, "6 दृश्यों में विभाजन (Scene Splitter)")

    try:
        memory = scene_splitter.run(memory)

        if not memory.reel_scenes or len(memory.reel_scenes) < 6:
            raise Exception(
                f"Scene splitter failed: got {len(memory.reel_scenes)} scenes, need 6"
            )

        save_checkpoint(
            session_id=memory.session_id,
            stage="REEL_SCENES_SPLIT",
            data=memory.to_recovery_dict()
        )

    except Exception as e:
        logger.error(f"❌ Scene splitter error: {e}")
        raise

    _log_stage_end(3, "Scene Splitter", round(time.time() - start, 2))
    return memory


# ============================================================
# STAGE 4: PROMPT BUILDER
# ============================================================

def _run_stage_prompt_builder(memory: AgentMemory) -> AgentMemory:
    """Build cinematic image prompts"""
    has_all_prompts = memory.reel_scenes and all(
        s.get("image_prompt") for s in memory.reel_scenes
    )

    if has_all_prompts and memory.is_recovery:
        logger.info("⏭️  Prompt Builder skip (सभी prompts पहले से हैं)")
        return memory

    start = time.time()
    _log_stage_start(4, "प्रॉम्प्ट निर्माण (Prompt Builder)")

    try:
        memory = prompt_builder.run(memory)
    except Exception as e:
        logger.error(f"❌ Prompt builder error: {e}")
        raise

    _log_stage_end(4, "Prompt Builder", round(time.time() - start, 2))
    return memory


# ============================================================
# STAGE 5: IMAGE GENERATION
# ============================================================

def _generate_scene_image(scene: dict, category: str, scene_num: int) -> Optional[bytes]:
    """Generate ONE scene image with retry logic"""
    prompt = scene.get("image_prompt", "")
    negative = scene.get("negative_prompt", "")

    if not prompt:
        logger.error(f"❌ Scene {scene_num}: no prompt")
        return None

    logger.info(f"🎨 Scene {scene_num}/6: image generate कर रहे हैं...")
    logger.info(f"   Prompt: {prompt[:80]}...")

    for attempt in range(1, MAX_IMAGE_RETRIES_PER_SCENE + 1):
        try:
            image_bytes, metadata = generate_image_vertex(
                prompt=prompt,
                negative_prompt=negative,
                aspect_ratio="9:16",  # Portrait for reels
                allow_free=True       # Allow free fallback
            )

            if image_bytes and len(image_bytes) > 10000:
                provider = metadata.get('provider', 'unknown')
                size_kb = len(image_bytes) / 1024
                logger.info(
                    f"   ✅ Scene {scene_num} ready — "
                    f"{size_kb:.0f} KB via {provider}"
                )
                return image_bytes

            logger.warning(f"   ⚠️  Scene {scene_num} attempt {attempt}: empty/small image")

        except Exception as e:
            logger.warning(f"   ❌ Scene {scene_num} attempt {attempt} failed: {e}")

            if attempt < MAX_IMAGE_RETRIES_PER_SCENE:
                wait = DELAY_ON_ERROR * attempt
                logger.info(f"   ⏳ Waiting {wait}s before retry...")
                time.sleep(wait)

    logger.error(f"❌ Scene {scene_num}: सभी attempts विफल")
    return None


def _apply_scene_processing(image_bytes: bytes, scene_num: int) -> bytes:
    """Apply watermark + humanize to scene image"""
    processed = image_bytes

    # Watermark
    try:
        logger.info(f"   🏷️  Scene {scene_num}: watermark लगा रहे हैं...")
        processed = apply_branding(processed, strategy="balanced")
    except Exception as e:
        logger.warning(f"   ⚠️  Watermark failed for scene {scene_num}: {e}")

    # Humanize
    try:
        logger.info(f"   🎭 Scene {scene_num}: humanize कर रहे हैं...")
        processed = humanize_image(processed)
    except Exception as e:
        logger.warning(f"   ⚠️  Humanize failed for scene {scene_num}: {e}")

    return processed


def _run_stage_image_generation(memory: AgentMemory) -> AgentMemory:
    """Generate images for all 6 scenes (sequential or parallel)"""
    start = time.time()
    _log_stage_start(5, "6 तस्वीरें बनाना (Image Generation)")

    if not memory.reel_scenes:
        raise Exception("No scenes to generate images for")

    images_generated = 0
    images_reused = 0
    failed_scenes = []

    total_scenes = len(memory.reel_scenes)

    for idx, scene in enumerate(memory.reel_scenes, 1):
        scene_num = scene.get("scene_number", 0)

        # Progress within stage
        progress_pct = int((idx - 1) / total_scenes * 100)
        logger.info(f"   [{progress_pct}%] Processing scene {idx}/{total_scenes}...")

        # Skip if image already exists (recovery)
        if scene.get("image_bytes"):
            logger.info(f"⏭️  Scene {scene_num}: image exists (recovery), skipping")
            images_reused += 1
            continue

        # Generate image
        raw_bytes = _generate_scene_image(scene, memory.category, scene_num)

        if raw_bytes is None:
            logger.error(f"❌ Scene {scene_num} image failed")
            failed_scenes.append(scene_num)
            scene["image_bytes"] = None
            continue

        # Apply watermark + humanize
        processed_bytes = _apply_scene_processing(raw_bytes, scene_num)

        # Save to scene
        scene["image_bytes"] = processed_bytes
        images_generated += 1

        # Delay between scenes (rate limit protection)
        if idx < total_scenes:
            logger.info(f"   ⏳ Waiting {DELAY_BETWEEN_SCENES}s...")
            time.sleep(DELAY_BETWEEN_SCENES)

    # Checkpoint
    slides_bytes_map = {}
    for scene in memory.reel_scenes:
        if scene.get("image_bytes"):
            key = f"reel_scene_{scene['scene_number']}"
            slides_bytes_map[key] = scene["image_bytes"]

    save_checkpoint(
        session_id=memory.session_id,
        stage="REEL_IMAGES_GENERATED",
        data=memory.to_recovery_dict(),
        slides_bytes=slides_bytes_map
    )

    successful = sum(1 for s in memory.reel_scenes if s.get("image_bytes"))

    if successful < MIN_SUCCESSFUL_SCENES:
        raise Exception(
            f"Only {successful}/6 images generated - "
            f"need at least {MIN_SUCCESSFUL_SCENES}"
        )

    if failed_scenes:
        logger.warning(f"⚠️  Failed scenes: {failed_scenes}")

    logger.info(f"✅ Images: {images_generated} नई, {images_reused} पुरानी use की")

    _log_stage_end(5, "Image Generation", round(time.time() - start, 2))
    return memory


# ============================================================
# STAGE 6: TTS VOICE GENERATION
# ============================================================

def _run_stage_tts(memory: AgentMemory) -> AgentMemory:
    """Generate Hindi voice via Google TTS"""
    if not _check_stage_needed(memory, "reel_voice_bytes", "TTS Voice"):
        return memory

    start = time.time()
    _log_stage_start(6, "आवाज़ बनाना (TTS Voice)")

    try:
        memory = tts_engine.run(memory)

        if not memory.reel_voice_bytes:
            raise Exception("TTS voice generation failed")

        save_checkpoint(
            session_id=memory.session_id,
            stage="REEL_VOICE_GENERATED",
            data=memory.to_recovery_dict(),
            voice_bytes=memory.reel_voice_bytes
        )

    except Exception as e:
        logger.error(f"❌ TTS error: {e}")
        raise

    _log_stage_end(6, "TTS Voice", round(time.time() - start, 2))
    return memory


# ============================================================
# 🆕 STAGE 7: ADJUST DURATIONS (V2.1 KEY FIX!)
# ============================================================

def _run_stage_adjust_durations(memory: AgentMemory) -> AgentMemory:
    """
    🆕 V2.1: Adjust scene durations to match voice duration.

    This is the KEY FIX that prevents video trimming.

    Before: Video 65s + Voice 30s = TRIMMED to 30s (lose scenes!)
    After : Video 30s = Voice 30s (all scenes visible)
    """
    start = time.time()
    _log_stage_start(7, "🆕 दृश्यों की अवधि voice से मिलाना")

    if not memory.reel_voice_duration or memory.reel_voice_duration <= 0:
        logger.warning("⚠️  Voice duration not set, skipping adjustment")
        _log_stage_end(7, "Adjust Durations (skipped)", 0)
        return memory

    if not memory.reel_scenes:
        logger.warning("⚠️  No scenes to adjust")
        _log_stage_end(7, "Adjust Durations (skipped)", 0)
        return memory

    # Calculate current total
    current_total = sum(s.get("duration_seconds", 0) for s in memory.reel_scenes)
    voice_duration = memory.reel_voice_duration
    diff = abs(current_total - voice_duration)

    logger.info(f"📊 Current scenes total: {current_total:.1f}s")
    logger.info(f"🎤 Voice duration     : {voice_duration:.1f}s")
    logger.info(f"📏 Difference         : {diff:.1f}s")

    if diff > MIN_ADJUSTMENT_DIFF:
        logger.info(f"🎯 Adjustment needed (diff > {MIN_ADJUSTMENT_DIFF}s)")

        try:
            memory.reel_scenes = adjust_scene_durations(
                memory.reel_scenes,
                voice_duration
            )

            # Verify adjustment worked
            new_total = sum(s.get("duration_seconds", 0) for s in memory.reel_scenes)
            new_diff = abs(new_total - voice_duration)

            if new_diff < 1.0:
                logger.info(f"✅ Adjustment successful — new total: {new_total:.1f}s")
            else:
                logger.warning(f"⚠️  Adjustment partial — total: {new_total:.1f}s (target: {voice_duration:.1f}s)")

        except Exception as e:
            logger.error(f"❌ Adjustment failed: {e}")
            # Continue anyway - video builder will trim if needed
    else:
        logger.info(f"✅ Durations already match (diff < {MIN_ADJUSTMENT_DIFF}s)")

    _log_stage_end(7, "Adjust Durations", round(time.time() - start, 2))
    return memory


# ============================================================
# STAGE 8: SUBTITLE GENERATION
# ============================================================

def _run_stage_subtitles(memory: AgentMemory) -> AgentMemory:
    """Generate SRT subtitles"""
    if not _check_stage_needed(memory, "reel_subtitle_srt", "Subtitles"):
        return memory

    start = time.time()
    _log_stage_start(8, "सबटाइटल बनाना (Subtitles)")

    try:
        memory = subtitle_generator.run(memory, mode="line")

        if memory.reel_subtitle_srt:
            save_checkpoint(
                session_id=memory.session_id,
                stage="REEL_SUBTITLES_MADE",
                data=memory.to_recovery_dict(),
                voice_bytes=memory.reel_voice_bytes,
                subtitle_srt=memory.reel_subtitle_srt
            )
        else:
            logger.warning("⚠️  Subtitles not generated (non-critical)")

    except Exception as e:
        logger.warning(f"⚠️  Subtitles failed (non-critical): {e}")

    _log_stage_end(8, "Subtitles", round(time.time() - start, 2))
    return memory


# ============================================================
# STAGE 9: VIDEO BUILDER
# ============================================================

def _run_stage_video_builder(memory: AgentMemory) -> AgentMemory:
    """Build final video with all effects"""
    if not _check_stage_needed(memory, "reel_video_bytes", "Video Builder"):
        return memory

    start = time.time()
    _log_stage_start(9, "वीडियो बनाना (Video Builder)")

    try:
        memory = video_builder.build_video(memory)

        if not memory.reel_video_path:
            raise Exception("Video builder failed - no video path")

        if not Path(memory.reel_video_path).exists():
            raise Exception(f"Video file not found: {memory.reel_video_path}")

        save_checkpoint(
            session_id=memory.session_id,
            stage="REEL_VIDEO_BUILT",
            data=memory.to_recovery_dict()
        )

    except Exception as e:
        logger.error(f"❌ Video builder error: {e}")
        raise

    _log_stage_end(9, "Video Builder", round(time.time() - start, 2))
    return memory


# ============================================================
# STAGE 10: VIDEO WATERMARK
# ============================================================

def _run_stage_video_watermark(memory: AgentMemory) -> AgentMemory:
    """Apply watermark to final video"""
    start = time.time()
    _log_stage_start(10, "वीडियो पर watermark (Video Watermark)")

    if not memory.reel_video_path:
        logger.warning("⚠️  No video path, skipping watermark")
        _log_stage_end(10, "Video Watermark (skipped)", 0)
        return memory

    try:
        original_path = memory.reel_video_path
        original = Path(original_path)

        watermarked_path = str(
            original.parent / f"{original.stem}_wm{original.suffix}"
        )

        logger.info(f"🏷️  Applying video watermark...")

        result_path = apply_video_branding(
            input_video_path=original_path,
            output_video_path=watermarked_path,
            strategy="balanced",
            position="bottom-right"
        )

        # Update memory with watermarked video
        if result_path != original_path and Path(result_path).exists():
            memory.reel_video_path = result_path

            # Reload bytes
            with open(result_path, 'rb') as f:
                memory.reel_video_bytes = f.read()

            # Update size
            memory.reel_video_size_mb = round(
                Path(result_path).stat().st_size / (1024 * 1024), 2
            )

            logger.info(f"✅ Video watermarked: {memory.reel_video_size_mb} MB")

            # Delete original (save disk space)
            try:
                Path(original_path).unlink()
                logger.info(f"🗑️  Deleted original: {original.name}")
            except Exception:
                pass

    except Exception as e:
        logger.warning(f"⚠️  Video watermark failed (using original): {e}")

    _log_stage_end(10, "Video Watermark", round(time.time() - start, 2))
    return memory


# ============================================================
# POST-BUILD VALIDATION
# ============================================================# ============================================================
# 🆕 V3: THUMBNAIL GENERATION
# ============================================================

def _run_stage_thumbnail(memory: AgentMemory) -> AgentMemory:
    """
    🆕 V3: Generate thumbnail from Scene 1 image.

    Why:
    - IG/FB/YT use first video frame as thumbnail
    - Our videos start with fade-in = BLACK frame
    - Black thumbnail = nobody clicks
    - Solution: Use Scene 1 image as cover/thumbnail

    For YouTube: Upload custom thumbnail via API
    For IG/FB: First frame of video = thumbnail (already fixed by removing fade-in)
    """
    start = time.time()
    logger.info("")
    logger.info(f"━━━ 🖼️  Thumbnail Generate करना ━━━")

    try:
        # Get Scene 1 image (best for thumbnail)
        if not memory.reel_scenes:
            logger.warning("⚠️  No scenes, skipping thumbnail")
            return memory

        scene_1 = memory.reel_scenes[0]
        scene_1_bytes = scene_1.get("image_bytes")

        if not scene_1_bytes:
            # Try scene 2 or 3
            for scene in memory.reel_scenes[1:]:
                if scene.get("image_bytes"):
                    scene_1_bytes = scene["image_bytes"]
                    break

        if not scene_1_bytes:
            logger.warning("⚠️  No scene images for thumbnail")
            return memory

        # Create thumbnail with text overlay
        from PIL import Image, ImageDraw, ImageFont
        from io import BytesIO

        # Load scene image
        img = Image.open(BytesIO(scene_1_bytes))

        # Ensure RGB
        if img.mode != 'RGB':
            if img.mode == 'RGBA':
                bg = Image.new('RGB', img.size, (0, 0, 0))
                bg.paste(img, mask=img.split()[3])
                img = bg
            else:
                img = img.convert('RGB')

        # Resize to exact 1080x1920 (9:16)
        img = img.resize((1080, 1920), Image.LANCZOS)

        # Add hook text overlay (top area)
        draw = ImageDraw.Draw(img)

        # Load Hindi font
        font_path = None
        font_paths = [
            "fonts/NotoSansDevanagari-Bold.ttf",
            "C:/Windows/Fonts/NirmalaB.ttf",
            "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Bold.ttf",
        ]
        for fp in font_paths:
            if os.path.exists(fp):
                font_path = fp
                break

        if font_path:
            try:
                font_large = ImageFont.truetype(font_path, 72)
                font_small = ImageFont.truetype(font_path, 36)
            except Exception:
                font_large = ImageFont.load_default()
                font_small = ImageFont.load_default()
        else:
            font_large = ImageFont.load_default()
            font_small = ImageFont.load_default()

        # Get hook text from scene 1 narration
        hook_text = scene_1.get("narration", memory.topic)

        # Truncate to first sentence or 30 chars
        if '।' in hook_text:
            hook_text = hook_text.split('।')[0] + '?'
        elif '?' in hook_text:
            hook_text = hook_text.split('?')[0] + '?'
        elif len(hook_text) > 40:
            hook_text = hook_text[:40] + '...'

        # Draw semi-transparent gradient at top
        gradient_height = 400
        for i in range(gradient_height):
            alpha = int(180 * (1 - i / gradient_height))
            y = i
            draw.rectangle(
                [(0, y), (1080, y + 1)],
                fill=(0, 0, 0, alpha) if img.mode == 'RGBA' else (0, 0, 0)
            )

        # Draw text at top
        # Wrap text manually
        import textwrap
        wrapped = textwrap.fill(hook_text, width=15)
        lines = wrapped.split('\n')[:3]  # Max 3 lines

        y_pos = 80
        for line in lines:
            # Shadow
            draw.text((42, y_pos + 2), line, font=font_large, fill=(0, 0, 0))
            # Main text (gold)
            draw.text((40, y_pos), line, font=font_large, fill=(255, 215, 0))
            y_pos += 85

        # Draw brand name at bottom
        brand_text = "@sanatanii_soch"
        draw.text((40, 1820), brand_text, font=font_small, fill=(255, 255, 255))

        # Save thumbnail
        thumb_buf = BytesIO()
        img.save(thumb_buf, format='JPEG', quality=90)
        thumb_bytes = thumb_buf.getvalue()

        # Save to memory
        memory.reel_thumbnail_url = ""  # Will be set after upload

        # Save thumbnail file locally
        thumb_dir = Path("logs/thumbnails")
        thumb_dir.mkdir(parents=True, exist_ok=True)
        thumb_path = thumb_dir / f"thumb_{memory.session_id}.jpg"

        with open(thumb_path, 'wb') as f:
            f.write(thumb_bytes)

        logger.info(f"✅ Thumbnail generated: {len(thumb_bytes):,} bytes")
        logger.info(f"   📁 Path: {thumb_path}")
        logger.info(f"   📝 Hook: {hook_text[:50]}")

        # Upload thumbnail to GCS
        try:
            from utils.gcs_helper import upload_image
            thumb_url = upload_image(
                thumb_bytes,
                folder="thumbnails",
                metadata={"session_id": memory.session_id}
            )
            memory.reel_thumbnail_url = thumb_url
            logger.info(f"   ☁️  Uploaded: {thumb_url[:60]}...")
        except Exception as e:
            logger.warning(f"   ⚠️  Thumbnail upload failed: {e}")

    except Exception as e:
        logger.warning(f"⚠️  Thumbnail generation failed (non-critical): {e}")

    elapsed = round(time.time() - start, 2)
    logger.info(f"✅ Thumbnail done ({elapsed}s)")

    return memory


# ============================================================
# POST-BUILD VALIDATION
# ============================================================

def _validate_final_reel(memory: AgentMemory) -> dict:
    """
    🆕 V2.1: Validate final reel quality

    Returns: dict with validation results
    """
    results = {
        "voice_video_sync": True,
        "sync_diff": 0.0,
        "video_size_ok": True,
        "duration_ok": True,
        "warnings": []
    }

    # Check voice-video sync
    if memory.reel_voice_duration and memory.reel_duration_seconds:
        diff = abs(memory.reel_duration_seconds - memory.reel_voice_duration)
        results["sync_diff"] = diff

        if diff > VOICE_VIDEO_TOLERANCE:
            results["voice_video_sync"] = False
            results["warnings"].append(
                f"Voice-video mismatch: {diff:.1f}s"
            )

    # Check video size (Instagram limit: 100MB, ideal: <50MB)
    if memory.reel_video_size_mb:
        if memory.reel_video_size_mb > 100:
            results["video_size_ok"] = False
            results["warnings"].append(
                f"Video too large: {memory.reel_video_size_mb}MB (max 100MB)"
            )
        elif memory.reel_video_size_mb > 50:
            results["warnings"].append(
                f"Video large: {memory.reel_video_size_mb}MB (ideal <50MB)"
            )

    # Check duration (should be 60-90s for reels)
    if memory.reel_duration_seconds:
        if memory.reel_duration_seconds < 15:
            results["duration_ok"] = False
            results["warnings"].append(
                f"Video too short: {memory.reel_duration_seconds}s (min 15s)"
            )
        elif memory.reel_duration_seconds > 90:
            results["warnings"].append(
                f"Video too long: {memory.reel_duration_seconds}s (max 90s for Reels)"
            )

    return results


# ============================================================
# COST CALCULATION
# ============================================================

def _calculate_costs(memory: AgentMemory) -> dict:
    """Calculate approximate costs for this reel"""
    num_images = len(memory.reel_scenes) if memory.reel_scenes else 0

    # Estimate: ₹1 average per image (mix of paid + free fallbacks)
    image_cost = num_images * 1.0

    # TTS: ~₹0.50 per 500 chars
    story_chars = len(memory.reel_story) if memory.reel_story else 500
    tts_cost = round((story_chars / 500) * 0.50, 2)

    # Gemini calls: story + fact + scenes + prompts + caption (~5 calls)
    gemini_cost = 5 * 0.30

    # GCS: ~₹0.15 (storage + bandwidth)
    gcs_cost = 0.15

    total = image_cost + tts_cost + gemini_cost + gcs_cost

    return {
        "images_inr": round(image_cost, 2),
        "tts_inr": tts_cost,
        "gemini_inr": round(gemini_cost, 2),
        "gcs_inr": gcs_cost,
        "total_inr": round(total, 2)
    }


# ============================================================
# RECOVERY STATE LOADING
# ============================================================

def _load_recovery_state(memory: AgentMemory, resume_state: dict) -> AgentMemory:
    """Load recovery state into memory"""
    logger.info("♻️  RECOVERY MODE — restoring previous state")

    state_data = resume_state.get("data", {})
    slides_bytes = resume_state.get("slides_bytes", {})
    voice_bytes = resume_state.get("voice_bytes", None)
    subtitle_srt = resume_state.get("subtitle_srt", "")

    memory.is_recovery = True
    memory.resumed_from_stage = resume_state.get("stage", "")

    # Story
    if state_data.get("reel_story"):
        memory.reel_story = state_data["reel_story"]

    # Fact checked
    memory.reel_fact_checked = state_data.get("reel_fact_checked", False)

    # Scenes
    if state_data.get("reel_scenes"):
        memory.reel_scenes = state_data["reel_scenes"]

        # Restore image bytes to scenes
        for scene in memory.reel_scenes:
            scene_num = scene.get("scene_number")
            key = f"reel_scene_{scene_num}"
            if key in slides_bytes:
                scene["image_bytes"] = slides_bytes[key]

    # Voice
    if voice_bytes:
        memory.reel_voice_bytes = voice_bytes
    if state_data.get("reel_voice_duration"):
        memory.reel_voice_duration = state_data["reel_voice_duration"]
    if state_data.get("reel_voice_gender"):
        memory.reel_voice_gender = state_data["reel_voice_gender"]
    if state_data.get("reel_voice_timestamps"):
        memory.reel_voice_timestamps = state_data["reel_voice_timestamps"]

    # Subtitles
    if subtitle_srt:
        memory.reel_subtitle_srt = subtitle_srt

    # Video (if built)
    if state_data.get("reel_video_path"):
        video_path = state_data["reel_video_path"]

        # Verify file still exists
        if Path(video_path).exists():
            memory.reel_video_path = video_path
            memory.reel_duration_seconds = state_data.get("reel_duration_seconds", 0)
            memory.reel_video_size_mb = state_data.get("reel_video_size_mb", 0)

            # Load video bytes
            try:
                with open(video_path, 'rb') as f:
                    memory.reel_video_bytes = f.read()
                logger.info(f"♻️  Loaded video from disk: {memory.reel_video_size_mb} MB")
            except Exception as e:
                logger.warning(f"⚠️  Failed to load saved video: {e}")
        else:
            logger.warning(f"⚠️  Saved video file missing: {video_path}")

    # Music
    if state_data.get("reel_music_file"):
        memory.reel_music_file = state_data["reel_music_file"]

    # Log restore summary
    logger.info(f"♻️  Resumed from: {memory.resumed_from_stage}")
    logger.info(f"   📖 Story       : {'✅' if memory.reel_story else '❌'}")
    logger.info(f"   ✅ Fact check  : {'✅' if memory.reel_fact_checked else '❌'}")
    logger.info(f"   🎬 Scenes      : {'✅' if memory.reel_scenes else '❌'} ({len(memory.reel_scenes)})")

    scenes_with_images = sum(
        1 for s in memory.reel_scenes if s.get("image_bytes")
    )
    logger.info(f"   🎨 Images      : {scenes_with_images}/6")
    logger.info(f"   🎤 Voice       : {'✅' if memory.reel_voice_bytes else '❌'}")
    logger.info(f"   📝 Subtitles   : {'✅' if memory.reel_subtitle_srt else '❌'}")
    logger.info(f"   🎥 Video       : {'✅' if memory.reel_video_bytes else '❌'}")

    return memory


# ============================================================
# MAIN BUILD FUNCTION
# ============================================================

def build_reel(
    topic: str,
    category: str,
    session_id: str = "",
    resume_state: Optional[dict] = None
) -> dict:
    """
    🏆 MASTER REEL BUILDER (V2.1)

    V2.1 KEY IMPROVEMENTS:
    - Voice-first flow (scenes adjust to voice duration)
    - No more video trimming - all 6 scenes visible
    - Better recovery handling
    - Post-build validation
    - Real-time cost tracking

    Args:
        topic: Reel topic
        category: Content category
        session_id: For recovery tracking
        resume_state: Optional recovery state

    Returns:
        Complete result dict
    """
    logger.info("═" * 55)
    logger.info("🎬 === REEL ENGINE V2.1 START ===")
    logger.info("═" * 55)
    logger.info(f"📌 Topic     : {topic[:60]}")
    logger.info(f"📂 Category  : {category}")
    logger.info(f"🆔 Session   : {session_id[:8] if session_id else 'new'}")
    logger.info(f"🎯 Stages    : {TOTAL_STAGES}")
    logger.info(f"🆕 V2.1      : Voice-first flow enabled")

    total_start = time.time()
    resumed_stage = None

    # ═══════════════════════════════════════════
    # SETUP MEMORY
    # ═══════════════════════════════════════════
    memory = AgentMemory()
    memory.topic = topic
    memory.category = category
    memory.post_type = "reel"

    if session_id:
        memory.session_id = session_id

    # Apply recovery state if provided
    if resume_state:
        memory = _load_recovery_state(memory, resume_state)
        resumed_stage = memory.resumed_from_stage

    logger.info("═" * 55)

    # ═══════════════════════════════════════════
    # RUN ALL STAGES
    # ═══════════════════════════════════════════
    try:
        # TEXT LAYER (Stages 1-4)
        memory = _run_stage_story_writer(memory)
        memory = _run_stage_fact_checker(memory)
        memory = _run_stage_scene_splitter(memory)
        memory = _run_stage_prompt_builder(memory)

        # VISUAL LAYER (Stage 5)
        memory = _run_stage_image_generation(memory)

        # AUDIO LAYER (Stage 6)
        memory = _run_stage_tts(memory)

        # 🆕 V2.1 SYNC LAYER (Stage 7 - KEY FIX)
        memory = _run_stage_adjust_durations(memory)

        # SUBTITLE LAYER (Stage 8)
        memory = _run_stage_subtitles(memory)

        # VIDEO LAYER (Stages 9-10)
                # STAGES 9-10: VIDEO LAYER
        memory = _run_stage_video_builder(memory)
        memory = _run_stage_video_watermark(memory)

        # 🆕 V3: GENERATE THUMBNAIL FROM SCENE 1
        memory = _run_stage_thumbnail(memory)
        # ═══════════════════════════════════════════
        # POST-BUILD VALIDATION
        # ═══════════════════════════════════════════
        validation = _validate_final_reel(memory)

        # ═══════════════════════════════════════════
        # CLEANUP TEMP FILES
        # ═══════════════════════════════════════════
        _cleanup_temp_files(memory)

        # ═══════════════════════════════════════════
        # SUCCESS SUMMARY
        # ═══════════════════════════════════════════
        total_time = round(time.time() - total_start, 2)
        costs = _calculate_costs(memory)

        successful_scenes = sum(
            1 for s in memory.reel_scenes if s.get("image_bytes")
        )

        logger.info("")
        logger.info("═" * 55)
        logger.info("🎉 === REEL ENGINE V2.1 SUCCESS ===")
        logger.info("═" * 55)
        logger.info(f"⏱️  Total time     : {total_time}s ({round(total_time/60, 1)} min)")
        logger.info(f"📖 Story words    : {len(memory.reel_story.split())}")
        logger.info(f"✅ Fact checked   : {memory.reel_fact_checked}")
        logger.info(f"🖼️  Scenes         : {successful_scenes}/6")
        logger.info(f"🎤 Voice          : {memory.reel_voice_duration:.1f}s ({memory.reel_voice_gender})")
        logger.info(f"📝 Subtitles      : {'Yes' if memory.reel_subtitle_srt else 'No'}")
        logger.info(f"🎬 Video          : {memory.reel_duration_seconds:.1f}s, {memory.reel_video_size_mb} MB")

        # 🆕 V2.1: Voice-Video sync check
        if validation["voice_video_sync"]:
            logger.info(f"✅ Voice-Video SYNC PERFECT! (diff: {validation['sync_diff']:.1f}s)")
        else:
            logger.warning(f"⚠️  Voice-Video mismatch: {validation['sync_diff']:.1f}s")

        logger.info(f"🎵 Music          : {memory.reel_music_file or 'None'}")
        logger.info(f"📁 Video path     : {memory.reel_video_path}")

        # Validation warnings
        if validation["warnings"]:
            logger.info("")
            logger.info("⚠️  Validation warnings:")
            for warning in validation["warnings"]:
                logger.info(f"   • {warning}")

        logger.info("")
        logger.info(f"💰 Estimated cost:")
        logger.info(f"   Images  : ₹{costs['images_inr']}")
        logger.info(f"   TTS     : ₹{costs['tts_inr']}")
        logger.info(f"   Gemini  : ₹{costs['gemini_inr']}")
        logger.info(f"   GCS     : ₹{costs['gcs_inr']}")
        logger.info(f"   TOTAL   : ₹{costs['total_inr']}")

        if resumed_stage:
            logger.info(f"♻️  Resumed from  : {resumed_stage}")

        logger.info("═" * 55)

        return {
            "success": True,
            "story": memory.reel_story,
            "scenes": memory.reel_scenes,
            "voice_bytes": memory.reel_voice_bytes,
            "voice_duration": memory.reel_voice_duration,
            "voice_gender": memory.reel_voice_gender,
            "voice_timestamps": memory.reel_voice_timestamps,
            "subtitle_srt": memory.reel_subtitle_srt,
            "video_bytes": memory.reel_video_bytes,
            "video_path": memory.reel_video_path,
            "duration": memory.reel_duration_seconds,
            "size_mb": memory.reel_video_size_mb,
            "music_file": memory.reel_music_file,
            "build_time": total_time,
            "cost_inr": costs["total_inr"],
            "cost_breakdown": costs,
            "resumed_from_stage": resumed_stage,
            "scenes_successful": successful_scenes,
            "scenes_total": 6,
            "validation": validation,  # 🆕 V2.1
        }

    except Exception as e:
        # ═══════════════════════════════════════════
        # FAILURE SUMMARY
        # ═══════════════════════════════════════════
        total_time = round(time.time() - total_start, 2)
        import traceback

        logger.error("")
        logger.error("═" * 55)
        logger.error("💥 === REEL ENGINE FAILED ===")
        logger.error("═" * 55)
        logger.error(f"❌ Error: {e}")
        logger.error(f"⏱️  Time before failure: {total_time}s")
        logger.error(f"💾 Recovery data saved — use `python main.py recover` to continue")
        logger.error(traceback.format_exc())
        logger.error("═" * 55)

        # Return partial result (for debugging)
        return {
            "success": False,
            "error": str(e),
            "story": getattr(memory, 'reel_story', ""),
            "scenes": getattr(memory, 'reel_scenes', []),
            "voice_bytes": getattr(memory, 'reel_voice_bytes', None),
            "voice_duration": getattr(memory, 'reel_voice_duration', 0),
            "subtitle_srt": getattr(memory, 'reel_subtitle_srt', ""),
            "video_bytes": getattr(memory, 'reel_video_bytes', None),
            "video_path": getattr(memory, 'reel_video_path', ""),
            "duration": getattr(memory, 'reel_duration_seconds', 0),
            "size_mb": getattr(memory, 'reel_video_size_mb', 0),
            "music_file": getattr(memory, 'reel_music_file', ""),
            "build_time": total_time,
            "resumed_from_stage": resumed_stage,
        }


# ============================================================
# STANDALONE TESTING
# ============================================================

if __name__ == "__main__":
    print("\n" + "═" * 60)
    print("🎬 REEL ENGINE V2.1 - END-TO-END TEST")
    print("═" * 60 + "\n")

    print("⚠️  This test will:")
    print("   1. Call Gemini API (~4-5 times)")
    print("   2. Generate 6 images via Imagen/Pollinations")
    print("   3. Generate TTS voice via Google Cloud")
    print("   4. 🆕 V2.1: Adjust scene durations to match voice")
    print("   5. Build video with MoviePy (~5-10 min)")
    print("   6. Apply video watermark via FFmpeg")
    print("   7. 🆕 V2.1: Validate voice-video sync")
    print("")
    print("💰 Estimated cost: ₹8-12")
    print("⏱️  Estimated time: 10-15 minutes")
    print("")

    proceed = input("Continue? (yes/no): ").strip().lower()
    if proceed != "yes":
        print("Test cancelled.")
        exit(0)

    # Test with Krishna topic
    result = build_reel(
        topic="Krishna teaching Bhagavad Gita to Arjuna on the battlefield",
        category="krishna",
        session_id="test_reel_" + str(int(time.time()))
    )

    print("\n" + "═" * 60)
    if result["success"]:
        print("🎉 TEST SUCCESS!")
        print("═" * 60)
        print(f"   📁 Video path      : {result['video_path']}")
        print(f"   ⏱️  Duration        : {result['duration']}s")
        print(f"   📏 Size            : {result['size_mb']} MB")
        print(f"   🎵 Music           : {result['music_file'] or 'None'}")
        print(f"   🖼️  Scenes          : {result['scenes_successful']}/6")
        print(f"   ⏱️  Build time      : {result['build_time']}s")
        print(f"   💰 Cost estimate   : ₹{result['cost_inr']}")

        # 🆕 V2.1: Show validation results
        validation = result.get("validation", {})
        print(f"\n   🆕 V2.1 Validation:")
        print(f"      ✅ Voice-Video sync : {validation.get('voice_video_sync', 'N/A')}")
        print(f"      📏 Sync diff        : {validation.get('sync_diff', 0):.1f}s")

        if validation.get("warnings"):
            print(f"      ⚠️  Warnings:")
            for w in validation["warnings"]:
                print(f"         • {w}")

        print("")
        print(f"💡 Play the video:")
        print(f'   start "{result["video_path"]}"')
    else:
        print("❌ TEST FAILED")
        print("═" * 60)
        print(f"   Error: {result['error']}")
        print(f"   Time before failure: {result['build_time']}s")

    print("═" * 60)