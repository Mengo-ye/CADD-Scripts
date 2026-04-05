"""Utility stage generators for GVSrun.

Three utility tasks:

- RMSD       -- rmsd.RmsdStage (in-pipeline RMSD calculation)
- PhaseShape -- phase.PhaseShapeStage (shape-based screening inside pipeline)
- localShape -- External $SCHRODINGER/shape_screen subprocess
"""

from __future__ import annotations

import os
import subprocess
from typing import Any


# ---------------------------------------------------------------------------
# A. RMSD -- rmsd.RmsdStage
# ---------------------------------------------------------------------------

def _generate_rmsd(task: str, ctx: dict[str, Any]) -> tuple[str, str]:
    """Generate an RMSD calculation stage.

    Required *ctx* keys:
      to_rmsd, ligand_name
    """
    to_rmsd: str = ctx["to_rmsd"]
    ligand_name: str = ctx["ligand_name"]

    lines = [
        "[STAGE:RMSD]",
        "    STAGECLASS  rmsd.RmsdStage",
        f"    INPUT   {to_rmsd},{ligand_name}",
        "    OUTPUTS RMSD_OUT",
        "    UNIQUEFIELD  s_m_title",
        f"[USEROUTS:{task}]",
        "    USEROUTS   RMSD_OUT,",
        "    STRUCTOUT   RMSD_OUT",
    ]

    return "\n".join(lines) + "\n", "RMSD_OUT"


# ---------------------------------------------------------------------------
# B. PhaseShape -- phase.PhaseShapeStage
# ---------------------------------------------------------------------------

def _generate_phase_shape(task: str, ctx: dict[str, Any]) -> tuple[str, str]:
    """Generate a PhaseShape screening stage.

    Required *ctx* keys:
      ligand_name, reference_ligand, max_confs
    """
    ligand_name: str = ctx["ligand_name"]
    reference_ligand: str = ctx["reference_ligand"]
    max_confs: str = ctx["max_confs"]

    lines = [
        "[STAGE:PhaseShape]",
        "    STAGECLASS  phase.PhaseShapeStage",
        f"    INPUT   {ligand_name}",
        "    OUTPUTS   Shape_OUT",
        f"    MAX_CONFS   {max_confs}",
        "    ATOM_TYPES  pharm",
        f"    REF_SHAPE_FILE     {reference_ligand}",
        "    EXISTING_CONFS  keep",
        "    CONFS_PER_BOND  12",
        "    AMIDE_MODE  trans",
        f"[USEROUTS:{task}]",
        "    USEROUTS   Shape_OUT,",
        "    STRUCTOUT   Shape_OUT",
    ]

    return "\n".join(lines) + "\n", "Shape_OUT"


# ---------------------------------------------------------------------------
# C. localShape -- External $SCHRODINGER/shape_screen subprocess
# ---------------------------------------------------------------------------

def _resolve_shape_database(
    database_location: str, database: str
) -> str:
    """Determine the shape_screen database argument.

    Mirrors the Bash logic:
    - If the path ends in ``.phdb`` -> use directly
    - If a single .mae / .maegz / .sdf file -> use directly
    - If a directory -> build a ``.list`` file from contained mae/maegz/sdf
    """
    valid_extensions = {"mae", "maegz", "sdf"}

    if database_location.endswith(".phdb"):
        return database_location

    ext = database_location.rsplit(".", 1)[-1] if "." in database_location else ""
    if ext in valid_extensions:
        return database_location

    if os.path.isdir(database_location):
        list_path = f"{database}.list"
        with open(list_path, "w") as fh:
            for fname in os.listdir(database_location):
                fext = fname.rsplit(".", 1)[-1] if "." in fname else ""
                if fext in valid_extensions:
                    # Copy file into working directory (mirrors original)
                    src = os.path.join(database_location, fname)
                    if not os.path.exists(fname):
                        # Use a simple copy; avoids importing shutil
                        with open(src, "rb") as sf, open(fname, "wb") as df:
                            df.write(sf.read())
                    fh.write(fname + "\n")
        return list_path

    raise ValueError(
        f"Unrecognised database location: {database_location}"
    )


