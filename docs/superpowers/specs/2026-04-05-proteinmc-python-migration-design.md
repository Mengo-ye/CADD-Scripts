# ProteinMC Shell-to-Python3 Migration Design

## Goal

Migrate `ProteinMC` (367-line Bash script) from shell to Python 3 as a pip-installable package. This is the first step toward migrating the entire CADD-Scripts suite (GVSrun, XDock, ProteinMC). The design must accommodate future modules.

## Scope

- **In scope:** All ProteinMC functionality — Prime (MC, SIDE_PRED, SIDE_OPT, Normal, Lysozyme, PPI_MMGBSA) and Rosetta (Fast_Relax, Relax, PPI_Relax, FlexPepDock, FlexPepRefine, PPI_Dock, PPI_Refine)
- **Out of scope:** GVSrun, XDock (future work), tests (deferred)

## Project Structure

```
cadd-scripts/
├── pyproject.toml
├── src/
│   └── cadd_scripts/
│       ├── __init__.py          # package version
│       ├── cli.py               # click top-level group
│       └── proteinmc/
│           ├── __init__.py
│           ├── config.py        # ProteinMCConfig dataclass
│           ├── prime.py         # Schrödinger Prime tasks
│           ├── rosetta.py       # Rosetta tasks
│           └── utils.py         # shared: input prep, subprocess helpers
```

## Packaging

- Build system: `hatchling` (lightweight, modern)
- Dependencies: `click` only
- Python: >=3.10 (for `X | Y` union syntax)
- Entry point: `cadd = cadd_scripts.cli:main`
- Install: `pip install .` or `pip install -e .` for development

## Configuration: `config.py`

```python
from dataclasses import dataclass, field
from pathlib import Path
import os

@dataclass
class ProteinMCConfig:
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
    schrodinger: Path = field(default_factory=lambda: Path(os.environ.get("SCHRODINGER", "")))
    rosetta_app: Path | None = field(default_factory=lambda: Path(p) if (p := os.environ.get("rosetta_app")) else None)
    rosetta_db: Path | None = field(default_factory=lambda: Path(p) if (p := os.environ.get("rosetta_db")) else None)
    rosetta_version: str = "mpi"
```

## CLI Design: `cli.py`

```
cadd proteinmc prime -i structure.mae -t MC -s 100 -n 5 -H CPU -N 30
cadd proteinmc rosetta -i structure.pdb -t Fast_Relax -n 3 -H CPU -N 30
```

Top-level `cadd` group with `proteinmc` subgroup. Under `proteinmc`, two commands: `prime` and `rosetta`.

Common options shared via a click decorator:
- `-i` / `--input`: Input file (required)
- `-t` / `--type`: Job type (required)
- `-H` / `--host`: CPU host
- `-N` / `--njobs`: Number of subjobs
- `-S` / `--schrodinger`: Schrödinger path (env fallback)
- `-n` / `--output-num`: Output conformations

Prime-specific:
- `-s` / `--steps`: MC steps
- `-r` / `--random-seed`: Use random seed (flag)
- `-m` / `--membrane`: Use membrane (flag)
- `-R` / `--range`: Refine range ASL
- `-c` / `--constraints`: Constraints ASL
- `-f` / `--constraints-force`: Constraint force
- `-d` / `--constraints-tolerance`: Constraint tolerance

PPI options (shared by both prime and rosetta):
- `-1` / `--comp1`: Receptor chain/ASL (prime: ASL for PPI_MMGBSA; rosetta: chain name)
- `-2` / `--comp2`: Ligand/peptide chain/ASL

Rosetta-specific:
- `-A` / `--rosetta-app`: Rosetta app path
- `-B` / `--rosetta-db`: Rosetta database path

## Prime Module: `prime.py`

### `run_prime(config: ProteinMCConfig) -> None`

Main entry point. Dispatches by `config.job_type`:

1. **Input preparation** (shared across all prime jobs):
   - `.mae`/`.maegz` → use directly
   - `.pdb` → `structconvert` to `.mae`
   - directory → `structcat` to merge PDBs

