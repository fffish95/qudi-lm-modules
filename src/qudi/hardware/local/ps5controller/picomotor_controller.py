import time
from evdev import InputDevice, categorize, ecodes
from telnetlib import Telnet
import select
import numpy as np


picomotor_ip = '10.140.1.153'

button_presses = {                          # ecodes.EV_KEY
    304: 'x',
    305: 'circle',
    306: '306',
    307: 'triangle',
    308: 'square',
    309: '309',
    310: 'L1',                              # this shows up when the button clicks before the analog signals are reported
    311: 'R1',
    312: 'L2',                           # 3 vertical lines, top left side of touchpad
    313: 'R2',                           # 3 horizontal lines, top right of touchpad
    314: 'share',                              # left joystick press down vertically
    315: 'pause',
    316: 'playstation',
    317: 'L3',
    318: 'R3'
}

button_values = {                           # ecodes.EV_KEY button press values
    0: 'up',
    1: 'down'
}

absolutes = {                               # ecodes.EV_ABS
    0: 'left joystick left/right',          # 0 = left, 255 = right
    1: 'left joystick up/down',             # 0 = up, 255 = down
    2: 'L2 analog',         # 0 = left, 255 = right
    3: 'right joystick left/right',                         # 0 = no press, 255 = full press
    4: 'right joystick up/down',                         # 0 = no press, 255 = full press
    5: 'R2 analog',            # 0 = up, 255 = down
    16: 'leftpad left/right',               # -1 = left, 0 = stop pressing, 1 = right
    17: 'leftpad up/down',                  # -1 = up, 0 = stop pressing, 1 = down
}

leftpad_left_right_values = {
    -1: 'left',
    0: 'left-right stop',                   # stoip means that the button was no longer pressed
    1: 'right'
}

leftpad_up_down_values = {
    -1: 'up',
    0: 'up-down stop',
    1: 'down'
}

CENTER = 128
BLIND = 20                                   # there's a lot of drift at 128, so don't report changes within (128 - this value)
L2R2_BLIND = 20
MAX_EMERGENCY_DELAY = 1000                  # max number of milliseconds between taps to qualify as an emergency double-tap
emergency_tap_time = 0                      # track when the last time the emergency button (playstation) was pressed
left_joystick, right_joystick = [CENTER, CENTER], [CENTER, CENTER]
READ_INT = 0.01                              # read interval - 0.3s
steps_array = [1,10,40,200]
steps = steps_array[0]

def is_emergency(event):
    global emergency_tap_time
    if event.code == 316 and event.value == 1:                           # emergency tap-down on the playstation
        previous_tap = emergency_tap_time
        emergency_tap_time = int(round(time.time() * 1000))                 # set now as the most recent tap time
        if emergency_tap_time < (previous_tap + MAX_EMERGENCY_DELAY):       # if the current tap-down comes less than x milliseconds after last tap
            return True
    return False

def update_left_joystick_position(event):
    global left_joystick
    if event.code == 0:                     # left joystick, x-axis (left/right)
        left_joystick[0] = value
    elif event.code == 1:                   # left joystick, y-axis (up/down)
        left_joystick[1] = value

def update_right_joystick_position(event):
    global right_joystick
    if event.code == 3:                     # right joystick, x-axis (left/right)
        right_joystick[0] = value
    elif event.code == 4:                   # right joystick, y-axis (up/down)
        right_joystick[1] = value

def decode_leftpad(event):
    action  = ''
    if event.code == 16:                    # leftpad, either a left or right action
        action = leftpad_left_right_values[value]
    elif event.code == 17:                  # leftpad, either an up or down action
        action = leftpad_up_down_values[value]
    else:                                   # unhandled event
        return ''
    return f'leftpad: {action}'

