"""
Agent Memory System
Shared memory across all agents in one pipeline run

Updated:
- session_id tracking (recovery के लिए)
- current_stage (कहां तक पहुंचे)
- Recovery resume support

V2 UPDATE: Added Reel fields (story, scenes, voice, video, publishing)
"""
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class AgentMemory:
    """Single memory object passed through all agents"""

    # ═══════════════════════════════════════════
    # 🆕 SESSION TRACKING (Recovery के लिए)
    # ═══════════════════════════════════════════
    session_id: str = ""              # Unique session ID
    current_stage: str = ""           # जहां तक पहुंचे हैं
    is_recovery: bool = False         # क्या ये recovery run है
    resumed_from_stage: str = ""      # किस stage से resume किया
    session_start_time: str = ""      # कब शुरू हुआ

    # Planner output
    topic: str = ""
    category: str = ""
    is_festival: bool = False
    festival_name: str = ""

    # Research output
    keywords: list = field(default_factory=list)
    mood: str = ""
    visual_elements: list = field(default_factory=list)
    colors: list = field(default_factory=list)
    symbols: list = field(default_factory=list)

    # Prompt agent output
    image_prompt: str = ""
    negative_prompt: str = ""
    image_style: str = ""

    # Image agent output
    image_bytes: Optional[bytes] = None
    image_url: str = ""
    image_metadata: dict = field(default_factory=dict)

    # Quality agent output
    quality_passed: bool = False
    quality_score: int = 0
    quality_issues: list = field(default_factory=list)
    regeneration_count: int = 0

    # Caption agent output
    caption: str = ""
    caption_style: str = ""

    # Hashtag agent output
    hashtags: str = ""

    # Publisher output
    ig_post_id: str = ""
    fb_post_id: str = ""
    ig_success: bool = False
    fb_success: bool = False

    # Analytics
    analytics_data: dict = field(default_factory=dict)

    # Meta
    post_id: int = 0
    duration_seconds: float = 0.0
    errors: list = field(default_factory=list)

    # ═══════════════════════════════════════════
    # POST TYPE (Updated: now supports "reel" also)
    # "image" | "carousel" | "reel"
    # ═══════════════════════════════════════════
    post_type: str = "image"

    # ═══════════════════════════════════════════
    # CAROUSEL FIELDS
    # ═══════════════════════════════════════════

    # Each slide dict structure:
    # {
    #   "slide_number": 1,
    #   "slide_type": "hook",          # hook|setup|climax|lesson|cta
    #   "title": "...",
    #   "description": "...",
    #   "image_prompt": "...",
    #   "image_bytes": bytes,
    #   "image_url": "",
    #   "media_id": "",                # After IG upload
    #   "fb_photo_id": "",             # After FB upload
    # }
    carousel_slides: list = field(default_factory=list)
    carousel_caption: str = ""
    carousel_ig_post_id: str = ""
    carousel_fb_post_id: str = ""
    carousel_ig_success: bool = False
    carousel_fb_success: bool = False

    # ═══════════════════════════════════════════
    # 🆕 REEL FIELDS (V2 ADDITION)
    # ═══════════════════════════════════════════

    # Story & structure
    reel_story: str = ""                  # 150-180 word Hindi story
    reel_scenes: list = field(default_factory=list)
    reel_fact_checked: bool = False       # Fact checker passed?

    # Each scene dict structure:
    # {
    #   "scene_number": 1,
    #   "scene_type": "hook",             # hook|context|climax|lesson|reflection|cta
    #   "narration": "Hindi text",        # What TTS will say
    #   "visual_description": "English",  # For prompt building
    #   "image_prompt": "Full prompt",
    #   "duration_seconds": 12,
    #   "image_bytes": bytes,
    #   "image_url": "",
    #   "start_time": 0.0,                # Video timeline start
    #   "end_time": 12.0,                 # Video timeline end
    #   "effect": "zoom_in",              # ken_burns effect type
    # }

    # Voice (TTS output)
    reel_voice_bytes: Optional[bytes] = None    # mp3 bytes
    reel_voice_url: str = ""                    # GCS URL
    reel_voice_duration: float = 0.0            # seconds
    reel_voice_gender: str = ""                 # male/female
    reel_voice_timestamps: list = field(default_factory=list)  # word-level times

    # Subtitles
    reel_subtitle_srt: str = ""                 # SRT format string
    reel_subtitle_style: str = "word_highlight"  # word_highlight | line

    # Video
    reel_video_bytes: Optional[bytes] = None
    reel_video_url: str = ""                    # GCS URL after upload
    reel_video_path: str = ""                   # Local path during build
    reel_video_size_mb: float = 0.0
    reel_duration_seconds: float = 0.0

    # Publishing (3 platforms)
    reel_ig_post_id: str = ""                   # Instagram Reel ID
    reel_fb_post_id: str = ""                   # Facebook Reel ID
    reel_yt_video_id: str = ""                  # YouTube Short video ID
    reel_ig_success: bool = False
    reel_fb_success: bool = False
    reel_yt_success: bool = False

    # Metadata
    reel_music_file: str = ""                   # Which BG music track used
    reel_thumbnail_url: str = ""                # Custom thumbnail URL
    reel_thumbnail_path: str = ""               # Local thumbnail/card path
    reel_thumbnail_title: str = ""              # Title used on thumbnail card
    reel_thumbnail_bytes: Optional[bytes] = None # Local PIL-generated card bytes
    reel_cta_card_duration: float = 0.0         # CTA card duration inside video

    # ═══════════════════════════════════════════
    # RECOVERY HELPERS
    # ═══════════════════════════════════════════

    def __post_init__(self):
        """नया memory बनते ही session_id auto-set करो"""
        if not self.session_id:
            self.session_id = uuid.uuid4().hex[:8]
        if not self.session_start_time:
            self.session_start_time = datetime.now().isoformat()

    def set_stage(self, stage: str):
        """
        Current stage set करो और log करो
        Stages:
        - TOPIC_SELECTED
        - SLIDES_STRUCTURED
        - IMAGES_GENERATED
        - IMAGES_UPLOADED
        - IG_CONTAINERS_READY
        - FB_UPLOADED
        - PUBLISHED
        - 🆕 REEL_STORY_WRITTEN
        - 🆕 REEL_SCENES_SPLIT
        - 🆕 REEL_IMAGES_GENERATED
        - 🆕 REEL_VOICE_GENERATED
        - 🆕 REEL_SUBTITLES_MADE
        - 🆕 REEL_VIDEO_BUILT
        - 🆕 REEL_VIDEO_UPLOADED
        - 🆕 REEL_IG_PUBLISHED
        - 🆕 REEL_FB_PUBLISHED
        - 🆕 REEL_YT_PUBLISHED
        """
        self.current_stage = stage

    def add_error(self, agent: str, error: str):
        """Error track करो"""
        self.errors.append({
            "agent":     agent,
            "error":     error,
            "timestamp": datetime.now().isoformat(),
            "stage":     self.current_stage
        })

    # ═══════════════════════════════════════════
    # CAROUSEL HELPERS
    # ═══════════════════════════════════════════

    def get_slides_with_data(self) -> list:
        """सिर्फ वो slides जिनमें image bytes हैं"""
        return [
            s for s in self.carousel_slides
            if s.get("image_bytes")
        ]

    def get_slides_with_urls(self) -> list:
        """सिर्फ वो slides जिनमें GCS URL है"""
        return [
            s for s in self.carousel_slides
            if s.get("image_url")
        ]

    def get_slides_with_media_ids(self) -> list:
        """सिर्फ वो slides जिनमें IG media_id है"""
        return [
            s for s in self.carousel_slides
            if s.get("media_id")
        ]

    def get_slides_with_fb_ids(self) -> list:
        """सिर्फ वो slides जिनमें FB photo_id है"""
        return [
            s for s in self.carousel_slides
            if s.get("fb_photo_id")
        ]

    # ═══════════════════════════════════════════
    # 🆕 REEL HELPERS
    # ═══════════════════════════════════════════

    def get_scenes_with_images(self) -> list:
        """Reel scenes जिनमें image bytes हैं"""
        return [
            s for s in self.reel_scenes
            if s.get("image_bytes")
        ]

    def get_scenes_with_urls(self) -> list:
        """Reel scenes जिनमें GCS URL है"""
        return [
            s for s in self.reel_scenes
            if s.get("image_url")
        ]

    def reel_is_ready_for_publish(self) -> bool:
        """Check करो कि reel publish करने के लिए ready है"""
        return bool(
            self.reel_video_url and
            self.caption and
            self.hashtags
        )

    def reel_scenes_complete(self) -> bool:
        """Check करो कि सभी scenes ready हैं"""
        if not self.reel_scenes:
            return False
        return all(s.get("image_bytes") for s in self.reel_scenes)

    def get_reel_publish_status(self) -> dict:
        """3 platforms का publish status"""
        return {
            "instagram": self.reel_ig_success,
            "facebook": self.reel_fb_success,
            "youtube": self.reel_yt_success,
            "all_success": all([
                self.reel_ig_success,
                self.reel_fb_success,
                self.reel_yt_success
            ]),
            "any_success": any([
                self.reel_ig_success,
                self.reel_fb_success,
                self.reel_yt_success
            ])
        }

    def to_recovery_dict(self) -> dict:
        """
        Recovery के लिए serializable dict
        (image_bytes, voice_bytes, video_bytes exclude — वो separately save होते हैं)
        """
        # Slides को clean करो — bytes remove
        clean_slides = []
        for slide in self.carousel_slides:
            clean_slide = {k: v for k, v in slide.items() if k != "image_bytes"}
            clean_slides.append(clean_slide)

        # 🆕 Reel scenes को clean करो — bytes remove
        clean_scenes = []
        for scene in self.reel_scenes:
            clean_scene = {k: v for k, v in scene.items() if k != "image_bytes"}
            clean_scenes.append(clean_scene)

        return {
            "session_id":          self.session_id,
            "current_stage":       self.current_stage,
            "session_start_time":  self.session_start_time,
            "topic":               self.topic,
            "category":            self.category,
            "is_festival":         self.is_festival,
            "festival_name":       self.festival_name,
            "post_type":           self.post_type,
            "image_prompt":        self.image_prompt,
            "image_url":           self.image_url,
            "caption":             self.caption,
            "hashtags":            self.hashtags,

            # Carousel
            "carousel_slides":     clean_slides,
            "carousel_caption":    self.carousel_caption,
            "carousel_ig_post_id": self.carousel_ig_post_id,
            "carousel_fb_post_id": self.carousel_fb_post_id,
            "carousel_ig_success": self.carousel_ig_success,
            "carousel_fb_success": self.carousel_fb_success,

            # 🆕 Reel
            "reel_story":            self.reel_story,
            "reel_scenes":           clean_scenes,
            "reel_fact_checked":     self.reel_fact_checked,
            "reel_voice_url":        self.reel_voice_url,
            "reel_voice_duration":   self.reel_voice_duration,
            "reel_voice_gender":     self.reel_voice_gender,
            "reel_voice_timestamps": self.reel_voice_timestamps,
            "reel_subtitle_srt":     self.reel_subtitle_srt,
            "reel_subtitle_style":   self.reel_subtitle_style,
            "reel_video_url":        self.reel_video_url,
            "reel_video_path":       self.reel_video_path,
            "reel_video_size_mb":    self.reel_video_size_mb,
            "reel_duration_seconds": self.reel_duration_seconds,
            "reel_ig_post_id":       self.reel_ig_post_id,
            "reel_fb_post_id":       self.reel_fb_post_id,
            "reel_yt_video_id":      self.reel_yt_video_id,
            "reel_ig_success":       self.reel_ig_success,
            "reel_fb_success":       self.reel_fb_success,
            "reel_yt_success":       self.reel_yt_success,
            "reel_music_file":       self.reel_music_file,
            "reel_thumbnail_url":    self.reel_thumbnail_url,
            "reel_thumbnail_path":   self.reel_thumbnail_path,
            "reel_thumbnail_title":  self.reel_thumbnail_title,
            "reel_cta_card_duration": self.reel_cta_card_duration,

            "errors":              self.errors,
        }

    def restore_from_recovery(self, state: dict, slides_bytes: dict):
        """
        Recovery state से memory restore करो

        Args:
            state: Full state dict from checkpoint
            slides_bytes: Dict with keys:
                - int (1,2,3...) for carousel slides
                - str ("reel_scene_1", "reel_scene_2"...) for reel scenes
                - "voice_bytes" for reel voice
        """
        data = state.get("data", {})

        self.session_id          = state.get("session_id", self.session_id)
        self.current_stage       = state.get("stage", "")
        self.session_start_time  = state.get("timestamp", "")
        self.is_recovery         = True
        self.resumed_from_stage  = state.get("stage", "")

        # Restore all fields
        self.topic               = data.get("topic", "")
        self.category            = data.get("category", "")
        self.is_festival         = data.get("is_festival", False)
        self.festival_name       = data.get("festival_name", "")
        self.post_type           = data.get("post_type", "image")
        self.image_prompt        = data.get("image_prompt", "")
        self.image_url           = data.get("image_url", "")
        self.caption             = data.get("caption", "")
        self.hashtags            = data.get("hashtags", "")

        # Carousel restore
        self.carousel_slides     = data.get("carousel_slides", [])
        self.carousel_caption    = data.get("carousel_caption", "")
        self.carousel_ig_post_id = data.get("carousel_ig_post_id", "")
        self.carousel_fb_post_id = data.get("carousel_fb_post_id", "")
        self.carousel_ig_success = data.get("carousel_ig_success", False)
        self.carousel_fb_success = data.get("carousel_fb_success", False)

        # Restore carousel image bytes into slides
        for slide in self.carousel_slides:
            slide_num = slide.get("slide_number")
            if slide_num in slides_bytes:
                slide["image_bytes"] = slides_bytes[slide_num]
            else:
                slide["image_bytes"] = None

        # 🆕 Reel restore
        self.reel_story            = data.get("reel_story", "")
        self.reel_scenes           = data.get("reel_scenes", [])
        self.reel_fact_checked     = data.get("reel_fact_checked", False)
        self.reel_voice_url        = data.get("reel_voice_url", "")
        self.reel_voice_duration   = data.get("reel_voice_duration", 0.0)
        self.reel_voice_gender     = data.get("reel_voice_gender", "")
        self.reel_voice_timestamps = data.get("reel_voice_timestamps", [])
        self.reel_subtitle_srt     = data.get("reel_subtitle_srt", "")
        self.reel_subtitle_style   = data.get("reel_subtitle_style", "word_highlight")
        self.reel_video_url        = data.get("reel_video_url", "")
        self.reel_video_path       = data.get("reel_video_path", "")
        self.reel_video_size_mb    = data.get("reel_video_size_mb", 0.0)
        self.reel_duration_seconds = data.get("reel_duration_seconds", 0.0)
        self.reel_ig_post_id       = data.get("reel_ig_post_id", "")
        self.reel_fb_post_id       = data.get("reel_fb_post_id", "")
        self.reel_yt_video_id      = data.get("reel_yt_video_id", "")
        self.reel_ig_success       = data.get("reel_ig_success", False)
        self.reel_fb_success       = data.get("reel_fb_success", False)
        self.reel_yt_success       = data.get("reel_yt_success", False)
        self.reel_music_file       = data.get("reel_music_file", "")
        self.reel_thumbnail_url    = data.get("reel_thumbnail_url", "")
        self.reel_thumbnail_path   = data.get("reel_thumbnail_path", "")
        self.reel_thumbnail_title  = data.get("reel_thumbnail_title", "")
        self.reel_cta_card_duration = data.get("reel_cta_card_duration", 0.0)

        # 🆕 Restore reel scene image bytes
        for scene in self.reel_scenes:
            scene_num = scene.get("scene_number")
            key = f"reel_scene_{scene_num}"
            if key in slides_bytes:
                scene["image_bytes"] = slides_bytes[key]
            else:
                scene["image_bytes"] = None

        # 🆕 Restore voice bytes (if in slides_bytes with special key)
        if "voice_bytes" in slides_bytes:
            self.reel_voice_bytes = slides_bytes["voice_bytes"]

        # Restore errors
        self.errors              = data.get("errors", [])

    def to_dict(self) -> dict:
        """DB save के लिए dict"""
        return {
            "session_id":          self.session_id,
            "current_stage":       self.current_stage,
            "is_recovery":         self.is_recovery,
            "topic":               self.topic,
            "category":            self.category,
            "is_festival":         self.is_festival,
            "festival_name":       self.festival_name,
            "post_type":           self.post_type,
            "image_style":         self.image_style,
            "image_url":           self.image_url,
            "caption":             self.caption,
            "hashtags":            self.hashtags,

            # Single image publishing
            "ig_post_id":          self.ig_post_id,
            "fb_post_id":          self.fb_post_id,
            "ig_success":          self.ig_success,
            "fb_success":          self.fb_success,

            # Quality
            "quality_score":       self.quality_score,
            "regeneration_count":  self.regeneration_count,

            # Carousel
            "carousel_slides":     len(self.carousel_slides),
            "carousel_ig_success": self.carousel_ig_success,
            "carousel_fb_success": self.carousel_fb_success,

            # 🆕 Reel
            "reel_video_url":         self.reel_video_url,
            "reel_duration_seconds":  self.reel_duration_seconds,
            "reel_ig_success":        self.reel_ig_success,
            "reel_fb_success":        self.reel_fb_success,
            "reel_yt_success":        self.reel_yt_success,
            "reel_yt_video_id":       self.reel_yt_video_id,
            "reel_scenes_count":      sum(1 for s in self.reel_scenes if not s.get("is_thumbnail_card")),

            "errors":              self.errors
        }