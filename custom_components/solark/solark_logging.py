"""Shared logging setup for SolArk modules."""
from __future__ import annotations

import logging
from pathlib import Path

LOG_FILE = Path(__file__).parent / "solark_debug.log"
_BASE_LOGGER_NAME = "custom_components.solark"


def get_logger(name: str) -> logging.Logger:
    """Return a logger with the SolArk file handler attached."""
    base_logger = logging.getLogger(_BASE_LOGGER_NAME)
    _ensure_file_handler(base_logger)
    return logging.getLogger(name)


def _ensure_file_handler(logger: logging.Logger) -> None:
    if any(
        isinstance(handler, logging.FileHandler)
        and getattr(handler, "_solark_file_handler", False)
        for handler in logger.handlers
    ):
        return

    try:
        file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
        file_handler._solark_file_handler = True  # type: ignore[attr-defined]
        file_handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter(
            "%(asctime)s %(levelname)s %(name)s: %(message)s"
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        logger.setLevel(logging.DEBUG)
        logger.debug("SolArk file logger initialized at %s", LOG_FILE)
    except Exception as exc:  # noqa: BLE001
        logger.error("Failed to initialize SolArk file logger: %s", exc)
