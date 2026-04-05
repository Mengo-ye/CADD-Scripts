"""Input-block generators for GVSrun .inp files.

Each public function mirrors one of the *input-section* helpers in the
original Bash script: ``setGrid`` (line 449), ``setdatabase`` (line 457),
and ``SMARTs`` (line 503).
"""

from __future__ import annotations

from pathlib import Path

from .config import GVSRunConfig


# ------------------------------------------------------------------
# Grid block  (Bash: setGrid, lines 449-455)
# ------------------------------------------------------------------


def generate_grid_block(grid_path: str) -> str:
    """Return a ``[SET:GRID]`` block for the .inp file."""
    return (
        "[SET:GRID]\n"
        "    VARCLASS   Grid\n"
        f'    FILE    "{grid_path}"\n'
    )


# ------------------------------------------------------------------
# Database block  (Bash: setdatabase, lines 457-501)
# ------------------------------------------------------------------


def generate_database_block(config: GVSRunConfig) -> str:
    """Return the input-database block for the .inp file.

    Handles:
    * ``.phdb``  -- Phase database (uses ``VARCLASS PhaseDB`` + DBExport stage)
    * ``.mae``, ``.maegz``, ``.sdf``, ``.smi`` -- single structure files
    * ``.csv``  -- assumes pre-converted to ``.sdf`` by the caller
    * directory -- enumerates all recognised structure files inside it
    """
    db = config.database_path
    if db is None:
        raise ValueError("Database path not set.")

    suffix = db.suffix.lower()

    # --- PhaseDB ---------------------------------------------------
    if suffix == ".phdb":
        return (
            "[SET:INPUT_PhaseDB]\n"
            "    VARCLASS    PhaseDB\n"
            f"    PATH    {db}\n"
            "[STAGE:DBexport]\n"
            "    STAGECLASS  phase.DBExportStage\n"
            "    INPUTS  INPUT_PhaseDB,\n"
            "    OUTPUTS INPUT_Ligands,\n"
        )

    # --- Single structure file (.mae, .maegz, .sdf, .smi) ---------
    if suffix in {".mae", ".maegz", ".sdf", ".smi"}:
        return (
            "[SET:INPUT_Ligands]\n"
            "    VARCLASS    Structures\n"
            f"    FILES   {db}, \n"
        )

    # --- CSV (expect pre-conversion to .sdf) -----------------------
    if suffix == ".csv":
        sdf_path = db.with_suffix(".sdf")
        return (
            "[SET:INPUT_Ligands]\n"
            "    VARCLASS    Structures\n"
            f"    FILES   {sdf_path},\n"
        )

    # --- Directory: list every recognised file inside it -----------
    if db.is_dir():
        valid_suffixes = {".mae", ".maegz", ".sdf", ".smi"}
        files: list[str] = []
        for child in sorted(db.iterdir()):
            if child.suffix.lower() in valid_suffixes:
                files.append(str(child))
            else:
                print(
                    f"Warning: Your input {child} is not recognized."
                )
        if not files:
            raise ValueError(
                f"No recognised structure files found in {db}"
            )
        files_str = ",".join(files)
        return (
            "[SET:INPUT_Ligands]\n"
            "    VARCLASS    Structures\n"
            f"   FILES   {files_str}\n"
        )

    raise ValueError(f"Your input {db} is not recognized.")


# ------------------------------------------------------------------
# SMARTs filter  (Bash: SMARTs, lines 503-512)
# ------------------------------------------------------------------


def generate_smarts_block(
    smarts: str, ligand_name: str
) -> tuple[str, str]:
    """Return a SMARTs-filter stage block and the new ligand variable name.

    Parameters
    ----------
    smarts:
        A SMARTS expression (e.g. ``[B]([O])[O]``).
    ligand_name:
        Current pipeline ligand variable name that feeds into this stage.

    Returns
    -------
    tuple[str, str]
        ``(block_text, new_ligand_name)``
    """
    output = "SMARTs_OUT"
    block = (
        "[STAGE:SMARTs]\n"
        "    STAGECLASS   filtering.LigFilterStage\n"
        f"    INPUTS   {ligand_name},\n"
        f"    OUTPUTS   {output},\n"
        f'    CONDITIONS   "{smarts} >= 1"\n'
    )
    return block, output
