# Picoscope Class Documentation

The `Picoscope` class provides a high-level Python interface to PicoScope 5000A series oscilloscopes using the PicoSDK library. It simplifies data acquisition by wrapping low-level C API calls into an easy-to-use context manager.

## Overview

This class handles:

1. Device connection and configuration
2. Channel setup with flexible voltage ranges and coupling options
3. Trigger configuration for precise signal capture
4. Block mode data acquisition with configurable sampling parameters
5. Automatic data conversion from ADC counts to voltage values
6. Context management for safe resource handling

## Installation

The class requires the following dependencies:
- `picosdk` - PicoScope SDK Python wrapper
- `numpy` - for numerical operations
- `ctypes` - for low-level SDK interaction

## Usage

### Basic Usage

```python
from openlifu_verification import Picoscope

# Use as context manager for automatic resource management
with Picoscope(resolution="12BIT") as scope:
    # Configure channels
    scope.set_channel('A', range_mv=100, coupling='DC')
    scope.set_channel('B', range_mv=5000, coupling='DC')
    
    # Set up trigger
    scope.set_trigger(channel='B', threshold_mv=500, direction='rising')
    
    # Capture data
    data = scope.capture_data(pre_trigger=2500, post_trigger=10000, timebase=8)
    
    print(f"Channel A voltage: {data['A']}")
    print(f"Channel B voltage: {data['B']}")
    print(f"Time array: {data['time']}")
```

### Advanced Configuration

```python
with Picoscope(resolution="15BIT") as scope:
    # Configure multiple channels with different settings
    scope.set_channel('A', range_mv=50, coupling='AC', offset_v=0.1)
    scope.set_channel('B', range_mv=2000, coupling='DC')
    scope.set_channel('C', enabled=False)  # Disable unused channel
    
    # Advanced trigger setup
    scope.set_trigger(
        channel='A', 
        threshold_mv=25, 
        direction='falling',
        delay_samples=100,
        auto_trigger_ms=3000
    )
    
    # Check timebase capabilities
    interval_ns, max_samples = scope.get_timebase_info(timebase=6, max_samples=50000)
    print(f"Sampling interval: {interval_ns} ns")
    
    # Manual capture sequence
    scope.run_block(pre_trigger_samples=5000, post_trigger_samples=20000, timebase=6)
    scope.wait_ready()
    data = scope.get_data(max_samples=25000, timebase=6)
```

## Class Reference

### Constructor

#### `Picoscope(resolution: str = "12BIT")`

Creates a new Picoscope instance.

**Parameters:**
- `resolution` (str): ADC resolution, either "12BIT", "14BIT", "15BIT", or "16BIT"

**Raises:**
- `ValueError`: If resolution is not supported

### Context Management

#### `__enter__() -> Picoscope`

Opens connection to the PicoScope device. Called automatically when using `with` statement.

**Returns:**
- `Picoscope`: Self reference for chaining

**Raises:**
- `PicoscopeError`: If device connection fails

#### `__exit__(exc_type, exc_val, exc_tb)`

Closes connection and cleans up resources. Called automatically when exiting `with` statement.

### Channel Configuration

#### `set_channel(channel, enabled=True, range_mv=1000, coupling='DC', offset_v=0.0)`

Configures an input channel.

**Parameters:**
- `channel` (str): Channel identifier ('A', 'B', 'C', 'D')
- `enabled` (bool): Enable/disable the channel (default: True)
- `range_mv` (int): Input voltage range in millivolts. Available ranges: 10, 20, 50, 100, 200, 500, 1000, 2000, 5000, 10000, 20000, 50000
- `coupling` (str): Input coupling, either 'AC' or 'DC' (default: 'DC')
- `offset_v` (float): Analog offset voltage in volts (default: 0.0)

**Raises:**
- `PicoscopeError`: If channel configuration fails
- `ValueError`: If channel or parameters are invalid

### Trigger Configuration

#### `set_trigger(channel, threshold_mv, direction='rising', delay_samples=0, auto_trigger_ms=5000)`

Configures a simple edge trigger.

**Parameters:**
- `channel` (str): Trigger source channel ('A', 'B', 'C', 'D')
- `threshold_mv` (float): Trigger threshold in millivolts
- `direction` (str): Trigger edge direction ('rising', 'falling', 'gate_high', 'gate_low')
- `delay_samples` (int): Trigger delay in sample periods (default: 0)
- `auto_trigger_ms` (int): Auto-trigger timeout in milliseconds (default: 5000)

**Raises:**
- `PicoscopeError`: If trigger configuration fails
- `ValueError`: If channel or direction is invalid

### Data Acquisition

#### `capture_data(pre_trigger_samples=2500, post_trigger_samples=10000, timebase=8) -> Dict[str, np.ndarray]`

