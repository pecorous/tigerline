"""
Wave transformation: shoaling, refraction, and breaking.

Implements classical Coastal Dynamics energy-conservation approach to transform
offshore buoy conditions to nearshore conditions.

Key assumptions documented:
- Linear wave theory used from buoy to inner shelf (no strong currents included)
- Depth-limited breaking with fixed gamma_b ≈ 0.78
- No explicit modeling of rip currents or 3D sandbar variability
- Breaking physics qualitatively informed by Basilisk simulations and Deike's
  work on breaking (steepness, Bond number, Reynolds number)

For ocean-scale surf waves:
- Reynolds number is very large; viscous effects are small in bulk
- Bond number is large, so capillary (surface tension) effects are negligible
- Depth-limited breaking criterion Hb ≈ gamma_b * h is reasonable for surf forecasting
"""

import numpy as np
from .dispersion import phase_speed, group_speed


def refract_direction(T, h1, h2, theta1):
    """
    Apply Snell's law to compute refracted wave direction.
    
    When waves travel over changing depth with no current, their direction
    changes following Snell's law:
        sin(theta) / c = constant along the ray
    
    Equivalently between two depths:
        sin(theta1) / c1 = sin(theta2) / c2
    
    where theta is measured from shore-normal (theta = 0 is straight-in).
    
    Parameters:
    -----------
    T : float
        Wave period (s)
    h1 : float
        Depth at first location (m)
    h2 : float
        Depth at second location (m)
    theta1 : float
        Wave direction at h1, measured from shore-normal (radians)
        
    Returns:
    --------
    theta2 : float
        Wave direction at h2, measured from shore-normal (radians)
    """
    c1 = phase_speed(T, h1)
    c2 = phase_speed(T, h2)
    
    if c1 <= 0 or c2 <= 0:
        return theta1
    
    # Snell's law: sin(theta2) = sin(theta1) * c2 / c1
    sin_theta2 = np.sin(theta1) * c2 / c1
    
    # Clip to valid range [-1, 1] to avoid numerical issues
    sin_theta2 = np.clip(sin_theta2, -1.0, 1.0)
    
    theta2 = np.arcsin(sin_theta2)
    
    # Waves refract towards shore-normal (theta → 0) as water becomes shallower
    return theta2


def shoal_and_refract(H1, T, h1, h2, theta1):
    """
    Apply shoaling and refraction to transform wave height and direction.
    
    Uses energy-flux conservation between two depths:
        H2 = H1 * sqrt( (cg1 * cos(theta1)) / (cg2 * cos(theta2)) )
    
    The combined shoaling-refraction coefficient:
        Ksr = H2 / H1 = sqrt( (cg1 * cos(theta1)) / (cg2 * cos(theta2)) )
    
    Parameters:
    -----------
    H1 : float
        Incident wave height at depth h1 (m)
    T : float
        Wave period (s)
    h1 : float
        Depth at first location (m)
    h2 : float
        Depth at second location (m)
    theta1 : float
        Wave direction at h1, measured from shore-normal (radians)
        
    Returns:
    --------
    H2 : float
        Transformed wave height at h2 (m)
    theta2 : float
        Refracted wave direction at h2 (radians)
    Ksr : float
        Shoaling-refraction coefficient
    """
    # Refract direction using Snell's law
    theta2 = refract_direction(T, h1, h2, theta1)
    
    # Compute group speeds
    cg1 = group_speed(T, h1)
    cg2 = group_speed(T, h2)
    
    # Avoid division by zero or negative values
    cos_theta1 = max(0.01, abs(np.cos(theta1)))  # Small minimum to avoid issues
    cos_theta2 = max(0.01, abs(np.cos(theta2)))
    
    # Energy flux conservation
    ratio = (cg1 * cos_theta1) / (cg2 * cos_theta2)
    ratio = max(0.01, ratio)  # Ensure positive
    
    Ksr = np.sqrt(ratio)
    H2 = H1 * Ksr
    
    return H2, theta2, Ksr


def check_breaking(H, h, gamma_b=0.78):
    """
    Check if wave is breaking using depth-limited breaking criterion.
    
    Field and lab data show that in shallow water the maximum wave height
    is roughly proportional to water depth:
        Hb ≈ gamma_b * hb
    
    where:
        Hb is breaking wave height
        hb is local water depth at breaking
        gamma_b is the breaker index, typically 0.7-0.8 for random waves
    
    Parameters:
    -----------
    H : float
        Incident wave height (m)
    h : float
        Local water depth (m)
    gamma_b : float
        Breaker index, default 0.78
        
    Returns:
    --------
    is_breaking : bool
        True if wave is breaking
    Hb : float
        Breaking wave height (m). When breaking occurs (H >= gamma_b * h),
        returns the actual wave height H (which represents the shoaled height
        at breaking). The breaking criterion gamma_b * h represents the maximum
        stable height, but waves can exceed this slightly before breaking.
    """
    if h <= 0:
        return True, 0.0
    
    H_max = gamma_b * h
    is_breaking = H >= H_max
    
    # When breaking occurs, use the actual shoaled wave height
    # This represents the actual breaking wave height after shoaling
    if is_breaking:
        Hb = H  # Use actual shoaled height
    else:
        Hb = H  # Not breaking yet, but return current height
    
    return is_breaking, Hb


