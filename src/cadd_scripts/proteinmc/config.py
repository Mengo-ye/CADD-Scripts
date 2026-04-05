from dataclasses import dataclass, field
from pathlib import Path
import os


@dataclass
class ProteinMCConfig:
    """Configuration for ProteinMC jobs."""

    input_file: Path
    job_type: str = "MC"
    cpu_host: str = "CPU"
    njobs: int = 30
    force_field: str = "S-OPLS"
    rosetta_score: str = "ref2015_cart"
    mc_steps: int = 50
    output_num: int = 3
    random_seed: bool = True
    use_membrane: bool = False
    refine_range: str = "all"
    constraints_asl: str | None = None
    constraints_force: float = 10.0
    constraints_tolerance: float = 0.0
    comp1: str = "A"
    comp2: str = "B"
    schrodinger: Path | None = field(
        default_factory=lambda: Path(p) if (p := os.environ.get("SCHRODINGER")) else None
    )
    rosetta_app: Path | None = field(
        default_factory=lambda: Path(p) if (p := os.environ.get("rosetta_app")) else None
    )
    rosetta_db: Path | None = field(
        default_factory=lambda: Path(p) if (p := os.environ.get("rosetta_db")) else None
    )
    rosetta_version: str = "mpi"

    @property
    def job_name(self) -> str:
        # SIDE_OPT internally uses SIDE_PRED, matching Bash behavior
        effective_type = "SIDE_PRED" if self.job_type == "SIDE_OPT" else self.job_type
        return f"{self.input_file.stem}_{effective_type}"

    @property
    def wait_cmd(self) -> list[str]:
        if self.cpu_host in ("localhost", "local"):
            return ["-WAIT"]
        return []

    def require_schrodinger(self) -> Path:
        """Return schrodinger path or raise if not set."""
        if not self.schrodinger:
            raise RuntimeError(
                "Schrödinger path not set. Use --schrodinger or set $SCHRODINGER."
            )
        return self.schrodinger

    def require_rosetta(self) -> tuple[Path, Path]:
        """Return (rosetta_app, rosetta_db) or raise if not set."""
        if not self.rosetta_app:
            raise RuntimeError(
                "Rosetta app path not set. Use --rosetta-app or set $rosetta_app."
            )
        if not self.rosetta_db:
            raise RuntimeError(
                "Rosetta database path not set. Use --rosetta-db or set $rosetta_db."
            )
        return self.rosetta_app, self.rosetta_db
