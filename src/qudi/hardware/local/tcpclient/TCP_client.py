# Modified from (c) 2020-2021, ETH Zurich, Power Electronic Systems Laboratory, T. Guillod

import socket
from qudi.core.configoption import ConfigOption
from qudi.core.module import Base

class TCPClient(Base):
    """
        fugsource_tcp_client:
        module.Class: 'local.tcpclient.TCP_client.TCPClient'
        options:
            ip: '10.140.0.211'
            port: 2101
            timeout: 0.01
            buffer: 1024

        
        newfocus_8752_tcp_client:
        module.Class: 'local.tcpclient.TCP_client.TCPClient'
        options:
            ip: '10.140.1.247'
            port: 23
            timeout: 0.1
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

        self.link = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.link.connect((self._ip, self._port))
        self.link.settimeout(self._timeout)

    def on_deactivate(self):
        """
        Close the connection.
        """

        self.data_buffer = ''
        self.link.close()
        self.link = None

    def start_command(self):
        """
        Clear the buffer for starting a new command.
        """

        self._receive_bytes()
        self.data_buffer = ''

    def send_byte(self, msg):
        """
        Send a byte to the power source.
        """

        try:
            self.link.send(msg.encode())
        except Exception:
            raise ValueError("send fail")

    def receive(self):
        """
        Get responses from the power source where the newline is the delimiter.
        """

        response = []
        buffer_new = self._receive_bytes()
        for char in buffer_new:
            if char == '\n':
                response.append(self.data_buffer)
                self.data_buffer = ''
            else:
                self.data_buffer += char

        return response

    def _receive_bytes(self):
        """
        Get bytes from the power sources.
        """

        try:
            try:
                return self.link.recv(self._buffer).decode()
            except socket.timeout:
                return ''
        except Exception:
            raise ValueError("receive fail")