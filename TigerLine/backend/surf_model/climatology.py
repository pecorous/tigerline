"""
Climatology module for seasonal surf patterns.

Implements:
- Monthly statistics calculation
- Seasonal expectations
- Climatology-based adjustments

Based on Section 4.3 of the Belmar specification.
"""

import json
import os
import numpy as np
from datetime import datetime
from collections import defaultdict
import logging
from . import storage

logger = logging.getLogger(__name__)

# Import production config for paths
try:
    from config import production
    CLIMATOLOGY_DIR = production.CLIMATOLOGY_DIR
except ImportError:
    # Fallback for local development
    CLIMATOLOGY_DIR = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        'data', 'climatology'
    )


def calculate_monthly_statistics(observations):
    """
    Calculate monthly statistics from observations.
    
    Parameters:
    -----------
    observations : list of dict
        Observations with 'model' (surf_score) and 'timestamp'
        
    Returns:
    --------
    monthly_stats : dict
        Dictionary with month numbers (1-12) as keys
        Each value contains: mean, std, p25, p50, p75, count
    """
    monthly_scores = defaultdict(list)
    
    for obs in observations:
        timestamp_str = obs.get('timestamp', '')
        if not timestamp_str:
            continue
        
        try:
            obs_time = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            month = obs_time.month
            
            surf_score = obs.get('model', {}).get('surf_score', None)
            if surf_score is not None:
                monthly_scores[month].append(float(surf_score))
        except (ValueError, KeyError):
            continue
    
    monthly_stats = {}
    for month in range(1, 13):
        scores = monthly_scores.get(month, [])
        if scores:
            monthly_stats[month] = {
                'mean': float(np.mean(scores)),
                'std': float(np.std(scores)),
                'p25': float(np.percentile(scores, 25)),
                'p50': float(np.percentile(scores, 50)),
                'p75': float(np.percentile(scores, 75)),
                'count': len(scores)
            }
        else:
            monthly_stats[month] = {
                'mean': None,
                'std': None,
                'p25': None,
                'p50': None,
                'p75': None,
                'count': 0
            }
    
    return monthly_stats


def get_seasonal_expectations(month):
    """
    Get typical score ranges for a given month.
    
    Parameters:
    -----------
    month : int
        Month number (1-12)
        
    Returns:
    --------
    expectations : dict
        Dictionary with 'typical_range', 'average', 'description'
    """
    # Load monthly statistics
    stats_path = os.path.join(CLIMATOLOGY_DIR, 'monthly_stats.json')
    
    if os.path.exists(stats_path):
        try:
            with open(stats_path, 'r') as f:
                monthly_stats = json.load(f)
                month_stats = monthly_stats.get(str(month), {})
                
                if month_stats.get('mean') is not None:
                    return {
                        'typical_range': (month_stats['p25'], month_stats['p75']),
                        'average': month_stats['mean'],
                        'description': f"December typically sees scores between {month_stats['p25']:.1f}-{month_stats['p75']:.1f}/10"
                    }
        except (json.JSONDecodeError, IOError, KeyError) as e:
            logger.warning(f"Failed to load climatology: {e}")
    
    # Default expectations (generic)
    return {
        'typical_range': (4.0, 7.0),
        'average': 5.5,
        'description': 'Typical conditions'
    }


def save_climatology(monthly_stats):
    """Save monthly statistics to JSON file."""
    os.makedirs(CLIMATOLOGY_DIR, exist_ok=True)
    
    # Convert month keys to strings for JSON
    stats_str_keys = {str(k): v for k, v in monthly_stats.items()}
    
    stats_path = os.path.join(CLIMATOLOGY_DIR, 'monthly_stats.json')
    with open(stats_path, 'w') as f:
        json.dump(stats_str_keys, f, indent=2)
    
    logger.info("Saved climatology data")


def load_climatology():
    """Load monthly statistics from JSON file."""
    stats_path = os.path.join(CLIMATOLOGY_DIR, 'monthly_stats.json')
    
    if os.path.exists(stats_path):
        try:
            with open(stats_path, 'r') as f:
                stats_str_keys = json.load(f)
                # Convert back to int keys
                return {int(k): v for k, v in stats_str_keys.items()}
        except (json.JSONDecodeError, IOError, ValueError) as e:
            logger.warning(f"Failed to load climatology: {e}")
    
    return {}

