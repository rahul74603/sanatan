# 🕉️ DIVINE AI CONTENT FACTORY V2 — MASTER CONTEXT FILE

> **PURPOSE:** Ye file complete project context deti hai. Agar AI chat khatam ho jaye ya naye chat mein continue karna ho, to bas ye file paste karo — AI turant sab samajh jayega ki kya already hai, kya banana hai, aur kahan se continue karna hai.

**Last Updated:** [Auto-fill karo jab bhi update karo]  
**Owner:** Rahul  
**Project Path:** `C:\Users\Rahul\Desktop\सनातन सोच\spiritual-auto-post`  
**GitHub:** [Add repo URL]

---

## 🚨 CRITICAL RULES (AI MUST FOLLOW)

1. ❌ **NEVER** rewrite working modules
2. ❌ **NEVER** break backward compatibility
3. ❌ **NEVER** assume — always inspect existing code first
4. ❌ **NEVER** create duplicate files
5. ✅ **ALWAYS** extend existing modules if solution exists
6. ✅ **ALWAYS** reuse maximum code (target: 70%+)
7. ✅ **ALWAYS** follow existing coding patterns
8. ✅ **ALWAYS** show Purpose/Inputs/Outputs/Dependencies before writing code
9. ✅ **ALWAYS** get user approval before writing each module
10. ✅ **ALWAYS** work module-by-module (never all files at once)

---

## 📊 PROJECT STATUS

### ✅ WHAT ALREADY EXISTS (Working in Production)

**Automation:** Daily posts on Instagram + Facebook (via GitHub Actions)

**Existing Features:**
- ✅ Topic Selection (200+ topics, festival-aware, weekday deity-based)
- ✅ AI Prompt Generation (Gemini)
- ✅ AI Image Generation (Imagen 4.0 → Imagen 3 → Gemini → Pollinations fallback chain)
- ✅ Caption Generation (10 styles, Hindi/Hinglish)
- ✅ Humanizer (anti-AI detection)
- ✅ Watermark (anti-crop, 4-layer branding)
- ✅ Facebook Posting (single image + album carousel)
- ✅ Instagram Posting (single image + carousel with recovery)
- ✅ Scheduler (GitHub Actions cron)
- ✅ Analytics (learning system — best styles, categories, hashtags, times)
- ✅ Memory (AgentMemory dataclass across all agents)
- ✅ Recovery Manager (checkpoint-based, saves ₹15/failure)
- ✅ Database (SQLite with post_history, analytics, style_performance)
- ✅ GCS Upload (retry logic, cleanup)
- ✅ Logger (colored, rotating, error separation)
- ✅ Cost Tracking (daily/monthly budget alerts)

---

## 🎯 PROJECT GOAL (V2)

Convert existing project into a **Complete AI Spiritual Media Factory** that generates:
- Images ✅ (already working)
- Carousels ✅ (already working)  
- **Reels** 🆕 (to be added)
- **Short Videos** 🆕 (to be added)
- **YouTube Shorts** 🆕 (to be added)

Automatically. Daily. 3 posts/day.

---

## 📅 FINAL POSTING SCHEDULE (User Confirmed)

| Time (IST) | Content Type | Status |
|---|---|---|
| **8:00 AM** | Single Premium Image | ✅ Existing (auto_image.yml) |
| **1:00 PM** | Reel (60-90s video) — 🆕 ab har 2 din mein 1 (video day) | auto_reel.yml |
| **8:00 PM** | Carousel (5 slides) / Reel / Image | ✅ Existing (auto_evening.yml) |

**V3 Note:** Reels ab daily nahi — har `VIDEO_EVERY_DAYS` (default 2) din mein 1
video. Non-video day → us slot mein image fallback (kam se kam pic).

---

## 📁 EXISTING FOLDER STRUCTURE

```
SPIRITUAL-AUTO-POST/
├── .github/workflows/
│   ├── auto_carousel.yml          [EXISTING - 8 PM Carousel]
│   └── auto_image.yml             [EXISTING - 8 AM Image]
│
├── agents/                        [ALL EXISTING]
│   ├── __init__.py                (blank)
│   ├── analytics_agent.py         (Learning system)
│   ├── caption_agent.py           (10 styles, Hindi/Hinglish)
│   ├── carousel_agent.py          (Thin wrapper for carousel_engine)
│   ├── hashtag_agent.py           (5-tier hashtag system)
│   ├── image_agent.py             (Uses vertex_ai + humanizer + watermark)
│   ├── planner_agent.py           (Strategic content decision)
│   ├── prompt_agent.py            (Category-specific art styles)
│   ├── publisher_agent.py         (IG + FB posting + carousel + recovery)
│   ├── quality_agent.py           (10-check image validation)
│   └── research_agent.py          (Visual elements + mood extraction)
│
├── config/
│   ├── __init__.py
│   ├── settings.py                [Central config, env vars]
│   └── topics.py                  [200+ topics + 50+ festivals]
│
├── core/
│   ├── __init__.py
│   ├── carousel_engine.py         [Story→5 slides→images→caption]
│   ├── database.py                [SQLite: post_history, analytics, style_performance]
│   ├── memory.py                  [AgentMemory dataclass with recovery]
│   └── recovery_manager.py        [Checkpoint system, 24h auto-cleanup]
│
├── utils/
│   ├── __init__.py
│   ├── gcs_helper.py              [Upload to Google Cloud Storage]
│   ├── humanizer.py               [Anti-AI detection for images]
│   ├── logger.py                  [Colored console + file logs]
│   ├── vertex_ai.py               [4-stage image gen fallback]
│   └── watermark.py               [Anti-crop 4-layer branding]
│
├── fonts/                         [EXISTING but empty]
├── logs/                          [Runtime logs]
├── venv/                          [Python virtual environment]
│
├── .env                           [Secrets — NEVER commit]
├── .gitignore
├── divine_poster.db               [SQLite database]
├── main.py                        [Entry point — CLI + Cloud Function]
├── requirements.txt               [Python dependencies]
├── spiritual-service-account.json [GCP credentials]
├── test_hindi_font.ttf
├── test_hindi.png
├── test_ig.py
└── tree.py
```

---

## 🔑 EXISTING FILES — DETAILED BREAKDOWN

### **main.py** (Entry Point)
- Has `run_pipeline()` for single image
- Has `run_carousel_pipeline()` for carousel with recovery
- Has `run_recovery_only()` for pending recoveries
- Has `auto_post()` cloud function HTTP entry
- Has `_run_cli()` with commands: `image`, `carousel`, `carousel-new`, `recover`, `recovery-stats`, `recovery-cleanup`, `test`, `health`, `cost`, `help`
- Pattern to follow for `run_reel_pipeline()`: same as carousel

### **config/settings.py**
- Central config: PROJECT_ID, LOCATION, BUCKET_NAME
- Gemini: GEMINI_API_KEY, GEMINI_MODEL, temperature settings
- Vertex AI: USE_VERTEX_AI, VERTEX_MODEL, budget limits (₹100/day, ₹2000/month)
- Pollinations: fallback enabled
- Meta: INSTAGRAM_ACCOUNT_ID, FACEBOOK_PAGE_ID, ACCESS_TOKEN
- Posting: POSTING_HOURS, delays
- Content: MAX_CAPTION_LENGTH=2200, MAX_HASHTAGS=25
- Quality: IMAGE_QUALITY_MIN_BYTES=30000, MAX_REGENERATION_ATTEMPTS=3
- Feature flags dictionary

### **config/topics.py**
- `TOPIC_POOL` dict with 12 categories (krishna, shiva, hanuman, ganesha, durga, ram, motivational, spiritual_nature, temple, festival_moments, daily_wisdom, festival)
- ~200+ detailed topics
- `FESTIVAL_CALENDAR` dict with 50+ festivals mapped to (month, day)
- `TIME_PREFERENCES` for morning/afternoon/evening/night
- `SEASONAL_PREFERENCES`
- `WEEKDAY_PREFERENCES` (Monday=Shiva, Tuesday=Hanuman, etc.)
- Helper functions: `get_smart_topic()`, `get_festival_today()`, `get_upcoming_festivals()`

### **core/memory.py** — `AgentMemory` dataclass
**Existing fields:**
- Session: session_id, current_stage, is_recovery, resumed_from_stage, session_start_time
- Planner: topic, category, is_festival, festival_name
- Research: keywords, mood, visual_elements, colors, symbols
- Prompt: image_prompt, negative_prompt, image_style
- Image: image_bytes, image_url, image_metadata
- Quality: quality_passed, quality_score, quality_issues, regeneration_count
- Caption: caption, caption_style
- Hashtag: hashtags
- Publisher: ig_post_id, fb_post_id, ig_success, fb_success
- Analytics: analytics_data
- Meta: post_id, duration_seconds, errors
- **post_type: str = "image"** (supports "image" | "carousel", need to add "reel")
- Carousel: carousel_slides, carousel_caption, carousel_ig_post_id, carousel_fb_post_id, carousel_ig_success, carousel_fb_success

**Methods:**
- `set_stage()`, `add_error()`, `get_slides_with_data/urls/media_ids/fb_ids()`
- `to_recovery_dict()`, `restore_from_recovery()`, `to_dict()`

### **core/database.py**
**Tables:**
- `post_history` (id, post_date, topic, category, image_style, image_url, caption, hashtags, ig_post_id, fb_post_id, ig_success, fb_success, duration_seconds)
- `analytics` (id, post_id, platform, likes, comments, shares, reach, impressions)
- `style_performance` (image_style, total_posts, total_reach, total_likes, avg_reach)
- `used_content` (content_type, content_value)

**Functions:**
- `initialize_database()`, `save_post()`, `get_recent_topics()`, `save_analytics()`, `update_style_performance()`, `get_best_performing_styles()`, `mark_content_used()`, `is_content_used()`

### **core/carousel_engine.py** — 🏆 GOLDEN TEMPLATE for Reel Engine
- `generate_slide_structure()` — Gemini generates 5-slide Hindi story (hook/setup/climax/lesson/cta)
- `generate_slide_image()` — Uses vertex_ai.generate_image_vertex()
- `apply_premium_overlay()` — Hindi text overlay with header, gradient, title, description, footer
- `generate_carousel_caption()` — Full Hindi Instagram caption
- `build_carousel()` — Main orchestrator with recovery support
- Font paths: Windows Nirmala + Linux Noto Sans Devanagari fallback

### **core/recovery_manager.py**
**Stages defined:**
```python
STAGES = {
    "TOPIC_SELECTED": 1,
    "SLIDES_STRUCTURED": 2,
    "IMAGES_GENERATED": 3,
    "IMAGES_UPLOADED": 4,
    "IG_CONTAINERS_READY": 5,
    "FB_UPLOADED": 6,
    "PUBLISHED": 7,
}
```
- `save_checkpoint()`, `load_checkpoint()`, `delete_checkpoint()`
- `find_pending_recovery()`, `cleanup_old_recoveries()`, `calculate_savings()`
- `display_recovery_stats()`, `display_pending_recovery()`
- Saves image bytes locally in `logs/recovery/{session_id}/slide_N.jpg`

### **utils/vertex_ai.py**
**4-stage fallback chain:**
1. Vertex AI SDK (paid, best quality) — SKIP_VERTEX_SDK=True currently
2. Vertex REST API (paid) — SKIP_VERTEX_REST=True currently
3. Gemini API (paid, ₹0.50)
4. Pollinations AI (FREE)

- Cost tracking in `logs/vertex_usage.json`
- Budget alerts (daily ₹100, monthly ₹2000)
- Aspect ratios supported: 1:1, 3:4, 4:3, **9:16 (perfect for Reels)**, 16:9

### **utils/watermark.py**
- `apply_branding(image_bytes, strategy)` with 3 strategies:
  - `maximum` — All 4 layers (diagonal + center + corners + micro)
  - `balanced` — Diagonal + center + corners (DEFAULT)
  - `minimal` — Diagonal + corners only
- Handle: `@sanatanii_soch`
- Brand: `सनातनी सोच`
- Anti-crop diagonal pattern across entire image
- **Video watermark NOT YET IMPLEMENTED** (to add for Reels)

### **utils/humanizer.py**
- `humanize_image()` — Random brightness/contrast/color/sharpness, occasional blur/vignette, random JPEG quality
- `humanize_caption()` — Remove AI artifacts, vary punctuation, manage emojis

### **utils/gcs_helper.py**
- `upload_image()` — With retry, metadata, public URL, MD5 hash
- `upload_file()` — Upload from disk
- `delete_blob()`, `cleanup_old_files()`, `get_bucket_stats()`
- **`upload_video()` NOT YET IMPLEMENTED** (to add for Reels)

### **utils/logger.py**
- `get_logger(name)` — Colored console + file logs
- Helper functions: `log_header`, `log_separator`, `log_success`, `log_failure`, `log_dict`, `log_warning_box`
- Auto rotation (10MB), error separation, 30-day cleanup

### **agents/planner_agent.py**
- Strategic decisions: priority level, content angle, target audience, SEO theme, time slot, season
- Weekday deity preferences
- Peak engagement hours: morning_worship (5-8), office_break (12-14), evening_prayer (18-21), night_reflection (21-23)
- Selects topic avoiding recent repetition

### **agents/research_agent.py**
- Gemini call for keywords, mood, visual_elements, colors, symbols, time_of_day, setting
- In-memory cache
- Comprehensive fallback database for all deities

### **agents/prompt_agent.py**
- 8 art styles: cinematic, oil_painting, hyperrealistic, moody_atmospheric, divine_golden, temple_photography, traditional_indian, epic_fantasy
- Category-specific artistic references (Raja Ravi Varma for Krishna, etc.)
- Composition + lighting selection
- Analytics-based style selection (70% winner, 30% explore)
- Strong negative prompt

### **agents/image_agent.py**
- USE_GEMINI_PRIMARY=True
- Gemini Imagen 4.0 → Pollinations fallback
- Category-specific style enhancers
- Applies humanization + branding + upload
- Metadata tracking

### **agents/quality_agent.py**
**10 checks:**
1. File size (min 30KB)
2. Corruption (CRITICAL)
3. Dimensions (min 512px, ideal 1024px)
4. Aspect ratio (0.75-1.35 for square, need to add 9:16 for reels)
5. Brightness (30-240)
6. Contrast (min 15)
7. Color diversity (min 100 unique colors)
8. Sharpness (Laplacian variance)
9. Duplicate detection (perceptual hash)
10. AI content validation (Gemini Vision, optional)

