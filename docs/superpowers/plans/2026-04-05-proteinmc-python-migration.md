# ProteinMC Python Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Migrate the ProteinMC Bash script (367 lines) to a pip-installable Python 3 package with click CLI, preserving all functionality (Prime + Rosetta).

**Architecture:** Python package `cadd_scripts` with `proteinmc` subpackage. Click CLI provides `cadd proteinmc prime` and `cadd proteinmc rosetta` subcommands. Config via dataclass, external tools called via `subprocess`.

**Tech Stack:** Python >=3.10, click, hatchling (build), subprocess/pathlib (stdlib)

---

## File Map

| File | Responsibility |
|------|---------------|
| `pyproject.toml` | Create: Package metadata, dependencies, entry point |
| `src/cadd_scripts/__init__.py` | Create: Package version |
| `src/cadd_scripts/cli.py` | Create: Click CLI group + proteinmc subcommands |
| `src/cadd_scripts/proteinmc/__init__.py` | Create: Subpackage init |
| `src/cadd_scripts/proteinmc/config.py` | Create: ProteinMCConfig dataclass |
| `src/cadd_scripts/proteinmc/utils.py` | Create: Shared helpers (run_cmd, resolve_input, derive_job_name) |
| `src/cadd_scripts/proteinmc/prime.py` | Create: All Schrödinger Prime job logic |
| `src/cadd_scripts/proteinmc/rosetta.py` | Create: All Rosetta job logic |

---

### Task 1: Project scaffolding and packaging

**Files:**
- Create: `pyproject.toml`
- Create: `src/cadd_scripts/__init__.py`
- Create: `src/cadd_scripts/proteinmc/__init__.py`

- [ ] **Step 1: Create directory structure**

```bash
mkdir -p src/cadd_scripts/proteinmc
```

- [ ] **Step 2: Write `pyproject.toml`**

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "cadd-scripts"
version = "2.0.0"
description = "CADD automation scripts for virtual screening, docking, and protein refinement"
requires-python = ">=3.10"
dependencies = ["click"]

[project.scripts]
cadd = "cadd_scripts.cli:main"
```

- [ ] **Step 3: Write `src/cadd_scripts/__init__.py`**

```python
"""CADD-Scripts: Computer-Aided Drug Design automation tools."""

__version__ = "2.0.0"
```

- [ ] **Step 4: Write `src/cadd_scripts/proteinmc/__init__.py`**

```python
"""ProteinMC: Protein refinement and Monte Carlo simulations."""
```

- [ ] **Step 5: Verify package installs**

```bash
pip install -e .
python -c "import cadd_scripts; print(cadd_scripts.__version__)"
```

Expected: prints `2.0.0`

---

### Task 2: Configuration dataclass

**Files:**
- Create: `src/cadd_scripts/proteinmc/config.py`

- [ ] **Step 1: Write `config.py`**

```python
from dataclasses import dataclass, field
from pathlib import Path
import os


@dataclass
class ProteinMCConfig:
    """Configuration for ProteinMC jobs."""

    input_file: Path
    job_type: str = "MC"
    cpu_host: str = "CPU"
    njobs: int = 30
    force_field: str = "S-OPLS"
    rosetta_score: str = "ref2015_cart"
    mc_steps: int = 50
    output_num: int = 3
    random_seed: bool = True
    use_membrane: bool = False
    refine_range: str = "all"
    constraints_asl: str | None = None
    constraints_force: float = 10.0
    constraints_tolerance: float = 0.0
    comp1: str = "A"
    comp2: str = "B"
    schrodinger: Path = field(
        default_factory=lambda: Path(os.environ.get("SCHRODINGER", ""))
    )
    rosetta_app: Path | None = field(
        default_factory=lambda: Path(p) if (p := os.environ.get("rosetta_app")) else None
    )
    rosetta_db: Path | None = field(
        default_factory=lambda: Path(p) if (p := os.environ.get("rosetta_db")) else None
    )
    rosetta_version: str = "mpi"

    @property
    def job_name(self) -> str:
        return f"{self.input_file.stem}_{self.job_type}"

    @property
    def wait_cmd(self) -> list[str]:
        if self.cpu_host in ("localhost", "local"):
            return ["-WAIT"]
        return []
