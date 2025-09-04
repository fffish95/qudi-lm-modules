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
from PySide2 import QtWidgets
from qudi.util import uic


class ShutterMainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        this_dir = os.path.dirname(__file__)
        ui_file = os.path.join(this_dir,'shutter_controller.ui')

        super().__init__()
        uic.loadUi(ui_file, self)
        self.show



class ShutterGui(GuiBase):
    shutterlogic= Connector(interface='ShutterLogic')
    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)
    def on_activate(self):
        
        self._shutter_logic = self.shutterlogic()
    
        self._mw= ShutterMainWindow()

        self._mw.setDockNestingEnabled(True)



        self._mw.pushButton_0.clicked.connect(self.update_shutter_state)


        self.show()
    
    def show(self):
        """Make window visible and put it above all other windows. """
        self._mw.show()
        self._mw.activateWindow()
        self._mw.raise_()

    def on_deactivate(self):

        self._mw.pushButton_0.clicked.disconnect()
        return 0


    def update_shutter_state(self):
        if self._mw.pushButton_0.text() == 'closed':
            self._shutter_logic.shutter_on()
            self._mw.pushButton_0.setText('opened')
        else:
            self._shutter_logic.shutter_off()
            self._mw.pushButton_0.setText('closed')

    



    


