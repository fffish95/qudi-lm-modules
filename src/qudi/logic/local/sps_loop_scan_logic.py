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






class SPSLoopScanLogic(LogicBase):

    """
        sps_loopscanlogic:
        module.Class: 'local.sps_loop_scan_logic.SPSLoopScanLogic'
    """
    # connector
    stepmotor1 = Connector(interface='MotorInterface')
    nicard = Connector(interface = "NICard")

    # status vars

    LoopScanMode = StatusVar(default = ['scan trigger', 'step motor'])
    Params =  StatusVar(default=[{
        'trigger_channel':['pfi1']
        'trigger_length': 500 # ms
    },{
        'motor_channel': 0,
        'start_deg': 0,
        'step_deg': 2,
    }])


    def __init__(self, **kwargs):
        super().__init__(**kwargs)



    def on_activate(self):
        """ Initialisation performed during activation of the module.
        """
        self._motor = self.stepmotor1()
        self._nicard = self.nicard()
        self._st_modenum = 0
        self._sm_modenum = 1


        self._trigger_task = None
        # Sets connections between signals and functions
        



    def on_deactivate(self):
        """ Deinitialisation performed during deactivation of the module.
        """
        return 0

    def start_scanner_handler(self, current): 

        value = self.LoopScanMode[current]
        func_map = {
            self.LoopScanMode[0]: self.scan_trigger_start_scanner,
            self.LoopScanMode[1]: self.step_motor_start_scanner,
        }
        func = func_map.get(value)
        func()

    def scan_trigger_start_scanner(self):
        # output a trigger before each loop
        self._trigger_task = self._nicard.create_do_task(taskname = 'trigger', channels = self.Params[self._st_modenum]['trigger_channel'])
        self._nicard.write_task(task= self._trigger_task, data = False)

    def step_motor_start_scanner(self):
        # move the motor to the start point 
        self._motor.move_abs(self.Params[self._sm_modenum]['motor_channel'], self.Params[self._sm_modenum]['start_deg'])
        # wait until done, the longest wait time = 180*(60/4)*3 = 8100 ms
        t_delay = int(8100)
        tools.delay(t_delay)


    def process_scanner_handler(self, current): 

        value = self.LoopScanMode[current]
        func_map = {
            self.LoopScanMode[0]: self.scan_trigger_process_scanner,
            self.LoopScanMode[1]: self.step_motor_process_scanner,
        }
        func = func_map.get(value)
        func()

    def scan_trigger_process_scanner(self):

        self._nicard.write_task(task= self._trigger_task, data = True)
        # keep the do on for trigger length time
        t_delay = int(self.Params[self._st_modenum]['trigger_length'])
        tools.delay(t_delay)
        self._nicard.write_task(task= self._trigger_task, data = False)

    def step_motor_process_scanner(self):

        # move the motor 
        self._motor.move_rel(self.Params[self._sm_modenum]['motor_channel'], self.Params[self._sm_modenum]['step_deg'])
        # wait until done
        t_delay = int(self.Params[self._sm_modenum]['step_deg']*(60/4)*3) 
        tools.delay(t_delay)

    def stop_scanner_handler(self, current): 

        value = self.LoopScanMode[current]
        func_map = {
            self.LoopScanMode[0]: self.scan_trigger_stop_scanner,
            self.LoopScanMode[1]: self.step_motor_stop_scanner,
        }
        func = func_map.get(value)
        func()

    def scan_trigger_stop_scanner(self):

        self._nicard.close_do_task(taskname = 'trigger')
        self._trigger_task = None

    def step_motor_stop_scanner(self):
        pass
    

    def function_0_handler(self, current): 

        value = self.LoopScanMode[current]
        func_map = {
            self.LoopScanMode[0]: self.scan_trigger_function_0,
            self.LoopScanMode[0]: self.step_motor_function_0,
        }
        func = func_map.get(value)
        func()

    def scan_trigger_function_0(self):
        pass

    def step_motor_function_0(self):
        pass   