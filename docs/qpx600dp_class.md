# QPX600DP Class Documentation

The `QPX600DP` class provides a Python interface to control an AIM TTi QPX600DP dual-channel power supply over serial communication. This class offers a clean, pythonic API for voltage control, current limiting, and monitoring.

## Overview

This class handles:

1. Automatic device discovery via USB VID/PID
2. Serial communication with command/query functionality
3. Dual-channel voltage and current control
4. Output enable/disable control
5. Protection settings (over-voltage, over-current)
6. Real-time monitoring of output parameters
7. Context management for safe resource handling

## Installation

The class requires the following dependencies:
- `pyserial` - for serial communication
- `time` - for timing operations (standard library)

## Usage

### Basic Usage

```python
from openlifu_verification import QPX600DP

# Use as context manager for automatic connection management
with QPX600DP() as psu:
    # Set voltage on both channels
    psu.set_voltage(12.0, output='both')
    
    # Enable outputs
    psu.set_all_outputs(True)
    
    # Wait for voltage to settle
    psu.wait_ready(target=12.0, timeout=2.0)
    
    # Monitor output
    v1 = psu.get_output_voltage(1)
    i1 = psu.get_output_current(1)
    print(f"Channel 1: {v1:.3f}V, {i1:.3f}A")
```

### Advanced Configuration

```python
with QPX600DP(port='COM3') as psu:  # Specify port manually
    # Configure each channel individually
    psu.set_voltage(5.0, output=1)
    psu.set_voltage(15.0, output=2)
    
    # Set current limits
    psu.set_current_limit(1, 2.0)  # 2A limit on channel 1
    psu.set_current_limit(2, 1.0)  # 1A limit on channel 2
    
    # Set protection levels
    psu.set_over_voltage_protection(1, 5.5)
    psu.set_over_voltage_protection(2, 16.0)
    
    # Enable channels individually
    psu.set_output(1, True)
    psu.set_output(2, True)
    
    # Verify settings
    for channel in [1, 2]:
        set_v = psu.get_set_voltage(channel)
        actual_v = psu.get_output_voltage(channel)
        current = psu.get_output_current(channel)
        print(f"Ch{channel}: Set={set_v:.2f}V, Actual={actual_v:.2f}V, Current={current:.3f}A")
```

## Class Reference

### Constructor

#### `QPX600DP(port='auto')`

Creates a new QPX600DP instance.

**Parameters:**
- `port` (str): Serial port to connect to. Use 'auto' for automatic discovery via VID/PID (default: 'auto')

**Raises:**
- `ConnectionError`: If device cannot be found (when port='auto')

### Context Management

#### `__enter__() -> QPX600DP`

Establishes serial connection to the power supply. Called automatically when using `with` statement.

**Returns:**
- `QPX600DP`: Self reference for chaining

#### `__exit__(exc_type, exc_value, traceback)`

Closes serial connection and cleans up resources. Called automatically when exiting `with` statement.

### Connection Management

#### `connect()`

Establishes serial connection to the device.

#### `disconnect()`

Closes the serial connection.

### Voltage Control

#### `set_voltage(voltage, *, output='both')`

Sets the output voltage for specified channel(s).

**Parameters:**
- `voltage` (float): Desired voltage in volts
- `output` (int or str): Channel number (1, 2) or 'both' for both channels

**Example:**
```python
psu.set_voltage(5.0, output=1)      # Set channel 1 to 5V
psu.set_voltage(12.0, output='both') # Set both channels to 12V
```

#### `get_set_voltage(output) -> float`

Gets the programmed voltage setting for a channel.

**Parameters:**
- `output` (int): Channel number (1 or 2)

**Returns:**
- `float`: Set voltage in volts

#### `get_output_voltage(output) -> float`

Gets the actual output voltage for a channel.

**Parameters:**
- `output` (int): Channel number (1 or 2)

**Returns:**
- `float`: Actual output voltage in volts

#### `wait_ready(target=None, *, output='both', timeout=1.0, thresh=0.02, poll_interval=0.001) -> bool`

Waits for output voltage to settle to target value.

**Parameters:**
- `target` (float, optional): Target voltage. Uses set voltage if None
- `output` (int or str): Channel(s) to monitor
- `timeout` (float): Maximum wait time in seconds
- `thresh` (float): Relative error threshold (default: 2%)
- `poll_interval` (float): Polling interval in seconds

**Returns:**
- `bool`: True if voltage settled within threshold, False if timeout

### Current Control and Monitoring

#### `set_current_limit(output, current)`

Sets the current limit for a channel.

**Parameters:**
- `output` (int): Channel number (1 or 2)
- `current` (float): Current limit in amperes

#### `get_set_current_limit(output) -> float`

Gets the programmed current limit for a channel.

**Parameters:**
- `output` (int): Channel number (1 or 2)

**Returns:**
- `float`: Current limit in amperes

#### `get_output_current(output) -> float`

Gets the actual output current for a channel.

**Parameters:**
- `output` (int): Channel number (1 or 2)

**Returns:**
- `float`: Output current in amperes

### Output Control

#### `set_output(output, state)`

Controls the output enable state for a single channel.

**Parameters:**
- `output` (int): Channel number (1 or 2)
- `state` (bool): True to enable, False to disable

#### `get_output_state(output) -> bool`

Gets the output enable state for a channel.

**Parameters:**
- `output` (int): Channel number (1 or 2)

**Returns:**
- `bool`: True if output enabled, False if disabled

#### `set_all_outputs(state)`

Controls the output enable state for both channels simultaneously.

**Parameters:**
- `state` (bool): True to enable all outputs, False to disable all

### Protection Settings

