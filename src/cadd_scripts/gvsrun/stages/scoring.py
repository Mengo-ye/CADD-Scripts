"""Advanced scoring stage generators for GVSrun.

Seven unique scoring tasks -- each has its own pipeline structure:

A. IFT          -- SP docking + PullStage + Prime REAL_MIN
B. MMGBSA_EN    -- PullStage + MMGBSAStage (no refinement)
C. MMGBSA_MIN   -- PullStage + Prime REAL_MIN + MMGBSAStage
D. MMGBSA_OPT   -- PullStage + Prime SIDE_PRED + MMGBSAStage
E. QMMM         -- PullStage + QSiteStage
F. QM_redock    -- PullStage + QSite + RecombineStage + SP docking (LIG_MAECHARGES)
G. CD           -- Prime COVALENT_DOCKING
"""

from __future__ import annotations

from typing import Any


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _parse_num_or_percentage(value: str) -> str:
    """Convert a keep-number string to the appropriate INP directive.

    ``"5%"`` -> ``"PERCENT_TO_KEEP   5"``
    ``"500"`` -> ``"NUM_TO_KEEP   500"``
    """
    if value.endswith("%"):
        return f"PERCENT_TO_KEEP   {value.rstrip('%')}"
    return f"NUM_TO_KEEP   {value}"


# ---------------------------------------------------------------------------
# A. IFT -- SP docking + PullStage + Prime REAL_MIN
# ---------------------------------------------------------------------------

def _generate_ift(task: str, ctx: dict[str, Any]) -> tuple[str, str]:
    """Induce-Fit Truncated: SP docking -> Pull -> Prime REAL_MIN."""
    ligand_name: str = ctx["ligand_name"]
    force_field: str = ctx["force_field"]
    dock_out_conf: int = ctx["dock_out_conf"]
    docking_out_num: str = ctx["docking_out_num"]
    set_pull_num: str = ctx["set_pull_num"]
    strain_energy: str = ctx["strain_energy"]

    keep_num = _parse_num_or_percentage(docking_out_num)
    pull_num = _parse_num_or_percentage(set_pull_num)

    lines = [
        # RecombineStage for SP docking
        f"[STAGE:{task}_PRE_DOCK_SP]",
        "    STAGECLASS   gencodes.RecombineStage",
        f"    INPUTS   {ligand_name},",
        "    OUTPUTS   DOCK_SP_INPUT,",
        "    NUMOUT   njobs",
        "    OUTFORMAT   maegz",
        "    MIN_SUBJOB_STS   300",
        "    MAX_SUBJOB_STS   5000",
        "    GENCODES   YES",
        "    OUTCOMPOUNDFIELD   s_vsw_compound_code",
        "    OUTVARIANTFIELD   s_vsw_variant",
        "    UNIQUEFIELD   NONE",
        # SP Docking
        f"[STAGE:{task}_DOCK_SP]",
        "    STAGECLASS   glide.DockingStage",
        "    INPUTS   DOCK_SP_INPUT, GRID",
        f"    OUTPUTS   {task}_SP_OUT,",
        "    RECOMBINE   NO",
        "    PRECISION   SP",
        "    REWARD_INTRA_HBONDS YES",
        "    HBOND_ACCEP_HALO    YES",
        "    UNIQUEFIELD   s_vsw_compound_code",
        f"    {keep_num}",
        f"    FORCEFIELD  {force_field}",
        "    DOCKING_METHOD   confgen",
        f"    POSES_PER_LIG   {dock_out_conf}",
        "    WRITE_XP_DESC   NO",
        "    NENHANCED_SAMPLING   1",
        "    BEST_BY_TITLE   NO",
        "    LIG_VSCALE   0.25",
        "    LIG_CCUT   0.15",
        "    MAXATOMS   500",
        "    MAXROTBONDS   50",
        "    AMIDE_MODE   penal",
        "    POSE_OUTTYPE   LIB",
        "    POSTDOCK   YES",
        f"    POSTDOCKSTRAIN   {strain_energy}",
        "    COMPRESS_POSES   YES",
        "    EPIK_PENALTIES   YES",
        "    FORCEPLANAR   NO",
        # PullStage
        f"[STAGE:{task}_PULL_IFT]",
        "    STAGECLASS   pull.PullStage",
        f"    INPUTS   {task}_SP_OUT, {ligand_name}",
        "    OUTPUTS   TO_INDUCE_FIT,",
        f"    {pull_num}",
        "    UNIQUEFIELD   s_m_title",
        # Prime REAL_MIN
        f"[STAGE:{task}_INDUCE_FIT]",
        "    STAGECLASS  prime.PrimeStage",
        "    INPUTS  TO_INDUCE_FIT",
        "    OUTPUTS INDUCE_FIT_OUT",
        "    PRIME_TYPE  REAL_MIN",
        f"    OPLS_VERSION    {force_field}",
        "    USE_RANDOM_SEED YES",
        "    NUMBER_OF_PASSES    1",
        "    MINIM_NITER 5",
        "    MINIM_RMSG  0.01",
        # UserOuts
        f"[USEROUTS:{task}]",
        "    USEROUTS   INDUCE_FIT_OUT,",
        "    STRUCTOUT   INDUCE_FIT_OUT",
    ]

    return "\n".join(lines) + "\n", "INDUCE_FIT_OUT"


