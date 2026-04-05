"""Core pipeline engine for GVSrun.

Generates the ``.inp`` input file consumed by the Schrodinger ``pipeline``
command and (optionally) submits the job.
"""

from __future__ import annotations

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


# ------------------------------------------------------------------
# .inp generation
# ------------------------------------------------------------------


def generate_inp(config: GVSRunConfig, grid_path: str) -> Path:
    """Generate a complete ``.inp`` file for the virtual screening pipeline.

    Parameters
    ----------
    config:
        Fully-populated :class:`GVSRunConfig`.
    grid_path:
        Path to the grid ``.zip`` file (or ``"None"`` when no grid is used).

    Returns
    -------
    Path
        Path to the written ``.inp`` file.
    """
    # Import the registry here to avoid circular imports; the stages
    # sub-package depends on *config* and *pipeline* helpers.
    from .stages import TASK_REGISTRY, dispatch  # noqa: WPS433

    title = config.auto_job_title
    pipeline_tasks = config.pipeline.split("+")

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


def run_pipeline(config: GVSRunConfig) -> None:
    """Run the full GVSrun virtual screening pipeline.

    1. Resolve the running mode to a pipeline string.
    2. Parse QM settings if needed.
    3. Iterate over grid files and generate + submit ``.inp`` jobs.
    """
    schrodinger = config.require_schrodinger()

    # Resolve mode -> pipeline string
    config.pipeline = resolve_pipeline(config.running_mode)

    grid_input = config.grid_input

    # Derive job title when the user did not supply one
    if not config.job_title:
        grid_stem = Path(grid_input).stem if grid_input != "None" else "NoGrid"
        # Strip .zip suffix if present
        if grid_stem.endswith(".zip"):
            grid_stem = grid_stem[: -len(".zip")]
        config.job_title = (
            f"{config.database}-{grid_stem}-{config.running_mode}"
        )

    job_title = config.job_title

    # Create working directory
    work_dir = Path(job_title)
    work_dir.mkdir(parents=True, exist_ok=True)

    # Generate .inp inside the working directory
    inp_path = work_dir / f"{job_title}.inp"

    # We generate in-memory then write; generate_inp writes to cwd so we
    # handle the path ourselves.
    generated = generate_inp(config, grid_input)
    if generated.resolve() != inp_path.resolve():
        inp_path.write_text(generated.read_text())

    # Build the submission command
    host = config.host
    njobs = config.njobs

    if host == "localhost":
        cmd = [
            str(schrodinger / "run"),
            "pipeline_startup.py",
            str(inp_path),
            "-OVERWRITE",
            "-NJOBS", str(njobs),
            "-HOST", f"{host}:{njobs}",
            "-JOBNAME", job_title,
            f"-host_glide", f"{host}:{config.glide_njobs}",
            f"-host_ligprep", f"{host}:{config.ligprep_njobs}",
            f"-host_phase", f"{host}:{config.phase_njobs}",
            f"-host_prime", f"{host}:{config.prime_njobs}",
            f"-host_mmod", f"{host}:{config.macromodel_njobs}",
            f"-host_qsite", f"{host}:{config.qsite_njobs}",
            f"-host_qikprop", f"{host}:{config.qikprop_njobs}",
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
            f"-host_glide", f"{host}:{config.glide_njobs}",
            f"-host_ligprep", f"{host}:{config.ligprep_njobs}",
            f"-host_phase", f"{host}:{config.phase_njobs}",
            f"-host_prime", f"{host}:{config.prime_njobs}",
            f"-host_mmod", f"{host}:{config.macromodel_njobs}",
            f"-host_qsite", f"{host}:{config.qsite_njobs}",
            f"-host_qikprop", f"{host}:{config.qikprop_njobs}",
            str(inp_path),
        ]

    run_cmd(cmd)
