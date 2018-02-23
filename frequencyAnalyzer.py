

import plistlib
import threading
import pyaudio
import numpy as np
import wave
import audioop
import time, os
import math
import json

import wx
from ynlib.maths import Interpolate
#from pysine import sine


###############################################################

frequencies = []
interpolatedFrequencies = []
volumes = {}
clipping = {}
intermediateSteps = 3
minimumVolume = None
maximumVolume = None
averageVolume = 0
currentVolume = 0
peakVolume = 80
volumeScope = 120.0

###############################################################

	
# output
out = pyaudio.PyAudio()



_volume = 1.0     # range [0.0, 1.0]
fs = 44100       # sampling rate, Hz, must be integer
duration = 0.10  # in seconds, may be float
# for paFloat32 sample values must be in range [-1.0, 1.0]


# input
CHUNK = 4096
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100



outputStream = out.open(format=pyaudio.paFloat32,
			channels=CHANNELS,
			rate=RATE,
			output=True,
			frames_per_buffer=2048,
			)


class AppKitNSUserDefaults(object):
	def __init__(self, name = None):
		from AppKit import NSUserDefaults
		if name:
			self.defaults = NSUserDefaults.alloc().initWithSuiteName_(name)
		else:
			self.defaults = NSUserDefaults.standardUserDefaults()


	def get(self, key):
		if self.defaults.objectForKey_(key):
			return json.loads(self.defaults.objectForKey_(key))

	def set(self, key, value):
		self.defaults.setObject_forKey_(json.dumps(value), key)

	def remove(self, key):
		self.defaults.removeObjectForKey_(key)




def play(f, thread):



	# generate samples, note conversion to float32 array
#	samples = (np.sin(2*np.pi*np.arange(fs*duration*2.0)*f/fs)).astype(np.float32)
	samples = (np.sin(2*np.pi*np.arange(fs*duration)*f/fs)).astype(np.float32).tobytes()
	# print samples

	# def sine_wave(frequency=440.0, framerate=RATE, amplitude=0.5):
	# 	amplitude = max(min(amplitude, 1), 0)
	# 	return (float(amplitude) * math.sin(2.0*math.pi*float(frequency)*(float(i)/float(framerate))) for i in count(0))

	# samples = (f, RATE)
	# print samples
	def sine_wave(frequency=440.0, framerate=44100, amplitude=0.5, duration = 1.0):
		period = int(framerate / frequency)
		if amplitude > 1.0: amplitude = 1.0
		if amplitude < 0.0: amplitude = 0.0
		lookup_table = [float(amplitude) * math.sin(2.0*math.pi*float(frequency)*(float(i%period)/float(framerate))) for i in xrange(period)]
		return lookup_table(lookup_table[i%period] for i in range(period))
		
#eq
#	samples = sine_wave(f, RATE, .5, .1)
#	print samples

# 	ramp = int(len(samples) * .1)
# #	print samples[-ramp:]
# 	for i in range(ramp):
# 		samples[i] = Interpolate(0, samples[i], i/float(ramp))
# 		samples[-i-1] = Interpolate(0, samples[-i-1], i/float(ramp))
	# print samples[-ramp:]

	# play. May repeat with different volume values (if done interactively) 
	outputStream.write(samples)


def volume(f, thread):

#	print f

	global averageVolume, clipping, currentVolume
	time.sleep(max(0, duration / 2.0 ))

	input = pyaudio.PyAudio()
	inputStream = input.open(format=FORMAT,
					channels=CHANNELS,
					rate=RATE,
					input=True,
					frames_per_buffer=CHUNK)

	_max = 0

	values = []
	for i in range(0, int(RATE / CHUNK * max(.1, duration * .2))):
		data = inputStream.read(CHUNK)
		rms = audioop.rms(data, 2)    # here's where you calculate the volume
		values.append(rms)
		_max = max(_max, rms)


	# for i in range(10): #to it a few times just to see
	# 	data = np.fromstring(inputStream.read(CHUNK),dtype=np.int16)
	# 	data = data * np.hanning(len(data)) # smooth the FFT by windowing data
	# 	fft = abs(np.fft.fft(data).real)
	# 	fft = fft[:int(len(fft)/2)] # keep only first half
	# 	freq = np.fft.fftfreq(CHUNK,1.0/RATE)
	# 	freq = freq[:int(len(freq)/2)] # keep only first half
	# 	freqPeak = freq[np.where(fft==np.max(fft))[0][0]]+1
	# 	print(f, "peak frequency: %d Hz"%freqPeak)

 #   	value = 0
	value = sum(values) / float(len(values))

#	print value



	value = 20 * math.log10(value) + 2.0


	if value > peakVolume:
		clipping[f] = True
	else:
		clipping[f] = False


	currentVolume = value


