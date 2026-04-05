"""Predefined running modes for the GVSrun virtual screening pipeline.

Every mode name maps to a ``+``-delimited pipeline string.  The mapping is
taken verbatim from the ``Parse_Running_Mode`` function in the original
GVSrun Bash script (lines 350-385).
"""

from __future__ import annotations

PREDEFINED_MODES: dict[str, str] = {
    "Fast": "HTVS_Normal+SP_Normal",
    "Normal": "RDL+HTVS_Normal+QIKPROP+R5R+SP_ExtensionA",
    "Prep_Normal": "No_Dup+RDL+IONIZE+HTVS_Normal+QIKPROP+R5R+SP_ExtensionA",
    "Normal_MMGBSA": "RDL+HTVS_Normal+QIKPROP+R5R+SP_ExtensionA+MMGBSA_EN",
    "Reference": "HTVS_REF+SP_REF+QIKPROP+R5R",
    "Induce_Fit_Screening": "IFT_pre+IFT",
    "Cov_Screening": "R+HTVS_Normal+SP_ExtensionA+SP_Enhanced",
    "QM_Screening": (
        "RDL+HTVS_Normal+QIKPROP+R5R+SP_ExtensionA+QM_redock+RMSD"
    ),
    "Shape_Screening": "localShape+SP_local",
    "LocalShape_Screening": "PhaseShape+SP_local",
    "Advance_Shape_Screening": "HTVS_Shape+SP_Shape",
    "Local": "SP_local+MMGBSA_OPT",
    "Advance": "HTVS_Normal+SP_ExtensionA+SP_Enhanced",
    "GeminiMol_Advance": (
        "No_Dup+RDL+EPIK4+HTVS_Normal+QIKPROP+R5R+SP_ExtensionA+SP_Enhanced"
    ),
}


def resolve_pipeline(running_mode: str) -> str:
    """Convert a running-mode name to a pipeline string.

    If *running_mode* matches a key in :data:`PREDEFINED_MODES` the
    corresponding pipeline string is returned.  Otherwise the value is
    assumed to be a custom pipeline (e.g. ``"EDL+R+HTVS+CD"``) and is
    returned as-is.
    """
    if running_mode in PREDEFINED_MODES:
        return PREDEFINED_MODES[running_mode]
    # Custom / user-defined mode -- pass through unchanged.
    return running_mode
