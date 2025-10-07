# -*- coding: utf-8 -*-
import requests
from qudi.core.configoption import ConfigOption
from qudi.core.module import Base


class ShellyPro(Base):
    """ Designed for the remote control of Shelly pro 2 switch.

    Example config for copy-paste: 

    Switch1:
        module.Class: 'local.shelly.ShellyPro'
        options:
            ip: '10.140.1.242'
            
            

    """
    # config options
    _ip = ConfigOption('ip', missing='error')

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def on_activate(self):
        url = f"http://{self._ip}/rpc/Switch.GetStatus?id=0"
        try:
            resp = requests.get(url, timeout=3)
            if resp.status_code == 200:
                self.log.info("Shelly device is connected.")
                return True
            else:
                self.log.error(f"Shelly responded with status {resp.status_code}")
                return False
        except requests.exceptions.RequestException as e:
            self.log.error(f"Shelly is not reachable: {e}")
            return False

    def on_deactivate(self):
        pass

    def get_status(self, ch=0, auth=None):
        return requests.get(f"http://{self._ip}/rpc/Switch.GetStatus?id={ch}", auth=auth, timeout=5).json()

    def set(self, ch=0, on=True, auth=None):
        return requests.get(f"http://{self._ip}/rpc/Switch.Set?id={ch}&on={'true' if on else 'false'}",
                            auth=auth, timeout=5).json()

    def toggle(self, ch=0, auth=None):
        return requests.get(f"http://{self._ip}/rpc/Switch.Toggle?id={ch}", auth=auth, timeout=5).json()
