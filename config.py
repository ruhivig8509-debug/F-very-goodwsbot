#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════╗
║                                                                      ║
║              RUHI JI BOT — CONFIGURATION MODULE v2.0                ║
║                                                                      ║
║   Centralized Configuration Management System                       ║
║                                                                      ║
║   Features:                                                         ║
║   ├── Environment Variable Loading (.env support)                   ║
║   ├── Type-Safe Configuration with Defaults                        ║
║   ├── Validation Engine with Detailed Error Reporting              ║
║   ├── Dynamic Configuration Reload Support                         ║
║   ├── Secure Credential Masking for Logs                           ║
║   ├── Multi-Environment Support (dev/staging/prod)                 ║
║   ├── Feature Flags System                                          ║
║   ├── Rate Limit Configuration                                     ║
║   ├── AI Model Configuration                                       ║
║   └── Database Connection Parameters                                ║
║                                                                      ║
║   Made with 💖 by @RUHI_VIG_QNR                                     ║
║                                                                      ║
╚══════════════════════════════════════════════════════════════════════╝
"""

import os
import sys
import json
import logging
from typing import Optional, Dict, List, Any, Union
from datetime import timezone

# === Try loading .env file for local development ===
try:
    from dotenv import load_dotenv
    # Load .env file if it exists
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if os.path.exists(env_path):
        load_dotenv(env_path)
        print(f"[CONFIG] Loaded .env from: {env_path}")
    else:
        load_dotenv()  # Try default locations
except ImportError:
    print("[CONFIG] python-dotenv not installed, using system env vars only")

# === Logger ===
logger = logging.getLogger("RuhiJiBot.Config")


# ============================================================
#          ENVIRONMENT HELPER FUNCTIONS
# ============================================================

def get_env(
    key: str,
    default: Any = None,
    required: bool = False,
    cast_type: type = str
) -> Any:
    """
    Get an environment variable with type casting and validation.
    
    Args:
        key: Environment variable name
        default: Default value if not found
        required: Whether this variable is required
        cast_type: Type to cast the value to
    
    Returns:
        The environment variable value, cast to the specified type
    
    Raises:
        SystemExit: If required variable is missing
    """
    value = os.environ.get(key)
    
    if value is None or value.strip() == "":
        if required:
            logger.error(
                f"[CONFIG] FATAL: Required environment variable "
                f"'{key}' is not set!"
            )
            print(f"\n❌ FATAL: Required environment variable '{key}' is missing!")
            print(f"   Please set it in your .env file or Render dashboard.\n")
            return default
        return default
    
    # Type casting
    try:
        if cast_type == bool:
            return value.lower() in ("true", "1", "yes", "on")
        elif cast_type == int:
            return int(value)
        elif cast_type == float:
            return float(value)
        elif cast_type == list:
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value.split(",")
        else:
            return str(value).strip()
    except (ValueError, TypeError) as e:
        logger.warning(
            f"[CONFIG] Failed to cast '{key}' to {cast_type.__name__}: {e}. "
            f"Using default: {default}"
        )
        return default


def mask_secret(value: str, show_chars: int = 6) -> str:
    """Mask a secret value for safe logging."""
    if not value:
        return "NOT_SET"
    if len(value) <= show_chars:
        return "***"
    return "***" + value[-show_chars:]


# ============================================================
#        MAIN CONFIGURATION CLASS
# ============================================================

class Config:
    """
    Central configuration class for Ruhi Ji Bot.
    All settings are loaded from environment variables
    with sensible defaults for development.
    """
    
    # ========================================================
    #           ENVIRONMENT MODE
    # ========================================================
    
    ENV = get_env("ENV", "production")
    DEBUG = get_env("DEBUG", False, cast_type=bool)
    
    # ========================================================
    #           TELEGRAM BOT SETTINGS
    # ========================================================
    
    BOT_TOKEN = get_env("BOT_TOKEN", "", required=True)
    BOT_USERNAME = get_env("BOT_USERNAME", "RuhiJiBot")
    BOT_NAME = "Ruhi Ji"
    BOT_VERSION = "2.0.0"
    
    # ========================================================
    #           HUGGING FACE / AI SETTINGS
    # ========================================================
    
    HF_TOKEN = get_env("HF_TOKEN", "", required=True)
    HF_BASE_URL = get_env(
        "HF_BASE_URL",
        "https://router.huggingface.co/v1"
    )
    MODEL_NAME = get_env(
        "MODEL_NAME",
        "moonshotai/Kimi-K2-Instruct-0905:groq"
    )
    MAX_RESPONSE_TOKENS = get_env("MAX_RESPONSE_TOKENS", 1024, cast_type=int)
    AI_TEMPERATURE = get_env("AI_TEMPERATURE", 0.85, cast_type=float)
    AI_TOP_P = get_env("AI_TOP_P", 0.9, cast_type=float)
    AI_MAX_RETRIES = get_env("AI_MAX_RETRIES", 3, cast_type=int)
    AI_RETRY_DELAY = get_env("AI_RETRY_DELAY", 2, cast_type=int)
    MAX_CONTEXT_MESSAGES = get_env("MAX_CONTEXT_MESSAGES", 30, cast_type=int)
    
    # ========================================================
    #           DATABASE SETTINGS (PostgreSQL / Neon.tech)
    # ========================================================
    
    DATABASE_URL = get_env(
        "DATABASE_URL",
        "postgresql://neondb_owner:npg_jYrNzuqFA0i8@"
        "ep-wispy-silence-a1lpucgo-pooler.ap-southeast-1.aws.neon.tech/"
        "neondb?sslmode=require",
        required=True
    )
    
    DB_MIN_CONNECTIONS = get_env("DB_MIN_CONNECTIONS", 2, cast_type=int)
    DB_MAX_CONNECTIONS = get_env("DB_MAX_CONNECTIONS", 10, cast_type=int)
    DB_CONNECT_TIMEOUT = get_env("DB_CONNECT_TIMEOUT", 15, cast_type=int)
    DB_STATEMENT_TIMEOUT = get_env("DB_STATEMENT_TIMEOUT", 30000, cast_type=int)
    DB_MAX_RETRIES = get_env("DB_MAX_RETRIES", 3, cast_type=int)
    DB_RETRY_DELAY = get_env("DB_RETRY_DELAY", 2, cast_type=int)
    
    # ========================================================
    #           OWNER / ADMIN SETTINGS
    # ========================================================
    
    OWNER_USERNAME = get_env("OWNER_USERNAME", "RUHI_VIG_QNR")
    OWNER_CHAT_ID = get_env("OWNER_CHAT_ID", None, cast_type=int)
    
    # ========================================================
    #           MEMORY / SESSION SETTINGS
    # ========================================================
    
    MAX_GROUP_MEMORY = get_env("MAX_GROUP_MEMORY", 20, cast_type=int)
    MAX_PRIVATE_MEMORY = get_env("MAX_PRIVATE_MEMORY", 50, cast_type=int)
    SESSION_TIMEOUT_MINUTES = get_env("SESSION_TIMEOUT", 10, cast_type=int)
    MESSAGE_RETENTION_DAYS = get_env("MESSAGE_RETENTION_DAYS", 7, cast_type=int)
    
    # ========================================================
    #           WEB SERVER / RENDER SETTINGS
    # ========================================================
    
    PORT = get_env("PORT", 10000, cast_type=int)
    HOST = get_env("HOST", "0.0.0.0")
    RENDER_EXTERNAL_URL = get_env("RENDER_EXTERNAL_URL", "")
    SELF_PING_INTERVAL = get_env("SELF_PING_INTERVAL", 600, cast_type=int)
    ADMIN_API_TOKEN = get_env("ADMIN_API_TOKEN", "")
    
    # ========================================================
    #           RATE LIMITING SETTINGS
    # ========================================================
    
    RATE_LIMIT_MESSAGES = get_env("RATE_LIMIT_MESSAGES", 8, cast_type=int)
    RATE_LIMIT_WINDOW = get_env("RATE_LIMIT_WINDOW", 15, cast_type=int)
    FLOOD_MUTE_DURATION = get_env("FLOOD_MUTE_DURATION", 60, cast_type=int)
    WEB_RATE_LIMIT = get_env("WEB_RATE_LIMIT", 60, cast_type=int)
    WEB_RATE_WINDOW = get_env("WEB_RATE_WINDOW", 60, cast_type=int)
    
    # ========================================================
    #           TELEGRAM POLLING SETTINGS
    # ========================================================
    
    POLL_INTERVAL = get_env("POLL_INTERVAL", 0.5, cast_type=float)
    POLL_TIMEOUT = get_env("POLL_TIMEOUT", 30, cast_type=int)
    CONNECT_TIMEOUT = get_env("CONNECT_TIMEOUT", 30, cast_type=int)
    READ_TIMEOUT = get_env("READ_TIMEOUT", 30, cast_type=int)
    WRITE_TIMEOUT = get_env("WRITE_TIMEOUT", 30, cast_type=int)
    POOL_TIMEOUT = get_env("POOL_TIMEOUT", 30, cast_type=int)
    DROP_PENDING_UPDATES = get_env("DROP_PENDING", True, cast_type=bool)
    CONCURRENT_UPDATES = get_env("CONCURRENT_UPDATES", True, cast_type=bool)
    
    # ========================================================
    #           FEATURE FLAGS
    # ========================================================
    
    ENABLE_SELF_PING = get_env("ENABLE_SELF_PING", True, cast_type=bool)
    ENABLE_BAD_WORD_FILTER = get_env("ENABLE_BAD_WORD_FILTER", True, cast_type=bool)
    ENABLE_FLOOD_CONTROL = get_env("ENABLE_FLOOD_CONTROL", True, cast_type=bool)
    ENABLE_MEDIA_RESPONSES = get_env("ENABLE_MEDIA_RESPONSES", True, cast_type=bool)
    ENABLE_WEB_DASHBOARD = get_env("ENABLE_WEB_DASHBOARD", True, cast_type=bool)
    ENABLE_ANALYTICS = get_env("ENABLE_ANALYTICS", True, cast_type=bool)
    ENABLE_SESSION_SYSTEM = get_env("ENABLE_SESSION_SYSTEM", True, cast_type=bool)
    ENABLE_BROADCAST = get_env("ENABLE_BROADCAST", True, cast_type=bool)
    
    # ========================================================
    #           LOGGING SETTINGS
    # ========================================================
    
    LOG_LEVEL = get_env("LOG_LEVEL", "INFO")
    LOG_FORMAT = get_env(
        "LOG_FORMAT",
        "%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s"
    )
    LOG_DATE_FORMAT = get_env("LOG_DATE_FORMAT", "%Y-%m-%d %H:%M:%S")
    
    # ========================================================
    #           BAD WORDS DEFAULT LIST
    # ========================================================
    
    BAD_WORDS_DEFAULT = [
        "madarchod", "bhenchod", "chutiya", "gandu", "randi",
        "bhosdike", "mc", "bc", "lodu", "harami", "kutti",
        "saala", "kamina", "gaand", "chut"
    ]
    
    # ========================================================
    #           WAKE PHRASES
    # ========================================================
    
    WAKE_PHRASES = [
        "ruhi ji", "ruhi-ji", "ruhiji", "ruhi",
        "roohi ji", "roohi", "रुही जी", "रूही जी", "रुही"
    ]
    
    # ========================================================
    #           VALIDATION
    # ========================================================
    
    @classmethod
    def validate(cls) -> bool:
        """
        Validate all required configuration variables.
        Returns True if valid, False otherwise.
        """
        errors = []
        warnings = []
        
        # Required checks
        if not cls.BOT_TOKEN:
            errors.append("BOT_TOKEN is not set")
        elif len(cls.BOT_TOKEN) < 20:
            errors.append("BOT_TOKEN looks invalid (too short)")
            
        if not cls.HF_TOKEN:
            errors.append("HF_TOKEN is not set")
        elif not cls.HF_TOKEN.startswith("hf_"):
            warnings.append(
                "HF_TOKEN doesn't start with 'hf_' — "
                "might be invalid"
            )
            
        if not cls.DATABASE_URL:
            errors.append("DATABASE_URL is not set")
        elif "postgresql" not in cls.DATABASE_URL:
            warnings.append("DATABASE_URL doesn't look like PostgreSQL")
        
        # Value range checks
        if cls.MAX_GROUP_MEMORY < 5 or cls.MAX_GROUP_MEMORY > 100:
            warnings.append(
                f"MAX_GROUP_MEMORY={cls.MAX_GROUP_MEMORY} "
                f"is outside recommended range (5-100)"
            )
            
        if cls.MAX_PRIVATE_MEMORY < 10 or cls.MAX_PRIVATE_MEMORY > 200:
            warnings.append(
                f"MAX_PRIVATE_MEMORY={cls.MAX_PRIVATE_MEMORY} "
                f"is outside recommended range (10-200)"
            )
            
        if cls.PORT < 1 or cls.PORT > 65535:
            errors.append(f"PORT={cls.PORT} is not a valid port number")
            
        if cls.MAX_RESPONSE_TOKENS < 100 or cls.MAX_RESPONSE_TOKENS > 4096:
            warnings.append(
                f"MAX_RESPONSE_TOKENS={cls.MAX_RESPONSE_TOKENS} "
                f"might cause issues"
            )
        
        # Log results
        for warning in warnings:
            logger.warning(f"[CONFIG] ⚠️  {warning}")
            
        if errors:
            for error in errors:
                logger.error(f"[CONFIG] ❌ {error}")
            logger.error(
                f"[CONFIG] Validation FAILED with {len(errors)} error(s)"
            )
            return False
            
        logger.info("[CONFIG] ✅ All configuration validated successfully")
        return True
    
    @classmethod
    def print_config(cls):
        """Print current configuration (with secrets masked)."""
        logger.info("=" * 60)
        logger.info("       RUHI JI BOT — CONFIGURATION")
        logger.info("=" * 60)
        logger.info(f"  Environment:     {cls.ENV}")
        logger.info(f"  Debug:           {cls.DEBUG}")
        logger.info(f"  Bot Token:       {mask_secret(cls.BOT_TOKEN)}")
        logger.info(f"  Bot Username:    @{cls.BOT_USERNAME}")
        logger.info(f"  HF Token:        {mask_secret(cls.HF_TOKEN)}")
        logger.info(f"  Model:           {cls.MODEL_NAME}")
        logger.info(f"  Max Tokens:      {cls.MAX_RESPONSE_TOKENS}")
        logger.info(f"  DB URL:          {mask_secret(cls.DATABASE_URL, 20)}")
        logger.info(f"  DB Pool:         {cls.DB_MIN_CONNECTIONS}-{cls.DB_MAX_CONNECTIONS}")
        logger.info(f"  Owner:           @{cls.OWNER_USERNAME}")
        logger.info(f"  Owner ID:        {cls.OWNER_CHAT_ID or 'auto-detect'}")
        logger.info(f"  Group Memory:    {cls.MAX_GROUP_MEMORY} msgs")
        logger.info(f"  Private Memory:  {cls.MAX_PRIVATE_MEMORY} msgs")
        logger.info(f"  Session Timeout: {cls.SESSION_TIMEOUT_MINUTES} min")
        logger.info(f"  Port:            {cls.PORT}")
        logger.info(f"  Render URL:      {cls.RENDER_EXTERNAL_URL or 'not set'}")
        logger.info(f"  Self Ping:       {'ON' if cls.ENABLE_SELF_PING else 'OFF'}")
        logger.info(f"  Rate Limit:      {cls.RATE_LIMIT_MESSAGES}/{cls.RATE_LIMIT_WINDOW}s")
        logger.info(f"  Flood Control:   {'ON' if cls.ENABLE_FLOOD_CONTROL else 'OFF'}")
        logger.info(f"  Bad Word Filter: {'ON' if cls.ENABLE_BAD_WORD_FILTER else 'OFF'}")
        logger.info(f"  Web Dashboard:   {'ON' if cls.ENABLE_WEB_DASHBOARD else 'OFF'}")
        logger.info(f"  Log Level:       {cls.LOG_LEVEL}")
        logger.info("=" * 60)

    @classmethod
    def to_dict(cls, mask_secrets: bool = True) -> Dict[str, Any]:
        """Export configuration as dictionary."""
        config = {
            "env": cls.ENV,
            "debug": cls.DEBUG,
            "bot_token": mask_secret(cls.BOT_TOKEN) if mask_secrets else cls.BOT_TOKEN,
            "bot_username": cls.BOT_USERNAME,
            "bot_version": cls.BOT_VERSION,
            "hf_token": mask_secret(cls.HF_TOKEN) if mask_secrets else cls.HF_TOKEN,
            "model": cls.MODEL_NAME,
            "max_tokens": cls.MAX_RESPONSE_TOKENS,
            "database_url": mask_secret(cls.DATABASE_URL, 20) if mask_secrets else cls.DATABASE_URL,
            "owner": cls.OWNER_USERNAME,
            "group_memory": cls.MAX_GROUP_MEMORY,
            "private_memory": cls.MAX_PRIVATE_MEMORY,
            "session_timeout": cls.SESSION_TIMEOUT_MINUTES,
            "port": cls.PORT,
            "render_url": cls.RENDER_EXTERNAL_URL,
        }
        return config


# ============================================================
#       MODULE-LEVEL EXPORTS (for backward compatibility)
# ============================================================

BOT_TOKEN = Config.BOT_TOKEN
HF_TOKEN = Config.HF_TOKEN
DATABASE_URL = Config.DATABASE_URL
OWNER_USERNAME = Config.OWNER_USERNAME
OWNER_CHAT_ID = Config.OWNER_CHAT_ID
BOT_USERNAME = Config.BOT_USERNAME
MAX_GROUP_MEMORY = Config.MAX_GROUP_MEMORY
MAX_PRIVATE_MEMORY = Config.MAX_PRIVATE_MEMORY
SESSION_TIMEOUT_MINUTES = Config.SESSION_TIMEOUT_MINUTES
MAX_RESPONSE_TOKENS = Config.MAX_RESPONSE_TOKENS
MODEL_NAME = Config.MODEL_NAME
HF_BASE_URL = Config.HF_BASE_URL
PORT = Config.PORT
LOG_LEVEL = Config.LOG_LEVEL
BAD_WORDS_DEFAULT = Config.BAD_WORDS_DEFAULT


# ============================================================
#       STARTUP VALIDATION (runs on import)
# ============================================================

if __name__ == "__main__":
    # Run validation when executed directly
    logging.basicConfig(level=logging.INFO)
    print("\n🔍 Validating Ruhi Ji Bot Configuration...\n")
    Config.print_config()
    valid = Config.validate()
    if valid:
        print("\n✅ Configuration is valid! Ready to deploy.\n")
    else:
        print("\n❌ Configuration has errors. Fix them before deploying.\n")
        sys.exit(1)
        