"""
Surf quality scoring model.

Combines breaking wave height, period, direction, wind, and tide into a
simple "wave quality for surfing" score (0-10).

Uses transparent, piecewise-linear rules based on physical parameters.
REVISED: Stricter scoring to target realistic average of 4-5/10.
"""

import numpy as np
from ..waves.stats import angle_between


def height_subscore(Hb_ft):
    """
    Compute height subscore based on breaking wave height.
    
    REVISED - REALISTIC SCORING:
    - < 2 ft = score 0.0-0.05 (essentially flat/unrideable)
    - 2-3 ft = knee-high, terrible = score 0.05-0.15 (NOT WORTH IT)
    - 3-4 ft = waist-high, poor = score 0.15-0.30 (ONLY if perfect conditions)
    - 4-5 ft = chest-high, fair = score 0.30-0.50 (MINIMUM for decent surf)
    - 5-7 ft = head-high, good = score 0.50-0.85 (GOOD CONDITIONS)
    - 7-9 ft = overhead, excellent = score 0.85-1.0 (BEST CONDITIONS)
    - > 9 ft = very large = score 0.5-0.2 (depends on period)
    
    Parameters:
    -----------
    Hb_ft : float
        Breaking wave height in feet
        
    Returns:
    --------
    S_H : float
        Height subscore (0-1)
    """
    # REALISTIC: Anything below 3 ft is essentially unrideable
    if Hb_ft < 2.0:
        return 0.0  # Essentially flat - unrideable
    elif Hb_ft < 2.5:
        return 0.02  # 2-2.5 ft = maybe ankle slappers, terrible
    elif Hb_ft < 3.0:
        return 0.05  # 2.5-3 ft = knee-high, NOT WORTH IT
    elif Hb_ft < 3.5:
        return 0.10  # 3-3.5 ft = barely waist-high, poor
    elif Hb_ft < 4.0:
        return 0.15  # 3.5-4 ft = waist-high, poor
    elif Hb_ft < 4.5:
        return 0.25  # 4-4.5 ft = chest-high, fair
    elif Hb_ft < 5.0:
        return 0.35  # 4.5-5 ft = chest-high, fair
    elif Hb_ft < 6.0:
        return 0.35 + 0.25 * (Hb_ft - 5.0) / 1.0  # 5-6 ft = 0.35-0.60
    elif Hb_ft < 7.0:
        return 0.60 + 0.20 * (Hb_ft - 6.0) / 1.0  # 6-7 ft = 0.60-0.80
    elif Hb_ft <= 8.0:
        return 0.80 + 0.15 * (Hb_ft - 7.0) / 1.0  # 7-8 ft = 0.80-0.95
    elif Hb_ft <= 9.0:
        return 0.95 + 0.05 * (Hb_ft - 8.0) / 1.0  # 8-9 ft = 0.95-1.0
    elif Hb_ft <= 10.0:
        return 1.0 - 0.30 * (Hb_ft - 9.0) / 1.0  # 9-10 ft = 0.70-1.0
    else:
        return 0.2  # Very large = closing out


def period_subscore(T):
    """
    Compute period subscore based on wave period.
    
    CALIBRATED FOR BELMAR 16TH AVE:
    - Peak at 9-14s (especially 10-12s) = score 1.0
    - 7-9s = fair, some power = score 0.4-0.6
    - <7s = peaky, less lined-up = score <0.5
    - >14s = may over-run bar = score 0.9
    
    Parameters:
    -----------
    T : float
        Wave period (s)
        
    Returns:
    --------
    S_T : float
        Period subscore (0-1)
    """
    if T < 5.0:
        return 0.1
    elif T < 7.0:
        return 0.2 + 0.2 * (T - 5.0) / 2.0
    elif T < 9.0:
        return 0.4 + 0.2 * (T - 7.0) / 2.0
    elif T <= 12.0:
        return 0.6 + 0.4 * (T - 9.0) / 3.0
    elif T <= 14.0:
        return 1.0 - 0.1 * (T - 12.0) / 2.0
    else:
        return 0.9