def run_event(event):
    global steps_array
    global steps
    if event.type == ecodes.EV_KEY and event.code in button_presses:       # any button press other than leftpad
        if event.code == 308 and event.value == 1:
            with Telnet(picomotor_ip, 23) as pico:
                _pico= pico_controller(pico)
                _pico.mov_nx2_up(steps)
            print(f'mov_nx2_up({steps})')

        if event.code == 305 and event.value == 1:
            with Telnet(picomotor_ip, 23) as pico:
                _pico= pico_controller(pico)
                _pico.mov_nx2_down(steps)
            print(f'mov_nx2_down({steps})')

        if event.code == 307 and event.value == 1:
            with Telnet(picomotor_ip, 23) as pico:
                _pico= pico_controller(pico)
                _pico.mov_ny2_up(steps)
            print(f'mov_ny2_up({steps})')

        if event.code == 304 and event.value == 1:
            with Telnet(picomotor_ip, 23) as pico:
                _pico= pico_controller(pico)
                _pico.mov_ny2_down(steps)
            print(f'mov_ny2_down({steps})')

        if event.code == 314 and event.value == 1:
            steps_array = np.roll(steps_array,-1)
            steps = steps_array[0]
            print(f'picosteps={steps}')

    if event.type == ecodes.EV_ABS and event.code in absolutes:                     # leftpad, joystick motion, or L2/R2 triggers
        if event.code == 16:
           if event.value == -1:
                with Telnet(picomotor_ip, 23) as pico:
                   _pico= pico_controller(pico)
                   _pico.mov_nx1_up(steps)
                print(f'mov_nx1_up({steps})')

           elif event.value == 1:
                with Telnet(picomotor_ip, 23) as pico:
                   _pico= pico_controller(pico)
                   _pico.mov_nx1_down(steps)
                print(f'mov_nx1_down({steps})')

        if event.code == 17:
            if event.value == 1:
                with Telnet(picomotor_ip, 23) as pico:
                    _pico= pico_controller(pico)
                    _pico.mov_ny1_down(steps)
                print(f'mov_ny1_down({steps})')

            elif event.value == -1:
                with Telnet(picomotor_ip, 23) as pico:
                    _pico= pico_controller(pico)
                    _pico.mov_ny1_up(steps)
                print(f'mov_ny1_up({steps})')

class pico_controller:
    def __init__(self, pico):
        self.x1_axis=1
        self.y1_axis=2
        self.x2_axis=3
        self.y2_axis=4

        self.x1_module = "{0}".format(self.x1_axis).encode('ascii')
        self.y1_module = "{0}".format(self.y1_axis).encode('ascii')
        self.x2_module = "{0}".format(self.x2_axis).encode('ascii')
        self.y2_module = "{0}".format(self.y2_axis).encode('ascii')

        self.pico = pico

    def gnd_all(self):
        self.pico.write(b"ST\r")

    def mov_1x1_up(self):
        self.pico.write(self.x1_module + b"PR1\r")

    def mov_1x1_down(self):
        self.pico.write(self.x1_module + b"PR-1\r")

    def mov_1y1_down(self):
        self.pico.write(self.y1_module + b"PR1\r")

    def mov_1y1_up(self):
        self.pico.write(self.y1_module + b"PR-1\r")

    def mov_1x2_up(self):
        self.pico.write(self.x2_module + b"PR1\r")

    def mov_1x2_down(self):
        self.pico.write(self.x2_module + b"PR-1\r")

    def mov_1y2_down(self):
        self.pico.write(self.y2_module + b"PR1\r")

    def mov_1y2_up(self):
        self.pico.write(self.y2_module + b"PR-1\r")

    def mov_nx1_up(self,steps):
        _steps = "{0}".format(steps).encode('ascii')
        self.pico.write(self.x1_module + b"PR"+ _steps + b")\r")

    def mov_nx1_down(self,steps):
        _steps = "{0}".format(steps).encode('ascii')
        self.pico.write(self.x1_module + b"PR-"+ _steps + b")\r")

    def mov_ny1_down(self,steps):
        _steps = "{0}".format(steps).encode('ascii')
        self.pico.write(self.y1_module + b"PR"+ _steps + b")\r")

    def mov_ny1_up(self,steps):
        _steps = "{0}".format(steps).encode('ascii')
        self.pico.write(self.y1_module + b"PR-"+ _steps + b")\r")

    def mov_nx2_up(self,steps):
        _steps = "{0}".format(steps).encode('ascii')
        self.pico.write(self.x2_module + b"PR"+ _steps + b")\r")

    def mov_nx2_down(self,steps):
        _steps = "{0}".format(steps).encode('ascii')
        self.pico.write(self.x2_module + b"PR-"+ _steps + b")\r")

    def mov_ny2_down(self,steps):
        _steps = "{0}".format(steps).encode('ascii')
        self.pico.write(self.y2_module + b"PR"+ _steps + b")\r")

    def mov_ny2_up(self,steps):
        _steps = "{0}".format(steps).encode('ascii')
        self.pico.write(self.y2_module + b"PR-"+ _steps + b")\r")

if __name__ == '__main__':
    while(True):
        try:
            gamepad = InputDevice('/dev/input/event2')

            while True:
                r, w, x = select.select([gamepad],[],[])
                time.sleep(READ_INT)
                events = []
                for ev in gamepad.read():
                    if ev.type != 0 and ev.code in [304,305,307,308, 314,316,16,17]:
                        events.append(ev)
                    else:
                        continue
                    if ev.type == ecodes.EV_KEY and ev.code in button_presses:
                        if is_emergency(ev):
                            print('emergency')
                            with Telnet(picomotor_ip, 23) as pico:
                                _pico= pico_controller(pico)
                                _pico.gnd_all()
                #print(events)
                if len(events) == 1:
                    run_event(events[-1])
                elif len(events) > 1:
                    run_event(events[-1])
                    run_event(events[-2])
                else:
                    continue


        except Exception as e:
                time.sleep(1)
