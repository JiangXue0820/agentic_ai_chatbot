import logging
import re
import sys
import io
from pathlib import Path
from datetime import datetime

EMAIL_RE = re.compile(r"([A-Za-z0-9._%+-]+)@([A-Za-z0-9.-]+)\.[A-Za-z]{2,}")
TOKEN_RE = re.compile(r"(Bearer\s+)?([A-Za-z0-9-_]{20,})")

class MaskPIIFilter(logging.Filter):
    """Filter to mask PII (emails, tokens) in log messages."""
    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            msg = EMAIL_RE.sub(lambda m: f"{m.group(1)[:2]}***@***", record.msg)
            msg = TOKEN_RE.sub("***TOKEN***", msg)
            record.msg = msg
        return True

def configure_logging():
    """
    Configure logging with both console and file output.
    
    Features:
    - Console output for real-time monitoring
    - File output for persistent logs (./logs/agent.log)
    - Daily rotating file with timestamp
    - PII masking for security
    - UTF-8 encoding for international characters
    - Windows console UTF-8 encoding support
    """
    # Set console output to UTF-8 encoding (especially for Windows)
    if sys.platform == "win32":
        try:
            # Wrap stdout and stderr with UTF-8 encoding
            if hasattr(sys.stdout, 'buffer'):
                sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
            if hasattr(sys.stderr, 'buffer'):
                sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
        except Exception:
            # If wrapping fails, continue with default encoding
            pass
    
    # Create logs directory
    log_dir = Path("./logs")
    log_dir.mkdir(exist_ok=True)
    
    # Log file with date
    log_file = log_dir / f"agent_{datetime.now().strftime('%Y%m%d')}.log"
    
    # Define log format
    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s:%(funcName)s:%(lineno)d - %(message)s"
    )
    
    # Console handler (for terminal output)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    console_handler.addFilter(MaskPIIFilter())
    
    # File handler (for persistent logs)
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)  # More detailed in file
    file_handler.setFormatter(formatter)
    file_handler.addFilter(MaskPIIFilter())
    
    # Configure root logger
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    
    # Remove existing handlers to avoid duplicates
    logger.handlers.clear()
    
    # Add our handlers
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    
    # Log startup message
    logger.info(f"Logging configured - Console: INFO, File: DEBUG ({log_file})")
