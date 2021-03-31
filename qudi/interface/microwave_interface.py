# -*- coding: utf-8 -*-

"""
This file contains the Qudi Interface file to control microwave devices.

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
from qudi.core.enums import TriggerEdge, SamplingOutputMode
from qudi.util.helpers import in_range


class MicrowaveInterface(Base):
    """This class defines the interface to simple microwave generators with or without frequency
    scan capability.
    """

    @property
    @abstractmethod
    def constraints(self):
        """The microwave constraints object for this device.

        @return MicrowaveConstraints:
        """
        raise NotImplementedError

    @property
    @abstractmethod
    def is_scanning(self):
        """Read-Only boolean flag indicating if a scan is running at the moment. Can be used
        together with module_state() to determine if the currently running microwave output is a
        scan or CW.
        Should return False if module_state() is 'idle'.

        @return bool: Flag indicating if a scan is running (True) or not (False)
        """
        raise NotImplementedError

    @property
    @abstractmethod
    def cw_power(self):
        """Read-only property returning the currently configured CW microwave power in dBm.

        @return float: The currently set CW microwave power in dBm.
        """
        raise NotImplementedError

    @property
    @abstractmethod
    def cw_frequency(self):
        """Read-only property returning the currently set CW microwave frequency in Hz.

        @return float: The currently set CW microwave frequency in Hz.
        """
        raise NotImplementedError

    @property
    @abstractmethod
    def scan_power(self):
        """Read-only property returning the currently configured microwave power in dBm used for
        scanning.

        @return float: The currently set scanning microwave power in dBm
        """
        raise NotImplementedError

    @property
    @abstractmethod
    def scan_frequencies(self):
        """Read-only property returning the currently configured microwave frequencies used for
        scanning.

        In case of self.scan_mode == SamplingOutputMode.JUMP_LIST, this will be a 1D numpy array.
        In case of self.scan_mode == SamplingOutputMode.EQUIDISTANT_SWEEP, this will be a tuple
        containing 3 values (freq_begin, freq_end, number_of_samples).
        If no frequency scan has been configured, return None.

        @return float[]: The currently set scanning frequencies. None if not set.
        """
        raise NotImplementedError

    @property
    @abstractmethod
    def scan_mode(self):
        """Read-only property returning the currently configured scan mode Enum.

        @return SamplingOutputMode: The currently set scan mode Enum
        """
        raise NotImplementedError

    @property
    @abstractmethod
    def scan_sample_rate(self):
        """Read-only property returning the currently configured scan sample rate in Hz.

        @return float: The currently set scan sample rate in Hz
        """
        raise NotImplementedError

    @abstractmethod
    def off(self):
        """Switches off any microwave output (both scan and CW).
        Must return AFTER the device has actually stopped.
        """
        raise NotImplementedError

    @abstractmethod
    def set_cw(self, frequency, power):
        """Configure the CW microwave output. Does not start physical signal output, see also
        "cw_on".

        @param float frequency: frequency to set in Hz
        @param float power: power to set in dBm
        """
        raise NotImplementedError

    @abstractmethod
    def cw_on(self):
        """Switches on preconfigured cw microwave output, see also "set_cw".

        Must return AFTER the output is actually active.
        """
        raise NotImplementedError

    @abstractmethod
    def configure_scan(self, power, frequencies, mode, sample_rate):
        """
        """
        raise NotImplementedError

    @abstractmethod
    def start_scan(self):
        """Switches on the preconfigured microwave scanning, see also "configure_scan".

        Must return AFTER the output is actually active (and can receive triggers for example).
        """
        raise NotImplementedError

    @abstractmethod
    def reset_scan(self):
        """Reset currently running scan and return to start frequency.
        Does not need to stop and restart the microwave output if the device allows soft scan reset.
        """
        raise NotImplementedError

    # ToDo: Think about if the logic should handle trigger settings and expand the interface if so.
    #  But I would argue the trigger config is something static and hard-wired for a specific setup,
    #  so it should be configurable via config and not handled by logic at runtime.


class MicrowaveConstraints:
    """A container to hold all constraints for microwave sources.
    """
    def __init__(self, power_limits, frequency_limits, scan_size_limits, sample_rate_limits,
                 scan_modes):
        """
        @param float[2] power_limits: Allowed min and max power
        @param float[2] frequency_limits: Allowed min and max frequency
        @param int[2] scan_size_limits: Allowed min and max number of samples for scanning
        @param float[2] sample_rate_limits: Allowed min and max scan sample rate (in Hz)
        @param SamplingOutputMode[] scan_modes: Allowed scan mode Enums
        """
        assert len(power_limits) == 2, 'power_limits must be iterable of length 2 (min, max)'
        assert len(frequency_limits) == 2, \
            'frequency_limits must be iterable of length 2 (min, max)'
        assert len(scan_size_limits) == 2, \
            'scan_size_limits must be iterable of length 2 (min, max)'
        assert len(sample_rate_limits) == 2, \
            'sample_rate_limits must be iterable of length 2 (min, max)'
        assert all(isinstance(mode, SamplingOutputMode) for mode in scan_modes), \
            'scan_modes must be iterable containing only qudi.core.enums.SamplingOutputMode Enums'

        tmp = [int(lim) for lim in scan_size_limits]
        self._scan_size_limits = (min(tmp), max(tmp))
        self._sample_rate_limits = (min(sample_rate_limits), max(sample_rate_limits))
        self._scan_modes = frozenset(scan_modes)
        self._power_limits = (min(power_limits), max(power_limits))
        self._frequency_limits = (min(frequency_limits), max(frequency_limits))

    @property
    def scan_size_limits(self):
        return self._scan_size_limits

    @property
    def min_scan_size(self):
        return self._scan_size_limits[0]

    @property
    def max_scan_size(self):
        return self._scan_size_limits[1]

    @property
    def sample_rate_limits(self):
        return self._sample_rate_limits

    @property
    def min_sample_rate(self):
        return self._sample_rate_limits[0]

    @property
    def max_sample_rate(self):
        return self._sample_rate_limits[1]

    @property
    def power_limits(self):
        return self._power_limits

    @property
    def min_power(self):
        return self._power_limits[0]

    @property
    def max_power(self):
        return self._power_limits[1]

    @property
    def frequency_limits(self):
        return self._frequency_limits

    @property
    def min_frequency(self):
        return self._frequency_limits[0]

    @property
    def max_frequency(self):
        return self._frequency_limits[1]

    @property
    def scan_modes(self):
        return self._scan_modes

    def frequency_in_range(self, value):
        return in_range(value, *self._frequency_limits)

    def power_in_range(self, value):
        return in_range(value, *self._power_limits)

    def scan_size_in_range(self, value):
        return in_range(value, *self._scan_size_limits)

    def sample_rate_in_range(self, value):
        return in_range(value, *self._sample_rate_limits)

    def mode_supported(self, mode):
        return mode in self._scan_modes
