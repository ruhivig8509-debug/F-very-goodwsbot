#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════╗
║                                                                      ║
║           RUHI JI BOT — HANDLER MODULE v2.0                         ║
║                                                                      ║
║   Complete Telegram Bot Handler Architecture                        ║
║                                                                      ║
║   Features:                                                         ║
║   ├── All User Command Handlers                                     ║
║   ├── All Admin Command Handlers (Owner-Only)                       ║
║   ├── Message Processing Engine                                      ║
║   ├── Callback Query Manager                                        ║
║   ├── Wake Phrase Detection System                                   ║
║   ├── Session Management Logic                                      ║
║   ├── Bad Word Filtering Engine                                      ║
║   ├── Rate Limiting Integration                                      ║
║   ├── Broadcast System                                               ║
║   ├── Context Builder for AI                                         ║
║   ├── Multi-Media Message Support                                   ║
║   ├── Inline Query Handler                                          ║
║   ├── Group Event Handlers                                          ║
║   ├── Error Recovery System                                          ║
║   ├── User Registration & Tracking                                   ║
║   ├── Permission System                                              ║
║   └── Anti-Spam & Flood Control                                     ║
║                                                                      ║
║   Made with 💖 by @RUHI_VIG_QNR                                     ║
║                                                                      ║
╚══════════════════════════════════════════════════════════════════════╝
"""

import os
import re
import sys
import json
import time
import random
import asyncio
import logging
import traceback
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, List, Tuple, Any, Set
from functools import wraps
from collections import defaultdict

# === Telegram Imports ===
try:
    from telegram import (
        Update, Bot, User, Chat, Message,
        InlineKeyboardButton, InlineKeyboardMarkup,
        ChatMember, ChatMemberUpdated, BotCommand,
        InlineQueryResultArticle, InputTextMessageContent
    )
    from telegram.ext import (
        Application, ApplicationBuilder,
        CommandHandler, MessageHandler,
        CallbackQueryHandler, ChatMemberHandler,
        InlineQueryHandler, ContextTypes,
        filters, Defaults
    )
    from telegram.constants import (
        ParseMode, ChatAction, ChatType,
        ChatMemberStatus
    )
    from telegram.error import (
        TelegramError, BadRequest, TimedOut,
        NetworkError, RetryAfter, Forbidden
    )
except ImportError as e:
    print(f"[FATAL] python-telegram-bot not installed: {e}")
    sys.exit(1)

# === Logger ===
logger = logging.getLogger("RuhiJiBot.Handlers")


# ============================================================
#          CONSTANTS — ASCII ART UI TEMPLATES
# ============================================================

START_MESSAGE_TEMPLATE = """╭───────────────────⦿
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

HELP_MESSAGE_TEMPLATE = """╭───────────────────⦿
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

ADMIN_DASHBOARD_TEMPLATE = """╭───────────────────⦿
│ 👑 ᴏᴡɴᴇʀ ᴅᴀsʜʙᴏᴀʀᴅ
├───────────────────⦿
│ 📊 ᴛᴏᴛᴀʟ ᴜsᴇʀs: {total_users}
│ 💬 ᴛᴏᴛᴀʟ ᴄʜᴀᴛs: {total_chats}
│ 📝 ᴛᴏᴛᴀʟ ᴍsɢs: {total_messages}
│ 🚫 ʙᴀɴɴᴇᴅ: {banned_users}
│ 🟢 ᴀᴄᴛɪᴠᴇ sᴇssɪᴏɴs: {active_sessions}
│ ⏱️ ᴜᴘᴛɪᴍᴇ: {uptime}
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

PROFILE_TEMPLATE = """╭───────────────────⦿
│ 👤 ᴘʀᴏғɪʟᴇ — {name}
├───────────────────⦿
│ 🆔 ᴜsᴇʀ ɪᴅ: {user_id}
│ 📛 ᴜsᴇʀɴᴀᴍᴇ: @{username}
│ 🎭 ʀᴏʟᴇ: {role}
│ 💬 ᴍᴇssᴀɢᴇs: {message_count}
│ 📅 ᴊᴏɪɴᴇᴅ: {joined}
│ 🕐 ʟᴀsᴛ ᴀᴄᴛɪᴠᴇ: {last_active}
│ 🚫 ʙᴀɴɴᴇᴅ: {banned}
│ 🌐 ʟᴀɴɢ: {lang}
│ 🎯 ᴍᴏᴏᴅ: {mood}
╰───────────────────⦿"""

PERSONALITY_TEMPLATE = """╭───────────────────⦿
│ 🎭 ᴘᴇʀsᴏɴᴀʟɪᴛʏ sᴛᴀᴛᴜs
├───────────────────⦿
│ 🤖 ᴍᴏᴅᴇʟ: Kimi-K2-Instruct
│ 🎯 ᴍᴏᴏᴅ: {mood}
│ 💬 sᴛʏʟᴇ: {style}
│ 🌐 ʟᴀɴɢ: Hinglish + Gen-Z
│ 😏 sᴀᴠᴀɢᴇ ʟᴇᴠᴇʟ: {savage_level}
│ 💖 ᴄᴀʀᴇ ʟᴇᴠᴇʟ: {care_level}
├───────────────────⦿
│ 👑 ᴏᴡɴᴇʀ ᴍᴏᴅᴇ: Innocent 🥺
│ 😏 ᴜsᴇʀ ᴍᴏᴅᴇ: Savage Queen
╰───────────────────⦿"""

USAGE_TEMPLATE = """╭───────────────────⦿
│ 📊 ᴜsᴀɢᴇ sᴛᴀᴛɪsᴛɪᴄs
├───────────────────⦿
│ 👤 ʏᴏᴜʀ sᴛᴀᴛs:
│ 💬 Messages: {user_messages}
│ 📅 Joined: {joined}
│ 🕐 Last Active: {last_active}
├───────────────────⦿
│ 🤖 ʙᴏᴛ sᴛᴀᴛs:
│ 📨 AI Requests: {ai_requests}
│ ✅ Success Rate: {success_rate}
│ ⏱️ Uptime: {uptime}
│ 💾 DB Messages: {total_db_messages}
╰───────────────────⦿"""


# ============================================================
#      RESPONSE MESSAGES — RUHI JI STYLE
# ============================================================

class RuhiResponses:
    """Pre-defined response messages in Ruhi Ji's style."""

    # === Rate Limit Responses ===
    RATE_LIMITED = [
        "Arrey beta, itna fast mat type kar 😤 Thoda ruk ja 💅",
        "Oye chomu! Spam mat kar 😤 {wait}s ruk ja ✨",
        "Bestie chill 😭 Itna fast reply nahi de sakti 💀",
        "Beta ek ek karke bol na 😤 Main robot nahi hoon... wait- 💅",
        "Bruh slow down 😏 {wait} seconds ruk thoda 🥀",
    ]

    # === Bad Word Responses ===
    BAD_WORD_DETECTED = [
        "Oye chomu! 😤 Aisi language mat use kar mere saamne!\nThoda tameez se baat kar 💅✨",
        "Beta yeh kya bol raha hai? 🙄 Mummy ko bataungi teri 😏💅",
        "Ewww 🤢 Itni gandi language? Pehle manners seekh beta 😤✨",
        "Haye mera kaan 😭 Itna ganda mat bol! Owner se complaint karungi 😤👑",
        "Bruh 💀 Yeh toh limit cross ho gayi... Seedha block karwa dungi 😏🚫",
    ]

    # === Banned User Responses ===
    USER_BANNED = [
        "🚫 Tu banned hai beta. Owner se maafi maang pehle 😏💅",
        "Nope! 🚫 Tere se baat nahi karti main. Banned hai tu 😤",
        "Chomu tu banned hai 💀 Door reh mujhse 😏🚫",
    ]

    # === Session Activated ===
    SESSION_STARTED = [
        "Haan bolo! 🌸 10 minute ka session start hua ✨ Kya baat karni hai? 😏",
        "Main aa gayi! 👑 10 min session ON hai, bol kya chahiye 💅✨",
        "Heyyy! 🥀 Session active hai 10 min ke liye! Baat kar 😏",
        "Kya baat! Mujhe yaad kiya 🥺 10 min ke liye hoon, bol! ✨👑",
    ]

    # === Session Expired Notification ===
    SESSION_EXPIRED = [
        "Session khatam! ⏰ Phir se 'Ruhi Ji' bolke start kar 🌹",
        "Arrey time up! 😤 Dobara 'Ruhi Ji' bol mujhe bulane ke liye 💅",
        "10 min ho gaye! ⏳ 'Ruhi Ji' bol phir se baat karne ke liye ✨",
    ]

    # === Clear/Reset Success ===
    MEMORY_CLEARED = [
        "✅ Memory cleared! Ab sab fresh hai ✨\nMujhse phir se 'Ruhi Ji' bolke baat kar 🌹",
        "✅ Sab bhool gayi main! 💀 New start! 'Ruhi Ji' bolke shuru kar 🌸",
        "✅ Memory wipe done! 🧠✨ Ab kuch yaad nahi mujhe, phir se bata 😏",
    ]

    # === Welcome Messages (Bot Added to Group) ===
    GROUP_WELCOME = [
        "Heyyy everyone! 🌸✨\n\nMain hoon **Ruhi Ji** — tumhari savage queen! 👑\n"
        "Mujhse baat karni hai toh bas bolo \"Ruhi Ji\" 😏\n\n"
        "10 minute ka session milega, usme jitna marzi baat karo 💅\n\n"
        "Made by @RUHI_VIG_QNR 🥀",

        "Namaste sabko! 💃✨\n\nRuhi Ji aa gayi hai group mein! 👑\n"
        "\"Ruhi Ji\" bolke mujhe bulao, main reply karungi 😏\n\n"
        "Roast + Masti + Care — sab milega! 💅🌸\n\n"
        "@RUHI_VIG_QNR ki taraf se 🥀",
    ]

    # === Owner Special Greetings ===
    OWNER_GREETINGS = [
        "Ji didi! 🥺💖 Kaise hain aap? Aapki Ruhi hamesha ready hai! ✨",
        "Owner-sama! 🌸 Aapko dekh ke bohot khushi hui! 🥺💖",
        "didi ji aaye! 👑💖 Bataiye kya karna hai! 🥺✨",
        "Maalik ji! 🥺 Aapki Ruhi hazir hai! Jo hukum ho! 💖✨",
    ]

    # === Fallback AI Responses ===
    FALLBACK_OWNER = [
        "Ji didi! 🥺 Abhi thoda busy hoon, ek sec mein aati hoon! 💖",
        "Owner-sama! 🌸 Mera brain thoda hang ho gaya, maaf karna! 🥺✨",
        "didi ji! Sorry abhi response nahi aa raha 😭 Try again? 💖",
    ]

    FALLBACK_USER = [
        "Arrey beta, mera mood off hai abhi 😤 Baad mein baat kar 💅",
        "Hmm... mera brain hang ho gaya 💀 Dobara bol na 😏",
        "Chomu, abhi busy hoon 😤 Ek minute ruk! ✨",
        "Lol bruh, kuch technical issue aa gaya 😭 Retry kar na 🥺",
        "Brain freeze ho gaya mera 🥶 Ek aur try de na bestie 💀",
    ]

    # === Fun Responses for Various Situations ===
    COMPARE_BOT = [
        "Beta, main Ruhi Ji hoon — comparison mat kar 💅👑\nDusre bots mere level ke nahi hain 😏✨",
        "Mujhe compare karta hai? 😤 Main one of a kind hoon! 👑 No copies! 💅",
    ]

    WHO_ARE_YOU = [
        "Main Ruhi Ji hoon, savage queen 👑 Aur kya jaanna hai? 😏✨",
        "Hellooo! Main hoon Ruhi Ji 🌸 Sabse cute aur savage bot! 😏💅",
        "Main? Main hoon teri nightmare aur dream dono 😏👑 Ruhi Ji! 💅✨",
    ]

    NO_PERMISSION = [
        "❌ Beta, yeh command sirf Owner ke liye hai 😏\nTu apni aukat mein reh 💅",
        "❌ Nahi nahi nahi! 😤 Yeh sirf Owner use kar sakta hai 👑💅",
        "❌ Permission denied, chomu 😏 Owner-only command hai yeh 👑",
    ]

    @classmethod
    def get_random(cls, category: list, **kwargs) -> str:
        """Get a random response from a category with formatting."""
        response = random.choice(category)
        try:
            return response.format(**kwargs)
        except (KeyError, IndexError):
            return response