def _generate_local_shape(task: str, ctx: dict[str, Any]) -> tuple[str, str]:
    """Build and (optionally) run the $SCHRODINGER/shape_screen command.

    Required *ctx* keys:
      reference_ligand, database_location, database,
      keep_num, shape_sample_method, max_confs,
      schrodinger, host, njobs, pipeline

    Returns
    -------
    tuple[str, str]
        ``(command_string, new_ligand_name)``

    Side effects when called in "execute" mode:
      Launches ``shape_screen`` as a subprocess.
    """
    reference_ligand: str = ctx["reference_ligand"]
    database_location: str = ctx["database_location"]
    database: str = ctx["database"]
    keep_num: str = ctx["keep_num"]
    shape_sample_method: str = ctx["shape_sample_method"]
    max_confs: str = ctx["max_confs"]
    schrodinger: str = ctx["schrodinger"]
    host: str = ctx["host"]
    njobs: int = ctx["njobs"]
    pipeline: str = ctx["pipeline"]

    # Determine pharm parameters
    if reference_ligand == "phypo":
        pharm_params = " -proj -pharm "
    else:
        pharm_params = " -pharm "

    # Resolve database
    shape_db = _resolve_shape_database(database_location, database)

    ref_basename = os.path.basename(reference_ligand)
    job_name = f"shape_screen_using_{ref_basename}"

    cmd_parts = [
        f"{schrodinger}/shape_screen",
        f"-shape {reference_ligand}",
        f"-screen {shape_db}",
        pharm_params.strip(),
        f"-JOB {job_name}",
        "-sort",
        f"-keep {keep_num}",
        f"-sample {shape_sample_method}",
        f"-max {max_confs}",
        f'-HOST "{host}:{njobs}"',
        "-TMPLAUNCHDIR",
    ]

    # If localShape is the only/first task in the pipeline, run without -WAIT
    # and exit (non-blocking). Otherwise, run with -WAIT (blocking).
    is_standalone = pipeline == "localShape" or pipeline.startswith("localShape")

    if is_standalone:
        cmd = " ".join(cmd_parts)
    else:
        cmd_parts.append("-WAIT")
        cmd = " ".join(cmd_parts)

    # New database location after shape screening completes
    align_file = os.path.join(
        os.getcwd(), f"{job_name}_align.maegz"
    )

    return cmd, align_file


def run_local_shape(task: str, ctx: dict[str, Any]) -> tuple[str, str]:
    """Execute localShape as a subprocess (mirrors original Bash behaviour).

    Returns
    -------
    tuple[str, str]
        ``(command_executed, new_database_location)``
    """
    cmd, align_file = _generate_local_shape(task, ctx)
    pipeline: str = ctx["pipeline"]
    is_standalone = pipeline == "localShape" or pipeline.startswith("localShape")

    subprocess.run(cmd, shell=True, check=True)  # noqa: S602

    if is_standalone:
        # Original script calls `exit` after non-blocking submission
        return cmd, ""

    return cmd, align_file


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------

_GENERATORS = {
    "rmsd": _generate_rmsd,
    "phase_shape": _generate_phase_shape,
    "local_shape": _generate_local_shape,
}


def generate(task: str, ctx: dict[str, Any]) -> tuple[str, str]:
    """Generate INP text (or command) for a utility *task*.

    Parameters
    ----------
    task:
        One of the keys in ``UTILITY_TASKS``.
    ctx:
        Runtime context dictionary.

    Returns
    -------
    tuple[str, str]
        ``(stage_text_or_command, new_ligand_name)``
    """
    entry = UTILITY_TASKS[task]
    gen_fn = _GENERATORS[entry["template"]]
    return gen_fn(task, ctx)


# ---------------------------------------------------------------------------
# Registry -- 3 tasks
# ---------------------------------------------------------------------------

UTILITY_TASKS: dict[str, dict[str, Any]] = {
    "RMSD": {
        "template": "rmsd",
        "description": "RMSD calculation between reference and docked poses",
    },
    "PhaseShape": {
        "template": "phase_shape",
        "description": "Phase shape-based screening inside the VSW pipeline",
    },
    "localShape": {
        "template": "local_shape",
        "description": "External shape_screen subprocess ($SCHRODINGER/shape_screen)",
    },
}
