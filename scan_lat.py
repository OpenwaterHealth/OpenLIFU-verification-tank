#
# Copyright (C) 2018-2022 Pico Technology Ltd. See LICENSE file for terms.
#
# PS5000A BLOCK MODE EXAMPLE
# This example opens a 5000a driver device, sets up two channels and a trigger then collects a block of data.
# This data is then plotted as mV against time in ns.
from __future__ import annotations

import ctypes
import logging
import os
import sys
import time
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from picoscope import Picoscope
from qpx600dp import QPX600DP

import openlifu
from openlifu.bf.pulse import Pulse
from openlifu.bf.sequence import Sequence
from openlifu.db import Database
from openlifu.geo import Point
from openlifu.io.LIFUInterface import LIFUInterface
from openlifu.io.LIFUTXDevice import Tx7332DelayProfile
from openlifu.plan.solution import Solution

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Prevent duplicate handlers and cluttered terminal output
if not logger.hasHandlers():
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
    logger.addHandler(handler)
    logger.propagate = False

log_interval = 1  # seconds; you can adjust this variable as needed

# set focus
xInput = 0
yInput = 0
zInput = 50
xfoci = np.linspace(-10, 10, 41)
yfoci = [0]

frequency_kHz = 400 # Frequency in kHz
voltage = 10.0 # Voltage in Volts
duration_msec = 20/400 # Pulse Duration in milliseconds
interval_msec = 20 # Pulse Repetition Interval in milliseconds
num_modules = 1 # Number of modules in the system
uniform_apodization=True

peak_to_peak_voltage = voltage * 2 # Peak to peak voltage for the pulse

openlifu_path = Path(openlifu.__file__).parent.parent.parent.resolve()
db_path = openlifu_path / "db_dvc"
db = Database(db_path)
arr = db.load_transducer(f"openlifu_{num_modules}x400_evt1")
arr.sort_by_pin()

target = Point(position=(xInput,yInput,zInput), units="mm")
focus = target.get_position(units="mm")
distances = np.sqrt(np.sum((focus - arr.get_positions(units="mm"))**2, 1)).reshape(1,-1)
tof = distances*1e-3 / 1500
delays = tof.max() - tof
print(f"TOF Max = {tof.max()*1e6} us")

apodizations = np.ones((1, arr.numelements()))

