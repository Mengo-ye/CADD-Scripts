"""Docking stage generators for GVSrun.

Provides a template function and a :data:`DOCKING_TASKS` registry for the 21
standard Glide docking tasks (HTVS / SP / XP families).
"""

from __future__ import annotations

from typing import Any


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _keep_num_line(config: Any, precision: str) -> str:
    """Return the KEEP_NUM / PERCENT_TO_KEEP .inp line.

    HTVS tasks use ``config.htvs_out_num``, SP/XP tasks use
    ``config.docking_out_num``.
    """
    if precision == "HTVS":
        raw = getattr(config, "htvs_out_num", "5%")
    else:
        raw = getattr(config, "docking_out_num", "4000")
    raw = str(raw)
    if raw.endswith("%"):
        return f"    PERCENT_TO_KEEP   {raw.rstrip('%')}"
    return f"    NUM_TO_KEEP   {raw}"


# ---------------------------------------------------------------------------
# Generic docking stage generator
# ---------------------------------------------------------------------------

def docking_stage(
    task_name: str,
    config: Any,
    params: dict[str, Any],
    ligand_name: str,
) -> tuple[str, str]:
    """Generate the .inp blocks for a Glide docking task.

    Each docking task produces up to four sections:

    1. ``[STAGE:PRE_DOCK_<task>]``  -- RecombineStage
    2. ``[STAGE:DOCK_<task>]``      -- DockingStage
    3. ``[STAGE:PULL_<label>]``     -- PullStage  *(HTVS with pull only)*
    4. ``[USEROUTS:<task>]``        -- output declaration

    Parameters
    ----------
    task_name:
        Pipeline task identifier (e.g. ``"HTVS_Normal"``, ``"SP_ExtensionA"``).
    config:
        Pipeline configuration object.  Expected attributes:
        ``coarse_ff``, ``force_field``, ``scaling_vdw``, ``strain_energy``,
        ``htvs_out_num``, ``docking_out_num``, ``dock_out_conf``,
        ``reference_ligand``.
    params:
        Entry from :data:`DOCKING_TASKS`.
    ligand_name:
        Current ligand variable name flowing through the pipeline.

    Returns
    -------
    tuple[str, str]
        ``(inp_block, new_ligand_name)``
    """
    precision = params["precision"]
    has_pull = params.get("has_pull", False)

    # Determine output variable names based on precision
    if precision == "HTVS":
        dock_output = "HTVS_OUT"
        recombine_output = "HTVS_RECOMBINE_OUT"
        final_output = "HTVS_OUT_ORIG" if has_pull else "HTVS_OUT"
        forcefield = getattr(config, "coarse_ff", "OPLS_2005")
        min_subjob = "4000"
        max_subjob = "40000"
    else:
        out_suffix = f"{precision}_OUT"
        dock_output = f"{task_name}_{out_suffix}"
        recombine_output = f"DOCK_{task_name}_INPUT"
        final_output = dock_output
        forcefield = getattr(config, "force_field", "OPLS4")
        min_subjob = "300"
        max_subjob = "5000"

    scaling_vdw = getattr(config, "scaling_vdw", "0.8")
    strain_energy = getattr(config, "strain_energy", "false")
    dock_out_conf = getattr(config, "dock_out_conf", "1")
    reference_ligand = getattr(config, "reference_ligand", "")

    keep_line = _keep_num_line(config, precision)

    # ----- RecombineStage -----
    if precision == "HTVS":
        pre_stage_name = "PRE_DOCK_HTVS"
    else:
        pre_stage_name = f"PRE_DOCK_{task_name}"

    block = (
        f"[STAGE:{pre_stage_name}]\n"
        "    STAGECLASS   gencodes.RecombineStage\n"
        f"    INPUTS   {ligand_name},\n"
        f"    OUTPUTS   {recombine_output},\n"
        "    NUMOUT   njobs\n"
        "    OUTFORMAT   maegz\n"
        f"    MIN_SUBJOB_STS   {min_subjob}\n"
        f"    MAX_SUBJOB_STS   {max_subjob}\n"
        "    GENCODES   YES\n"
        "    OUTCOMPOUNDFIELD   s_vsw_compound_code\n"
        "    OUTVARIANTFIELD   s_vsw_variant\n"
        "    UNIQUEFIELD   NONE\n"
    )

    # ----- DockingStage -----
    if precision == "HTVS":
        dock_stage_name = "DOCK_HTVS"
    else:
        dock_stage_name = f"DOCK_{task_name}"

    block += (
        f"[STAGE:{dock_stage_name}]\n"
        "    STAGECLASS   glide.DockingStage\n"
        f"    INPUTS   {recombine_output}, GRID\n"
        f"    OUTPUTS   {dock_output},\n"
        "    RECOMBINE   NO\n"
        f"    PRECISION   {precision}\n"
    )

    # Optional MAXKEEP / MAXREF / SCORING_CUTOFF (before extensions)
    if "maxkeep" in params:
        block += f"    MAXKEEP {params['maxkeep']}\n"
    if "maxref" in params:
        block += f"    MAXREF {params['maxref']}\n"
    if "scoring_cutoff" in params:
        block += f"    SCORING_CUTOFF {params['scoring_cutoff']}\n"

    # Extensions: REWARD_INTRA_HBONDS, HBOND_ACCEP_HALO, HBOND_DONOR_AROMH
    if params.get("reward_intra_hbonds"):
        block += "    REWARD_INTRA_HBONDS YES\n"
    if params.get("hbond_accep_halo"):
        block += "    HBOND_ACCEP_HALO    YES\n"
    if params.get("hbond_donor_aromh"):
        block += "    HBOND_DONOR_AROMH   YES\n"
        block += "    HBOND_DONOR_AROMH_CHARGE    0.15\n"

    block += "    UNIQUEFIELD   s_vsw_compound_code\n"
    block += f"{keep_line}\n"
    block += f"    FORCEFIELD  {forcefield}\n"

    # Docking method
    docking_method = params.get("docking_method", "confgen")
    block += f"    DOCKING_METHOD   {docking_method}\n"

    # Expanded sampling (Fragment variants)
    if params.get("expanded_sampling"):
        block += "    EXPANDED_SAMPLING   YES\n"

    # Poses per ligand
    if precision == "HTVS":
        block += "    POSES_PER_LIG   1\n"
    else:
        block += f"    POSES_PER_LIG   {dock_out_conf}\n"

    # WRITE_XP_DESC (present in SP and XP, absent in HTVS)
    if precision in ("SP", "XP"):
        block += "    WRITE_XP_DESC   NO\n"

    # NENHANCED_SAMPLING (SP only)
    if "nenhanced_sampling" in params:
        block += f"    NENHANCED_SAMPLING   {params['nenhanced_sampling']}\n"

    block += "    BEST_BY_TITLE   NO\n"

    # LIG_VSCALE -- can be overridden per-task
    lig_vscale = params.get("lig_vscale_override", scaling_vdw)
    block += f"    LIG_VSCALE   {lig_vscale}\n"
    block += "    LIG_CCUT   0.15\n"
    block += "    MAXATOMS   500\n"
    block += "    MAXROTBONDS   50\n"

    # RINGCONFCUT (HTVS only)
    if "ringconfcut" in params:
        block += f"    RINGCONFCUT {params['ringconfcut']}\n"

    block += "    AMIDE_MODE   penal\n"
    block += "    POSE_OUTTYPE   LIB\n"

    # CV_CUTOFF (IFT_pre only)
    if "cv_cutoff" in params:
        block += f"    CV_CUTOFF  {params['cv_cutoff']}\n"

    # POSTDOCK
    block += "    POSTDOCK   YES\n"

    # POSTDOCK_NPOSE (some Enhanced/Shape/ExtensionA/B variants)
    if "postdock_npose" in params:
        block += f"    POSTDOCK_NPOSE  {params['postdock_npose']}\n"

    # POSTDOCKSTRAIN: hardcoded NO for HTVS, config value for SP/XP
    if precision == "HTVS":
        block += "    POSTDOCKSTRAIN   NO\n"
    else:
        block += f"    POSTDOCKSTRAIN   {strain_energy}\n"

    block += "    COMPRESS_POSES   YES\n"
    block += "    EPIK_PENALTIES   YES\n"
    block += "    FORCEPLANAR   NO\n"

    # Reference ligand (REF variants)
    if params.get("use_ref_ligand"):
        block += "    USE_REF_LIGAND  YES\n"
        block += f"    REF_LIGAND_FILE {reference_ligand}\n"
        block += "    CORE_DEFINITION mcssmarts\n"
        block += "    CORE_RESTRAIN   YES\n"
        block += "    CORE_SNAP   YES\n"
        block += "    CORE_POS_MAX_RMSD   0.52\n"
        block += "    CORECONS_FALLBACK   YES\n"

    # Shape restrain (Shape variants)
    if params.get("shape_restrain"):
        block += "    SHAPE_RESTRAIN  YES\n"
        block += f"    SHAPE_REF_LIGAND_FILE   {reference_ligand}\n"
        block += "    SHAPE_TYPING    PHASE_QSAR\n"

    # ----- PullStage (HTVS with pull) -----
    if has_pull:
        block += (
            "[STAGE:PULL_HTVS]\n"
            "    STAGECLASS   pull.PullStage\n"
            f"    INPUTS   {dock_output}, {recombine_output}\n"
            "    OUTPUTS   HTVS_OUT_ORIG,\n"
            "    UNIQUEFIELD   s_vsw_variant\n"
        )

    # ----- USEROUTS -----
    block += (
        f"[USEROUTS:{task_name}]\n"
        f"    USEROUTS   {dock_output},\n"
        f"    STRUCTOUT   {dock_output}\n"
    )

    return block, final_output


