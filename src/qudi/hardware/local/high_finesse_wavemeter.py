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
            if self._parentclass.get_deviation_mode() and abs(setpoint - wavelength) < 0.00005:
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

    # config options
    _measurement_timing = ConfigOption('measurement_timing', default=10.)

    # signals
    sig_handle_timer = QtCore.Signal(bool)

    #############################################
    # Flags for the external DLL
    #############################################

    # define constants as flags for the wavemeter
    _cCtrlStop                   = ctypes.c_uint16(0x00)
    # this following flag is modified to override every existing file
    _cCtrlStartMeasurment        = ctypes.c_uint16(0x1002)
    
    _cReturnWavelangthVac        = ctypes.c_long(0x0000)
    _cReturnWavelangthAir        = ctypes.c_long(0x0001)
    _cReturnFrequency        = ctypes.c_long(0x0002)
    _cReturnWavenumber        = ctypes.c_long(0x0003)
    _cReturnPhotonEnergy        = ctypes.c_long(0x0004)

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)

        #locking for thread safety
        self.threadlock = Mutex()

        # the current wavelength read by the wavemeter in nm (vac)
        self._current_wavelength = 0.0
        self._current_wavelength2 = 0.0
        self._is_stable = False


    def on_activate(self):
        #############################################
        # Initialisation to access external DLL
        #############################################
        try:
            # imports the spectrometer specific function from dll
            self._wavemeterdll = ctypes.windll.LoadLibrary('wlmData.dll')

        except:
            self.log.critical('There is no Wavemeter installed on this '
                    'Computer.\nPlease install a High Finesse Wavemeter and '
                    'try again.')

        # define the use of the GetWavelength function of the wavemeter
#        self._GetWavelength2 = self._wavemeterdll.GetWavelength2
        # return data type of the GetWavelength function of the wavemeter
        self._wavemeterdll.GetWavelength2.restype = ctypes.c_double
        # parameter data type of the GetWavelength function of the wavemeter
        self._wavemeterdll.GetWavelength2.argtypes = [ctypes.c_double]

        # define the use of the GetWavelength function of the wavemeter
#        self._GetWavelength = self._wavemeterdll.GetWavelength
        # return data type of the GetWavelength function of the wavemeter
        self._wavemeterdll.GetWavelength.restype = ctypes.c_double
        # parameter data type of the GetWavelength function of the wavemeter
        self._wavemeterdll.GetWavelength.argtypes = [ctypes.c_double]

        # define the use of the ConvertUnit function of the wavemeter
#        self._ConvertUnit = self._wavemeterdll.ConvertUnit
        # return data type of the ConvertUnit function of the wavemeter
        self._wavemeterdll.ConvertUnit.restype = ctypes.c_double
        # parameter data type of the ConvertUnit function of the wavemeter
        self._wavemeterdll.ConvertUnit.argtypes = [ctypes.c_double, ctypes.c_long, ctypes.c_long]

        # manipulate perdefined operations with simple flags
