#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════╗
║                                                                      ║
║              RUHI JI BOT — WEB SERVER MODULE v2.0                   ║
║                                                                      ║
║     Production-Grade Flask Web Server for Render.com Deployment      ║
║                                                                      ║
║   Features:                                                         ║
║   ├── Health Check Endpoints (/, /health, /ping)                    ║
║   ├── Bot Statistics Dashboard (HTML + JSON)                        ║
║   ├── Admin API Endpoints (secured)                                 ║
║   ├── Rate Limiting & IP Throttling                                 ║
║   ├── Request Logging & Analytics                                   ║
║   ├── Self-Ping Keep-Alive System                                   ║
║   ├── Uptime Monitoring Integration                                 ║
║   ├── Error Handling & Recovery                                     ║
║   ├── CORS Support                                                   ║
║   ├── Security Headers                                              ║
║   ├── Metrics Collection                                            ║
║   ├── Webhook Support (Optional)                                    ║
║   └── Beautiful HTML Dashboard                                      ║
║                                                                      ║
║   Made with 💖 by @RUHI_VIG_QNR                                     ║
║                                                                      ║
╚══════════════════════════════════════════════════════════════════════╝
"""

import os
import sys
import json
import time
import hashlib
import secrets
import logging
import threading
import traceback
import urllib.request
from datetime import datetime, timedelta, timezone
from functools import wraps
from typing import Optional, Dict, List, Any, Tuple
from collections import defaultdict, deque

# === Flask Imports ===
try:
    from flask import (
        Flask, jsonify, request, Response,
        render_template_string, abort, redirect,
        url_for, make_response, g
    )
except ImportError:
    print("[FATAL] Flask not installed! Run: pip install flask")
    sys.exit(1)

# === Logger Setup ===
logger = logging.getLogger("RuhiJiBot.WebServer")

# ============================================================
#             CONSTANTS & CONFIGURATION
# ============================================================

WEB_VERSION = "2.0.0"
SERVER_NAME = "Ruhi Ji Web Server"
MAX_REQUEST_SIZE = 1 * 1024 * 1024  # 1MB max request body
RATE_LIMIT_WINDOW = 60  # seconds
RATE_LIMIT_MAX_REQUESTS = 60  # per window
ADMIN_RATE_LIMIT = 30  # admin endpoints
ANALYTICS_MAX_ENTRIES = 1000  # max entries in analytics deque
SELF_PING_INTERVAL = 600  # 10 minutes in seconds
HEALTH_CHECK_TIMEOUT = 10  # seconds


# ============================================================
#          WEB SERVER RATE LIMITER
# ============================================================

class WebRateLimiter:
    """
    IP-based rate limiter for the web server.
    Prevents abuse of health check and API endpoints.
    Uses sliding window counter algorithm.
    """

    def __init__(
        self,
        max_requests: int = RATE_LIMIT_MAX_REQUESTS,
        window_seconds: int = RATE_LIMIT_WINDOW
    ):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._requests: Dict[str, deque] = defaultdict(deque)
        self._blocked_ips: Dict[str, float] = {}
        self._block_duration = 300  # 5 minutes block
        self._lock = threading.Lock()

        logger.info(
            f"[RATE_LIMIT] Initialized: {max_requests} req/"
            f"{window_seconds}s per IP"
        )

    def is_allowed(self, ip: str) -> bool:
        """Check if an IP is allowed to make a request."""
        with self._lock:
            now = time.time()

            # Check if IP is blocked
            if ip in self._blocked_ips:
                if now < self._blocked_ips[ip]:
                    return False
                else:
                    del self._blocked_ips[ip]

            # Clean old entries
            while (
                self._requests[ip]
                and now - self._requests[ip][0] > self.window_seconds
            ):
                self._requests[ip].popleft()

            # Check limit
            if len(self._requests[ip]) >= self.max_requests:
                # Auto-block for repeated violations
                self._blocked_ips[ip] = now + self._block_duration
                logger.warning(
                    f"[RATE_LIMIT] IP {ip} blocked for "
                    f"{self._block_duration}s (exceeded {self.max_requests} req)"
                )
                return False

            self._requests[ip].append(now)
            return True

    def get_remaining(self, ip: str) -> int:
        """Get remaining requests for an IP."""
        with self._lock:
            now = time.time()
            while (
                self._requests[ip]
                and now - self._requests[ip][0] > self.window_seconds
            ):
                self._requests[ip].popleft()
            return max(0, self.max_requests - len(self._requests[ip]))

    def get_reset_time(self, ip: str) -> float:
        """Get time until rate limit resets for an IP."""
        with self._lock:
            if not self._requests[ip]:
                return 0
            oldest = self._requests[ip][0]
            return max(0, self.window_seconds - (time.time() - oldest))

    def block_ip(self, ip: str, duration: int = 3600):
        """Manually block an IP address."""
        with self._lock:
            self._blocked_ips[ip] = time.time() + duration
            logger.info(f"[RATE_LIMIT] IP {ip} manually blocked for {duration}s")

    def unblock_ip(self, ip: str):
        """Unblock an IP address."""
        with self._lock:
            if ip in self._blocked_ips:
                del self._blocked_ips[ip]
                logger.info(f"[RATE_LIMIT] IP {ip} unblocked")

    def get_blocked_ips(self) -> List[Dict]:
        """Get list of currently blocked IPs."""
        with self._lock:
            now = time.time()
            blocked = []
            for ip, expires in list(self._blocked_ips.items()):
                if now < expires:
                    blocked.append({
                        "ip": ip,
                        "expires_in": round(expires - now, 1),
                        "expires_at": datetime.fromtimestamp(
                            expires, tz=timezone.utc
                        ).isoformat()
                    })
                else:
                    del self._blocked_ips[ip]
            return blocked

    def get_stats(self) -> Dict:
        """Get rate limiter statistics."""
        with self._lock:
            active_ips = len([
                ip for ip, reqs in self._requests.items()
                if reqs
            ])
            blocked_count = len(self._blocked_ips)
            return {
                "active_ips": active_ips,
                "blocked_ips": blocked_count,
                "max_requests": self.max_requests,
                "window_seconds": self.window_seconds,
            }

    def cleanup(self):
        """Clean up expired entries."""
        with self._lock:
            now = time.time()
            # Clean expired blocks
            expired = [
                ip for ip, exp in self._blocked_ips.items()
                if now >= exp
            ]
            for ip in expired:
                del self._blocked_ips[ip]

            # Clean empty request deques
            empty = [
                ip for ip, reqs in self._requests.items()
                if not reqs
            ]
            for ip in empty:
                del self._requests[ip]


# ============================================================
#          REQUEST ANALYTICS COLLECTOR
# ============================================================

class RequestAnalytics:
    """
    Collects and stores request analytics for monitoring.
    Uses an in-memory deque with a maximum size.
    """

    def __init__(self, max_entries: int = ANALYTICS_MAX_ENTRIES):
        self.max_entries = max_entries
        self._requests: deque = deque(maxlen=max_entries)
        self._endpoint_counts: Dict[str, int] = defaultdict(int)
        self._status_counts: Dict[int, int] = defaultdict(int)
        self._total_requests = 0
        self._total_errors = 0
        self._start_time = time.time()
        self._response_times: deque = deque(maxlen=500)
        self._lock = threading.Lock()

        logger.info(
            f"[ANALYTICS] Initialized with max {max_entries} entries"
        )

    def record_request(
        self,
        method: str,
        path: str,
        status_code: int,
        response_time: float,
        ip: str = "",
        user_agent: str = ""
    ):
        """Record a web request for analytics."""
        with self._lock:
            self._total_requests += 1
            if status_code >= 400:
                self._total_errors += 1

            self._endpoint_counts[path] += 1
            self._status_counts[status_code] += 1
            self._response_times.append(response_time)

            entry = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "method": method,
                "path": path,
                "status": status_code,
                "response_time_ms": round(response_time * 1000, 2),
                "ip": self._mask_ip(ip),
                "user_agent": user_agent[:100] if user_agent else ""
            }
            self._requests.append(entry)

    def _mask_ip(self, ip: str) -> str:
        """Mask IP for privacy — show first two octets only."""
        if not ip:
            return "unknown"
        parts = ip.split(".")
        if len(parts) == 4:
            return f"{parts[0]}.{parts[1]}.x.x"
        return ip[:10] + "..."

    def get_summary(self) -> Dict:
        """Get analytics summary."""
        with self._lock:
            uptime = time.time() - self._start_time
            avg_response = 0
            if self._response_times:
                avg_response = sum(self._response_times) / len(
                    self._response_times
                )

            # Top endpoints
            top_endpoints = sorted(
                self._endpoint_counts.items(),
                key=lambda x: x[1],
                reverse=True
            )[:10]

            return {
                "total_requests": self._total_requests,
                "total_errors": self._total_errors,
                "error_rate": (
                    f"{(self._total_errors / max(self._total_requests, 1)) * 100:.2f}%"
                ),
                "avg_response_time_ms": round(avg_response * 1000, 2),
                "uptime_seconds": round(uptime, 0),
                "uptime_human": self._format_uptime(uptime),
                "requests_per_minute": round(
                    self._total_requests / max(uptime / 60, 1), 2
                ),
                "top_endpoints": dict(top_endpoints),
                "status_codes": dict(self._status_counts),
            }

    def get_recent_requests(self, count: int = 50) -> List[Dict]:
        """Get recent request entries."""
        with self._lock:
            entries = list(self._requests)
            return entries[-count:] if len(entries) > count else entries

    def _format_uptime(self, seconds: float) -> str:
        """Format uptime in human-readable format."""
        days = int(seconds // 86400)
        hours = int((seconds % 86400) // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)

        parts = []
        if days > 0:
            parts.append(f"{days}d")
        if hours > 0:
            parts.append(f"{hours}h")
        if minutes > 0:
            parts.append(f"{minutes}m")
        parts.append(f"{secs}s")
        return " ".join(parts)

    def reset(self):
        """Reset all analytics data."""
        with self._lock:
            self._requests.clear()
            self._endpoint_counts.clear()
            self._status_counts.clear()
            self._total_requests = 0
            self._total_errors = 0
            self._response_times.clear()
            self._start_time = time.time()
            logger.info("[ANALYTICS] Data reset ✓")


# ============================================================
#            SELF-PING KEEP-ALIVE SYSTEM
# ============================================================

class SelfPingManager:
    """
    Self-ping system to keep Render.com free tier alive.
    Pings the bot's own health endpoint at regular intervals.
    Also supports external URLs for multi-service setups.
    """

    def __init__(
        self,
        render_url: str = "",
        interval: int = SELF_PING_INTERVAL
    ):
        self.render_url = render_url
        self.interval = interval
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self._ping_count = 0
        self._success_count = 0
        self._fail_count = 0
        self._last_ping_time: Optional[float] = None
        self._last_ping_status: Optional[int] = None
        self._external_urls: List[str] = []

        logger.info(
            f"[SELF_PING] Initialized | URL: {render_url} | "
            f"Interval: {interval}s"
        )

    def add_external_url(self, url: str):
        """Add an external URL to ping (e.g., UptimeRobot callback)."""
        if url and url.startswith("http"):
            self._external_urls.append(url)
            logger.info(f"[SELF_PING] Added external URL: {url}")

    def start(self):
        """Start the self-ping background thread."""
        if not self.render_url:
            logger.info("[SELF_PING] No RENDER_EXTERNAL_URL set, skipping")
            return

        self._running = True
        self._thread = threading.Thread(
            target=self._ping_loop,
            daemon=True,
            name="SelfPingThread"
        )
        self._thread.start()
        logger.info("[SELF_PING] Background ping thread started ✓")

    def stop(self):
        """Stop the self-ping thread."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("[SELF_PING] Ping thread stopped")

    def _ping_loop(self):
        """Main ping loop running in background thread."""
        # Initial delay to let server start up
        time.sleep(30)

        while self._running:
            try:
                self._perform_ping()
            except Exception as e:
                logger.debug(f"[SELF_PING] Loop error: {e}")

            # Sleep in small intervals so we can stop quickly
            for _ in range(self.interval):
                if not self._running:
                    break
                time.sleep(1)

    def _perform_ping(self):
        """Perform a single ping to the health endpoint."""
        self._ping_count += 1
        urls_to_ping = [f"{self.render_url}/health"]
        urls_to_ping.extend(self._external_urls)

        for url in urls_to_ping:
            try:
                req = urllib.request.Request(
                    url,
                    headers={
                        "User-Agent": f"RuhiJiBot-SelfPing/{WEB_VERSION}",
                        "Accept": "application/json"
                    }
                )
                with urllib.request.urlopen(
                    req, timeout=HEALTH_CHECK_TIMEOUT
                ) as resp:
                    status = resp.status
                    self._last_ping_status = status
                    self._last_ping_time = time.time()

                    if status == 200:
                        self._success_count += 1
                        logger.debug(
                            f"[SELF_PING] OK #{self._ping_count}: "
                            f"{url} -> {status}"
                        )
                    else:
                        self._fail_count += 1
                        logger.warning(
                            f"[SELF_PING] Non-200 #{self._ping_count}: "
                            f"{url} -> {status}"
                        )
            except urllib.error.URLError as e:
                self._fail_count += 1
                logger.debug(
                    f"[SELF_PING] URL error #{self._ping_count}: "
                    f"{url} -> {e}"
                )
            except Exception as e:
                self._fail_count += 1
                logger.debug(
                    f"[SELF_PING] Error #{self._ping_count}: "
                    f"{url} -> {e}"
                )

    def get_stats(self) -> Dict:
        """Get self-ping statistics."""
        return {
            "enabled": bool(self.render_url),
            "render_url": self.render_url or "not set",
            "interval_seconds": self.interval,
            "total_pings": self._ping_count,
            "successful": self._success_count,
            "failed": self._fail_count,
            "success_rate": (
                f"{(self._success_count / max(self._ping_count, 1)) * 100:.1f}%"
            ),
            "last_ping_time": (
                datetime.fromtimestamp(
                    self._last_ping_time, tz=timezone.utc
                ).isoformat()
                if self._last_ping_time else None
            ),
            "last_ping_status": self._last_ping_status,
            "external_urls": len(self._external_urls),
            "thread_alive": (
                self._thread.is_alive() if self._thread else False
            ),
        }


