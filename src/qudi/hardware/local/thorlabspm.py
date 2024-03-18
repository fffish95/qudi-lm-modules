# -*- coding: utf-8 -*-

"""
This file contains the Qudi hardware ThorlabsPM class.

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

from qudi.core.module import Base
from qudi.core.configoption import ConfigOption

from ctypes import cdll,c_long, c_ulong, c_uint32,byref,create_string_buffer,c_bool,c_char_p,c_int,c_int16,c_double, sizeof, c_voidp
from qudi.hardware.local.ThorlabsPM.TLPM import TLPM

class ThorlabsPM(Base):
    """
    Example config for copy-paste:
    
    thorlabspm:
        module.Class: 'local.ThorlabsPM.ThorlabsPM'
    """


    def on_activate(self):
        self._tlPM = TLPM()        
        # connect power meter
        deviceCount = c_uint32()
        self._tlPM.findRsrc(byref(deviceCount))
        resourceName = create_string_buffer(1024)
        self._tlPM.getRsrcName(c_int(0), resourceName)
        self._tlPM.open(resourceName, c_bool(True), c_bool(False))

    def on_deactivate(self):
        self._tlPM.close()

    
    def get_power(self):
        power =  c_double()
        self._tlPM.measPower(byref(power))
        return power.value

