# -*- coding: utf-8 -*-
# NOTE: This module was written or modified by fffish
# (https://github.com/fffish95/qudi-lm-modules) and remains subject to the GNU
# license terms stated below (or, if none are stated in this file, to the GNU
# General Public License under which Qudi is distributed).

"""
Shared logic module that reads a PS5 (or similar) game controller with
``pygame`` and drives a :class:`NanopositionerController`, a :class:`PicomotorController`
or an ``NF8752Logic`` module, whichever is currently selected as the
"active device".

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

import os
import time

# SDL discards joystick input while none of *its* windows has focus. pygame
# never owns a window inside qudi, so without this hint every button press is
# silently dropped. Must be set before pygame/SDL is initialised.
os.environ.setdefault('SDL_JOYSTICK_ALLOW_BACKGROUND_EVENTS', '1')

import pygame

from PySide2 import QtCore
from qudi.core.connector import Connector
from qudi.core.configoption import ConfigOption
from qudi.core.module import LogicBase
from qudi.util.mutex import Mutex


# D-pad direction as (dx, dy): right/up are positive.
_DPAD_BUTTONS = {'dpad_up': (0, 1), 'dpad_down': (0, -1),
                 'dpad_left': (-1, 0), 'dpad_right': (1, 0)}


class NF8752Adapter:
    """ Gives the NewFocus 8752 picomotor logic (NF8752Logic) the same
    move_steps()/stop_all() interface as the two hardware modules. """

    def __init__(self, nf8752, velocity, acceleration):
        self._nf8752 = nf8752
        self._velocity = velocity
        self._acceleration = acceleration

    def move_steps(self, axis, steps):
        # Blocks until the move has finished (NF8752Logic.move_rel waits for it),
        # because the 8752 cannot switch channels while a motor is still moving.
        self._nf8752.move_rel(steps, axis, vel=self._velocity, acc=self._acceleration)

    def stop_all(self):
        self._nf8752.halt()


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

        The joystick subsystem is initialised only once and the controller is
        kept open across stop/start: re-initialising SDL's joystick subsystem
        makes it re-discover the controller asynchronously, so it would not be
        found right after a restart.

        @param bool state_change: True starts polling, False stops it.
        """
        if state_change:
            if not pygame.get_init():
                pygame.init()
            if not pygame.joystick.get_init():
                pygame.joystick.init()
            # Handle (dis)connects that happened while stopped, but drop any
            # button/axis input queued meanwhile so stale presses never move hardware.
            self._handle_device_events(pygame.event.get())
            if self._open_joystick():
                self.sig_message.emit(f'Using controller: {self._joystick.get_name()}')
            else:
                self.sig_message.emit('No controller found yet, waiting for one to be connected...')
            self._timer = QtCore.QTimer()
            self._timer.timeout.connect(self._poll)
            self._timer.start(self._parentclass._poll_interval_ms)
        else:
            if self._timer is not None:
                self._timer.stop()
                self._timer = None

    def _open_joystick(self):
        """ Open the first available controller if none is open. Never
        re-initialises the joystick subsystem. """
        if self._joystick is not None:
            return True
        if pygame.joystick.get_count() == 0:
            return False
        self._joystick = pygame.joystick.Joystick(0)
        self._joystick.init()
        self.sig_message.emit(
            f'Connected to controller: {self._joystick.get_name()} '
            f'({self._joystick.get_numbuttons()} buttons, {self._joystick.get_numaxes()} axes, '
            f'{self._joystick.get_numhats()} hats)')
        return True

    def _handle_device_events(self, events):
        """ Track controller (dis)connects; returns the remaining input events. """
        remaining = []
        for event in events:
            if event.type == pygame.JOYDEVICEREMOVED:
                if (self._joystick is not None
                        and event.instance_id == self._joystick.get_instance_id()):
                    self._joystick = None
                    self.sig_message.emit('Controller disconnected.')
            elif event.type == pygame.JOYDEVICEADDED:
                self._open_joystick()
            else:
                remaining.append(event)
        return remaining

    def _poll(self):
        events = self._handle_device_events(pygame.event.get())
        if self._joystick is None:
            self._open_joystick()
            return
        # Ignore input from any other controller that may be plugged in.
        own_id = self._joystick.get_instance_id()
        events = [e for e in events if getattr(e, 'instance_id', own_id) == own_id]

        p = self._parentclass
        last_hat = None
        last_axis = dict()
        for event in events:
            if p.diagnostic_mode:
                if event.type in (pygame.JOYBUTTONDOWN, pygame.JOYHATMOTION):
                    self.sig_message.emit(f'[diagnostic] {pygame.event.event_name(event.type)} '
                                          f'{event.dict}')
                elif event.type == pygame.JOYAXISMOTION and abs(event.value) > 0.5:
                    self.sig_message.emit(f'[diagnostic] axis {event.axis} = {event.value:+.2f}')
                continue
            if event.type == pygame.JOYBUTTONDOWN:
                if self._check_emergency(event):
                    self.sig_message.emit('EMERGENCY STOP (double-tap detected)')
                    p.emergency_stop()
                    continue
                self._dispatch_button(event.button)
            elif event.type == pygame.JOYHATMOTION and event.hat == p._dpad_hat_index:
                last_hat = event.value
            elif event.type == pygame.JOYAXISMOTION:
                # Analog axes flood the queue; only act on the newest value per axis.
                last_axis[event.axis] = event.value

        if last_hat is not None:
            self._move_dpad(*last_hat)
        for axis, value in last_axis.items():
            self._dispatch_axis(axis, value)

    def _check_emergency(self, event):
        p = self._parentclass
        if event.button != p._button_map.get('playstation', -1):
            return False
        now = int(round(time.time() * 1000))
        previous_tap = self._emergency_tap_time
        self._emergency_tap_time = now
        return now < previous_tap + p._emergency_max_delay_ms

    def _move(self, axis, steps):
        device = self._parentclass.active_hardware()
        if steps == 0:
            return
        if device is None:
            self.sig_message.emit(f'{self._parentclass.active_device} is not connected, move ignored.')
            return
        device.move_steps(axis, steps)
        self.sig_message.emit(f'{self._parentclass.active_device}: {axis} {steps:+d}')

    def _dispatch_button(self, button):
        p = self._parentclass
        names = [name for name, index in p._button_map.items() if index == button]
        if not names:
            self.sig_message.emit(f'button {button} pressed (not mapped)')
            return
        name = names[0]
        if name == 'share':
            p._advance_step_size()
            self.sig_message.emit(f'step size = {p.step_size}')
        elif name in _DPAD_BUTTONS:
            self._move_dpad(*_DPAD_BUTTONS[name])
        elif p.active_device == 'nanopositioner':
            if name == 'l1':
                self._move('z', 1)
            elif name == 'r1':
                self._move('z', -1)
        elif p.active_device in ('picomotor', 'nf8752'):
            # Same directions as the original picomotor_controller.py script.
            # The NF8752 additionally has a z axis on L1/R1 (evdev codes 310/311).
            if name == 'l1' and p.active_device == 'nf8752':
                self._move('z', p.step_size)
            elif name == 'r1' and p.active_device == 'nf8752':
                self._move('z', -p.step_size)
            elif name == 'square':
                self._move('x2', p.step_size)
            elif name == 'circle':
                self._move('x2', -p.step_size)
            elif name == 'triangle':
                self._move('y2', -p.step_size)
            elif name == 'cross':
                self._move('y2', p.step_size)

    def _move_dpad(self, dx, dy):
        """ D-pad move with dx/dy in {-1, 0, 1}, right/up positive. Signs reproduce
        the original scripts: left moves x "up" on both devices, up moves the
        nanopositioner y UP but the picomotor y1 by a negative relative step. """
        p = self._parentclass
        if p._dpad_invert_x:
            dx = -dx
        if p._dpad_invert_y:
            dy = -dy
        if p.active_device == 'nanopositioner':
            self._move('x', -dx * p.step_size)
            self._move('y', dy * p.step_size)
        elif p.active_device in ('picomotor', 'nf8752'):
            self._move('x1', -dx * p.step_size)
            self._move('y1', -dy * p.step_size)

    def _dispatch_axis(self, axis, value):
        p = self._parentclass
        if p.active_device != 'nanopositioner':
            return
        # Triggers rest at -1.0 and read +1.0 when fully pressed; rescale to 0..255
        # like the original evdev script.
        magnitude = int(round((value + 1) * 127.5))
        if magnitude <= p._trigger_blind:
            return
        if axis == p._trigger_axes.get('l2', -1):
            self._move('z', magnitude)
        elif axis == p._trigger_axes.get('r2', -1):
            self._move('z', -magnitude)


