import numpy as np
import os
import pyqtgraph as pg
from enum import Enum

from collections import OrderedDict
from qudi.core.connector import Connector
from qudi.core.module import GuiBase
from PySide2 import QtCore, QtGui, QtWidgets
from qudi.util import uic
from qudi.util import config
from qudi.core.statusvariable import StatusVar
from qudi.gui.local.timetagger.timetagger_setting_dialog import TimetaggerSettingDialog
from qudi.gui.local.timetagger.timetagger_writechannels_dialog import TimetaggerWriteintofileChannelsDialog
import copy


class TimeTaggerMainWindow(QtWidgets.QMainWindow):
    """ Create the Main Window based on the *.ui file. """

    def __init__(self):
        # Get the path to the *.ui file
        this_dir = os.path.dirname(__file__)
        ui_file = os.path.join(this_dir, 'ui_timetaggergui.ui')

        # Load it
        super(TimeTaggerMainWindow, self).__init__()
        uic.loadUi(ui_file, self)
        self.show()

class SaveDialog(QtWidgets.QDialog):
    """ Dialog to provide feedback and block GUI while saving """
    def __init__(self, parent, title="Please wait", text="Saving..."):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setWindowModality(QtCore.Qt.WindowModal)
        self.setAttribute(QtCore.Qt.WA_ShowWithoutActivating)

        # Dialog layout
        self.text = QtWidgets.QLabel("<font size='16'>" + text + "</font>")
        self.hbox = QtWidgets.QHBoxLayout()
        self.hbox.addSpacerItem(QtWidgets.QSpacerItem(50, 0))
        self.hbox.addWidget(self.text)
        self.hbox.addSpacerItem(QtWidgets.QSpacerItem(50, 0))
        self.setLayout(self.hbox)

class LoadDialog(QtWidgets.QDialog):
    """ Dialog to provide feedback and block GUI while loading """
    def __init__(self, parent, title="Please wait", text="Loading..."):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setWindowModality(QtCore.Qt.WindowModal)
        self.setAttribute(QtCore.Qt.WA_ShowWithoutActivating)

        # Dialog layout
        self.text = QtWidgets.QLabel("<font size='16'>" + text + "</font>")
        self.hbox = QtWidgets.QHBoxLayout()
        self.hbox.addSpacerItem(QtWidgets.QSpacerItem(50, 0))
        self.hbox.addWidget(self.text)
        self.hbox.addSpacerItem(QtWidgets.QSpacerItem(50, 0))
        self.setLayout(self.hbox)