Convenience method for complete data capture sequence.

**Parameters:**
- `pre_trigger_samples` (int): Number of samples before trigger event
- `post_trigger_samples` (int): Number of samples after trigger event
- `timebase` (int): Timebase index determining sampling rate

**Returns:**
- `Dict[str, np.ndarray]`: Dictionary with keys for each enabled channel ('A', 'B', etc.) plus 'time'

**Raises:**
- `PicoscopeError`: If capture sequence fails

#### `run_block(pre_trigger_samples, post_trigger_samples, timebase=8)`

Starts block mode data acquisition.

**Parameters:**
- `pre_trigger_samples` (int): Number of samples before trigger
- `post_trigger_samples` (int): Number of samples after trigger
- `timebase` (int): Timebase index (default: 8)

#### `wait_ready() -> bool`

Waits for data acquisition to complete.

**Returns:**
- `bool`: True if acquisition completed successfully

#### `get_data(max_samples, timebase) -> Dict[str, np.ndarray]`

Retrieves captured data from the device.

**Parameters:**
- `max_samples` (int): Maximum number of samples to retrieve
- `timebase` (int): Timebase used for acquisition

**Returns:**
- `Dict[str, np.ndarray]`: Voltage data for each channel plus time array

### Utility Methods

#### `get_timebase_info(timebase, max_samples) -> Tuple[float, int]`

Gets timing information for a given timebase.

**Parameters:**
- `timebase` (int): Timebase index to query
- `max_samples` (int): Maximum samples for the query

**Returns:**
- `Tuple[float, int]`: (sampling_interval_ns, max_samples_available)

#### `stop()`

Stops any running data acquisition.

## Utility Functions

### `timebase_to_sampling_interval(timebase: int, resolution: int) -> float`

Converts timebase index to sampling interval.

**Parameters:**
- `timebase` (int): Timebase index
- `resolution` (int): ADC resolution bits

**Returns:**
- `float`: Sampling interval in nanoseconds

### `sampling_interval_to_timebase(sampling_interval_ns: float, resolution: int) -> int`

Converts sampling interval to nearest valid timebase.

**Parameters:**
- `sampling_interval_ns` (float): Desired sampling interval in nanoseconds
- `resolution` (int): ADC resolution bits

**Returns:**
- `int`: Nearest valid timebase index

## Error Handling

### `PicoscopeError`

Custom exception class for Picoscope-related errors. Inherits from `Exception`.

**Common Causes:**
- Device not connected or already in use
- Invalid channel or parameter values
- Hardware communication failures
- Insufficient memory for requested sample count

## Available Voltage Ranges

The following voltage ranges are supported (in mV):
- 10, 20, 50, 100, 200, 500
- 1000 (1V), 2000 (2V), 5000 (5V)
- 10000 (10V), 20000 (20V), 50000 (50V)

## Sampling Rates and Timebases

Sampling rates depend on the selected timebase and resolution:
- Higher timebase values = lower sampling rates
- Higher resolution modes may limit maximum sampling rates
- Use `get_timebase_info()` to check capabilities before acquisition

## Best Practices

1. Always use the context manager (`with` statement) for automatic cleanup
2. Configure all channels before setting triggers
3. Choose appropriate voltage ranges to maximize resolution
4. Use AC coupling for signals with DC offsets you want to remove
5. Set trigger thresholds well above noise levels
6. Check timebase capabilities before long acquisitions
7. Handle `PicoscopeError` exceptions for robust applications

## Example Applications

### High-Speed Pulse Measurement

```python
with Picoscope(resolution="15BIT") as scope:
    # Configure for high-speed, high-resolution capture
    scope.set_channel('A', range_mv=100, coupling='DC')
    scope.set_trigger(channel='A', threshold_mv=50, direction='rising')
    
    # Fast sampling (timebase 0 = fastest)
    data = scope.capture_data(pre_trigger=1000, post_trigger=5000, timebase=0)
    
    # Analyze pulse characteristics
    pulse_amplitude = np.max(data['A']) - np.min(data['A'])
    print(f"Pulse amplitude: {pulse_amplitude:.3f} V")
```

### Dual-Channel Differential Measurement

```python
with Picoscope() as scope:
    # Configure channels for differential measurement
    scope.set_channel('A', range_mv=200, coupling='AC')
    scope.set_channel('B', range_mv=200, coupling='AC')
    scope.set_trigger(channel='A', threshold_mv=10, direction='rising')
    
    data = scope.capture_data(pre_trigger=2500, post_trigger=7500, timebase=10)
    
    # Calculate differential signal
    differential = data['A'] - data['B']
    print(f"Differential signal range: {np.ptp(differential):.3f} V")
```