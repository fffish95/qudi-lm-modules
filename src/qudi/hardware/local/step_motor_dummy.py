# -*- coding: utf-8 -*-

"""
This file contains the Qudi hardware StepMotor class.

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

from qudi.core.configoption import ConfigOption
from qudi.core.module import Base

import pyvisa as visa

class StepMotor(Base):
    """ Designed for driving a servo motor through Arduino.

    See [arduino-python3 Command API] & [arduino-libraries/Servo] for details.

    Example config for copy-paste:

    StepMotor:
        module.Class: 'local.step_motor.StepMotor'

    """



    def on_activate(self):
        pass

    def on_deactivate(self):
        pass

    
    def get_constraints(self):
        pass

    def move_rel(self, motor_channel=None, degree=None):
        pass

    
    def move_abs(self, motor_channel=None, degree=None):
        pass


    def abort(self):
        pass


    def get_pos(self):
        pass


    def get_status(self):
        pass
    def calibrate(self):
        pass
    def get_velocity(self):
        pass
    def set_velocity(self):
        pass

    def _attach(self):
        pass
 
