"""Shared logging setup for SolArk modules."""
from __future__ import annotations

import logging


def get_logger(name: str) -> logging.Logger:
    """Return a standard logger (respects Home Assistant logging config)."""
    return logging.getLogger(name)
