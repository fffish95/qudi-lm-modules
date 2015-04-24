# -*- coding: utf-8 -*-
# unstable: Christoph Müller

from logic.GenericLogic import GenericLogic
from pyqtgraph.Qt import QtCore
from collections import OrderedDict
import numpy as np

class TrackerLogic(GenericLogic):
    """unstable: Christoph Müller
    This is the Logic class for NV tracking and refocus
    """
    signal_scan_xy_line_next = QtCore.Signal()
    signal_xy_image_updated = QtCore.Signal()
    signal_z_image_updated = QtCore.Signal()
    

    def __init__(self, manager, name, config, **kwargs):
        ## declare actions for state transitions
        state_actions = {'onactivate': self.activation}
        GenericLogic.__init__(self, manager, name, config, state_actions, **kwargs)
        self._modclass = 'trackerlogic'
        self._modtype = 'logic'

        ## declare connectors
        self.connector['in']['confocalscanner1'] = OrderedDict()
        self.connector['in']['confocalscanner1']['class'] = 'ConfocalScannerInterface'
        self.connector['in']['confocalscanner1']['object'] = None
        self.connector['in']['fitlogic'] = OrderedDict()
        self.connector['in']['fitlogic']['class'] = 'FitLogic'
        self.connector['in']['fitlogic']['object'] = None
        
        self.connector['out']['trackerlogic'] = OrderedDict()
        self.connector['out']['trackerlogic']['class'] = 'TrackerLogic'
        

        self.logMsg('The following configuration was found.', 
                    msgType='status')
                            
        # checking for the right configuration
        for key in config.keys():
            self.logMsg('{}: {}'.format(key,config[key]), 
                        msgType='status')
        
        self.refocus_XY_size
        self.refocus_XY_step
        self.refocus_Z_size
        self.refocus_Z_step
        
        self.running = False
        self.stopRequested = False
                       
    def activation(self, e):
        """ Initialisation performed during activation of the module.
        """        
        self._scanning_device = self.connector['in']['confocalscanner1']['object']
        print("Scanning device is", self._scanning_device)
        self._fit_logic = self.connector['in']['fitlogic']['object']
        
        self.x_range = self._scanning_device.get_position_range()[0]
        self.y_range = self._scanning_device.get_position_range()[1]
        self.z_range = self._scanning_device.get_position_range()[2]
        
        self._trackpoint_x = 0.
        self._trackpoint_y = 0.   #woher?
        self._trackpoint_z = 0.
        
        self._scan_counter = 0
        
        self.signal_scan_xy_line_next.connect(self._scan_xy_line, QtCore.Qt.QueuedConnection)
        
    def start_refocus(self):
        """Starts refocus        
        """
        self._scan_counter = 0
        self._initialize_xy_refocus_image()
        self._initialize_z_refocus_image()
        self.start_scanner()
        self.signal_scan_xy_line_next.emit()
        
        
    def stop_refocus(self):
        """Stops refocus        
        """
        with self.lock:
            self.stopRequested = True
        
        
    def _initialize_xy_refocus_image(self):
        """Initialisation of the xy refocus image
        """
        self._scan_counter = 0
        
        x0 = self._trackpoint_x
        y0 = self._trackpoint_y
        
        xmin = np.clip(x0 - 0.5 * self.refocus_XY_size, self.x_range[0], self.x_range[1])
        xmax = np.clip(x0 + 0.5 * self.refocus_XY_size, self.x_range[0], self.x_range[1])
        ymin = np.clip(y0 - 0.5 * self.refocus_XY_size, self.y_range[0], self.y_range[1])
        ymax = np.clip(y0 + 0.5 * self.refocus_XY_size, self.y_range[0], self.y_range[1])
        
        self._X_values = np.arange(xmin, xmax + self.refocus_XY_step, self.refocus_XY_step)
        self._Y_values = np.arange(ymin, ymax + self.refocus_XY_step, self.refocus_XY_step)
        self._Z_values = self._trackpoint_z * np.ones(self._X_values.shape)
        self._A_values = np.zeros(self._X_values.shape)
        self._return_X_values = np.arange(xmax, xmin + self.refocus_XY_step, self.refocus_XY_step)
        
        self.xy_refocus_image = np.zeros(len(self._X_values), len(self._Y_values), 4)
        
        
    def _scan_xy_line(self):
        """Scanning one line of the xy refocus image
        """
        self.running = True        
        
        #stops scanning
        if self.stopRequested:
            with self.lock:
                self.running = False
                self.stopRequested = False
                self.signal_xy_image_updated.emit()
                return
                
        X_line = self._X_values
        Y_line = self._Y_values[self._scan_counter] * np.ones(X_line.shape)
        Z_line = self._Z_values    #todo: tilt_correction
        A_line = self._A_values
        return_X_line = self._return_X_values
        
        line = np.vstack( (X_line, Y_line, Z_line, A_line) )            
        line_counts = self._scanning_device.scan_line(line)
        return_line = np.vstack( (return_X_line, Y_line, Z_line, A_line) )
        return_line_counts = self._scanning_device.scan_line(return_line)                
        
        self.xy_refocus_image[self._scan_counter,:,0] = self._X_values
        self.xy_refocus_image[self._scan_counter,:,1] = self._Y_values
        self.xy_refocus_image[self._scan_counter,:,2] = self._Z_values
        self.xy_refocus_image[self._scan_counter,:,3] = line_counts
        
        self.signal_xy_image_updated.emit()
        self._scan_counter += 1
        
        if self._scan_counter < np.size(self._image_vert_axis):            
            self.signal_scan_xy_line_next.emit()
        else:
            #TODO: xy fitten  ---> self.refocus_x und self.refocus_y
            #vermutlich ungefähr so?
            #fit_parameters = self._fit_logic.Fit(self.xy_refocus_image[:,:,3], twoD_gaussian_estimator, twoD_gaussian_function)
            self._scan_z_line()
            self.running = False
            self.signal_z_image_updated.emit()
            # TODO: z fitten  ---> self.refocus_z
            # TODO: self.refocus x,y,z als neuen trackpoint setzen
            #und dort hinfahren
            self._scanning_device.scanner_set_position(x = self.refocus_x, 
                                                       y = self.refocus_y, 
                                                       z = self.refocus_z, 
                                                       a = 0.)
        
    
    def _initialize_z_refocus_image(self):
        """Initialisation of the z refocus image
        """
        self._scan_counter = 0
        z0 = self._trackpoint_z  #falls tilt correction, dann hier aufpassen
        zmin = np.clip(z0 - 0.5 * self.refocus_Z_size, self.z_range[0], self.z_range[1])
        zmax = np.clip(z0 + 0.5 * self.refocus_Z_size, self.z_range[0], self.z_range[1])
        
        self._Z_values = np.arange(zmin, zmax + self.refocus_Z_step, self.refocus_Z_step)
        self._A_values = np.zeros(self._Z_values.shape)
        #self._Z_values = np.clip(z0-0.5*self.ZSize, z0+0.5*self.ZSize, self.ZStep)
        self.z_refocus_line = np.zeros(len(self._Z_values))
        
        
    def _scan_z_line(self):
        """Scans the z line for refocus
        """
        Z_line = self._Z_values    #todo: tilt_correction
        X_line = self.refocus_x * np.ones(self._Z_values.shape)
        Y_line = self.refocus_y * np.ones(self._Z_values.shape)
        A_line = np.zeros(self._Z_values.shape)
        
        line = np.vstack( (X_line, Y_line, Z_line, A_line) )            
        line_counts = self._scanning_device.scan_line(line)
        
        self.z_refocus_line = line_counts