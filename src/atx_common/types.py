from enum import Enum
from typing import Protocol, runtime_checkable

from latch.types import LatchDir


class Genome(Enum):
    """Supported reference genomes."""
    hg38 = "hg38"
    mm10 = "mm10"
    mm39 = "mm39"
    rnor6 = "rnor6"


@runtime_checkable
class HasSpatialDir(Protocol):
    """Any Run-like object with a spatial_dir attribute."""
    spatial_dir: LatchDir


@runtime_checkable
class HasRunInfo(Protocol):
    """Any Run-like object with run_id and condition attributes."""
    run_id: str
    condition: str
