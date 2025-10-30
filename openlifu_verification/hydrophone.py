"""
Hydrophone calibration data handling for OpenLIFU verification.

This module provides the Hydrophone class for reading hydrophone calibration
files and performing frequency-dependent sensitivity corrections.
"""

import numpy as np
import pandas as pd
from pathlib import Path
from typing import Union, Dict, Any, Tuple
from scipy import signal
from scipy.interpolate import interp1d


class Hydrophone:
    """
    A class for handling hydrophone calibration data and performing 
    frequency-dependent deconvolution.
    
    Attributes:
        metadata (dict): Dictionary containing all calibration metadata
        calibration_data (pd.DataFrame): DataFrame with frequency-dependent calibration data
        sensitivity_interp (callable): Interpolation function for sensitivity vs frequency
    """
    
    def __init__(self, calibration_file_path: Union[str, Path]):
        """
        Initialize the Hydrophone object by reading a calibration file.
        
        Parameters:
            calibration_file_path: Path to the calibration file
        """
        self.calibration_file_path = Path(calibration_file_path)
        self.metadata = {}
        self.calibration_data = None
        self.sensitivity_interp = None
        
        self._parse_calibration_file()
        self._create_sensitivity_interpolator()
    
    def _parse_calibration_file(self):
        """Parse the calibration file to extract metadata and tabular data."""
        with open(self.calibration_file_path, 'r') as f:
            lines = f.readlines()
        
        # Parse metadata
        data_fields = []
        header_ended = False
        data_lines = []
        
        for line in lines:
            line = line.strip()
            
            # Skip comments and empty lines
            if line.startswith('#') or not line:
                continue
            
            # Check for header end
            if line.startswith('HEADER_END'):
                header_ended = True
                continue
            
            if not header_ended:
                # Handle DATA_FIELD entries specially (but not DATA_FIELDS)
                if line.startswith('DATA_FIELD\t'):  # Exact match for DATA_FIELD followed by tab
                    _, field_name = line.split('\t', 1)
                    data_fields.append(field_name)
                # Parse other metadata
                elif '\t' in line and not line.startswith('DATA_FIELD'):
                    key, value = line.split('\t', 1)
                    self.metadata[key] = value
            else:
                # This is data
                data_lines.append(line)
        
        # Parse tabular data
        if data_lines and data_fields:
            # Convert data lines to numeric arrays
            data_rows = []
            for line in data_lines:
                values = line.split()
                # Convert to float, handling scientific notation
                numeric_values = [float(val) for val in values]
                data_rows.append(numeric_values)
            
            # Create DataFrame
            self.calibration_data = pd.DataFrame(data_rows, columns=data_fields)
    
    def _create_sensitivity_interpolator(self):
        """Create interpolation function for sensitivity vs frequency."""
        if self.calibration_data is not None and 'FREQ_MHz' in self.calibration_data.columns:
            freq_mhz = self.calibration_data['FREQ_MHz'].values
            
            # Use V/Pa sensitivity for interpolation
            if 'SENS_VPERPA' in self.calibration_data.columns:
                sens_vperpa = self.calibration_data['SENS_VPERPA'].values
                self.sensitivity_interp = interp1d(
                    freq_mhz * 1e6,  # Convert MHz to Hz
                    1.0 / sens_vperpa,  # Convert V/Pa to Pa/V
                    kind='linear',
                    bounds_error=False,
                    fill_value='extrapolate'
                )
    
    def get_sensitivity_pa_per_v(self, frequency_hz: float) -> float:
        """
        Get the sensitivity in Pa/V at a given frequency.
        
        Parameters:
            frequency_hz: Frequency in Hz
            
        Returns:
            Sensitivity in Pa/V
        """
        if self.sensitivity_interp is None:
            raise ValueError("Sensitivity interpolator not available")
        
        return float(self.sensitivity_interp(frequency_hz))
    
    def get_frequency_response(self, frequencies_hz: np.ndarray) -> np.ndarray:
        """
        Get the frequency response (Pa/V) for an array of frequencies.
        
        Parameters:
            frequencies_hz: Array of frequencies in Hz
            
        Returns:
            Array of sensitivities in Pa/V
        """
        if self.sensitivity_interp is None:
            raise ValueError("Sensitivity interpolator not available")
        
        return self.sensitivity_interp(frequencies_hz)
    
    def deconvolve_voltage_signal(self, 
                                  voltage_signal: np.ndarray, 
                                  sampling_interval: float,
                                  center_frequency: float|None = None,
                                  bandwidth: float = 1.0) -> np.ndarray:
        """
        Deconvolve frequency-dependent sensitivity from a voltage signal to get pressure.
        
        This method applies the inverse frequency response of the hydrophone to convert
        a voltage vs time signal to pressure vs time, accounting for the frequency-
        dependent sensitivity.
        
        Parameters:
            voltage_signal: Voltage signal array (V)
            sampling_interval: Time between samples (seconds)
            center_frequency: Center frequency for optional bandpass filtering (Hz)
            bandwidth: Bandwidth for optional bandpass filtering (fraction of center frequency)
            
        Returns:
            Pressure signal array (Pa)
        """
        if self.sensitivity_interp is None:
            raise ValueError("Sensitivity interpolator not available")
        
        # Calculate sampling frequency and frequency array
        fs = 1.0 / sampling_interval
        n_samples = len(voltage_signal)
        
        # Create frequency array for FFT
        frequencies = np.fft.fftfreq(n_samples, sampling_interval)
        
        # Take FFT of voltage signal
        voltage_fft = np.fft.fft(voltage_signal)
        
        # Get frequency response (handle DC and negative frequencies)
        freq_response = np.zeros_like(frequencies, dtype=complex)
        
        # For positive frequencies
        pos_mask = frequencies > 0
        if np.any(pos_mask):
            freq_response[pos_mask] = self.get_frequency_response(frequencies[pos_mask])
        
        # For DC (f=0), use the sensitivity at the lowest calibrated frequency
        if frequencies[0] == 0:
            min_freq = self.calibration_data['FREQ_MHz'].min() * 1e6
            freq_response[0] = self.get_sensitivity_pa_per_v(min_freq)
        
        # For negative frequencies, use conjugate symmetry
        neg_mask = frequencies < 0
        if np.any(neg_mask):
            # Find corresponding positive frequencies
            pos_frequencies = -frequencies[neg_mask]
            freq_response[neg_mask] = self.get_frequency_response(pos_frequencies)

        # Optional hamming-windowed bandpass filtering
        if center_frequency is not None:
            # Create bandpass filter
            nyquist = fs / 2.0
            low_cut = max(center_frequency * (1 - bandwidth / 2), 0) / nyquist
            high_cut = min(center_frequency * (1 + bandwidth / 2), nyquist) / nyquist
            b, a = signal.butter(4, [low_cut, high_cut], btype='band')
            w, h = signal.freqz(b, a, worN=frequencies.size, fs=fs)
            # Interpolate filter response to match frequencies
            filter_response = np.interp(frequencies, w, np.abs(h))
            freq_response *= filter_response
        
        # Apply deconvolution (multiply by frequency response)
        pressure_fft = voltage_fft * freq_response
        
        # Take inverse FFT to get pressure signal
        pressure_signal = np.fft.ifft(pressure_fft).real
        
        return pressure_signal
    
    def get_metadata_summary(self) -> Dict[str, Any]:
        """
        Get a summary of the hydrophone metadata.
        
        Returns:
            Dictionary with key metadata fields
        """
        summary = {}
        
        # Extract key fields with more readable names
        field_mapping = {
            'Calibration_DATE': 'calibration_date',
            'HYD_MFG': 'manufacturer',
            'HYD_MODEL': 'model',
            'HYD_APERTURE_NOM_UM': 'aperture_um',
            'HYD_SN': 'serial_number',
            'HYD_POLARITY': 'polarity',
            'WATER_TEMP_DEGC': 'water_temperature_degc',
            'WATER_RESISTIVITY_MOHMS-CM': 'water_resistivity_mohms_cm'
        }
        
        for orig_key, new_key in field_mapping.items():
            if orig_key in self.metadata:
                summary[new_key] = self.metadata[orig_key]
        
        # Add frequency range information
        if self.calibration_data is not None:
            summary['frequency_range_mhz'] = {
                'min': float(self.calibration_data['FREQ_MHz'].min()),
                'max': float(self.calibration_data['FREQ_MHz'].max()),
                'n_points': len(self.calibration_data)
            }
        
        return summary
    
    def plot_calibration_data(self, figsize=(12, 8)):
        """
        Plot the calibration data.
        
        Parameters:
            figsize: Figure size tuple
            
        Returns:
            matplotlib figure object
        """
        try:
            import matplotlib.pyplot as plt
        except ImportError:
            raise ImportError("matplotlib is required for plotting")
        
        if self.calibration_data is None:
            raise ValueError("No calibration data available")
        
        fig, axes = plt.subplots(2, 2, figsize=figsize)
        fig.suptitle(f'Hydrophone Calibration Data - SN: {self.metadata.get("HYD_SN", "Unknown")}')
        
        freq_mhz = self.calibration_data['FREQ_MHz']
        
        # Sensitivity in dB
        if 'SENS_DB' in self.calibration_data.columns:
            axes[0, 0].plot(freq_mhz, self.calibration_data['SENS_DB'])
            axes[0, 0].set_xlabel('Frequency (MHz)')
            axes[0, 0].set_ylabel('Sensitivity (dB re 1V/µPa)')
            axes[0, 0].set_title('Sensitivity (dB)')
            axes[0, 0].grid(True)
        
        # Sensitivity in V/Pa
        if 'SENS_VPERPA' in self.calibration_data.columns:
            axes[0, 1].semilogy(freq_mhz, self.calibration_data['SENS_VPERPA'])
            axes[0, 1].set_xlabel('Frequency (MHz)')
            axes[0, 1].set_ylabel('Sensitivity (V/Pa)')
            axes[0, 1].set_title('Sensitivity (Linear)')
            axes[0, 1].grid(True)
        
        # Capacitance
        if 'CAP_PF' in self.calibration_data.columns:
            axes[1, 0].plot(freq_mhz, self.calibration_data['CAP_PF'])
            axes[1, 0].set_xlabel('Frequency (MHz)')
            axes[1, 0].set_ylabel('Capacitance (pF)')
            axes[1, 0].set_title('Capacitance')
            axes[1, 0].grid(True)
        
        # Power sensitivity
        if 'SENS_V2CM2PERW' in self.calibration_data.columns:
            axes[1, 1].semilogy(freq_mhz, self.calibration_data['SENS_V2CM2PERW'])
            axes[1, 1].set_xlabel('Frequency (MHz)')
            axes[1, 1].set_ylabel('Sensitivity (V²cm²/W)')
            axes[1, 1].set_title('Power Sensitivity')
            axes[1, 1].grid(True)
        
        plt.tight_layout()
        return fig
    
    def __repr__(self):
        """String representation of the Hydrophone object."""
        metadata = self.get_metadata_summary()
        return (f"Hydrophone(manufacturer='{metadata.get('manufacturer', 'Unknown')}', "
                f"model='{metadata.get('model', 'Unknown')}', "
                f"serial_number='{metadata.get('serial_number', 'Unknown')}', "
                f"aperture={metadata.get('aperture_um', 'Unknown')}µm)")