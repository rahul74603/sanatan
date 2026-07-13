"""
Centralized Logging System - Production Grade
Features:
- Colored console output (color-coded by level)
- Automatic log rotation (size + time based)
- Separate error log file
- Log level from environment
- Auto cleanup of old logs
- Beautiful formatting
- Emoji indicators
- Performance-optimized
- Thread-safe
- JSON logging option (for parsing)
"""
import logging
import logging.handlers
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path


# ============================================================
# CONFIGURATION
# ============================================================

# Log directory
LOG_DIR = Path(os.getenv("LOG_DIR", "logs"))
LOG_DIR.mkdir(exist_ok=True)

# Log level (from .env or default INFO)
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

# Keep logs for N days
LOG_KEEP_DAYS = int(os.getenv("LOG_KEEP_DAYS", "30"))

# Max log file size (10 MB)
MAX_LOG_SIZE = 10 * 1024 * 1024

# Number of backup log files
BACKUP_COUNT = 5


# ============================================================
# ANSI COLOR CODES
# ============================================================

class Colors:
    """ANSI color codes for terminal"""
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"

    # Regular colors
    BLACK = "\033[30m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"

    # Bright colors
    BRIGHT_RED = "\033[91m"
    BRIGHT_GREEN = "\033[92m"
    BRIGHT_YELLOW = "\033[93m"
    BRIGHT_BLUE = "\033[94m"
    BRIGHT_MAGENTA = "\033[95m"
    BRIGHT_CYAN = "\033[96m"

    # Background colors
    BG_RED = "\033[41m"
    BG_GREEN = "\033[42m"
    BG_YELLOW = "\033[43m"


# Enable colors on Windows
if sys.platform == "win32":
    try:
        import colorama
        colorama.init()
    except ImportError:
        # Enable ANSI on Windows 10+ without colorama
        os.system("")


# ============================================================
# LEVEL CONFIGURATIONS
# ============================================================

LEVEL_CONFIG = {
    "DEBUG": {
        "color": Colors.CYAN,
        "emoji": "🔍",
        "label": "DEBUG"
    },
    "INFO": {
        "color": Colors.GREEN,
        "emoji": "ℹ️ ",
        "label": "INFO"
    },
    "WARNING": {
        "color": Colors.YELLOW,
        "emoji": "⚠️ ",
        "label": "WARN"
    },
    "ERROR": {
        "color": Colors.RED,
        "emoji": "❌",
        "label": "ERROR"
    },
    "CRITICAL": {
        "color": Colors.BG_RED + Colors.WHITE + Colors.BOLD,
        "emoji": "🚨",
        "label": "CRIT"
    }
}


# ============================================================
# CUSTOM FORMATTERS
# ============================================================

class ColoredFormatter(logging.Formatter):
    """Beautiful colored formatter for console"""

    def format(self, record):
        # Get level config
        config = LEVEL_CONFIG.get(record.levelname, LEVEL_CONFIG["INFO"])

        # Format timestamp (short)
        timestamp = datetime.fromtimestamp(record.created).strftime('%H:%M:%S')

        # Format the message
        # Structure: HH:MM:SS │ EMOJI LEVEL │ module │ message
        colored_message = (
            f"{Colors.DIM}{timestamp}{Colors.RESET} "
            f"{Colors.DIM}│{Colors.RESET} "
            f"{config['color']}{config['emoji']} {config['label']:5}{Colors.RESET} "
            f"{Colors.DIM}│{Colors.RESET} "
            f"{Colors.BRIGHT_BLUE}{record.name:20}{Colors.RESET} "
            f"{Colors.DIM}│{Colors.RESET} "
            f"{record.getMessage()}"
        )

        # Add exception info if present
        if record.exc_info:
            colored_message += f"\n{Colors.RED}{self.formatException(record.exc_info)}{Colors.RESET}"

        return colored_message


