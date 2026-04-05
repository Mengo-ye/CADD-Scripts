"""Xglide .inp file generation and job submission.

Translates XDock Bash lines 581-728 (Xglide module + Native redock).
"""

from __future__ import annotations

import re
from pathlib import Path

from ..utils import run_cmd
from .config import XDockConfig
from .preparation import get_ligand_prep_flags, get_protein_prep_flags


# ---------------------------------------------------------------------------
# .inp generation
# ---------------------------------------------------------------------------

def _header_comment(config: XDockConfig) -> list[str]:
    """Return the header comment block that appears at the top of every .inp."""
    job_dir = Path.cwd()
    protein = config.protein_input
    ligand = config.ligand_input or ""
    schrodinger = config.require_schrodinger()
    title = config.auto_job_title
    njobs = config.njobs
    host = config.host
    return [
        f"#Job Dic.: {job_dir}",
        f"#Protein Lib: {protein}",
        f"#Ligand Input: {ligand}",
        "########################################",
        f"# {schrodinger}/run xglide.py -NJOBS {njobs} "
        f'-HOST "{host}:{njobs}" -verbose -DRIVERHOST "{host}" '
        f" -TMPLAUNCHDIR  {title}.inp",
        "########################################",
    ]


def check_inp(inp_path: Path) -> None:
    """Abort if the .inp has no RECEPTOR / GRID / COMPLEX lines."""
    text = inp_path.read_text()
    count = len(re.findall(r"^(RECEPTOR|GRID|COMPLEX)\b", text, re.MULTILINE))
    if count < 1:
        raise RuntimeError(
            "No RECEPTOR in inp file, please check your -P and -m Option!"
        )


def generate_xglide_inp(config: XDockConfig) -> Path:
    """Generate Xglide .inp file based on mode configuration.

    Faithfully reproduces the Bash heredoc / echo sequence in XDock
    lines 583-687.
    """
    title = config.auto_job_title
    lines: list[str] = _header_comment(config)

    protein = config.protein_input  # directory or file path

    # --- COMPLEX section (By_Complex) ---
    if config.by_complex:
        if not config.ligand_asl:
            # No ASL specified -- Bash default "first ligand detected" means
            # the COMPLEX line has no explicit ASL suffix.
            lines.append(f"COMPLEX       {protein}")
        else:
            lines.append(f"COMPLEX       {protein},{config.ligand_asl}")

    # --- SITEMAP section (By_SiteMap) ---
    if config.by_sitemap:
        lines.append(f"RECEPTOR       {protein}")
        lines.append("SITEMAP       TRUE")
        lines.append(f"SITEMAP_MAXSITES      {config.site_num}")
        lines.append("GRIDGEN_GRID_CENTER      SELF")
        lines.append("SITEMAP_FORCE       TRUE")
        lines.append("GRIDGEN_OUTERBOX       SELF")

    # --- CENTER section (By_Center) ---
    if config.by_center:
        outer = config.box_inner + config.box_buffer + 12
        outer_str = f"{outer}, {outer}, {outer}"
        lines.append(f"RECEPTOR       {protein}")
        lines.append("SITEMAP       FALSE")
        lines.append(f"GRIDGEN_GRID_CENTER      {config.grid_center}")
        lines.append(f"GRIDGEN_OUTERBOX       {outer_str}")

    # --- Grid input section (Grid_in) ---
    if config.grid_in:
        # Iterate over .grd / .zip files in the protein directory
        protein_dir = Path(protein)
        if not protein_dir.is_dir():
            raise ValueError(
                "Dock mode requires a directory of grid files as protein input."
            )
        grid_files = sorted(
            f
            for f in protein_dir.iterdir()
            if f.suffix in (".grd", ".zip")
        )
        for gf in grid_files:
            lines.append(f"GRID      {gf},-1")
    else:
        # Protein prep flags + grid generation settings (INP1 block)
        prep_flags = get_protein_prep_flags(config)
        for key, value in prep_flags.items():
            lines.append(f"{key}      {value}")

        lines.append(f"GRIDGEN_INNERBOX        {config.box_inner}")
        lines.append(f"GRIDGEN_OUTERBOX_BUFFER     {config.box_buffer}")
        lines.append(f"GRIDGEN_RECEP_VSCALE    {config.scaling_vdw_rec}")
        # GRIDGEN_PEPTIDE is true when docking mode is "peptide"
        gridgen_peptide = "true" if config.docking == "peptide" else "false"
        lines.append(f"GRIDGEN_PEPTIDE     {gridgen_peptide}")
        lines.append(f"GRIDGEN_FORCEFIELD      {config.force_field}")
        lines.append("GRIDGEN_OUTPUTDIR    .")

    # --- Ligand section (only if ligand_input provided) ---
    if config.ligand_input:
        lines.append(f"LIGAND      {config.ligand_input}")
        lines.append("MAXLIGATOMS     300")
    lig_flags = get_ligand_prep_flags(config)
    for key, value in lig_flags.items():
        lines.append(f"{key}    {value}")

    # --- Docking section ---
    # Format strain_correction bool as Bash-compatible TRUE/FALSE
    strain_str = "TRUE" if config.strain_correction else "FALSE"

    if config.docking == "true":
        lines.extend([
            f"DOCK_DOCKING_METHOD {config.docking_method}",
            f"DOCK_PRECISION      {config.precision}",
            f"DOCK_LIG_VSCALE     {config.scaling_vdw}",
            f"DOCK_POSES_PER_LIG      {config.pose_num}",
            "DOCK_POSE_OUTTYPE       poseviewer",
            f"GENERATE_TOP_COMPLEXES      {config.out_com}",
            f"DOCK_NENHANCED_SAMPLING     {config.sampling}",
            f"DOCK_FORCEFIELD      {config.force_field}",
            f"DOCK_MAXKEEP    {config.maxkeep}",
            "DOCK_POSTDOCK   True",
            f"DOCK_POSTDOCKSTRAIN     {strain_str}",
            "DOCK_EPIK_PENALTIES   True",
            "DOCK_HBOND_ACCEP_HALO    True",
        ])
    elif config.docking == "peptide":
        # In the Bash script, DOCK_PEPTIDE uses $Peptide_docking which is
        # set to true via the -t flag (same flag that sets Docking=peptide).
        lines.extend([
            "LIGPREP_STEREO_SOURCE  geometry",
            "DOCK_PEPTIDE    true",
            f"DOCK_DOCKING_METHOD {config.docking_method}",
            f"DOCK_PRECISION      {config.precision}",
            f"DOCK_LIG_VSCALE     {config.scaling_vdw}",
            f"DOCK_POSES_PER_LIG      {config.pose_num}",
            "DOCK_POSE_OUTTYPE       poseviewer",
            f"GENERATE_TOP_COMPLEXES      {config.out_com}",
            f"DOCK_NENHANCED_SAMPLING     {config.sampling}",
            f"DOCK_FORCEFIELD      {config.force_field}",
            "DOCK_MAXKEEP    200000",
            "DOCK_MAXREF     2000",
            "DOCK_POSTDOCK_NPOSE     200",
            "DOCK_POSTDOCK   True",
            f"DOCK_POSTDOCKSTRAIN     {strain_str}",
            "DOCK_EPIK_PENALTIES   True",
            "DOCK_HBOND_ACCEP_HALO    True",
        ])
    elif config.docking == "false":
        lines.append("SKIP_DOCKING      TRUE")
    else:
        raise RuntimeError(
            "Unknown docking mode. "
            "Please contact wanglin3@shanghaitech.edu.cn."
        )

    inp_path = Path(title) / f"{title}.inp"
    inp_path.parent.mkdir(parents=True, exist_ok=True)
    inp_path.write_text("\n".join(lines) + "\n")
    return inp_path


