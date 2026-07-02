#!/bin/bash
#SBATCH --job-name=prodtests_pre1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=6G
#SBATCH --time=12:00:00
#SBATCH --output=logs/%x_%A_%a.out
#SBATCH --error=logs/%x_%A_%a.err
#
# submit_pipeline.slurm — SLURM job-array launcher for the pre1_D121
# production_tests pipeline (falcon alternative to the LPC DAGMan setup).
#
# SLURM has no analog to DAGMan's per-node dependencies, so this instead
# runs all 3 stages (GSD -> RECO -> nanoML) SEQUENTIALLY inside a single
# job per array task. This is fine here because the 3 stages of a single
# replica must run in order on the same seed anyway — DAGMan's benefit
# was independent parallelism across the queue, which SLURM's --array
# gives us just as well.
#
# Usage:
#   sbatch --array=0-9 submit_pipeline.slurm \
#          --energy 100 --nevents 200 \
#          [--particle 22] [--partname photon] \
#          [--cmssw-base /path/to/CMSSW_20_0_0_pre1] \
#          [--outdir /path/to/output/dir]
#
# --outdir here is a shared filesystem path (falcon has no EOS). Defaults to
#   /home/export/${USER}/production_tests/pre1_D121/{GSD,RECO,nanoML}/
#
# Array indices ARE replica indices; run --array=0-9 for 10 replicas.

set -eu -o pipefail

# ---- Parse args (SLURM does pass argv through) ---------------------------
ENERGY=""
NEVENTS=""
PARTICLE=22
PARTNAME=photon
CMSSW_BASE_ARG=""
OUTDIR=""

while [ $# -gt 0 ]; do
    case "$1" in
        --energy)      ENERGY="$2";         shift 2 ;;
        --nevents)     NEVENTS="$2";        shift 2 ;;
        --particle)    PARTICLE="$2";       shift 2 ;;
        --partname)    PARTNAME="$2";       shift 2 ;;
        --cmssw-base)  CMSSW_BASE_ARG="$2"; shift 2 ;;
        --outdir)      OUTDIR="$2";         shift 2 ;;
        *)
            echo "unknown arg: $1" >&2
            exit 1
            ;;
    esac
done

for var in ENERGY NEVENTS; do
    if [ -z "${!var}" ]; then
        echo "ERROR: --$(echo $var | tr A-Z a-z) is required" >&2
        exit 1
    fi
done

# ---- Defaults ------------------------------------------------------------
: "${CMSSW_BASE_ARG:=$HOME/CMSSW_20_0_0_pre1}"
: "${OUTDIR:=/home/export/${USER}/production_tests/pre1_D121}"

REPLICA="${SLURM_ARRAY_TASK_ID:-0}"
JOBID="${SLURM_ARRAY_JOB_ID:-local}"

SEED_BASE=$(printf "%.0f" "$(echo "$ENERGY * 1000" | bc -l)")
SEED=$((SEED_BASE + REPLICA))
ETAG=$(printf "%.0f" "$ENERGY")
TAG="${PARTNAME}_E${ETAG}_rep${REPLICA}"

echo "=== $(hostname) $(date -u +%FT%TZ) ==="
echo "JOB=$JOBID  REPLICA=$REPLICA  SEED=$SEED"
echo "PARTICLE=$PARTICLE ($PARTNAME)  ENERGY=$ENERGY GeV  NEVENTS=$NEVENTS"
echo "CMSSW_BASE=$CMSSW_BASE_ARG"
echo "OUTDIR=$OUTDIR"
echo "TAG=$TAG"
echo

# ---- CMSSW setup ---------------------------------------------------------
source /cvmfs/cms.cern.ch/cmsset_default.sh
cd "$CMSSW_BASE_ARG/src"
eval $(scramv1 runtime -sh)
CFG_DIR="$CMSSW_BASE/src/production_tests"

# ---- Scratch dir ---------------------------------------------------------
SCRATCH="${TMPDIR:-/tmp}/prodtests_${JOBID}_${REPLICA}"
mkdir -p "$SCRATCH"
cd "$SCRATCH"
echo "SCRATCH=$SCRATCH"
echo

mkdir -p "$OUTDIR/GSD" "$OUTDIR/RECO" "$OUTDIR/nanoML"

# ---- Stage 1: GSD --------------------------------------------------------
GSD_OUT="${TAG}_GSD.root"
echo "[GSD $(date -u +%FT%TZ)]"
cmsRun "${CFG_DIR}/GSD_GUN.py" \
    seed="$SEED" \
    particle="$PARTICLE" \
    energy="$ENERGY" \
    maxEvents="$NEVENTS" \
    outputFile="$GSD_OUT"

[ -s "$GSD_OUT" ] || { echo "ERROR: GSD failed"; exit 2; }
cp -f "$GSD_OUT" "$OUTDIR/GSD/$GSD_OUT"

# ---- Stage 2: RECO -------------------------------------------------------
RECO_OUT="${TAG}_RECO.root"
echo "[RECO $(date -u +%FT%TZ)]"
cmsRun "${CFG_DIR}/RECO.py" \
    inputFiles="file:${GSD_OUT}" \
    outputFile="$RECO_OUT"

[ -s "$RECO_OUT" ] || { echo "ERROR: RECO failed"; exit 3; }
cp -f "$RECO_OUT" "$OUTDIR/RECO/$RECO_OUT"

# GSD no longer needed
rm -f "$GSD_OUT"

# ---- Stage 3: nanoML -----------------------------------------------------
NANO_OUT="${TAG}_nanoML.root"
echo "[NANO $(date -u +%FT%TZ)]"
cmsRun "${CFG_DIR}/nanoML_cfg.py" \
    inputFiles="file:${RECO_OUT}" \
    outputFile="$NANO_OUT"

[ -s "$NANO_OUT" ] || { echo "ERROR: nanoML failed"; exit 4; }
cp -f "$NANO_OUT" "$OUTDIR/nanoML/$NANO_OUT"

# Cleanup
rm -f "$RECO_OUT" "$NANO_OUT"
cd -
rm -rf "$SCRATCH"

echo
echo "=== DONE $(date -u +%FT%TZ) ==="
echo "Outputs at $OUTDIR/{GSD,RECO,nanoML}/$TAG*.root"
