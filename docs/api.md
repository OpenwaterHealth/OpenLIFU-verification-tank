# OpenLIFU Verification Tank API Documentation

This documentation covers the Python API for the OpenLIFU verification tank system. The system provides automated control and measurement capabilities for acoustic field verification using focused ultrasound transducers.

## Overview

The verification tank system consists of several key components that work together to provide comprehensive acoustic field measurement capabilities:

- **Transducer Control**: Integration with OpenLIFU system for precise beam steering and focusing
- **Data Acquisition**: High-speed oscilloscope interface for pressure field measurements  
- **Power Management**: Programmable power supply control for drive voltage regulation
- **Hydrophone Integration**: Calibrated hydrophone interface for absolute pressure measurements
- **Automation**: High-level interfaces for automated scanning and optimization

## Core Classes

### [Hydrophone](hydrophone_class.md)
The `Hydrophone` class handles calibrated hydrophone data processing, including:
- Calibration file parsing and metadata extraction
- Frequency-dependent sensitivity interpolation
- Voltage-to-pressure deconvolution with frequency response compensation
- Support for Onda Corporation and similar calibration formats

**Key Features:**
- Automatic calibration file format detection
- Scipy-based interpolation for arbitrary frequency sensitivity
- Built-in frequency response deconvolution
- Comprehensive metadata extraction

### [Picoscope](picoscope_class.md)
The `Picoscope` class provides a high-level interface to PicoScope 5000A series oscilloscopes:
- Context-managed device connection and configuration
- Multi-channel data acquisition with flexible trigger options
- Automatic ADC-to-voltage conversion with calibrated scaling
- Support for various resolution modes and sampling rates

**Key Features:**
- Pythonic API wrapping low-level PicoSDK calls
- Flexible channel configuration (voltage ranges, coupling, offsets)
- Advanced trigger capabilities (edge, level, delay)
- Efficient block-mode data capture

### [QPX600DP](qpx600dp_class.md)
The `QPX600DP` class controls AIM TTi QPX600DP dual-channel power supplies:
- Serial communication with automatic device discovery
- Independent dual-channel voltage and current control
- Built-in protection settings and monitoring
- Real-time voltage settling detection

**Key Features:**
- USB VID/PID-based automatic device detection
- Dual-channel independent or synchronized operation
- Comprehensive protection and monitoring capabilities
- Voltage settling detection with configurable thresholds

### [VerificationTank](verificationtank_class.md)
The `VerificationTank` class orchestrates the complete measurement system:
- Multi-instrument coordination and synchronization
- High-level measurement automation and scanning
- Acoustic focus control with real-time positioning
- Automated peak finding and field optimization

**Key Features:**
- Context-managed multi-instrument operation
- Synchronized pulse generation and data acquisition
- Automated 2D/3D field scanning capabilities
- Gradient ascent-based focus optimization

## System Architecture

```
                    ┌──────────────────┐
                    │ VerificationTank │  (Software Control Layer)
                    │   Orchestration  │
                    └─────────┬────────┘
                              │ Controls
                              ▼
         ┌────────────────────────────────────────────────────┐
         │                                                    │
         ▼                           ▼                        ▼
┌──────────────────┐        ┌──────────────┐         ┌───────────────┐
│     QPX600DP     │   HV   │   OpenLIFU   │  TRIG   │   Picoscope   │◄──┐
│  (Power Supply)  │───────►│    System    │────────►│   (Data Acq)  │   │
└──────────────────┘        └─────────┬────┘         └───────────────┘   │
                                      │                                  │
                                      │ Drive Signal                     │
                                      ▼                                  │ Voltage
                            ┌────────────────┐                           │ Output
                            │   Transducer   │                           │
                            │     Array      │                           │
                            └─────────┬──────┘                           │
                                      │                                  │
                                      │ Ultrasound                       │
                                      │ Emission                         │
                                      ▼                                  │
                            ┌────────────────┐                           │
                            │   Hydrophone   │                           │
                            │   (Pressure)   │───────────────────────────┘
                            └────────────────┘               
```

## Quick Start Guide