class JoystickControllerLogic(LogicBase):
    """ Reads a PS5-style game controller and drives a nanopositioner, a
    picomotor or a NewFocus 8752 picomotor driver, whichever is selected as
    "active device" from the GUI.

    All device connectors are optional (same as in SPSCustomScanLogic): to
    leave a device out, comment out its hardware/logic module AND its line in
    the "connect:" section. Only the connected devices are offered in the GUI.

    Example config for copy-paste:

    joystickcontrollerlogic:
        module.Class: 'local.joystick_controller_logic.JoystickControllerLogic'
        connect:
            nanopositioner: 'nanopositioner'
            picomotor: 'picomotor'
            #nf8752: 'nf8752'
        options:
            step_sizes: [1, 10, 40, 200]
            poll_interval: 0.15
            nf8752_velocity: 100       # steps/s, 1..2000
            nf8752_acceleration: 500   # steps/s^2, 1..32000
            trigger_blind: 20
            emergency_max_delay: 1.0
            dpad_hat_index: 0          # only used if the D-pad shows up as a hat
            dpad_invert_x: False
            dpad_invert_y: False
            button_map:                # SDL2 DualSense (PS5) layout
                cross: 0
                circle: 1
                square: 2
                triangle: 3
                share: 4
                playstation: 5
                l1: 9
                r1: 10
                dpad_up: 11
                dpad_down: 12
                dpad_left: 13
                dpad_right: 14
            trigger_axes:
                l2: 4
                r2: 5
    """

    # connectors, all optional
    nanopositioner = Connector(interface='NanopositionerController', optional=True)
    picomotor = Connector(interface='PicomotorController', optional=True)
    nf8752 = Connector(interface='NF8752Logic', optional=True)

    _DEVICES = ('nanopositioner', 'picomotor', 'nf8752')
    _step_sizes = ConfigOption(name='step_sizes', default=[1, 10, 40, 200], missing='nothing')
    _poll_interval = ConfigOption(name='poll_interval', default=0.15, missing='nothing')
    _nf8752_velocity = ConfigOption(name='nf8752_velocity', default=100, missing='nothing')
    _nf8752_acceleration = ConfigOption(name='nf8752_acceleration', default=500,
                                        missing='nothing')
    _trigger_blind = ConfigOption(name='trigger_blind', default=20, missing='nothing')
    _emergency_max_delay = ConfigOption(name='emergency_max_delay', default=1.0, missing='nothing')
    _dpad_hat_index = ConfigOption(name='dpad_hat_index', default=0, missing='nothing')
    _dpad_invert_x = ConfigOption(name='dpad_invert_x', default=False, missing='nothing')
    _dpad_invert_y = ConfigOption(name='dpad_invert_y', default=False, missing='nothing')
    # Defaults follow SDL2's DualSense (PS5) layout, where the D-pad is reported as buttons.
    _button_map = ConfigOption(name='button_map',
                                default={'cross': 0, 'circle': 1, 'square': 2, 'triangle': 3,
                                         'share': 4, 'playstation': 5, 'l1': 9, 'r1': 10,
                                         'dpad_up': 11, 'dpad_down': 12, 'dpad_left': 13,
                                         'dpad_right': 14},
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
        self._devices = dict()  # device type -> driver object, connected devices only
        self.diagnostic_mode = False
        self._polling = False

    def on_activate(self):
        self._poll_interval_ms = max(1, int(round(self._poll_interval * 1000)))
        self._emergency_max_delay_ms = max(1, int(round(self._emergency_max_delay * 1000)))
        nf8752 = self.nf8752()
        devices = {'nanopositioner': self.nanopositioner(),
                   'picomotor': self.picomotor(),
                   'nf8752': None if nf8752 is None else NF8752Adapter(
                       nf8752, self._nf8752_velocity, self._nf8752_acceleration)}
        self._devices = {name: dev for name, dev in devices.items() if dev is not None}
        if not self._devices:
            self.log.warning('No device connected to the joystick controller logic. '
                             'Uncomment at least one entry in its "connect:" section.')
        available = self.get_available_devices()
        if available and self.active_device not in available:
            self.active_device = available[0]
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
        """ Return the driver object of the active device, or None if that
        device is not connected in this config. """
        return self._devices.get(self.active_device)

    def get_available_devices(self):
        """ Return the device types that are connected in this config. """
        return [device for device in self._DEVICES if device in self._devices]

    def set_active_device(self, device):
        """ Switch which device the joystick drives. """
        if device not in self._DEVICES:
            self.log.error(f'Unknown device "{device}".')
            return
        if device not in self._devices:
            self.sigMessage.emit(f'{device} is not connected in the config.')
            self.sigActiveDeviceChanged.emit(self.active_device)
            return
        self.active_device = device
        self.sigMessage.emit(f'Active device: {device}')
        self.sigActiveDeviceChanged.emit(device)

    def start_polling(self):
        with self._thread_lock:
            if self._polling:
                return
            if self.active_hardware() is None:
                self.sigMessage.emit('No device connected, polling not started.')
                self.sigPollingChanged.emit(False)
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
            for device in self._devices.values():
                if device is not None:
                    try:
                        device.stop_all()
                    except Exception as e:
                        self.log.error(f'Error while stopping device: {e}')
        self.sigMessage.emit('Emergency stop executed.')
