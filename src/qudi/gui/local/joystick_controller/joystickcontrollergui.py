# -*- coding: utf-8 -*-
# NOTE: This module was written or modified by fffish
# (https://github.com/fffish95/qudi-lm-modules) and remains subject to the GNU
# license terms stated below (or, if none are stated in this file, to the GNU
# General Public License under which Qudi is distributed).

"""
GUI for JoystickControllerLogic: switch which device (nanopositioner,
picomotor or NewFocus 8752) the joystick drives from the menu bar, start/stop polling,
choose a step size, toggle diagnostic mode, and watch a terminal log of
everything the controller is doing. An emergency-stop button is always
available and takes effect immediately.
"""

import os

from qudi.core.connector import Connector
from qudi.core.module import GuiBase
from PySide2 import QtCore, QtWidgets
from qudi.util import uic


class JoystickControllerMainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        this_dir = os.path.dirname(__file__)
        ui_file = os.path.join(this_dir, 'ui_joystickcontroller.ui')

        super().__init__()
        uic.loadUi(ui_file, self)
        self.show


class JoystickControllerGui(GuiBase):
    """ GUI for JoystickControllerLogic.

    Example config for copy-paste:

    joystickcontrollergui:
        module.Class: 'local.joystick_controller.joystickcontrollergui.JoystickControllerGui'
        connect:
            joystickcontrollerlogic1: 'joystickcontrollerlogic'
    """

    joystickcontrollerlogic1 = Connector(interface='JoystickControllerLogic')

    # Long-running/ongoing requests are dispatched to the logic module's own
    # thread via queued connections so the GUI never blocks.
    sigSetActiveDeviceRequested = QtCore.Signal(str)
    sigStartPollingRequested = QtCore.Signal()
    sigStopPollingRequested = QtCore.Signal()
    sigSetDiagnosticModeRequested = QtCore.Signal(bool)

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)

    def on_activate(self):
        self._logic = self.joystickcontrollerlogic1()

        self._mw = JoystickControllerMainWindow()

        self._mw.stepSizeComboBox.addItems([str(s) for s in self._logic._step_sizes])
        self._mw.stepSizeComboBox.setCurrentText(str(self._logic.step_size))
        self._mw.stepSizeComboBox.setEnabled(False)  # step size is cycled by the "share" button

        self._device_actions = {'nanopositioner': self._mw.actionNanopositioner,
                                'picomotor': self._mw.actionPicomotor,
                                'nf8752': self._mw.actionNF8752}
        available = self._logic.get_available_devices()
        device_group = QtWidgets.QActionGroup(self._mw)
        device_group.setExclusive(True)
        for device, action in self._device_actions.items():
            action.setEnabled(device in available)
            device_group.addAction(action)
            # PySide2 does not always pass "checked" to triggered slots, so accept any args.
            action.triggered.connect(lambda *args, d=device: self._device_action_triggered(d))
        self._active_device_changed(self._logic.active_device)

        self.sigSetActiveDeviceRequested.connect(self._logic.set_active_device,
                                                  QtCore.Qt.QueuedConnection)
        self.sigStartPollingRequested.connect(self._logic.start_polling,
                                               QtCore.Qt.QueuedConnection)
        self.sigStopPollingRequested.connect(self._logic.stop_polling,
                                              QtCore.Qt.QueuedConnection)
        self.sigSetDiagnosticModeRequested.connect(self._logic.set_diagnostic_mode,
                                                    QtCore.Qt.QueuedConnection)

        self._logic.sigMessage.connect(self._append_message, QtCore.Qt.QueuedConnection)
        self._logic.sigStepSizeChanged.connect(self._step_size_changed, QtCore.Qt.QueuedConnection)
        self._logic.sigActiveDeviceChanged.connect(self._active_device_changed,
                                                    QtCore.Qt.QueuedConnection)
        self._logic.sigPollingChanged.connect(self._polling_changed, QtCore.Qt.QueuedConnection)

        self._mw.actionDiagnosticMode.toggled.connect(self.sigSetDiagnosticModeRequested.emit)
        self._mw.startPollingButton.toggled.connect(self._start_polling_toggled)
        self._mw.clearTerminalButton.clicked.connect(self._mw.terminalTextEdit.clear)
        # The emergency stop button is intentionally connected directly to the
        # logic method (not via a queued signal) so it always executes
        # immediately in the caller's thread instead of being queued behind a
        # currently running poll/move on the logic's own thread.
        self._mw.emergencyStopButton.clicked.connect(self._logic.emergency_stop)

        self.show()

    def show(self):
        """ Make window visible and put it above all other windows. """
        self._mw.show()
        self._mw.activateWindow()
        self._mw.raise_()

    def on_deactivate(self):
        return 0

    def _start_polling_toggled(self, checked):
        if checked:
            self._mw.startPollingButton.setText('Stop polling')
            self.sigStartPollingRequested.emit()
        else:
            self._mw.startPollingButton.setText('Start polling')
            self.sigStopPollingRequested.emit()

    def _append_message(self, text):
        self._mw.terminalTextEdit.appendPlainText(text)

    def _step_size_changed(self, step_size):
        self._mw.stepSizeComboBox.setCurrentText(str(step_size))

    def _device_action_triggered(self, device):
        if self._device_actions[device].isChecked():
            self.sigSetActiveDeviceRequested.emit(device)

    def _active_device_changed(self, device):
        self._mw.activeDeviceValueLabel.setText(device)
        action = self._device_actions.get(device)
        if action is not None:
            action.setChecked(True)

    def _polling_changed(self, polling):
        self._mw.pollingValueLabel.setText('running' if polling else 'stopped')
        # Keep the button in sync, e.g. when starting failed because the device could not load.
        self._mw.startPollingButton.blockSignals(True)
        self._mw.startPollingButton.setChecked(polling)
        self._mw.startPollingButton.setText('Stop polling' if polling else 'Start polling')
        self._mw.startPollingButton.blockSignals(False)