- Pass threshold: 60/100
- Max regenerations: 3

### **agents/caption_agent.py**
**10 caption styles:**
- short_powerful, storytelling, question_engaging, shayari_style, personal_thought, conversational, gratitude_style, festival_special, reminder_style, devotional_deep

- Deity-specific names/phrases/emotions
- Rich fallback library (50+ captions per category)
- Auto-detect style based on category + strategy

### **agents/hashtag_agent.py**
**5-tier strategy:**
- Tier 1: Massive reach (2 tags) — #india, #instagood
- Tier 2: High reach (4 tags) — #spiritual, #hindu
- Tier 3: Medium reach (8 tags) — Category-specific — SWEET SPOT
- Tier 4: Niche (6 tags) — #spiritualawakening, #gitawisdom
- Tier 5: Micro (3 tags) — #sanatansooch (brand)

- Festival hashtags (auto on festival days)
- Weekday hashtags (Monday=#mondaymotivation etc.)
- Time-based hashtags
- Blocked list (shadow-ban protection)
- Auto-dedup, max 25 total

### **agents/publisher_agent.py** — MOST COMPLEX
**Handles:**
- Single image → IG (container + publish) + FB (direct photo)
- Carousel → IG (upload each → carousel container → publish) + FB (upload → album feed)
- **Reels flow NOT YET IMPLEMENTED**

**Key fixes already in place:**
- IG media_id expiry check (Error 2207032 fix)
- Container ready waiting (FINISHED status polling)
- Retry with exponential backoff
- Rate limit handling

### **agents/analytics_agent.py**
**Tracks:**
- IG basic metrics (likes, comments) + insights (reach, impressions, saves, shares)
- FB metrics (likes, comments, shares, reactions)
- Category performance, caption style performance, time slot performance, hashtag performance
- Generates AI insights (best categories, times, styles, hashtags)

**Extended tables:**
- category_performance, caption_style_performance, time_slot_performance, hashtag_performance, insights

---

## 🆕 V3 — FREE / PRO / AUTO MODE SYSTEM

> **Purpose:** Budget khatam hone par bhi content rukta nahi. Mode switch karke
> paid (PRO) aur ₹0 (FREE) ke beech jao. Reel/video fail ho to bhi **kam se kam
> ek picture (pic) ban hi jati hai.**

### 3 Modes
| Mode | Images | Reels/Video | Cost |
|---|---|---|---|
| **free** | Sirf Pollinations (₹0) | ✅ agar free path ho, warna pic | ₹0 |
| **pro** | Premium Vertex Imagen | ✅ Enabled (TTS + video) | Paid |
| **auto** (default) | Pro, budget khatam → free | Video fail → pic fallback | As needed |

### 🎬 VIDEO FREQUENCY — har 2 din mein 1 video
- Reels ab **daily nahi** — har `VIDEO_EVERY_DAYS` (default **2**) din mein 1 video.
- **PRO mode** → video day par video bane.
- **FREE mode** → video sirf tab jab free path possible ho
  (`FREE_MODE_ALLOWS_VIDEO=true` + video pipeline available). Warna pic.
- Non-video day → us slot mein image fallback (kam se kam pic).
- Change karo: `.env` mein `VIDEO_EVERY_DAYS=3` → har 3 din mein 1 video.
- Decision `core.mode_manager.is_video_day()` / `should_make_video()` se:
  last video DB date ke baad `VIDEO_EVERY_DAYS` din ho → video day.
- `core/database.get_todays_content_type()` bhi is rule ko respect karta hai
  (afternoon/evening ab video day par hi "reel" deta hai).

### Switch karo (persistent, restart ke baad bhi bana rehta hai)
```bash
python main.py mode            # status
python main.py mode free       # ₹0, sirf images
python main.py mode pro        # paid (premium)
python main.py mode auto       # pro, budget khatam → free fallback
```

### .env se bhi set kar sakte ho
```bash
APP_MODE=auto                    # free | pro | auto (default auto)
FREE_MODE_DISABLES_REELS=false   # true → free mode mein video bilkul band
FREE_MODE_ALLOWS_VIDEO=true      # free mode mein video allow (agar free path ho)
VIDEO_EVERY_DAYS=2               # har 2 din mein 1 video (default)
```

### Kya hota hai
- **FREE mode** → `image_agent` paid Vertex/Imagen bypass karke seedha
  Pollinations (₹0) use karta hai. Video: `run_reel_pipeline` mein
  `should_make_video()` — video day + free path ho to video, warna picture.
- **AUTO mode** → daily/monthly Vertex budget (`VERTEX_DAILY_BUDGET` /
  `VERTEX_MONTHLY_BUDGET`) exhausted hone par auto FREE mein degrade ho jata
  hai (budget check `utils/vertex_ai.estimate_images_remaining()` se).
- **Reel fail fallback** → reel_engine video build fail kare to pipeline crash
  nahi hoti; uski jagah single-image pipeline chal kar ek picture post ho
  jati hai (flag `_mode_fallback`).
- **Video day** → har `VIDEO_EVERY_DAYS` din mein 1 video (`is_video_day()`).
  Non-video day → image fallback.
- State `logs/mode_state.json` mein save hoti hai (gitignored).

### Files
- 🆕 `core/mode_manager.py` — mode logic (get/set, budget check, capability)
- `config/settings.py` — `APP_MODE`, `MODE_STATE_FILE`, `FREE_MODE_DISABLES_REELS`
- `agents/image_agent.py` — FREE mode → Pollinations only
- `main.py` — `mode` CLI + health/cost mode display + reel→image fallback

---

## 💰 CURRENT BUDGET USAGE

- **Existing:** 1 Image (₹75/mo) + 1 Carousel (₹375/mo) = **₹450/month**
- **With Reels:** + ₹500/mo (1 reel/day) = **₹950/month total**
- **Budget limit:** ₹2000/month → **Well within budget ✅**

**Per Reel cost:**
- 6 Images (Imagen 4): ₹15
- Google TTS Hindi: ₹0.50
- Gemini (story + scenes + fact-check + caption): ₹0.85
- GCS storage + bandwidth: ₹0.15
- **Total: ~₹16.50/reel**

---

## 🎬 REEL SPECIFICATIONS (User Confirmed)

| Parameter | Value | Reason |
|---|---|---|
| **Duration** | 60-90 seconds | IG Reels max = 90s, YT Shorts max = 60s |
| **Story Length** | 150-180 words | Hindi TTS ~2 words/sec = 75-90s narration |
| **Scenes** | 6 scenes | Each ~10-12s screen time |
| **Format** | 1080×1920 (9:16) | Universal for IG Reel + YT Shorts + FB Reel |
| **FPS** | 30 | Standard, manageable file size |
| **Voice** | Google TTS Hindi Neural2 (Category-based) | Krishna/Ram=Male, Durga/Saraswati=Female |
| **Subtitles** | Word-by-word highlighted | Modern reel style, 2x retention |
| **Music** | Manual library (user provides) | Soft devotional BG, 10-15% volume |
| **Watermark** | On every scene image + final video | Anti-crop branding |
| **Quality** | Story FULL — no cutting | User priority: "cutna-pitna nahi, quality chahiye" |

---

## 🔧 EXISTING PROJECTS TO REUSE (User Has 2 Bonus Projects)

**Status:** User mentioned 2 existing working projects that can be reused:

### **Project 1: Auto YouTube Uploader**
- Topic auto-select
- Image generation
- Voice generation
- Video building (FFmpeg)
- YouTube upload
- GitHub Actions automation

### **Project 2: Long Video Generator**
- FFmpeg-based
- Can generate videos up to 25 minutes
- Scene concatenation
- (Full details TBD when user shares code)

**AWAITING:** User needs to share Project 1 & Project 2 code files for analysis. Main will identify reusable parts (TTS engine, FFmpeg wrapper, YouTube upload).

**Decision Pending:**
- Option A: Analyze existing projects → adapt reusable code (RECOMMENDED)
- Option B: Skip, write fresh (7 weeks)
- Option C: Hybrid — user selects specific files

---

## 📋 CONTINUATION POINT

**Where we stopped:** User answered Q1-Q6, and mentioned 2 existing projects that could be reused. AI recommended Option A (analyze existing projects first before coding).

**Next Steps (in order):**
1. User to share Project 1 and Project 2 code files
2. AI analyzes reusability
3. AI provides adaptation plan
4. Start Phase 1 (memory.py, database.py, recovery_manager.py, settings.py, requirements.txt)
5. Then Phase 2 (Story writer, scene splitter, prompt builder)
6. Continue phase by phase

**IF USER WANTS TO SKIP EXISTING PROJECTS:**
Just start with **Phase 1, Module 1: `core/memory.py` modifications** (add Reel fields).

---

## 🎯 USER'S FINAL CONFIRMED DECISIONS

| Question | Answer |
|---|---|
| **Q1: Schedule** | 8AM Image, 1PM Reel, 8PM Carousel (3 posts/day) |
| **Q2: YouTube** | Setup ready (env vars + GitHub secrets pattern) |
| **Q3: Music** | User will add tracks to `assets/music/` later |
| **Q4: Voice** | Category-based (Krishna/Ram=male, Durga/Saraswati=female) |
| **Q5: Dev Approach** | MVP first, polish later |
| **Q6: Font** | Download command provided (Noto Sans Devanagari) |
| **Branding** | On every carousel slide + reel scene + final video |
| **Story Length** | Full 150-180 words, NO cutting for quality |
| **Reel Length** | 60-90 seconds |

---

**[END OF PART 1 
 Continue reading PART 2 for modification plan, roadmap, and new files]**

 
---

## 📝 MODIFICATION PLAN (Existing Files)

> **RULE:** Ye files mein sirf NEW additions honge. Existing code TOUCH nahi hoga.

### 🟡 File 1: `core/memory.py` — Add Reel Fields

**Purpose:** AgentMemory dataclass mein Reel-specific fields add karna

**What to ADD (existing kuch nahi hatana):**
```python
# ═══════════════════════════════════════════
# 🆕 REEL FIELDS (new addition)
# ═══════════════════════════════════════════

# Reel story & structure
reel_story: str = ""                    # 150-180 word Hindi story
reel_scenes: list = field(default_factory=list)  # 6 scenes structure
reel_fact_checked: bool = False         # Fact checker passed?

# Reel voice (TTS output)
reel_voice_bytes: Optional[bytes] = None    # mp3 bytes
reel_voice_url: str = ""                    # GCS URL
reel_voice_duration: float = 0.0            # seconds
reel_voice_gender: str = ""                 # male/female
reel_voice_timestamps: list = field(default_factory=list)  # word-level times

# Reel subtitles
reel_subtitle_srt: str = ""             # SRT format
reel_subtitle_style: str = "word_highlight"  # style

# Reel video
reel_video_bytes: Optional[bytes] = None
reel_video_url: str = ""                # GCS URL after upload
reel_video_path: str = ""               # Local path during build
reel_video_size_mb: float = 0.0
reel_duration_seconds: float = 0.0

# Reel publishing (all 3 platforms)
reel_ig_post_id: str = ""
reel_fb_post_id: str = ""
reel_yt_video_id: str = ""              # YouTube video ID
reel_ig_success: bool = False
reel_fb_success: bool = False
reel_yt_success: bool = False

# Reel metadata
reel_music_file: str = ""               # Which BG music used
reel_thumbnail_url: str = ""            # Custom thumbnail
```

**Scene structure (inside reel_scenes list):**
```python
{
    "scene_number": 1,
    "scene_type": "hook",       # hook|context|climax|lesson|reflection|cta
    "narration": "Hindi text",  # What TTS will say
    "visual_description": "English visual",
    "image_prompt": "Full Imagen prompt",
    "duration_seconds": 12,
    "image_bytes": bytes,
    "image_url": "",
    "start_time": 0.0,          # Video timeline
    "end_time": 12.0,
    "effect": "zoom_in",        # ken_burns effect
}
```

**post_type support:** Currently `"image" | "carousel"`. Add `"reel"` as valid value.

**Update `to_recovery_dict()` and `restore_from_recovery()` methods** to include new fields.

---

### 🟡 File 2: `core/database.py` — Schema Migration

**Purpose:** Add columns for Reels + video

**What to ADD:**
```python
# In initialize_database(), add ALTER TABLE statements (backward compatible):

# Add to post_history table
ALTER TABLE post_history ADD COLUMN post_type TEXT DEFAULT 'image';
ALTER TABLE post_history ADD COLUMN video_url TEXT DEFAULT '';
ALTER TABLE post_history ADD COLUMN yt_post_id TEXT DEFAULT '';
ALTER TABLE post_history ADD COLUMN yt_success INTEGER DEFAULT 0;
ALTER TABLE post_history ADD COLUMN reel_duration_seconds REAL DEFAULT 0;

# New table for Reel-specific analytics
CREATE TABLE IF NOT EXISTS reel_analytics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    post_id INTEGER,
    platform TEXT,              -- instagram/facebook/youtube
    plays INTEGER DEFAULT 0,
    reach INTEGER DEFAULT 0,
    avg_watch_time REAL DEFAULT 0,
    total_interactions INTEGER DEFAULT 0,
    saves INTEGER DEFAULT 0,
    shares INTEGER DEFAULT 0,
    completion_rate REAL DEFAULT 0,
    fetched_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (post_id) REFERENCES post_history(id)
);
```

**Update `save_post()`** to accept new fields (with defaults).

**Add new function:** `save_reel_analytics(post_id, platform, data)`

**Migration Logic:** Use `try/except` for ALTER TABLE (SQLite doesn't have IF NOT EXISTS for columns). Wrap each ALTER in try/except so re-running doesn't error.

---

### 🟡 File 3: `core/recovery_manager.py` — Add Reel Stages

**Purpose:** Extend checkpoint stages for Reel pipeline

**What to ADD to `STAGES` dict:**
```python
STAGES = {
    # ... existing carousel stages ...
    
    # 🆕 REEL STAGES
    "REEL_STORY_WRITTEN": 10,
    "REEL_SCENES_SPLIT": 11,
    "REEL_IMAGES_GENERATED": 12,
    "REEL_VOICE_GENERATED": 13,
    "REEL_SUBTITLES_MADE": 14,
    "REEL_VIDEO_BUILT": 15,
    "REEL_VIDEO_UPLOADED": 16,
    "REEL_IG_PUBLISHED": 17,
    "REEL_FB_PUBLISHED": 18,
    "REEL_YT_PUBLISHED": 19,
}

STAGE_NAMES_HINDI = {
    # ... existing ...
    
    "REEL_STORY_WRITTEN": "रील की कहानी तैयार",
    "REEL_SCENES_SPLIT": "6 दृश्यों में बंटा",
    "REEL_IMAGES_GENERATED": "रील की तस्वीरें बनी",
    "REEL_VOICE_GENERATED": "आवाज़ तैयार",
    "REEL_SUBTITLES_MADE": "सबटाइटल बने",
    "REEL_VIDEO_BUILT": "वीडियो बना",
    "REEL_VIDEO_UPLOADED": "वीडियो अपलोड हुआ",
    "REEL_IG_PUBLISHED": "इंस्टाग्राम पर पब्लिश",
    "REEL_FB_PUBLISHED": "फेसबुक पर पब्लिश",
    "REEL_YT_PUBLISHED": "यूट्यूब पर पब्लिश",
}
```

**Extend `save_checkpoint()`** to also save:
- `voice_bytes` (as `voice.mp3` in session folder)
- `video_bytes` (as `video.mp4` in session folder)

**Update `find_pending_recovery()`** to handle `post_type="reel"` filter.

---

### 🟡 File 4: `config/settings.py` — Add Reel Config

**Purpose:** Add all new environment variables and constants

**What to ADD (new sections):**
```python
# ═══════════════════════════════════════════════════════════
# 🎤 GOOGLE CLOUD TEXT-TO-SPEECH
# ═══════════════════════════════════════════════════════════
TTS_ENABLED = os.getenv("TTS_ENABLED", "true").lower() == "true"
TTS_LANGUAGE = os.getenv("TTS_LANGUAGE", "hi-IN")

# Category-based voice mapping (User's choice: Q4)
TTS_VOICE_MALE = os.getenv("TTS_VOICE_MALE", "hi-IN-Neural2-B")
TTS_VOICE_FEMALE = os.getenv("TTS_VOICE_FEMALE", "hi-IN-Neural2-A")

# Category → Gender mapping
TTS_CATEGORY_VOICE = {
    "krishna": "male",
    "shiva": "male",
    "ram": "male",
    "hanuman": "male",
    "ganesha": "male",
    "durga": "female",
    "spiritual_nature": "female",
    "motivational": "male",
    "temple": "male",
    "daily_wisdom": "female",
    "festival": "female",
    "festival_moments": "female",
}

TTS_SPEAKING_RATE = float(os.getenv("TTS_SPEAKING_RATE", "0.95"))
TTS_PITCH = float(os.getenv("TTS_PITCH", "0.0"))
TTS_AUDIO_ENCODING = "MP3"

# ═══════════════════════════════════════════════════════════
# 🎬 REEL VIDEO CONFIG
# ═══════════════════════════════════════════════════════════
REEL_DURATION_MIN = int(os.getenv("REEL_DURATION_MIN", "60"))
REEL_DURATION_MAX = int(os.getenv("REEL_DURATION_MAX", "90"))
REEL_FPS = int(os.getenv("REEL_FPS", "30"))
REEL_WIDTH = 1080
REEL_HEIGHT = 1920
REEL_ASPECT_RATIO = "9:16"

# Story parameters
REEL_STORY_MIN_WORDS = int(os.getenv("REEL_STORY_MIN_WORDS", "150"))
REEL_STORY_MAX_WORDS = int(os.getenv("REEL_STORY_MAX_WORDS", "180"))
REEL_NUM_SCENES = int(os.getenv("REEL_NUM_SCENES", "6"))

# Video quality
REEL_VIDEO_CODEC = "libx264"
REEL_VIDEO_CRF = 23  # Quality (18-28, lower=better)
REEL_VIDEO_PRESET = "medium"
REEL_AUDIO_CODEC = "aac"
REEL_AUDIO_BITRATE = "128k"

# Effects
REEL_KEN_BURNS_ENABLED = True
REEL_KEN_BURNS_ZOOM = 1.15  # 15% zoom over scene duration
REEL_TRANSITION_TYPE = "crossfade"
REEL_TRANSITION_DURATION = 0.5  # seconds

# Music
REEL_MUSIC_ENABLED = True
REEL_MUSIC_VOLUME = 0.15  # 15% (voice dominant)
REEL_MUSIC_FOLDER = "assets/music"

# Subtitles
REEL_SUBTITLE_ENABLED = True
REEL_SUBTITLE_FONT_SIZE = 60
REEL_SUBTITLE_HIGHLIGHT_COLOR = "#FFD700"  # Gold
REEL_SUBTITLE_BASE_COLOR = "#FFFFFF"  # White
REEL_SUBTITLE_STROKE_COLOR = "#000000"  # Black outline

# ═══════════════════════════════════════════════════════════
# 📺 YOUTUBE SHORTS CONFIG
# ═══════════════════════════════════════════════════════════
YOUTUBE_ENABLED = os.getenv("YOUTUBE_ENABLED", "true").lower() == "true"
YOUTUBE_CHANNEL_ID = os.getenv("YOUTUBE_CHANNEL_ID", "")
YOUTUBE_CLIENT_SECRETS_FILE = os.getenv(
    "YOUTUBE_CLIENT_SECRETS_FILE", 
    "youtube_client_secrets.json"
)
YOUTUBE_TOKEN_FILE = os.getenv("YOUTUBE_TOKEN_FILE", "youtube_token.json")
YOUTUBE_CATEGORY_ID = "22"  # People & Blogs
YOUTUBE_PRIVACY_STATUS = "public"
YOUTUBE_MADE_FOR_KIDS = False
YOUTUBE_UPLOAD_MAX_RETRIES = 3

# ═══════════════════════════════════════════════════════════
# 🎬 REEL POSTING SCHEDULE
# ═══════════════════════════════════════════════════════════
REEL_POSTING_HOUR = int(os.getenv("REEL_POSTING_HOUR", "13"))  # 1 PM IST
```

---

### 🟡 File 5: `agents/publisher_agent.py` — Add Reel Publishing

**Purpose:** Add functions to post Reels on IG, FB, YouTube

**What to ADD (new functions, keep existing untouched):**
```python
def post_reel_to_instagram(video_url: str, caption: str, memory) -> dict:
    """
    Instagram Reels API:
    1. Create media container with media_type=REELS
    2. Wait for container ready (video takes longer)
    3. Publish container
    """
    # Uses same pattern as _post_instagram_container but with:
    # - media_type='REELS'
    # - video_url instead of image_url
    # - Longer wait (video processing = 30-90s)
    pass

def post_reel_to_facebook(video_url: str, caption: str, memory) -> dict:
    """
    Facebook Reels/Video posting:
    - POST to /{page_id}/video_reels endpoint
    - Or POST to /{page_id}/videos with source URL
    """
    pass

def post_reel_to_youtube(video_bytes: bytes, title: str, description: str, memory) -> dict:
    """
    YouTube Shorts upload:
    - Uses posting/youtube.py module
    - Requires OAuth token
    - Upload with chunked resumable upload
    """
    # Delegates to posting/youtube.py
    from posting.youtube import upload_short
    return upload_short(video_bytes, title, description)
```

**In `run()` function, add:**
```python
elif memory.post_type == "reel":
    logger.info("🎬 REEL PUBLISH MODE")
    
    if not memory.reel_video_url:
        memory.add_error("publisher", "Reel video URL missing")
        return memory
    
    full_caption = _prepare_caption(memory.caption, memory.hashtags)
    
    # Instagram Reel
    if not (memory.is_recovery and memory.reel_ig_success):
        ig_result = post_reel_to_instagram(memory.reel_video_url, full_caption, memory)
        memory.reel_ig_success = ig_result["success"]
        memory.reel_ig_post_id = ig_result.get("post_id", "")
        memory.ig_success = ig_result["success"]  # For backward compat
        memory.ig_post_id = ig_result.get("post_id", "")
    
    # Delay between platforms
    _human_like_delay(...)
    
    # Facebook Reel
    if not (memory.is_recovery and memory.reel_fb_success):
        fb_result = post_reel_to_facebook(memory.reel_video_url, full_caption, memory)
        memory.reel_fb_success = fb_result["success"]
        memory.reel_fb_post_id = fb_result.get("post_id", "")
    
    # YouTube Shorts
    if YOUTUBE_ENABLED and not (memory.is_recovery and memory.reel_yt_success):
        yt_result = post_reel_to_youtube(
            memory.reel_video_bytes,
            title=memory.topic[:100],
            description=full_caption,
            memory=memory
        )
        memory.reel_yt_success = yt_result["success"]
        memory.reel_yt_video_id = yt_result.get("video_id", "")
```

---

### 🟡 File 6: `agents/caption_agent.py` — Add Reel Style

**Purpose:** Add Reel-optimized caption style

**What to ADD to `CAPTION_STYLES` dict:**
```python
"reel_hook": {
    "description": "Reel के लिए hook + engaging body + CTA",
    "length": "80-120 words",
    "structure": "Hook question → Story teaser → Save/Share CTA",
    "example": "क्या आप जानते हैं...\n\nजब भगवान श्री कृष्ण ने अर्जुन से कहा था 'कर्म कर, फल की चिंता मत कर'... इस एक वाक्य में पूरा जीवन का सत्य छुपा है।\n\nपूरी कहानी video में देखिए 🎬\n\n💾 Save करें | 🔄 Share करें\n🙏 Follow @sanatanii_soch",
    "best_for": ["reel"],
    "engagement_type": "video_hook"
}
```

**In `_select_style_for_category()`:**
```python
# Check post_type FIRST (before category matching)
if hasattr(memory, 'post_type') and memory.post_type == "reel":
    return "reel_hook"
```

---

### 🟡 File 7: `agents/hashtag_agent.py` — Add Reel Hashtags

**Purpose:** Add Reels-specific hashtag tier

**What to ADD:**
```python
# New dict at top
REEL_SPECIFIC_HASHTAGS = [
    # Reel platform tags
    "#reels", "#reelsinstagram", "#reelitfeelit", "#reelkarofeelkaro",
    "#trendingreels", "#viralreels", "#instareels", "#reelsindia",
    
    # Short video tags
    "#shorts", "#youtubeshorts", "#shortsvideo", "#shortsindia",
    "#shortsfeed", "#shortvideo",
    
    # Content type
    "#spiritualreels", "#devotionalreels", "#storyreels",
    "#educationalreels", "#mythologyreels"
]
```

**In `run()` function, add BEFORE cleanup:**
```python
# ═══════════════════════════════════════════════
# REEL-SPECIFIC HASHTAGS (if applicable)
# ═══════════════════════════════════════════════
if hasattr(memory, 'post_type') and memory.post_type == "reel":
    reel_tags = random.sample(REEL_SPECIFIC_HASHTAGS, 5)
    all_hashtags.extend(reel_tags)
    breakdown["Reel-Specific"] = 5
    logger.info(f"🎬 Reel hashtags added: {len(reel_tags)}")
```

---

### 🟡 File 8: `agents/analytics_agent.py` — Add Reel Metrics

**Purpose:** Fetch Instagram Reel-specific metrics

**What to ADD in `_fetch_ig_analytics()`:**
```python
# After basic metrics fetch, check if it's a Reel
try:
    # Check media type
    if data.get("media_type") in ["VIDEO", "REELS"]:
        # Fetch reel-specific insights
        reel_metrics_url = f"https://graph.facebook.com/{META_VERSION}/{post_id}/insights"
        reel_response = requests.get(
            reel_metrics_url,
            params={
                'metric': 'plays,total_interactions,ig_reels_video_view_total_time,ig_reels_avg_watch_time',
                'access_token': ACCESS_TOKEN
            },
            timeout=10
        )
        if reel_response.status_code == 200:
            reel_data = reel_response.json().get('data', [])
            for item in reel_data:
                metric_name = item['name']
                value = item.get('values', [{}])[0].get('value', 0)
                result[metric_name] = value
except Exception as e:
    logger.info(f"ℹ️ Reel metrics fetch skipped: {e}")
```

---

### 🟡 File 9: `utils/watermark.py` — Add Video Watermark

**Purpose:** Add watermark to video (not just images)

**What to ADD (new function):**
```python
def apply_video_branding(
    video_path: str,
    output_path: str,
    strategy: str = "balanced"
) -> str:
    """
    Apply watermark to video using FFmpeg overlay
    
    Args:
        video_path: Input video file path
        output_path: Output video with watermark
        strategy: "maximum" | "balanced" | "minimal"
    
    Returns:
        Path to watermarked video
    """
    import subprocess
    
    # Create watermark image (transparent PNG with brand)
    watermark_img = _create_video_watermark_png(strategy)
    watermark_path = "temp_watermark.png"
    with open(watermark_path, "wb") as f:
        f.write(watermark_img)
    
    # FFmpeg command with:
    # - Diagonal repeating pattern (via overlay filter)
    # - Bottom-right handle
    # - Fade in/out
    
    cmd = [
        "ffmpeg", "-y",
        "-i", video_path,
        "-i", watermark_path,
        "-filter_complex",
        "[1:v]scale=200:-1[wm];[0:v][wm]overlay=W-w-20:H-h-20:enable='between(t,0,999)'",
        "-codec:a", "copy",
        output_path
    ]
    
    subprocess.run(cmd, check=True)
    
    # Cleanup
    os.remove(watermark_path)
    
    return output_path

def _create_video_watermark_png(strategy: str) -> bytes:
    """Create transparent PNG watermark for video overlay"""
    # Use existing PIL logic to create transparent watermark
    # Return PNG bytes
    pass
```

---

### 🟡 File 10: `utils/gcs_helper.py` — Add Video Upload

**Purpose:** Upload MP4 video files to GCS

**What to ADD (new function):**
```python
def upload_video(
    video_bytes: bytes,
    folder: str = "reels",
    use_date_folder: bool = True,
    metadata: Optional[dict] = None,
    make_public: bool = True
) -> str:
    """
    Upload video to GCS
    
    Args:
        video_bytes: Video data (MP4)
        folder: Base folder (default: reels)
        use_date_folder: Add YYYY-MM-DD subfolder
        metadata: Custom metadata
        make_public: Make publicly accessible
    
    Returns:
        Public URL of uploaded video
    """
    if not video_bytes:
        raise ValueError("No video bytes provided")
    
    if len(video_bytes) < 100_000:  # Min 100KB
        raise ValueError(f"Video too small: {len(video_bytes)} bytes")
    
    # Generate filename
    filename = _generate_filename(folder, "mp4", use_date_folder)
    
    size_mb = len(video_bytes) / (1024 * 1024)
    logger.info(f"☁️  Uploading video to GCS: {filename} ({size_mb:.1f} MB)")
    
    # Same retry logic as upload_image but with:
    # - content_type="video/mp4"
    # - Longer timeout (video files bigger)
    # - Progress tracking (optional)
    
    for attempt in range(1, MAX_UPLOAD_RETRIES + 1):
        try:
            bucket = _get_bucket()
            blob = bucket.blob(filename)
            blob.cache_control = DEFAULT_CACHE_CONTROL
            
            metadata = metadata or {}
            metadata.update({
                "uploaded_at": datetime.now().isoformat(),
                "size_bytes": str(len(video_bytes)),
                "md5_hash": _get_content_hash(video_bytes),
                "content_type": "video/mp4"
            })
            blob.metadata = metadata
            
            blob.upload_from_string(
                video_bytes,
                content_type="video/mp4",
                timeout=300  # 5 min timeout for videos
            )
            
            if make_public:
                blob.make_public()
                url = blob.public_url
            else:
                url = blob.generate_signed_url(
                    expiration=timedelta(days=7),
                    method='GET'
                )
            
            logger.info(f"✅ Video uploaded: {url}")
            return url
        
        except Exception as e:
            logger.warning(f"Video upload attempt {attempt} failed: {e}")
            if attempt < MAX_UPLOAD_RETRIES:
                time.sleep(RETRY_BASE_DELAY * (2 ** (attempt - 1)))
    
    raise Exception(f"Video upload failed after {MAX_UPLOAD_RETRIES} attempts")
```

---

### 🟡 File 11: `main.py` — Add Reel Pipeline

**Purpose:** Add `run_reel_pipeline()` function following carousel pattern

**What to ADD (new function + CLI):**
```python
def run_reel_pipeline(force_new: bool = False) -> dict:
    """
    Reel Pipeline (1 PM IST)
    
    Flow:
    1. Health check
    2. Recovery check (post_type="reel")
    3. Planner → Research → Story Writer → Fact Checker
    4. Scene Splitter → Prompt Builder
    5. Image Generation (6 scenes) with quality check
    6. TTS Voice Generation
    7. Subtitle Generation
    8. Video Building (FFmpeg)
    9. Upload to GCS
    10. Caption + Hashtag
    11. Publish (IG + FB + YT)
    12. Analytics + Cleanup
    """
    start_time = datetime.now()
    
    logger.info("")
    log_header(logger, "🎬 DIVINE AUTO POSTER — REEL", char="═")
    logger.info(f"📅 समय: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    log_header(logger, "", char="═")
    
    # Recovery check
    memory = None
    if not force_new:
        memory = _check_and_load_recovery(post_type="reel")
    
    if memory is None:
        memory = AgentMemory()
        memory.post_type = "reel"
    
    session_id = memory.session_id
    agent_results = {}
    
    try:
        # Health check
        is_healthy, issues = _health_check()
        if not is_healthy and len(issues) > 3:
            raise Exception(f"System health issues: {len(issues)}")
        
        # ═══ PLANNER (skip if recovery) ═══
        if memory.is_recovery and memory.topic:
            logger.info("⏭️  Planner skip (recovery)")
        else:
            memory, result = _execute_agent("planner", planner_agent.run, memory, critical=True, max_retries=2)
            agent_results["planner"] = result
            save_checkpoint(session_id, "TOPIC_SELECTED", {
                "topic": memory.topic, "category": memory.category,
                "post_type": "reel"
            })
        
        # ═══ RESEARCH ═══
        memory, result = _execute_agent("research", research_agent.run, memory, critical=False, max_retries=2)
        agent_results["research"] = result
        
        # ═══ REEL AGENT (main orchestrator) ═══
        from reels import reel_agent
        memory, result = _execute_agent("reel", reel_agent.run, memory, critical=True, max_retries=1)
        agent_results["reel"] = result
        
        # ═══ CAPTION ═══
        memory, result = _execute_agent("caption", caption_agent.run, memory, critical=False, max_retries=2)
        agent_results["caption"] = result
        
        # ═══ HASHTAG ═══
        memory, result = _execute_agent("hashtag", hashtag_agent.run, memory, critical=False, max_retries=1)
        agent_results["hashtag"] = result
        
        _human_like_delay()
        
        # ═══ PUBLISHER (IG + FB + YT) ═══
        memory, result = _execute_agent("publisher", publisher_agent.run, memory, critical=False, max_retries=1)
        agent_results["publisher"] = result
        
        # ═══ SAVE TO DB ═══
        # ... save to database ...
        
        # ═══ ANALYTICS ═══
        # ... analytics ...
        
        # ═══ REPORT ═══
        return {...}
    
    except Exception as e:
        # ... error handling ...
        return {...}


# Add CLI commands
elif command == "reel":
    logger.info("🎬 MANUAL REEL MODE")
    result = run_reel_pipeline()
    sys.exit(0 if result.get("status") in ["success", "partial"] else 2)

elif command == "reel-new":
    logger.info("🎬 FORCE NEW REEL (skip recovery)")
    result = run_reel_pipeline(force_new=True)
    sys.exit(0 if result.get("status") in ["success", "partial"] else 2)


# Update auto_post cloud function:
elif post_type == "reel":
    result = run_reel_pipeline()
```

---

### 🟡 File 12: `requirements.txt` — Add Dependencies

**What to ADD:**
```
# Existing dependencies (keep all)
google-generativeai==0.3.2
google-cloud-storage==2.13.0
Pillow==10.1.0
requests==2.31.0
python-dotenv==1.0.0
functions-framework==3.5.0
numpy==1.26.2
google-cloud-aiplatform==1.71.1
colorama==0.4.6

# 🆕 NEW DEPENDENCIES FOR REELS
google-cloud-texttospeech==2.16.3   # Hindi TTS Neural2
moviepy==1.0.3                       # Video building (Python wrapper for FFmpeg)
pysrt==1.1.2                         # Subtitle SRT handling
google-auth-oauthlib==1.2.0          # YouTube OAuth
google-api-python-client==2.108.0    # YouTube Data API v3
pydub==0.25.1                        # Audio processing (music mixing)
```

**FFmpeg system requirement:**
- Local (Windows): Install via `winget install ffmpeg` or download from ffmpeg.org
- GitHub Actions: Pre-installed on `ubuntu-latest` ✅
- Cloud Run: Need Docker image with FFmpeg

---

## 🆕 NEW FILES TO CREATE (Complete List)

### **📁 `reels/` folder (5 files)**

#### 1. `reels/__init__.py`
- Empty file (like agents/__init__.py)

#### 2. `reels/story_writer.py`
**Purpose:** Generate 150-180 word Hindi story with hook + emotion + CTA  
**Inputs:** `memory.topic`, `memory.category`, `memory.mood`, `memory.is_festival`  
**Outputs:** `memory.reel_story` (str)  
**Dependencies:** Gemini API (google.generativeai), config.settings  
**Pattern:** Same as research_agent.py — Gemini call with retries + fallback

#### 3. `reels/fact_checker.py`
**Purpose:** Verify mythological accuracy, remove false info  
**Inputs:** `memory.reel_story`  
**Outputs:** `memory.reel_story` (corrected), `memory.reel_fact_checked = True`  
**Dependencies:** Gemini API  
**Pattern:** Second Gemini call with fact-checking prompt

#### 4. `reels/scene_splitter.py`
**Purpose:** Split story into 6 scenes with narration + visual description + duration  
**Inputs:** `memory.reel_story`, `memory.category`  
**Outputs:** `memory.reel_scenes` (list of 6 dicts)  
**Dependencies:** Gemini API  
**Scene types:** hook, context, climax, lesson, reflection, cta

#### 5. `reels/prompt_builder.py`
**Purpose:** Build 6 cinematic Imagen prompts for each scene  
**Inputs:** `memory.reel_scenes`, `memory.category`, `memory.image_style`  
**Outputs:** Each scene gets `image_prompt` added  
**Dependencies:** Reuses logic from `agents/prompt_agent.py` (ART_STYLES, CATEGORY_ART_REFERENCES)  
**Pattern:** Loop 6 times, generate prompt per scene

#### 6. `reels/reel_agent.py`
**Purpose:** Thin wrapper (like `carousel_agent.py`)  
**Inputs:** memory  
**Outputs:** Delegates to `core/reel_engine.py`  
**Pattern:** Copy of `carousel_agent.py` structure

---

### **📁 `video_engine/` folder (8 files)**

#### 1. `video_engine/__init__.py`
- Empty file

#### 2. `video_engine/tts_engine.py`
**Purpose:** Convert story text → Hindi voice MP3 with word-level timestamps  
**Inputs:** `memory.reel_story`, `memory.category` (for voice selection)  
**Outputs:** `memory.reel_voice_bytes`, `memory.reel_voice_duration`, `memory.reel_voice_timestamps`  
**Dependencies:** `google-cloud-texttospeech`  
**Voice selection:** Uses `TTS_CATEGORY_VOICE` from settings  
**Key feature:** Word-level timestamps for subtitle sync  
**Pattern:**
```python
from google.cloud import texttospeech
client = texttospeech.TextToSpeechClient()
# Use SSML for better control
# Request word-level timestamps
```

#### 3. `video_engine/subtitle_generator.py`
**Purpose:** Generate SRT subtitles from TTS timestamps  
**Inputs:** `memory.reel_voice_timestamps`, `memory.reel_story`  
**Outputs:** `memory.reel_subtitle_srt` (SRT format string)  
**Dependencies:** `pysrt`  
**Style:** Word-by-word highlighted (like modern reels)  
**Pattern:**
```python
# Convert word timestamps to SRT
# Each subtitle = 2-4 words for readability
# Highlight current word being spoken
```

#### 4. `video_engine/clip_renderer.py`
**Purpose:** Convert one image → video clip with Ken Burns effect  
**Inputs:** `image_bytes`, `duration_seconds`, `effect` (zoom_in/zoom_out/pan_left/pan_right)  
**Outputs:** Video clip file (mp4)  
**Dependencies:** `moviepy` (FFmpeg wrapper)  
**Pattern:**
```python
from moviepy.editor import ImageClip
clip = ImageClip(image_path, duration=duration)
# Apply zoom animation
clip = clip.resize(lambda t: 1 + (0.15 * t / duration))
# Or Ken Burns pan
clip = clip.set_position(lambda t: ('center', 100 - t * 5))
```

#### 5. `video_engine/effects.py`
**Purpose:** Video effects — transitions, intro/outro  
**Functions:**
- `apply_crossfade(clip1, clip2, duration)` — Smooth transition
- `apply_fade_in(clip, duration)`
- `apply_fade_out(clip, duration)`
- `add_intro(main_clip)` — Optional 1s brand intro
- `add_outro(main_clip)` — Optional 2s CTA outro

#### 6. `video_engine/music_manager.py`
**Purpose:** Select + mix BG music with voice narration  
**Inputs:** `memory.category`, `voice_duration`  
**Outputs:** Mixed audio track (voice + music at 15%)  
**Dependencies:** `pydub`  
**Logic:**
- Select music from `assets/music/` folder based on category/mood
- Loop if music shorter than video
- Fade in/out
- Duck music to 15% when voice speaks
**Pattern:**
```python
from pydub import AudioSegment
voice = AudioSegment.from_mp3(voice_path)
music = AudioSegment.from_mp3(music_path)
music = music - 20  # Reduce by 20dB (~10% volume)
mixed = voice.overlay(music)
```

#### 7. `video_engine/concat_engine.py`
**Purpose:** Merge multiple video clips into one  
**Inputs:** List of clip file paths, transition type  
**Outputs:** Single merged video  
**Dependencies:** `moviepy`  
**Pattern:**
```python
from moviepy.editor import concatenate_videoclips
final = concatenate_videoclips(clips, method="compose", transition=crossfade)
```

#### 8. `video_engine/video_builder.py` — 🏆 MAIN ORCHESTRATOR
**Purpose:** Master function that combines everything  
**Inputs:** `memory` (with images, voice, subtitles)  
**Outputs:** `memory.reel_video_bytes`, `memory.reel_video_path`, `memory.reel_duration_seconds`  
**Flow:**
```python
def build_video(memory):
    # 1. Load all scene images
    # 2. For each scene:
    #    - Create video clip from image
    #    - Apply Ken Burns effect
    #    - Set duration matching narration
    # 3. Concatenate clips with transitions
    # 4. Add voice audio track
    # 5. Add BG music (mixed at 15%)
    # 6. Burn subtitles into video
    # 7. Apply watermark (utils/watermark.py)
    # 8. Export as MP4 (1080x1920, H.264, 30fps)
    # 9. Save to memory
    return memory
```

---

### **📁 `core/` folder (1 new file)**

#### `core/reel_engine.py` — 🏆 REEL MASTER ORCHESTRATOR
**Purpose:** Main reel building engine (like `carousel_engine.py` for carousels)  
**Inputs:** `topic`, `category`, `session_id`, `resume_state`  
**Outputs:** dict with `success`, `slides`, `caption`, `voice`, `video_path`, etc.  
**Dependencies:** ALL new modules + existing (vertex_ai, quality_agent, watermark, humanizer)  
**Pattern:** Follow `core/carousel_engine.py` structure exactly

**Flow:**
```python
def build_reel(topic, category, session_id, resume_state=None):
    # RECOVERY CHECK (like carousel_engine)
    
    # STEP 1: Story Writer
    if not memory.reel_story:
        run_story_writer()
        save_checkpoint("REEL_STORY_WRITTEN")
    
    # STEP 2: Fact Checker
    if not memory.reel_fact_checked:
        run_fact_checker()
    
    # STEP 3: Scene Splitter
    if not memory.reel_scenes:
        run_scene_splitter()
        save_checkpoint("REEL_SCENES_SPLIT")
    
    # STEP 4: Prompt Builder
    run_prompt_builder()
    
    # STEP 5: Generate 6 images (loop with recovery)
    for scene in memory.reel_scenes:
        if not scene.get("image_bytes"):
            image = generate_scene_image(scene)
            image = quality_check(image)  # Reuse quality_agent
            image = apply_branding(image)  # Reuse watermark
            image = humanize_image(image)  # Reuse humanizer
            scene["image_bytes"] = image
    save_checkpoint("REEL_IMAGES_GENERATED", voice_bytes=None, video_bytes=None)
    
    # STEP 6: TTS Voice
    if not memory.reel_voice_bytes:
        run_tts_engine()
        save_checkpoint("REEL_VOICE_GENERATED")
    
    # STEP 7: Subtitles
    if not memory.reel_subtitle_srt:
        run_subtitle_generator()
        save_checkpoint("REEL_SUBTITLES_MADE")
    
    # STEP 8: Build video
    if not memory.reel_video_bytes:
        run_video_builder()
        save_checkpoint("REEL_VIDEO_BUILT")
    
    # STEP 9: Upload to GCS
    if not memory.reel_video_url:
        memory.reel_video_url = upload_video(memory.reel_video_bytes)
        save_checkpoint("REEL_VIDEO_UPLOADED")
    
    return {...}
```

---

### **📁 `posting/` folder (2 files)**

#### 1. `posting/__init__.py`
- Empty file

#### 2. `posting/youtube.py`
**Purpose:** YouTube Shorts upload  
**Inputs:** `video_bytes`, `title`, `description`, `tags`  
**Outputs:** `{"success": bool, "video_id": str, "url": str}`  
**Dependencies:** `google-api-python-client`, `google-auth-oauthlib`  
**Pattern:**
```python
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2.credentials import Credentials

def upload_short(video_bytes, title, description, tags=None):
    # 1. Load OAuth credentials
    creds = _load_youtube_credentials()
    youtube = build('youtube', 'v3', credentials=creds)
    
    # 2. Save video to temp file
    temp_path = "temp_yt_upload.mp4"
    with open(temp_path, "wb") as f:
        f.write(video_bytes)
    
    # 3. Upload with #Shorts tag
    body = {
        'snippet': {
            'title': f"{title} #Shorts",  # #Shorts tag required
            'description': description,
            'tags': tags or [],
            'categoryId': YOUTUBE_CATEGORY_ID
        },
        'status': {
            'privacyStatus': YOUTUBE_PRIVACY_STATUS,
            'madeForKids': YOUTUBE_MADE_FOR_KIDS
        }
    }
    
    media = MediaFileUpload(temp_path, chunksize=-1, resumable=True)
    
    request = youtube.videos().insert(
        part='snippet,status',
        body=body,
        media_body=media
    )
    
    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            logger.info(f"Upload progress: {int(status.progress() * 100)}%")
    
    video_id = response['id']
    return {
        "success": True,
        "video_id": video_id,
        "url": f"https://youtube.com/shorts/{video_id}"
    }

def _load_youtube_credentials():
    """Load or refresh YouTube OAuth credentials"""
    # Uses YOUTUBE_TOKEN_FILE
    # Auto-refresh if expired
    pass

def _initial_oauth_setup():
    """One-time OAuth setup (run manually first time)"""
    # Uses YOUTUBE_CLIENT_SECRETS_FILE
    # Opens browser for user auth
    # Saves token to YOUTUBE_TOKEN_FILE
    pass
```

---

### **📁 `ai/` folder (2 files, OPTIONAL for MVP)**

#### 1. `ai/__init__.py`
- Empty

#### 2. `ai/content_orchestrator.py`
**Purpose:** Master decision maker — today image? carousel? reel?  
**Note:** MVP mein skip kar sakte hain, GitHub Actions already schedule handle karta hai.

---

### **📁 `assets/` folder (User adds content)**

```
assets/
├── music/                  # User adds 3-5 MP3 files
│   ├── peaceful_1.mp3
│   ├── powerful_1.mp3
│   └── devotional_1.mp3
├── intro/                  # Optional 1s brand intro
│   └── logo_intro.mp4
└── outro/                  # Optional 2s CTA outro
    └── subscribe.mp4
```

---

### **📁 `fonts/` folder (Download command)**

```
fonts/
├── NotoSansDevanagari-Bold.ttf      # Hindi bold
└── NotoSansDevanagari-Regular.ttf   # Hindi regular
```

**Download Command (PowerShell):**
```powershell
mkdir fonts -Force
curl -o fonts/NotoSansDevanagari-Bold.ttf https://github.com/googlefonts/noto-fonts/raw/main/hinted/ttf/NotoSansDevanagari/NotoSansDevanagari-Bold.ttf
curl -o fonts/NotoSansDevanagari-Regular.ttf https://github.com/googlefonts/noto-fonts/raw/main/hinted/ttf/NotoSansDevanagari/NotoSansDevanagari-Regular.ttf
```

---

### **📁 `.github/workflows/` (1 new file)**

#### `auto_reel.yml`
**Schedule:** 1 PM IST daily (7:30 AM UTC)  
**Timeout:** 60 minutes (video processing takes longer)  
**Pattern:** Copy `auto_carousel.yml` and modify:
```yaml
name: 🎬 Auto Reel Post

on:
  schedule:
    - cron: '30 7 * * *'  # 1 PM IST
  workflow_dispatch:

jobs:
  post-reel:
    runs-on: ubuntu-latest
    timeout-minutes: 60  # Videos take longer
    
    steps:
      - name: 📥 Checkout code
        uses: actions/checkout@v4
      
      - name: 🐍 Setup Python 3.11
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
          cache: 'pip'
      
      - name: 📦 Install FFmpeg
        run: sudo apt-get update && sudo apt-get install -y ffmpeg
      
      - name: 📦 Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
      
      - name: 🔐 Setup Google Cloud credentials
        run: |
          echo '${{ secrets.GCP_SERVICE_ACCOUNT_JSON }}' > spiritual-service-account.json
      
      - name: 🔐 Setup YouTube credentials
        run: |
          echo '${{ secrets.YOUTUBE_CLIENT_SECRETS_JSON }}' > youtube_client_secrets.json
          echo '${{ secrets.YOUTUBE_TOKEN_JSON }}' > youtube_token.json
      
      - name: 🎬 Run Reel Pipeline
        env:
          GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}
          ACCESS_TOKEN: ${{ secrets.ACCESS_TOKEN }}
          INSTAGRAM_ACCOUNT_ID: ${{ secrets.INSTAGRAM_ACCOUNT_ID }}
          FACEBOOK_PAGE_ID: ${{ secrets.FACEBOOK_PAGE_ID }}
          PROJECT_ID: ${{ secrets.PROJECT_ID }}
          LOCATION: ${{ secrets.LOCATION }}
          BUCKET_NAME: ${{ secrets.BUCKET_NAME }}
          YOUTUBE_CHANNEL_ID: ${{ secrets.YOUTUBE_CHANNEL_ID }}
          GOOGLE_APPLICATION_CREDENTIALS: spiritual-service-account.json
        run: |
          python main.py reel-new
      
      - name: 🗑️ Cleanup credentials
        if: always()
        run: |
          rm -f spiritual-service-account.json youtube_client_secrets.json youtube_token.json
```

---

## 🗺️ DEVELOPMENT ROADMAP (MVP-First)

### **Phase 1: Foundation (Day 1-2)** — Infrastructure
- [ ] Modify `core/memory.py` — Add Reel fields
- [ ] Modify `core/database.py` — Schema migration
- [ ] Modify `core/recovery_manager.py` — Add Reel stages
- [ ] Modify `config/settings.py` — Add TTS/YT/Reel config
- [ ] Update `requirements.txt` — Add dependencies
- [ ] Download Hindi fonts
- [ ] Install FFmpeg locally

**Deliverable:** System ready for Reel code (no reel functionality yet)

---

### **Phase 2: Story Layer (Day 3-4)** — Text Content
- [ ] Create `reels/__init__.py`
- [ ] Create `reels/story_writer.py`
- [ ] Create `reels/fact_checker.py`
- [ ] Create `reels/scene_splitter.py`
- [ ] Create `reels/prompt_builder.py`

**Deliverable:** Story + 6 scenes + prompts generate ho rahe (text only)

---

### **Phase 3: Visual Layer (Day 5)** — Images
- [ ] Test existing `vertex_ai.py` with 9:16 aspect ratio
- [ ] Verify quality_agent.py handles portrait images
- [ ] Test watermark.py on 9:16 images

**Deliverable:** 6 scene images ready with branding

---

### **Phase 4: Audio Layer (Day 6-7)** — Voice
- [ ] Setup Google Cloud TTS API
- [ ] Create `video_engine/__init__.py`
- [ ] Create `video_engine/tts_engine.py`
- [ ] Create `video_engine/subtitle_generator.py`

**Deliverable:** Voice + subtitles working

---

### **Phase 5: Video Layer (Day 8-11)** — 🔥 CORE
- [ ] Create `video_engine/clip_renderer.py`
- [ ] Create `video_engine/effects.py`
- [ ] Create `video_engine/music_manager.py`
- [ ] Create `video_engine/concat_engine.py`
- [ ] Create `video_engine/video_builder.py` (MAIN)
- [ ] Extend `utils/watermark.py` — Add `apply_video_branding()`

**Deliverable:** Full video MP4 ready locally

---

### **Phase 6: Storage & Orchestration (Day 12)**
- [ ] Extend `utils/gcs_helper.py` — Add `upload_video()`
- [ ] Create `core/reel_engine.py` (MAIN orchestrator)
- [ ] Create `reels/reel_agent.py` (thin wrapper)

**Deliverable:** End-to-end reel building + uploading

---

### **Phase 7: Publishing (Day 13-15)**
- [ ] Extend `agents/publisher_agent.py` — Add `post_reel_to_instagram()`
- [ ] Extend `agents/publisher_agent.py` — Add `post_reel_to_facebook()`
- [ ] Setup YouTube OAuth (one-time manual)
- [ ] Create `posting/__init__.py`
- [ ] Create `posting/youtube.py`
- [ ] Integrate YT into publisher_agent

**Deliverable:** Reel auto-posts to IG + FB + YT

---

### **Phase 8: Integration & Testing (Day 16-17)**
- [ ] Extend `agents/caption_agent.py` — Add reel_hook style
- [ ] Extend `agents/hashtag_agent.py` — Add reel hashtags
- [ ] Extend `agents/analytics_agent.py` — Add reel metrics
- [ ] Modify `main.py` — Add `run_reel_pipeline()`
- [ ] Create `.github/workflows/auto_reel.yml`
- [ ] End-to-end testing

**Deliverable:** 🎉 COMPLETE V2 running daily!

---

## 📊 CODE REUSE STATISTICS

| Layer | Reuse % | New Code % |
|---|---|---|
| Config | 87% | 13% |
| Agents | 93% | 7% |
| Core | 74% | 26% |
| Utils | 90% | 10% |
| main.py | 83% | 17% |
| Workflows | 67% | 33% |
| **Overall Existing System** | **72%** | **28%** |

**Reels/Video/Posting = 100% new (as expected)**

---

**[END OF PART 2 — Continue reading PART 3 for setup guide, secrets, testing, and troubleshooting]**


---

## 🔐 ENVIRONMENT VARIABLES (.env File)

### Complete `.env` file structure:

```bash
# ═══════════════════════════════════════════════════════════
# 🌐 GOOGLE CLOUD PLATFORM (Existing - Do Not Change)
# ═══════════════════════════════════════════════════════════
PROJECT_ID=strategic-well-501911-f3
LOCATION=us-central1
BUCKET_NAME=your-bucket-name
GOOGLE_APPLICATION_CREDENTIALS=spiritual-service-account.json

# ═══════════════════════════════════════════════════════════
# 🤖 GEMINI AI (Existing)
# ═══════════════════════════════════════════════════════════
GEMINI_API_KEY=your_gemini_api_key
GEMINI_MODEL=gemini-flash-latest
GEMINI_TEMPERATURE=0.9
GEMINI_MAX_TOKENS=1000

# ═══════════════════════════════════════════════════════════
# 🎨 VERTEX AI IMAGEN (Existing)
# ═══════════════════════════════════════════════════════════
USE_VERTEX_AI=true
VERTEX_MODEL=imagen-3.0-generate-002
VERTEX_MAX_RETRIES=3
VERTEX_RETRY_DELAY=5
VERTEX_ASPECT_RATIO=1:1
VERTEX_DAILY_BUDGET=100.0
VERTEX_MONTHLY_BUDGET=2000.0

# ═══════════════════════════════════════════════════════════
# 🖼️ POLLINATIONS.AI (Existing)
# ═══════════════════════════════════════════════════════════
POLLINATIONS_ENABLED=true
POLLINATIONS_MAX_RETRIES=3
POLLINATIONS_TIMEOUT=120

# ═══════════════════════════════════════════════════════════
# 📱 META - INSTAGRAM & FACEBOOK (Existing)
# ═══════════════════════════════════════════════════════════
INSTAGRAM_ACCOUNT_ID=your_ig_account_id
FACEBOOK_PAGE_ID=your_fb_page_id
ACCESS_TOKEN=your_long_lived_meta_token
META_APP_ID=your_meta_app_id
META_APP_SECRET=your_meta_app_secret
META_API_VERSION=v18.0

# ═══════════════════════════════════════════════════════════
# ⏰ POSTING SCHEDULE (Existing)
# ═══════════════════════════════════════════════════════════
POSTING_HOURS=8,13,20
POSTS_PER_DAY=3
TIME_VARIATION_MINUTES=45

# ═══════════════════════════════════════════════════════════
# 🎤 GOOGLE CLOUD TEXT-TO-SPEECH (🆕 NEW - For Reels)
# ═══════════════════════════════════════════════════════════
TTS_ENABLED=true
TTS_LANGUAGE=hi-IN
TTS_VOICE_MALE=hi-IN-Neural2-B
TTS_VOICE_FEMALE=hi-IN-Neural2-A
TTS_SPEAKING_RATE=0.95
TTS_PITCH=0.0

# ═══════════════════════════════════════════════════════════
# 🎬 REEL CONFIG (🆕 NEW)
# ═══════════════════════════════════════════════════════════
REEL_DURATION_MIN=60
REEL_DURATION_MAX=90
REEL_FPS=30
REEL_STORY_MIN_WORDS=150
REEL_STORY_MAX_WORDS=180
REEL_NUM_SCENES=6
REEL_KEN_BURNS_ENABLED=true
REEL_KEN_BURNS_ZOOM=1.15
REEL_TRANSITION_TYPE=crossfade
REEL_TRANSITION_DURATION=0.5
REEL_MUSIC_ENABLED=true
REEL_MUSIC_VOLUME=0.15
REEL_MUSIC_FOLDER=assets/music
REEL_SUBTITLE_ENABLED=true
REEL_SUBTITLE_FONT_SIZE=60
REEL_POSTING_HOUR=13

# ═══════════════════════════════════════════════════════════
# 📺 YOUTUBE SHORTS (🆕 NEW)
# ═══════════════════════════════════════════════════════════
YOUTUBE_ENABLED=true
YOUTUBE_CHANNEL_ID=your_youtube_channel_id
YOUTUBE_CLIENT_SECRETS_FILE=youtube_client_secrets.json
YOUTUBE_TOKEN_FILE=youtube_token.json
YOUTUBE_PRIVACY_STATUS=public

# ═══════════════════════════════════════════════════════════
# 💾 DATABASE (Existing)
# ═══════════════════════════════════════════════════════════
DB_PATH=divine_poster.db
DB_BACKUP_ENABLED=true

# ═══════════════════════════════════════════════════════════
# 📊 ANALYTICS (Existing)
# ═══════════════════════════════════════════════════════════
ANALYTICS_ENABLED=true
ANALYTICS_FETCH_DELAY_MINUTES=60

# ═══════════════════════════════════════════════════════════
# 📋 LOGGING (Existing)
# ═══════════════════════════════════════════════════════════
LOG_LEVEL=INFO
LOG_DIR=logs
LOG_KEEP_DAYS=30

# ═══════════════════════════════════════════════════════════
# 🎯 FEATURE FLAGS (Existing + New)
# ═══════════════════════════════════════════════════════════
ENABLE_HUMANIZER=true
ENABLE_DUPLICATE_CHECK=true
ENABLE_SELF_LEARNING=true
ENABLE_FESTIVAL_DETECTION=true
ENABLE_SMART_SCHEDULING=true
```

---

## 🔒 GITHUB SECRETS (Complete List)

**Location:** GitHub repo → Settings → Secrets and variables → Actions → New repository secret

### **Existing Secrets (Already Setup):**
```
GEMINI_API_KEY
ACCESS_TOKEN
INSTAGRAM_ACCOUNT_ID
FACEBOOK_PAGE_ID
PROJECT_ID
LOCATION
BUCKET_NAME
META_APP_ID
META_APP_SECRET
GCP_SERVICE_ACCOUNT_JSON     (full JSON content of spiritual-service-account.json)
```

### **🆕 New Secrets to Add:**
```
YOUTUBE_CHANNEL_ID                    (your YT channel ID)
YOUTUBE_CLIENT_SECRETS_JSON           (full JSON content of youtube_client_secrets.json)
YOUTUBE_TOKEN_JSON                    (full JSON content of youtube_token.json after OAuth)
```

**How to add JSON secrets:**
1. Open the JSON file (e.g., `youtube_client_secrets.json`)
2. Copy entire content
3. Paste as-is in GitHub secret value (multi-line supported)

---

## 🛠️ LOCAL SETUP COMMANDS (Windows)

### **1. Install FFmpeg (One-time)**

**Option A: Winget (Easiest)**
```powershell
winget install Gyan.FFmpeg
# Restart terminal after install
ffmpeg -version  # Verify
```

**Option B: Manual**
```powershell
# Download from https://www.gyan.dev/ffmpeg/builds/
# Extract to C:\ffmpeg
# Add C:\ffmpeg\bin to PATH
```

**Verify:**
```powershell
ffmpeg -version
# Should show: ffmpeg version N.N.N ...
```

---

### **2. Download Hindi Fonts (One-time)**

```powershell
cd C:\Users\Rahul\Desktop\सनातन सोच\spiritual-auto-post
mkdir fonts -Force

# Download bold
curl -o fonts/NotoSansDevanagari-Bold.ttf https://github.com/googlefonts/noto-fonts/raw/main/hinted/ttf/NotoSansDevanagari/NotoSansDevanagari-Bold.ttf

# Download regular
curl -o fonts/NotoSansDevanagari-Regular.ttf https://github.com/googlefonts/noto-fonts/raw/main/hinted/ttf/NotoSansDevanagari/NotoSansDevanagari-Regular.ttf

# Verify
dir fonts
# Should show both TTF files
```

---

### **3. Enable Google Cloud APIs (One-time)**

**Via Console:**
1. Go to https://console.cloud.google.com/apis/library
2. Select project: `strategic-well-501911-f3`
3. Enable these APIs:
   - ✅ Cloud Text-to-Speech API (🆕 for Reels)
   - ✅ YouTube Data API v3 (🆕 for YT upload)
   - ✅ Vertex AI API (Existing)
   - ✅ Cloud Storage API (Existing)

**Via CLI:**
```powershell
gcloud services enable texttospeech.googleapis.com
gcloud services enable youtube.googleapis.com
gcloud services enable aiplatform.googleapis.com
gcloud services enable storage.googleapis.com
```

---

### **4. YouTube OAuth Setup (One-time Manual)** 🔑

**Step 1: Create OAuth Client**
1. Go to https://console.cloud.google.com/apis/credentials
2. Click "CREATE CREDENTIALS" → "OAuth client ID"
3. Application type: **Desktop app**
4. Name: `Spiritual Auto Poster YT`
5. Download JSON → Rename to `youtube_client_secrets.json`
6. Place in project root

**Step 2: Add Test User**
1. Go to OAuth consent screen
2. Add your Gmail as "Test user"

**Step 3: Generate Token (One-time)**
```powershell
# After posting/youtube.py is created, run:
python -c "from posting.youtube import _initial_oauth_setup; _initial_oauth_setup()"

# Browser opens → login → grant permissions
# Token saved to youtube_token.json
```

**Step 4: Copy Both JSONs to GitHub Secrets**
- Content of `youtube_client_secrets.json` → `YOUTUBE_CLIENT_SECRETS_JSON`
- Content of `youtube_token.json` → `YOUTUBE_TOKEN_JSON`

---

### **5. Install Python Dependencies**

```powershell
cd C:\Users\Rahul\Desktop\सनातन सोच\spiritual-auto-post

# Activate venv
.\venv\Scripts\activate

# Install new requirements
pip install -r requirements.txt

# Verify key libraries
python -c "import moviepy; print('MoviePy:', moviepy.__version__)"
python -c "from google.cloud import texttospeech; print('TTS OK')"
python -c "from googleapiclient.discovery import build; print('YT API OK')"
```

---

### **6. Add Music Files**

```powershell
mkdir assets/music -Force
mkdir assets/intro -Force
mkdir assets/outro -Force

# Copy your MP3 files to assets/music/
# Recommended: 3-5 tracks
# Sources for copyright-free devotional music:
# - YouTube Audio Library
# - Pixabay Music
# - Free Music Archive
```

---

## 🧪 TESTING COMMANDS

### **Test individual modules:**

```powershell
# Test config
python config/settings.py

# Test topic pool
python config/topics.py

# Test image generation
python utils/vertex_ai.py

# Test watermark
python utils/watermark.py

# Test GCS upload
python utils/gcs_helper.py

# Test recovery
python core/recovery_manager.py

# Test each agent standalone
python -m agents.planner_agent
python -m agents.research_agent
python -m agents.prompt_agent
python -m agents.caption_agent
python -m agents.hashtag_agent
python -m agents.quality_agent test.jpg  # (needs image path)
```

### **Test full pipelines:**

```powershell
# Test single image (existing - should work)
python main.py image

# Test carousel (existing - should work)
python main.py carousel

# Test reel (🆕 after Phase 7)
python main.py reel

# Test recovery
python main.py recovery-stats
python main.py recover

# System health
python main.py health

# Config validation
python main.py test

# Cost stats
python main.py cost
```

---

## 🚨 COMMON ERRORS & SOLUTIONS

### **Error 1: FFmpeg not found**
```
FileNotFoundError: [WinError 2] The system cannot find the file specified: 'ffmpeg'
```
**Solution:**
```powershell
winget install Gyan.FFmpeg
# Restart terminal
# Verify: ffmpeg -version
```

---

### **Error 2: Hindi text shows boxes**
```
Symbols display as ▯▯▯ instead of Hindi
```
**Solution:**
```powershell
# Download fonts
curl -o fonts/NotoSansDevanagari-Bold.ttf https://github.com/googlefonts/noto-fonts/raw/main/hinted/ttf/NotoSansDevanagari/NotoSansDevanagari-Bold.ttf
```

---

### **Error 3: TTS API not enabled**
```
403 Cloud Text-to-Speech API has not been used
```
**Solution:**
```powershell
gcloud services enable texttospeech.googleapis.com
# Wait 2-3 minutes for propagation
```

---

### **Error 4: YouTube quota exceeded**
```
403 quotaExceeded: The request cannot be completed
```
**Solution:**
- Default YT quota: 10,000 units/day
- Video upload: ~1,600 units
- Max videos/day: ~6
- Wait 24 hours OR request quota increase

---

### **Error 5: Instagram Reel container error 2207032**
```
The image or video was uploaded in an unsupported format
```
**Solution:**
- Already handled in existing publisher_agent.py
- Video must be MP4, H.264, AAC audio
- Aspect ratio: 9:16
- Max size: 100 MB
- Max duration: 90 seconds

---

### **Error 6: Memory issues during video build**
```
MemoryError: Unable to allocate array
```
**Solution:**
- Reduce REEL_VIDEO_CRF to 28 (lower quality, smaller file)
- Reduce REEL_FPS to 24
- Process scenes one at a time (not all in memory)

---

### **Error 7: GitHub Actions timeout (60 min)**
```
Error: The operation was canceled
```
**Solution:**
- Optimize FFmpeg preset to "fast" or "ultrafast"
- Reduce video resolution to 720x1280 if desperate
- OR migrate reel workflow to Google Cloud Run (no time limit)

---

### **Error 8: Recovery not detected**
```
No pending recovery found even though pipeline failed
```
**Solution:**
```powershell
# Check recovery folder manually
ls logs/recovery/

# Force check
python main.py recovery-stats

# If corrupted, cleanup
python main.py recovery-cleanup
```

---

## 💾 RECOVERY SCENARIOS

### **Scenario 1: Pipeline fails during image generation**
- Recovery saves after each successful image
- Restart: `python main.py reel` (auto-detects)
- Only generates missing images
- **Savings:** ₹2.50 per already-generated image

### **Scenario 2: Video build fails but images ready**
- Recovery stage: `REEL_IMAGES_GENERATED`
- Restart resumes from video build step
- **Savings:** ₹15 (all 6 images) + Gemini calls

### **Scenario 3: Upload fails but video built**
- Recovery stage: `REEL_VIDEO_BUILT`
- Restart resumes from GCS upload
- **Savings:** ₹15 + video build time (5-10 min)

### **Scenario 4: IG posted, FB failed**
- Recovery stage: `REEL_IG_PUBLISHED`
- Restart only publishes to FB (skips IG)
- **Savings:** No re-posting to IG

### **Scenario 5: Manual recovery trigger**
```powershell
python main.py recover
# Only completes pending recoveries
```

---

## 💰 EXACT COST BREAKDOWN (Per Reel)

| Component | Details | Cost |
|---|---|---|
| **Story Writer (Gemini)** | 1 call, ~2000 tokens | ₹0.30 |
| **Fact Checker (Gemini)** | 1 call, ~1000 tokens | ₹0.20 |
| **Scene Splitter (Gemini)** | 1 call, ~1500 tokens | ₹0.20 |
| **Prompt Builder** | 6 calls, ~300 tokens each | ₹0.30 |
| **Image Generation (Imagen 3)** | 6 images × ₹1.50 | ₹9.00 |
| **Google TTS Hindi (Neural2)** | ~500 chars, $16/1M chars | ₹0.50 |
| **Caption Generator (Gemini)** | 1 call, ~800 tokens | ₹0.15 |
| **Hashtag (no API cost)** | Local | ₹0.00 |
| **GCS Upload (30 MB video)** | Storage + bandwidth | ₹0.15 |
| **YouTube Upload** | Free API | ₹0.00 |
| **Instagram Reel Post** | Free API | ₹0.00 |
| **Facebook Reel Post** | Free API | ₹0.00 |
| **Analytics Fetch** | Free API | ₹0.00 |
| **TOTAL** | | **₹10.80/reel** |

**With Imagen 4 (premium):** ₹15/reel  
**With Imagen 3 fast:** ₹7/reel

### **Monthly Budget (1 Reel/day):**
- 30 reels × ₹10.80 = **₹324/month**

### **Combined Monthly (V2 Full):**
- 30 Images × ₹2.50 = ₹75
- 30 Carousels × ₹12.50 = ₹375
- 30 Reels × ₹10.80 = ₹324
- **TOTAL: ₹774/month** ✅ (Well under ₹2000 budget)

---

## 📊 EXPECTED PERFORMANCE METRICS

### **Reel Generation Time (Local/GitHub Actions):**

| Stage | Time |
|---|---|
| Planner + Research | 30s |
| Story Writer + Fact Check | 45s |
| Scene Splitter | 20s |
| Prompt Builder | 15s |
| Image Generation (6 × ~30s) | 3 min |
| Quality Check (6 × ~5s) | 30s |
| Watermark + Humanize (6 × ~3s) | 18s |
| TTS Voice Generation | 20s |
| Subtitle Generation | 5s |
| Video Building (FFmpeg) | 3-5 min |
| GCS Upload (30MB) | 30-60s |
| IG Reel Post | 30-60s |
| FB Reel Post | 20s |
| YouTube Upload | 60-120s |
| **TOTAL** | **~12-15 minutes** |

**GitHub Actions timeout:** 60 min (plenty of buffer)

---

## 🔄 CONTINUATION INSTRUCTIONS

### **If Chat Ends / New Session Needed:**

**To resume EXACTLY where we left off, paste this in new chat:**

```
Bhai, main pehle wali chat mein Divine AI Content Factory V2 
project pe kaam kar raha tha. Ye complete context file hai — 
padho aur samjho ki kya already hai, kya karna hai, aur kahan 
se continue karna hai:

[PASTE ENTIRE PROJECT_CONTEXT.md CONTENT HERE]

Ab batao:
1. Kya sab samajh gaye?
2. Hum kis phase pe the?
3. Next module kaunsa banana hai?

Main strict rules follow karunga:
- Existing code touch nahi karna
- Extend, not duplicate
- Module by module
- Purpose/Inputs/Outputs pehle, code baad mein
- Aapki approval ke bina kuch nahi likhna
```

---

### **Current Status Tracking (Update after each module):**

```
✅ = Complete
🔄 = In Progress  
❌ = Not Started

PHASE 1: Foundation
[❌] core/memory.py — Add Reel fields
[❌] core/database.py — Schema migration
[❌] core/recovery_manager.py — Add Reel stages
[❌] config/settings.py — Add TTS/YT/Reel config
[❌] requirements.txt — Add dependencies
[❌] Download Hindi fonts
[❌] Install FFmpeg locally

PHASE 2: Story Layer
[❌] reels/__init__.py
[❌] reels/story_writer.py
[❌] reels/fact_checker.py
[❌] reels/scene_splitter.py
[❌] reels/prompt_builder.py

PHASE 3: Visual Layer
[❌] Test vertex_ai.py with 9:16
[❌] Verify quality_agent.py handles portrait

PHASE 4: Audio Layer
[❌] video_engine/__init__.py
[❌] video_engine/tts_engine.py
[❌] video_engine/subtitle_generator.py

PHASE 5: Video Layer
[❌] video_engine/clip_renderer.py
[❌] video_engine/effects.py
[❌] video_engine/music_manager.py
[❌] video_engine/concat_engine.py
[❌] video_engine/video_builder.py
[❌] utils/watermark.py — apply_video_branding()

PHASE 6: Storage & Orchestration
[❌] utils/gcs_helper.py — upload_video()
[❌] core/reel_engine.py
[❌] reels/reel_agent.py

PHASE 7: Publishing
[❌] agents/publisher_agent.py — Reel functions
[❌] YouTube OAuth setup
[❌] posting/__init__.py
[❌] posting/youtube.py

PHASE 8: Integration & Testing
[❌] agents/caption_agent.py — reel_hook style
[❌] agents/hashtag_agent.py — reel hashtags
[❌] agents/analytics_agent.py — reel metrics
[❌] main.py — run_reel_pipeline()
[❌] .github/workflows/auto_reel.yml
[❌] End-to-end testing
```

**IMPORTANT:** Aap khud har module complete hone par ✅ mark karo.

---

## 🎯 IMPORTANT CODING CONVENTIONS

### **1. Logging Pattern (Follow Existing)**
```python
from utils.logger import get_logger
logger = get_logger("module_name")

logger.info("=" * 55)
logger.info("=== MODULE NAME STARTED ===")
logger.info("=" * 55)

# Steps
logger.info("▶️  Step 1: Doing X...")
logger.info("✅ Step 1 complete")

# Success
logger.info(f"✅ SUCCESS in {duration}s")

# Errors
logger.error(f"❌ FAILED: {error}")

logger.info("=== MODULE NAME DONE ===\n")
```

### **2. Error Handling Pattern**
```python
try:
    # Main logic
    result = do_something()
    
    if not result:
        raise Exception("Result is empty")
    
    return result

except Exception as e:
    logger.error(f"❌ Failed: {e}")
    memory.add_error("module_name", str(e))
    raise  # Re-raise for critical operations
    # OR return fallback for non-critical
```

### **3. Recovery Pattern**
```python
# Check if already done (recovery)
if memory.some_field:
    logger.info("⏭️  Already done, skipping (recovery)")
    return memory

# Do work
memory.some_field = do_work()

# Save checkpoint
save_checkpoint(
    session_id=memory.session_id,
    stage="STAGE_NAME",
    data={...}
)
```

### **4. Gemini Call Pattern**
```python
import google.generativeai as genai
from config.settings import GEMINI_API_KEY, GEMINI_MODEL

genai.configure(api_key=GEMINI_API_KEY)

for attempt in range(1, 3 + 1):
    try:
        model = genai.GenerativeModel(GEMINI_MODEL)
        response = model.generate_content(
            prompt,
            generation_config={
                "temperature": 0.8,
                "max_output_tokens": 1000,
                "top_p": 0.95,
            }
        )
        text = response.text.strip()
        # Process...
        break
    except Exception as e:
        logger.warning(f"Attempt {attempt} failed: {e}")
        if attempt < 3:
            time.sleep(3)
```

### **5. Memory Update Pattern**
```python
def run(memory: AgentMemory) -> AgentMemory:
    # ALWAYS take memory as input
    # ALWAYS return memory (even on error)
    
    if not memory.some_input:
        memory.add_error("module", "Missing input")
        return memory  # Don't raise, return
    
    try:
        # Do work
        memory.some_output = result
    except Exception as e:
        logger.error(f"Failed: {e}")
        memory.add_error("module", str(e))
    
    return memory  # ALWAYS return
```

### **6. Hindi Text Pattern**
```python
# Devanagari script for logs (matches existing style)
logger.info("🎬 रील बना रहे हैं...")
logger.info(f"✅ पूर्ण: {duration}s में")

# Bilingual for user-facing
logger.info("🎬 Reel बनना शुरू हो गया")
```

---

## 🎨 KEY DESIGN DECISIONS (Approved by User)

1. **Video Duration:** 60-90s (universal for IG Reel + YT Shorts + FB Reel)
2. **Story Length:** 150-180 words (never cut, quality > brevity)
3. **Scenes:** 6 scenes per reel (10-12s each)
4. **Voice:** Category-based (Krishna/Ram/Shiva/Hanuman/Ganesha = male, Durga/Saraswati = female)
5. **Music:** Manual library (user provides copyright-free tracks)
6. **Subtitles:** Word-by-word highlighted (modern reel style)
7. **Watermark:** On EVERY scene image + final video (anti-crop)
8. **Fallback Chain:** Imagen 4 → Imagen 3 → Gemini → Pollinations (FREE)
9. **Development:** MVP-first (basic reel working → polish later)
10. **Publishing:** IG + FB + YouTube ALL on same day
11. **Recovery:** Full checkpoint system (never lose money on failures)
12. **Existing Projects:** User has 2 bonus projects to potentially reuse (pending analysis)

---

## 📚 EXTERNAL RESOURCES / DOCS

### **Google Cloud APIs:**
- Vertex AI Imagen: https://cloud.google.com/vertex-ai/docs/generative-ai/image/overview
- Cloud TTS: https://cloud.google.com/text-to-speech/docs/voices
- YouTube Data API: https://developers.google.com/youtube/v3/docs

### **Meta APIs:**
- Instagram Reels API: https://developers.facebook.com/docs/instagram-api/guides/content-publishing
- Facebook Reels: https://developers.facebook.com/docs/video-api/guides/reels-publishing

### **Libraries:**
- MoviePy: https://zulko.github.io/moviepy/
- FFmpeg: https://ffmpeg.org/documentation.html
- pydub: https://github.com/jiaaro/pydub

---

## 🔥 PENDING DECISIONS (Awaiting User Input)

### **Decision 1: Existing Projects Reuse**
User mentioned 2 existing working projects:
- Project 1: Auto YouTube uploader (topic → image → voice → video → YT)
- Project 2: Long video generator (FFmpeg, up to 25 min)

**Pending:** User to share code files → AI analyzes → identifies reusable parts

**Options:**
- **A:** Share both projects → 30-40% dev time saved ⭐ Recommended
- **B:** Skip, write fresh (7 weeks development)
- **C:** Hybrid — share only specific files

---

## 🚀 IMMEDIATE NEXT STEPS

### **If starting fresh:**

1. **User Action:** Copy this entire file (Part 1 + Part 2 + Part 3) into `PROJECT_CONTEXT.md`
2. **User Action:** Decide on existing projects reuse (Option A/B/C above)
3. **User Action:** Say **"Start Phase 1, Module 1 — memory.py modifications"**
4. **AI Action:** Show Purpose/Inputs/Outputs/Changes for `memory.py`
5. **User Action:** Approve → AI writes complete modified file
6. **User Action:** Test → Confirm working → Move to Module 2

### **If continuing from break:**

1. Check current status in Phase Tracker above
2. Identify last completed module
3. Move to next module in sequence
4. Follow same pattern (Purpose → Approval → Code)

---

## 🎬 FINAL NOTE

**Ye file MASTER SOURCE OF TRUTH hai. Har module banane se pehle isko refer karo.**

**Update rules:**
- Har module complete hone par Phase Tracker mein ✅ mark karo
- Naya decision aaye to relevant section update karo
- Naya error mile to "Common Errors" mein add karo
- File ka **"Last Updated"** date update karte raho

**Backup:**
- Ye file GitHub par bhi commit karo (`PROJECT_CONTEXT.md`)
- Ye NEVER delete karo
- Multiple copies rakho (Google Drive, email to self)

---

## 🙏 END OF CONTEXT FILE

**Total sections:** 3 parts merged into 1 complete file  
**Estimated total length:** ~15,000 words  
**Purpose:** Complete continuity across chat sessions  
**Reuse:** Copy-paste in new chat = instant full context

**Bolo "Start Phase 1" jab aap ready ho coding start karne ke liye.** 🚀

**Har Har Mahadev! 🕉️**

Ye pura context padho aur batao next kya karna hai


---




# 📌 PART 4/4 — CRITICAL NOTES & GOTCHAS (MUST READ)

> **Purpose:** Ye section un cheezon ke liye hai jo baaki jagah miss ho gayi thi, but production mein bahut zaroori hain.

---

## ⚠️ CRITICAL GOTCHAS (Common Mistakes to Avoid)

### **Gotcha 1: Instagram Reel API Requirements**

**Problem:** IG Reel API strict hai video specs pe. Galat spec = Error 2207032

**Required Video Specs:**
```
✅ Container: MP4
✅ Video Codec: H.264 (libx264)
✅ Audio Codec: AAC (aac)
✅ Aspect Ratio: 9:16 (1080x1920 exact)
✅ Frame Rate: 23-60 fps (30 recommended)
✅ Duration: 3-90 seconds (60-90s recommended for reels)
✅ File Size: Max 100 MB (aim for 20-50 MB)
✅ Bitrate: Video 3.5-5 Mbps, Audio 128 kbps
✅ Color Space: Full range (BT.709)
❌ NO variable frame rate (VFR) — must be CFR
❌ NO HDR
❌ NO progressive JPEG
```

**FFmpeg command that ALWAYS works:**
```bash
ffmpeg -i input.mp4 \
  -c:v libx264 -profile:v high -preset medium -crf 23 \
  -pix_fmt yuv420p -r 30 \
  -c:a aac -b:a 128k -ar 44100 \
  -movflags +faststart \
  -y output.mp4
```

**Note in code:** Video builder MUST use these exact params or reels will fail silently.

---

### **Gotcha 2: YouTube Shorts vs Regular Video**

**How YouTube decides it's a Short:**
1. ✅ Vertical aspect ratio (9:16)
2. ✅ Duration ≤ 60 seconds
3. ✅ Title/Description mein `#Shorts` hashtag

**Critical:** Agar 90 second reel banaya to YouTube pe **Short NAHI** hoga, regular video ban jayega.

**Solution:**
- IG + FB → 90 second reel OK
- YouTube → **Cut to 60 seconds** OR skip YouTube for that reel

**Or:** Generate 2 versions:
- Version 1: 90s for IG/FB
- Version 2: 60s (trimmed) for YouTube

**Add to future feature list.**

---

### **Gotcha 3: Google TTS Character Limits & Costs**

**Limits per request:**
- Max characters: 5,000 per API call
- SSML max: 5,000 chars
- Neural2 voice cost: $16 per 1M chars

**150-180 word Hindi story:**
- ~500-600 characters (Devanagari counts as multi-byte)
- Cost per reel: ~₹0.50
- Well under limit ✅

**Warning:** If story exceeds 5000 chars (very long documentary in future), need to split into multiple API calls and concatenate audio.

---

### **Gotcha 4: FFmpeg Memory Usage**

**Problem:** MoviePy loads entire video in RAM

**On GitHub Actions (7 GB RAM limit):**
- 6 images (1080x1920 each) + voice + BG music = **~2-3 GB RAM peak**
- Should work, but monitor

**On Google Cloud Functions (default 512 MB):**
- **WILL FAIL** ❌
- Need Cloud Run with 2GB+ RAM

**Solution for GH Actions:**
- Use `moviepy.editor.VideoFileClip.close()` after each clip
- Process scenes in chunks, not all at once
- Use `preset="ultrafast"` for lower memory

---

### **Gotcha 5: Recovery With Video Files**

**Problem:** Video files are BIG (30 MB avg)

**Existing recovery system saves:**
- ✅ Image bytes (small, ~500 KB each) — no issue
- ⚠️ Voice bytes (medium, ~1 MB) — OK
- ❌ Video bytes (huge, 30 MB) — will bloat `logs/recovery/`

**Solution:**
```python
# DON'T save video_bytes in recovery
# Save video_url (after GCS upload) instead

# If recovery needed AFTER video build but BEFORE upload:
# → Just re-build video (10 min) — cheaper than 30MB checkpoint
```

**Add rule:** Recovery only saves lightweight data. Big files (video) recreated on demand.

---

### **Gotcha 6: Hindi TTS Pronunciation Issues**

**Common problems:**
- English words in Hindi text → weird pronunciation
- Numbers → said in English by default
- Sanskrit words → sometimes wrong

**Solutions using SSML:**
```xml
<speak>
  <!-- Force Hindi pronunciation for English words -->
  भगवान <sub alias="कृष्ण">Krishna</sub> ने कहा
  
  <!-- Numbers in Hindi -->
  <say-as interpret-as="cardinal" language="hi-IN">5000</say-as> साल पहले
  
  <!-- Pause for effect -->
  यह ज्ञान <break time="500ms"/> अनमोल है
  
  <!-- Emphasis -->
  <emphasis level="strong">जय श्री कृष्ण</emphasis>
</speak>
```

**Add to `story_writer.py`:** Instruct Gemini to output SSML-friendly Hindi (all Devanagari, no English mixed in).

---

### **Gotcha 7: Font Rendering on Ubuntu (GitHub Actions)**

**Problem:** Windows font paths won't work on GH Actions runner

**In `core/carousel_engine.py`:**
```python
FONT_PATHS = {
    "bold": [
        "C:/Windows/Fonts/NirmalaB.ttf",        # ❌ Windows only
        "/usr/share/fonts/truetype/noto/...",   # ✅ Ubuntu
        "fonts/NotoSansDevanagari-Bold.ttf",    # ✅ CROSS-PLATFORM ⭐
    ]
}
```

**Solution:** ALWAYS put `fonts/NotoSansDevanagari-Bold.ttf` (local project font) as **first fallback**. This works on Windows, Mac, Linux.

**Same rule for video subtitles.**

---

### **Gotcha 8: GCS Signed URLs vs Public URLs**

**Instagram/Facebook needs:**
- **PUBLIC URLs** (they fetch the video from internet)
- Signed URLs sometimes work but risky

**In `upload_video()`:**
```python
if make_public:
    blob.make_public()
    url = blob.public_url  # ← USE THIS for social media
else:
    url = blob.generate_signed_url(...)  # ← Only for internal use
```

**Rule:** For social media uploads, ALWAYS use `make_public=True`.

---

### **Gotcha 9: Cost Tracking for New APIs**

**Existing `utils/vertex_ai.py` tracks:**
- ✅ Image generation costs

**Missing tracking for:**
- ❌ Google TTS calls (need to add)
- ❌ Gemini text calls (story/scene/caption)
- ❌ YouTube uploads (free but track quota)

**Solution:** Extend `vertex_ai.py` tracking system OR create `utils/cost_tracker.py` as unified tracker.

**Priority:** Medium (do in Phase 8 polish)

---

### **Gotcha 10: Meta Access Token Expiry**

**Problem:** Long-lived tokens still expire in 60 days

**Symptoms:**
- All IG/FB posts start failing
- Error: `Session has expired on X date`

**Prevention:**
1. Add token refresh reminder (60 day cron alert)
2. Store token creation date
3. Auto-refresh 7 days before expiry

**Manual refresh:**
```
https://developers.facebook.com/tools/debug/accesstoken/
→ Paste token → Extend
```

**Add to `main.py health` command:** Check token age, warn if > 50 days.

---

## 🔒 SECURITY CHECKLIST

### **Files that MUST be in `.gitignore`:**
```gitignore
# Credentials
.env
spiritual-service-account.json
youtube_client_secrets.json
youtube_token.json

# Database
*.db
divine_poster.db

# Recovery
logs/recovery/
logs/*.log
logs/*.json

# Cache
__pycache__/
*.pyc
venv/

# Temp files
temp_*.mp4
temp_*.jpg
temp_*.mp3
*_watermark.png

# Test outputs
test_*.jpg
test_*.mp4
test_vertex.jpg
test_humanized.jpg
test_watermark_*.jpg

# OS
.DS_Store
Thumbs.db
```

### **NEVER commit these to GitHub:**
- ❌ Any `.json` credentials
- ❌ `.env` file
- ❌ Database files
- ❌ Recovery folders

### **What to check before every commit:**
```powershell
git status
# Look for suspicious files

git diff --cached
# Review what's being committed

# If mistake:
git reset HEAD <file>
```

---

## 🐛 DEBUGGING WORKFLOW

### **When something breaks, follow this order:**

**Step 1: Check logs**
```powershell
# Latest log
type logs\$(Get-Date -Format "yyyy-MM-dd").log | Select-Object -Last 100

# Errors only
type logs\errors.log | Select-Object -Last 50
```

**Step 2: Check config**
```powershell
python main.py test
# Validates all env vars
```

**Step 3: Check system health**
```powershell
python main.py health
# API accessibility, DB, disk space
```

**Step 4: Check budget**
```powershell
python main.py cost
# Ensures budget not exceeded
```

**Step 5: Check recovery**
```powershell
python main.py recovery-stats
# Any pending recoveries?
```

**Step 6: Test individual agent**
```powershell
python -m agents.planner_agent
# Isolate the failing component
```

**Step 7: Run in DEBUG mode**
```powershell
# Set in .env
LOG_LEVEL=DEBUG

# Then run
python main.py reel
# Verbose output
```

---

## 📊 PERFORMANCE OPTIMIZATION TIPS

### **When Reel building is slow:**

**Optimization 1: Parallel Image Generation**
```python
# Instead of loop:
for scene in scenes:
    generate_image(scene)  # Sequential = 3 min

# Use ThreadPoolExecutor:
from concurrent.futures import ThreadPoolExecutor
with ThreadPoolExecutor(max_workers=3) as executor:
    results = list(executor.map(generate_image, scenes))
# Parallel = 1 min (3x faster)
```

**Optimization 2: FFmpeg Preset**
```python
# Slow but good quality
preset = "medium"  # ~5 min build

# Fast but bigger file
preset = "fast"    # ~3 min build

# Fastest but larger file
preset = "ultrafast"  # ~1 min build

# For GH Actions: use "fast"
# For local testing: use "ultrafast"
```

**Optimization 3: Cache TTS**
- If regenerating same story, use cached voice
- Save voice bytes in `logs/tts_cache/`

**Optimization 4: Use Imagen 3 Fast**
- Change model to `imagen-3.0-fast-generate-001` (₹1/image vs ₹2.50)
- Slightly lower quality, 2-3x faster

---

## 🎯 QUALITY CONTROL CHECKLIST

### **Before each Reel goes live, verify:**

- [ ] Story is 150-180 words
- [ ] Story has hook + emotion + CTA
- [ ] Fact checker passed (no false info)
- [ ] All 6 images generated successfully
- [ ] All images pass quality check (score ≥ 60)
- [ ] Voice is clearly audible (not too fast)
- [ ] Subtitles sync with voice
- [ ] Video duration is 60-90 seconds
- [ ] Video is 1080x1920 (9:16)
- [ ] Watermark visible but not distracting
- [ ] BG music at 15% (voice dominant)
- [ ] Caption has emojis and CTA
- [ ] Hashtags: 20-25 total, mixed tiers
- [ ] No duplicate topic (last 20 posts)

**Automate this in `quality_agent.py` for videos.**

---

## 🔄 BACKUP STRATEGY

### **What to backup daily:**
1. `divine_poster.db` — All post history + analytics
2. `logs/vertex_usage.json` — Cost tracking
3. `logs/recovery/` — Pending recoveries
4. `.env` — Config (encrypted)

**Auto-backup script:**
```powershell
# Add to Windows Task Scheduler (daily)
$date = Get-Date -Format "yyyy-MM-dd"
$backupDir = "C:\Users\Rahul\Desktop\Backups\spiritual\$date"
mkdir $backupDir -Force

Copy-Item "divine_poster.db" "$backupDir\"
Copy-Item "logs\vertex_usage.json" "$backupDir\"
Copy-Item -Recurse "logs\recovery" "$backupDir\" -ErrorAction SilentlyContinue

# Cloud backup (optional)
# gsutil cp -r $backupDir gs://your-backup-bucket/
```

**Recovery:** Just copy back from backup folder.

---

## 📅 MAINTENANCE SCHEDULE

### **Daily (Automatic):**
- ✅ 8 AM: Image post
- ✅ 1 PM: Reel post
- ✅ 8 PM: Carousel post
- ✅ Check logs for errors

### **Weekly (Manual, 5 min):**
- Review analytics: `python main.py cost`
- Check recovery stats: `python main.py recovery-stats`
- Delete old recoveries: `python main.py recovery-cleanup`
- Verify all 3 platforms posting

### **Monthly (Manual, 30 min):**
- Review best performing content
- Update `TOPIC_POOL` if needed
- Backup database
- Check Meta token expiry
- Review GCS storage costs

### **Every 60 Days (CRITICAL):**
- 🚨 Refresh Meta ACCESS_TOKEN
- 🚨 Verify YouTube OAuth still valid
- 🚨 Rotate service account keys (recommended)

---

## 🎓 LEARNING NOTES (For Future You)

### **Why we chose these tools:**

**Google TTS Neural2 (not ElevenLabs):**
- ✅ Free tier: 1M chars/month
- ✅ Native Hindi support
- ✅ Word-level timestamps
- ❌ ElevenLabs: better quality but $$$

**MoviePy (not raw FFmpeg subprocess):**
- ✅ Pythonic API
- ✅ Easy Ken Burns effects
- ❌ Slower than raw FFmpeg
- **Alternative:** Direct FFmpeg subprocess (2x faster but complex)

**Instagram Reels API (not Instagrapi):**
- ✅ Official Meta API
- ✅ Won't get banned
- ❌ Instagrapi: unofficial, high ban risk

**YouTube Data API v3:**
- ✅ Free (10K units/day)
- ✅ Official
- ⚠️ Quota resets 12:00 AM Pacific Time (not IST)

---

## 🚫 THINGS WE DECIDED NOT TO DO

Document decisions to avoid re-debating:

1. **No AI-generated music** — Cost + copyright concerns → Manual library
2. **No auto-thumbnail generation** — YT/IG auto-pick from video → Use first frame
3. **No comment auto-reply** — Spam risk → Manual for now
4. **No Twitter/X posting** — Different content format → Focus IG/FB/YT
5. **No custom video intro/outro (MVP)** — Add later after MVP works
6. **No multi-language support** — Focus Hindi only → English later
7. **No live streaming** — Out of scope
8. **No custom TTS voice training** — Use Google Neural2 → Good enough
9. **No AI story judgement** — Trust Gemini + fact-checker → Human review sample
10. **No auto-schedule optimization** — Fixed times (8AM/1PM/8PM) → Analytics later

---

## 🎯 FUTURE ENHANCEMENTS (V3 Roadmap)

**After V2 MVP is stable, consider:**

### **Phase 9: Long-form Videos**
- 10-15 min spiritual documentaries
- YouTube long-form (monetization eligible)
- Reuse existing engine, longer stories

### **Phase 10: Multi-language**
- English versions for global reach
- Regional (Marathi, Tamil, Bengali)
- Auto-translate + separate voice models

### **Phase 11: AI Comment Response**
- Detect genuine questions vs spam
- Reply with Gemini in appropriate tone
- Human approval queue for sensitive topics

### **Phase 12: A/B Testing**
- Same topic → 2 different styles
- Post at different times
- Measure engagement → auto-optimize

### **Phase 13: Voice Cloning**
- User records 5 min of their voice
- Use it for all Reels (personal brand)
- Uses ElevenLabs or similar

### **Phase 14: Interactive Content**
- IG Story polls based on Reel topics
- YouTube community posts
- Cross-promotion between platforms

---

## 🆘 EMERGENCY CONTACTS / RESOURCES

### **If APIs break:**
- Google Cloud Status: https://status.cloud.google.com/
- Meta Status: https://metastatus.com/
- YouTube API Status: https://status.cloud.google.com/

### **If you need help:**
- Meta Developer Community: https://developers.facebook.com/community/
- Google Cloud Support (if paid tier)
- Stack Overflow tags: `google-cloud-storage`, `moviepy`, `instagram-graph-api`

### **Documentation Bookmarks:**
- Vertex AI Imagen: https://cloud.google.com/vertex-ai/docs/generative-ai/image/generate-images
- Cloud TTS Voices: https://cloud.google.com/text-to-speech/docs/voices
- IG Reels API: https://developers.facebook.com/docs/instagram-api/guides/content-publishing#reels
- YouTube Shorts: https://developers.google.com/youtube/v3/guides/uploading_a_video

---

## 📝 FINAL CHECKLIST BEFORE STARTING CODING

Verify these ALL are done before Phase 1:

### **Environment Setup:**
- [ ] FFmpeg installed and in PATH (`ffmpeg -version` works)
- [ ] Python 3.11+ installed
- [ ] Virtual environment activated (`venv\Scripts\activate`)
- [ ] Existing `requirements.txt` installed
- [ ] Existing `.env` file has all current values
- [ ] Existing `spiritual-service-account.json` present

### **Google Cloud:**
- [ ] Text-to-Speech API enabled
- [ ] YouTube Data API v3 enabled
- [ ] Vertex AI API enabled (already done)
- [ ] Storage API enabled (already done)
- [ ] Service account has permissions for all APIs

### **YouTube:**
- [ ] YouTube channel exists
- [ ] Channel ID copied to notes
- [ ] OAuth Desktop client created
- [ ] `youtube_client_secrets.json` downloaded to project root
- [ ] Test user added in OAuth consent screen

### **Local Files:**
- [ ] `fonts/NotoSansDevanagari-Bold.ttf` downloaded
- [ ] `fonts/NotoSansDevanagari-Regular.ttf` downloaded
- [ ] `assets/music/` folder created (files can come later)
- [ ] `PROJECT_CONTEXT.md` saved in project root

### **GitHub:**
- [ ] All existing secrets still valid
- [ ] `.gitignore` includes all sensitive files
- [ ] `PROJECT_CONTEXT.md` committed to repo

### **Verification:**
- [ ] Existing image post still works: `python main.py image`
- [ ] Existing carousel still works: `python main.py carousel`
- [ ] Config validates: `python main.py test`
- [ ] Health check passes: `python main.py health`

**IF ALL ✅ → READY FOR PHASE 1**

---

## 💡 GOLDEN RULES (Repeat 3 Times Daily)

1. **"Never assume — always inspect existing code first"**
2. **"Extend, don't duplicate"**
3. **"One module at a time — no shortcuts"**
4. **"Purpose → Approval → Code (in that order)"**
5. **"Test after every module"**
6. **"Commit working code before starting next module"**
7. **"Update PROJECT_CONTEXT.md with progress"**
8. **"Backup before major changes"**
9. **"Read logs when things break"**
10. **"Har Har Mahadev 🕉️"**

---

## 🎯 SUMMARY: WHY THIS FILE EXISTS

**This file solves 3 problems:**

1. **Chat Continuity** — AI forgets. This file remembers.
2. **Onboarding** — Any new dev/AI reads this = instant productivity
3. **Reference** — Debugging, planning, decisions all in one place

**Usage:**
- Beginning of new chat: Paste entire file
- During coding: Reference specific sections
- After each module: Update progress tracker
- When confused: Re-read golden rules

---

## 🙏 FINAL WORDS

Bhai, ye file **complete blueprint** hai. Isme sab kuch hai jo Divine AI Content Factory V2 banane ke liye chahiye:

✅ What exists  
✅ What to modify  
✅ What to create  
✅ Data flow  
✅ Development roadmap  
✅ Environment setup  
✅ Testing commands  
✅ Common errors  
✅ Cost breakdown  
✅ Security checklist  
✅ Performance tips  
✅ Backup strategy  
✅ Maintenance schedule  
✅ Future roadmap  
✅ Emergency resources

**Ye file save karo, GitHub par push karo, aur coding start karo.**

**Har Har Mahadev! 🕉️**

**JAI SHRI KRISHNA! 🌸**

---

**[END OF PROJECT_CONTEXT.md — Total: Part 1 + Part 2 + Part 3 + Part 4]**

**Total Sections:** 4 parts merged  
**Estimated Length:** ~20,000 words  
**Purpose:** Complete master reference  
**Update Frequency:** After every module completion  
**Backup Location:** GitHub + Google Drive + Local