"""
Calibration module for learning from past observations.

Implements:
- K_site transformation factor calculation
- Tide/wind preference learning
- Bar state index calculation
- Bathymetry correction

Based on Section 4.1 and 4.2 of the Belmar specification.
"""

import json
import os
import numpy as np
from datetime import datetime, timedelta
import logging
from . import storage

logger = logging.getLogger(__name__)

# Import production config for paths
try:
    from config import production
    CALIBRATION_DIR = production.CALIBRATION_DIR
except ImportError:
    # Fallback for local development
    CALIBRATION_DIR = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        'data', 'calibration'
    )


def calculate_k_site(observations, direction_bins=None, period_bins=None):
    """
    Calculate empirical transformation factors K_site(dir, T).
    
    K_site(dir, T) = median(Hb_observed / Hs_offshore)
    
    Parameters:
    -----------
    observations : list of dict
        Observations with 'offshore', 'model', and optionally 'observation' keys
    direction_bins : list of float, optional
        Direction bin edges (degrees), default [45, 60, 90, 120, 180]
    period_bins : list of float, optional
        Period bin edges (seconds), default [7, 10, 14]
        
    Returns:
    --------
    k_site_dict : dict
        Dictionary with keys like 'k_site_60_90_7_10' (direction_range_period_range)
        Values are median K_site factors
    """
    if direction_bins is None:
        direction_bins = [45, 60, 90, 120, 180]
    if period_bins is None:
        period_bins = [7, 10, 14]
    
    # Filter observations that have human ratings
    rated_observations = [
        obs for obs in observations
        if 'observation' in obs and 'rating' in obs['observation']
    ]
    
    if len(rated_observations) < 5:
        logger.warning(f"Not enough rated observations ({len(rated_observations)}) for K_site calculation")
        return {}
    
    k_site_dict = {}
    
    # Bin by direction and period
    for i in range(len(direction_bins) - 1):
        dir_min = direction_bins[i]
        dir_max = direction_bins[i + 1]
        
        for j in range(len(period_bins) - 1):
            period_min = period_bins[j]
            period_max = period_bins[j + 1]
            
            # Find observations in this bin
            bin_observations = []
            for obs in rated_observations:
                offshore = obs.get('offshore', {})
                direction = offshore.get('direction', 0.0)
                period = offshore.get('Tp', 0.0)
                
                # Normalize direction to 0-360
                direction = direction % 360
                
                # Check if in direction bin
                if dir_min <= direction < dir_max or (dir_max == 180 and direction >= dir_min):
                    # Check if in period bin
                    if period_min <= period < period_max:
                        Hs_offshore = offshore.get('Hs', 0.0)
                        Hb_observed = obs.get('model', {}).get('Hb', 0.0)
                        
                        if Hs_offshore > 0:
                            k_site = Hb_observed / Hs_offshore
                            bin_observations.append(k_site)
            
            # Calculate median K_site for this bin
            if len(bin_observations) >= 3:  # Need at least 3 observations
                k_site_median = np.median(bin_observations)
                key = f"k_site_{dir_min}_{dir_max}_{period_min}_{period_max}"
                k_site_dict[key] = float(k_site_median)
                logger.info(f"K_site({dir_min}-{dir_max}°, {period_min}-{period_max}s) = {k_site_median:.3f} (n={len(bin_observations)})")
    
    return k_site_dict


def apply_k_site_correction(Hs_offshore, direction, period, k_site_dict):
    """
    Apply K_site correction to model predictions.
    
    Parameters:
    -----------
    Hs_offshore : float
        Offshore significant wave height (m)
    direction : float
        Swell direction (degrees, coming-FROM)
    period : float
        Wave period (s)
    k_site_dict : dict
        K_site factors from calculate_k_site()
        
    Returns:
    --------
    Hs_corrected : float
        Corrected offshore wave height (m)
    """
    if not k_site_dict:
        return Hs_offshore
    
    # Find matching bin
    direction = direction % 360
    
    # Try to find matching K_site factor
    k_site = 1.0  # Default (no correction)
    
    # Check each bin
    for key, k_value in k_site_dict.items():
        # Parse key: "k_site_60_90_7_10"
        parts = key.split('_')
        if len(parts) >= 6:
            try:
                dir_min = float(parts[2])
                dir_max = float(parts[3])
                period_min = float(parts[4])
                period_max = float(parts[5])
                
                if dir_min <= direction < dir_max and period_min <= period < period_max:
                    k_site = k_value
                    break
            except (ValueError, IndexError):
                continue
    
    # Apply correction
    Hs_corrected = k_site * Hs_offshore
    
    return Hs_corrected