#        self._Operation = self._wavemeterdll.Operation
        # return data type of the Operation function of the wavemeter
        self._wavemeterdll.Operation.restype = ctypes.c_long
        # parameter data type of the Operation function of the wavemeter
        self._wavemeterdll.Operation.argtypes = [ctypes.c_ushort]

        # return data type of the GetDeviationMode function of the wavemeter
        self._wavemeterdll.GetDeviationMode.restype = ctypes.c_bool
        # parameter data type of the GetDeviationMode function of the wavemeter
        self._wavemeterdll.GetDeviationMode.argtypes = [ctypes.c_bool]

        # return data type of the SetDeviationMode function of the wavemeter
        self._wavemeterdll.SetDeviationMode.restype = ctypes.c_bool
        # parameter data type of the SetDeviationMode function of the wavemeter
        self._wavemeterdll.SetDeviationMode.argtypes = [ctypes.c_long]

        # return data type of the GetOperationState function of the wavemeter
        self._wavemeterdll.GetOperationState.restype = ctypes.c_ushort
        # parameter data type of the GetOperationState function of the wavemeter
        self._wavemeterdll.GetOperationState.argtypes = [ctypes.c_ushort]

        # return data type of the SetExposureMode function of the wavemeter
        self._wavemeterdll.SetExposureMode.restype = ctypes.c_long
        # parameter data type of the SetExposureMode function of the wavemeter
        self._wavemeterdll.SetExposureMode.argtypes = [ctypes.c_bool]



        # create an indepentent thread for the hardware communication
        self.hardware_thread = QtCore.QThread()

        # create an object for the hardware communication and let it live on the new thread
        self._hardware_pull = HardwarePull(self)
        self._hardware_pull.moveToThread(self.hardware_thread)

        # connect the signals in and out of the threaded object
        self.sig_handle_timer.connect(self._hardware_pull.handle_timer)
        self._hardware_pull.sig_wavelength.connect(self.handle_wavelength, QtCore.Qt.DirectConnection)

        # start the event loop for the hardware
        self.hardware_thread.start()


    def on_deactivate(self):
        if self.module_state() != 'idle' and self.module_state() != 'deactivated':
            self.stop_acquisition()
        self.hardware_thread.quit()
        self.sig_handle_timer.disconnect()
        self._hardware_pull.sig_wavelength.disconnect()

        try:
            # clean up by removing reference to the ctypes library object
            del self._wavemeterdll
            return 0
        except:
            self.log.error('Could not unload the wlmData.dll of the '
                    'wavemeter.')


    #############################################
    # Methods of the main class
    #############################################

    def handle_wavelength(self, wavelength, is_stable):
        """ Function to save the wavelength, when it comes in with a signal.
        """
        self._current_wavelength = wavelength
        self._is_stable = is_stable

    def start_acquisition(self):
        """ Method to start the wavemeter software.

        @return int: error code (0:OK, -1:error)

        Also the actual threaded method for getting the current wavemeter reading is started.
        """

        # first check its status
        if self.module_state() == 'locked':
            self.log.error('Wavemeter busy')
            return -1

        self.module_state.lock()
        if not self.is_measuring():
            # actually start the wavemeter
            self._wavemeterdll.Operation(self._cCtrlStartMeasurment) #starts measurement

        # start the measuring thread
        self.sig_handle_timer.emit(True)

        return 0

    def stop_acquisition(self):
        """ Stops the Wavemeter from measuring and kills the thread that queries the data.

        @return int: error code (0:OK, -1:error)
        """
        # check status just for a sanity check
        if self.module_state() == 'idle':
            self.log.warning('Wavemeter was already stopped, stopping it '
                    'anyway!')
        else:
            # stop the measurement thread
            self.sig_handle_timer.emit(False)
            # set status to idle again
            self.module_state.unlock()

        # turn off regulation
        self.set_deviation_mode(False)

        # Stop the actual wavemeter measurement
        self._wavemeterdll.Operation(self._cCtrlStop)

        return 0
    
    def set_exposure_mode(self, mode):
        self._wavemeterdll.SetExposureMode(mode)


    def is_measuring(self):
        """
        self._wavemeterdll.GetOperationState(0) gives out:
        0 for stoped
        1 for Adjustment
        2 for Measurement
        """
        return self._wavemeterdll.GetOperationState(0) == 2

    

    def get_current_wavelength(self):
        """ This method returns the current wavelength in Vac.
        """
        return self._current_wavelength

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
        if from_ in 'WavelengthVac':
            _from_ =  self._cReturnWavelangthVac
        elif from_ in 'WavelengthAir':
            _from_ =  self._cReturnWavelangthAir
        elif from_ in 'Frequency':
            _from_ =  self._cReturnFrequency
        elif from_ in 'Wavenumber':
            _from_ = self._cReturnWavenumber
        elif from_ in 'PhotonEnergy':
            _from_ = self._cReturnPhotonEnergy
        else:
            return -2

        if to_ in 'WavelengthVac':
            _to_ =  self._cReturnWavelangthVac
        elif to_ in 'WavelengthAir':
            _to_ =  self._cReturnWavelangthAir
        elif to_ in 'Frequency':
            _to_ =  self._cReturnFrequency
        elif to_ in 'Wavenumber':
            _to_ = self._cReturnWavenumber
        elif to_ in 'PhotonEnergy':
            _to_ = self._cReturnPhotonEnergy
        else:
            return -2

        return float(self._wavemeterdll.ConvertUnit(value,_from_,_to_))


    def get_deviation_mode(self):
        return self._wavemeterdll.GetDeviationMode(0)

    def set_deviation_mode(self, mode):
        self._wavemeterdll.SetDeviationMode(mode)

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


    def get_reference_course(self, channel = 1) -> str:
        """
        Arguments: channel
        Returns: the string corresponing to the reference set on the WLM.
        For example, constant reference: '619.1234'
        Or a sawtooth with a center at '619.1234 + 0.001 * sawtooth(t/10)'
        """
        string_buffer = ctypes.create_string_buffer(1024)
        xp = ctypes.cast(string_buffer, ctypes.POINTER(ctypes.c_char))
        self._wavemeterdll.GetPIDCourseNum.restype = ctypes.c_long
        self._wavemeterdll.GetPIDCourseNum.argtypes = [ctypes.c_long, xp]
        self._wavemeterdll.GetPIDCourseNum(channel, string_buffer)
        return float(string_buffer.value)
    

    def set_reference_course(self, reference, channel = 1):
        """
        Arguments: the reference set on the WLM.
        Returns: None
        """ 

        if reference < 0:
            raise Exception("No signal at the wavelengthmeter!")
        else:
            string_buffer = ctypes.create_string_buffer(1024)
            xp = ctypes.cast(string_buffer, ctypes.POINTER(ctypes.c_char))
            self._wavemeterdll.SetPIDCourseNum.restype = ctypes.c_long
            self._wavemeterdll.SetPIDCourseNum.argtypes = [ctypes.c_long, xp]
            string_buffer.value = "{}".format(reference).encode()
            self._wavemeterdll.SetPIDCourseNum(channel, string_buffer)
