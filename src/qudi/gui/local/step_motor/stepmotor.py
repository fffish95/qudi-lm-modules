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
from qudi.core.statusvariable import StatusVar
from PySide2 import QtCore, QtWidgets
from qudi.util import uic


class StepMotorMainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        this_dir = os.path.dirname(__file__)
        ui_file = os.path.join(this_dir,'ui_stepmotor.ui')

        super().__init__()
        uic.loadUi(ui_file, self)
        self.show



class StepMotorGui(GuiBase):
    stepmotorlogic = Connector(interface='StepMotorLogic')

    # Persist the per-channel 0%/100% calibration positions across restarts.
    _calibration = StatusVar(
        name='calibration',
        default={channel: {'zero': None, 'full': None} for channel in range(4)}
    )

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)
    def on_activate(self):
        
        self._step_motor_logic = self.stepmotorlogic()
    
        self._mw= StepMotorMainWindow()

        self._mw.setDockNestingEnabled(True)
        self._motor_channel = 0
        # Ensure every channel has a calibration entry, even if the StatusVar was
        # saved by an older version of this GUI with fewer/different channels.
        for channel in range(4):
            self._calibration.setdefault(channel, {'zero': None, 'full': None})
        self._last_position = None

        self._mw.motorChannelComboBox.addItems([str(channel) for channel in range(4)])
        self._mw.moveAbsSlider.setRange(0, 100)
        self._mw.moveAbsSlider.valueChanged.connect(self._update_absolute_preview)
        self._mw.moveAbsSlider.sliderReleased.connect(self.MOVEABS)
        self._mw.motorChannelComboBox.currentIndexChanged.connect(self.update_motor_channel)
        self._mw.applyCalibrationButton.clicked.connect(self.apply_calibration)
        self._mw.moveAbsButton.clicked.connect(self.MOVEABS_VALUE)
        self._mw.moveAbsValueSpinBox.editingFinished.connect(self.MOVEABS_VALUE)

        self._position_timer = QtCore.QTimer(self._mw)
        self._position_timer.timeout.connect(self.update_position)
        self._position_timer.start(500)
        self.update_motor_channel(0)
        if self._step_motor_logic is None:
            self.log.error(
                'Step motor logic is not connected. Check the stepmotorlogic '
                'GUI connection in the configuration.'
            )
            self._mw.statusBar().showMessage('Step motor logic is not connected.')

        self.show()
    
    def show(self):
        """Make window visible and put it above all other windows. """
        self._mw.show()
        self._mw.activateWindow()
        self._mw.raise_()

    def on_deactivate(self):

        if hasattr(self, '_position_timer'):
            self._position_timer.stop()
        return 0


    def update_motor_channel(self, channel):
        self._motor_channel = int(channel)
        self._update_calibration_labels()
        self.update_position()
    
    def MOVEABS(self):
        calibration = self._calibration[self._motor_channel]
        if calibration['zero'] is None or calibration['full'] is None:
            self._mw.statusBar().showMessage('Define both calibration positions first.')
            return
        destination = self._percentage_to_position(self._mw.moveAbsSlider.value())
        self._step_motor_logic.move_abs(self._motor_channel, destination)

    def MOVEABS_VALUE(self):
        calibration = self._calibration[self._motor_channel]
        if calibration['zero'] is None or calibration['full'] is None:
            self._mw.statusBar().showMessage('Apply valid calibration values first.')
            return
        value = self._mw.moveAbsValueSpinBox.value()
        self._step_motor_logic.move_abs(self._motor_channel, round(value, 2))
        self._mw.moveAbsTargetLabel.setText(f'Target: {value:.2f}')

    def apply_calibration(self):
        zero = self._mw.zeroSpinBox.value()
        full = self._mw.fullSpinBox.value()
        if zero == full:
            self._mw.statusBar().showMessage('0% and 100% positions must be different.')
            return
        self._calibration[self._motor_channel] = {'zero': zero, 'full': full}
        self._update_calibration_labels()
        self._mw.statusBar().showMessage('Calibration applied.')

    def update_position(self):
        position = self._read_position()
        if position is None:
            return
        self._last_position = position
        self._mw.currentPositionLabel.setText(f'Current: {position:.2f}')
        calibration = self._calibration[self._motor_channel]
        if calibration['zero'] is not None and calibration['full'] is not None:
            percentage = self._position_to_percentage(position)
            self._mw.moveAbsPercentageLabel.setText(f'{percentage:.1f}%')
            self._mw.currentPercentageLabel.setText(f'Percentage: {percentage:.1f}%')
        else:
            self._mw.moveAbsPercentageLabel.setText('n/a')
            self._mw.currentPercentageLabel.setText('Percentage: n/a')

    def _read_position(self):
        if self._step_motor_logic is None:
            return None
        position = self._step_motor_logic.get_pos(self._motor_channel)
        if position is None or position < 0:
            self._mw.statusBar().showMessage('Unable to read the current motor position.')
            return None
        return float(position)

    def _span(self):
        calibration = self._calibration[self._motor_channel]
        return calibration['full'] - calibration['zero']

    def _percentage_to_position(self, percentage):
        calibration = self._calibration[self._motor_channel]
        return round(calibration['zero'] + self._span() * percentage / 100, 2)

    def _position_to_percentage(self, position):
        span = self._span()
        if span == 0:
            return 0
        return (position - self._calibration[self._motor_channel]['zero']) * 100 / span

    def _update_absolute_preview(self, percentage):
        calibration = self._calibration[self._motor_channel]
        if calibration['zero'] is not None and calibration['full'] is not None:
            position = self._percentage_to_position(percentage)
            self._mw.moveAbsPercentageLabel.setText(f'{percentage}%')
            self._mw.moveAbsTargetLabel.setText(f'Target: {position:.2f}')
            self._mw.moveAbsValueSpinBox.blockSignals(True)
            self._mw.moveAbsValueSpinBox.setValue(position)
            self._mw.moveAbsValueSpinBox.blockSignals(False)

    def _update_calibration_labels(self):
        calibration = self._calibration[self._motor_channel]
        self._mw.zeroSpinBox.blockSignals(True)
        self._mw.fullSpinBox.blockSignals(True)
        self._mw.zeroSpinBox.setValue(calibration['zero'] or 0)
        self._mw.fullSpinBox.setValue(calibration['full'] or 0)
        self._mw.zeroSpinBox.blockSignals(False)
        self._mw.fullSpinBox.blockSignals(False)
        calibrated = calibration['zero'] is not None and calibration['full'] is not None
        self._mw.moveAbsSlider.setEnabled(calibrated)
        self._mw.moveAbsButton.setEnabled(calibrated)
        self._mw.moveAbsValueSpinBox.setEnabled(calibrated)
        if not calibrated:
            self._mw.moveAbsTargetLabel.setText('Target: not calibrated')



    
