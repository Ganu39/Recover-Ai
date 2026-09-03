"""Deterministic fail-safe kill switch for the Safety Gateway (Phase 6)."""

import threading
from typing import Optional
from agents.gateway.schemas import GatewayConfig


class GatewayKillSwitch:
    """Thread-safe, fail-closed kill switch mechanism.
    
    If configuration cannot be trusted, is uninitialized, or is corrupted,
    the kill switch fails closed (returns active=True) to prevent unsafe execution.
    """

    def __init__(self, initial_state: bool = False):
        self._lock = threading.Lock()
        self._is_active = initial_state
        self._is_corrupted = False

    def activate(self) -> None:
        """Explicitly activate the kill switch."""
        with self._lock:
            self._is_active = True

    def deactivate(self) -> None:
        """Explicitly deactivate the kill switch (only if not corrupted)."""
        with self._lock:
            if not self._is_corrupted:
                self._is_active = False

    def set_corrupted(self) -> None:
        """Mark kill switch configuration as corrupted (fails closed)."""
        with self._lock:
            self._is_corrupted = True
            self._is_active = True

    def is_active(self) -> bool:
        """Check if kill switch is currently active or failed-closed."""
        with self._lock:
            if self._is_corrupted:
                return True
            return self._is_active

    @classmethod
    def from_config(cls, config: Optional[GatewayConfig]) -> "GatewayKillSwitch":
        """Construct kill switch from config, failing closed if config is invalid or None."""
        if config is None:
            ks = cls(initial_state=True)
            ks.set_corrupted()
            return ks
        try:
            return cls(initial_state=bool(config.kill_switch_active))
        except Exception:
            ks = cls(initial_state=True)
            ks.set_corrupted()
            return ks