# ============================================================
#            SECURITY MIDDLEWARE
# ============================================================

class SecurityManager:
    """
    Security middleware for the Flask web server.
    Handles:
    - Security headers
    - Request validation
    - Admin authentication
    - CORS management
    """

    def __init__(self, admin_token: str = ""):
        self.admin_token = admin_token or self._generate_token()
        self._allowed_origins = [
            "https://uptimerobot.com",
            "https://render.com",
            "https://*.onrender.com"
        ]
        logger.info("[SECURITY] Manager initialized ✓")
        logger.info(f"[SECURITY] Admin token: {self.admin_token[:8]}...")

    def _generate_token(self) -> str:
        """Generate a random admin token."""
        token = secrets.token_hex(32)
        return token

    def get_security_headers(self) -> Dict[str, str]:
        """Get security headers to add to responses."""
        return {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Strict-Transport-Security": (
                "max-age=31536000; includeSubDomains"
            ),
            "Content-Security-Policy": "default-src 'self' 'unsafe-inline'",
            "Referrer-Policy": "no-referrer",
            "Server": "RuhiJi-WebServer",
            "X-Powered-By": "Ruhi Ji 👑",
            "Cache-Control": "no-store, no-cache, must-revalidate",
            "Pragma": "no-cache",
        }

    def validate_admin_token(self, provided_token: str) -> bool:
        """Validate an admin API token."""
        if not provided_token:
            return False
        return secrets.compare_digest(
            provided_token, self.admin_token
        )

    def get_client_ip(self) -> str:
        """Get the real client IP from request headers."""
        # Check proxy headers first (Render uses a reverse proxy)
        forwarded = request.headers.get("X-Forwarded-For", "")
        if forwarded:
            # Take the first IP (client IP)
            return forwarded.split(",")[0].strip()

        real_ip = request.headers.get("X-Real-IP", "")
        if real_ip:
            return real_ip.strip()

        return request.remote_addr or "unknown"

    def get_cors_headers(self, origin: str = "") -> Dict[str, str]:
        """Get CORS headers for cross-origin requests."""
        headers = {
            "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
            "Access-Control-Allow-Headers": (
                "Content-Type, Authorization, X-Admin-Token"
            ),
            "Access-Control-Max-Age": "3600",
        }

        if origin:
            headers["Access-Control-Allow-Origin"] = origin
        else:
            headers["Access-Control-Allow-Origin"] = "*"

        return headers


# ============================================================
#           SYSTEM METRICS COLLECTOR
# ============================================================

