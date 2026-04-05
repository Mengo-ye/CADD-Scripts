"""Peptide segmentation and FASTA-based building.

Translates XDock Bash lines 409-489 (peptide handling).
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from ..utils import run_cmd
from .config import XDockConfig

# ---------------------------------------------------------------------------
# Julia segmentation script -- exact copy of XDock lines 411-463
# ---------------------------------------------------------------------------

SEGMENT_JL = """\
using BioStructures

function splitPeptide(file,length,step)
    filename = split(basename(file),".")[1]
    if endswith(file,".pdb")
        println(file," will be read as pdb file.","\\n")
        Structure = read(file,PDB)
    elseif endswith(file,".cif")
        println(file," will be read as cif file.","\\n")
        Structure = read(file,MMCIF)
    else
        println("Error: Input File Extensions not recognized.",file,"\\n")
    end
    for model in Structure
        modelname = modelnumber(model)
        for chain in model
            chainname = chainid(chain)
            resiudenumber=0
            isfritresiduenumberhadgot=0
            fristresidue=1
                for residue in chain
                    if  isfritresiduenumberhadgot < 1
                    fristresidue=resnumber(residue)
                    isfritresiduenumberhadgot+=2
                    resiudenumber=fristresidue
                    end
                    resiudenumber=resiudenumber + 1
                end
                for i in fristresidue:step:resiudenumber
                    stratpoint=i
                    endpoint=i + length
                    if endpoint > resiudenumber
                        continue
                    end
                    peptide = collectresidues(chain, res -> stratpoint <= resnumber(res) < endpoint)
                    println("Residues form ",stratpoint," to ",endpoint," of ",filename,"-model_",modelname,"-chain_",chainname," has been split out.")
                    writepdb("$filename-$modelname-$chainname-$stratpoint-$endpoint.pdb",peptide)
                    stratpoint=stratpoint+step
                    endpoint=endpoint+step
                end
        end
    end
end

print("What's your inputfile?\\n")
fileinput=readline(stdin)
print("Define a length for each peptide:\\n")
peptidelength=parse(Int,readline(stdin))
print("Specify a step size for peptide:\\n")
stepsize=parse(Int,readline(stdin))
splitPeptide(fileinput,peptidelength,stepsize)
"""


# ---------------------------------------------------------------------------
# Peptide segmentation
# ---------------------------------------------------------------------------

def segment_peptides(config: XDockConfig) -> Path:
    """Segment protein structures into peptides using Julia.

    Reproduces XDock lines 409-483.  Returns the output directory
    containing peptide PDB files (``Peptides_Lib``).
    """
    if not config.peptide_segment:
        raise ValueError(
            "Peptide segment not specified. Use -d 'length:stepwise'."
        )

    parts = config.peptide_segment.split(":")
    if len(parts) != 2:
        raise ValueError(
            f"Invalid peptide_segment format '{config.peptide_segment}'. "
            "Expected 'length:stepwise'."
        )

    pep_length, pep_step = parts[0], parts[1]

    # Create output directory
    out_dir = Path("Peptides_Lib")
    out_dir.mkdir(parents=True, exist_ok=True)

    # Write Julia script (in parent of out_dir, matching Bash `cd Peptides_Lib; julia ../Segment.jl`)
    jl_path = Path("Segment.jl")
    jl_path.write_text(SEGMENT_JL)

    # Collect PDB files
    ligand_input = config.ligand_input
    if ligand_input is None:
        raise ValueError("Ligand input is required for peptide segmentation.")

    print(
        "Warning: Only pdb file in Ligand Library will be considered "
        "when you turn on the -d option!"
    )

    if ligand_input.is_dir():
        pdb_files = sorted(ligand_input.glob("*.pdb"))
    elif ligand_input.is_file():
        pdb_files = [ligand_input]
    else:
        pdb_files = []

    # Run segmentation for each file
    # Bash: ( echo "$1"; echo "$Peptide_Length"; echo "$Peptide_Stepwise" ) | julia ../Segment.jl
    for pdb in pdb_files:
        input_data = f"{pdb}\n{pep_length}\n{pep_step}\n"
        print(
            f"File segment to peptides: {pdb}, "
            f"Peptide_Length: {pep_length}, Peptide_Stepwise: {pep_step}"
        )
        subprocess.run(
            ["julia", str(Path("..") / jl_path.name)],
            input=input_data,
            text=True,
            cwd=str(out_dir),
            check=True,
        )

    return out_dir


# ---------------------------------------------------------------------------
# FASTA-based peptide building
# ---------------------------------------------------------------------------

def build_from_fasta(config: XDockConfig) -> Path:
    """Build peptides from a FASTA file using Schrodinger build_peptide.py.

    Reproduces XDock lines 485-489.
    Returns the output directory containing peptide structures
    (``Peptides_lib``).
    """
    schrodinger = config.require_schrodinger()

    if not config.peptide_fasta:
        raise ValueError("Peptide FASTA file not specified. Use -f <fasta>.")

    out_dir = Path("Peptides_lib")
    out_dir.mkdir(parents=True, exist_ok=True)

    out_file = out_dir / "Peptides_lib.maegz"
    cap_flag = "-c" if config.peptide_cap else "-z"

    # Bash: $SCHRODINGER/run build_peptide.py $Peptide_fasta Peptides_lib/Peptides_lib.maegz -f ${Peptide_fasta} ${cap} -s "Extended"
    run_cmd([
        str(schrodinger / "run"), "build_peptide.py",
        str(config.peptide_fasta),
        str(out_file),
        "-f", str(config.peptide_fasta),
        cap_flag,
        "-s", "Extended",
    ])

    return out_dir
