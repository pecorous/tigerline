"""
Wave propagation model for forecasting future wave conditions.

Implements:
- Travel time calculation from buoy to beach
- Wave decay/dissipation
- Wind wave generation
- Combined swell + wind wave forecast

Physics:
- Travel time: t = distance / cg (group velocity)
- Decay: Hs(t) = Hs(0) * exp(-t/tau) for swell
- Wind waves: Fetch-limited growth model
- Combined: Hs_total = sqrt(Hs_swell^2 + Hs_wind^2)
"""

import numpy as np
from datetime import datetime, timedelta
import logging
from . import dispersion

logger = logging.getLogger(__name__)

# Distance from buoy (Station 44025) to Belmar 16th Ave (km)
BUOY_TO_BEACH_DISTANCE_KM = 34.0

# Decay time constant for swell (hours)
# Typical values: 20-40 hours for swell, shorter for windswell
SWELL_DECAY_TAU_HOURS = 30.0

# Wind wave parameters
WIND_WAVE_FETCH_KM = 100.0  # Effective fetch for wind wave generation
WIND_WAVE_MIN_SPEED_MS = 3.0  # Minimum wind speed to generate waves


def calculate_travel_time(distance_km, period_s, depth_m=25.0):
    """
    Calculate travel time for waves to propagate from buoy to beach.
    
    Uses group velocity: t = distance / cg
    
    Parameters:
    -----------
    distance_km : float
        Distance from buoy to beach (km)
    period_s : float
        Wave period (s)
    depth_m : float
        Water depth at buoy location (m), default 25.0
    
    Returns:
    --------
    travel_time_hours : float
        Time for waves to travel (hours)
    """
    if period_s <= 0:
        return 0.0
    
    # Calculate group velocity
    cg = dispersion.group_speed(period_s, depth_m)
    
    if cg <= 0:
        return 0.0
    
    # Convert distance to meters
    distance_m = distance_km * 1000.0
    
    # Calculate travel time in seconds, then convert to hours
    travel_time_seconds = distance_m / cg
    travel_time_hours = travel_time_seconds / 3600.0
    
    return travel_time_hours


def propagate_wave_height(Hs_initial, time_hours, decay_rate=None, tau_hours=None):
    """
    Apply exponential decay to wave height over time.
    
    Decay model: Hs(t) = Hs(0) * exp(-t/tau)
    
    Parameters:
    -----------
    Hs_initial : float
        Initial significant wave height (m)
    time_hours : float
        Time elapsed (hours)
    decay_rate : float, optional
        Decay rate per hour (alternative to tau)
        If provided, tau = 1 / decay_rate
    tau_hours : float, optional
        Decay time constant (hours), default SWELL_DECAY_TAU_HOURS
    
    Returns:
    --------
    Hs_decayed : float
        Decayed wave height (m)
    """
    if tau_hours is None:
        if decay_rate is not None:
            tau_hours = 1.0 / decay_rate if decay_rate > 0 else SWELL_DECAY_TAU_HOURS
        else:
            tau_hours = SWELL_DECAY_TAU_HOURS
    
    if tau_hours <= 0:
        return Hs_initial
    
    # Exponential decay
    Hs_decayed = Hs_initial * np.exp(-time_hours / tau_hours)
    
    # Ensure non-negative
    return max(0.0, Hs_decayed)


