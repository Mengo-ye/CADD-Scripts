"""Pipeline stage registry and unified dispatcher for GVSrun.

Each task name maps to (category, entry) where category determines the dispatcher:
- 'filter' / 'no_dup' / 'qikprop' / 'mw' -> filtering.generate_filter(task, config, ligand_name)
- 'docking' -> docking.generate_docking(task, config, ligand_name)
- 'ligprep' / 'samplerings' / 'confsearch' / 'combine_confsearch' -> ligprep.generate(task, ctx)
- 'clustering' -> clustering.generate(task, ctx)
- 'ift' / 'mmgbsa_en' / 'mmgbsa_min' / 'mmgbsa_opt' / 'qmmm' / 'qm_redock' / 'cd' -> scoring.generate(task, ctx)
- 'rmsd' / 'phase_shape' / 'local_shape' -> utility.generate(task, ctx)
"""
from __future__ import annotations

from typing import Any

from cadd_scripts.gvsrun.stages.clustering import CLUSTERING_TASKS
from cadd_scripts.gvsrun.stages.docking import DOCKING_TASKS, generate_docking
from cadd_scripts.gvsrun.stages.filtering import FILTER_TASKS, generate_filter
from cadd_scripts.gvsrun.stages.ligprep import LIGPREP_TASKS
from cadd_scripts.gvsrun.stages.scoring import SCORING_TASKS
from cadd_scripts.gvsrun.stages.utility import UTILITY_TASKS

from cadd_scripts.gvsrun.stages import clustering as _clustering
from cadd_scripts.gvsrun.stages import ligprep as _ligprep
from cadd_scripts.gvsrun.stages import scoring as _scoring
from cadd_scripts.gvsrun.stages import utility as _utility


# Unified registry: task_name -> (source, entry)
# "source" determines which module handles the task
TASK_REGISTRY: dict[str, tuple[str, dict[str, Any]]] = {}

for _name, _entry in FILTER_TASKS.items():
    TASK_REGISTRY[_name] = ("filtering", _entry)
for _name, _entry in DOCKING_TASKS.items():
    TASK_REGISTRY[_name] = ("docking", _entry)
for _name, _entry in LIGPREP_TASKS.items():
    TASK_REGISTRY[_name] = ("ligprep", _entry)
for _name, _entry in CLUSTERING_TASKS.items():
    TASK_REGISTRY[_name] = ("clustering", _entry)
for _name, _entry in SCORING_TASKS.items():
    TASK_REGISTRY[_name] = ("scoring", _entry)
for _name, _entry in UTILITY_TASKS.items():
    TASK_REGISTRY[_name] = ("utility", _entry)


def _make_ctx(config: Any, ligand_name: str) -> dict[str, Any]:
    """Build a context dict for ctx-based generators.

    Exposes commonly-needed config fields plus ligand_name.
    """
    return {
        "config": config,
        "ligand_name": ligand_name,
        "force_field": config.force_field,
        "coarse_ff": config.coarse_ff,
        "ph": config.ph,
        "scaling_vdw": config.scaling_vdw,
        "strain_energy": config.strain_energy,
        "dock_out_conf": config.dock_out_conf,
        "htvs_out_num": config.htvs_out_num,
        "docking_out_num": config.docking_out_num,
        "set_pull_num": config.set_pull_num,
        "qm_set": config.qm_set,
        "mw_range": config.mw_range,
        "covalent_attach_residue": config.covalent_attach_residue,
        "reference_ligand": config.reference_ligand,
        "shape_screen": config.shape_screen,
        "pipeline": config.pipeline,
        "njobs": config.njobs,
        "prime_njobs": config.prime_njobs,
        "glide_njobs": config.glide_njobs,
        "ligprep_njobs": config.ligprep_njobs,
        "qikprop_njobs": config.qikprop_njobs,
        "macromodel_njobs": config.macromodel_njobs,
        "dft_name": config.qm_dft_name,
        "basis_name": config.qm_basis,
        "database": config.database,
        "database_location": str(config.database_path) if config.database_path else "",
        "keep_num": config.shape_screen_array[0] if config.shape_screen else "10000",
        "shape_sample_method": config.shape_screen_array[1] if config.shape_screen else "rapid",
        "max_confs": config.shape_screen_array[2] if config.shape_screen else "100",
        "schrodinger": str(config.require_schrodinger()) if config.schrodinger else "",
        "host": config.host,
        "to_rmsd": config.to_rmsd,
    }


def dispatch(task_name: str, config: Any, ligand_name: str) -> tuple[str, str]:
    """Dispatch task to its generator. Returns (inp_block, new_ligand_name)."""
    if task_name not in TASK_REGISTRY:
        raise ValueError(f"Unknown pipeline task: {task_name}")

    source, _entry = TASK_REGISTRY[task_name]

    # Style A: (task_name, config, ligand_name) signature
    if source == "filtering":
        return generate_filter(task_name, config, ligand_name)
    if source == "docking":
        return generate_docking(task_name, config, ligand_name)

    # Style B: (task, ctx) signature with ctx dict
    ctx = _make_ctx(config, ligand_name)
    if source == "ligprep":
        return _ligprep.generate(task_name, ctx)
    if source == "clustering":
        return _clustering.generate(task_name, ctx)
    if source == "scoring":
        return _scoring.generate(task_name, ctx)
    if source == "utility":
        return _utility.generate(task_name, ctx)

    raise RuntimeError(f"No dispatcher for source: {source}")


__all__ = [
    "TASK_REGISTRY",
    "dispatch",
    "CLUSTERING_TASKS",
    "DOCKING_TASKS",
    "FILTER_TASKS",
    "LIGPREP_TASKS",
    "SCORING_TASKS",
    "UTILITY_TASKS",
]