# ---------------------------------------------------------------------------
# B. MMGBSA_EN -- PullStage + MMGBSAStage (no refinement)
# ---------------------------------------------------------------------------

def _generate_mmgbsa_en(task: str, ctx: dict[str, Any]) -> tuple[str, str]:
    """MM-GBSA energy: Pull -> MMGBSAStage."""
    ligand_name: str = ctx["ligand_name"]
    set_pull_num: str = ctx["set_pull_num"]

    pull_num = _parse_num_or_percentage(set_pull_num)

    lines = [
        # PullStage
        "[STAGE:PULL_SELF]",
        "    STAGECLASS   pull.PullStage",
        f"    INPUTS   {ligand_name}, {ligand_name}",
        "    OUTPUTS   PULL_SELF_OUT,",
        f"    {pull_num}",
        "    UNIQUEFIELD   s_m_title",
        # MMGBSAStage
        "[STAGE:MMGBSA_EN]",
        "    STAGECLASS  prime.MMGBSAStage",
        f"    INPUTS  {ligand_name},",
        "    OUTPUTS MMGBSA_EN_OUT",
        # UserOuts
        f"[USEROUTS:{task}]",
        "    USEROUTS   MMGBSA_EN_OUT,",
        "    STRUCTOUT   MMGBSA_EN_OUT",
    ]

    return "\n".join(lines) + "\n", "MMGBSA_EN_OUT"


# ---------------------------------------------------------------------------
# C. MMGBSA_MIN -- PullStage + Prime REAL_MIN + MMGBSAStage
# ---------------------------------------------------------------------------

def _generate_mmgbsa_min(task: str, ctx: dict[str, Any]) -> tuple[str, str]:
    """MM-GBSA minimisation: Pull -> Prime REAL_MIN -> MMGBSAStage."""
    ligand_name: str = ctx["ligand_name"]
    set_pull_num: str = ctx["set_pull_num"]

    pull_num = _parse_num_or_percentage(set_pull_num)

    lines = [
        # PullStage
        "[STAGE:PULL_SELF]",
        "    STAGECLASS   pull.PullStage",
        f"    INPUTS   {ligand_name}, {ligand_name}",
        "    OUTPUTS   PULL_SELF_OUT,",
        f"    {pull_num}",
        "    UNIQUEFIELD   s_m_title",
        # Prime REAL_MIN
        "[STAGE:MMGBSA_MIN]",
        "    STAGECLASS  prime.PrimeStage",
        f"    INPUTS  {ligand_name},",
        "    OUTPUTS MMGBSA_MIN_OUT",
        "    PRIME_TYPE  REAL_MIN",
        "    USE_RANDOM_SEED YES",
        '    LIGAND asl = "ligand"',
        "    SELECT all",
        "    NUMBER_OF_PASSES    2",
        "    MINIM_NITER 2",
        "    MINIM_RMSG  0.01",
        # MMGBSAStage
        "[STAGE:MMGBSA_EN]",
        "    STAGECLASS  prime.MMGBSAStage",
        "    INPUTS  MMGBSA_MIN_OUT,",
        "    OUTPUTS MMGBSA_EN_OUT",
        # UserOuts
        f"[USEROUTS:{task}]",
        "    USEROUTS   MMGBSA_MIN_OUT,",
        "    STRUCTOUT   MMGBSA_MIN_OUT",
    ]

    return "\n".join(lines) + "\n", "MMGBSA_MIN_OUT"