```

- [ ] **Step 2: Verify import**

```bash
python -c "from cadd_scripts.proteinmc.config import ProteinMCConfig; print('OK')"
```

Expected: `OK`

---

### Task 3: Utility functions

**Files:**
- Create: `src/cadd_scripts/proteinmc/utils.py`

- [ ] **Step 1: Write `utils.py`**

```python
import subprocess
from pathlib import Path


def run_cmd(cmd: list[str], check: bool = True) -> subprocess.CompletedProcess:
    """Run a subprocess command, printing it for transparency."""
    print(f"Running: {' '.join(cmd)}")
    return subprocess.run(cmd, check=check)


def resolve_input(
    input_path: Path, schrodinger: Path, job_name: str
) -> tuple[Path, bool]:
    """Normalize input to .mae format.

    Returns (resolved_path, is_mpi_mode).
    - .mae/.maegz -> use directly, mpi_mode=False
    - .pdb -> structconvert to .mae, mpi_mode=True
    - directory -> structcat to merge PDBs, mpi_mode=False
    """
    suffix = input_path.suffix.lstrip(".")
    if suffix in ("mae", "maegz"):
        return input_path, False
    elif suffix == "pdb":
        out_mae = Path(f"{input_path.stem}.mae")
        run_cmd([
            str(schrodinger / "utilities" / "structconvert"),
            str(input_path),
            str(out_mae),
        ])
        return out_mae.resolve(), True
    elif input_path.is_dir():
        out_mae = Path(f"{job_name}_in.mae")
        run_cmd([
            str(schrodinger / "utilities" / "structcat"),
            "-ipdb",
            *[str(p) for p in sorted(input_path.glob("*.pdb"))],
            "-omae",
            str(out_mae),
        ])
        return out_mae.resolve(), False
    else:
        raise ValueError(f"Unsupported input format: {input_path}")
```

- [ ] **Step 2: Verify import**

```bash
python -c "from cadd_scripts.proteinmc.utils import run_cmd, resolve_input; print('OK')"
```

Expected: `OK`

---

### Task 4: Prime module

**Files:**
- Create: `src/cadd_scripts/proteinmc/prime.py`

Reference: `ProteinMC` lines 134-217 (the `PrimeMC` function)

- [ ] **Step 1: Write `prime.py`**

```python
from pathlib import Path

from .config import ProteinMCConfig
from .utils import resolve_input, run_cmd


def _generate_mc_inp(config: ProteinMCConfig, job_name: str) -> Path:
    """Generate .inp file for Prime MC refinement."""
    lines = [
        f"STRUCT_FILE\t{config.input_file}",
        "JOB_TYPE\tREFINE",
        "PRIME_TYPE\tMC",
        f"SELECT\tasl={config.refine_range}",
        f"NSTEPS\t{config.mc_steps}",
        "PROB_SIDEMC\t0.000000",
        "PROB_RIGIDMC\t0.000000",
        "PROB_HMC\t1.000000",
        "TEMP_HMC\t900.000000",
        "FIND_BEST_STRUCTURE\tyes",
        f"NUM_OUTPUT_STRUCT\t{config.output_num}",
        "USE_CRYSTAL_SYMMETRY\tno",
        f"USE_RANDOM_SEED\t{'yes' if config.random_seed else 'no'}",
        "SEED\t0",
        f"OPLS_VERSION {config.force_field}",
        "EXT_DIEL\t80.00",
        f"USE_MEMBRANE\t{'yes' if config.use_membrane else 'no'}",
    ]
    if config.constraints_asl:
        lines.append(
            f"CONSTRAINT_0 asl={config.constraints_asl};"
            f"{config.constraints_force};{config.constraints_tolerance}"
        )
    inp_path = Path(f"{job_name}.inp")
    inp_path.write_text("\n".join(lines) + "\n")
    return inp_path


