# VerificationTank Class Documentation

The `VerificationTank` class provides a high-level interface for conducting OpenLIFU verification measurements in a tank setup. It orchestrates the interaction between the LIFU transducer system, PicoScope oscilloscope, and QPX600DP power supply to automate acoustic field measurements.

## Overview

This class handles:

1. Initialization and coordination of multiple instruments (LIFU system, oscilloscope, power supply)
2. Transducer configuration and focusing control
3. Pulse parameter setup (frequency, duration, voltage)
4. Synchronized data acquisition and pulse generation
5. Automated peak finding and field mapping
6. Context management for safe multi-instrument operation

## Installation

The class requires the following dependencies:
- `openlifu` - OpenLIFU library for transducer control
- `numpy` - for numerical operations
- `logging` - for operation logging (standard library)
- Local modules: `Picoscope`, `QPX600DP`

## Usage

### Basic Setup

```python
from openlifu_verification import VerificationTank

# Initialize verification tank system
with VerificationTank(frequency=400, use_picoscope=True) as tank:
    # Configure LIFU system
    tank.configure_lifu(
        frequency_kHz=400,
        voltage=50,
        duration_msec=1.0,
        interval_msec=100
    )
    
    # Set focus position
    tank.set_focus(x=0, y=0, z=30)  # mm coordinates
    
    # Configure oscilloscope trigger
    tank.set_scope_trigger(channel="A", threshold_mV=100)
    
    # Capture data
    data = tank.run_capture(pre_trigger_samples=2500, post_trigger_samples=10000)
    
    print(f"Captured signal amplitude: {np.max(data['A']) - np.min(data['A']):.3f} V")
```

### Advanced Field Mapping

```python
with VerificationTank(frequency=400, resolution="15BIT") as tank:
    # Setup measurement parameters
    tank.configure_lifu(frequency_kHz=400, voltage=75, duration_msec=0.5, interval_msec=50)
    tank.set_voltage(75, wait=True)  # Set HVPS voltage
    
    # Define scan grid
    x_positions = np.linspace(-5, 5, 11)  # -5 to +5 mm, 11 points
    y_positions = np.linspace(-5, 5, 11)
    z_focus = 30  # mm
    
    # Perform 2D scan
    field_map = np.zeros((len(x_positions), len(y_positions)))
    
    for i, x in enumerate(x_positions):
        for j, y in enumerate(y_positions):
            # Get peak voltage at this position
            peak_voltage = tank.get_peak_voltage(x, y, z_focus)
            field_map[i, j] = peak_voltage
            print(f"Position ({x:.1f}, {y:.1f}): {peak_voltage:.3f} V")
    
    # Find maximum location
    max_idx = np.unravel_index(np.argmax(field_map), field_map.shape)
    max_x = x_positions[max_idx[0]]
    max_y = y_positions[max_idx[1]]
    print(f"Peak found at ({max_x:.1f}, {max_y:.1f}) mm")
```

## Class Reference

### Constructor

#### `VerificationTank(frequency=400, use_picoscope=True, num_modules=1, resolution="15BIT")`

Creates a new VerificationTank instance.

**Parameters:**
- `frequency` (int): Default operating frequency in kHz (default: 400)
- `use_picoscope` (bool): Enable PicoScope for data acquisition (default: True)
- `num_modules` (int): Number of LIFU modules (default: 1)
- `resolution` (str): PicoScope ADC resolution ("12BIT", "14BIT", "15BIT", "16BIT")

### Context Management

#### `__enter__() -> VerificationTank`

Initializes and connects to all required instruments. Called automatically when using `with` statement.

**Returns:**
- `VerificationTank`: Self reference for chaining

**Raises:**
- Various exceptions if instrument connections fail

#### `__exit__(exc_type, exc_val, exc_tb)`

Safely disconnects from all instruments and cleans up resources. Called automatically when exiting `with` statement.

### System Configuration

#### `configure_lifu(frequency_kHz, voltage, duration_msec, interval_msec, trigger_mode="single")`

Configures the LIFU system with pulse parameters.

**Parameters:**
- `frequency_kHz` (float): Pulse frequency in kHz
- `voltage` (float): Drive voltage
- `duration_msec` (float): Pulse duration in milliseconds
- `interval_msec` (float): Interval between pulses in milliseconds
- `trigger_mode` (str): Trigger mode ("single" or "continuous")

