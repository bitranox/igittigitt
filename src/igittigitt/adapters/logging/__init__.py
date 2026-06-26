"""Logging adapter - lib_log_rich setup.

Provides centralized logging initialization for all entry points.

Contents:
    * :func:`.setup.init_logging` - Idempotent logging initialization
"""

from __future__ import annotations

from .setup import init_logging

__all__ = ["init_logging"]