def _generate_side_pred_inp(
    config: ProteinMCConfig, job_name: str, backbone_sampling: bool
) -> Path:
    """Generate .inp file for Prime SIDE_PRED refinement."""
    lines = [
        f"STRUCT_FILE\t{config.input_file}",
        "JOB_TYPE\tREFINE",
        "PRIME_TYPE\tSIDE_PRED",
        f"SELECT\tasl={config.refine_range}",
        f"NUM_SC_OUTPUT_STRUCT\t{config.output_num}",
        "USE_CRYSTAL_SYMMETRY\tno",
        f"USE_RANDOM_SEED\t{'yes' if config.random_seed else 'no'}",
        "SEED\t0",
        f"OPLS_VERSION {config.force_field}",
        "EXT_DIEL\t80.00",
        f"USE_MEMBRANE\t{'yes' if config.use_membrane else 'no'}",
        f"SAMPLE_BACKBONE {'yes' if backbone_sampling else 'no'}",
        "BACKBONE_LEN 3",
    ]
    if config.constraints_asl:
        lines.append(
            f"CONSTRAINT_0 asl={config.constraints_asl};"
            f"{config.constraints_force};{config.constraints_tolerance}"
        )
    inp_path = Path(f"{job_name}.inp")
    inp_path.write_text("\n".join(lines) + "\n")
    return inp_path


def run_prime(config: ProteinMCConfig) -> None:
    """Run a Schrödinger Prime-based protein refinement job."""
    job_name = config.job_name
    schrodinger = config.schrodinger

    # Resolve input format
    resolved_input, _ = resolve_input(config.input_file, schrodinger, job_name)
    config.input_file = resolved_input

    if config.job_type == "Normal":
        print("Protein Prepare.....")
        run_cmd([
            str(schrodinger / "utilities" / "prepwizard"),
            "-fillsidechains", "-disulfides", "-rehtreat",
            "-epik_pH", "6.9", "-epik_pHt", "0.6",
            "-samplewater", "-propka_pH", "6.9",
            "-f", "S-OPLS", "-rmsd", "0.3", "-WAIT",
            "-keepfarwat", "-glycosylation", "-delwater_hbond_cutoff", "3",
            str(config.input_file),
            f"{job_name}-prep.maegz",
        ])

    elif config.job_type == "Lysozyme":
        print("Protein Prepare.....")
        run_cmd([
            str(schrodinger / "utilities" / "prepwizard"),
            "-fillsidechains", "-disulfides", "-rehtreat",
            "-epik_pH", "4.75", "-epik_pHt", "0.75",
            "-samplewater", "-propka_pH", "4.75",
            "-f", "S-OPLS", "-rmsd", "0.3", "-WAIT",
            "-keepfarwat", "-glycosylation", "-delwater_hbond_cutoff", "3",
            str(config.input_file),
            f"{job_name}-prep.maegz",
        ])

    elif config.job_type == "PPI_MMGBSA":
        print(f"\nSet up a MM-GBSA calculation:\nUse_membrane: {config.use_membrane}\n")
        cmd = [
            str(schrodinger / "prime_mmgbsa"),
            "-job_type", "REAL_MIN",
            "-rflexdist", "5",
            "-jobname", f"{job_name}-MMGBSA",
            "-ligand", config.comp2,
        ]
        if config.use_membrane:
            cmd.append("-membrane")
        cmd.extend([
            "-HOST", f"{config.cpu_host}:{config.njobs}",
            "-NJOBS", str(config.njobs),
            *config.wait_cmd,
            str(config.input_file),
        ])
        run_cmd(cmd)

    elif config.job_type in ("MC", "SIDE_PRED", "SIDE_OPT"):
        backbone_sampling = config.job_type != "SIDE_OPT"
        print(
            f"\nSet up a Prime {config.job_type} simulation:\n"
            f"Refine_Range:\t{config.refine_range}\n"
            f"Use_random_seed:\t{config.random_seed}\n"
            f"Use_membrane: {config.use_membrane}\n"
            f"Use_constraints: {config.constraints_asl is not None}\n"
            f"Steps: {config.mc_steps}\n"
        )
        if config.job_type in ("MC",):
            inp_path = _generate_mc_inp(config, job_name)
        else:
            inp_path = _generate_side_pred_inp(config, job_name, backbone_sampling)

        run_cmd([
            str(schrodinger / "prime"),
            "-HOST", f"{config.cpu_host}:{config.njobs}",
            "-NJOBS", str(config.njobs),
            *config.wait_cmd,
            str(inp_path),
        ])

    else:
        raise ValueError(f"Unknown Prime job type: {config.job_type}")
