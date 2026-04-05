"""Core pipeline engine for GVSrun.

Generates the ``.inp`` input file consumed by the Schrodinger ``pipeline``
command and (optionally) submits the job.
"""

from __future__ import annotations

import glob
import os
from pathlib import Path

from ..utils import run_cmd
from .config import GVSRunConfig
from .inputs import (
    generate_database_block,
    generate_grid_block,
    generate_smarts_block,
)
from .modes import resolve_pipeline


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------


def parse_num_or_percentage(value: str) -> str:
    """Convert a keep-number spec to the .inp keyword format.

    * ``"5%"``   -> ``"PERCENT_TO_KEEP   5"``
    * ``"500"``  -> ``"NUM_TO_KEEP   500"``

    Mirrors the Bash ``parse_num_or_percentage`` function (lines 1195-1201).
    """
    value = value.strip()
    if value.endswith("%"):
        return f"PERCENT_TO_KEEP   {value.rstrip('%')}"
    return f"NUM_TO_KEEP   {value}"


def _resolve_database_location(config: GVSRunConfig) -> Path:
    """Resolve database path with $compound_library fallback.

    Matches Bash behavior (lines 408-420):
    - If --db-path is given, use it directly.
    - Otherwise, look for $compound_library/{database} or $compound_library/{database}*
    """
    if config.database_path:
        return config.database_path

    compound_library = os.environ.get("compound_library")
    if not compound_library:
        raise RuntimeError(
            "Database path not set. Use --db-path or set $compound_library "
            "and provide --database name."
        )

    # Look for exact match first, then prefix match
    lib_dir = Path(compound_library)
    exact = lib_dir / config.database
    if exact.exists():
        return exact

    # Match files/dirs starting with database name
    matches = sorted(lib_dir.glob(f"{config.database}*"))
    if not matches:
        raise RuntimeError(
            f"Database '{config.database}' not found in $compound_library={compound_library}"
        )
    return matches[0]


def _preprocess_shape_screen(config: GVSRunConfig, db_path: Path) -> Path:
    """Run Schrodinger shape_screen to align the database against reference.

    Matches Bash Shape() function (lines 3089-3097). Returns the aligned maegz path.
    """
    if not config.reference_ligand:
        raise RuntimeError(
            "Shape screening requires a reference ligand. Use -R/--reference."
        )

    schrodinger = config.require_schrodinger()
    keep_num, sample_method, max_confs = config.shape_screen_array

    output_name = f"{db_path.stem}_shape_aligned"
    cmd = [
        str(schrodinger / "shape_screen"),
        "-shape", str(config.reference_ligand),
        "-screen", str(db_path),
        "-max", str(keep_num),
        "-flex", "-sample", sample_method,
        "-max_confs", str(max_confs),
        "-JOBNAME", output_name,
        "-WAIT", "-NOJOBID",
    ]
    run_cmd(cmd)
    return Path(f"{output_name}_align.maegz").resolve()


# ------------------------------------------------------------------
# .inp generation
# ------------------------------------------------------------------


def generate_inp(config: GVSRunConfig, grid_path: str, title: str) -> Path:
    """Generate a complete ``.inp`` file for the virtual screening pipeline.

    Parameters
    ----------
    config:
        Fully-populated :class:`GVSRunConfig`.
    grid_path:
        Path to the grid ``.zip`` file (or ``"None"`` when no grid is used).
    title:
        Job title used for the .inp filename and header.

    Returns
    -------
    Path
        Path to the written ``.inp`` file.
    """
    # Import the registry here to avoid circular imports; the stages
    # sub-package depends on *config* and *pipeline* helpers.
    from .stages import TASK_REGISTRY, dispatch  # noqa: WPS433

    pipeline_tasks = config.pipeline.split("+")

    # Reset chaining state for each .inp
    config.ligand_name = "INPUT_Ligands"
    config.to_rmsd = "INPUT_Ligands"

    lines: list[str] = [
        "########## Virtual Screening Workflow Input File ###############",
        f"### to restart: $SCHRODINGER/pipeline -RESTART {title}.inp",
        "######################################################################",
        "    ",
    ]

    # Grid input
    if grid_path != "None":
        lines.append(generate_grid_block(grid_path))

    # Database input
    lines.append(generate_database_block(config))

    # Optional SMARTs filter
    if config.smarts:
        block, config.ligand_name = generate_smarts_block(
            config.smarts, config.ligand_name
        )
        lines.append(block)

    # Pipeline stages
    for task_name in pipeline_tasks:
        if task_name not in TASK_REGISTRY:
            raise ValueError(f"Unknown pipeline task: {task_name}")

        block, config.ligand_name = dispatch(
            task_name, config, config.ligand_name
        )
        lines.append(block)
        print(f"NOTE: Set up {task_name} Task!")

    inp_path = Path(f"{title}.inp")
    inp_path.write_text("\n".join(lines))
    return inp_path


