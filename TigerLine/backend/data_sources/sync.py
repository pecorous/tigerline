"""
Data synchronization module.

Aligns buoy, wind, and tide data to a common time grid (hourly) with interpolation.
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


def synchronize_data(buoy_data, wind_data, tide_data, time_grid=None, hours=72):
    """
    Synchronize all data sources to a common hourly time grid.
    
    Parameters:
    -----------
    buoy_data : dict
        Buoy data with 'timestamp' key (or list of timestamps)
    wind_data : dict
        Wind data with 'times' list
    tide_data : dict
        Tide data with 'times' list
    time_grid : list, optional
        Custom time grid (list of datetime objects). If None, creates hourly grid.
    hours : int
        Number of hours for time grid (if time_grid is None)
        
    Returns:
    --------
    dict with synchronized data:
        times : list of datetime
            Common time grid
        buoy : dict with interpolated buoy data
        wind : dict with interpolated wind data
        tide : dict with interpolated tide data
    """
    # Create time grid if not provided
    if time_grid is None:
        now = datetime.now()
        time_grid = [now + timedelta(hours=i) for i in range(hours)]
    
    time_grid = pd.to_datetime(time_grid)
    
    # Synchronize buoy data
    # Assume buoy data is at single timestamp or needs interpolation
    buoy_sync = _sync_buoy_data(buoy_data, time_grid)
    
    # Synchronize wind data
    wind_sync = _sync_wind_data(wind_data, time_grid)
    
    # Synchronize tide data
    tide_sync = _sync_tide_data(tide_data, time_grid)
    
    return {
        'times': time_grid.tolist(),
        'buoy': buoy_sync,
        'wind': wind_sync,
        'tide': tide_sync
    }


def _sync_buoy_data(buoy_data, time_grid):
    """
    Synchronize buoy data to time grid.
    
    Handles both:
    - Single timestamp data: {'timestamp': ..., 'Hs': ..., 'Tp': ...}
    - Time series data: {'times': [...], 'Hs': [...], 'Tp': [...]}
    """
    if not isinstance(buoy_data, dict):
        return {}
    
    # Check if it's time series data (has 'times' key)
    if 'times' in buoy_data and isinstance(buoy_data['times'], list) and len(buoy_data['times']) > 0:
        # Time series data - return as-is for propagation model to handle
        # The propagation model will interpolate and forecast
        return {
            'times': buoy_data.get('times', []),
            'Hs': buoy_data.get('Hs', []),
            'Tp': buoy_data.get('Tp', []),
            'peak_direction': buoy_data.get('peak_direction', buoy_data.get('mean_direction', [])),
            'mean_direction': buoy_data.get('mean_direction', []),
            'source': buoy_data.get('source', 'unknown')
        }
    
    # Single timestamp data (legacy format)
    if 'timestamp' in buoy_data:
        # Use same values for all times
        return {
            'Hs': buoy_data.get('Hs', 1.5),
            'Tp': buoy_data.get('Tp', 8.0),
            'peak_direction': buoy_data.get('peak_direction', 120.0),
            'mean_direction': buoy_data.get('mean_direction', 125.0),
            'source': buoy_data.get('source', 'unknown')
        }
    
    # Fallback: try to extract single values
    return {
        'Hs': buoy_data.get('Hs', 1.5),
        'Tp': buoy_data.get('Tp', 8.0),
        'peak_direction': buoy_data.get('peak_direction', 120.0),
        'mean_direction': buoy_data.get('mean_direction', 125.0),
        'source': buoy_data.get('source', 'unknown')
    }


def _sync_wind_data(wind_data, time_grid):
    """Synchronize wind data to time grid with interpolation."""
    if not wind_data or 'times' not in wind_data:
        return {}
    
    times = pd.to_datetime(wind_data['times'])
    speeds = np.array(wind_data.get('speeds', []))
    directions = np.array(wind_data.get('directions', []))
    
    if len(times) == 0:
        return {}
    
    # Interpolate speeds and directions
    # Convert times to numeric for interpolation
    times_numeric = times.astype(np.int64) / 1e9  # Convert to seconds
    time_grid_numeric = time_grid.astype(np.int64) / 1e9
    
    speeds_interp = np.interp(time_grid_numeric, times_numeric, speeds)
    
    # For directions, handle circular interpolation (0-360 degrees)
    directions_interp = _interp_angles(time_grid_numeric, times_numeric, directions)
    
    # Interpolate temperature data if available
    temps_c = wind_data.get('temperature_c', [])
    temps_f = wind_data.get('temperature_f', [])
    feels_c = wind_data.get('feels_like_c', [])
    feels_f = wind_data.get('feels_like_f', [])
    
    temps_c_interp = []
    temps_f_interp = []
    feels_c_interp = []
    feels_f_interp = []
    
    if len(temps_c) == len(times):
        temps_c_interp = np.interp(time_grid_numeric, times_numeric, np.array(temps_c)).tolist()
        temps_f_interp = np.interp(time_grid_numeric, times_numeric, np.array(temps_f)).tolist()
        feels_c_interp = np.interp(time_grid_numeric, times_numeric, np.array(feels_c)).tolist()
        feels_f_interp = np.interp(time_grid_numeric, times_numeric, np.array(feels_f)).tolist()
    
    return {
        'speeds': speeds_interp.tolist(),
        'directions': directions_interp.tolist(),
        'temperature_c': temps_c_interp,
        'temperature_f': temps_f_interp,
        'feels_like_c': feels_c_interp,
        'feels_like_f': feels_f_interp,
        'source': wind_data.get('source', 'unknown')
    }


def _sync_tide_data(tide_data, time_grid):
    """Synchronize tide data to time grid with interpolation."""
    if not tide_data or 'times' not in tide_data:
        return {}
    
    times = pd.to_datetime(tide_data['times'])
    levels = np.array(tide_data.get('levels', []))
    
    if len(times) == 0:
        return {}
    
    # Interpolate tide levels
    times_numeric = times.astype(np.int64) / 1e9
    time_grid_numeric = time_grid.astype(np.int64) / 1e9
    
    levels_interp = np.interp(time_grid_numeric, times_numeric, levels)
    
    return {
        'levels': levels_interp.tolist(),
        'source': tide_data.get('source', 'unknown')
    }


def _interp_angles(x_new, x_old, angles_old):
    """
    Interpolate angles (circular interpolation for 0-360 degrees).
    
    Parameters:
    -----------
    x_new : array
        New x values
    x_old : array
        Old x values
    angles_old : array
        Angles in degrees (0-360)
        
    Returns:
    --------
    angles_new : array
        Interpolated angles
    """
    # Convert to radians, then to complex representation for circular interpolation
    angles_rad = np.deg2rad(angles_old)
    complex_old = np.exp(1j * angles_rad)
    
    # Interpolate real and imaginary parts separately
    real_interp = np.interp(x_new, x_old, np.real(complex_old))
    imag_interp = np.interp(x_new, x_old, np.imag(complex_old))
    
    # Convert back to angles
    angles_new_rad = np.angle(real_interp + 1j * imag_interp)
    angles_new = np.rad2deg(angles_new_rad)
    
    # Ensure 0-360 range
    angles_new = angles_new % 360
    
    return angles_new

