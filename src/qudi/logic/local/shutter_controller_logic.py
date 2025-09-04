# -*- coding: utf-8 -*-

"""
A module for controlling a camera.

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

from PySide2 import QtCore
from qudi.core.connector import Connector
from qudi.core.configoption import ConfigOption
from qudi.core.module import LogicBase
from qudi.util.mutex import Mutex


class ShutterLogic(LogicBase):
    """
    Control a shutter.
    """

    # declare connectors
    nicard = Connector(interface = "NICard")
    # declare config options
    _do_channel = ConfigOption('do_channel', None, missing='nothing')

    # # signals
    # sigFrameChanged = QtCore.Signal(object)
    # sigAcquisitionFinished = QtCore.Signal()
    # sig_handle_timer = QtCore.Signal(bool)

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)
        self._thread_lock = Mutex()
        # self._exposure = -1
        # self._gain = -1
        # self._last_frame = None


    def on_activate(self):
        """ Initialisation performed during activation of the module.
        """
        self._nicard = self.nicard()
        self.do_task = self._nicard.create_do_task(taskname = 'shutter', channels = self._do_channel)

    def on_deactivate(self):
        """ Perform required deactivation. """
        self._nicard.close_do_task(taskname = 'shutter')
        self.do_task = None

    def shutter_on(self):
        return self._nicard.write_task(task= self.do_task, data = True)
    
    def shutter_off(self):
        return self._nicard.write_task(task= self.do_task, data = False)
