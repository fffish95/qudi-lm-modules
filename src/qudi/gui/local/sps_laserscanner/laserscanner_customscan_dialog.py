from PySide2 import QtCore, QtGui, QtWidgets
import copy



class LaserscannerCustomScanDialog(QtWidgets.QDialog):
    """
    """

    def __init__(self, current_modes, CustomScanMode, Params):
        super().__init__()
        self.setObjectName('customscan_settings_dialog')
        self.setWindowTitle('Customscan Settings')

        self.settings_widget = LaserscannerCustomScanWidget(current_modes = current_modes, CustomScanMode = CustomScanMode, Params = Params)
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

class LaserscannerCustomScanWidget(QtWidgets.QWidget):
    """ Widget containing infrequently used scanner settings
    """

    def __init__(self, *args, current_modes, CustomScanMode, Params, **kwargs):
        super().__init__(*args, **kwargs)

        self._current_modes = current_modes
        self._customscan_mode = CustomScanMode
        self._params = copy.deepcopy(Params)


        font = QtGui.QFont()
        font.setBold(True)

        customscan_mode_layout = QtWidgets.QHBoxLayout()
        HSpacer = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        customscan_mode_layout.addItem(HSpacer)
        label = QtWidgets.QLabel('Custom scan mode')
        customscan_mode_layout.addWidget(label)
        self.customscan_mode_combobox = QtWidgets.QComboBox()
        for n, name in enumerate(self._customscan_mode):
            self.customscan_mode_combobox.addItem(str(name), n)
        customscan_mode_layout.addWidget(self.customscan_mode_combobox)
        customscan_add_button = QtWidgets.QPushButton('Add')
        customscan_add_button.setCheckable(True)
        customscan_add_button.clicked.connect(self.customscan_add)
        customscan_mode_layout.addWidget(customscan_add_button)

        self.dynamic_layout = QtWidgets.QGridLayout()
        self.update_dynamic_layout()


        customscan_mode_frame = QtWidgets.QFrame()
        customscan_mode_frame.setFont(font)
        customscan_mode_frame.setLayout(customscan_mode_layout)

        customscan_frame = QtWidgets.QFrame()
        customscan_frame.setFont(font)
        customscan_frame.setLayout(self.dynamic_layout)



        self.setLayout(QtWidgets.QGridLayout())
        self.layout().addWidget(customscan_mode_frame,0,0,1,60)
        self.layout().addWidget(customscan_frame,1,0,40,60)



    def customscan_add(self):
        if self.customscan_mode_combobox.currentIndex() not in self._current_modes:
            self._current_modes.append(self.customscan_mode_combobox.currentIndex())
            self._current_modes.sort()
        self.update_dynamic_layout()

    def update_dynamic_layout(self):
        self.deleteItemsOfLayout(self.dynamic_layout)
        self._customscan_del_button_hashmap = dict()
        func_map = {
            self._customscan_mode[0]: self.saturation_scan_layout,
            self._customscan_mode[1]: self.power_record_layout,
            self._customscan_mode[2]: self.EIT_layout,
            self._customscan_mode[3]: self.stark_shift_scan_layout
        }
        for n, mode in enumerate(self._current_modes):
            value = self._customscan_mode[mode]
            func = func_map.get(value)
            groupbox = func()
            self.dynamic_layout.addWidget(groupbox, n, 0, 1, 6)

        


    def saturation_scan_layout(self):
        # mode num
        modenum = 0

        font = QtGui.QFont()
        font.setBold(True)

        # measurements_per_action_layout
        ss_measurements_per_action_layout = QtWidgets.QHBoxLayout()
        HSpacer = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        ss_measurements_per_action_layout.addItem(HSpacer)
        label = QtWidgets.QLabel('Measurements per action')
        ss_measurements_per_action_layout.addWidget(label)
        self.ss_measurements_per_action_lineedit = QtWidgets.QLineEdit()
        self.ss_measurements_per_action_lineedit.setText('{0}'.format(self._params[modenum]['measurements_per_action']))
        self.ss_measurements_per_action_lineedit.editingFinished.connect(lambda: self.ss_measurements_per_action_changed(modenum))
        ss_measurements_per_action_layout.addWidget(self.ss_measurements_per_action_lineedit)

        # delete button
        ss_delete_button_layout = QtWidgets.QHBoxLayout()
        delete_button = QtWidgets.QPushButton('Delete')
        delete_button.setCheckable(True)
        delete_button.clicked.connect(self.customscan_delete)
        ss_delete_button_layout.addWidget(delete_button)

        # motor_layout
        ss_motor_layout = QtWidgets.QHBoxLayout()
        label = QtWidgets.QLabel('motor_channel')
        ss_motor_layout.addWidget(label)
        self.ss_motor_channel_lineedit = QtWidgets.QLineEdit()
        self.ss_motor_channel_lineedit.setText('{0}'.format(self._params[modenum]['motor_channel']))
        self.ss_motor_channel_lineedit.editingFinished.connect(lambda: self.ss_motor_channel_changed(modenum))
        ss_motor_layout.addWidget(self.ss_motor_channel_lineedit)

        label = QtWidgets.QLabel('start_deg')
        ss_motor_layout.addWidget(label)
        self.ss_start_deg_lineedit = QtWidgets.QLineEdit()
        self.ss_start_deg_lineedit.setText('{0}'.format(self._params[modenum]['start_deg']))
        self.ss_start_deg_lineedit.editingFinished.connect(lambda: self.ss_start_deg_changed(modenum))
        ss_motor_layout.addWidget(self.ss_start_deg_lineedit)

        label = QtWidgets.QLabel('step_deg')
        ss_motor_layout.addWidget(label)
        self.ss_step_deg_lineedit = QtWidgets.QLineEdit()
        self.ss_step_deg_lineedit.setText('{0}'.format(self._params[modenum]['step_deg']))
        self.ss_step_deg_lineedit.editingFinished.connect(lambda: self.ss_step_deg_changed(modenum))
        ss_motor_layout.addWidget(self.ss_step_deg_lineedit)    

        ss_layout = QtWidgets.QGridLayout()
        ss_layout.addLayout(ss_measurements_per_action_layout, 0, 0, 1, 4)
        ss_layout.addLayout(ss_delete_button_layout, 0, 5, 1, 1)
        ss_layout.addLayout(ss_motor_layout, 1, 0, 1, 6)

        value = self._customscan_mode[modenum]
        ss_groupbox = QtWidgets.QGroupBox(value)
        ss_groupbox.setLayout(ss_layout)
        self._customscan_del_button_hashmap[delete_button] = {'mode':modenum, 'groupbox': ss_groupbox}

        return ss_groupbox

    def power_record_layout(self):
        # mode num
        modenum = 1

        font = QtGui.QFont()
        font.setBold(True)

        # measurements_per_action_layout
        pr_measurements_per_action_layout = QtWidgets.QHBoxLayout()
        HSpacer = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        pr_measurements_per_action_layout.addItem(HSpacer)
        label = QtWidgets.QLabel('Measurements per action')
        pr_measurements_per_action_layout.addWidget(label)
        self.pr_measurements_per_action_lineedit = QtWidgets.QLineEdit()
        self.pr_measurements_per_action_lineedit.setText('{0}'.format(self._params[modenum]['measurements_per_action']))
        self.pr_measurements_per_action_lineedit.editingFinished.connect(lambda: self.pr_measurements_per_action_changed(modenum))
        pr_measurements_per_action_layout.addWidget(self.pr_measurements_per_action_lineedit)

        # pr_averages_layout
        pr_averages_layout = QtWidgets.QHBoxLayout()
        HSpacer = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        pr_averages_layout.addItem(HSpacer)
        label = QtWidgets.QLabel('Averages:')
        pr_averages_layout.addWidget(label)
        self.pr_averages_lineedit = QtWidgets.QLineEdit()
        self.pr_averages_lineedit.setText('{0}'.format(self._params[modenum]['averages']))
        self.pr_averages_lineedit.editingFinished.connect(lambda: self.pr_averages_changed(modenum))
        pr_averages_layout.addWidget(self.pr_averages_lineedit)

        # delete button
        pr_delete_button_layout = QtWidgets.QHBoxLayout()
        delete_button = QtWidgets.QPushButton('Delete')
        delete_button.setCheckable(True)
        delete_button.clicked.connect(self.customscan_delete)
        pr_delete_button_layout.addWidget(delete_button)


        # motor_layout
        pr_motor_layout = QtWidgets.QHBoxLayout()
        label = QtWidgets.QLabel('motor_channel')
        pr_motor_layout.addWidget(label)
        self.pr_motor_channel_lineedit = QtWidgets.QLineEdit()
        self.pr_motor_channel_lineedit.setText('{0}'.format(self._params[modenum]['motor_channel']))
        self.pr_motor_channel_lineedit.editingFinished.connect(lambda: self.pr_motor_channel_changed(modenum))
        pr_motor_layout.addWidget(self.pr_motor_channel_lineedit)

        label = QtWidgets.QLabel('idle_deg')
        pr_motor_layout.addWidget(label)
        self.pr_idle_deg_lineedit = QtWidgets.QLineEdit()
        self.pr_idle_deg_lineedit.setText('{0}'.format(self._params[modenum]['idle_deg']))
        self.pr_idle_deg_lineedit.editingFinished.connect(lambda: self.pr_idle_deg_changed(modenum))
        pr_motor_layout.addWidget(self.pr_idle_deg_lineedit)

        label = QtWidgets.QLabel('running_deg')
        pr_motor_layout.addWidget(label)
        self.pr_running_deg_lineedit = QtWidgets.QLineEdit()
        self.pr_running_deg_lineedit.setText('{0}'.format(self._params[modenum]['running_deg']))
        self.pr_running_deg_lineedit.editingFinished.connect(lambda: self.pr_running_deg_changed(modenum))
        pr_motor_layout.addWidget(self.pr_running_deg_lineedit) 

        pr_layout = QtWidgets.QGridLayout()
        pr_layout.addLayout(pr_measurements_per_action_layout, 0, 0, 1, 2)
        pr_layout.addLayout(pr_averages_layout, 0, 2, 1, 2)
        pr_layout.addLayout(pr_delete_button_layout, 0, 4, 1, 2)
        pr_layout.addLayout(pr_motor_layout, 1, 0, 1, 6)

        value = self._customscan_mode[modenum]
        pr_groupbox = QtWidgets.QGroupBox(value)
        pr_groupbox.setLayout(pr_layout)
        self._customscan_del_button_hashmap[delete_button] = {'mode':modenum, 'groupbox': pr_groupbox}

        return pr_groupbox  

    def EIT_layout(self):
        modenum = 2

        font = QtGui.QFont()
        font.setBold(True)

        # measurements_per_action_layout
        eit_measurements_per_action_layout = QtWidgets.QHBoxLayout()
        HSpacer = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        eit_measurements_per_action_layout.addItem(HSpacer)
        label = QtWidgets.QLabel('Measurements per action')
        eit_measurements_per_action_layout.addWidget(label)
        self.eit_measurements_per_action_lineedit = QtWidgets.QLineEdit()
        self.eit_measurements_per_action_lineedit.setText('{0}'.format(self._params[modenum]['measurements_per_action']))
        self.eit_measurements_per_action_lineedit.editingFinished.connect(lambda: self.eit_measurements_per_action_changed(modenum))
        eit_measurements_per_action_layout.addWidget(self.eit_measurements_per_action_lineedit)

        # delete button
        eit_delete_button_layout = QtWidgets.QHBoxLayout()
        delete_button = QtWidgets.QPushButton('Delete')
        delete_button.setCheckable(True)
        delete_button.clicked.connect(self.customscan_delete)
        eit_delete_button_layout.addWidget(delete_button)

        # wavelength_ramp_layout
        eit_wavelength_ramp_layout = QtWidgets.QHBoxLayout()

        self.eit_wavelength_ramp_radio_button = QtWidgets.QCheckBox('wavelength_ramp')
        self.eit_wavelength_ramp_radio_button.setChecked(self._params[modenum]['wavelength_ramp'])
        self.eit_wavelength_ramp_radio_button.clicked.connect(
            lambda: self.eit_wavelength_ramp_changed(modenum)
        )
        eit_wavelength_ramp_layout.addWidget(self.eit_wavelength_ramp_radio_button)

        label = QtWidgets.QLabel('start_frequency(THz)')
        eit_wavelength_ramp_layout.addWidget(label)
        self.eit_start_frequency_lineedit = QtWidgets.QLineEdit()
        self.eit_start_frequency_lineedit.setText('{0}'.format(self._params[modenum]['start_frequency(THz)']))
        self.eit_start_frequency_lineedit.editingFinished.connect(lambda: self.eit_start_frequency_changed(modenum))
        eit_wavelength_ramp_layout.addWidget(self.eit_start_frequency_lineedit)

        label = QtWidgets.QLabel('step_frequency(MHz)')
        eit_wavelength_ramp_layout.addWidget(label)
        self.eit_step_frequency_lineedit = QtWidgets.QLineEdit()
        self.eit_step_frequency_lineedit.setText('{0}'.format(self._params[modenum]['step_frequency(MHz)']))
        self.eit_step_frequency_lineedit.editingFinished.connect(lambda: self.eit_step_frequency_changed(modenum))
        eit_wavelength_ramp_layout.addWidget(self.eit_step_frequency_lineedit)

        # Background_subtract_layout
        eit_Background_subtract_layout = QtWidgets.QHBoxLayout()
        self.eit_Background_subtract_radio_button = QtWidgets.QCheckBox('Background_subtract')
        self.eit_Background_subtract_radio_button.setChecked(self._params[modenum]['Background_subtract'])
        self.eit_Background_subtract_radio_button.clicked.connect(
            lambda: self.eit_Background_subtract_changed(modenum)
        )
        eit_Background_subtract_layout.addWidget(self.eit_Background_subtract_radio_button)

        label = QtWidgets.QLabel('shutter_channels')
        eit_Background_subtract_layout.addWidget(label)
        self.eit_shutter_channels_lineedit = QtWidgets.QLineEdit()
        self.eit_shutter_channels_lineedit.setText('{0}'.format(self._params[modenum]['shutter_channels'][0]))
        self.eit_shutter_channels_lineedit.editingFinished.connect(lambda: self.eit_shutter_channels_changed(modenum))
        eit_Background_subtract_layout.addWidget(self.eit_shutter_channels_lineedit)


        eit_layout = QtWidgets.QGridLayout()
        eit_layout.addLayout(eit_measurements_per_action_layout, 0, 0, 1, 4)
        eit_layout.addLayout(eit_delete_button_layout, 0, 5, 1, 1)
        eit_layout.addLayout(eit_wavelength_ramp_layout, 1, 0, 1, 6)
        eit_layout.addLayout(eit_Background_subtract_layout, 2, 2, 1, 4)

        value = self._customscan_mode[modenum]
        eit_groupbox = QtWidgets.QGroupBox(value)
        eit_groupbox.setLayout(eit_layout)
        self._customscan_del_button_hashmap[delete_button] = {'mode':modenum, 'groupbox': eit_groupbox}
        return eit_groupbox

    def stark_shift_scan_layout(self):
        pass


    def customscan_delete(self):
        mode = self._customscan_del_button_hashmap[self.sender()]['mode']
        groupbox = self._customscan_del_button_hashmap[self.sender()]['groupbox']

        self._current_modes.remove(mode)
        self.dynamic_layout.removeWidget(groupbox)
        groupbox.deleteLater()
        groupbox = None



    def ss_measurements_per_action_changed(self, modenum):
        self._params[modenum]['measurements_per_action'] = int(self.ss_measurements_per_action_lineedit.text())

    def ss_motor_channel_changed(self, modenum):
        self._params[modenum]['motor_channel'] = int(self.ss_motor_channel_lineedit.text())

    def ss_start_deg_changed(self, modenum):
        self._params[modenum]['start_deg'] = int(self.ss_start_deg_lineedit.text())

    def ss_step_deg_changed(self, modenum):
        self._params[modenum]['step_deg'] = int(self.ss_step_deg_lineedit.text())


    def pr_measurements_per_action_changed(self, modenum):
        self._params[modenum]['measurements_per_action'] = int(self.pr_measurements_per_action_lineedit.text())

    def pr_averages_changed(self, modenum):
        self._params[modenum]['averages'] = int(self.pr_averages_lineedit.text())

    def pr_motor_channel_changed(self, modenum):
        self._params[modenum]['motor_channel'] = int(self.pr_motor_channel_lineedit.text())

    def pr_idle_deg_changed(self, modenum):
        self._params[modenum]['idle_deg'] = int(self.pr_idle_deg_lineedit.text())

    def pr_running_deg_changed(self, modenum):
        self._params[modenum]['running_deg'] = int(self.pr_running_deg_lineedit.text())
        

    def eit_measurements_per_action_changed(self, modenum):
        self._params[modenum]['measurements_per_action'] = int(self.eit_measurements_per_action_lineedit.text())

    def eit_wavelength_ramp_changed(self, modenum):
        self._params[modenum]['wavelength_ramp'] = self.eit_wavelength_ramp_radio_button.isChecked()
    
    def eit_start_frequency_changed(self, modenum):
        self._params[modenum]['start_frequency(THz)'] = float(self.eit_start_frequency_lineedit.text())

    def eit_step_frequency_changed(self, modenum):
        self._params[modenum]['step_frequency(MHz)'] = int(self.eit_step_frequency_lineedit.text())

    def eit_Background_subtract_changed(self, modenum):
        self._params[modenum]['Background_subtract'] = self.eit_Background_subtract_radio_button.isChecked()
    
    def eit_shutter_channels_changed(self, modenum):
        self._params[modenum]['shutter_channels'][0] = str(self.eit_step_frequency_lineedit.text())




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
