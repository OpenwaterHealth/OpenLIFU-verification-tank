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

    frequency_kHz = 400
    voltage = 10.0
    duration_msec = 10 / 400
    interval_msec = 50
    num_modules = 1
    transducer_name = "openlifu_1x400_evt1"

    logger.info("Starting Continuous CLI Script...")
    try:
        with OpenLIFUVerification(transducer_name=transducer_name, num_modules=num_modules) as ver:
            # Configure LIFU and HVPS
            ver.configure_lifu(
                frequency_kHz=frequency_kHz,
                voltage=voltage,
                duration_msec=duration_msec,
                interval_msec=interval_msec
            )
            ver.set_focus(xInput, yInput, zInput)

            command = None
            while True:
                command = input(":")
                if command == "exit":
                    break
                elif command == "start":
                    logger.info("Starting Trigger...")
                    ver.hv.set_all_outputs(True)
                    ver.lifu.txdevice.start_trigger()
                elif command == "stop":
                    logger.info("Stopping Trigger...")
                    ver.lifu.txdevice.stop_trigger()
                    ver.hv.set_all_outputs(False)
                elif command == 'von':
                    ver.hv.set_all_outputs(True)
                elif command == 'voff':
                    ver.hv.set_all_outputs(False)
                elif len(command) > 3 and command[:2] == "v=":
                    try:
                        new_v = float(command.split('=')[-1].strip())
                        ver.set_voltage(new_v)
                    except ValueError:
                        print('Invalid command')
                else:
                    try:
                        focus = [float(x) for x in command.split(",")]
                        if len(focus) == 3:
                            ver.set_focus(*focus)
                        else:
                            print("Invalid coordinates. Please provide x, y, and z.")
                    except ValueError:
                        print('Invalid command')

            # Ensure trigger is stopped and HV is off before exiting
            ver.lifu.txdevice.stop_trigger()
            ver.hv.set_all_outputs(False)

    except (ConnectionError, ValueError, Exception) as e:
        logger.error(f"An error occurred: {e}")
        return # Exit gracefully

    logger.info("Finished Continuous CLI.")

if __name__ == "__main__":
    main()
