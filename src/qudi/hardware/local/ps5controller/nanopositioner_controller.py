import time
from evdev import InputDevice, categorize, ecodes
from telnetlib import Telnet
import select


attocube_ip = '10.140.1.111'
password = b"123456\n"

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
READ_INT = 0.15                              # read interval - 0.3s

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
    if event.type == ecodes.EV_KEY and event.code in button_presses:       # any button press other than leftpad
        if event.code == 310 and event.value == 1:
            with Telnet(attocube_ip, 7231) as pos:
                _pos= pos_controller(pos)
                pos.read_until(b"Authorization code:")
                pos.write(password)
                _pos.mov_1z_up()
            #print('1zup')

        if event.code == 311 and event.value == 1:
            with Telnet(attocube_ip, 7231) as pos:
                _pos= pos_controller(pos)
                pos.read_until(b"Authorization code:")
                pos.write(password)
                _pos.mov_1z_down()
            #print('1zdown')

    if event.type == ecodes.EV_ABS and event.code in absolutes:                     # leftpad, joystick motion, or L2/R2 triggers
        if event.code == 16:
           if event.value == -1:
                with Telnet(attocube_ip, 7231) as pos:
                    _pos= pos_controller(pos)
                    pos.read_until(b"Authorization code:")
                    pos.write(password)
                    _pos.mov_1x_up()
                #print('1xdown')
           elif event.value == 1:
                with Telnet(attocube_ip, 7231) as pos:
                    _pos= pos_controller(pos)
                    pos.read_until(b"Authorization code:")
                    pos.write(password)
                    _pos.mov_1x_down()
                #print('1xup')


        if event.code == 17:
            if event.value == 1:
                with Telnet(attocube_ip, 7231) as pos:
                    _pos= pos_controller(pos)
                    pos.read_until(b"Authorization code:")
                    pos.write(password)
                    _pos.mov_1y_up()
                #print('1ydown')
            elif event.value == -1:
                with Telnet(attocube_ip, 7231) as pos:
                    _pos= pos_controller(pos)
                    pos.read_until(b"Authorization code:")
                    pos.write(password)
                    _pos.mov_1y_down()
                #print('1yup')

        if event.code == 2 and event.value > L2R2_BLIND:
            with Telnet(attocube_ip, 7231) as pos:
                _pos= pos_controller(pos)
                pos.read_until(b"Authorization code:")
                pos.write(password)
                _pos.mov_nz_up(event.value)
            #print(f'_pos.mov_nz_up({event.value})')

        if event.code == 5 and event.value > L2R2_BLIND:
            with Telnet(attocube_ip, 7231) as pos:
                _pos= pos_controller(pos)
                pos.read_until(b"Authorization code:")
                pos.write(password)
                _pos.mov_nz_down(event.value)
            #print(f'_pos.mov_nz_down({event.value})')

        if event.code == 0:                                              # left joystick moving
            if event.value > (CENTER - BLIND) and event.value < (CENTER + BLIND):   # skip printing the jittery center for the joysticks
                return
            elif event.value > CENTER:
                steps = event.value - CENTER
                with Telnet(attocube_ip, 7231) as pos:
                    _pos= pos_controller(pos)
                    pos.read_until(b"Authorization code:")
                    pos.write(password)
                    _pos.mov_nx_down(steps)
                #print(f'_pos.mov_nx_up({steps})')
            else:
                steps = CENTER - event.value
                with Telnet(attocube_ip, 7231) as pos:
                    _pos= pos_controller(pos)
                    pos.read_until(b"Authorization code:")
                    pos.write(password)
                    _pos.mov_nx_up(steps)
                #print(f'_pos.mov_nx_down({steps})')

        if event.code == 1:                                              # left joystick moving
            if event.value > (CENTER - BLIND) and event.value < (CENTER + BLIND):   # skip printing the jittery center for the joysticks
                return
            elif event.value > CENTER:
                steps = event.value - CENTER
                with Telnet(attocube_ip, 7231) as pos:
                    _pos= pos_controller(pos)
                    pos.read_until(b"Authorization code:")
                    pos.write(password)
                    _pos.mov_ny_up(steps)
                #print(f'_pos.mov_ny_down({steps})')
            else:
                steps = CENTER - event.value
                with Telnet(attocube_ip, 7231) as pos:
                    _pos= pos_controller(pos)
                    pos.read_until(b"Authorization code:")
                    pos.write(password)
                    _pos.mov_ny_down(steps)
                #print(f'_pos.mov_ny_up({steps})')


