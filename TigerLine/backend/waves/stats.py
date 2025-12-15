"""
Statistical helper functions for wave analysis.
"""

import numpy as np


def normalize_angle(angle, degrees=False):
    """
    Normalize angle to [-pi, pi] or [-180, 180] range.
    
    Parameters:
    -----------
    angle : float
        Angle to normalize
    degrees : bool
        If True, treat as degrees; if False, treat as radians
        
    Returns:
    --------
    normalized : float
        Normalized angle
    """
    if degrees:
        period = 360.0
        half_period = 180.0
    else:
        period = 2.0 * np.pi
        half_period = np.pi
    
    normalized = angle % period
    if normalized > half_period:
        normalized -= period
    
    return normalized


def angle_between(dir1, dir2, degrees=False):
    """
    Compute smallest angle between two directions.
    
    Parameters:
    -----------
    dir1 : float
        First direction
    dir2 : float
        Second direction
    degrees : bool
        If True, treat as degrees; if False, treat as radians
        
    Returns:
    --------
    angle : float
        Smallest angle between directions
    """
    diff = normalize_angle(dir2 - dir1, degrees=degrees)
    return abs(diff)

