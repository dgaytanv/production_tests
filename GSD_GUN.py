# coding: utf-8

import os
import math

import FWCore.ParameterSet.Config as cms
from FWCore.ParameterSet.VarParsing import VarParsing

# option parsing
options = VarParsing('python')
options.setDefault('outputFile', 'file:partGun_PDGid22_x96_Pt1.0To100.0_GSD_1.root')
options.setDefault('maxEvents', 500)
options.register("pileup", 0, VarParsing.multiplicity.singleton, VarParsing.varType.int,
    "pileup")
options.register("seed", 1, VarParsing.multiplicity.singleton, VarParsing.varType.int,
    "random seed")
options.register("nThreads", 1, VarParsing.multiplicity.singleton, VarParsing.varType.int,
    "number of threads")
options.register("nParticles", 1, VarParsing.multiplicity.singleton, VarParsing.varType.int,
    "number of particles in gun")
options.parseArguments()
options.register("useFineCalo", 1, VarParsing.multiplicity.singleton, VarParsing.varType.int,
    "use fine calorimeter segmentation (1=True, 0=False)")
options.parseArguments()

# Import process based on useFineCalo flag
if options.useFineCalo:
    from reco_prodtools.templates.GSDfineCalo_fragment import process
else:
    from reco_prodtools.templates.GSD_fragment import process

process.maxEvents.input = cms.untracked.int32(options.maxEvents)

seed = int(options.seed)+1
# random seeds
process.RandomNumberGeneratorService.generator.initialSeed = cms.untracked.uint32(seed)
process.RandomNumberGeneratorService.VtxSmeared.initialSeed = cms.untracked.uint32(seed)
process.RandomNumberGeneratorService.mix.initialSeed = cms.untracked.uint32(seed)

# Input source
process.source.firstLuminosityBlock = cms.untracked.uint32(seed)

# Output definition
process.FEVTDEBUGoutput.fileName = cms.untracked.string(
    options.__getattr__("outputFile", noTags=True))

process.FEVTDEBUGoutput.outputCommands.append("keep *_*G4*_*_*")
process.FEVTDEBUGoutput.outputCommands.append("keep SimClustersedmAssociation_mix_*_*")
process.FEVTDEBUGoutput.outputCommands.append("keep CaloParticlesedmAssociation_mix_*_*")

# helper
def calculate_rho(z, eta):
    return z * math.tan(2 * math.atan(math.exp(-eta)))


process.generator = cms.EDProducer("FlatEtaRangeGunProducer",
    PGunParameters = cms.PSet(
    # particle ids
    PartID=cms.vint32(15), #(22, 22, 11,-11,211,-211,13,-13, 310, 130, 111, 311, 321, -321),
    # max number of particles to shoot at a time
    nParticles=cms.int32(options.nParticles),
    # shoot exactly the particles defined in particleIDs in that order
    exactShoot=cms.bool(False),
    # randomly shoot [1, nParticles] particles, each time randomly drawn from particleIDs
    randomShoot=cms.bool(False),
    # energy range
    MinE=cms.double(200.0),
    MaxE=cms.double(200.0),
    # phi range
    MinPhi=cms.double(-math.pi),
    MaxPhi=cms.double(math.pi),
    # eta range
    MinEta=cms.double(1.7),
    MaxEta=cms.double(2.7),
    ),
    AddAntiParticle = cms.bool(False),
    debug=cms.untracked.bool(True),
    firstRun=cms.untracked.uint32(1)
)

#process.generator = cms.EDProducer("CloseByParticleGunProducer",
#    PGunParameters = cms.PSet(PartID = cms.vint32(22), # Since I'm shooting antiparticles, I'm putting gamma and K0 twice in the vector
#        VarMin = cms.double(100.0),
#        VarMax = cms.double(100.0),
#        ControlledByEta = cms.bool(False),
#        MaxVarSpread = cms.bool(False),
#        RMin = cms.double(60),
#        RMax = cms.double(120),
#        ZMin = cms.double(320), #320#-410
#        ZMax = cms.double(321),
#        Delta = cms.double(0),
#        Pointing = cms.bool(True),
#        Overlapping = cms.bool(False),
#        RandomShoot = cms.bool(False),
#        NParticles = cms.int32(options.nParticles),
#        MaxEta = cms.double(2.7),
#        MinEta = cms.double(1.7), #-2.7
#        MaxPhi = cms.double(3.14159265359),
#        MinPhi = cms.double(-3.14159265359)
#    ),
#    Verbosity = cms.untracked.int32(0),
#    firstRun = cms.untracked.uint32(1),
#    AddAntiParticle = cms.bool(False),
#    psethack = cms.string('Random particles in front of HGCAL')
#)