class pos_controller:
    def __init__(self, pos):
        self.z_axis=4
        self.x_axis=5
        self.y_axis=6

        self.z_module = "m{0}".format(self.z_axis).encode('ascii')
        self.x_module = "m{0}".format(self.x_axis).encode('ascii')
        self.y_module = "m{0}".format(self.y_axis).encode('ascii')

        self.pos = pos

    def gnd_all(self):
        self.pos.write(self.z_module + b":stop()\n")
        self.pos.write(self.x_module + b":stop()\n")
        self.pos.write(self.y_module + b":stop()\n")

        self.pos.write(self.z_module + b".mode = GND\n")
        self.pos.write(self.x_module + b".mode = GND\n")
        self.pos.write(self.y_module + b".mode = GND\n")

    def mov_1x_up(self):
        self.pos.write(self.x_module + b":step(UP,1)\n")

    def mov_1x_down(self):
        self.pos.write(self.x_module + b":step(DOWN,1)\n")

    def mov_1y_up(self):
        self.pos.write(self.y_module + b":step(UP,1)\n")

    def mov_1y_down(self):
        self.pos.write(self.y_module + b":step(DOWN,1)\n")

    def mov_1z_up(self):
        self.pos.write(self.z_module + b":step(UP,1)\n")

    def mov_1z_down(self):
        self.pos.write(self.z_module + b":step(DOWN,1)\n")

    def mov_nx_up(self,steps):
        _steps = "{0}".format(steps).encode('ascii')
        self.pos.write(self.x_module + b":step(UP,"+ _steps + b")\n")

    def mov_nx_down(self,steps):
        _steps = "{0}".format(steps).encode('ascii')
        self.pos.write(self.x_module + b":step(DOWN,"+ _steps + b")\n")

    def mov_ny_up(self,steps):
        _steps = "{0}".format(steps).encode('ascii')
        self.pos.write(self.y_module + b":step(UP,"+ _steps + b")\n")

    def mov_ny_down(self,steps):
        _steps = "{0}".format(steps).encode('ascii')
        self.pos.write(self.y_module + b":step(DOWN,"+ _steps + b")\n")

    def mov_nz_up(self,steps):
        _steps = "{0}".format(steps).encode('ascii')
        self.pos.write(self.z_module + b":step(UP,"+ _steps + b")\n")

    def mov_nz_down(self,steps):
        _steps = "{0}".format(steps).encode('ascii')
        self.pos.write(self.z_module + b":step(DOWN,"+ _steps + b")\n")

if __name__ == '__main__':
    while(True):
        try:
            gamepad = InputDevice('/dev/input/event2')

            while True:
                r, w, x = select.select([gamepad],[],[])
                time.sleep(READ_INT)
                events = []
                for ev in gamepad.read():
                    if ev.type != 0 and ev.code in [310,311,316,16,17]:
                        events.append(ev)
                    elif ev.type != 0 and ev.code in [2,5] and ev.value > L2R2_BLIND:
                        events.append(ev)
                    elif ev.type != 0 and ev.code in [0,1] and (ev.value < (CENTER - BLIND) or ev.value > (CENTER + BLIND)):
                        events.append(ev)
                    else:
                        continue
                    if ev.type == ecodes.EV_KEY and ev.code in button_presses:
                        if is_emergency(ev):
                            #print('emergency')
                            with Telnet(attocube_ip, 7231) as pos:
                                _pos= pos_controller(pos)
                                pos.read_until(b"Authorization code:")
                                pos.write(password)
                                _pos.gnd_all()
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