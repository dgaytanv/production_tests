#!/bin/bash
# Args: STAGE PARTICLE ENERGY SEED REPLICA NEVENTS OUTDIR PARTNAME
set -eu -o pipefail

STAGE="${1:?}"; PARTICLE="${2:?}"; ENERGY="${3:?}"; SEED="${4:?}"
REPLICA="${5:?}"; NEVENTS="${6:?}"; OUTDIR="${7:?}"; PARTNAME="${8:?}"

ETAG=$(printf "%.0f" "$ENERGY")
TAG="${PARTNAME}_E${ETAG}_rep${REPLICA}"
echo "=== $(hostname) $(date -u +%FT%TZ) STAGE=$STAGE TAG=$TAG OUTDIR=$OUTDIR ==="

source /cvmfs/cms.cern.ch/cmsset_default.sh
tar -xzf CMSSW_*.tar.gz
CMSSW_DIR=$(find . -maxdepth 2 -name "CMSSW_*_pre1" -type d | head -1)
[ -n "$CMSSW_DIR" ] || { echo "no CMSSW dir"; ls; exit 1; }
cd "$CMSSW_DIR/src"; scram b ProjectRename 2>&1 | tail -3 || true
eval $(scramv1 runtime -sh)
CFG_DIR="$CMSSW_BASE/src/production_tests"
cd -

is_remote() { [[ "$1" == /store/* || "$1" == root://* ]]; }
fetch() {
    local src="$1" dst="./$(basename "$1")"
    if is_remote "$src"; then
        [[ "$src" == /store/* ]] && src="root://cmseos.fnal.gov/$src"
        xrdcp -f "$src" "$dst"
    else
        cp -f "$src" "$dst"
    fi
}
stage_out() {
    local file="$1" dest="$2"
    if is_remote "$dest"; then
        local url="$dest"; [[ "$dest" == /store/* ]] && url="root://cmseos.fnal.gov/$dest"
        eos root://cmseos.fnal.gov mkdir -p "$dest" 2>/dev/null || true
        xrdcp -f "$file" "$url/$(basename "$file")"
    else
        mkdir -p "$dest"
        cp -f "$file" "$dest/$(basename "$file")"
    fi
}

case "$STAGE" in
    gsd)
        OUT="${TAG}_GSD.root"
        cmsRun "${CFG_DIR}/GSD_GUN.py" seed="$SEED" particle="$PARTICLE" energy="$ENERGY" maxEvents="$NEVENTS" outputFile="$OUT"
        DEST="${OUTDIR}/GSD" ;;
    reco)
        IN="${TAG}_GSD.root"; OUT="${TAG}_RECO.root"
        fetch "${OUTDIR}/GSD/${IN}"
        cmsRun "${CFG_DIR}/RECO.py" inputFiles="file:${IN}" outputFile="$OUT"
        rm -f "$IN"; DEST="${OUTDIR}/RECO" ;;
    nano)
        IN="${TAG}_RECO.root"; OUT="${TAG}_nanoML.root"
        fetch "${OUTDIR}/RECO/${IN}"
        cmsRun "${CFG_DIR}/nanoML_cfg.py" inputFiles="file:${IN}" outputFile="$OUT"
        rm -f "$IN"; DEST="${OUTDIR}/nanoML" ;;
    *) echo "bad STAGE $STAGE"; exit 1 ;;
esac

[ -s "$OUT" ] || { echo "ERROR: $OUT missing"; exit 2; }
stage_out "$OUT" "$DEST"
rm -f "$OUT"
echo "=== DONE $(date -u +%FT%TZ) ==="