```

- [ ] **Step 2: Verify import**

```bash
python -c "from cadd_scripts.proteinmc.prime import run_prime; print('OK')"
```

Expected: `OK`

---

### Task 5: Rosetta module

**Files:**
- Create: `src/cadd_scripts/proteinmc/rosetta.py`

Reference: `ProteinMC` lines 219-339 (the `RosettaMC` function)

- [ ] **Step 1: Write `rosetta.py`**

```python
import subprocess
from pathlib import Path

from .config import ProteinMCConfig
from .utils import run_cmd


def _prepare_rosetta_input(config: ProteinMCConfig, job_name: str) -> bool:
    """Prepare input files for Rosetta. Returns is_mpi_mode."""
    suffix = config.input_file.suffix.lstrip(".")
    if suffix in ("mae", "maegz"):
        split_dir = Path(config.input_file.stem)
        split_dir.mkdir(parents=True, exist_ok=True)
        prefix = str(split_dir / config.input_file.stem)
        run_cmd([
            str(config.schrodinger / "utilities" / "structconvert"),
            "-split-nstructures", "1",
            str(config.input_file),
            f"{prefix}.mae",
        ])
        # Convert each split mae to pdb
        for mae_file in sorted(split_dir.glob(f"{config.input_file.stem}-*.mae")):
            pdb_out = mae_file.with_suffix(".pdb")
            run_cmd([
                str(config.schrodinger / "utilities" / "structconvert"),
                str(mae_file),
                str(pdb_out),
            ])
        # Build input list
        input_list = Path(f"{job_name}_input.list")
        with open(input_list, "w") as f:
            for pdb_file in sorted(split_dir.glob("*.pdb")):
                f.write(f"{pdb_file}\n")
        return False
    elif suffix == "pdb":
        return True  # MPI mode
    elif config.input_file.is_dir():
        input_list = Path(f"{job_name}_input.list")
        with open(input_list, "w") as f:
            for pdb_file in sorted(config.input_file.iterdir()):
                f.write(f"{config.input_file / pdb_file.name}\n")
        return False
    else:
        raise ValueError(f"Unsupported input format: {config.input_file}")


PBS_HEADERS = {
    "CPU": """\
#PBS -N {job_name}
#PBS -l nodes=1:ppn={njobs}:centos7
#PBS -S /bin/bash
#PBS -j oe
#PBS -l walltime=360:00:00
#PBS -q siais_pub_cpu

module load mpi/openmpi/4.1.1
module load compiler/gnu/8.3.0
cd $PBS_O_WORKDIR
""",
    "amdnode": """\
#PBS -N {job_name}
#PBS -l nodes=1:ppn={njobs}
#PBS -S /bin/bash
#PBS -j oe
#PBS -l walltime=360:00:00
#PBS -q amdnode

module load mpi/openmpi/4.1.1
module load compiler/gnu/8.3.0
cd $PBS_O_WORKDIR
""",
    "fat": """\
#PBS -N {job_name}
#PBS -l nodes=1:ppn={njobs}
#PBS -S /bin/bash
#PBS -j oe
#PBS -l walltime=360:00:00
#PBS -q pub_fat

module load mpi/openmpi/4.1.1
module load compiler/gnu/8.3.0
cd $PBS_O_WORKDIR
""",
}


def _rosetta_exe(config: ProteinMCConfig, tool: str) -> str:
    """Build path to a Rosetta executable."""
    return f"{config.rosetta_app}/{tool}.{config.rosetta_version}.linuxgccrelease"


