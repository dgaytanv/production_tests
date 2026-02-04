import FWCore.ParameterSet.Config as cms
from FWCore.ParameterSet.VarParsing import VarParsing
from Configuration.Eras.Era_Phase2C17I13M9_cff import Phase2C17I13M9
from Configuration.ProcessModifiers.ticl_v5_cff import ticl_v5

process = cms.Process('TICL', Phase2C17I13M9, ticl_v5)

# option parsing
options = VarParsing('python')
options.setDefault('outputFile', 'testNanoTICL_ML.root')
options.register("nThreads", 1, VarParsing.multiplicity.singleton, VarParsing.varType.int, "number of threads")
options.register("runPFTruth", 0, VarParsing.multiplicity.singleton, VarParsing.varType.int, "Don't run PFTruth (currently not working with pileup)")
options.parseArguments()

# Load necessary services and configurations
process.load('Configuration.StandardSequences.Services_cff')
process.load('SimGeneral.HepPDTESSource.pythiapdt_cfi')
process.load('FWCore.MessageService.MessageLogger_cfi')
process.load('Configuration.StandardSequences.MagneticField_cff')
process.load('Configuration.StandardSequences.Reconstruction_cff')
process.load('Configuration.StandardSequences.FrontierConditions_GlobalTag_cff')
process.load('Configuration.StandardSequences.EndOfProcess_cff')
process.load('Configuration.Geometry.GeometryExtendedRun4D110Reco_cff')
process.load('Configuration.Geometry.GeometryExtendedRun4D110_cff')
process.load('Configuration.EventContent.EventContent_cff')
process.load('SimGeneral.MixingModule.mixNoPU_cfi')

# Load HGCal-specific modules
process.load('SimCalorimetry.HGCalSimProducers.hgcHitAssociation_cfi')
process.load('SimCalorimetry.HGCalAssociatorProducers.LCToTSAssociator_cfi')
process.load('SimCalorimetry.HGCalAssociatorProducers.HitToTracksterAssociation_cfi')
process.load('SimCalorimetry.HGCalAssociatorProducers.hitToSimClusterCaloParticleAssociator_cfi')
process.load('SimCalorimetry.HGCalAssociatorProducers.SimClusterToCaloParticleAssociation_cfi')
process.load('RecoHGCal.TICL.ticlLayerTileProducer_cfi')
process.load('RecoHGCal.TICL.trackstersProducer_cfi')
process.load('RecoHGCal.TICL.filteredLayerClustersProducer_cfi')
process.load('RecoHGCal.TICL.SimTracksters_cff')

# Load NanoAOD modules
process.load('DPGAnalysis.HGCalNanoAOD.nanoHGCML_cff')

from Configuration.AlCa.GlobalTag import GlobalTag
process.GlobalTag = GlobalTag(process.GlobalTag, 'auto:phase2_realistic', '')

from RecoTracker.IterativeTracking.iterativeTk_cff import trackdnn_source
from RecoHGCal.TICL.customiseForTICLv5_cff import *
from RecoHGCal.TICL.ticlDumper_cff import ticlDumper

# Input source
process.source = cms.Source("PoolSource",
    fileNames = cms.untracked.vstring(options.inputFiles),
    secondaryFileNames = cms.untracked.vstring()
)

process.maxEvents = cms.untracked.PSet(
    input = cms.untracked.int32(options.maxEvents),
    output = cms.optional.untracked.allowed(cms.int32,cms.PSet)
)

process.options = cms.untracked.PSet(
    IgnoreCompletely = cms.untracked.vstring(),
    Rethrow = cms.untracked.vstring(),
    allowUnscheduled = cms.obsolete.untracked.bool,
    canDeleteEarly = cms.untracked.vstring(),
    emptyRunLumiMode = cms.obsolete.untracked.string,
    eventSetup = cms.untracked.PSet(
        forceNumberOfConcurrentIOVs = cms.untracked.PSet(
            allowAnyLabel_=cms.required.untracked.uint32
        ),
        numberOfConcurrentIOVs = cms.untracked.uint32(1)
    ),
    fileMode = cms.untracked.string('FULLMERGE'),
    forceEventSetupCacheClearOnNewRun = cms.untracked.bool(False),
    makeTriggerResults = cms.obsolete.untracked.bool,
    numberOfConcurrentLuminosityBlocks = cms.untracked.uint32(1),
    numberOfConcurrentRuns = cms.untracked.uint32(1),
    numberOfStreams = cms.untracked.uint32(0),
    numberOfThreads = cms.untracked.uint32(options.nThreads),
    printDependencies = cms.untracked.bool(False),
    sizeOfStackForThreadsInKB = cms.optional.untracked.uint32,
    throwIfIllegalParameter = cms.untracked.bool(True),
    wantSummary = cms.untracked.bool(False),
    TryToContinue = cms.untracked.vstring('ProductNotFound')
)

