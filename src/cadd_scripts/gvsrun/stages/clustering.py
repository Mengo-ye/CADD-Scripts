"""Clustering stage generators for GVSrun.

Twenty clustering tasks: 5 fingerprints x 4 similarity metrics.

All follow the same template:
  RecombineStage (PRE_CLUSTER) -> Canvas2DSimilarityStage -> UserOuts

Note: In the original Bash script, ``Linear_Tanimoto`` is the only
function that feeds ``To_Cluster`` (the RecombineStage output) into
the Canvas2DSimilarityStage. All other 19 functions pass
``${Ligand_name}`` directly to the similarity stage. This module
faithfully preserves that inconsistency.
"""

from __future__ import annotations

from typing import Any

# ---------------------------------------------------------------------------
# Fingerprint / metric matrix
# ---------------------------------------------------------------------------

FINGERPRINTS: list[str] = [
    "Linear",
    "Radial",
    "MolPrint2D",
    "Topo",
    "Dendritic",
]

METRICS: list[str] = [
    "Tanimoto",
    "Euclidean",
    "Cosine",
    "Soergel",
]


# ---------------------------------------------------------------------------
# Generator
# ---------------------------------------------------------------------------

def _generate_clustering(task: str, ctx: dict[str, Any]) -> tuple[str, str]:
    """Generate a Canvas2DSimilarityStage clustering block.

    Parameters
    ----------
    task:
        Task name of the form ``{Fingerprint}_{Metric}``.
    ctx:
        Runtime context; must include ``ligand_name``.

    Returns
    -------
    tuple[str, str]
        ``(stage_text, new_ligand_name)``
    """
    entry = CLUSTERING_TASKS[task]
    fingerprint: str = entry["fingerprint"]
    metric: str = entry["metric"]
    ligand_name: str = ctx["ligand_name"]
    output: str = entry["output"]

    # Determine the input for the similarity stage.
    # Only Linear_Tanimoto uses To_Cluster; all others use ligand_name.
    if task == "Linear_Tanimoto":
        similarity_input = "To_Cluster"
    else:
        similarity_input = ligand_name

    lines = [
        # RecombineStage
        "[STAGE:PRE_CLUSTER]",
        "    STAGECLASS  gencodes.RecombineStage",
        f"    INPUTS  {ligand_name},",
        "    NUMOUT  preserve",
        "    PRESERVE_NJOBS  TRUE",
        "    SKIP_BAD_LIGANDS    False",
        "    SKIP_RECEPTOR   TRUE",
        "    OUTPUTS     To_Cluster,",
        # Canvas2DSimilarityStage
        f"[STAGE:{task}]",
        "    STAGECLASS  canvas.Canvas2DSimilarityStage",
        f"    FINGERPRINT_TYPE    {fingerprint}",
        f"    SIMILARITY_METRIC    {metric}",
        "    ATOM_TYPING_SCHEME    9",
        f"    INPUTS    {similarity_input},",
        f"    OUTPUTS    {output},",
        # UserOuts
        f"[USEROUTS:{task}]",
        f"    USEROUTS    {output},",
        f"    STRUCTOUT    {output}",
    ]

    return "\n".join(lines) + "\n", output


def generate(task: str, ctx: dict[str, Any]) -> tuple[str, str]:
    """Generate INP text for a clustering *task*.

    Parameters
    ----------
    task:
        One of the keys in ``CLUSTERING_TASKS``.
    ctx:
        Runtime context dictionary (must include ``ligand_name``).

    Returns
    -------
    tuple[str, str]
        ``(stage_text, new_ligand_name)``
    """
    return _generate_clustering(task, ctx)


# ---------------------------------------------------------------------------
# Registry -- 20 tasks (5 fingerprints x 4 metrics), built programmatically
# ---------------------------------------------------------------------------

CLUSTERING_TASKS: dict[str, dict[str, Any]] = {}

for _fp in FINGERPRINTS:
    for _metric in METRICS:
        _name = f"{_fp}_{_metric}"
        CLUSTERING_TASKS[_name] = {
            "template": "clustering",
            "fingerprint": _fp,
            "metric": _metric,
            "output": f"{_name}_Cluster_OUT",
        }