# ------------------------------------------------------------------
# Pipeline execution
# ------------------------------------------------------------------


def _submit_pipeline(config: GVSRunConfig, inp_path: Path, job_title: str) -> None:
    """Submit a .inp file to the Schrodinger pipeline."""
    schrodinger = config.require_schrodinger()
    host = config.host
    njobs = config.njobs

    host_flags = [
        "-host_glide", f"{host}:{config.glide_njobs}",
        "-host_ligprep", f"{host}:{config.ligprep_njobs}",
        "-host_phase", f"{host}:{config.phase_njobs}",
        "-host_prime", f"{host}:{config.prime_njobs}",
        "-host_mmod", f"{host}:{config.macromodel_njobs}",
        "-host_qsite", f"{host}:{config.qsite_njobs}",
        "-host_qikprop", f"{host}:{config.qikprop_njobs}",
    ]

    if host == "localhost":
        cmd = [
            str(schrodinger / "run"),
            "pipeline_startup.py",
            str(inp_path.name),
            "-OVERWRITE",
            "-NJOBS", str(njobs),
            "-HOST", f"{host}:{njobs}",
            "-JOBNAME", job_title,
            *host_flags,
            "-TMPLAUNCHDIR",
            "-WAIT",
        ]
    else:
        cmd = [
            str(schrodinger / "pipeline"),
            "-OVERWRITE",
            "-TMPLAUNCHDIR",
            "-adjust",
            "-NJOBS", str(njobs),
            "-HOST", f"{host}:{njobs}",
            "-JOBNAME", job_title,
            *host_flags,
            str(inp_path.name),
        ]

    # Run from within the work directory
    run_cmd(cmd)


def run_pipeline(config: GVSRunConfig) -> None:
    """Run the full GVSrun virtual screening pipeline.

    1. Resolve the running mode to a pipeline string.
    2. Resolve the database path (with $compound_library fallback).
    3. Optionally run shape screening preprocessing.
    4. Iterate over grid files and generate + submit .inp jobs.
    """
    config.require_schrodinger()

    # Resolve mode -> pipeline string
    config.pipeline = resolve_pipeline(config.running_mode)

    # Resolve database path
    config.database_path = _resolve_database_location(config)

    # Shape screening preprocessing
    if config.shape_screen_switch:
        aligned_db = _preprocess_shape_screen(config, config.database_path)
        config.database_path = aligned_db

    # Resolve grid files (supports glob patterns and multiple files)
    grid_input = config.grid_input
    if grid_input == "None":
        grid_files: list[str] = ["None"]
    else:
        # Expand glob patterns
        expanded = sorted(glob.glob(grid_input))
        grid_files = expanded if expanded else [grid_input]

    user_title = config.job_title  # Preserve user override

    original_cwd = Path.cwd()
    for grid_file in grid_files:
        # Per-grid job title: use user override if given, else auto-generate
        if user_title:
            job_title = user_title
        else:
            config.grid_input = grid_file  # Let auto_job_title see this grid
            job_title = config.auto_job_title
        config.job_title = job_title

        # Create and enter working directory
        work_dir = original_cwd / job_title
        work_dir.mkdir(parents=True, exist_ok=True)
        os.chdir(work_dir)
        try:
            inp_path = generate_inp(config, grid_file, job_title)
            _submit_pipeline(config, inp_path, job_title)
        finally:
            os.chdir(original_cwd)

    # Restore user-supplied title for cleanliness
    config.job_title = user_title
    config.grid_input = grid_input