def _interface_analyzer_cmd(config: ProteinMCConfig, job_name: str) -> str:
    """Generate InterfaceAnalyzer parallel command."""
    exe = _rosetta_exe(config, "InterfaceAnalyzer")
    return (
        f"ls {job_name}_OUT/ | parallel -j {config.njobs} "
        f"{exe} "
        f"-s {job_name}_OUT/{{}} "
        f"-out:file:score_only {job_name}_Interface_Score.sc "
        f"-interface {config.comp1}_{config.comp2} "
        f"-compute_packstat true -tracer_data_print false -pack_separated true "
        f"-packstat::oversample 100 -add_regular_scores_to_scorefile true "
        f"-pose_metrics::interface_cutoff 8.0 -sasa_calculator_probe_radius 1.4 "
        f"-atomic_burial_cutoff 0.01 -no_nstruct_label true "
        f"-score:weights {config.rosetta_score}"
    )


def _relax_base_flags(config: ProteinMCConfig, job_name: str) -> str:
    """Common relax flags."""
    return (
        f"-database {config.rosetta_db} "
        f"-out:file:scorefile {job_name}_score.sc "
        f"-out:path:pdb {job_name}_OUT/ "
        f"-nstruct {config.output_num} "
        f"-ex1 -ex2aro -ignore_zero_occupancy false "
        f"-score:weights {config.rosetta_score} "
        f"-relax:jump_move true -relax:bb_move true -relax:chi_move true "
        f"-relax:dualspace true -relax::minimize_bond_angles"
    )


def _generate_docking_commands(config: ProteinMCConfig, job_name: str) -> str:
    """Generate docking commands for PBS script (MPI mode only)."""
    commands = []
    rosetta_db = config.rosetta_db
    njobs = config.njobs
    input_file = config.input_file
    comp1 = config.comp1
    comp2 = config.comp2
    score = config.rosetta_score
    output_num = config.output_num

    if config.job_type == "FlexPepDock":
        exe = _rosetta_exe(config, "FlexPepDocking")
        commands.append(
            f"mpirun -np {njobs} {exe} -database {rosetta_db} "
            f"-in:file:s {input_file} -out:file:scorefile {job_name}_score.sc "
            f"-out:path:pdb {job_name}_OUT/ -nstruct {output_num} "
            f"-ex1 -ex2aro -ignore_zero_occupancy false -score:weights {score} "
            f"-receptor_chain {comp1} -flexPepDocking:peptide_chain {comp2} "
            f"-flexPepDocking:lowres_abinitio "
            f"-frag3 frags/frags.3mers.offset -frag9 frags/frags.9mers.offset "
            f"-flexPepDocking:frag5 frags/frags.5mers.offset "
            f"-flexPepDocking:frag5_weight 0.25 -flexPepDocking:frag9_weight 0.1 "
            f"-flexPepDocking:pep_refine"
        )
    elif config.job_type == "FlexPepRefine":
        exe = _rosetta_exe(config, "FlexPepDocking")
        commands.append(
            f"mpirun -np {njobs} {exe} -database {rosetta_db} "
            f"-in:file:s {input_file} -out:file:scorefile {job_name}_score.sc "
            f"-out:path:pdb {job_name}_OUT/ -nstruct {output_num} "
            f"-ex1 -ex2aro -ignore_zero_occupancy false -score:weights {score} "
            f"-receptor_chain {comp1} -flexPepDocking:peptide_chain {comp2} "
            f"-flexPepDocking:pep_refine"
        )
    elif config.job_type == "PPI_Dock":
        prepack_exe = _rosetta_exe(config, "docking_prepack_protocol")
        dock_exe = _rosetta_exe(config, "docking_protocol")
        prepacked = f"{input_file.stem}_0001.pdb"
        commands.append(
            f"mpirun -np {njobs} {prepack_exe} "
            f"-docking:partners {comp1}_{comp2} -docking::dock_rtmin true "
            f"-in:file:s {input_file} -ex1 -ex2aro "
            f"-score:weights {score} -ignore_zero_occupancy false"
        )
        commands.append(
            f"mpirun -np {njobs} {dock_exe} -database {rosetta_db} "
            f"-in:file:s {prepacked} -out:file:scorefile {job_name}_score.sc "
            f"-out:path:pdb {job_name}_OUT/ -nstruct {output_num} "
            f"-ex1 -ex2aro -ignore_zero_occupancy false -score:weights {score} "
            f"-partners {comp1}_{comp2} -dock_pert 3 8 -randomize2 -ex1 -ex2aro "
            f"-spin -use_input_sc -dock_mcm_trans_magnitude 0.7 "
            f"-dock_mcm_rot_magnitude 5.0 "
            f"-mh:path:scores_BB_BB {rosetta_db}/additional_protocol_data/motif_dock/xh_16_ "
            f"-mh:score:use_ss1 false -mh:score:use_ss2 false "
            f"-mh:score:use_aa1 true -mh:score:use_aa2 true "
            f"-docking_low_res_score motif_dock_score"
        )
    elif config.job_type == "PPI_Refine":
        prepack_exe = _rosetta_exe(config, "docking_prepack_protocol")
        dock_exe = _rosetta_exe(config, "docking_protocol")
        prepacked = f"{input_file.stem}_0001.pdb"
        commands.append(
            f"mpirun -np {njobs} {prepack_exe} "
            f"-docking:partners {comp1}_{comp2} -docking::dock_rtmin true "
            f"-in:file:s {input_file} -ex1 -ex2aro "
            f"-score:weights {score} -ignore_zero_occupancy false"
        )
        commands.append(
            f"mpirun -np {njobs} {dock_exe} -database {rosetta_db} "
            f"-in:file:s {prepacked} -out:file:scorefile {job_name}_score.sc "
            f"-out:path:pdb {job_name}_OUT/ -nstruct {output_num} "
            f"-ex1 -ex2aro -ignore_zero_occupancy false -score:weights {score} "
            f"-partners {comp1}_{comp2} -dock_pert 3 8 -use_input_sc"
        )

    # All docking jobs get InterfaceAnalyzer
    commands.append(_interface_analyzer_cmd(config, job_name))
    return "\n".join(commands)


