# atx-common

Shared utilities for AtlasXomics Latch workflows.

## Installation

In a workflow Dockerfile:

```dockerfile
# pin to a release tag so workflows stay stable
run pip install git+https://github.com/atlasxomics/atx-common.git@v0.1.0
```

For local development:

```bash
pip install -e /path/to/atx-common
# or with anndata helpers:
pip install -e "/path/to/atx-common[analysis]"
```

## What's included

### `atx_common.types`
- `Genome` enum (hg38, mm10, mm39, rnor6)
- `HasSpatialDir` / `HasRunInfo` protocols — let your workflow define its own `Run` dataclass while still using shared functions

### `atx_common.reference`
- Chromosome sizes: `mm10_chrsizes`, `hg38_chrsizes`, `rnor6_chrsizes`, `chrsizes` (unified dict)
- `ref_dict` — genome annotation GFF3 paths
- `pt_sizes` — DBiT channel-to-point-size mapping
- `gene_keys` — mitochondrial/ribosomal gene prefixes per genome
- `get_genome_fasta(genome)` — S3 FASTA paths
- `get_blacklist_path(genome)` — resolve blacklist BED files

### `atx_common.latch_utils`
- `log(msg, title, type)` — combined Python logging + Latch UI message
- `get_channels(run, default)` — read numChannels from spatial metadata
- `get_LatchFile(directory, file_name, retries, retry_delay_s)` — retry-aware file lookup

### `atx_common.analysis`
- `sanitize_condition(condition)` — normalize condition labels
- `get_groups(runs)` — determine grouping columns for differential analysis
- `filter_anndata(adata, group, subgroup)` — subset AnnData by obs column
- `rename_obs_columns(adata)` — standardize ArchR column names
- `create_output_directories(project_name)` — create figures/tables dirs
- `organize_outputs(project_name, dirs)` — move outputs into standard layout
- `copy_peak_files(project_name, dirs)` — copy ArchR peak call files
- `move_files_to_directory(patterns, target_dir)` — glob-and-move helper

## Usage example

```python
from dataclasses import dataclass
from latch.types import LatchFile, LatchDir

from atx_common import (
    Genome,
    get_channels,
    get_groups,
    get_LatchFile,
    log,
    pt_sizes,
    sanitize_condition,
)


@dataclass
class Run:
    run_id: str
    fragments_file: LatchFile
    spatial_dir: LatchDir
    condition: str = "None"


# All shared functions work with your custom Run because it satisfies
# the HasSpatialDir and HasRunInfo protocols.
channels = get_channels(run)
groups = get_groups(runs)
size = pt_sizes[channels]
```

## Versioning

Tag releases on GitHub (`v0.1.0`, `v0.2.0`, ...) and pin to them in Dockerfiles.
Bump the tag in a workflow's Dockerfile only when you want it to pick up changes.