### Focus Control

#### `set_focus(x, y, z, apodizations=None)`

Sets the acoustic focus position.

**Parameters:**
- `x` (float): X coordinate in mm
- `y` (float): Y coordinate in mm  
- `z` (float): Z coordinate in mm
- `apodizations` (array-like, optional): Element apodization weights

**Example:**
```python
# Set focus 30mm in front of transducer, centered
tank.set_focus(x=0, y=0, z=30)

# Set focus with custom apodization
apod = np.ones(64) * 0.8  # 80% amplitude on all elements
tank.set_focus(x=2, y=-1, z=25, apodizations=apod)
```

#### `set_pulse(frequency_kHz, duration_msec)`

Updates pulse parameters without full system reconfiguration.

**Parameters:**
- `frequency_kHz` (float): New pulse frequency in kHz
- `duration_msec` (float): New pulse duration in milliseconds

### Data Acquisition

#### `set_scope_trigger(channel="A", threshold_mV=100, direction="rising")`

Configures oscilloscope trigger settings.

**Parameters:**
- `channel` (str): Trigger channel ("A", "B", "C", "D")
- `threshold_mV` (float): Trigger threshold in millivolts
- `direction` (str): Trigger direction ("rising", "falling")

#### `run_capture(pre_trigger_samples=2500, post_trigger_samples=10000, timebase=8) -> Dict[str, np.ndarray]`

Executes synchronized pulse generation and data capture.

**Parameters:**
- `pre_trigger_samples` (int): Samples before trigger
- `post_trigger_samples` (int): Samples after trigger
- `timebase` (int): Sampling timebase index

**Returns:**
- `Dict[str, np.ndarray]`: Captured data for each channel plus time array

#### `run_capture_with_interval(pre_trigger_samples=2500, post_trigger_samples=10000, sampling_interval_ns=16) -> Dict[str, np.ndarray]`

Alternative capture method using sampling interval instead of timebase.

**Parameters:**
- `pre_trigger_samples` (int): Samples before trigger
- `post_trigger_samples` (int): Samples after trigger
- `sampling_interval_ns` (float): Sampling interval in nanoseconds

**Returns:**
- `Dict[str, np.ndarray]`: Captured data for each channel plus time array

### Power Supply Control

#### `set_voltage(voltage, wait=False)`

Sets the high-voltage power supply output.

**Parameters:**
- `voltage` (float): Output voltage in volts
- `wait` (bool): Wait for voltage to settle if True

**Example:**
```python
# Set voltage and continue immediately
tank.set_voltage(100)

# Set voltage and wait for settling
tank.set_voltage(100, wait=True)
```

### Measurement Methods

#### `get_peak_voltage(x, y, z) -> float`

Measures peak-to-peak voltage at specified coordinates.

**Parameters:**
- `x` (float): X coordinate in mm
- `y` (float): Y coordinate in mm
- `z` (float): Z coordinate in mm

**Returns:**
- `float`: Peak-to-peak voltage in volts

**Example:**
```python
# Single point measurement
voltage = tank.get_peak_voltage(0, 0, 30)
print(f"Peak voltage: {voltage:.3f} V")
```

#### `find_peak_by_gradient_ascent(x_start, y_start, z, step_size=0.5, iterations=10, learning_rate=0.1) -> Tuple[float, float]`

Automatically finds the position of maximum acoustic pressure using gradient ascent optimization.

**Parameters:**
- `x_start` (float): Starting X coordinate in mm
- `y_start` (float): Starting Y coordinate in mm
- `z` (float): Fixed Z coordinate in mm
- `step_size` (float): Step size for gradient estimation (default: 0.5)
- `iterations` (int): Maximum number of iterations (default: 10)
- `learning_rate` (float): Learning rate for position updates (default: 0.1)

**Returns:**
- `Tuple[float, float]`: Optimized (x, y) coordinates in mm

**Example:**
```python
# Find peak starting from approximate center
optimal_x, optimal_y = tank.find_peak_by_gradient_ascent(
    x_start=0, 
    y_start=0, 
    z=30,
    step_size=0.2,
    iterations=15
)
print(f"Peak found at ({optimal_x:.2f}, {optimal_y:.2f}) mm")
```

## Properties

### `lifu`
OpenLIFU interface object for transducer control.

### `scope`
Picoscope object for data acquisition (if `use_picoscope=True`).

