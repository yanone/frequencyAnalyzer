# frequencyAnalyzer

Graphical tool written in Python to measure frequency response of P.A. systems, in order to adjust the frequency range with a graphical EQ unit. This is mostly important in small rooms that have a very high probability to show resonance and dissonance frequencies, which will distort your music reproduction.

The frequencies that your EQ can adjust (and that you want to measure) are defined in `.plist` files (see example file in `devices` sub folder). You can adjust such a file to match your EQ. Then load a device file with the `Device` button.

Then, press `Play` to visualize the frequency response. 

This tool is a cheaply hacked implementation of similar professional solutions. It is meant to be used in combination with a professional sound card playing the frequencies to the P.A., and a professional measurement microphone to record them back into the computer. The system’s standard sound input and output devices are used. Change them in the system preferences.

![](window.png)

Requires  `wx`, as well as `pyaudio`, which in turns requires `portaudio`, which in turn you can install using `homebrew`.

Install (on Mac):

```
pip install wxPython
brew install portaudio
pip install pyaudio
```

Then, you can call the app using `python frequencyAnalyzer.py`