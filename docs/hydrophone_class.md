# Hydrophone Class Documentation

The `Hydrophone` class provides functionality for reading hydrophone calibration files and performing frequency-dependent deconvolution of voltage signals to recover pressure measurements.

## Overview

This class is designed to work with Onda Corporation hydrophone calibration files and similar formats. It can:

1. Parse calibration files to extract metadata and frequency-dependent sensitivity data
2. Provide sensitivity values (Pa/V) at arbitrary frequencies through interpolation
3. Deconvolve voltage vs time signals to recover pressure vs time, accounting for frequency-dependent response

## Installation

The class requires the following dependencies (automatically installed with the project):
- `numpy` - for numerical operations
- `pandas` - for data handling
- `scipy` - for interpolation and signal processing
- `matplotlib` (optional) - for plotting calibration data

## Usage

### Basic Usage

```python
from openlifu_verification import Hydrophone
from pathlib import Path

# Load hydrophone calibration
cal_file = Path("path/to/calibration_file.txt")
hydrophone = Hydrophone(cal_file)

# Get basic information
print(hydrophone)  # Shows manufacturer, model, serial number, aperture
metadata = hydrophone.get_metadata_summary()
print(f"Calibrated from {metadata['frequency_range_mhz']['min']:.3f} to {metadata['frequency_range_mhz']['max']:.1f} MHz")
```

### Querying Sensitivity

```python
# Get sensitivity at specific frequencies
freq_hz = 5e6  # 5 MHz
sensitivity = hydrophone.get_sensitivity_pa_per_v(freq_hz)
print(f"Sensitivity at 5 MHz: {sensitivity:.2e} Pa/V")

# Get sensitivity for multiple frequencies
frequencies = np.array([1e6, 5e6, 10e6])  # 1, 5, 10 MHz
sensitivities = hydrophone.get_frequency_response(frequencies)
```

### Deconvolving Voltage Signals

```python
import numpy as np

# Example: voltage signal from measurement
fs = 100e6  # 100 MHz sampling rate
voltage_signal = np.array([...])  # Your measured voltage data
sampling_interval = 1.0 / fs

# Deconvolve to get pressure
pressure_signal = hydrophone.deconvolve_voltage_signal(voltage_signal, sampling_interval)
```

### Plotting Calibration Data

```python
# Plot the calibration curves
fig = hydrophone.plot_calibration_data()
import matplotlib.pyplot as plt
plt.show()
```

## Calibration File Format

The class expects calibration files in the following format:

```
# Comments start with #
# 
# Metadata fields are tab-separated key-value pairs
Calibration_DATE	19-Dec-2022
HYD_MFG	Onda
HYD_MODEL	HNR
HYD_SN	2246
# ... more metadata ...

# Data field definitions
DATA_FIELDS	5
DATA_FIELD	FREQ_MHz
DATA_FIELD	SENS_DB
DATA_FIELD	SENS_VPERPA
DATA_FIELD	SENS_V2CM2PERW
DATA_FIELD	CAP_PF

# End of header marker
HEADER_END	0

# Tabular data (tab or space separated)
0.030	-259.54	1.055E-007	1.669E-004	188.506
0.035	-259.99	1.001E-007	1.504E-004	188.506
# ... more data rows ...
```

## Class Methods

### `__init__(calibration_file_path)`
Initialize the hydrophone object by loading a calibration file.

**Parameters:**
- `calibration_file_path`: Path to the calibration file (string or Path object)

### `get_sensitivity_pa_per_v(frequency_hz)`
Get the sensitivity in Pa/V at a specific frequency.

**Parameters:**
- `frequency_hz`: Frequency in Hz (float)

**Returns:**
- Sensitivity in Pa/V (float)

### `get_frequency_response(frequencies_hz)`
Get the frequency response for multiple frequencies.

**Parameters:**
- `frequencies_hz`: Array of frequencies in Hz (numpy array)

**Returns:**
- Array of sensitivities in Pa/V (numpy array)