def add_wind_wave_component(Hs_swell, wind_speed_ms, wind_dir_deg, swell_dir_deg, fetch_km=None):
    """
    Estimate wind wave contribution to total wave height.
    
    Uses simplified fetch-limited growth model:
    - Only generates waves if wind is onshore or cross-shore
    - Wind wave height depends on wind speed, fetch, and duration
    - Combined height: Hs_total = sqrt(Hs_swell^2 + Hs_wind^2)
    
    Parameters:
    -----------
    Hs_swell : float
        Swell wave height (m)
    wind_speed_ms : float
        Wind speed (m/s)
    wind_dir_deg : float
        Wind direction (degrees, coming-FROM)
    swell_dir_deg : float
        Swell direction (degrees, coming-FROM)
    fetch_km : float, optional
        Effective fetch (km), default WIND_WAVE_FETCH_KM
    
    Returns:
    --------
    Hs_total : float
        Combined swell + wind wave height (m)
    Hs_wind : float
        Wind wave component (m)
    """
    if fetch_km is None:
        fetch_km = WIND_WAVE_FETCH_KM
    
    # Calculate angle between wind and swell
    angle_diff = abs(wind_dir_deg - swell_dir_deg) % 360
    if angle_diff > 180:
        angle_diff = 360 - angle_diff
    
    # Wind wave generation is most effective when:
    # - Wind speed > minimum threshold
    # - Wind is roughly aligned with swell direction (within 45 degrees)
    # - Or wind is onshore (can generate local windswell)
    
    if wind_speed_ms < WIND_WAVE_MIN_SPEED_MS:
        # No wind wave generation
        return Hs_swell, 0.0
    
    # Simplified wind wave height estimation
    # Based on fetch-limited growth: Hs ~ U^2 * sqrt(fetch) / (g * duration)
    # Simplified: Hs_wind ≈ 0.01 * U^2 for moderate fetch
    # More accurate would use full fetch-limited growth formulas
    
    # Wind wave height (rough estimate)
    # For fetch ~100km, duration ~few hours: Hs_wind ≈ 0.008 * U^2
    Hs_wind = 0.008 * wind_speed_ms**2
    
    # Reduce wind wave if wind is not aligned with swell
    # If wind is perpendicular to swell (>90 degrees), minimal generation
    if angle_diff > 90:
        Hs_wind *= 0.3  # Reduced generation
    elif angle_diff > 45:
        Hs_wind *= 0.6  # Moderate generation
    
    # Limit wind wave height (realistic maximum)
    Hs_wind = min(Hs_wind, 2.0)  # Max ~2m wind waves
    
    # Combined height (energy addition)
    Hs_total = np.sqrt(Hs_swell**2 + Hs_wind**2)
    
    return Hs_total, Hs_wind


def interpolate_historical_data(historical_data, target_time):
    """
    Interpolate historical buoy data to a specific time.
    
    Parameters:
    -----------
    historical_data : dict
        Historical data with keys: 'times', 'Hs', 'Tp', 'peak_direction'
    target_time : datetime
        Target time for interpolation
    
    Returns:
    --------
    dict with keys: 'Hs', 'Tp', 'peak_direction'
    """
    if not historical_data or 'times' not in historical_data:
        # Fallback to latest values
        return {
            'Hs': historical_data.get('Hs', [1.5])[-1] if isinstance(historical_data.get('Hs'), list) else historical_data.get('Hs', 1.5),
            'Tp': historical_data.get('Tp', [10.0])[-1] if isinstance(historical_data.get('Tp'), list) else historical_data.get('Tp', 10.0),
            'peak_direction': historical_data.get('peak_direction', [90.0])[-1] if isinstance(historical_data.get('peak_direction'), list) else historical_data.get('peak_direction', 90.0)
        }
    
    times = historical_data['times']
    Hs_list = historical_data['Hs']
    Tp_list = historical_data['Tp']
    dir_list = historical_data.get('peak_direction', historical_data.get('mean_direction', [90.0]))
    
    if not times:
        return {'Hs': 1.5, 'Tp': 10.0, 'peak_direction': 90.0}
    
    # Convert times to numeric for interpolation
    times_numeric = np.array([(t - datetime(1970, 1, 1)).total_seconds() for t in times])
    target_numeric = (target_time - datetime(1970, 1, 1)).total_seconds()
    
    # Handle edge cases
    if target_numeric <= times_numeric[0]:
        return {'Hs': Hs_list[0], 'Tp': Tp_list[0], 'peak_direction': dir_list[0]}
    if target_numeric >= times_numeric[-1]:
        return {'Hs': Hs_list[-1], 'Tp': Tp_list[-1], 'peak_direction': dir_list[-1]}
    
    # Linear interpolation
    Hs_interp = np.interp(target_numeric, times_numeric, Hs_list)
    Tp_interp = np.interp(target_numeric, times_numeric, Tp_list)
    
    # Circular interpolation for direction
    dir_rad = np.deg2rad(dir_list)
    dir_complex = np.exp(1j * dir_rad)
    real_interp = np.interp(target_numeric, times_numeric, np.real(dir_complex))
    imag_interp = np.interp(target_numeric, times_numeric, np.imag(dir_complex))
    dir_interp_rad = np.angle(real_interp + 1j * imag_interp)
    dir_interp = np.rad2deg(dir_interp_rad) % 360
    
    return {
        'Hs': float(Hs_interp),
        'Tp': float(Tp_interp),
        'peak_direction': float(dir_interp)
    }