def swell_direction_subscore(swell_dir_coming_from):
    """
    Compute subscore based on swell coming-FROM direction.
    
    CALIBRATED FOR BELMAR 16TH AVE:
    - Peak for E-ENE (90-60° coming-FROM) = score 1.0
    - SE (120-135°) = okay but less focused = score 0.6-0.8
    - NE (45°) = very good but stormy = score 0.8-0.9
    - S/SSW (180-225°) = not well exposed = score 0.2-0.4
    
    Parameters:
    -----------
    swell_dir_coming_from : float
        Swell direction coming-FROM (degrees clockwise from north)
        
    Returns:
    --------
    S_swell : float
        Swell direction subscore (0-1)
    """
    # Normalize to 0-360
    dir_norm = swell_dir_coming_from % 360
    
    # E-ENE (60-90°) = ideal
    if 60 <= dir_norm <= 90:
        return 1.0
    # NE (45-60°) = very good
    elif 45 <= dir_norm < 60:
        return 0.8 + 0.2 * (dir_norm - 45) / 15
    # ENE-E (90-100°) = still good
    elif 90 < dir_norm <= 100:
        return 1.0 - 0.2 * (dir_norm - 90) / 10
    # SE (120-135°) = okay but less focused
    elif 120 <= dir_norm <= 135:
        return 0.6 + 0.2 * (135 - dir_norm) / 15
    # S/SSW (180-225°) = not well exposed
    elif 180 <= dir_norm <= 225:
        return 0.2 + 0.2 * (225 - dir_norm) / 45
    else:
        return 0.4  # Other directions


def breaking_angle_subscore(theta_break):
    """
    Compute subscore based on breaking angle relative to shore-normal.
    
    CALIBRATED FOR BELMAR 16TH AVE:
    - 10-25° = ideal peel = score 1.0
    - 8-10° = good peel = score 0.8-1.0
    - 25-30° = too much angle = score 0.7-1.0
    - <5° = closes out = score 0.3
    
    Parameters:
    -----------
    theta_break : float
        Breaking angle relative to shore-normal (degrees)
        
    Returns:
    --------
    S_angle : float
        Breaking angle subscore (0-1)
    """
    abs_theta = abs(theta_break)
    # 10-25° = ideal peel
    if 10 <= abs_theta <= 25:
        return 1.0
    # 8-10° = good peel
    elif 8 <= abs_theta < 10:
        return 0.8 + 0.2 * (abs_theta - 8) / 2
    # 25-30° = too much angle
    elif 25 < abs_theta <= 30:
        return 1.0 - 0.3 * (abs_theta - 25) / 5
    # <5° = closes out
    elif abs_theta < 5:
        return 0.3
    else:
        return 0.5


def direction_subscore(theta_break, swell_dir_coming_from):
    """
    Compute direction subscore combining swell direction and breaking angle.
    
    CALIBRATED FOR BELMAR 16TH AVE:
    Combines:
    - Swell direction score (60% weight) - based on coming-FROM direction
    - Breaking angle score (40% weight) - based on peel angle
    
    Parameters:
    -----------
    theta_break : float
        Breaking angle relative to shore-normal (degrees)
    swell_dir_coming_from : float
        Swell direction coming-FROM (degrees clockwise from north)
        
    Returns:
    --------
    S_dir : float
        Direction subscore (0-1)
    """
    S_swell = swell_direction_subscore(swell_dir_coming_from)
    S_angle = breaking_angle_subscore(theta_break)
    return 0.6 * S_swell + 0.4 * S_angle


def wind_subscore(U, wind_type):
    """
    Compute wind subscore based on wind speed and type.
    
    REVISED - REALISTIC SCORING:
    - Offshore (W-NW): Light to moderate (up to 8 m/s) = score 1.0
    - Cross-shore (N/S): Light = score 0.6, moderate = score 0.3
    - Onshore (E-sector): ANY onshore = score 0.0-0.15 (DEVASTATING)
    
    Parameters:
    -----------
    U : float
        Wind speed (m/s)
    wind_type : str
        'offshore', 'cross', or 'onshore'
        
    Returns:
    --------
    S_wind : float
        Wind subscore (0-1)
    """
    if wind_type == 'offshore':
        if U < 2.0:
            return 1.0
        elif U <= 8.0:
            return 1.0 - 0.1 * (U - 2.0) / 6.0
        elif U <= 12.0:
            return 0.9 - 0.3 * (U - 8.0) / 4.0
        else:
            return 0.6
    elif wind_type == 'cross':
        if U < 3.0:
            return 0.6  # Light cross-shore
        elif U <= 8.0:
            return 0.6 - 0.3 * (U - 3.0) / 5.0  # 0.6-0.3
        else:
            return 0.2  # Strong cross-shore
    else:  # onshore - DEVASTATING
        # ANY onshore wind ruins conditions
        if U < 2.0:
            return 0.15  # Very light onshore = still terrible
        elif U < 5.0:
            return 0.10  # Light onshore = terrible
        elif U <= 8.0:
            return 0.05  # Moderate onshore = very terrible
        else:
            return 0.0  # Strong onshore = completely unrideable


