import logging
from pathlib import Path
import numpy as np
import openlifu
from openlifu_verification import OpenLIFUVerification

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Prevent duplicate handlers and cluttered terminal output
if not logger.hasHandlers():
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
    logger.addHandler(handler)
    logger.propagate = False

def main():
    # Parameters
    xInput = 0
    yInput = 0
    zInput = 50
    voltages = np.arange(5, 20, 1)

    frequency_kHz = 400
    initial_voltage = 10.0
    duration_msec = 20 / 400
    interval_msec = 20
    num_modules = 1
    transducer_name = "openlifu_1x400_evt1"

    logger.info("Starting Voltage Scan Script...")
    try:
        with OpenLIFUVerification(transducer_name=transducer_name, num_modules=num_modules) as ver:
            # Configure LIFU and HVPS
            ver.configure_lifu(
                frequency_kHz=frequency_kHz,
                voltage=initial_voltage,
                duration_msec=duration_msec,
                interval_msec=interval_msec
            )
            ver.set_focus(xInput, yInput, zInput)

            # Configure Picoscope
            ver.scope.set_channel('A', range_mv=100, coupling='DC')
            ver.scope.set_channel('B', range_mv=5000, coupling='DC')
            ver.scope.set_trigger(channel='A', threshold_mv=-2, direction='falling')

            # Enable power supply
            ver.hv.set_all_outputs(True)

            s = input("Press any key to start")

            outputs = []
            for voltage in voltages:
                ver.set_voltage(voltage)
                data = ver.run_capture(pre_trigger_samples=100, post_trigger_samples=1500)
                outputs.append(data)

            # Stop the trigger manually after the scan is complete
            ver.lifu.txdevice.stop_trigger()

    except (ConnectionError, ValueError, Exception) as e:
        logger.error(f"An error occurred: {e}")
        return # Exit gracefully

    logger.info("Finished Voltage Scan.")
    if outputs:
        # Process and save data
        t = outputs[0]["time"]
        a_channel_outputs = np.array([output["A"] for output in outputs]).reshape([len(voltages), -1])
        savedata = {'t': t, "outputs": a_channel_outputs, "voltages": voltages}
        np.savez("scan_voltage_data.npz", **savedata)
        logger.info("Data saved to scan_voltage_data.npz")
    else:
        logger.warning("No data was collected.")

if __name__ == "__main__":
    main()
