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
	inputs = ['logic']
	outputs = ['ltar_smartdevice']
	channels = (
		{'id': 'audio', 'name': 'audio', 'desc': 'Audio stream from the LTAR'},
	)
	options = (
		{'id': 'devicetype', 'desc': 'Blaster or SmartDevice', 'default': 'blaster',
			'values': ('blaster', 'smartdevice')},
	)
	annotations = (
		('bit-raw', 'Raw Bit'),
		('bit-start', 'Start Bit'),
		('bit-data', 'Data Bit'),
		('bit-stop', 'Stop Bit'),
		('frame', 'Data frame'),
		('block', 'Data block'),
	)
	annotation_rows = (
		('raw-bits', 'Raw Bits', (0,)),
		('bit-meanings', 'Bits', (1, 2, 3,)),
		('frames', 'Frames', (4,)),
		('blocks', 'Blocks', (5,)),
	)
	
	def putbitraw(self):
		self.put(self.twoedgesagosample, self.currentedgesample, self.out_ann,
				[0, ['%d' % self.lastbit]])
	
	def putbitstart(self):
		self.put(self.twoedgesagosample, self.currentedgesample, self.out_ann,
				[1, ['Start Bit', 'Start B', 'Start']])
	
	def putbitdata(self):
		self.put(self.twoedgesagosample, self.currentedgesample, self.out_ann,
				[2, ['%d' % self.lastbit]])
	
	def putbitstop(self):
		self.put(self.twoedgesagosample, self.currentedgesample, self.out_ann,
				[3, ['Stop Bit', 'Stop B', 'Stop']])
				
	def putframe(self):
		self.put(self.framestartsample, self.frameendsample, self.out_ann,
				[4, ['Data frame: 0x%02X' % self.data, 'Data: 0x%02X' % self.data, 'D 0x%02X' % self.data]])
	
	def putblock(self):
		self.put(self.blockstartsample, self.blockendsample, self.out_ann,
				[5, ['Block', 'B']])
	
	def __init__(self):
		self.state = 'IDLE'
		self.lastbit = None
		self.bitstartsample = self.bitendsample = self.framestartsample = self.frameendsample = self.blockstartsample = self.blockendsample = self.twoedgesagosample = self.oneedgeagosample = self.currentedgesample = self.lastcycletype = self.cycletype = self.count = None
	
	def start(self):
		self.out_python = self.register(srd.OUTPUT_PYTHON)
		self.out_ann = self.register(srd.OUTPUT_ANN)
		self.devicetype = 0 if self.options['devicetype'] == 'blaster' else 1
		
		if self.devicetype == 0:
			self.margin = int(self.samplerate * 0.0000625) - 1 # 62.5us
			
			self.activehalfcycle = int(self.samplerate * 0.000125) - 1 #125us
			self.inactivehalfcycle = int(self.samplerate * 0.000250) - 1 #250us
		else:
			self.margin = int(self.samplerate * 0.0000565) - 1 #56.5us
			
			self.activehalfcycle = int(self.samplerate * 0.000113) - 1 #113us
			self.inactivehalfcycle = int(self.samplerate * 0.000227) - 1 #227us
	
	def metadata(self, key, value):
		if key == srd.SRD_CONF_SAMPLERATE:
			self.samplerate = value
			if self.samplerate < 16000:
				raise SamplerateError('Samplerate too low to decode.')
	
	def handle_bit(self, tick):
		self.lastbit = None
		#if tick in range(self.dazero - self.margin, self.dazero + self.margin):
		#	self.lastbit = 0
		#elif tick in range(self.daone - self.margin, self.daone + self.margin):
		#	self.lastbit = 1
		
		#print('Processing bit of', tick, 'length.')
		
		if tick in range(self.dazero - self.margin, self.dazero + self.margin):
			self.lastbit = 0
		elif tick in range(self.daone - self.margin, self.daone + self.margin):
			self.lastbit = 1
		
		if self.lastbit in (0, 1):
			self.putbit()
			self.data = (self.data << 1)
			self.data |= self.lastbit
			#self.data = self.data + str(self.lastbit)
			self.count = self.count + 1
		
	
	def decode(self):
		if not self.samplerate:
			raise SamplerateError('Cannot decode without samplerate.')
		
		while True:
			#Save the most recent edge sample for the next length
			self.twoedgesagosample = self.oneedgeagosample
			self.oneedgeagosample = self.currentedgesample
			#Save the last cycle type
			self.lastcycletype = self.cycletype
			
			#Wait for any edge
			(self.audio,) = self.wait({0: 'e'})
			#self.log(5, 'Found edge at sample ' + self.samplenum)
			#print('Found edge at', self.samplenum, '!')
			
			#Save the new edge
			self.currentedgesample = self.samplenum
			
			length = self.currentedgesample - self.oneedgeagosample
			#print('Length since last edge', length, '.')
			
			if length in range(self.inactivehalfcycle - self.margin, self.inactivehalfcycle + self.margin):
				self.cycletype = 'INACTIVE'
			elif length in range(self.activehalfcycle - self.margin, self.activehalfcycle + self.margin):
				self.cycletype = 'ACTIVE'
			else:
				#Invalid half-cycle length. Clean up!
				self.cycletype = 'ERROR'
			
			if self.cycletype == 'ACTIVE' and self.lastcycletype == 'ACTIVE':
				#Two unprocessed ACTIVE half-cycles
				self.lastbit = 0
				self.putrawbit()
				
				self.cycletype = 'PROCESSED'
			elif self.cycletype == 'INACTIVE' and self.lastcycletype == 'INACTIVE':
				#Two unprocessed INACTIVE half-cycles
				self.lastbit = 1
				self.putrawbit()
				
				self.cycletype = 'PROCESSED'
			elif self.cycletype == 'ERROR':
				#This cycle was an error, pass it onward so that things can clean up
				self.lastbit = 2
			else:
				#Nothing to do with this half-cycle
				self.lastbit = 2