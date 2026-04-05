import click
from pathlib import Path

from .proteinmc.config import ProteinMCConfig


@click.group()
@click.version_option(package_name="cadd-scripts")
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
@click.option("-r", "--random-seed/--no-random-seed", default=True, help="Use random seed (default: enabled).")
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
        schrodinger=Path(schrodinger) if schrodinger else None,
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
        schrodinger=Path(schrodinger) if schrodinger else None,
        output_num=output_num,
        rosetta_app=Path(rosetta_app) if rosetta_app else None,
        rosetta_db=Path(rosetta_db) if rosetta_db else None,
        comp1=comp1,
        comp2=comp2,
    )
    run_rosetta(config)
