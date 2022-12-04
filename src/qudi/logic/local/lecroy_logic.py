# -*- coding: utf-8 -*-

from qudi.core.configoption import ConfigOption
from qudi.core.connector import Connector
from qudi.core.module import LogicBase
from qudi.util.mutex import Mutex
from PySide2 import QtCore
import time
import numpy as np

class HardwarePull(QtCore.QObject):
    """ Helper class for running the hardware communication in a separate thread. """

    # signal to deliver the wavelength to the parent class
    sig_dataframe = QtCore.Signal(object)

    def __init__(self, parentclass):
        super().__init__()

        # remember the reference to the parent class to access functions ad settings
        self._parentclass = parentclass


    def handle_timer(self, state_change):
        """ Threaded method that can be called by a signal from outside to start the timer.

        @param bool state: (True) starts timer, (False) stops it.
        """

        if state_change:
            self.timer = QtCore.QTimer()
            # every _measurement_timing (ms) send out the signal
            self.timer.timeout.connect(self._measure_thread)
            self.timer.start(self._parentclass._measurement_timing)
        else:
            if hasattr(self, 'timer'):
                self.timer.stop()

    def _measure_thread(self):
        """ The threaded method querying the data from the scope.
        """

        # update as long as the state is busy
        if self._parentclass.module_state() == 'locked':
            # get the current dataframe from the scope
            _, Dataframe=self._parentclass._scope.getDataFloats(channel=str(self._parentclass._channel))

            # send the data to the parent via a signal
            self.sig_dataframe.emit(Dataframe)


class LecroyLogic(LogicBase):

    """

    Example config for copy-paste:

    lecroy_scope_logic:
        module.Class: 'local.lecroy_logic.LecroyLogic'
        connect:
            scope1: 'lecroy_scope'
        options:
            measurement_timing: 100.0 # in miliseconds
            channel: 'C1'
            channel_resolution: 1000
    """



    scope1 = Connector(interface='ScopeInterface')
    # configoptions
    _measurement_timing = ConfigOption('measurement_timing', default=100.)
    _channel = ConfigOption('channel', default='C1')
    _channel_resolution = ConfigOption('channel_resolution', default = 1000)
    # signals
    sig_handle_timer = QtCore.Signal(bool)
    signal_plots_updated = QtCore.Signal()

    def __init__(self, config, **kwargs):
        super().__init__(config= config, **kwargs)
        self.threadlock = Mutex()

    def on_activate(self):
        self._scope = self.scope1()


        # create an indepentent thread for the hardware communication
        self.hardware_thread = QtCore.QThread()

        # create an object for the hardware communication and let it live on the new thread
        self._hardware_pull = HardwarePull(self)
        self._hardware_pull.moveToThread(self.hardware_thread)

        # connect the signals in and out of the threaded object
        self.sig_handle_timer.connect(self._hardware_pull.handle_timer)
        self._hardware_pull.sig_dataframe.connect(self.handle_dataframe, QtCore.Qt.DirectConnection)

        # start the event loop for the hardware
        self.hardware_thread.start()

        # init dataframe for plots
        self._dataframe_y = np.zeros(self._channel_resolution)
        self._dataframe_x = np.linspace(0, self._channel_resolution, self._channel_resolution)

    def on_deactivate(self):
        if self.module_state() != 'idle' and self.module_state() != 'deactivated':
            self.stop_acquisition()
        self.hardware_thread.quit()
        self.sig_handle_timer.disconnect()
        self._hardware_pull.sig_dataframe.disconnect()

    def handle_dataframe(self, dataframe):
        """ Function to save the wavelength, when it comes in with a signal.
        """
        # self._dataframe_y = dataframe
        self._dataframe_x = np.linspace(0, len(dataframe), len(dataframe))


        normIndex = np.where(dataframe == np.max(dataframe))
        valList = np.zeros(50)
        for i in range(50):
            val = dataframe[normIndex[0][0] + i]
            valList[i] = val

        normFactor = np.mean(valList)
        self._dataframe_y = dataframe/normFactor
        self.signal_plots_updated.emit()



    def start_acquisition(self):
        """ Method to start the acquisition.

        @return int: error code (0:OK, -1:error)

        Also the actual threaded method for getting the current wavemeter reading is started.
        """

        # first check its status
        if self.module_state() == 'locked':
            self.log.error('Scope busy')
            return -1

        self.module_state.lock()

        # start the measuring thread
        self.sig_handle_timer.emit(True)

        return 0

    def stop_acquisition(self):
        """ Stops the acquisition from measuring and kills the thread that queries the data.

        @return int: error code (0:OK, -1:error)
        """
        # check status just for a sanity check
        if self.module_state() == 'idle':
            self.log.warning('Acquisition was already stopped, stopping it '
                    'anyway!')
        else:
            # stop the measurement thread
            self.sig_handle_timer.emit(False)
            # set status to idle again
            self.module_state.unlock()
        return 0


    def get_timing(self):
        """ Get the timing of the internal measurement thread.

        @return float: clock length in second
        """
        return self._measurement_timing

    def set_timing(self, timing):
        """ Set the timing of the internal measurement thread.

        @param float timing: clock length in second

        @return int: error code (0:OK, -1:error)
        """
        self._measurement_timing=float(timing)
        return 0