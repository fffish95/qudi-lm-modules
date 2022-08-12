from TimeTagger import createTimeTagger, freeTimeTagger, Correlation, Histogram, Counter, CountBetweenMarkers, FileWriter, Countrate, Combiner, TimeDifferences
from qudi.core.configoption import ConfigOption
from qudi.core.module import Base


class TT(Base):
    """ Designed for driving TimeTagger from swabian instruments.

    See Time Tagger User Manual.

    Example config for copy-paste: 

    tagger:
        module.Class: 'local.timetagger.timetagger.TT' 

    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)


    def on_activate(self):
        pass

    

    def on_deactivate(self):
        pass



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
        pass
    
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
        pass


    def delay_channel(self, channel, delay):
        """
        Set delay on the channel,
        this delay can be positive or negative,
        if absolute value of the delay not exceed 2000000 ps, this delay will be applied onboard directly.
        """
        pass

    def counter(self, **kwargs):
        """
        Using a circular buffer to record countrate.
        bins_width: binwidth in ps; n_values: number of bins
        get data by .getData(). The output is 2D_array giving the current values of the circular buffer for each channel.
        """
        pass


    def combiner(self, channels):
        """
        Create virtual channel that combines time_tags from 'combiner channels'. 
        """
        pass


    def count_between_markers(self, click_channel, begin_channel, n_values):
        """
        Counts events on a single channel within the time indicated by a “start” and “stop” signals.
        Compared with counter function, this function gives possibility to synchronize the measurements and actions.
        With end_channel on this function accumulate counts within a gate.
        """
        pass



    def write_into_file(self, filename, apdChans = None, filteredChans = []):
        """
        Writes the time-tag-stream into a file in a binary format with a lossless compression.
        """
        pass


    def time_differences(self, click_channel, start_channel, scan_trigger_channel, line_trigger_channel, binwidth, n_bins, n_histograms):
        """
        Gives the ability to launch startstop measurement with scan trigger and line trigger.
        make 2d g^2 measurement possible
        """
        pass

    