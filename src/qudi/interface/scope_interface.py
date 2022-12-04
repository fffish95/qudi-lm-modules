# -*- coding: utf-8 -*-

"""
This file contains the Qudi Interface file for control wavemeter hardware.

Copyright (c) 2021, the qudi developers. See the AUTHORS.md file at the top-level directory of this
distribution and on <https://github.com/Ulm-IQO/qudi-iqo-modules/>

This file is part of qudi.

Qudi is free software: you can redistribute it and/or modify it under the terms of
the GNU Lesser General Public License as published by the Free Software Foundation,
either version 3 of the License, or (at your option) any later version.

Qudi is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY;
without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
See the GNU Lesser General Public License for more details.

You should have received a copy of the GNU Lesser General Public License along with qudi.
If not, see <https://www.gnu.org/licenses/>.
"""

from abc import abstractmethod
from qudi.core.module import Base


class ScopeInterface(Base):
    """ Define the controls for a scope hardware.
    """

    @abstractmethod
    def send(self, message):
        """ Send a message through the socket to LeCroy oscilloscope. 
        Sends message length in header frame and then writes to the 
        socket until all is received by the oscilloscope
        returns 0 if abnormal exit
        """
        pass

    @abstractmethod
    def readAll(self):
        """ Read all that the device gives us (ascii) on Lecroy.s socket
        1) Get header from device (flag, len)
        2) receive len bytes and decode it
        returns the flag of the last transmission frame and complete data string in ascii
        NB! assumes all data frame transfers can be done in one go
        """
        pass

    @abstractmethod
    def getDataBytes(self, channel="C1", block="DAT1"):
        """
        Simplest data retrieval, by byte values (low precision)
        Use only for verification (should work regardless of data packing)
        Channel can be "C1" or "C2", 
        data type "DAT1" for first block or "DAT2" for second (special, look at doc.)
        returns list of values in 8-bit signed precision
        """
        pass

    @abstractmethod
    def getDataWords(self, channel="C1", block="DAT1"):
        """
        return data in tuple of word values (-32768 to 32767)
        Reads header, and double checks:
        1: that the data stream ended correctly (!LECROY_DATA_FLAG flag with "\n" end),
        2: length of the byte vector matches the specified length in the header
        channel : "C1" or "C2"
        block : "DAT1" (mostly), or "DAT2"
        
        returns list of values (16-bit signed)
        """
        pass

    @abstractmethod
    def getDataFloats(self, channel="C1", block="DAT1"):
        """
        return the data in measured units in np.float64
        channel : "C1" or "C2"
        block : "DAT1" (mostly), or "DAT2"
        DAT1 is basic integer data block for storing measurements
        DAT2 is used to hold the results of processing functions (extrema, FFT, etc.)
        returns (VERTUNIT, array) : properly scaled numpy array of vertical value data
        """
        pass

    @abstractmethod
    def getHorProperties(self, channel="C1"):
        """
        return the time vector data for the measurement for channel "channel"
        for single sweep waveforms, for data point i, we have the horiz.
        time from trigger being
        t[i] = HORIZ_INTERVAL * i + HORIZ_OFFSET
        in specified HORIZ_UNIT units
        returns (HORUNIT, HORIZ_OFFSET, HORIZ_INTERVAL)
        where
        HORUNIT (string) is horizontal unit
        HORIZ_OFFSET (double) is trigger offset for the first sweep of the trigger,
                                 seconds b.w. the trig. and 1st data point
        HORIZ_INTERVAL (float) is sampling interal for time domain waveforms
        """
        pass

