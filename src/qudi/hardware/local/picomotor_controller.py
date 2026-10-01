# -*- coding: utf-8 -*-
# NOTE: This module was written or modified by fffish
# (https://github.com/fffish95/qudi-lm-modules) and remains subject to the GNU
# license terms stated below (or, if none are stated in this file, to the GNU
# General Public License under which Qudi is distributed).

"""
Qudi hardware module for a Newport picomotor controller (4 axes: x1/y1/x2/y2)
talked to over a plain TCP socket.

This replaces the old, standalone
``hardware/local/ps5controller/picomotor_controller.py`` script: the raw
socket implementation below works the same way on Windows and Linux, whereas
``telnetlib`` (used by the old script) was removed from the Python standard
library in Python 3.13.

The old script's multi-step relative move commands (``mov_nx1_up`` and
friends) also appended a stray ``)`` byte before the terminating ``\\r``
(e.g. ``b"1PR10)\\r"``), which does not match the Newport ``PR<n>`` command
syntax used correctly everywhere else in that file. That bug is fixed here.
"""

import socket

from qudi.core.configoption import ConfigOption
from qudi.core.module import Base
from qudi.util.mutex import Mutex


class PicomotorController(Base):
    """ Hardware module for a Newport picomotor controller with 4 axes
    (x1/y1/x2/y2), talked to over a raw TCP socket.

    Example config for copy-paste:

    picomotor:
        module.Class: 'local.picomotor_controller.PicomotorController'
        options:
            ip: '10.140.0.213'
            port: 23
            timeout: 1.0
            x1_axis: 1
            y1_axis: 2
            x2_axis: 3
            y2_axis: 4
    """

    _ip = ConfigOption(name='ip', missing='error')
    _port = ConfigOption(name='port', default=23, missing='nothing')
    _timeout = ConfigOption(name='timeout', default=1.0, missing='nothing')
    _x1_axis = ConfigOption(name='x1_axis', default=1, missing='nothing')
    _y1_axis = ConfigOption(name='y1_axis', default=2, missing='nothing')
    _x2_axis = ConfigOption(name='x2_axis', default=3, missing='nothing')
    _y2_axis = ConfigOption(name='y2_axis', default=4, missing='nothing')

    def on_activate(self):
        self._lock = Mutex()
        self._socket = None
        self._modules = {
            'x1': str(self._x1_axis).encode('ascii'),
            'y1': str(self._y1_axis).encode('ascii'),
            'x2': str(self._x2_axis).encode('ascii'),
            'y2': str(self._y2_axis).encode('ascii'),
        }
        try:
            self._connect()
        except Exception as e:
            self.log.error(f'Could not connect to picomotor at {self._ip}:{self._port}: {e}')

    def on_deactivate(self):
        self._disconnect()

    def _connect(self):
        with self._lock:
            self._disconnect_unlocked()
            self._socket = socket.create_connection((self._ip, self._port), timeout=self._timeout)

    def _disconnect(self):
        with self._lock:
            self._disconnect_unlocked()

    def _disconnect_unlocked(self):
        if self._socket is not None:
            try:
                self._socket.close()
            except OSError:
                pass
            self._socket = None

    def _send(self, command):
        """ Send a raw command, reconnecting first if the connection dropped. """
        with self._lock:
            if self._socket is None:
                try:
                    self._socket = socket.create_connection((self._ip, self._port),
                                                             timeout=self._timeout)
                except Exception as e:
                    self.log.error(f'Picomotor reconnect failed: {e}')
                    return
            try:
                self._socket.sendall(command)
            except OSError as e:
                self.log.error(f'Picomotor send failed ({e}); will reconnect on next command.')
                self._disconnect_unlocked()

    def move_steps(self, axis, steps):
        """ Move the given axis ('x1', 'y1', 'x2' or 'y2') by a signed
        number of relative steps.
        """
        if steps == 0:
            return
        module = self._modules.get(axis)
        if module is None:
            self.log.error(f'Unknown picomotor axis "{axis}".')
            return
        steps = int(steps)
        self._send(module + b'PR' + str(steps).encode('ascii') + b'\r')

    def stop_all(self):
        """ Emergency stop: halt every axis of the controller. """
        self._send(b'ST\r')
