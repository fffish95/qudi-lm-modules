# -*- coding: utf-8 -*-

"""
This file contains the Qudi hardware module for the Windfreak SynthHDPro microwave source.

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

import pyvisa

from qudi.util.mutex import Mutex
from qudi.core.configoption import ConfigOption
from qudi.interface.microwave_interface import MicrowaveInterface, MicrowaveConstraints
from qudi.util.enums import SamplingOutputMode


class MicrowaveSynthHDPro(MicrowaveInterface):
    """ Hardware class to controls a SynthHD Pro.

    Important note: This MW source is low active. Using it together with trigger signals make sure
    to use falling trigger edges. For the ni_x_series_finite_sampling_input there is the
    `trigger_edge` option. You can change the default value (RISING) to FALLING.

    Example config for copy-paste:

    mw_source_synthhd:
        module.Class: 'microwave.mw_source_windfreak_synthhdpro.MicrowaveSynthHDPro'
        options:
            serial_port: 'COM3'
            comm_timeout: 10  # in seconds
            output_channel: 0  # either 0 or 1
    """

    _serial_port = ConfigOption('serial_port', missing='error')
    _comm_timeout = ConfigOption('comm_timeout', default=10, missing='warn')
    _output_channel = ConfigOption('output_channel', 0, missing='error')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._thread_lock = Mutex()
        self._rm = None
        self._device = None
        self._model = ''
        self._constraints = None
        self._scan_power = -20
        self._scan_frequencies = None
        self._scan_sample_rate = 0.
        self._in_cw_mode = True

    def on_activate(self):
        """ Initialisation performed during activation of the module.
        """
        self._connect()
        self._model = self._device.query('+')
        # Generate constraints
        self._constraints = MicrowaveConstraints(
            power_limits=(-50, 18),
            frequency_limits=(54e6, 14e9),
            scan_size_limits=(2, 100),
            sample_rate_limits=(0.1, 1e3/4),
            scan_modes=(SamplingOutputMode.EQUIDISTANT_SWEEP,)
        )
        self._close()
        self._scan_power = -20
        self._scan_frequencies = None
        self._scan_sample_rate = self._constraints.max_sample_rate
        self._in_cw_mode = True


    def on_deactivate(self):
        """ Cleanup performed during deactivation of the module.
        """
        self.off()

    @property
    def constraints(self):
        return self._constraints

    @property
    def is_scanning(self):
        """Read-Only boolean flag indicating if a scan is running at the moment. Can be used together with
        module_state() to determine if the currently running microwave output is a scan or CW.
        Should return False if module_state() is 'idle'.

        @return bool: Flag indicating if a scan is running (True) or not (False)
        """
        with self._thread_lock:
            return (self.module_state() != 'idle') and not self._in_cw_mode

    @property
    def cw_power(self):
        """The CW microwave power in dBm. Must implement setter as well.

        @return float: The currently set CW microwave power in dBm.
        """
        with self._thread_lock:
            self._connect()
            # query the power in dBm
            w = self._device.query('W?')
            # close the connection again
            self._close()
            return float(w)

    @property
    def cw_frequency(self):
        """The CW microwave frequency in Hz. Must implement setter as well.

        @return float: The currently set CW microwave frequency in Hz.
        """
        with self._thread_lock:
            self._connect()
            f = self._device.query('f?')
            self._close()
            return float(f) * 1e6

    @property
    def scan_power(self):
        """The microwave power in dBm used for scanning. Must implement setter as well.

        @return float: The currently set scanning microwave power in dBm
        """
        with self._thread_lock:
            return self._scan_power

    @property
    def scan_frequencies(self):
        """The microwave frequencies used for scanning. Must implement setter as well.

        In case of scan_mode == SamplingOutputMode.JUMP_LIST, this will be a 1D numpy array.
        In case of scan_mode == SamplingOutputMode.EQUIDISTANT_SWEEP, this will be a tuple
        containing 3 values (freq_begin, freq_end, number_of_samples).
        If no frequency scan has been specified, return None.

        @return float[]: The currently set scanning frequencies. None if not set.
        """
        with self._thread_lock:
            return self._scan_frequencies

    @property
    def scan_mode(self):
        """Scan mode Enum. Must implement setter as well.

        @return SamplingOutputMode: The currently set scan mode Enum
        """
        with self._thread_lock:
            return SamplingOutputMode.EQUIDISTANT_SWEEP

    @property
    def scan_sample_rate(self):
        """Read-only property returning the currently configured scan sample rate in Hz.

        @return float: The currently set scan sample rate in Hz
        """
        with self._thread_lock:
            return self._scan_sample_rate

    def set_cw(self, frequency, power):
        """Configure the CW microwave output. Does not start physical signal output, see also
        "cw_on".

        @param float frequency: frequency to set in Hz
        @param float power: power to set in dBm
        """
        with self._thread_lock:
            if self.module_state() != 'idle':
                raise RuntimeError('Unable to set CW parameters. Microwave output active.')
            self._assert_cw_parameters_args(frequency, power)
            self._connect()
            self._device.write('X0')
            self._device.write('c1')
            # trigger mode: software
            self._device.write('w0')
            self._device.write(f'W{power:2.3f}')
            self._device.write(f'[{power:2.3f}')
            self._device.write(f']{power:2.3f}')
            self._device.write(f'f{frequency / 1e6:5.7f}')
            self._device.write(f'l{frequency / 1e6:5.7f}')
            self._device.write(f'u{frequency / 1e6:5.7f}')
            self._close()

    def configure_scan(self, power, frequencies, mode, sample_rate):
        """
        """
        with self._thread_lock:
            # Sanity checks
            if self.module_state() != 'idle':
                raise RuntimeError('Unable to configure frequency scan. Microwave output active.')
            self._assert_scan_configuration_args(power, frequencies, mode, sample_rate)

            # configure scan according to scan mode
            self._scan_power = power
            self._scan_frequencies = tuple(frequencies)
            self._write_sweep()
            self._connect()
            self._device.write(f't{1000 * 2 / sample_rate:f}') # sweep step trigger will trigger one step in a linear sweep or list weep when pulled low. use step time to debounce and make sure step time is longer than your trigger pulse duration to avoid two steps in one pulse
            self._scan_sample_rate = sample_rate

            self.log.debug(f'Configured scan with: '
                           f'scan_power = {self._scan_power}, '
                           f'len(scan_frequencies) = {len(self._scan_frequencies)}, '
                           f'scan_sample_rate = {self._scan_sample_rate}')
            self._close()

    def off(self):
        """Switches off any microwave output (both scan and CW).
        Must return AFTER the device has actually stopped.
        """
        with self._thread_lock:
            if self.module_state() != 'idle':
                self._connect()
                # disable sweep mode
                self._device.write('g0')
                # set trigger source to software
                self._device.write('w0')
                # turn off everything for the current channel
                self._device.write('E0r0h0')
                self._close()
                self.module_state.unlock()

    def cw_on(self):
        """ Switches on cw microwave output.

        Must return AFTER the output is actually active.
        """
        with self._thread_lock:
            if self.module_state() != 'idle':
                if self._in_cw_mode:
                    return
                raise RuntimeError(
                    'Unable to start CW microwave output. Microwave output is currently active.'
                )

            self._in_cw_mode = True
            self._connect()
            self._device.write('E1r1h1')
            # enable sweep mode and set to start frequency
            self._device.write('g1')
            self._close()
            self.module_state.lock()

    def start_scan(self):
        """Switches on the microwave scanning.

        Must return AFTER the output is actually active (and can receive triggers for example).
        """
        with self._thread_lock:
            if self.module_state() != 'idle':
                if not self._in_cw_mode:
                    return
                raise RuntimeError('Unable to start frequency scan. CW microwave output is active.')
            assert self._scan_frequencies is not None, \
                'No scan_frequencies set. Unable to start scan.'

            self._in_cw_mode = False
            self._connect()
            self._device.write('E1r1h1')
            # enable sweep mode and set to start frequency
            self._device.write('g1')
            self._close()
            self.module_state.lock()

    def reset_scan(self):
        """Reset currently running scan and return to start frequency.
        Does not need to stop and restart the microwave output if the device allows soft scan reset.
        """
        with self._thread_lock:
            if self.module_state() == 'idle':
                return
            if self._in_cw_mode:
                raise RuntimeError('Can not reset frequency scan. CW microwave output active.')

            self._connect()
            # enable sweep mode and set to start frequency
            self._device.write('g1')
            self._close()

    def _write_sweep(self):
        start, stop, points = self._scan_frequencies
        step = (stop - start) / (points - 1)
        self._connect()
        # sweep mode: linear sweep, non-continuous
        self._device.write('X0')
        self._device.write('c0')

        # trigger mode: single step
        self._device.write('w2')

        # sweep direction
        if stop >= start:
            self._device.write('^1')
        else:
            self._device.write('^0')

        # sweep lower and upper frequency and steps
        self._device.write(f'l{start / 1e6:5.7f}')
        self._device.write(f'u{stop / 1e6:5.7f}')
        self._device.write(f's{step / 1e6:5.7f}')

        # set power
        self._device.write(f'W{self._scan_power:2.3f}')
        # set sweep lower end power
        self._device.write(f'[{self._scan_power:2.3f}')
        # set sweep upper end power
        self._device.write(f']{self._scan_power:2.3f}')
        self._close()

    def _connect(self):
        """Connect to the microwave source."""
        self._rm = pyvisa.ResourceManager()
        self._device = self._rm.open_resource(self._serial_port,
                                              baud_rate=9600,
                                              read_termination='\n',
                                              write_termination='\n',
                                              timeout=int(self._comm_timeout * 1000))
        self._device.write(f'C{self._output_channel}')
        
    def _close(self):
        if self._device is not None:
            self._device.close()
            self._device = None
        if self._rm is not None:
            self._rm.close()
            self._rm = None