2. **Job dispatch:**
   - `Normal` → `prepwizard` with pH 6.9
   - `Lysozyme` → `prepwizard` with pH 4.75
   - `PPI_MMGBSA` → `prime_mmgbsa` (membrane optional)
   - `MC` → generate `.inp` with MC parameters → `prime`
   - `SIDE_PRED` → generate `.inp` with backbone_sampling=yes → `prime`
   - `SIDE_OPT` → generate `.inp` with backbone_sampling=no → `prime` (internally uses SIDE_PRED type)

3. **`.inp` generation:**
   Uses f-strings. Each job type generates its own `.inp` content.
   Constraints appended as an extra line if specified.

4. **Execution:**
   - Local/localhost host → add `-WAIT` flag
   - Otherwise submit to cluster queue

## Rosetta Module: `rosetta.py`

### `run_rosetta(config: ProteinMCConfig) -> None`

Main entry point. Two phases:

1. **Input preparation:**
   - `.mae`/`.maegz` → split with `structconvert`, convert each to PDB, build input list
   - `.pdb` → MPI mode (single file, use `mpirun`)
   - directory → build input list from directory contents

2. **PBS script generation:**
   Generate `.pbs` file with header based on `cpu_host`:
   - `CPU` → `siais_pub_cpu` queue, centos7 node constraint
   - `amdnode` → `amdnode` queue
   - `fat` → `pub_fat` queue
   - Other → error

3. **Command generation** (appended to PBS script):

   **Docking jobs** (MPI only, requires single PDB):
   - `FlexPepDock` → `FlexPepDocking` with abinitio + fragment flags
   - `FlexPepRefine` → `FlexPepDocking` with pep_refine
   - `PPI_Dock` → `docking_prepack_protocol` + `docking_protocol` with full docking flags
   - `PPI_Refine` → `docking_prepack_protocol` + `docking_protocol` (simpler flags)

   All docking jobs append `InterfaceAnalyzer` via `parallel`.

   **Relaxation jobs** (MPI or parallel):
   - `Fast_Relax` → `relax` with `-relax:fast`
   - `Relax` → `relax` with `-relax:thorough`
   - `PPI_Relax` → `relax` with `-relax:script InterfaceRelax2019`

   MPI mode uses `mpirun -np`, parallel mode uses `cat list | parallel`.

4. **Submission:** `qsub` the generated PBS script via `subprocess.run()`.

## Utility Module: `utils.py`

Shared helpers:

```python
def run_cmd(cmd: list[str], check: bool = True) -> subprocess.CompletedProcess:
    """Run a subprocess command, printing the command for transparency."""
    print(f"Running: {' '.join(cmd)}")
    return subprocess.run(cmd, check=check)

def resolve_input(input_path: Path, schrodinger: Path, job_name: str) -> tuple[Path, bool]:
    """
    Normalize input to .mae format.
    Returns (resolved_path, is_mpi_mode).
    """

def derive_job_name(input_file: Path, job_type: str) -> str:
    """Generate job name from input filename and job type."""
    return f"{input_file.stem}_{job_type}"
```

## Key Behavioral Differences from Bash Version

| Aspect | Bash | Python |
|--------|------|--------|
| CLI parsing | `getopts` (single-letter only) | `click` (short + long options, auto-help, type validation) |
| Error handling | Partial (some checks, many silent failures) | `click.BadParameter` for invalid inputs, `subprocess.CalledProcessError` propagated |
| Boolean params | `"yes"/"no"` strings | Native `bool` |
| Path handling | String concatenation | `pathlib.Path` |
| Job routing | if/elif chain at end of script | Explicit `prime`/`rosetta` subcommands |
| SIDE_OPT | Sets `backbone_sampling="no"` then calls SIDE_PRED | Same logic, cleaner via config field |

## Migration Checklist

For each function/feature in the Bash script, verify the Python version:

- [ ] Default values match
- [ ] Generated `.inp` file content is identical
- [ ] Generated `.pbs` file content is identical
- [ ] `structconvert`/`structcat` calls have same arguments
- [ ] `prepwizard` calls have same flags
- [ ] `prime_mmgbsa` calls have same flags
- [ ] `prime` calls have same flags
- [ ] All Rosetta command lines match exactly
- [ ] `qsub` is called correctly
- [ ] Local/localhost wait mode works
