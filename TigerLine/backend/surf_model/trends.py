"""
Trend analysis module for swell forecasting.

Implements:
- Swell trend calculation (dHs/dt, dTp/dt)
- Trend classification (rising, falling, steady)
- Trend factor application to surf scores

Based on Section 4.3 of the Belmar specification.
"""

import numpy as np
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


def calculate_swell_trends(historical_buoy_data, hours=24):
    """
    Calculate swell trends from historical buoy data.
    
    Computes dHs/dt and dTp/dt over the last N hours.
    
    Parameters:
    -----------
    historical_buoy_data : dict
        Historical buoy data with 'times', 'Hs', 'Tp' lists
    hours : int
        Number of hours to analyze (default 24)
        
    Returns:
    --------
    trend_data : dict
        Dictionary with 'dHs_dt', 'dTp_dt', 'Hs_change', 'Tp_change'
    """
    if not historical_buoy_data or 'times' not in historical_buoy_data:
        return {
            'dHs_dt': 0.0,
            'dTp_dt': 0.0,
            'Hs_change': 0.0,
            'Tp_change': 0.0,
            'trend_classification': 'unknown'
        }
    
    times = historical_buoy_data['times']
    Hs_list = historical_buoy_data['Hs']
    Tp_list = historical_buoy_data['Tp']
    
    if len(times) < 2:
        return {
            'dHs_dt': 0.0,
            'dTp_dt': 0.0,
            'Hs_change': 0.0,
            'Tp_change': 0.0,
            'trend_classification': 'insufficient_data'
        }
    
    # Filter to last N hours
    now = datetime.now()
    cutoff_time = now - timedelta(hours=hours)
    
    recent_times = []
    recent_Hs = []
    recent_Tp = []
    
    for i, time in enumerate(times):
        if isinstance(time, str):
            time_obj = datetime.fromisoformat(time.replace('Z', '+00:00'))
        else:
            time_obj = time
        
        if time_obj >= cutoff_time:
            recent_times.append(time_obj)
            recent_Hs.append(Hs_list[i] if i < len(Hs_list) else Hs_list[-1])
            recent_Tp.append(Tp_list[i] if i < len(Tp_list) else Tp_list[-1])
    
    if len(recent_times) < 2:
        return {
            'dHs_dt': 0.0,
            'dTp_dt': 0.0,
            'Hs_change': 0.0,
            'Tp_change': 0.0,
            'trend_classification': 'insufficient_data'
        }
    
    # Calculate trends
    # Use linear regression for trend
    time_numeric = np.array([(t - recent_times[0]).total_seconds() / 3600.0 for t in recent_times])
    
    # Linear fit: Hs = a + b*t
    Hs_array = np.array(recent_Hs)
    Tp_array = np.array(recent_Tp)
    
    if len(time_numeric) > 1 and np.std(time_numeric) > 0:
        # Linear regression
        Hs_trend = np.polyfit(time_numeric, Hs_array, 1)[0]  # Slope (m/hour)
        Tp_trend = np.polyfit(time_numeric, Tp_array, 1)[0]  # Slope (s/hour)
    else:
        Hs_trend = 0.0
        Tp_trend = 0.0
    
    # Overall change
    Hs_change = Hs_array[-1] - Hs_array[0] if len(Hs_array) > 0 else 0.0
    Tp_change = Tp_array[-1] - Tp_array[0] if len(Tp_array) > 0 else 0.0
    
    # Classify trend
    trend_class = classify_swell_trend({
        'dHs_dt': Hs_trend,
        'dTp_dt': Tp_trend,
        'Hs_change': Hs_change,
        'Tp_change': Tp_change
    })
    
    return {
        'dHs_dt': float(Hs_trend),
        'dTp_dt': float(Tp_trend),
        'Hs_change': float(Hs_change),
        'Tp_change': float(Tp_change),
        'trend_classification': trend_class
    }


def classify_swell_trend(trend_data):
    """
    Classify swell trend as rising, falling, or steady.
    
    Parameters:
    -----------
    trend_data : dict
        Dictionary with 'dHs_dt', 'dTp_dt', 'Hs_change', 'Tp_change'
        
    Returns:
    --------
    classification : str
        'rising', 'falling', 'steady', or 'complex'
    """
    dHs_dt = trend_data.get('dHs_dt', 0.0)
    dTp_dt = trend_data.get('dTp_dt', 0.0)
    Hs_change = trend_data.get('Hs_change', 0.0)
    
    # Thresholds
    Hs_threshold = 0.05  # m/hour
    change_threshold = 0.2  # m over period
    
    if abs(dHs_dt) < Hs_threshold and abs(Hs_change) < change_threshold:
        return 'steady'
    elif dHs_dt > Hs_threshold or Hs_change > change_threshold:
        return 'rising'
    elif dHs_dt < -Hs_threshold or Hs_change < -change_threshold:
        return 'falling'
    else:
        return 'complex'


def apply_trend_factor(surf_score, trend_data, period_s):
    """
    Apply trend factor to adjust surf score.
    
    Logic:
    - Rapidly rising short-period = negative (junky surf coming)
    - Slowly easing long-period = positive (clean waves)
    - Steady = no change
    
    Parameters:
    -----------
    surf_score : float
        Base surf score (0-10)
    trend_data : dict
        Trend data from calculate_swell_trends()
    period_s : float
        Current wave period (s)
        
    Returns:
    --------
    adjusted_score : float
        Score adjusted for trends (0-10)
    """
    trend_class = trend_data.get('trend_classification', 'steady')
    dHs_dt = trend_data.get('dHs_dt', 0.0)
    
    # Base adjustment
    adjustment = 0.0
    
    if trend_class == 'rising':
        # Rapidly rising short-period = bad
        if period_s < 8.0 and abs(dHs_dt) > 0.1:
            adjustment = -0.5  # Penalty for junky windswell
        elif period_s >= 10.0:
            adjustment = 0.2  # Bonus for rising groundswell
    elif trend_class == 'falling':
        # Slowly easing long-period = good (clean conditions)
        if period_s >= 10.0 and abs(dHs_dt) < 0.05:
            adjustment = 0.3  # Bonus for clean easing swell
        else:
            adjustment = -0.2  # Penalty for falling swell
    # 'steady' = no adjustment
    
    # Apply adjustment
    adjusted_score = surf_score + adjustment
    
    # Clamp to [0, 10]
    adjusted_score = max(0.0, min(10.0, adjusted_score))
    
    return adjusted_score

