## Copyright (C) 2017 Ryan "Izzy" Bales <izzy84075@gmail.com>

# Recoil laser tag IR protocol decoder

import sigrokdecode as srd

class SamplerateError(Exception):
    pass

class Decoder(srd.Decoder):
	api_version = 3
	id = 'ltar_smartdevice'
	name = 'LTAR SmartDevice'
	longname = 'LTAR SmartDevice'
	desc = 'A decoder for the LTAR laser tag blaster\'s Smart Device protocol'
	license = 'unknown'
	inputs = ['afsk_bits']
	outputs = ['ltar_smartdevice']
	annotations = (
		('bit-start', 'Start Bit'),
		('bit-data', 'Data Bit'),
		('bit-stop', 'Stop Bit'),
		('bit-spacer', 'Spacer Bit'),
		('bit-blockend', 'Block Stop Bit'),
		('frame', 'Data frame'),
		('frame-error', 'Framing error'),
		('block', 'Data block'),
	)
	annotation_rows = (
		('bits', 'Bits', (0, 1, 2, 3, 4)),
		('frames', 'Frames', (5, 6,)),
		('blocks', 'Blocks', (7,)),
	)
	
	def putbitstart(self, startsample, endsample):
		self.put(startsample, endsample, self.out_ann,
				[0, ['Start Bit', 'Start B', 'Start']])
	
	def putbitdata(self, startsample, endsample, bitdata):
		self.put(startsample, endsample, self.out_ann,
				[1, ['%d' % bitdata]])
	
	def putbitstop(self, startsample, endsample):
		self.put(startsample, endsample, self.out_ann,
				[2, ['Stop Bit', 'Stop B', 'Stop']])
	
	def putbitspacer(self, startsample, endsample):
		self.put(startsample, endsample, self.out_ann,
				[3, ['Spacer Bit', 'Spacer']])
	
	def putbitblockend(self, startsample, endsample):
		self.put(startsample, endsample, self.out_ann,
				[4, ['Block Stop', 'Block']])
	
	def putframe(self, currentframedata, data):
		self.put(currentframedata[0][0], currentframedata[len(currentframedata)-1][1], self.out_ann,
				[5, ['Data frame: 0x%02X' % data, 'Data: 0x%02X' % data, 'D 0x%02X' % data]])
	
	def putframingerror(self, currentframedata):
		self.put(currentframedata[0][0], currentframedata[len(currentframedata)-1][1], self.out_ann,
				[6, ['Data framing error', 'Framing error', 'Frame Error', 'FE']])
	
	def putblock(self, currentblockdata, endsample):
		self.put(currentblockdata[0][0][0][0], endsample, self.out_ann,
				[7, ['Block, %d frames' % len(currentblockdata), 'B %d' % len(currentblockdata)]])
	
	def __init__(self):
		self.state = 'IDLE'
		self.framestartsample = self.frameendsample = 0
		self.currentframedata = []
		self.blockstartsample = self.blockendsample = 0
		self.currentblockdata = []
	
	def start(self):
		self.out_python = self.register(srd.OUTPUT_PYTHON)
		self.out_ann = self.register(srd.OUTPUT_ANN)
	
	def decode(self, startsample, endsample, afskdata):
		datatype, argument = afskdata
		
		if datatype == 'BIT':
			#A probably-valid data bit!
			if self.state == 'IDLE':
				if argument == 0:
					#Start bit!
					self.putbitstart(startsample, endsample)
					self.currentframedata = []
					self.currentframedata.append([startsample, endsample, argument])
					self.state = 'DATA'
			elif self.state == 'DATA':
				#Capture 8 data bits
				self.putbitdata(startsample, endsample, argument)
				self.currentframedata.append([startsample, endsample, argument])
				if len(self.currentframedata) == 9:
					self.state = 'FRAMESTOP'
			elif self.state == 'FRAMESTOP':
				if argument == 1:
					#End of a data frame
					self.putbitstop(startsample, endsample)
					self.currentframedata.append([startsample, endsample, argument])
					
					data = (self.currentframedata[8][2] << 7) | (self.currentframedata[7][2] << 6) | (self.currentframedata[6][2] << 5) | (self.currentframedata[5][2] << 4) | (self.currentframedata[4][2] << 3) | (self.currentframedata[3][2] << 2) | (self.currentframedata[2][2] << 1) | self.currentframedata[1][2]
					
					self.putframe(self.currentframedata, data)
					self.currentblockdata.append([self.currentframedata, data])
					self.state = 'FRAMESTOP2'
				else:
					#Framing error!
					self.putframingerror(self.currentframedata)
					self.currentframedata = []
					if len(self.currentblockdata) != 0:
						self.putblockerror(self.currentblockdata)
						self.currentblockdata = []
					self.state = 'IDLE'
			elif self.state == 'FRAMESTOP2':
				if argument == 1:
					#Optional spacer bit between frames.
					self.putbitspacer(startsample, endsample)
					self.state = 'BLOCKSTOP'
				else:
					#Start bit of another frame
					self.putbitstart(startsample, endsample)
					self.currentframedata = []
					self.currentframedata.append([startsample, endsample, argument])
					self.state = 'DATA'
			elif self.state == 'BLOCKSTOP':
				if argument == 1:
					#End of a block!
					self.putbitblockend(startsample, endsample)
					self.putblock(self.currentblockdata, endsample)
					self.currentblockdata = []
					self.state = 'IDLE'
				else:
					#Start bit of another frame
					self.putbitstart(startsample, endsample)
					self.currentframedata = []
					self.currentframedata.append([startsample, endsample, argument])
					self.state = 'DATA'
		elif datatype == 'ERROR':
			if argument == 'PHASE':
				#Resynced to the proper phase of the signal. Abort all current decodes.
				argument = argument
			elif argument == 'INVALID':
				#A cycle that doesn't match our AFSK settings. Abort all current decodes.
				argument = argument