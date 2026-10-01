# -*- coding: utf-8 -*-
# NOTE: This module was written or modified by fffish
# (https://github.com/fffish95/qudi-lm-modules) and remains subject to the GNU
# license terms stated below (or, if none are stated in this file, to the GNU
# General Public License under which Qudi is distributed).

"""
Shared logic module that reads a PS5 (or similar) game controller with
``pygame`` and drives either a :class:`NanopositionerController` or a
:class:`PicomotorController` hardware module, whichever is currently
selected as the "active device".

This replaces the two old, standalone scripts
``hardware/local/ps5controller/nanopositioner_controller.py`` and
``hardware/local/ps5controller/picomotor_controller.py``: instead of
``evdev`` (Linux-only) it uses ``pygame.joystick``, which works the same way
on Windows and Linux.

Because the exact pygame button/axis/hat indices for a given controller
depend on the OS, driver and connection type (USB vs. Bluetooth), every
mapping used below is a ``ConfigOption`` with a documented default. Use
``start_diagnostic_mode()`` (wired up to the "Diagnostic mode" GUI action)
to print raw controller events to the on-screen terminal without moving any
hardware, so the real indices can be read off and copied into the config
file.
"""

import pygame
import time

from PySide2 import QtCore
from qudi.core.connector import Connector
from qudi.core.configoption import ConfigOption
from qudi.core.module import LogicBase
from qudi.util.mutex import Mutex


class JoystickWorker(QtCore.QObject):
    """ Polls pygame joystick events on its own thread so the logic module's
    own (already dedicated) thread is never blocked waiting on the
    controller, mirroring the HardwarePull worker pattern used elsewhere in
    this codebase (see e.g. camera_logic.py).
    """

    sig_message = QtCore.Signal(str)

    def __init__(self, parentclass):
        super().__init__()
        self._parentclass = parentclass
        self._timer = None
        self._joystick = None
        self._emergency_tap_time = 0

    def handle_timer(self, state_change):
        """ Start or stop the polling timer.

        @param bool state_change: True starts polling, False stops it.
        """
        if state_change:
            if not pygame.get_init():
                pygame.init()
            if not pygame.joystick.get_init():
                pygame.joystick.init()
            self._timer = QtCore.QTimer()
            self._timer.timeout.connect(self._poll)
            self._timer.start(self._parentclass._poll_interval_ms)
        else:
            if self._timer is not None:
                self._timer.stop()
                self._timer = None

    def _ensure_joystick(self):
        if self._joystick is not None:
            return True
        pygame.joystick.quit()
        pygame.joystick.init()
        if pygame.joystick.get_count() == 0:
            return False
        self._joystick = pygame.joystick.Joystick(0)
        self._joystick.init()
        self.sig_message.emit(f'Connected to controller: {self._joystick.get_name()}')
        return True

    def _poll(self):
        if not self._ensure_joystick():
            return
        pygame.event.pump()
        events = pygame.event.get()
        if not events:
            return

        p = self._parentclass
        if p.diagnostic_mode:
            for event in events:
                self.sig_message.emit(f'[diagnostic] {event}')
            return

        # Throttle down to at most one button event and one axis/hat event
        # per poll tick, mirroring the original scripts' behaviour of only
        # ever acting on the last one or two queued events.
        last_button = None
        last_axis_or_hat = None
        for event in events:
            if event.type == pygame.JOYBUTTONDOWN:
                if self._check_emergency(event):
                    self.sig_message.emit('EMERGENCY STOP (double-tap detected)')
                    p.emergency_stop()
                last_button = event
            elif event.type in (pygame.JOYHATMOTION, pygame.JOYAXISMOTION):
                last_axis_or_hat = event

        if last_button is not None:
            self._dispatch_button(last_button)
        if last_axis_or_hat is not None:
            self._dispatch_axis_or_hat(last_axis_or_hat)

    def _check_emergency(self, event):
        p = self._parentclass
        if event.button != p._button_map.get('playstation', -1):
            return False
        now = int(round(time.time() * 1000))
        previous_tap = self._emergency_tap_time
        self._emergency_tap_time = now
        return now < previous_tap + p._emergency_max_delay_ms

    def _dispatch_button(self, event):
        p = self._parentclass
        button_map = p._button_map
        if event.button == button_map.get('share', -2):
            p._advance_step_size()
            self.sig_message.emit(f'step size = {p.step_size}')
            return

        device = p.active_hardware()
        if device is None:
            return

        if p.active_device == 'nanopositioner':
            if event.button == button_map.get('l1', -2):
                device.move_steps('z', 1)
                self.sig_message.emit('nanopositioner: z +1')
            elif event.button == button_map.get('r1', -2):
                device.move_steps('z', -1)
                self.sig_message.emit('nanopositioner: z -1')
        elif p.active_device == 'picomotor':
            if event.button == button_map.get('square', -2):
                device.move_steps('x2', 1)
                self.sig_message.emit('picomotor: x2 +1')
            elif event.button == button_map.get('circle', -2):
                device.move_steps('x2', -1)
                self.sig_message.emit('picomotor: x2 -1')
            elif event.button == button_map.get('triangle', -2):
                device.move_steps('y2', 1)
                self.sig_message.emit('picomotor: y2 +1')
            elif event.button == button_map.get('cross', -2):
                device.move_steps('y2', -1)
                self.sig_message.emit('picomotor: y2 -1')

    def _dispatch_axis_or_hat(self, event):
        p = self._parentclass
        device = p.active_hardware()

        if event.type == pygame.JOYHATMOTION and event.hat == p._dpad_hat_index:
            x, y = event.value
            if p._dpad_invert_x:
                x = -x
            if p._dpad_invert_y:
                y = -y
            if device is None:
                return
            if p.active_device == 'nanopositioner':
                if x:
                    device.move_steps('x', x * p.step_size)
                    self.sig_message.emit(f'nanopositioner: x {"+" if x > 0 else "-"}{p.step_size}')
                if y:
                    device.move_steps('y', y * p.step_size)
                    self.sig_message.emit(f'nanopositioner: y {"+" if y > 0 else "-"}{p.step_size}')
            elif p.active_device == 'picomotor':
                if x:
                    device.move_steps('x1', x * p.step_size)
                    self.sig_message.emit(f'picomotor: x1 {"+" if x > 0 else "-"}{p.step_size}')
                if y:
                    device.move_steps('y1', y * p.step_size)
                    self.sig_message.emit(f'picomotor: y1 {"+" if y > 0 else "-"}{p.step_size}')
            return

        if event.type == pygame.JOYAXISMOTION and p.active_device == 'nanopositioner':
            trigger_axes = p._trigger_axes
            if event.axis == trigger_axes.get('l2', -1):
                magnitude = int(round((event.value + 1) * 127.5))
                if magnitude > p._trigger_blind:
                    device.move_steps('z', magnitude)
                    self.sig_message.emit(f'nanopositioner: z +{magnitude}')
            elif event.axis == trigger_axes.get('r2', -1):
                magnitude = int(round((event.value + 1) * 127.5))
                if magnitude > p._trigger_blind:
                    device.move_steps('z', -magnitude)
                    self.sig_message.emit(f'nanopositioner: z -{magnitude}')


