from dataclasses import dataclass, field
from pathlib import Path
import os


@dataclass
class XDockConfig:
    """Configuration for XDock jobs."""

    # Input
    protein_input: Path
    ligand_input: Path | None = None

    # Mode
    mode: str = "SITEMAP"

    # Peptide
    peptide_segment: str | None = None  # "length:stepwise" format, e.g. "12:5"
    peptide_fasta: Path | None = None
    peptide_cap: bool = False
    only_peptide_segment: bool = False

    # Preparation
    lig_prep: str = "epik"       # none/epik/ionizer
    pro_prep: str = "rough"      # none/rosetta/rough/fine/hopt/mini

    # Mode flags (set by resolve_mode)
    by_center: bool = False
    by_complex: bool = True
    by_sitemap: bool = True
    xglide: bool = True
    docking: str = "true"        # "true"/"false"/"peptide"
    induce_fit: bool = False
    grid_in: bool = False

    # Grid
    grid_center: str = ""        # "x, y, z"
    site_num: int = 2
    box_inner: int = 12
    box_buffer: int = 5
    ligand_asl: str = ""

    # Docking
    pose_num: int = 1
    out_com: int = 1
    docking_method: str = "confgen"  # confgen/mininplace
    precision: str = "SP"            # SP/XP/HTVS
    strain_correction: bool = True
    scaling_vdw: float = 0.8
    scaling_vdw_rec: float = 1.0
    sampling: int = 1
    maxkeep: int = 5000

    # Induce Fit
    ref_ligand_asl: str = "A:999"
    force_field: str = "OPLS_2005"
    distance: float = 5.0
    prime_njobs: int = 10

    # Job control
    host: str = "CPU"
    njobs: int = 50
    job_title: str = ""

    # Paths
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

    # UniProt filtering
    uniprot_list: Path | None = None
    grid_lib: Path | None = None

    def require_schrodinger(self) -> Path:
        if not self.schrodinger:
            raise RuntimeError(
                "Schrödinger path not set. Use --schrodinger or set $SCHRODINGER."
            )
        return self.schrodinger

    def require_rosetta(self) -> tuple[Path, Path]:
        if not self.rosetta_app:
            raise RuntimeError(
                "Rosetta app path not set. Use --rosetta-app or set $rosetta_app."
            )
        if not self.rosetta_db:
            raise RuntimeError(
                "Rosetta database path not set. Use --rosetta-db or set $rosetta_db."
            )
        return self.rosetta_app, self.rosetta_db

    @property
    def auto_job_title(self) -> str:
        if self.job_title:
            return self.job_title
        protein_name = self.protein_input.name
        ligand_name = self.ligand_input.stem if self.ligand_input else "NoLigand"
        return f"{self.mode}-{protein_name}-{ligand_name}-XDOCK"