def analyze_tide_preferences(observations):
    """
    Analyze tide preferences from observations.
    
    Bins scores by tide level and calculates average rating per bin.
    
    Parameters:
    -----------
    observations : list of dict
        Observations with 'local' (tide), 'model' (surf_score), and 'observation' (rating)
        
    Returns:
    --------
    tide_preferences : dict
        Dictionary with tide bins and average ratings
    """
    rated_observations = [
        obs for obs in observations
        if 'observation' in obs and 'rating' in obs['observation']
    ]
    
    if len(rated_observations) < 5:
        return {}
    
    # Bin by tide level (relative to mean tide = 0)
    tide_bins = {
        'low': [],      # < -0.4m
        'low_mid': [],  # -0.4 to -0.2m
        'mid': [],      # -0.2 to 0.2m
        'mid_high': [], # 0.2 to 0.4m
        'high': []      # > 0.4m
    }
    
    for obs in rated_observations:
        tide_level = obs.get('local', {}).get('tide', 0.0)
        rating = obs['observation']['rating']
        
        if tide_level < -0.4:
            tide_bins['low'].append(rating)
        elif tide_level < -0.2:
            tide_bins['low_mid'].append(rating)
        elif tide_level <= 0.2:
            tide_bins['mid'].append(rating)
        elif tide_level <= 0.4:
            tide_bins['mid_high'].append(rating)
        else:
            tide_bins['high'].append(rating)
    
    # Calculate averages
    preferences = {}
    for bin_name, ratings in tide_bins.items():
        if ratings:
            preferences[bin_name] = {
                'average_rating': float(np.mean(ratings)),
                'count': len(ratings)
            }
    
    return preferences


def analyze_wind_preferences(observations):
    """
    Analyze wind preferences from observations.
    
    Bins scores by wind type and speed, calculates average rating per bin.
    
    Parameters:
    -----------
    observations : list of dict
        Observations with 'local' (wind), 'model' (surf_score), and 'observation' (rating)
        
    Returns:
    --------
    wind_preferences : dict
        Dictionary with wind bins and average ratings
    """
    rated_observations = [
        obs for obs in observations
        if 'observation' in obs and 'rating' in obs['observation']
    ]
    
    if len(rated_observations) < 5:
        return {}
    
    # Import wind classification
    from . import quality
    
    # Bin by wind type and speed
    wind_bins = {
        'offshore_light': [],    # < 5 m/s
        'offshore_moderate': [], # 5-10 m/s
        'offshore_strong': [],   # > 10 m/s
        'cross_light': [],
        'cross_moderate': [],
        'onshore_light': [],
        'onshore_moderate': [],
        'onshore_strong': []
    }
    
    for obs in rated_observations:
        wind_speed = obs.get('local', {}).get('wind_speed', 0.0)
        wind_dir = obs.get('local', {}).get('wind_dir', 0.0)
        rating = obs['observation']['rating']
        
        wind_type = quality.classify_wind_type(wind_dir)
        
        if wind_type == 'offshore':
            if wind_speed < 5.0:
                wind_bins['offshore_light'].append(rating)
            elif wind_speed <= 10.0:
                wind_bins['offshore_moderate'].append(rating)
            else:
                wind_bins['offshore_strong'].append(rating)
        elif wind_type == 'cross':
            if wind_speed < 5.0:
                wind_bins['cross_light'].append(rating)
            else:
                wind_bins['cross_moderate'].append(rating)
        else:  # onshore
            if wind_speed < 5.0:
                wind_bins['onshore_light'].append(rating)
            elif wind_speed <= 10.0:
                wind_bins['onshore_moderate'].append(rating)
            else:
                wind_bins['onshore_strong'].append(rating)
    
    # Calculate averages
    preferences = {}
    for bin_name, ratings in wind_bins.items():
        if ratings:
            preferences[bin_name] = {
                'average_rating': float(np.mean(ratings)),
                'count': len(ratings)
            }
    
    return preferences