logger.info("Starting LIFU Test Script...")
with LIFUInterface(ext_power_supply=True) as interface, Picoscope(resolution="15BIT") as scope, QPX600DP() as hv:
    tx_connected, hv_connected = interface.is_device_connected()
    hv.set_all_outputs(False)

    if tx_connected:
        logger.info(f"  TX Connected: {tx_connected}")
        logger.info("✅ LIFU Device fully connected.")
    else:
        logger.error("❌ TX NOT fully connected.")
        sys.exit(1)

    stop_logging = False  # flag to signal the logging thread to stop

    # Verify communication with the devices
    if not interface.txdevice.ping():
        logger.error("Failed to ping the transmitter device.")
        sys.exit(1)
    try:
        tx_firmware_version = interface.txdevice.get_version()
        logger.info(f"TX Firmware Version: {tx_firmware_version}")
    except Exception as e:
        logger.error(f"Error querying TX firmware version: {e}")

    logger.info("Enumerate TX7332 chips")
    num_tx_devices = interface.txdevice.enum_tx7332_devices()
    if num_tx_devices == 0:
        raise ValueError("No TX7332 devices found.")
    elif num_tx_devices == num_modules*2:
        logger.info(f"Number of TX7332 devices found: {num_tx_devices}")
        numelements = 32*num_tx_devices
    else:
        raise Exception(f"Number of TX7332 devices found: {num_tx_devices} != 2x{num_modules}")

    logger.info(f'Apodizations: {apodizations}')
    logger.info(f'Delays: {delays}')

    pulse = Pulse(frequency=frequency_kHz*1e3, duration=duration_msec*1e-3)

    sequence = Sequence(
        pulse_interval=interval_msec*1e-3,
        pulse_count=2,
        pulse_train_interval=0,
        pulse_train_count=1
    )

    pin_order = np.argsort([el.pin for el in arr.elements])
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

    for output in [1,2]:
        hv.set_voltage(output, voltage=voltage)
        
    interface.set_solution(
        solution=solution,
        profile_index=profile_index,
        profile_increment=profile_increment,
        trigger_mode=trigger_mode)

    logger.info("Get Trigger")
    trigger_setting = interface.txdevice.get_trigger_json()
    if trigger_setting:
        logger.info(f"Trigger Setting: {trigger_setting}")
    else:
        logger.error("Failed to get trigger setting.")
        sys.exit(1)

    duty_cycle = int((duration_msec/interval_msec) * 100)
    if duty_cycle > 50:
        logger.warning("❗❗ Duty cycle is above 50% ❗❗")

    logger.info(f"User parameters set: \n\
        Module Invert: {arr.module_invert}\n\
        Frequency: {frequency_kHz}kHz\n\
        Voltage Per Rail: {voltage}V\n\
        Voltage Peak to Peak: {peak_to_peak_voltage}V\n\
        Duration: {duration_msec}ms\n\
        Interval: {interval_msec}ms\n\
        Duty Cycle: {duty_cycle}%\n")

    # Create chandle and status ready for use

    scope.set_channel('A', range_mv=100, coupling='DC')
    scope.set_channel('B', range_mv=5000, coupling='DC')
    scope.set_trigger(channel='A', threshold_mv=-2, direction='falling')

    # Set number of pre and post trigger samples to be collected
    preTriggerSamples = 2500
    postTriggerSamples = 10000

    hv.set_all_outputs(True)

    s = input("Press any key to start")

    outputs = []
    for yfocus in yfoci:
        for xfocus in xfoci:            
            focus = np.array([xfocus, yfocus, zInput])
            logger.info(f"calculating delays for {focus=}")
            distances = np.sqrt(np.sum((focus - arr.get_positions(units="mm"))**2, 1)).reshape(-1)
            tof = distances*1e-3 / 1500
            delays = tof.max() - tof
            delay_profile = Tx7332DelayProfile(
                        profile=1,
                        delays=delays,
                        apodizations=apodizations[0,:]
                    )
            interface.txdevice.tx_registers.add_delay_profile(delay_profile)
            logger.info("writing registers...")
            control_registers = interface.txdevice.tx_registers.get_delay_control_registers()
            data_registers = interface.txdevice.tx_registers.get_delay_data_registers(pack=True, pack_single=True)
            for txi, (ctrl_regs, data_regs) in enumerate(zip(control_registers, data_registers)):
                if not uniform_apodization:
                    for addr, reg_values in ctrl_regs.items():
                        if not interface.txdevice.write_register(identifier=txi, address=addr, value=reg_values):
                            logger.error(f"Error applying TX CHIP ID: {txi} registers")
                for addr, reg_values in data_regs.items():
                    if not interface.txdevice.write_block(identifier=txi, start_address=addr, reg_values=reg_values):
                        logger.error(f"Error applying TX CHIP ID: {txi} registers")

            logger.info("Sending Single Trigger...")
            scope.run_block(pre_trigger_samples=preTriggerSamples, post_trigger_samples=postTriggerSamples, timebase=8)
            time.sleep(0.01)
            interface.txdevice.start_trigger()
            scope.wait_ready()
            outputs.append(scope.get_data(preTriggerSamples+postTriggerSamples, 8))

    interface.txdevice.stop_trigger()
    hv.set_all_outputs(False)

logger.info("Finished")
# plot data from channel A and B
t = outputs[0]["time"]
outputs = np.array([output["A"] for output in outputs]).reshape([len(yfoci), len(xfoci), -1])
savedata = {'t':t, "outputs":outputs, "xfoci":xfoci, "yfoci":yfoci}
np.savez("foo.npz", **savedata)
