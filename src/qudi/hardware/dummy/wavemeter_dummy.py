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


class WavemeterDummy(Base):
    # Todo change of wavemeter interface
    # todo push
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
    _measurement_timing = ConfigOption('measurement_timing', 10.e-3)
    #todo check available units
    _unit = ConfigOption('unit', 'vac')
    automatic_acquisition = ConfigOption('automatic_acquisition', True)

    _sig_start_hardware_query = QtCore.Signal()

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

        # the inital wavelength as list which should contain timestamp and wavelength
        self._wavelength = list()

        # initial set of property showing if acquisition is running
        self._is_running = False
        self._last_error = 0, ''
        # self._initial_wavelength = round(random.uniform(420, 1100), 2) * 10 ** (-9)

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

        # start automatically measurement thread on activate
        if self.automatic_acquisition:
            self._set_run(True)

    def on_deactivate(self):
        """
        Deactivate module.
        Stop threaded _start_hardware_query
        Disconnects signal to _start_hardware_query
        """
        self.is_running = False
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
        # set initial wavemeter value randomly between 4200nm and 1100nm in SI units
        # todo should not be here because it isn't likely that the wavelength jumps so much
        # todo how to do that wavelength is changed in certain step to previous wavelength?
        wavelength = round(random.uniform(420, 1100), 2) * 10 ** (-9)
        #self._parentclass._current_wavelength2 += random.uniform(-range_step, range_step)

        if wavelength > 0:
            with self.threadlock:
                self._wavelength.append((time.time(), wavelength))
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
        Property for saving if some errorous wavelength was detected.

        @return tuple: Error number, error message.
        """
        tmp_error = self._last_error[0], self._last_error[1]
        self._last_error = 0, ''
        return tmp_error

    @property
    def is_running(self):
        """
        Property to indicate if measurement is running, and used to start and stop measurements.

        @ return bool: True if measurement thread is running, False if not.
        """
        return self._is_running

    @is_running.setter
    def is_running(self, value):
        """
        Setter of the is_running property. Uses the protected function _set_run but with additional
        sanity checks of the current module state. Setting the value starts or stops the measurement

        @ param bool value: True starts the measurement, False stops
        """
        # todo should be here some return value if that worked?
        if value:
            if self.module_state() == 'idle':
                self._set_run(True)
            else:
                self.log.warning('acquisition already running, nothing done')
        if not value:
            if self.module_state() != 'idle':
                self._set_run(False)
                self.log.warning('stop requested, stopping the measurement')
            else:
                self.log.warning('stop requested, but measurement was already stopped before.')

    def _set_run(self, value):
        """
        Protected function to set the is_running property. The is_running.setter uses this function.
        Written in protected way that during activation already the measurement thread can be
        started.
        Uses signal emitting to start the hardware query.
        """
        self._is_running = value
        if value:
            self._sig_start_hardware_query.emit()
            self.log.info('measurement thread started')

    @property
    def wavelength(self):
        """
        Property wavelength gets list of wavelengths which have been collected.

        @return tuple result: returns list with two entries, first the time second the wavelength
        """
        with self.threadlock:
            #todo do here the unit conversion

            # self._convert_unit(self._unit)
            result = tuple(self._wavelength)
            self._wavelength = list()
            return result

    @property
    def unit(self):
        """
        Property to store the unit of measured value.

        @return str: Returns the unit as a string
        """
        return self._unit

    @unit.setter
    def unit(self, value):
        """
        Sets a different unit.

        @params str value: The target unit inserted as str.
        """
        #todo use here convert unit
        self._unit = value

    @property
    def measurement_timing(self):
        """
        Property measurement timing given in seconds.
        """
        return self._measurement_timing

    @measurement_timing.setter
    def measurement_timing(self, timing):
        """
        Setter for the measurement timing.

        @params float timing: sets the measurement timing. Has to be given in seconds
        """
        self._measurement_timing = float(timing)

    def _convert_unit(self, value, unit_from, unit_to):
        """
        Converts a wavelength value from one to another unit if in unit dict.

        @params float value: Here to put in the actual measurement value
        @params str unit_from: Here to put string of actual unit
        @params str unit_to: Here to put a string out of unit dictionary

        @return float: value converted in other unit
        """
        #todo rewrite convert unit that suitable for list?
        #todo how to handle convert unit during one measurement? Probably the whole list...
        refractive_index_air = 1.0003
        #todo write dict of units somewhere else?
        units = {'vac', 'air', 'freq'}
        if unit_from and unit_to in units:
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