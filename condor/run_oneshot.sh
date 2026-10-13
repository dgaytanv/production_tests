#!/bin/bash
# run_oneshot.sh — one LPC HTCondor job of the one-shot chain (see submit_oneshot.sh).
#
# Unpacks the CMSSW tarball shipped with the job, runs scripts/generate.sh for one
# batch and copies everything it wrote (ROOT files, parquet, logs) to EOS. The
# output is staged out even when generate.sh fails, so its logs can be inspected.
#
# Usage: run_oneshot.sh <eos_dir> <n_events> <generate.sh options...>
#   e.g. run_oneshot.sh /store/user/$USER/sample/photons_E10/batch0 250 \
#            --particle 22 --gun closeBy --minE 10 --maxE 10 --seed 2210010
set -eu -o pipefail

EOS_DIR="$1"; NEVENTS="$2"; shift 2
EOS_HOST=cmseos.fnal.gov

echo "=== $(hostname) $(date -u +%FT%TZ) n_events=$NEVENTS -> $EOS_DIR"
echo "    generate.sh options: $*"

# ---- CMSSW area from the tarball ----------------------------------------------
source /cvmfs/cms.cern.ch/cmsset_default.sh
TARBALL=$(ls CMSSW_*.tar.gz 2>/dev/null | head -1)
[ -n "$TARBALL" ] || { echo "ERROR: no CMSSW_*.tar.gz in the sandbox" >&2; ls; exit 1; }
tar -xzf "$TARBALL"
CMSSW_DIR=$(find . -maxdepth 1 -name "CMSSW_*" -type d | head -1)
pushd "$CMSSW_DIR/src" >/dev/null
scram b ProjectRename 2>&1 | tail -3 || true
eval "$(scramv1 runtime -sh)"
popd >/dev/null

# ---- python for the parquet step ------------------------------------------------
# The scripts default to an apptainer image, which is not used inside batch jobs;
# PARQUET_PYTHON makes them use this python3 (uproot/awkward/pyarrow from the LCG
# view) instead, run with a clean environment so that cmsenv does not leak in.
cat > lcg_python3 <<'EOF'
#!/bin/bash
exec env -i HOME="$HOME" PATH=/usr/bin:/bin bash -c \
    'source /cvmfs/sft.cern.ch/lcg/views/LCG_109/x86_64-el9-gcc13-opt/setup.sh >/dev/null && exec python3 "$@"' \
    python3 "$@"
EOF
chmod +x lcg_python3
export PARQUET_PYTHON="$PWD/lcg_python3"

# ---- the chain ------------------------------------------------------------------
OUT="$PWD/out"
rc=0
bash "$CMSSW_BASE/src/production_tests/scripts/generate.sh" "$OUT" "$NEVENTS" "$@" || rc=$?

# ---- stage out ------------------------------------------------------------------
xrd_retry() {
    local n
    for n in 1 2 3; do
        xrdcp -f -p "$@" && return 0
        echo "xrdcp attempt $n failed, retrying in 30 s" >&2
        sleep 30
    done
    return 1
}
if [ -d "$OUT" ]; then
    (cd "$OUT" && find . -type f) | while read -r f; do
        xrd_retry "$OUT/$f" "root://${EOS_HOST}/${EOS_DIR}/${f#./}"
    done
    echo "staged out $(cd "$OUT" && find . -type f | wc -l) files to $EOS_DIR"
fi
echo "=== DONE $(date -u +%FT%TZ) generate.sh exit code $rc"
exit "$rc"
