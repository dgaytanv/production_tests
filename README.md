# production_tests — CMSSW_20_0_0_pre1 branch

Simple production scripts for HGCAL Phase 2 studies on the pepr fork of
CMSSW_20_0_0_pre1 with the `Run4D121` geometry. Fork of
[kdlong/production_tests](https://github.com/kdlong/production_tests),
adapted for pre1 and the new default TICL reconstruction.

For the `CMSSW_15_1_0` / `Run4D110` version, see the `master` branch.

## Setup

```shell
export SCRAM_ARCH=el9_amd64_gcc13
version=CMSSW_20_0_0_pre1
cmsrel $version
cd $version/src
cmsenv
git cms-init -y
git cms-merge-topic dgaytanv:pepr_${version}
scram b -j 4      # -j 12 can OOM on cmslpc

# Reco fragments
git clone git@github.com:dgaytanv/reco-prodtools.git reco_prodtools
cd reco_prodtools/templates/python
./produceSkeletons_D121.sh
cd ../../..

# This repo (pre1_D121 branch)
git clone -b pre1_D121 git@github.com:dgaytanv/production_tests.git
cd production_tests
```

## Workflow

Three sequential `cmsRun` stages produce a nanoAOD flat ntuple with the
full HGCAL truth chain, TICL reconstruction, and their associations.

### 1. GSD (Generate → Sim → Digi)

`GSD_GUN.py` fires a configurable particle gun into HGCAL and runs
GEN + SIM + DIGI. Before running, edit the file to set particle IDs,
energy range, and eta range. `useFineCalo=1` (default) enables the
fineCalo boundary-crossing SimCluster/CaloParticle producer.

```shell
cmsRun GSD_GUN.py seed=1 outputFile=testGSD.root
```

Options:
- `seed=N` — random seed and first lumiBlock (required for unique output)
- `nParticles=N` — particles per event
- `useFineCalo={0,1}` — fineCalo on/off
- `pileup=N` — average PU (0 = no PU, uses `mixNoPU_cfi`)
- `maxEvents=N`, `nThreads=N`

### 2. RECO (Reconstruction)

`RECO.py` runs standard Phase 2 reconstruction on GSD output. TICL is
the default reco path in pre1, so all trackster collections
(`ticlTrackstersCLUE3DHigh`, `ticlTrackstersRecovery`,
`ticlTracksterLinks`, `ticlTracksterLinksSuperclusteringDNN`) and the
final `ticlCandidate` are always in the output.

```shell
cmsRun RECO.py inputFiles=file:testGSD.root outputFile=testRECO.root
```

Options:
- `useTICL={0,1}` — kept for CLI compatibility with the 15_1_0 branch,
  no-op in pre1. TICL is always on.

The RECO output also runs the pepr `SimClusterMerger` (mergedSimClusters
alongside legacy SimClusters and boundary/CaloParticle SimClusters) and
the standard HGCAL associations (LC↔CP, LC↔SC).

### 3. nanoML (flat ntuples)

`nanoML_cfg.py` reads RECO output and produces a nanoAOD flat file with
372 branches covering GEN, sim truth, HGCAL rechits, layer clusters,
tracksters, and TICLCandidates, plus their pairwise index associations.

```shell
cmsRun nanoML_cfg.py inputFiles=file:testRECO.root outputFile=testNanoML.root
```

Options:
- `runPFTruth={0,1}` — PFTruth sequence (currently broken with pileup).

## Nano output — the RecHit → TICLCand chain

The chain from RecHits to TICLCandidates is available via three index
associations in the flat tree, plus per-object kinematic tables.
