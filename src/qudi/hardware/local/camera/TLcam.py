"""
This hardware module implement the camera interface to use a Thorlabs scientific sCMOS cameras.
"""
import numpy as np

import pylablib as pll
from pylablib.devices import Thorlabs
from pylablib.devices.Thorlabs.tl_camera_sdk_lib import wlib as lib

from qudi.core.configoption import ConfigOption
from qudi.interface.camera_interface import CameraInterface

class TLcam(CameraInterface):
    """ Main class of the module

    Example config for copy-paste:

    thorlabs_camera:
        module.Class: 'local.camera.TLcam.TLcam'
        options:
            dll_location: 'C:\\Program Files\\Thorlabs\\Scientific Imaging\\ThorCam' # path to library file
            exposure: 0.2
            gain: 0.0

    """
    _dll_location = ConfigOption('dll_location', missing='error')
    _exposure = ConfigOption('exposure', 200000)
    _gain = ConfigOption('gain', 0.0)

    def on_activate(self):
        """ Initialisation performed during activation of the module.
         """
        pll.par["devices/dlls/thorlabs_tlcam"] = self._dll_location
        serial_num = Thorlabs.list_cameras_tlcam()[0]
        try:
            self.serial_num = Thorlabs.list_cameras_tlcam()[0]
        except:
            self.log.error('No Thorlabs camera found.')
        self._cam = Thorlabs.ThorlabsTLCamera(serial=serial_num)

        self._acquiring = False
        self._live = False

        self.set_exposure(self._exposure)
        self.set_gain(self._gain)

    def on_deactivate(self):
        """ Deinitialisation performed during deactivation of the module.
        """
        self.stop_acquisition()
        self._cam.close()

    def get_name(self):
        """ Retrieve an identifier of the camera that the GUI can print

        @return string: name for the camera
        """
        return self._cam.get_device_info().name()
    
    def get_size(self):
        """ Retrieve size of the image in pixel

        @return tuple: Size (width, height)
        """
        return self._cam.get_detector_size()

    def support_live_acquisition(self):
        """ Return whether or not the camera can take care of live acquisition

        @return bool: True if supported, False if not
        """
        return True

    def start_live_acquisition(self):
        """ Start a continuous acquisition

        @return bool: Success ?
        """
        if self.get_ready_state():
            self._acquiring = True
            self._live = True
            try:
                self._cam.setup_acquisition()
                self._cam.start_acquisition()
            except:
                self._acquiring = False
                self._live = False
                return False
            finally:
                return True
        else:
            return False

    def start_single_acquisition(self):
        """ Start a single acquisition

        @return bool: Success ?
        """
        if self.get_ready_state():
            try:
                self._cam.grab(nframes = 1)
            except:
                return False
            finally:
                return True
        else:
            return False

    def stop_acquisition(self):
        """ Stop/abort live or single acquisition

        @return bool: Success ?
        """
        if self._acquiring:
            try:
                self._cam.stop_acquisition()
            except:
                self.log.error('Cannot stop acquisition.')
                return False
        self._acquiring = False
        self._live = False
        return True

    def get_acquired_data(self):
        """ Return an array of last acquired image.
        @return numpy array: image data in format [[row],[row]...]

        Each pixel might be a float, integer or sub pixels
        """

        data, _ = self._cam._buffer.buffer[-1]
        return data
    
    def set_exposure(self, exposure):
        """ Set the exposure time in seconds

        @param float exposure: desired new exposure time

        @return float: setted new exposure time
        """
        return self._cam.set_exposure(exposure)
    
    def get_exposure(self):
        """ Get the exposure time in seconds

        @return float exposure time
        """
        return self._cam.get_exposure()

    def set_gain(self, gain):
        """ Set the gain

        @param float gain: desired new gain

        @return float: new exposure gain
        """
        return lib.tl_camera_set_gain(self._cam.handle,int(gain))

    def get_gain(self):
        """ Get the gain

        @return float: exposure gain
        """
        return lib.tl_camera_get_gain(self._cam.handle)

    def get_ready_state(self):
        """
        Return whether or not the camera is ready for an acquisition
        """
        if self.module_state()!='idle':
            return False
        return not self._acquiring

    def wait_for_next_frame(self):
        return self._cam._wait_for_next_frame()