def classify_wind_type(wind_dir_coming_from):
    """
    Classify wind as offshore, cross-shore, or onshore.
    
    CALIBRATED FOR BELMAR 16TH AVE:
    Uses absolute wind directions (coming-FROM):
    - W-NW (260-330°) = offshore
    - E-sector (45-135°) = onshore
    - N or S quadrant = cross-shore
    
    Parameters:
    -----------
    wind_dir_coming_from : float
        Wind direction (degrees, coming-FROM, clockwise from north)
        
    Returns:
    --------
    wind_type : str
        'offshore', 'cross', or 'onshore'
    """
    dir_norm = wind_dir_coming_from % 360
    # W-NW (260-330°) = offshore
    if 260 <= dir_norm <= 330:
        return 'offshore'
    # E-sector (45-135°) = onshore
    elif 45 <= dir_norm <= 135:
        return 'onshore'
    # N or S quadrant = cross-shore
    else:
        return 'cross'


def tide_subscore(eta_tide, mean_tide=0.0):
    """
    Compute tide subscore based on tide level.
    
    CALIBRATED FOR BELMAR 16TH AVE:
    - Mid-tide = score 1.0
    - Low-mid or mid-rising = score 0.9-1.0
    - Low and high tide = score 0.5-0.7
    
    Parameters:
    -----------
    eta_tide : float
        Tide level relative to mean sea level (m)
    mean_tide : float
        Mean tide level (m), default 0
        
    Returns:
    --------
    S_tide : float
        Tide subscore (0-1)
    """
    dist_from_mean = abs(eta_tide - mean_tide)
    # Mid-tide (within 0.2m) = 1.0
    if dist_from_mean <= 0.2:
        return 1.0
    # Low-mid/mid-rising (0.2-0.4m) = 0.9-1.0
    elif dist_from_mean <= 0.4:
        return 0.9 + 0.1 * (0.4 - dist_from_mean) / 0.2
    # Low/high (0.4-0.8m) = 0.5-0.7
    elif dist_from_mean <= 0.8:
        return 0.7 - 0.2 * (dist_from_mean - 0.4) / 0.4
    # Extreme (>0.8m) = 0.3-0.5
    else:
        return max(0.3, 0.5 - 0.2 * min(1.0, (dist_from_mean - 0.8) / 0.7))


def breaker_type_multiplier(breaker_type):
    """
    Compute breaker type multiplier.
    
    CALIBRATED FOR BELMAR 16TH AVE:
    - Plunging = 1.0 (hollow barrels - best)
    - Spilling = 0.85 (softer waves)
    - Surging = 0.4 (close-outs - strong penalty)
    
    Parameters:
    -----------
    breaker_type : str
        'spilling', 'plunging', or 'surging'
        
    Returns:
    --------
    M_break : float
        Breaker type multiplier (0-1)
    """
    multipliers = {
        'spilling': 0.85,  # Softer waves
        'plunging': 1.0,   # Best for barrels
        'surging': 0.4     # Strong penalty for close-outs
    }
    return multipliers.get(breaker_type.lower(), 0.7)


def apply_penalties(S_base, Hb_ft, T, theta_break, wind_type, U, eta_tide, swell_dir_coming_from):
    """
    Apply multiplicative penalties for bad condition combinations.
    
    REVISED - MUCH STRICTER PENALTIES:
    - Small waves + onshore wind = DEVASTATING (near-zero score)
    - Small waves (< 3 ft) = hard penalty regardless
    - Onshore wind = heavy penalty
    
    Parameters:
    -----------
    S_base : float
        Base score before penalties
    Hb_ft : float
        Breaking wave height (ft)
    T : float
        Wave period (s)
    theta_break : float
        Breaking angle (degrees)
    wind_type : str
        Wind type ('offshore', 'cross', 'onshore')
    U : float
        Wind speed (m/s)
    eta_tide : float
        Tide level (m)
    swell_dir_coming_from : float
        Swell direction coming-FROM (degrees)
        
    Returns:
    --------
    penalty_multiplier : float
        Multiplier to apply to base score (0-1)
    """
    penalty = 1.0
    
    # CRITICAL PENALTY: Small waves + onshore wind = unrideable
    if Hb_ft < 3.0 and wind_type == 'onshore':
        penalty *= 0.1  # Devastating combination - 90% penalty
    
    # CRITICAL PENALTY: Very small waves (< 2.5 ft) = essentially unrideable
    if Hb_ft < 2.5:
        penalty *= 0.2  # 80% penalty - unrideable
    
    # CRITICAL PENALTY: Small waves (< 3 ft) = not worth it
    if Hb_ft < 3.0:
        penalty *= 0.4  # 60% penalty
    
    # CRITICAL PENALTY: ANY onshore wind = ruins conditions
    if wind_type == 'onshore':
        penalty *= 0.3  # 70% penalty for onshore
    
    # Penalty: S/SSW swell (not well exposed)
    dir_norm = swell_dir_coming_from % 360
    if 180 <= dir_norm <= 225:
        penalty *= 0.7
    
    # Penalty: Large waves + short period = closing out
    if Hb_ft > 8.0 and T < 8.0:
        penalty *= 0.5
    
    # Penalty: Onshore wind + short period = mushy mess
    if wind_type == 'onshore' and T < 7.0:
        penalty *= 0.5  # Additional penalty
    
    # Penalty: Straight-in waves + onshore wind = terrible
    if abs(theta_break) < 5.0 and wind_type == 'onshore':
        penalty *= 0.4  # Additional penalty
    
    # Penalty: Extreme tide + large waves = may not break properly
    dist_from_mean = abs(eta_tide)
    if dist_from_mean > 0.8 and Hb_ft > 6.0:
        penalty *= 0.8
    
    return penalty


