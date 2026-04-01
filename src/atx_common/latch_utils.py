import json
import logging
import time
from pathlib import Path
from typing import Optional

from latch.functions.messages import message
from latch.types import LatchDir, LatchFile

from atx_common.types import HasSpatialDir


logging.basicConfig(
    format="%(levelname)s - %(asctime)s - %(message)s", level=logging.INFO
)


# ---------------------------------------------------------------------------
# Logging helper (user-facing + developer log)
# ---------------------------------------------------------------------------
def log(msg: str, title: str, type: str = "info") -> None:
    """Log *msg* via Python logging and send a Latch UI message."""
    getattr(logging, type)(msg)
    message(typ=type, data={"title": title, "body": msg})


# ---------------------------------------------------------------------------
# Channel detection from spatial metadata
# ---------------------------------------------------------------------------
def get_channels(run: HasSpatialDir, default: int = 50) -> int:
    """Read ``numChannels`` from a run's ``spatial_dir/metadata.json``.

    Falls back to *default* when the key is missing, not an integer, or the
    metadata file doesn't exist.
    """
    spatial_dir = run.spatial_dir.local_path
    metadata_json = f"{spatial_dir}/metadata.json"

    try:
        with open(metadata_json, "r") as f:
            metadata = json.load(f)
            channels = metadata["numChannels"]
    except FileNotFoundError:
        logging.warning(
            "metadata.json not found in %s; defaulting to %d channels.",
            spatial_dir,
            default,
        )
        return default
    except KeyError:
        logging.warning(
            "Key 'numChannels' not found in %s; defaulting to %d channels.",
            metadata_json,
            default,
        )
        return default

    try:
        return int(channels)
    except (ValueError, TypeError):
        logging.warning(
            "Value '%s' in %s is not an integer; defaulting to %d channels.",
            channels,
            metadata_json,
            default,
        )
        return default


# ---------------------------------------------------------------------------
# Retry-aware file lookup in a LatchDir
# ---------------------------------------------------------------------------
_TRANSIENT_MARKERS = [
    "remote end closed connection",
    "connection aborted",
    "connection reset",
    "timed out",
    "timeout",
    "temporarily unavailable",
    "service unavailable",
    "too many requests",
]


def _is_transient(err: Exception) -> bool:
    cur: Optional[BaseException] = err
    while cur is not None:
        msg = f"{type(cur).__name__}: {cur}".lower()
        if any(marker in msg for marker in _TRANSIENT_MARKERS):
            return True
        cur = cur.__cause__ or cur.__context__
    return False


def get_LatchFile(
    directory: LatchDir,
    file_name: str,
    retries: int = 3,
    retry_delay_s: float = 5.0,
) -> Optional[LatchFile]:
    """Find a single file by name inside *directory*, with transient-error retries.

    Returns ``None`` (with an error log) when the file is missing, duplicated,
    or lookup fails after all retries.
    """
    for attempt in range(1, retries + 1):
        try:
            files = [
                file for file in directory.iterdir()
                if isinstance(file, LatchFile)
                and Path(file.path).name == file_name
            ]
        except Exception as e:
            if not _is_transient(e):
                logging.error(
                    "Failed to list '%s' in '%s' (non-retryable): %s",
                    file_name, directory.remote_path, e,
                )
                return None

            if attempt == retries:
                logging.error(
                    "Failed to list '%s' in '%s' after %d transient attempt(s): %s",
                    file_name, directory.remote_path, retries, e,
                )
                return None

            logging.warning(
                "Attempt %d/%d failed to find file '%s' in '%s': %s. "
                "Retrying in %.1f seconds.",
                attempt, retries, file_name, directory.remote_path,
                e, retry_delay_s,
            )
            time.sleep(retry_delay_s)
            continue

        if len(files) == 1:
            return files[0]
        if len(files) == 0:
            logging.error(
                "No file '%s' found in '%s'.",
                file_name, directory.remote_path,
            )
            return None

        logging.error(
            "Multiple files named '%s' found in '%s'.",
            file_name, directory.remote_path,
        )
        return None

    return None