def _generate_relax_commands(config: ProteinMCConfig, job_name: str, mpi_mode: bool) -> str:
    """Generate relaxation commands for PBS script."""
    exe = _rosetta_exe(config, "relax")
    base = _relax_base_flags(config, job_name)

    relax_type_flag = {
        "Fast_Relax": "-relax:fast",
        "Relax": "-relax:thorough",
        "PPI_Relax": "-relax:script InterfaceRelax2019",
    }[config.job_type]

    if mpi_mode:
        return (
            f"mpirun -np {config.njobs} {exe} "
            f"{base} -in:file:s {config.input_file} {relax_type_flag}"
        )
    else:
        return (
            f"cat {job_name}_input.list | parallel -j {config.njobs} "
            f"{exe} {base} -in:file:s {{}} {relax_type_flag}"
        )


def run_rosetta(config: ProteinMCConfig) -> None:
    """Run a Rosetta-based protein refinement job."""
    job_name = config.job_name
    out_dir = Path(f"{job_name}_OUT")
    out_dir.mkdir(parents=True, exist_ok=True)

    print(
        f"\nSet up a Rosetta MC simulation:\n"
        f"nstruct for per input: {config.output_num}\n"
        f"output directory: {out_dir}\n"
    )

    # Prepare input
    mpi_mode = _prepare_rosetta_input(config, job_name)

    # Generate PBS header
    if config.cpu_host not in PBS_HEADERS:
        raise ValueError(f"Rosetta job cannot run on {config.cpu_host}")

    pbs_header = PBS_HEADERS[config.cpu_host].format(
        job_name=job_name, njobs=config.njobs
    )

    # Generate commands
    docking_types = {"FlexPepDock", "FlexPepRefine", "PPI_Dock", "PPI_Refine"}
    relax_types = {"Fast_Relax", "Relax", "PPI_Relax"}

    if config.job_type in docking_types:
        if not mpi_mode:
            raise ValueError("Must specify only one pdb file path for docking mode!")
        commands = _generate_docking_commands(config, job_name)
    elif config.job_type in relax_types:
        commands = _generate_relax_commands(config, job_name, mpi_mode)
    else:
        raise ValueError(f"Unknown Rosetta job type: {config.job_type}")

    # Write and submit PBS script
    pbs_path = Path(f"{job_name}.pbs")
    pbs_path.write_text(pbs_header + "\n" + commands + "\n")
    run_cmd(["qsub", str(pbs_path)])
