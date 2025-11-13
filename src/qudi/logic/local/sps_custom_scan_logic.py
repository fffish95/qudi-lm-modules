# -*- coding: utf-8 -*-
"""
This file contains a Qudi logic module for different type scan application.

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
import numpy as np

from qudi.core.connector import Connector
from qudi.core.statusvariable import StatusVar
from qudi.util import tools
from qudi.core.module import LogicBase







class SPSCustonScanLogic(LogicBase):

    """
        sps_customscanlogic:
        module.Class: 'local.sps_custom_scan_logic.SPSCustonScanLogic'
    """
    # connector
    stepmotor1 = Connector(interface='StepMotor', optional=True)
    stepmotor2 = Connector(interface='StepMotor', optional=True)
    thorlabspm1 = Connector(interface = "ThorlabsPM", optional=True)
    nicard = Connector(interface = "NICard", optional=True)
    wavemeter = Connector(interface= "HighFinesseWavemeter", optional=True)
    fugsourcelogic = Connector(interface = "FugSourceLogic", optional=True)
    timetaggerlogic = Connector(interface = "TimeTaggerLogic", optional=True)

    # status vars

    CustomScanMode = StatusVar(default = ['step motor', 'power record', 'EIT', 'stark shift scan', 'scan trigger', 'timetagger writeintofile'])
    Params =  StatusVar(default=[{'step_motor_number': 1, 'motor_channel': 2, 'start_deg': 360.0, 'step_deg': -2.0, 'measurements_per_action': 4}, {'motor_on': False, 'step_motor_number': 1, 'motor_channel': 0, 'idle_deg': 0, 'running_deg': 90, 'averages': 4, 'measurements_per_action': 4, 'realpower_to_readout_ratio': 1.0, 'lines_power': [1.799035e-08, 1.7917925e-08, 1.9807925e-08, 2.0980975e-08, 2.1918575e-08, 2.4369349999999997e-08, 2.2822124999999998e-08, 2.6361400000000002e-08, 2.72615e-08, 2.8294125e-08, 3.1588325e-08, 3.5721525000000005e-08, 3.5477300000000004e-08, 4.0060575e-08, 3.826825e-08, 4.2179075e-08, 4.2636075e-08, 4.7786225e-08, 4.7433e-08, 5.3052425000000004e-08, 5.66623e-08, 5.5764849999999995e-08, 5.9578850000000005e-08, 6.0471075e-08, 6.872355000000001e-08, 6.840695e-08, 7.37708e-08, 8.89849e-08, 8.4034475e-08, 8.653235000000001e-08, 9.660505e-08, 9.06089e-08, 1.094355e-07, 1.10482e-07, 1.17251e-07, 1.1235549999999999e-07, 1.402885e-07, 1.4455175e-07, 1.7112825e-07, 1.6312100000000002e-07, 1.6719124999999999e-07, 1.7472425000000003e-07, 1.984345e-07, 2.0192275000000002e-07, 2.104945e-07, 2.2064375e-07, 2.49918e-07, 2.5896324999999997e-07, 2.5740300000000005e-07, 2.6508950000000004e-07, 3.070725e-07, 3.2915925e-07, 3.5789874999999996e-07, 3.7962624999999997e-07, 3.83737e-07, 4.0973275000000003e-07, 4.6803574999999994e-07, 4.883695e-07, 5.2559325e-07, 5.287575e-07, 5.951142499999999e-07, 6.306552499999999e-07, 6.26755e-07, 7.148485e-07, 7.592939999999999e-07, 8.040467499999999e-07, 8.293940000000001e-07, 9.3201075e-07, 9.029647499999999e-07, 1.0758575000000001e-06, 9.906815e-07, 1.1592075e-06, 1.1321275e-06, 1.223795e-06, 2.19223e-06]}, {'Background_subtract': False, 'wavelength_ramp': False, 'shutter_channels': ['pfi2'], 'start_frequency(THz)': 630.7234, 'step_frequency(MHz)': 50, 'lines_frequency': [], 'measurements_per_action': 1}, {'start_V': 250, 'step_V': -2, 'measurements_per_action': 1}, {'trigger_channel': ['pfi2'], 'trigger_length': 50},{
        'sample_name':'sample1',
        'measurements_per_action':1,
    }])


    def __init__(self, **kwargs):
        super().__init__(**kwargs)



    def on_activate(self):
        """ Initialisation performed during activation of the module.
        """
        self._tlpm = self.thorlabspm1()
        self._nicard = self.nicard()
        self._wavemeter = self.wavemeter()
        self._fugsourcelogic = self.fugsourcelogic()
        self._timetaggerlogic = self.timetaggerlogic()
        self._sm_modenum = 0
        self._pr_modenum = 1
        self._eit_modenum = 2
        self._ss_modenum = 3
        self._st_modenum = 4
        self._tw_modenum = 5


        self._shutter_task = None
        # Sets connections between signals and functions
        



    def on_deactivate(self):
        """ Deinitialisation performed during deactivation of the module.
        """
        return 0

    def start_scanner_handler(self, current): 

        value = self.CustomScanMode[current]
        func_map = {
            self.CustomScanMode[0]: self.step_motor_start_scanner,
            self.CustomScanMode[1]: self.power_record_start_scanner,
            self.CustomScanMode[2]: self.EIT_start_scanner,
            self.CustomScanMode[3]: self.stark_shift_scan_start_scanner,
            self.CustomScanMode[4]: self.scan_trigger_start_scanner,
            self.CustomScanMode[5]: self.timetagger_writeintofile_start_scanner,
        }
        func = func_map.get(value)
        func()

    def step_motor_start_scanner(self):
        # select which stepmotor controller
        if self.Params[self._sm_modenum]['step_motor_number'] == 1:
            motor = self.stepmotor1()
        elif self.Params[self._sm_modenum]['step_motor_number']== 2:
            motor = self.stepmotor2()
        else:
            self.log.error("wrong stepmotor number!")
            return -1
        # move the motor to the start point 
        motor.move_abs(self.Params[self._sm_modenum]['motor_channel'], self.Params[self._sm_modenum]['start_deg'])
        # wait until done, the longest wait time = 180*(60/4)*3 = 8100 ms
        t_delay = int(8100)
        tools.delay(t_delay)

    def power_record_start_scanner(self):
        self.Params[self._pr_modenum]['lines_power'] = []

    
    def EIT_start_scanner(self):
        if self.Params[self._eit_modenum]['wavelength_ramp']:
            self.Params[self._eit_modenum]['lines_frequency'] = []
            self._wavemeter.start_acquisition() # start the measurement
            self._wavemeter.set_exposure_mode(True) # automatically change the exposure time
            set_wavelength = self._wavemeter.convert_unit(self.Params[self._eit_modenum]['start_frequency(THz)'], 'Frequency', 'WavelengthVac')
            self._wavemeter.set_reference_course(set_wavelength)
            self._wavemeter.set_deviation_mode(True)
            # wait until wavelength is stable
            if not self.Params[self._eit_modenum]['Background_subtract']:
                timecounter = 0
                while timecounter < 80:
                    if self._wavemeter._is_stable:
                        break
                    tools.delay(250)
                    timecounter += 1
                if not timecounter<80:
                    self.log.warning('Wavelength not stablized!')
            


        if self.Params[self._eit_modenum]['Background_subtract']:
            for param in self.Params:
                param['measurements_per_action'] *= 2 # add 1 action for background substract
            self._shutter_task = self._nicard.create_do_task(taskname = 'shutter', channels = self.Params[self._eit_modenum]['shutter_channels'])
            # Stop deviation and automatical exposure time before close the shutter
            if self.Params[self._eit_modenum]['wavelength_ramp']:
                self._wavemeter.set_deviation_mode(False)
                self._wavemeter.set_exposure_mode(False)
            self._nicard.write_task(task= self._shutter_task, data = False)
        


    def stark_shift_scan_start_scanner(self):
        # enable voltage source
        self._fugsourcelogic.enable()
        # set to initial voltage
        self._fugsourcelogic.set_V(self.Params[self._ss_modenum]['start_V'])

    def scan_trigger_start_scanner(self):
        # output a trigger before each loop
        self._trigger_task = self._nicard.create_do_task(taskname = 'trigger1', channels = self.Params[self._st_modenum]['trigger_channel'])
        self._nicard.write_task(task= self._trigger_task, data = True)
        # keep the do on for trigger length time
        t_delay = int(self.Params[self._st_modenum]['trigger_length'])
        tools.delay(t_delay)
        self._nicard.write_task(task= self._trigger_task, data = False)
    
    def timetagger_writeintofile_start_scanner(self):
        self._timetaggerlogic._writeintofile_params['sample_name'] = f'{self.Params[self._tw_modenum]["sample_name"]}_0'
        self._timetaggerlogic.start_recording()

    def process_scanner_handler(self, current, scan_counter): 

        value = self.CustomScanMode[current]
        func_map = {
            self.CustomScanMode[0]: self.step_motor_process_scanner,
            self.CustomScanMode[1]: self.power_record_process_scanner,
            self.CustomScanMode[2]: self.EIT_process_scanner,
            self.CustomScanMode[3]: self.stark_shift_scan_process_scanner,
            self.CustomScanMode[4]: self.scan_trigger_process_scanner,
            self.CustomScanMode[5]: self.timetagger_writeintofile_process_scanner,
        }
        func = func_map.get(value)
        func(scan_counter)

    def step_motor_process_scanner(self, scan_counter):
        if self.Params[self._sm_modenum]['step_motor_number'] == 1:
            motor = self.stepmotor1()
        elif self.Params[self._sm_modenum]['step_motor_number']== 2:
            motor = self.stepmotor2()
        else:
            self.log.error("wrong stepmotor number!")
            return -1
        if scan_counter % self.Params[self._sm_modenum]['measurements_per_action'] == 0:
            # move the motor 
            motor.move_rel(self.Params[self._sm_modenum]['motor_channel'], self.Params[self._sm_modenum]['step_deg'])
            # wait until done
            t_delay = int(self.Params[self._sm_modenum]['step_deg']*(60/4)*3) 
            tools.delay(t_delay)

    def power_record_process_scanner(self, scan_counter):
        if self.Params[self._pr_modenum]['step_motor_number'] == 1:
            motor = self.stepmotor1()
        elif self.Params[self._pr_modenum]['step_motor_number']== 2:
            motor = self.stepmotor2()
        else:
            self.log.error("wrong stepmotor number!")
            return -1
        
        if scan_counter % self.Params[self._pr_modenum]['measurements_per_action'] == 0:      
            # connect power meter
            self._tlpm.connect()     
            if self.Params[self._pr_modenum]['motor_on']:
                # move the motor to the measurement point 
                motor.move_abs(self.Params[self._pr_modenum]['motor_channel'], self.Params[self._pr_modenum]['running_deg'])
                # wait until done, the longest wait time = 90*(60/4)*3 = 4050 ms
                t_delay = int(abs(self.Params[self._pr_modenum]['running_deg'] - self.Params[self._pr_modenum]['idle_deg'])*(60/4)*3)
                tools.delay(t_delay)

            # measurement
            power_measurements = []
            count = 0 
            while count < self.Params[self._pr_modenum]['averages']:
                power_measurements.append(self._tlpm.get_power())
                count+=1
                tools.delay(1000)
            if self.Params[self._pr_modenum]['motor_on']:
                # move the motor to the idle point 
                motor.move_abs(self.Params[self._pr_modenum]['motor_channel'], self.Params[self._pr_modenum]['idle_deg'])
                tools.delay(t_delay)
            power_measurements = np.array(power_measurements)
            value = np.mean(power_measurements) * self.Params[self._pr_modenum]['realpower_to_readout_ratio']
            self.Params[self._pr_modenum]['lines_power'].append(value)
            self._tlpm.disconnect()     
    
    def EIT_process_scanner(self,scan_counter):
        if self.Params[self._eit_modenum]['Background_subtract']:
            if scan_counter % self.Params[self._eit_modenum]['measurements_per_action'] == 0:
                # close the shutter
                if self.Params[self._eit_modenum]['wavelength_ramp']:
                    self._wavemeter.set_deviation_mode(False)
                    self._wavemeter.set_exposure_mode(False)
                self._nicard.write_task(task= self._shutter_task, data = False)
            elif scan_counter % self.Params[self._eit_modenum]['measurements_per_action'] == int(self.Params[self._eit_modenum]['measurements_per_action']/2):
                # open the shutter
                self._nicard.write_task(task= self._shutter_task, data = True)
                if self.Params[self._eit_modenum]['wavelength_ramp']:
                    self._wavemeter.set_deviation_mode(True)
                    self._wavemeter.set_exposure_mode(True)
                    set_frequency = float(self.Params[self._eit_modenum]['start_frequency(THz)'] + self.Params[self._eit_modenum]['step_frequency(MHz)']* (scan_counter // self.Params[self._eit_modenum]['measurements_per_action'])/1e6)
                    set_wavelength = self._wavemeter.convert_unit(set_frequency, 'Frequency', 'WavelengthVac')
                    self._wavemeter.set_reference_course(set_wavelength)
                    self.Params[self._eit_modenum]['lines_frequency'].append(set_frequency)
                    timecounter = 0
                    while timecounter < 80:
                        if self._wavemeter._is_stable:
                            break
                        tools.delay(250)
                        timecounter += 1
                    if not timecounter<80:
                        self.log.warning('Wavelength not stablized!')

        
        elif self.Params[self._eit_modenum]['wavelength_ramp']:
            if scan_counter % self.Params[self._eit_modenum]['measurements_per_action'] == 0:
                set_frequency = float(self.Params[self._eit_modenum]['start_frequency(THz)'] + self.Params[self._eit_modenum]['step_frequency(MHz)']* (scan_counter // self.Params[self._eit_modenum]['measurements_per_action'])/1e6)
                set_wavelength = self._wavemeter.convert_unit(set_frequency, 'Frequency', 'WavelengthVac')
                self._wavemeter.set_reference_course(set_wavelength)
                self.Params[self._eit_modenum]['lines_frequency'].append(set_frequency)
                timecounter = 0
                while timecounter < 80:
                    if self._wavemeter._is_stable:
                        break
                    tools.delay(250)
                    timecounter += 1
                if not timecounter<80:
                    self.log.warning('Wavelength not stablized!')
        

    def stark_shift_scan_process_scanner(self,scan_counter):
        if scan_counter % self.Params[self._ss_modenum]['measurements_per_action'] == 0:
            current_V = self._fugsourcelogic.get_V()
            set_V = current_V + self.Params[self._ss_modenum]['step_V']
            self._fugsourcelogic.set_V(set_V)

    def scan_trigger_process_scanner(self,scan_counter):

        self._nicard.write_task(task= self._trigger_task, data = True)
        # keep the do on for trigger length time
        t_delay = int(self.Params[self._st_modenum]['trigger_length'])
        tools.delay(t_delay)
        self._nicard.write_task(task= self._trigger_task, data = False)

    def timetagger_writeintofile_process_scanner(self,scan_counter):
        if scan_counter % self.Params[self._tw_modenum]['measurements_per_action'] == 0:
            self._timetaggerlogic.stop_recording()
            # wait until done 3000ms
            tools.delay(3000)
            self._timetaggerlogic._writeintofile_params['sample_name'] = f'{self.Params[self._tw_modenum]["sample_name"]}_{scan_counter}'
            self._timetaggerlogic.start_recording()            

    def stop_scanner_handler(self, current): 

        value = self.CustomScanMode[current]
        func_map = {
            self.CustomScanMode[0]: self.step_motor_stop_scanner,
            self.CustomScanMode[1]: self.power_record_stop_scanner,
            self.CustomScanMode[2]: self.EIT_stop_scanner,
            self.CustomScanMode[3]: self.stark_shift_scan_stop_scanner,
            self.CustomScanMode[4]: self.scan_trigger_stop_scanner,
            self.CustomScanMode[5]: self.timetagger_writeintofile_stop_scanner,
        }
        func = func_map.get(value)
        func()

    def step_motor_stop_scanner(self):
        if self.Params[self._pr_modenum]['step_motor_number'] == 1:
            motor = self.stepmotor1()
        elif self.Params[self._pr_modenum]['step_motor_number']== 2:
            motor = self.stepmotor2()
        else:
            self.log.error("wrong stepmotor number!")
            return -1

        # move the motor to the start point 
        motor.move_abs(self.Params[self._sm_modenum]['motor_channel'], self.Params[self._sm_modenum]['start_deg'])
        # wait until done, the longest wait time = 180*(60/4)*3 = 8100 ms
        t_delay = int(8100)
        tools.delay(t_delay)    

    def power_record_stop_scanner(self):
        pass
        #self._tlpm.disconnect()     
    
    def EIT_stop_scanner(self):
        if self.Params[self._eit_modenum]['Background_subtract']:
            for param in self.Params:
                param['measurements_per_action'] = int(param['measurements_per_action']/2) # remove 1 action added before
            # keep the shutter open
            self._nicard.write_task(task= self._shutter_task, data = True)
            self._nicard.close_do_task(taskname = 'shutter')
            self._shutter_task = None
        if self.Params[self._eit_modenum]['wavelength_ramp']:
            self._wavemeter.stop_acquisition()


    def stark_shift_scan_stop_scanner(self):
        self._fugsourcelogic.disable()

    def scan_trigger_stop_scanner(self):

        self._nicard.close_do_task(taskname = 'trigger1')
        self._trigger_task = None

    def timetagger_writeintofile_stop_scanner(self):
        self._timetaggerlogic.stop_recording()

    def function_0_handler(self, current): 

        value = self.CustomScanMode[current]
        func_map = {
            self.CustomScanMode[0]: self.step_motor_function_0,
            self.CustomScanMode[1]: self.power_record_function_0,
            self.CustomScanMode[2]: self.EIT_function_0,
            self.CustomScanMode[3]: self.stark_shift_scan_function_0,
            self.CustomScanMode[4]: self.scan_trigger_stop_scanner_0,
            self.CustomScanMode[5]: self.timetagger_writeintofile_stop_scanner_0,
        }
        func = func_map.get(value)
        func()

    def step_motor_function_0(self):
        pass

    def power_record_function_0(self):
        pass   
    
    def EIT_function_0(self):
        pass

    def stark_shift_scan_function_0(self):
        pass

    def scan_trigger_stop_scanner_0(self):
        pass

    def timetagger_writeintofile_stop_scanner_0(self):
        pass