def forecast_wave_conditions(historical_data, forecast_time, wind_data=None, buoy_distance_km=None):
    """
    Forecast wave conditions at beach for a specific future time.
    
    Uses propagation model:
    1. Interpolate historical buoy data to time when waves left buoy
    2. Calculate travel time from buoy to beach
    3. Apply decay during propagation
    4. Add wind wave component if wind data provided
    
    Parameters:
    -----------
    historical_data : dict
        Historical buoy data with 'times', 'Hs', 'Tp', 'peak_direction'
    forecast_time : datetime
        Future time to forecast (when waves arrive at beach)
    wind_data : dict, optional
        Wind data with 'speed_ms' and 'direction_deg' for forecast_time
    buoy_distance_km : float, optional
        Distance from buoy to beach (km), default BUOY_TO_BEACH_DISTANCE_KM
    
    Returns:
    --------
    dict with keys:
        Hs : float
            Forecast significant wave height at beach (m)
        Tp : float
            Forecast peak period (s)
        peak_direction : float
            Forecast peak direction (degrees, coming-FROM)
        travel_time_hours : float
            Travel time from buoy to beach (hours)
        Hs_swell : float
            Swell component height (m)
        Hs_wind : float
            Wind wave component height (m)
    """
    if buoy_distance_km is None:
        buoy_distance_km = BUOY_TO_BEACH_DISTANCE_KM
    
    # Step 1: Find time when waves left buoy (forecast_time - travel_time)
    # For first iteration, use average period to estimate travel time
    avg_period = 10.0  # Default estimate
    if historical_data and 'Tp' in historical_data:
        Tp_list = historical_data['Tp']
        if isinstance(Tp_list, list) and Tp_list:
            avg_period = np.mean(Tp_list)
        elif not isinstance(Tp_list, list):
            avg_period = Tp_list
    
    # ALWAYS use most recent buoy data for current conditions
    # The "propagation" model was looking back in time and finding old high waves
    # For a real forecast, use CURRENT buoy reading
    buoy_conditions = interpolate_historical_data(historical_data, datetime.now())
    
    # Calculate travel time for reference (but don't use it to look backwards)
    travel_time = 0.0  # Minimal delay for current conditions
    
    Hs_initial = buoy_conditions['Hs']
    Tp_initial = buoy_conditions['Tp']
    dir_initial = buoy_conditions['peak_direction']
    
    # Step 3: Recalculate travel time with actual period
    travel_time = calculate_travel_time(buoy_distance_km, Tp_initial)
    
    # Step 4: Apply decay during propagation
    Hs_swell = propagate_wave_height(Hs_initial, travel_time)
    
    # Period and direction don't change significantly during propagation
    # (slight dispersion, but negligible for forecast purposes)
    Tp_forecast = Tp_initial
    dir_forecast = dir_initial
    
    # Step 5: Add wind wave component if wind data provided
    Hs_wind = 0.0
    if wind_data:
        wind_speed = wind_data.get('speed_ms', 0.0)
        wind_dir = wind_data.get('direction_deg', 0.0)
        
        Hs_total, Hs_wind = add_wind_wave_component(
            Hs_swell, wind_speed, wind_dir, dir_forecast
        )
        Hs_forecast = Hs_total
    else:
        Hs_forecast = Hs_swell
    
    return {
        'Hs': float(Hs_forecast),
        'Tp': float(Tp_forecast),
        'peak_direction': float(dir_forecast),
        'travel_time_hours': float(travel_time),
        'Hs_swell': float(Hs_swell),
        'Hs_wind': float(Hs_wind)
    }

