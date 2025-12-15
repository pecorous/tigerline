"""
Tide prediction data fetching module.

Fetches tide predictions from NOAA CO-OPS API for Belmar, NJ area.

Data Source: NOAA CO-OPS (Center for Operational Oceanographic Products and Services)
- API: https://api.tidesandcurrents.noaa.gov/api/prod/datagetter
- Station: 8531680 (Sandy Hook, NJ)
- Citation: NOAA Tides & Currents. Station 8531680. https://tidesandcurrents.noaa.gov/
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

# FAKE DATA FALLBACK: Path to fake tide data file
FAKE_DATA_PATH = os.path.join(PROJECT_ROOT, 'config', 'fake_data', 'fake_tide_data.json')

# Belmar coordinates (approximate)
BELMAR_LAT = 40.18
BELMAR_LON = -74.02

# Nearest NOAA CO-OPS station to Belmar (Sandy Hook or similar)
# FAKE DATA: This station ID needs verification
TIDE_STATION_ID = '8531680'  # Sandy Hook, NJ (example - verify actual station)


def get_tide_predictions(location='Belmar', days=3):
    """
    Fetch tide predictions from NOAA CO-OPS API.
    
    FAKE DATA FALLBACK: If API fails, loads from config/fake_data/fake_tide_data.json
    
    Parameters:
    -----------
    location : str
        Location name (for reference)
    days : int
        Number of days of predictions to fetch
        
    Returns:
    --------
    dict with keys:
        times : list
            List of datetime objects
        levels : list
            List of tide levels (m) relative to mean sea level
        station_id : str
            Tide station ID used
        timestamp : datetime
            Data fetch timestamp
        source : str
            'api' or 'fake_data'
    """
    try:
        # NOAA CO-OPS API endpoint for predictions
        # Format: https://api.tidesandcurrents.noaa.gov/api/prod/datagetter?
        # product=predictions&application=NOS.COOPS.TAC.WL&begin_date=...&end_date=...
        # &datum=MLLW&station=8531680&time_zone=gmt&units=metric&interval=h&format=json
        
        end_date = datetime.now() + timedelta(days=days)
        begin_date = datetime.now()
        
        url = (
            'https://api.tidesandcurrents.noaa.gov/api/prod/datagetter?'
            f'product=predictions&application=NOS.COOPS.TAC.WL&'
            f'begin_date={begin_date.strftime("%Y%m%d")}&'
            f'end_date={end_date.strftime("%Y%m%d")}&'
            f'datum=MLLW&station={TIDE_STATION_ID}&'
            'time_zone=gmt&units=metric&interval=h&format=json'
        )
        
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        # Parse CO-OPS JSON response
        if 'predictions' in data:
            times = []
            levels = []
            for pred in data['predictions']:
                times.append(datetime.strptime(pred['t'], '%Y-%m-%d %H:%M'))
                levels.append(float(pred['v']))
            
            logger.info(f"Successfully fetched {len(times)} tide predictions from CO-OPS")
            
            return {
                'times': times,
                'levels': levels,
                'station_id': TIDE_STATION_ID,
                'timestamp': datetime.now(),
                'source': 'api'
            }
        else:
            raise ValueError("Unexpected API response format")
            
    except Exception as e:
        logger.warning(f"Failed to fetch tide predictions from API: {e}. Using fake data.")
        return _load_fake_tide_data(days)


def _load_fake_tide_data(days=3):
    """
    Load fake tide data from file or generate synthetic data.
    
    FAKE DATA: Generates semi-realistic tide predictions with ~12.5 hour period
    """
    try:
        if os.path.exists(FAKE_DATA_PATH):
            with open(FAKE_DATA_PATH, 'r') as f:
                data = json.load(f)
                if 'tides' in data:
                    tides = data['tides']
                    times = [datetime.fromisoformat(t) for t in tides.get('times', [])]
                    levels = tides.get('levels', [])
                    
                    return {
                        'times': times,
                        'levels': levels,
                        'station_id': TIDE_STATION_ID,
                        'timestamp': datetime.now(),
                        'source': 'fake_data'
                    }
    except Exception as e:
        logger.warning(f"Failed to load fake tide data from file: {e}")
    
    # Generate synthetic tide data (semi-diurnal with ~12.5 hour period)
    import numpy as np
    now = datetime.now()
    times = []
    levels = []
    
    n_hours = days * 24
    for i in range(n_hours):
        t = now + timedelta(hours=i)
        times.append(t)
        # Simple sine wave with semi-diurnal period (~12.5 hours)
        hours_since_start = i
        level = 0.5 * np.sin(2 * np.pi * hours_since_start / 12.5) + 0.2 * np.sin(2 * np.pi * hours_since_start / 25.0)
        levels.append(float(level))
    
    return {
        'times': times,
        'levels': levels,
        'station_id': TIDE_STATION_ID,
        'timestamp': datetime.now(),
        'source': 'fake_data'
    }

