# Modified from (c) 2020-2021, ETH Zurich, Power Electronic Systems Laboratory, T. Guillod

import socket
from qudi.core.configoption import ConfigOption
from qudi.core.module import Base

class TCPClient_dummy(Base):
    """
        fugsource_tcp_client:
        module.Class: 'local.tcpclient.TCP_client.TCPClient'
        options:
            ip: '10.140.1.45'
            port: 2101
            timeout: 0.01
            buffer: 1024
    """
    # config options
    _ip = ConfigOption('ip', missing='error')
    _port = ConfigOption('port', missing='error')
    _timeout = ConfigOption('timeout', missing='error')
    _buffer = ConfigOption('buffer', missing='error')

    def on_activate(self):
        """
        Connect to the power source and set the timeout of the connection.
        """

        pass

    def on_deactivate(self):
        """
        Close the connection.
        """

        pass

    def start_command(self):
        """
        Clear the buffer for starting a new command.
        """

        pass

    def send_byte(self, msg):
        """
        Send a byte to the power source.
        """

        pass

    def receive(self):
        """
        Get responses from the power source where the newline is the delimiter.
        """

        pass

    def _receive_bytes(self):
        """
        Get bytes from the power sources.
        """

        pass