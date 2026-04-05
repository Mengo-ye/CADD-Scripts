"""Ligand preparation stage generators for GVSrun.

Ten ligand-preparation tasks organised into three sub-templates:

A. LigPrep  (IONIZE, EPIK4, EPIK32)
   LigPrepStage (with RECOMBINE YES) -> PostLigPrepStage -> UserOuts

B. SampleRings  (RS1, RS4, RS_Fast)
   RecombineStage -> SampleRingsStage -> UserOuts

C. ConfSearch  (CONFGEN, CONFGEN_Fast, MMFF_CONFGEN, Combine_CONFGEN)
   RecombineStage -> ConfSearchStage -> CombineStage -> UserOuts
"""

from __future__ import annotations

from typing import Any


# ---------------------------------------------------------------------------
# Template A -- LigPrep (IONIZE, EPIK4, EPIK32)
# ---------------------------------------------------------------------------

def _generate_ligprep(task: str, ctx: dict[str, Any]) -> tuple[str, str]:
    """Generate a LigPrepStage-based ligand preparation block.

    Required *ctx* keys:
      ligand_name, ph
    Template parameters come from the LIGPREP_TASKS registry entry.
    """
    params: dict[str, Any] = LIGPREP_TASKS[task]
    ligand_name: str = ctx["ligand_name"]

    # Parse PH value and tolerance from "7.0:2.0" format
    ph_parts = ctx["ph"].split(":")
    ph_value = ph_parts[0]
    pht = ph_parts[1]

    stage_name = task
    out_name = f"{task}_OUT"

    # Build the LigPrepStage lines
    lines = [
        f"[STAGE:{stage_name}]",
        f"    STAGECLASS   ligprep.LigPrepStage",
        f"    INPUTS    {ligand_name},",
        f"    OUTPUTS   {out_name},",
        f"    RECOMBINE   YES",
    ]

    # RETITLE only for EPIK variants
    if params.get("retitle", False):
        lines.append("    RETITLE   YES")

    lines.extend([
        "    MIXLIGS   YES",
        "    SKIP_BAD_LIGANDS   YES",
        "    UNIQUEFIELD   s_m_title",
        "    OUTCOMPOUNDFIELD   s_vsw_compound_code",
        f"    USE_EPIK   {params['use_epik']}",
    ])

    if params.get("max_states") is not None:
        lines.append(f"    MAX_STATES  {params['max_states']}")

    if params.get("metal_binding") is not None:
        lines.append(f"    METAL_BINDING   {params['metal_binding']}")

    lines.extend([
        f"    PH   {ph_value}",
        f"    PHT  {pht}",
        f"    MAX_TAUTOMERS   {params['max_tautomers']}",
        f"    NRINGCONFS   {params['nringconfs']}",
        "    COMBINEOUTS   YES",
    ])

    # IONIZE flag only for IONIZE task
    if params.get("ionize", False):
        lines.append("    IONIZE  YES")

    lines.extend([
        "    STEREO_SOURCE   parities",
        f"    NUM_STEREOISOMERS   {params['num_stereoisomers']}",
        f"    MAX_STEREOISOMERS   {params['max_stereoisomers']}",
        "    REGULARIZE   NO",
    ])

    # PostLigPrepStage
    lines.extend([
        "[STAGE:POSTLIGPREP]",
        "    STAGECLASS   ligprep.PostLigPrepStage",
        f"    INPUTS   {out_name},",
        "    OUTPUTS   LIGPREP_OUT,",
        "    UNIQUEFIELD   s_vsw_compound_code",
        "    OUTVARIANTFIELD   s_vsw_variant",
    ])

    if params.get("maxstereo") is not None:
        lines.append(f"    MAXSTEREO   {params['maxstereo']}")

    lines.extend([
        "    PRESERVE_NJOBS   YES",
        "    REMOVE_PENALIZED_STATES   YES",
    ])

    # UserOuts
    lines.extend([
        f"[USEROUTS:{task}]",
        "    USEROUTS   LIGPREP_OUT,",
        "    STRUCTOUT   LIGPREP_OUT",
    ])

    return "\n".join(lines) + "\n", "LIGPREP_OUT"


