

import threading
import pyaudio
import numpy as np
import wave
import audioop
import time

import wx
from ynlib.maths import Interpolate



###############################################################

frequencies = [25, 40, 63, 100, 160, 250, 400, 630, 1000, 1600, 2500, 4000, 6300, 10000, 16000]
intermediateSteps = 5

frequencies = [20, 25, 31.5, 40, 50, 63, 80, 100, 125, 160, 200, 250, 315, 400, 500, 630, 800, 1000, 1250, 1600, 2000, 2500, 3150, 4000, 5000, 6300, 8000, 10000, 12500, 16000, 20000]
intermediateSteps = 3

###############################################################

	
# output
out = pyaudio.PyAudio()
_volume = 1.0     # range [0.0, 1.0]
fs = 44100       # sampling rate, Hz, must be integer
duration = 0.10  # in seconds, may be float
# for paFloat32 sample values must be in range [-1.0, 1.0]


# input
CHUNK = 2048
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100




interpolatedFrequencies = []
for i, f in enumerate(frequencies):
	if i > 0 and intermediateSteps > 0:

		for s in range(intermediateSteps):
			print s
			interpolatedFrequencies.append(Interpolate(frequencies[i-1], f, (s + 1)/float(intermediateSteps + 1)))

	interpolatedFrequencies.append(f)

volumes = {}
for f in interpolatedFrequencies:
	volumes[f] = 0


outputStream = out.open(format=pyaudio.paFloat32,
			channels=CHANNELS,
			rate=RATE,
			output=True,
			frames_per_buffer=CHUNK)

def play(f, thread):



	# generate samples, note conversion to float32 array
	samples = (np.sin(2*np.pi*np.arange(fs*duration*2.0)*f/fs)).astype(np.float32)


	ramp = int(len(samples) * .1)
#	print samples[-ramp:]
	for i in range(ramp):
		samples[i] = Interpolate(0, samples[i], i/float(ramp))
		samples[-i-1] = Interpolate(0, samples[-i-1], i/float(ramp))
	# print samples[-ramp:]

	# play. May repeat with different volume values (if done interactively) 
	outputStream.write(_volume*samples)


def volume(f, thread):

	time.sleep(max(0, duration / 2.0 - 0.1))

	input = pyaudio.PyAudio()
	inputStream = input.open(format=FORMAT,
					channels=CHANNELS,
					rate=RATE,
					input=True,
					frames_per_buffer=CHUNK)

	_max = 0


	for i in range(0, int(RATE / CHUNK * max(.1, duration * .2))):
		data = inputStream.read(CHUNK)
		rms = audioop.rms(data, 2)    # here's where you calculate the volume
		_max = max(_max, rms)

	volumes[f] = _max

	thread.frame._max = max(thread.frame._max, _max)
#	thread.frame.Refresh()

#	print volumes

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

			time.sleep(.1)



class Example(wx.Frame):
	def __init__(self, parent, title):
		super(Example, self).__init__(parent, title=title, 
			size=(800, 400))

		self.alive = True
		self._max = 0
		self.currentFrequency = None

		self.playing = False
		self.recorder = Record(self)
		self.recorder.start()

		self.playButton = wx.Button(self, -1, "Play")
		self.playButton.Bind(wx.EVT_BUTTON, self.OnPlay) 
		self.stopButton = wx.Button(self, -1, "Stop")
		self.stopButton.Bind(wx.EVT_BUTTON, self.OnStop) 

		self.Centre()
		self.Bind(wx.EVT_CLOSE, self.OnClose)
		self.Bind(wx.EVT_PAINT, self.OnPaint)

		dc = wx.ClientDC(self)
		dc.DrawLine(50, 60, 190, 60)

	def OnPaint(self, event=None):
		dc = wx.PaintDC(self)
		dc.Clear()
		dc.SetPen(wx.Pen(wx.BLACK, 4))


		size = dc.GetSize()



		dc.SetBackground(wx.Brush(wx.Colour(30,30,30)))
		dc.Clear()

#		dc.DrawRectangle(0, 0, size[0], size[1])


		marginHorizontal = 100
		marginTop = 100
		marginBottom = 200
		left = marginHorizontal
		right = size[0] - marginHorizontal
		top = marginTop
		bottom = size[1] - marginBottom
		height = max(1, (bottom - top))
		width = max(1, (right - left))


		_min = min([volumes[x] for x in volumes.keys()])
		_max = min([volumes[x] for x in volumes.keys()])
#		self._max = max(_max, self._max)

		if self._max:
			factor = float(height) / float(self._max)
		else:
			factor = 1

#		print 'max', self._max, 'height', height, 'factor', factor
#		print factor

		for i, f in enumerate(interpolatedFrequencies):

			colour = wx.Colour(223,219,0)
			activeColour = wx.Colour(229,53,45)

			# if self.currentFrequency == f:
			# 	pen=wx.Pen(activeColour ,4)
			# else:
			# 	pen=wx.Pen(colour ,4)


			x = left + i * (right - left) / float(len(interpolatedFrequencies) - 1)
			if f in frequencies:
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
				font = wx.Font(10, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL)
				dc.SetTextForeground(colour)
				dc.SetFont(font)

				text = str(f)
				if f > 1000:
					text = '%sk' % (f // 1000)

					if f % 1000:
						text += str(f % 1000 / 100)

				dc.DrawLabel(text, wx.Rect(x - 20, bottom + 20, 40, 20), wx.ALIGN_CENTER)


			if f in frequencies:
				dc.SetPen(wx.Pen(colour ,0))
				dc.SetBrush(wx.Brush(colour))

				pointSize = float(width) / float(len(frequencies) - 1) * .2
				dc.DrawCircle(pointPosition[0], pointPosition[1], pointSize)

		self.playButton.SetPosition((marginHorizontal, size[1] - marginBottom + 100))
		self.stopButton.SetPosition((marginHorizontal + 100, size[1] - marginBottom + 100))


	def OnClose(self, event):


		outputStream.stop_stream()
		outputStream.close()
		out.terminate()


		self.playing = False
		self.alive = False
#		self.recorder.join(1)

		self.Destroy()
#		exit()

	def OnPlay(self, event):
		self.playing = True
		print 'Play'

	def OnStop(self, event):
		self.currentFrequency = None
		self.Refresh()
		self.playing = False
		print 'Stop'

	def DrawLine(self):
		dc = wx.ClientDC(self)
		dc.DrawLine(50, 60, 190, 60)

if __name__ == '__main__':
	app = wx.App()
	e = Example(None, 'Line')
	e.DrawLine()
	e.Show()
#	e.play()
	e.DrawLine()
	app.MainLoop()








