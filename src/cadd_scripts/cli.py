import click
from pathlib import Path

from .gvsrun.config import GVSRunConfig
from .gvsrun.modes import PREDEFINED_MODES
from .proteinmc.config import ProteinMCConfig
from .xdock.config import XDockConfig
from .xdock.modes import VALID_MODES


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


# XDock command
VALID_PRECISIONS = ["SP", "XP", "HTVS"]
VALID_FORCE_FIELDS = ["OPLS4", "OPLS3e", "OPLS3", "OPLS_2005"]
VALID_PRO_PREPS = ["none", "rosetta", "rough", "fine", "hopt", "mini"]
VALID_LIG_PREPS = ["none", "epik", "ionizer"]


@main.command()
@click.option("-P", "--protein", "protein_input", required=True, type=click.Path(exists=True), help="Protein library directory or structure file.")
@click.option("-L", "--ligand", "ligand_input", default=None, type=click.Path(exists=True), help="Ligand file or directory.")
@click.option("-m", "--mode", default="SITEMAP", type=click.Choice(VALID_MODES), help="XDock mode.")
@click.option("-p", "--pro-prep", default="rough", type=click.Choice(VALID_PRO_PREPS), help="Protein preparation mode.")
@click.option("-l", "--lig-prep", default="epik", type=click.Choice(VALID_LIG_PREPS), help="Ligand preparation mode.")
@click.option("-H", "--host", default="CPU", help="Host for CPU queue.")
@click.option("-N", "--njobs", default=50, type=int, help="Number of parallel jobs.")
@click.option("-S", "--schrodinger", default=None, type=click.Path(), help="Path to Schrödinger (default: $SCHRODINGER).")
@click.option("-R", "--rosetta-app", default=None, type=click.Path(), help="Path to Rosetta app (default: $rosetta_app).")
@click.option("-B", "--rosetta-db", default=None, type=click.Path(), help="Path to Rosetta database (default: $rosetta_db).")
@click.option("-M", "--rosetta-version", default="mpi", type=click.Choice(["mpi", "static"]), help="Rosetta version.")
@click.option("-g", "--grid-center", default="", help="Grid center coordinates (x, y, z).")
@click.option("-s", "--sites", "site_num", default=2, type=int, help="Number of SiteMap grid sites per protein.")
@click.option("-a", "--ligand-asl", default="", help="Ligand ASL for complex modes.")
@click.option("-n", "--poses", "pose_num", default=1, type=int, help="Poses per ligand.")
@click.option("-o", "--output", "out_com", default=1, type=int, help="Top complexes to output per protein.")
@click.option("-x", "--precision", default="SP", type=click.Choice(VALID_PRECISIONS), help="Docking precision.")
@click.option("-F", "--force-field", default="OPLS_2005", type=click.Choice(VALID_FORCE_FIELDS), help="Force field.")
@click.option("-v", "--vdw", "scaling_vdw", default=0.8, type=float, help="VdW scaling for ligand.")
@click.option("-V", "--vdw-rec", "scaling_vdw_rec", default=1.0, type=float, help="VdW scaling for receptor.")
@click.option("-i", "--inner", "box_inner", default=12, type=int, help="Inner box size (Å).")
@click.option("-b", "--buffer", "box_buffer", default=5, type=int, help="Outer box buffer (Å).")
@click.option("-A", "--ref-ligand", "ref_ligand_asl", default="A:999", help="Reference ligand ASL for Induce Fit.")
@click.option("-D", "--distance", default=5.0, type=float, help="Flexible residue distance for IFD (Å).")
@click.option("-r", "--prime-njobs", default=10, type=int, help="Number of Prime licenses.")
@click.option("-e", "--enhanced", is_flag=True, default=False, help="Enhanced sampling (3x, maxkeep=15000).")
@click.option("-w", "--refine-inplace", is_flag=True, default=False, help="Refine ligand in-place (mininplace).")
@click.option("-t", "--peptide", is_flag=True, default=False, help="Peptide docking mode.")
@click.option("-d", "--peptide-segment", default=None, help="Segment peptides (format: length:stepwise).")
@click.option("-f", "--peptide-fasta", default=None, type=click.Path(exists=True), help="Build peptides from FASTA file.")
@click.option("-c", "--cap", "peptide_cap", is_flag=True, default=False, help="Cap peptides.")
@click.option("-0", "--only-segment", "only_peptide_segment", is_flag=True, default=False, help="Stop after peptide segmentation.")
@click.option("-1", "--no-strain", "no_strain", is_flag=True, default=False, help="Disable strain correction.")
@click.option("-T", "--title", "job_title", default="", help="Job title.")
@click.option("-u", "--uniprot-list", default=None, type=click.Path(exists=True), help="UniProt ID list for grid filtering.")
@click.option("-U", "--grid-lib", default=None, type=click.Path(exists=True), help="Grid library for UniProt filtering.")
def xdock(protein_input, ligand_input, mode, pro_prep, lig_prep,
          host, njobs, schrodinger, rosetta_app, rosetta_db, rosetta_version,
          grid_center, site_num, ligand_asl, pose_num, out_com,
          precision, force_field, scaling_vdw, scaling_vdw_rec,
          box_inner, box_buffer, ref_ligand_asl, distance, prime_njobs,
          enhanced, refine_inplace, peptide, peptide_segment, peptide_fasta,
          peptide_cap, only_peptide_segment, no_strain, job_title,
          uniprot_list, grid_lib):
    """Reverse docking, global docking, and grid generation."""
    import os
    from .xdock.modes import resolve_mode
    from .xdock.xglide import run_xglide
    from .xdock.ifd import run_ifd
    from .xdock.peptide import segment_peptides, build_from_fasta
    from .xdock.preparation import prepare_proteins_rosetta, filter_grids_by_uniprot

    config = XDockConfig(
        protein_input=Path(protein_input).resolve(),
        ligand_input=Path(ligand_input).resolve() if ligand_input else None,
        mode=mode,
        pro_prep=pro_prep,
        lig_prep=lig_prep,
        host=host,
        njobs=njobs,
        schrodinger=Path(schrodinger) if schrodinger else None,
        rosetta_app=Path(rosetta_app) if rosetta_app else None,
        rosetta_db=Path(rosetta_db) if rosetta_db else None,
        rosetta_version=rosetta_version,
        grid_center=grid_center,
        site_num=site_num,
        ligand_asl=ligand_asl,
        pose_num=pose_num,
        out_com=out_com,
        precision=precision,
        force_field=force_field,
        scaling_vdw=scaling_vdw,
        scaling_vdw_rec=scaling_vdw_rec,
        box_inner=box_inner,
        box_buffer=box_buffer,
        ref_ligand_asl=ref_ligand_asl,
        distance=distance,
        prime_njobs=prime_njobs,
        strain_correction=not no_strain,
        sampling=3 if enhanced else 1,
        maxkeep=15000 if enhanced else 5000,
        docking_method="mininplace" if refine_inplace else "confgen",
        peptide_segment=peptide_segment,
        peptide_fasta=Path(peptide_fasta) if peptide_fasta else None,
        peptide_cap=peptide_cap,
        only_peptide_segment=only_peptide_segment,
        job_title=job_title,
        uniprot_list=Path(uniprot_list) if uniprot_list else None,
        grid_lib=Path(grid_lib) if grid_lib else None,
    )

    # Apply mode flags
    resolve_mode(config)

    # Validate grid_center for center-based modes
    if config.by_center and not config.grid_center.strip():
        raise click.UsageError(
            "Grid center coordinates required for this mode. Use -g 'x, y, z'."
        )

    # UniProt filtering
    if config.uniprot_list and config.grid_lib:
        filtered_dir = filter_grids_by_uniprot(config)
        config.protein_input = filtered_dir
        config.pro_prep = "none"

    # Peptide docking flag — sets GRIDGEN_PEPTIDE in .inp
    if peptide:
        config.docking = "peptide"

    # Peptide segmentation
    if config.peptide_segment:
        pep_dir = segment_peptides(config)
        if config.only_peptide_segment:
            print(f"Peptide segmentation complete. Output: {pep_dir}")
            return
        config.ligand_input = pep_dir

    # Peptide FASTA building
    if config.peptide_fasta:
        pep_dir = build_from_fasta(config)
        config.ligand_input = pep_dir

    # Rosetta protein prep
    if config.pro_prep == "rosetta":
        out_dir = prepare_proteins_rosetta(config)
        config.protein_input = out_dir
        config.pro_prep = "none"

    # Dispatch
    if config.mode == "Native":
        run_xglide(config)
    elif config.xglide:
        run_xglide(config)
    elif config.induce_fit:
        run_ifd(config)


