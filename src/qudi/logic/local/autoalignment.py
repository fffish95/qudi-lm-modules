# Modified from (c) 2019, Robert Kauffman
import numpy as np

from qudi.core.connector import Connector
from qudi.core.statusvariable import StatusVar
from qudi.util import tools
from qudi.core.module import LogicBase
from qudi.util.mutex import Mutex
import time



class autoalignmentLogic(LogicBase):

    """
    autoalignmentlogic:
        module.Class: 'local.sps_custom_scan_logic.SPSCustonScanLogic'
        connect:
            pmc: 'nf8752'
            # thorlabspm1: 'thorlabspm'
            # timetagger: 'tagger'
    """
    # connector
    pmc = Connector(interface='NF8752Logic')
    thorlabspm1 = Connector(interface = "ThorlabsPM", optional=True)
    timetagger = Connector(interface = "TT", optional=True)

    def on_activate(self):
        """ Initialisation performed during activation of the module.
        """
        self._pmc = self.pmc()
        self._tlpm = self.thorlabspm1()
        self._tt = self.timetagger()
        if self._tlpm is not None:
            self._tlpm.connect()
        # Number of samples wanted. The read time per sample is 1 second.
        self.num_samples = 4
        self.motor_alphabet = ['x1','y1','x2','y2','z']
        self.full_simplex_range = dict(zip(self.motor_alphabet, list([1000]*4+[10000])))
        self.motor_list = ['x1','y1','x2','y2','z'] # optional ['x1','y1','x2','y2']
        self.correct_hysteresis_steps = {'x1':10,'y1':10,'x2':10,'y2':10,'z':10}
        #The length of optimization time in seconds. 
        self.timeout = 300

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
                tools.delay(1000)
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
        for i in self.motor_number:
            self._pmc.move_abs(position=position[i], axis= self.motor_list[i])
        output = self.read_output()
        return 
    
    def move_two_motors_rel(self, motor1, motor2, motor1_displacement, motor2_displacement):
        """
        Relative motion of two motors. Used in the correct_hysteresis funtion.
        """
        self._pmc.move_rel(steps = motor1_displacement, axis = motor1)
        self._pmc.move_rel(steps = motor2_displacement, axis = motor2)

    def randomize_initial_simplex(self,simplex_range):
        """
        Set current position to 0.
        pick motor_number +1 positions for initial the simplex, the randomized range could be defined individually for different motors.
        """
        # set current postion to 0
        self._pmc.define_home()

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
                self._pmc.move_abs(position=position, axis= motor)
                motor_position.append(position)
            output = self.read_output()
            simplex.append(motor_position)
            output_simplex.append(output)

        #Orders simplex positions from least to greatest output.
        sorted_output_simplex, sorted_simplex = zip(*sorted(zip(output_simplex,simplex)))
        return sorted_simplex, sorted_output_simplex
    
    def downhill_simplex(self, sorted_simplex, sorted_output_simplex):
        """
        optimize the simplex
        """

        # Solves for the centroid of the simplex excluding the worst position. Used in elements of downhill_simplex and optimize function.
        # Requires no inputs and uses whatever the current simplex is.
        sorted_simplex = np.asarray(sorted_simplex, dtype=float)
        centroid_position = sorted_simplex[:1].mean(axis=0)
        #Solves for a position reflected from the worst position. Used in elements of downhill_simplex and optimize function.
        worst_position = sorted_simplex[0]
        reflection_position = centroid_position + 1*(centroid_position-worst_position)
        # move motors to the reflection position
        reflection_output = self.move_motors_abs(reflection_position)
        # if the reflection point is within the rest output_simplex range, accept the reflection.
        if sorted_output_simplex[1] < reflection_output <= sorted_output_simplex[-1]:
            sorted_simplex[0] = reflection_position
            sorted_output_simplex[0] = reflection_output
        # if reflection was very good, try expanding further
        elif reflection_output > sorted_output_simplex[-1]:
            expansion_position = centroid_position + 2 * (reflection_position - centroid_position)
            expansion_output = self.move_motors_abs(expansion_position)
            # Keep whichever is better
            if reflection_output > expansion_output:
                sorted_simplex[0] = reflection_position
                sorted_output_simplex[0] = reflection_output
            else:
                sorted_simplex[0] = expansion_position
                sorted_output_simplex[0] = expansion_output
        # if reflection is not so good but better than the worst, try outside contraction
        elif sorted_output_simplex[0] < reflection_output <= sorted_output_simplex[1]:
            contraction_position = centroid_position + 0.5 * (reflection_position - centroid_position)
            contraction_output = self.move_motors_abs(contraction_position)
            # if contraction output is better than the reflection output, keep it. Otherwise shrink step: all new simplex positions shrunk toward the current best position
            if contraction_output > reflection_output:
                sorted_simplex[0] = contraction_position
                sorted_output_simplex[0] = contraction_output
            else:
                for i in range(self.motor_number):
                    sorted_simplex[i] = sorted_simplex[-1] + 0.5 * (sorted_simplex[i] - sorted_simplex[-1])
                    sorted_output_simplex[i] = self.move_motors_abs(sorted_simplex[i])
        # if the reflection is worse than the worst, try inside contraction
        else:
            contraction_position = centroid_position + 0.5 * (worst_position - centroid_position)
            contraction_output = self.move_motors_abs(contraction_position)
            # if contraction output is better than the worst output, keep it. Otherwise shrink step: all new simplex positions shrunk toward the current best position
            if contraction_output > sorted_output_simplex[0]:
                sorted_simplex[0] = contraction_position
                sorted_output_simplex[0] = contraction_output
            else:
                for i in range(self.motor_number):
                    sorted_simplex[i] = sorted_simplex[-1] + 0.5 * (sorted_simplex[i] - sorted_simplex[-1])
                    sorted_output_simplex[i] = self.move_motors_abs(sorted_simplex[i])
        final_output_simplex, final_simplex = zip(*sorted(zip(sorted_output_simplex,sorted_simplex)))
        return final_simplex, final_output_simplex
    
    def correct_hysteresis(self):
        """
        Because of the pizeo hysteresis, the picomotor could not remeber previous absolute positions. 
        This function corrects the hysteresis of the best position by determining which direction each motor needs to move to get back to maximum.
        """
        # correct hysteresis 'z'
        if 'z' in self.motor_list:
            prev_output = self.read_output()
            self._pmc.move_rel(steps = self.correct_hysteresis_steps['z'], axis = 'z')
            new_output = self.read_output()
            if new_output < prev_output:
                self.correct_hysteresis_steps['z'] = -self.correct_hysteresis_steps['z']
                self._pmc.move_rel(steps = 2*self.correct_hysteresis_steps['z'], axis = 'z')
                new_output = self.read_output()
            if new_output < prev_output:
                self.log.info("correct hysteresis for z failed. You may want to assign a smaller value for self.correct_hysteresis_steps['z']")
            while new_output >= prev_output:
                prev_output = new_output
                self._pmc.move_rel(steps = self.correct_hysteresis_steps['z'], axis = 'z')
            self._pmc.move_rel(steps = -self.correct_hysteresis_steps['z'], axis = 'z')

        # correct hysteresis 'x1' and 'x2'
        prev_output = self.read_output()
        self._pmc.move_rel(steps = self.correct_hysteresis_steps['x1'], axis = 'x1')
        new_output = self.read_output()
        if new_output < prev_output:
            self.correct_hysteresis_steps['x1'] = -self.correct_hysteresis_steps['x1']
            self._pmc.move_rel(steps = 2*self.correct_hysteresis_steps['x1'], axis = 'x1')
            new_output = self.read_output()
        if new_output < prev_output:
            self.log.info("correct hysteresis for x1 failed. You may want to assign a smaller value for self.correct_hysteresis_steps['x1']")
        prev_output = new_output
        self._pmc.move_rel(steps = self.correct_hysteresis_steps['x2'], axis = 'x2')
        new_output = self.read_output()
        if new_output < prev_output:
            self.correct_hysteresis_steps['x2'] = -self.correct_hysteresis_steps['x2']
            self._pmc.move_rel(steps = 2*self.correct_hysteresis_steps['x2'], axis = 'x2')
            new_output = self.read_output()
        if new_output < prev_output:
            self.log.info("correct hysteresis for x2 failed. You may want to assign a smaller value for self.correct_hysteresis_steps['x2']")
        while new_output >= prev_output:
            prev_output = new_output
            self.move_two_motors_rel(motor1 = 'x1', motor2 = 'x2', motor1_displacement = self.correct_hysteresis_steps['x1'], motor2_displacement = self.correct_hysteresis_steps['x2'])
        self.move_two_motors_rel(motor1 = 'x1', motor2 = 'x2', motor1_displacement = -self.correct_hysteresis_steps['x1'], motor2_displacement = -self.correct_hysteresis_steps['x2'])

        # correct hysteresis 'y1' and 'y2'
        prev_output = self.read_output()
        self._pmc.move_rel(steps = self.correct_hysteresis_steps['y1'], axis = 'y1')
        new_output = self.read_output()
        if new_output < prev_output:
            self.correct_hysteresis_steps['y1'] = -self.correct_hysteresis_steps['y1']
            self._pmc.move_rel(steps = 2*self.correct_hysteresis_steps['y1'], axis = 'y1')
            new_output = self.read_output()
        if new_output < prev_output:
            self.log.info("correct hysteresis for y1 failed. You may want to assign a smaller value for self.correct_hysteresis_steps['y1']")
        prev_output = new_output
        self._pmc.move_rel(steps = self.correct_hysteresis_steps['y2'], axis = 'y2')
        new_output = self.read_output()
        if new_output < prev_output:
            self.correct_hysteresis_steps['y2'] = -self.correct_hysteresis_steps['y2']
            self._pmc.move_rel(steps = 2*self.correct_hysteresis_steps['y2'], axis = 'y2')
            new_output = self.read_output()
        if new_output < prev_output:
            self.log.info("correct hysteresis for y2 failed. You may want to assign a smaller value for self.correct_hysteresis_steps['y2']")
        while new_output >= prev_output:
            prev_output = new_output
            self.move_two_motors_rel(motor1 = 'y1', motor2 = 'y2', motor1_displacement = self.correct_hysteresis_steps['y1'], motor2_displacement = self.correct_hysteresis_steps['y2'])
        self.move_two_motors_rel(motor1 = 'y1', motor2 = 'y2', motor1_displacement = -self.correct_hysteresis_steps['y1'], motor2_displacement = -self.correct_hysteresis_steps['y2'])

    def explore_motor(self, motor, direction):
        """
        Explores one motor in one direction 2000 steps by moving this far and working back to the original position 100 steps at a time. Used in optimize function.
        Requires the motor to be explored and the direction of exploration (1 is forward and -1 is backward).
        """
        explore_step = 100
        if direction < 0:
            explore_step = -explore_step
        explore_counter = 20
        best_count = 0
        target_output = self.read_output()
        self._pmc.move_rel(steps = explore_counter*explore_step, axis = motor)
        while explore_counter >= 0:
            explore_counter = explore_counter - 1
            self._pmc.move_rel(steps = -explore_step, axis = motor)
            explore_output = self.read_output()
            if explore_output > target_output:
                best_count = explore_counter
                target_output = explore_output    
        self._pmc.move_rel(steps = explore_step*best_count, axis = motor)

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
            final_position = final_simplex[-1]
            final_output = final_output_simplex[-1]
            self.log.info(f'Best position = {final_position}')
            self.log.info(f'Best output = {final_output}')
            if power_achieved_counter>2:
                self.log.info('Optimization succeed.')
                break
                
            if final_position == prev_best_position:
                hysteresis_counter = hysteresis_counter + 1
                if hysteresis_counter > 2:
                    self.move_motors_abs(final_position)
                    self.log.info('Correcting hysteresis...')
                    self.correct_hysteresis()
                    self.log.info('Local Max Achieved.')
                    final_output = self.read_output()
                if final_output > desired_power:
                    self.log.info('Desired Power achieved. Initializing small search.')
                    simplex_range = {k:v/20 for k, v in self.full_simplex_range.items()}
                    sorted_simplex, sorted_output_simplex = self.randomize_initial_simplex(simplex_range)
                    power_achieved_counter +=1
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
                    direction = 1
                    explore_counter = 0
                    while explore == True:
                        explore_counter = explore_counter + 1
                        self.explore_motor(self.motor_list[exploring_motor], direction)
                        direction = -direction
                        self.correct_hysteresis()
                        explore_output=self.read_output()
                        if explore_output > 10*final_output:
                            self.log.info('Explore Success.')
                            explore = False
                        if explore_counter > 1:
                            exploring_motor = exploring_motor + 1
                            explore_counter = 0
                        if exploring_motor >= len(self.motor_list):
                            self.correct_hysteresis()
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
        self.log(f'Final power ={final_output}')