# ---------------------------------------------------------------------------
# DOCKING_TASKS registry
# ---------------------------------------------------------------------------
# Each entry maps a task name to its parameters.
#
# Keys common to all:
#   precision          -- "HTVS", "SP", or "XP"
#
# Keys for HTVS:
#   has_pull           -- Whether a PullStage follows (True for Normal/Rough/Fragment)
#   ringconfcut        -- RINGCONFCUT value (2.5 or 5)
#
# Optional keys (omitted = not present in .inp):
#   maxkeep, maxref, scoring_cutoff
#   reward_intra_hbonds, hbond_accep_halo, hbond_donor_aromh
#   nenhanced_sampling (SP only, int)
#   docking_method     -- "confgen" (default) or "mininplace"
#   expanded_sampling  -- True for Fragment variants
#   use_ref_ligand     -- True for REF variants
#   shape_restrain     -- True for Shape variants
#   postdock_npose     -- e.g. 10
#   lig_vscale_override-- Override the config value (e.g. "0.50" for IFT_pre)
#   cv_cutoff          -- CV_CUTOFF value (IFT_pre only)

DOCKING_TASKS: dict[str, dict[str, Any]] = {
    # =======================================================================
    # HTVS family  (screening precision, coarse force field, HTVS_out_num)
    # =======================================================================
    "HTVS_Normal": {
        "precision": "HTVS",
        "has_pull": True,
        "ringconfcut": "2.5",
    },
    "HTVS_Rough": {
        "precision": "HTVS",
        "has_pull": True,
        "maxkeep": 3000,
        "maxref": 200,
        "ringconfcut": "5",
    },
    "HTVS_Fragment": {
        "precision": "HTVS",
        "has_pull": True,
        "maxkeep": 20000,
        "maxref": 1000,
        "scoring_cutoff": 500,
        "expanded_sampling": True,
        "ringconfcut": "5",
    },
    "HTVS_REF": {
        "precision": "HTVS",
        "has_pull": False,
        "use_ref_ligand": True,
        "ringconfcut": "2.5",
    },
    "HTVS_Shape": {
        "precision": "HTVS",
        "has_pull": False,
        "shape_restrain": True,
        "ringconfcut": "2.5",
    },
    "IFT_pre": {
        "precision": "HTVS",
        "has_pull": False,
        "lig_vscale_override": "0.50",
        "cv_cutoff": "100.0",
        "ringconfcut": "2.5",
    },
    # =======================================================================
    # SP family  (standard precision, full force field, docking_out_num)
    # =======================================================================
    "SP_Normal": {
        "precision": "SP",
        "nenhanced_sampling": 1,
    },
    "SP_ExtensionA": {
        "precision": "SP",
        "reward_intra_hbonds": True,
        "hbond_accep_halo": True,
        "nenhanced_sampling": 1,
    },
    "SP_ExtensionB": {
        "precision": "SP",
        "reward_intra_hbonds": True,
        "hbond_accep_halo": True,
        "hbond_donor_aromh": True,
        "nenhanced_sampling": 1,
    },
    "SP_REF": {
        "precision": "SP",
        "reward_intra_hbonds": True,
        "hbond_accep_halo": True,
        "use_ref_ligand": True,
        "nenhanced_sampling": 1,
    },
    "SP_Shape": {
        "precision": "SP",
        "reward_intra_hbonds": True,
        "hbond_accep_halo": True,
        "shape_restrain": True,
        "postdock_npose": 10,
        "nenhanced_sampling": 1,
    },
    "SP_Fragment": {
        "precision": "SP",
        "maxkeep": 50000,
        "maxref": 1000,
        "scoring_cutoff": 500,
        "reward_intra_hbonds": True,
        "hbond_accep_halo": True,
        "expanded_sampling": True,
        "nenhanced_sampling": 1,
    },
    "SP_Enhanced": {
        "precision": "SP",
        "maxkeep": 15000,
        "maxref": 800,
        "reward_intra_hbonds": True,
        "hbond_accep_halo": True,
        "nenhanced_sampling": 3,
        "postdock_npose": 10,
    },
    "SP_local": {
        "precision": "SP",
        "reward_intra_hbonds": True,
        "hbond_accep_halo": True,
        "docking_method": "mininplace",
        "nenhanced_sampling": 3,
    },
    # =======================================================================
    # XP family  (extra precision, full force field, docking_out_num)
    # =======================================================================
    "XP_Normal": {
        "precision": "XP",
        "maxkeep": 10000,
        "maxref": 800,
    },
    "XP_ExtensionA": {
        "precision": "XP",
        "reward_intra_hbonds": True,
        "hbond_accep_halo": True,
        "maxkeep": 10000,
        "maxref": 800,
        "postdock_npose": 10,
    },
    "XP_ExtensionB": {
        "precision": "XP",
        "reward_intra_hbonds": True,
        "hbond_accep_halo": True,
        "hbond_donor_aromh": True,
        "maxkeep": 10000,
        "maxref": 800,
        "postdock_npose": 10,
    },
    "XP_REF": {
        "precision": "XP",
        "reward_intra_hbonds": True,
        "hbond_accep_halo": True,
        "maxkeep": 4000,
        "maxref": 400,
        "use_ref_ligand": True,
    },
    "XP_Fragment": {
        "precision": "XP",
        "reward_intra_hbonds": True,
        "hbond_accep_halo": True,
        "maxkeep": 50000,
        "maxref": 1000,
        "scoring_cutoff": 500,
        "expanded_sampling": True,
    },
    "XP_Enhanced": {
        "precision": "XP",
        "reward_intra_hbonds": True,
        "hbond_accep_halo": True,
        "maxkeep": 20000,
        "maxref": 1000,
        "postdock_npose": 10,
    },
    "XP_local": {
        "precision": "XP",
        "reward_intra_hbonds": True,
        "hbond_accep_halo": True,
        "maxkeep": 3000,
        "maxref": 300,
        "docking_method": "mininplace",
    },
}


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------

def generate_docking(
    task_name: str,
    config: Any,
    ligand_name: str,
) -> tuple[str, str]:
    """Look up *task_name* in :data:`DOCKING_TASKS` and generate the .inp blocks.

    Returns
    -------
    tuple[str, str]
        ``(inp_block, new_ligand_name)``

    Raises
    ------
    KeyError
        If *task_name* is not found in the registry.
    """
    params = DOCKING_TASKS[task_name]
    return docking_stage(task_name, config, params, ligand_name)
