#!/usr/bin/env python3
# coding:utf-8

# default libraries
import sys

if sys.version_info < (3, 6):  # minimum is python3.6
    raise AssertionError("Minimum python version to run PPanGGOLiN is 3.6. Your current python version is " +
                         ".".join(map(str, sys.version_info)))
import argparse
import pkg_resources

# local modules
import ppanggolin.pangenome
from ppanggolin.utils import check_input_files, set_verbosity_level, add_common_arguments, manage_cli_and_config_args
import ppanggolin.nem.rarefaction
import ppanggolin.graph
import ppanggolin.annotate
import ppanggolin.cluster
import ppanggolin.figures
import ppanggolin.formats
import ppanggolin.info
import ppanggolin.metrics
import ppanggolin.align
import ppanggolin.RGP
import ppanggolin.mod
import ppanggolin.context
import ppanggolin.workflow
import ppanggolin.utility

def cmd_line() -> argparse.Namespace:
    """ Manage the command line argument given by user

    :return: arguments given and readable by PPanGGOLiN
    """
    # need to manually write the description so that it's displayed into groups of subcommands ....
    desc = "\n"
    desc += "All of the following subcommands have their own set of options. To see them for a given subcommand," \
            " use it with -h or --help, as such:\n"
    desc += "  ppanggolin <subcommand> -h\n"
    desc += "\n"
    desc += "  Basic:\n"
    desc += "    all           Easy workflow to run all possible analysis\n"
    desc += "    workflow      Easy workflow to run a pangenome analysis in one go\n"
    desc += "    panrgp        Easy workflow to run a pangenome analysis with genomic islands and spots of" \
            " insertion detection\n"
    desc += "    panmodule     Easy workflow to run a pangenome analysis with module prediction\n"
    desc += "  \n"
    desc += "  Expert:\n"
    desc += "    annotate      Annotate genomes\n"
    desc += "    cluster       Cluster proteins in protein families\n"
    desc += "    graph         Create the pangenome graph\n"
    desc += "    partition     Partition the pangenome graph\n"
    desc += "    rarefaction   Compute the rarefaction curve of the pangenome\n"
    desc += "    msa           Compute Multiple Sequence Alignments for pangenome gene families\n"
    desc += "  \n"
    desc += "  Output:\n"
    desc += "    draw          Draw figures representing the pangenome through different aspects\n"
    desc += "    write         Writes 'flat' files representing the pangenome that can be used with other software\n"
    desc += "    fasta         Writes fasta files for different elements of the pan\n"
    desc += "    info          Prints information about a given pangenome graph file\n"
    desc += "    metrics       Compute several metrics on a given pan\n"
    desc += "  \n"
    desc += "  Regions of genomic Plasticity:\n"
    desc += "    align        aligns a genome or a set of proteins to the pangenome gene families representatives and "\
            "predict information from it\n"
    desc += "    rgp          predicts Regions of Genomic Plasticity in the genomes of your pan\n"
    desc += "    spot         predicts spots in your pan\n"
    desc += "    module       Predicts functional modules in your pan\n"
    desc += "  \n"
    desc += "  Genomic context:\n"
    desc += "    context      Local genomic context analysis\n"
    desc += "  \n"
    desc += "  Utility command:\n"
    desc += "    default_config      Generate a yaml config file with default values.\n"
    desc += "  \n"


    subcommand_to_subparser = {
                        "annotate":ppanggolin.annotate.subparser,
                        "cluster":ppanggolin.cluster.subparser,
                        "graph":ppanggolin.graph.subparser,
                        "partition":ppanggolin.nem.partition.subparser,
                        "rarefaction":ppanggolin.nem.rarefaction.subparser,
                        "workflow":ppanggolin.workflow.workflow.subparser,
                        "panrgp":ppanggolin.workflow.panRGP.subparser,
                        "panModule":ppanggolin.workflow.panModule.subparser,
                        "all":ppanggolin.workflow.all.subparser,
                        "draw":ppanggolin.figures.subparser,
                        "write":ppanggolin.formats.writeFlat.subparser,
                        "fasta":ppanggolin.formats.writeSequences.subparser,
                        "msa":ppanggolin.formats.writeMSA.subparser,
                        "metrics":ppanggolin.metrics.metrics.subparser,
                        "align":ppanggolin.align.subparser,
                        "rgp":ppanggolin.RGP.genomicIsland.subparser,
                        "spot":ppanggolin.RGP.spot.subparser,
                        "module":ppanggolin.mod.subparser,
                        "context":ppanggolin.context.subparser,
                        "info":ppanggolin.info.subparser,
                        "default_config":ppanggolin.utility.default_config.subparser}
    
    cmd_with_no_common_args = ['info', 'default_config']

    parser = argparse.ArgumentParser(
        description="Depicting microbial species diversity via a Partitioned PanGenome Graph Of Linked Neighbors",
        formatter_class=argparse.RawTextHelpFormatter)
    
    parser.add_argument('-v', '--version', action='version',
                        version='%(prog)s ' + pkg_resources.get_distribution("ppanggolin").version)
    
    subparsers = parser.add_subparsers(metavar="", dest="subcommand", title="subcommands", description=desc)
    subparsers.required = True  # because python3 sent subcommands to hell apparently
    
    for cmd, sub_fct in subcommand_to_subparser.items():  
        sub = sub_fct(subparsers)
        if cmd not in cmd_with_no_common_args:
            # add options common to all subcommands except for the one that does need it
            add_common_arguments(sub)
    
        if len(sys.argv) == 2 and sub.prog.split()[1] == sys.argv[1]:
            sub.print_help()
            exit(0)

    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(0)

    # First parse args to check that nothing is missing or not expected in cli and throw help when requested
    args = parser.parse_args()

    if hasattr(args, "config"): # the two subcommand with no common args does not have config parameter. so we can skip this part for them.
        args = manage_cli_and_config_args(args.subcommand, args.config, subcommand_to_subparser)
    else:
        set_verbosity_level(args)

    if args.subcommand == "annotate" and args.fasta is None and args.anno is None:
        parser.error("You must provide at least a file with the --fasta option to annotate from sequences, "
                        "or a file with the --gff option to load annotations through the command line or the config file.")
    
    cmds_pangenome_required = ["cluster", "info", "module", "graph","align", 
                               "context", "write", "msa", "draw", "partition",
                               "rarefaction", "spot", "fasta", "metrics", "rgp"]
    if args.subcommand in  cmds_pangenome_required and args.pangenome is None:
        parser.error("You must provide a pangenome file with the --pangenome "
                        "argument through the command line or the config file.")
    
    if args.subcommand == "align" and args.sequences is None:
        parser.error("You must provide sequences (nucleotides or amino acids) to align on the pangenome gene families "
                            "with the --sequences argument through the command line or the config file.")
        
    return args


