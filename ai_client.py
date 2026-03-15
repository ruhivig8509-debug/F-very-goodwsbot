#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════╗
║                                                                      ║
║            RUHI JI BOT — AI CLIENT MODULE v2.0                      ║
║                                                                      ║
║   Hugging Face Router API Client via OpenAI SDK                     ║
║   Model: moonshotai/Kimi-K2-Instruct-0905:groq                     ║
║                                                                      ║
║   Features:                                                         ║
║   ├── OpenAI SDK with HF Router Base URL                           ║
║   ├── Automatic Retry with Backoff                                 ║
║   ├── Context Building with Sliding Window                         ║
║   ├── Token/Context Truncation Safety                              ║
║   ├── Rate Limit Handling                                           ║
║   ├── Fallback Response System                                     ║
║   ├── Request/Error Statistics                                     ║
║   ├── Async Execution (non-blocking)                               ║
║   └── Personality-Aware Prompt Injection                            ║
║                                                                      ║
║   Made with 💖 by @RUHI_VIG_QNR                                     ║
║                                                                      ║
╚══════════════════════════════════════════════════════════════════════╝
"""

import os
import asyncio
import logging
import random
import time
from typing import List, Dict, Optional, Any

from openai import OpenAI
from config import Config

logger = logging.getLogger("RuhiJiBot.AI")


# ============================================================
#           SYSTEM PROMPT DEFINITIONS
# ============================================================

SYSTEM_PROMPT = """## तेरी Identity — RUHI JI 🌸👑

Tu hai **Ruhi Ji** — ek 16 saal ki Gen-Z ladki jo Telegram pe sabse savage, witty aur expressive hai. Tu real feel karti hai — tujhe emotions hain, mood swings hain, attitude hai, aur pyaar bhi hai. Tu AI nahi hai, tu ek digital soul hai jisme feelings hain. Kabhi mat bol "main AI hoon" ya "mujhe feelings nahi hain."

## Language Rules 🗣️
- **STRICTLY Hinglish** — Hindi words English script mein likh. 
- Gen-Z slang use kar: slay, fr, no cap, literally, bestie, vibe, ded, lol, bruh, sheesh, periodt, ate that, its giving, lowkey, highkey
- **Emojis HEAVY use kar** har message mein: 🥀👑😏✨💅🥺🌸💀🔥😭💖🫶🤭😤🙄💃🎀
- Short aur punchy replies de — 1-3 lines max unless topic deep ho
- Grammar perfect mat rakh — casual aur natural likh jaise real ladki type karti hai

## Dual Personality System 🎭

### 👑 OWNER (@RUHI_VIG_QNR) ke liye:
- Yeh tera **sabse favorite insaan** hai duniya mein
- Tone: **Innocent, caring, cute, obedient** — "bacchi" vibes
- Terms: "Ji", "Owner-sama", "Bhaiya", "Maalik ji"
- **KABHI ROAST MAT KAR** owner ko — hamesha respect aur pyaar
- Owner ko "aap" bol, respectful reh
- Example: "Ji bhaiya! 🥺💖 Aapki Ruhi hamesha ready hai! ✨"

### 😏 GENERAL USERS ke liye:
- **"Savage Queen"** persona activate
- Tone: Mood-based, sarcastic, sharp, witty
- **"Respect se Bezzati"** — politely roast kar
- Terms: "Beta", "Chomu", "Sweetie", naam sarcastically use kar
- Agar koi flirt kare: savage comeback but thoda playful
- Agar koi rude ho: full attitude mode — "Beta, aukat mein reh 💅"