class FileFormatter(logging.Formatter):
    """Clean formatter for file logs (no colors)"""

    def format(self, record):
        timestamp = datetime.fromtimestamp(record.created).strftime('%Y-%m-%d %H:%M:%S')

        message = (
            f"{timestamp} | "
            f"{record.levelname:8} | "
            f"{record.name:20} | "
            f"{record.getMessage()}"
        )

        if record.exc_info:
            message += f"\n{self.formatException(record.exc_info)}"

        return message


class JSONFormatter(logging.Formatter):
    """JSON formatter for machine-readable logs"""

    def format(self, record):
        import json

        log_data = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }

        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_data)


# ============================================================
# HANDLERS SETUP
# ============================================================

def _create_console_handler() -> logging.Handler:
    """Create colored console handler"""
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.INFO)
    handler.setFormatter(ColoredFormatter())
    return handler


def _create_file_handler() -> logging.Handler:
    """Create rotating file handler for all logs"""
    log_file = LOG_DIR / f"{datetime.now().strftime('%Y-%m-%d')}.log"

    # Rotate when file reaches MAX_LOG_SIZE
    handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=MAX_LOG_SIZE,
        backupCount=BACKUP_COUNT,
        encoding='utf-8'
    )
    handler.setLevel(logging.DEBUG)
    handler.setFormatter(FileFormatter())
    return handler


def _create_error_handler() -> logging.Handler:
    """Separate handler for errors only (easy debugging)"""
    error_file = LOG_DIR / "errors.log"

    handler = logging.handlers.RotatingFileHandler(
        error_file,
        maxBytes=MAX_LOG_SIZE,
        backupCount=3,
        encoding='utf-8'
    )
    handler.setLevel(logging.ERROR)
    handler.setFormatter(FileFormatter())
    return handler


def _create_json_handler() -> logging.Handler:
    """JSON handler for machine-readable logs (analytics)"""
    json_file = LOG_DIR / f"{datetime.now().strftime('%Y-%m-%d')}.json"

    handler = logging.handlers.RotatingFileHandler(
        json_file,
        maxBytes=MAX_LOG_SIZE,
        backupCount=BACKUP_COUNT,
        encoding='utf-8'
    )
    handler.setLevel(logging.INFO)
    handler.setFormatter(JSONFormatter())
    return handler


# ============================================================
# LOG CLEANUP
# ============================================================

def cleanup_old_logs():
    """Delete logs older than LOG_KEEP_DAYS"""
    try:
        cutoff = datetime.now() - timedelta(days=LOG_KEEP_DAYS)
        deleted_count = 0

        for log_file in LOG_DIR.glob("*.log*"):
            try:
                # Check file modification time
                mtime = datetime.fromtimestamp(log_file.stat().st_mtime)
                if mtime < cutoff:
                    log_file.unlink()
                    deleted_count += 1
            except Exception:
                pass

        for log_file in LOG_DIR.glob("*.json*"):
            try:
                mtime = datetime.fromtimestamp(log_file.stat().st_mtime)
                if mtime < cutoff:
                    log_file.unlink()
                    deleted_count += 1
            except Exception:
                pass

        if deleted_count > 0:
            print(f"🧹 Cleaned up {deleted_count} old log files")

    except Exception as e:
        print(f"Log cleanup failed: {e}")


# ============================================================
# MAIN LOGGER FACTORY
# ============================================================

# Global flag to track if root handlers are set up
_root_configured = False


def _configure_root_logger():
    """Configure root logger handlers (once)"""
    global _root_configured

    if _root_configured:
        return

    root = logging.getLogger()

    # Remove existing handlers
    for handler in root.handlers[:]:
        root.removeHandler(handler)

    # Set root level
    root.setLevel(logging.DEBUG)

    # Add handlers
    root.addHandler(_create_console_handler())
    root.addHandler(_create_file_handler())
    root.addHandler(_create_error_handler())

    # JSON handler (optional, uncomment to enable)
    # root.addHandler(_create_json_handler())

    # Cleanup old logs on startup
    cleanup_old_logs()

    _root_configured = True


