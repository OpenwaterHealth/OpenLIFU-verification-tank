import logging
import sys
from pathlib import Path

from openlifu_verification.verification import OpenLIFUVerification
import openlifu

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
    """
    Finds the x-y peak using gradient ascent.
    """
    transducer_name = "openlifu_1x400_evt1"

    with OpenLIFUVerification(transducer_name=transducer_name) as ver:

        # Initial parameters
        z = 50
        x_start = 0
        y_start = 0

        # Set up the picoscope
        ver.scope.set_channel('A', range_mv=100, coupling='DC')
        ver.scope.set_channel('B', range_mv=5000, coupling='DC')
        ver.scope.set_trigger(channel='B', threshold_mv=1000, direction='rising')

        # Turn on the power supply
        ver.hv.set_all_outputs(True)

        # Find the peak
        x_peak, y_peak = ver.find_peak_by_gradient_ascent(x_start, y_start, z)

        logger.info(f"Peak found at x={x_peak:.2f}, y={y_peak:.2f}")

if __name__ == "__main__":
    main()