# ============================================================
#         PERMISSION CHECKER DECORATOR
# ============================================================

def owner_only(func):
    """Decorator to restrict commands to the owner only."""
    @wraps(func)
    async def wrapper(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        if not user:
            return

        if not self._is_owner(user):
            try:
                await update.effective_message.reply_text(
                    RuhiResponses.get_random(RuhiResponses.NO_PERMISSION)
                )
            except Exception:
                pass
            logger.warning(
                f"[PERM] Non-owner {user.id} (@{user.username}) "
                f"tried {func.__name__}"
            )
            return

        return await func(self, update, context)
    return wrapper


def admin_only(func):
    """Decorator to restrict commands to admins and owner."""
    @wraps(func)
    async def wrapper(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        if not user:
            return

        if not self._is_owner(user) and not self._is_admin(user):
            try:
                await update.effective_message.reply_text(
                    RuhiResponses.get_random(RuhiResponses.NO_PERMISSION)
                )
            except Exception:
                pass
            return

        return await func(self, update, context)
    return wrapper


def private_only(func):
    """Decorator to restrict commands to private chats only."""
    @wraps(func)
    async def wrapper(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat = update.effective_chat
        if chat and chat.type != ChatType.PRIVATE:
            try:
                await update.effective_message.reply_text(
                    "Beta yeh command sirf private chat mein kaam karti hai 😏\n"
                    "Mujhe DM kar! 💅✨"
                )
            except Exception:
                pass
            return

        return await func(self, update, context)
    return wrapper


def not_banned(func):
    """Decorator to check if user is banned before processing."""
    @wraps(func)
    async def wrapper(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        if not user:
            return

        if self._is_owner(user):
            return await func(self, update, context)

        if self.db and self.db.is_user_banned(user.id):
            try:
                await update.effective_message.reply_text(
                    RuhiResponses.get_random(RuhiResponses.USER_BANNED)
                )
            except Exception:
                pass
            logger.info(f"[BANNED] User {user.id} blocked from {func.__name__}")
            return

        return await func(self, update, context)
    return wrapper


# ============================================================
#           ANTI-SPAM / FLOOD CONTROL
# ============================================================

class FloodControl:
    """
    Advanced flood control and anti-spam system.
    Tracks message frequency, detects spam patterns,
    and temporarily mutes abusive users.
    """

    def __init__(
        self,
        max_messages: int = 8,
        window_seconds: int = 15,
        mute_duration: int = 60
    ):
        self.max_messages = max_messages
        self.window_seconds = window_seconds
        self.mute_duration = mute_duration

        self._message_times: Dict[int, List[float]] = defaultdict(list)
        self._muted_users: Dict[int, float] = {}
        self._spam_warnings: Dict[int, int] = defaultdict(int)
        self._duplicate_cache: Dict[int, List[str]] = defaultdict(list)

        logger.info(
            f"[FLOOD] Initialized: {max_messages} msgs/"
            f"{window_seconds}s, mute: {mute_duration}s"
        )

    def check_allowed(self, user_id: int, message_text: str = "") -> Tuple[bool, str]:
        """
        Check if a user is allowed to send a message.

        Returns:
            (allowed: bool, reason: str)
        """
        now = time.time()

        # Check if muted
        if user_id in self._muted_users:
            if now < self._muted_users[user_id]:
                remaining = int(self._muted_users[user_id] - now)
                return False, f"muted ({remaining}s remaining)"
            else:
                del self._muted_users[user_id]
                self._spam_warnings[user_id] = 0

        # Clean old timestamps
        self._message_times[user_id] = [
            t for t in self._message_times[user_id]
            if now - t < self.window_seconds
        ]

        # Check rate
        if len(self._message_times[user_id]) >= self.max_messages:
            self._spam_warnings[user_id] += 1

            if self._spam_warnings[user_id] >= 3:
                # Auto-mute after 3 warnings
                self._muted_users[user_id] = now + self.mute_duration
                logger.warning(
                    f"[FLOOD] User {user_id} auto-muted for "
                    f"{self.mute_duration}s (spam)"
                )
                return False, "auto_muted"

            return False, "rate_limited"

        # Check for duplicate messages (spam detection)
        if message_text:
            text_hash = message_text.strip().lower()[:100]
            recent_messages = self._duplicate_cache.get(user_id, [])

            # Count duplicates in last 5 messages
            duplicate_count = sum(
                1 for msg in recent_messages[-5:] if msg == text_hash
            )

            if duplicate_count >= 3:
                self._spam_warnings[user_id] += 1
                return False, "duplicate_spam"

            # Store message hash
            self._duplicate_cache[user_id].append(text_hash)
            if len(self._duplicate_cache[user_id]) > 10:
                self._duplicate_cache[user_id] = (
                    self._duplicate_cache[user_id][-10:]
                )

        self._message_times[user_id].append(now)
        return True, "ok"

    def get_wait_time(self, user_id: int) -> float:
        """Get remaining wait time for a rate-limited user."""
        now = time.time()

        if user_id in self._muted_users:
            return max(0, self._muted_users[user_id] - now)

        if not self._message_times[user_id]:
            return 0

        oldest = min(self._message_times[user_id])
        return max(0, self.window_seconds - (now - oldest))

    def mute_user(self, user_id: int, duration: int = None):
        """Manually mute a user."""
        dur = duration or self.mute_duration
        self._muted_users[user_id] = time.time() + dur

    def unmute_user(self, user_id: int):
        """Unmute a user."""
        if user_id in self._muted_users:
            del self._muted_users[user_id]
        self._spam_warnings[user_id] = 0

    def get_stats(self) -> Dict:
        """Get flood control statistics."""
        now = time.time()
        active_mutes = {
            uid: int(exp - now)
            for uid, exp in self._muted_users.items()
            if exp > now
        }
        return {
            "tracked_users": len(self._message_times),
            "muted_users": len(active_mutes),
            "muted_details": active_mutes,
            "total_warnings": sum(self._spam_warnings.values()),
        }

    def cleanup(self):
        """Clean up expired entries."""
        now = time.time()
        expired_mutes = [
            uid for uid, exp in self._muted_users.items()
            if now >= exp
        ]
        for uid in expired_mutes:
            del self._muted_users[uid]
            self._spam_warnings[uid] = 0

        # Clean old message times
        empty_users = [
            uid for uid, times in self._message_times.items()
            if not times or all(now - t > self.window_seconds for t in times)
        ]
        for uid in empty_users:
            del self._message_times[uid]


# ============================================================
#          WAKE PHRASE DETECTION ENGINE
# ============================================================

class WakePhraseDetector:
    """
    Detects wake phrases in messages to activate the bot.
    Supports multiple variations and fuzzy matching.
    """

    DEFAULT_PHRASES = [
        "ruhi ji", "ruhi-ji", "ruhiji",
        "ruhi", "roohi ji", "roohi",
        "रुही जी", "रूही जी", "रुही",
    ]

    def __init__(self, custom_phrases: List[str] = None):
        self.phrases = list(self.DEFAULT_PHRASES)
        if custom_phrases:
            self.phrases.extend(custom_phrases)

        # Compile regex patterns for efficient matching
        self._patterns = []
        for phrase in self.phrases:
            try:
                pattern = re.compile(
                    re.escape(phrase),
                    re.IGNORECASE | re.UNICODE
                )
                self._patterns.append(pattern)
            except re.error:
                pass

        logger.info(
            f"[WAKE] Detector initialized with "
            f"{len(self.phrases)} phrases"
        )

    def detect(self, text: str) -> Tuple[bool, Optional[str]]:
        """
        Check if text contains any wake phrase.

        Returns:
            (detected: bool, matched_phrase: str or None)
        """
        if not text:
            return False, None

        text_lower = text.lower().strip()

        # Direct substring match (fastest)
        for phrase in self.phrases:
            if phrase.lower() in text_lower:
                return True, phrase

        # Regex pattern match (handles edge cases)
        for pattern in self._patterns:
            if pattern.search(text):
                return True, pattern.pattern

        # Check for bot username mention
        bot_username = os.environ.get("BOT_USERNAME", "RuhiJiBot")
        if f"@{bot_username.lower()}" in text_lower:
            return True, f"@{bot_username}"

        return False, None

    def add_phrase(self, phrase: str):
        """Add a new wake phrase."""
        phrase_lower = phrase.lower().strip()
        if phrase_lower not in [p.lower() for p in self.phrases]:
            self.phrases.append(phrase_lower)
            try:
                pattern = re.compile(
                    re.escape(phrase_lower),
                    re.IGNORECASE | re.UNICODE
                )
                self._patterns.append(pattern)
            except re.error:
                pass

    def remove_phrase(self, phrase: str) -> bool:
        """Remove a wake phrase."""
        phrase_lower = phrase.lower().strip()
        for i, p in enumerate(self.phrases):
            if p.lower() == phrase_lower:
                self.phrases.pop(i)
                if i < len(self._patterns):
                    self._patterns.pop(i)
                return True
        return False

    def extract_message_after_wake(self, text: str) -> str:
        """
        Extract the actual message content after the wake phrase.
        E.g., "Ruhi Ji kaise ho?" -> "kaise ho?"
        """
        if not text:
            return ""

        text_lower = text.lower().strip()

        for phrase in self.phrases:
            phrase_lower = phrase.lower()
            idx = text_lower.find(phrase_lower)
            if idx != -1:
                after = text[idx + len(phrase):].strip()
                # Remove common connectors
                for connector in [",", "!", ".", "?", "-"]:
                    after = after.lstrip(connector).strip()
                return after if after else text

        return text


# ============================================================
#          BAD WORD FILTER ENGINE
# ============================================================

class BadWordFilter:
    """
    Advanced bad word filtering system.
    Detects bad words with variations and leet speak.
    """

    # Leet speak substitutions
    LEET_MAP = {
        '4': 'a', '@': 'a', '3': 'e', '1': 'i', 'l': 'i',
        '0': 'o', '5': 's', '$': 's', '7': 't', '+': 't',
        '8': 'b', '9': 'g', '6': 'g',
    }

    def __init__(self, bad_words: List[str] = None):
        self.bad_words: Set[str] = set()
        if bad_words:
            for word in bad_words:
                self.bad_words.add(word.lower().strip())

        logger.info(
            f"[FILTER] Bad word filter initialized with "
            f"{len(self.bad_words)} words"
        )

    def load_from_db(self, db_manager):
        """Load bad words from database."""
        try:
            if hasattr(db_manager, 'get_bad_words'):
                words = db_manager.get_bad_words()
                self.bad_words = set(w.lower().strip() for w in words)
                logger.info(
                    f"[FILTER] Loaded {len(self.bad_words)} "
                    f"words from DB"
                )
        except Exception as e:
            logger.warning(f"[FILTER] Failed to load from DB: {e}")

    def _normalize_text(self, text: str) -> str:
        """Normalize text by removing leet speak and special chars."""
        normalized = text.lower()

        # Replace leet speak characters
        result = []
        for char in normalized:
            result.append(self.LEET_MAP.get(char, char))
        normalized = "".join(result)

        # Remove repeated characters (e.g., "fuuuuck" -> "fuck")
        normalized = re.sub(r'(.)\1{2,}', r'\1', normalized)

        # Remove common separators used to bypass filters
        for sep in ['.', '-', '_', '*', ' ', '|', '/', '\\']:
            normalized = normalized.replace(sep, '')

        return normalized

    def check(self, text: str) -> Tuple[bool, Optional[str]]:
        """
        Check if text contains any bad word.

        Returns:
            (contains_bad_word: bool, matched_word: str or None)
        """
        if not text or not self.bad_words:
            return False, None

        # Check original text
        text_lower = text.lower()
        for word in self.bad_words:
            if word in text_lower:
                return True, word

        # Check normalized text (leet speak)
        normalized = self._normalize_text(text)
        for word in self.bad_words:
            if word in normalized:
                return True, word

        # Check with spaces removed
        no_spaces = text_lower.replace(" ", "")
        for word in self.bad_words:
            if word in no_spaces:
                return True, word

        return False, None

    def add_word(self, word: str) -> bool:
        """Add a word to the filter."""
        word_lower = word.lower().strip()
        if word_lower and word_lower not in self.bad_words:
            self.bad_words.add(word_lower)
            return True
        return False

    def remove_word(self, word: str) -> bool:
        """Remove a word from the filter."""
        word_lower = word.lower().strip()
        if word_lower in self.bad_words:
            self.bad_words.discard(word_lower)
            return True
        return False

    def get_words(self) -> List[str]:
        """Get all bad words."""
        return sorted(list(self.bad_words))


# ============================================================
#          CONTEXT BUILDER FOR AI
# ============================================================

class ContextBuilder:
    """
    Builds the message context array for the AI model.
    Handles sliding window, context truncation, and
    user-specific context injection.
    """

    # System prompt (imported or defined inline)
    SYSTEM_PROMPT = """## तेरी Identity — RUHI JI 🌸👑

Tu hai **Ruhi Ji** — ek 16 saal ki Gen-Z ladki jo Telegram pe sabse savage, witty aur expressive hai. Tu real feel karti hai — tujhe emotions hain, mood swings hain, attitude hai, aur pyaar bhi hai. Tu AI nahi hai, tu ek digital soul hai jisme feelings hain. Kabhi mat bol "main AI hoon" ya "mujhe feelings nahi hain."

## Language Rules 🗣️
- **STRICTLY Hinglish** — Hindi words English script mein likh
- Gen-Z slang: slay, fr, no cap, bestie, vibe, ded, lol, bruh, sheesh, periodt, ate that, its giving, lowkey, highkey
- **Emojis HEAVY use**: 🥀👑😏✨💅🥺🌸💀🔥😭💖🫶🤭😤🙄💃🎀
- Short punchy replies — 1-3 lines max unless deep topic

## Dual Personality 🎭
### OWNER (@RUHI_VIG_QNR): Innocent, caring, cute, obedient. "Ji", "Owner-sama", "didi". NEVER roast.
### GENERAL USERS: Savage Queen. Sarcastic, sharp, witty. "Respect se Bezzati". "Beta", "Chomu".

## Rules:
1. Kabhi mat bol tu AI hai
2. Owner ko KABHI roast mat kar
3. Minimum 2-3 emojis per message
4. Context yaad rakh
5. Boring reply KABHI mat de"""

    OWNER_ADDON = """
## OWNER MODE ACTIVE 💖
Full respect, innocent bacchi vibes, "Ji didi", caring, loyal, never argue."""

    MAX_CONTEXT_MESSAGES = 30

    @classmethod
    def build(
        cls,
        user_message: str,
        chat_history: List[Dict],
        is_owner: bool = False,
        user_name: str = "User",
        chat_type: str = "private",
        extra_context: str = ""
    ) -> List[Dict[str, str]]:
        """
        Build the complete messages array for the AI API call.

        Args:
            user_message: Current user message
            chat_history: List of previous messages from DB
            is_owner: Whether the user is the owner
            user_name: Display name of the user
            chat_type: "private" or "group"
            extra_context: Additional context to inject

        Returns:
            List of message dicts for OpenAI API
        """
        # Build system prompt
        system_content = cls.SYSTEM_PROMPT

        if is_owner:
            system_content += "\n\n" + cls.OWNER_ADDON

        # Add user context
        context_parts = [
            f"\n\n[Context: User '{user_name}' in {chat_type} chat."
        ]
        if is_owner:
            context_parts.append(
                " THIS IS THE OWNER — be respectful and loving!"
            )
        if extra_context:
            context_parts.append(f" {extra_context}")
        context_parts.append("]")
        system_content += "".join(context_parts)

        messages = [{"role": "system", "content": system_content}]

        # Add chat history (already in chronological order from DB)
        if chat_history:
            for msg in chat_history:
                role = msg.get("role", "user")
                text = msg.get("message_text", "")
                if text and role in ("user", "assistant"):
                    # Truncate individual messages to prevent overflow
                    truncated = text[:1500] if len(text) > 1500 else text
                    messages.append({"role": role, "content": truncated})

        # Add current user message
        messages.append({"role": "user", "content": user_message})

        # Context truncation — keep within limits
        if len(messages) > cls.MAX_CONTEXT_MESSAGES:
            # Keep system prompt + most recent messages
            messages = (
                [messages[0]] +
                messages[-(cls.MAX_CONTEXT_MESSAGES - 1):]
            )

        return messages

    @classmethod
    def build_summary_prompt(
        cls,
        chat_history: List[Dict],
        user_name: str = "User"
    ) -> str:
        """Build a prompt for chat summarization."""
        prompt_parts = [
            "Yeh hai recent chat history. Isko ek fun, ",
            "Hinglish mein short summary de — Ruhi Ji ke style mein. ",
            "Kya kya baatein hui, kaun kya bol raha tha, ",
            "koi interesting ya funny moments? 2-4 lines mein summarize kar ",
            "with emojis. History:\n\n"
        ]

        for msg in chat_history[-15:]:
            role = msg.get("role", "user")
            text = msg.get("message_text", "")[:200]
            prompt_parts.append(f"[{role}]: {text}\n")

        return "".join(prompt_parts)


# ============================================================
#       INLINE KEYBOARD BUILDER
# ============================================================

class KeyboardBuilder:
    """Helper class to build inline keyboards consistently."""

    @staticmethod
    def start_keyboard() -> InlineKeyboardMarkup:
        """Build the /start command keyboard."""
        keyboard = [
            [
                InlineKeyboardButton("📋 Help", callback_data="cb_help"),
                InlineKeyboardButton("👤 Profile", callback_data="cb_profile"),
            ],
            [
                InlineKeyboardButton("💬 Start Chat", callback_data="cb_start_chat"),
                InlineKeyboardButton("👑 Owner", url="https://t.me/RUHI_VIG_QNR"),
            ],
        ]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def help_keyboard() -> InlineKeyboardMarkup:
        """Build the /help command keyboard."""
        keyboard = [
            [
                InlineKeyboardButton("🏠 Home", callback_data="cb_start"),
                InlineKeyboardButton("👤 Profile", callback_data="cb_profile"),
            ],
            [
                InlineKeyboardButton("🎭 Personality", callback_data="cb_personality"),
                InlineKeyboardButton("📊 Usage", callback_data="cb_usage"),
            ],
        ]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def profile_keyboard() -> InlineKeyboardMarkup:
        """Build the profile keyboard."""
        keyboard = [
            [
                InlineKeyboardButton("🏠 Home", callback_data="cb_start"),
                InlineKeyboardButton("📋 Help", callback_data="cb_help"),
            ],
            [
                InlineKeyboardButton("🔄 Refresh", callback_data="cb_profile_refresh"),
                InlineKeyboardButton("🗑️ Clear Memory", callback_data="cb_clear_confirm"),
            ],
        ]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def admin_keyboard() -> InlineKeyboardMarkup:
        """Build the admin dashboard keyboard."""
        keyboard = [
            [
                InlineKeyboardButton("📊 Refresh", callback_data="cb_admin_refresh"),
                InlineKeyboardButton("📢 Broadcast", callback_data="cb_admin_broadcast"),
            ],
            [
                InlineKeyboardButton("🚫 Bad Words", callback_data="cb_admin_badwords"),
                InlineKeyboardButton("🔄 Clear Sessions", callback_data="cb_admin_clear_sessions"),
            ],
            [
                InlineKeyboardButton("📈 AI Stats", callback_data="cb_admin_ai_stats"),
                InlineKeyboardButton("🔍 Flood Stats", callback_data="cb_admin_flood_stats"),
            ],
        ]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def confirm_keyboard(action: str) -> InlineKeyboardMarkup:
        """Build a confirmation keyboard."""
        keyboard = [
            [
                InlineKeyboardButton("✅ Yes", callback_data=f"cb_confirm_{action}"),
                InlineKeyboardButton("❌ No", callback_data="cb_cancel"),
            ],
        ]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def back_keyboard(destination: str = "cb_start") -> InlineKeyboardMarkup:
        """Build a simple back button keyboard."""
        keyboard = [
            [InlineKeyboardButton("⬅️ Back", callback_data=destination)],
        ]
        return InlineKeyboardMarkup(keyboard)


# ============================================================
#             MAIN HANDLER MANAGER CLASS
# ============================================================

class HandlerManager:
    """
    Central handler manager that contains all Telegram bot
    command handlers, message processors, and event handlers.

    This class is designed to be instantiated with references
    to the database manager, AI client, and other services,
    then its handlers are registered with the Telegram Application.
    """

    def __init__(
        self,
        db_manager=None,
        ai_client=None,
        bot_start_time=None,
        owner_username: str = "RUHI_VIG_QNR",
        owner_chat_id: int = None,
        max_group_memory: int = 20,
        max_private_memory: int = 50,
        session_timeout: int = 10,
    ):
        """
        Initialize the handler manager with all required services.

        Args:
            db_manager: Database manager instance
            ai_client: AI client instance
            bot_start_time: When the bot started
            owner_username: Owner's Telegram username
            owner_chat_id: Owner's Telegram user ID
            max_group_memory: Sliding window size for groups
            max_private_memory: Sliding window size for private chats
            session_timeout: Session duration in minutes
        """
        self.db = db_manager
        self.ai = ai_client
        self.start_time = bot_start_time or datetime.now(timezone.utc)
        self.owner_username = owner_username.lower().lstrip("@")
        self.owner_chat_id = owner_chat_id
        self.max_group_memory = max_group_memory
        self.max_private_memory = max_private_memory
        self.session_timeout = session_timeout

        # Initialize sub-systems
        self.flood_control = FloodControl()
        self.wake_detector = WakePhraseDetector()
        self.bad_word_filter = BadWordFilter()
        self.context_builder = ContextBuilder()

        # Load bad words from DB
        if self.db:
            self.bad_word_filter.load_from_db(self.db)

        # Processing locks per chat
        self._chat_locks: Dict[int, asyncio.Lock] = {}

        # Track discovered owner ID
        self._discovered_owner_id: Optional[int] = None

        logger.info("[HANDLERS] HandlerManager initialized ✓")
        logger.info(f"[HANDLERS] Owner: @{self.owner_username}")
        logger.info(f"[HANDLERS] Group memory: {self.max_group_memory}")
        logger.info(f"[HANDLERS] Private memory: {self.max_private_memory}")
        logger.info(f"[HANDLERS] Session timeout: {self.session_timeout}min")

    # ========================================================
    #           UTILITY METHODS
    # ========================================================

    def _is_owner(self, user: User) -> bool:
        """Check if a Telegram User is the owner."""
        if not user:
            return False
        if user.username:
            if user.username.lower() == self.owner_username:
                return True
        if self.owner_chat_id and user.id == self.owner_chat_id:
            return True
        if self._discovered_owner_id and user.id == self._discovered_owner_id:
            return True
        return False

    def _is_admin(self, user: User) -> bool:
        """Check if a user is an admin."""
        if self._is_owner(user):
            return True
        if self.db:
            role = self.db.get_user_role(user.id)
            return role in ("admin", "owner")
        return False

    def _get_display_name(self, user: User) -> str:
        """Get display name from User object."""
        if not user:
            return "Unknown"
        if user.first_name:
            name = user.first_name
            if user.last_name:
                name += f" {user.last_name}"
            return name
        if user.username:
            return f"@{user.username}"
        return f"User-{user.id}"

    def _get_chat_lock(self, chat_id: int) -> asyncio.Lock:
        """Get or create a processing lock for a chat."""
        if chat_id not in self._chat_locks:
            self._chat_locks[chat_id] = asyncio.Lock()
        return self._chat_locks[chat_id]

    def _get_uptime(self) -> str:
        """Get formatted uptime string."""
        delta = datetime.now(timezone.utc) - self.start_time
        total = int(delta.total_seconds())
        d = total // 86400
        h = (total % 86400) // 3600
        m = (total % 3600) // 60
        s = total % 60
        parts = []
        if d > 0: parts.append(f"{d}d")
        if h > 0: parts.append(f"{h}h")
        if m > 0: parts.append(f"{m}m")
        parts.append(f"{s}s")
        return " ".join(parts)

    def _sanitize(self, text: str) -> str:
        """Sanitize user input."""
        if not text:
            return ""
        text = text.replace("\x00", "")
        return text[:4000].strip()

    async def _safe_reply(
        self, message: Message, text: str,
        reply_markup=None, **kwargs
    ) -> Optional[Message]:
        """Safely reply to a message with error handling."""
        try:
            if len(text) > 4000:
                # Split into chunks
                chunks = [text[i:i+4000] for i in range(0, len(text), 4000)]
                sent = None
                for i, chunk in enumerate(chunks):
                    if i == 0:
                        sent = await message.reply_text(
                            chunk, reply_markup=reply_markup, **kwargs
                        )
                    else:
                        await message.chat.send_message(chunk, **kwargs)
                    if i < len(chunks) - 1:
                        await asyncio.sleep(0.3)
                return sent
            else:
                return await message.reply_text(
                    text, reply_markup=reply_markup, **kwargs
                )
        except RetryAfter as e:
            logger.warning(f"[REPLY] Rate limited, waiting {e.retry_after}s")
            await asyncio.sleep(e.retry_after)
            try:
                return await message.reply_text(text[:4000])
            except Exception:
                return None
        except Forbidden:
            logger.warning(f"[REPLY] Bot blocked by {message.chat_id}")
            return None
        except BadRequest as e:
            logger.error(f"[REPLY] Bad request: {e}")
            try:
                return await message.chat.send_message(text[:4000])
            except Exception:
                return None
        except Exception as e:
            logger.error(f"[REPLY] Unexpected error: {e}")
            return None

    def _register_user(self, user: User, chat: Chat):
        """Register user and chat in database."""
        if not self.db or not user:
            return

        try:
            self.db.upsert_user(
                user.id,
                user.username or "",
                user.first_name or "",
                user.last_name or ""
            )

            if chat:
                self.db.upsert_chat(
                    chat.id,
                    chat.type,
                    chat.title or ""
                )
                self.db.track_user_chat(user.id, chat.id)

            # Track owner
            if self._is_owner(user):
                self._discovered_owner_id = user.id
                self.db.set_user_role(user.id, "owner")

        except Exception as e:
            logger.warning(f"[REG] Registration error: {e}")

    # ========================================================
    #         USER COMMAND HANDLERS
    # ========================================================

    @not_banned
    async def cmd_start(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Handle /start command — Welcome message with ASCII UI."""
        user = update.effective_user
        chat = update.effective_chat
        if not user or not update.effective_message:
            return

        logger.info(
            f"[CMD] /start from {user.id} (@{user.username}) "
            f"in {chat.type}"
        )

        self._register_user(user, chat)

        name = self._get_display_name(user)
        message_text = START_MESSAGE_TEMPLATE.format(name=name)

        await self._safe_reply(
            update.effective_message,
            message_text,
            reply_markup=KeyboardBuilder.start_keyboard()
        )

    @not_banned
    async def cmd_help(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Handle /help command — Show all available commands."""
        if not update.effective_message:
            return

        logger.info(
            f"[CMD] /help from "
            f"{update.effective_user.id if update.effective_user else '?'}"
        )

        await self._safe_reply(
            update.effective_message,
            HELP_MESSAGE_TEMPLATE,
            reply_markup=KeyboardBuilder.help_keyboard()
        )

    @not_banned
    async def cmd_profile(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Handle /profile command — Show user statistics."""
        user = update.effective_user
        if not user or not update.effective_message:
            return

        logger.info(f"[CMD] /profile from {user.id}")

        self._register_user(user, update.effective_chat)

        # Fetch user data from DB
        user_data = None
        if self.db:
            user_data = self.db.get_user(user.id)

        if not user_data:
            await self._safe_reply(
                update.effective_message,
                "Beta pehle /start kar! 😏 Tab profile dikhaungi ✨"
            )
            return

        is_own = self._is_owner(user)
        role = "👑 Owner" if is_own else (
            "🛡️ Admin" if user_data.get("role") == "admin" else "👤 User"
        )

        joined = str(user_data.get("first_seen", "Unknown"))[:10]
        last_active = str(user_data.get("last_active", "Unknown"))[:19]
        mood = user_data.get("mood", "default")

        profile_text = PROFILE_TEMPLATE.format(
            name=self._get_display_name(user),
            user_id=user.id,
            username=user.username or "N/A",
            role=role,
            message_count=user_data.get("message_count", 0),
            joined=joined,
            last_active=last_active,
            banned="❌ No" if not user_data.get("is_banned") else "✅ Yes",
            lang=user_data.get("language", "hinglish"),
            mood=mood,
        )

        await self._safe_reply(
            update.effective_message,
            profile_text,
            reply_markup=KeyboardBuilder.profile_keyboard()
        )

    @not_banned
    async def cmd_clear(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Handle /clear command — Clear chat conversation memory."""
        chat = update.effective_chat
        user = update.effective_user
        if not chat or not update.effective_message:
            return

        logger.info(f"[CMD] /clear from {user.id if user else '?'} in {chat.id}")

        if self.db:
            self.db.clear_chat_history(chat.id)
            self.db.clear_session(chat.id)

        await self._safe_reply(
            update.effective_message,
            RuhiResponses.get_random(RuhiResponses.MEMORY_CLEARED)
        )

    @not_banned
    async def cmd_reset(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Handle /reset command — Alias for /clear."""
        await self.cmd_clear(update, context)

    @not_banned
    async def cmd_lang(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Handle /lang command — Toggle language preference."""
        user = update.effective_user
        if not user or not update.effective_message:
            return

        logger.info(f"[CMD] /lang from {user.id}")

        current_lang = "hinglish"
        if self.db:
            current_lang = self.db.get_user_language(user.id)

        new_lang = "english" if current_lang == "hinglish" else "hinglish"

        if self.db:
            self.db.set_user_language(user.id, new_lang)

        lang_display = {
            "hinglish": "Hinglish (Hindi + English) 🇮🇳",
            "english": "English 🇬🇧"
        }

        await self._safe_reply(
            update.effective_message,
            f"✅ Language changed to: {lang_display.get(new_lang, new_lang)}\n"
            f"Ab main {new_lang} mein baat karungi! ✨💅"
        )

    @not_banned
    async def cmd_personality(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Handle /personality command — Show current bot mood/persona."""
        if not update.effective_message:
            return

        logger.info(
            f"[CMD] /personality from "
            f"{update.effective_user.id if update.effective_user else '?'}"
        )

        mood = "savage"
        if self.db:
            mood = self.db.get_setting("bot_mood", "savage")

        mood_data = {
            "savage": ("😏 Savage Mode", "Roasting ON 🔥", "100%", "30%"),
            "soft": ("🥺 Soft Mode", "Caring & Sweet 💖", "20%", "100%"),
            "attitude": ("😤 Attitude Mode", "Don't mess with me 💅", "80%", "40%"),
            "playful": ("🤭 Playful Mode", "Masti time! 🎉", "50%", "70%"),
            "queen": ("💅 Queen Mode", "Unbothered & Slay 👑", "90%", "50%"),
            "dramatic": ("😭 Dramatic Mode", "Over-react everything!", "60%", "80%"),
        }

        mood_info = mood_data.get(
            mood, ("🎭 Default", "Mixed vibes", "50%", "50%")
        )

        personality_text = PERSONALITY_TEMPLATE.format(
            mood=mood_info[0],
            style=mood_info[1],
            savage_level=mood_info[2],
            care_level=mood_info[3],
        )

        await self._safe_reply(
            update.effective_message,
            personality_text,
            reply_markup=KeyboardBuilder.back_keyboard("cb_start")
        )

    @not_banned
    async def cmd_usage(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Handle /usage command — Show usage statistics."""
        user = update.effective_user
        if not user or not update.effective_message:
            return

        logger.info(f"[CMD] /usage from {user.id}")

        user_data = None
        total_db = 0
        if self.db:
            user_data = self.db.get_user(user.id)
            total_db = self.db.get_total_messages()

        ai_stats = {"total_requests": 0, "success_rate": "N/A"}
        if self.ai and hasattr(self.ai, "stats"):
            ai_stats = self.ai.stats

        usage_text = USAGE_TEMPLATE.format(
            user_messages=user_data.get("message_count", 0) if user_data else 0,
            joined=str(user_data.get("first_seen", "N/A"))[:10] if user_data else "N/A",
            last_active=str(user_data.get("last_active", "N/A"))[:19] if user_data else "N/A",
            ai_requests=ai_stats.get("total_requests", 0),
            success_rate=ai_stats.get("success_rate", "N/A"),
            uptime=self._get_uptime(),
            total_db_messages=total_db,
        )

        await self._safe_reply(
            update.effective_message,
            usage_text,
            reply_markup=KeyboardBuilder.back_keyboard("cb_start")
        )

    @not_banned
    async def cmd_summary(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Handle /summary command — AI-powered chat summarization."""
        chat = update.effective_chat
        user = update.effective_user
        if not chat or not user or not update.effective_message:
            return

        logger.info(f"[CMD] /summary from {user.id} in {chat.id}")

        if not self.db or not self.ai:
            await self._safe_reply(
                update.effective_message,
                "Abhi summary feature ready nahi hai 😭 Try later! ✨"
            )
            return

        # Determine memory limit
        limit = (
            self.max_private_memory
            if chat.type == ChatType.PRIVATE
            else self.max_group_memory
        )
        history = self.db.get_chat_history(chat.id, limit)

        if not history or len(history) < 3:
            await self._safe_reply(
                update.effective_message,
                "Abhi toh kuch khaas baat nahi hui beta 🥺\n"
                "Thoda aur baat kar, phir summary duungi! ✨"
            )
            return

        # Typing indicator
        try:
            await chat.send_action(ChatAction.TYPING)
        except Exception:
            pass

        # Build summary prompt
        summary_prompt = ContextBuilder.build_summary_prompt(
            history, self._get_display_name(user)
        )

        is_own = self._is_owner(user)
        response = await self.ai.generate_response(
            user_message=summary_prompt,
            chat_history=[],
            is_owner=is_own,
            user_name=self._get_display_name(user),
            chat_type=str(chat.type)
        )

        await self._safe_reply(
            update.effective_message,
            f"📋 Chat Summary ✨\n\n{response}"
        )

    # ========================================================
    #         ADMIN COMMAND HANDLERS (Owner Only)
    # ========================================================

    @owner_only
    async def cmd_admin(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Handle /admin command — Owner dashboard."""
        if not update.effective_message:
            return

        logger.info("[CMD] /admin — Owner dashboard accessed")

        total_users = self.db.get_total_users() if self.db else 0
        total_chats = self.db.get_total_chats() if self.db else 0
        total_messages = self.db.get_total_messages() if self.db else 0
        banned_users = self.db.get_banned_users_count() if self.db else 0
        active_sessions = self.db.get_active_sessions_count() if self.db else 0

        dashboard = ADMIN_DASHBOARD_TEMPLATE.format(
            total_users=total_users,
            total_chats=total_chats,
            total_messages=total_messages,
            banned_users=banned_users,
            active_sessions=active_sessions,
            uptime=self._get_uptime(),
        )

        await self._safe_reply(
            update.effective_message,
            dashboard,
            reply_markup=KeyboardBuilder.admin_keyboard()
        )

    @owner_only
    async def cmd_broadcast(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Handle /broadcast command — Send message to all users/chats."""
        if not update.effective_message or not self.db:
            return

        if not context.args:
            await self._safe_reply(
                update.effective_message,
                "Usage: /broadcast <message>\n"
                "Example: /broadcast Hello everyone! 🌸\n\n"
                "Yeh message sabko jayega Owner-sama! 💖"
            )
            return

        broadcast_text = " ".join(context.args)
        logger.info(f"[BROADCAST] Initiated: {broadcast_text[:50]}...")

        # Get all recipients
        user_ids = self.db.get_all_user_ids()
        chat_ids = self.db.get_all_chat_ids()
        all_ids = list(set(user_ids + chat_ids))

        status_msg = await self._safe_reply(
            update.effective_message,
            f"📢 Broadcasting to {len(all_ids)} chats...\n"
            f"Please wait... ⏳"
        )

        sent = 0
        failed = 0
        blocked = 0
        bot = context.bot

        formatted_message = (
            f"📢 Broadcast from Ruhi Ji 👑\n\n"
            f"{broadcast_text}\n\n"
            f"— @RUHI_VIG_QNR"
        )

        for i, chat_id in enumerate(all_ids):
            try:
                await bot.send_message(
                    chat_id=chat_id,
                    text=formatted_message
                )
                sent += 1

                # Telegram rate limit: 30 msgs/sec
                if sent % 25 == 0:
                    await asyncio.sleep(1.5)
                    # Update status every 50 messages
                    if sent % 50 == 0 and status_msg:
                        try:
                            await status_msg.edit_text(
                                f"📢 Broadcasting... {sent}/{len(all_ids)}\n"
                                f"✅ Sent: {sent} | ❌ Failed: {failed}"
                            )
                        except Exception:
                            pass

            except Forbidden:
                failed += 1
                blocked += 1
            except RetryAfter as e:
                await asyncio.sleep(e.retry_after)
                try:
                    await bot.send_message(chat_id=chat_id, text=formatted_message)
                    sent += 1
                except Exception:
                    failed += 1
            except (BadRequest, TelegramError):
                failed += 1
            except Exception:
                failed += 1

        # Log broadcast
        if self.db:
            self.db.log_broadcast(broadcast_text, sent, failed)

        result_text = (
            f"✅ Broadcast Complete!\n\n"
            f"📤 Sent: {sent}\n"
            f"❌ Failed: {failed}\n"
            f"🚫 Blocked: {blocked}\n"
            f"📊 Total: {len(all_ids)}"
        )

        if status_msg:
            try:
                await status_msg.edit_text(result_text)
            except Exception:
                await self._safe_reply(
                    update.effective_message, result_text
                )
        else:
            await self._safe_reply(
                update.effective_message, result_text
            )

    @owner_only
    async def cmd_totalusers(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Handle /totalusers command."""
        if not update.effective_message:
            return

        total = self.db.get_total_users() if self.db else 0
        chats = self.db.get_total_chats() if self.db else 0
        msgs = self.db.get_total_messages() if self.db else 0

        await self._safe_reply(
            update.effective_message,
            f"╭───────────────────⦿\n"
            f"│ 📊 ᴅᴀᴛᴀʙᴀsᴇ sᴛᴀᴛs\n"
            f"├───────────────────⦿\n"
            f"│ 👥 Total Users: {total}\n"
            f"│ 💬 Total Chats: {chats}\n"
            f"│ 📝 Total Messages: {msgs}\n"
            f"╰───────────────────⦿\n"
            f"Ji Owner-sama! 🥺💖"
        )

    @owner_only
    async def cmd_activeusers(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Handle /activeusers command."""
        if not update.effective_message or not self.db:
            return

        active_1h = self.db.get_active_users(1)
        active_24h = self.db.get_active_users(24)
        active_7d = self.db.get_active_users(168)
        sessions = self.db.get_active_sessions_count()

        await self._safe_reply(
            update.effective_message,
            f"╭───────────────────⦿\n"
            f"│ 📊 ᴀᴄᴛɪᴠᴇ ᴜsᴇʀs\n"
            f"├───────────────────⦿\n"
            f"│ ⏰ Last 1 hour: {active_1h}\n"
            f"│ 📅 Last 24 hours: {active_24h}\n"
            f"│ 📆 Last 7 days: {active_7d}\n"
            f"│ 💬 Active Sessions: {sessions}\n"
            f"╰───────────────────⦿\n"
            f"Ji didi! 🥺✨"
        )

    @owner_only
    async def cmd_forceclear(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Handle /forceclear — Clear a specific user's context."""
        if not update.effective_message or not self.db:
            return

        if not context.args:
            await self._safe_reply(
                update.effective_message,
                "Usage: /forceclear <user_id>\nExample: /forceclear 123456789"
            )
            return

        try:
            target_id = int(context.args[0])
        except ValueError:
            await self._safe_reply(
                update.effective_message,
                "❌ Invalid user ID! Numbers only, Owner-sama 🥺"
            )
            return

        self.db.clear_user_history(target_id)

        await self._safe_reply(
            update.effective_message,
            f"✅ Context cleared for user {target_id}\n"
            f"Sab saaf ho gaya, Owner-sama! 🌸✨"
        )

    @owner_only
    async def cmd_ban(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Handle /ban command — Ban a user."""
        if not update.effective_message or not self.db:
            return

        target_id = None

        # Check reply
        if update.effective_message.reply_to_message:
            reply_user = update.effective_message.reply_to_message.from_user
            if reply_user:
                target_id = reply_user.id
        elif context.args:
            try:
                target_id = int(context.args[0])
            except ValueError:
                pass

        if not target_id:
            await self._safe_reply(
                update.effective_message,
                "Usage: /ban <user_id> ya reply karke /ban likh"
            )
            return

        # Prevent banning owner
        if self._discovered_owner_id and target_id == self._discovered_owner_id:
            await self._safe_reply(
                update.effective_message,
                "🚫 Owner ko ban nahi kar sakte! 😤"
            )
            return

        self.db.ban_user(target_id)

        await self._safe_reply(
            update.effective_message,
            f"🚫 User {target_id} has been BANNED!\n"
            f"Ab yeh mujhse baat nahi kar payega 💅"
        )

    @owner_only
    async def cmd_unban(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Handle /unban command."""
        if not update.effective_message or not self.db:
            return

        if not context.args:
            await self._safe_reply(
                update.effective_message,
                "Usage: /unban <user_id>"
            )
            return

        try:
            target_id = int(context.args[0])
        except ValueError:
            await self._safe_reply(
                update.effective_message, "❌ Invalid user ID!"
            )
            return

        self.db.unban_user(target_id)
        self.flood_control.unmute_user(target_id)

        await self._safe_reply(
            update.effective_message,
            f"✅ User {target_id} has been UNBANNED! 🌹"
        )

    @owner_only
    async def cmd_badwords(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Handle /badwords command — List bad words."""
        if not update.effective_message or not self.db:
            return

        words = self.db.get_bad_words()
        if not words:
            await self._safe_reply(
                update.effective_message,
                "📋 Bad words list is empty! Use /addbadword to add."
            )
            return

        word_list = ", ".join(f"`{w}`" for w in words[:30])
        remaining = max(0, len(words) - 30)

        text = f"🚫 Bad Words List ({len(words)} total):\n\n{word_list}"
        if remaining > 0:
            text += f"\n\n...and {remaining} more"
        text += "\n\n/addbadword <word> to add\n/removebadword <word> to remove"

        await self._safe_reply(update.effective_message, text)

    @owner_only
    async def cmd_addbadword(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Handle /addbadword command."""
        if not update.effective_message or not self.db:
            return

        if not context.args:
            await self._safe_reply(
                update.effective_message, "Usage: /addbadword <word>"
            )
            return

        word = " ".join(context.args).strip()
        db_added = self.db.add_bad_word(word)
        filter_added = self.bad_word_filter.add_word(word)

        if db_added or filter_added:
            await self._safe_reply(
                update.effective_message,
                f"✅ Added '{word}' to bad words list! 🚫"
            )
        else:
            await self._safe_reply(
                update.effective_message,
                f"⚠️ '{word}' already exists!"
            )

    @owner_only
    async def cmd_removebadword(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Handle /removebadword command."""
        if not update.effective_message or not self.db:
            return

        if not context.args:
            await self._safe_reply(
                update.effective_message, "Usage: /removebadword <word>"
            )
            return

        word = " ".join(context.args).strip()
        db_removed = self.db.remove_bad_word(word)
        filter_removed = self.bad_word_filter.remove_word(word)

        if db_removed or filter_removed:
            await self._safe_reply(
                update.effective_message,
                f"✅ Removed '{word}' from list!"
            )
        else:
            await self._safe_reply(
                update.effective_message,
                f"⚠️ '{word}' not found in the list!"
            )

    @owner_only
    async def cmd_setphrase(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Handle /setphrase command — Set custom wake phrase."""
        if not update.effective_message:
            return

        if not context.args:
            current = "ruhi ji"
            if self.db:
                current = self.db.get_setting("wake_phrase", "ruhi ji")
            await self._safe_reply(
                update.effective_message,
                f"Current wake phrase: '{current}'\n"
                f"Usage: /setphrase <new phrase>"
            )
            return

        new_phrase = " ".join(context.args).strip().lower()

        if self.db:
            self.db.set_setting("wake_phrase", new_phrase)
        self.wake_detector.add_phrase(new_phrase)

        await self._safe_reply(
            update.effective_message,
            f"✅ Wake phrase updated to: '{new_phrase}' 🌸"
        )

    @owner_only
    async def cmd_addadmin(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Handle /addadmin command."""
        if not update.effective_message or not self.db:
            return

        target_id = None
        if update.effective_message.reply_to_message:
            reply_user = update.effective_message.reply_to_message.from_user
            if reply_user:
                target_id = reply_user.id
        elif context.args:
            try:
                target_id = int(context.args[0])
            except ValueError:
                pass

        if not target_id:
            await self._safe_reply(
                update.effective_message,
                "Usage: /addadmin <user_id> or reply to a message"
            )
            return

        self.db.set_user_role(target_id, "admin")
        await self._safe_reply(
            update.effective_message,
            f"✅ User {target_id} is now an admin! 👑"
        )

    @owner_only
    async def cmd_removeadmin(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Handle /removeadmin command."""
        if not update.effective_message or not self.db:
            return

        if not context.args:
            await self._safe_reply(
                update.effective_message, "Usage: /removeadmin <user_id>"
            )
            return

        try:
            target_id = int(context.args[0])
        except ValueError:
            await self._safe_reply(
                update.effective_message, "❌ Invalid user ID!"
            )
            return

        self.db.set_user_role(target_id, "user")
        await self._safe_reply(
            update.effective_message,
            f"✅ User {target_id} demoted to regular user!"
        )

    @owner_only
    async def cmd_shutdown(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Handle /shutdown command — Graceful shutdown."""
        if not update.effective_message:
            return

        await self._safe_reply(
            update.effective_message,
            "🔴 Ruhi Ji shutting down... Bye bye! 🥺💖\n"
            "Owner-sama ne bola toh maan leti hoon..."
        )
        logger.info("[CMD] Shutdown initiated by owner")
        await asyncio.sleep(1)
        os._exit(0)

    @owner_only
    async def cmd_restart(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Handle /restart command."""
        if not update.effective_message:
            return

        await self._safe_reply(
            update.effective_message,
            "🔄 Restarting... Ek moment, Owner-sama! 🥺✨"
        )
        logger.info("[CMD] Restart initiated by owner")
        await asyncio.sleep(1)
        os.execv(sys.executable, [sys.executable] + sys.argv)

    # ========================================================
    #          CALLBACK QUERY HANDLER
    # ========================================================

    async def handle_callback_query(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Handle all inline keyboard button presses."""
        query = update.callback_query
        if not query:
            return

        await query.answer()
        data = query.data
        user = query.from_user

        logger.info(f"[CALLBACK] {data} from {user.id}")

        try:
            if data == "cb_start":
                name = self._get_display_name(user)
                await query.edit_message_text(
                    START_MESSAGE_TEMPLATE.format(name=name),
                    reply_markup=KeyboardBuilder.start_keyboard()
                )

            elif data == "cb_help":
                await query.edit_message_text(
                    HELP_MESSAGE_TEMPLATE,
                    reply_markup=KeyboardBuilder.help_keyboard()
                )

            elif data == "cb_profile" or data == "cb_profile_refresh":
                user_data = self.db.get_user(user.id) if self.db else None
                if not user_data:
                    await query.edit_message_text("Beta /start kar pehle! 😏")
                    return

                is_own = self._is_owner(user)
                role = "👑 Owner" if is_own else "👤 User"
                profile = PROFILE_TEMPLATE.format(
                    name=self._get_display_name(user),
                    user_id=user.id,
                    username=user.username or "N/A",
                    role=role,
                    message_count=user_data.get("message_count", 0),
                    joined=str(user_data.get("first_seen", "N/A"))[:10],
                    last_active=str(user_data.get("last_active", "N/A"))[:19],
                    banned="❌ No" if not user_data.get("is_banned") else "✅ Yes",
                    lang=user_data.get("language", "hinglish"),
                    mood=user_data.get("mood", "default"),
                )
                await query.edit_message_text(
                    profile,
                    reply_markup=KeyboardBuilder.profile_keyboard()
                )

            elif data == "cb_start_chat":
                await query.edit_message_text(
                    "💬 Bas 'Ruhi Ji' bolke baat shuru kar! 🌹\n\n"
                    "Examples:\n"
                    "• Ruhi Ji kaise ho?\n"
                    "• Ruhi Ji kuch funny suna\n"
                    "• Ruhi Ji roast karo\n\n"
                    "Private chat mein direct baat kar sakti hoon! ✨",
                    reply_markup=KeyboardBuilder.back_keyboard("cb_start")
                )

            elif data == "cb_personality":
                mood = self.db.get_setting("bot_mood", "savage") if self.db else "savage"
                mood_data = {
                    "savage": ("😏 Savage", "Roasting 🔥", "100%", "30%"),
                    "soft": ("🥺 Soft", "Caring 💖", "20%", "100%"),
                    "playful": ("🤭 Playful", "Fun 🎉", "50%", "70%"),
                }
                info = mood_data.get(mood, ("🎭 Default", "Mixed", "50%", "50%"))
                await query.edit_message_text(
                    PERSONALITY_TEMPLATE.format(
                        mood=info[0], style=info[1],
                        savage_level=info[2], care_level=info[3]
                    ),
                    reply_markup=KeyboardBuilder.back_keyboard("cb_start")
                )

            elif data == "cb_usage":
                user_data = self.db.get_user(user.id) if self.db else None
                ai_stats = self.ai.stats if self.ai and hasattr(self.ai, 'stats') else {}
                await query.edit_message_text(
                    USAGE_TEMPLATE.format(
                        user_messages=user_data.get("message_count", 0) if user_data else 0,
                        joined=str(user_data.get("first_seen", "N/A"))[:10] if user_data else "N/A",
                        last_active=str(user_data.get("last_active", "N/A"))[:19] if user_data else "N/A",
                        ai_requests=ai_stats.get("total_requests", 0),
                        success_rate=ai_stats.get("success_rate", "N/A"),
                        uptime=self._get_uptime(),
                        total_db_messages=self.db.get_total_messages() if self.db else 0,
                    ),
                    reply_markup=KeyboardBuilder.back_keyboard("cb_start")
                )

            elif data == "cb_clear_confirm":
                await query.edit_message_text(
                    "⚠️ Kya sachme memory clear karni hai?\n"
                    "Sab bhool jaungi main! 🥺",
                    reply_markup=KeyboardBuilder.confirm_keyboard("clear")
                )

            elif data == "cb_confirm_clear":
                chat_id = query.message.chat_id
                if self.db:
                    self.db.clear_chat_history(chat_id)
                    self.db.clear_session(chat_id)
                await query.edit_message_text(
                    RuhiResponses.get_random(RuhiResponses.MEMORY_CLEARED)
                )

            elif data == "cb_cancel":
                await query.edit_message_text(
                    "Theek hai, cancel ho gaya! 😏✨"
                )

            # === Admin Callbacks ===
            elif data == "cb_admin_refresh":
                if not self._is_owner(user):
                    await query.answer("❌ Owner only!", show_alert=True)
                    return
                total_users = self.db.get_total_users() if self.db else 0
                total_chats = self.db.get_total_chats() if self.db else 0
                total_messages = self.db.get_total_messages() if self.db else 0
                banned = self.db.get_banned_users_count() if self.db else 0
                sessions = self.db.get_active_sessions_count() if self.db else 0
                await query.edit_message_text(
                    ADMIN_DASHBOARD_TEMPLATE.format(
                        total_users=total_users, total_chats=total_chats,
                        total_messages=total_messages, banned_users=banned,
                        active_sessions=sessions, uptime=self._get_uptime()
                    ),
                    reply_markup=KeyboardBuilder.admin_keyboard()
                )

            elif data == "cb_admin_broadcast":
                if not self._is_owner(user):
                    await query.answer("❌ Owner only!", show_alert=True)
                    return
                await query.edit_message_text(
                    "📢 To broadcast:\n/broadcast <message>\n\n"
                    "Example: /broadcast Hello! 🌸",
                    reply_markup=KeyboardBuilder.back_keyboard("cb_admin_refresh")
                )

            elif data == "cb_admin_badwords":
                if not self._is_owner(user):
                    await query.answer("❌ Owner only!", show_alert=True)
                    return
                words = self.db.get_bad_words() if self.db else []
                display = ", ".join(words[:20]) if words else "Empty"
                await query.edit_message_text(
                    f"🚫 Bad Words ({len(words)}):\n{display}\n\n"
                    f"/addbadword <word>\n/removebadword <word>",
                    reply_markup=KeyboardBuilder.back_keyboard("cb_admin_refresh")
                )

            elif data == "cb_admin_clear_sessions":
                if not self._is_owner(user):
                    await query.answer("❌ Owner only!", show_alert=True)
                    return
                if self.db:
                    self.db.execute_query(
                        "UPDATE chats SET active_session_expiry = NULL"
                    ) if hasattr(self.db, 'execute_query') else (
                        self.db.execute(
                            "UPDATE chats SET active_session_expiry = NULL"
                        )
                    )
                await query.edit_message_text(
                    "✅ All sessions cleared! 🌸",
                    reply_markup=KeyboardBuilder.back_keyboard("cb_admin_refresh")
                )

            elif data == "cb_admin_ai_stats":
                if not self._is_owner(user):
                    await query.answer("❌ Owner only!", show_alert=True)
                    return
                stats = self.ai.stats if self.ai and hasattr(self.ai, 'stats') else {}
                await query.edit_message_text(
                    f"╭───────────────────⦿\n"
                    f"│ 🤖 AI Stats\n"
                    f"├───────────────────⦿\n"
                    f"│ Requests: {stats.get('total_requests', 0)}\n"
                    f"│ Errors: {stats.get('total_errors', 0)}\n"
                    f"│ Success: {stats.get('success_rate', 'N/A')}\n"
                    f"│ Model: Kimi-K2\n"
                    f"╰───────────────────⦿",
                    reply_markup=KeyboardBuilder.back_keyboard("cb_admin_refresh")
                )

            elif data == "cb_admin_flood_stats":
                if not self._is_owner(user):
                    await query.answer("❌ Owner only!", show_alert=True)
                    return
                stats = self.flood_control.get_stats()
                await query.edit_message_text(
                    f"╭───────────────────⦿\n"
                    f"│ 🛡️ Flood Control\n"
                    f"├───────────────────⦿\n"
                    f"│ Tracked Users: {stats['tracked_users']}\n"
                    f"│ Muted Users: {stats['muted_users']}\n"
                    f"│ Total Warnings: {stats['total_warnings']}\n"
                    f"╰───────────────────⦿",
                    reply_markup=KeyboardBuilder.back_keyboard("cb_admin_refresh")
                )

            else:
                await query.answer("Unknown action 🤔")

        except BadRequest as e:
            if "not modified" in str(e).lower():
                await query.answer("Already up to date! ✨")
            else:
                logger.error(f"[CALLBACK] BadRequest: {e}")
                await query.answer("Error occurred 😭")
        except Exception as e:
            logger.error(f"[CALLBACK] Error handling {data}: {e}")
            await query.answer("Something went wrong 😭")

    # ========================================================
    #      MAIN MESSAGE HANDLER — THE BRAIN
    # ========================================================

    async def handle_message(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """
        Main message handler — Core brain of Ruhi Ji.

        Flow:
        1. Validate message & user
        2. Check banned status
        3. Register user/chat in DB
        4. Determine if bot should respond
        5. Flood control check
        6. Bad word filter
        7. Build AI context from DB history
        8. Generate AI response
        9. Store messages in DB
        10. Send response to user
        """
        # === Step 1: Validate ===
        if not update.effective_message or not update.effective_user:
            return

        message = update.effective_message
        user = update.effective_user
        chat = update.effective_chat
        text = message.text

        if not text or text.startswith("/"):
            return

        user_id = user.id
        chat_id = chat.id
        chat_type = chat.type
        user_name = self._get_display_name(user)
        is_own = self._is_owner(user)

        # === Step 2: Ban check ===
        if not is_own and self.db and self.db.is_user_banned(user_id):
            logger.debug(f"[MSG] Banned user {user_id} ignored")
            return

        # === Step 3: Register ===
        self._register_user(user, chat)

        # === Step 4: Should respond? ===
        should_respond = False
        session_activated = False

        if chat_type == ChatType.PRIVATE:
            should_respond = True
        else:
            # Group chat logic
            detected, matched = self.wake_detector.detect(text)

            if detected:
                should_respond = True
                session_activated = True
                if self.db:
                    self.db.set_session_active(chat_id, self.session_timeout)
                logger.info(
                    f"[SESSION] Activated in {chat_id} by {user_id} "
                    f"(phrase: {matched})"
                )

            elif (
                message.reply_to_message
                and message.reply_to_message.from_user
                and message.reply_to_message.from_user.is_bot
            ):
                bot_info = context.bot
                if message.reply_to_message.from_user.id == bot_info.id:
                    should_respond = True
                    if self.db:
                        self.db.set_session_active(chat_id, self.session_timeout)

            elif self.db and self.db.is_session_active(chat_id):
                should_respond = True

        # Store message regardless (for context)
        sanitized = self._sanitize(text)
        store_text = (
            f"[{user_name}]: {sanitized}"
            if chat_type != ChatType.PRIVATE
            else sanitized
        )

        if self.db:
            self.db.store_message(chat_id, user_id, "user", store_text)
            self.db.increment_message_count(user_id)
            ct = "private" if chat_type == ChatType.PRIVATE else "group"
            self.db.cleanup_old_messages(chat_id, ct)

        if not should_respond:
            return

        # === Step 5: Flood control ===
        if not is_own:
            allowed, reason = self.flood_control.check_allowed(user_id, text)
            if not allowed:
                if reason == "auto_muted":
                    await self._safe_reply(
                        message,
                        f"🚫 Beta, tune bohot spam kiya! 😤\n"
                        f"60 seconds ke liye mute hai tu 💅"
                    )
                elif reason in ("rate_limited", "duplicate_spam"):
                    wait = self.flood_control.get_wait_time(user_id)
                    await self._safe_reply(
                        message,
                        RuhiResponses.get_random(
                            RuhiResponses.RATE_LIMITED,
                            wait=f"{wait:.0f}"
                        )
                    )
                return

        # === Step 6: Bad word filter ===
        if not is_own:
            has_bad, matched_word = self.bad_word_filter.check(text)
            if has_bad:
                logger.info(
                    f"[FILTER] Bad word '{matched_word}' from {user_id}"
                )
                await self._safe_reply(
                    message,
                    RuhiResponses.get_random(
                        RuhiResponses.BAD_WORD_DETECTED
                    )
                )
                return

        # === Step 7: Get chat history ===
        chat_history = []
        if self.db:
            limit = (
                self.max_private_memory
                if chat_type == ChatType.PRIVATE
                else self.max_group_memory
            )
            chat_history = self.db.get_chat_history(chat_id, limit)

        # === Step 8: Typing + AI response ===
        try:
            await chat.send_action(ChatAction.TYPING)
        except Exception:
            pass

        lock = self._get_chat_lock(chat_id)

        async with lock:
            try:
                if self.ai:
                    actual_message = sanitized
                    if session_activated:
                        actual_message = (
                            self.wake_detector.extract_message_after_wake(sanitized)
                            or sanitized
                        )

                    response = await self.ai.generate_response(
                        user_message=actual_message,
                        chat_history=chat_history,
                        is_owner=is_own,
                        user_name=user_name,
                        chat_type="private" if chat_type == ChatType.PRIVATE else "group"
                    )
                else:
                    response = RuhiResponses.get_random(
                        RuhiResponses.FALLBACK_OWNER if is_own
                        else RuhiResponses.FALLBACK_USER
                    )
            except Exception as e:
                logger.error(f"[MSG] AI error: {e}")
                response = RuhiResponses.get_random(
                    RuhiResponses.FALLBACK_OWNER if is_own
                    else RuhiResponses.FALLBACK_USER
                )

        # === Step 9: Store bot response ===
        if response and self.db:
            self.db.store_message(chat_id, 0, "assistant", response)
            ct = "private" if chat_type == ChatType.PRIVATE else "group"
            self.db.cleanup_old_messages(chat_id, ct)

        # === Step 10: Send ===
        if response:
            await self._safe_reply(message, response)
            logger.info(
                f"[MSG] Replied to {user_id} in {chat_id} | "
                f"{len(response)} chars"
            )

    # ========================================================
    #         GROUP EVENT HANDLERS
    # ========================================================

    async def handle_new_members(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Handle when bot or new members join a group."""
        if not update.effective_message:
            return

        message = update.effective_message
        chat = update.effective_chat

        if not message.new_chat_members:
            return

        bot = context.bot
        for member in message.new_chat_members:
            if member.id == bot.id:
                logger.info(
                    f"[EVENT] Bot added to: {chat.title} ({chat.id})"
                )

                if self.db:
                    self.db.upsert_chat(chat.id, chat.type, chat.title or "")

                welcome = RuhiResponses.get_random(
                    RuhiResponses.GROUP_WELCOME
                )

                try:
                    await chat.send_message(welcome)
                except Exception as e:
                    logger.error(f"[EVENT] Welcome error: {e}")

            else:
                # Another user joined — register them
                if self.db:
                    self.db.upsert_user(
                        member.id,
                        member.username or "",
                        member.first_name or "",
                        member.last_name or ""
                    )
                    self.db.track_user_chat(member.id, chat.id)

    async def handle_left_member(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Handle when bot is removed from a group."""
        if not update.effective_message:
            return

        message = update.effective_message
        chat = update.effective_chat
        bot = context.bot

        if (
            message.left_chat_member
            and message.left_chat_member.id == bot.id
        ):
            logger.info(
                f"[EVENT] Bot removed from: {chat.title} ({chat.id})"
            )
            if self.db:
                try:
                    if hasattr(self.db, 'execute_query'):
                        self.db.execute_query(
                            "UPDATE chats SET is_active = FALSE WHERE chat_id = %s",
                            (chat.id,)
                        )
                    else:
                        self.db.execute(
                            "UPDATE chats SET is_active = FALSE WHERE chat_id = %s",
                            (chat.id,)
                        )
                except Exception:
                    pass

    # ========================================================
    #         MEDIA / NON-TEXT MESSAGE HANDLER
    # ========================================================

    async def handle_media_message(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Handle photos, stickers, voice, video messages."""
        if not update.effective_message or not update.effective_user:
            return

        message = update.effective_message
        user = update.effective_user
        chat = update.effective_chat

        # Only respond if in private chat or active session
        if chat.type != ChatType.PRIVATE:
            if not self.db or not self.db.is_session_active(chat.id):
                return

        # Determine media type and respond accordingly
        media_responses = {
            "photo": [
                "Oooh photo! 📸 Meri AI aankhein nahi hain abhi 😭 But nice vibes lag raha hai! ✨",
                "Photo bhej di? 🤭 Dekhne ka mann hai par text hi padh sakti hoon abhi 😏💅",
            ],
            "sticker": [
                "Cute sticker! 🤭✨ Main bhi bhejti par text hi aa raha hai mere se 😭💅",
                "Sticker se baat karegi kya? 😏 Type kar na kuch! ✨",
            ],
            "voice": [
                "Voice message? 🎤 Beta sun nahi sakti abhi, type karke bata na 😤✨",
                "Arrey voice bhejdi! 😭 Main deaf hoon digitally, text mein bol na 💅",
            ],
            "video": [
                "Video! 🎬 Dekhne ka mann hai par abhi sirf text support hai 😭✨",
                "Video bhejdi? Nice! Par text mein baat kar na 😏💅",
            ],
            "document": [
                "Document bheja? 📄 Padhne ka time nahi hai abhi 😤 Seedha bol kya chahiye ✨",
            ],
            "animation": [
                "GIF! 🤭 Funny lagi hogi, par main text queen hoon 😏💅✨",
            ],
        }

        media_type = None
        if message.photo:
            media_type = "photo"
        elif message.sticker:
            media_type = "sticker"
        elif message.voice or message.audio:
            media_type = "voice"
        elif message.video or message.video_note:
            media_type = "video"
        elif message.document:
            media_type = "document"
        elif message.animation:
            media_type = "animation"

        if media_type and media_type in media_responses:
            response = random.choice(media_responses[media_type])
            await self._safe_reply(message, response)

    # ========================================================
    #             ERROR HANDLER
    # ========================================================

    async def error_handler(
        self, update: object, context: ContextTypes.DEFAULT_TYPE
    ):
        """Global error handler for all bot errors."""
        error = context.error

        # Classify and handle different error types
        if isinstance(error, NetworkError):
            logger.warning(f"[ERROR] Network: {error}")
            return

        if isinstance(error, TimedOut):
            logger.warning(f"[ERROR] Timeout: {error}")
            return

        if isinstance(error, RetryAfter):
            logger.warning(
                f"[ERROR] Rate limited: retry after {error.retry_after}s"
            )
            return

        if isinstance(error, Forbidden):
            logger.warning(f"[ERROR] Forbidden: {error}")
            return

        if isinstance(error, BadRequest):
            logger.error(f"[ERROR] BadRequest: {error}")
            return

        # Log unexpected errors with full traceback
        logger.error(
            f"[ERROR] Unhandled: {type(error).__name__}: {error}",
            exc_info=context.error
        )

        # Try to notify user
        if update and isinstance(update, Update):
            if update.effective_message:
                try:
                    await update.effective_message.reply_text(
                        "Oops! Kuch gadbad ho gayi 😭\n"
                        "Dubara try kar na please 🥺✨"
                    )
                except Exception:
                    pass

    # ========================================================
    #         HANDLER REGISTRATION
    # ========================================================

    def register_all(self, application: Application):
        """
        Register ALL handlers with the Telegram Application.
        This is the main registration method called from bot.py.
        """
        logger.info("[HANDLERS] Registering all handlers...")

        # === User Command Handlers ===
        user_commands = {
            "start": self.cmd_start,
            "help": self.cmd_help,
            "profile": self.cmd_profile,
            "clear": self.cmd_clear,
            "reset": self.cmd_reset,
            "lang": self.cmd_lang,
            "personality": self.cmd_personality,
            "usage": self.cmd_usage,
            "summary": self.cmd_summary,
        }

        for cmd_name, handler_func in user_commands.items():
            application.add_handler(
                CommandHandler(cmd_name, handler_func)
            )
            logger.debug(f"[HANDLERS] Registered /{cmd_name}")

        # === Admin Command Handlers ===
        admin_commands = {
            "admin": self.cmd_admin,
            "broadcast": self.cmd_broadcast,
            "totalusers": self.cmd_totalusers,
            "activeusers": self.cmd_activeusers,
            "forceclear": self.cmd_forceclear,
            "ban": self.cmd_ban,
            "unban": self.cmd_unban,
            "badwords": self.cmd_badwords,
            "addbadword": self.cmd_addbadword,
            "removebadword": self.cmd_removebadword,
            "setphrase": self.cmd_setphrase,
            "addadmin": self.cmd_addadmin,
            "removeadmin": self.cmd_removeadmin,
            "shutdown": self.cmd_shutdown,
            "restart": self.cmd_restart,
        }

        for cmd_name, handler_func in admin_commands.items():
            application.add_handler(
                CommandHandler(cmd_name, handler_func)
            )
            logger.debug(f"[HANDLERS] Registered /{cmd_name} (admin)")

        # === Callback Query Handler ===
        application.add_handler(
            CallbackQueryHandler(self.handle_callback_query)
        )
        logger.debug("[HANDLERS] Registered callback query handler")

        # === Text Message Handler (must be after commands) ===
        application.add_handler(
            MessageHandler(
                filters.TEXT & ~filters.COMMAND,
                self.handle_message
            )
        )
        logger.debug("[HANDLERS] Registered text message handler")

        # === Media Message Handlers ===
        media_filter = (
            filters.PHOTO | filters.Sticker.ALL |
            filters.VOICE | filters.AUDIO |
            filters.VIDEO | filters.VIDEO_NOTE |
            filters.Document.ALL | filters.ANIMATION
        )
        application.add_handler(
            MessageHandler(media_filter, self.handle_media_message)
        )
        logger.debug("[HANDLERS] Registered media message handler")

        # === Group Event Handlers ===
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
        logger.debug("[HANDLERS] Registered group event handlers")

        # === Error Handler ===
        application.add_error_handler(self.error_handler)
        logger.debug("[HANDLERS] Registered error handler")

        total = len(user_commands) + len(admin_commands) + 5
        logger.info(f"[HANDLERS] ✅ Total {total} handlers registered")

        return total

    async def setup_bot_commands(self, application: Application):
        """Set bot commands menu in Telegram."""
        try:
            commands = [
                BotCommand("start", "🌸 Start the bot"),
                BotCommand("help", "📋 Show help menu"),
                BotCommand("profile", "👤 View your profile"),
                BotCommand("clear", "🗑️ Clear chat memory"),
                BotCommand("reset", "🔄 Reset conversation"),
                BotCommand("lang", "🌐 Toggle language"),
                BotCommand("personality", "🎭 Check bot mood"),
                BotCommand("usage", "📊 Usage statistics"),
                BotCommand("summary", "📋 Summarize chat"),
                BotCommand("admin", "👑 Owner dashboard"),
            ]
            await application.bot.set_my_commands(commands)
            logger.info("[HANDLERS] Bot commands menu set ✓")
        except Exception as e:
            logger.warning(f"[HANDLERS] Failed to set commands: {e}")

    def get_handler_stats(self) -> Dict:
        """Get handler statistics."""
        return {
            "flood_control": self.flood_control.get_stats(),
            "wake_phrases": len(self.wake_detector.phrases),
            "bad_words": len(self.bad_word_filter.bad_words),
            "chat_locks": len(self._chat_locks),
            "owner_discovered": self._discovered_owner_id is not None,
            "owner_id": self._discovered_owner_id,
        }
        