#### `set_over_voltage_protection(output, voltage)`

Sets the over-voltage protection trip point.

**Parameters:**
- `output` (int): Channel number (1 or 2)
- `voltage` (float): Trip voltage in volts

#### `get_over_voltage_protection(output) -> float`

Gets the over-voltage protection setting.

**Parameters:**
- `output` (int): Channel number (1 or 2)

**Returns:**
- `float`: Over-voltage protection trip point in volts

#### `set_over_current_protection(output, current)`

Sets the over-current protection trip point.

**Parameters:**
- `output` (int): Channel number (1 or 2)
- `current` (float): Trip current in amperes

#### `get_over_current_protection(output) -> float`

Gets the over-current protection setting.

**Parameters:**
- `output` (int): Channel number (1 or 2)

**Returns:**
- `float`: Over-current protection trip point in amperes

### Configuration

#### `set_sense_mode(output, remote)`

Sets the voltage sensing mode (local or remote).

**Parameters:**
- `output` (int): Channel number (1 or 2)
- `remote` (bool): True for remote sensing, False for local

#### `set_config(mode)`

Sets the operating configuration mode.

**Parameters:**
- `mode` (int): Operating mode (0, 2, 3, or 4)
  - 0: Independent dual output
  - 2: Series connection
  - 3: Parallel connection
  - 4: Tracking (channels track each other)

#### `get_config() -> int`

Gets the current operating configuration mode.

**Returns:**
- `int`: Current operating mode

### System Commands

#### `clear_status()`

Clears all status registers.

#### `reset()`

Resets the instrument to factory default settings.

#### `get_id() -> str`

Gets the instrument identification string.

**Returns:**
- `str`: Device identification information

### Private Methods

#### `_find_device() -> str`

Automatically finds the first QPX600DP device by scanning serial ports for matching VID/PID.

**Returns:**
- `str`: COM port name, or None if not found

#### `_send_command(command)`

Sends a command to the device without expecting a response.

#### `_query(query) -> str`

Sends a query to the device and returns the response.

## Device Specifications

### QPX600DP Technical Details

- **VID/PID**: 0x103E/0x0456
- **Communication**: Serial over USB
- **Channels**: 2 independent outputs
- **Voltage Range**: 0-60V per channel
- **Current Range**: 0-10A per channel
- **Total Power**: 360W max

## Error Handling

The class handles communication errors gracefully and will raise appropriate exceptions for:
- Connection failures
- Invalid parameter values
- Communication timeouts
- Device not found errors

## Best Practices

1. **Always use context manager**: Use `with QPX600DP() as psu:` for automatic cleanup
2. **Set current limits**: Always configure appropriate current limits before enabling outputs
3. **Use protection settings**: Configure over-voltage/over-current protection for safety
4. **Wait for settling**: Use `wait_ready()` after voltage changes for stable operation
5. **Monitor outputs**: Regularly check actual voltage/current vs. set values
6. **Gradual voltage changes**: For large voltage changes, consider ramping gradually

## Example Applications

### Precision Power Control

```python
with QPX600DP() as psu:
    # Configure for precision operation
    psu.set_voltage(5.000, output=1)
    psu.set_current_limit(1, 0.5)
    psu.set_over_voltage_protection(1, 5.5)
    
    psu.set_output(1, True)
    
    # Wait for precise settling
    if psu.wait_ready(target=5.000, thresh=0.001, timeout=5.0):
        actual = psu.get_output_voltage(1)
        print(f"Voltage settled to: {actual:.4f}V")
    else:
        print("Warning: Voltage did not settle within tolerance")
```

### Dual Supply Configuration

```python
with QPX600DP() as psu:
    # Configure asymmetric dual supply
    psu.set_voltage(15.0, output=1)   # Positive rail
    psu.set_voltage(-15.0, output=2)  # Negative rail
    
    # Set conservative current limits
    psu.set_current_limit(1, 1.0)
    psu.set_current_limit(2, 1.0)
    
    # Enable both outputs
    psu.set_all_outputs(True)
    
    # Monitor both rails
    v_pos = psu.get_output_voltage(1)
    v_neg = psu.get_output_voltage(2)
    print(f"Dual supply: +{v_pos:.2f}V / {v_neg:.2f}V")
```

### Automated Testing

```python
import time

def voltage_sweep_test():
    with QPX600DP() as psu:
        psu.set_current_limit(1, 0.1)  # Conservative limit
        psu.set_output(1, True)
        
        voltages = [1.0, 2.0, 3.0, 5.0, 10.0]
        measurements = []
        
        for target_v in voltages:
            psu.set_voltage(target_v, output=1)
            psu.wait_ready(target=target_v, timeout=2.0)
            
            actual_v = psu.get_output_voltage(1)
            current = psu.get_output_current(1)
            
            measurements.append({
                'target': target_v,
                'actual': actual_v,
                'current': current,
                'error_pct': abs(actual_v - target_v) / target_v * 100
            })
            
            time.sleep(0.1)  # Brief settling time
        
        return measurements
```

## Troubleshooting

### Common Issues

1. **Device not found**: Check USB connection and ensure QPX600DP drivers are installed
2. **Permission errors**: On Linux/macOS, ensure user has permission to access serial ports
3. **Communication timeout**: Check cable connection and verify device is responding
4. **Voltage not settling**: Check load conditions and current limit settings
5. **Protection triggering**: Verify over-voltage/current protection settings are appropriate

### Debug Tips

- Use `get_id()` to verify communication is working
- Check `get_output_state()` to confirm outputs are enabled
- Monitor actual vs. set values to identify regulation issues
- Use conservative timeout values when first testing