def generate_native_inp(config: XDockConfig) -> Path:
    """Generate .inp file for Native re-docking mode.

    Faithfully reproduces XDock lines 702-718.
    """
    title = config.auto_job_title
    schrodinger = config.require_schrodinger()
    protein = config.protein_input

    lines = [
        f"#Job Dic.: {Path.cwd()}",
        f"#Protein Lib: {protein}",
        "########################################",
        f"# {schrodinger}/run xglide.py -OVERWRITE -NJOBS {config.njobs} "
        f'-HOST "{config.host}:{config.njobs}" -verbose '
        f'-DRIVERHOST "{config.host}" -TMPLAUNCHDIR -OVERWRITE {title}.inp',
        "########################################",
        f"COMPLEX         {protein}",
        f"DOCK_PRECISION       {config.precision}",
        "GRIDGEN_GRID_CENTER  SELF",
        "NATIVEONLY           TRUE",
        f"DOCK_POSES_PER_LIG      {config.pose_num}",
        f"DOCK_NENHANCED_SAMPLING {config.sampling}",
        f"DOCK_DOCKING_METHOD     {config.docking_method}",
        "DOCK_POSE_OUTTYPE       poseviewer",
    ]

    inp_path = Path(title) / f"{title}.inp"
    inp_path.parent.mkdir(parents=True, exist_ok=True)
    inp_path.write_text("\n".join(lines) + "\n")
    return inp_path


# ---------------------------------------------------------------------------
# Job submission
# ---------------------------------------------------------------------------

def run_xglide(config: XDockConfig) -> None:
    """Run Xglide virtual screening job.

    Reproduces XDock lines 689-698 (Xglide) and 720-728 (Native).
    """
    schrodinger = config.require_schrodinger()
    title = config.auto_job_title

    # Create job directory and work inside it
    job_dir = Path(title)
    job_dir.mkdir(parents=True, exist_ok=True)

    if config.mode == "Native":
        inp_path = generate_native_inp(config)
        check_inp(inp_path)
        print("Submitting Native re-docking Jobs......")
        print()

        cmd = [
            str(schrodinger / "run"), "xglide.py",
            "-OVERWRITE",
            "-NJOBS", str(config.njobs),
        ]
        if config.host == "localhost":
            cmd += [
                "-HOST", f"localhost:{config.njobs}",
                "-verbose", "-WAIT", "-TMPLAUNCHDIR", "-OVERWRITE",
                str(inp_path),
            ]
        else:
            cmd += [
                "-HOST", f"{config.host}:{config.njobs}",
                "-verbose",
                "-DRIVERHOST", config.host,
                "-TMPLAUNCHDIR", "-OVERWRITE",
                str(inp_path),
            ]
        run_cmd(cmd)
    else:
        inp_path = generate_xglide_inp(config)
        check_inp(inp_path)
        print("Submitting Flexible Docking Jobs......")
        print()

        cmd = [
            str(schrodinger / "run"), "xglide.py",
            "-NJOBS", str(config.njobs),
        ]
        if config.host == "localhost":
            cmd += [
                "-HOST", f"localhost:{config.njobs}",
                "-WAIT", "-DRIVERHOST", "localhost",
                "-verbose", "-TMPLAUNCHDIR", "-OVERWRITE",
                str(inp_path),
            ]
        else:
            cmd += [
                "-HOST", f"{config.host}:{config.njobs}",
                "-verbose",
                "-DRIVERHOST", config.host,
                "-TMPLAUNCHDIR", "-OVERWRITE",
                str(inp_path),
            ]
        run_cmd(cmd)
