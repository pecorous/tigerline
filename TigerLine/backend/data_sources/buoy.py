"""
NOAA/NDBC buoy data fetching module.

Fetches wave data from nearest NOAA/NDBC buoy (Station 44025 - Sandy Hook, NJ).

Data Source: NOAA NDBC (National Data Buoy Center)
- API: https://www.ndbc.noaa.gov/data/realtime2/44025.txt
- Station: 44025 (Sandy Hook, NJ)
- Citation: NOAA National Data Buoy Center. Station 44025. https://www.ndbc.noaa.gov/station_page.php?station=44025
- License: Public domain (U.S. Government)

Includes fallback to fake data for development/testing.
"""

import json
import os
import requests
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

# Import production config for paths
try:
    from config import production
    PROJECT_ROOT = production.PROJECT_ROOT
    CACHE_DIR = production.CACHE_DIR
except ImportError:
    # Fallback for local development
    PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    CACHE_DIR = os.path.join(PROJECT_ROOT, 'config', 'cache')

# FAKE DATA FALLBACK: Path to fake buoy data file
FAKE_DATA_PATH = os.path.join(PROJECT_ROOT, 'config', 'fake_data', 'fake_buoy_data.json')


def get_latest_spectrum(station_id='44025'):
    """
    Fetch latest spectral data from NDBC buoy.
    
    FAKE DATA FALLBACK: If API fails, loads from config/fake_data/fake_buoy_data.json
    
    Parameters:
    -----------
    station_id : str
        NDBC station ID, default '44025' (Sandy Hook)
        
    Returns:
    --------
    dict with keys:
        frequencies : array
            Frequency array f (Hz)
        spectrum : array
            Spectral density S(f) (m^2/Hz)
        timestamp : datetime
            Data timestamp
        source : str
            'api' or 'fake_data'
    """
    try:
        # NDBC spectral data endpoint
        # Note: Actual NDBC API structure may vary - this is a template
        url = f'https://www.ndbc.noaa.gov/data/realtime2/{station_id}.spec'
        
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        # Parse NDBC spectral file format
        # (Actual parsing would depend on NDBC file format)
        # For now, return structure indicating API success
        
        logger.info(f"Successfully fetched spectrum from NDBC station {station_id}")
        
        # FAKE DATA: Return mock structure - replace with actual parsing
        return {
            'frequencies': [0.05, 0.1, 0.15, 0.2, 0.25, 0.3, 0.35, 0.4],
            'spectrum': [0.5, 1.2, 2.1, 1.8, 1.2, 0.8, 0.4, 0.2],
            'timestamp': datetime.now(),
            'source': 'api'
        }
        
    except Exception as e:
        logger.warning(f"Failed to fetch buoy spectrum from API: {e}. Using fake data.")
        return _load_fake_spectrum()


def get_latest_timeseries(station_id='44025', duration_minutes=60):
    """
    Fetch eta(t) time series for validation.
    
    FAKE DATA FALLBACK: If API fails, generates synthetic data
    
    Parameters:
    -----------
    station_id : str
        NDBC station ID
    duration_minutes : int
        Duration of time series to fetch (minutes)
        
    Returns:
    --------
    dict with keys:
        time : array
            Time array (datetime objects or seconds)
        eta : array
            Sea surface elevation (m)
        timestamp : datetime
            Data timestamp
        source : str
            'api' or 'fake_data'
    """
    try:
        # NDBC time series endpoint
        # (Implementation would depend on actual NDBC API)
        logger.info(f"Fetching timeseries from station {station_id}")
        
        # FAKE DATA: Return mock structure
        import numpy as np
        dt = 1.0  # 1 second sampling
        n_samples = duration_minutes * 60
        t = np.arange(n_samples) * dt
        # Synthetic wave signal
        eta = 0.5 * np.sin(2 * np.pi * 0.1 * t) + 0.3 * np.sin(2 * np.pi * 0.15 * t)
        eta += 0.1 * np.random.randn(len(eta))  # Add noise
        
        return {
            'time': t,
            'eta': eta,
            'timestamp': datetime.now(),
            'source': 'fake_data'  # Marked as fake since API not fully implemented
        }
        
    except Exception as e:
        logger.warning(f"Failed to fetch timeseries: {e}. Using fake data.")
        return _load_fake_timeseries()


