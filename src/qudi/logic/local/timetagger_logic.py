from collections import OrderedDict
import numpy as np
import matplotlib.pyplot as plt
from qudi.core.connector import Connector
from qudi.core.statusvariable import StatusVar
from qudi.core.module import LogicBase
from qudi.util.mutex import Mutex
from PySide2 import QtCore
import datetime
import os
import copy

class TimeTaggerHistoryEntry(QtCore.QObject):
    """ This class contains all relevant parameters of for timetagger.
        It provides methods to extract, restore and serialize this data.
    """
    def __init__(self, timetagger):
        """ Make timetagger data setting with default values. """
        super().__init__()
        # Set parameters for Autocorrelation
        self.autocorr_params = {
            'ch1-ch2':{'channel_stop':2, 'channel_start':1, 'bins_width':1000, 'number_of_bins':1200},
            'ch2-ch1':{'channel_stop':1, 'channel_start':2, 'bins_width':1000, 'number_of_bins':1200}
        }
        # Set parameters for Histogram
        self.histogram_params = {
            'ch1-ch8':{'channel':1, 'trigger_channel':8, 'bins_width':1000, 'number_of_bins':1200},
            'ch2-ch8':{'channel':2, 'trigger_channel':8, 'bins_width':1000, 'number_of_bins':1200}
        }
        # Set parameters for writeintofile
        self.writeintofile_params ={
            'sample_name':'Sample1', 'trigger':[1, 2], 'filtered': [8]
        }

        # Set plotting mode
        self.autocorr_accumulate = False
        self.histogram_accumulate = False

    def restore(self, timetagger):
        """ Write data back into timetagger logic and pull all the necessary strings"""
        timetagger._autocorr_params = copy.deepcopy(self.autocorr_params)
        timetagger._histogram_params = copy.deepcopy(self.histogram_params)
        timetagger._writeintofile_params = copy.deepcopy(self.writeintofile_params)
        timetagger._autocorr_accumulate = self.autocorr_accumulate
        timetagger._histogram_accumulate = self.histogram_accumulate
        timetagger.initialise_plots()
        try:
            timetagger.autocorr_y = np.copy(self.autocorr_y)
            timetagger.histogram_y = np.copy(self.histogram_y)
            timetagger.autocorr_x = np.copy(self.autocorr_x)
            timetagger.histogram_x = np.copy(self.histogram_x)

        except AttributeError:
            self.autocorr_y = np.copy(timetagger.autocorr_y)
            self.histogram_y = np.copy(timetagger.histogram_y)
            self.autocorr_x = np.copy(timetagger.autocorr_x)
            self.histogram_x = np.copy(timetagger.histogram_x)
    
    def snapshot(self, timetagger):
        """ Extract all necessary data from a timetagger logic and keep it for later use """
        self.autocorr_params = copy.deepcopy(timetagger._autocorr_params)
        self.histogram_params = copy.deepcopy(timetagger._histogram_params)
        self.writeintofile_params = copy.deepcopy(timetagger._writeintofile_params)
        self.autocorr_accumulate = timetagger._autocorr_accumulate
        self.histogram_accumulate = timetagger._histogram_accumulate

        self.autocorr_y = np.copy(timetagger.autocorr_y)
        self.histogram_y = np.copy(timetagger.histogram_y)
        self.autocorr_x = np.copy(timetagger.autocorr_x)
        self.histogram_x = np.copy(timetagger.histogram_x)

    def serialize(self):
        """ Give out a dictionary that can be saved via the usua means """
        serialized = dict()
        serialized['autocorr_params'] = copy.deepcopy(self.autocorr_params)
        serialized['histogram_params'] = copy.deepcopy(self.histogram_params)
        serialized['writeintofile_params'] = copy.deepcopy(self.writeintofile_params)
        serialized['autocorr_accumulate'] = self.autocorr_accumulate
        serialized['histogram_accumulate'] = self.histogram_accumulate

        serialized['autocorr_y'] = self.autocorr_y
        serialized['histogram_y'] = self.histogram_y
        serialized['autocorr_x'] = self.autocorr_x
        serialized['histogram_x'] = self.histogram_x
        return serialized

    def deserialize(self, serialized):
        """ Restore timetagger history object from a dict """
        if 'autocorr_params' in serialized:
            self.autocorr_params = serialized['autocorr_params']
        if 'histogram_params' in serialized:
            self.histogram_params = serialized['histogram_params']
        if 'writeintofile_params' in serialized:
            self.writeintofile_params = serialized['writeintofile_params']
        if 'autocorr_accumulate' in serialized:
            self.autocorr_accumulate = serialized['autocorr_accumulate']
        if 'histogram_accumulate' in serialized:
            self.histogram_accumulate = serialized['histogram_accumulate']

        if 'autocorr_y' in serialized:
            self.autocorr_y = serialized['autocorr_y']
        if 'histogram_y' in serialized:
            self.histogram_y = serialized['histogram_y']
        if 'autocorr_x' in serialized:
            self.autocorr_x = serialized['autocorr_x']
        if 'histogram_x' in serialized:
            self.histogram_x = serialized['histogram_x']

