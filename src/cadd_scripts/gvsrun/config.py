"""Configuration dataclass for the GVSrun virtual screening pipeline.

All defaults are taken from the original GVSrun Bash script (lines 8-61).
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class GVSRunConfig:
    """Configuration for GVSrun virtual screening pipeline.

    Mirrors every tuneable knob exposed by the Bash ``GVSrun`` script.
    """

    # ------------------------------------------------------------------
    # Input
    # ------------------------------------------------------------------
    grid_input: str = "None"  # Grid file pattern (*.zip by default)
    database: str = "Custom_DB"
    database_path: Path | None = None

    # ------------------------------------------------------------------
    # Pipeline
    # ------------------------------------------------------------------
    running_mode: str = "Fast"
    pipeline: str = ""  # Resolved pipeline string (set during execution)
    job_title: str = ""

    # ------------------------------------------------------------------
    # Reference
    # ------------------------------------------------------------------
    reference_ligand: Path | None = None

    # ------------------------------------------------------------------
    # Molecular properties / output control
    # ------------------------------------------------------------------
    ph: str = "7.0:2.0"
    dock_out_conf: int = 1
    htvs_out_num: str = "5%"
    docking_out_num: str = "4000"
    set_pull_num: str = "500"
    qm_set: str = "B3LYP-D3(BJ):6-311G**"
    mw_range: str = "100:400"
    scaling_vdw: float = 0.8
    smarts: str | None = None

    # ------------------------------------------------------------------
    # Filtering
    # ------------------------------------------------------------------
    ligand_filter: bool = True
    filter_reactive_group: bool = False
    covalent_attach_residue: str | None = None

    # ------------------------------------------------------------------
    # Force fields
    # ------------------------------------------------------------------
    coarse_ff: str = "OPLS_2005"
    force_field: str = "OPLS4"
    strain_energy: str = "false"

    # ------------------------------------------------------------------
    # Shape screening  ("keep_num:sample_method:max_confs")
    # ------------------------------------------------------------------
    shape_screen: str | None = None  # User-provided override
    shape_screen_default: str = "10000:rapid:100"
    shape_screen_switch: bool = False

    # ------------------------------------------------------------------
    # Job control
    # ------------------------------------------------------------------
    host: str = "CPU"
    njobs: int = 100
    prime_njobs: int = 10
    glide_njobs: int = 90
    ligprep_njobs: int = 30
    phase_njobs: int = 10
    qsite_njobs: int = 10
    qikprop_njobs: int = 10
    macromodel_njobs: int = 10

    # ------------------------------------------------------------------
    # Paths
    # ------------------------------------------------------------------
    schrodinger: Path | None = field(
        default_factory=lambda: (
            Path(p) if (p := os.environ.get("SCHRODINGER")) else None
        )
    )

    # ------------------------------------------------------------------
    # Internal state (set during execution, not from CLI)
    # ------------------------------------------------------------------
    ligand_name: str = "INPUT_Ligands"
    to_rmsd: str = "INPUT_Ligands"

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def require_schrodinger(self) -> Path:
        """Return the Schrodinger installation path or raise."""
        if not self.schrodinger:
            raise RuntimeError(
                "Schrodinger path not set. Use -S or set $SCHRODINGER."
            )
        return self.schrodinger

    @property
    def auto_job_title(self) -> str:
        """Derive a job title when none was explicitly given.

        Format matches Bash: {database}-{grid_stem}-{running_mode}.
        The grid portion is "NoGrid" when grid_input is "None".
        """
        if self.job_title:
            return self.job_title
        # Extract stem from grid_input (supports glob patterns by taking first part)
        if self.grid_input == "None" or not self.grid_input:
            grid_stem = "NoGrid"
        else:
            # Use Bash-style %%.zip* extraction (longest match at end)
            grid_name = Path(self.grid_input).name
            grid_stem = grid_name.split(".zip")[0] if ".zip" in grid_name else Path(grid_name).stem
        return f"{self.database}-{grid_stem}-{self.running_mode}"

    @property
    def shape_screen_array(self) -> list[str]:
        """Return the effective shape-screen parameters as a list.

        The format is ``[keep_num, sample_method, max_confs]``.
        """
        raw = self.shape_screen or self.shape_screen_default
        return raw.split(":")

    @property
    def qm_dft_name(self) -> str:
        """DFT functional extracted from *qm_set* (``DFT:Basis``)."""
        return self.qm_set.split(":")[0]

    @property
    def qm_basis(self) -> str:
        """Basis set extracted from *qm_set* (``DFT:Basis``)."""
        return self.qm_set.split(":")[1]

    @property
    def ph_value(self) -> str:
        """pH value extracted from *ph* (``pH:tolerance``)."""
        return self.ph.split(":")[0]

    @property
    def ph_tolerance(self) -> str:
        """pH tolerance extracted from *ph* (``pH:tolerance``)."""
        return self.ph.split(":")[1]

    @property
    def mw_min(self) -> str:
        """Minimum molecular weight from *mw_range* (``min:max``)."""
        return self.mw_range.split(":")[0]

    @property
    def mw_max(self) -> str:
        """Maximum molecular weight from *mw_range* (``min:max``)."""
        return self.mw_range.split(":")[1]