### Basic Setup
```python
from openlifu_verification import VerificationTank, Hydrophone
from pathlib import Path

# Load hydrophone calibration
hydrophone = Hydrophone(Path("calibration_file.txt"))

# Initialize verification system
with VerificationTank(frequency=400, use_picoscope=True) as tank:
    # Configure measurement parameters
    tank.configure_lifu(
        frequency_kHz=400,
        voltage=50,
        duration_msec=1.0,
        interval_msec=100
    )
    
    # Set focus position
    tank.set_focus(x=0, y=0, z=30)  # mm
    
    # Capture pressure data
    data = tank.run_capture()
    
    # Convert to pressure using hydrophone calibration
    sensitivity = hydrophone.get_sensitivity_pa_per_v(400e3)  # 400 kHz
    pressure_pa = data['A'] * sensitivity
    
    print(f"Peak pressure: {np.max(pressure_pa):.0f} Pa")
```

### Automated Field Mapping
```python
with VerificationTank() as tank:
    tank.configure_lifu(frequency_kHz=1000, voltage=75, duration_msec=0.5, interval_msec=50)
    
    # Define measurement grid
    x_range = np.linspace(-10, 10, 21)  # ±10 mm, 1 mm steps
    y_range = np.linspace(-10, 10, 21)
    z_focus = 25  # mm
    
    # Automated 2D scan
    pressure_map = np.zeros((len(x_range), len(y_range)))
    
    for i, x in enumerate(x_range):
        for j, y in enumerate(y_range):
            pressure_map[i, j] = tank.get_peak_voltage(x, y, z_focus)
    
    # Find peak location
    peak_idx = np.unravel_index(np.argmax(pressure_map), pressure_map.shape)
    peak_x = x_range[peak_idx[0]]
    peak_y = y_range[peak_idx[1]]
    
    print(f"Peak pressure at ({peak_x:.1f}, {peak_y:.1f}) mm")
```

## Installation Requirements

### Hardware
- PicoScope 5000A series oscilloscope
- AIM TTi QPX600DP power supply
- OpenLIFU transducer system
- Calibrated hydrophone with tank positioning system

### Software Dependencies
```bash
pip install numpy scipy pandas matplotlib
pip install pyserial
pip install picosdk
pip install openlifu
```

### USB Drivers
- Install PicoScope drivers from Pico Technology
- Install QPX600DP drivers from AIM TTi
- Ensure OpenLIFU system drivers are installed

## Common Measurement Workflows

### 1. Frequency Response Characterization
Measure transducer response across frequency range with calibrated pressure measurements.

### 2. Beam Profile Mapping  
2D or 3D scanning to characterize acoustic field distribution and beam geometry.

### 3. Focus Optimization
Automated peak finding to determine optimal focus position for maximum pressure.

### 4. Drive Voltage Linearity
Systematic voltage sweeps to characterize pressure vs. drive voltage relationships.

### 5. Temporal Response Analysis
High-speed capture of pulse waveforms for rise time, duration, and stability analysis.

## Best Practices

### Safety
- Always use appropriate drive voltage limits for your transducer
- Implement proper interlock systems for high-power operation
- Monitor for cavitation and heating effects during extended operation

### Measurement Accuracy
- Allow adequate settling time between measurements
- Use appropriate sampling rates for your frequency range
- Calibrate hydrophone positioning system regularly
- Account for temperature effects on sound speed

### System Performance
- Use context managers for proper resource cleanup
- Implement error handling for robust automated measurements
- Choose optimal resolution modes based on signal amplitude
- Consider measurement time vs. spatial resolution trade-offs

## Troubleshooting

### Common Issues
1. **Instrument Connection Failures**: Check USB connections and driver installations
2. **Trigger Issues**: Verify signal levels and trigger threshold settings
3. **Positioning Errors**: Calibrate coordinate system and check mechanical systems
4. **Communication Timeouts**: Verify instrument availability and reduce polling rates

### Performance Optimization
- Use efficient scanning patterns to minimize measurement time
- Implement parallel processing for data analysis
- Cache calibration data for repeated measurements
- Use appropriate data acquisition parameters for your signal characteristics

## Support and Contributing

This documentation covers the primary API interfaces for the OpenLIFU verification tank system. For additional support:

- Check the example scripts in the `scripts/` directory
- Review the test cases in `tests/` for usage patterns
- Refer to the OpenLIFU main documentation for transducer-specific guidance

For contributing improvements or reporting issues, please follow the project's contribution guidelines.