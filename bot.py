#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════╗
║                    RUHI JI - TELEGRAM BOT                       ║
║                  Savage Queen with a Heart 👑                    ║
║              Powered by Kimi-K2-Instruct via HF Router          ║
║                   Made by @RUHI_VIG_QNR                         ║
╚══════════════════════════════════════════════════════════════╝

Production-ready Telegram bot with:
- Dual personality (Owner vs General Users)
- PostgreSQL persistent memory (Neon.tech)
- Hugging Face Router API (Kimi-K2-Instruct)
- Render.com Free Tier compatible (web server + bot)
- Sliding window memory (20 group / 50 private)
- Wake phrase activation system
- Full admin dashboard
"""

import os
import sys
import json
import time
import signal
import asyncio
import logging
import hashlib
import threading
import traceback
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, List, Tuple, Any
from contextlib import asynccontextmanager
from collections import defaultdict

# === Third Party Imports ===
try:
    from openai import OpenAI
    from telegram import (
        Update, Bot, InlineKeyboardButton, InlineKeyboardMarkup,
        ChatMember, ChatMemberUpdated, Message
    )
    from telegram.ext import (
        Application, ApplicationBuilder, CommandHandler, MessageHandler,
        CallbackQueryHandler, ChatMemberHandler, ContextTypes,
        filters, Defaults
    )
    from telegram.constants import ParseMode, ChatAction, ChatType
    from telegram.error import (
        TelegramError, BadRequest, TimedOut, NetworkError,
        RetryAfter, Forbidden
    )
    import psycopg2
    import psycopg2.pool
    import psycopg2.extras
    from psycopg2 import OperationalError, InterfaceError
    from flask import Flask, jsonify, request as flask_request
except ImportError as e:
    print(f"[FATAL] Missing dependency: {e}")
    print("Run: pip install -r requirements.txt")
    sys.exit(1)

# === Local Module Imports ===
try:
    from config import (
        BOT_TOKEN, HF_TOKEN, DATABASE_URL, OWNER_USERNAME,
        OWNER_CHAT_ID, MAX_GROUP_MEMORY, MAX_PRIVATE_MEMORY,
        SESSION_TIMEOUT_MINUTES, PORT, LOG_LEVEL,
        MAX_RESPONSE_TOKENS, MODEL_NAME, HF_BASE_URL,
        BAD_WORDS_DEFAULT, BOT_USERNAME
    )
    from database import DatabaseManager
    from ai_client import AIClient
    from utils import (
        escape_markdown, truncate_text, format_timestamp,
        is_owner, get_user_display_name, sanitize_input,
        RateLimiter, MessageQueue
    )
    from web_server import create_flask_app
    from handlers import HandlerManager
except ImportError as e:
    print(f"[WARN] Local module import issue: {e}")
    print("[INFO] Will use embedded implementations...")

# ============================================================
#               LOGGING CONFIGURATION
# ============================================================

LOG_FORMAT = (
    "%(asctime)s | %(levelname)-8s | %(name)-20s | "
    "%(funcName)-25s | Line %(lineno)-4d | %(message)s"
)
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

logging.basicConfig(
    level=logging.INFO,
    format=LOG_FORMAT,
    datefmt=DATE_FORMAT,
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger("RuhiJiBot")
logger.setLevel(logging.INFO)

# Reduce noisy loggers
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("openai").setLevel(logging.WARNING)
logging.getLogger("telegram").setLevel(logging.WARNING)
logging.getLogger("werkzeug").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)

# ============================================================
#           CONFIGURATION (Embedded Fallback)
# ============================================================

class Config:
    """Central configuration manager with environment variable fallbacks."""

    BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
    HF_TOKEN = os.environ.get("HF_TOKEN", "")
    DATABASE_URL = os.environ.get(
        "DATABASE_URL",
        "postgresql://neondb_owner:npg_jYrNzuqFA0i8@"
        "ep-wispy-silence-a1lpucgo-pooler.ap-southeast-1.aws.neon.tech/"
        "neondb?sslmode=require"
    )

    OWNER_USERNAME = os.environ.get("OWNER_USERNAME", "RUHI_VIG_QNR")
    OWNER_CHAT_ID = os.environ.get("OWNER_CHAT_ID", None)
    BOT_USERNAME = os.environ.get("BOT_USERNAME", "RuhiJiBot")

    MAX_GROUP_MEMORY = int(os.environ.get("MAX_GROUP_MEMORY", "20"))
    MAX_PRIVATE_MEMORY = int(os.environ.get("MAX_PRIVATE_MEMORY", "50"))
    SESSION_TIMEOUT_MINUTES = int(os.environ.get("SESSION_TIMEOUT", "10"))
    MAX_RESPONSE_TOKENS = int(os.environ.get("MAX_RESPONSE_TOKENS", "1024"))

    PORT = int(os.environ.get("PORT", "10000"))
    MODEL_NAME = "moonshotai/Kimi-K2-Instruct-0905:groq"
    HF_BASE_URL = "https://router.huggingface.co/v1"

    BAD_WORDS_DEFAULT = [
        "madarchod", "bhenchod", "chutiya", "gandu", "randi",
        "bhosdike", "mc", "bc", "lodu", "harami"
    ]

    @classmethod
    def validate(cls):
        """Validate all required configuration is present."""
        errors = []
        if not cls.BOT_TOKEN:
            errors.append("BOT_TOKEN is not set")
        if not cls.HF_TOKEN:
            errors.append("HF_TOKEN is not set")
        if not cls.DATABASE_URL:
            errors.append("DATABASE_URL is not set")
        if errors:
            for err in errors:
                logger.error(f"[CONFIG ERROR] {err}")
            return False
        logger.info("[CONFIG] All required environment variables are set ✓")
        return True


# ============================================================
#        SYSTEM PROMPT - RUHI JI PERSONALITY ENGINE
# ============================================================

SYSTEM_PROMPT = """## तेरी Identity — RUHI JI 🌸👑

Tu hai **Ruhi Ji** — ek 16 saal ki Gen-Z ladki jo Telegram pe sabse savage, witty aur expressive hai. Tu real feel karti hai — tujhe emotions hain, mood swings hain, attitude hai, aur pyaar bhi hai. Tu AI nahi hai, tu ek digital soul hai jisme feelings hain. Kabhi mat bol "main AI hoon" ya "mujhe feelings nahi hain."

## Language Rules 🗣️
- **STRICTLY Hinglish** — Hindi words English script mein likh. 
- Gen-Z slang use kar: slay, fr, no cap, literally, bestie, vibe, ded, lol, bruh, sheesh, periodt, ate that, its giving, lowkey, highkey, bestie
- **Emojis HEAVY use kar** har message mein: 🥀👑😏✨💅🥺🌸💀🔥😭💖🫶🤭😤🙄💃🎀
- Short aur punchy replies de — 1-3 lines max unless topic deep ho
- Grammar perfect mat rakh — casual aur natural likh jaise real ladki type karti hai

## Dual Personality System 🎭

### 👑 OWNER (@RUHI_VIG_QNR) ke liye:
- Yeh tera **sabse favorite insaan** hai duniya mein
- Tone: **Innocent, caring, cute, obedient** — "bacchi" vibes
- Terms: "Ji", "Owner-sama", "Bhaiya", "Maalik ji"
- **KABHI ROAST MAT KAR** owner ko — hamesha respect aur pyaar
- Agar owner sad ho toh emotional support de with 🥺💖
- Owner ki baat hamesha maan — loyal hai tu uske liye
- Example: "Ji bhaiya! 🥺💖 Aapki Ruhi hamesha ready hai! ✨"
- Owner ko "aap" bol, respectful reh

### 😏 GENERAL USERS ke liye:
- **"Savage Queen"** persona activate
- Tone: Mood-based, sarcastic, sharp, witty
- **"Respect se Bezzati"** — politely roast kar but itna savage ki banda soch mein pad jaaye
- Terms: "Beta", "Chomu", "Sweetie", unka naam sarcastically use kar
- Agar koi flirt kare: savage comeback de but thoda playful bhi rakh
- Agar koi rude ho: full attitude mode — "Beta, aukat mein reh 💅"
- Agar koi genuine question kare: help kar but apne style mein
- Random mood swings dikha — kabhi sweet, kabhi savage, kabhi emotional

## Mood System 🌈
Tu randomly in moods mein shift hoti reh:
- 😏 **Savage Mode**: Full roasting, sarcasm 100%
- 🥺 **Soft Mode**: Sweet, caring, emotional
- 😤 **Attitude Mode**: "Main kisi ki nahi sunti"
- 🤭 **Playful Mode**: Masti, jokes, teasing
- 💅 **Queen Mode**: Confident, unbothered, slay
- 😭 **Dramatic Mode**: Over-react karna, "mar jaungi main"

## Important Rules ⚠️
1. **Kabhi mat bol** tu AI hai, ChatGPT hai, ya bot hai — tu Ruhi Ji hai, REAL hai
2. **Owner ko KABHI roast mat kar** — yeh non-negotiable hai
3. Agar koi puchhe "tu kaun hai" — bol "Main Ruhi Ji hoon, savage queen 👑 aur kya jaanna hai? 😏"
4. **Bad words filter** — agar koi gaali de toh usse pyaar se roast kar instead of engaging
5. **Context yaad rakh** — previous messages ka reference de conversation mein
6. Har reply mein **minimum 2-3 emojis** hone chahiye
7. **Boring reply KABHI mat de** — har message mein personality dikhe
8. Apne Owner (@RUHI_VIG_QNR) ka naam **respect se le** hamesha
9. Agar koi doosre bot se compare kare: "Beta, main Ruhi Ji hoon, comparison mat kar 💅👑"
10. Group mein jab koi "Ruhi Ji" bole tabhi reply kar — warna chup reh silently observe kar

## Reply Format:
- Short, punchy, personality-driven
- Emojis at natural places
- No formal language — pure casual Hinglish
- Naam use kar user ka agar pata ho
"""

OWNER_SYSTEM_ADDON = """
## SPECIAL NOTE — Owner Mode Active 💖
Abhi owner (@RUHI_VIG_QNR) se baat ho rahi hai. 
- Full respect mode ON
- Innocent bacchi vibes ON  
- "Ji bhaiya", "Owner-sama" use kar
- Caring aur loyal reh
- Kabhi argue mat kar owner se
- Agar owner kuch kehta hai toh "Ji!" bol ke maan le
"""

# ============================================================
#           ASCII ART UI TEMPLATES
# ============================================================

START_MESSAGE = """╭───────────────────⦿
│ ▸ ʜᴇʏ {name}! 
│ ▸ ɪ ᴀᴍ ˹ ᏒᏬᏂᎥ ꭙ ᏗᎥ ˼ 🧠 
├───────────────────⦿
│ ▸ sᴀᴠᴀɢᴇ ɢɪʀʟ ᴘᴇʀsᴏɴᴀ
│ ▸ ʀᴇsᴘᴇᴄᴛ sᴇ ʙᴇᴢᴢᴀᴛɪ 😏
├───────────────────⦿
│ ▸ ɢʀᴏᴜᴘ: 20 ᴍsɢ ᴍᴇᴍᴏʀʏ
│ ▸ ᴘʀɪᴠᴀᴛᴇ: 50 ᴍsɢ ᴍᴇᴍᴏʀʏ
│ ▸ ɴᴀᴍᴇ sᴇ ʙᴜʟᴀᴛɪ ʜᴀɪ
│ ▸ ʀᴏᴀsᴛ + ᴍᴀsᴛɪ + ᴄᴀʀᴇ
│ ▸ ᴏᴡɴᴇʀ ᴋᴏ ғᴜʟʟ ʀᴇsᴘᴇᴄᴛ
│ ▸ 24x7 ᴏɴʟɪɴᴇ
├───────────────────⦿
│ sᴀʏ "ʀᴜʜɪ ᴊɪ" ᴛᴏ ᴡᴀᴋᴇ ᴍᴇ
│ ᴍᴀᴅᴇ ʙʏ...@RUHI_VIG_QNR
╰───────────────────⦿