```

- [ ] **Step 2: Verify import**

```bash
python -c "from cadd_scripts.proteinmc.rosetta import run_rosetta; print('OK')"
```

Expected: `OK`

---

### Task 6: CLI with click

**Files:**
- Create: `src/cadd_scripts/cli.py`

- [ ] **Step 1: Write `cli.py`**

```python
import click
from pathlib import Path
import os

from .proteinmc.config import ProteinMCConfig


@click.group()
def main():
    """CADD-Scripts: Computer-Aided Drug Design automation tools."""
    pass


@main.group()
def proteinmc():
    """Protein refinement and Monte Carlo simulations."""
    pass


PRIME_JOB_TYPES = ["Normal", "Lysozyme", "MC", "SIDE_PRED", "SIDE_OPT", "PPI_MMGBSA"]
ROSETTA_JOB_TYPES = [
    "Fast_Relax", "Relax", "PPI_Relax",
    "FlexPepDock", "FlexPepRefine", "PPI_Dock", "PPI_Refine",
]


@proteinmc.command()
@click.option("-i", "--input", "input_file", required=True, type=click.Path(exists=True), help="Input structure file (.mae, .maegz, .pdb) or directory of .pdb files.")
@click.option("-t", "--type", "job_type", required=True, type=click.Choice(PRIME_JOB_TYPES), help="Prime job type.")
@click.option("-H", "--host", "cpu_host", default="CPU", help="Host for CPU queue.")
@click.option("-N", "--njobs", default=30, type=int, help="Number of subjobs (CPU cores).")
@click.option("-S", "--schrodinger", default=None, type=click.Path(), help="Path to Schrödinger package (default: $SCHRODINGER).")
@click.option("-n", "--output-num", default=3, type=int, help="Number of output conformations per input.")
@click.option("-s", "--steps", "mc_steps", default=50, type=int, help="Steps of MC simulation.")
@click.option("-r", "--random-seed", is_flag=True, default=True, help="Use random seed.")
@click.option("-m", "--membrane", "use_membrane", is_flag=True, default=False, help="Consider membrane in simulation.")
@click.option("-R", "--range", "refine_range", default="all", help="ASL for refine range.")
@click.option("-c", "--constraints", "constraints_asl", default=None, help="ASL for position constraints.")
@click.option("-f", "--constraints-force", default=10.0, type=float, help="Force for position constraints.")
@click.option("-d", "--constraints-tolerance", default=0.0, type=float, help="Distance tolerance for position constraints.")
@click.option("-1", "--comp1", default="A", help="Component 1 ASL (receptor).")
@click.option("-2", "--comp2", default="B", help="Component 2 ASL (ligand/peptide).")
def prime(input_file, job_type, cpu_host, njobs, schrodinger, output_num,
          mc_steps, random_seed, use_membrane, refine_range,
          constraints_asl, constraints_force, constraints_tolerance,
          comp1, comp2):
    """Schrödinger Prime-based protein refinement."""
    from .proteinmc.prime import run_prime

    config = ProteinMCConfig(
        input_file=Path(input_file).resolve(),
        job_type=job_type,
        cpu_host=cpu_host,
        njobs=njobs,
        schrodinger=Path(schrodinger) if schrodinger else Path(os.environ.get("SCHRODINGER", "")),
        output_num=output_num,
        mc_steps=mc_steps,
        random_seed=random_seed,
        use_membrane=use_membrane,
        refine_range=refine_range,
        constraints_asl=constraints_asl,
        constraints_force=constraints_force,
        constraints_tolerance=constraints_tolerance,
        comp1=comp1,
        comp2=comp2,
    )
    run_prime(config)


