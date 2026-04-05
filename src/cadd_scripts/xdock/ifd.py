"""Induce Fit Docking .inp generation and job submission.

Translates XDock Bash lines 732-820 (Induce Fit Module).
"""

from __future__ import annotations

from pathlib import Path

from ..utils import run_cmd
from .config import XDockConfig


VALID_FORCE_FIELDS = ("OPLS4", "OPLS3e", "OPLS3", "OPLS_2005")


def _structcat_merge(
    schrodinger: Path,
    input_dir: Path,
    output_file: Path,
) -> None:
    """Concatenate all structure files in *input_dir* into *output_file*.

    Reproduces the Bash loop::

        for i in `ls ${dir}`;do
            $SCHRODINGER/utilities/structcat -i ${dir}/${i} -o merged.maegz
        done

    Each call appends to *output_file*.
    """
    structcat = str(schrodinger / "utilities" / "structcat")
    if input_dir.is_dir():
        files = sorted(input_dir.iterdir())
    else:
        files = [input_dir]

    for f in files:
        run_cmd([structcat, "-i", str(f), "-o", str(output_file)])


def generate_ifd_inp(config: XDockConfig) -> Path:
    """Generate Induce Fit Docking .inp file.

    Faithfully reproduces XDock lines 733-811.
    """
    schrodinger = config.require_schrodinger()
    title = config.auto_job_title

    # Merge protein structures
    proteins_merged = Path("Proteins_to_InduceFitDock.maegz")
    _structcat_merge(schrodinger, config.protein_input, proteins_merged)

    # Merge ligand structures
    ligands_merged = Path("Ligands_to_InduceFitDock.maegz")
    if config.ligand_input:
        _structcat_merge(schrodinger, config.ligand_input, ligands_merged)

    # Determine binding site definition
    if config.by_complex:
        binding_site = f"ligand {config.ref_ligand_asl}"
    elif config.by_center:
        binding_site = f"coords {config.grid_center}"
    else:
        raise ValueError(
            "Induce Fit Docking cannot be used with SiteMap."
        )

    # Validate force field
    if config.force_field not in VALID_FORCE_FIELDS:
        valid = ", ".join(VALID_FORCE_FIELDS)
        raise ValueError(
            f"Invalid force field '{config.force_field}'. Valid: {valid}"
        )

    # Build .inp content -- matches the exact Bash heredoc (lines 745-811)
    lines = [
        f"#Job Dic.: {Path.cwd()}",
        "########################################",
        f"# {schrodinger}/ifd -NGLIDECPU {config.njobs} "
        f"-NPRIMECPU {config.prime_njobs}  {title}.inp "
        f"-NOLOCAL -HOST {config.host} -SUBHOST {config.host} -TMPLAUNCHDIR",
        "########################################",
        f"INPUT_FILE  {proteins_merged}",
    ]

    # Optional PPREP stage (original Bash checks ProPrep == "true",
    # which never matches the allowed values; kept for fidelity)
    if config.pro_prep == "true":
        lines.extend([
            "STAGE PPREP",
            "    RMSD    0.5",
            "",
        ])

    # Main IFD stages (exact replica of Bash heredoc IFT2)
    lines.extend([
        "STAGE VDW_SCALING",
        f"  BINDING_SITE {binding_site}",
        "",
        "STAGE PREDICT_FLEXIBILITY",
        f"  BINDING_SITE  {binding_site}",
        "",
        "STAGE INITIAL_DOCKING",
        f"  BINDING_SITE  {binding_site}",
        "  INNERBOX 12.0",
        "  OUTERBOX 30.0",
        f"  LIGAND_FILE {ligands_merged}",
        "  LIGANDS_TO_DOCK all",
        "  DOCKING_RINGCONFCUT 10.0",
        "  DOCKING_AMIDE_MODE penal",
        f"  DOCKING_FORCEFIELD {config.force_field}",
        "",
        "STAGE COMPILE_RESIDUE_LIST",
        f"  DISTANCE_CUTOFF {config.distance}",
        "",
        "STAGE PRIME_REFINEMENT",
        "  NUMBER_OF_PASSES 1",
        "  USE_MEMBRANE no",
        f"  OPLS_VERSION  {config.force_field}",
        "",
        "STAGE SORT_AND_FILTER",
        "  POSE_FILTER r_psp_Prime_Energy",
        "  POSE_KEEP 30.0",
        "",
        "STAGE SORT_AND_FILTER",
        "  POSE_FILTER r_psp_Prime_Energy",
        "  POSE_KEEP 20#",
        "",
        "STAGE GLIDE_DOCKING2",
        "  BINDING_SITE ligand Z:999",
        "  INNERBOX 10.0",
        "  OUTERBOX auto",
        f"  LIGAND_FILE {ligands_merged}",
        "  LIGANDS_TO_DOCK existing",
        "  DOCKING_PRECISION SP",
        "  DOCKING_CANONICALIZE False",
        "  DOCKING_RINGCONFCUT 10.0",
        "  DOCKING_AMIDE_MODE penal",
        f"  PRECISION {config.precision}",
        f"  DOCKING_FORCEFIELD {config.force_field}",
        "",
        "STAGE SCORING",
        "  SCORE_NAME  r_psp_IFDScore",
        "  TERM 1.0,r_i_glide_gscore,0",
        "  TERM 0.05,r_psp_Prime_Energy,1",
        "  REPORT_FILE report.csv",
        "",
    ])

    inp_path = Path(f"{title}.inp")
    inp_path.write_text("\n".join(lines) + "\n")
    return inp_path


# ---------------------------------------------------------------------------
# Job submission
# ---------------------------------------------------------------------------

def run_ifd(config: XDockConfig) -> None:
    """Run Induce Fit Docking job.

    Reproduces XDock lines 813-819.
    """
    schrodinger = config.require_schrodinger()
    title = config.auto_job_title

    # Create job directory
    job_dir = Path(title)
    job_dir.mkdir(parents=True, exist_ok=True)

    inp_path = generate_ifd_inp(config)

    print("Submitting Induce Fit Docking Jobs......")
    print()

    cmd = [str(schrodinger / "ifd")]
    if config.host == "localhost":
        cmd += [
            "-NGLIDECPU", str(config.njobs),
            "-NPRIMECPU", str(config.prime_njobs),
            "-HOST", f"localhost:{config.njobs}",
            "-TMPLAUNCHDIR", "-WAIT", "-OVERWRITE",
            str(inp_path),
        ]
    else:
        cmd += [
            "-NGLIDECPU", str(config.njobs),
            "-NPRIMECPU", str(config.prime_njobs),
            str(inp_path),
            "-NOLOCAL",
            "-HOST", config.host,
            "-SUBHOST", config.host,
            "-TMPLAUNCHDIR", "-OVERWRITE",
            str(inp_path),
        ]
    run_cmd(cmd)
