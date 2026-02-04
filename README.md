# production_tests

This is an updated fork of https://github.com/kdlong/production_tests, which are simple productions scripts based on the HGCAL Reco prod tools: https://github.com/CMS-HGCAL/reco-prodtools. 


NOTE: The NanoML ntuples require pepr_CMSSW_15_0_0 or pepr_CMSSW_15_1_1 (some older pepr_CMSSW_X_Y_Z branches are available, if you prefer, in the original cms-pepr repo at https://github.com/cms-pepr/cmssw/tree/pepr_CMSSW_12_6_0_pre2).

## Setup
A simple recipe in CMSSW_15_1_0 is:

```shell
version=CMSSW_15_1_0
cmsrel $version
cd $version/src
cmsenv
git cms-init
git cms-merge-topic dgaytanv:pepr_${version}
scram b -j 12

# Note: Here follow the same instructions as in the main reco-prodtools repo, but use the D110 geometry
# Create RECO fragment
git clone git@github.com:dgaytanv/reco-prodtools.git reco_prodtools
cd reco_prodtools/templates/python
./produceSkeletons_D110_v2.sh
cd ../../..
scram b

# Now copy this repo for nanoML production
git clone git@github.com:dgaytanv/production_tests.git
cd production_tests
```

Before running the GSD step, you should edit the [GSD_GUN.py](GSD_GUN.py) file to select the number of particles, IDs, and energy range you would like to generate. To activate or deactivate fineCalo, use the useFineCalo flag (by default useFineCalo=1). Then to run the GSD step you do (replace the X with an actual numeric seed)

```cmsRun GSD_GUN.py seed=X outputFile=testGSD.root```

Then process the output of this using the RECO config

```cmsRun RECO.py inputFiles=file:testGSD.root outputFile=testRECO.root```

For the NanoML ntuples, you should use the configurations [nanoML_cfg.py](nanoML_cfg.py) for samples with RECO content.

<!-- (Conversely, use [nanoMLGSD_cfg.py](nanoMLGSD_cfg) if you have a file with only GEN content. Several aspects of this are configurable (store simclusters or not, store merged simclusters or not). configureX functions in the configuration take care of this. This will be made configurable at some point, but open the configuration file and edit to include or not these functions for now. Note: at the moment, only files with RECO content have been tested for CMSSW_15_0_0 and newer.) -->

Then you run them in the expected way

```cmsRun nanoML_cfg.py inputFiles=file:testRECO.root outputFile=testNanoML.root```

## Save TICL reconstruction
To save the output of the TICL reconstruction, run the RECO step with the useTICL flag (by default useTICL=0)

```cmsRun RECO.py inputFiles=file:testGSD.root outputFile=testRECO-TICL.root useTICL=1```


To produce a rootfile containing the TICL candidates information ONLY, use the RECO output as input for [nanoTICL_cfg.py](nanoTICL_cfg.py)

```cmsRun nanoTICL_cfg.py inputFiles=file:testRECO-TICL.root outputFile=testTICL.root```

To produce the two rootfiles at the same time, i.e one with the nanoML output and one with the TICL output, run the merged TICL-ML configuration [nanoTICL-ML_cfg.py](nanoTICL-ML_cfg.py)

```cmsRun nanoTICL-ML_cfg.py inputFiles=file:testRECO-TICL.root outputFile=output.root```

This creates two files: ```output.root``` and ```output_ticl.root```.