### `deconvolve_voltage_signal(voltage_signal, sampling_interval)`
Deconvolve a voltage signal to recover pressure, accounting for frequency-dependent sensitivity.

**Parameters:**
- `voltage_signal`: Voltage vs time data (numpy array)
- `sampling_interval`: Time between samples in seconds (float)

**Returns:**
- Pressure vs time data (numpy array)

**Note:** This method uses FFT-based deconvolution to apply the inverse frequency response of the hydrophone.

### `get_metadata_summary()`
Get a summary of hydrophone metadata.

**Returns:**
- Dictionary with key metadata fields and frequency range information

### `plot_calibration_data(figsize=(12, 8))`
Plot the calibration data showing sensitivity, capacitance, and power sensitivity vs frequency.

**Parameters:**
- `figsize`: Figure size tuple (optional)

**Returns:**
- matplotlib figure object

## Attributes

### `metadata`
Dictionary containing all metadata from the calibration file.

### `calibration_data`
Pandas DataFrame containing the frequency-dependent calibration data with columns as specified in the DATA_FIELD entries.

### `sensitivity_interp`
Scipy interpolation function for sensitivity vs frequency (used internally).

## Example Applications

### 1. Calibrating Measured Data

```python
# Load hydrophone
hydrophone = Hydrophone("calibration_file.txt")

# Your measurement data
voltage_measurements = load_voltage_data()  # Your function to load data
sampling_rate = 100e6  # Hz

# Convert to pressure
pressure_measurements = hydrophone.deconvolve_voltage_signal(
    voltage_measurements, 
    1.0 / sampling_rate
)
```

### 2. Frequency Response Analysis

```python
# Check sensitivity across frequency range
frequencies = np.logspace(5, 7.3, 100)  # 100 kHz to 20 MHz
sensitivities = hydrophone.get_frequency_response(frequencies)

import matplotlib.pyplot as plt
plt.semilogx(frequencies/1e6, sensitivities)
plt.xlabel('Frequency (MHz)')
plt.ylabel('Sensitivity (Pa/V)')
plt.title('Hydrophone Frequency Response')
plt.grid(True)
plt.show()
```

### 3. Comparing Multiple Hydrophones

```python
# Load multiple calibrations
hydro1 = Hydrophone("hydrophone1_cal.txt")
hydro2 = Hydrophone("hydrophone2_cal.txt")

# Compare at same frequency
freq = 5e6  # 5 MHz
sens1 = hydro1.get_sensitivity_pa_per_v(freq)
sens2 = hydro2.get_sensitivity_pa_per_v(freq)

print(f"Hydrophone 1 sensitivity at 5 MHz: {sens1:.2e} Pa/V")
print(f"Hydrophone 2 sensitivity at 5 MHz: {sens2:.2e} Pa/V")
print(f"Difference: {abs(sens1-sens2)/sens1*100:.1f}%")
```

## Technical Notes

### Interpolation
- Sensitivity values are interpolated linearly in the linear domain (not dB)
- Extrapolation is allowed for frequencies outside the calibrated range
- For best accuracy, use frequencies within the calibrated range

### Deconvolution
- Uses FFT-based frequency domain deconvolution
- Handles negative frequencies using conjugate symmetry
- DC component uses sensitivity at the lowest calibrated frequency
- Works best when the signal bandwidth is within the hydrophone's calibrated range

### Accuracy Considerations
- Deconvolution accuracy depends on the signal-to-noise ratio
- Best results when the signal frequency content is well within the calibrated range
- Edge frequencies (near the calibration limits) may have reduced accuracy

## Error Handling

The class includes error checking for:
- Invalid calibration file format
- Missing sensitivity interpolator
- Mismatched data columns vs field definitions
- File not found errors

Common issues and solutions:
- **"Sensitivity interpolator not available"**: Check that the calibration file contains SENS_VPERPA data
- **Column mismatch errors**: Verify the calibration file format matches the expected structure
- **Interpolation warnings**: Ensure query frequencies are within or near the calibrated range