class JoystickControllerLogic(LogicBase):
    """ Reads a PS5-style game controller and drives either a nanopositioner
    or a picomotor hardware module, whichever is selected as "active
    device" from the GUI.

    Example config for copy-paste:

    joystickcontrollerlogic:
        module.Class: 'local.joystick_controller_logic.JoystickControllerLogic'
        connect:
            nanopositioner: 'nanopositioner'
            picomotor: 'picomotor'
        options:
            step_sizes: [1, 10, 40, 200]
            poll_interval: 0.15
            trigger_blind: 20
            emergency_max_delay: 1.0
            dpad_hat_index: 0
            dpad_invert_x: False
            dpad_invert_y: True
            button_map:
                square: 2
                circle: 1
                triangle: 3
                cross: 0
                l1: 9
                r1: 10
                share: 8
                playstation: 12
            trigger_axes:
                l2: 4
                r2: 5
    """

    nanopositioner = Connector(name='nanopositioner', interface='NanopositionerController',
                                optional=True)
    picomotor = Connector(name='picomotor', interface='PicomotorController', optional=True)

    _step_sizes = ConfigOption(name='step_sizes', default=[1, 10, 40, 200], missing='nothing')
    _poll_interval = ConfigOption(name='poll_interval', default=0.15, missing='nothing')
    _trigger_blind = ConfigOption(name='trigger_blind', default=20, missing='nothing')
    _emergency_max_delay = ConfigOption(name='emergency_max_delay', default=1.0, missing='nothing')
    _dpad_hat_index = ConfigOption(name='dpad_hat_index', default=0, missing='nothing')
    _dpad_invert_x = ConfigOption(name='dpad_invert_x', default=False, missing='nothing')
    _dpad_invert_y = ConfigOption(name='dpad_invert_y', default=True, missing='nothing')
    _button_map = ConfigOption(name='button_map',
                                default={'square': 2, 'circle': 1, 'triangle': 3, 'cross': 0,
                                         'l1': 9, 'r1': 10, 'share': 8, 'playstation': 12},
                                missing='nothing')
    _trigger_axes = ConfigOption(name='trigger_axes', default={'l2': 4, 'r2': 5},
                                  missing='nothing')

    sig_handle_timer = QtCore.Signal(bool)
    sigMessage = QtCore.Signal(str)
    sigStepSizeChanged = QtCore.Signal(int)
    sigActiveDeviceChanged = QtCore.Signal(str)
    sigPollingChanged = QtCore.Signal(bool)

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)
        self._thread_lock = Mutex()
        self._step_index = 0
        self.active_device = 'nanopositioner'
        self.diagnostic_mode = False
        self._polling = False

    def on_activate(self):
        self._poll_interval_ms = max(1, int(round(self._poll_interval * 1000)))
        self._emergency_max_delay_ms = max(1, int(round(self._emergency_max_delay * 1000)))
        self.worker_thread = QtCore.QThread()
        self._worker = JoystickWorker(self)
        self._worker.moveToThread(self.worker_thread)
        self.sig_handle_timer.connect(self._worker.handle_timer)
        self._worker.sig_message.connect(self._relay_message, QtCore.Qt.QueuedConnection)
        self.worker_thread.start()

    def on_deactivate(self):
        if self._polling:
            self.stop_polling()
        self.worker_thread.quit()
        self.worker_thread.wait()
        self.sig_handle_timer.disconnect()
        self._worker.sig_message.disconnect()

    def _relay_message(self, text):
        self.sigMessage.emit(text)

    @property
    def step_size(self):
        return self._step_sizes[self._step_index]

    def _advance_step_size(self):
        with self._thread_lock:
            self._step_index = (self._step_index + 1) % len(self._step_sizes)
        self.sigStepSizeChanged.emit(self.step_size)

    def active_hardware(self):
        """ Return the currently active hardware module instance, or None if
        it is not connected in this config. """
        if self.active_device == 'nanopositioner':
            return self.nanopositioner()
        elif self.active_device == 'picomotor':
            return self.picomotor()
        return None

    def get_available_devices(self):
        """ Return the list of device names that actually have a hardware
        module connected in this config. """
        devices = []
        if self.nanopositioner.is_connected:
            devices.append('nanopositioner')
        if self.picomotor.is_connected:
            devices.append('picomotor')
        return devices

    def set_active_device(self, device):
        """ Switch which hardware module the joystick drives. """
        if device not in ('nanopositioner', 'picomotor'):
            self.log.error(f'Unknown device "{device}".')
            return
        self.active_device = device
        self.sigMessage.emit(f'Active device: {device}')
        self.sigActiveDeviceChanged.emit(device)

    def start_polling(self):
        with self._thread_lock:
            if self._polling:
                return
            self._polling = True
        self.sig_handle_timer.emit(True)
        self.sigMessage.emit('Polling started.')
        self.sigPollingChanged.emit(True)

    def stop_polling(self):
        with self._thread_lock:
            if not self._polling:
                return
            self._polling = False
        self.sig_handle_timer.emit(False)
        self.sigMessage.emit('Polling stopped.')
        self.sigPollingChanged.emit(False)

    def set_diagnostic_mode(self, enabled):
        """ When enabled, raw controller events are logged to the terminal
        instead of being translated into hardware moves. Use this to work
        out the real button/axis/hat indices for your controller and OS. """
        self.diagnostic_mode = bool(enabled)
        self.sigMessage.emit(f'Diagnostic mode {"enabled" if enabled else "disabled"}.')

    def emergency_stop(self):
        """ Immediately stop every connected hardware module. Safe to call
        directly (not queued) from the GUI thread at any time. """
        with self._thread_lock:
            for connector in (self.nanopositioner, self.picomotor):
                device = connector()
                if device is not None:
                    try:
                        device.stop_all()
                    except Exception as e:
                        self.log.error(f'Error while stopping device: {e}')
        self.sigMessage.emit('Emergency stop executed.')
