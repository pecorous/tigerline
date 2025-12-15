"""
Wind data fetching module.

Fetches wind data from OpenWeatherMap API for Belmar, NJ.

Data Source: OpenWeatherMap
- API: https://api.openweathermap.org/data/2.5/forecast
- Plan: Free Plan (3-hour forecast, 5 days)
- Citation: OpenWeatherMap. Weather Forecast API. https://openweathermap.org/api
- License: OpenWeatherMap Free Plan (Terms: https://openweathermap.org/terms)

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

# FAKE DATA FALLBACK: Path to fake wind data file
FAKE_DATA_PATH = os.path.join(PROJECT_ROOT, 'config', 'fake_data', 'fake_wind_data.json')

# Belmar coordinates
BELMAR_LAT = 40.18
BELMAR_LON = -74.02

# OpenWeatherMap API key
OWM_API_KEY = '8fc8c57e1c3819d16ee2209ce298e117'


def get_wind_data(lat=BELMAR_LAT, lon=BELMAR_LON, days=3):
    """
    Fetch wind data from weather API.
    
    FAKE DATA FALLBACK: If API fails or key not set, loads from config/fake_data/fake_wind_data.json
    
    Parameters:
    -----------
    lat : float
        Latitude
    lon : float
        Longitude
    days : int
        Number of days of forecast to fetch
        
    Returns:
    --------
    dict with keys:
        times : list
            List of datetime objects
        speeds : list
            Wind speeds (m/s)
        directions : list
            Wind directions (degrees, coming-from)
        timestamp : datetime
            Data fetch timestamp
        source : str
            'api' or 'fake_data'
    """
    try:
        # OpenWeatherMap API endpoint
        url = (
            'https://api.openweathermap.org/data/2.5/forecast?'
            f'lat={lat}&lon={lon}&'
            f'appid={OWM_API_KEY}&'
            'units=metric'
        )
        
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        # Parse OpenWeatherMap response
        times = []
        speeds = []
        directions = []
        temps_c = []
        temps_f = []
        feels_like_c = []
        feels_like_f = []
        
        if 'list' in data:
            for item in data['list']:
                dt = datetime.fromtimestamp(item['dt'])
                wind = item.get('wind', {})
                main = item.get('main', {})
                
                times.append(dt)
                speeds.append(wind.get('speed', 0.0))  # m/s
                directions.append(wind.get('deg', 0.0))  # degrees
                
                # Temperature data (API already returns Celsius with units=metric)
                temp_c = main.get('temp', 15.0)  # Already in Celsius
                temp_f = temp_c * 9/5 + 32
                temps_c.append(temp_c)
                temps_f.append(temp_f)
                
                # Feels like temperature (also in Celsius)
                feels_c = main.get('feels_like', temp_c)
                feels_f = feels_c * 9/5 + 32
                feels_like_c.append(feels_c)
                feels_like_f.append(feels_f)
            
            logger.info(f"Successfully fetched {len(times)} wind data points from OpenWeatherMap")
            
            return {
                'times': times,
                'speeds': speeds,
                'directions': directions,
                'temperature_c': temps_c,
                'temperature_f': temps_f,
                'feels_like_c': feels_like_c,
                'feels_like_f': feels_like_f,
                'timestamp': datetime.now(),
                'source': 'api'
            }
        else:
            raise ValueError("Unexpected API response format")
            
    except Exception as e:
        logger.warning(f"Failed to fetch wind data from API: {e}. Using fake data.")
        return _load_fake_wind_data(days)


def _load_fake_wind_data(days=3):
    """
    Load fake wind data from file or generate synthetic data.
    
    FAKE DATA: Generates realistic wind patterns
    """
    try:
        if os.path.exists(FAKE_DATA_PATH):
            with open(FAKE_DATA_PATH, 'r') as f:
                data = json.load(f)
                if 'wind' in data:
                    wind = data['wind']
                    times = [datetime.fromisoformat(t) for t in wind.get('times', [])]
                    speeds = wind.get('speeds', [])
                    directions = wind.get('directions', [])
                    
                    return {
                        'times': times,
                        'speeds': speeds,
                        'directions': directions,
                        'timestamp': datetime.now(),
                        'source': 'fake_data'
                    }
    except Exception as e:
        logger.warning(f"Failed to load fake wind data from file: {e}")
    
    # Generate synthetic wind data
    import numpy as np
    now = datetime.now()
    times = []
    speeds = []
    directions = []
    temps_c = []
    temps_f = []
    feels_like_c = []
    feels_like_f = []
    
    n_hours = days * 24
    for i in range(n_hours):
        t = now + timedelta(hours=i)
        times.append(t)
        # Varying wind speed (3-8 m/s typical)
        speed = 5.0 + 2.0 * np.sin(2 * np.pi * i / 24.0) + 0.5 * np.random.randn()
        speeds.append(max(0.0, float(speed)))
        # Varying wind direction (onshore/offshore variations)
        direction = 180.0 + 30.0 * np.sin(2 * np.pi * i / 12.0) + 10.0 * np.random.randn()
        directions.append(float(direction % 360))
        # Temperature (varies with time of day)
        temp_c = 15.0 + 5.0 * np.sin(2 * np.pi * (i - 6) / 24.0)  # Peak afternoon
        temps_c.append(float(temp_c))
        temps_f.append(float(temp_c * 9/5 + 32))
        feels_like_c.append(float(temp_c - 2.0))
        feels_like_f.append(float((temp_c - 2.0) * 9/5 + 32))
    
    return {
        'times': times,
        'speeds': speeds,
        'directions': directions,
        'temperature_c': temps_c,
        'temperature_f': temps_f,
        'feels_like_c': feels_like_c,
        'feels_like_f': feels_like_f,
        'timestamp': datetime.now(),
        'source': 'fake_data'
    }