#	print value
#	print f, _max

	volumes[f] = value
	averageVolume = sum(volumes.values())/ float(len(volumes.values()))

	thread.frame._max = max(thread.frame._max, value)
#	thread.frame.Refresh()

#	print volumes
#	print min(volumes.values()), max(volumes.values())

	inputStream.stop_stream()
	inputStream.close()
	input.terminate()


class Record(threading.Thread): 

	def __init__(self, frame):
		threading.Thread.__init__(self) 
		self.frame = frame

	def run(self): 

		while self.frame.alive:
		

			for f in interpolatedFrequencies:

				if self.frame.playing:

					self.frame.currentFrequency = f
					self.frame.Refresh()


					p = threading.Thread(target=play, args=(f, self,))
					p.start()
					v = threading.Thread(target=volume, args=(f, self,))
					v.start()
					time.sleep(duration)


#			for f in interpolatedFrequencies:
#				print '%s: %s' % (f, volumes[f])

			time.sleep(duration)



class Example(wx.Frame):
	def __init__(self, parent, title):
		super(Example, self).__init__(parent, title=title, 
			size=(1000, 600))

		self.preferences = AppKitNSUserDefaults('de.yanone.frequencyAnalyzer')

		self.alive = True
		self._max = 0
		self.currentFrequency = None

		self.playing = False
		self.recorder = Record(self)
		self.recorder.start()

		self.deviceButton = wx.Button(self, -1, "Device")
		self.deviceButton.Bind(wx.EVT_BUTTON, self.OnDevice) 
		self.playButton = wx.Button(self, -1, "Play")
		self.playButton.Bind(wx.EVT_BUTTON, self.OnPlay) 
		self.stopButton = wx.Button(self, -1, "Stop")
		self.stopButton.Bind(wx.EVT_BUTTON, self.OnStop) 

		self.Centre()
		self.Bind(wx.EVT_CLOSE, self.OnClose)
		self.Bind(wx.EVT_PAINT, self.OnPaint)

		dc = wx.ClientDC(self)
		dc.DrawLine(50, 60, 190, 60)


		if self.preferences.get('deviceFile'):
			self.openDeviceFile(self.preferences.get('deviceFile'))


	def OnPaint(self, event=None):
		dc = wx.PaintDC(self)
		dc.Clear()
		dc.SetPen(wx.Pen(wx.BLACK, 4))


		size = dc.GetSize()



		dc.SetBackground(wx.Brush(wx.Colour(30,30,30)))
		dc.Clear()

