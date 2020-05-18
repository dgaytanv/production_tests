#!/bin/bash

maxEvents=10 #70
inputnumber=$1

finalfile="${inputnumber}_windowntup.root"
eosoutdir="/eos/cms/store/user/kelong/ML4Reco"

THISDIR=`pwd`
cmsswdir="/afs/cern.ch/user/k/kelong/work/ML4Reco/CMSSW_11_0_0_patch1/src"
cd $cmsswdir
eval `scramv1 runtime -sh`
cd $THISDIR

scriptdir="/afs/cern.ch/user/k/kelong/work/ML4Reco/CMSSW_11_0_0_patch1/src/production_tests"

cmsRun $scriptdir/GSD_GUN.py seed=$inputnumber outputFile="file:${inputnumber}_GSD.root" maxEvents=$maxEvents
echo "${inputnumber} GSD done"
cmsRun $scriptdir/RECO.py inputFiles="file://${inputnumber}_GSD.root" outputFile="file:${inputnumber}_RECO.root" outputFileDQM="file:${inputnumber}_DQM.root"
#rm -f "${inputnumber}_GSD.root" "${inputnumber}_DQM.root"
#echo "${inputnumber} RECO done"
#cmsRun $scriptdir/windowNTuple_cfg.py inputFiles="file://${inputnumber}_RECO.root" outputFile="file:${finalfile}"
#rm -f "${inputnumber}_RECO.root"
#echo "${inputnumber} window done"
#eoscp $finalfile $eosoutdir/$finalfile
#rm -f *.root