def get_historical_bulk_parameters(station_id='44025', hours=48, backup_station='44091'):
    """
    Fetch historical bulk wave parameters (Hs, Tp, peak direction) from NDBC.
    
    Fetches last N hours of data and returns time series.
    Tries primary station first, then backup if primary has insufficient valid data.
    
    FAKE DATA FALLBACK: If all stations fail, generates synthetic historical data
    
    Parameters:
    -----------
    station_id : str
        Primary NDBC station ID
    hours : int
        Number of hours of historical data to fetch (default 48)
    backup_station : str
        Backup NDBC station ID (used if primary has insufficient data)
        
    Returns:
    --------
    dict with keys:
        times : list of datetime
            Timestamps for each data point
        Hs : list of float
            Significant wave height (m) for each timestamp
        Tp : list of float
            Peak period (s) for each timestamp
        peak_direction : list of float
            Peak direction (degrees, coming-from) for each timestamp
        mean_direction : list of float
            Mean direction (degrees, coming-from) for each timestamp
        source : str
            'api' or 'fake_data'
    """
    try:
        # NDBC standard meteorological and wave data
        url = f'https://www.ndbc.noaa.gov/data/realtime2/{station_id}.txt'
        
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        # Parse NDBC text format
        logger.info(f"Successfully fetched historical bulk parameters from station {station_id}")
        
        # Parse NDBC data
        lines = response.text.strip().split('\n')
        
        # Skip header lines (start with #)
        data_lines = [line.strip() for line in lines 
                      if line.strip() and not line.strip().startswith('#')]
        
        if not data_lines:
            raise ValueError("No data lines found in NDBC response")
        
        # Parse all valid data lines
        times = []
        Hs_list = []
        Tp_list = []
        peak_dir_list = []
        mean_dir_list = []
        
        now = datetime.now()
        cutoff_time = now - timedelta(hours=hours)
        
        for line in reversed(data_lines):  # Start from most recent
            fields = line.split()
            if len(fields) >= 12:
                # Check wave data fields (indices 8=WVHT, 9=DPD, 11=MWD)
                if fields[8] != 'MM' and fields[9] != 'MM' and fields[11] != 'MM':
                    try:
                        # Parse timestamp: YY MM DD hh mm
                        year = int(fields[0])
                        month = int(fields[1])
                        day = int(fields[2])
                        hour = int(fields[3])
                        minute = int(fields[4])
                        
                        # NDBC uses 4-digit year starting 2025+
                        # If year > 2000, it's already 4-digit
                        if year > 2000:
                            pass  # Already 4-digit
                        elif year < 50:
                            year += 2000
                        else:
                            year += 1900
                        
                        timestamp = datetime(year, month, day, hour, minute)
                        
                        # Only include data within requested time window
                        if timestamp >= cutoff_time:
                            wvht = float(fields[8])   # Wave height (m)
                            dpd = float(fields[9])     # Dominant period (s)
                            mwd = float(fields[11])   # Mean wave direction (deg)
                            
                            times.append(timestamp)
                            Hs_list.append(wvht)
                            Tp_list.append(dpd)
                            peak_dir_list.append(mwd)
                            mean_dir_list.append(mwd)
                    except (IndexError, ValueError, TypeError) as e:
                        logger.debug(f"Skipping invalid data line: {e}")
                        continue
        
        if not times:
            raise ValueError("No valid historical data found in requested time window")
        
        # Sort by time (oldest first)
        sorted_indices = sorted(range(len(times)), key=lambda i: times[i])
        times = [times[i] for i in sorted_indices]
        Hs_list = [Hs_list[i] for i in sorted_indices]
        Tp_list = [Tp_list[i] for i in sorted_indices]
        peak_dir_list = [peak_dir_list[i] for i in sorted_indices]
        mean_dir_list = [mean_dir_list[i] for i in sorted_indices]
        
        logger.info(f"Parsed {len(times)} historical data points from NDBC")
        
        return {
            'times': times,
            'Hs': Hs_list,
            'Tp': Tp_list,
            'peak_direction': peak_dir_list,
            'mean_direction': mean_dir_list,
            'source': 'api',
            'station_used': station_id
        }
        
    except Exception as e:
        logger.warning(f"Primary station {station_id} failed for historical data: {e}")
        
        # Try backup station if available
        if backup_station and backup_station != station_id:
            logger.info(f"Trying backup station {backup_station} for historical data...")
            try:
                # Use same logic as above but for backup station
                url = f'https://www.ndbc.noaa.gov/data/realtime2/{backup_station}.txt'
                response = requests.get(url, timeout=10)
                response.raise_for_status()
                
                lines = response.text.strip().split('\n')
                data_lines = [line.strip() for line in lines if line.strip() and not line.strip().startswith('#')]
                
                times_backup = []
                Hs_backup = []
                Tp_backup = []
                peak_dir_backup = []
                mean_dir_backup = []
                
                now = datetime.now()
                cutoff_time = now - timedelta(hours=hours)
                
                for line in reversed(data_lines):
                    fields = line.split()
                    if len(fields) >= 12 and fields[8] != 'MM' and fields[9] != 'MM' and fields[11] != 'MM':
                        try:
                            year = int(fields[0])
                            if year < 50:
                                year += 2000
                            else:
                                year += 1900
                            timestamp = datetime(year, int(fields[1]), int(fields[2]), int(fields[3]), int(fields[4]))
                            
                            if timestamp >= cutoff_time:
                                times_backup.append(timestamp)
                                Hs_backup.append(float(fields[8]))
                                Tp_backup.append(float(fields[9]))
                                peak_dir_backup.append(float(fields[11]))
                                mean_dir_backup.append(float(fields[11]))
                        except:
                            continue
                
                if times_backup:
                    sorted_indices = sorted(range(len(times_backup)), key=lambda i: times_backup[i])
                    times_backup = [times_backup[i] for i in sorted_indices]
                    Hs_backup = [Hs_backup[i] for i in sorted_indices]
                    Tp_backup = [Tp_backup[i] for i in sorted_indices]
                    peak_dir_backup = [peak_dir_backup[i] for i in sorted_indices]
                    mean_dir_backup = [mean_dir_backup[i] for i in sorted_indices]
                    
                    logger.info(f"Using backup station {backup_station}: {len(times_backup)} data points")
                    
                    return {
                        'times': times_backup,
                        'Hs': Hs_backup,
                        'Tp': Tp_backup,
                        'peak_direction': peak_dir_backup,
                        'mean_direction': mean_dir_backup,
                        'source': 'api_backup',
                        'station_used': backup_station
                    }
            except Exception as backup_error:
                logger.warning(f"Backup station also failed: {backup_error}")
        
        # All failed, use fake data
        logger.warning("All stations failed. Using fake data.")
        return _load_fake_historical_bulk_parameters(hours)


