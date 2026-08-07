"""
Assignment 11 — Rate Limiter (TODO 8).

Sliding-window, per-user rate limiting. Blocks flooding / cost attacks
that other guardrail layers do not address.

Implemented as an ADK BasePlugin using before_agent_callback to intercept
requests before they reach the LLM.
"""
from __future__ import annotations

from collections import defaultdict, deque
import time

from google.adk.plugins import base_plugin
from google.genai import types


class RateLimitPlugin(base_plugin.BasePlugin):
    """Block users who exceed max_requests within window_seconds.

    Algorithm: Sliding Window — keeps a deque of request timestamps per user.
    Old timestamps outside the window are evicted before checking the count.
    This prevents burst abuse while allowing steady usage up to the limit.
    """

    def __init__(self, max_requests: int = 10, window_seconds: int = 60):
        super().__init__(name="rate_limiter")
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        # Per-user sliding window of request timestamps
        self.user_windows: dict[str, deque] = defaultdict(deque)
        self.blocked_count = 0
        self.total_count = 0

    def _block_response(self, message: str) -> types.Content:
        """Build a blocked Content response."""
        return types.Content(
            role="model",
            parts=[types.Part.from_text(text=message)],
        )

    async def before_agent_callback(self, *, agent, callback_context):
        """
        TODO 8 — Sliding-window rate limit check.

        Returns:
            types.Content if rate limit is exceeded (blocks the request),
            or None to allow the request through.
        """
        self.total_count += 1
        ic = callback_context.get_invocation_context()
        user_id = getattr(ic, "user_id", None) or "anonymous"
        now = time.time()
        window = self.user_windows[user_id]

        # Evict timestamps outside the sliding window
        while window and window[0] < now - self.window_seconds:
            window.popleft()

        if len(window) >= self.max_requests:
            wait = self.window_seconds - (now - window[0])
            self.blocked_count += 1
            return self._block_response(
                f"Rate limit exceeded. Try again in {wait:.0f}s."
            )
        else:
            window.append(now)
            return None

    def stats(self) -> dict:
        """Return current rate limiter statistics."""
        return {
            "total_requests": self.total_count,
            "blocked_requests": self.blocked_count,
            "block_rate": self.blocked_count / self.total_count if self.total_count else 0.0,
        }
