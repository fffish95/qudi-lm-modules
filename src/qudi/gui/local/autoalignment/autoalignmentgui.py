# -*- coding: utf-8 -*-

"""

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

import os

from qudi.core.connector import Connector
from qudi.core.module import GuiBase
from PySide2 import QtCore, QtWidgets
from qudi.util import uic


class AutoAlignmentMainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        this_dir = os.path.dirname(__file__)
        ui_file = os.path.join(this_dir, 'ui_autoalignment.ui')

        super().__init__()
        uic.loadUi(ui_file, self)
        self.show


class AutoAlignmentGui(GuiBase):
    """ GUI for autoalignmentLogic: pick the read source/channel, run the simplex
    optimizer with a chosen search range, correct hysteresis, or emergency-stop
    everything.

    Example config for copy-paste:

    autoalignmentgui:
        module.Class: 'local.autoalignment.autoalignmentgui.AutoAlignmentGui'
        connect:
            autoalignmentlogic1: 'autoalignmentlogic'
    """

    autoalignmentlogic1 = Connector(interface='autoalignmentLogic')

    # Signals used to hand long-running requests off to the logic module's own
    # thread via a queued connection, so the GUI never blocks while an
    # optimization or hysteresis correction is running.
    sigOptimizeRequested = QtCore.Signal(str)
    sigCorrectHysteresisRequested = QtCore.Signal()
    sigReadSourceChangeRequested = QtCore.Signal(str)
    sigReadChannelChangeRequested = QtCore.Signal(str)

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)

    def on_activate(self):
        self._logic = self.autoalignmentlogic1()

        self._mw = AutoAlignmentMainWindow()
        self._mw.setDockNestingEnabled(True)

        self._mw.rangeSizeComboBox.addItems(['small', 'medium', 'large'])

        self._populate_read_sources()
        self._populate_channels()

        # Long-running actions: forward to the logic thread via queued signals so
        # the GUI stays responsive while they run.
        self.sigOptimizeRequested.connect(self._logic.start_optimize, QtCore.Qt.QueuedConnection)
        self.sigCorrectHysteresisRequested.connect(
            self._logic.start_correct_hysteresis, QtCore.Qt.QueuedConnection
        )
        self.sigReadSourceChangeRequested.connect(
            self._logic.set_read_source, QtCore.Qt.QueuedConnection
        )
        self.sigReadChannelChangeRequested.connect(
            self._logic.set_timetagger_read_channel, QtCore.Qt.QueuedConnection
        )

        self._logic.sigOptimizeFinished.connect(
            self._optimize_finished, QtCore.Qt.QueuedConnection
        )
        self._logic.sigHysteresisFinished.connect(
            self._hysteresis_finished, QtCore.Qt.QueuedConnection
        )
        self._logic.sigStopped.connect(self._stopped, QtCore.Qt.QueuedConnection)

        self._mw.readSourceComboBox.currentTextChanged.connect(self._read_source_changed)
        self._mw.channelComboBox.currentTextChanged.connect(self._channel_changed)
        self._mw.refreshChannelsButton.clicked.connect(self._populate_channels)
        self._mw.optimizeButton.clicked.connect(self._optimize_clicked)
        self._mw.correctHysteresisButton.clicked.connect(self._correct_hysteresis_clicked)
        # The emergency stop button is intentionally connected to a local slot
        # (not directly to a logic method) so it always executes immediately in
        # the GUI thread instead of being queued behind a currently running,
        # blocking optimize()/correct_hysteresis() call on the logic thread.
        self._mw.emergencyStopButton.clicked.connect(self._emergency_stop_clicked)

        self.show()

    def show(self):
        """Make window visible and put it above all other windows. """
        self._mw.show()
        self._mw.activateWindow()
        self._mw.raise_()

    def on_deactivate(self):
        return 0

    def _populate_read_sources(self):
        sources = self._logic.get_available_read_sources()
        self._mw.readSourceComboBox.blockSignals(True)
        self._mw.readSourceComboBox.clear()
        self._mw.readSourceComboBox.addItems(sources)
        current = self._logic.get_read_source()
        if current in sources:
            self._mw.readSourceComboBox.setCurrentText(current)
        self._mw.readSourceComboBox.blockSignals(False)

    def _populate_channels(self):
        channels = list(self._logic.get_available_timetagger_channels())
        current_channel = self._logic.get_timetagger_read_channel()
        if current_channel and current_channel not in channels:
            channels.append(current_channel)
        self._mw.channelComboBox.blockSignals(True)
        self._mw.channelComboBox.clear()
        self._mw.channelComboBox.addItems(channels)
        if current_channel in channels:
            self._mw.channelComboBox.setCurrentText(current_channel)
        self._mw.channelComboBox.blockSignals(False)

    def _read_source_changed(self, source):
        if not source:
            return
        self.sigReadSourceChangeRequested.emit(source)

    def _channel_changed(self, channel):
        if not channel:
            return
        self.sigReadChannelChangeRequested.emit(channel)

    def _optimize_clicked(self):
        range_size = self._mw.rangeSizeComboBox.currentText()
        self._set_busy(f'Status: optimizing ({range_size})...')
        self.sigOptimizeRequested.emit(range_size)

    def _correct_hysteresis_clicked(self):
        self._set_busy('Status: correcting hysteresis...')
        self.sigCorrectHysteresisRequested.emit()

    def _emergency_stop_clicked(self):
        # Direct call (not a signal emit): takes effect immediately, even while
        # the logic module is busy running a blocking optimize()/
        # correct_hysteresis() call on its own thread.
        self._logic.stop_all()
        self._mw.statusLabel.setText('Status: stopping...')

    def _set_busy(self, message):
        self._mw.optimizeButton.setEnabled(False)
        self._mw.correctHysteresisButton.setEnabled(False)
        self._mw.statusLabel.setText(message)

    def _set_idle(self, message):
        self._mw.optimizeButton.setEnabled(True)
        self._mw.correctHysteresisButton.setEnabled(True)
        self._mw.statusLabel.setText(message)

    def _optimize_finished(self):
        self._set_idle('Status: idle (optimize finished)')

    def _hysteresis_finished(self):
        self._set_idle('Status: idle (hysteresis correction finished)')

    def _stopped(self):
        self._mw.statusBar().showMessage('Emergency stop requested.')
