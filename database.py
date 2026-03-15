#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════╗
║                                                                      ║
║            RUHI JI BOT — DATABASE MODULE v2.0                       ║
║                                                                      ║
║   Production-Grade PostgreSQL Database Manager                      ║
║   Optimized for Neon.tech + Render.com Deployment                   ║
║                                                                      ║
║   Features:                                                         ║
║   ├── ThreadedConnectionPool with Auto-Recovery                    ║
║   ├── Retry Logic with Exponential Backoff                         ║
║   ├── Automatic Table Creation & Migration                         ║
║   ├── Sliding Window Memory Management                              ║
║   ├── Session Tracking with Expiry                                  ║
║   ├── User/Chat CRUD Operations                                    ║
║   ├── Bad Words Management                                          ║
║   ├── Settings Key-Value Store                                      ║
║   ├── Broadcast Logging                                             ║
║   ├── Connection Health Monitoring                                  ║
║   └── Graceful Shutdown                                             ║
║                                                                      ║
║   Made with 💖 by @RUHI_VIG_QNR                                     ║
║                                                                      ║
╚══════════════════════════════════════════════════════════════════════╝
"""

import json
import time
import logging
import threading
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, List, Any, Tuple

import psycopg2
import psycopg2.pool
import psycopg2.extras
from psycopg2 import OperationalError, InterfaceError, ProgrammingError

from config import Config

logger = logging.getLogger("RuhiJiBot.Database")


# ============================================================
#           SQL SCHEMA DEFINITIONS
# ============================================================

CREATE_TABLES_SQL = """
-- ============================================
-- Users Table — Stores all bot users
-- ============================================
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

