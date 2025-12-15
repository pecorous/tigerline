"""
Wave statistics and spectral analysis module.

Implements spectral moments, significant wave height calculations, and Rayleigh
wave height distribution following Ocean Waves course material.

The sea surface elevation eta(t) at a fixed point is modeled as a superposition
of many linear sinusoidal components with random phase:

    eta(t) = sum over n [ a_n * cos(omega_n * t + phi_n) ]

where:
    a_n are amplitudes
    omega_n are angular frequencies
    phi_n are random phases

Under this linear random-phase model, eta(t) is approximately a Gaussian
(normal) process with mean close to 0.
"""

import numpy as np


def compute_mean_std(eta_t):
    """
    Compute mean and standard deviation from time series eta(t).
    
    Parameters:
    -----------
    eta_t : array-like
        Sea surface elevation time series
        
    Returns:
    --------
    mu : float
        Mean of eta(t)
    sigma : float
        Standard deviation of eta(t)
    """
    eta_t = np.asarray(eta_t)
    mu = np.mean(eta_t)
    sigma = np.std(eta_t, ddof=0)  # Population std dev
    return mu, sigma


def compute_spectral_moments(frequencies, S):
    """
    Compute spectral moments m0, m1, and m_1 from energy spectrum S(f).
    
    Spectral moments are defined as:
        m0 = integral over all f [ S(f) df ]
        m1 = integral over all f [ f * S(f) df ]
        m_1 = integral over all f [ S(f) / f df ]
    
    Parameters:
    -----------
    frequencies : array-like
        Frequency array f (Hz)
    S : array-like
        Spectral density S(f) (m^2/Hz)
        
    Returns:
    --------
    m0 : float
        Zeroth moment (variance)
    m1 : float
        First moment
    m_1 : float
        Negative first moment
    """
    f = np.asarray(frequencies)
    S = np.asarray(S)
    
    # Integrate using trapezoidal rule
    m0 = np.trapz(S, f)
    m1 = np.trapz(f * S, f)
    
    # For m_1, avoid division by zero at f=0
    # Use S/f where f > 0, otherwise 0
    mask = f > 0
    if np.any(mask):
        m_1 = np.trapz(np.where(mask, S / f, 0), f)
    else:
        m_1 = 0.0
    
    return m0, m1, m_1


def significant_wave_height_spectral(m0):
    """
    Compute significant wave height from spectral moment m0.
    
    For a Gaussian sea surface, Hs = 4 * sqrt(m0)
    
    Parameters:
    -----------
    m0 : float
        Zeroth spectral moment (variance)
        
    Returns:
    --------
    Hs : float
        Significant wave height (m)
    """
    if m0 < 0:
        return 0.0
    return 4.0 * np.sqrt(m0)


def significant_wave_height_time(eta_t):
    """
    Compute significant wave height from time series eta(t).
    
    For a sufficiently long time series:
        sigma = standard deviation of eta(t)
        Hs = 4 * sigma
    
    This should match Hs from the spectrum reasonably well.
    
    Parameters:
    -----------
    eta_t : array-like
        Sea surface elevation time series
        
    Returns:
    --------
    Hs : float
        Significant wave height (m)
    """
    _, sigma = compute_mean_std(eta_t)
    return 4.0 * sigma


def mean_periods(m0, m1, m_1):
    """
    Compute mean periods from spectral moments.
    
    Tm01 = m0 / m1  (mean period based on m0 and m1)
    Tm_10 = m_1 / m0  (mean period based on m0 and m_1)
    
    Parameters:
    -----------
    m0 : float
        Zeroth moment
    m1 : float
        First moment
    m_1 : float
        Negative first moment
        
    Returns:
    --------
    Tm01 : float
        Mean period (s)
    Tm_10 : float
        Mean period (s)
    """
    if m1 > 0:
        Tm01 = m0 / m1
    else:
        Tm01 = 0.0
    
    if m0 > 0:
        Tm_10 = m_1 / m0
    else:
        Tm_10 = 0.0
    
    return Tm01, Tm_10


def peak_period(frequencies, S):
    """
    Compute peak period from energy spectrum.
    
    Tp = 1 / fp, where fp is the frequency at which S(f) is maximum.
    
    Parameters:
    -----------
    frequencies : array-like
        Frequency array f (Hz)
    S : array-like
        Spectral density S(f)
        
    Returns:
    --------
    Tp : float
        Peak period (s)
    fp : float
        Peak frequency (Hz)
    """
    f = np.asarray(frequencies)
    S = np.asarray(S)
    
    if len(f) == 0 or np.all(S == 0):
        return 0.0, 0.0
    
    idx_max = np.argmax(S)
    fp = f[idx_max]
    
    if fp > 0:
        Tp = 1.0 / fp
    else:
        Tp = 0.0
    
    return Tp, fp


def H_rms_from_sigma(sigma):
    """
    Compute root-mean-square wave height from standard deviation.
    
    For a Gaussian process, H_rms^2 = 8 * sigma^2
    Therefore: H_rms = sqrt(8) * sigma
    
    Parameters:
    -----------
    sigma : float
        Standard deviation of sea surface elevation
        
    Returns:
    --------
    H_rms : float
        Root-mean-square wave height (m)
    """
    return np.sqrt(8.0) * sigma


def rayleigh_distribution(H, H_rms):
    """
    Compute Rayleigh distribution for wave heights.
    
    For narrow-band Gaussian seas, individual crest-to-trough wave heights
    H follow approximately a Rayleigh distribution.
    
    Probability density:
        p(H) = (H / H_rms^2) * exp( - (H^2 / (2 * H_rms^2)) )
    
    Exceedance probability:
        P(H > H0) = exp( - (H0^2 / (2 * H_rms^2)) )
    
    Parameters:
    -----------
    H : array-like or float
        Wave height(s) (m)
    H_rms : float
        Root-mean-square wave height (m)
        
    Returns:
    --------
    pdf : array-like or float
        Probability density p(H)
    exceedance : array-like or float
        Exceedance probability P(H > H0)
    """
    H = np.asarray(H)
    H_rms = np.asarray(H_rms)
    
    if H_rms <= 0:
        return np.zeros_like(H), np.ones_like(H)
    
    # Avoid division by zero
    H_safe = np.maximum(H, 0)
    
    # Probability density
    pdf = (H_safe / (H_rms**2)) * np.exp(-(H_safe**2) / (2 * H_rms**2))
    
    # Exceedance probability
    exceedance = np.exp(-(H_safe**2) / (2 * H_rms**2))
    
    return pdf, exceedance

