# -*- coding: utf-8 -*-

"""
This file contains the Qudi Interface file for control wavemeter hardware.

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

from abc import abstractmethod
from qudi.core.module import Base


class WavemeterInterface(Base):
    """ Define the controls for a wavemeter hardware.

    """

    @abstractmethod
    def start_acquisition(self):
        """ Method to start the wavemeter software.

        @return (int): error code (0:OK, -1:error)

        Also the actual threaded method for getting the current wavemeter
        reading is started.
        """
        pass

    @abstractmethod
    def stop_acquisition(self):
        """ Stops the Wavemeter from measuring and kills the thread that queries the data.

        @return (int): error code (0:OK, -1:error)
        """
        pass

    @property
    @abstractmethod
    def is_running(self):
        """
        Read-only flag indicating if the data acquisition is running.

        @return bool: Data acquisition is running (True) or not (False)
        """
        pass

    @abstractmethod
    def get_wavelength_stream(self):
        """ This method gets a continuous stream of the measured wavelengths with timestamp.

        @return float: returns tuple list of measured wavelengths with timestamp
        """
        pass

    @abstractmethod
    def get_current_wavelength(self, unit):
        """ This method returns the current wavelength.

        @param (str) unit: should be the unit in which the wavelength should be returned

        @return (float): wavelength (or negative value for errors)
        """
        pass

    @property
    @abstractmethod
    def measurement_timing(self):
        """ Get the measurement time

        @return (float): Measurement time in second
        """
        pass

    @measurement_timing.setter
    @abstractmethod
    def measurement_timing(self, value):
        """ Set the measurement time

        @param (float) value: Measurement time to set in second
        """
        pass

    @property
    @abstractmethod
    def unit(self):
        """ Property to store the unit of measured value.

        @return str: Returns the unit as a string
        """
        pass

    @unit.setter
    @abstractmethod
    def unit(self, value):
        """ Sets a different unit.

        @params str value: The target unit inserted as str.
        """
        pass
