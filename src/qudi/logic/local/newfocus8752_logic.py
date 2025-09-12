# Modified from (c) 2022 Marc de Cea Falco

from qudi.core.connector import Connector
from qudi.core.module import LogicBase
import math
import time

class NF8752Logic(LogicBase):
    """
        nf8752:
        module.Class: 'local.newfocus8752_logic.NF8752Logic'
            connect:
                tcpclient: 'newfocus_8752_tcp_client'
    """

    tcpclient = Connector(interface='TCPClient')

    def on_activate(self):
        self._tcpclient = self.tcpclient()
        # nf8752 drives motors with driver channel + motor channel. To simplify assigning driver channels and motor channels for each picomotor.
        # We define axis codes. The driver channel is calculated as the ceiling of the axis code divided by 3,
        # the motor channel is the remainder of the axis code divided by 3. 
        # The axis alphabet in the hardware corresponds to the ports, ordered from left to right and from top to bottom.
        self.axis_alphabet = ['x1','y1','z','x2','y2']
        self.axis_codes = dict(zip(self.axis_alphabet, list(range(1,6,1))))


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
        """Read response from picomotor driver."""
        return self._tcpclient.receive()

    def set_axis(self, axis, vel=None, acc=None):
        """Set current axis and (optionally) its velocity.
        You have to call this function before moving the picomotor, because 1 driver channel can only move 1 motor at a time.

        :param motor: some picomotor controllers have 3 channels, so we could select the specific channel
            with this parameter. Nevertheless, what we have in lab only has one channel (so motor = 0)

        """

        assert axis in self.axis_alphabet

        fmt = dict(driver=f'a{math.ceil(self.axis_codes[axis]/3)}', motor=f'{(self.axis_codes[axis]-1) % 3 }')
        basecmd = '{cmd} {driver} {motor}={value}'

        cmd = 'chl {driver}={motor}'.format(**fmt)
        self.send(cmd)

        # Set the type to standard picomotor, we don't have tiny picomotor in the lab
        cmd = 'typ {driver} 0'.format(**fmt)
        self.send(cmd)

        if acc is not None:
            assert 0 < acc <= 32000, 'Acceleration out of range (1..32000).'
            cmd = basecmd.format(cmd='ACC', value=acc, **fmt)
            self.send(cmd)

        if vel is not None:
            assert 0 < vel <= 2000, 'Velocity out of range (1..2000).'
            cmd = basecmd.format(cmd='VEL', value=vel, **fmt)
            self.send(cmd)
        
        cmd = 'mon'  # Turn drivers on
        self.send(cmd)

    def move_to_limit(
            self,
            axis,
            direction='forward',
            vel=None,
            acc=None):
        """
        Moves the specified axis to its limit
        :param direction: 'forward' or 'reverse', if we want to find the forward or reverse limit.
        """
        self.set_axis(axis, vel=vel, acc=acc)

        if direction == 'forward':
            cmd = 'fli {driver}'.format(driver=f'a{math.ceil(self.axis_codes[axis]/3)}')
        elif direction == 'reverse':
            cmd = 'rli {driver}'.format(driver=f'a{math.ceil(self.axis_codes[axis]/3)}')
        return self.send(cmd)

    def move_rel(self, steps, axis, vel=100, acc=500, go=True):
        """
        Send command to move `axis` of the given `steps`.

        :param steps: how many steps to move with respect to the current position
        :param go: if True, the command is executed right away
        """

        steps = int(steps)
        self.set_axis(axis, vel=vel, acc=acc)
        cmd = 'rel {driver}={steps}'.format(
            driver=f'a{math.ceil(self.axis_codes[axis]/3)}', steps=steps)
        if go:
            cmd = cmd + ' g'
        delay = math.ceil(abs(steps/vel))
        self.send(cmd)
        time.sleep(delay+0.5)

    def go(self):
        """Send 'go' command to execute all previously sent move commands."""
        return self.send('go')

    def halt(self):
        """Send 'HAL' command to stop motion with deceleration."""
        return self.send('hal')
