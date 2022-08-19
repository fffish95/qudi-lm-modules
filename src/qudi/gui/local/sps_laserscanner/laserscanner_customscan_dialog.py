from PySide2 import QtCore, QtGui, QtWidgets
import copy



class LaserscannerCustomScanDialog(QtWidgets.QDialog):
    """
    """

    def __init__(self, power_record, PowerRecordParams, current, measurements_per_action, CustomScanMode, Params):
        super().__init__()
        self.setObjectName('customscan_settings_dialog')
        self.setWindowTitle('Customscan Settings')

        self.settings_widget = LaserscannerCustomScanWidget( power_record = power_record, PowerRecordParams = PowerRecordParams, current = current, measurements_per_action = measurements_per_action, CustomScanMode = CustomScanMode, Params = Params)
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

    def __init__(self, *args, power_record, PowerRecordParams, current, measurements_per_action, CustomScanMode, Params, **kwargs):
        super().__init__(*args, **kwargs)

        self._power_record = power_record
        self._powerrecord_params = copy.deepcopy(PowerRecordParams)
        self._current_customscan_mode = current
        self._measurements_per_action = measurements_per_action
        self._customscan_mode = CustomScanMode
        self._params = copy.deepcopy(Params)
        font = QtGui.QFont()
        font.setBold(True)

        # power record
        power_record_radio_button_layout = QtWidgets.QHBoxLayout()
        self.power_record_radio_button = QtWidgets.QRadioButton('Record power')
        self.power_record_radio_button.setChecked(self._power_record)
        self.power_record_radio_button.toggled.connect(
            self.power_record_radio_button_changed
        )
        power_record_radio_button_layout.addWidget(self.power_record_radio_button)
        HSpacer = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        power_record_radio_button_layout.addItem(HSpacer)

        power_record_averages_layout = QtWidgets.QHBoxLayout()
        HSpacer = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        power_record_averages_layout.addItem(HSpacer)
        label = QtWidgets.QLabel('Averages:')
        power_record_averages_layout.addWidget(label)
        self.power_record_averages_lineedit = QtWidgets.QLineEdit()
        self.power_record_averages_lineedit.setText('{0}'.format(self._powerrecord_params['averages']))
        self.power_record_averages_lineedit.editingFinished.connect(self.power_record_averages_changed)
        power_record_averages_layout.addWidget(self.power_record_averages_lineedit)

        power_record_motor_layout = QtWidgets.QHBoxLayout()
        label = QtWidgets.QLabel('motor_channel')
        power_record_motor_layout.addWidget(label)
        self.pr_motor_channel_lineedit = QtWidgets.QLineEdit()
        self.pr_motor_channel_lineedit.setText('{0}'.format(self._powerrecord_params['motor_channel']))
        self.pr_motor_channel_lineedit.editingFinished.connect(self.pr_motor_channel_changed)
        power_record_motor_layout.addWidget(self.pr_motor_channel_lineedit)

        label = QtWidgets.QLabel('idle_deg')
        power_record_motor_layout.addWidget(label)
        self.pr_idle_deg_lineedit = QtWidgets.QLineEdit()
        self.pr_idle_deg_lineedit.setText('{0}'.format(self._powerrecord_params['idle_deg']))
        self.pr_idle_deg_lineedit.editingFinished.connect(self.pr_idle_deg_changed)
        power_record_motor_layout.addWidget(self.pr_idle_deg_lineedit)

        label = QtWidgets.QLabel('running_deg')
        power_record_motor_layout.addWidget(label)
        self.pr_running_deg_lineedit = QtWidgets.QLineEdit()
        self.pr_running_deg_lineedit.setText('{0}'.format(self._powerrecord_params['running_deg']))
        self.pr_running_deg_lineedit.editingFinished.connect(self.pr_running_deg_changed)
        power_record_motor_layout.addWidget(self.pr_running_deg_lineedit)    




        # custom scan
        measurements_per_action_layout = QtWidgets.QHBoxLayout()
        HSpacer = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        measurements_per_action_layout.addItem(HSpacer)
        label = QtWidgets.QLabel('Measurements per action')
        measurements_per_action_layout.addWidget(label)
        self.measurements_per_action_lineedit = QtWidgets.QLineEdit()
        self.measurements_per_action_lineedit.setText('{0}'.format(self._measurements_per_action))
        self.measurements_per_action_lineedit.editingFinished.connect(self.measurements_per_action_changed)
        measurements_per_action_layout.addWidget(self.measurements_per_action_lineedit)

        customscan_mode_layout = QtWidgets.QHBoxLayout()
        HSpacer = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        customscan_mode_layout.addItem(HSpacer)
        label = QtWidgets.QLabel('Custom scan mode')
        customscan_mode_layout.addWidget(label)
        self.customscan_mode_combobox = QtWidgets.QComboBox()
        for n, name in enumerate(self._customscan_mode):
            self.customscan_mode_combobox.addItem(str(name), n)
        self.customscan_mode_combobox.setCurrentIndex(self._current_customscan_mode)
        self.customscan_mode_combobox.activated.connect(self.update_dynamic_layout)
        customscan_mode_layout.addWidget(self.customscan_mode_combobox)

        self.dynamic_layout = QtWidgets.QGridLayout()
        self.update_dynamic_layout()

        powerrecord_layout = QtWidgets.QGridLayout()
        powerrecord_layout.addLayout(power_record_radio_button_layout, 0, 0, 1, 1)
        powerrecord_layout.addLayout(power_record_averages_layout, 0, 1, 1, 2)
        powerrecord_layout.addLayout(power_record_motor_layout, 1, 0, 1, 3)

        powerrecord_groupbox = QtWidgets.QGroupBox('Power record')
        powerrecord_groupbox.setFont(font)
        powerrecord_groupbox.setLayout(powerrecord_layout)

        customscan_layout = QtWidgets.QGridLayout()
        customscan_layout.addLayout(measurements_per_action_layout, 0, 0, 1, 2)
        customscan_layout.addLayout(customscan_mode_layout, 0, 2, 1, 4)
        customscan_layout.addLayout(self.dynamic_layout, 1, 0, 1, 6)

        customscan_groupbox = QtWidgets.QGroupBox('Custom Scan')
        customscan_groupbox.setFont(font)
        customscan_groupbox.setLayout(customscan_layout)

        self.setLayout(QtWidgets.QGridLayout())
        self.layout().addWidget(powerrecord_groupbox,0,0,2,60)
        self.layout().addWidget(customscan_groupbox,2,0,40,60)




    def update_dynamic_layout(self):
        self._current_customscan_mode = self.customscan_mode_combobox.currentIndex()
        self.deleteItemsOfLayout(self.dynamic_layout)
        value = self._customscan_mode[self._current_customscan_mode]
        func_map = {
            self._customscan_mode[0]: self.method_0_layout,
            self._customscan_mode[1]: self.method_1_layout,
            self._customscan_mode[2]: self.method_2_layout,
        }
        func = func_map.get(value)
        func()


    def method_0_layout(self):
        font = QtGui.QFont()
        font.setBold(True)
        layout = QtWidgets.QHBoxLayout()
        label = QtWidgets.QLabel('motor_channel')
        layout.addWidget(label)
        self.ss_motor_channel_lineedit = QtWidgets.QLineEdit()
        self.ss_motor_channel_lineedit.setText('{0}'.format(self._params[0]['motor_channel']))
        self.ss_motor_channel_lineedit.editingFinished.connect(self.ss_motor_channel_changed)
        layout.addWidget(self.ss_motor_channel_lineedit)

        label = QtWidgets.QLabel('start_deg')
        layout.addWidget(label)
        self.ss_start_deg_lineedit = QtWidgets.QLineEdit()
        self.ss_start_deg_lineedit.setText('{0}'.format(self._params[0]['start_deg']))
        self.ss_start_deg_lineedit.editingFinished.connect(self.ss_start_deg_changed)
        layout.addWidget(self.ss_start_deg_lineedit)

        label = QtWidgets.QLabel('step_deg')
        layout.addWidget(label)
        self.ss_step_deg_lineedit = QtWidgets.QLineEdit()
        self.ss_step_deg_lineedit.setText('{0}'.format(self._params[0]['step_deg']))
        self.ss_step_deg_lineedit.editingFinished.connect(self.ss_step_deg_changed)
        layout.addWidget(self.ss_step_deg_lineedit)    

        self.dynamic_layout.addLayout(layout, 0, 0, 1, 6)

    def method_1_layout(self):
        pass

    def method_2_layout(self):
        pass



    def power_record_radio_button_changed(self):
        self._power_record = self.power_record_radio_button.isChecked()

    def power_record_averages_changed(self):
        self._powerrecord_params['averages'] = int(self.power_record_averages_lineedit.text())

    def pr_motor_channel_changed(self):
        self._powerrecord_params['motor_channel'] = int(self.pr_motor_channel_lineedit.text())

    def pr_idle_deg_changed(self):
        self._powerrecord_params['idle_deg'] = int(self.pr_idle_deg_lineedit.text())

    def pr_running_deg_changed(self):
        self._powerrecord_params['running_deg'] = int(self.pr_running_deg_lineedit.text())

    def measurements_per_action_changed(self):
        self._measurements_per_action = int(self.measurements_per_action_lineedit.text())

    def ss_motor_channel_changed(self):
        self._params[0]['motor_channel'] = int(self.ss_motor_channel_lineedit.text())

    def ss_start_deg_changed(self):
        self._params[0]['start_deg'] = int(self.ss_start_deg_lineedit.text())

    def ss_step_deg_changed(self):
        self._params[0]['step_deg'] = int(self.ss_step_deg_lineedit.text())





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

    def power_measurement(self):
        pass