class TimetaggerPull(QtCore.QObject):
    """ Helper class for running the hardware communication in a separate thread. """

    # signal to deliver the plot matrix to the parent class
    sig_TimetaggerPull = QtCore.Signal(np.ndarray, np.ndarray, np.ndarray, np.ndarray)

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
            self.autocorr_tasks = list()
            for key, value in self._parentclass._autocorr_params.items():
                self.autocorr_tasks.append(self._parentclass._timetagger.correlation(**value))
            self.histogram_tasks = list()
            for key, value in self._parentclass._histogram_params.items():
                self.histogram_tasks.append(self._parentclass._timetagger.histogram(**value))

            self.autocorr_all_data = np.zeros((len(self._parentclass._autocorr_params), list(self._parentclass._autocorr_params.values())[0]['number_of_bins']))
            self.autocorr_x = self.autocorr_tasks[0].getIndex()/1e3


            self.histogram_all_data = np.zeros((len(self._parentclass._histogram_params), list(self._parentclass._histogram_params.values())[0]['number_of_bins']))
            self.histogram_x = self.histogram_tasks[0].getIndex()/1e3

            # every _refresh_time (ms) send out the signal
            self.timer.timeout.connect(self._measure_thread)
            self.timer.start(self._parentclass._refresh_time)
        else:
            if hasattr(self, 'timer'):
                self.timer.stop()
            if hasattr(self,'autocorr_tasks'):
                for i, task in enumerate(self.autocorr_tasks):
                    if task.isRunning():
                        task.stop()
                    task.clear()
            if hasattr(self,'histogram_tasks'):
                for i, task in enumerate(self.histogram_tasks):
                    if task.isRunning():
                        task.stop()
                    task.clear()

    def _measure_thread(self):

        # update as long as the state is busy
        if self._parentclass.module_state() == 'locked':
            for i, task in enumerate(self.autocorr_tasks):
                counts = np.nan_to_num(task.getData())
                data = np.reshape(counts,(1, list(self._parentclass._autocorr_params.values())[0]['number_of_bins']))
                self.autocorr_all_data[i] = data
            for i, task in enumerate(self.histogram_tasks):
                counts = np.nan_to_num(task.getData())
                data = np.reshape(counts,(1, list(self._parentclass._histogram_params.values())[0]['number_of_bins']))
                self.histogram_all_data[i] = data

            if not self._parentclass._autocorr_accumulate:
                for i, task in enumerate(self.autocorr_tasks):
                    task.clear()
            if not self._parentclass._histogram_accumulate:
                for i, task in enumerate(self.histogram_tasks):
                    task.clear()
            # send the data to the parent via a signal
            self.sig_TimetaggerPull.emit(self.autocorr_x, self.autocorr_all_data, self.histogram_x, self.histogram_all_data)

class TimetaggerWrite(QtCore.QObject):
    """ Helper class for writting into file in a separate thread. """

    sig_TimetaggerWrite = QtCore.Signal(float, float)
    def __init__(self, parentclass):
        super().__init__()

        # remember the reference to the parent class to access functions ad settings
        self._parentclass = parentclass

    def handle_timer(self, state_change):
        """ Threaded method that can be called by a signal from outside to writeintofile.
        @param bool state: (True) starts, (False) stops.
        """

        if state_change:
            timestamp = datetime.datetime.now()
            self.timer_counter = 0
            self.timer = QtCore.QTimer()
            filepath = self._parentclass._save_logic.get_path_for_module('timetagger')
            filelabel = timestamp.strftime('%Y%m%d-%H%M-%S' + '_' + self._parentclass._writeintofile_params['sample_name'])
            filename = os.path.join(filepath, filelabel)
            self.writeintofile_task = self._parentclass._timetagger.write_into_file(filename = filename, apdChans = self._parentclass._writeintofile_params['trigger'], filteredChans = self._parentclass._writeintofile_params['filtered'])
            # every _refresh_time (ms) send out the signal
            self.timer.timeout.connect(self._measure_thread)
            self.timer.start(self._parentclass._refresh_time)
        else:
            if hasattr(self, 'timer'):
                self.timer.stop()
            if hasattr(self,'writeintofile_task'):
                if self.writeintofile_task.isRunning():
                    self.writeintofile_task.stop()
                self.writeintofile_task.clear()

    def _measure_thread(self):

        # update as long as the task is running
        if self.writeintofile_task.isRunning():
            self.timer_counter += 1
            # get the recording time
            measure_time = round(self.timer_counter * self._parentclass._refresh_time /1000, 2)
            total_size = round(self.writeintofile_task.getTotalSize()/1073741824, 3)

            # send the data to the parent via a signal
            self.sig_TimetaggerWrite.emit(measure_time, total_size)