def find_breaking_point(H_offshore, T, theta_offshore, profile, gamma_b=0.78, return_path=False):
    """
    Find breaking point by stepping through bathymetric profile.
    
    Steps from offshore towards shore, applying shoaling/refraction at each
    step and checking breaking condition. Stops when wave first satisfies
    H >= gamma_b * h.
    
    Parameters:
    -----------
    H_offshore : float
        Offshore wave height (m)
    T : float
        Wave period (s)
    theta_offshore : float
        Offshore wave direction, measured from shore-normal (radians)
    profile : list of tuples or array
        Bathymetric profile: [(x1, h1), (x2, h2), ...] where x is distance
        from shore (m) and h is depth (m). Should be ordered from offshore
        to nearshore.
    gamma_b : float
        Breaker index, default 0.78
    return_path : bool
        If True, return the full shoaling path with intermediate calculations
        
    Returns:
    --------
    Hb : float
        Breaking wave height (m)
    h_break : float
        Depth at breaking (m)
    x_break : float
        Distance from shore at breaking (m)
    theta_break : float
        Wave direction at breaking (radians)
    path : list (optional)
        If return_path=True, list of dicts with shoaling path details:
        [{'x': x, 'h': h, 'H': H, 'theta': theta, 'c': c, 'cg': cg, 'Ksr': Ksr}, ...]
    """
    profile = np.asarray(profile)
    
    if len(profile) == 0:
        if return_path:
            return 0.0, 0.0, 0.0, 0.0, []
        return 0.0, 0.0, 0.0, 0.0
    
    # Start from offshore (last point in profile)
    H = H_offshore
    theta = theta_offshore
    path = []
    
    # Step from offshore to nearshore
    for i in range(len(profile) - 1, -1, -1):
        x, h = profile[i]
        
        # Calculate phase and group speeds at this point
        c = phase_speed(T, h)
        cg = group_speed(T, h)
        
        # Store path point
        if return_path:
            path.append({
                'x': float(x),
                'h': float(h),
                'H': float(H),
                'theta_rad': float(theta),
                'theta_deg': float(np.rad2deg(theta)),
                'c': float(c),
                'cg': float(cg),
                'Ksr': float(H / H_offshore) if H_offshore > 0 else 1.0
            })
        
        # Check breaking condition
        is_breaking, Hb = check_breaking(H, h, gamma_b)
        
        if is_breaking:
            if return_path:
                return Hb, h, x, theta, path
            return Hb, h, x, theta
        
        # If not breaking and not at shore, propagate to next point
        if i > 0:
            x_next, h_next = profile[i - 1]
            H_new, theta_new, Ksr = shoal_and_refract(H, T, h, h_next, theta)
            H = H_new
            theta = theta_new
    
    # If we reach here, wave didn't break (shouldn't happen in practice)
    # Return values at shore
    x_shore, h_shore = profile[0]
    _, Hb = check_breaking(H, h_shore, gamma_b)
    if return_path:
        return Hb, h_shore, x_shore, theta, path
    return Hb, h_shore, x_shore, theta


def iribarren_number(beta, H0, T):
    """
    Compute Iribarren number (surf similarity parameter).
    
    Iribarren number:
        Xi = tan(beta) / sqrt(H0 / L0)
    
    where:
        beta is the local beach slope at breaking (radians)
        H0 is a deep-water wave height equivalent to the incident wave (m)
        L0 is deep-water wavelength: L0 = g * T^2 / (2 * pi)
    
    Parameters:
    -----------
    beta : float
        Beach slope (radians)
    H0 : float
        Deep-water equivalent wave height (m)
    T : float
        Wave period (s)
        
    Returns:
    --------
    Xi : float
        Iribarren number
    """
    from .dispersion import G
    
    if T <= 0 or H0 <= 0:
        return 0.0
    
    # Deep-water wavelength
    L0 = G * T**2 / (2.0 * np.pi)
    
    if L0 <= 0:
        return 0.0
    
    Xi = np.tan(beta) / np.sqrt(H0 / L0)
    return Xi


def breaker_type_from_iribarren(Xi):
    """
    Classify breaker type from Iribarren number.
    
    Empirical classification (approximate):
    - Xi < 0.4: spilling breakers
    - 0.4 <= Xi < 2: plunging breakers
    - Xi >= 2: surging/collapsing
    
    Parameters:
    -----------
    Xi : float
        Iribarren number
        
    Returns:
    --------
    breaker_type : str
        "spilling", "plunging", or "surging"
    """
    if Xi < 0.4:
        return "spilling"
    elif Xi < 2.0:
        return "plunging"
    else:
        return "surging"

