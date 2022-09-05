# -*- coding: utf-8 -*-

"""
This module contains a POI Manager core class which gives capability to mark
points of interest, re-optimise their position, and keep track of sample drift
over time.

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

from qtpy import QtCore
import ctypes   # is a foreign function library for Python. It provides C
                # compatible data types, and allows calling functions in DLLs
                # or shared libraries. It can be used to wrap these libraries
                # in pure Python.

from qudi.interface.wavemeter_interface import WavemeterInterface
from qudi.core.module import Base
from qudi.core.configoption import ConfigOption
from qudi.util.mutex import Mutex


class HardwarePull(QtCore.QObject):
    """ Helper class for running the hardware communication in a separate thread. """

    # signal to deliver the wavelength to the parent class
    sig_wavelength = QtCore.Signal(float, bool)

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
        """ The threaded method querying the data from the wavemeter.
        """

        # update as long as the state is busy
        if self._parentclass.module_state() == 'locked':
            # get the current wavelength from the wavemeter
            wavelength=float(self._parentclass._wavemeterdll.GetWavelength(0))
            setpoint = self._parentclass.get_reference_course()
            if self._parentclass.get_deviation_mode() and abs(setpoint - wavelength) < 0.00003:
                is_stable = True
            else:
                is_stable = False

            # send the data to the parent via a signal
            self.sig_wavelength.emit(wavelength, is_stable)



class HighFinesseWavemeter(WavemeterInterface):
    """ Hardware class to controls a High Finesse Wavemeter.

    Example config for copy-paste:

    high_finesse_wavemeter:
        module.Class: 'high_finesse_wavemeter.HighFinesseWavemeter'
        measurement_timing: 10.0 # in seconds

    """



    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)



    def on_activate(self):
        #############################################
        # Initialisation to access external DLL
        #############################################
        pass


    def on_deactivate(self):
        pass


    #############################################
    # Methods of the main class
    #############################################

    def handle_wavelength(self, wavelength, is_stable):
        """ Function to save the wavelength, when it comes in with a signal.
        """
        pass

    def start_acquisition(self):
        """ Method to start the wavemeter software.

        @return int: error code (0:OK, -1:error)

        Also the actual threaded method for getting the current wavemeter reading is started.
        """

        pass

    def stop_acquisition(self):
        """ Stops the Wavemeter from measuring and kills the thread that queries the data.

        @return int: error code (0:OK, -1:error)
        """
        pass
    
    def set_exposure_mode(self, mode):
        pass


    def is_measuring(self):
        """
        self._wavemeterdll.GetOperationState(0) gives out:
        0 for stoped
        1 for Adjustment
        2 for Measurement
        """
        pass

    

    def get_current_wavelength(self):
        """ This method returns the current wavelength in Vac.
        """
        pass

    def get_current_wavelength2(self):
        pass


    def convert_unit(self,value, from_ , to_):
        """
        Convert unit between:
        'WavelengthVac'[nm], 
        'WavelengthAir'[nm],
        'Frequency'[THz],
        'Wavenumber'[1/cm],
        'PhotonEnergy'[eV]
        """
        pass


    def get_deviation_mode(self):
        pass

    def set_deviation_mode(self, mode):
        pass

    def get_timing(self):
        """ Get the timing of the internal measurement thread.

        @return float: clock length in second
        """
        pass

    def set_timing(self, timing):
        """ Set the timing of the internal measurement thread.

        @param float timing: clock length in second

        @return int: error code (0:OK, -1:error)
        """
        pass


    def get_reference_course(self, channel = 1) -> str:
        """
        Arguments: channel
        Returns: the string corresponing to the reference set on the WLM.
        For example, constant reference: '619.1234'
        Or a sawtooth with a center at '619.1234 + 0.001 * sawtooth(t/10)'
        """
        pass
    

    def set_reference_course(self, reference, channel = 1):
        """
        Arguments: the reference set on the WLM.
        Returns: None
        """ 

        pass