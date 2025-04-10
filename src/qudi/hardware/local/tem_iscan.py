# -*- coding: utf-8 -*-

from qtpy import QtCore
from qudi.core.module import Base
from qudi.core.configoption import ConfigOption
from qudi.util.mutex import Mutex
import pyvisa as visa
import queue

class HardwarePull(QtCore.QObject):
    """ Helper class for running the hardware communication in a separate thread. """

    def __init__(self, parentclass):
        super().__init__()
        # remember the reference to the parent class to access functions and settings
        self._parentclass = parentclass


    def handle_timer(self, state_change):
        """ Threaded method that can be called by a signal from outside to start the timer.

        @param bool state: (True) starts timer, (False) stops it.
        """
        if state_change:
            self.timer = QtCore.QTimer()
            # every _readout_timing (ms) read out the output from iScan
            self.timer.timeout.connect(self._measure_thread)
            self.timer.start(self._parentclass._readout_timing)
        else:
            if hasattr(self, 'timer'):
                self.timer.stop()

    def _measure_thread(self):
        """ The threaded method querying the data from the wavemeter.
        """

        # update as long as the state is busy
        if self._parentclass.module_state() == 'locked':
            try:
                # get the current output from the device
                line=self._parentclass._my_instrument.read()
                try:
                    self.read_queue.put_nowait(line)
                except queue.Full:


            setpoint = self._parentclass.get_reference_course()
            if self._parentclass.get_deviation_mode() and abs(setpoint - wavelength) < 0.00005:
                is_stable = True
            else:
                is_stable = False

            # send the data to the parent via a signal
            self.sig_wavelength.emit(wavelength, is_stable)

class iScan(Base):
    """ Designed for remote communication to the iScan system from TEM-technik

    Example config for copy-paste:
    iScan:
        module.Class: 'local.tem_iscan.iScan'
        options:
            port:
                - 'COM9'

    """

    # config options
    _resurce_name = ConfigOption('port', list(), missing='error')

    def on_activate(self):
        self.rm = visa.ResourceManager()
        try:
            self._my_instrument = self.rm.open_resource(resource_name = self._resurce_name[0], baud_rate=57600, write_termination='\r\n', read_termination='\r\n')
        except:
            self.log.error('Could not connect to iScan.')
            self.rm.close()
            self._readout_timing = 100
        

    def on_deactivate(self):
        self._my_instrument.close()
        self.rm.close()
        return 0

    def _prepare_commmand(self,command):
        if not self.echo