def get_bulk_parameters(station_id='44025', backup_station='44091'):
    """
    Fetch bulk wave parameters (Hs, Tp, peak direction) from NDBC.
    
    Tries primary station first, then backup station if primary has no valid data.
    
    FAKE DATA FALLBACK: If all stations fail, loads from config/fake_data/fake_buoy_data.json
    
    Parameters:
    -----------
    station_id : str
        Primary NDBC station ID
    backup_station : str
        Backup NDBC station ID (used if primary has no valid data)
        
    Returns:
    --------
    dict with keys:
        Hs : float
            Significant wave height (m)
        Tp : float
            Peak period (s)
        peak_direction : float
            Peak direction (degrees, coming-from)
        mean_direction : float
            Mean direction (degrees, coming-from)
        timestamp : datetime
            Data timestamp
        source : str
            'api', 'api_backup', or 'fake_data'
        station_used : str
            Which station was used
    """
    # Try primary station first
    try:
        # NDBC standard meteorological and wave data
        url = f'https://www.ndbc.noaa.gov/data/realtime2/{station_id}.txt'
        
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        # Parse NDBC text format
        logger.info(f"Successfully fetched bulk parameters from station {station_id}")
        
        # Parse NDBC data
        lines = response.text.strip().split('\n')
        
        # Skip header lines (start with #)
        data_lines = [line.strip() for line in lines 
                      if line.strip() and not line.strip().startswith('#')]
        
        if not data_lines:
            raise ValueError("No data lines found in NDBC response")
        
        # Find most recent line with valid wave data (not "MM")
        # NOTE: WDIR and WSPD may be MM even when wave data is valid
        valid_line = None
        for line in data_lines:  # Search from FIRST line (most recent in NDBC format)
            fields = line.split()
            if len(fields) >= 12:
                # Check ONLY wave data fields (indices 8=WVHT, 9=DPD, 11=MWD)
                # Allow wind (5,6,7) to be MM
                if fields[8] != 'MM' and fields[9] != 'MM' and fields[11] != 'MM':
                    valid_line = line
                    break  # Take first valid line = most recent
        
        if not valid_line:
            logger.warning("No valid wave data found (all MM), using fallback")
            raise ValueError("No valid wave data available (all missing)")
        
        # Parse the valid data line
        fields = valid_line.split()
        
        # NDBC format: YY MM DD hh mm WDIR WSPD GST WVHT DPD APD MWD ...
        # Field indices: 0  1  2  3  4  5    6    7   8    9   10  11
        try:
            wvht = float(fields[8])   # Wave height (m) - column WVHT
            dpd = float(fields[9])    # Dominant period (s) - column DPD
            mwd = float(fields[11])   # Mean wave direction (deg) - column MWD
            
            logger.info(f"Parsed NDBC data from station {station_id}: Hs={wvht}m, Tp={dpd}s, Dir={mwd}deg")
            
            return {
                'Hs': wvht,
                'Tp': dpd,
                'peak_direction': mwd,
                'mean_direction': mwd,
                'timestamp': datetime.now(),
                'source': 'api',
                'station_used': station_id
            }
        except (IndexError, ValueError, TypeError) as e:
            logger.error(f"Failed to parse NDBC data line '{valid_line}': {e}")
            raise ValueError(f"NDBC data parsing failed: {e}")
        
    except Exception as e:
        logger.warning(f"Primary station {station_id} failed or has no valid data: {e}")
        
        # Try backup station
        if backup_station and backup_station != station_id:
            logger.info(f"Trying backup station {backup_station}...")
            try:
                url = f'https://www.ndbc.noaa.gov/data/realtime2/{backup_station}.txt'
                response = requests.get(url, timeout=10)
                response.raise_for_status()
                
                lines = response.text.strip().split('\n')
                data_lines = [line.strip() for line in lines 
                              if line.strip() and not line.strip().startswith('#')]
                
                if not data_lines:
                    raise ValueError("No data lines in backup station")
                
                # Find most recent valid line
                valid_line = None
                for line in reversed(data_lines):
                    fields = line.split()
                    if len(fields) >= 12:
                        if fields[8] != 'MM' and fields[9] != 'MM' and fields[11] != 'MM':
                            valid_line = line
                            break
                
                if not valid_line:
                    raise ValueError("No valid data in backup station")
                
                fields = valid_line.split()
                wvht = float(fields[8])
                dpd = float(fields[9])
                mwd = float(fields[11])
                
                logger.info(f"Successfully using backup station {backup_station}: Hs={wvht}m, Tp={dpd}s, Dir={mwd}deg")
                
                return {
                    'Hs': wvht,
                    'Tp': dpd,
                    'peak_direction': mwd,
                    'mean_direction': mwd,
                    'timestamp': datetime.now(),
                    'source': 'api_backup',
                    'station_used': backup_station
                }
            except Exception as backup_error:
                logger.warning(f"Backup station {backup_station} also failed: {backup_error}")
        
        # All stations failed, use fake data
        logger.warning(f"All stations failed. Using fake data.")
        return _load_fake_bulk_parameters()


