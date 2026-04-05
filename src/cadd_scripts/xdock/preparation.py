from pathlib import Path
import shutil

from ..utils import run_cmd
from .config import XDockConfig


# Protein preparation profiles
# Maps ProPrep value to (PPREP, REHTREAT, EPIK, PROTASSIGN, IMPREF)
PROTEIN_PREP_PROFILES = {
    "none":    (False, False, False, False, False),
    "rosetta": (False, False, False, False, False),  # handled separately
    "rough":   (True,  False, False, False, False),
    "fine":    (True,  True,  True,  False, False),
    "hopt":    (True,  True,  True,  True,  False),
    "mini":    (True,  True,  True,  True,  True),
}

VALID_PRO_PREP = list(PROTEIN_PREP_PROFILES.keys())

# Ligand preparation profiles
# Maps ligPrep value to (LIGPREP, LIGPREP_EPIK)
LIGAND_PREP_PROFILES = {
    "none":    (False, False),
    "epik":    (True,  True),
    "ionizer": (True,  False),
}

VALID_LIG_PREP = list(LIGAND_PREP_PROFILES.keys())


def get_protein_prep_flags(config: XDockConfig) -> dict[str, str]:
    """Return protein preparation flags for xglide .inp file."""
    if config.pro_prep not in PROTEIN_PREP_PROFILES:
        valid = ", ".join(VALID_PRO_PREP)
        raise ValueError(f"Unknown protein prep '{config.pro_prep}'. Valid: {valid}")

    pprep, rehtreat, epik, protassign, impref = PROTEIN_PREP_PROFILES[config.pro_prep]
    return {
        "PPREP": str(pprep).upper(),
        "PPREP_REHTREAT": str(rehtreat).upper(),
        "PPREP_EPIK": str(epik).upper(),
        "PPREP_PROTASSIGN": str(protassign).upper(),
        "PPREP_PROTASSIGN_EXHAUSTIVE": "FALSE",
        "PPREP_IMPREF": str(impref).upper(),
        "PPREP_IMPREF_RMSD": "0.30",
        "PPREP_WATERDIST": "3.0",
    }


def get_ligand_prep_flags(config: XDockConfig) -> dict[str, str]:
    """Return ligand preparation flags for xglide .inp file."""
    if config.lig_prep not in LIGAND_PREP_PROFILES:
        valid = ", ".join(VALID_LIG_PREP)
        raise ValueError(f"Unknown ligand prep '{config.lig_prep}'. Valid: {valid}")

    ligprep, ligprep_epik = LIGAND_PREP_PROFILES[config.lig_prep]
    return {
        "LIGPREP": str(ligprep).upper(),
        "LIGPREP_EPIK": str(ligprep_epik).upper(),
    }


def prepare_proteins_rosetta(config: XDockConfig) -> Path:
    """Prepare proteins using Rosetta score_jd2. Returns output directory."""
    rosetta_app, rosetta_db = config.require_rosetta()
    protein_input = config.protein_input

    out_dir = Path(f"{protein_input.name}-OUT")
    out_dir.mkdir(parents=True, exist_ok=True)

    exe = f"{rosetta_app}/score_jd2.{config.rosetta_version}.linuxgccrelease"

    def _run_score_jd2(pdb: Path) -> None:
        run_cmd([
            exe, "-database", str(rosetta_db),
            "-in:file:s", str(pdb),
            "-out:file:scorefile", f"{protein_input.name}_jd2.sc",
            "-out:path:pdb", str(out_dir),
            "-score:weights", "ref2015",
            "-out:pdb",
            "-ex1", "-ex2aro",
            "-ignore_zero_occupancy", "false",
            "-in:ignore_unrecognized_res", "false",
        ])

    if protein_input.is_dir():
        for pdb in sorted(protein_input.glob("*.pdb")):
            _run_score_jd2(pdb)
    else:
        _run_score_jd2(protein_input)

    return out_dir


def filter_grids_by_uniprot(config: XDockConfig) -> Path:
    """Filter grid files by UniProt IDs. Returns output directory.

    Reproduces XDock Bash lines 303-311.
    """
    if not config.uniprot_list or not config.grid_lib:
        raise ValueError("Both --uniprot-list and --grid-lib are required for UniProt filtering.")

    # Read and deduplicate UniProt IDs
    ids = sorted(set(config.uniprot_list.read_text().strip().splitlines()))

    out_dir = Path(f"{config.uniprot_list.stem}-Grid")
    out_dir.mkdir(parents=True, exist_ok=True)

    grid_lib = config.grid_lib
    copied = 0
    for uid in ids:
        uid = uid.strip()
        if not uid:
            continue
        for grid_file in grid_lib.glob(f"*{uid}*"):
            shutil.copy2(grid_file, out_dir / grid_file.name)
            copied += 1

    print(f"UniProt filtering: {len(ids)} IDs, {copied} grid files copied to {out_dir}")
    return out_dir
