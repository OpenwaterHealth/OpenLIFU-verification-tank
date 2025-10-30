import logging
from pathlib import Path
import numpy as np
from openlifu_verification import VerificationTank
import matplotlib.pyplot as plt

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

    frequency_kHz = 400
    voltage = 10.0
    duration_msec = 20 / frequency_kHz
    interval_msec = 10
    num_modules = 1

    logger.info("Starting Single Pulse Script...")
    try:
        with VerificationTank(frequency=frequency_kHz, num_modules=num_modules) as ver:
            # Configure LIFU and HVPS
            ver.configure_lifu(
                frequency_kHz=frequency_kHz,
                voltage=voltage,
                duration_msec=duration_msec,
                interval_msec=interval_msec
            )
            ver.set_focus(xInput, yInput, zInput)

            # Configure Picoscope
            ver.scope.set_channel('A', range_mv=100, coupling='DC')
            ver.scope.set_channel('B', range_mv=5000, coupling='DC')
            ver.scope.set_trigger(channel='A', threshold_mv=-4, direction='falling')

            # Enable power supply
            ver.hv.set_all_outputs(True)
            ver.hv.wait_ready(target=voltage)

            s = input("Press any key to start")

            result = ver.run_capture(pre_trigger_samples=100, post_trigger_samples=1500)

            # Stop the trigger manually after the capture is complete
            ver.lifu.txdevice.stop_trigger()

    except (ConnectionError, ValueError, Exception) as e:
        logger.error(f"An error occurred: {e}")
        return # Exit gracefully

    logger.info("Finished Single Pulse.")
    if result:
        # Plot data
        plt.plot(result["time"], result["A"])
        plt.xlabel('Time (ns)')
        plt.ylabel('Voltage (mV)')
        plt.show()
    else:
        logger.warning("No data was collected.")


if __name__ == "__main__":
    main()
