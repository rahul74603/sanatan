"""
Agent Memory System
Shared memory across all agents in one pipeline run

Updated:
- session_id tracking (recovery के लिए)
- current_stage (कहां तक पहुंचे)
- Recovery resume support
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
    # CAROUSEL FIELDS
    # ═══════════════════════════════════════════
    post_type: str = "image"           # "image" | "carousel"

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

    def to_recovery_dict(self) -> dict:
        """
        Recovery के लिए serializable dict
        (image_bytes exclude — वो separately save होते हैं)
        """
        # Slides को clean करो — bytes remove
        clean_slides = []
        for slide in self.carousel_slides:
            clean_slide = {k: v for k, v in slide.items() if k != "image_bytes"}
            clean_slides.append(clean_slide)

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
            "carousel_slides":     clean_slides,
            "carousel_caption":    self.carousel_caption,
            "carousel_ig_post_id": self.carousel_ig_post_id,
            "carousel_fb_post_id": self.carousel_fb_post_id,
            "carousel_ig_success": self.carousel_ig_success,
            "carousel_fb_success": self.carousel_fb_success,
            "errors":              self.errors,
        }

    def restore_from_recovery(self, state: dict, slides_bytes: dict):
        """
        Recovery state से memory restore करो
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

        # Restore image bytes into slides
        for slide in self.carousel_slides:
            slide_num = slide.get("slide_number")
            if slide_num in slides_bytes:
                slide["image_bytes"] = slides_bytes[slide_num]
            else:
                slide["image_bytes"] = None

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
            "ig_post_id":          self.ig_post_id,
            "fb_post_id":          self.fb_post_id,
            "ig_success":          self.ig_success,
            "fb_success":          self.fb_success,
            "quality_score":       self.quality_score,
            "regeneration_count":  self.regeneration_count,
            "carousel_slides":     len(self.carousel_slides),
            "carousel_ig_success": self.carousel_ig_success,
            "carousel_fb_success": self.carousel_fb_success,
            "errors":              self.errors
        }