"""
Interface for the AIM TTi QPX600DP power supply.
"""

import serial
import serial.tools.list_ports
import time

class QPX600DP:
    """
    A pythonic interface to control an AIM QPX600DP over serial.
    """

    VID = 0x103E
    PID = 0x0456

    def __init__(self, port='auto'):
        """
        Initializes the QPX600DP controller.

        Args:
            port (str): The COM port to connect to. If 'auto', the first
                        device with matching VID and PID will be used.
        """
        if port == 'auto':
            self.port = self._find_device()
            if self.port is None:
                raise ConnectionError("Could not find a QPX600DP device.")
        else:
            self.port = port
        
        self.ser = None

    def __enter__(self):
        """
        Context manager entry point.
        """
        self.connect()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """
        Context manager exit point.
        """
        self.disconnect()

    def _find_device(self):
        """
        Finds the first COM port with a matching VID and PID.

        Returns:
            str: The COM port string, or None if no device is found.
        """
        ports = serial.tools.list_ports.comports()
        for port in ports:
            if port.vid == self.VID and port.pid == self.PID:
                return port.device
        return None

    def connect(self):
        """
        Connects to the device.
        """
        self.ser = serial.Serial(self.port, 9600, timeout=1, xonxoff=True)

    def disconnect(self):
        """
        Disconnects from the device.
        """
        if self.ser and self.ser.is_open:
            self.ser.close()

    def _send_command(self, command):
        """
        Sends a command to the device.

        Args:
            command (str): The command to send.
        """
        if self.ser is None or not self.ser.is_open:
            raise ConnectionError("Not connected to a device.")
        
        self.ser.write(f"{command}\n".encode('ascii'))
        self.ser.flush()

    def _query(self, query):
        """
        Sends a query to the device and returns the response.

        Args:
            query (str): The query to send.

        Returns:
            str: The device's response.
        """
        self._send_command(query)
        response = self.ser.readline().decode('ascii').strip()
        return response

    # Instrument Specific Commands
    def set_voltage(self, voltage, *, output='both'):
        """
        Sets the output voltage.

        Args:
            voltage (float): The desired voltage.
            output (int or 'both'): The output channel (1, 2, or 'both').
        """
        outputs = [1, 2] if output == 'both' else [output]
        for out in outputs:
            self._send_command(f"V{out} {voltage}")

    def wait_ready(self, target=None, *, output='both', timeout=1.0, thresh=0.02, poll_interval=0.001) -> bool:
        """
        Waits for the output voltage to settle.

        Args:
            target (float, optional): The target voltage. Defaults to the set voltage.
            output (int or 'both'): The output channel (1, 2, or 'both').
            timeout (float): The maximum time to wait.
            thresh (float): The acceptable error threshold.
            poll_interval (float): The time between checks.

        Returns:
            bool: True if the voltage settled, False otherwise.
        """
        outputs = [1, 2] if output == 'both' else [output]
        for out in outputs:
            if not self.get_output_state(out):
                continue  # No output to sync

            _target = target if target is not None else self.get_set_voltage(out)

            t0 = time.time()
            while True:
                actual_v = self.get_output_voltage(out)
                if abs(actual_v - _target) / _target <= thresh:
                    break
                if (time.time() - t0) > timeout:
                    return False
                time.sleep(poll_interval)
        return True

    def get_set_voltage(self, output):
        """
        Gets the set voltage of an output.

        Args:
            output (int): The output channel (1 or 2).

        Returns:
            float: The set voltage.
        """
        response = self._query(f"V{output}?")
        return float(response.split(' ')[1])

    def get_output_voltage(self, output):
        """
        Gets the actual output voltage of an output.

        Args:
            output (int): The output channel (1 or 2).

        Returns:
            float: The output voltage.
        """
        response = self._query(f"V{output}O?")
        return float(response.removesuffix('V'))

    def set_current_limit(self, output, current):
        """
        Sets the output current limit.

        Args:
            output (int): The output channel (1 or 2).
            current (float): The desired current limit.
        """
        self._send_command(f"I{output} {current}")

    def get_set_current_limit(self, output):
        """
        Gets the set current limit of an output.

        Args:
            output (int): The output channel (1 or 2).

        Returns:
            float: The set current limit.
        """
        response = self._query(f"I{output}?")
        return float(response.split(' ')[1])

    def get_output_current(self, output):
        """
        Gets the actual output current of an output.

        Args:
            output (int): The output channel (1 or 2).

        Returns:
            float: The output current.
        """
        response = self._query(f"I{output}O?")
        return float(response.removesuffix('A'))

    def set_output(self, output, state):
        """
        Sets the output on or off.

        Args:
            output (int): The output channel (1 or 2).
            state (bool): True for on, False for off.
        """
        self._send_command(f"OP{output} {1 if state else 0}")

    def get_output_state(self, output):
        """
        Gets the output state.

        Args:
            output (int): The output channel (1 or 2).

        Returns:
            bool: True if the output is on, False otherwise.
        """
        response = self._query(f"OP{output}?")
        return response == '1'

    def set_all_outputs(self, state):
        """
        Sets all outputs on or off.

        Args:
            state (bool): True for on, False for off.
        """
        self._send_command(f"OPALL {1 if state else 0}")

    def set_over_voltage_protection(self, output, voltage):
        """
        Sets the over voltage protection trip point.

        Args:
            output (int): The output channel (1 or 2).
            voltage (float): The desired trip point voltage.
        """
        self._send_command(f"OVP{output} {voltage}")

    def get_over_voltage_protection(self, output):
        """
        Gets the over voltage protection trip point.

        Args:
            output (int): The output channel (1 or 2).

        Returns:
            float: The trip point voltage.
        """
        response = self._query(f"OVP{output}?")
        return float(response.split(' ')[1])

    def set_over_current_protection(self, output, current):
        """
        Sets the over current protection trip point.

        Args:
            output (int): The output channel (1 or 2).
            current (float): The desired trip point current.
        """
        self._send_command(f"OCP{output} {current}")

    def get_over_current_protection(self, output):
        """
        Gets the over current protection trip point.

        Args:
            output (int): The output channel (1 or 2).

        Returns:
            float: The trip point current.
        """
        response = self._query(f"OCP{output}?")
        return float(response.split(' ')[1])

    def set_sense_mode(self, output, remote):
        """
        Sets the sense mode for an output.

        Args:
            output (int): The output channel (1 or 2).
            remote (bool): True for remote, False for local.
        """
        self._send_command(f"SENSE{output} {1 if remote else 0}")

    def set_config(self, mode):
        """
        Sets the operating mode of the instrument.

        Args:
            mode (int): The operating mode (0, 2, 3, or 4).
        """
        if mode not in [0, 2, 3, 4]:
            raise ValueError("Invalid mode. Must be 0, 2, 3, or 4.")
        self._send_command(f"CONFIG {mode}")

    def get_config(self):
        """
        Gets the operating mode of the instrument.

        Returns:
            int: The operating mode.
        """
        return int(self._query("CONFIG?"))

    # System and Status Commands
    def clear_status(self):
        """
        Clears the status registers.
        """
        self._send_command("*CLS")

    def reset(self):
        """
        Resets the instrument to factory defaults.
        """
        self._send_command("*RST")

    def get_id(self):
        """
        Gets the instrument identification string.

        Returns:
            str: The identification string.
        """
        return self._query("*IDN?")
