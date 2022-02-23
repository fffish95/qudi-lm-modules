# -*- coding: utf-8 -*-

"""
This module provides a dummy wavemeter hardware module that is useful for
troubleshooting logic and gui modules.

Copyright (c) 2021, the qudi developers. See the AUTHORS.md file at the top-level directory of this
distribution and on <https://github.com/Ulm-IQO/qudi-iqo-modules/>

This file is part of qudi.

Qudi is free software: you can redistribute it and/or modify it under the terms of
the GNU Lesser General Public License as published by the Free Software Foundation,
either version 3 of the License, or (at your option) any later version.

Qudi is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY;
without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
See the GNU Lesser General Public License for more details.

You should have received a copy of the GNU Lesser General Public License along with qudi.
If not, see <https://www.gnu.org/licenses/>.
"""

import random
import scipy.constants as sc
from PySide2 import QtCore
import time

from qudi.core.configoption import ConfigOption
from qudi.core.module import Base
from qudi.interface.wavemeter_interface import WavemeterInterface
from qudi.util.mutex import Mutex


class WavemeterDummy(WavemeterInterface):
    """ Threaded dummy hardware class to simulate the controls for a wavemeter.

    Example config for copy-paste:

    wavemeter_dummy:
        module.Class: 'wavemeter_dummy.WavemeterDummy'
        measurement_timing: 10.0e-3 # measurement timing should be given in seconds
        unit: 'vac' # unit of the read out wavelength
        automatic_acquisition: True # if set True on activation of the module measurement starts
    """
    _threaded = True

    # config opts
    _measurement_timing = ConfigOption(name='measurement_timing', default=10.e-3)
    # todo check available units?
    _unit = ConfigOption(name='unit', default='vac')
    automatic_acquisition = ConfigOption(name='automatic_acquisition', default=True)

    _sig_start_hardware_query = QtCore.Signal()

    available_units = {'vac', 'air', 'freq'}

    error_dict = {0: 'Error no value as acquisition stopped',
                  -1: 'Error no signal, wavlength meter has not detected any signal.',
                  -2: 'Error bad signal, wavelength meter has not detected calculatable signal',
                  -3: 'Error low signal, signal is too small to be calculated properly',
                  -4: 'Error big signal, signal is too large to be calculated properly',
                  -5: 'Error wavelength meter missing',
                  -6: 'Error not available',
                  -7: 'Nothing changed',
                  -8: ' Error no pulse, the detected signal could not be divided in separated '
                      'pulses',
                  -13: 'Error division by 0',
                  -14: 'Error out of range',
                  -15: 'Error unit not available'}

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)

        # locking for thread safety
        self.threadlock = Mutex()

        # the initial wavelength as list which should contain timestamp and wavelength
        self._wavelength = list()

        # initial set of property showing if acquisition is running
        self._is_running = False
        self._last_error = 0, ''
        self._initial_wavelength = round(random.uniform(420, 1100), 2) * 10 ** (-9)
        self._current_wavelength = 0.0

    def on_activate(self):
        """
        Activate module.
        Connects signal to the hardware query mimicing measurement of a wavelength.
        Will automatically start measurement if ConfigOption automatic_acquisition is set to True.
        """
        self.log.warning("This module has not been tested on the new qudi core."
                         "Use with caution and contribute bug fixed back, please.")

        # connect signal to _start_hardware_query
        self._sig_start_hardware_query.connect(self._start_hardware_query)

        # start automatically measurement thread on activate using _set_run instead of
        # start_acquisition (latter one can't work until on_activate is fully through)
        if self.automatic_acquisition:
            self._set_run(True)

    def on_deactivate(self):
        """
        Deactivate module.
        Stop threaded _start_hardware_query
        Disconnects signal to _start_hardware_query
        """
        self.stop_acquisition()
        self._sig_start_hardware_query.disconnect(self._start_hardware_query)

    #############################################
    # Methods of the main class
    #############################################

    def _start_hardware_query(self):
        """
        Function who mimics the behavior of an hardware measuring some wavelength using QTimer
        single shot function.
        As soon as activated the module state is locked and also the thread is locked that no other
        function can do changes to this time to the wavelength.
        Module checks if the measured wavelength is valid, if not the error will be saved in the
        property _last_error
        """
        if self.module_state() == 'idle':
            self.module_state.lock()

        if self._current_wavelength == 0:
            self._current_wavelength = self._initial_wavelength
        range_step = 0.1 * 10 ** (-9)
        wavelength = self._current_wavelength + random.uniform(-range_step, range_step)

        if wavelength > 0:
            with self.threadlock:
                self._wavelength.append((time.time(), wavelength))
                self._current_wavelength = wavelength
        elif wavelength in self.error_dict:
            self._last_error = wavelength, self.error_dict[wavelength]
        else:
            self._last_error = wavelength, 'Unknown error'

        if self._is_running:
            QtCore.QTimer.singleShot(int(self._measurement_timing * 1e3),
                                     self._start_hardware_query)
        else:
            self.module_state.unlock()

    @property
    def last_error(self):
        """
        Property for saving if some erroneous wavelength was detected.

        @return tuple: Error number, error message.
        """
        tmp_error = self._last_error[0], self._last_error[1]
        self._last_error = 0, ''
        return tmp_error

    @property
    def is_running(self):
        """
        Read-only flag indicating if the data acquisition is running.

        @return bool: Data acquisition is running (True) or not (False)
        """
        return self._is_running

    def _set_run(self, value):
        """
        Protected function to set the is_running property.
        start_acquisition and stop_acquisition uses this function.
        Written in protected way that during activation already the measurement thread can be
        started.
        Method for getting the current wavemeter reading started.
        """
        self._is_running = value
        if value:
            self._initial_wavelength = round(random.uniform(420, 1100), 2) * 10 ** (-9)
            self._sig_start_hardware_query.emit()
            self.log.info('measurement thread started')
        else:
            self._initial_wavelength = 0.0
            self._current_wavelength = 0.0

    def start_acquisition(self):
        """ Method to start the wavemeter software.

        @return (int): error code (0:OK, -1:error)

        Also the actual threaded method for getting the current wavemeter
        reading is started.

        """
        if self.module_state() == 'idle':
            self._set_run(True)
            return 0
        else:
            self.log.warning('acquisition already running, nothing done')
            return -1

    def stop_acquisition(self):
        """ Stops the Wavemeter from measuring and kills the thread that queries the data.

        @return (int): error code (0:OK, -1:error)
        """
        if self.module_state() != 'idle':
            self._set_run(False)
            self.log.warning('stop requested, stopping the measurement')
        else:
            self.log.warning('stop requested, but measurement was already stopped before.')
        return 0

    @property
    def current_wavelength(self):
        """
        Read-only property

        @return float: returns current wavelength
        """
        if self._current_wavelength in self.error_dict:
            # self._last_error = self._current_wavelength, self.error_dict[self._current_wavelength]
            self.log.error(self.error_dict[self._current_wavelength])
        return self._current_wavelength

    def get_current_wavelength(self, unit):
        # todo implement this function or delete it as obsolete due to property current_wavelength
        """ This method returns the current wavelength.

        @param (str) unit: should be the unit in which the wavelength should be returned

        @return (float): wavelength (or negative value for errors)
        """
        pass

    def get_wavelength_stream(self):
        # todo implement this method
        """ This method gets a continuous stream of the measured wavelengths with timestamp.

        @return float: returns tuple list of measured wavelengths with timestamp
        """
        pass

    @property
    def wavelength(self):
        """
        Property wavelength gets list of wavelengths which have been collected.

        @return tuple result: returns list with two entries, first the time second the wavelength
        """
        with self.threadlock:
            #todo do here the unit conversion?

            # self.convert_unit(self._unit)
            result = tuple(self._wavelength)
            self._wavelength = list()
            return result

    @property
    def unit(self):
        """ Property to store the unit of measured value.

        @return str: Returns the unit as a string
        """
        return self._unit

    @unit.setter
    def unit(self, value):
        """ Sets a different unit.

        @params str value: The target unit inserted as str.
        """
        self._unit = value

    @property
    def measurement_timing(self):
        """ Get the measurement time

        @return (float): Measurement time in second
        """
        return self._measurement_timing

    @measurement_timing.setter
    def measurement_timing(self, timing):
        """ Set the measurement time

        @param (float) timing: Measurement time to set in second
        """
        self._measurement_timing = float(timing)

    def convert_unit(self, value, unit_from, unit_to):
        """
        Converts a wavelength value from one to another unit if in unit dict.

        @params float value: Here to put in the actual measurement value
        @params str unit_from: Here to put string of actual unit
        @params str unit_to: Here to put a string out of unit dictionary

        @return float: value converted in other unit
        """
        #todo how to handle convert unit during one measurement? How to make it suitable for whole list?
        refractive_index_air = 1.0003
        if unit_from and unit_to in self.available_units:
            if unit_from == unit_to:
                return value
            if unit_from == 'vac' and unit_to == 'freq':
                return sc.lambda2nu(value)
            if unit_from == 'vac' and unit_to == 'air':
                return value / refractive_index_air
            if unit_from == 'freq' and unit_to == 'vac':
                return sc.nu2lambda(value)
            if unit_from == 'freq' and unit_to == 'air':
                return sc.nu2lambda(value) / refractive_index_air
            if unit_from == 'air' and unit_to == 'vac':
                return value * refractive_index_air
            if unit_from == 'air' and unit_to == 'freq':
                return sc.lambda2nu(value * refractive_index_air)
        else:
            return self.log.error('not allowed unit(s)')