# -*- coding: utf-8 -*-
import copy
import numpy as np
from enum import Enum 
import time


from qudi.core.configoption import ConfigOption
from qudi.core.connector import Connector
from qudi.util.helpers import natural_sort
from qudi.interface.data_instream_interface import DataInStreamInterface, DataInStreamConstraints
from qudi.interface.data_instream_interface import StreamChannelType, StreamChannel
from qudi.util import tools


class TTInstreamInterfuse(DataInStreamInterface):
    """ Methods to use TimeTagger as data in-streaming device (continuously read values)

    Example config for copy-paste:

    """

    nicard = Connector(interface = "NICard")
    timetagger = Connector(interface = "TT")
    # config options
    _timetagger_channels = ConfigOption('timetagger_channels', list(), missing='info')
    _stream_ai_channels = ConfigOption('stream_ai_channels', list(), missing='nothing')
    _ai_voltage_ranges = ConfigOption('ai_voltage_ranges', None, missing='nothing')
    __sample_rate = ConfigOption(name='sample_rate', default=50, missing='nothing')
    __buffer_size = ConfigOption(name='buffer_size', default=10000000, missing='nothing')


    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.__data_type = np.float64

        # Data buffer
        self._data_buffer = np.empty(0, dtype=self.__data_type)
        self._has_overflown = False
        self._is_running = False
        self._last_read = None
        self._start_time = None
        self.__active_channels = tuple()

        # Stored hardware constraints
        self._constraints = None

        return


    def on_activate(self):
        self._tt = self.timetagger()

        # Create constraints
        self._constraints = DataInStreamConstraints()
        self._constraints.digital_channels = tuple(
            StreamChannel(name=ch, type=StreamChannelType.DIGITAL, unit='Cps') for ch in
            self._timetagger_channels)
        self._constraints.analog_channels = tuple(
            StreamChannel(name=ch, type=StreamChannelType.ANALOG, unit='V') for ch in
            self._stream_ai_channels)
        self.__available_channels = self._constraints.digital_channels + self._constraints.analog_channels



    def on_deactivate(self):
        """ Deactivate the module and clean up.
        """
        if self.is_running:
            self._is_running = False
        if hasattr(self, 'Counterfunc'):
            for chn in self.__active_channels:
                if chn.type == StreamChannelType.DIGITAL:
                    self.Counterfunc[chn.name].clear()

    def configure(self, *args, **kwargs):
        """
            FIX ME
        """

        if self._check_settings_change():
            if len(args) == 0:
                param_dict = kwargs
            elif len(args) == 1 and isinstance(args[0], dict):
                param_dict = args[0]
                param_dict.update(kwargs)
            else:
                raise TypeError('"TTInstreamInterfuse.configure" takes exactly 0 or 1 positional '
                                'argument of type dict.')


            if 'channel' in param_dict.keys():
                self.__active_channels = tuple(param_dict['channel'])
                self.__active_channels = tuple(ch for ch in self.__available_channels if ch.name in param_dict['channel'])
            else:
                self.__active_channels = self.__available_channels 

            if 'sample_rate' in param_dict.keys():
                self.__sample_rate = param_dict['sample_rate']
            else:
                self.log.error('Please input timetagger counter sample rate')
                return

            if 'buffer_size' in param_dict.keys():
                self.__buffer_size = param_dict['buffer_size']
            else:
                self.log.error('Please input buffer size (samples per channel)')
                return
            
        return self.all_settings

    @property
    def all_settings(self):
        """
        FIX ME
        """
   
        return {    'active_channels': self.__active_channels,
                    'sample_rate': self.__sample_rate,
                    'buffer_size': self.__buffer_size}

    @property
    def sample_rate(self):
        """
        Read-only property to return the currently set sample rate

        @return float: current sample rate in Hz
        """
        return self.__sample_rate

    @sample_rate.setter
    def sample_rate(self, rate):
        if self._check_settings_change():
            if not self._clk_frequency_valid(rate):
                if self._analog_channels:
                    min_val = self._constraints.combined_sample_rate.min
                    max_val = self._constraints.combined_sample_rate.max
                else:
                    min_val = self._constraints.digital_sample_rate.min
                    max_val = self._constraints.digital_sample_rate.max
                self.log.warning(
                    'Sample rate requested ({0:.3e}Hz) is out of bounds. Please choose '
                    'a value between {1:.3e}Hz and {2:.3e}Hz. Value will be clipped to '
                    'the closest boundary.'.format(rate, min_val, max_val))
                rate = max(min(max_val, rate), min_val)
            self.__sample_rate = float(rate)
        return

    @property
    def data_type(self):
        """
        Read-only property to return the currently set data type

        @return type: current data type
        """
        return self.__data_type

    @property
    def buffer_size(self):
        """
        Read-only property to return the currently buffer size.
        Buffer size corresponds to the number of samples per channel that can be buffered. So the
        actual buffer size in bytes can be estimated by:
            buffer_size * number_of_channels * size_in_bytes(data_type)

        @return int: current buffer size in samples per channel
        """
        return self.__buffer_size

    @buffer_size.setter
    def buffer_size(self, size):
        if self._check_settings_change():
            size = int(size)
            if size < 1:
                self.log.error('Buffer size smaller than 1 makes no sense. Tried to set {0} as '
                               'buffer size and failed.'.format(size))
                return
            self.__buffer_size = int(size)
            self._init_buffer()
        return

    @property
    def number_of_channels(self):
        """
        Read-only property to return the currently configured number of data channels.

        @return int: the currently set number of channels
        """
        return len(self.__active_channels)

    @property
    def active_channels(self):
        """
        The currently configured data channel properties.
        Returns a dict with channel names as keys and corresponding StreamChannel instances as
        values.

        @return dict: currently active data channel properties with keys being the channel names
                      and values being the corresponding StreamChannel instances.
        """
        return (ch.copy() for ch in self.__active_channels)

    @active_channels.setter
    def active_channels(self, channels):
        if self._check_settings_change():
            channels = tuple(channels)
            avail_chnl_names = tuple(ch.name for ch in self.available_channels)
            if any(ch not in avail_chnl_names for ch in channels):
                self.log.error('Invalid channel to stream from encountered: {0}.\nValid channels '
                               'are: {1}'
                               ''.format(channels, avail_chnl_names))
                return
            self.__active_channels = channels
        return

    def get_constraints(self):
        """
        Return the constraints on the settings for this data streamer.

        @return DataInStreamConstraints: Instance of DataInStreamConstraints containing constraints
        """
        return self._constraints.copy()

    def start_stream(self):
        """
        Start the data acquisition and data stream.

        @return int: error code (0: OK, -1: Error)
        """
        if self.is_running:
            self.log.warning('Unable to start input stream. It is already running.')
            return 0

        self._init_buffer()
        self._is_running = True
        self._start_time = time.perf_counter()
        self._last_read = self._start_time

        self.Counterfunc=dict()
        for chn in self.__active_channels:
            self.Counterfunc[chn] = self._tt.counter(channels=[self._tt.channel_codes[chn]], refresh_rate=self.__sample_rate, n_values=(self.buffer_size // self.number_of_channels))
        return 0

    def stop_stream(self):
        """
        Stop the data acquisition and data stream.

        @return int: error code (0: OK, -1: Error)
        """
        if self.is_running:
            self._is_running = False
        if hasattr(self, 'Counterfunc'):
            for chn in self.__active_channels:
                self.Counterfunc[chn].clear()
        return 0

    def read_data_into_buffer(self, buffer, number_of_samples=None):
        """
        Read data from the stream buffer into a 1D/2D numpy array given as parameter.
        In case of a single data channel the numpy array can be either 1D or 2D. In case of more
        channels the array must be 2D with the first index corresponding to the channel number and
        the second index serving as sample index:
            buffer.shape == (self.number_of_channels, number_of_samples)
        The numpy array must have the same data type as self.data_type.
        If number_of_samples is omitted it will be derived from buffer.shape[1]

        This method will not return until all requested samples have been read or a timeout occurs.

        @param numpy.ndarray buffer: The numpy array to write the samples to
        @param int number_of_samples: optional, number of samples to read per channel. If omitted,
                                      this number will be derived from buffer axis 1 size.

        @return int: Number of samples read into buffer; negative value indicates error
                     (e.g. read timeout)
        """
        if not self.is_running:
            self.log.error('Unable to read data. Device is not running.')
            return -1

        if not isinstance(buffer, np.ndarray) or buffer.dtype != self.__data_type:
            self.log.error('buffer must be numpy.ndarray with dtype {0}. Read failed.'
                           ''.format(self.__data_type))
            return -1

        if buffer.ndim == 2:
            if buffer.shape[0] != self.number_of_channels:
                self.log.error('Configured number of channels ({0:d}) does not match first '
                               'dimension of 2D buffer array ({1:d}).'
                               ''.format(self.number_of_channels, buffer.shape[0]))
                return -1
            number_of_samples = buffer.shape[1] if number_of_samples is None else number_of_samples
            buffer = buffer.flatten()
        elif buffer.ndim == 1:
            number_of_samples = (buffer.size // self.number_of_channels) if number_of_samples is None else number_of_samples
        else:
            self.log.error('Buffer must be a 1D or 2D numpy.ndarray.')
            return -1

        if number_of_samples < 1:
            return 0
        while self.available_samples < number_of_samples:
            tools.delay(1)

        # Check for buffer overflow
        avail_samples = self.available_samples
        if avail_samples > self.buffer_size:
            self._has_overflown = True


        self._last_read = time.perf_counter()

        write_offset = 0
        for i, chn in enumerate(self.__active_channels):
            buffer[write_offset:(write_offset+number_of_samples)] = self.Counterfunc[chn].getData()[0][-number_of_samples:]
            write_offset += number_of_samples
        return number_of_samples

    def read_available_data_into_buffer(self, buffer):
        """
        Read data from the stream buffer into a 1D/2D numpy array given as parameter.
        In case of a single data channel the numpy array can be either 1D or 2D. In case of more
        channels the array must be 2D with the first index corresponding to the channel number and
        the second index serving as sample index:
            buffer.shape == (self.number_of_channels, number_of_samples)
        The numpy array must have the same data type as self.data_type.

        This method will read all currently available samples into buffer. If number of available
        samples exceed buffer size, read only as many samples as fit into the buffer.

        @param numpy.ndarray buffer: The numpy array to write the samples to

        @return int: Number of samples read into buffer; negative value indicates error
                     (e.g. read timeout)

        adjust number_of_samples to min(buffer.size // self.number_of_channels, self.available_samples)
        """
        if not self.is_running:
            self.log.error('Unable to read data. Device is not running.')
            return -1

        avail_samples = min(buffer.size // self.number_of_channels, self.available_samples)
        return self.read_data_into_buffer(buffer=buffer, number_of_samples=avail_samples)

    def read_data(self, number_of_samples=None):
        """
        Read data from the stream buffer into a 2D numpy array and return it.
        The arrays first index corresponds to the channel number and the second index serves as
        sample index:
            return_array.shape == (self.number_of_channels, number_of_samples)
        The numpy arrays data type is the one defined in self.data_type.
        If number_of_samples is omitted all currently available samples are read from buffer.

        This method will not return until all requested samples have been read or a timeout occurs.

        @param int number_of_samples: optional, number of samples to read per channel. If omitted,
                                      all available samples are read from buffer.

        @return numpy.ndarray: The read samples


        reshape the data buffer from read_data_into_buffer, delete extra zeros in the buffer
        """
        if not self.is_running:
            self.log.error('Unable to read data. Device is not running.')
            return np.empty((0, 0), dtype=self.data_type)

        if number_of_samples is None:
            read_samples = self.read_available_data_into_buffer(self._data_buffer)
            if read_samples < 0:
                return np.empty((0, 0), dtype=self.data_type)
        else:
            read_samples = self.read_data_into_buffer(self._data_buffer,
                                                      number_of_samples=number_of_samples)
            if read_samples != number_of_samples:
                return np.empty((0, 0), dtype=self.data_type)

        total_samples = self.number_of_channels * read_samples
        return self._data_buffer[:total_samples].reshape((self.number_of_channels,
                                                          number_of_samples))

    def read_single_point(self):
        """
        This method will initiate a single sample read on each configured data channel.
        In general this sample may not be acquired simultaneous for all channels and timing in
        general can not be assured. Us this method if you want to have a non-timing-critical
        snapshot of your current data channel input.
        May not be available for all devices.
        The returned 1D numpy array will contain one sample for each channel.

        @return numpy.ndarray: 1D array containing one sample for each channel. Empty array
                               indicates error.
        """
        # if not self.is_running:
        #     self.log.error('Unable to read data. Device is not running.')
        #     return np.empty(0, dtype=self.__data_type)

        # data = np.empty(self.number_of_channels, dtype=self.__data_type)
        # self._last_read = self.Counterfunc[self.__active_channels[0]].getIndex()[0][-1] 
        # for i, chnl in enumerate(self.__active_channels):
        #     if chnl in self._digital_channels:
        #         ch_index = self._digital_channels.index(chnl)
        #         events_per_bin = self._digital_event_rates[ch_index] / self.__sample_rate
        #         data[i] = np.random.poisson(events_per_bin)
        #     else:
        #         ch_index = self._analog_channels.index(chnl)
        #         amplitude = self._analog_amplitudes[ch_index]
        #         noise_level = 0.05 * amplitude
        #         noise = noise_level - 2 * noise_level * np.random.rand()
        #         data[i] = amplitude * np.sin(analog_x) + noise
        # return data
        pass

    @property
    def available_channels(self):
        """
        Read-only property to return the currently used data channel properties.
        Returns a dict with channel names as keys and corresponding StreamChannel instances as
        values.

        @return tuple: data channel properties for all available channels with keys being the
                       channel names and values being the corresponding StreamChannel instances.
        """
        return (*(ch.copy() for ch in self._constraints.digital_channels),
                *(ch.copy() for ch in self._constraints.analog_channels))


    @property
    def available_samples(self):
        """
        Read-only property to return the currently available number of samples per channel ready
        to read from buffer.

        @return int: Number of available samples per channel
        """
        if not self.is_running:
            return 0
        return int((time.perf_counter() - self._last_read) * self.__sample_rate)

    @property
    def is_running(self):
        """
        Read-only flag indicating if the data acquisition is running.

        @return bool: Data acquisition is running (True) or not (False)
        """
        return self._is_running

    @property
    def buffer_overflown(self):
        """
        Read-only flag to check if the read buffer has overflown.
        In case of a circular buffer it indicates data loss.
        In case of a non-circular buffer the data acquisition should have stopped if this flag is
        coming up.
        Flag will only be reset after starting a new data acquisition.

        @return bool: Flag indicates if buffer has overflown (True) or not (False)
        """
        return self._has_overflown



    # =============================================================================================
    def _clk_frequency_valid(self, frequency):
        if self._analog_channels:
            max_rate = self._constraints.combined_sample_rate.max
            min_rate = self._constraints.combined_sample_rate.min
        else:
            max_rate = self._constraints.digital_sample_rate.max
            min_rate = self._constraints.digital_sample_rate.min
        return min_rate <= frequency <= max_rate

    def _init_buffer(self):
        if not self.is_running:
            self._data_buffer = np.zeros(
                self.number_of_channels * self.buffer_size,
                dtype=self.data_type)
            self._has_overflown = False
        return

    def _check_settings_change(self):
        """
        Helper method to check if streamer settings can be changed, i.e. if the streamer is idle.
        Throw a warning if the streamer is running.

        @return bool: Flag indicating if settings can be changed (True) or not (False)
        """
        if self.is_running:
            self.log.warning('Unable to change streamer settings while streamer is running. '
                             'New settings ignored.')
            return False
        return True