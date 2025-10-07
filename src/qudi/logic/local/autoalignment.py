# Modified from (c) 2019, Robert Kauffman
import numpy as np

from qudi.core.connector import Connector
from qudi.core.statusvariable import StatusVar
from qudi.core.configoption import ConfigOption
from qudi.util import tools
from qudi.core.module import LogicBase
from qudi.util.mutex import Mutex
import time


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

    def on_activate(self):
        """ Initialisation performed during activation of the module.
        """
        self._pmc = self.pmc()
        self._tlpm = self.thorlabspm1()
        self._time_series_logic = self._time_series_logic_con()
        if self._tlpm is not None:
            self._tlpm.connect()
        # Number of samples wanted. The read time per sample is 1 second.
        self._vel = 100 # picomotor moving velocity
        self._acc = 500 # picomotor acceleration
        self.num_samples = 10
        self.motor_alphabet = ['x1','y1','x2','y2','z']
        self.full_simplex_range = dict(zip(self.motor_alphabet, list([300]*4+[900])))
        self.explore_step = dict(zip(self.motor_alphabet, list([20]*4+[60])))
        self.motor_list = ['x1','y1','x2','y2','z'] # optional ['x1','y1','x2','y2']
        self.correct_hysteresis_steps = {'x1':5,'y1':5,'x2':5,'y2':5,'z':15}
        self.channel_codes = {'x1':0,'y1':1,'x2':2,'y2':3,'z':4}
        #The length of optimization time in seconds. 
        self.timeout = 1200
        self._current_position = [0,0,0,0,0]

    def on_deactivate(self):
        """ Deinitialisation performed during deactivation of the module.
        """
        if self._tlpm is not None:
            self._tlpm.disconnect()

    def read_output(self):
        """ Read the output of powermeter or timetagger counter.
        """
        if self._tlpm is not None:
            # power measurement
            power_measurements = []
            count = 0 
            while count < self.num_samples:
                power_measurements.append(self._tlpm.get_power())
                count+=1
                tools.delay(500)
            power_measurements = np.array(power_measurements)
            value = np.mean(power_measurements)
        else:
            power_measurements = []
            count = 0 
            while count < self.num_samples:
                data_time, data = self._time_series_logic.trace_data
                power_measurements.append(data[self._timetagger_read_channel][-1])
                count+=1
                tools.delay(1100)
            power_measurements = np.array(power_measurements)
            value = np.mean(power_measurements)

        return value

    def move_motors_abs(self, position):
        """
        Move the motors to the absolute position, return the corresponding read out.
        """
        self.motor_number = len(self.motor_list)
        if len(position) != self.motor_number:
            self.log.error('position dimension doesnt match motor list dimension.')
            return
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
            motor_position = []
            for motor in self.motor_list:
                position = np.random.randint(low=-(simplex_range[motor]/2), high=(simplex_range[motor]/2))
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
        print(f'worst_position = {worst_position}')
        print(f'centroid_position= {centroid_position}')
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
                    prev_output = new_output
                    new_position = self._current_position.copy()
                    new_position[self.channel_codes['y1']] = self._current_position[self.channel_codes['y1']] + self.correct_hysteresis_steps['y1']
                    new_position[self.channel_codes['y2']] = self._current_position[self.channel_codes['y2']] + self.correct_hysteresis_steps['y2']
                    new_output= self.move_motors_abs(new_position)
                new_position[self.channel_codes['y1']] = self._current_position[self.channel_codes['y1']] - self.correct_hysteresis_steps['y1']
                new_position[self.channel_codes['y2']] = self._current_position[self.channel_codes['y2']] - self.correct_hysteresis_steps['y2']
                new_output= self.move_motors_abs(new_position)
        print(f'correct_hysteresis: new_position = {new_position}, old_position = {old_position}')

    def correct_hysteresis_oneaxis(self, motor):
        old_position = self._current_position.copy()
        
        prev_output = self.read_output()
        new_position = self._current_position.copy()
        new_position[self.channel_codes[motor]] = self._current_position[self.channel_codes[motor]] + self.correct_hysteresis_steps['z']
        new_output= self.move_motors_abs(new_position)
        if new_output < prev_output:
            self.correct_hysteresis_steps[motor] = -self.correct_hysteresis_steps[motor]
            new_position = self._current_position.copy()
            new_position[self.channel_codes[motor]] = self._current_position[self.channel_codes[motor]] + 2*self.correct_hysteresis_steps[motor]
            new_output= self.move_motors_abs(new_position)
        if new_output < prev_output:
            self.log.info(f"correct hysteresis for {motor} failed. You may want to assign a smaller value for self.correct_hysteresis_steps[{motor}]")
        while new_output > prev_output:
            prev_output = new_output
            new_position = self._current_position.copy()
            new_position[self.channel_codes[motor]] = self._current_position[self.channel_codes[motor]] + self.correct_hysteresis_steps[motor]
            new_output= self.move_motors_abs(new_position)
        new_position[self.channel_codes[motor]] = self._current_position[self.channel_codes[motor]] - self.correct_hysteresis_steps[motor]
        self.move_motors_abs(new_position)
        print(f'correct_hysteresis_oneaxis: new_position = {new_position}, old_position = {old_position}')

    def explore_motor(self, motor):
        """
        Explores one motor in one direction 2000 steps by moving this far and working back to the original position 100 steps at a time. Used in optimize function.
        Requires the motor to be explored and the direction of exploration (1 is forward and -1 is backward).
        """
        explore_step = self.explore_step[motor]
        explore_counter = 30
        explore_range = int(explore_counter/2)*explore_step
        best_count = 0
        target_output = self.read_output()
        new_position = self._current_position.copy()
        new_position[self.channel_codes[motor]] = self._current_position[self.channel_codes[motor]] + explore_range
        self.move_motors_abs(new_position)
        while explore_counter >= 0:
            explore_counter = explore_counter - 1
            new_position = self._current_position.copy()
            new_position[self.channel_codes[motor]] = self._current_position[self.channel_codes[motor]] -explore_step
            explore_output = self.move_motors_abs(new_position)
            if explore_output > target_output:
                best_count = explore_counter
                target_output = explore_output    
        new_position[self.channel_codes[motor]] = self._current_position[self.channel_codes[motor]] + explore_step*best_count
        self.move_motors_abs(new_position)

    def optimize(self, desired_power):
        """
        Optimizes motors and finds a local maximum of power. Begins with intializing a simplex and performing downhill simplex. After 3 iterations of same best postion
        this function corrects for hystersis and prompts the user to decide if they would like to continue optimizing. If a low output is found, optimizer will explore to find
        the global peak instead. Optimization with stop if desired power is achieved.
        """
        hysteresis_counter = 0
        power_achieved_counter = 0
        final_output = self.read_output()
        if final_output > desired_power:
            self.log.info('Desired Power achieved. Initializing small search.')
            simplex_range = {k:v/20 for k, v in self.full_simplex_range.items()}
            sorted_simplex, sorted_output_simplex = self.randomize_initial_simplex(simplex_range)
        elif desired_power > final_output > 0.9*desired_power:
            simplex_range = {k:v/10 for k, v in self.full_simplex_range.items()}
            sorted_simplex, sorted_output_simplex = self.randomize_initial_simplex(simplex_range)
        elif 0.9*desired_power > final_output > 0.5*desired_power:
            simplex_range = {k:v/5 for k, v in self.full_simplex_range.items()}
            sorted_simplex, sorted_output_simplex = self.randomize_initial_simplex(simplex_range)
        else:
            sorted_simplex, sorted_output_simplex = self.randomize_initial_simplex(self.full_simplex_range)
        deadline = time.time() + self.timeout
        while deadline > time.time():
            prev_best_position = sorted_simplex[-1]
            final_simplex, final_output_simplex = self.downhill_simplex(sorted_simplex, sorted_output_simplex)
            sorted_simplex = final_simplex
            sorted_output_simplex = final_output_simplex
            final_position = final_simplex[-1]
            final_output = final_output_simplex[-1]
            print(f'final_simple = {final_simplex}')
            print(f'final_output_simplex = {final_output_simplex}')
            self.log.info(f'Best position = {final_position}')
            self.log.info(f'Best output = {final_output}')
            if power_achieved_counter > 0:
                self.log.info('Optimization succeed.')
                break
            if final_output > desired_power:
                final_output = self.move_motors_abs(final_position)
                print(final_output)
                simplex_range = {k:v/20 for k, v in self.full_simplex_range.items()}
                sorted_simplex, sorted_output_simplex = self.randomize_initial_simplex(simplex_range)
                power_achieved_counter +=1
            if final_position == prev_best_position:
                hysteresis_counter = hysteresis_counter + 1
                if hysteresis_counter > 2:
                    self.move_motors_abs(final_position)
                    self.log.info('Correcting hysteresis...')
                    self.correct_hysteresis()
                    self.log.info('Local Max Achieved.')
                    final_output = self.read_output()
                    print(final_output)
                    hysteresis_counter  = 0
                    if final_output > desired_power:
                        self.log.info('Desired Power achieved. Initializing small search.')
                        simplex_range = {k:v/20 for k, v in self.full_simplex_range.items()}
                        sorted_simplex, sorted_output_simplex = self.randomize_initial_simplex(simplex_range)
                    elif desired_power > final_output > 0.9*desired_power:
                        simplex_range = {k:v/10 for k, v in self.full_simplex_range.items()}
                        sorted_simplex, sorted_output_simplex = self.randomize_initial_simplex(simplex_range)
                    elif 0.9*desired_power > final_output > 0.5*desired_power:
                        simplex_range = {k:v/5 for k, v in self.full_simplex_range.items()}
                        sorted_simplex, sorted_output_simplex = self.randomize_initial_simplex(simplex_range)
                    elif 0.5*desired_power > final_output > 0.1*desired_power:
                        sorted_simplex, sorted_output_simplex = self.randomize_initial_simplex(self.full_simplex_range)
                    else:
                        self.log.info('Exploring...')
                        explore = True
                        exploring_motor = 0
                        explore_counter = 0
                        while explore == True:
                            explore_counter = explore_counter + 1
                            self.explore_motor(self.motor_list[exploring_motor])
                            self.correct_hysteresis()
                            explore_output=self.read_output()
                            if explore_output > 10*final_output:
                                self.log.info('Explore Success.')
                                explore = False
                            if explore_counter > 1:
                                exploring_motor = exploring_motor + 1
                                explore_counter = 0
                            if exploring_motor >= len(self.motor_list):
                                self.log.info('Explore Failed. Optimizer may be stuck or output is too low. Couple manually to better output.')
                                explore = False
                        self.log.info(f'Explore Output = {explore_output}')
                        if explore_output > desired_power:
                            self.log.info('Desired Power achieved. Initializing small search.')
                            simplex_range = {k:v/20 for k, v in self.full_simplex_range.items()}
                            sorted_simplex, sorted_output_simplex = self.randomize_initial_simplex(simplex_range)
                        elif desired_power > explore_output > 0.9*desired_power:
                            simplex_range = {k:v/10 for k, v in self.full_simplex_range.items()}
                            sorted_simplex, sorted_output_simplex = self.randomize_initial_simplex(simplex_range)
                        elif 0.9*desired_power > explore_output > 0.5*desired_power:
                            simplex_range = {k:v/5 for k, v in self.full_simplex_range.items()}
                            sorted_simplex, sorted_output_simplex = self.randomize_initial_simplex(simplex_range)
                        else:
                            sorted_simplex, sorted_output_simplex = self.randomize_initial_simplex(self.full_simplex_range)
            else:
                hysteresis_counter = 0
        self.move_motors_abs(final_position)
        self.log.info('Correcting hysteresis...')
        self.correct_hysteresis()
        self.log.info('Local Max Achieved.')
        final_output = self.read_output()
        self.log.info(f'Final power ={final_output}')