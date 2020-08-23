# coding: utf-8

import FWCore.ParameterSet.Config as cms
from FWCore.ParameterSet.VarParsing import VarParsing
from reco_prodtools.templates.RECO_fragment import process

# option parsing
options = VarParsing('python')
options.setDefault('outputFile', 'file:partGun_PDGid22_x96_Pt1.0To100.0_RECO_1.root')
options.setDefault('inputFiles', "file://partGun_PDGid22_x96_Pt1.0To100.0_GSD_1.root")
options.setDefault('maxEvents', -1)
options.register('outputFileDQM', 'file:partGun_PDGid22_x96_Pt1.0To100.0_DQM_1.root',
    VarParsing.multiplicity.singleton, VarParsing.varType.string, 'path to the DQM output file')
options.parseArguments()

process.maxEvents.input = cms.untracked.int32(options.maxEvents)

# append the HGCTruthProducer to the recosim step
process.hgcTruthProducer = cms.EDProducer("HGCTruthProducer",
    # options
)
process.recosim_step += process.hgcTruthProducer

process.load("SimTracker.TrackAssociation.trackingParticleRecoTrackAsssociation_cfi")
process.hgcSimTruth = cms.EDProducer("HGCTruthProducer",
)

process.recosim_step += process.trackingParticleRecoTrackAsssociation
process.recosim_step += process.hgcSimTruth

#process.dump=cms.EDAnalyzer('EventContentAnalyzer')
#process.recosim_step += process.dump

# Input source
process.source.fileNames = cms.untracked.vstring(options.inputFiles)

# Output definition
process.FEVTDEBUGoutput.fileName = cms.untracked.string(
    options.__getattr__("outputFile", noTags=True))
process.FEVTDEBUGoutput.outputCommands.append("keep *_*G4*_*_*")
process.FEVTDEBUGoutput.outputCommands.append("keep *_trackingParticleRecoTrackAsssociation_*_*")
process.FEVTDEBUGoutput.outputCommands.append("keep *_MergedTrackTruth_*_*")
process.FEVTDEBUGoutput.outputCommands.append("keep *_hgcSimTruth_*_*")

if hasattr(process, "DQMoutput"):
    process.DQMoutput.fileName = cms.untracked.string(options.outputFileDQM)