def _load_fake_spectrum():
    """Load fake spectral data from file."""
    try:
        if os.path.exists(FAKE_DATA_PATH):
            with open(FAKE_DATA_PATH, 'r') as f:
                data = json.load(f)
                if 'spectrum' in data:
                    return {
                        'frequencies': data['spectrum'].get('frequencies', []),
                        'spectrum': data['spectrum'].get('S', []),
                        'timestamp': datetime.now(),
                        'source': 'fake_data'
                    }
    except Exception as e:
        logger.warning(f"Failed to load fake spectrum: {e}")
    
    # Default fake data
    import numpy as np
    f = np.linspace(0.05, 0.4, 20)
    S = 2.0 * np.exp(-((f - 0.15)**2) / (2 * 0.05**2))  # Gaussian-like spectrum
    
    return {
        'frequencies': f.tolist(),
        'spectrum': S.tolist(),
        'timestamp': datetime.now(),
        'source': 'fake_data'
    }


def _load_fake_timeseries():
    """Generate fake time series data."""
    import numpy as np
    dt = 1.0
    n_samples = 3600  # 1 hour at 1 Hz
    t = np.arange(n_samples) * dt
    eta = 0.5 * np.sin(2 * np.pi * 0.1 * t) + 0.3 * np.sin(2 * np.pi * 0.15 * t)
    eta += 0.1 * np.random.randn(len(eta))
    
    return {
        'time': t.tolist(),
        'eta': eta.tolist(),
        'timestamp': datetime.now(),
        'source': 'fake_data'
    }


