from PySide2 import QtCore, QtGui, QtWidgets
import copy



class ConfocalLoopScanDialog(QtWidgets.QDialog):
    """
    """

    def __init__(self, current_modes, LoopScanMode, Params):
        super().__init__()
        self.setObjectName('loopscan_settings_dialog')
        self.setWindowTitle('Loopscan Settings')

        self.settings_widget = ConfocalLoopScanWidget(current_modes = current_modes, LoopScanMode = LoopScanMode, Params = Params)
        self.button_box = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok |
                                                     QtWidgets.QDialogButtonBox.Cancel |
                                                     QtCore.Qt.Horizontal,
                                                     self)

        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.settings_widget)
        layout.addWidget(self.button_box)
        layout.setSizeConstraint(QtWidgets.QLayout.SetFixedSize)
        self.setLayout(layout)
        return

class ConfocalLoopScanWidget(QtWidgets.QWidget):
    """
    """

    def __init__(self, *args, current_modes, LoopScanMode, Params, **kwargs):
        super().__init__(*args, **kwargs)

        self._current_modes = current_modes
        self._loopscan_mode = LoopScanMode
        self._params = copy.deepcopy(Params)


        font = QtGui.QFont()
        font.setBold(True)

        loopscan_mode_layout = QtWidgets.QHBoxLayout()
        HSpacer = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        loopscan_mode_layout.addItem(HSpacer)
        label = QtWidgets.QLabel('Loop scan mode')
        loopscan_mode_layout.addWidget(label)
        self.loopscan_mode_combobox = QtWidgets.QComboBox()
        for n, name in enumerate(self._loopscan_mode):
            self.loopscan_mode_combobox.addItem(str(name), n)
        loopscan_mode_layout.addWidget(self.loopscan_mode_combobox)
        loopscan_add_button = QtWidgets.QPushButton('Add')
        loopscan_add_button.setCheckable(True)
        loopscan_add_button.clicked.connect(self.loopscan_add)
        loopscan_mode_layout.addWidget(loopscan_add_button)

        self.dynamic_layout = QtWidgets.QGridLayout()
        self.update_dynamic_layout()


        loopscan_mode_frame = QtWidgets.QFrame()
        loopscan_mode_frame.setFont(font)
        loopscan_mode_frame.setLayout(loopscan_mode_layout)

        loopscan_frame = QtWidgets.QFrame()
        loopscan_frame.setFont(font)
        loopscan_frame.setLayout(self.dynamic_layout)



        self.setLayout(QtWidgets.QGridLayout())
        self.layout().addWidget(loopscan_mode_frame,0,0,1,60)
        self.layout().addWidget(loopscan_frame,1,0,40,60)



    def loopscan_add(self):
        if self.loopscan_mode_combobox.currentIndex() not in self._current_modes:
            self._current_modes.append(self.loopscan_mode_combobox.currentIndex())
            self._current_modes.sort()
        self.update_dynamic_layout()

    def update_dynamic_layout(self):
        self.deleteItemsOfLayout(self.dynamic_layout)
        self._loopscan_del_button_hashmap = dict()
        func_map = {
            self._loopscan_mode[0]: self.scan_trigger_layout,
            self._loopscan_mode[1]: self.step_motor_layout,
        }
        for n, mode in enumerate(self._current_modes):
            value = self._loopscan_mode[mode]
            func = func_map.get(value)
            groupbox = func()
            self.dynamic_layout.addWidget(groupbox, n, 0, 1, 6)


    def scan_trigger_layout(self):
        # mode num
        modenum = 0

        font = QtGui.QFont()
        font.setBold(True)

        # st_setting_layout
        st_setting_layout = QtWidgets.QHBoxLayout()
        label = QtWidgets.QLabel('trigger_channel')
        st_setting_layout.addWidget(label)
        self.st_trigger_channel_lineedit = QtWidgets.QLineEdit()
        self.st_trigger_channel_lineedit.setText('{0}'.format(self._params[modenum]['trigger_channel'][0]))
        self.st_trigger_channel_lineedit.editingFinished.connect(lambda: self.st_trigger_channel_changed(modenum))
        st_setting_layout.addWidget(self.st_trigger_channel_lineedit)


        label = QtWidgets.QLabel('trigger_length')
        st_setting_layout.addWidget(label)
        self.st_trigger_length_lineedit = QtWidgets.QLineEdit()
        self.st_trigger_length_lineedit.setText('{0}'.format(self._params[modenum]['trigger_length']))
        self.st_trigger_length_lineedit.editingFinished.connect(lambda: self.st_trigger_length_changed(modenum))
        st_setting_layout.addWidget(self.st_trigger_length_lineedit)

        # delete button
        st_delete_button_layout = QtWidgets.QHBoxLayout()
        delete_button = QtWidgets.QPushButton('Delete')
        delete_button.setCheckable(True)
        delete_button.clicked.connect(self.loopscan_delete)
        st_delete_button_layout.addWidget(delete_button)

 

        st_layout = QtWidgets.QGridLayout()
        st_layout.addLayout(st_setting_layout, 0, 0, 1, 4)
        st_layout.addLayout(st_delete_button_layout, 0, 5, 1, 1)

        value = self._loopscan_mode[modenum]
        st_groupbox = QtWidgets.QGroupBox(value)
        st_groupbox.setLayout(st_layout)
        self._loopscan_del_button_hashmap[delete_button] = {'mode':modenum, 'groupbox': st_groupbox}

        return st_groupbox

    def step_motor_layout(self):
        # mode num
        modenum = 1

        font = QtGui.QFont()
        font.setBold(True)

        # motor_layout
        sm_motor_layout = QtWidgets.QHBoxLayout()
        label = QtWidgets.QLabel('motor_channel')
        sm_motor_layout.addWidget(label)
        self.sm_motor_channel_lineedit = QtWidgets.QLineEdit()
        self.sm_motor_channel_lineedit.setText('{0}'.format(self._params[modenum]['motor_channel']))
        self.sm_motor_channel_lineedit.editingFinished.connect(lambda: self.sm_motor_channel_changed(modenum))
        sm_motor_layout.addWidget(self.sm_motor_channel_lineedit)

        label = QtWidgets.QLabel('start_deg')
        sm_motor_layout.addWidget(label)
        self.sm_start_deg_lineedit = QtWidgets.QLineEdit()
        self.sm_start_deg_lineedit.setText('{0}'.format(self._params[modenum]['start_deg']))
        self.sm_start_deg_lineedit.editingFinished.connect(lambda: self.sm_start_deg_changed(modenum))
        sm_motor_layout.addWidget(self.sm_start_deg_lineedit)

        label = QtWidgets.QLabel('step_deg')
        sm_motor_layout.addWidget(label)
        self.sm_step_deg_lineedit = QtWidgets.QLineEdit()
        self.sm_step_deg_lineedit.setText('{0}'.format(self._params[modenum]['step_deg']))
        self.sm_step_deg_lineedit.editingFinished.connect(lambda: self.sm_step_deg_changed(modenum))
        sm_motor_layout.addWidget(self.sm_step_deg_lineedit)    

        # delete button
        sm_delete_button_layout = QtWidgets.QHBoxLayout()
        delete_button = QtWidgets.QPushButton('Delete')
        delete_button.setCheckable(True)
        delete_button.clicked.connect(self.loopscan_delete)
        sm_delete_button_layout.addWidget(delete_button)


        sm_layout = QtWidgets.QGridLayout()
        sm_layout.addLayout(sm_motor_layout, 0, 0, 1, 6)
        sm_layout.addLayout(sm_delete_button_layout, 1, 0, 1, 1)

        value = self._loopscan_mode[modenum]
        sm_groupbox = QtWidgets.QGroupBox(value)
        sm_groupbox.setLayout(sm_layout)
        self._loopscan_del_button_hashmap[delete_button] = {'mode':modenum, 'groupbox': sm_groupbox}

        return sm_groupbox  


    def loopscan_delete(self):
        mode = self._loopscan_del_button_hashmap[self.sender()]['mode']
        groupbox = self._loopscan_del_button_hashmap[self.sender()]['groupbox']

        self._current_modes.remove(mode)
        self.dynamic_layout.removeWidget(groupbox)
        groupbox.deleteLater()
        groupbox = None
    
    def st_trigger_channel_changed(self, modenum):
        self._params[modenum]['trigger_channel'][0] = str(self.st_trigger_channel_lineedit.text())

    def st_trigger_length_changed(self, modenum):
        self._params[modenum]['trigger_length'] = str(self.st_trigger_length_lineedit.text())

    def sm_motor_channel_changed(self, modenum):
        self._params[modenum]['motor_channel'] = int(self.sm_motor_channel_lineedit.text())

    def sm_start_deg_changed(self, modenum):
        self._params[modenum]['start_deg'] = int(self.sm_start_deg_lineedit.text())

    def sm_step_deg_changed(self, modenum):
        self._params[modenum]['step_deg'] = int(self.sm_step_deg_lineedit.text())



    def deleteItemsOfLayout(self, layout):
        """
            Layout delete function from TheTrowser
        """
        if layout is not None:
            while layout.count():
                item = layout.takeAt(0)
                widget = item.widget()
                if widget is not None:
                    widget.setParent(None)
                else:
                    self.deleteItemsOfLayout(item.layout())