@proteinmc.command()
@click.option("-i", "--input", "input_file", required=True, type=click.Path(exists=True), help="Input structure file (.mae, .maegz, .pdb) or directory of .pdb files.")
@click.option("-t", "--type", "job_type", required=True, type=click.Choice(ROSETTA_JOB_TYPES), help="Rosetta job type.")
@click.option("-H", "--host", "cpu_host", default="CPU", help="Host for CPU queue.")
@click.option("-N", "--njobs", default=30, type=int, help="Number of subjobs (CPU cores).")
@click.option("-S", "--schrodinger", default=None, type=click.Path(), help="Path to Schrödinger package (default: $SCHRODINGER).")
@click.option("-n", "--output-num", default=3, type=int, help="Number of output conformations per input.")
@click.option("-A", "--rosetta-app", default=None, type=click.Path(), help="Path to Rosetta app (default: $rosetta_app).")
@click.option("-B", "--rosetta-db", default=None, type=click.Path(), help="Path to Rosetta database (default: $rosetta_db).")
@click.option("-1", "--comp1", default="A", help="Component 1 chain name (receptor).")
@click.option("-2", "--comp2", default="B", help="Component 2 chain name (ligand/peptide).")
def rosetta(input_file, job_type, cpu_host, njobs, schrodinger, output_num,
            rosetta_app, rosetta_db, comp1, comp2):
    """Rosetta-based relaxation and docking."""
    from .proteinmc.rosetta import run_rosetta

    config = ProteinMCConfig(
        input_file=Path(input_file).resolve(),
        job_type=job_type,
        cpu_host=cpu_host,
        njobs=njobs,
        schrodinger=Path(schrodinger) if schrodinger else Path(os.environ.get("SCHRODINGER", "")),
        output_num=output_num,
        rosetta_app=Path(rosetta_app) if rosetta_app else (Path(p) if (p := os.environ.get("rosetta_app")) else None),
        rosetta_db=Path(rosetta_db) if rosetta_db else (Path(p) if (p := os.environ.get("rosetta_db")) else None),
        comp1=comp1,
        comp2=comp2,
    )
    run_rosetta(config)
```

- [ ] **Step 2: Verify CLI registers**

```bash
cadd --help
cadd proteinmc --help
cadd proteinmc prime --help
cadd proteinmc rosetta --help
```

Expected: All four show help text without errors.

---

### Task 7: End-to-end smoke test (dry run)

**Files:** None (manual verification)

- [ ] **Step 1: Test prime help**

```bash
cadd proteinmc prime --help
```

Verify: Shows all prime options (`-i`, `-t`, `-s`, `-r`, `-m`, `-R`, `-c`, `-f`, `-d`, `-1`, `-2`, `-H`, `-N`, `-S`, `-n`)

- [ ] **Step 2: Test rosetta help**

```bash
cadd proteinmc rosetta --help
```

Verify: Shows all rosetta options (`-i`, `-t`, `-A`, `-B`, `-1`, `-2`, `-H`, `-N`, `-S`, `-n`)

- [ ] **Step 3: Test invalid job type rejection**

```bash
cadd proteinmc prime -i /dev/null -t INVALID_TYPE 2>&1 || true
```

Expected: Error message about invalid choice for `-t`

- [ ] **Step 4: Verify default values match Bash version**

Cross-check these defaults against the original `ProteinMC` script (lines 9-29):

| Parameter | Bash default | Python default |
|-----------|-------------|----------------|
| CPU_HOST | CPU | CPU |
| NJOBS | 30 | 30 |
| Job_Type | MC | MC |
| Force_Field | S-OPLS | S-OPLS |
| Rosetta_score | ref2015_cart | ref2015_cart |
| MC_Steps | 50 | 50 |
| output_num | 3 | 3 |
| random_seed | yes | True |
| use_membrane | no | False |
| Range | all | all |
| constraints_force | 10.00 | 10.0 |
| constraints_tolerance | 0.00 | 0.0 |
| rosetta_version | mpi | mpi |
| comp1 | A | A |
| comp2 | B | B |
