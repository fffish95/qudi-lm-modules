# -*- coding: utf-8 -*-
"""
This file contains a Qudi logic module for power control. Coarse control: with ND filter, fine control: with half waveplate and PBS.

Qudi is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

Qudi is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with Qudi. If not, see <http://www.gnu.org/licenses/>.

Copyright (c) the Qudi Developers. See the COPYRIGHT.txt file at the
top-level directory of this distribution and at <https://github.com/Ulm-IQO/qudi/>
"""
import numpy as np

from PySide2 import QtCore
from qudi.core.connector import Connector
from qudi.core.configoption import ConfigOption
from qudi.core.module import LogicBase
from qudi.util.mutex import Mutex



class HardwarePull(QtCore.QObject):
    """ Helper class for running the hardware communication in a separate thread. """

    # signal to deliver the wavelength to the parent class
    sig_power = QtCore.Signal(float)

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
            # get the current dataframe from the powermeter
            power=self._parentclass._tlpm.get_power()
            # send the data to the parent via a signal
            self.sig_power.emit(power)



class PowercontrolLogic(LogicBase):

    """
        sps_customscanlogic:
        module.Class: 'local.sps_custom_scan_logic.SPSCustonScanLogic'
    """
    # connector
    stepmotor1 = Connector(interface='MotorInterface')
    thorlabspm1 = Connnector(interface='ThorlabsPM')

    # signals
    sig_handle_timer = QtCore.Signal(bool)

    _measurement_timing = 100.

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        #locking for thread safety
        self.threadlock = Mutex()

        # the current power read by the powermeter in W
        self._current_power = 0.0

    def on_activate(self):
        """ Initialisation performed during activation of the module.
        """
        self._motor = self.stepmotor1()
        self._tlpm = self.thorlabspm1()

        # create an indepentent thread for the hardware communication
        self.hardware_thread = QtCore.QThread()

        # create an object for the hardware communication and let it live on the new thread
        self._hardware_pull = HardwarePull(self)
        self._hardware_pull.moveToThread(self.hardware_thread)

        # connect the signals in and out of the threaded object
        self.sig_handle_timer.connect(self._hardware_pull.handle_timer)
        self._hardware_pull.sig_power.connect(self.handle_power, QtCore.Qt.DirectConnection)

        # start the event loop for the hardware
        self.hardware_thread.start()

    def on_deactivate(self):
        """ Deinitialisation performed during deactivation of the module.
        """
        return 0
    

    def handle_power(self, power):
        """ Function to save the power, when it comes in with a signal.
        """
        self._current_power = power

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
    
    def get_stepmotor_





    def get_s