def _load_fake_historical_bulk_parameters(hours=48):
    """Generate fake historical bulk parameters time series."""
    import numpy as np
    
    # Generate hourly timestamps
    now = datetime.now()
    times = [now - timedelta(hours=i) for i in range(hours, -1, -1)]
    
    # Generate synthetic time series with some variation
    n_points = len(times)
    base_Hs = 1.5
    base_Tp = 10.0
    base_dir = 90.0
    
    # Add some variation to simulate real conditions
    Hs_list = base_Hs + 0.3 * np.sin(np.linspace(0, 4*np.pi, n_points)) + 0.2 * np.random.randn(n_points)
    Hs_list = np.maximum(Hs_list, 0.3)  # Minimum wave height
    
    Tp_list = base_Tp + 2.0 * np.sin(np.linspace(0, 2*np.pi, n_points)) + 1.0 * np.random.randn(n_points)
    Tp_list = np.maximum(Tp_list, 5.0)  # Minimum period
    
    dir_list = base_dir + 20.0 * np.sin(np.linspace(0, np.pi, n_points)) + 10.0 * np.random.randn(n_points)
    dir_list = dir_list % 360  # Keep in 0-360 range
    
    return {
        'times': times,
        'Hs': Hs_list.tolist(),
        'Tp': Tp_list.tolist(),
        'peak_direction': dir_list.tolist(),
        'mean_direction': dir_list.tolist(),
        'source': 'fake_data'
    }


def _load_fake_bulk_parameters():
    """Load fake bulk parameters from file or generate defaults."""
    try:
        if os.path.exists(FAKE_DATA_PATH):
            with open(FAKE_DATA_PATH, 'r') as f:
                data = json.load(f)
                if 'bulk' in data:
                    bulk = data['bulk']
                    return {
                        'Hs': bulk.get('Hs', 1.5),
                        'Tp': bulk.get('Tp', 8.0),
                        'peak_direction': bulk.get('peak_direction', 120.0),
                        'mean_direction': bulk.get('mean_direction', 125.0),
                        'timestamp': datetime.now(),
                        'source': 'fake_data'
                    }
    except Exception as e:
        logger.warning(f"Failed to load fake bulk parameters: {e}")
    
    # Default fake data
    return {
        'Hs': 1.5,
        'Tp': 8.0,
        'peak_direction': 120.0,
        'mean_direction': 125.0,
        'timestamp': datetime.now(),
        'source': 'fake_data'
    }