#		dc.DrawRectangle(0, 0, size[0], size[1])


		marginHorizontal = max(size[0] * .05, 100)
		marginTop = max(size[1] * .1, 100)
		marginBottom = max(size[1] * .2, 200)
		left = marginHorizontal
		right = size[0] - marginHorizontal - 100
		top = marginTop
		bottom = size[1] - marginBottom
		height = max(1, (bottom - top))
		width = max(1, (right - left))

		colour = wx.Colour(223,219,0)
		colour = wx.Colour(223,219,0)
		activeColour = wx.Colour(229,53,45)

		fontSize = max(width / 80.0, 10)

		# dB(A) label
		font = wx.Font(fontSize, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL)
		dc.SetTextForeground(colour)
		dc.SetFont(font)
		dc.DrawLabel('dB(A)', wx.Rect(left - 50, top + height / 2.0, 40, 20), wx.ALIGN_RIGHT)


		# Volume
		pen=wx.Pen(colour ,4)
		dc.SetPen(pen)
		y = bottom - height * currentVolume / volumeScope
		dc.DrawLine(right + 85, bottom, right + 85, y)

		pen=wx.Pen(activeColour ,4)
		dc.SetPen(pen)
		dc.DrawLine(right + 70, top, right + 100, top)
		dc.DrawLine(right + 100, top, right + 100, bottom)
		dc.DrawLine(right + 70, bottom, right + 100, bottom)
		y = bottom - height * peakVolume / volumeScope
		dc.DrawLine(right + 70, y, right + 100, y)



		if frequencies:
			_min = min(volumes.values())
			_max = max(volumes.values())
	#		self._max = max(_max, self._max)

			if self._max:
				factor = float(height) / float(self._max)
			else:
				factor = 1
			factor = height / volumeScope

	#		print 'max', self._max, 'height', height, 'factor', factor
	#		print factor

			# Average
			y = bottom - averageVolume * factor
			pen=wx.Pen(colour ,4)
			dc.SetPen(pen)
			dc.DrawLine(left, y, right, y)

			# Peak
			y = bottom - peakVolume * factor
			pen=wx.Pen(activeColour ,4)
			dc.SetPen(pen)
			dc.DrawLine(left, y, right, y)

			for i, f in enumerate(interpolatedFrequencies):


				# if self.currentFrequency == f:
				# 	pen=wx.Pen(activeColour ,4)
				# else:
				# 	pen=wx.Pen(colour ,4)


				x = left + i * (right - left) / float(len(interpolatedFrequencies) - 1)
				if f in frequencies:

					if clipping.has_key(f) and clipping[f] == True:
						pen=wx.Pen(colour ,4)
					else:
						pen=wx.Pen(activeColour ,4)
					dc.SetPen(pen)
					dc.DrawLine(x, top, x, bottom)

				# connecting lines
				pointPosition = (x, bottom - volumes[f] * factor)

				if i > 0:
					previousPointPosition = (left + (i-1) * (right - left) / float(len(interpolatedFrequencies) - 1), bottom - volumes[interpolatedFrequencies[i-1]] * factor)

					pen=wx.Pen(colour ,4)
					dc.SetPen(pen)
					dc.DrawLine(pointPosition[0], pointPosition[1], previousPointPosition[0], previousPointPosition[1])



				if f in frequencies:
					font = wx.Font(fontSize, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL)
					dc.SetTextForeground(colour)
					dc.SetFont(font)

					text = str(f)
					if f > 1000:
						text = '%sk' % (f // 1000)

						if f % 1000:
							text += str(f % 1000 / 100)

					dc.DrawLabel(text, wx.Rect(x - 20, bottom + max(20, size[0] / 75.0), 40, 20), wx.ALIGN_CENTER)




				if f in frequencies:
					dc.SetPen(wx.Pen(colour ,0))
					dc.SetBrush(wx.Brush(colour))

					pointSize = float(width) / float(len(frequencies) - 1) * .2
					dc.DrawCircle(pointPosition[0], pointPosition[1], pointSize)

		self.deviceButton.SetPosition((marginHorizontal, size[1] - marginBottom + max(100, size[0] / 15.0)))
		self.playButton.SetPosition((marginHorizontal + 100, size[1] - marginBottom + max(100, size[0] / 15.0)))
		self.stopButton.SetPosition((marginHorizontal + 200, size[1] - marginBottom + max(100, size[0] / 15.0)))

		font = wx.Font(12, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL)
		dc.SetTextForeground(colour)
		dc.SetFont(font)
		dc.DrawLabel('Input: %s, Output: %s' % (out.get_default_input_device_info()['name'], out.get_default_output_device_info()['name']), wx.Rect(marginHorizontal + 310, size[1] - marginBottom + 2 + max(100, size[0] / 15.0), 200, 100))


	def OnClose(self, event):


		outputStream.stop_stream()
		outputStream.close()
		out.terminate()


		self.playing = False
		self.alive = False
#		self.recorder.join(1)

		self.Destroy()
#		exit()

	def OnDevice(self, event):


		# otherwise ask the user what new file to open
		with wx.FileDialog(self, "Open EQ .plist file", wildcard="plist files (*.plist)|*.plist",
						   style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST) as fileDialog:

			if fileDialog.ShowModal() == wx.ID_CANCEL:
				return     # the user changed their mind

			# Proceed loading the file chosen by the user
			pathname = fileDialog.GetPath()

			self.openDeviceFile(pathname)

	def openDeviceFile(self, pathname):

		global frequencies, interpolatedFrequencies, volumes, averageVolume, clipping

		try:
			frequencies = plistlib.readPlist(pathname)

			self.SetTitle(os.path.basename(os.path.splitext(pathname)[0]))

			interpolatedFrequencies = []
			for i, f in enumerate(frequencies):
				if i > 0 and intermediateSteps > 0:

					for s in range(intermediateSteps):
						interpolatedFrequencies.append(Interpolate(frequencies[i-1], f, (s + 1)/float(intermediateSteps + 1)))

				interpolatedFrequencies.append(f)

			volumes = {}
			clipping = {}			
			averageVolume = 0
			for f in interpolatedFrequencies:
				volumes[f] = 0

			self.Refresh()

			self.preferences.set('deviceFile', pathname)

		except IOError:
			wx.LogError("Cannot open file '%s'." % pathname)


	def OnPlay(self, event):

		if frequencies:
			self.playing = True

	def OnStop(self, event):


		if frequencies:
			self.currentFrequency = None
			self.Refresh()
			self.playing = False

	
	def DrawLine(self):
		dc = wx.ClientDC(self)
		dc.DrawLine(50, 60, 190, 60)

if __name__ == '__main__':
	app = wx.App()
	e = Example(None, 'Frequency Response')
	e.DrawLine()
	e.Show()
#	e.play()
	e.DrawLine()
	app.MainLoop()








