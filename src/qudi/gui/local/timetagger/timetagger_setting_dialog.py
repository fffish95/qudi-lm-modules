
from PySide2 import QtCore, QtGui, QtWidgets
import copy


class TimetaggerSettingDialog(QtWidgets.QDialog):
    """
    """

    def __init__(self, channel_codes, refresh_time, corr_params, hist_params):
        super().__init__()
        self.setObjectName('timetagger_settings_dialog')
        self.setWindowTitle('Timetagger Settings')

        self.settings_widget = TimetaggerSettingsWidget(channel_codes = channel_codes, refresh_time = refresh_time, corr_params = corr_params, hist_params = hist_params)
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


class TimetaggerSettingsWidget(QtWidgets.QWidget):
    """ Widget containing infrequently used scanner settings
    """

    def __init__(self, *args, channel_codes, refresh_time, corr_params, hist_params, **kwargs):
        super().__init__(*args, **kwargs)

        self._channel_codes = copy.deepcopy(channel_codes)
        self._refresh_time = refresh_time
        self._corr_params = copy.deepcopy(corr_params)
        self._hist_params = copy.deepcopy(hist_params)


        font = QtGui.QFont()
        font.setBold(True)
        refresh_time_layout = QtWidgets.QHBoxLayout()
        HSpacer = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        refresh_time_layout.addItem(HSpacer)
        label = QtWidgets.QLabel('Refresh time (ms)')
        refresh_time_layout.addWidget(label)
        self.refresh_time_lineedit = QtWidgets.QLineEdit()
        self.refresh_time_lineedit.setText('{0}'.format(self._refresh_time))
        self.refresh_time_lineedit.editingFinished.connect(self.refresh_time_changed)
        refresh_time_layout.addWidget(self.refresh_time_lineedit)


        self.corr_channels_layout = QtWidgets.QGridLayout()
        label = QtWidgets.QLabel('Start Channel:')
        label.setFont(font)
        label.setAlignment(QtCore.Qt.AlignCenter)
        self.corr_channels_layout.addWidget(label, 0, 0)

        label = QtWidgets.QLabel('Stop Channel:')
        label.setFont(font)
        label.setAlignment(QtCore.Qt.AlignCenter)
        self.corr_channels_layout.addWidget(label, 0, 1)

        self.corr_channels_start_combobox = QtWidgets.QComboBox()
        self.corr_channels_stop_combobox = QtWidgets.QComboBox()
        for n, key in enumerate(self._channel_codes.keys()):
            self.corr_channels_start_combobox.addItem(str(key), n)
            self.corr_channels_stop_combobox.addItem(str(key), n)          
        self.corr_channels_layout.addWidget(self.corr_channels_start_combobox, 1, 0)
        self.corr_channels_layout.addWidget(self.corr_channels_stop_combobox, 1, 1)
        corr_channels_add_button = QtWidgets.QPushButton('Add')
        corr_channels_add_button.setCheckable(True)
        corr_channels_add_button.clicked.connect(self.corr_channels_add)
        self.corr_channels_layout.addWidget(corr_channels_add_button, 1, 2)

        self.corr_channels_dynamic_layout = QtWidgets.QGridLayout()
        self.update_corr_channels_display()
        self.corr_channels_layout.addLayout(self.corr_channels_dynamic_layout, 2, 0, 1, 3)
        verticalSpacer = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.corr_channels_layout.addItem(verticalSpacer)


        self.hist_channels_layout = QtWidgets.QGridLayout()
        label = QtWidgets.QLabel('Channel:')
        label.setFont(font)
        label.setAlignment(QtCore.Qt.AlignCenter)
        self.hist_channels_layout.addWidget(label, 0, 0)

        label = QtWidgets.QLabel('Trigger Channel:')
        label.setFont(font)
        label.setAlignment(QtCore.Qt.AlignCenter)
        self.hist_channels_layout.addWidget(label, 0, 1)

        self.hist_channels_select_combobox = QtWidgets.QComboBox()
        self.hist_channels_trigger_combobox = QtWidgets.QComboBox()
        for n, key in enumerate(self._channel_codes.keys()):
            self.hist_channels_select_combobox.addItem(str(key), n)
            self.hist_channels_trigger_combobox.addItem(str(key), n)          
        self.hist_channels_layout.addWidget(self.hist_channels_select_combobox, 1, 0)
        self.hist_channels_layout.addWidget(self.hist_channels_trigger_combobox, 1, 1)
        hist_channels_add_button = QtWidgets.QPushButton('Add')
        hist_channels_add_button.setCheckable(True)
        hist_channels_add_button.clicked.connect(self.hist_channels_add)
        self.hist_channels_layout.addWidget(hist_channels_add_button, 1, 2)

        self.hist_channels_dynamic_layout = QtWidgets.QGridLayout()
        self.update_hist_channels_display()
        self.hist_channels_layout.addLayout(self.hist_channels_dynamic_layout, 2, 0, 1, 3)
        verticalSpacer = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.hist_channels_layout.addItem(verticalSpacer)

        corr_groupbox = QtWidgets.QGroupBox('Autocorrelation channels')
        corr_groupbox.setFont(font)
        corr_groupbox.setLayout(self.corr_channels_layout)

        hist_groupbox = QtWidgets.QGroupBox('Histogram channels')
        hist_groupbox.setFont(font)
        hist_groupbox.setLayout(self.hist_channels_layout)

        refresh_time_frame = QtWidgets.QFrame()
        refresh_time_frame.setFont(font)
        refresh_time_frame.setLayout(refresh_time_layout)

        self.setLayout(QtWidgets.QGridLayout())
        self.layout().addWidget(refresh_time_frame,0,0,1,60)
        self.layout().addWidget(corr_groupbox,1,0,40,60)
        self.layout().addWidget(hist_groupbox,42,0,40,60)
    
    def update_corr_channels_display(self):
        
        font = QtGui.QFont()
        font.setBold(True)
        self._corr_del_button_hashmap = dict()
        self.deleteItemsOfLayout(self.corr_channels_dynamic_layout)
        for n, key in enumerate(self._corr_params.keys()):
            layout = QtWidgets.QHBoxLayout()

            label = QtWidgets.QLabel(str(self._corr_params[key]['channel_start']))
            label.setFont(font)
            label.setAlignment(QtCore.Qt.AlignCenter)
            layout.addWidget(label)

            label = QtWidgets.QLabel(str(self._corr_params[key]['channel_stop']))
            label.setFont(font)
            label.setAlignment(QtCore.Qt.AlignCenter)
            layout.addWidget(label)

            delete_button = QtWidgets.QPushButton('Delete')
            delete_button.setCheckable(True)
            delete_button.clicked.connect(self.corr_channels_delete)
            layout.addWidget(delete_button)

            self._corr_del_button_hashmap[delete_button] = {'key':key, 'layout': layout}

            self.corr_channels_dynamic_layout.addLayout(layout, n, 0, 1, 3)

        
    def update_hist_channels_display(self):
        font = QtGui.QFont()
        font.setBold(True)
        self._hist_del_button_hashmap = dict()
        self.deleteItemsOfLayout(self.hist_channels_dynamic_layout)
        for n, key in enumerate(self._hist_params.keys()):
            layout = QtWidgets.QHBoxLayout()

            label = QtWidgets.QLabel(str(self._hist_params[key]['channel']))
            label.setFont(font)
            label.setAlignment(QtCore.Qt.AlignCenter)
            layout.addWidget(label)

            label = QtWidgets.QLabel(str(self._hist_params[key]['trigger_channel']))
            label.setFont(font)
            label.setAlignment(QtCore.Qt.AlignCenter)
            layout.addWidget(label)

            delete_button = QtWidgets.QPushButton('Delete')
            delete_button.setCheckable(True)
            delete_button.clicked.connect(self.hist_channels_delete)
            layout.addWidget(delete_button)

            self._hist_del_button_hashmap[delete_button] = {'key':key, 'layout': layout}

            self.hist_channels_dynamic_layout.addLayout(layout, n, 0, 1, 3)

    def refresh_time_changed(self):
        self._refresh_time = int(self.refresh_time_lineedit.text())

    def corr_channels_add(self):
        channel_start = str(self.corr_channels_start_combobox.currentText())
        channel_stop = str(self.corr_channels_stop_combobox.currentText())
        key = channel_start + '-' + channel_stop
        if key in self._corr_params:
            return
        self._corr_params[key] = {'channel_start':self._channel_codes[channel_start], 'channel_stop': self._channel_codes[channel_stop]}
        self.update_corr_channels_display()

    def hist_channels_add(self):
        font = QtGui.QFont()
        font.setBold(True)
        row = len(self._hist_params) + 2
        channel_select = str(self.hist_channels_select_combobox.currentText())
        channel_trigger = str(self.hist_channels_trigger_combobox.currentText())
        key = channel_select + '-' + channel_trigger
        if key in self._hist_params:
            return
        self._hist_params[key] = {'channel':self._channel_codes[channel_select], 'trigger_channel': self._channel_codes[channel_trigger]}
        self.update_hist_channels_display()

    def corr_channels_delete(self):
        if len(self._corr_params) == 1: # Will cause problem, if _****_params is empty; there will be no stored information about binwidth and binnumbers.
            return
        key = self._corr_del_button_hashmap[self.sender()]['key']
        layout = self._corr_del_button_hashmap[self.sender()]['layout']

        self._corr_params.pop(key)
        self.deleteItemsOfLayout(layout)

    def hist_channels_delete(self):
        if len(self._hist_params) == 1: # Will cause problem, if _****_params is empty; there will be no stored information about binwidth and binnumbers.
            return
        key = self._hist_del_button_hashmap[self.sender()]['key']
        layout = self._hist_del_button_hashmap[self.sender()]['layout']

        self._hist_params.pop(key)
        self.deleteItemsOfLayout(layout)

    
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