### `hv`
QPX600DP power supply object for voltage control.

### `arr`
Array configuration object from OpenLIFU system.

## Coordinate System

The verification tank uses a standard coordinate system:
- **X-axis**: Lateral (left-right when facing transducer)
- **Y-axis**: Elevation (up-down)  
- **Z-axis**: Axial (away from transducer face)
- **Origin**: Typically at transducer geometric center
- **Units**: Millimeters (mm)

## Best Practices

1. **Use context manager**: Always use `with VerificationTank() as tank:` for proper cleanup
2. **Configure before use**: Call `configure_lifu()` before attempting measurements
3. **Set focus before capture**: Always call `set_focus()` before data acquisition
4. **Wait for voltage settling**: Use `wait=True` when changing HVPS voltage significantly
5. **Choose appropriate resolution**: Higher resolution modes provide better SNR but slower sampling
6. **Monitor for safety**: Keep drive voltages within safe limits for your transducer

## Example Applications

### Basic Pressure Measurement

```python
with VerificationTank() as tank:
    # Setup for 1 MHz measurement
    tank.configure_lifu(
        frequency_kHz=1000,
        voltage=50,
        duration_msec=2.0,
        interval_msec=100
    )
    
    # Measure at focus
    tank.set_focus(0, 0, 20)
    data = tank.run_capture()
    
    # Calculate pressure parameters
    voltage_pp = np.max(data['A']) - np.min(data['A'])
    print(f"Peak-to-peak voltage: {voltage_pp:.3f} V")
```

### Frequency Response Measurement

```python
frequencies = [200, 400, 600, 800, 1000]  # kHz
responses = []

with VerificationTank() as tank:
    # Fixed position and voltage
    tank.set_focus(0, 0, 30)
    tank.set_voltage(75, wait=True)
    
    for freq in frequencies:
        # Update frequency
        tank.set_pulse(frequency_kHz=freq, duration_msec=1.0)
        
        # Measure response
        voltage = tank.get_peak_voltage(0, 0, 30)
        responses.append(voltage)
        
        print(f"{freq} kHz: {voltage:.3f} V")
    
    # Analyze frequency response
    max_response = max(responses)
    normalized = [r/max_response for r in responses]
```

### Automated Peak Finding

```python
with VerificationTank() as tank:
    tank.configure_lifu(frequency_kHz=400, voltage=60, duration_msec=1.0, interval_msec=50)
    
    # Coarse search with grid
    x_coarse = np.linspace(-10, 10, 5)
    y_coarse = np.linspace(-10, 10, 5)
    z_fixed = 25
    
    max_voltage = 0
    best_x, best_y = 0, 0
    
    for x in x_coarse:
        for y in y_coarse:
            voltage = tank.get_peak_voltage(x, y, z_fixed)
            if voltage > max_voltage:
                max_voltage = voltage
                best_x, best_y = x, y
    
    print(f"Coarse peak at ({best_x:.1f}, {best_y:.1f}): {max_voltage:.3f} V")
    
    # Fine optimization
    final_x, final_y = tank.find_peak_by_gradient_ascent(
        x_start=best_x,
        y_start=best_y, 
        z=z_fixed,
        step_size=0.1,
        iterations=20
    )
    
    final_voltage = tank.get_peak_voltage(final_x, final_y, z_fixed)
    print(f"Optimized peak at ({final_x:.2f}, {final_y:.2f}): {final_voltage:.3f} V")
```

## Error Handling

The class handles various error conditions gracefully:
- Instrument connection failures
- Invalid coordinate ranges
- Trigger timeout conditions
- Power supply communication errors

Common exceptions include:
- `ConnectionError`: Instrument not found or connection failed
- `ValueError`: Invalid parameter values
- `TimeoutError`: Measurement timeout
- OpenLIFU-specific exceptions for transducer control

## Troubleshooting

### Connection Issues
- Verify all instruments are powered and connected
- Check USB connections and driver installations
- Ensure no other software is using the instruments

### Measurement Issues  
- Verify hydrophone is positioned correctly
- Check signal levels and trigger settings
- Ensure adequate coupling between transducer and medium
- Verify power supply output voltage

### Performance Optimization
- Use appropriate sampling rates for your frequency range
- Choose optimal trigger levels for your signal amplitude
- Consider using higher resolution modes for low-amplitude signals
- Minimize measurement time for automated scans