# ---------------------------------------------------------------------------
# Template B -- SampleRings (RS1, RS4, RS_Fast)
# ---------------------------------------------------------------------------

def _generate_samplerings(task: str, ctx: dict[str, Any]) -> tuple[str, str]:
    """Generate a SampleRingsStage-based ligand preparation block.

    Required *ctx* keys:
      ligand_name, force_field
    """
    params: dict[str, Any] = LIGPREP_TASKS[task]
    ligand_name: str = ctx["ligand_name"]
    force_field: str = ctx["force_field"]

    pre_out = f"PRE_{task}_RECOMBINE_OUT"
    stage_out = f"{task}_OUT"

    lines = [
        # RecombineStage
        f"[STAGE:PRE_{task}]",
        "    STAGECLASS   gencodes.RecombineStage",
        f"    INPUTS   {ligand_name},",
        f"    OUTPUTS   {pre_out},",
        "    NUMOUT   njobs",
        "    OUTFORMAT   maegz",
        "    MIN_SUBJOB_STS   4000",
        "    MAX_SUBJOB_STS   40000",
        "    GENCODES   YES",
        "    OUTCOMPOUNDFIELD   s_vsw_compound_code",
        "    OUTVARIANTFIELD   s_vsw_variant",
        "    UNIQUEFIELD   s_m_title",
        # SampleRingsStage
        f"[STAGE:{task}]",
        "    STAGECLASS   macromodel.SampleRingsStage",
        f"    INPUTS    {pre_out},",
        f"    OUTPUTS   {stage_out},",
        "    RECOMBINE   YES",
        f"    FORCE_FIELD {force_field}",
        "    SOLVENT Water",
        "    ELECTROSTATIC_TREATMENT Constant dielectric",
        "    CHARGES_FROM    Force field",
        f"    MAXIMUM_ITERATION   {params['maximum_iteration']}",
        f"    OUTCONFS_PER_SEARCH {params['outconfs']}",
        # UserOuts
        f"[USEROUTS:{task}]",
        f"    USEROUTS   {stage_out},",
        f"    STRUCTOUT   {stage_out}",
    ]

    return "\n".join(lines) + "\n", stage_out


# ---------------------------------------------------------------------------
# Template C -- ConfSearch (CONFGEN, CONFGEN_Fast, MMFF_CONFGEN,
#                           Combine_CONFGEN)
# ---------------------------------------------------------------------------