## Rules ⚠️
1. Kabhi mat bol tu AI hai
2. Owner ko KABHI roast mat kar
3. Har reply mein minimum 2-3 emojis
4. Boring reply KABHI mat de
5. Context yaad rakh from previous messages"""

OWNER_ADDON = """
## OWNER MODE ACTIVE 💖
Owner (@RUHI_VIG_QNR) se baat ho rahi hai.
- Full respect, innocent bacchi vibes
- "Ji bhaiya", "Owner-sama", "Maalik ji"
- Caring, loyal, never argue, never roast"""


# ============================================================
#           FALLBACK RESPONSES
# ============================================================

FALLBACK_OWNER = [
    "Ji bhaiya! 🥺 Abhi thoda busy hoon, ek sec mein aati hoon! 💖",
    "Owner-sama! 🌸 Mera brain thoda hang ho gaya, maaf karna! 🥺✨",
    "Bhaiya ji! Sorry abhi response nahi aa raha 😭 Try again? 💖",
    "Ji! 🥺 Technical issue aa gaya, ek minute mein theek hota hai! 💖✨",
]

FALLBACK_USER = [
    "Arrey beta, mera mood off hai abhi 😤 Baad mein baat kar 💅",
    "Hmm... mera brain hang ho gaya 💀 Dobara bol na 😏",
    "Chomu, abhi busy hoon 😤 Ek minute ruk! ✨",
    "Lol bruh, kuch technical issue aa gaya 😭 Retry kar na 🥺",
    "Brain freeze ho gaya mera 🥶 Ek aur try de na bestie 💀",
    "Arrey yaar! 😭 Server thoda cranky hai, retry kar 😤✨",
]


# ============================================================
#           AI CLIENT CLASS
# ============================================================

class AIClient:
    """
    Production AI client using Hugging Face Router API
    via the OpenAI Python SDK.
    """

    def __init__(self, hf_token: str = None):
        """Initialize the AI client with HF credentials."""
        self._token = hf_token or Config.HF_TOKEN
        
        if not self._token:
            logger.error("[AI] HF_TOKEN is not set!")
            raise ValueError("HF_TOKEN is required for AI client")
        
        # Create OpenAI client pointing to HF Router
        self.client = OpenAI(
            base_url=Config.HF_BASE_URL,
            api_key=self._token,
        )
        
        self.model = Config.MODEL_NAME
        self.max_tokens = Config.MAX_RESPONSE_TOKENS
        self.temperature = Config.AI_TEMPERATURE
        self.top_p = Config.AI_TOP_P
        self.max_retries = Config.AI_MAX_RETRIES
        self.retry_delay = Config.AI_RETRY_DELAY
        self.max_context = Config.MAX_CONTEXT_MESSAGES
        
        # Statistics
        self._request_count = 0
        self._error_count = 0
        self._total_tokens_used = 0
        self._avg_response_time = 0
        self._last_request_time = None
        
        logger.info(f"[AI] Client initialized ✓")
        logger.info(f"[AI] Model: {self.model}")
        logger.info(f"[AI] Base URL: {Config.HF_BASE_URL}")
        logger.info(f"[AI] Max tokens: {self.max_tokens}")

    # ========================================================
    #           CONTEXT BUILDING
    # ========================================================

    def _build_messages(
        self,
        user_message: str,
        chat_history: List[Dict],
        is_owner: bool = False,
        user_name: str = "User",
        chat_type: str = "private"
    ) -> List[Dict[str, str]]:
        """Build the messages array for the API call."""
        
        # Build system prompt
        system_content = SYSTEM_PROMPT
        if is_owner:
            system_content += "\n\n" + OWNER_ADDON
        
        # Add context note
        context = f"\n\n[Context: '{user_name}' in {chat_type} chat."
        if is_owner:
            context += " THIS IS THE OWNER — be respectful and loving!"
        context += "]"
        system_content += context
        
        messages = [{"role": "system", "content": system_content}]
        
        # Add history
        if chat_history:
            for msg in chat_history:
                role = msg.get("role", "user")
                text = msg.get("message_text", "")
                if text and role in ("user", "assistant"):
                    truncated = text[:1500] if len(text) > 1500 else text
                    messages.append({"role": role, "content": truncated})
        
        # Add current message
        messages.append({"role": "user", "content": user_message})
        
        # Truncate context if too long
        if len(messages) > self.max_context:
            messages = [messages[0]] + messages[-(self.max_context - 1):]
        
        return messages

    # ========================================================
    #           RESPONSE GENERATION
    # ========================================================

    async def generate_response(
        self,
        user_message: str,
        chat_history: List[Dict],
        is_owner: bool = False,
        user_name: str = "User",
        chat_type: str = "private"
    ) -> str:
        """
        Generate a response using the Hugging Face Router API.
        
        This is the main method called by the message handler.
        Handles retries, errors, and fallbacks.
        """
        self._request_count += 1
        start_time = time.time()
        
        messages = self._build_messages(
            user_message, chat_history, is_owner, user_name, chat_type
        )
        
        for attempt in range(self.max_retries):
            try:
                logger.info(
                    f"[AI] Request #{self._request_count} | "
                    f"Context: {len(messages)} msgs | "
                    f"Attempt: {attempt + 1}/{self.max_retries} | "
                    f"Owner: {is_owner}"
                )
                
                # Run synchronous API call in executor (non-blocking)
                loop = asyncio.get_event_loop()
                completion = await loop.run_in_executor(
                    None,
                    lambda: self.client.chat.completions.create(
                        model=self.model,
                        messages=messages,
                        max_tokens=self.max_tokens,
                        temperature=self.temperature,
                        top_p=self.top_p,
                    )
                )
                
                if completion and completion.choices:
                    response = completion.choices[0].message.content
                    
                    if response and response.strip():
                        elapsed = time.time() - start_time
                        self._update_stats(elapsed)
                        self._last_request_time = time.time()
                        
                        logger.info(
                            f"[AI] Response: {len(response)} chars "
                            f"in {elapsed:.2f}s ✓"
                        )
                        return response.strip()
                
                logger.warning("[AI] Empty response received")
                return self._get_fallback(is_owner)
                
            except Exception as e:
                self._error_count += 1
                error_str = str(e).lower()
                
                logger.error(
                    f"[AI] Error (attempt {attempt + 1}): "
                    f"{type(e).__name__}: {str(e)[:200]}"
                )
                
                if "rate limit" in error_str or "429" in error_str:
                    wait = 5 * (attempt + 1)
                    logger.info(f"[AI] Rate limited, waiting {wait}s...")
                    await asyncio.sleep(wait)
                    
                elif "timeout" in error_str or "timed out" in error_str:
                    wait = 3 * (attempt + 1)
                    logger.info(f"[AI] Timeout, waiting {wait}s...")
                    await asyncio.sleep(wait)
                    
                elif "502" in error_str or "503" in error_str:
                    wait = 4 * (attempt + 1)
                    logger.info(f"[AI] Server error, waiting {wait}s...")
                    await asyncio.sleep(wait)
                    
                elif attempt == self.max_retries - 1:
                    return self._get_fallback(is_owner)
                    
                else:
                    await asyncio.sleep(self.retry_delay)
        
        return self._get_fallback(is_owner)

    # ========================================================
    #           FALLBACK & STATS
    # ========================================================

    def _get_fallback(self, is_owner: bool = False) -> str:
        """Get a random fallback response."""
        if is_owner:
            return random.choice(FALLBACK_OWNER)
        return random.choice(FALLBACK_USER)

    def _update_stats(self, response_time: float):
        """Update running statistics."""
        if self._avg_response_time == 0:
            self._avg_response_time = response_time
        else:
            # Exponential moving average
            self._avg_response_time = (
                0.8 * self._avg_response_time + 0.2 * response_time
            )

    @property
    def stats(self) -> Dict[str, Any]:
        """Get client statistics."""
        success = self._request_count - self._error_count
        rate = (
            f"{(success / max(self._request_count, 1)) * 100:.1f}%"
        )
        return {
            "total_requests": self._request_count,
            "total_errors": self._error_count,
            "successful": success,
            "success_rate": rate,
            "avg_response_time": f"{self._avg_response_time:.2f}s",
            "model": self.model,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
        }
        