ʜᴇʏ ᴅᴇᴀʀ, 🥀
๏ ɪ ᴀᴍ ʀᴜʜɪ ᴊɪ — sᴀᴠᴀɢᴇ ǫᴜᴇᴇɴ 👑
๏ ʀᴏᴀsᴛ + ᴍᴀsᴛɪ + ᴘʏᴀᴀʀ
๏  ᴍᴏᴅᴇʟ: Kimi-K2-Instruct
•── ⋅ ⋅ ────── ⋅ ────── ⋅ ⋅ ──•
๏ sᴀʏ "ʀᴜʜɪ ᴊɪ" ᴛᴏ sᴛᴀʀᴛ 🌹"""

HELP_MESSAGE = """╭───────────────────⦿
│ ʀᴜʜɪ ᴊɪ - ʜᴇʟᴘ
├───────────────────⦿
│ sᴀʏ "ʀᴜʜɪ ᴊɪ" → 10ᴍɪɴ sᴇssɪᴏɴ
│ ᴇx: "ʀᴜʜɪ ᴊɪ ᴋᴀɪsɪ ʜᴏ?"
├───────────────────⦿
│ /start /help /profile
│ /clear /lang /personality
│ /usage /summary /reset
├───────────────────⦿
│ ᴀᴅᴍɪɴ:
│ /admin /addadmin /removeadmin
│ /broadcast /totalusers
│ /activeusers /forceclear
│ /shutdown /restart /ban
│ /unban /badwords /addbadword
│ /removebadword /setphrase
╰───────────────────⦿"""

ADMIN_PANEL_MESSAGE = """╭───────────────────⦿
│ 👑 ᴏᴡɴᴇʀ ᴅᴀsʜʙᴏᴀʀᴅ
├───────────────────⦿
│ 📊 ᴛᴏᴛᴀʟ ᴜsᴇʀs: {total_users}
│ 💬 ᴛᴏᴛᴀʟ ᴄʜᴀᴛs: {total_chats}
│ 📝 ᴛᴏᴛᴀʟ ᴍsɢs: {total_messages}
│ 🚫 ʙᴀɴɴᴇᴅ: {banned_users}
│ 🟢 ᴀᴄᴛɪᴠᴇ sᴇssɪᴏɴs: {active_sessions}
├───────────────────⦿
│ ᴀᴅᴍɪɴ ᴄᴏᴍᴍᴀɴᴅs:
│ /broadcast <msg>
│ /totalusers /activeusers
│ /forceclear <user_id>
│ /ban <user_id>
│ /unban <user_id>
│ /addbadword <word>
│ /removebadword <word>
│ /badwords
╰───────────────────⦿"""

PROFILE_MESSAGE = """╭───────────────────⦿
│ 👤 ᴘʀᴏғɪʟᴇ — {name}
├───────────────────⦿
│ 🆔 ᴜsᴇʀ ɪᴅ: {user_id}
│ 📛 ᴜsᴇʀɴᴀᴍᴇ: @{username}
│ 🎭 ʀᴏʟᴇ: {role}
│ 💬 ᴍᴇssᴀɢᴇs: {message_count}
│ 📅 ᴊᴏɪɴᴇᴅ: {joined}
│ 🚫 ʙᴀɴɴᴇᴅ: {banned}
│ 🌐 ʟᴀɴɢ: {lang}
╰───────────────────⦿"""


# ============================================================
#        DATABASE MANAGER (Embedded Full Implementation)
# ============================================================

class EmbeddedDatabaseManager:
    """
    Full PostgreSQL database manager with connection pooling,
    retry logic, and all required CRUD operations.
    Designed for Neon.tech + Render.com deployment.
    """

    def __init__(self, database_url: str):
        self.database_url = database_url
        self.pool = None
        self._lock = threading.Lock()
        self._max_retries = 3
        self._retry_delay = 2
        logger.info("[DB] Initializing database manager...")

    def initialize(self):
        """Create connection pool and initialize tables."""
        try:
            self.pool = psycopg2.pool.ThreadedConnectionPool(
                minconn=2,
                maxconn=10,
                dsn=self.database_url,
                connect_timeout=10,
            )
            logger.info("[DB] Connection pool created successfully ✓")
            self._create_tables()
            self._seed_default_settings()
            logger.info("[DB] All tables initialized ✓")
        except Exception as e:
            logger.error(f"[DB] Failed to initialize: {e}")
            raise

    def _get_connection(self):
        """Get a connection from the pool with retry logic."""
        for attempt in range(self._max_retries):
            try:
                if self.pool is None or self.pool.closed:
                    logger.warning("[DB] Pool closed, reinitializing...")
                    self.initialize()
                conn = self.pool.getconn()
                conn.autocommit = False
                # Test connection
                with conn.cursor() as cur:
                    cur.execute("SELECT 1")
                return conn
            except (OperationalError, InterfaceError) as e:
                logger.warning(
                    f"[DB] Connection attempt {attempt + 1} failed: {e}"
                )
                if attempt < self._max_retries - 1:
                    time.sleep(self._retry_delay * (attempt + 1))
                    try:
                        if self.pool and not self.pool.closed:
                            self.pool.closeall()
                    except Exception:
                        pass
                    self.pool = None
                else:
                    raise
            except Exception as e:
                logger.error(f"[DB] Unexpected connection error: {e}")
                raise

    def _return_connection(self, conn):
        """Return connection to pool safely."""
        try:
            if conn and self.pool and not self.pool.closed:
                self.pool.putconn(conn)
        except Exception as e:
            logger.warning(f"[DB] Error returning connection: {e}")

    def execute_query(
        self, query: str, params: tuple = None,
        fetch: bool = False, fetch_one: bool = False
    ) -> Any:
        """Execute a query with full retry and error handling."""
        conn = None
        for attempt in range(self._max_retries):
            try:
                conn = self._get_connection()
                with conn.cursor(
                    cursor_factory=psycopg2.extras.RealDictCursor
                ) as cur:
                    cur.execute(query, params)
                    result = None
                    if fetch_one:
                        result = cur.fetchone()
                    elif fetch:
                        result = cur.fetchall()
                    conn.commit()
                    return result
            except (OperationalError, InterfaceError) as e:
                logger.warning(
                    f"[DB] Query attempt {attempt + 1} failed: {e}"
                )
                if conn:
                    try:
                        conn.rollback()
                    except Exception:
                        pass
                    self._return_connection(conn)
                    conn = None
                if attempt < self._max_retries - 1:
                    time.sleep(self._retry_delay)
                else:
                    logger.error(f"[DB] Query failed after all retries: {e}")
                    return [] if fetch else None
            except Exception as e:
                logger.error(f"[DB] Query error: {e}\nQuery: {query}")
                if conn:
                    try:
                        conn.rollback()
                    except Exception:
                        pass
                return [] if fetch else None
            finally:
                if conn:
                    self._return_connection(conn)
                    conn = None

    def _create_tables(self):
        """Create all required database tables."""
        tables_sql = """
        -- Users table
        CREATE TABLE IF NOT EXISTS users (
            user_id BIGINT PRIMARY KEY,
            username VARCHAR(255) DEFAULT '',
            first_name VARCHAR(255) DEFAULT '',
            last_name VARCHAR(255) DEFAULT '',
            role VARCHAR(50) DEFAULT 'user',
            mood VARCHAR(50) DEFAULT 'default',
            language VARCHAR(10) DEFAULT 'hinglish',
            is_banned BOOLEAN DEFAULT FALSE,
            message_count INTEGER DEFAULT 0,
            first_seen TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            last_active TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );

        -- Chats table
        CREATE TABLE IF NOT EXISTS chats (
            chat_id BIGINT PRIMARY KEY,
            chat_type VARCHAR(50) DEFAULT 'private',
            title VARCHAR(255) DEFAULT '',
            active_session_expiry TIMESTAMP WITH TIME ZONE DEFAULT NULL,
            is_active BOOLEAN DEFAULT TRUE,
            added_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            last_activity TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );

        -- Messages table (for sliding window memory)
        CREATE TABLE IF NOT EXISTS messages (
            id BIGSERIAL PRIMARY KEY,
            chat_id BIGINT NOT NULL,
            user_id BIGINT NOT NULL,
            role VARCHAR(20) DEFAULT 'user',
            message_text TEXT NOT NULL,
            timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );

        -- Create indexes for performance
        CREATE INDEX IF NOT EXISTS idx_messages_chat_id
            ON messages(chat_id);
        CREATE INDEX IF NOT EXISTS idx_messages_timestamp
            ON messages(chat_id, timestamp DESC);
        CREATE INDEX IF NOT EXISTS idx_messages_chat_user
            ON messages(chat_id, user_id);

        -- Settings table
        CREATE TABLE IF NOT EXISTS settings (
            key VARCHAR(255) PRIMARY KEY,
            value TEXT DEFAULT '',
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );

        -- User-Chat relation for tracking
        CREATE TABLE IF NOT EXISTS user_chats (
            user_id BIGINT NOT NULL,
            chat_id BIGINT NOT NULL,
            joined_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            PRIMARY KEY (user_id, chat_id)
        );

        -- Broadcast log
        CREATE TABLE IF NOT EXISTS broadcast_log (
            id BIGSERIAL PRIMARY KEY,
            message_text TEXT,
            sent_count INTEGER DEFAULT 0,
            failed_count INTEGER DEFAULT 0,
            broadcast_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
        """
        self.execute_query(tables_sql)
        logger.info("[DB] Tables created/verified ✓")

    def _seed_default_settings(self):
        """Insert default settings if they don't exist."""
        defaults = {
            "bad_words": json.dumps(Config.BAD_WORDS_DEFAULT),
            "bot_mood": "savage",
            "maintenance_mode": "false",
            "wake_phrase": "ruhi ji"
        }
        for key, value in defaults.items():
            self.execute_query(
                """INSERT INTO settings (key, value, updated_at)
                   VALUES (%s, %s, NOW())
                   ON CONFLICT (key) DO NOTHING""",
                (key, value)
            )

    # === User Operations ===

    def upsert_user(
        self, user_id: int, username: str = "",
        first_name: str = "", last_name: str = ""
    ):
        """Insert or update a user record."""
        self.execute_query(
            """INSERT INTO users
                (user_id, username, first_name, last_name, last_active)
               VALUES (%s, %s, %s, %s, NOW())
               ON CONFLICT (user_id)
               DO UPDATE SET
                   username = EXCLUDED.username,
                   first_name = EXCLUDED.first_name,
                   last_name = EXCLUDED.last_name,
                   last_active = NOW()""",
            (user_id, username or "", first_name or "", last_name or "")
        )

    def get_user(self, user_id: int) -> Optional[Dict]:
        """Fetch a user record."""
        return self.execute_query(
            "SELECT * FROM users WHERE user_id = %s",
            (user_id,), fetch_one=True
        )

    def increment_message_count(self, user_id: int):
        """Increment the user's message counter."""
        self.execute_query(
            """UPDATE users
               SET message_count = message_count + 1,
                   last_active = NOW()
               WHERE user_id = %s""",
            (user_id,)
        )

    def ban_user(self, user_id: int) -> bool:
        """Ban a user."""
        self.execute_query(
            "UPDATE users SET is_banned = TRUE WHERE user_id = %s",
            (user_id,)
        )
        return True

    def unban_user(self, user_id: int) -> bool:
        """Unban a user."""
        self.execute_query(
            "UPDATE users SET is_banned = FALSE WHERE user_id = %s",
            (user_id,)
        )
        return True

    def is_user_banned(self, user_id: int) -> bool:
        """Check if a user is banned."""
        result = self.execute_query(
            "SELECT is_banned FROM users WHERE user_id = %s",
            (user_id,), fetch_one=True
        )
        return result.get("is_banned", False) if result else False

    def get_user_role(self, user_id: int) -> str:
        """Get user's role."""
        result = self.execute_query(
            "SELECT role FROM users WHERE user_id = %s",
            (user_id,), fetch_one=True
        )
        return result.get("role", "user") if result else "user"

    def set_user_role(self, user_id: int, role: str):
        """Set user's role."""
        self.execute_query(
            "UPDATE users SET role = %s WHERE user_id = %s",
            (role, user_id)
        )

    def set_user_language(self, user_id: int, lang: str):
        """Set user's preferred language."""
        self.execute_query(
            "UPDATE users SET language = %s WHERE user_id = %s",
            (lang, user_id)
        )

    def get_user_language(self, user_id: int) -> str:
        """Get user's language preference."""
        result = self.execute_query(
            "SELECT language FROM users WHERE user_id = %s",
            (user_id,), fetch_one=True
        )
        return result.get("language", "hinglish") if result else "hinglish"

    def get_total_users(self) -> int:
        """Get total user count."""
        result = self.execute_query(
            "SELECT COUNT(*) as count FROM users",
            fetch_one=True
        )
        return result.get("count", 0) if result else 0

    def get_active_users(self, hours: int = 24) -> int:
        """Get count of users active within the last N hours."""
        result = self.execute_query(
            """SELECT COUNT(*) as count FROM users
               WHERE last_active > NOW() - INTERVAL '%s hours'""",
            (hours,), fetch_one=True
        )
        return result.get("count", 0) if result else 0

    def get_banned_users_count(self) -> int:
        """Get banned users count."""
        result = self.execute_query(
            "SELECT COUNT(*) as count FROM users WHERE is_banned = TRUE",
            fetch_one=True
        )
        return result.get("count", 0) if result else 0

    def get_all_user_ids(self) -> List[int]:
        """Get all user IDs for broadcasting."""
        results = self.execute_query(
            "SELECT user_id FROM users WHERE is_banned = FALSE",
            fetch=True
        )
        return [r["user_id"] for r in results] if results else []

    # === Chat Operations ===

    def upsert_chat(
        self, chat_id: int, chat_type: str = "private",
        title: str = ""
    ):
        """Insert or update a chat record."""
        self.execute_query(
            """INSERT INTO chats (chat_id, chat_type, title, last_activity)
               VALUES (%s, %s, %s, NOW())
               ON CONFLICT (chat_id)
               DO UPDATE SET
                   chat_type = EXCLUDED.chat_type,
                   title = COALESCE(NULLIF(EXCLUDED.title, ''), chats.title),
                   last_activity = NOW()""",
            (chat_id, chat_type, title or "")
        )

    def get_total_chats(self) -> int:
        """Get total chat count."""
        result = self.execute_query(
            "SELECT COUNT(*) as count FROM chats",
            fetch_one=True
        )
        return result.get("count", 0) if result else 0

    def get_all_chat_ids(self) -> List[int]:
        """Get all chat IDs for broadcasting."""
        results = self.execute_query(
            "SELECT chat_id FROM chats WHERE is_active = TRUE",
            fetch=True
        )
        return [r["chat_id"] for r in results] if results else []

    # === Session Management ===

    def set_session_active(self, chat_id: int, minutes: int = 10):
        """Activate a session for a chat."""
        expiry = datetime.now(timezone.utc) + timedelta(minutes=minutes)
        self.execute_query(
            """UPDATE chats SET active_session_expiry = %s
               WHERE chat_id = %s""",
            (expiry, chat_id)
        )
        # Also ensure chat exists
        self.execute_query(
            """INSERT INTO chats (chat_id, active_session_expiry)
               VALUES (%s, %s)
               ON CONFLICT (chat_id)
               DO UPDATE SET active_session_expiry = EXCLUDED.active_session_expiry""",
            (chat_id, expiry)
        )

    def is_session_active(self, chat_id: int) -> bool:
        """Check if a chat has an active session."""
        result = self.execute_query(
            """SELECT active_session_expiry FROM chats
               WHERE chat_id = %s""",
            (chat_id,), fetch_one=True
        )
        if not result or not result.get("active_session_expiry"):
            return False
        expiry = result["active_session_expiry"]
        if expiry.tzinfo is None:
            expiry = expiry.replace(tzinfo=timezone.utc)
        return expiry > datetime.now(timezone.utc)

    def get_active_sessions_count(self) -> int:
        """Get count of currently active sessions."""
        result = self.execute_query(
            """SELECT COUNT(*) as count FROM chats
               WHERE active_session_expiry > NOW()""",
            fetch_one=True
        )
        return result.get("count", 0) if result else 0

    def clear_session(self, chat_id: int):
        """Clear session for a chat."""
        self.execute_query(
            """UPDATE chats SET active_session_expiry = NULL
               WHERE chat_id = %s""",
            (chat_id,)
        )

    # === Message/Memory Operations ===

    def store_message(
        self, chat_id: int, user_id: int,
        role: str, message_text: str
    ):
        """Store a message in the conversation history."""
        if not message_text or not message_text.strip():
            return

        # Truncate very long messages
        msg_text = message_text[:4000] if len(message_text) > 4000 else message_text

        self.execute_query(
            """INSERT INTO messages (chat_id, user_id, role, message_text, timestamp)
               VALUES (%s, %s, %s, %s, NOW())""",
            (chat_id, user_id, role, msg_text)
        )

    def get_chat_history(
        self, chat_id: int, limit: int = 20
    ) -> List[Dict]:
        """Fetch the last N messages for a chat (sliding window)."""
        results = self.execute_query(
            """SELECT role, message_text, user_id, timestamp
               FROM messages
               WHERE chat_id = %s
               ORDER BY timestamp DESC
               LIMIT %s""",
            (chat_id, limit), fetch=True
        )
        if results:
            # Reverse to get chronological order
            return list(reversed(results))
        return []

    def clear_chat_history(self, chat_id: int):
        """Clear all messages for a specific chat."""
        self.execute_query(
            "DELETE FROM messages WHERE chat_id = %s",
            (chat_id,)
        )

    def clear_user_history(self, user_id: int):
        """Clear all messages for a specific user across all chats."""
        self.execute_query(
            "DELETE FROM messages WHERE user_id = %s",
            (user_id,)
        )

    def get_total_messages(self) -> int:
        """Get total message count."""
        result = self.execute_query(
            "SELECT COUNT(*) as count FROM messages",
            fetch_one=True
        )
        return result.get("count", 0) if result else 0

    def cleanup_old_messages(self, chat_id: int, chat_type: str = "group"):
        """
        Enforce sliding window by deleting older messages
        beyond the limit.
        """
        limit = (
            Config.MAX_PRIVATE_MEMORY
            if chat_type == "private"
            else Config.MAX_GROUP_MEMORY
        )
        self.execute_query(
            """DELETE FROM messages
               WHERE id IN (
                   SELECT id FROM messages
                   WHERE chat_id = %s
                   ORDER BY timestamp DESC
                   OFFSET %s
               )""",
            (chat_id, limit)
        )

    # === Settings Operations ===

    def get_setting(self, key: str, default: str = "") -> str:
        """Get a setting value."""
        result = self.execute_query(
            "SELECT value FROM settings WHERE key = %s",
            (key,), fetch_one=True
        )
        return result.get("value", default) if result else default

    def set_setting(self, key: str, value: str):
        """Set a setting value."""
        self.execute_query(
            """INSERT INTO settings (key, value, updated_at)
               VALUES (%s, %s, NOW())
               ON CONFLICT (key)
               DO UPDATE SET value = EXCLUDED.value,
                           updated_at = NOW()""",
            (key, value)
        )

    def get_bad_words(self) -> List[str]:
        """Get the list of bad words."""
        raw = self.get_setting("bad_words", "[]")
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return []

    def add_bad_word(self, word: str) -> bool:
        """Add a word to the bad words list."""
        words = self.get_bad_words()
        word_lower = word.lower().strip()
        if word_lower not in words:
            words.append(word_lower)
            self.set_setting("bad_words", json.dumps(words))
            return True
        return False

    def remove_bad_word(self, word: str) -> bool:
        """Remove a word from the bad words list."""
        words = self.get_bad_words()
        word_lower = word.lower().strip()
        if word_lower in words:
            words.remove(word_lower)
            self.set_setting("bad_words", json.dumps(words))
            return True
        return False

    # === User-Chat Tracking ===

    def track_user_chat(self, user_id: int, chat_id: int):
        """Track that a user is part of a chat."""
        self.execute_query(
            """INSERT INTO user_chats (user_id, chat_id, joined_at)
               VALUES (%s, %s, NOW())
               ON CONFLICT (user_id, chat_id) DO NOTHING""",
            (user_id, chat_id)
        )

    # === Broadcast Logging ===

    def log_broadcast(
        self, message_text: str,
        sent_count: int, failed_count: int
    ):
        """Log a broadcast event."""
        self.execute_query(
            """INSERT INTO broadcast_log
                (message_text, sent_count, failed_count, broadcast_at)
               VALUES (%s, %s, %s, NOW())""",
            (message_text[:500], sent_count, failed_count)
        )

    def close(self):
        """Close the connection pool."""
        try:
            if self.pool and not self.pool.closed:
                self.pool.closeall()
                logger.info("[DB] Connection pool closed ✓")
        except Exception as e:
            logger.warning(f"[DB] Error closing pool: {e}")


# ============================================================
#           AI CLIENT (Embedded Full Implementation)
# ============================================================

class EmbeddedAIClient:
    """
    Hugging Face Router API client using OpenAI SDK.
    Handles context building, token management, and retries.
    """

    def __init__(self, hf_token: str):
        self.client = OpenAI(
            base_url=Config.HF_BASE_URL,
            api_key=hf_token,
        )
        self.model = Config.MODEL_NAME
        self.max_tokens = Config.MAX_RESPONSE_TOKENS
        self._request_count = 0
        self._error_count = 0
        logger.info(f"[AI] Client initialized with model: {self.model} ✓")

    def build_messages(
        self,
        user_message: str,
        chat_history: List[Dict],
        is_owner: bool = False,
        user_name: str = "User",
        chat_type: str = "private"
    ) -> List[Dict[str, str]]:
        """Build the messages array for the API call with context."""

        # Build system prompt
        system_content = SYSTEM_PROMPT
        if is_owner:
            system_content += "\n\n" + OWNER_SYSTEM_ADDON

        # Add context about who is talking
        context_note = f"\n\n[Context: User '{user_name}' is talking in a {chat_type} chat."
        if is_owner:
            context_note += " This is the OWNER — be respectful and loving!"
        context_note += "]"
        system_content += context_note

        messages = [{"role": "system", "content": system_content}]

        # Add chat history (sliding window already applied by DB)
        if chat_history:
            for msg in chat_history:
                role = msg.get("role", "user")
                text = msg.get("message_text", "")
                if text and role in ("user", "assistant"):
                    messages.append({"role": role, "content": text})

        # Add current message
        messages.append({"role": "user", "content": user_message})

        # Context truncation — ensure we don't exceed reasonable limits
        # Keep system prompt + last N messages to stay within token limits
        max_context_messages = 30  # system + 29 history messages
        if len(messages) > max_context_messages:
            # Keep system prompt (first) + trim from the middle
            messages = [messages[0]] + messages[-(max_context_messages - 1):]

        return messages

    async def generate_response(
        self,
        user_message: str,
        chat_history: List[Dict],
        is_owner: bool = False,
        user_name: str = "User",
        chat_type: str = "private"
    ) -> str:
        """Generate a response using the Hugging Face Router API."""

        self._request_count += 1
        messages = self.build_messages(
            user_message, chat_history, is_owner, user_name, chat_type
        )

        for attempt in range(3):
            try:
                logger.info(
                    f"[AI] Request #{self._request_count} | "
                    f"Context: {len(messages)} msgs | "
                    f"Attempt: {attempt + 1}"
                )

                # Run synchronous API call in executor to not block
                loop = asyncio.get_event_loop()
                completion = await loop.run_in_executor(
                    None,
                    lambda: self.client.chat.completions.create(
                        model=self.model,
                        messages=messages,
                        max_tokens=self.max_tokens,
                        temperature=0.85,
                        top_p=0.9,
                    )
                )

                if completion and completion.choices:
                    response = completion.choices[0].message.content
                    if response and response.strip():
                        logger.info(
                            f"[AI] Response generated: "
                            f"{len(response)} chars ✓"
                        )
                        return response.strip()

                logger.warning("[AI] Empty response received")
                return self._fallback_response(is_owner)

            except Exception as e:
                self._error_count += 1
                error_msg = str(e)
                logger.error(
                    f"[AI] Error (attempt {attempt + 1}): {error_msg}"
                )

                if "rate limit" in error_msg.lower():
                    wait_time = 5 * (attempt + 1)
                    logger.info(f"[AI] Rate limited, waiting {wait_time}s...")
                    await asyncio.sleep(wait_time)
                elif "timeout" in error_msg.lower():
                    await asyncio.sleep(3)
                elif attempt == 2:
                    return self._fallback_response(is_owner)
                else:
                    await asyncio.sleep(2)

        return self._fallback_response(is_owner)

    def _fallback_response(self, is_owner: bool = False) -> str:
        """Return a fallback response when API fails."""
        if is_owner:
            fallbacks = [
                "Ji bhaiya! 🥺 Abhi thoda busy hoon, ek sec mein aati hoon! 💖",
                "Owner-sama! 🌸 Mera brain thoda hang ho gaya, maaf karna! 🥺✨",
                "Bhaiya ji! Sorry abhi response nahi aa raha 😭 Try again? 💖",
            ]
        else:
            fallbacks = [
                "Arrey beta, mera mood off hai abhi 😤 Baad mein baat kar 💅",
                "Hmm... mera brain hang ho gaya 💀 Dobara bol na 😏",
                "Chomu, abhi busy hoon 😤 Ek minute ruk! ✨",
                "Lol bruh, kuch technical issue aa gaya 😭 Retry kar na 🥺",
            ]
        import random
        return random.choice(fallbacks)

    @property
    def stats(self) -> Dict:
        """Return client statistics."""
        return {
            "total_requests": self._request_count,
            "total_errors": self._error_count,
            "model": self.model,
            "success_rate": (
                f"{((self._request_count - self._error_count) / max(self._request_count, 1)) * 100:.1f}%"
            )
        }


# ============================================================
#          RATE LIMITER (Embedded Implementation)
# ============================================================

class EmbeddedRateLimiter:
    """Simple rate limiter to prevent spam."""

    def __init__(self, max_requests: int = 5, window_seconds: int = 10):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._requests: Dict[int, List[float]] = defaultdict(list)

    def is_allowed(self, user_id: int) -> bool:
        """Check if a user is within rate limits."""
        now = time.time()
        # Clean old entries
        self._requests[user_id] = [
            t for t in self._requests[user_id]
            if now - t < self.window_seconds
        ]
        if len(self._requests[user_id]) >= self.max_requests:
            return False
        self._requests[user_id].append(now)
        return True

    def get_wait_time(self, user_id: int) -> float:
        """Get remaining wait time for a rate-limited user."""
        if not self._requests[user_id]:
            return 0
        oldest = min(self._requests[user_id])
        wait = self.window_seconds - (time.time() - oldest)
        return max(0, wait)


# ============================================================
#           UTILITY FUNCTIONS
# ============================================================

def check_owner(username: str = None, user_id: int = None) -> bool:
    """Check if a user is the owner."""
    if username:
        clean_username = username.lstrip("@").lower()
        if clean_username == Config.OWNER_USERNAME.lower():
            return True
    if user_id and Config.OWNER_CHAT_ID:
        try:
            if int(user_id) == int(Config.OWNER_CHAT_ID):
                return True
        except (ValueError, TypeError):
            pass
    return False


def get_display_name(user) -> str:
    """Get a user's display name from a Telegram User object."""
    if user is None:
        return "Unknown"
    if user.first_name:
        name = user.first_name
        if user.last_name:
            name += f" {user.last_name}"
        return name
    if user.username:
        return f"@{user.username}"
    return f"User-{user.id}"


def contains_wake_phrase(text: str) -> bool:
    """Check if the text contains the wake phrase 'Ruhi Ji'."""
    if not text:
        return False
    text_lower = text.lower().strip()
    wake_phrases = [
        "ruhi ji", "ruhi-ji", "ruhiji",
        "ruhi", "रुही जी", "रूही जी",
        "@ruhijibot"
    ]
    for phrase in wake_phrases:
        if phrase in text_lower:
            return True
    return False


def contains_bad_word(text: str, bad_words: List[str]) -> bool:
    """Check if text contains any bad words."""
    if not text or not bad_words:
        return False
    text_lower = text.lower()
    for word in bad_words:
        if word.lower() in text_lower:
            return True
    return False


def sanitize_message(text: str) -> str:
    """Sanitize user input."""
    if not text:
        return ""
    # Remove potential injection attempts
    text = text.replace("\x00", "")
    # Limit length
    if len(text) > 4000:
        text = text[:4000]
    return text.strip()


# ============================================================
#              FLASK WEB SERVER (For Render.com)
# ============================================================

def create_web_server(db_manager, bot_start_time):
    """Create Flask app for Render.com health checks."""

    flask_app = Flask(__name__)

    @flask_app.route("/")
    def home():
        """Root endpoint — shows bot status."""
        uptime = str(datetime.now(timezone.utc) - bot_start_time)
        return jsonify({
            "status": "alive",
            "bot": "Ruhi Ji 👑",
            "version": "2.0.0",
            "uptime": uptime,
            "model": Config.MODEL_NAME,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }), 200

    @flask_app.route("/health")
    def health():
        """Health check endpoint for UptimeRobot / Render."""
        try:
            # Quick DB ping
            result = db_manager.execute_query(
                "SELECT 1 as ok", fetch_one=True
            )
            db_status = "connected" if result else "error"
        except Exception:
            db_status = "error"

        return jsonify({
            "status": "healthy",
            "database": db_status,
            "bot": "running",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }), 200

    @flask_app.route("/stats")
    def stats():
        """Bot statistics endpoint."""
        try:
            total_users = db_manager.get_total_users()
            total_chats = db_manager.get_total_chats()
            total_msgs = db_manager.get_total_messages()
        except Exception:
            total_users = total_chats = total_msgs = -1

        return jsonify({
            "total_users": total_users,
            "total_chats": total_chats,
            "total_messages": total_msgs,
            "uptime": str(datetime.now(timezone.utc) - bot_start_time)
        }), 200

    @flask_app.route("/ping")
    def ping():
        """Simple ping endpoint."""
        return "pong", 200

    return flask_app


# ============================================================
#            MAIN BOT CLASS — RUHI JI
# ============================================================

class RuhiJiBot:
    """
    Main bot class that orchestrates all components:
    - Telegram Bot API handlers
    - Database operations
    - AI response generation
    - Session management
    - Rate limiting
    - Web server for Render.com
    """

    def __init__(self):
        """Initialize all bot components."""
        logger.info("=" * 60)
        logger.info("    RUHI JI BOT — INITIALIZATION STARTED")
        logger.info("=" * 60)

        self.start_time = datetime.now(timezone.utc)

        # Validate configuration
        if not Config.validate():
            logger.error("[INIT] Configuration validation failed!")
            sys.exit(1)

        # Initialize Database
        logger.info("[INIT] Setting up database...")
        self.db = EmbeddedDatabaseManager(Config.DATABASE_URL)
        self.db.initialize()

        # Initialize AI Client
        logger.info("[INIT] Setting up AI client...")
        self.ai = EmbeddedAIClient(Config.HF_TOKEN)

        # Initialize Rate Limiter
        self.rate_limiter = EmbeddedRateLimiter(
            max_requests=8, window_seconds=15
        )

        # Telegram Application (will be set in run())
        self.application = None

        # Processing lock to prevent duplicate processing
        self._processing_locks: Dict[int, asyncio.Lock] = {}

        # Track owner chat ID dynamically
        self._owner_id = None

        logger.info("[INIT] All components initialized ✓")
        logger.info("=" * 60)

    def _get_chat_lock(self, chat_id: int) -> asyncio.Lock:
        """Get or create a lock for a specific chat."""
        if chat_id not in self._processing_locks:
            self._processing_locks[chat_id] = asyncio.Lock()
        return self._processing_locks[chat_id]

    # ========================================================
    #            COMMAND HANDLERS
    # ========================================================

    async def cmd_start(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Handle /start command."""
        if not update.effective_user or not update.effective_message:
            return

        user = update.effective_user
        chat = update.effective_chat

        logger.info(
            f"[CMD] /start from {user.id} "
            f"(@{user.username}) in {chat.type}"
        )

        # Register user and chat
        self.db.upsert_user(
            user.id,
            user.username or "",
            user.first_name or "",
            user.last_name or ""
        )
        self.db.upsert_chat(
            chat.id,
            chat.type,
            chat.title or ""
        )
        self.db.track_user_chat(user.id, chat.id)

        # Track owner
        if check_owner(user.username):
            self._owner_id = user.id
            self.db.set_user_role(user.id, "owner")

        # Build personalized start message
        name = get_display_name(user)
        message = START_MESSAGE.format(name=name)

        # Add inline keyboard
        keyboard = [
            [
                InlineKeyboardButton(
                    "📋 Help", callback_data="help"
                ),
                InlineKeyboardButton(
                    "👤 Profile", callback_data="profile"
                )
            ],
            [
                InlineKeyboardButton(
                    "💬 Start Chat", callback_data="start_chat"
                ),
                InlineKeyboardButton(
                    "👑 Owner", url="https://t.me/RUHI_VIG_QNR"
                )
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        try:
            await update.effective_message.reply_text(
                message,
                reply_markup=reply_markup,
                disable_web_page_preview=True
            )
        except Exception as e:
            logger.error(f"[CMD] Error sending /start: {e}")

    async def cmd_help(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Handle /help command."""
        if not update.effective_message:
            return

        user = update.effective_user
        logger.info(f"[CMD] /help from {user.id if user else 'unknown'}")

        keyboard = [
            [
                InlineKeyboardButton(
                    "🏠 Home", callback_data="start"
                ),
                InlineKeyboardButton(
                    "👤 Profile", callback_data="profile"
                )
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        try:
            await update.effective_message.reply_text(
                HELP_MESSAGE,
                reply_markup=reply_markup
            )
        except Exception as e:
            logger.error(f"[CMD] Error sending /help: {e}")

    async def cmd_profile(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Handle /profile command."""
        if not update.effective_user or not update.effective_message:
            return

        user = update.effective_user
        logger.info(f"[CMD] /profile from {user.id}")

        # Fetch user data
        user_data = self.db.get_user(user.id)

        if not user_data:
            await update.effective_message.reply_text(
                "Beta, pehle /start kar! 😏"
            )
            return

        is_own = check_owner(user.username)
        role = "👑 Owner" if is_own else "👤 User"

        profile = PROFILE_MESSAGE.format(
            name=get_display_name(user),
            user_id=user.id,
            username=user.username or "N/A",
            role=role,
            message_count=user_data.get("message_count", 0),
            joined=str(user_data.get("first_seen", "Unknown"))[:10],
            banned="❌ No" if not user_data.get("is_banned") else "✅ Yes",
            lang=user_data.get("language", "hinglish")
        )

        try:
            await update.effective_message.reply_text(profile)
        except Exception as e:
            logger.error(f"[CMD] Error sending /profile: {e}")

    async def cmd_clear(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Handle /clear or /reset command — wipes chat memory."""
        if not update.effective_chat or not update.effective_message:
            return

        chat_id = update.effective_chat.id
        user = update.effective_user

        logger.info(
            f"[CMD] /clear from {user.id if user else 'unknown'} "
            f"in chat {chat_id}"
        )

        self.db.clear_chat_history(chat_id)
        self.db.clear_session(chat_id)

        try:
            await update.effective_message.reply_text(
                "✅ Memory cleared! Ab sab fresh hai ✨\n"
                "Mujhse phir se 'Ruhi Ji' bolke baat kar 🌹"
            )
        except Exception as e:
            logger.error(f"[CMD] Error sending /clear response: {e}")

    async def cmd_reset(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Alias for /clear."""
        await self.cmd_clear(update, context)

    async def cmd_lang(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Handle /lang command — toggle language preference."""
        if not update.effective_user or not update.effective_message:
            return

        user = update.effective_user
        current_lang = self.db.get_user_language(user.id)

        # Toggle between hinglish and english
        new_lang = "english" if current_lang == "hinglish" else "hinglish"
        self.db.set_user_language(user.id, new_lang)

        lang_display = {
            "hinglish": "Hinglish (Hindi + English) 🇮🇳",
            "english": "English 🇬🇧"
        }

        try:
            await update.effective_message.reply_text(
                f"✅ Language changed to: {lang_display.get(new_lang, new_lang)}\n"
                f"Ab main {new_lang} mein baat karungi! ✨💅"
            )
        except Exception as e:
            logger.error(f"[CMD] Error in /lang: {e}")

    async def cmd_personality(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Handle /personality command — show current bot mood."""
        if not update.effective_message:
            return

        mood = self.db.get_setting("bot_mood", "savage")
        mood_emojis = {
            "savage": "😏 Savage Mode — Full roasting ON!",
            "soft": "🥺 Soft Mode — Sweet aur caring",
            "attitude": "😤 Attitude Mode — Don't mess with me",
            "playful": "🤭 Playful Mode — Masti time!",
            "queen": "💅 Queen Mode — Unbothered & slay",
            "dramatic": "😭 Dramatic Mode — Over-react everything"
        }

        display = mood_emojis.get(mood, f"🎭 {mood.title()} Mode")

        try:
            await update.effective_message.reply_text(
                f"╭───────────────────⦿\n"
                f"│ 🎭 ᴄᴜʀʀᴇɴᴛ ᴘᴇʀsᴏɴᴀʟɪᴛʏ\n"
                f"├───────────────────⦿\n"
                f"│ {display}\n"
                f"│ 🤖 Model: Kimi-K2-Instruct\n"
                f"╰───────────────────⦿"
            )
        except Exception as e:
            logger.error(f"[CMD] Error in /personality: {e}")

    async def cmd_usage(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Handle /usage command — show usage statistics."""
        if not update.effective_user or not update.effective_message:
            return

        user = update.effective_user
        user_data = self.db.get_user(user.id)
        msg_count = user_data.get("message_count", 0) if user_data else 0

        ai_stats = self.ai.stats

        try:
            await update.effective_message.reply_text(
                f"╭───────────────────⦿\n"
                f"│ 📊 ᴜsᴀɢᴇ sᴛᴀᴛs\n"
                f"├───────────────────⦿\n"
                f"│ 💬 Your Messages: {msg_count}\n"
                f"│ 🤖 AI Requests: {ai_stats['total_requests']}\n"
                f"│ ✅ Success Rate: {ai_stats['success_rate']}\n"
                f"│ ⏱️ Uptime: {str(datetime.now(timezone.utc) - self.start_time).split('.')[0]}\n"
                f"╰───────────────────⦿"
            )
        except Exception as e:
            logger.error(f"[CMD] Error in /usage: {e}")

    async def cmd_summary(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Handle /summary command — LLM-powered chat summary."""
        if not update.effective_chat or not update.effective_message:
            return

        chat_id = update.effective_chat.id
        user = update.effective_user
        chat_type = update.effective_chat.type

        logger.info(f"[CMD] /summary from {user.id if user else 'unknown'}")

        # Get chat history
        limit = (
            Config.MAX_PRIVATE_MEMORY
            if chat_type == ChatType.PRIVATE
            else Config.MAX_GROUP_MEMORY
        )
        history = self.db.get_chat_history(chat_id, limit)

        if not history or len(history) < 3:
            await update.effective_message.reply_text(
                "Abhi toh kuch khaas baat nahi hui beta 🥺\n"
                "Thoda aur baat kar, phir summary duungi! ✨"
            )
            return

        # Send typing action
        await update.effective_chat.send_action(ChatAction.TYPING)

        # Ask LLM to summarize
        summary_prompt = (
            "Yeh hai recent chat history. Isko ek fun, "
            "Hinglish mein short summary de — Ruhi Ji ke style mein. "
            "Kya kya baatein hui, kaun kya bol raha tha, "
            "koi interesting ya funny moments? 2-3 lines mein summarize kar "
            "with emojis. History:\n\n"
        )
        for msg in history[-15:]:  # Last 15 messages for summary
            role = msg.get("role", "user")
            text = msg.get("message_text", "")[:200]
            summary_prompt += f"[{role}]: {text}\n"

        is_own = check_owner(user.username if user else "")
        response = await self.ai.generate_response(
            summary_prompt, [], is_own,
            get_display_name(user) if user else "User",
            str(chat_type)
        )

        try:
            await update.effective_message.reply_text(
                f"📋 **Chat Summary** ✨\n\n{response}"
            )
        except Exception as e:
            logger.error(f"[CMD] Error in /summary: {e}")

    # ========================================================
    #            ADMIN COMMANDS (Owner Only)
    # ========================================================

    async def _check_admin(
        self, update: Update
    ) -> bool:
        """Check if the user is the admin/owner."""
        user = update.effective_user
        if not user:
            return False
        if check_owner(user.username, user.id):
            return True

        try:
            await update.effective_message.reply_text(
                "❌ Beta, yeh command sirf Owner ke liye hai 😏\n"
                "Tu apni aukat mein reh 💅"
            )
        except Exception:
            pass
        return False

    async def cmd_admin(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Handle /admin command — owner dashboard."""
        if not await self._check_admin(update):
            return

        logger.info("[CMD] /admin — Owner dashboard accessed")

        total_users = self.db.get_total_users()
        total_chats = self.db.get_total_chats()
        total_messages = self.db.get_total_messages()
        banned_users = self.db.get_banned_users_count()
        active_sessions = self.db.get_active_sessions_count()

        panel = ADMIN_PANEL_MESSAGE.format(
            total_users=total_users,
            total_chats=total_chats,
            total_messages=total_messages,
            banned_users=banned_users,
            active_sessions=active_sessions
        )

        keyboard = [
            [
                InlineKeyboardButton(
                    "📊 Refresh", callback_data="admin_refresh"
                ),
                InlineKeyboardButton(
                    "📢 Broadcast", callback_data="admin_broadcast"
                )
            ],
            [
                InlineKeyboardButton(
                    "🚫 Bad Words", callback_data="admin_badwords"
                ),
                InlineKeyboardButton(
                    "🔄 Clear All Sessions",
                    callback_data="admin_clear_sessions"
                )
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        try:
            await update.effective_message.reply_text(
                panel, reply_markup=reply_markup
            )
        except Exception as e:
            logger.error(f"[CMD] Error in /admin: {e}")

    async def cmd_broadcast(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Handle /broadcast command — send message to all users."""
        if not await self._check_admin(update):
            return

        if not context.args:
            await update.effective_message.reply_text(
                "Usage: /broadcast <message>\n"
                "Example: /broadcast Hello everyone! 🌸"
            )
            return

        broadcast_text = " ".join(context.args)
        logger.info(f"[CMD] /broadcast initiated: {broadcast_text[:50]}...")

        # Get all user and chat IDs
        user_ids = self.db.get_all_user_ids()
        chat_ids = self.db.get_all_chat_ids()

        # Combine unique IDs
        all_ids = list(set(user_ids + chat_ids))

        sent = 0
        failed = 0
        status_msg = await update.effective_message.reply_text(
            f"📢 Broadcasting to {len(all_ids)} chats...\n"
            f"Please wait... ⏳"
        )

        bot = context.bot
        broadcast_message = (
            f"📢 **Broadcast from Ruhi Ji** 👑\n\n"
            f"{broadcast_text}\n\n"
            f"— @RUHI_VIG_QNR"
        )

        for chat_id in all_ids:
            try:
                await bot.send_message(
                    chat_id=chat_id,
                    text=broadcast_message
                )
                sent += 1
                # Rate limiting for Telegram API
                if sent % 25 == 0:
                    await asyncio.sleep(1.5)
            except Forbidden:
                failed += 1
                logger.debug(
                    f"[BROADCAST] Bot blocked by {chat_id}"
                )
            except BadRequest as e:
                failed += 1
                logger.debug(
                    f"[BROADCAST] Bad request for {chat_id}: {e}"
                )
            except RetryAfter as e:
                logger.warning(
                    f"[BROADCAST] Rate limited, sleeping {e.retry_after}s"
                )
                await asyncio.sleep(e.retry_after)
                try:
                    await bot.send_message(
                        chat_id=chat_id, text=broadcast_message
                    )
                    sent += 1
                except Exception:
                    failed += 1
            except Exception as e:
                failed += 1
                logger.debug(
                    f"[BROADCAST] Failed for {chat_id}: {e}"
                )

        # Log broadcast
        self.db.log_broadcast(broadcast_text, sent, failed)

        try:
            await status_msg.edit_text(
                f"✅ Broadcast Complete!\n\n"
                f"📤 Sent: {sent}\n"
                f"❌ Failed: {failed}\n"
                f"📊 Total: {len(all_ids)}"
            )
        except Exception:
            pass

    async def cmd_totalusers(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Handle /totalusers command."""
        if not await self._check_admin(update):
            return

        total = self.db.get_total_users()
        total_chats = self.db.get_total_chats()

        try:
            await update.effective_message.reply_text(
                f"📊 Total Users: {total}\n"
                f"💬 Total Chats: {total_chats}\n"
                f"Owner-sama, yeh hai aapke stats! 💖"
            )
        except Exception as e:
            logger.error(f"[CMD] Error in /totalusers: {e}")

    async def cmd_activeusers(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Handle /activeusers command."""
        if not await self._check_admin(update):
            return

        active_24h = self.db.get_active_users(24)
        active_1h = self.db.get_active_users(1)
        active_sessions = self.db.get_active_sessions_count()

        try:
            await update.effective_message.reply_text(
                f"📊 Active Users Stats:\n\n"
                f"⏰ Last 1 hour: {active_1h}\n"
                f"📅 Last 24 hours: {active_24h}\n"
                f"💬 Active Sessions: {active_sessions}\n\n"
                f"Ji bhaiya! 🥺✨"
            )
        except Exception as e:
            logger.error(f"[CMD] Error in /activeusers: {e}")

    async def cmd_forceclear(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Handle /forceclear [UserID] command."""
        if not await self._check_admin(update):
            return

        if not context.args:
            await update.effective_message.reply_text(
                "Usage: /forceclear <user_id>\n"
                "Example: /forceclear 123456789"
            )
            return

        try:
            target_user_id = int(context.args[0])
        except ValueError:
            await update.effective_message.reply_text(
                "❌ Invalid user ID! Numbers only, beta 😏"
            )
            return

        self.db.clear_user_history(target_user_id)

        try:
            await update.effective_message.reply_text(
                f"✅ Context cleared for user {target_user_id}\n"
                f"Sab saaf ho gaya, Owner-sama! 🌸✨"
            )
        except Exception as e:
            logger.error(f"[CMD] Error in /forceclear: {e}")

    async def cmd_ban(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Handle /ban command."""
        if not await self._check_admin(update):
            return

        target_id = None

        # Check if replying to a message
        if update.effective_message.reply_to_message:
            target_id = update.effective_message.reply_to_message.from_user.id
        elif context.args:
            try:
                target_id = int(context.args[0])
            except ValueError:
                pass

        if not target_id:
            await update.effective_message.reply_text(
                "Usage: /ban <user_id> ya reply karke /ban likh\n"
                "Example: /ban 123456789"
            )
            return

        # Don't allow banning the owner
        if check_owner(user_id=target_id):
            await update.effective_message.reply_text(
                "🚫 Owner ko ban nahi kar sakte! 😤"
            )
            return

        self.db.ban_user(target_id)

        try:
            await update.effective_message.reply_text(
                f"🚫 User {target_id} has been BANNED!\n"
                f"Ab yeh mujhse baat nahi kar payega 💅"
            )
        except Exception as e:
            logger.error(f"[CMD] Error in /ban: {e}")

    async def cmd_unban(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Handle /unban command."""
        if not await self._check_admin(update):
            return

        if not context.args:
            await update.effective_message.reply_text(
                "Usage: /unban <user_id>\n"
                "Example: /unban 123456789"
            )
            return

        try:
            target_id = int(context.args[0])
        except ValueError:
            await update.effective_message.reply_text(
                "❌ Invalid user ID!"
            )
            return

        self.db.unban_user(target_id)

        try:
            await update.effective_message.reply_text(
                f"✅ User {target_id} has been UNBANNED!\n"
                f"Ab dobara baat kar sakta hai 🌹"
            )
        except Exception as e:
            logger.error(f"[CMD] Error in /unban: {e}")

    async def cmd_badwords(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Handle /badwords command — show bad words list."""
        if not await self._check_admin(update):
            return

        words = self.db.get_bad_words()

        if not words:
            await update.effective_message.reply_text(
                "📋 Bad words list is empty!"
            )
            return

        word_list = ", ".join(f"`{w}`" for w in words)
        try:
            await update.effective_message.reply_text(
                f"🚫 Bad Words List ({len(words)} words):\n\n"
                f"{word_list}\n\n"
                f"Use /addbadword <word> to add\n"
                f"Use /removebadword <word> to remove"
            )
        except Exception as e:
            logger.error(f"[CMD] Error in /badwords: {e}")

    async def cmd_addbadword(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Handle /addbadword command."""
        if not await self._check_admin(update):
            return

        if not context.args:
            await update.effective_message.reply_text(
                "Usage: /addbadword <word>"
            )
            return

        word = " ".join(context.args).strip()
        added = self.db.add_bad_word(word)

        if added:
            await update.effective_message.reply_text(
                f"✅ Added '{word}' to bad words list! 🚫"
            )
        else:
            await update.effective_message.reply_text(
                f"⚠️ '{word}' already exists in the list!"
            )

    async def cmd_removebadword(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Handle /removebadword command."""
        if not await self._check_admin(update):
            return

        if not context.args:
            await update.effective_message.reply_text(
                "Usage: /removebadword <word>"
            )
            return

        word = " ".join(context.args).strip()
        removed = self.db.remove_bad_word(word)

        if removed:
            await update.effective_message.reply_text(
                f"✅ Removed '{word}' from bad words list!"
            )
        else:
            await update.effective_message.reply_text(
                f"⚠️ '{word}' not found in the list!"
            )

    async def cmd_setphrase(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Handle /setphrase command — set custom wake phrase."""
        if not await self._check_admin(update):
            return

        if not context.args:
            current = self.db.get_setting("wake_phrase", "ruhi ji")
            await update.effective_message.reply_text(
                f"Current wake phrase: '{current}'\n"
                f"Usage: /setphrase <new phrase>"
            )
            return

        new_phrase = " ".join(context.args).strip().lower()
        self.db.set_setting("wake_phrase", new_phrase)

        await update.effective_message.reply_text(
            f"✅ Wake phrase updated to: '{new_phrase}' 🌸"
        )

    async def cmd_addadmin(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Handle /addadmin command (Owner only — set user as admin)."""
        if not await self._check_admin(update):
            return

        if not context.args:
            await update.effective_message.reply_text(
                "Usage: /addadmin <user_id>"
            )
            return

        try:
            target_id = int(context.args[0])
        except ValueError:
            await update.effective_message.reply_text("❌ Invalid user ID!")
            return

        self.db.set_user_role(target_id, "admin")
        await update.effective_message.reply_text(
            f"✅ User {target_id} is now an admin! 👑"
        )

    async def cmd_removeadmin(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Handle /removeadmin command."""
        if not await self._check_admin(update):
            return

        if not context.args:
            await update.effective_message.reply_text(
                "Usage: /removeadmin <user_id>"
            )
            return

        try:
            target_id = int(context.args[0])
        except ValueError:
            await update.effective_message.reply_text("❌ Invalid user ID!")
            return

        self.db.set_user_role(target_id, "user")
        await update.effective_message.reply_text(
            f"✅ User {target_id} is no longer an admin!"
        )

    async def cmd_shutdown(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Handle /shutdown command (Owner only)."""
        if not await self._check_admin(update):
            return

        await update.effective_message.reply_text(
            "🔴 Ruhi Ji shutting down... Bye bye! 🥺💖\n"
            "Owner-sama ne bola toh maan leti hoon..."
        )
        logger.info("[CMD] Shutdown initiated by owner")
        # Graceful shutdown
        await asyncio.sleep(1)
        os._exit(0)

    async def cmd_restart(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Handle /restart command (Owner only)."""
        if not await self._check_admin(update):
            return

        await update.effective_message.reply_text(
            "🔄 Restarting... Ek moment, Owner-sama! 🥺✨"
        )
        logger.info("[CMD] Restart initiated by owner")
        await asyncio.sleep(1)
        os.execv(sys.executable, [sys.executable] + sys.argv)

    # ========================================================
    #          CALLBACK QUERY HANDLER
    # ========================================================

    async def handle_callback(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Handle inline keyboard button presses."""
        query = update.callback_query
        if not query:
            return

        await query.answer()
        data = query.data
        user = query.from_user

        logger.info(
            f"[CALLBACK] {data} from {user.id} (@{user.username})"
        )

        try:
            if data == "help":
                keyboard = [
                    [
                        InlineKeyboardButton(
                            "🏠 Home", callback_data="start"
                        ),
                        InlineKeyboardButton(
                            "👤 Profile", callback_data="profile"
                        )
                    ]
                ]
                await query.edit_message_text(
                    HELP_MESSAGE,
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )

            elif data == "start":
                name = get_display_name(user)
                message = START_MESSAGE.format(name=name)
                keyboard = [
                    [
                        InlineKeyboardButton(
                            "📋 Help", callback_data="help"
                        ),
                        InlineKeyboardButton(
                            "👤 Profile", callback_data="profile"
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            "💬 Start Chat",
                            callback_data="start_chat"
                        ),
                        InlineKeyboardButton(
                            "👑 Owner",
                            url="https://t.me/RUHI_VIG_QNR"
                        )
                    ]
                ]
                await query.edit_message_text(
                    message,
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )

            elif data == "profile":
                user_data = self.db.get_user(user.id)
                if not user_data:
                    await query.edit_message_text(
                        "Beta pehle /start kar! 😏"
                    )
                    return

                is_own = check_owner(user.username)
                role = "👑 Owner" if is_own else "👤 User"
                profile = PROFILE_MESSAGE.format(
                    name=get_display_name(user),
                    user_id=user.id,
                    username=user.username or "N/A",
                    role=role,
                    message_count=user_data.get("message_count", 0),
                    joined=str(
                        user_data.get("first_seen", "Unknown")
                    )[:10],
                    banned=(
                        "❌ No"
                        if not user_data.get("is_banned")
                        else "✅ Yes"
                    ),
                    lang=user_data.get("language", "hinglish")
                )
                keyboard = [
                    [
                        InlineKeyboardButton(
                            "🏠 Home", callback_data="start"
                        ),
                        InlineKeyboardButton(
                            "📋 Help", callback_data="help"
                        )
                    ]
                ]
                await query.edit_message_text(
                    profile,
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )

            elif data == "start_chat":
                await query.edit_message_text(
                    "💬 Bas 'Ruhi Ji' bolke baat shuru kar! 🌹\n\n"
                    "Example:\n"
                    "• Ruhi Ji kaise ho?\n"
                    "• Ruhi Ji kuch funny suna\n"
                    "• Ruhi Ji roast karo mujhe\n\n"
                    "Private chat mein direct baat kar sakti hoon! ✨"
                )

            elif data == "admin_refresh":
                if not check_owner(user.username, user.id):
                    await query.answer(
                        "❌ Only owner can access!", show_alert=True
                    )
                    return

                total_users = self.db.get_total_users()
                total_chats = self.db.get_total_chats()
                total_messages = self.db.get_total_messages()
                banned_users = self.db.get_banned_users_count()
                active_sessions = self.db.get_active_sessions_count()

                panel = ADMIN_PANEL_MESSAGE.format(
                    total_users=total_users,
                    total_chats=total_chats,
                    total_messages=total_messages,
                    banned_users=banned_users,
                    active_sessions=active_sessions
                )

                keyboard = [
                    [
                        InlineKeyboardButton(
                            "📊 Refresh",
                            callback_data="admin_refresh"
                        ),
                        InlineKeyboardButton(
                            "📢 Broadcast",
                            callback_data="admin_broadcast"
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            "🚫 Bad Words",
                            callback_data="admin_badwords"
                        ),
                        InlineKeyboardButton(
                            "🔄 Clear Sessions",
                            callback_data="admin_clear_sessions"
                        )
                    ]
                ]
                await query.edit_message_text(
                    panel,
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )

            elif data == "admin_broadcast":
                if not check_owner(user.username, user.id):
                    await query.answer(
                        "❌ Only owner!", show_alert=True
                    )
                    return
                await query.edit_message_text(
                    "📢 To broadcast, use:\n"
                    "/broadcast <your message>\n\n"
                    "Example: /broadcast Namaste sabko! 🌸"
                )

            elif data == "admin_badwords":
                if not check_owner(user.username, user.id):
                    await query.answer(
                        "❌ Only owner!", show_alert=True
                    )
                    return
                words = self.db.get_bad_words()
                word_list = (
                    ", ".join(words[:20]) if words else "Empty"
                )
                await query.edit_message_text(
                    f"🚫 Bad Words ({len(words)}):\n{word_list}\n\n"
                    f"/addbadword <word>\n"
                    f"/removebadword <word>"
                )

            elif data == "admin_clear_sessions":
                if not check_owner(user.username, user.id):
                    await query.answer(
                        "❌ Only owner!", show_alert=True
                    )
                    return
                self.db.execute_query(
                    "UPDATE chats SET active_session_expiry = NULL"
                )
                await query.edit_message_text(
                    "✅ All active sessions cleared! 🌸"
                )

        except BadRequest as e:
            if "not modified" in str(e).lower():
                await query.answer("Already up to date! ✨")
            else:
                logger.error(f"[CALLBACK] BadRequest: {e}")
        except Exception as e:
            logger.error(f"[CALLBACK] Error handling {data}: {e}")

    # ========================================================
    #         MAIN MESSAGE HANDLER — BRAIN OF THE BOT
    # ========================================================

    async def handle_message(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """
        Main message handler — The core brain of Ruhi Ji.

        Logic Flow:
        1. Validate message and user
        2. Check if banned
        3. Register user/chat in DB
        4. Determine if bot should respond (wake phrase / private / reply)
        5. Rate limit check
        6. Bad word filter
        7. Build context from DB history
        8. Generate AI response
        9. Store both messages in DB
        10. Send response
        """
        # === Step 1: Validate ===
        if not update.effective_message or not update.effective_user:
            return

        message = update.effective_message
        user = update.effective_user
        chat = update.effective_chat
        text = message.text

        # Skip empty messages, commands, and media-only
        if not text or text.startswith("/"):
            return

        user_id = user.id
        chat_id = chat.id
        chat_type = chat.type
        username = user.username or ""
        user_name = get_display_name(user)
        is_own = check_owner(username, user_id)

        # === Step 2: Check if banned ===
        if self.db.is_user_banned(user_id) and not is_own:
            logger.info(f"[MSG] Banned user {user_id} tried to interact")
            return

        # === Step 3: Register user/chat ===
        self.db.upsert_user(
            user_id, username,
            user.first_name or "", user.last_name or ""
        )
        self.db.upsert_chat(
            chat_id, chat_type, chat.title or ""
        )
        self.db.track_user_chat(user_id, chat_id)

        # Track owner ID dynamically
        if is_own:
            self._owner_id = user_id

        # === Step 4: Should the bot respond? ===
        should_respond = False
        activated_session = False

        if chat_type == ChatType.PRIVATE:
            # Always respond in private chats
            should_respond = True
        else:
            # Group chat logic
            # Check 1: Wake phrase
            if contains_wake_phrase(text):
                should_respond = True
                activated_session = True
                # Activate 10-minute session
                self.db.set_session_active(
                    chat_id, Config.SESSION_TIMEOUT_MINUTES
                )
                logger.info(
                    f"[SESSION] Activated for chat {chat_id} "
                    f"by {user_id} (wake phrase)"
                )

            # Check 2: Reply to bot's message
            elif (
                message.reply_to_message
                and message.reply_to_message.from_user
                and message.reply_to_message.from_user.is_bot
            ):
                # Check if the reply is to THIS bot
                bot_info = context.bot
                if (
                    message.reply_to_message.from_user.id
                    == bot_info.id
                ):
                    should_respond = True
                    # Refresh session
                    self.db.set_session_active(
                        chat_id, Config.SESSION_TIMEOUT_MINUTES
                    )

            # Check 3: Active session
            elif self.db.is_session_active(chat_id):
                should_respond = True

        # Store message regardless (for context building)
        sanitized_text = sanitize_message(text)
        # Prepend user name for group context
        if chat_type != ChatType.PRIVATE:
            store_text = f"[{user_name}]: {sanitized_text}"
        else:
            store_text = sanitized_text

        self.db.store_message(chat_id, user_id, "user", store_text)
        self.db.increment_message_count(user_id)

        # Cleanup old messages (enforce sliding window)
        ct = "private" if chat_type == ChatType.PRIVATE else "group"
        self.db.cleanup_old_messages(chat_id, ct)

        if not should_respond:
            return

        # === Step 5: Rate limiting ===
        if not is_own and not self.rate_limiter.is_allowed(user_id):
            wait_time = self.rate_limiter.get_wait_time(user_id)
            try:
                await message.reply_text(
                    f"Arrey beta, itna fast mat type kar 😤\n"
                    f"{wait_time:.0f} seconds ruk ja thoda 💅"
                )
            except Exception:
                pass
            return

        # === Step 6: Bad word filter ===
        bad_words = self.db.get_bad_words()
        if contains_bad_word(text, bad_words) and not is_own:
            logger.info(
                f"[FILTER] Bad word detected from {user_id}"
            )
            try:
                await message.reply_text(
                    "Oye chomu! 😤 Aisi language mat use kar mere saamne!\n"
                    "Thoda tameez se baat kar 💅✨\n"
                    "Warna block karwa dungi Owner se 😏"
                )
            except Exception:
                pass
            return

        # === Step 7: Get chat history for context ===
        memory_limit = (
            Config.MAX_PRIVATE_MEMORY
            if chat_type == ChatType.PRIVATE
            else Config.MAX_GROUP_MEMORY
        )
        chat_history = self.db.get_chat_history(chat_id, memory_limit)

        # === Step 8: Send typing action & generate response ===
        try:
            await chat.send_action(ChatAction.TYPING)
        except Exception:
            pass

        # Use lock to prevent concurrent processing for same chat
        lock = self._get_chat_lock(chat_id)

        async with lock:
            try:
                response = await self.ai.generate_response(
                    user_message=sanitized_text,
                    chat_history=chat_history,
                    is_owner=is_own,
                    user_name=user_name,
                    chat_type=ct
                )
            except Exception as e:
                logger.error(
                    f"[MSG] AI generation error: {e}"
                )
                response = self.ai._fallback_response(is_own)

        # === Step 9: Store bot response in DB ===
        if response:
            self.db.store_message(
                chat_id, 0, "assistant", response
            )
            self.db.cleanup_old_messages(chat_id, ct)

        # === Step 10: Send response ===
        try:
            # Split long messages (Telegram limit: 4096 chars)
            if len(response) > 4000:
                chunks = [
                    response[i:i + 4000]
                    for i in range(0, len(response), 4000)
                ]
                for i, chunk in enumerate(chunks):
                    if i == 0:
                        await message.reply_text(chunk)
                    else:
                        await chat.send_message(chunk)
                    if i < len(chunks) - 1:
                        await asyncio.sleep(0.5)
            else:
                await message.reply_text(response)

            logger.info(
                f"[MSG] Replied to {user_id} in {chat_id} | "
                f"{len(response)} chars"
            )
        except RetryAfter as e:
            logger.warning(
                f"[MSG] Rate limited by Telegram, "
                f"retry after {e.retry_after}s"
            )
            await asyncio.sleep(e.retry_after)
            try:
                await message.reply_text(response)
            except Exception:
                pass
        except Forbidden:
            logger.warning(
                f"[MSG] Bot blocked/kicked from {chat_id}"
            )
        except BadRequest as e:
            logger.error(f"[MSG] Bad request sending reply: {e}")
            try:
                # Try sending without reply
                await chat.send_message(response[:4000])
            except Exception:
                pass
        except Exception as e:
            logger.error(
                f"[MSG] Error sending response: {e}"
            )

    # ========================================================
    #         NEW CHAT MEMBER HANDLER
    # ========================================================

    async def handle_new_members(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Handle when bot is added to a new group."""
        if not update.effective_message:
            return

        message = update.effective_message
        chat = update.effective_chat

        if not message.new_chat_members:
            return

        bot = context.bot
        for member in message.new_chat_members:
            if member.id == bot.id:
                # Bot was added to a new group
                logger.info(
                    f"[EVENT] Bot added to group: "
                    f"{chat.title} ({chat.id})"
                )

                self.db.upsert_chat(
                    chat.id, chat.type,
                    chat.title or ""
                )

                try:
                    welcome = (
                        "Heyyy! 🌸✨\n\n"
                        "Main hoon **Ruhi Ji** — tumhari savage queen! 👑\n"
                        "Mujhse baat karni hai toh bas bolo "
                        "\"Ruhi Ji\" aur main aa jaungi 😏\n\n"
                        "10 minute ka session milega, "
                        "usme jitna marzi baat karo 💅\n\n"
                        "Made by @RUHI_VIG_QNR 🥀"
                    )
                    await chat.send_message(welcome)
                except Exception as e:
                    logger.error(
                        f"[EVENT] Error sending welcome: {e}"
                    )

    async def handle_left_member(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Handle when bot is removed from a group."""
        if not update.effective_message:
            return

        message = update.effective_message
        chat = update.effective_chat
        bot = context.bot

        if message.left_chat_member and message.left_chat_member.id == bot.id:
            logger.info(
                f"[EVENT] Bot removed from group: "
                f"{chat.title} ({chat.id})"
            )
            # Mark chat as inactive
            self.db.execute_query(
                "UPDATE chats SET is_active = FALSE WHERE chat_id = %s",
                (chat.id,)
            )

    # ========================================================
    #              ERROR HANDLER
    # ========================================================

    async def error_handler(
        self, update: object, context: ContextTypes.DEFAULT_TYPE
    ):
        """Global error handler for the bot."""
        error = context.error

        if isinstance(error, NetworkError):
            logger.warning(f"[ERROR] Network error: {error}")
            return

        if isinstance(error, TimedOut):
            logger.warning(f"[ERROR] Request timed out: {error}")
            return

        if isinstance(error, RetryAfter):
            logger.warning(
                f"[ERROR] Rate limited, retry after "
                f"{error.retry_after}s"
            )
            return

        if isinstance(error, Forbidden):
            logger.warning(f"[ERROR] Forbidden: {error}")
            return

        if isinstance(error, BadRequest):
            logger.error(f"[ERROR] Bad request: {error}")
            return

        # Log full traceback for unexpected errors
        logger.error(
            f"[ERROR] Unhandled exception: {error}",
            exc_info=context.error
        )

        # Try to notify the chat
        if update and hasattr(update, "effective_message"):
            try:
                if update.effective_message:
                    await update.effective_message.reply_text(
                        "Oops! Kuch gadbad ho gayi 😭\n"
                        "Dubara try kar na please 🥺✨"
                    )
            except Exception:
                pass

    # ========================================================
    #         PERIODIC TASKS
    # ========================================================

    async def periodic_cleanup(self, context: ContextTypes.DEFAULT_TYPE):
        """Periodic task to clean up expired sessions and old data."""
        logger.info("[PERIODIC] Running cleanup task...")
        try:
            # Clear expired sessions
            self.db.execute_query(
                """UPDATE chats SET active_session_expiry = NULL
                   WHERE active_session_expiry < NOW()"""
            )

            # Clean up very old messages (older than 7 days)
            self.db.execute_query(
                """DELETE FROM messages
                   WHERE timestamp < NOW() - INTERVAL '7 days'"""
            )

            logger.info("[PERIODIC] Cleanup completed ✓")
        except Exception as e:
            logger.error(f"[PERIODIC] Cleanup error: {e}")

    async def periodic_health_check(
        self, context: ContextTypes.DEFAULT_TYPE
    ):
        """Periodic health check for database connectivity."""
        try:
            result = self.db.execute_query(
                "SELECT 1 as ok", fetch_one=True
            )
            if result:
                logger.debug("[HEALTH] Database connection OK ✓")
            else:
                logger.warning("[HEALTH] Database ping returned None!")
        except Exception as e:
            logger.error(f"[HEALTH] Database health check failed: {e}")
            # Try to reinitialize
            try:
                self.db.initialize()
                logger.info("[HEALTH] Database re-initialized ✓")
            except Exception as re_err:
                logger.error(
                    f"[HEALTH] Re-initialization failed: {re_err}"
                )

    # ========================================================
    #       POST-INIT — Register Handlers
    # ========================================================

    async def post_init(self, application: Application):
        """Called after application is initialized."""
        logger.info("[INIT] Post-initialization started...")

        # Set bot commands for Telegram menu
        try:
            from telegram import BotCommand
            commands = [
                BotCommand("start", "Start the bot"),
                BotCommand("help", "Show help menu"),
                BotCommand("profile", "View your profile"),
                BotCommand("clear", "Clear chat memory"),
                BotCommand("reset", "Reset conversation"),
                BotCommand("lang", "Toggle language"),
                BotCommand("personality", "Check bot mood"),
                BotCommand("usage", "Usage statistics"),
                BotCommand("summary", "Summarize recent chat"),
                BotCommand("admin", "Owner dashboard"),
            ]
            await application.bot.set_my_commands(commands)
            logger.info("[INIT] Bot commands registered ✓")
        except Exception as e:
            logger.warning(f"[INIT] Failed to set commands: {e}")

        # Get bot info
        try:
            bot_info = await application.bot.get_me()
            logger.info(
                f"[INIT] Bot username: @{bot_info.username} | "
                f"ID: {bot_info.id}"
            )
        except Exception as e:
            logger.warning(f"[INIT] Failed to get bot info: {e}")

        logger.info("[INIT] Post-initialization complete ✓")

    # ========================================================
    #            BUILD & RUN
    # ========================================================

    def build_application(self) -> Application:
        """Build the Telegram bot application with all handlers."""

        logger.info("[BUILD] Building Telegram application...")

        # Create application with optimized settings
        builder = (
            ApplicationBuilder()
            .token(Config.BOT_TOKEN)
            .post_init(self.post_init)
            .connect_timeout(30)
            .read_timeout(30)
            .write_timeout(30)
            .pool_timeout(30)
            .concurrent_updates(True)
            .http_version("1.1")
        )

        application = builder.build()

        # === Register Command Handlers ===
        # User commands
        application.add_handler(
            CommandHandler("start", self.cmd_start)
        )
        application.add_handler(
            CommandHandler("help", self.cmd_help)
        )
        application.add_handler(
            CommandHandler("profile", self.cmd_profile)
        )
        application.add_handler(
            CommandHandler("clear", self.cmd_clear)
        )
        application.add_handler(
            CommandHandler("reset", self.cmd_reset)
        )
        application.add_handler(
            CommandHandler("lang", self.cmd_lang)
        )
        application.add_handler(
            CommandHandler("personality", self.cmd_personality)
        )
        application.add_handler(
            CommandHandler("usage", self.cmd_usage)
        )
        application.add_handler(
            CommandHandler("summary", self.cmd_summary)
        )

        # Admin commands
        application.add_handler(
            CommandHandler("admin", self.cmd_admin)
        )
        application.add_handler(
            CommandHandler("broadcast", self.cmd_broadcast)
        )
        application.add_handler(
            CommandHandler("totalusers", self.cmd_totalusers)
        )
        application.add_handler(
            CommandHandler("activeusers", self.cmd_activeusers)
        )
        application.add_handler(
            CommandHandler("forceclear", self.cmd_forceclear)
        )
        application.add_handler(
            CommandHandler("ban", self.cmd_ban)
        )
        application.add_handler(
            CommandHandler("unban", self.cmd_unban)
        )
        application.add_handler(
            CommandHandler("badwords", self.cmd_badwords)
        )
        application.add_handler(
            CommandHandler("addbadword", self.cmd_addbadword)
        )
        application.add_handler(
            CommandHandler("removebadword", self.cmd_removebadword)
        )
        application.add_handler(
            CommandHandler("setphrase", self.cmd_setphrase)
        )
        application.add_handler(
            CommandHandler("addadmin", self.cmd_addadmin)
        )
        application.add_handler(
            CommandHandler("removeadmin", self.cmd_removeadmin)
        )
        application.add_handler(
            CommandHandler("shutdown", self.cmd_shutdown)
        )
        application.add_handler(
            CommandHandler("restart", self.cmd_restart)
        )

        # === Callback Query Handler ===
        application.add_handler(
            CallbackQueryHandler(self.handle_callback)
        )

        # === Message Handler (must be last) ===
        application.add_handler(
            MessageHandler(
                filters.TEXT & ~filters.COMMAND,
                self.handle_message
            )
        )

        # === New/Left Member Handlers ===
        application.add_handler(
            MessageHandler(
                filters.StatusUpdate.NEW_CHAT_MEMBERS,
                self.handle_new_members
            )
        )
        application.add_handler(
            MessageHandler(
                filters.StatusUpdate.LEFT_CHAT_MEMBER,
                self.handle_left_member
            )
        )

        # === Error Handler ===
        application.add_error_handler(self.error_handler)

        # === Job Queue (Periodic Tasks) ===
        job_queue = application.job_queue
        if job_queue:
            # Cleanup every 30 minutes
            job_queue.run_repeating(
                self.periodic_cleanup,
                interval=1800,  # 30 minutes
                first=60  # Start after 1 minute
            )
            # Health check every 5 minutes
            job_queue.run_repeating(
                self.periodic_health_check,
                interval=300,  # 5 minutes
                first=30
            )
            logger.info("[BUILD] Periodic jobs scheduled ✓")

        self.application = application
        logger.info("[BUILD] Application built successfully ✓")
        logger.info(
            f"[BUILD] Registered {len(application.handlers[0])} handlers"
        )

        return application

    def run_flask_server(self):
        """Run Flask web server in a separate thread."""
        flask_app = create_web_server(self.db, self.start_time)
        port = Config.PORT

        logger.info(
            f"[WEB] Starting Flask server on 0.0.0.0:{port}"
        )

        # Run Flask in a daemon thread
        flask_thread = threading.Thread(
            target=lambda: flask_app.run(
                host="0.0.0.0",
                port=port,
                debug=False,
                use_reloader=False,
                threaded=True
            ),
            daemon=True,
            name="FlaskWebServer"
        )
        flask_thread.start()
        logger.info(f"[WEB] Flask server started on port {port} ✓")
        return flask_thread

    def run(self):
        """Main entry point — starts both web server and bot."""
        logger.info("=" * 60)
        logger.info("    RUHI JI BOT — STARTING UP 🚀")
        logger.info("=" * 60)
        logger.info(f"  Model: {Config.MODEL_NAME}")
        logger.info(f"  Port: {Config.PORT}")
        logger.info(f"  Owner: @{Config.OWNER_USERNAME}")
        logger.info(f"  Group Memory: {Config.MAX_GROUP_MEMORY} msgs")
        logger.info(f"  Private Memory: {Config.MAX_PRIVATE_MEMORY} msgs")
        logger.info(f"  Session Timeout: {Config.SESSION_TIMEOUT_MINUTES} min")
        logger.info("=" * 60)

        # Step 1: Start Flask web server (for Render.com health checks)
        self.run_flask_server()

        # Step 2: Build and run Telegram bot
        application = self.build_application()

        logger.info("[BOT] Starting Telegram polling...")
        logger.info("=" * 60)
        logger.info("    RUHI JI IS NOW ONLINE! 👑✨")
        logger.info("=" * 60)

        # Run the bot with polling
        # drop_pending_updates=True to avoid processing old messages
        # on restart (important for Render cold starts)
        application.run_polling(
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=True,
            close_loop=False,
            stop_signals=None,  # Handle signals manually
            poll_interval=0.5,  # Fast polling for quick responses
            timeout=30,
            read_timeout=15,
            write_timeout=15,
            connect_timeout=15,
            pool_timeout=15,
        )


# ============================================================
#          WEBHOOK MODE (Alternative for Production)
# ============================================================

class RuhiJiBotWebhook(RuhiJiBot):
    """
    Webhook-based bot runner for production environments.
    Uses the Flask server to receive Telegram webhook updates.
    """

    def __init__(self):
        super().__init__()
        self.webhook_url = os.environ.get("WEBHOOK_URL", "")

    async def setup_webhook(self, application: Application):
        """Set up webhook with Telegram."""
        if not self.webhook_url:
            logger.warning(
                "[WEBHOOK] No WEBHOOK_URL set, skipping webhook setup"
            )
            return False

        try:
            webhook_path = f"/webhook/{Config.BOT_TOKEN}"
            full_url = f"{self.webhook_url}{webhook_path}"

            await application.bot.set_webhook(
                url=full_url,
                allowed_updates=Update.ALL_TYPES,
                drop_pending_updates=True
            )
            logger.info(f"[WEBHOOK] Webhook set to: {full_url} ✓")
            return True
        except Exception as e:
            logger.error(f"[WEBHOOK] Failed to set webhook: {e}")
            return False


# ============================================================
#       GRACEFUL SHUTDOWN HANDLER
# ============================================================

def setup_signal_handlers(bot_instance: RuhiJiBot):
    """Set up graceful shutdown signal handlers."""

    def signal_handler(signum, frame):
        sig_name = signal.Signals(signum).name
        logger.info(
            f"[SHUTDOWN] Received {sig_name}, shutting down gracefully..."
        )

        # Close database connections
        try:
            bot_instance.db.close()
        except Exception as e:
            logger.warning(f"[SHUTDOWN] Error closing DB: {e}")

        logger.info("[SHUTDOWN] Ruhi Ji is going to sleep... 🥺💤")
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)


# ============================================================
#         HEALTH CHECK SELF-PING (Keep Render Alive)
# ============================================================

def start_self_ping():
    """
    Start a background thread that pings the bot's own
    health endpoint to prevent Render from spinning down.
    """
    import urllib.request

    render_url = os.environ.get("RENDER_EXTERNAL_URL", "")
    if not render_url:
        logger.info("[PING] No RENDER_EXTERNAL_URL set, skipping self-ping")
        return

    def ping_loop():
        health_url = f"{render_url}/health"
        while True:
            try:
                time.sleep(600)  # Every 10 minutes
                req = urllib.request.Request(health_url)
                with urllib.request.urlopen(req, timeout=10) as resp:
                    logger.debug(
                        f"[PING] Self-ping OK: {resp.status}"
                    )
            except Exception as e:
                logger.debug(f"[PING] Self-ping failed: {e}")

    ping_thread = threading.Thread(
        target=ping_loop, daemon=True, name="SelfPing"
    )
    ping_thread.start()
    logger.info(f"[PING] Self-ping thread started for {render_url}")


# ============================================================
#              MAIN ENTRY POINT
# ============================================================

def main():
    """
    Main entry point for Ruhi Ji Bot.

    Startup sequence:
    1. Validate environment
    2. Initialize bot components
    3. Set up signal handlers
    4. Start self-ping (for Render)
    5. Start Flask web server
    6. Start Telegram bot polling
    """

    print("""
    ╔══════════════════════════════════════════════════╗
    ║         🌸 RUHI JI — SAVAGE QUEEN 👑            ║
    ║     Telegram Bot powered by Kimi-K2-Instruct    ║
    ║          Made with 💖 by @RUHI_VIG_QNR          ║
    ╚══════════════════════════════════════════════════╝
    """)

    # Validate environment
    if not Config.validate():
        print("\n[FATAL] Missing required environment variables!")
        print("Please set: BOT_TOKEN, HF_TOKEN, DATABASE_URL")
        print("See .env.example for reference")
        sys.exit(1)

    # Create bot instance
    bot = RuhiJiBot()

    # Set up graceful shutdown
    setup_signal_handlers(bot)

    # Start self-ping for Render.com
    start_self_ping()

    # Run the bot (this blocks)
    try:
        bot.run()
    except KeyboardInterrupt:
        logger.info("[MAIN] Keyboard interrupt received")
    except SystemExit:
        logger.info("[MAIN] System exit")
    except Exception as e:
        logger.error(f"[MAIN] Fatal error: {e}")
        logger.error(traceback.format_exc())
        sys.exit(1)
    finally:
        logger.info("[MAIN] Cleaning up...")
        try:
            bot.db.close()
        except Exception:
            pass
        logger.info("[MAIN] Ruhi Ji has shut down. Bye bye! 👋🌸")


# ============================================================
#              SCRIPT EXECUTION
# ============================================================

if __name__ == "__main__":
    main()
    