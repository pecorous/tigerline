"""
Linear wave theory: dispersion relation, phase and group velocity, energy.

Implements the linear dispersion relation for surface gravity waves:
    omega^2 = g * k * tanh(k * h)

where:
    omega = 2 * pi / T is angular frequency (rad/s)
    T is wave period (s)
    k is wavenumber (1/m)
    h is water depth (m)
    g = 9.81 m/s^2
"""

import numpy as np
from scipy.optimize import fsolve


# Gravitational acceleration (m/s^2)
G = 9.81

# Water density (kg/m^3)
RHO_WATER = 1025.0


def solve_dispersion(T, h, tol=1e-6):
    """
    Solve dispersion relation for wavenumber k given period T and depth h.
    
    Uses Newton-Raphson iterative solver with deep-water initial guess.
    
    Deep water initial guess: k0 = omega^2 / g
    
    Special cases:
    - Deep water (h very large, k*h >> 1): tanh(k*h) ≈ 1
      omega^2 ≈ g * k, so k_deep = omega^2 / g
    - Shallow water (k*h << 1): tanh(k*h) ≈ k*h
      omega^2 ≈ g * k^2 * h, so phase speed c ≈ sqrt(g*h), independent of frequency
    
    Parameters:
    -----------
    T : float
        Wave period (s)
    h : float
        Water depth (m)
    tol : float
        Convergence tolerance
        
    Returns:
    --------
    k : float
        Wavenumber (1/m)
    """
    if T <= 0:
        return 0.0
    
    if h <= 0:
        return 0.0
    
    omega = 2.0 * np.pi / T
    
    # Deep water initial guess
    k0 = omega**2 / G
    
    # For very deep water, use deep water approximation
    if h > 1000:  # Effectively infinite depth
        return k0
    
    # Define function to solve: f(k) = omega^2 - g*k*tanh(k*h) = 0
    def f(k):
        return omega**2 - G * k * np.tanh(k * h)
    
    # Derivative: df/dk = -g*tanh(k*h) - g*k*h*sech^2(k*h)
    def df(k):
        kh = k * h
        return -G * np.tanh(kh) - G * k * h * (1.0 / np.cosh(kh))**2
    
    # Newton-Raphson iteration
    k = k0
    max_iter = 100
    
    for _ in range(max_iter):
        f_val = f(k)
        if abs(f_val) < tol:
            break
        
        df_val = df(k)
        if abs(df_val) < 1e-10:  # Avoid division by zero
            break
        
        k_new = k - f_val / df_val
        
        # Ensure k stays positive
        if k_new <= 0:
            k_new = k0
        
        if abs(k_new - k) < tol:
            k = k_new
            break
        
        k = k_new
    
    return k


def phase_speed(T, h):
    """
    Compute phase speed from period and depth.
    
    Phase speed: c = omega / k
    
    Parameters:
    -----------
    T : float
        Wave period (s)
    h : float
        Water depth (m)
        
    Returns:
    --------
    c : float
        Phase speed (m/s)
    """
    if T <= 0:
        return 0.0
    
    omega = 2.0 * np.pi / T
    k = solve_dispersion(T, h)
    
    if k <= 0:
        return 0.0
    
    return omega / k


def group_speed(T, h):
    """
    Compute group velocity from period and depth.
    
    Group velocity in finite depth:
        cg = 0.5 * c * (1 + (2 * k * h) / sinh(2 * k * h))
    
    Special cases:
    - Deep water: cg = 0.5 * c
    - Shallow water: cg ≈ c ≈ sqrt(g * h)
    
    Parameters:
    -----------
    T : float
        Wave period (s)
    h : float
        Water depth (m)
        
    Returns:
    --------
    cg : float
        Group velocity (m/s)
    """
    if T <= 0:
        return 0.0
    
    c = phase_speed(T, h)
    k = solve_dispersion(T, h)
    
    if k <= 0 or h <= 0:
        return c
    
    kh = k * h
    
    # Deep water approximation
    if kh > 10:
        return 0.5 * c
    
    # Shallow water approximation
    if kh < 0.1:
        return c
    
    # Full expression
    sinh_2kh = np.sinh(2 * kh)
    if sinh_2kh > 0:
        cg = 0.5 * c * (1.0 + (2 * kh) / sinh_2kh)
    else:
        cg = c
    
    return cg


def wave_energy(H, rho=RHO_WATER):
    """
    Compute wave energy per unit horizontal area.
    
    Energy per unit area for linear waves:
        E = (1/8) * rho * g * H^2
    
    For irregular waves, use Hs (significant wave height) for "bulk" energy.
    
    Parameters:
    -----------
    H : float
        Wave height (m)
    rho : float
        Water density (kg/m^3), default 1025
    
    Returns:
    --------
    E : float
        Energy per unit area (J/m^2)
    """
    return (1.0 / 8.0) * rho * G * H**2


def energy_flux(H, T, h, theta=0.0):
    """
    Compute energy flux per unit crest length.
    
    Energy flux: F = E * cg * cos(theta)
    
    When waves propagate over slowly varying depth without breaking or
    dissipation, energy flux along a ray is approximately conserved:
        E1 * cg1 * cos(theta1) ≈ E2 * cg2 * cos(theta2)
    
    where theta is the angle between wave direction and shore-normal.
    
    Parameters:
    -----------
    H : float
        Wave height (m)
    T : float
        Wave period (s)
    h : float
        Water depth (m)
    theta : float
        Angle from shore-normal (radians), default 0 (straight in)
        
    Returns:
    --------
    F : float
        Energy flux (W/m)
    """
    E = wave_energy(H)
    cg = group_speed(T, h)
    return E * cg * np.cos(theta)

