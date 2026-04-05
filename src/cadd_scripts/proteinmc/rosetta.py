from pathlib import Path

from ..utils import run_cmd
from .config import ProteinMCConfig


def _prepare_rosetta_input(config: ProteinMCConfig, job_name: str) -> bool:
    """Prepare input files for Rosetta. Returns is_mpi_mode."""
    schrodinger = config.require_schrodinger()
    suffix = config.input_file.suffix.lstrip(".")
    if suffix in ("mae", "maegz"):
        split_dir = Path(config.input_file.stem)
        split_dir.mkdir(parents=True, exist_ok=True)
        prefix = str(split_dir / config.input_file.stem)
        run_cmd([
            str(schrodinger / "utilities" / "structconvert"),
            "-split-nstructures", "1",
            str(config.input_file),
            f"{prefix}.mae",
        ])
        # Convert each split mae to pdb
        for mae_file in sorted(split_dir.glob(f"{config.input_file.stem}-*.mae")):
            pdb_out = mae_file.with_suffix(".pdb")
            run_cmd([
                str(schrodinger / "utilities" / "structconvert"),
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
        pdb_files = sorted(config.input_file.glob("*.pdb"))
        if not pdb_files:
            raise ValueError(f"No .pdb files found in directory: {config.input_file}")
        with open(input_list, "w") as f:
            for pdb_file in pdb_files:
                f.write(f"{pdb_file}\n")
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
    config.require_schrodinger()
    config.require_rosetta()

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
        supported = ", ".join(PBS_HEADERS.keys())
        raise ValueError(
            f"Unsupported host '{config.cpu_host}' for Rosetta jobs. Supported: {supported}"
        )

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
