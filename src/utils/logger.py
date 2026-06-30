"""
Structured pipeline logger.

Controlled entirely by the PIPELINE_DEBUG environment variable.
Set PIPELINE_DEBUG=1 to enable full structured logging.
In normal execution this module is a no-op — no output is produced.
"""
import os
import json
import logging
import sys
from datetime import datetime
from typing import Any, Dict

_DEBUG = os.environ.get("PIPELINE_DEBUG", "0").strip() == "1"

# Build a private logger that only emits when debug is enabled.
_logger = logging.getLogger("pipeline")
_logger.setLevel(logging.DEBUG if _DEBUG else logging.CRITICAL)

if _DEBUG and not _logger.handlers:
    _handler = logging.StreamHandler(sys.stderr)
    _handler.setFormatter(
        logging.Formatter(
            fmt="%(asctime)s [PIPELINE] %(levelname)s %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S"
        )
    )
    _logger.addHandler(_handler)


def _serialise(obj: Any) -> str:
    """Best-effort JSON serialisation for log payloads."""
    try:
        if hasattr(obj, "model_dump"):
            return json.dumps(obj.model_dump(), default=str, indent=2)
        return json.dumps(obj, default=str, indent=2)
    except Exception:
        return str(obj)


def log_stage(stage: str, payload: Any) -> None:
    """Log a pipeline stage payload when PIPELINE_DEBUG=1."""
    if not _DEBUG:
        return
    _logger.debug("[%s]\n%s", stage, _serialise(payload))


def log_event(stage: str, message: str, extra: Dict[str, Any] | None = None) -> None:
    """Log a short pipeline event message when PIPELINE_DEBUG=1."""
    if not _DEBUG:
        return
    suffix = f" | {extra}" if extra else ""
    _logger.info("[%s] %s%s", stage, message, suffix)


def log_error(stage: str, error: Exception) -> None:
    """Log a pipeline error when PIPELINE_DEBUG=1."""
    if not _DEBUG:
        return
    _logger.error("[%s] ERROR: %s", stage, str(error), exc_info=True)
