"""Filtering stage generators for GVSrun.

Provides template functions and a registry for ligand filter tasks,
the No_Dup (MergeDuplicates) stage, the QIKPROP stage, and the MW stage.
"""

from __future__ import annotations

from typing import Any


# ---------------------------------------------------------------------------
# Generic LigFilter stage
# ---------------------------------------------------------------------------

def filter_stage(
    task_name: str,
    config: Any,
    params: dict[str, Any],
    ligand_name: str,
) -> tuple[str, str]:
    """Generate .inp block for a LigFilterStage task.

    Parameters
    ----------
    task_name:
        Pipeline task identifier (e.g. ``"RDL"``, ``"5R"``).
    config:
        Pipeline configuration object (unused by simple filters but
        kept for interface consistency with other stage generators).
    params:
        Entry from :data:`FILTER_TASKS`.
    ligand_name:
        Current ligand variable name flowing through the pipeline.

    Returns
    -------
    tuple[str, str]
        ``(inp_block, new_ligand_name)``
    """
    stage_name = params.get("stage_name", task_name)
    output = params["output"]
    conditions = params["conditions"]  # list of condition strings
    has_userouts = params.get("has_userouts", False)
    userouts_output = params.get("userouts_output", output)

    cond_str = ", ".join(f'"{c}"' for c in conditions)

    block = (
        f"[STAGE:{stage_name}]\n"
        f"    STAGECLASS   filtering.LigFilterStage\n"
        f"    INPUTS   {ligand_name},\n"
        f"    OUTPUTS   {output},\n"
        f"    CONDITIONS   {cond_str}\n"
    )

    if has_userouts:
        block += (
            f"[USEROUTS:{task_name}]\n"
            f"    USEROUTS   {userouts_output},\n"
            f"    STRUCTOUT   {userouts_output}\n"
        )

    return block, output


# ---------------------------------------------------------------------------
# No_Dup  --  MergeDuplicatesStage (not a LigFilter)
# ---------------------------------------------------------------------------

def no_dup_stage(
    task_name: str,
    config: Any,
    params: dict[str, Any],
    ligand_name: str,
) -> tuple[str, str]:
    """Generate .inp block for the No_Dup (MergeDuplicatesStage) task."""
    output = "No_Dup_OUT"
    block = (
        "[STAGE:No_Dup]\n"
        "    STAGECLASS   filtering.MergeDuplicatesStage\n"
        f"    INPUTS   {ligand_name},\n"
        f"    OUTPUTS   {output},\n"
        "    SMILES_FIELD   VendorSMILES\n"
        "    DESALT   YES\n"
        "    MERGE_PROPS   YES\n"
        "    OUTFORMAT   sdf\n"
        "    NEUTRALIZE  YES\n"
    )
    return block, output


# ---------------------------------------------------------------------------
# QIKPROP  --  RecombineStage + QikPropStage
# ---------------------------------------------------------------------------

def qikprop_stage(
    task_name: str,
    config: Any,
    params: dict[str, Any],
    ligand_name: str,
) -> tuple[str, str]:
    """Generate .inp block for the QIKPROP task."""
    output = "QIKPROP_OUT"
    block = (
        "[STAGE:PRE_QIKPROP]\n"
        "    STAGECLASS   gencodes.RecombineStage\n"
        f"    INPUTS   {ligand_name},\n"
        "    OUTPUTS   PRE_QIKPROP_RECOMBINE_OUT,\n"
        "    NUMOUT   njobs\n"
        "    OUTFORMAT   maegz\n"
        "    MIN_SUBJOB_STS   4000\n"
        "    MAX_SUBJOB_STS   40000\n"
        "    GENCODES   YES\n"
        "    OUTCOMPOUNDFIELD   s_vsw_compound_code\n"
        "    OUTVARIANTFIELD   s_vsw_variant\n"
        "    UNIQUEFIELD   s_m_title\n"
        "[STAGE:QIKPROP]\n"
        "    STAGECLASS   qikprop.QikPropStage\n"
        "    INPUTS   PRE_QIKPROP_RECOMBINE_OUT,\n"
        f"    OUTPUTS   {output},\n"
        "    RECOMBINE   YES\n"
        f"[USEROUTS:{task_name}]\n"
        f"    USEROUTS   {output},\n"
        f"    STRUCTOUT   {output}\n"
    )
    return block, output


