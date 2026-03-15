#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════╗
║                                                                      ║
║              RUHI JI BOT — UTILITIES MODULE v2.0                    ║
║                                                                      ║
║   Common utility functions used across all modules                  ║
║                                                                      ║
║   Made with 💖 by @RUHI_VIG_QNR                                     ║
║                                                                      ║
╚══════════════════════════════════════════════════════════════════════╝
"""

import re
import time
import logging
from typing import Dict, List, Optional
from collections import defaultdict
from datetime import datetime, timezone

from config import Config

logger = logging.getLogger("RuhiJiBot.Utils")


# ============================================================
#           TEXT UTILITIES
# ============================================================

def escape_markdown(text: str) -> str:
    """Escape Telegram MarkdownV2 special characters."""
    special = [
        '_', '*', '[', ']', '(', ')', '~', '`',
        '>', '#', '+', '-', '=', '|', '{', '}', '.', '!'
    ]
    for char in special:
        text = text.replace(char, f'\\{char}')
    return text


def truncate_text(text: str, max_length: int = 4000) -> str:
    """Truncate text to maximum length with ellipsis."""
    if not text:
        return ""
    if len(text) <= max_length:
        return text
    return text[:max_length - 3] + "..."


def sanitize_input(text: str) -> str:
    """Sanitize user input text."""
    if not text:
        return ""
    text = text.replace("\x00", "")
    return text[:4000].strip()


def format_timestamp(dt: datetime) -> str:
    """Format a datetime for display."""
    if dt is None:
        return "Unknown"
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.strftime("%Y-%m-%d %H:%M:%S UTC")


def format_duration(seconds: float) -> str:
    """Format seconds into human-readable duration."""
    total = int(seconds)
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


def split_message(text: str, max_length: int = 4000) -> List[str]:
    """Split a long message into chunks respecting Telegram limits."""
    if len(text) <= max_length:
        return [text]
    chunks = []
    while text:
        if len(text) <= max_length:
            chunks.append(text)
            break
        # Try to split at newline
        split_at = text.rfind('\n', 0, max_length)
        if split_at == -1:
            split_at = text.rfind(' ', 0, max_length)
        if split_at == -1:
            split_at = max_length
        chunks.append(text[:split_at])
        text = text[split_at:].lstrip()
    return chunks


# ============================================================
#           USER / OWNER UTILITIES
# ============================================================

def is_owner(username: str = None, user_id: int = None) -> bool:
    """Check if user is the owner."""
    if username:
        clean = username.lstrip("@").lower()
        if clean == Config.OWNER_USERNAME.lower():
            return True
    if user_id and Config.OWNER_CHAT_ID:
        try:
            if int(user_id) == int(Config.OWNER_CHAT_ID):
                return True
        except (ValueError, TypeError):
            pass
    return False


def get_user_display_name(user) -> str:
    """Get display name from Telegram User object."""
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


# ============================================================
#           RATE LIMITER
# ============================================================

class RateLimiter:
    """Simple sliding window rate limiter."""

    def __init__(self, max_requests: int = 5, window: int = 10):
        self.max_requests = max_requests
        self.window = window
        self._data: Dict[int, List[float]] = defaultdict(list)

    def check(self, user_id: int) -> bool:
        """Returns True if request is allowed."""
        now = time.time()
        self._data[user_id] = [
            t for t in self._data[user_id]
            if now - t < self.window
        ]
        if len(self._data[user_id]) >= self.max_requests:
            return False
        self._data[user_id].append(now)
        return True

    def wait_time(self, user_id: int) -> float:
        """Get seconds until next allowed request."""
        if not self._data[user_id]:
            return 0
        oldest = min(self._data[user_id])
        return max(0, self.window - (time.time() - oldest))

    def is_allowed(self, user_id: int) -> bool:
        """Alias for check()."""
        return self.check(user_id)

    def get_wait_time(self, user_id: int) -> float:
        """Alias for wait_time()."""
        return self.wait_time(user_id)


# ============================================================
#           MESSAGE QUEUE
# ============================================================

class MessageQueue:
    """Simple async message queue for rate-limited sending."""

    def __init__(self, max_per_second: float = 25):
        self.max_per_second = max_per_second
        self.interval = 1.0 / max_per_second
        self.last_sent = 0

    async def wait(self):
        """Wait until we can send the next message."""
        import asyncio
        now = time.time()
        elapsed = now - self.last_sent
        if elapsed < self.interval:
            await asyncio.sleep(self.interval - elapsed)
        self.last_sent = time.time()
        