class TTGui(GuiBase):
    """
    """
    
    # declare connectors
    timetaggerlogic = Connector(interface='TimeTaggerLogic')
    savelogic = Connector(interface='SaveLogic')

    # status vars
    _autocorr_crosshair = StatusVar(default = True)
    _autocorr_crosshair_size = StatusVar(default=0.01)
    _autocorr_crosshair_X = StatusVar(default=0.0)
    _autocorr_crosshair_Y = StatusVar(default=0.0)
    _histogram_crosshair = StatusVar(default = True)
    _histogram_crosshair_size = StatusVar(default=0.01)
    _histogram_crosshair_X = StatusVar(default=0.0)
    _histogram_crosshair_Y = StatusVar(default=0.0)

    sigToggleCorr = QtCore.Signal()
    sigToggleHist = QtCore.Signal()
   
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def on_activate(self):
        """ Initializes all needed UI files and establishes the connectors.

        This method executes the all the inits for the differnt GUIs and passes
        the event argument from fysom to the methods.
        """
        # Getting an access to all connectors:
        self._timetagger_logic = self.timetaggerlogic()
        self._save_logic = self.savelogic()

        self.initMainUI()      # initialize the main GUI
        self.initSettingsUI()  # initialize the settings GUI
        self.initWriteintofileChannelsUI() 
        self._save_dialog = SaveDialog(self._mw)
        self._load_dialog = LoadDialog(self._mw) 

    def initMainUI(self):
        """ Definition, configuration and initialisation of the timetagger GUI.

        This init connects all the graphic modules, which were created in the
        *.ui file and configures the event handling between the modules.
        Moreover it sets default values.
        """
        self._mw = TimeTaggerMainWindow()

        ###################################################################
        #               Configuring the dock widgets                      #
        ###################################################################
        # All our gui elements are dockable, and so there should be no "central" widget.
        self._mw.centralwidget.hide()
        self._mw.setDockNestingEnabled(True)

        # always use first channel on startup, can be changed afterwards
        self._autocorr_channel = 0
        self._histogram_channel = 0

        # Get the plots for the display from the logic


        raw_data_autocorr_x = self._timetagger_logic.autocorr_x
        raw_data_autocorr_y = self._timetagger_logic.autocorr_y[self._autocorr_channel, :]



        raw_data_histogram_x = self._timetagger_logic.histogram_x
        raw_data_histogram_y = self._timetagger_logic.histogram_y[self._histogram_channel, :]



        # Load the plots in the display
        self.autocorr_plot = pg.PlotDataItem(
            raw_data_autocorr_x,
            raw_data_autocorr_y)

        self.histogram_plot = pg.PlotDataItem(
            raw_data_histogram_x,
            raw_data_histogram_y)
        
        # Add the display item to the VieWidget, which was defined in
        # the UI file.
        self._mw.autocorr_PlotWidget.addItem(self.autocorr_plot)
        self._mw.autocorr_PlotWidget.showGrid(x=True, y=True, alpha=0.8)
        self._mw.autocorr_PlotWidget.setLabel('left', 'Coincidence', units='a.u.')
        self._mw.autocorr_PlotWidget.setLabel('bottom', 'time', units='μs')

        self._mw.hist_PlotWidget.addItem(self.histogram_plot)
        self._mw.hist_PlotWidget.showGrid(x=True, y=True, alpha=0.8)
        self._mw.hist_PlotWidget.setLabel('left', 'Signal', units='a.u.')
        self._mw.hist_PlotWidget.setLabel('bottom', 'time', units='μs')
        # Set Cursor
        if self._autocorr_crosshair:
            self._mw.corrCrosshair_radioButton.setChecked(True)
        else:
            self._mw.corrCrosshair_radioButton.setChecked(False)
        self._mw.corrCrosshairSizedoubleSpinBox.setValue(self._autocorr_crosshair_size)
        self._mw.corrCrosshairXdoubleSpinBox.setValue(self._autocorr_crosshair_X)
        self._mw.corrCrosshairYdoubleSpinBox.setValue(self._autocorr_crosshair_Y)

        if self._histogram_crosshair:
            self._mw.histCrosshair_radioButton.setChecked(True)
        else:
            self._mw.histCrosshair_radioButton.setChecked(False)
        self._mw.histCrosshairSizedoubleSpinBox.setValue(self._histogram_crosshair_size)
        self._mw.histCrosshairXdoubleSpinBox.setValue(self._histogram_crosshair_X)
        self._mw.histCrosshairYdoubleSpinBox.setValue(self._histogram_crosshair_Y)     
        self.update_autocorr_crosshair_visibility()
        self.update_autocorr_crosshair_size()
        self.update_autocorr_crosshair_XY()
        self.update_histogram_crosshair_visibility()
        self.update_histogram_crosshair_size()
        self.update_histogram_crosshair_XY()


        self._mw.autocorr_PlotWidget.sigCrosshairDraggedPosChanged.connect(self.autocorr_update_from_roi_xy)
        self._mw.hist_PlotWidget.sigCrosshairDraggedPosChanged.connect(self.histogram_update_from_roi_xy)

        self._mw.corrCrosshair_radioButton.clicked.connect(self.update_autocorr_crosshair_visibility)
        self._mw.corrCrosshairSizedoubleSpinBox.editingFinished.connect(self.update_autocorr_crosshair_size)
        self._mw.corrCrosshairXdoubleSpinBox.editingFinished.connect(self.update_autocorr_crosshair_XY)
        self._mw.corrCrosshairYdoubleSpinBox.editingFinished.connect(self.update_autocorr_crosshair_XY)
        self._mw.histCrosshair_radioButton.clicked.connect(self.update_histogram_crosshair_visibility)
        self._mw.histCrosshairSizedoubleSpinBox.editingFinished.connect(self.update_histogram_crosshair_size)
        self._mw.histCrosshairXdoubleSpinBox.editingFinished.connect(self.update_histogram_crosshair_XY)
        self._mw.histCrosshairYdoubleSpinBox.editingFinished.connect(self.update_histogram_crosshair_XY)


        # Set the state button as ready button as default setting.
        self._mw.action_stop.setEnabled(False)

        # Set up and connect channel combobox
        self.setup_autocorr_combobox()
        self.setup_histogram_combobox()
        self._mw.corr_channels_ComboBox.activated.connect(self.update_autocorr_channel)
        self._mw.hist_channels_ComboBox.activated.connect(self.update_histogram_channel)

        # Take the default values from logic:

        self._mw.corrBinWidthDoubleSpinBox.setValue(list(self._timetagger_logic._autocorr_params.values())[0]['bins_width'])
        Record_length = float(list(self._timetagger_logic._autocorr_params.values())[0]['bins_width'] * list(self._timetagger_logic._autocorr_params.values())[0]['number_of_bins']/1000) 
        self._mw.corrRecordLengthDoubleSpinBox.setValue(Record_length)



        self._mw.histBinWidthDoubleSpinBox.setValue(list(self._timetagger_logic._histogram_params.values())[0]['bins_width'])
        Record_length = float(list(self._timetagger_logic._histogram_params.values())[0]['bins_width'] * list(self._timetagger_logic._histogram_params.values())[0]['number_of_bins']/1000) 
        self._mw.histRecordLengthDoubleSpinBox.setValue(Record_length)

        
        if self._timetagger_logic._autocorr_accumulate:
            self._mw.corr_accumulate_RadioButton.setChecked(True)
        else:
            self._mw.corr_refresh_RadioButton.setChecked(True)

        if self._timetagger_logic._histogram_accumulate:
            self._mw.hist_accumulate_RadioButton.setChecked(True)
        else:
            self._mw.hist_refresh_RadioButton.setChecked(True)

        # Update the inputed/displayed numbers if the cursor has left the field:
        self._mw.corrBinWidthDoubleSpinBox.editingFinished.connect(self.update_corrBinwidth)
        self._mw.corrRecordLengthDoubleSpinBox.editingFinished.connect(self.update_corrRecordlength)
        self._mw.histBinWidthDoubleSpinBox.editingFinished.connect(self.update_histBinwidth)
        self._mw.histRecordLengthDoubleSpinBox.editingFinished.connect(self.update_histRecordlength)
        self._mw.writeintofileTagLineEdit.editingFinished.connect(self.update_writeintofileTag)

        # Connect radiobutton
        self._mw.corr_accumulate_RadioButton.clicked.connect(self.corr_accumulate_RadioButton_clicked)
        self._mw.corr_refresh_RadioButton.clicked.connect(self.corr_refresh_RadioButton_clicked)
        self._mw.hist_accumulate_RadioButton.clicked.connect(self.hist_accumulate_RadioButton_clicked)
        self._mw.hist_refresh_RadioButton.clicked.connect(self.hist_refresh_RadioButton_clicked)

        #################################################################
        #                           Actions                             #
        #################################################################
        # Connect the scan actions to the events if they are clicked. 
        self._mw.action_stop.triggered.connect(self.stop_clicked)

        self._start_proxy = pg.SignalProxy(
            self._mw.action_start.triggered,
            delay=0.1,
            slot=self.start_clicked
            )
        
        self._writeintofile_proxy = pg.SignalProxy(
            self._mw.writeintoFile_PushButton.clicked,
            delay = 0.1,
            slot = self.writeintofile_clicked
        )

        # Connect the emitted signal of an image change from the logic with
        self._timetagger_logic.signal_plots_updated.connect(self.refresh_plots)
        self._timetagger_logic.signal_writeintofile_updated.connect(self.refresh_writeintofilestatus)

        # Connect other signals from the logic with an update of the gui
        self._timetagger_logic.signal_save_started.connect(self.logic_started_save)
        self._timetagger_logic.signal_save_ended.connect(self.logic_finished_save)


        # Connect the 'File' Menu dialog and the Settings window in confocal
        # with the methods:
        self._mw.action_Settings.triggered.connect(self.menu_settings)
        self._mw.actionSave_images.triggered.connect(self.save_images)
        self._mw.actionSave_configuration.triggered.connect(self.save_configuration)
        self._mw.actionLoad_configuration.triggered.connect(self.load_configuration)
        self._mw.writeChannels_PushButton.clicked.connect(self.writeintofile_channels)

        # history actions
        self._mw.actionForward.triggered.connect(self.history_forward_clicked)
        self._mw.actionBack.triggered.connect(self.history_back_clicked)
        self._timetagger_logic.signal_history_event.connect(lambda: self.set_history_actions(True))
        self._timetagger_logic.signal_history_event.connect(self.history_event)
        self._timetagger_logic.signal_history_event.connect(self._mw.autocorr_PlotWidget.autoRange)
        self._timetagger_logic.signal_history_event.connect(self._mw.hist_PlotWidget.autoRange)
        self._timetagger_logic.signal_history_event.connect(self.setup_autocorr_combobox)
        self._timetagger_logic.signal_history_event.connect(self.setup_histogram_combobox)

        # all other components:
        self.enable_actions()
        self.refresh_plots()
        self.show()

    def show(self):
        """Make main window visible and put it above all other windows. """
        # Show the Main Confocal GUI:
        self._mw.show()
        self._mw.activateWindow()
        self._mw.raise_()

    def initSettingsUI(self):
        """ Definition, configuration and initialisation of the settings GUI.

        This init connects all the graphic modules, which were created in the
        *.ui file and configures the event handling between the modules.
        Moreover it sets default values if not existed in the logic modules.
        """
        # Create the Settings window
        self._sd = TimetaggerSettingDialog(channel_codes = self._timetagger_logic._timetagger.channel_codes, refresh_time = self._timetagger_logic._refresh_time, corr_params = self._timetagger_logic._autocorr_params, hist_params = self._timetagger_logic._histogram_params)

        # Connect the action of the settings window with the code:
        self._sd.button_box.accepted.connect(self.update_settings)
        self._sd.button_box.rejected.connect(self.keep_former_settings)

    def initWriteintofileChannelsUI(self):
        """ Definition, configuration and initialisation of the settings GUI.

        This init connects all the graphic modules, which were created in the
        *.ui file and configures the event handling between the modules.
        Moreover it sets default values if not existed in the logic modules.
        """
        # Create the Settings window
        self._wcd = TimetaggerWriteintofileChannelsDialog(channel_codes = self._timetagger_logic._timetagger.channel_codes, writeintofile_params = self._timetagger_logic._writeintofile_params)

        # Connect the action of the settings window with the code:
        self._wcd.button_box.accepted.connect(self.update_writeintofilechannels)
        self._wcd.button_box.rejected.connect(self.keep_former_writeintofilechannels)


    def on_deactivate(self):
        """ Reverse steps of activation

        @return int: error code (0:OK, -1:error)
        """
        self._mw.close()
        return 0


    def setup_autocorr_combobox(self):
        autocorr_channels = self._timetagger_logic._autocorr_params.keys()
        self._mw.corr_channels_ComboBox.clear()
        for n, ch in enumerate(autocorr_channels):
            self._mw.corr_channels_ComboBox.addItem(str(ch), n)

    def setup_histogram_combobox(self):
        histogram_channels = self._timetagger_logic._histogram_params.keys()
        self._mw.hist_channels_ComboBox.clear()
        for n, ch in enumerate(histogram_channels):
            self._mw.hist_channels_ComboBox.addItem(str(ch), n)
    
    def update_autocorr_channel(self, index):
        """ The displayed channel for autocorrelation was changed, refresh the displayed image.

            @param index int: index of selected channel item in combo box
        """
        self._autocorr_channel = int(self._mw.corr_channels_ComboBox.itemData(index, QtCore.Qt.UserRole))
        self.refresh_plots()

    def update_histogram_channel(self, index):
        """ The displayed channel for histogram was changed, refresh the displayed image.

            @param index int: index of selected channel item in combo box
        """
        self._histogram_channel = int(self._mw.hist_channels_ComboBox.itemData(index, QtCore.Qt.UserRole))
        self.refresh_plots()

    def update_corrBinwidth(self):
        corrBinwidth = self._mw.corrBinWidthDoubleSpinBox.value()
        for key, value in self._timetagger_logic._autocorr_params.items():
            value['bins_width'] = corrBinwidth

    def update_corrRecordlength(self):
        corrRecordlength = self._mw.corrRecordLengthDoubleSpinBox.value()

        corrNumberofbins = int(corrRecordlength * 1000 / list(self._timetagger_logic._autocorr_params.values())[0]['bins_width'])
        for key, value in self._timetagger_logic._autocorr_params.items():
            value['number_of_bins'] = corrNumberofbins

    def update_histBinwidth(self):
        histBinwidth = self._mw.histBinWidthDoubleSpinBox.value()
        for key, value in self._timetagger_logic._histogram_params.items():
            value['bins_width'] = histBinwidth

    def update_histRecordlength(self):
        histRecordlength = self._mw.histRecordLengthDoubleSpinBox.value()

        histNumberofbins = int(histRecordlength * 1000 / list(self._timetagger_logic._histogram_params.values())[0]['bins_width'])
        for key, value in self._timetagger_logic._histogram_params.items():
            value['number_of_bins'] = histNumberofbins

    def update_writeintofileTag(self):
        if len(self._mw.writeintofileTagLineEdit.text()) != 0:
            self._timetagger_logic._writeintofile_params['sample_name'] = self._mw.writeintofileTagLineEdit.text()
        else:
            self._timetagger_logic._writeintofile_params['sample_name'] = 'Sample1'

    def stop_clicked(self):
        """ Stop the measurement if the state has switched to ready. """
        if self._timetagger_logic.module_state() == 'locked':
            self._timetagger_logic.stop_measurement()
        # Disable the stop button
        self._mw.action_stop.setEnabled(False)
        self.enable_actions()
    
    def start_clicked(self):
    
        """ Manages what happens if the measurement is started. """
        self.disable_actions()
        self._timetagger_logic.start_measurement()

    def writeintofile_clicked(self):
        if not self._timetagger_logic._recording_states:
            self._mw.writeintoFile_PushButton.setText('Stop writing')
            self._timetagger_logic.start_recording()
        else:
            self._mw.writeintoFile_PushButton.setText('Write into File')
            self._timetagger_logic.stop_recording()  

    def enable_actions(self):
        """ Reset the action buttons to the default active
        state when the system is idle.
        """
        # Disable the stop button
        self._mw.action_stop.setEnabled(False)

        # Disable the start buttons
        self._mw.action_start.setEnabled(True)
        self.set_history_actions(True)

        self._mw.action_Settings.setEnabled(True)
    
        self._mw.corrBinWidthDoubleSpinBox.setEnabled(True)
        self._mw.corrRecordLengthDoubleSpinBox.setEnabled(True)
        self._mw.histBinWidthDoubleSpinBox.setEnabled(True)
        self._mw.histRecordLengthDoubleSpinBox.setEnabled(True)

        # Cursor buttons

        self._mw.corrCrosshairSizedoubleSpinBox.setEnabled(True)
        self._mw.corrCrosshairXdoubleSpinBox.setEnabled(True)
        self._mw.corrCrosshairYdoubleSpinBox.setEnabled(True)
        self._mw.histCrosshairSizedoubleSpinBox.setEnabled(True)
        self._mw.histCrosshairXdoubleSpinBox.setEnabled(True)
        self._mw.histCrosshairYdoubleSpinBox.setEnabled(True)

        self.update_autocorr_crosshair_visibility()
        self.update_autocorr_crosshair_size()
        self.update_histogram_crosshair_visibility()
        self.update_histogram_crosshair_size()


    def disable_actions(self):
        # Enable the stop button
        self._mw.action_stop.setEnabled(True)

        # Enable the start buttons
        self._mw.action_start.setEnabled(False)
        self.set_history_actions(False)

        self._mw.action_Settings.setEnabled(False)

        self._mw.corrBinWidthDoubleSpinBox.setEnabled(False)
        self._mw.corrRecordLengthDoubleSpinBox.setEnabled(False)
        self._mw.histBinWidthDoubleSpinBox.setEnabled(False)
        self._mw.histRecordLengthDoubleSpinBox.setEnabled(False)

        # Cursor buttons
        self._mw.autocorr_PlotWidget.toggle_crosshair(False, movable=False)
        self._mw.hist_PlotWidget.toggle_crosshair(False, movable=False)
        self._mw.corrCrosshairSizedoubleSpinBox.setEnabled(False)
        self._mw.corrCrosshairXdoubleSpinBox.setEnabled(False)
        self._mw.corrCrosshairYdoubleSpinBox.setEnabled(False)
        self._mw.histCrosshairSizedoubleSpinBox.setEnabled(False)
        self._mw.histCrosshairXdoubleSpinBox.setEnabled(False)
        self._mw.histCrosshairYdoubleSpinBox.setEnabled(False)

    def refresh_plots(self):

        _data_autocorr_x = self._timetagger_logic.autocorr_x
        _data_autocorr_y = self._timetagger_logic.autocorr_y[self._autocorr_channel, :]
        self.autocorr_plot.setData(_data_autocorr_x,_data_autocorr_y)
        

        _data_histogram_x = self._timetagger_logic.histogram_x
        _data_histogram_y = self._timetagger_logic.histogram_y[self._histogram_channel, :]
        self.histogram_plot.setData(_data_histogram_x,_data_histogram_y)


    def refresh_writeintofilestatus(self):
        self._mw.measure_time_OutputWidget.setText('{0}'.format(self._timetagger_logic.mearsure_time))
        self._mw.total_size_OutputWidget.setText('{0}'.format(self._timetagger_logic.total_size))

    def logic_started_save(self):
        """ Displays modal dialog when save process starts """
        self._save_dialog.show()

    def logic_finished_save(self):
        """ Hides modal dialog when save process done """
        self._save_dialog.hide()

    def menu_settings(self):
        """ This method opens the settings menu. """
        self._sd.exec_()

    def save_images(self):
        self._save_dialog.show()
        self._timetagger_logic.save_data()

    def save_configuration(self):
        """ Save current statusvariable to the file"""
        defaultconfigpath = self._save_logic.get_path_for_module(module_name='timetagger_cfg')
        filename = QtWidgets.QFileDialog.getSaveFileName(
            self._mw,
            'Save Configuration',
            defaultconfigpath,
            'Configuration files (*.cfg)')[0]

        if filename != '':
            self._save_dialog.show()
            self._timetagger_logic.save_history_config()
            variables = self._timetagger_logic._statusVariables
            try:
                config.save(filename, variables)
                self._save_dialog.hide()
            except:
                self._save_dialog.hide()
                print(variables)
                self.log.exception('Failed to save status variables to {0}'.format(filename))

    def load_configuration(self):
        """ Load statusvariable to the program"""
        try:
            defaultconfigpath = self._save_logic.get_path_for_module(module_name='timetagger_cfg')
            filename = QtWidgets.QFileDialog.getOpenFileName(
                self._mw,
                'Load Configuration',
                defaultconfigpath,
                'Configuration files (*.cfg)')[0]
            if filename != '':
                if os.path.isfile(filename):
                    self._load_dialog.show()
                    variables = config.load(filename)
                    self._load_dialog.hide()
                else:
                    variables = OrderedDict()
                self._timetagger_logic._statusVariables=variables
                self._timetagger_logic.load_history_config()
        except:
            self.log.exception('Failed to load status variables from {0}'.format(filename))

    def writeintofile_channels(self):
        self._wcd.exec_()

    def history_forward_clicked(self):
        self.set_history_actions(False)
        self._timetagger_logic.history_forward()
        self.set_history_actions(True)

    def history_back_clicked(self):
        self.set_history_actions(False)
        self._timetagger_logic.history_back()
        self.set_history_actions(True)

    def set_history_actions(self, enable):
        """ Enable or disable history arrows taking history state into account. """
        if enable and self._timetagger_logic.history_index < len(self._timetagger_logic.history) - 1:
            self._mw.actionForward.setEnabled(True)
        else:
            self._mw.actionForward.setEnabled(False)
        if enable and self._timetagger_logic.history_index > 0:
            self._mw.actionBack.setEnabled(True)
        else:
            self._mw.actionBack.setEnabled(False)

    def update_settings(self):
        """ Write new settings from the gui to the file. """      
        self._timetagger_logic._refresh_time = self._sd.settings_widget._refresh_time
        self._timetagger_logic._autocorr_params = copy.deepcopy(self._sd.settings_widget._corr_params)
        self._timetagger_logic._histogram_params = copy.deepcopy(self._sd.settings_widget._hist_params)

        # add Binwidth and Recordlength into params
        self.update_corrBinwidth()
        self.update_corrRecordlength()
        self.update_histBinwidth()
        self.update_histRecordlength()

        # update channel combobox
        self._autocorr_channel = 0
        self._histogram_channel = 0
        self.setup_autocorr_combobox()
        self.setup_histogram_combobox()

    def keep_former_settings(self):
        self._sd.settings_widget._refresh_time = self._timetagger_logic._refresh_time
        self._sd.settings_widget._corr_params = copy.deepcopy(self._timetagger_logic._autocorr_params)
        self._sd.settings_widget._hist_params = copy.deepcopy(self._timetagger_logic._histogram_params)

        self._sd.settings_widget.refresh_time_lineedit.setText('{0}'.format(self._sd.settings_widget._refresh_time))
        self._sd.settings_widget.update_corr_channels_display()
        self._sd.settings_widget.update_hist_channels_display()


    def update_writeintofilechannels(self):
        self._timetagger_logic._writeintofile_params = copy.deepcopy(self._wcd.settings_widget._writeintofile_params)

    def keep_former_writeintofilechannels(self):
        self._wcd.settings_widget._writeintofile_params = copy.deepcopy(self._timetagger_logic._writeintofile_params)


    def corr_accumulate_RadioButton_clicked(self):
        self._timetagger_logic._autocorr_accumulate = True
    def corr_refresh_RadioButton_clicked(self):
        self._timetagger_logic._autocorr_accumulate = False
    def hist_accumulate_RadioButton_clicked(self):
        self._timetagger_logic._histogram_accumulate = True
    def hist_refresh_RadioButton_clicked(self):
        self._timetagger_logic._histogram_accumulate = False

    def update_autocorr_crosshair_visibility(self):
        self._autocorr_crosshair = self._mw.corrCrosshair_radioButton.isChecked()
        if self._autocorr_crosshair:
            self._mw.autocorr_PlotWidget.toggle_crosshair(True, movable=True)
        else:
            self._mw.autocorr_PlotWidget.toggle_crosshair(False, movable=False)

    def update_autocorr_crosshair_size(self):
        self._autocorr_crosshair_size = self._mw.corrCrosshairSizedoubleSpinBox.value()
        autocorr_xRange = self._mw.autocorr_PlotWidget.getViewBox().getState()['viewRange'][0]
        autocorr_crosshair_Xsize = (autocorr_xRange[1] - autocorr_xRange[0]) * self._autocorr_crosshair_size
        autocorr_yRange = self._mw.autocorr_PlotWidget.getViewBox().getState()['viewRange'][1]
        autocorr_crosshair_Ysize = (autocorr_yRange[1] - autocorr_yRange[0]) * self._autocorr_crosshair_size
        self._mw.autocorr_PlotWidget.set_crosshair_size([autocorr_crosshair_Xsize ,autocorr_crosshair_Ysize])

    def update_autocorr_crosshair_XY(self):
        self._autocorr_crosshair_X = self._mw.corrCrosshairXdoubleSpinBox.value()
        self._autocorr_crosshair_Y = self._mw.corrCrosshairYdoubleSpinBox.value()
        self._mw.autocorr_PlotWidget.set_crosshair_pos((self._autocorr_crosshair_X,self._autocorr_crosshair_Y))

    def update_histogram_crosshair_visibility(self):
        self._histogram_crosshair = self._mw.histCrosshair_radioButton.isChecked()
        if self._histogram_crosshair:
            self._mw.hist_PlotWidget.toggle_crosshair(True, movable=True)
        else:
            self._mw.hist_PlotWidget.toggle_crosshair(False, movable=False)

    def update_histogram_crosshair_size(self):
        self._histogram_crosshair_size = self._mw.histCrosshairSizedoubleSpinBox.value()
        histogram_xRange = self._mw.hist_PlotWidget.getViewBox().getState()['viewRange'][0]
        histogram_crosshair_Xsize = (histogram_xRange[1] - histogram_xRange[0]) * self._histogram_crosshair_size
        histogram_yRange = self._mw.hist_PlotWidget.getViewBox().getState()['viewRange'][1]
        histogram_crosshair_Ysize = (histogram_yRange[1] - histogram_yRange[0]) * self._histogram_crosshair_size
        self._mw.hist_PlotWidget.set_crosshair_size([histogram_crosshair_Xsize, histogram_crosshair_Ysize])

    def update_histogram_crosshair_XY(self):
        self._histogram_crosshair_X = self._mw.histCrosshairXdoubleSpinBox.value()
        self._histogram_crosshair_Y = self._mw.histCrosshairYdoubleSpinBox.value()
        self._mw.hist_PlotWidget.set_crosshair_pos((self._histogram_crosshair_X,self._histogram_crosshair_Y))


    def autocorr_update_from_roi_xy(self, pos):
        X_pos = pos.x()
        Y_pos = pos.y()
        self._mw.corrCrosshairXdoubleSpinBox.setValue(X_pos)
        self._mw.corrCrosshairYdoubleSpinBox.setValue(Y_pos)

    def histogram_update_from_roi_xy(self, pos):
        X_pos = pos.x()
        Y_pos = pos.y()
        self._mw.histCrosshairXdoubleSpinBox.setValue(X_pos)
        self._mw.histCrosshairYdoubleSpinBox.setValue(Y_pos)

    def history_event(self):
        # Take the default values from logic:
        self._mw.corrBinWidthDoubleSpinBox.setValue(list(self._timetagger_logic._autocorr_params.values())[0]['bins_width'])
        Record_length = float(list(self._timetagger_logic._autocorr_params.values())[0]['bins_width'] * list(self._timetagger_logic._autocorr_params.values())[0]['number_of_bins']/1000) 
        self._mw.corrRecordLengthDoubleSpinBox.setValue(Record_length)


        self._mw.histBinWidthDoubleSpinBox.setValue(list(self._timetagger_logic._histogram_params.values())[0]['bins_width'])
        Record_length = float(list(self._timetagger_logic._histogram_params.values())[0]['bins_width'] * list(self._timetagger_logic._histogram_params.values())[0]['number_of_bins']/1000) 
        self._mw.histRecordLengthDoubleSpinBox.setValue(Record_length)

        
        if self._timetagger_logic._autocorr_accumulate:
            self._mw.corr_accumulate_RadioButton.setChecked(True)
        else:
            self._mw.corr_refresh_RadioButton.setChecked(True)

        if self._timetagger_logic._histogram_accumulate:
            self._mw.hist_accumulate_RadioButton.setChecked(True)
        else:
            self._mw.hist_refresh_RadioButton.setChecked(True)


        self.keep_former_settings()
        self.keep_former_writeintofilechannels()

        # update channel combobox
        self._autocorr_channel = 0
        self._histogram_channel = 0
        self.setup_autocorr_combobox()
        self.setup_histogram_combobox()

        self.refresh_plots()
