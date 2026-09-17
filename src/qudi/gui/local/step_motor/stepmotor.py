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


class StepMotorMainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        this_dir = os.path.dirname(__file__)
        ui_file = os.path.join(this_dir,'ui_stepmotor.ui')

        super().__init__()
        uic.loadUi(ui_file, self)
        self.show



class StepMotorGui(GuiBase):
    stepmotorlogic = Connector(interface='StepMotorLogic')
    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)
    def on_activate(self):
        
        self._step_motor_logic = self.stepmotorlogic()
    
        self._mw= StepMotorMainWindow()

        self._mw.setDockNestingEnabled(True)
        self._motor_channel = 0
        self._calibration = {
            channel: {'zero': None, 'full': None}
            for channel in range(4)
        }
        self._last_position = None

        self._mw.motorChannelComboBox.addItems([str(channel) for channel in range(4)])
        for slider in (self._mw.moveAbsSlider, self._mw.moveRelSlider):
            slider.setRange(0, 100)
        self._mw.moveAbsSlider.valueChanged.connect(self._update_absolute_preview)
        self._mw.moveAbsSlider.sliderReleased.connect(self.MOVEABS)
        self._mw.moveRelSlider.valueChanged.connect(self._update_relative_preview)
        self._mw.moveRelSlider.sliderReleased.connect(self.MOVEREL)
        self._mw.motorChannelComboBox.currentIndexChanged.connect(self.update_motor_channel)
        self._mw.setZeroButton.clicked.connect(self.set_zero_position)
        self._mw.setFullButton.clicked.connect(self.set_full_position)

        self._position_timer = QtCore.QTimer(self._mw)
        self._position_timer.timeout.connect(self.update_position)
        self._position_timer.start(500)
        self.update_motor_channel(0)

        self.show()
    
    def show(self):
        """Make window visible and put it above all other windows. """
        self._mw.show()
        self._mw.activateWindow()
        self._mw.raise_()

    def on_deactivate(self):

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

    def MOVEREL(self):
        calibration = self._calibration[self._motor_channel]
        if calibration['zero'] is None or calibration['full'] is None:
            self._mw.statusBar().showMessage('Define both calibration positions first.')
            return
        degree = self._span() * self._mw.moveRelSlider.value() / 100
        self._step_motor_logic.move_rel(self._motor_channel, round(degree, 2))

    def set_zero_position(self):
        position = self._read_position()
        if position is not None:
            if self._calibration[self._motor_channel]['full'] == position:
                self._mw.statusBar().showMessage('0% and 100% positions must be different.')
                return
            self._calibration[self._motor_channel]['zero'] = position
            self._update_calibration_labels()

    def set_full_position(self):
        position = self._read_position()
        if position is not None:
            if self._calibration[self._motor_channel]['zero'] == position:
                self._mw.statusBar().showMessage('0% and 100% positions must be different.')
                return
            self._calibration[self._motor_channel]['full'] = position
            self._update_calibration_labels()

    def update_position(self):
        position = self._read_position()
        if position is None:
            return
        self._last_position = position
        self._mw.moveAbsPositionLabel.setText(f'Current: {position:.2f}')
        self._mw.moveRelPositionLabel.setText(f'Current: {position:.2f}')
        calibration = self._calibration[self._motor_channel]
        if calibration['zero'] is not None and calibration['full'] is not None:
            percentage = self._position_to_percentage(position)
            self._mw.moveAbsPercentageLabel.setText(f'{percentage:.1f}%')
            self._mw.moveRelPercentageLabel.setText(f'{percentage:.1f}%')
        else:
            self._mw.moveAbsPercentageLabel.setText('n/a')
            self._mw.moveRelPercentageLabel.setText('n/a')

    def _read_position(self):
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

    def _update_relative_preview(self, percentage):
        calibration = self._calibration[self._motor_channel]
        if calibration['zero'] is not None and calibration['full'] is not None:
            distance = self._span() * percentage / 100
            self._mw.moveRelPercentageLabel.setText(f'{percentage}%')
            self._mw.moveRelTargetLabel.setText(f'Move: {distance:+.2f}')

    def _update_calibration_labels(self):
        calibration = self._calibration[self._motor_channel]
        zero = 'not set' if calibration['zero'] is None else f'{calibration["zero"]:.2f}'
        full = 'not set' if calibration['full'] is None else f'{calibration["full"]:.2f}'
        self._mw.zeroPositionLabel.setText(f'0%: {zero}')
        self._mw.fullPositionLabel.setText(f'100%: {full}')
        calibrated = calibration['zero'] is not None and calibration['full'] is not None
        self._mw.moveAbsSlider.setEnabled(calibrated)
        self._mw.moveRelSlider.setEnabled(calibrated)
        if not calibrated:
            self._mw.moveAbsTargetLabel.setText('Target: not calibrated')
            self._mw.moveRelTargetLabel.setText('Move: not calibrated')



    
