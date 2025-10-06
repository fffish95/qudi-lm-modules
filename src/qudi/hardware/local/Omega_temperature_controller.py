from pymodbus.client.tcp import ModbusTcpClient as ModbusClient
from qudi.core.configoption import ConfigOption
import struct
from qudi.core.module import Base



class OmegaTemperatureController(Base):
    """ 
        temperature_controller:
        module.Class: 'local.Omega_temperature_controller.OmegaTemperatureController'
        options:
            port:
                '502'
    """
    # config options
    _port = ConfigOption('port', missing='error')

    def __init__(self, **kwargs):
        super().__init__(**kwargs)


    def on_activate(self):
        pass
    

    def on_deactivate(self):
        pass

    def float_to_hex(self, f):
        return hex(struct.unpack('<I', struct.pack('<f', f))[0])

    def read_actual_temperature(self, host):
        client = ModbusClient(host = host, port = self._port)
        client.connect()
        registers_decimal_value = client.read_holding_registers(528,2).registers
        registers_hex_value = ''.join(format(e,'04x') for e in registers_decimal_value)
        client.close()

        return struct.unpack('!f', bytes.fromhex(registers_hex_value))[0]

    def read_setpoint(self, host):
        client = ModbusClient(host = host, port = self._port)
        client.connect()
        registers_decimal_value = client.read_holding_registers(544,2).registers
        registers_hex_value = ''.join(format(e,'04x') for e in registers_decimal_value)
        client.close()

        return struct.unpack('!f', bytes.fromhex(registers_hex_value))[0]

    def write_setpoint(self, host,setpoint):
        client = ModbusClient(host = host, port = self._port)
        client.connect()
        registers_hex_value = hex(struct.unpack('<I', struct.pack('<f', setpoint))[0])
        registers_array = [int(registers_hex_value[2:6],16), int(registers_hex_value[6:11],16)]
        client.write_registers(738,registers_array)
        client.close()