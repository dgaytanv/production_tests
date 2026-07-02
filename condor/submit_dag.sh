#!/bin/bash
# submit_dag.sh — one-shot submission wrapper for the pre1_D121 pipeline.
#
# Builds a CMSSW tarball (once, cached), generates a DAG for the requested
# energy + replicas, submits it to condor. Run from
#   $CMSSW_BASE/src/production_tests/condor/
# in a fresh (non-cmsenv) shell to avoid the PYTHONHOME env-leak that
# breaks condor_submit_dag.
#
# Usage:
#   bash submit_dag.sh --energy 100 --nreplicas 10 --nevents 200 \
#                     [--particle 22] [--partname photon] \
#                     [--outdir /store/user/dgaytanv/production_tests/pre1_D121] \
#                     [--schedd lpcschedd4.fnal.gov] \
#                     [--rebuild-tarball]

set -eu -o pipefail

# ---- Defaults ------------------------------------------------------------
ENERGY=""
NREPLICAS=""
NEVENTS=""
PARTICLE=22
PARTNAME=photon
OUTDIR=""
SCHEDD=""
REBUILD_TAR=0

# ---- Parse args ----------------------------------------------------------
while [ $# -gt 0 ]; do
    case "$1" in
        --energy)          ENERGY="$2";     shift 2 ;;
        --nreplicas)       NREPLICAS="$2";  shift 2 ;;
        --nevents)         NEVENTS="$2";    shift 2 ;;
        --particle)        PARTICLE="$2";   shift 2 ;;
        --partname)        PARTNAME="$2";   shift 2 ;;
        --outdir)        OUTDIR="$2";   shift 2 ;;
        --schedd)          SCHEDD="$2";     shift 2 ;;
        --rebuild-tarball) REBUILD_TAR=1;   shift ;;
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

for var in ENERGY NREPLICAS NEVENTS; do
    if [ -z "${!var}" ]; then
        echo "ERROR: --$(echo $var | tr A-Z a-z) is required" >&2
        exit 1
    fi
done

# ---- Locate CMSSW area ---------------------------------------------------
# We assume this script lives at $CMSSW_BASE/src/production_tests/condor/
SUBMIT_DIR="$(cd "$(dirname "$0")" && pwd)"
PRODTESTS_DIR="$(cd "$SUBMIT_DIR/.." && pwd)"
SRC_DIR="$(cd "$PRODTESTS_DIR/.." && pwd)"
CMSSW_TOP="$(cd "$SRC_DIR/.." && pwd)"
CMSSW_NAME="$(basename "$CMSSW_TOP")"

if [ ! -d "$CMSSW_TOP/src" ] || [ ! -d "$CMSSW_TOP/lib" ]; then
    echo "ERROR: $CMSSW_TOP does not look like a CMSSW release" >&2
    exit 1
fi

echo "CMSSW area:    $CMSSW_TOP"
echo "prod. tests:   $PRODTESTS_DIR"
echo "submit dir:    $SUBMIT_DIR"
echo

if [ -z "$OUTDIR" ]; then
    OUTDIR="/store/user/${USER}/production_tests/pre1_D121"
fi
echo "output base:   $OUTDIR"
echo

TARBALL="${SUBMIT_DIR}/${CMSSW_NAME}.tar.gz"

# ---- Build tarball if needed --------------------------------------------
if [ "$REBUILD_TAR" -eq 1 ] || [ ! -f "$TARBALL" ]; then
    echo "Building tarball $TARBALL ..."
    cd "$(dirname "$CMSSW_TOP")"
    tar --exclude="${CMSSW_NAME}/tmp" \
        --exclude="${CMSSW_NAME}/logs" \
        --exclude="${CMSSW_NAME}/src/production_tests/condor" \
        --exclude="${CMSSW_NAME}/src/production_tests/parquet_out" \
        --exclude="${CMSSW_NAME}/src/production_tests/test*.root" \
        --exclude=".git" \
        -czf "$TARBALL" "${CMSSW_NAME}"
    cd -
    echo "Tarball: $(du -h "$TARBALL" | cut -f1)"
else
    echo "Reusing existing tarball: $TARBALL ($(du -h "$TARBALL" | cut -f1))"
    echo "(pass --rebuild-tarball to force refresh)"
fi
echo

# ---- Verify proxy -------------------------------------------------------
if [ -z "${X509_USER_PROXY:-}" ] || [ ! -f "$X509_USER_PROXY" ]; then
    echo "ERROR: X509_USER_PROXY not set or file missing" >&2
    echo "  Run: voms-proxy-init -voms cms -valid 192:00" >&2
    exit 1
fi
PROXY_HOURS=$(voms-proxy-info -timeleft 2>/dev/null | awk '{print int($1/3600)}')
echo "Proxy at $X509_USER_PROXY (~${PROXY_HOURS} h left)"
echo

# ---- Ensure EOS dirs exist ----------------------------------------------
echo "Ensuring output dirs exist under ${OUTDIR}/{GSD,RECO,nanoML}"
for sub in GSD RECO nanoML; do
    if [[ "$OUTDIR" == /store/* || "$OUTDIR" == root://* ]]; then
        eos root://cmseos.fnal.gov mkdir -p "${OUTDIR}/${sub}" 2>/dev/null || true
    else
        mkdir -p "${OUTDIR}/${sub}"
    fi
done
echo

# ---- Build DAG ----------------------------------------------------------
cd "$SUBMIT_DIR"
mkdir -p logs

ETAG=$(printf "%.0f" "$ENERGY")
DAG="pipeline_${PARTNAME}_E${ETAG}.dag"
bash build_dag.sh \
    --energy "$ENERGY" \
    --nreplicas "$NREPLICAS" \
    --nevents "$NEVENTS" \
    --particle "$PARTICLE" \
    --partname "$PARTNAME" \
    --outdir "$OUTDIR" \
    --outfile "$DAG"

# ---- Submit -------------------------------------------------------------
echo
SCHEDD_ARG=""
if [ -n "$SCHEDD" ]; then
    SCHEDD_ARG="-name $SCHEDD"
fi

# The env -u block prevents cmsenv (if the user sourced it) from breaking
# condor_submit_dag via PYTHONHOME/PYTHONPATH.
echo "Submitting DAG..."
env -u PYTHONHOME -u PYTHONPATH -u LD_LIBRARY_PATH \
    condor_submit_dag $SCHEDD_ARG -f "$DAG"

echo
echo "Done. Monitor with:"
if [ -n "$SCHEDD" ]; then
    echo "  condor_q -name $SCHEDD -dag \$(whoami)"
else
    echo "  condor_q -dag \$(whoami)"
fi
echo "  tail -f ${DAG}.dagman.out"
echo
echo "Outputs land at:"
if [[ "$OUTDIR" == /store/* || "$OUTDIR" == root://* ]]; then
    echo "  root://cmseos.fnal.gov/${OUTDIR}/{GSD,RECO,nanoML}/${PARTNAME}_E${ETAG}_rep*.root"
else
    echo "  ${OUTDIR}/{GSD,RECO,nanoML}/${PARTNAME}_E${ETAG}_rep*.root"
fi
