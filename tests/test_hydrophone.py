"""
Test script for the Hydrophone class.

This script demonstrates how to use the Hydrophone class to:
1. Load calibration data
2. Query sensitivity at specific frequencies
3. Deconvolve voltage signals to get pressure
"""

import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
import sys

# Add the parent directory to the path so we can import openlifu_verification
sys.path.append(str(Path(__file__).parent.parent))

from openlifu_verification import Hydrophone


def test_hydrophone_basic_functionality():
    """Test basic functionality of the Hydrophone class."""
    print("Testing Hydrophone class...")
    
    # Path to the calibration file
    cal_file = Path(__file__).parent.parent / "hydrophone_calibrations" / "HNR0500-2246_xxxxxx-xxxx-xx_xx_20221219 (1).txt"
    
    # Create hydrophone object
    hydrophone = Hydrophone(cal_file)
    
    # Print basic information
    print(f"Hydrophone: {hydrophone}")
    print("\nMetadata summary:")
    metadata = hydrophone.get_metadata_summary()
    for key, value in metadata.items():
        print(f"  {key}: {value}")
    
    # Test sensitivity queries
    print("\nSensitivity tests:")
    test_frequencies = [150e3, 400e3, 1e6, 5e6, 10e6, 15e6]  # 1, 5, 10, 15 MHz
    for freq in test_frequencies:
        sensitivity = hydrophone.get_sensitivity_pa_per_v(freq)
        print(f"  Sensitivity at {freq/1e6:.1f} MHz: {sensitivity:.2e} Pa/V")
    
    # Display calibration data info
    print(f"\nCalibration data shape: {hydrophone.calibration_data.shape}")
    print("Columns:", list(hydrophone.calibration_data.columns))
    print("Frequency range: {:.3f} - {:.3f} MHz".format(
        hydrophone.calibration_data['FREQ_MHz'].min(),
        hydrophone.calibration_data['FREQ_MHz'].max()
    ))


def test_deconvolution():
    """Test the deconvolution functionality."""
    print("\n" + "="*60)
    print("Testing deconvolution functionality...")
    
    # Path to the calibration file
    cal_file = Path(__file__).parent.parent / "hydrophone_calibrations" / "HNR0500-2246_xxxxxx-xxxx-xx_xx_20221219 (1).txt"
    
    # Create hydrophone object
    hydrophone = Hydrophone(cal_file)
    
    # Create a test signal (5 MHz sine wave with some noise)
    fs = 100e6  # 100 MHz sampling rate
    duration = 1e-6  # 1 microsecond
    t = np.linspace(0, duration, int(fs * duration), endpoint=False)
    
    # Create test pressure signal (Pa)
    freq_test = 400e3  # 400 kHz
    pressure_true = 1000 * np.sin(2 * np.pi * freq_test * t)  # 1000 Pa amplitude
    
    # Add some noise
    pressure_true += 10 * np.random.randn(len(t))  # 10 Pa RMS noise
    
    # Convert to voltage using the hydrophone sensitivity
    sensitivity_at_test_freq = hydrophone.get_sensitivity_pa_per_v(freq_test)
    voltage_signal = pressure_true / sensitivity_at_test_freq
    
    # Now deconvolve to recover pressure
    sampling_interval = 1.0 / fs
    pressure_recovered = hydrophone.deconvolve_voltage_signal(voltage_signal, sampling_interval)
    
    # Calculate error
    rms_error = np.sqrt(np.mean((pressure_true - pressure_recovered)**2))
    rms_signal = np.sqrt(np.mean(pressure_true**2))
    relative_error = rms_error / rms_signal * 100
    
    print(f"Test signal frequency: {freq_test/1e6:.1f} MHz")
    print(f"True pressure amplitude: {np.max(np.abs(pressure_true)):.1f} Pa")
    print(f"Sensitivity at test frequency: {sensitivity_at_test_freq:.2e} Pa/V")
    print(f"Voltage signal amplitude: {np.max(np.abs(voltage_signal)):.2e} V")
    print(f"Recovered pressure amplitude: {np.max(np.abs(pressure_recovered)):.1f} Pa")
    print(f"RMS error: {rms_error:.1f} Pa ({relative_error:.2f}%)")
    
    return t, pressure_true, pressure_recovered, voltage_signal


def plot_results():
    """Create plots showing the hydrophone calibration and deconvolution test."""
    print("\n" + "="*60)
    print("Creating plots...")
    
    # Path to the calibration file
    cal_file = Path(__file__).parent.parent / "hydrophone_calibrations" / "HNR0500-2246_xxxxxx-xxxx-xx_xx_20221219 (1).txt"
    
    # Create hydrophone object
    hydrophone = Hydrophone(cal_file)
    
    # Plot calibration data
    fig1 = hydrophone.plot_calibration_data()
    
    # Test deconvolution and plot results
    t, pressure_true, pressure_recovered, voltage_signal = test_deconvolution()
    
    # Create deconvolution comparison plot
    fig2, axes = plt.subplots(3, 1, figsize=(12, 10))
    
    # Plot time signals
    t_us = t * 1e6  # Convert to microseconds
    
    axes[0].plot(t_us, pressure_true, 'b-', label='True pressure', alpha=0.7)
    axes[0].plot(t_us, pressure_recovered, 'r--', label='Recovered pressure', alpha=0.7)
    axes[0].set_xlabel('Time (µs)')
    axes[0].set_ylabel('Pressure (Pa)')
    axes[0].set_title('Deconvolution Test: Pressure Signals')
    axes[0].legend()
    axes[0].grid(True)
    
    axes[1].plot(t_us, voltage_signal, 'g-', alpha=0.7)
    axes[1].set_xlabel('Time (µs)')
    axes[1].set_ylabel('Voltage (V)')
    axes[1].set_title('Measured Voltage Signal')
    axes[1].grid(True)
    
    # Plot error
    error = pressure_true - pressure_recovered
    axes[2].plot(t_us, error, 'k-', alpha=0.7)
    axes[2].set_xlabel('Time (µs)')
    axes[2].set_ylabel('Error (Pa)')
    axes[2].set_title('Deconvolution Error')
    axes[2].grid(True)
    
    plt.tight_layout()
    
    plt.show()


if __name__ == "__main__":
    try:
        # Run basic tests
        test_hydrophone_basic_functionality()
        
        # Run deconvolution test
        test_deconvolution()
        
        # Create plots (optional - requires matplotlib)
        try:
            plot_results()
        except ImportError:
            print("\nMatplotlib not available - skipping plots")
        except Exception as e:
            print(f"\nError creating plots: {e}")
        
        print("\n" + "="*60)
        print("All tests completed successfully!")
        
    except Exception as e:
        print(f"Error during testing: {e}")
        import traceback
        traceback.print_exc()