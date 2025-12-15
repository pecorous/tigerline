"""
Data storage module for surf forecast observations and calibration.

Stores:
- Model predictions (offshore conditions, local conditions, predictions)
- Human observations (ratings, tags)
- Historical data for calibration and learning

Storage format: JSON files in data/observations/YYYY-MM-DD.json
"""

import json
import os
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

# Import production config for paths
try:
    from config import production
    DATA_DIR = production.DATA_DIR
    OBSERVATIONS_DIR = production.OBSERVATIONS_DIR
    CALIBRATION_DIR = production.CALIBRATION_DIR
    CLIMATOLOGY_DIR = production.CLIMATOLOGY_DIR
except ImportError:
    # Fallback for local development
    DATA_DIR = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        'data'
    )
    OBSERVATIONS_DIR = os.path.join(DATA_DIR, 'observations')
    CALIBRATION_DIR = os.path.join(DATA_DIR, 'calibration')
    CLIMATOLOGY_DIR = os.path.join(DATA_DIR, 'climatology')


def initialize_storage():
    """Create data directory structure if it doesn't exist."""
    for directory in [DATA_DIR, OBSERVATIONS_DIR, CALIBRATION_DIR, CLIMATOLOGY_DIR]:
        os.makedirs(directory, exist_ok=True)
        logger.debug(f"Ensured directory exists: {directory}")


def _get_observation_file_path(timestamp):
    """
    Get file path for observation based on timestamp.
    
    Parameters:
    -----------
    timestamp : datetime or str
        Timestamp for observation
        
    Returns:
    --------
    file_path : str
        Path to observation file (YYYY-MM-DD.json)
    """
    if isinstance(timestamp, str):
        timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
    
    date_str = timestamp.strftime('%Y-%m-%d')
    filename = f"{date_str}.json"
    return os.path.join(OBSERVATIONS_DIR, filename)


def store_observation(timestamp, offshore_data, local_data, model_prediction, human_rating=None, tags=None):
    """
    Store a single observation.
    
    Parameters:
    -----------
    timestamp : datetime or str
        Observation timestamp
    offshore_data : dict
        Offshore conditions: {'Hs': float, 'Tp': float, 'direction': float}
    local_data : dict
        Local conditions: {'wind_speed': float, 'wind_dir': float, 'tide': float}
    model_prediction : dict
        Model predictions: {'Hb': float, 'theta_break': float, 'breaker_type': str, 'surf_score': float}
    human_rating : float, optional
        Human rating (0-10)
    tags : list of str, optional
        Tags like ['barreling', 'mushy', 'close-out']
        
    Returns:
    --------
    success : bool
        True if stored successfully
    """
    try:
        initialize_storage()
        
        # Convert timestamp to datetime if needed
        if isinstance(timestamp, str):
            obs_time = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        else:
            obs_time = timestamp
        
        # Load existing observations for this day
        file_path = _get_observation_file_path(obs_time)
        observations = []
        
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r') as f:
                    observations = json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"Failed to load existing observations: {e}. Starting fresh.")
                observations = []
        
        # Create observation entry
        observation = {
            'timestamp': obs_time.isoformat(),
            'offshore': offshore_data,
            'local': local_data,
            'model': model_prediction
        }
        
        if human_rating is not None:
            observation['observation'] = {
                'rating': float(human_rating),
                'tags': tags if tags else []
            }
        
        # Add to observations list
        observations.append(observation)
        
        # Save back to file
        with open(file_path, 'w') as f:
            json.dump(observations, f, indent=2)
        
        logger.debug(f"Stored observation for {obs_time.isoformat()}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to store observation: {e}")
        return False


def load_observations(start_date, end_date):
    """
    Load observations between start_date and end_date.
    
    Parameters:
    -----------
    start_date : datetime or str
        Start date (inclusive)
    end_date : datetime or str
        End date (inclusive)
        
    Returns:
    --------
    observations : list of dict
        List of observation dictionaries
    """
    try:
        # Convert to datetime if needed
        if isinstance(start_date, str):
            start_date = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        if isinstance(end_date, str):
            end_date = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
        
        all_observations = []
        
        # Iterate through each day
        current_date = start_date.date()
        end_date_obj = end_date.date()
        
        while current_date <= end_date_obj:
            file_path = os.path.join(OBSERVATIONS_DIR, f"{current_date.strftime('%Y-%m-%d')}.json")
            
            if os.path.exists(file_path):
                try:
                    with open(file_path, 'r') as f:
                        day_observations = json.load(f)
                        
                        # Filter by timestamp
                        for obs in day_observations:
                            obs_time = datetime.fromisoformat(obs['timestamp'].replace('Z', '+00:00'))
                            if start_date <= obs_time <= end_date:
                                all_observations.append(obs)
                except (json.JSONDecodeError, IOError) as e:
                    logger.warning(f"Failed to load observations from {file_path}: {e}")
            
            current_date += timedelta(days=1)
        
        # Sort by timestamp
        all_observations.sort(key=lambda x: x['timestamp'])
        
        return all_observations
        
    except Exception as e:
        logger.error(f"Failed to load observations: {e}")
        return []


def get_observation_count():
    """
    Get total number of stored observations.
    
    Returns:
    --------
    count : int
        Total number of observations
    """
    try:
        count = 0
        if not os.path.exists(OBSERVATIONS_DIR):
            return 0
        
        for filename in os.listdir(OBSERVATIONS_DIR):
            if filename.endswith('.json'):
                file_path = os.path.join(OBSERVATIONS_DIR, filename)
                try:
                    with open(file_path, 'r') as f:
                        observations = json.load(f)
                        count += len(observations)
                except (json.JSONDecodeError, IOError):
                    continue
        
        return count
        
    except Exception as e:
        logger.error(f"Failed to count observations: {e}")
        return 0


def get_observations_with_ratings():
    """
    Get all observations that have human ratings.
    
    Returns:
    --------
    observations : list of dict
        List of observations with 'observation' key containing rating
    """
    try:
        all_observations = []
        
        if not os.path.exists(OBSERVATIONS_DIR):
            return []
        
        # Load all observation files
        for filename in os.listdir(OBSERVATIONS_DIR):
            if filename.endswith('.json'):
                file_path = os.path.join(OBSERVATIONS_DIR, filename)
                try:
                    with open(file_path, 'r') as f:
                        observations = json.load(f)
                        for obs in observations:
                            if 'observation' in obs and 'rating' in obs['observation']:
                                all_observations.append(obs)
                except (json.JSONDecodeError, IOError):
                    continue
        
        # Sort by timestamp
        all_observations.sort(key=lambda x: x['timestamp'])
        
        return all_observations
        
    except Exception as e:
        logger.error(f"Failed to get observations with ratings: {e}")
        return []