class TimeTaggerLogic(LogicBase):
    """ Logic module agreggating multiple hardware switches.
    """

    timetagger = Connector(interface='TT')
    savelogic = Connector(interface='SaveLogic')

    # status vars
    _refresh_time = StatusVar(default=50)
    _statusVariables = StatusVar(default=OrderedDict())
    max_history_length = StatusVar(default=10)
    
    # signals
    signal_plots_updated = QtCore.Signal()
    signal_writeintofile_updated = QtCore.Signal()
    signal_history_event = QtCore.Signal()
    signal_timetagger_pull_handle_timer = QtCore.Signal(bool)
    signal_timetagger_write_handle_timer = QtCore.Signal(bool)
    signal_save_started = QtCore.Signal()
    signal_save_ended = QtCore.Signal()

    def __init__(self, **kwargs):
        """ Create CwaveScannerLogic object with connectors.

          @param dict kwargs: optional parameters
        """
        super().__init__(**kwargs)

        # locking for thread safety
        self.threadlock = Mutex()

    def on_activate(self):
        """ Initialisation performed during activation of the module.
        """
        self._timetagger = self.timetagger()
        self._save_logic = self.savelogic()


        # restore history in StatusVariables
        self.load_history_config()        
        # Sets connections between signals and functions

        # create an indepentent thread for the TimetaggerPull
        self.timetaggerpull_thread = QtCore.QThread()
        self.timetaggerwrite_thread = QtCore.QThread()

        # initialize recording states
        self._recording_states = False

        # create an object for the TimetaggerPull and let it live on the new thread
        self._timetagger_pull = TimetaggerPull(self)
        self._timetagger_pull.moveToThread(self.timetaggerpull_thread)
        self._timetagger_write = TimetaggerWrite(self)
        self._timetagger_write.moveToThread(self.timetaggerwrite_thread)

        # connect the signals in and out of the threaded object
        self.signal_timetagger_pull_handle_timer.connect(self._timetagger_pull.handle_timer)
        self._timetagger_pull.sig_TimetaggerPull.connect(self.handle_timetaggerpull)
        self.signal_timetagger_write_handle_timer.connect(self._timetagger_write.handle_timer)
        self._timetagger_write.sig_TimetaggerWrite.connect(self.handle_timetaggerwrtie)

        # start the event loop for the hardware
        self.timetaggerpull_thread.start()
        self.timetaggerwrite_thread.start()

    def on_deactivate(self):
        if self.module_state() != 'idle' and self.module_state() != 'deactivated':
            self.stop_measurement()
        if self._recording_states == True:
            self.stop_recording()
        
        closing_state = TimeTaggerHistoryEntry(self)
        closing_state.snapshot(self)
        self.history.append(closing_state)
        histindex = 0
        for state in reversed(self.history):
            self._statusVariables['history_{0}'.format(histindex)] = state.serialize()
            histindex += 1

        self.timetaggerpull_thread.quit()
        self.timetaggerwrite_thread.quit()
        self.signal_timetagger_pull_handle_timer.disconnect()
        self._timetagger_pull.sig_TimetaggerPull.disconnect()
        self.signal_timetagger_write_handle_timer.disconnect()
        self._timetagger_write.sig_TimetaggerWrite.disconnect()
        return 0

    def save_history_config(self):
        state_config = TimeTaggerHistoryEntry(self)
        state_config.snapshot(self)
        self.history.append(state_config)
        histindex = 0
        for state in reversed(self.history):
            self._statusVariables['history_{0}'.format(histindex)] = state.serialize()
            histindex += 1

    def load_history_config(self):
        # restore here ...
        self.history = []
        for i in reversed(range(1, self.max_history_length)):
            try:
                new_history_item = TimeTaggerHistoryEntry(self)
                new_history_item.deserialize(
                    self._statusVariables['history_{0}'.format(i)])
                self.history.append(new_history_item)
            except KeyError:
                pass
            except:
                self.log.warning(
                        'Restoring history {0} failed.'.format(i))
        try:
            new_state = TimeTaggerHistoryEntry(self)
            new_state.deserialize(self._statusVariables['history_0'])
            new_state.restore(self)
        except:
            new_state = TimeTaggerHistoryEntry(self)
            new_state.restore(self)
        finally:
            self.history.append(new_state)

        self.history_index = len(self.history) - 1
        self.history[self.history_index].restore(self)
        self.signal_history_event.emit()

    def history_forward(self):
        """ Move forward in history.
        """
        if self.history_index < len(self.history) - 1:
            self.history_index += 1
            self.history[self.history_index].restore(self)
            self.signal_history_event.emit()

    def history_back(self):
        """ Move forward in history.
        """
        if self.history_index > 0:
            self.history_index -= 1
            self.history[self.history_index].restore(self)
            self.signal_history_event.emit()

    def handle_timetaggerpull(self, autocorr_x, autocorr_all_data, histogram_x, histogram_all_data):
        """ Function to save the plots, when it comes in with a signal
        """
        self.autocorr_x = autocorr_x
        self.autocorr_y = autocorr_all_data
        self.histogram_x = histogram_x
        self.histogram_y = histogram_all_data
        self.signal_plots_updated.emit()

    def handle_timetaggerwrtie(self, measure_time, total_size):
        self.mearsure_time = measure_time
        self.total_size = total_size
        self.signal_writeintofile_updated.emit()

    def start_measurement(self):
        """ Method to start measurement.

        @return int: error code (0:OK, -1:error)
        """

        # first check its status
        if self.module_state() == 'locked':
            self.log.error('TimetaggerPull busy')
            return -1

        self.module_state.lock()
        # start the measuring thread
        self.signal_timetagger_pull_handle_timer.emit(True)
        return 0
    
    def start_recording(self):

        if self._recording_states:
            self.log.error('TimetaggerWrite busy')
            return -1
        self._recording_states = True
        # start the recording thread
        self.signal_timetagger_write_handle_timer.emit(True)
        return 0

    def stop_measurement(self):
        if self.module_state() == 'idle':
            self.log.warning('TimetaggerPull was already stopped.')
        else:
            # stop the measurement thread
            self.signal_timetagger_pull_handle_timer.emit(False)
            # set status to idle again
            self.module_state.unlock()
            # add new history entry
            new_history = TimeTaggerHistoryEntry(self)
            new_history.snapshot(self)
            self.history.append(new_history)
            if len(self.history) > self.max_history_length:
                self.history.pop(0)
            self.history_index = len(self.history) - 1

    def stop_recording(self):
        if self._recording_states == False:
            self.log.warning('TimetaggerWrite was already stopped.')
        else:
            # stop the measurement thread
            self.signal_timetagger_write_handle_timer.emit(False)
            # set status to idle again
            self._recording_states = False

    def initialise_plots(self):
        self.autocorr_x = np.arange(0,1000,1)
        self.autocorr_y = np.zeros((1,1000))
        self.histogram_x = np.arange(0,1000,1)
        self.histogram_y = np.zeros((1,1000))
    def save_data(self):
        """ Save the Autocorr and Histogram data and writes it to a file.
        @return int: error code (0:OK, -1:error)
        """
        self.signal_save_started.emit()
        filepath = self._save_logic.get_path_for_module('timetagger')
        timestamp = datetime.datetime.now()
        parameters = OrderedDict()

        for i, key in enumerate(self._autocorr_params):
            parameters = self._autocorr_params[key]
            data = OrderedDict()
            data['autocorr_x'] = self.autocorr_x
            data[list(self._autocorr_params.keys())[i]] = self.autocorr_y[i]
            fig = self._draw_figure(self.autocorr_x, self.autocorr_y[i])
            filelabel = 'autocorrelation_{0}'.format(i)
            self._save_logic.save_data(data=data,
                                filepath=filepath,
                                parameters=parameters,
                                filelabel=filelabel,
                                plotfig=fig,
                                delimiter='\t',
                                timestamp=timestamp)
        
        for i, key in enumerate(self._histogram_params):
            parameters = self._histogram_params[key]
            data = OrderedDict()
            data['histogram_x'] = self.histogram_x
            data[list(self._histogram_params.keys())[i]] = self.histogram_y[i]
            fig = self._draw_figure(self.histogram_x, self.histogram_y[i])
            filelabel = 'histogram_{0}'.format(i)
            self._save_logic.save_data(data=data,
                                filepath=filepath,
                                parameters=parameters,
                                filelabel=filelabel,
                                plotfig=fig,
                                delimiter='\t',
                                timestamp=timestamp)
        self.signal_save_ended.emit()


    def _draw_figure(self, x, y):
        """ Draw figure to save with data file.

        @param: nparray data: a numpy array containing counts vs time for all detectors

        @return: fig fig: a matplotlib figure object to be saved to file.
        """
        # Use qudi style
        plt.style.use(self._save_logic.mpl_qd_style)

        fig, ax = plt.subplots()
        ax.plot(x,
                y,
                linestyle=':',
                linewidth=0.5)
        ax.set_xlabel('Time (μs)')
        ax.set_ylabel('Signal (a.u.)')
        return fig