def calculate_bar_state_index(observations, window_days=30):
    """
    Calculate bar state index based on recent K_site behavior.
    
    Compares recent K_site to long-term average to detect bar changes.
    
    Parameters:
    -----------
    observations : list of dict
        All observations
    window_days : int
        Number of days for recent window (default 30)
        
    Returns:
    --------
    bar_state_index : float
        Index > 1.0 means bar moved closer (higher K_site)
        Index < 1.0 means bar moved offshore (lower K_site)
    """
    if len(observations) < 10:
        return 1.0  # Default (no change)
    
    # Separate recent vs long-term
    now = datetime.now()
    cutoff_date = now - timedelta(days=window_days)
    
    recent_obs = []
    long_term_obs = []
    
    for obs in observations:
        obs_time = datetime.fromisoformat(obs['timestamp'].replace('Z', '+00:00'))
        if obs_time >= cutoff_date:
            recent_obs.append(obs)
        else:
            long_term_obs.append(obs)
    
    if len(recent_obs) < 5 or len(long_term_obs) < 5:
        return 1.0
    
    # Calculate K_site for both periods
    recent_k_site = calculate_k_site(recent_obs)
    long_term_k_site = calculate_k_site(long_term_obs)
    
    if not recent_k_site or not long_term_k_site:
        return 1.0
    
    # Compare averages
    recent_avg = np.mean(list(recent_k_site.values()))
    long_term_avg = np.mean(list(long_term_k_site.values()))
    
    if long_term_avg > 0:
        bar_state_index = recent_avg / long_term_avg
    else:
        bar_state_index = 1.0
    
    return float(bar_state_index)


def save_calibration_data(k_site_dict, tide_preferences, wind_preferences, bar_state_index):
    """Save calibration data to JSON files."""
    os.makedirs(CALIBRATION_DIR, exist_ok=True)
    
    # Save K_site
    k_site_path = os.path.join(CALIBRATION_DIR, 'k_site.json')
    with open(k_site_path, 'w') as f:
        json.dump(k_site_dict, f, indent=2)
    
    # Save preferences
    preferences = {
        'tide': tide_preferences,
        'wind': wind_preferences,
        'bar_state_index': bar_state_index,
        'last_updated': datetime.now().isoformat()
    }
    
    prefs_path = os.path.join(CALIBRATION_DIR, 'preferences.json')
    with open(prefs_path, 'w') as f:
        json.dump(preferences, f, indent=2)


def load_calibration_data():
    """Load calibration data from JSON files."""
    k_site_dict = {}
    tide_preferences = {}
    wind_preferences = {}
    bar_state_index = 1.0
    
    # Load K_site
    k_site_path = os.path.join(CALIBRATION_DIR, 'k_site.json')
    if os.path.exists(k_site_path):
        try:
            with open(k_site_path, 'r') as f:
                k_site_dict = json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logger.warning(f"Failed to load K_site: {e}")
    
    # Load preferences
    prefs_path = os.path.join(CALIBRATION_DIR, 'preferences.json')
    if os.path.exists(prefs_path):
        try:
            with open(prefs_path, 'r') as f:
                prefs = json.load(f)
                tide_preferences = prefs.get('tide', {})
                wind_preferences = prefs.get('wind', {})
                bar_state_index = prefs.get('bar_state_index', 1.0)
        except (json.JSONDecodeError, IOError) as e:
            logger.warning(f"Failed to load preferences: {e}")
    
    return k_site_dict, tide_preferences, wind_preferences, bar_state_index

