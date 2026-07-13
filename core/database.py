"""
SQLite Database - Memory, History, Analytics
"""
import sqlite3
from datetime import datetime
from config.settings import DB_PATH
from utils.logger import get_logger

logger = get_logger("database")


def get_connection():
    return sqlite3.connect(DB_PATH)


def initialize_database():
    """Create all tables on first run"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS post_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            post_date TEXT NOT NULL,
            topic TEXT NOT NULL,
            category TEXT,
            image_style TEXT,
            image_url TEXT,
            caption TEXT,
            hashtags TEXT,
            ig_post_id TEXT,
            fb_post_id TEXT,
            ig_success INTEGER DEFAULT 0,
            fb_success INTEGER DEFAULT 0,
            duration_seconds REAL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS analytics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            post_id INTEGER,
            platform TEXT,
            likes INTEGER DEFAULT 0,
            comments INTEGER DEFAULT 0,
            shares INTEGER DEFAULT 0,
            reach INTEGER DEFAULT 0,
            impressions INTEGER DEFAULT 0,
            fetched_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (post_id) REFERENCES post_history(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS style_performance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            image_style TEXT UNIQUE,
            total_posts INTEGER DEFAULT 0,
            total_reach INTEGER DEFAULT 0,
            total_likes INTEGER DEFAULT 0,
            avg_reach REAL DEFAULT 0,
            last_updated TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS used_content (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content_type TEXT,
            content_value TEXT,
            used_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()
    logger.info("Database initialized successfully")


def save_post(data: dict) -> int:
    """Save post to history. Returns post ID"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO post_history (
            post_date, topic, category, image_style,
            image_url, caption, hashtags,
            ig_post_id, fb_post_id,
            ig_success, fb_success, duration_seconds
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        data.get("post_date", datetime.now().isoformat()),
        data.get("topic", ""),
        data.get("category", ""),
        data.get("image_style", ""),
        data.get("image_url", ""),
        data.get("caption", ""),
        data.get("hashtags", ""),
        data.get("ig_post_id", ""),
        data.get("fb_post_id", ""),
        1 if data.get("ig_success") else 0,
        1 if data.get("fb_success") else 0,
        data.get("duration_seconds", 0)
    ))

    post_id = cursor.lastrowid
    conn.commit()
    conn.close()

    logger.info(f"Post saved with ID: {post_id}")
    return post_id


def get_recent_topics(limit=20) -> list:
    """Get recently used topics to avoid repetition"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT topic FROM post_history 
        ORDER BY created_at DESC 
        LIMIT ?
    """, (limit,))
    topics = [row[0] for row in cursor.fetchall()]
    conn.close()
    return topics


def save_analytics(post_id: int, platform: str, data: dict):
    """Save engagement analytics for a post"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO analytics (
            post_id, platform, likes, comments,
            shares, reach, impressions
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        post_id,
        platform,
        data.get("likes", 0),
        data.get("comments", 0),
        data.get("shares", 0),
        data.get("reach", 0),
        data.get("impressions", 0)
    ))

    conn.commit()
    conn.close()


def update_style_performance(image_style: str, reach: int, likes: int):
    """Update style performance after analytics fetch"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO style_performance (image_style, total_posts, total_reach, total_likes)
        VALUES (?, 1, ?, ?)
        ON CONFLICT(image_style) DO UPDATE SET
            total_posts = total_posts + 1,
            total_reach = total_reach + ?,
            total_likes = total_likes + ?,
            avg_reach = (total_reach + ?) / (total_posts + 1),
            last_updated = CURRENT_TIMESTAMP
    """, (image_style, reach, likes, reach, likes, reach))

    conn.commit()
    conn.close()


def get_best_performing_styles(limit=3) -> list:
    """Get top performing image styles"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT image_style, avg_reach, total_posts 
        FROM style_performance 
        WHERE total_posts >= 3
        ORDER BY avg_reach DESC 
        LIMIT ?
    """, (limit,))
    rows = cursor.fetchall()
    conn.close()
    return [{"style": r[0], "avg_reach": r[1], "posts": r[2]} for r in rows]


def mark_content_used(content_type: str, content_value: str):
    """Mark a topic/quote as used"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO used_content (content_type, content_value)
        VALUES (?, ?)
    """, (content_type, content_value))
    conn.commit()
    conn.close()


def is_content_used(content_type: str, content_value: str) -> bool:
    """Check if content was already used"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id FROM used_content 
        WHERE content_type = ? AND content_value = ?
        LIMIT 1
    """, (content_type, content_value))
    result = cursor.fetchone()
    conn.close()
    return result is not None