import logging
import sys
from pathlib import Path

# Create logs directory if it doesn't exist
log_dir = Path(__file__).parent.parent.parent / "logs"
log_dir.mkdir(exist_ok=True)

# Main application logger
logger = logging.getLogger("ai_app")
logger.setLevel(logging.DEBUG)

# Create formatters
formatter = logging.Formatter(
    "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

# File handler
file_handler = logging.FileHandler(log_dir / "app.log")
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(formatter)

# Console handler
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(formatter)

# Add handlers
if not logger.handlers:
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

def get_logger(name: str) -> logging.Logger:
    """Get a child logger with the given name."""
    return logger.getChild(name)
