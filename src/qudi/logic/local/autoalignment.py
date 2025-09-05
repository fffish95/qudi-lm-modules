# Modified from (c) 2019, Robert Kauffman
import numpy as np

from qudi.core.connector import Connector
from qudi.core.statusvariable import StatusVar
from qudi.util import tools
from qudi.core.module import LogicBase
from qudi.util.mutex import Mutex






class autoalignmentLogic(LogicBase):

    """
    autoalignmentlogic:
        module.Class: 'local.sps_custom_scan_logic.SPSCustonScanLogic'
        connect:
            pmc: 'nf8752'
            # thorlabspm1: 'thorlabspm'
            # timetagger: 'tagger'
    """
    # connector
    pmc = Connector(interface='NF8752Logic')
    thorlabspm1 = Connector(interface = "ThorlabsPM", optional=True)
    timetagger = Connector(interface = "TT", optional=True)

    def on_activate(self):
        """ Initialisation performed during activation of the module.
        """
        self._pmc = self.pmc()
        self._tlpm = self.thorlabspm1()
        self._tt = self.timetagger()
        if self._tlpm is not None:
            self._tlpm.connect()
        # Number of samples wanted. The read time per sample is 1 second.
        self.num_samples = 4
        self.motor_alphabet = ['x1','x2','y1','y2','z']
        self.simplex_range = dict(zip(self.motor_alphabet, list([1000]*4+[10000])))

    def on_deactivate(self):
        """ Deinitialisation performed during deactivation of the module.
        """
        if self._tlpm is not None:
            self._tlpm.disconnect()

    def read_output(self):
        """ Read the output of powermeter or timetagger counter.
        """
        if self._tlpm is not None:
            # power measurement
            power_measurements = []
            count = 0 
            while count < self.num_samples:
                power_measurements.append(self._tlpm.get_power())
                count+=1
                tools.delay(1000)
            power_measurements = np.array(power_measurements)
            value = np.mean(power_measurements)
        return value

    def randomize_initial_simplex(self, motor_list, simplex_range):
        """
        pick motor_number +1 positions for initial the simplex, the randomized range could be defined individually for different motors.
        """
        # set current postion to 0
        self._pmc.define_home()

        motor_number = len(motor_list)
        motor_position = [0]*motor_number
        output = self.read_output()
        self.simplex = []
        self.output_simplex = []
        self.simplex.append
        # we need to measure motor_number + 1 positions




    def start_scanner_handler(self, current): 

        value = self.CustomScanMode[current]
        func_map = {
            self.CustomScanMode[0]: self.step_motor_start_scanner,
            self.CustomScanMode[1]: self.power_record_start_scanner,
            self.CustomScanMode[2]: self.EIT_start_scanner,
            self.CustomScanMode[3]: self.stark_shift_scan_start_scanner,
            self.CustomScanMode[4]: self.scan_trigger_start_scanner,
            self.CustomScanMode[5]: self.timetagger_writeintofile_start_scanner,
        }
        func = func_map.get(value)
        func()

    def step_motor_start_scanner(self):
        # select which stepmotor controller
        if self.Params[self._sm_modenum]['step_motor_number'] == 1:
            motor = self.stepmotor1()
        elif self.Params[self._sm_modenum]['step_motor_number']== 2:
            motor = self.stepmotor2()
        else:
            self.log.error("wrong stepmotor number!")
            return -1
        # move the motor to the start point 
        motor.move_abs(self.Params[self._sm_modenum]['motor_channel'], self.Params[self._sm_modenum]['start_deg'])
        # wait until done, the longest wait time = 180*(60/4)*3 = 8100 ms
        t_delay = int(8100)
        tools.delay(t_delay)

    def power_record_start_scanner(self):
        self.Params[self._pr_modenum]['lines_power'] = []
        self._tlpm.connect()     
    
    def EIT_start_scanner(self):
        if self.Params[self._eit_modenum]['wavelength_ramp']:
            self.Params[self._eit_modenum]['lines_frequency'] = []
            self._wavemeter.start_acquisition() # start the measurement
            self._wavemeter.set_exposure_mode(True) # automatically change the exposure time
            set_wavelength = self._wavemeter.convert_unit(self.Params[self._eit_modenum]['start_frequency(THz)'], 'Frequency', 'WavelengthVac')
            self._wavemeter.set_reference_course(set_wavelength)
            self._wavemeter.set_deviation_mode(True)
            # wait until wavelength is stable
            if not self.Params[self._eit_modenum]['Background_subtract']:
                timecounter = 0
                while timecounter < 80:
                    if self._wavemeter._is_stable:
                        break
                    tools.delay(250)
                    timecounter += 1
                if not timecounter<80:
                    self.log.warning('Wavelength not stablized!')
            


        if self.Params[self._eit_modenum]['Background_subtract']:
            for param in self.Params:
                param['measurements_per_action'] *= 2 # add 1 action for background substract
            self._shutter_task = self._nicard.create_do_task(taskname = 'shutter', channels = self.Params[self._eit_modenum]['shutter_channels'])
            # Stop deviation and automatical exposure time before close the shutter
            if self.Params[self._eit_modenum]['wavelength_ramp']:
                self._wavemeter.set_deviation_mode(False)
                self._wavemeter.set_exposure_mode(False)
            self._nicard.write_task(task= self._shutter_task, data = False)
        


    def stark_shift_scan_start_scanner(self):
        # enable voltage source
        self._fugsourcelogic.enable()
        # set to initial voltage
        self._fugsourcelogic.set_V(self.Params[self._ss_modenum]['start_V'])

    def scan_trigger_start_scanner(self):
        # output a trigger before each loop
        self._trigger_task = self._nicard.create_do_task(taskname = 'trigger1', channels = self.Params[self._st_modenum]['trigger_channel'])
        self._nicard.write_task(task= self._trigger_task, data = True)
        # keep the do on for trigger length time
        t_delay = int(self.Params[self._st_modenum]['trigger_length'])
        tools.delay(t_delay)
        self._nicard.write_task(task= self._trigger_task, data = False)
    
    def timetagger_writeintofile_start_scanner(self):
        self._timetaggerlogic._writeintofile_params['sample_name'] = f'{self.Params[self._tw_modenum]["sample_name"]}_0'
        self._timetaggerlogic.start_recording()

    def process_scanner_handler(self, current, scan_counter): 

        value = self.CustomScanMode[current]
        func_map = {
            self.CustomScanMode[0]: self.step_motor_process_scanner,
            self.CustomScanMode[1]: self.power_record_process_scanner,
            self.CustomScanMode[2]: self.EIT_process_scanner,
            self.CustomScanMode[3]: self.stark_shift_scan_process_scanner,
            self.CustomScanMode[4]: self.scan_trigger_process_scanner,
            self.CustomScanMode[5]: self.timetagger_writeintofile_process_scanner,
        }
        func = func_map.get(value)
        func(scan_counter)

    def step_motor_process_scanner(self, scan_counter):
        if self.Params[self._sm_modenum]['step_motor_number'] == 1:
            motor = self.stepmotor1()
        elif self.Params[self._sm_modenum]['step_motor_number']== 2:
            motor = self.stepmotor2()
        else:
            self.log.error("wrong stepmotor number!")
            return -1
        if scan_counter % self.Params[self._sm_modenum]['measurements_per_action'] == 0:
            # move the motor 
            motor.move_rel(self.Params[self._sm_modenum]['motor_channel'], self.Params[self._sm_modenum]['step_deg'])
            # wait until done
            t_delay = int(self.Params[self._sm_modenum]['step_deg']*(60/4)*3) 
            tools.delay(t_delay)

    def power_record_process_scanner(self, scan_counter):
        if self.Params[self._pr_modenum]['step_motor_number'] == 1:
            motor = self.stepmotor1()
        elif self.Params[self._pr_modenum]['step_motor_number']== 2:
            motor = self.stepmotor2()
        else:
            self.log.error("wrong stepmotor number!")
            return -1
        
        if scan_counter % self.Params[self._pr_modenum]['measurements_per_action'] == 0:      
            # connect power meter

            if self.Params[self._pr_modenum]['motor_on']:
                # move the motor to the measurement point 
                motor.move_abs(self.Params[self._pr_modenum]['motor_channel'], self.Params[self._pr_modenum]['running_deg'])
                # wait until done, the longest wait time = 90*(60/4)*3 = 4050 ms
                
                t_delay = int(abs(self.Params[self._pr_modenum]['running_deg'] - self.Params[self._pr_modenum]['idle_deg'])*(60/4)*3)
                tools.delay(t_delay)

            # measurement
            power_measurements = []
            count = 0 
            while count < self.Params[self._pr_modenum]['averages']:
                power_measurements.append(self._tlpm.get_power())
                count+=1
                tools.delay(1000)
            if self.Params[self._pr_modenum]['motor_on']:
                # move the motor to the idle point 
                motor.move_abs(self.Params[self._pr_modenum]['motor_channel'], self.Params[self._pr_modenum]['idle_deg'])
                tools.delay(t_delay)
            power_measurements = np.array(power_measurements)
            value = np.mean(power_measurements) * self.Params[self._pr_modenum]['realpower_to_readout_ratio']
            self.Params[self._pr_modenum]['lines_power'].append(value)

    
    def EIT_process_scanner(self,scan_counter):
        if self.Params[self._eit_modenum]['Background_subtract']:
            if scan_counter % self.Params[self._eit_modenum]['measurements_per_action'] == 0:
                # close the shutter
                if self.Params[self._eit_modenum]['wavelength_ramp']:
                    self._wavemeter.set_deviation_mode(False)
                    self._wavemeter.set_exposure_mode(False)
                self._nicard.write_task(task= self._shutter_task, data = False)
            elif scan_counter % self.Params[self._eit_modenum]['measurements_per_action'] == int(self.Params[self._eit_modenum]['measurements_per_action']/2):
                # open the shutter
                self._nicard.write_task(task= self._shutter_task, data = True)
                if self.Params[self._eit_modenum]['wavelength_ramp']:
                    self._wavemeter.set_deviation_mode(True)
                    self._wavemeter.set_exposure_mode(True)
                    set_frequency = float(self.Params[self._eit_modenum]['start_frequency(THz)'] + self.Params[self._eit_modenum]['step_frequency(MHz)']* (scan_counter // self.Params[self._eit_modenum]['measurements_per_action'])/1e6)
                    set_wavelength = self._wavemeter.convert_unit(set_frequency, 'Frequency', 'WavelengthVac')
                    self._wavemeter.set_reference_course(set_wavelength)
                    self.Params[self._eit_modenum]['lines_frequency'].append(set_frequency)
                    timecounter = 0
                    while timecounter < 80:
                        if self._wavemeter._is_stable:
                            break
                        tools.delay(250)
                        timecounter += 1
                    if not timecounter<80:
                        self.log.warning('Wavelength not stablized!')

        
        elif self.Params[self._eit_modenum]['wavelength_ramp']:
            if scan_counter % self.Params[self._eit_modenum]['measurements_per_action'] == 0:
                set_frequency = float(self.Params[self._eit_modenum]['start_frequency(THz)'] + self.Params[self._eit_modenum]['step_frequency(MHz)']* (scan_counter // self.Params[self._eit_modenum]['measurements_per_action'])/1e6)
                set_wavelength = self._wavemeter.convert_unit(set_frequency, 'Frequency', 'WavelengthVac')
                self._wavemeter.set_reference_course(set_wavelength)
                self.Params[self._eit_modenum]['lines_frequency'].append(set_frequency)
                timecounter = 0
                while timecounter < 80:
                    if self._wavemeter._is_stable:
                        break
                    tools.delay(250)
                    timecounter += 1
                if not timecounter<80:
                    self.log.warning('Wavelength not stablized!')
        

    def stark_shift_scan_process_scanner(self,scan_counter):
        if scan_counter % self.Params[self._ss_modenum]['measurements_per_action'] == 0:
            current_V = self._fugsourcelogic.get_V()
            set_V = current_V + self.Params[self._ss_modenum]['step_V']
            self._fugsourcelogic.set_V(set_V)

    def scan_trigger_process_scanner(self,scan_counter):

        self._nicard.write_task(task= self._trigger_task, data = True)
        # keep the do on for trigger length time
        t_delay = int(self.Params[self._st_modenum]['trigger_length'])
        tools.delay(t_delay)
        self._nicard.write_task(task= self._trigger_task, data = False)

    def timetagger_writeintofile_process_scanner(self,scan_counter):
        if scan_counter % self.Params[self._tw_modenum]['measurements_per_action'] == 0:
            self._timetaggerlogic.stop_recording()
            # wait until done 3000ms
            tools.delay(3000)
            self._timetaggerlogic._writeintofile_params['sample_name'] = f'{self.Params[self._tw_modenum]["sample_name"]}_{scan_counter}'
            self._timetaggerlogic.start_recording()            

    def stop_scanner_handler(self, current): 

        value = self.CustomScanMode[current]
        func_map = {
            self.CustomScanMode[0]: self.step_motor_stop_scanner,
            self.CustomScanMode[1]: self.power_record_stop_scanner,
            self.CustomScanMode[2]: self.EIT_stop_scanner,
            self.CustomScanMode[3]: self.stark_shift_scan_stop_scanner,
            self.CustomScanMode[4]: self.scan_trigger_stop_scanner,
            self.CustomScanMode[5]: self.timetagger_writeintofile_stop_scanner,
        }
        func = func_map.get(value)
        func()

    def step_motor_stop_scanner(self):
        if self.Params[self._pr_modenum]['step_motor_number'] == 1:
            motor = self.stepmotor1()
        elif self.Params[self._pr_modenum]['step_motor_number']== 2:
            motor = self.stepmotor2()
        else:
            self.log.error("wrong stepmotor number!")
            return -1

        # move the motor to the start point 
        motor.move_abs(self.Params[self._sm_modenum]['motor_channel'], self.Params[self._sm_modenum]['start_deg'])
        # wait until done, the longest wait time = 180*(60/4)*3 = 8100 ms
        t_delay = int(8100)
        tools.delay(t_delay)    

    def power_record_stop_scanner(self):
        self._tlpm.disconnect()     
    
    def EIT_stop_scanner(self):
        if self.Params[self._eit_modenum]['Background_subtract']:
            for param in self.Params:
                param['measurements_per_action'] = int(param['measurements_per_action']/2) # remove 1 action added before
            # keep the shutter open
            self._nicard.write_task(task= self._shutter_task, data = True)
            self._nicard.close_do_task(taskname = 'shutter')
            self._shutter_task = None
        if self.Params[self._eit_modenum]['wavelength_ramp']:
            self._wavemeter.stop_acquisition()


    def stark_shift_scan_stop_scanner(self):
        self._fugsourcelogic.disable()

    def scan_trigger_stop_scanner(self):

        self._nicard.close_do_task(taskname = 'trigger1')
        self._trigger_task = None

    def timetagger_writeintofile_stop_scanner(self):
        self._timetaggerlogic.stop_recording()

    def function_0_handler(self, current): 

        value = self.CustomScanMode[current]
        func_map = {
            self.CustomScanMode[0]: self.step_motor_function_0,
            self.CustomScanMode[1]: self.power_record_function_0,
            self.CustomScanMode[2]: self.EIT_function_0,
            self.CustomScanMode[3]: self.stark_shift_scan_function_0,
            self.CustomScanMode[4]: self.scan_trigger_stop_scanner_0,
            self.CustomScanMode[5]: self.timetagger_writeintofile_stop_scanner_0,
        }
        func = func_map.get(value)
        func()

    def step_motor_function_0(self):
        pass

    def power_record_function_0(self):
        pass   
    
    def EIT_function_0(self):
        pass

    def stark_shift_scan_function_0(self):
        pass

    def scan_trigger_stop_scanner_0(self):
        pass

    def timetagger_writeintofile_stop_scanner_0(self):
        pass