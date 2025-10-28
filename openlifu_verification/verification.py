import logging
import sys
import time

import numpy as np

from .picoscope import Picoscope
from .qpx600dp import QPX600DP

from openlifu.io import LIFUInterface
from openlifu.io.LIFUTXDevice import Tx7332DelayProfile
from openlifu.bf.pulse import Pulse
from openlifu.bf.sequence import Sequence
from openlifu.plan.solution import Solution
from openlifu.transducer import Transducer


logger = logging.getLogger(__name__)


class OpenLIFUVerification:
    """
    A context manager to simplify OpenLIFU verification tasks.
    """

    def __init__(self, transducer_name, picoscope_resolution="15BIT", num_modules=1):
        self.picoscope_resolution = picoscope_resolution
        self.num_modules = num_modules
        self.transducer_name = transducer_name
        self.lifu = None
        self.scope = None
        self.hv = None
        self.arr = None

    def __enter__(self):
        """
        Initializes and connects to all the required instruments.
        """
        try:
            self.lifu = LIFUInterface(ext_power_supply=True)
            self.scope = Picoscope(resolution=self.picoscope_resolution)
            self.hv = QPX600DP()

            self.lifu.__enter__()
            self.scope.__enter__()
            self.hv.__enter__()

            tx_connected, hv_connected = self.lifu.is_device_connected()
            self.hv.set_all_outputs(False)

            if tx_connected:
                logger.info(f"  TX Connected: {tx_connected}")
                logger.info("✅ LIFU Device fully connected.")
            else:
                raise ConnectionError("❌ TX NOT fully connected.")

            if not self.lifu.txdevice.ping():
                raise ConnectionError("Failed to ping the transmitter device.")

            tx_firmware_version = self.lifu.txdevice.get_version()
            logger.info(f"TX Firmware Version: {tx_firmware_version}")

            num_tx_devices = self.lifu.txdevice.enum_tx7332_devices()
            if num_tx_devices == 0:
                raise ValueError("No TX7332 devices found.")
            elif num_tx_devices != self.num_modules * 2:
                 raise Exception(f"Number of TX7332 devices found: {num_tx_devices} != 2x{self.num_modules}")
            logger.info(f"Number of TX7332 devices found: {num_tx_devices}")

            self.arr = Transducer.from_file(f"transducers/{self.transducer_name}.yaml")
            self.arr.sort_by_pin()


        except Exception as e:
            logger.error(f"Error during initialization: {e}")
            self.__exit__(None, None, None)
            raise

        return self

    def configure_lifu(self, frequency_kHz, voltage, duration_msec, interval_msec):

        pulse = Pulse(frequency=frequency_kHz*1e3, duration=duration_msec*1e-3)

        sequence = Sequence(
            pulse_interval=interval_msec*1e-3,
            pulse_count=2,
            pulse_train_interval=0,
            pulse_train_count=1
        )

        #Dummy values for delays and apodizations
        delays = np.zeros((1, self.arr.numelements()))
        apodizations = np.ones((1, self.arr.numelements()))

        pin_order = np.argsort([el.pin for el in self.arr.elements])
        solution = Solution(
            delays = delays[:, pin_order],
            apodizations = apodizations[:, pin_order],
            pulse = pulse,
            voltage=voltage,
            sequence = sequence
        )
        profile_index = 1
        profile_increment = True
        trigger_mode = "single"

        self.hv.set_voltage(voltage)

        self.lifu.set_solution(
            solution=solution,
            profile_index=profile_index,
            profile_increment=profile_increment,
            trigger_mode=trigger_mode)

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Disconnects from all instruments and cleans up resources.
        """
        if self.hv:
            try:
                self.hv.set_all_outputs(False)
            except Exception as e:
                logger.error(f"Error turning off HV outputs: {e}")
            self.hv.__exit__(exc_type, exc_val, exc_tb)
        if self.scope:
            self.scope.__exit__(exc_type, exc_val, exc_tb)
        if self.lifu:
            self.lifu.__exit__(exc_type, exc_val, exc_tb)

        logger.info("All instruments disconnected.")

    def set_focus(self, x, y, z, apodizations=None):
        if self.arr is None:
            raise Exception("Transducer array not loaded. Please provide db_path during initialization.")

        focus = np.array([x, y, z])
        logger.info(f"calculating delays for {focus=}")
        distances = np.sqrt(np.sum((focus - self.arr.get_positions(units="mm"))**2, 1)).reshape(-1)
        tof = distances*1e-3 / 1500
        delays = tof.max() - tof

        if apodizations is None:
            apodizations = np.ones_like(delays)

        delay_profile = Tx7332DelayProfile(
                    profile=1,
                    delays=delays,
                    apodizations=apodizations
                )
        self.lifu.txdevice.tx_registers.add_delay_profile(delay_profile)
        logger.info("writing registers...")
        control_registers = self.lifu.txdevice.tx_registers.get_delay_control_registers()
        data_registers = self.lifu.txdevice.tx_registers.get_delay_data_registers(pack=True, pack_single=True)

        for txi, (ctrl_regs, data_regs) in enumerate(zip(control_registers, data_registers)):
            #if not uniform_apodization: #TODO add this as a parameter
            #    for addr, reg_values in ctrl_regs.items():
            #        if not self.lifu.txdevice.write_register(identifier=txi, address=addr, value=reg_values):
            #            logger.error(f"Error applying TX CHIP ID: {txi} registers")
            for addr, reg_values in data_regs.items():
                if not self.lifu.txdevice.write_block(identifier=txi, start_address=addr, reg_values=reg_values):
                    logger.error(f"Error applying TX CHIP ID: {txi} registers")


    def run_capture(self, pre_trigger_samples=2500, post_trigger_samples=10000, timebase=8):
        logger.info("Sending Single Trigger...")
        self.scope.run_block(pre_trigger_samples=pre_trigger_samples, post_trigger_samples=post_trigger_samples, timebase=timebase)
        time.sleep(0.01)
        self.lifu.txdevice.start_trigger()
        self.scope.wait_ready()
        return self.scope.get_data(pre_trigger_samples+post_trigger_samples, timebase)

    def set_voltage(self, voltage):
        """
        Sets the voltage on both channels of the HVPS and waits for them to be ready.
        """
        self.hv.set_voltage(voltage)
        self.hv.wait_ready(target=voltage)

    def get_peak_voltage(self, x, y, z):
        """
        Sets the focus to the given coordinates and returns the peak-to-peak voltage.
        """
        self.set_focus(x, y, z)
        data = self.run_capture()
        peak_to_peak = np.max(data['A']) - np.min(data['A'])
        return peak_to_peak

    def find_peak_by_gradient_ascent(self, x_start, y_start, z, step_size=0.5, iterations=10, learning_rate=0.1):
        """
        Finds the x-y coordinates that produce the maximum peak voltage using gradient ascent.
        """
        x = x_start
        y = y_start

        for i in range(iterations):
            # Calculate the gradient
            v_current = self.get_peak_voltage(x, y, z)
            v_x = self.get_peak_voltage(x + step_size, y, z)
            v_y = self.get_peak_voltage(x, y + step_size, z)

            grad_x = (v_x - v_current) / step_size
            grad_y = (v_y - v_current) / step_size

            # Update the coordinates
            x += learning_rate * grad_x
            y += learning_rate * grad_y

            logger.info(f"Iteration {i+1}/{iterations}: x={x:.2f}, y={y:.2f}, Vp-p={v_current:.2f}")

        return x, y