# Production Info
process.configurationMetadata = cms.untracked.PSet(
    annotation = cms.untracked.string('Merged TICL + NanoML configuration'),
    name = cms.untracked.string('Applications'),
    version = cms.untracked.string('$Revision: 1.19 $')
)

process.trackdnn_source = trackdnn_source

from SimCalorimetry.HGCalAssociatorProducers.LCToCPAssociation_cfi import layerClusterCaloParticleAssociation
from SimCalorimetry.HGCalAssociatorProducers.LCToSCAssociation_cfi import layerClusterSimClusterAssociation
process.layerClusterCaloParticleAssociationProducer = layerClusterCaloParticleAssociation.clone()
process.layerClusterSimClusterAssociationProducer = layerClusterSimClusterAssociation.clone()

# Specify where to look for simSiPixelDigis objects (from nanoML)
process.tpClusterProducer.pixelSimLinkSrc = cms.InputTag("simSiPixelDigis", "Pixel", "HLT")
process.tpClusterProducer.phase2OTSimLinkSrc = cms.InputTag("simSiPixelDigis", "Tracker", "HLT")

# Apply TICLv5 customization
process = customiseTICLv5FromReco(process, enableDumper=True)

# Handle PFTruth sequence based on option (from nanoML)
if not options.runPFTruth:
    process.pfTruth = cms.Sequence()
    process.trackSCAssocTable = cms.Sequence()

# TICLDumper configuration
process.ticlDumper = ticlDumper.clone(
    saveLCs=True,
    saveTICLCandidate=True,
    saveSimTICLCandidate=True,
    saveTracks=True,
    saveSuperclustering=False,
    saveRecoSuperclusters=False,
)

# Output TICL dumper to a separate file with _ticl suffix
outputFileName = options.__getattr__("outputFile", noTags=True)
ticlFileName = outputFileName.replace('.root', '_ticl.root')
process.TFileService = cms.Service("TFileService",
    fileName=cms.string(ticlFileName)
)

# NanoAOD Output - outputs to the SAME file name
process.NANOAODSIMoutput = cms.OutputModule("NanoAODOutputModule",
    compressionAlgorithm = cms.untracked.string('LZMA'),
    compressionLevel = cms.untracked.int32(9),
    dataset = cms.untracked.PSet(
        dataTier = cms.untracked.string('NANOAODSIM'),
        filterName = cms.untracked.string('')
    ),
    fileName = cms.untracked.string(options.__getattr__("outputFile", noTags=True)),
    outputCommands = process.NANOAODSIMEventContent.outputCommands
)

process.NANOAODSIMoutput.outputCommands.remove("keep edmTriggerResults_*_*_*")

# Omit genIso objects to avoid product not found error (from nanoML)
if hasattr(process, 'genParticleTable'):
    if hasattr(process.genParticleTable.externalVariables, 'iso'):
        del process.genParticleTable.externalVariables.iso

# Path and EndPath definitions
#process.nanoAOD_step = cms.Path(process.nanoHGCMLSequence)
#process.ticlDumper_step = cms.EndPath(process.ticlDumper)
#process.endjob_step = cms.EndPath(process.endOfProcess)
#process.NANOAODSIMoutput_step = cms.EndPath(process.NANOAODSIMoutput)

# Schedule definition - NanoML processing first, then TICL dumper, then output
#process.schedule = cms.Schedule(
#    process.nanoAOD_step,
#    process.ticlDumper_step,
#    process.endjob_step,
#    process.NANOAODSIMoutput_step
#)

# Path and EndPath definitions
process.nanoAOD_step = cms.Path(process.nanoHGCMLSequence)
process.endjob_step = cms.EndPath(process.endOfProcess)
process.NANOAODSIMoutput_step = cms.EndPath(process.NANOAODSIMoutput)

# Append to existing schedule (created by customiseTICLv5FromReco)
# DON'T create new schedule - this would erase TICL reconstruction paths
process.schedule.append(process.nanoAOD_step)
process.schedule.append(process.endjob_step)
process.schedule.append(process.NANOAODSIMoutput_step)


from PhysicsTools.PatAlgos.tools.helpers import associatePatAlgosToolsTask
associatePatAlgosToolsTask(process)

# Customisation from nanoML
from DPGAnalysis.HGCalNanoAOD.nanoHGCML_cff import customizeReco, customizeMergedSimClusters
process = customizeMergedSimClusters(process)
process = customizeReco(process)

# Add early deletion of temporary data products to reduce peak memory need
from Configuration.StandardSequences.earlyDeleteSettings_cff import customiseEarlyDelete
process = customiseEarlyDelete(process)

# End of configuration