# GVSrun command
VALID_FORCE_FIELDS_GVS = ["OPLS4", "OPLS3e", "OPLS3", "OPLS_2005"]
GVS_MODES = list(PREDEFINED_MODES.keys()) + ["User_Defined"]


@main.command()
@click.option("-i", "--input", "grid_input", default="None", help="Grid file (.zip) or pattern. Use 'None' for DB-only pipelines.")
@click.option("-D", "--database", default="Custom_DB", help="Database name from $compound_library.")
@click.option("-d", "--db-path", "database_path", default=None, type=click.Path(exists=True), help="Custom database path (file or directory).")
@click.option("-m", "--mode", "running_mode", default="Fast", help="Running mode name or custom pipeline (e.g. 'RDL+HTVS_Normal+SP_Normal').")
@click.option("-T", "--title", "job_title", default="", help="Job title (auto-generated if empty).")
@click.option("-R", "--reference", "reference_ligand", default=None, type=click.Path(exists=True), help="Reference ligand file.")
@click.option("-a", "--htvs-out-num", default="5%", help="HTVS output (percentage '5%%' or count '500').")
@click.option("-b", "--docking-out-num", default="4000", help="SP/XP output compounds.")
@click.option("-e", "--set-pull-num", default="500", help="IFT/MMGBSA/CD candidates to pull.")
@click.option("-c", "--dock-out-conf", default=1, type=int, help="Poses per ligand.")
@click.option("-p", "--ph", default="7.0:2.0", help="pH:tolerance for LigPrep.")
@click.option("-s", "--smarts", default=None, help="SMARTs filter expression.")
@click.option("-q", "--qm-set", default="B3LYP-D3(BJ):6-311G**", help="QM method:basis set.")
@click.option("-W", "--mw-range", default="100:400", help="MW filter range (min:max).")
@click.option("-v", "--vdw", "scaling_vdw", default=0.8, type=float, help="VdW scaling for ligand.")
@click.option("-C", "--covalent-residue", "covalent_attach_residue", default=None, help="Covalent residue (e.g. 'cys:A:1425').")
@click.option("-E", "--shape-screen", default=None, help="Shape screen params (keep:method:confs).")
@click.option("-F", "--force-field", default="OPLS4", type=click.Choice(VALID_FORCE_FIELDS_GVS), help="Docking force field.")
@click.option("-f", "--coarse-ff", default="OPLS_2005", type=click.Choice(VALID_FORCE_FIELDS_GVS), help="Coarse force field for HTVS.")
@click.option("-u", "--strain-correction", is_flag=True, default=False, help="Enable strain correction.")
@click.option("-H", "--host", default="CPU", help="Host for CPU queue.")
@click.option("-N", "--njobs", default=100, type=int, help="Max subjobs.")
@click.option("-S", "--schrodinger", default=None, type=click.Path(), help="Schrödinger path (default: $SCHRODINGER).")
@click.option("-P", "--prime-njobs", default=10, type=int, help="Prime licenses.")
@click.option("-G", "--glide-njobs", default=90, type=int, help="Glide licenses.")
@click.option("-L", "--ligprep-njobs", default=30, type=int, help="LigPrep licenses.")
@click.option("-A", "--phase-njobs", default=10, type=int, help="Phase licenses.")
@click.option("-Q", "--qsite-njobs", default=10, type=int, help="QSite licenses.")
@click.option("-K", "--qikprop-njobs", default=10, type=int, help="QikProp licenses.")
@click.option("-M", "--macromodel-njobs", default=10, type=int, help="MacroModel licenses.")
def gvsrun(grid_input, database, database_path, running_mode, job_title,
           reference_ligand, htvs_out_num, docking_out_num, set_pull_num,
           dock_out_conf, ph, smarts, qm_set, mw_range, scaling_vdw,
           covalent_attach_residue, shape_screen, force_field, coarse_ff,
           strain_correction, host, njobs, schrodinger,
           prime_njobs, glide_njobs, ligprep_njobs, phase_njobs,
           qsite_njobs, qikprop_njobs, macromodel_njobs):
    """Virtual screening automation pipeline."""
    from .gvsrun.pipeline import run_pipeline

    config = GVSRunConfig(
        grid_input=grid_input,
        database=database,
        database_path=Path(database_path) if database_path else None,
        running_mode=running_mode,
        job_title=job_title,
        reference_ligand=Path(reference_ligand) if reference_ligand else None,
        htvs_out_num=htvs_out_num,
        docking_out_num=docking_out_num,
        set_pull_num=set_pull_num,
        dock_out_conf=dock_out_conf,
        ph=ph,
        smarts=smarts,
        qm_set=qm_set,
        mw_range=mw_range,
        scaling_vdw=scaling_vdw,
        covalent_attach_residue=covalent_attach_residue,
        shape_screen=shape_screen,
        force_field=force_field,
        coarse_ff=coarse_ff,
        strain_energy="true" if strain_correction else "false",
        host=host,
        njobs=njobs,
        schrodinger=Path(schrodinger) if schrodinger else None,
        prime_njobs=prime_njobs,
        glide_njobs=glide_njobs,
        ligprep_njobs=ligprep_njobs,
        phase_njobs=phase_njobs,
        qsite_njobs=qsite_njobs,
        qikprop_njobs=qikprop_njobs,
        macromodel_njobs=macromodel_njobs,
    )
    run_pipeline(config)
