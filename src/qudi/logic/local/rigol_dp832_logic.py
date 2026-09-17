# NOTE: This module was written or modified by fffish
# (https://github.com/fffish95/qudi-lm-modules) and remains subject to the GNU
# license terms stated below (or, if none are stated in this file, to the GNU
# General Public License under which Qudi is distributed).

# Modified from (c) 2022 Marc de Cea Falco

from qudi.core.connector import Connector
from qudi.core.module import LogicBase

class DP832Logic(LogicBase):
    """
    dp832:
        module.Class: 'local.rigol_dp832_logic.DP832Logic'
            connect:
                tcpclient: 'rigol_dp832_client'
    """

    tcpclient = Connector(interface='TCPClient')

    def on_activate(self):
        self._tcpclient = self.tcpclient()


    def on_deactivate(self):
        """
        Disconnect from the power source.
        """
        return 0

    def send(self, cmd):
        """Send a command to the picomotor driver."""
        # reset the buffer

        try:
            self._tcpclient.start_command()
            line = cmd + '\r\n'
            self._tcpclient.send_byte(line)
        except:
            self._tcpclient.disconnect()
            self._tcpclient.connect()
            self._tcpclient.start_command()
            line = cmd + '\r\n'
            self._tcpclient.send_byte(line)

    def readlines(self):
        """Read response."""
        return self._tcpclient.receive()

    def On(self, channel):
        self.send(":OUTP:STAT CH{0},ON".format(channel))
    
    def Off(self, channel):
        self.send(":OUTP:STAT CH{0},OFF".format(channel))    

    def SetVoltage(self, channel, voltage):
        self.send("SOUR{0}:VOLT:IMM {1}".format(channel,voltage))    

    def SetCurrent(self, channel, current):
        self.send("SOUR{0}:CURR:IMM {1}".format(channel,current))   