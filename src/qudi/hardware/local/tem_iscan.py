# -*- coding: utf-8 -*-

from qtpy import QtCore
from qudi.core.module import Base
from qudi.core.configoption import ConfigOption
from qudi.util.mutex import Mutex
import pyvisa as visa
import queue

class HardwarePull(QtCore.QObject):
    """ Helper class for running the hardware communication in a separate thread. """

    # signal to deliver the message to the parent class
    iscan_msg_update = QtCore.Signal(list)
    def __init__(self, parentclass):
        super().__init__()
        # remember the reference to the parent class to access functions and settings
        self._parentclass = parentclass
        self.read_queue = queue.Queue()

    def handle_timer(self, state_change):
        """ Threaded method that can be called by a signal from outside to start the timer.

        @param bool state: (True) starts timer, (False) stops it.
        """
        if state_change:
            self.timer = QtCore.QTimer()
            # every _readout_timing (ms) read out the output from iScan
            self.timer.timeout.connect(self._listen)
            self.timer.start(self._parentclass._readout_timing)
        else:
            if hasattr(self, 'timer'):
                self.timer.stop()


    def _listen(self):
        """ The threaded method querying the message from the iscan.
        """

        # update as long as the state is busy
        if self._parentclass.module_state() == 'locked':
            try:
                # get the current output from the device
                line=self._parentclass._my_instrument.read()
                try:
                    self.read_queue.put_nowait(line)
                    with self.read_queue.mutex:
                        self.msg_list = list(self.read_queue.queue)
                    self.iscan_msg_update.emit(self.msg_list)
                except queue.Full:
                    # Buffer full: discard the oldest and insert the newes
                    try:
                        _ = self.read_queue.get_nowait() # remove the old item
                        self.read_queue.put_nowait(line)
                        with self.read_queue.mutex:
                            self.msg_list = list(self.read_queue.queue)
                        self.iscan_msg_update.emit(self.msg_list)
                    except queue.Empty:
                        pass # Should not happen
            except visa.errors.VisaIOError:
                # No data available at the moment, just wait
                pass
            

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

    # signals
    sig_handle_timer = QtCore.Signal(bool)

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)

        #locking for thread safety
        self.threadlock = Mutex()

        self._msg_list = []

    def on_activate(self):
        self.write_termination='\r\n'
        self.read_termination='\r\n'
        self.rm = visa.ResourceManager()
        self._my_instrument = self.rm.open_resource(resource_name = self._resurce_name[0], baud_rate=57600, write_termination=self.write_termination, read_termination=self.read_termination)

        self._readout_timing = 100


        # create an indepentent thread for the hardware communication
        self.hardware_thread = QtCore.QThread()

        # create an object for the hardware communication and let it live on the new thread
        self._hardware_pull = HardwarePull(self)
        self._hardware_pull.moveToThread(self.hardware_thread)

        # connect the signals in and out of the threaded object
        self.sig_handle_timer.connect(self._hardware_pull.handle_timer)
        self._hardware_pull.iscan_msg_update.connect(self.handle_msg, QtCore.Qt.DirectConnection)

        # start the event loop for the hardware
        self.hardware_thread.start()        

    def on_deactivate(self):

        if self.module_state() != 'idle' and self.module_state() != 'deactivated':
            self.stop_acquisition()
        self.hardware_thread.quit()
        self.sig_handle_timer.disconnect()
        self._hardware_pull.iscan_msg_update.disconnect()
        self._my_instrument.close()
        return 0


    def handle_msg(self, msg_list):
        """ Function to save the message list, when it comes in with a signal.
        """
        self._msg_list = msg_list

    def send_command(self,command):
        return self._my_instrument.write(command)
    
    def set_variable(self, var_name, value):
        command = f"{var_name}={value}"
        return self.send_command(command)

    def start_acquisition(self):
        """ Method to start acquiring the message from iscan system

        @return int: error code (0:OK, -1:error)

        Also the actual thread is started.
        """

        # first check its status
        if self.module_state() == 'locked':
            self.log.error('iscan acquisition thread busy')
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
            self.log.warning('Acquisition  was already stopped, stopping it '
                    'anyway!')
        else:
            # stop the measurement thread
            self.sig_handle_timer.emit(False)
            # set status to idle again
            self.module_state.unlock()
        return 0