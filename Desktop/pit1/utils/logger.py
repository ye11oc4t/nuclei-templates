"""utils/logger.py — centralized logger."""
import logging
import os

_level = logging.DEBUG if os.environ.get("PIT1_DEBUG") else logging.INFO
logging.basicConfig(
    level=_level,
    format="[pit1] %(levelname)s %(message)s",
    handlers=[logging.StreamHandler()],
)
log = logging.getLogger("pit1")