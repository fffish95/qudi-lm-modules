# -*- coding: utf-8 -*-

"""
A module for controlling a camera.

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

from PySide2 import QtCore
from qudi.core.connector import Connector
from qudi.core.configoption import ConfigOption
from qudi.core.module import LogicBase
from qudi.util.mutex import Mutex


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
            exposure = max(self._parentclass._exposure, self._parentclass._minimum_exposure_time)
            self.timer.timeout.connect(self._measure_thread)
            self.timer.start(1000*exposure)
        else:
            if hasattr(self, 'timer'):
                self.timer.stop()

    def _measure_thread(self):
        """ The threaded method querying the data from the scope.
        """

        # update as long as the state is busy
        if self._parentclass.module_state() == 'locked':
            # get the current dataframe from the camera
            Dataframe=self._parentclass._camera().get_acquired_data()
            # send the data to the parent via a signal
            self.sig_dataframe.emit(Dataframe)

class CameraLogic(LogicBase):
    """
    Control a camera.
    """

    # declare connectors
    _camera = Connector(name='camera', interface='CameraInterface')
    # declare config options
    _minimum_exposure_time = ConfigOption(name='minimum_exposure_time',
                                          default=0.05,
                                          missing='warn')

    # signals
    sigFrameChanged = QtCore.Signal(object)
    sigAcquisitionFinished = QtCore.Signal()
    sig_handle_timer = QtCore.Signal(bool)

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)
        self._thread_lock = Mutex()
        self._exposure = -1
        self._gain = -1
        self._last_frame = None


    def on_activate(self):
        """ Initialisation performed during activation of the module.
        """
        camera = self._camera()
        self._exposure = camera.get_exposure()
        self._gain = camera.get_gain()
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


    def on_deactivate(self):
        """ Perform required deactivation. """
        if self.module_state() != 'idle' and self.module_state() != 'deactivated':
            self.stop_acquisition()
        self.hardware_thread.quit()
        self.sig_handle_timer.disconnect()
        self._hardware_pull.sig_dataframe.disconnect()

    @property
    def last_frame(self):
        return self._last_frame

    def handle_dataframe(self, dataframe):
        """ Function to save the wavelength, when it comes in with a signal.
        """
        self._last_frame = dataframe
        self.sigFrameChanged.emit(self._last_frame)

    def set_exposure(self, time):
        """ Set exposure time of camera """
        with self._thread_lock:
            if self.module_state() == 'idle':
                camera = self._camera()
                camera.set_exposure(time)
                self._exposure = camera.get_exposure()
            else:
                self.log.error('Unable to set exposure time. Acquisition still in progress.')

    def get_exposure(self):
        """ Get exposure of hardware """
        with self._thread_lock:
            self._exposure = self._camera().get_exposure()
            return self._exposure

    def set_gain(self, gain):
        with self._thread_lock:
            if self.module_state() == 'idle':
                camera = self._camera()
                camera.set_gain(gain)
                self._gain = camera.get_gain()
            else:
                self.log.error('Unable to set gain. Acquisition still in progress.')

    def get_gain(self):
        with self._thread_lock:
            self._gain = self._camera().get_gain()
            return self._gain

    def capture_frame(self):
        """
        """
        with self._thread_lock:
            if self.module_state() == 'idle':
                self.module_state.lock()
                camera = self._camera()
                camera.start_single_acquisition()
                self._last_frame = camera.get_acquired_data()
                self.module_state.unlock()
                self.sigFrameChanged.emit(self._last_frame)
                self.sigAcquisitionFinished.emit()
            else:
                self.log.error('Unable to capture single frame. Acquisition still in progress.')

    def toggle_video(self, start):
        if start:
            self._start_video()
        else:
            self._stop_video()

    def _start_video(self):
        """ Start the data recording loop.
        """
        if self.module_state() == 'locked':
            self.log.error('Camera busy')
            return -1
        self.module_state.lock()
        camera = self._camera()
        camera.start_live_acquisition()
        camera.wait_for_next_frame()
        # start the measuring thread
        self.sig_handle_timer.emit(True)
    def _stop_video(self):
        """ Stop the data recording loop.
        """

        # check status just for a sanity check
        if self.module_state() == 'idle':
            self.log.warning('Acquisition was already stopped, stopping it '
                    'anyway!')
        else:
            # stop the measurement thread
            self.sig_handle_timer.emit(False)
            # stop acquisition
            self._camera().stop_acquisition()
            # set status to idle again
            self.module_state.unlock()
            self.sigAcquisitionFinished.emit()
        return 0

    def create_tag(self, time_stamp):
        return f"{time_stamp}_captured_frame"
