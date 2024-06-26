from TimeTagger import createTimeTagger, freeTimeTagger, Correlation, Histogram, Counter, CountBetweenMarkers, FileWriter, Countrate, Combiner, TimeDifferences
from qudi.core.configoption import ConfigOption
from qudi.core.module import Base


class TT(Base):
    """ Designed for driving TimeTagger from swabian instruments.

    See Time Tagger User Manual.

    Example config for copy-paste: 

    tagger:
        module.Class: 'local.timetagger.timetagger.TT'
        options:
            channels_params:
                ch1:
                    delay: 0
                    # triggerLevel: 2 # range 0.5V-2.5V, with 50 Ohms impedance usually half input Volts is read out

            test_channels: [1,2,8] #[1,2,3,4,5,6,7]#[1,2, 4, -4]
            combined_channels: # Alias for combined channels must not start with 'ch'
                DetectorChans:
                    - 'ch1'
                    - 'ch2'
                APDset1:
                    - 'ch1'
                    - 'ch2'
                APDset2:
                    - 'ch3'
                    - 'ch4'
            
            

    """
    # config options
    _test_channels = ConfigOption('test_channels', False, missing='nothing')
    _channels_params = ConfigOption('channels_params', False, missing='nothing')
    _combined_channels = ConfigOption('combined_channels', missing = 'error')

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        chan_alphabet = ['ch1', 'ch2', 'ch3', 'ch4', 'ch5', 'ch6', 'ch7', 'ch8', 'ch9', 'ch10', 
        'ch11', 'ch12', 'ch13', 'ch14', 'ch15', 'ch16', 'ch17', 'ch18']
        self.channel_codes = dict(zip(chan_alphabet, list(range(1,19,1))))

    def on_activate(self):
        try:
            self.tagger = createTimeTagger()
            # self.tagger.reset()
            self.log.info(f"Tagger initialization successful: {self.tagger.getSerial()}")
        except:
            self.log.error(f"Check if the TimeTagger device is being used by another instance.")
            Exception(f"\nCheck if the TimeTagger device is being used by another instance.")

        # set test signals
        if self._test_channels:
            for i in self._test_channels:
                self.log.info(f"RUNNING CHANNEL {i} WITH TEST SIGNAL!")
                self.tagger.setTestSignal(i, True)

        # set specified in the cfg channels params
        if self._channels_params:
            for channel, params in self._channels_params.items():
                channel = self.channel_codes[channel]
                if 'delay' in params.keys():
                    self.delay_channel(delay=params['delay'], channel = channel)
                if 'triggerLevel' in params.keys():
                    self.tagger.setTriggerLevel(channel, params['triggerLevel'])

        #Create combine channels:
        self.__combined_channels = self._combined_channels.copy()
        for key, channels in self.__combined_channels.items():
            channels_array = []
            for i in range(len(channels)):
                channels_array.append(self.channel_codes[channels[i]])
            self.__combined_channels.update({key:self.combiner(channels_array)})

        #Append Channel codes with combined channels
        for chn in self.__combined_channels.keys():
            self.channel_codes[chn]=self.__combined_channels[chn].getChannel()
    

    def on_deactivate(self):
        freeTimeTagger(self.tagger)



    def histogram(self, **kwargs):  
        """
        Histogram the clicks in 'channel' with trigger
        It is possible to set values:
        Example:
        channel=1, trigger_channel=5, bins_width=1000, numer_of_bins= 1000
        bins_width is in ps
        get data by .getData()
        get time index by .getIndex()
        """
        return Histogram(self.tagger,
                            kwargs['channel'],
                            kwargs['trigger_channel'],
                            kwargs['bins_width'],
                            kwargs['number_of_bins'])
    
    def correlation(self, **kwargs):  
        """
        Accumulates time differences between clicks on two channels into a histogram.
        It is possible to set values:
        Example:
        channel_start=1, channel_stop=2, bins_width=1000, numer_of_bins= 1000

        get data by .getData()
        get normalized g2 by .getDataNormalized()
        get time index by .getIndex()
        """
        return Correlation(self.tagger,
                            kwargs['channel_stop'],
                            kwargs['channel_start'],
                            kwargs['bins_width'],
                            kwargs['number_of_bins'])


    def delay_channel(self, channel, delay):
        """
        Set delay on the channel,
        this delay can be positive or negative,
        if absolute value of the delay not exceed 2000000 ps, this delay will be applied onboard directly.
        """
        self.tagger.setInputDelay(delay=delay, channel=channel)

    def counter(self, **kwargs):
        """
        Using a circular buffer to record countrate.
        bins_width: binwidth in ps; n_values: number of bins
        get data by .getData(). The output is 2D_array giving the current values of the circular buffer for each channel.
        """
        for key, value in kwargs.items():
            if key == 'refresh_rate' and value != None:
                bins_width = int(1e12/value)
            if key == 'bins_width' and value != None:
                bins_width = value
        return Counter(self.tagger,
                                kwargs['channels'],
                                bins_width,
                                kwargs['n_values'])


    def combiner(self, channels):
        """
        Create virtual channel that combines time_tags from 'combiner channels'. 
        """
        return Combiner(self.tagger, channels)


    def count_between_markers(self, click_channel, begin_channel, n_values):
        """
        Counts events on a single channel within the time indicated by a “start” and “stop” signals.
        Compared with counter function, this function gives possibility to synchronize the measurements and actions.
        With end_channel on this function accumulate counts within a gate.
        """
        return CountBetweenMarkers(self.tagger,
                                click_channel=click_channel,
                                begin_channel=begin_channel,
                                n_values=n_values)     



    def write_into_file(self, filename, apdChans = None, filteredChans = []):
        """
        Writes the time-tag-stream into a file in a binary format with a lossless compression.
        """
        if filteredChans == []:
            self.tagger.setConditionalFilter(trigger=[], filtered=[])
        else:
            self.tagger.setConditionalFilter(trigger=apdChans, filtered=filteredChans)
        self.allChans = [ *apdChans, *filteredChans]
        return FileWriter(self.tagger,
        filename, self.allChans)


    def time_differences(self, click_channel, start_channel, scan_trigger_channel, line_trigger_channel, binwidth, n_bins, n_histograms):
        """
        Gives the ability to launch startstop measurement with scan trigger and line trigger.
        make 2d g^2 measurement possible
        """
        return TimeDifferences(self.tagger, 
                                click_channel, 
                                start_channel, 
                                scan_trigger_channel,
                                line_trigger_channel,
                                binwidth, 
                                n_bins,
                                n_histograms)

    