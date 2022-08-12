from PySide2 import QtCore, QtGui, QtWidgets
import copy



class TimetaggerWriteintofileChannelsDialog(QtWidgets.QDialog):
    """
    """

    def __init__(self, channel_codes, writeintofile_params):
        super().__init__()
        self.setObjectName('timetagger_writeintofile_channels_dialog')
        self.setWindowTitle('Timetagger Writeintofile Channels')

        self.settings_widget = TimetaggerWriteintofileChannelsWidget(channel_codes = channel_codes, writeintofile_params = writeintofile_params)
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

class TimetaggerWriteintofileChannelsWidget(QtWidgets.QWidget):
    """ Widget containing infrequently used scanner settings
    """

    def __init__(self, *args, channel_codes, writeintofile_params, **kwargs):
        super().__init__(*args, **kwargs)

        self._channel_codes = copy.deepcopy(channel_codes)
        self._writeintofile_params = copy.deepcopy(writeintofile_params)

        font = QtGui.QFont()
        font.setBold(True)

        self.trigger_channels_layout = QtWidgets.QGridLayout()
        label = QtWidgets.QLabel('Trigger Channel:')
        label.setFont(font)
        label.setAlignment(QtCore.Qt.AlignCenter)
        self.trigger_channels_layout.addWidget(label, 0, 0)

        self.trigger_channels_combobox = QtWidgets.QComboBox()
        for n, key in enumerate(self._channel_codes.keys()):
            self.trigger_channels_combobox.addItem(str(key), n)

        self.trigger_channels_layout.addWidget(self.trigger_channels_combobox, 1, 0)
        trigger_channels_add_button = QtWidgets.QPushButton('Add')
        trigger_channels_add_button.setCheckable(True)
        trigger_channels_add_button.clicked.connect(self.trigger_channels_add)
        self.trigger_channels_layout.addWidget(trigger_channels_add_button, 1, 1)

        self.trigger_channels_dynamic_layout = QtWidgets.QGridLayout()
        self.update_trigger_channels_display()
        self.trigger_channels_layout.addLayout(self.trigger_channels_dynamic_layout, 2, 0, 1, 2)
        verticalSpacer = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.trigger_channels_layout.addItem(verticalSpacer)
        
        self.filtered_channels_layout = QtWidgets.QGridLayout()
        label = QtWidgets.QLabel('Filtered Channel:')
        label.setFont(font)
        label.setAlignment(QtCore.Qt.AlignCenter)
        self.filtered_channels_layout.addWidget(label, 0, 0)

        self.filtered_channels_combobox = QtWidgets.QComboBox()
        for n, key in enumerate(self._channel_codes.keys()):
            self.filtered_channels_combobox.addItem(str(key), n)

        self.filtered_channels_layout.addWidget(self.filtered_channels_combobox, 1, 0)
        filtered_channels_add_button = QtWidgets.QPushButton('Add')
        filtered_channels_add_button.setCheckable(True)
        filtered_channels_add_button.clicked.connect(self.filtered_channels_add)
        self.filtered_channels_layout.addWidget(filtered_channels_add_button, 1, 1)


        self.filtered_channels_dynamic_layout = QtWidgets.QGridLayout()
        self.update_filtered_channels_display()
        self.filtered_channels_layout.addLayout(self.filtered_channels_dynamic_layout, 2, 0, 1, 2)
        verticalSpacer = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.filtered_channels_layout.addItem(verticalSpacer)

        trigger_groupbox = QtWidgets.QGroupBox('Trigger channels')
        trigger_groupbox.setFont(font)
        trigger_groupbox.setLayout(self.trigger_channels_layout)

        filtered_groupbox = QtWidgets.QGroupBox('Filtered channels')
        filtered_groupbox.setFont(font)
        filtered_groupbox.setLayout(self.filtered_channels_layout)

        self.setLayout(QtWidgets.QGridLayout())
        self.layout().addWidget(trigger_groupbox,0,0,40,60)
        self.layout().addWidget(filtered_groupbox,0,65,40,60)


    def trigger_channels_add(self):
        channel_add = str(self.trigger_channels_combobox.currentText())
        channel_add_code = self._channel_codes[channel_add]
        if channel_add_code in self._writeintofile_params['trigger']:
            return
        self._writeintofile_params['trigger'].append(channel_add_code)
        self.update_trigger_channels_display()

    def update_trigger_channels_display(self):

        font = QtGui.QFont()
        font.setBold(True)
        self._trigger_del_button_hashmap = dict()
        self.deleteItemsOfLayout(self.trigger_channels_dynamic_layout)
        for n, channel in enumerate(self._writeintofile_params['trigger']):
            layout = QtWidgets.QHBoxLayout()

            label = QtWidgets.QLabel(str(channel))
            label.setFont(font)
            label.setAlignment(QtCore.Qt.AlignCenter)
            layout.addWidget(label)

            delete_button = QtWidgets.QPushButton('Delete')
            delete_button.setCheckable(True)
            delete_button.clicked.connect(self.trigger_channels_delete)
            layout.addWidget(delete_button)

            self._trigger_del_button_hashmap[delete_button] = {'channel':channel, 'layout': layout}

            self.trigger_channels_dynamic_layout.addLayout(layout, n, 0, 1, 2)

    def trigger_channels_delete(self):
        channel = self._trigger_del_button_hashmap[self.sender()]['channel']
        layout = self._trigger_del_button_hashmap[self.sender()]['layout']

        self._writeintofile_params['trigger'].remove(channel)
        self.deleteItemsOfLayout(layout)


    def filtered_channels_add(self):
        channel_add = str(self.filtered_channels_combobox.currentText())
        channel_add_code = self._channel_codes[channel_add]
        if channel_add_code in self._writeintofile_params['filtered']:
            return
        self._writeintofile_params['filtered'].append(channel_add_code)
        self.update_filtered_channels_display()

    def update_filtered_channels_display(self):

        font = QtGui.QFont()
        font.setBold(True)
        self._filtered_del_button_hashmap = dict()
        self.deleteItemsOfLayout(self.filtered_channels_dynamic_layout)
        for n, channel in enumerate(self._writeintofile_params['filtered']):
            layout = QtWidgets.QHBoxLayout()

            label = QtWidgets.QLabel(str(channel))
            label.setFont(font)
            label.setAlignment(QtCore.Qt.AlignCenter)
            layout.addWidget(label)

            delete_button = QtWidgets.QPushButton('Delete')
            delete_button.setCheckable(True)
            delete_button.clicked.connect(self.filtered_channels_delete)
            layout.addWidget(delete_button)

            self._filtered_del_button_hashmap[delete_button] = {'channel':channel, 'layout': layout}

            self.filtered_channels_dynamic_layout.addLayout(layout, n, 0, 1, 2)

    def filtered_channels_delete(self):
        channel = self._filtered_del_button_hashmap[self.sender()]['channel']
        layout = self._filtered_del_button_hashmap[self.sender()]['layout']

        self._writeintofile_params['filtered'].remove(channel)
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