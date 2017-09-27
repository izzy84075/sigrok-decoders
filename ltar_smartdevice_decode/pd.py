## Copyright (C) 2017 Ryan "Izzy" Bales <izzy84075@gmail.com>

# LTAR SmartDevice decoder

import sigrokdecode as srd

class SamplerateError(Exception):
    pass

btype = {
	0x02: 'TAGGER-STATUS',
}

class Decoder(srd.Decoder):
	api_version = 3
	id = 'ltar_smartdevice_decode'
	name = 'LTAR SmartDevice Decode'
	longname = 'LTAR SmartDevice Decode'
	desc = 'A decoder for the LTAR SmartDevice protocol'
	license = 'unknown'
	inputs = ['ltar_smartdevice']
	outputs = ['ltar_smartdevice_decode']
	annotations = (
		('frame-name', 'Frame Name'),
		('frame-error', 'Frame Error'),
		('frame-bit-names', 'Frame Bit Names'),
		('frame-bits-data', 'Frame Bits Data'),
		('block-error', 'Block Errors'),
		('block-data', 'Block Data'),
	)
	annotation_rows = (
		('frame-name', 'Frame name', (0,)),
		('frame-error', 'Frame errors', (1,)),
		('frame-bit-names', 'Frame bit names', (2,)),
		('frame-bits-data', 'Frame bits data', (3,)),
		('block-errors', 'Block errors', (4,)),
	)
	
	def putBlockLengthError(self, blockstartsample, blockendsample):
		self.put(blockstartsample, blockendsample, self.out_ann,
				[4, ['Invalid block length', 'Invalid B length', 'E: B length', 'E: BL']])
	
	def checkBlockLength(self, btype, length, blockstartsample, blockendsample):
		if btype == 0x02:
			if length != 11:
				self.putBlockLengthError(blockstartsample, blockendsample)
	
	def putBlockCSumError(self, blockstartsample, blockendsample):
		self.put(blockstartsample, blockendsample, self.out_ann,
				[4, ['Invalid block checksum', 'Invalid B CSum', 'E: B CSum', 'E: B CS']])
	
	def checkBlockCSum(self, blockdata, blockstartsample, blockendsample):
		temp = 0xFF
		for item in blockdata:
			#print(item)
			temp = temp - item[1]
		if temp < 0:
			temp = temp * -1
		temp = temp & 0xFF
		
		if temp != 0:
			self.putBlockCSumError(blockstartsample, blockendsample)
		else:
			self.put(blockdata[len(blockdata)-1][0][1][0], blockdata[len(blockdata)-1][0][8][1], self.out_ann,
				[3, ['Valid Checksum', 'Valid CSum']])
	
	def putBlockType(self, frame):
		self.put(frame[0][1][0], frame[0][8][1], self.out_ann,
				[0, ['Block Type', 'BType', 'BT']])
		self.put(frame[0][1][0], frame[0][8][1], self.out_ann,
				[2, ['Block Type', 'BType', 'BT']])
		if btype.get(frame[1]) != None:
			self.put(frame[0][1][0], frame[0][8][1], self.out_ann,
					[3, ['%s (0x%02X)' % (btype[frame[1]], frame[1])]])
		else:
			self.put(frame[0][1][0], frame[0][8][1], self.out_ann,
					[3, ['Unknown Block Type (0x%02X)' % frame[1], 'Unknown BType (0x%02X)' % frame[1], 'Unk BType (0x%02X)' % frame[1], 'E: BT 0x%02X' % frame[1]]])
	
	def putCSum(self, frame):
		self.put(frame[0][1][0], frame[0][8][1], self.out_ann,
				[0, ['Block Checksum', 'B Checksum', 'B CSum', 'B CS']])
		self.put(frame[0][1][0], frame[0][8][1], self.out_ann,
				[2, ['Block Checksum', 'B Checksum', 'B CSum', 'B CS']])
	
	def putData(self, btype, index, frame):
		self.put(frame[0][1][0], frame[0][8][1], self.out_ann,
				[0, ['Block Data %d' % index, 'BData%d' % index]])
	
	def __init__(self):
		self.state = 'IDLE'
	
	def start(self):
		#self.out_python = self.register(srd.OUTPUT_PYTHON)
		self.out_ann = self.register(srd.OUTPUT_ANN)
	
	def decode(self, startsample, endsample, data):
		
		garbage, data = data
		
		length = len(data)
		btype = data[0][1]
		blockstartsample = startsample
		blockendsample = endsample
		
		self.checkBlockLength(btype, length, blockstartsample, blockendsample)
		
		self.checkBlockCSum(data, blockstartsample, blockendsample)
		
		for index, frame in enumerate(data):
			if index == 0:
				self.putBlockType(frame)
			elif index == (length-1):
				self.putCSum(frame)
			else:
				dataCount = index - 1
				self.putData(btype, dataCount, frame)
				