# ---------------------------------------------------------------------------
# D. MMGBSA_OPT -- PullStage + Prime SIDE_PRED + MMGBSAStage
# ---------------------------------------------------------------------------

def _generate_mmgbsa_opt(task: str, ctx: dict[str, Any]) -> tuple[str, str]:
    """MM-GBSA side-chain optimisation: Pull -> Prime SIDE_PRED -> MMGBSA.

    Note: The original Bash script outputs ``MMGBSA_MIN_OUT`` in USEROUTS
    (likely a copy-paste artefact). This is faithfully preserved.
    """
    ligand_name: str = ctx["ligand_name"]
    set_pull_num: str = ctx["set_pull_num"]

    pull_num = _parse_num_or_percentage(set_pull_num)

    lines = [
        # PullStage
        "[STAGE:PULL_SELF]",
        "    STAGECLASS   pull.PullStage",
        f"    INPUTS   {ligand_name}, {ligand_name}",
        "    OUTPUTS   PULL_SELF_OUT,",
        f"    {pull_num}",
        "    UNIQUEFIELD   s_m_title",
        # Prime SIDE_PRED
        "[STAGE:MMGBSA_OPT]",
        "    STAGECLASS  prime.PrimeStage",
        f"    INPUTS  {ligand_name},",
        "    OUTPUTS MMGBSA_OPT_OUT",
        "    PRIME_TYPE  SIDE_PRED",
        '    LIGAND asl = "ligand"',
        "    SELECT all",
        "    USE_RANDOM_SEED YES",
        "    NUMBER_OF_PASSES    2",
        "    NITER_SIDE  8",
        # MMGBSAStage
        "[STAGE:MMGBSA_EN]",
        "    STAGECLASS  prime.MMGBSAStage",
        "    INPUTS  MMGBSA_OPT_OUT,",
        "    OUTPUTS MMGBSA_EN_OUT",
        # UserOuts -- original script uses MMGBSA_MIN_OUT here (see note)
        f"[USEROUTS:{task}]",
        "    USEROUTS   MMGBSA_MIN_OUT,",
        "    STRUCTOUT   MMGBSA_MIN_OUT",
    ]

    # Original script sets Ligand_name="MMGBSA_MIN_OUT"
    return "\n".join(lines) + "\n", "MMGBSA_MIN_OUT"


# ---------------------------------------------------------------------------
# E. QMMM -- PullStage + QSiteStage
# ---------------------------------------------------------------------------

def _generate_qmmm(task: str, ctx: dict[str, Any]) -> tuple[str, str]:
    """QM/MM optimisation: Pull -> QSiteStage."""
    ligand_name: str = ctx["ligand_name"]
    set_pull_num: str = ctx["set_pull_num"]
    dft_name: str = ctx["dft_name"]
    basis_name: str = ctx["basis_name"]
    force_field: str = ctx["force_field"]

    pull_num = _parse_num_or_percentage(set_pull_num)

    lines = [
        # PullStage
        "[STAGE:PULL_SELF]",
        "    STAGECLASS   pull.PullStage",
        f"    INPUTS   {ligand_name}, {ligand_name}",
        "    OUTPUTS   PULL_SELF_OUT,",
        f"    {pull_num}",
        "    UNIQUEFIELD   s_m_title",
        # QSiteStage
        "[STAGE:QMMM]",
        "    STAGECLASS  qsite.QSiteStage",
        "    INPUTS   PULL_SELF_OUT",
        "    OUTPUTS   QMMM_OUT,",
        "    OUTPUT_LIGS_ONLY    False",
        "    IGNORE_RECEP    False",
        f"    QM_DFTNAME  {dft_name}",
        f"    QM_BASIS    {basis_name}",
        f"    MM_FORCEFIELD   {force_field}",
        # UserOuts
        f"[USEROUTS:{task}]",
        "    USEROUTS   QMMM_OUT,",
        "    STRUCTOUT   QMMM_OUT",
    ]

    return "\n".join(lines) + "\n", "QMMM_OUT"


