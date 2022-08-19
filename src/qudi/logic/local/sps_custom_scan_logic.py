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
from PySide2 import QtCore
import copy
from ctypes import cdll,c_long, c_ulong, c_uint32,byref,create_string_buffer,c_bool,c_char_p,c_int,c_int16,c_double, sizeof, c_voidp
from qudi.hardware.local.ThorlabsPM.TLPM import TLPM






class SPSCustonScanLogic(LogicBase):

    """
        sps_customscanlogic:
        module.Class: 'local.sps_custom_scan_logic.SPSCustonScanLogic'
    """
    # connector
    stepmotor1 = Connector(interface='MotorInterface')

    # status vars
    PowerRecordParams = StatusVar(default={
        'motor_channel': 0,
        'idle_deg': 0,
        'running_deg': 90,
        'averages': 1
    })
    CustomScanMode = StatusVar(default = ['saturation scan', 'EIT', 'stark shift scan'])
    SaturationScanParams = StatusVar(default={
        'motor_channel': 0,
        'start_deg': 0,
        'step_deg': 2
    })
    EITParams = StatusVar(default=dict())
    StarkShiftScanParams = StatusVar(default=dict())


    def __init__(self, **kwargs):
        super().__init__(**kwargs)



    def on_activate(self):
        """ Initialisation performed during activation of the module.
        """
        self._motor = self.stepmotor1()
        self.Params = [self.SaturationScanParams, self.EITParams, self.StarkShiftScanParams]



        # Sets connections between signals and functions
        



    def on_deactivate(self):
        """ Deinitialisation performed during deactivation of the module.
        """
        return 0

    def start_scanner_handler(self, current): 

        value = self.CustomScanMode[current]
        func_map = {
            self.CustomScanMode[0]: self.method_0_start_scanner,
            self.CustomScanMode[1]: self.method_1_start_scanner,
            self.CustomScanMode[2]: self.method_2_start_scanner,
        }
        func = func_map.get(value)
        func()

    def method_0_start_scanner(self):
        # move the motor to the start point 
        self._motor.move_abs(self.SaturationScanParams['motor_channel'], self.SaturationScanParams['start_deg'])
        # wait until done, the longest wait time = 180*(60/4)*3 = 8100 ms
        t_delay = int(8100)
        tools.delay(t_delay)
    
    def method_1_start_scanner(self):
        pass

    def method_2_start_scanner(self):
        pass


    
    def process_scanner_handler(self, current, scan_counter, measurements_per_action): 

        value = self.CustomScanMode[current]
        func_map = {
            self.CustomScanMode[0]: self.method_0_process_scanner,
            self.CustomScanMode[1]: self.method_1_process_scanner,
            self.CustomScanMode[2]: self.method_2_process_scanner,
        }
        func = func_map.get(value)
        func(scan_counter, measurements_per_action)

    def method_0_process_scanner(self, scan_counter, measurements_per_action):
        if scan_counter % measurements_per_action == 0:
            # move the motor 
            self._motor.move_rel(self.SaturationScanParams['motor_channel'], self.SaturationScanParams['step_deg'])
            # wait until done
            t_delay = int(self.SaturationScanParams['step_deg']*(60/4)*3) 
            tools.delay(t_delay)
    
    def method_1_process_scanner(self,scan_counter, measurements_per_action):
        pass

    def method_2_process_scanner(self,scan_counter, measurements_per_action):
        pass



    def stop_scanner_handler(self, current): 

        value = self.CustomScanMode[current]
        func_map = {
            self.CustomScanMode[0]: self.method_0_stop_scanner,
            self.CustomScanMode[1]: self.method_1_stop_scanner,
            self.CustomScanMode[2]: self.method_2_stop_scanner,
        }
        func = func_map.get(value)
        func()

    def method_0_stop_scanner(self):
        pass
    
    def method_0_stop_scanner(self):
        pass

    def method_0_stop_scanner(self):
        pass


    def function_0_handler(self, current): 

        value = self.CustomScanMode[current]
        func_map = {
            self.CustomScanMode[0]: self.method_0_function_0,
            self.CustomScanMode[1]: self.method_1_function_0,
            self.CustomScanMode[2]: self.method_2_function_0,
        }
        func = func_map.get(value)
        func()

    def method_0_function_0(self):
        pass
    
    def method_1_function_0(self):
        pass

    def method_2_function_0(self):
        pass

    def power_measurement(self):
        tlPM = TLPM()

        # connect power meter
        resourceName = create_string_buffer(1024)
        tlPM.getRsrcName(c_int(0), resourceName)
        tlPM.open(resourceName, c_bool(True), c_bool(False))

        # move the motor to the measurement point 
        self._motor.move_abs(self.PowerRecordParams['motor_channel'], self.PowerRecordParams['running_deg'])
            # wait until done, the longest wait time = 90*(60/4)*3 = 4050 ms
        t_delay = int(4050)
        tools.delay(t_delay)

        # measurement
        power_measurements = []
        count = 0 
        while count < self.PowerRecordParams['averages']:
            power =  c_double()
            tlPM.measPower(byref(power))
            power_measurements.append(power.value)
            count+=1
            tools.delay(1000)
        tlPM.close()
        power_measurements = np.array(power_measurements)
        value = np.mean(power_measurements)            
        return value