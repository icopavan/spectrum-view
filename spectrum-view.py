#!/usr/bin/python

from scipy.interpolate import interp1d
from numpy import *
from optparse import OptionParser
from threading import Thread
import matplotlib.pyplot as plt

from vesna.spectrumsensor import SpectrumSensor, SweepConfig

class VesnaSpectrumPlot:
    '''
    @summary: A spectrogram plotter for VESNA sensor node with spectrum sensing capabilities.
    '''    
    
    def __init__(self, start_freq, end_freq, step):
        '''
        Init a new object
        @param start_freq: Lower bound of the frequency band to scan [Hz].
        @param end_freq: Upper bound of the frequency band to scan [Hz].
        @param step: Bandwidth of a single step [Hz].        
        '''
        plt.ion()
        
        # Calculate number of steps
        nsteps = round((end_freq - start_freq)/step)+1
        
        # Need to instantiate the image object with expected range of numbers to get correct color scale
        self.A = array([linspace(-100,-20,256) for i in range(256)])
        self.fig,self.ax = plt.subplots(1,1)        
        
        self.ax.set_title('Spectrum [dBm]')
        
        self.image = self.ax.imshow(self.A, cmap=plt.get_cmap('spectral'))
        self.fig.colorbar(self.image)
        
        # Set array elements to zero
        self.A = zeros(shape=(256,256))-100
        self.image.set_data(self.A)             
        
        # Generate two linspace arrays needed later for interpolation
        self.x1 = linspace(start_freq,end_freq, nsteps)
        self.x2 = linspace(start_freq,end_freq,256)
        
        plt.yticks(linspace(0,255,10))        
        plt.ylabel('Time')
        
        plt.xticks(linspace(0,255,10), around(linspace(round(start_freq/1000),round(end_freq/1000), 10)), rotation=30)
        plt.xlabel('Frequency [kHz]')
        
        self.line = 0
        
        self.fig.canvas.draw()
    
    def callback(self, sweep_config, sweep):
        '''
        @summary: Method is intended to be called by the Run method of the SpectrumSensor class when the data is received
        via RS232.
        
        Method interpolates the received data to get sufficient number of points and
        then updates the spectrogram.
        
        @param sweep_config: Frequency sweep configuration object.
        @param sweep: Object containing the time stamp and RSSI measurements.
        '''        
        self.interpolator = interp1d(self.x1,sweep.data, kind = 'cubic')
        if (len(sweep.data) < 256):
            
            # Interpolate the received data
            data = self.interpolator(self.x2)
            
            # Put the data into the image array, update the image and draw it.
            self.A[self.line] = data
            self.image.set_data(self.A)            
            self.fig.canvas.draw()            
            
            # If at the end of the image, roll the array for one row and update the last row
            if (self.line > 254):
                self.A = roll(self.A,-256)
            else:
                self.line = self.line + 1
            
            return True
        else:
            return False

def main():
    '''
    @summary: Main function. Configures the VESNA sensor node with the given parameters and starts plotting
    the data received via RS232.
    '''
    
    # Full range of RF input (center frequency)
    RF_UPPER = 866000000
    RF_LOWER = 45000000
    MIN_STEP = 1000
    
    # Default options
    DEFAULT_LOWER = 554000000
    DEFAULT_UPPER = 570000000
    DEFAULT_STEP = 2000000
    
    # Options parser
    parser = OptionParser(conflict_handler="resolve")
    
    parser.add_option('-s', '--start-freq', type="int", default=DEFAULT_LOWER, help='Set the lower bound of the frequency band to scan [Hz]. [default=%default]')
    parser.add_option('-e', '--end-freq', type="int", default=DEFAULT_UPPER, help='Set the upper bound of the frequency band to scan [Hz]. [default=%default]')
    parser.add_option('-d', '--step', type="int", default=DEFAULT_STEP, help='Step [Hz]. [default=%default]')
    
    options, args = parser.parse_args()
    
    # Test the input parameters
    lower_freq =  ((options.start_freq > RF_LOWER) and (options.start_freq < RF_UPPER)) and options.start_freq or DEFAULT_LOWER
    upper_freq =  ((options.end_freq > RF_LOWER) and (options.end_freq < RF_UPPER) and (options.end_freq > lower_freq)) and options.end_freq or DEFAULT_UPPER
    step = ((options.step > MIN_STEP) and ((upper_freq - lower_freq) > options.step)) and options.step or DEFAULT_STEP    
    
    # Open the device
    spectrumsensor = SpectrumSensor("/dev/ttyUSB0")
    config_list = spectrumsensor.get_config_list()
    
    # Configure the device
    sweep_config = config_list.get_sweep_config(lower_freq, upper_freq, step)
    
    # Configure the plotter    
    plotter = VesnaSpectrumPlot(lower_freq, upper_freq, step)
    
    # Get the ball rollin'    
    spectrumsensor.run(sweep_config, plotter.callback)
    
main()