# ---------------------------------------------------------------------------
# MW  --  LigFilterStage with dynamic MW range from config
# ---------------------------------------------------------------------------

def mw_stage(
    task_name: str,
    config: Any,
    params: dict[str, Any],
    ligand_name: str,
) -> tuple[str, str]:
    """Generate .inp block for the MW (molecular weight) filter task.

    Uses ``config.mw_range`` which should be ``"MIN:MAX"`` (e.g. ``"100:400"``).
    """
    mw_range = getattr(config, "mw_range", "100:400")
    parts = mw_range.split(":")
    mw_min = parts[0]
    mw_max = parts[1]
    output = "MW_OUT"

    block = (
        "[STAGE:MW]\n"
        "    STAGECLASS   filtering.LigFilterStage\n"
        f"    INPUTS   {ligand_name},\n"
        f"    OUTPUTS   {output},\n"
        f'    CONDITIONS   "Molecular_weight <= {mw_max} AND >= {mw_min}"\n'
    )
    return block, output


# ---------------------------------------------------------------------------
# FILTER_TASKS registry
# ---------------------------------------------------------------------------
# Each entry maps a task name to its parameters.
#
# Keys:
#   template   -- "filter" (standard LigFilter), or the name of a special
#                 generator function ("no_dup", "qikprop", "mw").
#   stage_name -- The [STAGE:xxx] label if different from the task name.
#   output     -- The OUTPUTS variable name.
#   conditions -- List of condition strings (without surrounding quotes).
#   has_userouts -- Whether to emit a [USEROUTS] block.
#   userouts_output -- Override for the USEROUTS variable if different from
#                      ``output`` (see Warhead_SO).