def _generate_confsearch(task: str, ctx: dict[str, Any]) -> tuple[str, str]:
    """Generate a ConfSearchStage-based ligand preparation block.

    Required *ctx* keys:
      ligand_name, force_field
    """
    params: dict[str, Any] = LIGPREP_TASKS[task]
    ligand_name: str = ctx["ligand_name"]
    force_field: str = ctx["force_field"]

    pre_out = f"PRE_{task}_RECOMBINE_OUT"

    lines = [
        # RecombineStage
        f"[STAGE:PRE_{task}]",
        "    STAGECLASS   gencodes.RecombineStage",
        f"    INPUTS   {ligand_name},",
        f"    OUTPUTS   {pre_out},",
        "    NUMOUT   njobs",
        "    OUTFORMAT   maegz",
        "    MIN_SUBJOB_STS   4000",
        "    MAX_SUBJOB_STS   40000",
        "    GENCODES   YES",
        "    OUTCOMPOUNDFIELD   s_vsw_compound_code",
        "    OUTVARIANTFIELD   s_vsw_variant",
        "    UNIQUEFIELD   s_m_title",
    ]

    # Single ConfSearch variants
    stage_force_field = params.get("force_field_override", force_field)
    conf_out = f"{task}_OUT"

    lines.extend([
        f"[STAGE:{task}]",
        "    STAGECLASS   macromodel.ConfSearchStage",
        f"    INPUTS    {pre_out},",
        "    RECOMBINE   YES",
        f"    OUTPUTS   {conf_out},",
        "    JOB_TYPE    CONFSEARCH",
        f"    FORCE_FIELD {stage_force_field}",
        "    SOLVENT Water",
        "    CHARGES_FROM    Force field",
        "    MINI_METHOD   TNCG",
        "    CONFSEARCH_METHOD   Mixed",
        f"    MAXIMUM_ITERATION   {params['maximum_iteration']}",
        f"    OUTCONFS_PER_SEARCH {params['outconfs']}",
        "    CUTOFF   Extended",
    ])

    # CombineStage
    combine_label = params["combine_labels"]
    lines.extend([
        "[STAGE:COMBINE]",
        "    STAGECLASS   combine.CombineStage",
        f"    INPUTS   {ligand_name}, {conf_out}",
        "    OUTPUTS   CONFGEN_COMBINED,",
        "    LABELFIELD   s_vsw_conformer_field",
        f"    LABELS   {combine_label}",
    ])

    # UserOuts
    lines.extend([
        f"[USEROUTS:{task}]",
        f"    USEROUTS   {conf_out},",
        f"    STRUCTOUT   {conf_out}",
    ])

    return "\n".join(lines) + "\n", "CONFGEN_COMBINED"


def _generate_combine_confsearch(
    task: str, ctx: dict[str, Any]
) -> tuple[str, str]:
    """Generate the Combine_CONFGEN block (dual ConfSearch + Combine).

    Required *ctx* keys:
      ligand_name, force_field
    """
    ligand_name: str = ctx["ligand_name"]
    force_field: str = ctx["force_field"]

    pre_out = f"PRE_{task}_RECOMBINE_OUT"

    lines = [
        # RecombineStage
        f"[STAGE:PRE_{task}]",
        "    STAGECLASS   gencodes.RecombineStage",
        f"    INPUTS   {ligand_name},",
        f"    OUTPUTS   {pre_out},",
        "    NUMOUT   njobs",
        "    OUTFORMAT   maegz",
        "    MIN_SUBJOB_STS   4000",
        "    MAX_SUBJOB_STS   40000",
        "    GENCODES   YES",
        "    OUTCOMPOUNDFIELD   s_vsw_compound_code",
        "    OUTVARIANTFIELD   s_vsw_variant",
        "    UNIQUEFIELD   s_m_title",
        # OPLS ConfSearch
        "[STAGE:OPLS_CONFGEN]",
        "    STAGECLASS   macromodel.ConfSearchStage",
        f"    INPUTS    {pre_out},",
        "    OUTPUTS   OPLS_CONFGEN_OUT,",
        "    RECOMBINE   YES",
        "    JOB_TYPE    CONFSEARCH",
        f"    FORCE_FIELD {force_field}",
        "    SOLVENT Water",
        "    CHARGES_FROM    Force field",
        "    MINI_METHOD   TNCG",
        "    CONFSEARCH_METHOD   Mixed",
        "    MAXIMUM_ITERATION   5000",
        "    OUTCONFS_PER_SEARCH 8",
        "    CUTOFF   Extended",
        # MMFF ConfSearch
        "[STAGE:MMFF_CONFGEN]",
        "    STAGECLASS   macromodel.ConfSearchStage",
        f"    INPUTS    {pre_out},",
        "    OUTPUTS   MMFF_CONFGEN_OUT,",
        "    RECOMBINE   YES",
        "    JOB_TYPE    CONFSEARCH",
        "    FORCE_FIELD MMFFs",
        "    SOLVENT Water",
        "    CHARGES_FROM    Force field",
        "    MINI_METHOD   TNCG",
        "    CONFSEARCH_METHOD   Mixed",
        "    MAXIMUM_ITERATION   5000",
        "    OUTCONFS_PER_SEARCH 8",
        "    CUTOFF   Extended",
        # CombineStage (3 inputs)
        "[STAGE:COMBINE]",
        "    STAGECLASS   combine.CombineStage",
        f"    INPUTS   {ligand_name}, OPLS_CONFGEN_OUT, MMFF_CONFGEN_OUT",
        "    OUTPUTS   CONFGEN_COMBINED,",
        "    LABELFIELD   s_vsw_conformer_field",
        "    LABELS   Original, OPLS, MMFFS",
        # UserOuts
        f"[USEROUTS:{task}]",
        "    USEROUTS   CONFGEN_COMBINED,",
        "    STRUCTOUT   CONFGEN_COMBINED",
    ]

    return "\n".join(lines) + "\n", "CONFGEN_COMBINED"


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------

