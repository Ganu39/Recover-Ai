"""Deterministic in-memory safety rate limiter (Phase 6)."""

import threading
import time
from typing import Dict, List, Optional, Tuple
import uuid


class InMemoryRateLimiter:
    """Thread-safe, sliding-window rate limiter for safety gateway evaluation.
    
    Prevents repeated automated authorization loops against the same target or customer.
    """

    def __init__(self, max_per_window: int = 3, window_seconds: int = 3600):
        self._lock = threading.Lock()
        self.max_per_window = max_per_window
        self.window_seconds = window_seconds
        # Target lookup: (target_type, target_id_str) -> List of epoch timestamps
        self._target_timestamps: Dict[Tuple[str, str], List[float]] = {}
        # Customer lookup: customer_id_str -> List of epoch timestamps
        self._customer_timestamps: Dict[str, List[float]] = {}

    def is_rate_limited(
        self,
        target_type: str,
        target_id: uuid.UUID,
        customer_id: Optional[uuid.UUID] = None,
        now_epoch: Optional[float] = None,
    ) -> bool:
        """Check if target or customer has exceeded the sliding-window threshold."""
        if now_epoch is None:
            now_epoch = time.time()

        cutoff = now_epoch - self.window_seconds

        with self._lock:
            target_key = (target_type, str(target_id))
            target_history = [t for t in self._target_timestamps.get(target_key, []) if t >= cutoff]
            self._target_timestamps[target_key] = target_history
            if len(target_history) >= self.max_per_window:
                return True

            if customer_id is not None:
                cust_key = str(customer_id)
                cust_history = [t for t in self._customer_timestamps.get(cust_key, []) if t >= cutoff]
                self._customer_timestamps[cust_key] = cust_history
                # Customer limit allows 3x target limit within window across different targets
                if len(cust_history) >= (self.max_per_window * 3):
                    return True

            return False

    def record_attempt(
        self,
        target_type: str,
        target_id: uuid.UUID,
        customer_id: Optional[uuid.UUID] = None,
        now_epoch: Optional[float] = None,
    ) -> None:
        """Record an authorization attempt in the sliding window."""
        if now_epoch is None:
            now_epoch = time.time()

        with self._lock:
            target_key = (target_type, str(target_id))
            self._target_timestamps.setdefault(target_key, []).append(now_epoch)
            if customer_id is not None:
                cust_key = str(customer_id)
                self._customer_timestamps.setdefault(cust_key, []).append(now_epoch)

    def clear(self) -> None:
        """Reset rate limiter state (for test isolation)."""
        with self._lock:
            self._target_timestamps.clear()
            self._customer_timestamps.clear()
