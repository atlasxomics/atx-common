import fnmatch
import glob
import logging
import os
import re
import subprocess
from pathlib import Path
from typing import Dict, List, Optional

from atx_common.types import HasRunInfo


logging.basicConfig(
    format="%(levelname)s - %(asctime)s - %(message)s", level=logging.INFO
)


# ---------------------------------------------------------------------------
# Condition / grouping helpers
# ---------------------------------------------------------------------------
def sanitize_condition(condition: Optional[str]) -> str:
    """Normalize condition labels: strip whitespace, collapse spaces to ``_``,
    treat empty / None as ``"None"``."""
    if condition is None:
        return "None"

    condition_str = str(condition).strip()
    if condition_str == "":
        return "None"

    return re.sub(r"\s+", "_", condition_str)


def get_groups(runs: List[HasRunInfo]) -> List[str]:
    """Determine grouping columns for differential analysis.

    Always includes ``"cluster"``; adds ``"sample"`` when there are multiple
    runs, and ``"condition"`` when there are multiple distinct conditions.
    """
    samples = [run.run_id for run in runs]
    conditions = list({sanitize_condition(run.condition) for run in runs})

    groups = ["cluster"]
    if len(samples) > 1:
        groups.append("sample")
    if len(conditions) > 1:
        groups.append("condition")

    return groups


# ---------------------------------------------------------------------------
# AnnData helpers (require `anndata` — install with `pip install atx-common[analysis]`)
# ---------------------------------------------------------------------------
def filter_anndata(adata: "anndata.AnnData", group: str, subgroup: str) -> "anndata.AnnData":
    """Subset *adata* to rows where ``obs[group] == subgroup``."""
    return adata[adata.obs[group] == subgroup]


def rename_obs_columns(adata: "anndata.AnnData") -> "anndata.AnnData":
    """Rename common ArchR-style obs columns to lowercase equivalents."""
    rename_map = {
        "Clusters": "cluster",
        "Condition": "condition",
        "Sample": "sample",
        "nFrags": "n_fragment",
    }

    for old_name, new_name in rename_map.items():
        if old_name in adata.obs.columns:
            adata.obs.rename(columns={old_name: new_name}, inplace=True)

    return adata


# ---------------------------------------------------------------------------
# Output directory helpers
# ---------------------------------------------------------------------------
def create_output_directories(project_name: str) -> Dict[str, Path]:
    """Create ``<project>/figures/`` and ``<project>/tables/`` under ``/root``."""
    base_dir = Path(f"/root/{project_name}")
    figures_dir = base_dir / "figures"
    tables_dir = base_dir / "tables"

    for directory in [base_dir, figures_dir, tables_dir]:
        directory.mkdir(parents=True, exist_ok=True)

    return {
        "base": base_dir,
        "figures": figures_dir,
        "tables": tables_dir,
    }


def move_files_to_directory(patterns: List[str], target_dir: Path) -> None:
    """Move files matching *patterns* (globs) into *target_dir*."""
    files_to_move = []
    for pattern in patterns:
        files_to_move.extend(glob.glob(pattern))

    if files_to_move:
        subprocess.run(["mv"] + files_to_move + [str(target_dir)], check=True)


def organize_outputs(
    project_name: str,
    dirs: Dict[str, Path],
    exclude_pattern: Optional[str] = None,
) -> None:
    """Move generated outputs into the standard directory structure."""
    logging.info("Moving outputs to output directory...")

    # Move main project files
    project_patterns = [f"{project_name}_*", "*.rds", "*.h5ad"]
    move_files_to_directory(project_patterns, dirs["base"])

    # Move tables
    csv_files = glob.glob("*.csv")
    if exclude_pattern:
        csv_files = [
            f for f in csv_files if not fnmatch.fnmatch(f, exclude_pattern)
        ]
    if csv_files:
        subprocess.run(["mv"] + csv_files + [str(dirs["tables"])], check=True)

    # Move figures (excluding Rplots.pdf)
    figures = [fig for fig in glob.glob("*.pdf") if fig != "Rplots.pdf"]
    if figures:
        subprocess.run(["mv"] + figures + [str(dirs["figures"])], check=True)


def copy_peak_files(project_name: str, dirs: Dict[str, Path]) -> None:
    """Copy ArchR peak-call CSVs and PDFs into the output dirs."""
    table_dir = f"/root/{project_name}/{project_name}_ArchRProject/PeakCalls/"
    plot_dir = f"/root/{project_name}/{project_name}_ArchRProject/Plots/"

    if os.path.exists(table_dir):
        peak_csvs = glob.glob(f"{table_dir}/*.csv")
        if not peak_csvs:
            logging.warning("No peak CSV files found in %s", table_dir)
        else:
            subprocess.run(["cp"] + peak_csvs + [str(dirs["tables"])], check=True)
    else:
        logging.warning("No %s found", table_dir)

    if os.path.exists(plot_dir):
        peak_pdfs = glob.glob(f"{plot_dir}/*.pdf")
        if not peak_pdfs:
            logging.warning("No peak PDF files found in %s", plot_dir)
        else:
            subprocess.run(["cp"] + peak_pdfs + [str(dirs["figures"])], check=True)
    else:
        logging.warning("No %s found", plot_dir)
