#!/bin/bash
# build_dag.sh — generate a DAGMan .dag for the pre1_D121 pipeline.
#
# Per replica the chain is:
#   [minbias_repN if PILEUP>0] --> gsd_repN --> reco_repN --> nano_repN
#
# Replicas are independent so DAGMan parallelizes them across the queue.
#
# Usage:
#   bash build_dag.sh --energy 100 --nreplicas 10 --nevents 200 \
#                     [--particle 22] [--partname photon] \
#                     [--outdir /store/user/$USER/production_tests/pre1_D121] \
#                     [--pileup 0] [--nminbias <same as --nevents>] \
#                     [--seed-base <round(energy*1000)>] \
#                     [--outfile pipeline.dag] \
#                     [--retry 2]

set -eu -o pipefail

# ---- Defaults ------------------------------------------------------------
ENERGY=""
NREPLICAS=""
NEVENTS=""
PARTICLE=22
PARTNAME=photon
OUTDIR="/store/user/${USER:-dgaytanv}/production_tests/pre1_D121"
PILEUP=0
NMINBIAS=""
SEED_BASE=""
OUTFILE="pipeline.dag"
RETRY=2

# ---- Parse args ----------------------------------------------------------
while [ $# -gt 0 ]; do
    case "$1" in
        --energy)    ENERGY="$2";    shift 2 ;;
        --nreplicas) NREPLICAS="$2"; shift 2 ;;
        --nevents)   NEVENTS="$2";   shift 2 ;;
        --particle)  PARTICLE="$2";  shift 2 ;;
        --partname)  PARTNAME="$2";  shift 2 ;;
        --outdir)    OUTDIR="$2";    shift 2 ;;
        --pileup)    PILEUP="$2";    shift 2 ;;
        --nminbias)  NMINBIAS="$2";  shift 2 ;;
        --seed-base) SEED_BASE="$2"; shift 2 ;;
        --outfile)   OUTFILE="$2";   shift 2 ;;
        --retry)     RETRY="$2";     shift 2 ;;
        -h|--help)
            grep '^#' "$0" | head -25
            exit 0
            ;;
        *)
            echo "unknown arg: $1" >&2
            exit 1
            ;;
    esac
done

# ---- Validate ------------------------------------------------------------
for var in ENERGY NREPLICAS NEVENTS; do
    if [ -z "${!var}" ]; then
        echo "ERROR: --$(echo $var | tr A-Z a-z) is required" >&2
        exit 1
    fi
done

# Default seed base uses energy for globally unique seeds
if [ -z "$SEED_BASE" ]; then
    SEED_BASE=$(printf "%.0f" "$(echo "$ENERGY * 1000" | bc -l)")
fi

# Default nminbias = nevents
if [ -z "$NMINBIAS" ]; then
    NMINBIAS="$NEVENTS"
fi

ETAG=$(printf "%.0f" "$ENERGY")

# ---- Emit DAG ------------------------------------------------------------
echo "Generating $OUTFILE"
echo "  energy=$ENERGY GeV, nevents=$NEVENTS, nreplicas=$NREPLICAS"
echo "  particle=$PARTICLE ($PARTNAME), seed_base=$SEED_BASE"
echo "  pileup=$PILEUP, nminbias=$NMINBIAS"
echo "  outdir=$OUTDIR"
echo

{
    echo "# Auto-generated DAG for pre1_D121 production_tests"
    echo "# energy=${ENERGY}  nreplicas=${NREPLICAS}  nevents=${NEVENTS}"
    echo "# particle=${PARTICLE} (${PARTNAME})  outdir=${OUTDIR}"
    echo "# pileup=${PILEUP}  nminbias=${NMINBIAS}  seed_base=${SEED_BASE}"
    echo ""
    echo "CONFIG dag.config"
    echo ""

    for REP in $(seq 0 $((NREPLICAS - 1))); do
        SEED=$((SEED_BASE + REP))
        BASE_VARS="particle=\"${PARTICLE}\" energy=\"${ENERGY}\" seed=\"${SEED}\" replica=\"${REP}\" nevents=\"${NEVENTS}\" outdir=\"${OUTDIR}\" partname=\"${PARTNAME}\" pileup=\"${PILEUP}\" nminbias=\"${NMINBIAS}\""

        NMB="minbias_E${ETAG}_rep${REP}"
        NGSD="gsd_E${ETAG}_rep${REP}"
        NRECO="reco_E${ETAG}_rep${REP}"
        NNANO="nano_E${ETAG}_rep${REP}"

        # Optional minbias node
        if [ "$PILEUP" -gt 0 ]; then
            echo "JOB  ${NMB} stage.jdl"
            echo "VARS ${NMB} stage=\"minbias\" ${BASE_VARS} jobname=\"${NMB}\""
            echo "RETRY ${NMB} ${RETRY}"
            echo ""
        fi

        echo "JOB  ${NGSD}  stage.jdl"
        echo "VARS ${NGSD} stage=\"gsd\"  ${BASE_VARS} jobname=\"${NGSD}\""
        echo "RETRY ${NGSD} ${RETRY}"
        echo ""

        echo "JOB  ${NRECO} stage.jdl"
        echo "VARS ${NRECO} stage=\"reco\" ${BASE_VARS} jobname=\"${NRECO}\""
        echo "RETRY ${NRECO} ${RETRY}"
        echo ""

        echo "JOB  ${NNANO} stage.jdl"
        echo "VARS ${NNANO} stage=\"nano\" ${BASE_VARS} jobname=\"${NNANO}\""
        echo "RETRY ${NNANO} ${RETRY}"
        echo ""

        # Chain within this replica
        if [ "$PILEUP" -gt 0 ]; then
            echo "PARENT ${NMB}   CHILD ${NGSD}"
        fi
        echo "PARENT ${NGSD}  CHILD ${NRECO}"
        echo "PARENT ${NRECO} CHILD ${NNANO}"
        echo ""
    done
} > "$OUTFILE"

if [ "$PILEUP" -gt 0 ]; then
    TOTAL=$((NREPLICAS * 4))
    echo "Wrote $OUTFILE with $TOTAL nodes ($NREPLICAS replicas × 4 stages incl. minbias)"
else
    TOTAL=$((NREPLICAS * 3))
    echo "Wrote $OUTFILE with $TOTAL nodes ($NREPLICAS replicas × 3 stages)"
fi
