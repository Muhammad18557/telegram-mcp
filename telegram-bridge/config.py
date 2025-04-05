"""
Configuration management for the Telegram bridge.

Loads environment variables and provides configuration settings.
"""

import os
import logging
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
load_dotenv()

# Directory paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STORE_DIR = os.path.join(BASE_DIR, "store")
os.makedirs(STORE_DIR, exist_ok=True)

# Session and database files
SESSION_FILE = os.path.join(STORE_DIR, "telegram_session")
DB_PATH = os.path.join(STORE_DIR, "messages.db")

# API credentials
API_ID = os.getenv("TELEGRAM_API_ID")
API_HASH = os.getenv("TELEGRAM_API_HASH")

# Server configuration
HTTP_PORT = int(os.getenv("HTTP_PORT", "8081"))
HTTP_HOST = os.getenv("HTTP_HOST", "")

# Logging configuration
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# Initialize logging
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format=LOG_FORMAT,
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Validate required settings
if not API_ID or not API_HASH:
    logger.error(
        "TELEGRAM_API_ID and TELEGRAM_API_HASH environment variables must be set"
    )
    logger.error("Get them from https://my.telegram.org/auth")
    raise ValueError("Missing API credentials")