FILTER_TASKS: dict[str, dict[str, Any]] = {
    # ---- Standard LigFilter tasks (no QIKPROP dependency) ----
    "RDL": {
        "template": "filter",
        "output": "RDL_OUT",
        "conditions": [
            "Molecular_weight <= 650",
            "Num_rotatable_bonds <= 10",
            "Num_rings <= 6",
        ],
        "has_userouts": False,
    },
    "EDL": {
        "template": "filter",
        "output": "EDL_OUT",
        "conditions": [
            "Molecular_weight <= 350",
            "Num_rotatable_bonds <= 8",
            "Num_rings <= 4",
        ],
        "has_userouts": False,
    },
    "Fragment": {
        "template": "filter",
        "output": "Fragment_OUT",
        "conditions": [
            "Num_heavy_atoms <= 15",
        ],
        "has_userouts": False,
    },
    "R": {
        "template": "filter",
        "stage_name": "RR",
        "output": "R_OUT",
        "conditions": [
            "Reactive_groups > 0",
        ],
        "has_userouts": False,
    },
    "NR": {
        "template": "filter",
        "output": "NR_OUT",
        "conditions": [
            "Reactive_groups == 0",
        ],
        "has_userouts": False,
    },
    "NPSE": {
        "template": "filter",
        "output": "NPSE_OUT",
        "conditions": [
            "Phosphonate_esters == 0",
            "Sulphonate_esters == 0",
        ],
        "has_userouts": False,
    },
    "PosMol": {
        "template": "filter",
        "output": "PosMol_OUT",
        "conditions": [
            "Total_charge > 0",
        ],
        "has_userouts": False,
    },
    "NegMol": {
        "template": "filter",
        "output": "NegMol_OUT",
        "conditions": [
            "Total_charge < 0",
        ],
        "has_userouts": False,
    },
    # ---- LigFilter tasks requiring QIKPROP upstream ----
    "5R": {
        "template": "filter",
        "output": "5R_OUT",
        "conditions": [
            "r_qp_mol_MW <= 500",
            "r_qp_QPlogPo/w <= 5",
            "r_qp_donorHB <= 5",
            "r_qp_accptHB <= 10",
            "r_qp_PSA <= 120",
        ],
        "has_userouts": True,
    },
    "R5R": {
        "template": "filter",
        "output": "R5R_OUT",
        "conditions": [
            "r_qp_mol_MW <= 650",
            "r_qp_QPlogPo/w <= 7",
            "r_qp_donorHB <= 6",
            "r_qp_accptHB <= 20",
        ],
        "has_userouts": True,
    },
    "3R": {
        "template": "filter",
        "output": "3R_OUT",
        "conditions": [
            "r_qp_QPlogS > -5.7",
            "r_qp_QPPCaco > 22",
            "r_qp_accptHB <= 10",
            "r_qp_#metab < 7",
        ],
        "has_userouts": True,
    },
    "Star": {
        "template": "filter",
        "output": "Star_OUT",
        "conditions": [
            "r_qp_#Star <= 5",
        ],
        "has_userouts": True,
    },
    "Oral": {
        "template": "filter",
        "output": "Oral_OUT",
        "conditions": [
            "r_qp_HumanOralAbsorption >= 2",
        ],
        "has_userouts": True,
    },
    "BBB": {
        "template": "filter",
        "output": "BBB_OUT",
        "conditions": [
            "Num_rotatable_bonds <= 8",
            "r_qp_QPlogBB >= -3.0 AND <= 1.2",
            "r_qp_QPPMDCK >= 25",
        ],
        "has_userouts": True,
    },
    "Oral_Drug": {
        "template": "filter",
        "output": "Oral_Drug_OUT",
        "conditions": [
            "r_qp_RuleOfFive < 2",
            "r_qp_RuleOfThree < 2",
        ],
        "has_userouts": True,
    },
    # ---- Warhead filters ----
    "Warhead_SO": {
        "template": "filter",
        "stage_name": "Warhead",
        "output": "Warhead_SO_OUT",
        "conditions": [
            "Michael_acceptors >= 1 OR [B]([O])[O] >= 1 OR [C;r3][O;r3][C;r3] >= 1 "
            "OR [S;X2;H1] >= 1 OR [C]#[N] >=1 OR [O-0X1]=[C]1[C][C][N]1 >= 1 "
            "OR [O]=[C,c]-[C,c]=[O] >=1 OR NC(=O)C(=O)C(C)N >= 1 "
            "OR [C,c]=[C,c]-[C,c]#[N,n] >= 1 OR [C-0X2]#[C-0X2][C-0X3]=[O-0X1] >= 1 "
            "OR [C][S][S][H] >= 1 OR [N]=[O,S] >= 1 OR [N]=[C]=[S] >= 1 "
            "OR  [C;H1]([Cl])-[C](=[O]) >= 1  OR  [C]=[C][c][n] >= 1",
        ],
        "has_userouts": True,
        "userouts_output": "Warhead_OUT",
    },
    "Warhead_N": {
        "template": "filter",
        "stage_name": "Warhead",
        "output": "Warhead_N_OUT",
        "conditions": [
            "[C]=[C]-[S](=O)(=O) >= 1 OR [C](=[O])-[C] >= 1",
        ],
        "has_userouts": False,
    },
    # ---- Special stages (not standard LigFilter) ----
    "No_Dup": {
        "template": "no_dup",
    },
    "QIKPROP": {
        "template": "qikprop",
    },
    "MW": {
        "template": "mw",
    },
}


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------

_GENERATORS = {
    "filter": filter_stage,
    "no_dup": no_dup_stage,
    "qikprop": qikprop_stage,
    "mw": mw_stage,
}


def generate_filter(
    task_name: str,
    config: Any,
    ligand_name: str,
) -> tuple[str, str]:
    """Look up *task_name* in :data:`FILTER_TASKS` and generate the .inp block.

    Returns
    -------
    tuple[str, str]
        ``(inp_block, new_ligand_name)``

    Raises
    ------
    KeyError
        If *task_name* is not found in the registry.
    """
    params = FILTER_TASKS[task_name]
    gen_fn = _GENERATORS[params["template"]]
    return gen_fn(task_name, config, params, ligand_name)
