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
    stepmotor1 = Connector(interface='MotorInterface')
    thorlabspm1 = Connector(interface = "ThorlabsPM")
    nicard = Connector(interface = "NICard")
    wavemeter = Connector(interface= "HighFinesseWavemeter")
    fugsourcelogic = Connector(interface = "FugSourceLogic")
    timetaggerlogic = Connector(interface = "TimeTaggerLogic")

    # status vars

    CustomScanMode = StatusVar(default = ['step motor', 'power record', 'EIT', 'stark shift scan', 'scan trigger', 'timetagger writeintofile'])
    Params =  StatusVar(default=[{
        'motor_channel': 0,
        'start_deg': 0,
        'step_deg': 2,
        'measurements_per_action': 1
    },{ 'motor_on': False,
        'motor_channel': 0,
        'idle_deg': 0,
        'running_deg': 90,
        'averages': 1,
        'measurements_per_action': 1,
        'realpower_to_readout_ratio': 1,
        'lines_power': []
    },{ 'Background_subtract': False,
        'wavelength_ramp': False,
        'shutter_channels': ['pfi2'],
        'start_frequency(THz)' : 630.72340,
        'step_frequency(MHz)' : 50,
        'lines_frequency': [],
        'measurements_per_action': 1
        },{
        'start_V': 250,
        'step_V': -2,
        'measurements_per_action': 1 
    },{
        'trigger_channel':['pfi1'],
        'trigger_length': 50,
    },{
        'sample_name':'sample1',
        'measurements_per_action':1,
    }])


    def __init__(self, **kwargs):
        super().__init__(**kwargs)



    def on_activate(self):
        """ Initialisation performed during activation of the module.
        """
        self._motor = self.stepmotor1()
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
        # move the motor to the start point 
        self._motor.move_abs(self.Params[self._sm_modenum]['motor_channel'], self.Params[self._sm_modenum]['start_deg'])
        # wait until done, the longest wait time = 180*(60/4)*3 = 8100 ms
        t_delay = int(8100)
        tools.delay(t_delay)

    def power_record_start_scanner(self):
        self.Params[self._pr_modenum]['lines_power'] = []
        self._tlpm.connect()     
    
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
        if scan_counter % self.Params[self._sm_modenum]['measurements_per_action'] == 0:
            # move the motor 
            self._motor.move_rel(self.Params[self._sm_modenum]['motor_channel'], self.Params[self._sm_modenum]['step_deg'])
            # wait until done
            t_delay = int(self.Params[self._sm_modenum]['step_deg']*(60/4)*3) 
            tools.delay(t_delay)

    def power_record_process_scanner(self, scan_counter):
        if scan_counter % self.Params[self._pr_modenum]['measurements_per_action'] == 0:      
            # connect power meter

            if self.Params[self._pr_modenum]['motor_on']:
                # move the motor to the measurement point 
                self._motor.move_abs(self.Params[self._pr_modenum]['motor_channel'], self.Params[self._pr_modenum]['running_deg'])
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
                self._motor.move_abs(self.Params[self._pr_modenum]['motor_channel'], self.Params[self._pr_modenum]['idle_deg'])
                tools.delay(t_delay)
            power_measurements = np.array(power_measurements)
            value = np.mean(power_measurements) * self.Params[self._pr_modenum]['realpower_to_readout_ratio']
            self.Params[self._pr_modenum]['lines_power'].append(value)

    
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
        # move the motor to the start point 
        self._motor.move_abs(self.Params[self._sm_modenum]['motor_channel'], self.Params[self._sm_modenum]['start_deg'])
        # wait until done, the longest wait time = 180*(60/4)*3 = 8100 ms
        t_delay = int(8100)
        tools.delay(t_delay)    

    def power_record_stop_scanner(self):
        self._tlpm.disconnect()     
    
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