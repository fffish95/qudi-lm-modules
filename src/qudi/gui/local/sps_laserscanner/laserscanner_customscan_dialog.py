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
            self._customscan_mode[0]: self.step_motor_layout,
            self._customscan_mode[1]: self.power_record_layout,
            self._customscan_mode[2]: self.EIT_layout,
            self._customscan_mode[3]: self.stark_shift_scan_layout,
            self._customscan_mode[4]: self.scan_trigger_layout,
            self._customscan_mode[5]: self.timetagger_writeintofile_layout,
        }
        for n, mode in enumerate(self._current_modes):
            value = self._customscan_mode[mode]
            func = func_map.get(value)
            groupbox = func()
            self.dynamic_layout.addWidget(groupbox, n, 0, 1, 6)

        


    def step_motor_layout(self):
        # mode num
        modenum = 0

        font = QtGui.QFont()
        font.setBold(True)

        # measurements_per_action_layout
        sm_measurements_per_action_layout = QtWidgets.QHBoxLayout()
        HSpacer = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        sm_measurements_per_action_layout.addItem(HSpacer)
        label = QtWidgets.QLabel('Measurements per action')
        sm_measurements_per_action_layout.addWidget(label)
        self.sm_measurements_per_action_lineedit = QtWidgets.QLineEdit()
        self.sm_measurements_per_action_lineedit.setText('{0}'.format(self._params[modenum]['measurements_per_action']))
        self.sm_measurements_per_action_lineedit.editingFinished.connect(lambda: self.sm_measurements_per_action_changed(modenum)) # Use lambda if you have some arguements for the function
        sm_measurements_per_action_layout.addWidget(self.sm_measurements_per_action_lineedit)

        # delete button
        sm_delete_button_layout = QtWidgets.QHBoxLayout()
        delete_button = QtWidgets.QPushButton('Delete')
        delete_button.setCheckable(True)
        delete_button.clicked.connect(self.customscan_delete)
        sm_delete_button_layout.addWidget(delete_button)

        # motor_layout
        sm_motor_layout = QtWidgets.QHBoxLayout()
        label = QtWidgets.QLabel('step_motor_number')
        sm_motor_layout.addWidget(label)
        self.sm_step_motor_number_lineedit = QtWidgets.QLineEdit()
        self.sm_step_motor_number_lineedit.setText('{0}'.format(self._params[modenum]['step_motor_number']))
        self.sm_step_motor_number_lineedit.editingFinished.connect(lambda: self.sm_step_motor_number_changed(modenum))
        sm_motor_layout.addWidget(self.sm_step_motor_number_lineedit)


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

        sm_layout = QtWidgets.QGridLayout()
        sm_layout.addLayout(sm_measurements_per_action_layout, 0, 0, 1, 5)
        sm_layout.addLayout(sm_delete_button_layout, 0, 6, 1, 1)
        sm_layout.addLayout(sm_motor_layout, 1, 0, 1, 7)

        value = self._customscan_mode[modenum]
        sm_groupbox = QtWidgets.QGroupBox(value)
        sm_groupbox.setLayout(sm_layout)
        self._customscan_del_button_hashmap[delete_button] = {'mode':modenum, 'groupbox': sm_groupbox}

        return sm_groupbox

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

        # realpower_to_readout_ratio_layout
        pr_realpower_to_readout_ratio_layout = QtWidgets.QHBoxLayout()
        HSpacer = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        pr_realpower_to_readout_ratio_layout.addItem(HSpacer)
        label = QtWidgets.QLabel('realpower_to_readout_ratio')
        pr_realpower_to_readout_ratio_layout.addWidget(label)
        self.pr_realpower_to_readout_ratio_lineedit = QtWidgets.QLineEdit()
        self.pr_realpower_to_readout_ratio_lineedit.setText('{0}'.format(self._params[modenum]['measurements_per_action']))
        self.pr_realpower_to_readout_ratio_lineedit.editingFinished.connect(lambda: self.pr_realpower_to_readout_ratio_changed(modenum))
        pr_realpower_to_readout_ratio_layout.addWidget(self.pr_realpower_to_readout_ratio_lineedit)

        # delete button
        pr_delete_button_layout = QtWidgets.QHBoxLayout()
        delete_button = QtWidgets.QPushButton('Delete')
        delete_button.setCheckable(True)
        delete_button.clicked.connect(self.customscan_delete)
        pr_delete_button_layout.addWidget(delete_button)


        # motor_layout
        pr_motor_layout = QtWidgets.QHBoxLayout()
        label = QtWidgets.QLabel('motor_on')
        pr_motor_layout.addWidget(label)
        self.pr_motor_on_checkbox = QtWidgets.QCheckBox()
        self.pr_motor_on_checkbox.setChecked(self._params[modenum]['motor_on'])
        self.pr_motor_on_checkbox.stateChanged.connect(lambda: self.pr_motor_on_changed(modenum))
        pr_motor_layout.addWidget(self.pr_motor_on_checkbox)

        label = QtWidgets.QLabel('step_motor_number')
        pr_motor_layout.addWidget(label)
        self.pr_step_motor_number_lineedit = QtWidgets.QLineEdit()
        self.pr_step_motor_number_lineedit.setText('{0}'.format(self._params[modenum]['step_motor_number']))
        self.pr_step_motor_number_lineedit.editingFinished.connect(lambda: self.pr_step_motor_number_changed(modenum))
        pr_motor_layout.addWidget(self.pr_step_motor_number_lineedit)        

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
        pr_layout.addLayout(pr_realpower_to_readout_ratio_layout, 0, 2, 1, 2)
        pr_layout.addLayout(pr_averages_layout, 0, 4, 1, 2)
        pr_layout.addLayout(pr_delete_button_layout, 0, 6, 1, 2)
        pr_layout.addLayout(pr_motor_layout, 1, 0, 1, 8)

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
        # mode num
        modenum = 3

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
        self.ss_measurements_per_action_lineedit.editingFinished.connect(lambda: self.ss_measurements_per_action_changed(modenum)) # Use lambda if you have some arguements for the function
        ss_measurements_per_action_layout.addWidget(self.ss_measurements_per_action_lineedit)

        # delete button
        ss_delete_button_layout = QtWidgets.QHBoxLayout()
        delete_button = QtWidgets.QPushButton('Delete')
        delete_button.setCheckable(True)
        delete_button.clicked.connect(self.customscan_delete)
        ss_delete_button_layout.addWidget(delete_button)

        # voltage source layout
        ss_voltage_layout = QtWidgets.QHBoxLayout()

        label = QtWidgets.QLabel('start_V')
        ss_voltage_layout.addWidget(label)
        self.ss_start_V_lineedit = QtWidgets.QLineEdit()
        self.ss_start_V_lineedit.setText('{0}'.format(self._params[modenum]['start_V']))
        self.ss_start_V_lineedit.editingFinished.connect(lambda: self.ss_start_V_changed(modenum))
        ss_voltage_layout.addWidget(self.ss_start_V_lineedit)

        label = QtWidgets.QLabel('step_V')
        ss_voltage_layout.addWidget(label)
        self.ss_step_V_lineedit = QtWidgets.QLineEdit()
        self.ss_step_V_lineedit.setText('{0}'.format(self._params[modenum]['step_V']))
        self.ss_step_V_lineedit.editingFinished.connect(lambda: self.ss_step_V_changed(modenum))
        ss_voltage_layout.addWidget(self.ss_step_V_lineedit)    

        ss_layout = QtWidgets.QGridLayout()
        ss_layout.addLayout(ss_measurements_per_action_layout, 0, 0, 1, 3)
        ss_layout.addLayout(ss_delete_button_layout, 0, 5, 1, 1)
        ss_layout.addLayout(ss_voltage_layout, 1, 0, 1, 4)

        value = self._customscan_mode[modenum]
        ss_groupbox = QtWidgets.QGroupBox(value)
        ss_groupbox.setLayout(ss_layout)
        self._customscan_del_button_hashmap[delete_button] = {'mode':modenum, 'groupbox': ss_groupbox}

        return ss_groupbox        

    def scan_trigger_layout(self):

        # mode num
        modenum = 4

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
        delete_button.clicked.connect(self.customscan_delete)
        st_delete_button_layout.addWidget(delete_button)

 

        st_layout = QtWidgets.QGridLayout()
        st_layout.addLayout(st_setting_layout, 0, 0, 1, 4)
        st_layout.addLayout(st_delete_button_layout, 0, 5, 1, 1)

        value = self._customscan_mode[modenum]
        st_groupbox = QtWidgets.QGroupBox(value)
        st_groupbox.setLayout(st_layout)
        self._customscan_del_button_hashmap[delete_button] = {'mode':modenum, 'groupbox': st_groupbox}

        return st_groupbox
    

    def timetagger_writeintofile_layout(self):
        # mode num
        modenum = 5

        font = QtGui.QFont()
        font.setBold(True)  

        # measurements_per_action_layout
        tw_setting_layout = QtWidgets.QHBoxLayout()
        label = QtWidgets.QLabel('Measurements per action')
        tw_setting_layout.addWidget(label)
        self.tw_measurements_per_action_lineedit = QtWidgets.QLineEdit()
        self.tw_measurements_per_action_lineedit.setText('{0}'.format(self._params[modenum]['measurements_per_action']))
        self.tw_measurements_per_action_lineedit.editingFinished.connect(lambda: self.tw_measurements_per_action_changed(modenum)) # Use lambda if you have some arguements for the function
        tw_setting_layout.addWidget(self.tw_measurements_per_action_lineedit)

        label = QtWidgets.QLabel('sample_name')
        tw_setting_layout.addWidget(label)
        self.tw_sample_name_lineedit = QtWidgets.QLineEdit()
        self.tw_sample_name_lineedit.setText('{0}'.format(self._params[modenum]['sample_name']))
        self.tw_sample_name_lineedit.editingFinished.connect(lambda: self.tw_sample_name_changed(modenum))
        tw_setting_layout.addWidget(self.tw_sample_name_lineedit)

        # delete button
        tw_delete_button_layout = QtWidgets.QHBoxLayout()
        delete_button = QtWidgets.QPushButton('Delete')
        delete_button.setCheckable(True)
        delete_button.clicked.connect(self.customscan_delete)
        tw_delete_button_layout.addWidget(delete_button)

        tw_layout = QtWidgets.QGridLayout()
        tw_layout.addLayout(tw_setting_layout, 0, 0, 1, 4)
        tw_layout.addLayout(tw_delete_button_layout, 0, 5, 1, 1)

        value = self._customscan_mode[modenum]
        tw_groupbox = QtWidgets.QGroupBox(value)
        tw_groupbox.setLayout(tw_layout)
        self._customscan_del_button_hashmap[delete_button] = {'mode':modenum, 'groupbox': tw_groupbox}

        return tw_groupbox
    

    def customscan_delete(self):
        mode = self._customscan_del_button_hashmap[self.sender()]['mode']
        groupbox = self._customscan_del_button_hashmap[self.sender()]['groupbox']

        self._current_modes.remove(mode)
        self.dynamic_layout.removeWidget(groupbox)
        groupbox.deleteLater()
        groupbox = None



    def sm_measurements_per_action_changed(self, modenum):
        self._params[modenum]['measurements_per_action'] = int(self.sm_measurements_per_action_lineedit.text())

    def sm_step_motor_number_changed(self, modenum):
        self._params[modenum]['step_motor_number'] = int(self.sm_step_motor_number_lineedit.text())        

    def sm_motor_channel_changed(self, modenum):
        self._params[modenum]['motor_channel'] = int(self.sm_motor_channel_lineedit.text())

    def sm_start_deg_changed(self, modenum):
        self._params[modenum]['start_deg'] = float(self.sm_start_deg_lineedit.text())

    def sm_step_deg_changed(self, modenum):
        self._params[modenum]['step_deg'] = float(self.sm_step_deg_lineedit.text())


    def pr_measurements_per_action_changed(self, modenum):
        self._params[modenum]['measurements_per_action'] = int(self.pr_measurements_per_action_lineedit.text())

    def pr_realpower_to_readout_ratio_changed(self, modenum):
        self._params[modenum]['realpower_to_readout_ratio'] = float(self.pr_realpower_to_readout_ratio_lineedit.text())

    def pr_averages_changed(self, modenum):
        self._params[modenum]['averages'] = int(self.pr_averages_lineedit.text())

    def pr_motor_on_changed(self, modenum):
        self._params[modenum]['motor_on'] = self.pr_motor_on_checkbox.isChecked()

    def pr_step_motor_number_changed(self, modenum):
        self._params[modenum]['step_motor_number'] = int(self.pr_step_motor_number_lineedit.text())

    def pr_motor_channel_changed(self, modenum):
        self._params[modenum]['motor_channel'] = int(self.pr_motor_channel_lineedit.text())

    def pr_idle_deg_changed(self, modenum):
        self._params[modenum]['idle_deg'] = float(self.pr_idle_deg_lineedit.text())

    def pr_running_deg_changed(self, modenum):
        self._params[modenum]['running_deg'] = float(self.pr_running_deg_lineedit.text())
        

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
        self._params[modenum]['shutter_channels'][0] = str(self.eit_shutter_channels_lineedit.text())


    def ss_measurements_per_action_changed(self, modenum):
        self._params[modenum]['measurements_per_action'] = int(self.ss_measurements_per_action_lineedit.text())

    def ss_start_V_changed(self, modenum):
        self._params[modenum]['start_V'] = float(self.ss_start_V_lineedit.text())

    def ss_step_V_changed(self, modenum):
        self._params[modenum]['step_V'] = float(self.ss_step_V_lineedit.text())

    def st_trigger_channel_changed(self, modenum):
        self._params[modenum]['trigger_channel'][0] = str(self.st_trigger_channel_lineedit.text())

    def st_trigger_length_changed(self, modenum):
        self._params[modenum]['trigger_length'] = str(self.st_trigger_length_lineedit.text())        

    def tw_measurements_per_action_changed(self, modenum):
        self._params[modenum]['measurements_per_action'] = int(self.tw_measurements_per_action_lineedit.text())

    def tw_sample_name_changed(self, modenum):
        self._params[modenum]['sample_name'] = str(self.tw_sample_name_lineedit .text())



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