class SystemMetrics:
    """
    Collects system-level metrics for monitoring.
    Works within Render.com's constraints (no psutil dependency).
    """

    def __init__(self):
        self._start_time = time.time()
        self._memory_snapshots: deque = deque(maxlen=100)

    def get_metrics(self) -> Dict:
        """Collect and return current system metrics."""
        import gc

        uptime = time.time() - self._start_time

        metrics = {
            "uptime_seconds": round(uptime, 0),
            "uptime_human": self._format_duration(uptime),
            "python_version": sys.version.split()[0],
            "platform": sys.platform,
            "pid": os.getpid(),
            "thread_count": threading.active_count(),
            "active_threads": [t.name for t in threading.enumerate()],
            "gc_stats": {
                "collections": gc.get_count(),
                "objects_tracked": len(gc.get_objects())
                if len(gc.get_objects()) < 100000 else "100000+",
            },
        }

        # Try to get memory info from /proc (Linux/Render)
        try:
            with open("/proc/self/status", "r") as f:
                for line in f:
                    if line.startswith("VmRSS"):
                        # Resident memory in kB
                        parts = line.split()
                        if len(parts) >= 2:
                            mem_kb = int(parts[1])
                            metrics["memory_mb"] = round(
                                mem_kb / 1024, 2
                            )
                    elif line.startswith("VmSize"):
                        parts = line.split()
                        if len(parts) >= 2:
                            vm_kb = int(parts[1])
                            metrics["virtual_memory_mb"] = round(
                                vm_kb / 1024, 2
                            )
        except (FileNotFoundError, PermissionError):
            metrics["memory_mb"] = "N/A (not Linux)"

        # Try to get load average
        try:
            load = os.getloadavg()
            metrics["load_average"] = {
                "1min": round(load[0], 2),
                "5min": round(load[1], 2),
                "15min": round(load[2], 2),
            }
        except (OSError, AttributeError):
            metrics["load_average"] = "N/A"

        return metrics

    def _format_duration(self, seconds: float) -> str:
        """Format seconds into human-readable duration."""
        days = int(seconds // 86400)
        hours = int((seconds % 86400) // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)

        parts = []
        if days > 0:
            parts.append(f"{days} day{'s' if days > 1 else ''}")
        if hours > 0:
            parts.append(f"{hours} hour{'s' if hours > 1 else ''}")
        if minutes > 0:
            parts.append(f"{minutes} min{'s' if minutes > 1 else ''}")
        parts.append(f"{secs} sec{'s' if secs != 1 else ''}")
        return ", ".join(parts)


# ============================================================
#             HTML DASHBOARD TEMPLATES
# ============================================================

DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Ruhi Ji Bot — Dashboard 👑</title>
    <style>
        :root {
            --bg-primary: #0a0a0f;
            --bg-secondary: #12121a;
            --bg-card: #1a1a2e;
            --bg-card-hover: #1f1f35;
            --accent: #e94560;
            --accent-soft: #e9456033;
            --accent-glow: #e9456066;
            --text-primary: #ffffff;
            --text-secondary: #a0a0b8;
            --text-muted: #6c6c82;
            --border: #2a2a3e;
            --success: #00d97e;
            --warning: #f6c23e;
            --danger: #e74a3b;
            --info: #36b9cc;
            --gradient-1: linear-gradient(135deg, #e94560, #ff6b8a);
            --gradient-2: linear-gradient(135deg, #0f3460, #16213e);
            --gradient-3: linear-gradient(135deg, #533483, #e94560);
        }

        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
            background-color: var(--bg-primary);
            color: var(--text-primary);
            min-height: 100vh;
            overflow-x: hidden;
        }

        /* Animated background */
        body::before {
            content: '';
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background:
                radial-gradient(circle at 20% 50%, var(--accent-soft) 0%, transparent 50%),
                radial-gradient(circle at 80% 20%, rgba(83, 52, 131, 0.15) 0%, transparent 50%),
                radial-gradient(circle at 50% 80%, rgba(15, 52, 96, 0.2) 0%, transparent 50%);
            z-index: -1;
            animation: bgPulse 8s ease-in-out infinite;
        }

        @keyframes bgPulse {
            0%, 100% { opacity: 0.6; }
            50% { opacity: 1; }
        }

        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }

        /* Header */
        .header {
            text-align: center;
            padding: 40px 20px;
            margin-bottom: 30px;
            background: var(--gradient-2);
            border-radius: 20px;
            border: 1px solid var(--border);
            position: relative;
            overflow: hidden;
        }

        .header::after {
            content: '';
            position: absolute;
            top: -50%;
            left: -50%;
            width: 200%;
            height: 200%;
            background: radial-gradient(
                circle,
                var(--accent-soft) 0%,
                transparent 70%
            );
            animation: headerGlow 6s ease-in-out infinite;
        }

        @keyframes headerGlow {
            0%, 100% { transform: translate(-30%, -30%); opacity: 0.3; }
            50% { transform: translate(-20%, -20%); opacity: 0.6; }
        }

        .header h1 {
            font-size: 2.5em;
            margin-bottom: 10px;
            position: relative;
            z-index: 1;
            text-shadow: 0 0 30px var(--accent-glow);
        }

        .header p {
            color: var(--text-secondary);
            font-size: 1.1em;
            position: relative;
            z-index: 1;
        }

        .header .badge {
            display: inline-block;
            background: var(--gradient-1);
            color: white;
            padding: 5px 15px;
            border-radius: 20px;
            font-size: 0.85em;
            margin-top: 15px;
            position: relative;
            z-index: 1;
            animation: pulse 2s infinite;
        }

        @keyframes pulse {
            0%, 100% { box-shadow: 0 0 0 0 var(--accent-glow); }
            50% { box-shadow: 0 0 0 10px transparent; }
        }

        /* Status indicator */
        .status-dot {
            display: inline-block;
            width: 12px;
            height: 12px;
            border-radius: 50%;
            margin-right: 8px;
            animation: blink 1.5s infinite;
        }

        .status-dot.online {
            background: var(--success);
            box-shadow: 0 0 10px var(--success);
        }

        .status-dot.offline {
            background: var(--danger);
            box-shadow: 0 0 10px var(--danger);
        }

        @keyframes blink {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.4; }
        }

        /* Grid */
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }

        /* Cards */
        .card {
            background: var(--bg-card);
            border-radius: 16px;
            padding: 24px;
            border: 1px solid var(--border);
            transition: all 0.3s ease;
            position: relative;
            overflow: hidden;
        }

        .card:hover {
            background: var(--bg-card-hover);
            transform: translateY(-4px);
            box-shadow: 0 8px 30px rgba(233, 69, 96, 0.15);
            border-color: var(--accent);
        }

        .card::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 3px;
            background: var(--gradient-1);
        }

        .card h3 {
            font-size: 0.85em;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 12px;
        }

        .card .value {
            font-size: 2.2em;
            font-weight: 700;
            color: var(--text-primary);
            line-height: 1.2;
        }

        .card .subtitle {
            font-size: 0.85em;
            color: var(--text-secondary);
            margin-top: 8px;
        }

        .card .icon {
            font-size: 1.8em;
            position: absolute;
            top: 20px;
            right: 20px;
            opacity: 0.3;
        }

        /* Table */
        .table-card {
            background: var(--bg-card);
            border-radius: 16px;
            padding: 24px;
            border: 1px solid var(--border);
            margin-bottom: 30px;
            overflow-x: auto;
        }

        .table-card h2 {
            font-size: 1.3em;
            margin-bottom: 20px;
            color: var(--text-primary);
        }

        table {
            width: 100%;
            border-collapse: collapse;
        }

        th {
            text-align: left;
            padding: 12px 16px;
            font-size: 0.8em;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 1px;
            border-bottom: 2px solid var(--border);
        }

        td {
            padding: 12px 16px;
            font-size: 0.9em;
            color: var(--text-secondary);
            border-bottom: 1px solid var(--border);
        }

        tr:hover td {
            background: rgba(233, 69, 96, 0.05);
        }

        /* Status badges */
        .status-badge {
            display: inline-block;
            padding: 4px 12px;
            border-radius: 12px;
            font-size: 0.8em;
            font-weight: 600;
        }

        .status-badge.success {
            background: rgba(0, 217, 126, 0.15);
            color: var(--success);
        }

        .status-badge.danger {
            background: rgba(231, 74, 59, 0.15);
            color: var(--danger);
        }

        .status-badge.warning {
            background: rgba(246, 194, 62, 0.15);
            color: var(--warning);
        }

        /* Footer */
        .footer {
            text-align: center;
            padding: 30px;
            color: var(--text-muted);
            font-size: 0.85em;
        }

        .footer a {
            color: var(--accent);
            text-decoration: none;
        }

        .footer a:hover {
            text-decoration: underline;
        }

        /* Responsive */
        @media (max-width: 768px) {
            .header h1 { font-size: 1.8em; }
            .grid { grid-template-columns: 1fr; }
            .container { padding: 10px; }
            .card .value { font-size: 1.8em; }
        }

        /* Loading animation */
        .loading {
            display: inline-block;
            width: 20px;
            height: 20px;
            border: 2px solid var(--text-muted);
            border-top-color: var(--accent);
            border-radius: 50%;
            animation: spin 0.8s linear infinite;
        }

        @keyframes spin {
            to { transform: rotate(360deg); }
        }

        /* Auto-refresh indicator */
        .refresh-bar {
            position: fixed;
            top: 0;
            left: 0;
            height: 3px;
            background: var(--gradient-1);
            animation: refreshBar 30s linear infinite;
            z-index: 1000;
        }

        @keyframes refreshBar {
            from { width: 100%; }
            to { width: 0%; }
        }

        /* Endpoint list */
        .endpoint-list {
            list-style: none;
            padding: 0;
        }

        .endpoint-list li {
            padding: 10px 16px;
            border-bottom: 1px solid var(--border);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .endpoint-list li:last-child {
            border-bottom: none;
        }

        .endpoint-method {
            display: inline-block;
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 0.75em;
            font-weight: 700;
            margin-right: 8px;
        }

        .endpoint-method.get {
            background: rgba(54, 185, 204, 0.2);
            color: var(--info);
        }

        .endpoint-method.post {
            background: rgba(0, 217, 126, 0.2);
            color: var(--success);
        }
    </style>
</head>
<body>
    <div class="refresh-bar"></div>
    <div class="container">
        <div class="header">
            <h1>🌸 Ruhi Ji Bot 👑</h1>
            <p>Savage Queen — Telegram Bot Dashboard</p>
            <div class="badge">
                <span class="status-dot online"></span>
                {{ status | upper }}
            </div>
        </div>

        <div class="grid">
            <div class="card">
                <span class="icon">⏱️</span>
                <h3>Uptime</h3>
                <div class="value">{{ uptime }}</div>
                <div class="subtitle">Since {{ start_time }}</div>
            </div>

            <div class="card">
                <span class="icon">👥</span>
                <h3>Total Users</h3>
                <div class="value">{{ total_users }}</div>
                <div class="subtitle">Registered in database</div>
            </div>

            <div class="card">
                <span class="icon">💬</span>
                <h3>Total Chats</h3>
                <div class="value">{{ total_chats }}</div>
                <div class="subtitle">Groups + Private</div>
            </div>

            <div class="card">
                <span class="icon">📝</span>
                <h3>Total Messages</h3>
                <div class="value">{{ total_messages }}</div>
                <div class="subtitle">Stored in memory</div>
            </div>

            <div class="card">
                <span class="icon">🤖</span>
                <h3>AI Model</h3>
                <div class="value" style="font-size:1em;">Kimi-K2</div>
                <div class="subtitle">moonshotai/Kimi-K2-Instruct</div>
            </div>

            <div class="card">
                <span class="icon">🌐</span>
                <h3>Web Requests</h3>
                <div class="value">{{ web_requests }}</div>
                <div class="subtitle">Total HTTP requests</div>
            </div>
        </div>

        <div class="table-card">
            <h2>📡 API Endpoints</h2>
            <ul class="endpoint-list">
                <li>
                    <span>
                        <span class="endpoint-method get">GET</span>
                        <code>/</code> — Dashboard (this page)
                    </span>
                    <span class="status-badge success">Active</span>
                </li>
                <li>
                    <span>
                        <span class="endpoint-method get">GET</span>
                        <code>/health</code> — Health check (JSON)
                    </span>
                    <span class="status-badge success">Active</span>
                </li>
                <li>
                    <span>
                        <span class="endpoint-method get">GET</span>
                        <code>/ping</code> — Simple ping-pong
                    </span>
                    <span class="status-badge success">Active</span>
                </li>
                <li>
                    <span>
                        <span class="endpoint-method get">GET</span>
                        <code>/stats</code> — Bot statistics (JSON)
                    </span>
                    <span class="status-badge success">Active</span>
                </li>
                <li>
                    <span>
                        <span class="endpoint-method get">GET</span>
                        <code>/api/metrics</code> — System metrics
                    </span>
                    <span class="status-badge success">Active</span>
                </li>
                <li>
                    <span>
                        <span class="endpoint-method get">GET</span>
                        <code>/api/analytics</code> — Request analytics
                    </span>
                    <span class="status-badge success">Active</span>
                </li>
                <li>
                    <span>
                        <span class="endpoint-method get">GET</span>
                        <code>/api/self-ping</code> — Self-ping stats
                    </span>
                    <span class="status-badge success">Active</span>
                </li>
                <li>
                    <span>
                        <span class="endpoint-method get">GET</span>
                        <code>/status</code> — Full status page (HTML)
                    </span>
                    <span class="status-badge success">Active</span>
                </li>
            </ul>
        </div>

        <div class="footer">
            <p>
                🌸 <strong>Ruhi Ji Bot</strong> v{{ version }} |
                Made with 💖 by
                <a href="https://t.me/RUHI_VIG_QNR" target="_blank">
                    @RUHI_VIG_QNR
                </a>
            </p>
            <p style="margin-top:8px;">
                Powered by Kimi-K2-Instruct | Hosted on Render.com
            </p>
            <p style="margin-top:5px; font-size:0.8em;">
                Auto-refreshes every 30 seconds
            </p>
        </div>
    </div>

    <script>
        // Auto-refresh every 30 seconds
        setTimeout(function() {
            location.reload();
        }, 30000);
    </script>
</body>
</html>
"""

# ============================================================
#          HEALTH STATUS PAGE HTML
# ============================================================

STATUS_PAGE_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Ruhi Ji — System Status</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', system-ui, sans-serif;
            background: #0a0a0f;
            color: #fff;
            padding: 20px;
            min-height: 100vh;
        }
        .container { max-width: 900px; margin: 0 auto; }
        h1 {
            text-align: center;
            margin-bottom: 30px;
            font-size: 2em;
            text-shadow: 0 0 20px rgba(233,69,96,0.5);
        }
        .section {
            background: #1a1a2e;
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 20px;
            border: 1px solid #2a2a3e;
        }
        .section h2 {
            font-size: 1.2em;
            margin-bottom: 15px;
            color: #e94560;
        }
        .metric {
            display: flex;
            justify-content: space-between;
            padding: 8px 0;
            border-bottom: 1px solid #2a2a3e;
        }
        .metric:last-child { border-bottom: none; }
        .metric-label { color: #a0a0b8; }
        .metric-value { color: #fff; font-weight: 600; }
        .ok { color: #00d97e; }
        .err { color: #e74a3b; }
        .warn { color: #f6c23e; }
        pre {
            background: #12121a;
            padding: 15px;
            border-radius: 8px;
            overflow-x: auto;
            font-size: 0.85em;
            color: #a0a0b8;
        }
        .footer {
            text-align: center;
            padding: 20px;
            color: #6c6c82;
            font-size: 0.85em;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🌸 Ruhi Ji — System Status 👑</h1>

        <div class="section">
            <h2>🟢 Service Status</h2>
            <div class="metric">
                <span class="metric-label">Bot Status</span>
                <span class="metric-value ok">● Online</span>
            </div>
            <div class="metric">
                <span class="metric-label">Web Server</span>
                <span class="metric-value ok">● Running</span>
            </div>
            <div class="metric">
                <span class="metric-label">Database</span>
                <span class="metric-value {{ 'ok' if db_ok else 'err' }}">
                    {{ '● Connected' if db_ok else '● Error' }}
                </span>
            </div>
            <div class="metric">
                <span class="metric-label">AI Model</span>
                <span class="metric-value ok">● Ready</span>
            </div>
        </div>

        <div class="section">
            <h2>📊 System Metrics</h2>
            <div class="metric">
                <span class="metric-label">Uptime</span>
                <span class="metric-value">{{ uptime }}</span>
            </div>
            <div class="metric">
                <span class="metric-label">Memory Usage</span>
                <span class="metric-value">{{ memory }}MB</span>
            </div>
            <div class="metric">
                <span class="metric-label">Active Threads</span>
                <span class="metric-value">{{ threads }}</span>
            </div>
            <div class="metric">
                <span class="metric-label">Python Version</span>
                <span class="metric-value">{{ python_version }}</span>
            </div>
            <div class="metric">
                <span class="metric-label">PID</span>
                <span class="metric-value">{{ pid }}</span>
            </div>
        </div>

        <div class="section">
            <h2>🤖 Bot Statistics</h2>
            <div class="metric">
                <span class="metric-label">Total Users</span>
                <span class="metric-value">{{ total_users }}</span>
            </div>
            <div class="metric">
                <span class="metric-label">Total Chats</span>
                <span class="metric-value">{{ total_chats }}</span>
            </div>
            <div class="metric">
                <span class="metric-label">Total Messages</span>
                <span class="metric-value">{{ total_messages }}</span>
            </div>
            <div class="metric">
                <span class="metric-label">Web Requests</span>
                <span class="metric-value">{{ web_requests }}</span>
            </div>
        </div>

        <div class="section">
            <h2>📡 Self-Ping Status</h2>
            <div class="metric">
                <span class="metric-label">Total Pings</span>
                <span class="metric-value">{{ ping_total }}</span>
            </div>
            <div class="metric">
                <span class="metric-label">Successful</span>
                <span class="metric-value ok">{{ ping_success }}</span>
            </div>
            <div class="metric">
                <span class="metric-label">Failed</span>
                <span class="metric-value {{ 'err' if ping_failed > 0 else 'ok' }}">
                    {{ ping_failed }}
                </span>
            </div>
        </div>

        <div class="footer">
            Made with 💖 by @RUHI_VIG_QNR | v{{ version }}
            <br>Auto-refreshes every 30s
        </div>
    </div>
    <script>setTimeout(()=>location.reload(), 30000);</script>
</body>
</html>
"""

# ============================================================
#         ERROR PAGE HTML
# ============================================================

ERROR_PAGE_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ error_code }} — Ruhi Ji</title>
    <style>
        * { margin:0; padding:0; box-sizing:border-box; }
        body {
            font-family: system-ui, sans-serif;
            background: #0a0a0f;
            color: #fff;
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
            text-align: center;
        }
        .error-container {
            background: #1a1a2e;
            border-radius: 20px;
            padding: 50px 40px;
            border: 1px solid #2a2a3e;
            max-width: 500px;
        }
        .error-code {
            font-size: 5em;
            font-weight: 800;
            color: #e94560;
            text-shadow: 0 0 30px rgba(233,69,96,0.4);
        }
        .error-message {
            font-size: 1.2em;
            color: #a0a0b8;
            margin: 15px 0 30px;
        }
        .error-emoji { font-size: 3em; margin-bottom: 15px; }
        a {
            display: inline-block;
            background: linear-gradient(135deg, #e94560, #ff6b8a);
            color: #fff;
            text-decoration: none;
            padding: 12px 30px;
            border-radius: 10px;
            font-weight: 600;
            transition: transform 0.2s;
        }
        a:hover { transform: translateY(-2px); }
    </style>
</head>
<body>
    <div class="error-container">
        <div class="error-emoji">{{ emoji }}</div>
        <div class="error-code">{{ error_code }}</div>
        <div class="error-message">{{ message }}</div>
        <a href="/">← Back to Dashboard</a>
    </div>
</body>
</html>
"""


# ============================================================
#           MAIN FLASK APP FACTORY
# ============================================================

def create_flask_app(
    db_manager=None,
    start_time=None,
    ai_client=None,
    bot_instance=None
) -> Flask:
    """
    Create and configure the production Flask application.

    This is the main factory function that sets up:
    - All route handlers
    - Middleware (rate limiting, security, analytics)
    - Error handlers
    - Self-ping system
    - HTML dashboard
    - JSON API endpoints

    Args:
        db_manager: Database manager instance for stats
        start_time: Bot start datetime for uptime calculation
        ai_client: AI client instance for stats
        bot_instance: Main bot instance for stats

    Returns:
        Configured Flask application
    """

    # === Create Flask App ===
    app = Flask(__name__)
    app.config["MAX_CONTENT_LENGTH"] = MAX_REQUEST_SIZE
    app.config["JSON_SORT_KEYS"] = False

    # === Initialize Components ===
    _start_time = start_time or datetime.now(timezone.utc)
    rate_limiter = WebRateLimiter()
    analytics = RequestAnalytics()
    security = SecurityManager(
        admin_token=os.environ.get("ADMIN_API_TOKEN", "")
    )
    system_metrics = SystemMetrics()

    render_url = os.environ.get("RENDER_EXTERNAL_URL", "")
    self_ping = SelfPingManager(render_url=render_url)

    logger.info("[WEB] Creating Flask application...")
    logger.info(f"[WEB] Render URL: {render_url or 'not set'}")

    # ========================================================
    #              MIDDLEWARE — Before Request
    # ========================================================

    @app.before_request
    def before_request_handler():
        """Execute before every request."""
        # Store request start time for analytics
        g.request_start_time = time.time()
        g.client_ip = security.get_client_ip()

        # Rate limiting
        if not rate_limiter.is_allowed(g.client_ip):
            remaining = rate_limiter.get_remaining(g.client_ip)
            reset_time = rate_limiter.get_reset_time(g.client_ip)

            response = jsonify({
                "error": "Rate limit exceeded",
                "message": "Too many requests. Thoda slow ho ja beta 😤💅",
                "retry_after": round(reset_time, 1),
                "remaining": remaining
            })
            response.status_code = 429
            response.headers["Retry-After"] = str(int(reset_time))
            response.headers["X-RateLimit-Limit"] = str(
                rate_limiter.max_requests
            )
            response.headers["X-RateLimit-Remaining"] = str(remaining)
            return response

        # Skip logging for favicon and health checks to reduce noise
        if request.path not in ("/favicon.ico",):
            logger.debug(
                f"[WEB] {request.method} {request.path} "
                f"from {g.client_ip}"
            )

    # ========================================================
    #              MIDDLEWARE — After Request
    # ========================================================

    @app.after_request
    def after_request_handler(response):
        """Execute after every request — add headers & analytics."""
        # Add security headers
        for header, value in security.get_security_headers().items():
            response.headers[header] = value

        # Add CORS headers
        origin = request.headers.get("Origin", "")
        for header, value in security.get_cors_headers(origin).items():
            response.headers[header] = value

        # Add rate limit headers
        client_ip = getattr(g, "client_ip", "unknown")
        remaining = rate_limiter.get_remaining(client_ip)
        response.headers["X-RateLimit-Limit"] = str(
            rate_limiter.max_requests
        )
        response.headers["X-RateLimit-Remaining"] = str(remaining)

        # Record analytics
        request_time = time.time() - getattr(
            g, "request_start_time", time.time()
        )
        analytics.record_request(
            method=request.method,
            path=request.path,
            status_code=response.status_code,
            response_time=request_time,
            ip=client_ip,
            user_agent=request.headers.get("User-Agent", "")
        )

        return response

    # ========================================================
    #         HELPER — Get Database Stats Safely
    # ========================================================

    def _get_db_stats() -> Dict:
        """Safely get database statistics."""
        stats = {
            "total_users": 0,
            "total_chats": 0,
            "total_messages": 0,
            "db_connected": False,
            "active_sessions": 0,
            "banned_users": 0,
        }

        if not db_manager:
            return stats

        try:
            # Try using execute_query (EmbeddedDatabaseManager)
            if hasattr(db_manager, "get_total_users"):
                stats["total_users"] = db_manager.get_total_users()
                stats["total_chats"] = db_manager.get_total_chats()
                stats["total_messages"] = db_manager.get_total_messages()
                stats["db_connected"] = True

                if hasattr(db_manager, "get_active_sessions_count"):
                    stats["active_sessions"] = (
                        db_manager.get_active_sessions_count()
                    )
                if hasattr(db_manager, "get_banned_users_count"):
                    stats["banned_users"] = (
                        db_manager.get_banned_users_count()
                    )
            elif hasattr(db_manager, "execute"):
                result = db_manager.execute(
                    "SELECT 1 as ok", fetch_one=True
                )
                stats["db_connected"] = bool(result)
        except Exception as e:
            logger.warning(f"[WEB] DB stats error: {e}")
            stats["db_connected"] = False

        return stats

    def _get_uptime() -> str:
        """Get formatted uptime string."""
        delta = datetime.now(timezone.utc) - _start_time
        total_seconds = int(delta.total_seconds())
        days = total_seconds // 86400
        hours = (total_seconds % 86400) // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60

        parts = []
        if days > 0:
            parts.append(f"{days}d")
        if hours > 0:
            parts.append(f"{hours}h")
        if minutes > 0:
            parts.append(f"{minutes}m")
        parts.append(f"{seconds}s")
        return " ".join(parts)

    def _get_ai_stats() -> Dict:
        """Get AI client stats safely."""
        if ai_client and hasattr(ai_client, "stats"):
            return ai_client.stats
        return {
            "total_requests": 0,
            "total_errors": 0,
            "model": "moonshotai/Kimi-K2-Instruct-0905:groq",
            "success_rate": "N/A"
        }

    # ========================================================
    #         DECORATOR — Admin Authentication
    # ========================================================

    def require_admin(f):
        """Decorator to require admin token for API endpoints."""
        @wraps(f)
        def decorated(*args, **kwargs):
            token = request.headers.get("X-Admin-Token", "")
            if not token:
                token = request.args.get("token", "")

            if not security.validate_admin_token(token):
                return jsonify({
                    "error": "Unauthorized",
                    "message": "Invalid admin token. Beta, permission nahi hai 😤💅"
                }), 401

            return f(*args, **kwargs)
        return decorated

    # ========================================================
    #              CORE ROUTES
    # ========================================================

    @app.route("/")
    def dashboard():
        """
        Root endpoint — Beautiful HTML dashboard.
        Shows bot status, stats, and available endpoints.
        """
        db_stats = _get_db_stats()
        uptime = _get_uptime()
        web_stats = analytics.get_summary()

        try:
            return render_template_string(
                DASHBOARD_HTML,
                status="online",
                uptime=uptime,
                start_time=_start_time.strftime("%Y-%m-%d %H:%M UTC"),
                total_users=db_stats["total_users"],
                total_chats=db_stats["total_chats"],
                total_messages=db_stats["total_messages"],
                web_requests=web_stats["total_requests"],
                version=WEB_VERSION,
            )
        except Exception as e:
            logger.error(f"[WEB] Dashboard render error: {e}")
            # Fallback to JSON
            return jsonify({
                "status": "alive",
                "bot": "Ruhi Ji 👑",
                "version": WEB_VERSION,
                "uptime": uptime,
                "error": "Dashboard render failed, showing JSON"
            }), 200

    @app.route("/health")
    def health_check():
        """
        Health check endpoint — Primary endpoint for UptimeRobot
        and Render.com health monitoring.

        Returns:
            200 JSON with database and bot status.
        """
        db_stats = _get_db_stats()
        uptime = _get_uptime()

        # Determine overall health
        is_healthy = db_stats["db_connected"]

        response_data = {
            "status": "healthy" if is_healthy else "degraded",
            "bot": "running",
            "database": (
                "connected" if db_stats["db_connected"] else "error"
            ),
            "uptime": uptime,
            "model": "moonshotai/Kimi-K2-Instruct-0905:groq",
            "version": WEB_VERSION,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "checks": {
                "web_server": "ok",
                "database": "ok" if db_stats["db_connected"] else "error",
                "bot_process": "ok",
            }
        }

        status_code = 200 if is_healthy else 503
        return jsonify(response_data), status_code

    @app.route("/ping")
    def ping():
        """
        Simple ping-pong endpoint.
        Fastest possible response for uptime monitoring.
        """
        return "pong", 200, {"Content-Type": "text/plain"}

    @app.route("/health/live")
    def liveness():
        """
        Liveness probe — checks if the process is alive.
        Always returns 200 unless the server itself is down.
        """
        return jsonify({
            "status": "alive",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }), 200

    @app.route("/health/ready")
    def readiness():
        """
        Readiness probe — checks if the service can handle requests.
        Verifies database connectivity.
        """
        db_stats = _get_db_stats()

        if db_stats["db_connected"]:
            return jsonify({
                "status": "ready",
                "database": "connected",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }), 200
        else:
            return jsonify({
                "status": "not_ready",
                "database": "disconnected",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }), 503

    # ========================================================
    #              STATISTICS ROUTES
    # ========================================================

    @app.route("/stats")
    def stats():
        """
        Bot statistics endpoint — Returns comprehensive stats.
        """
        db_stats = _get_db_stats()
        ai_stats = _get_ai_stats()
        uptime = _get_uptime()

        return jsonify({
            "bot": {
                "name": "Ruhi Ji 👑",
                "version": WEB_VERSION,
                "status": "online",
                "uptime": uptime,
                "owner": "@RUHI_VIG_QNR",
                "model": ai_stats.get("model", "Kimi-K2-Instruct"),
            },
            "database": {
                "connected": db_stats["db_connected"],
                "total_users": db_stats["total_users"],
                "total_chats": db_stats["total_chats"],
                "total_messages": db_stats["total_messages"],
                "active_sessions": db_stats.get("active_sessions", 0),
                "banned_users": db_stats.get("banned_users", 0),
            },
            "ai": ai_stats,
            "web": analytics.get_summary(),
            "self_ping": self_ping.get_stats(),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }), 200

    @app.route("/stats/db")
    def stats_db():
        """Database-specific statistics."""
        db_stats = _get_db_stats()
        return jsonify({
            "database": db_stats,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }), 200

    @app.route("/stats/ai")
    def stats_ai():
        """AI client statistics."""
        ai_stats = _get_ai_stats()
        return jsonify({
            "ai": ai_stats,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }), 200

    @app.route("/stats/web")
    def stats_web():
        """Web server statistics."""
        return jsonify({
            "web": analytics.get_summary(),
            "rate_limiter": rate_limiter.get_stats(),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }), 200

    # ========================================================
    #              STATUS PAGE (HTML)
    # ========================================================

    @app.route("/status")
    def status_page():
        """
        Full system status page — Beautiful HTML view
        with all system metrics and statuses.
        """
        db_stats = _get_db_stats()
        sys_metrics = system_metrics.get_metrics()
        ping_stats = self_ping.get_stats()
        web_stats = analytics.get_summary()
        uptime = _get_uptime()

        try:
            return render_template_string(
                STATUS_PAGE_HTML,
                db_ok=db_stats["db_connected"],
                uptime=uptime,
                memory=sys_metrics.get("memory_mb", "N/A"),
                threads=sys_metrics.get("thread_count", 0),
                python_version=sys_metrics.get("python_version", "N/A"),
                pid=sys_metrics.get("pid", "N/A"),
                total_users=db_stats["total_users"],
                total_chats=db_stats["total_chats"],
                total_messages=db_stats["total_messages"],
                web_requests=web_stats["total_requests"],
                ping_total=ping_stats.get("total_pings", 0),
                ping_success=ping_stats.get("successful", 0),
                ping_failed=ping_stats.get("failed", 0),
                version=WEB_VERSION,
            )
        except Exception as e:
            logger.error(f"[WEB] Status page error: {e}")
            return jsonify({"error": "Status page render failed"}), 500

    # ========================================================
    #              API ROUTES
    # ========================================================

    @app.route("/api/metrics")
    def api_metrics():
        """System metrics endpoint."""
        metrics = system_metrics.get_metrics()
        return jsonify({
            "metrics": metrics,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }), 200

    @app.route("/api/analytics")
    def api_analytics():
        """Request analytics endpoint."""
        summary = analytics.get_summary()
        return jsonify({
            "analytics": summary,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }), 200

    @app.route("/api/analytics/recent")
    def api_analytics_recent():
        """Recent requests analytics."""
        count = request.args.get("count", 50, type=int)
        count = min(count, 200)  # Cap at 200

        recent = analytics.get_recent_requests(count)
        return jsonify({
            "recent_requests": recent,
            "count": len(recent),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }), 200

    @app.route("/api/self-ping")
    def api_self_ping():
        """Self-ping system status."""
        return jsonify({
            "self_ping": self_ping.get_stats(),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }), 200

    @app.route("/api/rate-limit")
    def api_rate_limit():
        """Rate limiter status for the requesting IP."""
        client_ip = security.get_client_ip()
        remaining = rate_limiter.get_remaining(client_ip)
        reset = rate_limiter.get_reset_time(client_ip)

        return jsonify({
            "ip": client_ip[:10] + "...",
            "remaining_requests": remaining,
            "max_requests": rate_limiter.max_requests,
            "window_seconds": rate_limiter.window_seconds,
            "reset_in_seconds": round(reset, 1),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }), 200

    @app.route("/api/version")
    def api_version():
        """Version information."""
        return jsonify({
            "bot_name": "Ruhi Ji",
            "version": WEB_VERSION,
            "python_version": sys.version.split()[0],
            "model": "moonshotai/Kimi-K2-Instruct-0905:groq",
            "owner": "@RUHI_VIG_QNR",
            "api_base": "https://router.huggingface.co/v1",
            "features": [
                "dual_personality",
                "sliding_window_memory",
                "wake_phrase_activation",
                "session_management",
                "admin_dashboard",
                "broadcast_system",
                "bad_word_filter",
                "rate_limiting",
                "self_ping_keepalive",
                "html_dashboard",
            ],
            "timestamp": datetime.now(timezone.utc).isoformat()
        }), 200

    @app.route("/api/uptime")
    def api_uptime():
        """Detailed uptime information."""
        now = datetime.now(timezone.utc)
        delta = now - _start_time
        total_seconds = delta.total_seconds()

        return jsonify({
            "uptime_seconds": round(total_seconds, 0),
            "uptime_human": _get_uptime(),
            "start_time": _start_time.isoformat(),
            "current_time": now.isoformat(),
            "days": delta.days,
            "hours": int((total_seconds % 86400) // 3600),
            "minutes": int((total_seconds % 3600) // 60),
            "timestamp": now.isoformat()
        }), 200

    # ========================================================
    #           ADMIN API ROUTES (Protected)
    # ========================================================

    @app.route("/api/admin/stats")
    @require_admin
    def admin_stats():
        """Admin-only detailed statistics."""
        db_stats = _get_db_stats()
        ai_stats = _get_ai_stats()
        web_stats = analytics.get_summary()
        sys_stats = system_metrics.get_metrics()
        ping_stats = self_ping.get_stats()
        rl_stats = rate_limiter.get_stats()

        return jsonify({
            "admin": True,
            "database": db_stats,
            "ai": ai_stats,
            "web": web_stats,
            "system": sys_stats,
            "self_ping": ping_stats,
            "rate_limiter": rl_stats,
            "blocked_ips": rate_limiter.get_blocked_ips(),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }), 200

    @app.route("/api/admin/block-ip", methods=["POST"])
    @require_admin
    def admin_block_ip():
        """Admin: Block an IP address."""
        data = request.get_json(silent=True) or {}
        ip = data.get("ip", "")
        duration = data.get("duration", 3600)

        if not ip:
            return jsonify({"error": "IP address required"}), 400

        rate_limiter.block_ip(ip, duration)
        return jsonify({
            "success": True,
            "message": f"IP {ip} blocked for {duration}s",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }), 200

    @app.route("/api/admin/unblock-ip", methods=["POST"])
    @require_admin
    def admin_unblock_ip():
        """Admin: Unblock an IP address."""
        data = request.get_json(silent=True) or {}
        ip = data.get("ip", "")

        if not ip:
            return jsonify({"error": "IP address required"}), 400

        rate_limiter.unblock_ip(ip)
        return jsonify({
            "success": True,
            "message": f"IP {ip} unblocked",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }), 200

    @app.route("/api/admin/blocked-ips")
    @require_admin
    def admin_blocked_ips():
        """Admin: List blocked IPs."""
        return jsonify({
            "blocked_ips": rate_limiter.get_blocked_ips(),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }), 200

    @app.route("/api/admin/reset-analytics", methods=["POST"])
    @require_admin
    def admin_reset_analytics():
        """Admin: Reset analytics data."""
        analytics.reset()
        return jsonify({
            "success": True,
            "message": "Analytics data reset",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }), 200

    @app.route("/api/admin/cleanup", methods=["POST"])
    @require_admin
    def admin_cleanup():
        """Admin: Trigger manual cleanup."""
        rate_limiter.cleanup()
        return jsonify({
            "success": True,
            "message": "Cleanup completed",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }), 200

    @app.route("/api/admin/config")
    @require_admin
    def admin_config():
        """Admin: View current configuration (redacted)."""
        return jsonify({
            "config": {
                "bot_token": "***" + (
                    os.environ.get("BOT_TOKEN", "")[-6:]
                    if os.environ.get("BOT_TOKEN") else "not set"
                ),
                "hf_token": "***" + (
                    os.environ.get("HF_TOKEN", "")[-6:]
                    if os.environ.get("HF_TOKEN") else "not set"
                ),
                "database_url": "***configured***" if (
                    os.environ.get("DATABASE_URL")
                ) else "not set",
                "owner_username": os.environ.get(
                    "OWNER_USERNAME", "RUHI_VIG_QNR"
                ),
                "max_group_memory": int(
                    os.environ.get("MAX_GROUP_MEMORY", 20)
                ),
                "max_private_memory": int(
                    os.environ.get("MAX_PRIVATE_MEMORY", 50)
                ),
                "session_timeout": int(
                    os.environ.get("SESSION_TIMEOUT", 10)
                ),
                "port": int(os.environ.get("PORT", 10000)),
                "render_url": os.environ.get(
                    "RENDER_EXTERNAL_URL", "not set"
                ),
                "model": "moonshotai/Kimi-K2-Instruct-0905:groq",
            },
            "timestamp": datetime.now(timezone.utc).isoformat()
        }), 200

    @app.route("/api/admin/logs")
    @require_admin
    def admin_logs():
        """Admin: View recent request logs."""
        count = request.args.get("count", 100, type=int)
        count = min(count, 500)
        recent = analytics.get_recent_requests(count)
        return jsonify({
            "logs": recent,
            "count": len(recent),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }), 200

    # ========================================================
    #           WEBHOOK ENDPOINT (Optional)
    # ========================================================

    @app.route("/webhook/<token>", methods=["POST"])
    def webhook_handler(token: str):
        """
        Telegram webhook endpoint (for webhook mode).
        Validates the token matches the bot token.
        """
        bot_token = os.environ.get("BOT_TOKEN", "")
        if not bot_token or token != bot_token:
            abort(403)

        # Get the update data
        update_data = request.get_json(silent=True)
        if not update_data:
            return jsonify({"error": "No data"}), 400

        # Process update (would need bot application reference)
        logger.info(
            f"[WEBHOOK] Received update: "
            f"{update_data.get('update_id', 'unknown')}"
        )

        # In webhook mode, the bot application would process this
        # For now, acknowledge receipt
        return jsonify({"ok": True}), 200

    # ========================================================
    #           UTILITY ROUTES
    # ========================================================

    @app.route("/robots.txt")
    def robots():
        """Robots.txt — Prevent search engine indexing."""
        return Response(
            "User-agent: *\nDisallow: /\n",
            mimetype="text/plain"
        )

    @app.route("/favicon.ico")
    def favicon():
        """Return empty favicon to prevent 404 logs."""
        return "", 204

    @app.route("/.well-known/health")
    def well_known_health():
        """Alternative health check path."""
        return jsonify({"status": "ok"}), 200

    @app.route("/heartbeat")
    def heartbeat():
        """Heartbeat endpoint — minimal response."""
        return jsonify({
            "beat": True,
            "time": time.time()
        }), 200

    @app.route("/info")
    def info():
        """Bot information endpoint."""
        return jsonify({
            "name": "Ruhi Ji",
            "description": (
                "Savage Queen Telegram Bot — Respect se Bezzati 😏👑"
            ),
            "version": WEB_VERSION,
            "owner": "@RUHI_VIG_QNR",
            "platform": "Telegram",
            "model": "Kimi-K2-Instruct (Moonshot AI via HuggingFace)",
            "language": "Hinglish (Hindi + English + Gen-Z slang)",
            "features": {
                "dual_personality": True,
                "owner_mode": "Innocent & Caring 🥺",
                "user_mode": "Savage Queen 👑",
                "memory": {
                    "group": "20 messages sliding window",
                    "private": "50 messages sliding window"
                },
                "wake_phrase": "Ruhi Ji",
                "session_duration": "10 minutes",
                "bad_word_filter": True,
                "broadcast_system": True,
            },
            "links": {
                "owner": "https://t.me/RUHI_VIG_QNR",
                "health": "/health",
                "stats": "/stats",
                "dashboard": "/",
            },
            "timestamp": datetime.now(timezone.utc).isoformat()
        }), 200

    # ========================================================
    #           CORS OPTIONS HANDLER
    # ========================================================

    @app.route("/<path:path>", methods=["OPTIONS"])
    def options_handler(path):
        """Handle CORS preflight requests."""
        response = make_response()
        origin = request.headers.get("Origin", "*")
        cors_headers = security.get_cors_headers(origin)
        for header, value in cors_headers.items():
            response.headers[header] = value
        response.status_code = 204
        return response

    # ========================================================
    #              ERROR HANDLERS
    # ========================================================

    @app.errorhandler(400)
    def bad_request(error):
        """Handle 400 Bad Request."""
        if request.accept_mimetypes.accept_json:
            return jsonify({
                "error": "Bad Request",
                "status": 400,
                "message": "Kya bhej raha hai tu beta? 😤",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }), 400

        return render_template_string(
            ERROR_PAGE_HTML,
            error_code=400,
            emoji="😤",
            message="Bad Request — Kya bhej raha hai tu beta?"
        ), 400

    @app.errorhandler(401)
    def unauthorized(error):
        """Handle 401 Unauthorized."""
        if request.accept_mimetypes.accept_json:
            return jsonify({
                "error": "Unauthorized",
                "status": 401,
                "message": "Permission nahi hai tere paas 💅",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }), 401

        return render_template_string(
            ERROR_PAGE_HTML,
            error_code=401,
            emoji="🔒",
            message="Unauthorized — Permission nahi hai tere paas 💅"
        ), 401

    @app.errorhandler(403)
    def forbidden(error):
        """Handle 403 Forbidden."""
        if request.accept_mimetypes.accept_json:
            return jsonify({
                "error": "Forbidden",
                "status": 403,
                "message": "Aukat mein reh beta 😏💅",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }), 403

        return render_template_string(
            ERROR_PAGE_HTML,
            error_code=403,
            emoji="🚫",
            message="Forbidden — Aukat mein reh beta 😏💅"
        ), 403

    @app.errorhandler(404)
    def not_found(error):
        """Handle 404 Not Found."""
        if request.accept_mimetypes.accept_json:
            return jsonify({
                "error": "Not Found",
                "status": 404,
                "message": "Yeh page exist nahi karta chomu 😏",
                "path": request.path,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }), 404

        return render_template_string(
            ERROR_PAGE_HTML,
            error_code=404,
            emoji="🔍",
            message="Page Not Found — Yeh exist nahi karta chomu 😏"
        ), 404

    @app.errorhandler(405)
    def method_not_allowed(error):
        """Handle 405 Method Not Allowed."""
        return jsonify({
            "error": "Method Not Allowed",
            "status": 405,
            "message": "Yeh method allowed nahi hai beta 😤",
            "allowed": error.valid_methods if hasattr(
                error, "valid_methods"
            ) else [],
            "timestamp": datetime.now(timezone.utc).isoformat()
        }), 405

    @app.errorhandler(413)
    def payload_too_large(error):
        """Handle 413 Payload Too Large."""
        return jsonify({
            "error": "Payload Too Large",
            "status": 413,
            "message": "Itna bada data mat bhej! 😤",
            "max_size": f"{MAX_REQUEST_SIZE / 1024 / 1024:.1f}MB",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }), 413

    @app.errorhandler(429)
    def too_many_requests(error):
        """Handle 429 Too Many Requests."""
        return jsonify({
            "error": "Too Many Requests",
            "status": 429,
            "message": "Itna fast mat kar beta, thoda ruk 😤💅",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }), 429

    @app.errorhandler(500)
    def internal_error(error):
        """Handle 500 Internal Server Error."""
        logger.error(f"[WEB] 500 Error: {error}")

        if request.accept_mimetypes.accept_json:
            return jsonify({
                "error": "Internal Server Error",
                "status": 500,
                "message": "Oops! Kuch toot gaya 😭 Try again later",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }), 500

        return render_template_string(
            ERROR_PAGE_HTML,
            error_code=500,
            emoji="💀",
            message="Internal Server Error — Kuch toot gaya 😭"
        ), 500

    @app.errorhandler(502)
    def bad_gateway(error):
        """Handle 502 Bad Gateway."""
        return jsonify({
            "error": "Bad Gateway",
            "status": 502,
            "message": "Server thoda confused hai 🤔",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }), 502

    @app.errorhandler(503)
    def service_unavailable(error):
        """Handle 503 Service Unavailable."""
        return jsonify({
            "error": "Service Unavailable",
            "status": 503,
            "message": "Abhi rest le rahi hoon, baad mein aana 😴",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }), 503

    @app.errorhandler(Exception)
    def handle_exception(error):
        """Catch-all error handler for unhandled exceptions."""
        logger.error(
            f"[WEB] Unhandled exception: {error}\n"
            f"{traceback.format_exc()}"
        )

        return jsonify({
            "error": "Internal Server Error",
            "status": 500,
            "message": "Unexpected error occurred 😭",
            "type": type(error).__name__,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }), 500

    # ========================================================
    #        START SELF-PING SYSTEM
    # ========================================================

    # Start the self-ping background thread
    if render_url:
        self_ping.start()
        logger.info("[WEB] Self-ping system started ✓")

    # Schedule periodic cleanup of rate limiter
    def _periodic_cleanup():
        """Background thread for periodic cleanup tasks."""
        while True:
            try:
                time.sleep(300)  # Every 5 minutes
                rate_limiter.cleanup()
                logger.debug("[WEB] Periodic cleanup completed")
            except Exception as e:
                logger.debug(f"[WEB] Cleanup error: {e}")

    cleanup_thread = threading.Thread(
        target=_periodic_cleanup,
        daemon=True,
        name="WebCleanup"
    )
    cleanup_thread.start()

    # ========================================================
    #        FINAL LOGGING
    # ========================================================

    logger.info("[WEB] Flask application created successfully ✓")
    logger.info(f"[WEB] Version: {WEB_VERSION}")
    logger.info(f"[WEB] Rate Limit: {RATE_LIMIT_MAX_REQUESTS}/{RATE_LIMIT_WINDOW}s")
    logger.info(f"[WEB] Self-Ping: {'enabled' if render_url else 'disabled'}")
    logger.info(f"[WEB] Admin Token: {security.admin_token[:8]}...")
    logger.info("[WEB] Endpoints registered:")
    logger.info("[WEB]   / (Dashboard HTML)")
    logger.info("[WEB]   /health (Health Check)")
    logger.info("[WEB]   /ping (Ping-Pong)")
    logger.info("[WEB]   /stats (Full Stats)")
    logger.info("[WEB]   /status (Status Page HTML)")
    logger.info("[WEB]   /api/metrics (System Metrics)")
    logger.info("[WEB]   /api/analytics (Request Analytics)")
    logger.info("[WEB]   /api/self-ping (Self-Ping Stats)")
    logger.info("[WEB]   /api/rate-limit (Rate Limit Info)")
    logger.info("[WEB]   /api/version (Version Info)")
    logger.info("[WEB]   /api/uptime (Uptime Details)")
    logger.info("[WEB]   /info (Bot Info)")
    logger.info("[WEB]   /heartbeat (Heartbeat)")
    logger.info("[WEB]   /robots.txt (Search Engine Block)")
    logger.info("[WEB]   /api/admin/* (Admin Endpoints)")

    return app


# ============================================================
#        STANDALONE WEB SERVER RUNNER
# ============================================================

class WebServerRunner:
    """
    Manages the Flask web server lifecycle.
    Can run standalone or as part of the main bot process.
    """

    def __init__(
        self,
        db_manager=None,
        start_time=None,
        ai_client=None,
        bot_instance=None
    ):
        self.db_manager = db_manager
        self.start_time = start_time or datetime.now(timezone.utc)
        self.ai_client = ai_client
        self.bot_instance = bot_instance
        self.app = None
        self._thread: Optional[threading.Thread] = None
        self._running = False

    def create_app(self) -> Flask:
        """Create the Flask application."""
        self.app = create_flask_app(
            db_manager=self.db_manager,
            start_time=self.start_time,
            ai_client=self.ai_client,
            bot_instance=self.bot_instance
        )
        return self.app

    def run_threaded(self, host: str = "0.0.0.0", port: int = None):
        """Run the web server in a background thread."""
        if self.app is None:
            self.create_app()

        if port is None:
            port = int(os.environ.get("PORT", 10000))

        self._running = True

        def _run():
            try:
                logger.info(
                    f"[WEB_RUNNER] Starting Flask on {host}:{port}"
                )
                self.app.run(
                    host=host,
                    port=port,
                    debug=False,
                    use_reloader=False,
                    threaded=True
                )
            except Exception as e:
                logger.error(f"[WEB_RUNNER] Flask server error: {e}")
                self._running = False

        self._thread = threading.Thread(
            target=_run,
            daemon=True,
            name="FlaskWebServer"
        )
        self._thread.start()

        logger.info(
            f"[WEB_RUNNER] Flask server started in background "
            f"on {host}:{port} ✓"
        )

    def run_blocking(self, host: str = "0.0.0.0", port: int = None):
        """Run the web server in blocking mode (main thread)."""
        if self.app is None:
            self.create_app()

        if port is None:
            port = int(os.environ.get("PORT", 10000))

        logger.info(
            f"[WEB_RUNNER] Starting Flask (blocking) on {host}:{port}"
        )
        self.app.run(
            host=host,
            port=port,
            debug=False,
            use_reloader=False,
            threaded=True
        )

    def is_running(self) -> bool:
        """Check if the web server is running."""
        if self._thread:
            return self._thread.is_alive()
        return self._running

    def get_app(self) -> Optional[Flask]:
        """Get the Flask app instance."""
        return self.app


# ============================================================
#        GUNICORN ENTRY POINT
# ============================================================

def create_gunicorn_app():
    """
    Factory function for Gunicorn deployment.

    Usage in Procfile:
        web: gunicorn web_server:create_gunicorn_app() --bind 0.0.0.0:$PORT

    Or use the 'app' variable directly:
        web: gunicorn web_server:app --bind 0.0.0.0:$PORT
    """
    logger.info("[GUNICORN] Creating app for Gunicorn...")

    # Try to import database manager
    db = None
    try:
        from database import DatabaseManager
        from config import DATABASE_URL
        db = DatabaseManager(DATABASE_URL)
        db.initialize()
        logger.info("[GUNICORN] Database initialized ✓")
    except Exception as e:
        logger.warning(f"[GUNICORN] DB init failed: {e}")

        # Try embedded version
        try:
            db_url = os.environ.get("DATABASE_URL", "")
            if db_url:
                import psycopg2.pool
                # Minimal DB manager for web-only mode
                logger.info("[GUNICORN] Using minimal DB connection")
        except Exception:
            pass

    flask_app = create_flask_app(
        db_manager=db,
        start_time=datetime.now(timezone.utc)
    )

    return flask_app


# ============================================================
#            STANDALONE EXECUTION
# ============================================================

def main():
    """
    Run the web server standalone (for testing or
    separate web service deployment).
    """
    print("""
    ╔══════════════════════════════════════════════╗
    ║   🌐 Ruhi Ji Web Server — Standalone Mode   ║
    ║        Made with 💖 by @RUHI_VIG_QNR        ║
    ╚══════════════════════════════════════════════╝
    """)

    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    port = int(os.environ.get("PORT", 10000))
    host = os.environ.get("HOST", "0.0.0.0")

    # Try to connect to database
    db = None
    db_url = os.environ.get("DATABASE_URL", "")
    if db_url:
        try:
            # Use embedded DB manager
            import psycopg2.pool
            logger.info("[STANDALONE] Attempting DB connection...")

            # Minimal connection test
            import psycopg2
            conn = psycopg2.connect(db_url, connect_timeout=10)
            conn.close()
            logger.info("[STANDALONE] Database connection verified ✓")
        except Exception as e:
            logger.warning(f"[STANDALONE] DB connection failed: {e}")

    # Create and run app
    app = create_flask_app(
        db_manager=db,
        start_time=datetime.now(timezone.utc)
    )

    logger.info(f"[STANDALONE] Starting on {host}:{port}")
    logger.info(f"[STANDALONE] Dashboard: http://localhost:{port}/")
    logger.info(f"[STANDALONE] Health: http://localhost:{port}/health")

    app.run(
        host=host,
        port=port,
        debug=os.environ.get("FLASK_DEBUG", "false").lower() == "true",
        use_reloader=False,
        threaded=True
    )


# Module-level app for Gunicorn
# Usage: gunicorn web_server:app --bind 0.0.0.0:$PORT
try:
    app = create_gunicorn_app()
except Exception as e:
    logger.warning(f"[MODULE] Could not create module-level app: {e}")
    app = None


if __name__ == "__main__":
    main()
    