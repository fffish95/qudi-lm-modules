# -*- coding: utf-8 -*-
# NOTE: This module was written or modified by fffish
# (https://github.com/fffish95/qudi-lm-modules) and remains subject to the GNU
# license terms stated below (or, if none are stated in this file, to the GNU
# General Public License under which Qudi is distributed).

"""
Qudi hardware module for an Attocube-style nanopositioner that is driven over
a plain TCP socket (the device exposes a Telnet-like ASCII console on a
configurable port, password-protected).

This replaces the old, standalone
``hardware/local/ps5controller/nanopositioner_controller.py`` script: the raw
socket implementation below works the same way on Windows and Linux, whereas
``telnetlib`` (used by the old script) was removed from the Python standard
library in Python 3.13.
"""

import socket
import time

from qudi.core.configoption import ConfigOption
from qudi.core.module import Base
from qudi.util.mutex import Mutex


class NanopositionerController(Base):
    """ Hardware module for an Attocube-style nanopositioner (x/y/z axes),
    talked to over a raw TCP socket.

    Example config for copy-paste:

    nanopositioner:
        module.Class: 'local.nanopositioner_controller.NanopositionerController'
        options:
            ip: '10.140.0.212'
            port: 7231
            password: '123456'
            timeout: 1.0
            x_axis: 5
            y_axis: 6
            z_axis: 4
    """

    _ip = ConfigOption(name='ip', missing='error')
    _port = ConfigOption(name='port', default=7231, missing='nothing')
    _password = ConfigOption(name='password', default='123456', missing='nothing')
    _timeout = ConfigOption(name='timeout', default=1.0, missing='nothing')
    _x_axis = ConfigOption(name='x_axis', default=5, missing='nothing')
    _y_axis = ConfigOption(name='y_axis', default=6, missing='nothing')
    _z_axis = ConfigOption(name='z_axis', default=4, missing='nothing')

    _AUTH_PROMPT = b'Authorization code:'

    def on_activate(self):
        self._lock = Mutex()
        self._socket = None
        self._modules = {
            'x': 'm{0:d}'.format(self._x_axis).encode('ascii'),
            'y': 'm{0:d}'.format(self._y_axis).encode('ascii'),
            'z': 'm{0:d}'.format(self._z_axis).encode('ascii'),
        }
        try:
            self._connect()
        except Exception as e:
            self.log.error(f'Could not connect to nanopositioner at {self._ip}:{self._port}: {e}')

    def on_deactivate(self):
        self._disconnect()

    def _connect(self):
        """ Open the socket and complete the password handshake. """
        with self._lock:
            self._disconnect_unlocked()
            self._socket = socket.create_connection((self._ip, self._port), timeout=self._timeout)
            self._read_until(self._AUTH_PROMPT)
            self._socket.sendall(f'{self._password}\n'.encode('ascii'))

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

    def _read_until(self, expected, max_wait=None):
        """ Read from the socket until the expected byte string shows up (or
        the timeout expires); tolerant of the prompt never arriving so that a
        misbehaving device does not deadlock the caller.
        """
        deadline = time.time() + (self._timeout if max_wait is None else max_wait)
        buffer = b''
        while expected not in buffer and time.time() < deadline:
            try:
                chunk = self._socket.recv(1024)
            except socket.timeout:
                break
            if not chunk:
                break
            buffer += chunk
        return buffer

    def _send(self, command):
        """ Send a raw command, reconnecting first if the connection dropped. """
        with self._lock:
            if self._socket is None:
                try:
                    self._connect_unlocked_from_send()
                except Exception as e:
                    self.log.error(f'Nanopositioner reconnect failed: {e}')
                    return
            try:
                self._socket.sendall(command)
            except OSError as e:
                self.log.error(f'Nanopositioner send failed ({e}); will reconnect on next command.')
                self._disconnect_unlocked()

    def _connect_unlocked_from_send(self):
        """ Reconnect helper used from within _send() where the lock is already held. """
        self._socket = socket.create_connection((self._ip, self._port), timeout=self._timeout)
        self._read_until(self._AUTH_PROMPT)
        self._socket.sendall(f'{self._password}\n'.encode('ascii'))

    def move_steps(self, axis, steps):
        """ Move the given axis ('x', 'y' or 'z') by a signed number of steps.
        Positive is UP, negative is DOWN, matching the original script.
        """
        if steps == 0:
            return
        module = self._modules.get(axis)
        if module is None:
            self.log.error(f'Unknown nanopositioner axis "{axis}".')
            return
        direction = b'UP' if steps > 0 else b'DOWN'
        count = str(abs(int(steps))).encode('ascii')
        self._send(module + b':step(' + direction + b',' + count + b')\n')

    def stop_all(self):
        """ Emergency stop: halt every axis and ground its output stage. """
        for module in self._modules.values():
            self._send(module + b':stop()\n')
        for module in self._modules.values():
            self._send(module + b'.mode = GND\n')
