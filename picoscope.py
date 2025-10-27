"""
Picoscope wrapper class for simplified data acquisition.

This module provides a clean, Pythonic interface to the PicoScope 5000A series
oscilloscopes using the picosdk library. It wraps the low-level C API calls
into an easy-to-use context manager.

Example usage:
    with Picoscope() as scope:
        scope.set_channel('A', range_mv=100, coupling='DC')
        scope.set_channel('B', range_mv=5000, coupling='DC')
        scope.set_trigger(channel='B', threshold_mv=500, direction='rising')
        data = scope.capture_data(pre_trigger=2500, post_trigger=10000, timebase=8)
        print(f"Channel A: {data['A']}")
        print(f"Channel B: {data['B']}")
        print(f"Time: {data['time']}")
"""

import ctypes
import logging
from typing import Dict, Optional, Tuple, Union, Literal
import numpy as np

from picosdk.functions import adc2mV, assert_pico_ok, mV2adc
from picosdk.ps5000a import ps5000a as ps

logger = logging.getLogger(__name__)


class PicoscopeError(Exception):
    """Custom exception for Picoscope-related errors."""
    pass


class Picoscope:
    """
    A context manager wrapper for PicoScope 5000A series oscilloscopes.
    
    This class provides a high-level interface to the PicoScope, handling
    initialization, configuration, data acquisition, and cleanup automatically.
    """
    
    # Define available ranges in mV for easy reference
    RANGES_MV = {
        10: ps.PS5000A_RANGE["PS5000A_10MV"],
        20: ps.PS5000A_RANGE["PS5000A_20MV"],
        50: ps.PS5000A_RANGE["PS5000A_50MV"],
        100: ps.PS5000A_RANGE["PS5000A_100MV"],
        200: ps.PS5000A_RANGE["PS5000A_200MV"],
        500: ps.PS5000A_RANGE["PS5000A_500MV"],
        1000: ps.PS5000A_RANGE["PS5000A_1V"],
        2000: ps.PS5000A_RANGE["PS5000A_2V"],
        5000: ps.PS5000A_RANGE["PS5000A_5V"],
        10000: ps.PS5000A_RANGE["PS5000A_10V"],
        20000: ps.PS5000A_RANGE["PS5000A_20V"],
        50000: ps.PS5000A_RANGE["PS5000A_50V"],
    }
    
    CHANNELS = {
        'A': ps.PS5000A_CHANNEL["PS5000A_CHANNEL_A"],
        'B': ps.PS5000A_CHANNEL["PS5000A_CHANNEL_B"],
        'C': ps.PS5000A_CHANNEL["PS5000A_CHANNEL_C"],
        'D': ps.PS5000A_CHANNEL["PS5000A_CHANNEL_D"],
    }
    
    COUPLING = {
        'AC': ps.PS5000A_COUPLING["PS5000A_AC"],
        'DC': ps.PS5000A_COUPLING["PS5000A_DC"],
    }
    
    TRIGGER_DIRECTIONS = {
        'rising': 2,  # PS5000A_RISING
        'falling': 3,  # PS5000A_FALLING
        'gate_high': 0,  # PS5000A_GATE_HIGH
        'gate_low': 1,  # PS5000A_GATE_LOW
    }
    
    def __init__(self, resolution: str = "12BIT"):
        """
        Initialize the Picoscope wrapper.
        
        Args:
            resolution: Device resolution ("8BIT", "12BIT", "14BIT", "15BIT", "16BIT")
        """
        self.chandle = ctypes.c_int16()
        self.status = {}
        self.max_adc = ctypes.c_int16()
        self.channel_ranges = {}  # Store configured channel ranges
        self.enabled_channels = set()
        self._is_open = False
        
        # Resolution mapping
        resolution_map = {
            "8BIT": ps.PS5000A_DEVICE_RESOLUTION["PS5000A_DR_8BIT"],
            "12BIT": ps.PS5000A_DEVICE_RESOLUTION["PS5000A_DR_12BIT"],
            "14BIT": ps.PS5000A_DEVICE_RESOLUTION["PS5000A_DR_14BIT"],
            "15BIT": ps.PS5000A_DEVICE_RESOLUTION["PS5000A_DR_15BIT"],
            "16BIT": ps.PS5000A_DEVICE_RESOLUTION["PS5000A_DR_16BIT"],
        }
        
        if resolution not in resolution_map:
            raise ValueError(f"Invalid resolution: {resolution}. Must be one of {list(resolution_map.keys())}")
        
        self.resolution = resolution_map[resolution]
        
    def __enter__(self):
        """Context manager entry."""
        self.open_unit()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit with cleanup."""
        self.close_unit()
        
    def open_unit(self):
        """
        Open connection to the PicoScope device.
        
        Raises:
            PicoscopeError: If the device cannot be opened or power issues occur.
        """
        if self._is_open:
            logger.warning("Device already open")
            return
            
        try:
            self.status["openunit"] = ps.ps5000aOpenUnit(
                ctypes.byref(self.chandle), None, self.resolution
            )
            assert_pico_ok(self.status["openunit"])
            
        except Exception as e:
            # Handle power source issues
            power_status = self.status["openunit"]
            if power_status in [286, 282]:  # Power supply issues
                logger.info("Attempting to change power source...")
                self.status["changePowerSource"] = ps.ps5000aChangePowerSource(
                    self.chandle, power_status
                )
                try:
                    assert_pico_ok(self.status["changePowerSource"])
                except Exception as power_error:
                    raise PicoscopeError(f"Failed to change power source: {power_error}")
            else:
                raise PicoscopeError(f"Failed to open PicoScope: {e}")
        
        # Get maximum ADC value
        self.status["maximumValue"] = ps.ps5000aMaximumValue(
            self.chandle, ctypes.byref(self.max_adc)
        )
        assert_pico_ok(self.status["maximumValue"])
        
        self._is_open = True
        logger.info(f"PicoScope opened successfully (handle: {self.chandle.value})")
        
    def close_unit(self):
        """
        Close connection to the PicoScope device.
        """
        if not self._is_open:
            return
            
        try:
            # Stop any running acquisition
            self.status["stop"] = ps.ps5000aStop(self.chandle)
            assert_pico_ok(self.status["stop"])
            
            # Close the unit
            self.status["close"] = ps.ps5000aCloseUnit(self.chandle)
            assert_pico_ok(self.status["close"])
            
            self._is_open = False
            logger.info("PicoScope closed successfully")
            
        except Exception as e:
            logger.error(f"Error closing PicoScope: {e}")
            
    def set_channel(self, 
                   channel: Literal['A', 'B', 'C', 'D'], 
                   enabled: bool = True,
                   range_mv: int = 1000, 
                   coupling: Literal['AC', 'DC'] = 'DC',
                   offset_v: float = 0.0):
        """
        Configure a channel on the PicoScope.
        
        Args:
            channel: Channel to configure ('A', 'B', 'C', 'D')
            enabled: Whether to enable the channel
            range_mv: Input range in millivolts (10, 20, 50, 100, 200, 500, 1000, 2000, 5000, 10000, 20000, 50000)
            coupling: Input coupling ('AC' or 'DC')
            offset_v: Analog offset in volts
            
        Raises:
            PicoscopeError: If channel configuration fails
        """
        if not self._is_open:
            raise PicoscopeError("Device not open. Use within a context manager or call open_unit() first.")
            
        if channel not in self.CHANNELS:
            raise ValueError(f"Invalid channel: {channel}. Must be one of {list(self.CHANNELS.keys())}")
            
        if range_mv not in self.RANGES_MV:
            raise ValueError(f"Invalid range: {range_mv}mV. Must be one of {list(self.RANGES_MV.keys())}")
            
        if coupling not in self.COUPLING:
            raise ValueError(f"Invalid coupling: {coupling}. Must be one of {list(self.COUPLING.keys())}")
        
        channel_enum = self.CHANNELS[channel]
        range_enum = self.RANGES_MV[range_mv]
        coupling_enum = self.COUPLING[coupling]
        
        try:
            self.status[f"setCh{channel}"] = ps.ps5000aSetChannel(
                self.chandle, 
                channel_enum, 
                int(enabled), 
                coupling_enum, 
                range_enum, 
                offset_v
            )
            assert_pico_ok(self.status[f"setCh{channel}"])
            
            if enabled:
                self.enabled_channels.add(channel)
                self.channel_ranges[channel] = range_enum
            else:
                self.enabled_channels.discard(channel)
                self.channel_ranges.pop(channel, None)
                
            logger.info(f"Channel {channel} configured: {range_mv}mV, {coupling}, enabled={enabled}")
            
        except Exception as e:
            raise PicoscopeError(f"Failed to configure channel {channel}: {e}")
            
    def set_trigger(self, 
                   channel: Literal['A', 'B', 'C', 'D'],
                   threshold_mv: float,
                   direction: Literal['rising', 'falling', 'gate_high', 'gate_low'] = 'rising',
                   delay_samples: int = 0,
                   auto_trigger_ms: int = 5000):
        """
        Configure a simple trigger.
        
        Args:
            channel: Trigger channel ('A', 'B', 'C', 'D')
            threshold_mv: Trigger threshold in millivolts
            direction: Trigger direction ('rising', 'falling', 'gate_high', 'gate_low')
            delay_samples: Trigger delay in sample periods
            auto_trigger_ms: Auto trigger timeout in milliseconds
            
        Raises:
            PicoscopeError: If trigger configuration fails
        """
        if not self._is_open:
            raise PicoscopeError("Device not open. Use within a context manager or call open_unit() first.")
            
        if channel not in self.CHANNELS:
            raise ValueError(f"Invalid channel: {channel}. Must be one of {list(self.CHANNELS.keys())}")
            
        if channel not in self.channel_ranges:
            raise PicoscopeError(f"Channel {channel} must be configured before setting trigger")
            
        if direction not in self.TRIGGER_DIRECTIONS:
            raise ValueError(f"Invalid direction: {direction}. Must be one of {list(self.TRIGGER_DIRECTIONS.keys())}")
        
        channel_enum = self.CHANNELS[channel]
        direction_enum = self.TRIGGER_DIRECTIONS[direction]
        channel_range = self.channel_ranges[channel]
        
        # Convert threshold from mV to ADC counts
        threshold_adc = int(mV2adc(threshold_mv, channel_range, self.max_adc))
        
        try:
            self.status["trigger"] = ps.ps5000aSetSimpleTrigger(
                self.chandle,
                1,  # enabled
                channel_enum,
                threshold_adc,
                direction_enum,
                delay_samples,
                auto_trigger_ms
            )
            assert_pico_ok(self.status["trigger"])
            
            logger.info(f"Trigger configured: Channel {channel}, {threshold_mv}mV, {direction}")
            
        except Exception as e:
            raise PicoscopeError(f"Failed to configure trigger: {e}")
            
    def get_timebase_info(self, timebase: int, max_samples: int) -> Tuple[float, int]:
        """
        Get timebase information.
        
        Args:
            timebase: Timebase index
            max_samples: Maximum number of samples
            
        Returns:
            Tuple of (time_interval_ns, max_samples_available)
            
        Raises:
            PicoscopeError: If timebase query fails
        """
        if not self._is_open:
            raise PicoscopeError("Device not open. Use within a context manager or call open_unit() first.")
            
        time_interval_ns = ctypes.c_float()
        returned_max_samples = ctypes.c_int32()
        
        try:
            self.status["getTimebase2"] = ps.ps5000aGetTimebase2(
                self.chandle,
                timebase,
                max_samples,
                ctypes.byref(time_interval_ns),
                ctypes.byref(returned_max_samples),
                0  # segment index
            )
            assert_pico_ok(self.status["getTimebase2"])
            
            return time_interval_ns.value, returned_max_samples.value
            
        except Exception as e:
            raise PicoscopeError(f"Failed to get timebase info: {e}")
            
    def run_block(self, 
                 pre_trigger_samples: int, 
                 post_trigger_samples: int, 
                 timebase: int = 8):
        """
        Start block mode data capture.
        
        Args:
            pre_trigger_samples: Number of samples before trigger
            post_trigger_samples: Number of samples after trigger
            timebase: Timebase index (determines sampling rate)
            
        Raises:
            PicoscopeError: If block capture fails to start
        """
        if not self._is_open:
            raise PicoscopeError("Device not open. Use within a context manager or call open_unit() first.")
            
        try:
            self.status["runBlock"] = ps.ps5000aRunBlock(
                self.chandle,
                pre_trigger_samples,
                post_trigger_samples,
                timebase,
                None,  # time indisposed
                0,     # segment index
                None,  # lpReady callback
                None   # pParameter
            )
            assert_pico_ok(self.status["runBlock"])
            
            logger.info(f"Block capture started: {pre_trigger_samples + post_trigger_samples} samples")
            
        except Exception as e:
            raise PicoscopeError(f"Failed to start block capture: {e}")
            
    def wait_ready(self) -> bool:
        """
        Wait for data capture to complete.
        
        Returns:
            True when ready
            
        Raises:
            PicoscopeError: If ready check fails
        """
        if not self._is_open:
            raise PicoscopeError("Device not open. Use within a context manager or call open_unit() first.")
            
        ready = ctypes.c_int16(0)
        check = ctypes.c_int16(0)
        
        try:
            while ready.value == check.value:
                self.status["isReady"] = ps.ps5000aIsReady(self.chandle, ctypes.byref(ready))
                assert_pico_ok(self.status["isReady"])
                
            logger.info("Data capture completed")
            return True
            
        except Exception as e:
            raise PicoscopeError(f"Error waiting for ready: {e}")
            
    def get_data(self, max_samples: int, timebase: int) -> Dict[str, np.ndarray]:
        """
        Retrieve captured data from all enabled channels.
        
        Args:
            max_samples: Maximum number of samples to retrieve
            timebase: Timebase used for capture (for time array generation)
            
        Returns:
            Dictionary containing data arrays for each enabled channel plus time array
            Keys: 'A', 'B', 'C', 'D' (for enabled channels), 'time'
            
        Raises:
            PicoscopeError: If data retrieval fails
        """
        if not self._is_open:
            raise PicoscopeError("Device not open. Use within a context manager or call open_unit() first.")
            
        if not self.enabled_channels:
            raise PicoscopeError("No channels enabled for data capture")
            
        # Create buffers and set data buffer locations
        buffers = {}
        
        for channel in self.enabled_channels:
            channel_enum = self.CHANNELS[channel]
            
            # Create max and min buffers (min not used in this example)
            buffer_max = (ctypes.c_int16 * max_samples)()
            buffer_min = (ctypes.c_int16 * max_samples)()
            
            # Set data buffer location
            try:
                self.status[f"setDataBuffers{channel}"] = ps.ps5000aSetDataBuffers(
                    self.chandle,
                    channel_enum,
                    ctypes.byref(buffer_max),
                    ctypes.byref(buffer_min),
                    max_samples,
                    0,  # segment index
                    0   # ratio mode (no downsampling)
                )
                assert_pico_ok(self.status[f"setDataBuffers{channel}"])
                
                buffers[channel] = {
                    'max': buffer_max,
                    'min': buffer_min,
                    'range': self.channel_ranges[channel]
                }
                
            except Exception as e:
                raise PicoscopeError(f"Failed to set data buffer for channel {channel}: {e}")
        
        # Retrieve data
        overflow = ctypes.c_int16()
        c_max_samples = ctypes.c_int32(max_samples)
        
        try:
            self.status["getValues"] = ps.ps5000aGetValues(
                self.chandle,
                0,  # start index
                ctypes.byref(c_max_samples),
                0,  # downsample ratio
                0,  # downsample ratio mode
                0,  # segment index
                ctypes.byref(overflow)
            )
            assert_pico_ok(self.status["getValues"])
            
        except Exception as e:
            raise PicoscopeError(f"Failed to retrieve data: {e}")
        
        # Convert ADC counts to mV and create result dictionary
        result = {}
        
        for channel in self.enabled_channels:
            buffer_data = buffers[channel]
            adc_data = buffer_data['max']
            channel_range = buffer_data['range']
            
            # Convert to mV
            mv_data = adc2mV(adc_data, channel_range, self.max_adc)
            result[channel] = np.array(mv_data)
        
        # Create time array
        time_interval_ns, _ = self.get_timebase_info(timebase, max_samples)
        time_array = np.linspace(0, (c_max_samples.value - 1) * time_interval_ns, c_max_samples.value)
        result['time'] = time_array
        
        logger.info(f"Retrieved {c_max_samples.value} samples from {len(self.enabled_channels)} channels")
        
        return result
        
    def capture_data(self, 
                    pre_trigger_samples: int = 2500,
                    post_trigger_samples: int = 10000,
                    timebase: int = 8) -> Dict[str, np.ndarray]:
        """
        Convenience method to run a complete data capture sequence.
        
        Args:
            pre_trigger_samples: Number of samples before trigger
            post_trigger_samples: Number of samples after trigger  
            timebase: Timebase index (determines sampling rate)
            
        Returns:
            Dictionary containing data arrays for each enabled channel plus time array
            
        Raises:
            PicoscopeError: If capture sequence fails
        """
        max_samples = pre_trigger_samples + post_trigger_samples
        
        # Start capture
        self.run_block(pre_trigger_samples, post_trigger_samples, timebase)
        
        # Wait for completion
        self.wait_ready()
        
        # Retrieve data
        return self.get_data(max_samples, timebase)
        
    def stop(self):
        """
        Stop any running data capture.
        
        Raises:
            PicoscopeError: If stop operation fails
        """
        if not self._is_open:
            return
            
        try:
            self.status["stop"] = ps.ps5000aStop(self.chandle)
            assert_pico_ok(self.status["stop"])
            logger.info("Data capture stopped")
            
        except Exception as e:
            raise PicoscopeError(f"Failed to stop capture: {e}")