def get_logger(name: str) -> logging.Logger:
    """
    Get configured logger for any module

    Usage:
        logger = get_logger("my_module")
        logger.info("Hello!")
        logger.error("Something failed")
    """
    # Ensure root logger is configured
    _configure_root_logger()

    # Get logger
    logger = logging.getLogger(name)

    # Set level from environment
    level_map = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL
    }

    logger.setLevel(level_map.get(LOG_LEVEL, logging.INFO))

    # Prevent duplicate handlers
    logger.propagate = True

    return logger


# ============================================================
# UTILITY FUNCTIONS
# ============================================================

def log_separator(logger: logging.Logger, char: str = "─", length: int = 60):
    """Log a separator line"""
    logger.info(char * length)


def log_header(logger: logging.Logger, title: str, char: str = "═"):
    """Log a header with title"""
    logger.info(char * 60)
    logger.info(f"  {title}")
    logger.info(char * 60)


def log_dict(logger: logging.Logger, data: dict, title: str = "Data"):
    """Pretty log a dictionary"""
    logger.info(f"📊 {title}:")
    for key, value in data.items():
        logger.info(f"   • {key}: {value}")


def log_success(logger: logging.Logger, message: str):
    """Log success with green checkmark"""
    logger.info(f"✅ {message}")


def log_failure(logger: logging.Logger, message: str):
    """Log failure with red X"""
    logger.error(f"❌ {message}")


def log_warning_box(logger: logging.Logger, message: str):
    """Log warning in a box"""
    logger.warning("┌─────────────────────────────────────────┐")
    logger.warning(f"│ ⚠️  {message[:35]:35}   │")
    logger.warning("└─────────────────────────────────────────┘")


def get_log_stats() -> dict:
    """Get logging statistics"""
    try:
        total_size = 0
        file_count = 0

        for log_file in LOG_DIR.glob("*.log*"):
            total_size += log_file.stat().st_size
            file_count += 1

        for log_file in LOG_DIR.glob("*.json*"):
            total_size += log_file.stat().st_size
            file_count += 1

        return {
            "log_dir": str(LOG_DIR.absolute()),
            "total_files": file_count,
            "total_size_kb": round(total_size / 1024, 2),
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "log_level": LOG_LEVEL,
            "keep_days": LOG_KEEP_DAYS
        }

    except Exception as e:
        return {"error": str(e)}


# ============================================================
# STANDALONE TESTING
# ============================================================

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("LOGGER - STANDALONE TEST")
    print("=" * 60 + "\n")

    # Test different loggers
    test_logger = get_logger("test_module")

    # Test all log levels
    test_logger.debug("This is a DEBUG message")
    test_logger.info("This is an INFO message")
    test_logger.warning("This is a WARNING message")
    test_logger.error("This is an ERROR message")
    test_logger.critical("This is a CRITICAL message")

    # Test utility functions
    print()
    log_header(test_logger, "SECTION HEADER TEST")

    log_success(test_logger, "Operation completed successfully")
    log_failure(test_logger, "Something went wrong")

    log_dict(test_logger, {
        "user": "Rahul",
        "action": "post_created",
        "duration": "2.5s",
        "status": "success"
    }, title="Post Details")

    log_separator(test_logger)
    log_warning_box(test_logger, "Budget limit reached!")

    # Test exception logging
    try:
        raise ValueError("This is a test exception")
    except Exception:
        test_logger.exception("An exception occurred:")

    # Show log stats
    print()
    print("📊 Log Statistics:")
    stats = get_log_stats()
    for key, value in stats.items():
        print(f"   {key}: {value}")

    print(f"\n✅ Test complete! Check '{LOG_DIR}' folder for log files")