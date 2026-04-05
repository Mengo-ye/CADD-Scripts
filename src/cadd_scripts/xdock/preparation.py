from pathlib import Path

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
        "PPREP_IMPREF": str(impref).upper(),
        "PPREP_WATERDIST": "5.0",
        "PPREP_DELWATER": "hbond_cut",
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

    if protein_input.is_dir():
        pdb_files = sorted(protein_input.glob("*.pdb"))
        for pdb in pdb_files:
            run_cmd([
                exe, "-database", str(rosetta_db),
                "-in:file:s", str(pdb),
                "-out:path:pdb", str(out_dir),
            ])
    else:
        run_cmd([
            exe, "-database", str(rosetta_db),
            "-in:file:s", str(protein_input),
            "-out:path:pdb", str(out_dir),
        ])

    return out_dir