# ---------------------------------------------------------------------------
# F. QM_redock -- QSite + RecombineStage + SP docking with LIG_MAECHARGES
# ---------------------------------------------------------------------------

def _generate_qm_redock(task: str, ctx: dict[str, Any]) -> tuple[str, str]:
    """QM-optimised re-docking: Pull -> QSite -> Recombine -> SP (MAE charges)."""
    ligand_name: str = ctx["ligand_name"]
    set_pull_num: str = ctx["set_pull_num"]
    dft_name: str = ctx["dft_name"]
    basis_name: str = ctx["basis_name"]
    force_field: str = ctx["force_field"]
    scaling_vdw: str = ctx["scaling_vdw"]
    strain_energy: str = ctx["strain_energy"]

    pull_num = _parse_num_or_percentage(set_pull_num)

    lines = [
        # PullStage
        f"[STAGE:{task}_PULL_SELF]",
        "    STAGECLASS   pull.PullStage",
        f"    INPUTS   {ligand_name}, {ligand_name}",
        "    OUTPUTS   PULL_SELF_OUT,",
        f"    {pull_num}",
        "    UNIQUEFIELD   s_m_title",
        # QSiteStage (OUTPUT_LIGS_ONLY = True for redock)
        f"[STAGE:{task}_QMMM]",
        "    STAGECLASS  qsite.QSiteStage",
        "    INPUTS   PULL_SELF_OUT",
        "    OUTPUTS   QMMM_OUT,",
        "    OUTPUT_LIGS_ONLY    True",
        "    IGNORE_RECEP    False",
        f"    QM_DFTNAME  {dft_name}",
        f"    QM_BASIS    {basis_name}",
        f"    MM_FORCEFIELD   {force_field}",
        # RecombineStage
        f"[STAGE:{task}_PRE_DOCK_SP]",
        "    STAGECLASS   gencodes.RecombineStage",
        "    INPUTS   QMMM_OUT,",
        "    OUTPUTS   DOCK_QMSP_INPUT,",
        "    NUMOUT   njobs",
        "    OUTFORMAT   maegz",
        "    MIN_SUBJOB_STS   300",
        "    MAX_SUBJOB_STS   5000",
        "    GENCODES   YES",
        "    OUTCOMPOUNDFIELD   s_vsw_compound_code",
        "    OUTVARIANTFIELD   s_vsw_variant",
        "    UNIQUEFIELD   NONE",
        # SP Docking with LIG_MAECHARGES
        f"[STAGE:{task}_DOCK_SP]",
        "    STAGECLASS   glide.DockingStage",
        "    INPUTS   DOCK_QMSP_INPUT, GRID",
        "    OUTPUTS   QMSP_OUT,",
        "    LIG_MAECHARGES  YES",
        "    RECOMBINE   NO",
        "    PRECISION   SP",
        "    REWARD_INTRA_HBONDS YES",
        "    HBOND_ACCEP_HALO    YES",
        "    UNIQUEFIELD   s_vsw_compound_code",
        "    PERCENT_TO_KEEP 100",
        f"    FORCEFIELD  {force_field}",
        "    DOCKING_METHOD   confgen",
        "    POSES_PER_LIG   5",
        "    WRITE_XP_DESC   NO",
        "    NENHANCED_SAMPLING   1",
        "    BEST_BY_TITLE   NO",
        f"    LIG_VSCALE   {scaling_vdw}",
        "    LIG_CCUT   0.15",
        "    MAXATOMS   500",
        "    MAXROTBONDS   50",
        "    AMIDE_MODE   penal",
        "    POSE_OUTTYPE   LIB",
        "    POSTDOCK   YES",
        f"    POSTDOCKSTRAIN   {strain_energy}",
        "    COMPRESS_POSES   YES",
        "    EPIK_PENALTIES   YES",
        "    FORCEPLANAR   NO",
        # UserOuts
        f"[USEROUTS:{task}]",
        "    USEROUTS   QMSP_OUT,",
        "    STRUCTOUT   QMSP_OUT",
    ]

    return "\n".join(lines) + "\n", "QMSP_OUT"


