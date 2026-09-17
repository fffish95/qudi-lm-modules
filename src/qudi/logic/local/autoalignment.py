# NOTE: This module was written or modified by fffish
# (https://github.com/fffish95/qudi-lm-modules) and remains subject to the GNU
# license terms stated below (or, if none are stated in this file, to the GNU
# General Public License under which Qudi is distributed).

# Modified from (c) 2019, Robert Kauffman
import numpy as np

from qudi.core.connector import Connector
from qudi.core.configoption import ConfigOption
from qudi.util import tools
from qudi.core.module import LogicBase
from PySide2 import QtCore
import time


class AutoAlignmentStopRequested(Exception):
    """ Internal control-flow exception used to unwind a running optimize()/
    correct_hysteresis() call as soon as stop_all() has been invoked.
    """
    pass


class autoalignmentLogic(LogicBase):

    """
    autoalignmentlogic:
        module.Class: 'local.autoalignment.autoalignmentLogic'
        connect:
            pmc: 'nf8752'
            # thorlabspm1: 'thorlabspm'
            # timetaggerlogic: 'timetaggerlogic'
        options:
            timetagger_read_channel: 'APDset2'
    """
    # connector
    pmc = Connector(interface='NF8752Logic')
    thorlabspm1 = Connector(interface = "ThorlabsPM", optional=True)
    _time_series_logic_con = Connector(interface='TimeSeriesReaderLogic', optional = True)
    _timetagger_read_channel = ConfigOption('timetagger_read_channel', missing='info')

    # signals for GUI notification
    sigOptimizeFinished = QtCore.Signal()
    sigHysteresisFinished = QtCore.Signal()
    sigStopped = QtCore.Signal()
    sigReadSourceChanged = QtCore.Signal(str)
    sigReadChannelChanged = QtCore.Signal(str)

    def on_activate(self):
        """ Initialisation performed during activation of the module.
        """
        self._pmc = self.pmc()
        self._tlpm = self.thorlabspm1()
        self._time_series_logic = self._time_series_logic_con()
        if self._tlpm is not None:
            self._tlpm.connect()
        # Measurement samples used for final confirmation. Broad optimization uses fewer.
        self._vel = 100 # picomotor moving velocity
        self._acc = 500 # picomotor acceleration
        self.num_samples = 10
        self.exploration_samples = 3
        self._active_num_samples = self.num_samples
        self.motor_alphabet = ['x1','y1','x2','y2','z']
        self.full_simplex_range = dict(zip(self.motor_alphabet, list([300]*4+[900])))
        self.motor_list = ['x1','y1','x2','y2','z'] # optional ['x1','y1','x2','y2']
        self.correct_hysteresis_steps = {'x1':5,'y1':5,'x2':5,'y2':5,'z':15}
        self.channel_codes = {'x1':0,'y1':1,'x2':2,'y2':3,'z':4}
        #The length of optimization time in seconds. 
        self.timeout = 100
        self._current_position = [0,0,0,0,0]
        self._stop_requested = False
        # Default read source: prefer the power meter if connected, otherwise fall back
        # to the time series (timetagger) reader.
        if self._tlpm is not None:
            self._read_source = 'powermeter'
        elif self._time_series_logic is not None:
            self._read_source = 'timetagger'
        else:
            self._read_source = None
            self.log.error(
                'Neither a power meter nor a time series logic is connected. '
                'read_output() will not work until one of them is connected.'
            )

    def on_deactivate(self):
        """ Deinitialisation performed during deactivation of the module.
        """
        if self._tlpm is not None:
            self._tlpm.disconnect()

    def read_output(self, num_samples=None):
        """ Read the output of powermeter or timetagger counter, depending on the
        currently selected read source (see set_read_source()).
        """
        sample_count = self._active_num_samples if num_samples is None else num_samples
        if self._read_source == 'powermeter':
            if self._tlpm is None:
                self.log.error('Power meter is not connected; cannot read output.')
                return np.nan
            # power measurement
            power_measurements = []
            count = 0 
            while count < sample_count:
                self._check_stop()
                power_measurements.append(self._tlpm.get_power())
                count+=1
                tools.delay(500)
            power_measurements = np.array(power_measurements)
            value = np.mean(power_measurements)
        elif self._read_source == 'timetagger':
            if self._time_series_logic is None:
                self.log.error('Time series logic is not connected; cannot read output.')
                return np.nan
            power_measurements = []
            count = 0 
            while count < sample_count:
                self._check_stop()
                data_time, data = self._time_series_logic.trace_data
                power_measurements.append(data[self._timetagger_read_channel][-1])
                count+=1
                tools.delay(1100)
            power_measurements = np.array(power_measurements)
            value = np.mean(power_measurements)
        else:
            self.log.error(
                "No valid read source is set. Use set_read_source('powermeter' or "
                "'timetagger') first."
            )
            return np.nan

        return value

    def _check_stop(self):
        """ Raise AutoAlignmentStopRequested if stop_all() has been called.

        Called from within the long-running loops of read_output(),
        randomize_initial_simplex(), downhill_simplex() and correct_hysteresis(), so
        that an emergency stop takes effect promptly instead of waiting for the whole
        optimize()/correct_hysteresis() call to complete on its own.
        """
        if self._stop_requested:
            raise AutoAlignmentStopRequested()

    def get_available_read_sources(self):
        """ Return the read sources ('powermeter'/'timetagger') that are currently
        usable, based on which optional connectors are actually connected.
        """
        sources = []
        if self._tlpm is not None:
            sources.append('powermeter')
        if self._time_series_logic is not None:
            sources.append('timetagger')
        return sources

    def get_read_source(self):
        """ Return the currently selected read source. """
        return self._read_source

    def set_read_source(self, source):
        """ Select whether read_output() reads from the power meter or the timetagger
        (time series logic).

        @param str source: 'powermeter' or 'timetagger'
        """
        source = source.lower() if isinstance(source, str) else source
        if source == 'powermeter' and self._tlpm is None:
            self.log.error('No power meter connected; cannot switch to powermeter readout.')
            return
        if source == 'timetagger' and self._time_series_logic is None:
            self.log.error(
                'No time series logic connected; cannot switch to timetagger readout.'
            )
            return
        if source not in ('powermeter', 'timetagger'):
            self.log.error("read source must be 'powermeter' or 'timetagger'.")
            return
        self._read_source = source
        self.sigReadSourceChanged.emit(self._read_source)

    def get_available_timetagger_channels(self):
        """ Return the timetagger channels currently active in the connected time
        series logic, i.e. the channels that read_output() can actually read from.
        """
        if self._time_series_logic is None:
            return tuple()
        return self._time_series_logic.active_channel_names

    def get_timetagger_read_channel(self):
        """ Return the timetagger channel currently used by read_output() when
        read_source is 'timetagger'.
        """
        return self._timetagger_read_channel

    def set_timetagger_read_channel(self, channel):
        """ Change which timetagger channel is used by read_output() when
        read_source is 'timetagger'.
        """
        available = self.get_available_timetagger_channels()
        if available and channel not in available:
            self.log.warning(
                f'Channel {channel} is not currently an active time series channel '
                f'(available: {available}). Setting it anyway.'
            )
        self._timetagger_read_channel = channel
        self.sigReadChannelChanged.emit(channel)

    def stop_all(self):
        """ Emergency stop: immediately halt the picomotor controller and request
        that any running optimize()/correct_hysteresis() call abort as soon as
        possible.

        This method must be invoked directly (not via a queued Qt signal) so it
        takes effect immediately even while the logic module's own thread is stuck
        inside a long-running optimize()/correct_hysteresis() call.
        """
        self._stop_requested = True
        try:
            self._pmc.halt()
        except Exception:
            self.log.exception('Error while trying to halt the picomotor controller.')
        self.log.warning('Emergency stop requested: aborting autoalignment and halting motors.')
        self.sigStopped.emit()

    def start_optimize(self, range_size):
        """ Public entry point for the GUI. Guards against re-entrancy, resets the
        stop flag, and emits sigOptimizeFinished when done (successfully or not).
        """
        if self.module_state() == 'locked':
            self.log.warning('Autoalignment is already busy; ignoring new optimize request.')
            return
        self.module_state.lock()
        self._stop_requested = False
        try:
            self.optimize(range_size)
        except AutoAlignmentStopRequested:
            self.log.info('Optimization stopped by user request.')
        except ValueError:
            self.log.exception('Invalid range_size for optimize().')
        finally:
            self._active_num_samples = self.num_samples
            self.module_state.unlock()
            self.sigOptimizeFinished.emit()

    def start_correct_hysteresis(self):
        """ Public entry point for the GUI. Guards against re-entrancy, resets the
        stop flag, and emits sigHysteresisFinished when done (successfully or not).
        """
        if self.module_state() == 'locked':
            self.log.warning(
                'Autoalignment is already busy; ignoring new correct hysteresis request.'
            )
            return
        self.module_state.lock()
        self._stop_requested = False
        try:
            self.correct_hysteresis()
        except AutoAlignmentStopRequested:
            self.log.info('Hysteresis correction stopped by user request.')
        finally:
            self.module_state.unlock()
            self.sigHysteresisFinished.emit()

    def move_motors_abs(self, position):
        """
        Move the motors to the absolute position, return the corresponding read out.
        """
        self.motor_number = len(self.motor_list)
        if len(position) != self.motor_number:
            self.log.error('position dimension doesnt match motor list dimension.')
            return
        position = np.asarray(position, dtype=float)
        limits = np.asarray([
            self.full_simplex_range[motor] / 2
            for motor in self.motor_list
        ])
        bounded_position = np.clip(position, -limits, limits)
        if not np.array_equal(position, bounded_position):
            self.log.warning(
                f'Position {position} exceeds motor limits; '
                f'clipping to {bounded_position}.'
            )
        position = bounded_position
        # if 'z' in motor_list
        if len(position) > 4:
            # move z axis
            steps_z = position[self.channel_codes['z']] - self._current_position[self.channel_codes['z']]
            if steps_z < 0:
                steps_z = steps_z *1.20 # calibrate the backlash
            self._pmc.move_rel(steps=steps_z, axis= 'z',vel=self._vel, acc=self._acc)

        # move 'x1' and 'x2'
        steps_x1 = position[self.channel_codes['x1']] - self._current_position[self.channel_codes['x1']]
        if steps_x1 < 0:
            steps_x1 = steps_x1 *1.3 # calibrate the backlash
        self._pmc.move_rel(steps=steps_x1, axis= 'x1',vel=self._vel, acc=self._acc)

        steps_x2 = position[self.channel_codes['x2']] - self._current_position[self.channel_codes['x2']]
        if steps_x2 < 0:
            steps_x2 = steps_x2 *1.19 # calibrate the backlash
        self._pmc.move_rel(steps=steps_x2, axis= 'x2',vel=self._vel, acc=self._acc)


        # move 'y1' and 'y2'
        steps_y1 = position[self.channel_codes['y1']] - self._current_position[self.channel_codes['y1']]
        if steps_y1 < 0:
            steps_y1 = steps_y1 *1.34 # calibrate the backlash
        self._pmc.move_rel(steps=steps_y1, axis= 'y1',vel=self._vel, acc=self._acc)

        steps_y2 = position[self.channel_codes['y2']] - self._current_position[self.channel_codes['y2']]
        if steps_y2 < 0:
            steps_y2 = steps_y2 *1.23 # calibrate the backlash
        self._pmc.move_rel(steps=steps_y2, axis= 'y2',vel=self._vel, acc=self._acc)

        self._current_position = list(position)
        output = self.read_output()
        return output
    
    def define_home(self):
        self.motor_number = len(self.motor_list)
        self._current_position = list([0]*self.motor_number)

    def randomize_initial_simplex(self,simplex_range):
        """
        Set current position to 0.
        pick motor_number +1 positions for initial the simplex, the randomized range could be defined individually for different motors.
        """
        # set current postion to 0
        self.define_home()

        self.motor_number = len(self.motor_list)
        if self.motor_number <4:
            self.log.error('Need at least 2 axises for optimization.')
            return
        motor_position = [0]*self.motor_number
        output = self.read_output()
        simplex = []
        output_simplex = []
        simplex.append(motor_position)
        output_simplex.append(output)
        # we need to measure motor_number + 1 positions

        for i in range(self.motor_number):
            self._check_stop()
            motor_position = []
            for motor in self.motor_list:
                position = np.random.randint(
                    low=int(-simplex_range[motor] / 2),
                    high=int(simplex_range[motor] / 2)
                )
                motor_position.append(position)
            output = self.move_motors_abs(motor_position)
            simplex.append(motor_position)
            output_simplex.append(output)

        #Orders simplex positions from least to greatest output.
        sorted_output_simplex, sorted_simplex = zip(*sorted(zip(output_simplex,simplex)))
        return list(sorted_simplex), list(sorted_output_simplex)
    
    def downhill_simplex(self, sorted_simplex, sorted_output_simplex):
        """
        optimize the simplex
        """
        # Solves for the centroid of the simplex excluding the worst position. Used in elements of downhill_simplex and optimize function.
        # Requires no inputs and uses whatever the current simplex is.
        centroid_position = np.asarray(sorted_simplex[1:]).mean(axis=0)
        #Solves for a position reflected from the worst position. Used in elements of downhill_simplex and optimize function.
        worst_position = np.asarray(sorted_simplex[0])
        self.log.info(f'worst_position = {worst_position}')
        self.log.info(f'centroid_position= {centroid_position}')
        reflection_position = centroid_position + 1*(centroid_position-worst_position)
        # move motors to the reflection position
        reflection_output = self.move_motors_abs(reflection_position)
        # if the reflection point is within the rest output_simplex range, accept the reflection.
        if sorted_output_simplex[1] < reflection_output <= sorted_output_simplex[-1]:
            sorted_simplex[0] = list(reflection_position)
            sorted_output_simplex[0] = reflection_output
        # if reflection was very good, try expanding further
        elif reflection_output > sorted_output_simplex[-1]:
            expansion_position = centroid_position + 2 * (reflection_position - centroid_position)
            expansion_output = self.move_motors_abs(expansion_position)
            # Keep whichever is better
            if reflection_output > expansion_output:
                sorted_simplex[0] = list(reflection_position)
                sorted_output_simplex[0] = reflection_output
            else:
                sorted_simplex[0] = list(expansion_position)
                sorted_output_simplex[0] = expansion_output
        # if reflection is not so good but better than the worst, try outside contraction
        elif sorted_output_simplex[0] < reflection_output <= sorted_output_simplex[1]:
            contraction_position = centroid_position + 0.5 * (reflection_position - centroid_position)
            contraction_output = self.move_motors_abs(contraction_position)
            # if contraction output is better than the reflection output, keep it. Otherwise shrink step: all new simplex positions shrunk toward the current best position
            if contraction_output > reflection_output:
                sorted_simplex[0] = list(contraction_position)
                sorted_output_simplex[0] = contraction_output
            else:
                for i in range(self.motor_number):
                    self._check_stop()
                    sorted_simplex[i] = list(np.asarray(sorted_simplex[-1]) + 0.5 * (np.asarray(sorted_simplex[i]) - np.asarray(sorted_simplex[-1])))
                    sorted_output_simplex[i] = self.move_motors_abs(sorted_simplex[i])
        # if the reflection is worse than the worst, try inside contraction
        else:
            contraction_position = centroid_position + 0.5 * (worst_position - centroid_position)
            contraction_output = self.move_motors_abs(contraction_position)
            # if contraction output is better than the worst output, keep it. Otherwise shrink step: all new simplex positions shrunk toward the current best position
            if contraction_output > sorted_output_simplex[0]:
                sorted_simplex[0] = list(contraction_position)
                sorted_output_simplex[0] = contraction_output
            else:
                for i in range(self.motor_number):
                    self._check_stop()
                    sorted_simplex[i] = list(np.asarray(sorted_simplex[-1]) + 0.5 * (np.asarray(sorted_simplex[i]) - np.asarray(sorted_simplex[-1])))
                    sorted_output_simplex[i] = self.move_motors_abs(sorted_simplex[i])
        final_output_simplex, final_simplex = zip(*sorted(zip(sorted_output_simplex,sorted_simplex)))
        return list(final_simplex), list(final_output_simplex)
    
    def correct_hysteresis(self):
        """
        Because of the pizeo hysteresis, the picomotor could not remeber previous absolute positions. 
        This function corrects the hysteresis of the best position by determining which direction each motor needs to move to get back to maximum.
        """
        # correct hysteresis 'z'
        old_position = self._current_position.copy()
        if 'z' in self.motor_list:
            self.correct_hysteresis_oneaxis('z')

        # correct hysteresis 'x1' and 'x2'
        prev_output = self.read_output()
        new_position = self._current_position.copy()
        new_position[self.channel_codes['x1']] = self._current_position[self.channel_codes['x1']] + self.correct_hysteresis_steps['x1']
        new_output= self.move_motors_abs(new_position)
        if new_output < prev_output:
            self.correct_hysteresis_steps['x1'] = -self.correct_hysteresis_steps['x1']
            new_position = self._current_position.copy()
            new_position[self.channel_codes['x1']] = self._current_position[self.channel_codes['x1']] + 2*self.correct_hysteresis_steps['x1']
            new_output= self.move_motors_abs(new_position)
        if new_output < prev_output:
            self.log.info("correct hysteresis for x1 failed. You may want to assign a smaller value for self.correct_hysteresis_steps['x1']")
            new_position[self.channel_codes['x1']] = self._current_position[self.channel_codes['x1']] - self.correct_hysteresis_steps['x1']
            self.move_motors_abs(new_position)
        else:
            prev_output = new_output
            new_position = self._current_position.copy()
            new_position[self.channel_codes['x2']] = self._current_position[self.channel_codes['x2']] + self.correct_hysteresis_steps['x2']
            new_output= self.move_motors_abs(new_position)
            if new_output < prev_output:
                self.correct_hysteresis_steps['x2'] = -self.correct_hysteresis_steps['x2']
                new_position = self._current_position.copy()
                new_position[self.channel_codes['x2']] = self._current_position[self.channel_codes['x2']] + 2*self.correct_hysteresis_steps['x2']
                new_output= self.move_motors_abs(new_position)
            if new_output < prev_output:
                self.log.info("correct hysteresis for x2 failed. You may want to assign a smaller value for self.correct_hysteresis_steps['x2']")
                new_position[self.channel_codes['x2']] = self._current_position[self.channel_codes['x2']] - self.correct_hysteresis_steps['x2']
                self.move_motors_abs(new_position)
            else:
                while new_output > prev_output:
                    self._check_stop()
                    prev_output = new_output
                    new_position = self._current_position.copy()
                    new_position[self.channel_codes['x1']] = self._current_position[self.channel_codes['x1']] + self.correct_hysteresis_steps['x1']
                    new_position[self.channel_codes['x2']] = self._current_position[self.channel_codes['x2']] + self.correct_hysteresis_steps['x2']
                    new_output= self.move_motors_abs(new_position)
                new_position[self.channel_codes['x1']] = self._current_position[self.channel_codes['x1']] - self.correct_hysteresis_steps['x1']
                new_position[self.channel_codes['x2']] = self._current_position[self.channel_codes['x2']] - self.correct_hysteresis_steps['x2']
                new_output= self.move_motors_abs(new_position)

        # correct hysteresis 'y1' and 'y2'
        prev_output = new_output
        new_position = self._current_position.copy()
        new_position[self.channel_codes['y1']] = self._current_position[self.channel_codes['y1']] + self.correct_hysteresis_steps['y1']
        new_output= self.move_motors_abs(new_position)
        if new_output < prev_output:
            self.correct_hysteresis_steps['y1'] = -self.correct_hysteresis_steps['y1']
            new_position = self._current_position.copy()
            new_position[self.channel_codes['y1']] = self._current_position[self.channel_codes['y1']] + 2*self.correct_hysteresis_steps['y1']
            new_output= self.move_motors_abs(new_position)
        if new_output < prev_output:
            self.log.info("correct hysteresis for y1 failed. You may want to assign a smaller value for self.correct_hysteresis_steps['y1']")
            new_position[self.channel_codes['y1']] = self._current_position[self.channel_codes['y1']] - self.correct_hysteresis_steps['y1']
            self.move_motors_abs(new_position)
        else:
            prev_output = new_output
            new_position = self._current_position.copy()
            new_position[self.channel_codes['y2']] = self._current_position[self.channel_codes['y2']] + self.correct_hysteresis_steps['y2']
            new_output= self.move_motors_abs(new_position)
            if new_output < prev_output:
                self.correct_hysteresis_steps['y2'] = -self.correct_hysteresis_steps['y2']
                new_position = self._current_position.copy()
                new_position[self.channel_codes['y2']] = self._current_position[self.channel_codes['y2']] + 2*self.correct_hysteresis_steps['y2']
                new_output= self.move_motors_abs(new_position)
            if new_output < prev_output:
                self.log.info("correct hysteresis for y2 failed. You may want to assign a smaller value for self.correct_hysteresis_steps['y2']")
                new_position[self.channel_codes['y2']] = self._current_position[self.channel_codes['y2']] - self.correct_hysteresis_steps['y2']
                self.move_motors_abs(new_position)
            else:
                while new_output > prev_output:
                    self._check_stop()
                    prev_output = new_output
                    new_position = self._current_position.copy()
                    new_position[self.channel_codes['y1']] = self._current_position[self.channel_codes['y1']] + self.correct_hysteresis_steps['y1']
                    new_position[self.channel_codes['y2']] = self._current_position[self.channel_codes['y2']] + self.correct_hysteresis_steps['y2']
                    new_output= self.move_motors_abs(new_position)
                new_position[self.channel_codes['y1']] = self._current_position[self.channel_codes['y1']] - self.correct_hysteresis_steps['y1']
                new_position[self.channel_codes['y2']] = self._current_position[self.channel_codes['y2']] - self.correct_hysteresis_steps['y2']
                new_output= self.move_motors_abs(new_position)
        self.log.info(f'correct_hysteresis: new_position = {new_position}, old_position = {old_position}')

    def correct_hysteresis_oneaxis(self, motor):
        old_position = self._current_position.copy()
        
        prev_output = self.read_output()
        new_position = self._current_position.copy()
        new_position[self.channel_codes[motor]] = self._current_position[self.channel_codes[motor]] + self.correct_hysteresis_steps[motor]
        new_output= self.move_motors_abs(new_position)
        if new_output < prev_output:
            self.correct_hysteresis_steps[motor] = -self.correct_hysteresis_steps[motor]
            new_position = self._current_position.copy()
            new_position[self.channel_codes[motor]] = self._current_position[self.channel_codes[motor]] + 2*self.correct_hysteresis_steps[motor]
            new_output= self.move_motors_abs(new_position)
        if new_output < prev_output:
            self.log.info(f"correct hysteresis for {motor} failed. You may want to assign a smaller value for self.correct_hysteresis_steps[{motor}]")
        while new_output > prev_output:
            self._check_stop()
            prev_output = new_output
            new_position = self._current_position.copy()
            new_position[self.channel_codes[motor]] = self._current_position[self.channel_codes[motor]] + self.correct_hysteresis_steps[motor]
            new_output= self.move_motors_abs(new_position)
        new_position[self.channel_codes[motor]] = self._current_position[self.channel_codes[motor]] - self.correct_hysteresis_steps[motor]
        self.move_motors_abs(new_position)
        self.log.info(f'correct_hysteresis_oneaxis: new_position = {new_position}, old_position = {old_position}')

    def _simplex_range_for_size(self, range_size):
        """Return the configured simplex range for a named search size."""
        range_scales = {
            'small': 1 / 20,
            'medium': 1 / 5,
            'large': 1,
        }
        try:
            scale = range_scales[range_size.lower()]
        except (AttributeError, KeyError) as error:
            raise ValueError(
                "range_size must be 'small', 'medium', or 'large'."
            ) from error
        return {motor: value * scale for motor, value in self.full_simplex_range.items()}

    def optimize(self, range_size):
        """
        Optimize the motor positions using a named simplex search range.

        ``range_size`` must be ``small``, ``medium``, or ``large``.
        """
        hysteresis_counter = 0
        self._active_num_samples = self.exploration_samples
        simplex_range = self._simplex_range_for_size(range_size)
        final_output = self.read_output()
        sorted_simplex, sorted_output_simplex = self.randomize_initial_simplex(simplex_range)
        deadline = time.time() + self.timeout
        while deadline > time.time():
            self._check_stop()
            prev_best_position = sorted_simplex[-1]
            final_simplex, final_output_simplex = self.downhill_simplex(sorted_simplex, sorted_output_simplex)
            sorted_simplex = final_simplex
            sorted_output_simplex = final_output_simplex
            final_position = final_simplex[-1]
            final_output = final_output_simplex[-1]
            self.log.info(f'final_simple = {final_simplex}')
            self.log.info(f'final_output_simplex = {final_output_simplex}')
            self.log.info(f'Best position = {final_position}')
            self.log.info(f'Best output = {final_output}')
            if final_position == prev_best_position:
                hysteresis_counter = hysteresis_counter + 1
                if hysteresis_counter > 2:
                    self.move_motors_abs(final_position)
                    self.log.info('Correcting hysteresis...')
                    self._active_num_samples = self.num_samples
                    self.correct_hysteresis()
                    self.log.info('Local Max Achieved.')
                    final_output = self.read_output()
                    self.log.info(final_output)
                    hysteresis_counter  = 0
                    self._active_num_samples = self.exploration_samples
                    sorted_simplex, sorted_output_simplex = self.randomize_initial_simplex(simplex_range)
            else:
                hysteresis_counter = 0

        self._active_num_samples = self.num_samples
        final_position = sorted_simplex[-1]
        final_output = sorted_output_simplex[-1]
        self.log.info(f'final_simple = {sorted_simplex}')
        self.log.info(f'final_output_simplex = {sorted_output_simplex}')
        self.log.info(f'Best position = {final_position}')
        self.log.info(f'Best output = {final_output}')
        self.move_motors_abs(final_position)
        self.log.info('Correcting hysteresis...')
        self.correct_hysteresis()
        self.log.info('Local Max Achieved.')
        final_output = self.read_output()
        self.log.info(f'Final power ={final_output}')