-- ============================================
-- Chats Table — Stores all chats (group + private)
-- ============================================
CREATE TABLE IF NOT EXISTS chats (
    chat_id BIGINT PRIMARY KEY,
    chat_type VARCHAR(50) DEFAULT 'private',
    title VARCHAR(255) DEFAULT '',
    active_session_expiry TIMESTAMP WITH TIME ZONE DEFAULT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    added_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_activity TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================
-- Messages Table — Sliding window conversation memory
-- ============================================
CREATE TABLE IF NOT EXISTS messages (
    id BIGSERIAL PRIMARY KEY,
    chat_id BIGINT NOT NULL,
    user_id BIGINT NOT NULL,
    role VARCHAR(20) DEFAULT 'user',
    message_text TEXT NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Performance indexes
CREATE INDEX IF NOT EXISTS idx_messages_chat_id
    ON messages(chat_id);
CREATE INDEX IF NOT EXISTS idx_messages_chat_timestamp
    ON messages(chat_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_messages_chat_user
    ON messages(chat_id, user_id);
CREATE INDEX IF NOT EXISTS idx_messages_timestamp
    ON messages(timestamp);

-- ============================================
-- Settings Table — Key-Value configuration store
-- ============================================
CREATE TABLE IF NOT EXISTS settings (
    key VARCHAR(255) PRIMARY KEY,
    value TEXT DEFAULT '',
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================
-- User-Chat Tracking — M:N relationship
-- ============================================
CREATE TABLE IF NOT EXISTS user_chats (
    user_id BIGINT NOT NULL,
    chat_id BIGINT NOT NULL,
    joined_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    PRIMARY KEY (user_id, chat_id)
);

-- ============================================
-- Broadcast Log — Tracks broadcast history
-- ============================================
CREATE TABLE IF NOT EXISTS broadcast_log (
    id BIGSERIAL PRIMARY KEY,
    message_text TEXT,
    sent_count INTEGER DEFAULT 0,
    failed_count INTEGER DEFAULT 0,
    broadcast_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
"""


# ============================================================
#           DATABASE MANAGER CLASS
# ============================================================

class DatabaseManager:
    """
    Production-grade PostgreSQL database manager.
    
    Designed for:
    - Neon.tech serverless PostgreSQL
    - Render.com ephemeral filesystem
    - High-concurrency Telegram bot workload
    """

    def __init__(self, database_url: str = None):
        self.database_url = database_url or Config.DATABASE_URL
        self.pool = None
        self._lock = threading.Lock()
        self._max_retries = Config.DB_MAX_RETRIES
        self._retry_delay = Config.DB_RETRY_DELAY
        self._initialized = False
        self._health_ok = False
        
        logger.info("[DB] DatabaseManager created")

    # ========================================================
    #           CONNECTION MANAGEMENT
    # ========================================================

    def initialize(self):
        """Create connection pool and initialize all tables."""
        try:
            logger.info("[DB] Creating connection pool...")
            
            self.pool = psycopg2.pool.ThreadedConnectionPool(
                minconn=Config.DB_MIN_CONNECTIONS,
                maxconn=Config.DB_MAX_CONNECTIONS,
                dsn=self.database_url,
                connect_timeout=Config.DB_CONNECT_TIMEOUT,
                options=f"-c statement_timeout={Config.DB_STATEMENT_TIMEOUT}"
            )
            
            logger.info("[DB] Connection pool created ✓")
            
            # Create tables
            self._create_tables()
            
            # Seed defaults
            self._seed_default_settings()
            
            self._initialized = True
            self._health_ok = True
            logger.info("[DB] Database fully initialized ✓")
            
        except Exception as e:
            logger.error(f"[DB] Initialization failed: {e}")
            self._health_ok = False
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
                
                # Verify connection is alive
                with conn.cursor() as cur:
                    cur.execute("SELECT 1")
                
                return conn
                
            except (OperationalError, InterfaceError) as e:
                logger.warning(
                    f"[DB] Connection attempt {attempt + 1}/{self._max_retries} "
                    f"failed: {e}"
                )
                if attempt < self._max_retries - 1:
                    time.sleep(self._retry_delay * (attempt + 1))
                    # Reset pool
                    try:
                        if self.pool and not self.pool.closed:
                            self.pool.closeall()
                    except Exception:
                        pass
                    self.pool = None
                else:
                    self._health_ok = False
                    raise
                    
            except Exception as e:
                logger.error(f"[DB] Unexpected connection error: {e}")
                raise

    def _return_connection(self, conn):
        """Return a connection to the pool safely."""
        try:
            if conn and self.pool and not self.pool.closed:
                self.pool.putconn(conn)
        except Exception as e:
            logger.warning(f"[DB] Error returning connection: {e}")

    # ========================================================
    #           QUERY EXECUTION ENGINE
    # ========================================================

    def execute_query(
        self,
        query: str,
        params: tuple = None,
        fetch: bool = False,
        fetch_one: bool = False
    ) -> Any:
        """
        Execute a SQL query with full retry and error handling.
        
        Args:
            query: SQL query string
            params: Query parameters
            fetch: Whether to fetch all results
            fetch_one: Whether to fetch one result
        
        Returns:
            Query results or None
        """
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
                    self._health_ok = True
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
                    self._health_ok = False
                    logger.error(f"[DB] Query failed after all retries")
                    return [] if fetch else None
                    
            except ProgrammingError as e:
                logger.error(f"[DB] SQL error: {e}\nQuery: {query[:200]}")
                if conn:
                    try:
                        conn.rollback()
                    except Exception:
                        pass
                return [] if fetch else None
                
            except Exception as e:
                logger.error(f"[DB] Unexpected query error: {e}")
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

    # Alias for backward compatibility
    def execute(self, query, params=None, fetch=False, fetch_one=False):
        """Alias for execute_query."""
        return self.execute_query(query, params, fetch, fetch_one)

    # ========================================================
    #           TABLE CREATION & SEEDING
    # ========================================================

    def _create_tables(self):
        """Create all required database tables."""
        self.execute_query(CREATE_TABLES_SQL)
        logger.info("[DB] Tables created/verified ✓")

    def _seed_default_settings(self):
        """Insert default settings if they don't exist."""
        defaults = {
            "bad_words": json.dumps(Config.BAD_WORDS_DEFAULT),
            "bot_mood": "savage",
            "maintenance_mode": "false",
            "wake_phrase": "ruhi ji",
            "bot_version": Config.BOT_VERSION,
        }
        for key, value in defaults.items():
            self.execute_query(
                """INSERT INTO settings (key, value, updated_at)
                   VALUES (%s, %s, NOW())
                   ON CONFLICT (key) DO NOTHING""",
                (key, value)
            )
        logger.info("[DB] Default settings seeded ✓")

    # ========================================================
    #           USER OPERATIONS
    # ========================================================

    def upsert_user(
        self, user_id: int, username: str = "",
        first_name: str = "", last_name: str = ""
    ):
        """Insert or update a user."""
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
        """Increment user's message counter."""
        self.execute_query(
            """UPDATE users SET message_count = message_count + 1,
                   last_active = NOW() WHERE user_id = %s""",
            (user_id,)
        )

    def ban_user(self, user_id: int) -> bool:
        self.execute_query(
            "UPDATE users SET is_banned = TRUE WHERE user_id = %s",
            (user_id,)
        )
        return True

    def unban_user(self, user_id: int) -> bool:
        self.execute_query(
            "UPDATE users SET is_banned = FALSE WHERE user_id = %s",
            (user_id,)
        )
        return True

    def is_user_banned(self, user_id: int) -> bool:
        result = self.execute_query(
            "SELECT is_banned FROM users WHERE user_id = %s",
            (user_id,), fetch_one=True
        )
        return result.get("is_banned", False) if result else False

    def get_user_role(self, user_id: int) -> str:
        result = self.execute_query(
            "SELECT role FROM users WHERE user_id = %s",
            (user_id,), fetch_one=True
        )
        return result.get("role", "user") if result else "user"

    def set_user_role(self, user_id: int, role: str):
        self.execute_query(
            "UPDATE users SET role = %s WHERE user_id = %s",
            (role, user_id)
        )

    def set_user_language(self, user_id: int, lang: str):
        self.execute_query(
            "UPDATE users SET language = %s WHERE user_id = %s",
            (lang, user_id)
        )

    def get_user_language(self, user_id: int) -> str:
        result = self.execute_query(
            "SELECT language FROM users WHERE user_id = %s",
            (user_id,), fetch_one=True
        )
        return result.get("language", "hinglish") if result else "hinglish"

    def get_total_users(self) -> int:
        result = self.execute_query(
            "SELECT COUNT(*) as count FROM users", fetch_one=True
        )
        return result.get("count", 0) if result else 0

    def get_active_users(self, hours: int = 24) -> int:
        result = self.execute_query(
            """SELECT COUNT(*) as count FROM users
               WHERE last_active > NOW() - INTERVAL '%s hours'""",
            (hours,), fetch_one=True
        )
        return result.get("count", 0) if result else 0

    def get_banned_users_count(self) -> int:
        result = self.execute_query(
            "SELECT COUNT(*) as count FROM users WHERE is_banned = TRUE",
            fetch_one=True
        )
        return result.get("count", 0) if result else 0

    def get_all_user_ids(self) -> List[int]:
        results = self.execute_query(
            "SELECT user_id FROM users WHERE is_banned = FALSE",
            fetch=True
        )
        return [r["user_id"] for r in results] if results else []

    # ========================================================
    #           CHAT OPERATIONS
    # ========================================================

    def upsert_chat(
        self, chat_id: int, chat_type: str = "private",
        title: str = ""
    ):
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
        result = self.execute_query(
            "SELECT COUNT(*) as count FROM chats", fetch_one=True
        )
        return result.get("count", 0) if result else 0

    def get_all_chat_ids(self) -> List[int]:
        results = self.execute_query(
            "SELECT chat_id FROM chats WHERE is_active = TRUE",
            fetch=True
        )
        return [r["chat_id"] for r in results] if results else []

    # ========================================================
    #           SESSION MANAGEMENT
    # ========================================================

    def set_session_active(self, chat_id: int, minutes: int = 10):
        expiry = datetime.now(timezone.utc) + timedelta(minutes=minutes)
        self.execute_query(
            """INSERT INTO chats (chat_id, active_session_expiry)
               VALUES (%s, %s)
               ON CONFLICT (chat_id)
               DO UPDATE SET active_session_expiry = EXCLUDED.active_session_expiry""",
            (chat_id, expiry)
        )

    def is_session_active(self, chat_id: int) -> bool:
        result = self.execute_query(
            "SELECT active_session_expiry FROM chats WHERE chat_id = %s",
            (chat_id,), fetch_one=True
        )
        if not result or not result.get("active_session_expiry"):
            return False
        expiry = result["active_session_expiry"]
        if expiry.tzinfo is None:
            expiry = expiry.replace(tzinfo=timezone.utc)
        return expiry > datetime.now(timezone.utc)

    def get_active_sessions_count(self) -> int:
        result = self.execute_query(
            "SELECT COUNT(*) as count FROM chats WHERE active_session_expiry > NOW()",
            fetch_one=True
        )
        return result.get("count", 0) if result else 0

    def clear_session(self, chat_id: int):
        self.execute_query(
            "UPDATE chats SET active_session_expiry = NULL WHERE chat_id = %s",
            (chat_id,)
        )

    # ========================================================
    #           MESSAGE / MEMORY OPERATIONS
    # ========================================================

    def store_message(
        self, chat_id: int, user_id: int,
        role: str, message_text: str
    ):
        if not message_text or not message_text.strip():
            return
        text = message_text[:4000]
        self.execute_query(
            """INSERT INTO messages (chat_id, user_id, role, message_text, timestamp)
               VALUES (%s, %s, %s, %s, NOW())""",
            (chat_id, user_id, role, text)
        )

    def get_chat_history(self, chat_id: int, limit: int = 20) -> List[Dict]:
        results = self.execute_query(
            """SELECT role, message_text, user_id, timestamp
               FROM messages WHERE chat_id = %s
               ORDER BY timestamp DESC LIMIT %s""",
            (chat_id, limit), fetch=True
        )
        return list(reversed(results)) if results else []

    def clear_chat_history(self, chat_id: int):
        self.execute_query(
            "DELETE FROM messages WHERE chat_id = %s", (chat_id,)
        )

    def clear_user_history(self, user_id: int):
        self.execute_query(
            "DELETE FROM messages WHERE user_id = %s", (user_id,)
        )

    def get_total_messages(self) -> int:
        result = self.execute_query(
            "SELECT COUNT(*) as count FROM messages", fetch_one=True
        )
        return result.get("count", 0) if result else 0

    def cleanup_old_messages(self, chat_id: int, chat_type: str = "group"):
        limit = (
            Config.MAX_PRIVATE_MEMORY
            if chat_type == "private"
            else Config.MAX_GROUP_MEMORY
        )
        self.execute_query(
            """DELETE FROM messages WHERE id IN (
                SELECT id FROM messages WHERE chat_id = %s
                ORDER BY timestamp DESC OFFSET %s
            )""",
            (chat_id, limit)
        )

    # ========================================================
    #           SETTINGS OPERATIONS
    # ========================================================

    def get_setting(self, key: str, default: str = "") -> str:
        result = self.execute_query(
            "SELECT value FROM settings WHERE key = %s",
            (key,), fetch_one=True
        )
        return result.get("value", default) if result else default

    def set_setting(self, key: str, value: str):
        self.execute_query(
            """INSERT INTO settings (key, value, updated_at)
               VALUES (%s, %s, NOW())
               ON CONFLICT (key) DO UPDATE SET
                   value = EXCLUDED.value, updated_at = NOW()""",
            (key, value)
        )

    def get_bad_words(self) -> List[str]:
        raw = self.get_setting("bad_words", "[]")
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return []

    def add_bad_word(self, word: str) -> bool:
        words = self.get_bad_words()
        w = word.lower().strip()
        if w not in words:
            words.append(w)
            self.set_setting("bad_words", json.dumps(words))
            return True
        return False

    def remove_bad_word(self, word: str) -> bool:
        words = self.get_bad_words()
        w = word.lower().strip()
        if w in words:
            words.remove(w)
            self.set_setting("bad_words", json.dumps(words))
            return True
        return False

    # ========================================================
    #           TRACKING & LOGGING
    # ========================================================

    def track_user_chat(self, user_id: int, chat_id: int):
        self.execute_query(
            """INSERT INTO user_chats (user_id, chat_id, joined_at)
               VALUES (%s, %s, NOW())
               ON CONFLICT (user_id, chat_id) DO NOTHING""",
            (user_id, chat_id)
        )

    def log_broadcast(self, message_text: str, sent: int, failed: int):
        self.execute_query(
            """INSERT INTO broadcast_log
                (message_text, sent_count, failed_count, broadcast_at)
               VALUES (%s, %s, %s, NOW())""",
            (message_text[:500], sent, failed)
        )

    # ========================================================
    #           HEALTH & CLEANUP
    # ========================================================

    def health_check(self) -> bool:
        """Check database connectivity."""
        try:
            result = self.execute_query("SELECT 1 as ok", fetch_one=True)
            self._health_ok = bool(result)
            return self._health_ok
        except Exception:
            self._health_ok = False
            return False

    @property
    def is_healthy(self) -> bool:
        return self._health_ok

    def close(self):
        """Close the connection pool."""
        try:
            if self.pool and not self.pool.closed:
                self.pool.closeall()
                logger.info("[DB] Connection pool closed ✓")
        except Exception as e:
            logger.warning(f"[DB] Error closing pool: {e}")
            