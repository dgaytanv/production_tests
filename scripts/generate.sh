#!/bin/bash
#
# Full production chain for any particle: [MINBIAS] -> GSD -> RECO -> nanoML -> parquet.
# The particle is set with --particle <pdgId> (file names use --partname, by default
# derived from the pdgId); --fine-calo switches to the fineCalo truth configuration,
# which has no pileup support.
#
# Usage:   bash generate.sh <output_directory> [n_events] --particle <pdgId> [options]
# Example: bash generate.sh /path/to/output/folder 1000 --particle 130 --gun closeBy --minE 10 --maxE 10
# Run with --help for the full option list.

PARTICLE=""
PARTNAME=""
USE_FINE_CALO=0

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
source "$SCRIPT_DIR/chain_common.sh"

run_chain "$@"