# ---------------------------------------------------------------------------
# G. CD -- Prime COVALENT_DOCKING
# ---------------------------------------------------------------------------

def _generate_cd(task: str, ctx: dict[str, Any]) -> tuple[str, str]:
    """Covalent docking via Prime."""
    ligand_name: str = ctx["ligand_name"]
    force_field: str = ctx["force_field"]

    lines = [
        "[STAGE:GEN_COMPLEX]",
        "    STAGECLASS  prime.PrimeStage",
        "    PRIME_TYPE  COVALENT_DOCKING",
        f"    INPUTS   {ligand_name},",
        "    OUTPUTS     COV_COMPLEX_OUT,",
        f"    OPLS_VERSION    {force_field}",
        "    USE_RANDOM_SEED YES",
        "    NUMBER_OF_PASSES    3",
        "    MINIM_NITER 6",
        "    MINIM_RMSG  0.01",
        # UserOuts
        f"[USEROUTS:{task}]",
        "    USEROUTS   COV_COMPLEX_OUT,",
        "    STRUCTOUT   COV_COMPLEX_OUT",
    ]

    return "\n".join(lines) + "\n", "COV_COMPLEX_OUT"


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------

_GENERATORS: dict[str, Any] = {
    "IFT": _generate_ift,
    "MMGBSA_EN": _generate_mmgbsa_en,
    "MMGBSA_MIN": _generate_mmgbsa_min,
    "MMGBSA_OPT": _generate_mmgbsa_opt,
    "QMMM": _generate_qmmm,
    "QM_redock": _generate_qm_redock,
    "CD": _generate_cd,
}


def generate(task: str, ctx: dict[str, Any]) -> tuple[str, str]:
    """Generate INP text for a scoring *task*.

    Parameters
    ----------
    task:
        One of the keys in ``SCORING_TASKS``.
    ctx:
        Runtime context dictionary.  Required keys vary per task:

        - All tasks need ``ligand_name``.
        - IFT needs ``force_field``, ``dock_out_conf``, ``docking_out_num``,
          ``set_pull_num``, ``strain_energy``.
        - MMGBSA_EN needs ``set_pull_num``.
        - MMGBSA_MIN needs ``set_pull_num``.
        - MMGBSA_OPT needs ``set_pull_num``.
        - QMMM needs ``set_pull_num``, ``dft_name``, ``basis_name``,
          ``force_field``.
        - QM_redock needs ``set_pull_num``, ``dft_name``, ``basis_name``,
          ``force_field``, ``scaling_vdw``, ``strain_energy``.
        - CD needs ``force_field``.

    Returns
    -------
    tuple[str, str]
        ``(stage_text, new_ligand_name)``
    """
    gen_fn = _GENERATORS[task]
    return gen_fn(task, ctx)


# ---------------------------------------------------------------------------
# Registry -- 7 tasks
# ---------------------------------------------------------------------------

SCORING_TASKS: dict[str, dict[str, Any]] = {
    "IFT": {
        "template": "IFT",
        "description": "Induced Fit Truncated: SP docking + PullStage + Prime REAL_MIN",
    },
    "MMGBSA_EN": {
        "template": "MMGBSA_EN",
        "description": "MM-GBSA energy calculation (no refinement)",
    },
    "MMGBSA_MIN": {
        "template": "MMGBSA_MIN",
        "description": "MM-GBSA with Prime REAL_MIN minimisation",
    },
    "MMGBSA_OPT": {
        "template": "MMGBSA_OPT",
        "description": "MM-GBSA with Prime SIDE_PRED optimisation",
    },
    "QMMM": {
        "template": "QMMM",
        "description": "QM/MM optimisation via QSite",
    },
    "QM_redock": {
        "template": "QM_redock",
        "description": "QM-optimised re-docking with MAE charges",
    },
    "CD": {
        "template": "CD",
        "description": "Covalent docking via Prime",
    },
}
