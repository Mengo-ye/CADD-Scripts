from pathlib import Path

from ..utils import run_cmd
from .config import ProteinMCConfig
from .utils import resolve_input


def _generate_mc_inp(config: ProteinMCConfig, job_name: str, input_file: Path) -> Path:
    """Generate .inp file for Prime MC refinement."""
    lines = [
        f"STRUCT_FILE\t{input_file}",
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
            f"{config.constraints_force:.2f};{config.constraints_tolerance:.2f}"
        )
    inp_path = Path(f"{job_name}.inp")
    inp_path.write_text("\n".join(lines) + "\n")
    return inp_path


def _generate_side_pred_inp(
    config: ProteinMCConfig, job_name: str, input_file: Path, backbone_sampling: bool
) -> Path:
    """Generate .inp file for Prime SIDE_PRED refinement."""
    lines = [
        f"STRUCT_FILE\t{input_file}",
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
            f"{config.constraints_force:.2f};{config.constraints_tolerance:.2f}"
        )
    inp_path = Path(f"{job_name}.inp")
    inp_path.write_text("\n".join(lines) + "\n")
    return inp_path


def run_prime(config: ProteinMCConfig) -> None:
    """Run a Schrödinger Prime-based protein refinement job."""
    schrodinger = config.require_schrodinger()
    job_name = config.job_name

    # Resolve input format (use local var, don't mutate config)
    resolved_input, _ = resolve_input(config.input_file, schrodinger, job_name)

    if config.job_type == "Normal":
        print("Protein Prepare.....")
        run_cmd([
            str(schrodinger / "utilities" / "prepwizard"),
            "-fillsidechains", "-disulfides", "-rehtreat",
            "-epik_pH", "6.9", "-epik_pHt", "0.6",
            "-samplewater", "-propka_pH", "6.9",
            "-f", "S-OPLS", "-rmsd", "0.3", "-WAIT",
            "-keepfarwat", "-glycosylation", "-delwater_hbond_cutoff", "3",
            str(resolved_input),
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
            str(resolved_input),
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
            str(resolved_input),
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
        if config.job_type == "MC":
            inp_path = _generate_mc_inp(config, job_name, resolved_input)
        else:
            inp_path = _generate_side_pred_inp(config, job_name, resolved_input, backbone_sampling)

        run_cmd([
            str(schrodinger / "prime"),
            "-HOST", f"{config.cpu_host}:{config.njobs}",
            "-NJOBS", str(config.njobs),
            *config.wait_cmd,
            str(inp_path),
        ])

    else:
        raise ValueError(f"Unknown Prime job type: {config.job_type}")
