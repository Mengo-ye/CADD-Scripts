import shlex
import subprocess
from pathlib import Path


def run_cmd(cmd: list[str], check: bool = True) -> subprocess.CompletedProcess:
    """Run a subprocess command, printing it for transparency."""
    print(f"Running: {shlex.join(cmd)}")
    return subprocess.run(cmd, check=check)


def resolve_input(
    input_path: Path, schrodinger: Path, job_name: str
) -> tuple[Path, bool]:
    """Normalize input to .mae format.

    Returns (resolved_path, is_mpi_mode).
    - .mae/.maegz -> use directly, mpi_mode=False
    - .pdb -> structconvert to .mae, mpi_mode=True
    - directory -> structcat to merge PDBs, mpi_mode=False
    """
    suffix = input_path.suffix.lstrip(".")
    if suffix in ("mae", "maegz"):
        return input_path, False
    elif suffix == "pdb":
        out_mae = Path(f"{input_path.stem}.mae")
        run_cmd([
            str(schrodinger / "utilities" / "structconvert"),
            str(input_path),
            str(out_mae),
        ])
        return out_mae.resolve(), True
    elif input_path.is_dir():
        pdb_files = sorted(input_path.glob("*.pdb"))
        if not pdb_files:
            raise ValueError(f"No .pdb files found in directory: {input_path}")
        out_mae = Path(f"{job_name}_in.mae")
        run_cmd([
            str(schrodinger / "utilities" / "structcat"),
            "-ipdb",
            *[str(p) for p in pdb_files],
            "-omae",
            str(out_mae),
        ])
        return out_mae.resolve(), False
    else:
        raise ValueError(f"Unsupported input format: {input_path}")