def compute_surf_score(Hb, T, theta_break, breaker_type, U, wind_dir, eta_tide, swell_dir_coming_from):
    """
    Compute final surf quality score (0-10) from all physical parameters.
    
    CALIBRATED FOR BELMAR 16TH AVE:
    Combines sub-scores using weighted average:
        S_base = w_H * S_H + w_T * S_T + w_dir * S_dir + w_wind * S_wind + w_tide * S_tide
    
    Applies penalties for bad combinations, then breaker type multiplier:
        S_final = S_base * penalty * M_break
    
    Finally maps to 0-10 scale:
        surf_score = 10 * S_final
    
    Parameters:
    -----------
    Hb : float
        Breaking wave height (m)
    T : float
        Wave period (s)
    theta_break : float
        Breaking angle relative to shore-normal (degrees)
    breaker_type : str
        'spilling', 'plunging', or 'surging'
    U : float
        Wind speed (m/s)
    wind_dir : float
        Wind direction (degrees, coming-from)
    eta_tide : float
        Tide level relative to mean sea level (m)
    swell_dir_coming_from : float
        Swell direction coming-FROM (degrees, clockwise from north)
        
    Returns:
    --------
    dict with keys:
        surf_score : float
            Final surf score (0-10)
        sub_scores : dict
            All individual sub-scores for transparency
        physical_params : dict
            Physical parameters used
    """
    # Convert height to feet for surfer feel
    Hb_ft = Hb * 3.28084  # meters to feet
    
    # Compute sub-scores
    S_H = height_subscore(Hb_ft)
    S_T = period_subscore(T)
    S_dir = direction_subscore(theta_break, swell_dir_coming_from)
    
    # Classify wind type using absolute directions
    wind_type = classify_wind_type(wind_dir)
    S_wind = wind_subscore(U, wind_type)
    
    S_tide = tide_subscore(eta_tide)
    
    # Weights - adjusted to emphasize height and wind (most critical)
    weights = {
        'H': 0.30,  # Wave height is CRITICAL - can't surf without waves
        'T': 0.20,  # Period matters but less than height
        'dir': 0.15,  # Direction affects quality
        'wind': 0.30,  # Wind can completely ruin conditions
        'tide': 0.05  # Tide matters least
    }
    
    S_base = (
        weights['H'] * S_H +
        weights['T'] * S_T +
        weights['dir'] * S_dir +
        weights['wind'] * S_wind +
        weights['tide'] * S_tide
    )
    
    # Apply penalties for bad combinations
    penalty = apply_penalties(S_base, Hb_ft, T, theta_break, wind_type, U, eta_tide, swell_dir_coming_from)
    S_penalized = S_base * penalty
    
    # Apply breaker type multiplier
    M_break = breaker_type_multiplier(breaker_type)
    S_final = S_penalized * M_break
    
    # Map to 0-10 scale
    surf_score = 10.0 * S_final
    surf_score = float(np.clip(surf_score, 0.0, 10.0))  # Ensure Python float
    
    return {
        'surf_score': surf_score,
        'sub_scores': {
            'height': float(S_H),
            'period': float(S_T),
            'direction': float(S_dir),
            'wind': float(S_wind),
            'tide': float(S_tide)
        },
        'weights': weights,
        'penalty_multiplier': float(penalty),
        'breaker_multiplier': float(M_break),
        'base_score': float(S_base),
        'penalized_score': float(S_penalized),
        'physical_params': {
            'Hb_m': float(Hb),
            'Hb_ft': float(Hb_ft),
            'T': float(T),
            'theta_break_deg': float(theta_break),
            'breaker_type': breaker_type,
            'wind_speed_ms': float(U),
            'wind_direction_deg': float(wind_dir),
            'wind_type': wind_type,
            'tide_level_m': float(eta_tide),
            'swell_direction_deg': float(swell_dir_coming_from)
        }
    }
