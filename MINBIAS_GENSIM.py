# coding: utf-8
#
# MINBIAS_GENSIM.py — generate a minbias GEN-SIM file to be used as the PU
# library for GSD_GUN.py (via its `pu=<file>` VarParsing option). Reuses
# pepr's GSD_fragment for all reco/geometry/conditions plumbing; only the
# generator is swapped from FlatEtaRangeGunProducer to Pythia8's minbias
# filter (SoftQCD).
#
# Ported from mmarchegiani/hgcal_pu_production/cfg_gensim_D110.py
# (`thing=minbias` branch) but adapted for pre1/D121:
#   - geometry, era, and conditions are inherited from pepr's GSD_fragment,
#   - no cmsDriver.py step required at runtime.

import os
import math

import FWCore.ParameterSet.Config as cms
from FWCore.ParameterSet.VarParsing import VarParsing

# option parsing
options = VarParsing('python')
options.setDefault('outputFile', 'file:pileup_gensim.root')
options.setDefault('maxEvents', 10)
options.register("seed", 1, VarParsing.multiplicity.singleton, VarParsing.varType.int,
    "random seed")
options.register("nThreads", 1, VarParsing.multiplicity.singleton, VarParsing.varType.int,
    "number of threads")
options.register("useFineCalo", 0, VarParsing.multiplicity.singleton, VarParsing.varType.int,
    "use fine calorimeter segmentation (1=True, 0=False)")
options.parseArguments()

# Load the same GSD process fragment that GSD_GUN.py uses. This gives us
# geometry (Run4D121), era (Phase2C22I13M9), magnetic field, sim modules,
# and the FEVTDEBUG output module — everything except the generator.
if options.useFineCalo:
    from reco_prodtools.templates.GSDfineCalo_fragment import process
else:
    from reco_prodtools.templates.GSD_fragment import process

process.maxEvents.input = cms.untracked.int32(options.maxEvents)

# Random seeds (same convention as GSD_GUN.py: seed+1 to avoid the pepr
# fragment's default hard-coded seed value colliding when seed==0)
seed = int(options.seed) + 1
process.RandomNumberGeneratorService.generator.initialSeed = cms.untracked.uint32(seed)
process.RandomNumberGeneratorService.VtxSmeared.initialSeed = cms.untracked.uint32(seed)
process.RandomNumberGeneratorService.mix.initialSeed = cms.untracked.uint32(seed)

# Input source
process.source.firstLuminosityBlock = cms.untracked.uint32(seed)

# Output
process.FEVTDEBUGoutput.fileName = cms.untracked.string(
    options.__getattr__("outputFile", noTags=True))

# Keep the G4 sim products + edm associations needed by the mixing module
# downstream in GSD_GUN.py.
process.FEVTDEBUGoutput.outputCommands.append("keep *_*G4*_*_*")
process.FEVTDEBUGoutput.outputCommands.append("keep SimClustersedmAssociation_mix_*_*")
process.FEVTDEBUGoutput.outputCommands.append("keep CaloParticlesedmAssociation_mix_*_*")

# Replace the FlatEtaRangeGunProducer generator with the Pythia8 minbias
# filter. SoftQCD (non-diffractive + single + double diffractive) at
# 14 TeV, CP5 tune — same as mmarchegiani's cfg_gensim_D110.py.
from Configuration.Generator.Pythia8CommonSettings_cfi import pythia8CommonSettingsBlock
from Configuration.Generator.MCTunes2017.PythiaCP5Settings_cfi import pythia8CP5SettingsBlock

process.generator = cms.EDFilter(
    "Pythia8GeneratorFilter",
    maxEventsToPrint = cms.untracked.int32(1),
    pythiaPylistVerbosity = cms.untracked.int32(1),
    filterEfficiency = cms.untracked.double(1.0),
    pythiaHepMCVerbosity = cms.untracked.bool(False),
    comEnergy = cms.double(14000.),
    PythiaParameters = cms.PSet(
        pythia8CommonSettingsBlock,
        pythia8CP5SettingsBlock,
        processParameters = cms.vstring(
            'SoftQCD:nonDiffractive = on',
            'SoftQCD:singleDiffractive = on',
            'SoftQCD:doubleDiffractive = on',
        ),
        parameterSets = cms.vstring(
            'pythia8CommonSettings',
            'pythia8CP5Settings',
            'processParameters',
        )
    )
)

process.options.numberOfThreads = cms.untracked.uint32(options.nThreads)

# No pileup mixing here — this file IS the pileup library. GSD_GUN.py's
# mix module gets its inputs from mixNoPU_cfi during the minbias GENSIM.
process.load("SimGeneral.MixingModule.mixNoPU_cfi")
process.mix.digitizers = cms.PSet(process.theDigitizersValid)
process.mix.bunchspace = cms.int32(25)
process.mix.minBunch = cms.int32(-3)
process.mix.maxBunch = cms.int32(3)