def main():
    """
    Run the command given by user and set / check some things.

    :return:
    """
    args = cmd_line()

    if hasattr(args, "pangenome"):
        check_input_files(pangenome=args.pangenome)
    if hasattr(args, "fasta"):
        check_input_files(fasta=args.fasta)
    if hasattr(args, "anno"):
        check_input_files(anno=args.anno)

    if args.subcommand == "annotate":
        ppanggolin.annotate.launch(args)
    elif args.subcommand == "cluster":
        ppanggolin.cluster.launch(args)
    elif args.subcommand == "graph":
        ppanggolin.graph.launch(args)
    elif args.subcommand == "partition":
        ppanggolin.nem.partition.launch(args)
    elif args.subcommand == "workflow":
        ppanggolin.workflow.workflow.launch(args)
    elif args.subcommand == "rarefaction":
        ppanggolin.nem.rarefaction.launch(args)
    elif args.subcommand == "draw":
        ppanggolin.figures.launch(args)
    elif args.subcommand == "write":
        ppanggolin.formats.writeFlat.launch(args)
    elif args.subcommand == "fasta":
        ppanggolin.formats.writeSequences.launch(args)
    elif args.subcommand == "msa":
        ppanggolin.formats.writeMSA.launch(args)
    elif args.subcommand == "info":
        ppanggolin.info.launch(args)
    elif args.subcommand == "metrics":
        ppanggolin.metrics.metrics.launch(args)
    elif args.subcommand == "align":
        ppanggolin.align.launch(args)
    elif args.subcommand == "rgp":
        ppanggolin.RGP.genomicIsland.launch(args)
    elif args.subcommand == "spot":
        ppanggolin.RGP.spot.launch(args)
    elif args.subcommand == "panrgp":
        ppanggolin.workflow.panRGP.launch(args)
    elif args.subcommand == "module":
        ppanggolin.mod.launch(args)
    elif args.subcommand == "panmodule":
        ppanggolin.workflow.panModule.launch(args)
    elif args.subcommand == "all":
        ppanggolin.workflow.all.launch(args)
    elif args.subcommand == "context":
        ppanggolin.context.launch(args)
    elif args.subcommand == "default_config":
        ppanggolin.utility.launch(args)


if __name__ == "__main__":
    main()