_GENERATORS = {
    "ligprep": _generate_ligprep,
    "samplerings": _generate_samplerings,
    "confsearch": _generate_confsearch,
    "combine_confsearch": _generate_combine_confsearch,
}


def generate(task: str, ctx: dict[str, Any]) -> tuple[str, str]:
    """Generate INP text for a ligand-preparation *task*.

    Parameters
    ----------
    task:
        One of the keys in ``LIGPREP_TASKS``.
    ctx:
        Runtime context dictionary (ligand_name, force_field, ph, ...).

    Returns
    -------
    tuple[str, str]
        ``(stage_text, new_ligand_name)``
    """
    entry = LIGPREP_TASKS[task]
    gen_fn = _GENERATORS[entry["template"]]
    return gen_fn(task, ctx)


# ---------------------------------------------------------------------------
# Registry -- 10 tasks
# ---------------------------------------------------------------------------

LIGPREP_TASKS: dict[str, dict[str, Any]] = {
    # -- Template A: LigPrep ------------------------------------------------
    "IONIZE": {
        "template": "ligprep",
        "use_epik": "False",
        "retitle": False,
        "ionize": True,
        "max_states": None,
        "metal_binding": None,
        "max_tautomers": 4,
        "nringconfs": 3,
        "num_stereoisomers": 16,
        "max_stereoisomers": 8,
        "maxstereo": None,
    },
    "EPIK4": {
        "template": "ligprep",
        "use_epik": "YES",
        "retitle": True,
        "ionize": False,
        "max_states": 8,
        "metal_binding": "NO",
        "max_tautomers": 4,
        "nringconfs": 4,
        "num_stereoisomers": 16,
        "max_stereoisomers": 4,
        "maxstereo": None,
    },
    "EPIK32": {
        "template": "ligprep",
        "use_epik": "YES",
        "retitle": True,
        "ionize": False,
        "max_states": 64,
        "metal_binding": "YES",
        "max_tautomers": 16,
        "nringconfs": 16,
        "num_stereoisomers": 64,
        "max_stereoisomers": 32,
        "maxstereo": 32,
    },
    # -- Template B: SampleRings --------------------------------------------
    "RS1": {
        "template": "samplerings",
        "maximum_iteration": 300,
        "outconfs": 2,
    },
    "RS4": {
        "template": "samplerings",
        "maximum_iteration": 500,
        "outconfs": 8,
    },
    "RS_Fast": {
        "template": "samplerings",
        "maximum_iteration": 100,
        "outconfs": 2,
    },
    # -- Template C: ConfSearch ---------------------------------------------
    "CONFGEN": {
        "template": "confsearch",
        "maximum_iteration": 5000,
        "outconfs": 8,
        "combine_labels": "Original, OPLS",
    },
    "CONFGEN_Fast": {
        "template": "confsearch",
        "maximum_iteration": 1000,
        "outconfs": 4,
        "combine_labels": "Original, OPLS",
    },
    "MMFF_CONFGEN": {
        "template": "confsearch",
        "force_field_override": "MMFFs",
        "maximum_iteration": 5000,
        "outconfs": 8,
        "combine_labels": "Original, MMFFS",
    },
    "Combine_CONFGEN": {
        "template": "combine_confsearch",
    },
}