process.options.numberOfThreads=cms.untracked.uint32(options.nThreads)

#load and configure the appropriate pileup modules
if options.pileup > 0:
    process.load("SimGeneral.MixingModule.mix_POISSON_average_cfi")
    process.mix.input.nbPileupEvents.averageNumber = cms.double(options.pileup)
    # process.mix.input.fileNames = cms.untracked.vstring(["/store/relval/CMSSW_10_6_0_patch2/RelValMinBias_14TeV/GEN-SIM/106X_upgrade2023_realistic_v3_2023D41noPU-v1/10000/F7FE3FE9-565B-544A-855E-902BA4E3C5FD.root', '/store/relval/CMSSW_10_6_0_patch2/RelValMinBias_14TeV/GEN-SIM/106X_upgrade2023_realistic_v3_2023D41noPU-v1/10000/82584FBA-A1E6-DF48-99BA-B1759C3A190F.root', '/store/relval/CMSSW_10_6_0_patch2/RelValMinBias_14TeV/GEN-SIM/106X_upgrade2023_realistic_v3_2023D41noPU-v1/10000/F806295A-492F-EF4F-9D91-15DA8769DD72.root', '/store/relval/CMSSW_10_6_0_patch2/RelValMinBias_14TeV/GEN-SIM/106X_upgrade2023_realistic_v3_2023D41noPU-v1/10000/6FCA2E1D-D1E2-514B-8ABA-5B71A2C1E1B3.root', '/store/relval/CMSSW_10_6_0_patch2/RelValMinBias_14TeV/GEN-SIM/106X_upgrade2023_realistic_v3_2023D41noPU-v1/10000/287275CC-953A-0C4C-B352-E39EC2D571F0.root', '/store/relval/CMSSW_10_6_0_patch2/RelValMinBias_14TeV/GEN-SIM/106X_upgrade2023_realistic_v3_2023D41noPU-v1/10000/657065A5-F35B-3147-AED9-E4ACA915C982.root', '/store/relval/CMSSW_10_6_0_patch2/RelValMinBias_14TeV/GEN-SIM/106X_upgrade2023_realistic_v3_2023D41noPU-v1/10000/2C56BC73-5687-674C-8684-6C785A88DB78.root', '/store/relval/CMSSW_10_6_0_patch2/RelValMinBias_14TeV/GEN-SIM/106X_upgrade2023_realistic_v3_2023D41noPU-v1/10000/B96F4064-156C-5E47-90A0-07475310157A.root', '/store/relval/CMSSW_10_6_0_patch2/RelValMinBias_14TeV/GEN-SIM/106X_upgrade2023_realistic_v3_2023D41noPU-v1/10000/2564B36D-A0DB-6C42-9105-B1CFF44F311D.root', '/store/relval/CMSSW_10_6_0_patch2/RelValMinBias_14TeV/GEN-SIM/106X_upgrade2023_realistic_v3_2023D41noPU-v1/10000/2CB8C960-47C0-1A40-A9F7-0B62987097E0.root"])  # noqa: E501
    local_pu_dir = "/home/k/kelong/work/ML4Reco/CMSSW_12_0_0/src/production_tests/pileup"
    process.mix.input.fileNames = cms.untracked.vstring([
        "file://" + os.path.abspath(os.path.join(local_pu_dir, elem))
        for elem in os.listdir(local_pu_dir)
        if elem.endswith(".root")
    ])
else:
    process.load("SimGeneral.MixingModule.mixNoPU_cfi")
    process.mix.digitizers = cms.PSet(process.theDigitizersValid)
    # I don't think this matters, but just to be safe...
    process.mix.bunchspace = cms.int32(25)
    process.mix.minBunch = cms.int32(-3)
    process.mix.maxBunch = cms.int32(3)

