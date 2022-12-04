import numpy as np
import os
import pyqtgraph as pg

from qudi.core.connector import Connector
from qudi.core.module import GuiBase
from PySide2 import QtCore, QtGui, QtWidgets
from qudi.util import uic
from qudi.util import config


class RbSpectrumMainWindow(QtWidgets.QMainWindow):
    """ Create the Main Window based on the *.ui file. """

    def __init__(self):
        # Get the path to the *.ui file
        this_dir = os.path.dirname(__file__)
        ui_file = os.path.join(this_dir, 'ui_Rb_spectrum.ui')

        # Load it
        super(RbSpectrumMainWindow, self).__init__()
        uic.loadUi(ui_file, self)
        self.show()



class RbSpectrumGui(GuiBase):
    """
    Gui class for Rb spectrum in lecroy scope

        Example config for copy-paste:

    rbspectrum:
        module.Class: 'local.Rb_spectrum.Rb_spectrum_gui.RbSpectrumGui'
        connect:
            lecroylogic: 'lecroy_scope_logic'
    """
    
    # declare connectors
    lecroylogic = Connector(interface='LecroyLogic')

   
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def on_activate(self):
        """ Initializes all needed UI files and establishes the connectors.

        This method executes the all the inits for the differnt GUIs and passes
        the event argument from fysom to the methods.
        """
        # Getting an access to all connectors:
        self._lecroy_logic = self.lecroylogic()

        self.initMainUI()      # initialize the main GUI

    def initMainUI(self):
        """ Definition, configuration and initialisation of the timetagger GUI.

        This init connects all the graphic modules, which were created in the
        *.ui file and configures the event handling between the modules.
        Moreover it sets default values.
        """
        self._mw = RbSpectrumMainWindow()

        ###################################################################
        #               Configuring the dock widgets                      #
        ###################################################################
        # All our gui elements are dockable, and so there should be no "central" widget.
        self._mw.centralwidget.hide()
        self._mw.setDockNestingEnabled(True)


        # Get the plots for the display from the logic
        raw_dataframe_x = self._lecroy_logic._dataframe_x
        raw_dataframe_y = self._lecroy_logic._dataframe_y


        # Load the plots in the display
        self._plot = pg.PlotDataItem(
            raw_dataframe_x,
            raw_dataframe_x)
        # Add the display item to the VieWidget, which was defined in
        # the UI file.
        self._mw.PlotWidget.addItem(self._plot)
        self._mw.PlotWidget.showGrid(x=True, y=True, alpha=0.8)
        self._mw.PlotWidget.setLabel('left', 'y', units='a.u.')
        self._mw.PlotWidget.setLabel('bottom', 'x', units='a.u.')

        # Set the state button as ready button as default setting.
        self._mw.action_stop.setEnabled(False)

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
        
        # Connect the emitted signal of an image change from the logic with
        self._lecroy_logic.signal_plots_updated.connect(self.refresh_plots)

        # all other components:
        self.enable_actions()
        self.refresh_plots()
        self.show()

    def show(self):
        """Make main window visible and put it above all other windows. """
        # Show the Main GUI:
        self._mw.show()
        self._mw.activateWindow()
        self._mw.raise_()


    def on_deactivate(self):
        """ Reverse steps of activation

        @return int: error code (0:OK, -1:error)
        """
        self._mw.close()
        return 0

    def stop_clicked(self):
        """ Stop the measurement if the state has switched to ready. """
        if self._lecroy_logic.module_state() == 'locked':
            self._lecroy_logic.stop_acquisition()
        # Disable the stop button
        self._mw.action_stop.setEnabled(False)
        self.enable_actions()
    
    def start_clicked(self):    
        """ Manages what happens if the measurement is started. """
        self.disable_actions()
        self._lecroy_logic.start_acquisition()

    def enable_actions(self):
        """ Reset the action buttons to the default active
        state when the system is idle.
        """
        # Disable the stop button
        self._mw.action_stop.setEnabled(False)

        # Disable the start buttons
        self._mw.action_start.setEnabled(True)


    def disable_actions(self):
        # Enable the stop button
        self._mw.action_stop.setEnabled(True)

        # Enable the start buttons
        self._mw.action_start.setEnabled(False)

    def refresh_plots(self):

        _dataframe_x = self._lecroy_logic._dataframe_x
        _dataframe_y = self._lecroy_logic._dataframe_y
        self._plot.setData(_dataframe_x,_dataframe_y)

