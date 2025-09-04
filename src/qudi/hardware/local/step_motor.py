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
import time

class StepMotor(Base):
    """ Designed for driving a servo motor through Arduino.

    See [arduino-python3 Command API] & [arduino-libraries/Servo] for details.

    Example config for copy-paste:

    StepMotor:
        module.Class: 'local.step_motor.StepMotor'
        options:
            port:
                - 'COM9'


    """

    # config options
    _resurce_name = ConfigOption('port', list(), missing='error')


    def on_activate(self):
        self.rm = visa.ResourceManager()
        try:
            self._my_instrument = self.rm.open_resource(resource_name = self._resurce_name[0], baud_rate=57600, write_termination='\n')
        except:
            print("PANIC, COULDNT OPEN")
            self.rm.close()
        

    def on_deactivate(self):
        self._my_instrument.close()
        self.rm.close()
        return 0

    
    def get_constraints(self):
        pass

    def move_rel(self, motor_channel=None, degree=None):
        if motor_channel is None:
            self.log.error('The motor channel is None.')
            return -1
        if degree is None:
            self.log.error('The degree is None.')
            return -1

        self._my_instrument.write('MOVEREL {} {} deg'.format(motor_channel, degree))

    
    def move_abs(self, motor_channel=None, degree=None):
        if motor_channel is None:
            self.log.error('The motor channel is None.')
            return -1
        if degree is None:
            self.log.error('The degree is None.')
            return -1

        self._my_instrument.write('MOVEABS {} {} deg'.format(motor_channel, degree))

    def get_pos(self):
        try:
            pos = self._my_instrument.query('GETPOS')
            position = float(''.join(char for char in pos if char.isdigit() or char in '.-'))
            return position #returns position in degrees
        except Exception as e:
            self.log.error(f'Error getting position: {e}')
            return -1
        
    def set_zero(self, motor_channel=None):
        """Set the current position as zero for the specified motor channel."""
        if motor_channel is None:
            self.log.error('The motor channel is None.')
            return -1

        position = self.get_pos()
        self._my_instrument.write('SETOPTZEROPOS {} {}'.format(motor_channel, position))

    def calibrate(self, motor_channel=None):
        if motor_channel is None:
            self.log.error('The motor channel is None.')
            return -1
        self._my_instrument.write('ZERORUN {}'.format(motor_channel))

    def stop(self, motor_channel=None):
        if motor_channel is None:
            self.log.error('The motor channel is None.')
            return -1
        self._my_instrument.write('STOP {}'.format(motor_channel))

    def scan_line(self, motor_channel=None, start=None, stop=None, stepnum=None, frequency=None):
        if motor_channel is None:
            self.log.error('The motor channel is None.')
            return -1
        if start is None or stop is None or stepnum is None or frequency is None:
            self.log.error('One or more parameters are None: start={}, stop={}, stepnum={}, frequency={}'.format(start, stop, stepnum, frequency))
            return -1

        degree = (stop - start) / stepnum
        sleep_time = 1 / frequency
        for i in range(stepnum):
            self.move_rel(motor_channel, degree)
            time.sleep(sleep_time)
 
