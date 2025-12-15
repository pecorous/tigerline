"""
Flask API server for Belmar surf forecast.

Exposes endpoints:
- GET /forecast - Main forecast endpoint
- GET /forecast/physics - Detailed physics view
- GET /health - Health check

Data Sources:
- Tide data: NOAA CO-OPS API (Station 8531680, Sandy Hook, NJ)
  Citation: NOAA Tides & Currents, https://tidesandcurrents.noaa.gov/
- Wave data: NOAA NDBC (Station 44025, Sandy Hook, NJ)
  Citation: NOAA National Data Buoy Center, https://www.ndbc.noaa.gov/
- Wind data: OpenWeatherMap API (Free Plan)
  Citation: OpenWeatherMap, https://openweathermap.org/api
"""

import json
import os
import sys
import logging
from datetime import datetime, timedelta
from flask import Flask, jsonify, request
import numpy as np

# Handle both direct execution and module import
# Add project root to path for imports
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Use absolute imports (works for both direct execution and module import)
from backend.data_sources import buoy, tides, wind, sync
from backend.waves import dispersion, transform, spectra, propagation
from backend.surf_model import quality, config, board_recommendations, recommendations as rec_module, storage, calibration, trends, climatology

# Import production config to ensure directories are created
try:
    from config import production
    # Directories are created automatically on import
except ImportError:
    # Fallback - ensure directories exist
    storage.initialize_storage()

# Detect if running on PythonAnywhere
is_pythonanywhere = 'PYTHONANYWHERE_DOMAIN' in os.environ or os.environ.get('FLASK_ENV') == 'production'
is_production = is_pythonanywhere or os.environ.get('FLASK_ENV') == 'production'

# Configure logging
if is_production:
    # Production logging - log to file
    log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'logs')
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, 'app.log')
    
    # Use RotatingFileHandler for log rotation (max 10MB, keep 5 backups)
    from logging.handlers import RotatingFileHandler
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(name)s %(message)s'))
    
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(name)s %(message)s'))
    
    logging.basicConfig(
        level=logging.INFO,
        handlers=[file_handler, console_handler]
    )
else:
    # Development logging
    logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['DEBUG'] = not is_production

# Enable CORS for frontend
@app.after_request
def after_request(response):
    # In production, allow specific domain; in development, allow all
    if is_production:
        # Get allowed origin from environment or use PythonAnywhere domain
        allowed_origin = os.environ.get('ALLOWED_ORIGIN', '*')
        response.headers.add('Access-Control-Allow-Origin', allowed_origin)
    else:
        response.headers.add('Access-Control-Allow-Origin', '*')
    
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    
    # Add caching headers for static data in production
    if is_production and request.endpoint in ['forecast', 'forecast_physics']:
        response.cache_control.max_age = 300  # 5 minutes cache
    
    return response


def load_bathymetric_profile():
    """Load bathymetric profile from config file."""
    config_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        'config',
        'belmar_profile.json'
    )
    
    try:
        with open(config_path, 'r') as f:
            data = json.load(f)
            profile = [(point['x'], point['h']) for point in data.get('profile', [])]
            return profile
    except Exception as e:
        logger.warning(f"Failed to load bathymetric profile: {e}. Using default.")
        # Default profile
        return [
            (0, 0.0),
            (50, 1.0),
            (100, 2.0),
            (200, 3.5),
            (300, 5.0),
            (500, 7.0),
            (1000, 10.0),
            (2000, 15.0),
            (5000, 20.0),
            (10000, 25.0)
        ]


def ensure_json_serializable(obj):
    """
    Recursively convert numpy types to Python native types for JSON serialization.
    """
    if isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        return float(obj)
    elif isinstance(obj, np.bool_):
        return bool(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, dict):
        return {key: ensure_json_serializable(value) for key, value in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [ensure_json_serializable(item) for item in obj]
    else:
        return obj


def compute_forecast(hours=72):
    """
    Compute surf forecast for next N hours.
    
    Parameters:
    -----------
    hours : int
        Number of hours to forecast
        
    Returns:
    --------
    list of forecast dicts, one per hour
    """
    # Load calibration data
    k_site_dict, tide_prefs, wind_prefs, bar_state_index = calibration.load_calibration_data()
    
    # Load bathymetric profile
    profile = load_bathymetric_profile()
    
    # Fetch data from all sources
    logger.info("Fetching historical buoy data...")
    historical_buoy = buoy.get_historical_bulk_parameters(
        config.BUOY_STATION, 
        hours=48,
        backup_station=getattr(config, 'BUOY_STATION_BACKUP', '44091')
    )
    
    # Calculate swell trends
    trend_data = trends.calculate_swell_trends(historical_buoy, hours=24)
    
    logger.info("Fetching wind data...")
    wind_data = wind.get_wind_data(config.LATITUDE, config.LONGITUDE, days=hours/24)
    
    logger.info("Fetching tide data...")
    tide_data = tides.get_tide_predictions('Belmar', days=hours/24)
    
    # Synchronize all data to common time grid
    logger.info("Synchronizing data...")
    synced = sync.synchronize_data(
        historical_buoy,  # Pass historical data instead of single point
        wind_data,
        tide_data,
        hours=hours
    )
    
    forecasts = []
    
    for i, time in enumerate(synced['times']):
        # Get synchronized data for this time
        wind_speed = synced['wind'].get('speeds', [5.0] * len(synced['times']))[i] if synced['wind'].get('speeds') else 5.0
        wind_dir = synced['wind'].get('directions', [180.0] * len(synced['times']))[i] if synced['wind'].get('directions') else 180.0
        tide_level = synced['tide'].get('levels', [0.0] * len(synced['times']))[i] if synced['tide'].get('levels') else 0.0
        
        # Get temperature data
        temp_c = synced['wind'].get('temperature_c', [])[i] if i < len(synced['wind'].get('temperature_c', [])) else 15.0
        temp_f = synced['wind'].get('temperature_f', [])[i] if i < len(synced['wind'].get('temperature_f', [])) else 59.0
        feels_c = synced['wind'].get('feels_like_c', [])[i] if i < len(synced['wind'].get('feels_like_c', [])) else 15.0
        feels_f = synced['wind'].get('feels_like_f', [])[i] if i < len(synced['wind'].get('feels_like_f', [])) else 59.0
        
        # Forecast wave conditions using propagation model
        # Convert time to datetime if needed
        if isinstance(time, str):
            forecast_time = datetime.fromisoformat(time.replace('Z', '+00:00'))
        elif isinstance(time, datetime):
            forecast_time = time
        else:
            forecast_time = datetime.now() + timedelta(hours=i)
        
        # Get wind data for propagation
        wind_for_propagation = {
            'speed_ms': wind_speed,
            'direction_deg': wind_dir
        }
        
        # Forecast wave conditions at beach for this time
        wave_forecast = propagation.forecast_wave_conditions(
            historical_buoy,
            forecast_time,
            wind_data=wind_for_propagation,
            buoy_distance_km=propagation.BUOY_TO_BEACH_DISTANCE_KM
        )
        
        # Extract forecasted wave parameters
        Hs_offshore_raw = wave_forecast['Hs']
        Tp_offshore = wave_forecast['Tp']
        swell_dir_coming_from = wave_forecast['peak_direction']
        h_offshore = config.BUOY_DEPTH
        
        # Apply K_site correction if available
        Hs_offshore = calibration.apply_k_site_correction(
            Hs_offshore_raw,
            swell_dir_coming_from,
            Tp_offshore,
            k_site_dict
        )
        
        # Convert "coming FROM" to "going TO" for refraction physics
        wave_going_to = (swell_dir_coming_from + 180) % 360
        
        # Calculate angle between wave going direction and shore-normal
        # Both are now "going TO" directions
        angle_diff = wave_going_to - config.SHORE_NORMAL
        
        # Normalize to [-180, 180] for proper angle representation
        while angle_diff > 180:
            angle_diff -= 360
        while angle_diff < -180:
            angle_diff += 360
        
        # Convert to radians: theta = 0 means straight in (perpendicular to shore)
        # Positive = waves from right (looking offshore), Negative = from left
        theta_offshore = np.deg2rad(angle_diff)
        
        # Adjust bathymetric profile for tide
        profile_tided = [(x, max(0.0, h + tide_level)) for x, h in profile]
        
        # Transform offshore to nearshore
        # Use shoaling and refraction to find breaking point
        # Get detailed shoaling path for physics view
        Hb, h_break, x_break, theta_break, shoaling_path = transform.find_breaking_point(
            Hs_offshore,
            Tp_offshore,
            theta_offshore,
            profile_tided,
            gamma_b=config.GAMMA_B,
            return_path=True
        )
        
        # Convert breaking angle back to degrees
        theta_break_deg = np.rad2deg(theta_break)
        
        # Compute Iribarren number and breaker type
        # Use deep-water equivalent height for Iribarren
        # Approximate: H0 ≈ Hs_offshore (for simplicity)
        H0 = Hs_offshore
        Xi = transform.iribarren_number(
            config.BEACH_SLOPE_RADIANS,
            H0,
            Tp_offshore
        )
        breaker_type = transform.breaker_type_from_iribarren(Xi)
        
        # Convert Hb (significant height) to typical surf height
        # Hs is average of highest 1/3 waves - surfers see smaller typical waves
        # Use Hs / 1.6 which gives average individual wave height
        Hb_surf = Hb / 1.6  # Average individual wave height
        Hb_ft = Hb_surf * 3.28084
        
        # Compute surf quality score using surf height (not Hs)
        quality_result = quality.compute_surf_score(
            Hb=Hb_surf,  # Use typical surf height, not significant height
            T=Tp_offshore,
            theta_break=theta_break_deg,
            breaker_type=breaker_type,
            U=wind_speed,
            wind_dir=wind_dir,
            eta_tide=tide_level,
            swell_dir_coming_from=swell_dir_coming_from
        )
        
        # Apply trend factor
        surf_score_base = quality_result['surf_score']
        surf_score_adjusted = trends.apply_trend_factor(surf_score_base, trend_data, Tp_offshore)
        quality_result['surf_score'] = surf_score_adjusted
        
        # Get wind type using absolute directions
        wind_type = quality.classify_wind_type(wind_dir)
        
        # Get board recommendations (for intermediate skill level)
        board_rec = board_recommendations.recommend_board(
            wave_height_ft=Hb_ft,
            period_s=Tp_offshore,
            wind_type=wind_type,
            wind_speed_ms=wind_speed,
            skill_level='intermediate'
        )
        
        # Get condition descriptor
        condition_desc = rec_module.get_condition_descriptor(
            surf_score=quality_result['surf_score'],
            wind_type=wind_type,
            wind_speed_ms=wind_speed,
            period_s=Tp_offshore,
            wave_height_ft=Hb_ft
        )
        
        # Get skill level indicator
        skill_level = rec_module.get_skill_level_indicator(
            surf_score=quality_result['surf_score'],
            wave_height_ft=Hb_ft,
            wind_speed_ms=wind_speed,
            wind_type=wind_type
        )
        
        # Generate recommendation text
        rec_text = rec_module.generate_recommendation_text({
            'surf_score': quality_result['surf_score'],
            'breaking_wave_height_ft': Hb_ft,
            'period_s': Tp_offshore,
            'wind': {
                'type': wind_type,
                'speed_ms': wind_speed
            },
            'tide': {
                'level_ft': tide_level * 3.28084
            }
        })
        
        # Build forecast entry - ensure all values are JSON serializable
        forecast_entry = {
            'timestamp': time.isoformat() if isinstance(time, datetime) else str(time),
            'surf_score': float(quality_result['surf_score']),
            'breaking_wave_height_m': float(Hb_surf),  # Store surf height in meters
            'breaking_wave_height_ft': float(Hb_ft),    # Already surf height in feet
            'breaking_wave_height_hs_m': float(Hb),    # Store Hs for reference
            'period_s': float(Tp_offshore),
            'wind': {
                'speed_ms': float(wind_speed),
                'speed_mph': float(wind_speed * 2.237),
                'direction_deg': float(wind_dir),
                'type': str(wind_type)
            },
            'tide': {
                'level_m': float(tide_level),
                'level_ft': float(tide_level * 3.28084)
            },
            'temperature': {
                'celsius': float(temp_c),
                'fahrenheit': float(temp_f),
                'feels_like_celsius': float(feels_c),
                'feels_like_fahrenheit': float(feels_f)
            },
            'sub_scores': {
                'height': float(quality_result['sub_scores']['height']),
                'period': float(quality_result['sub_scores']['period']),
                'direction': float(quality_result['sub_scores']['direction']),
                'wind': float(quality_result['sub_scores']['wind']),
                'tide': float(quality_result['sub_scores']['tide'])
            },
            'board_recommendation': ensure_json_serializable(board_rec),
            'condition_descriptor': str(condition_desc),
            'skill_level': ensure_json_serializable(skill_level),
            'recommendation': str(rec_text),
            'physics': {
                'offshore': {
                    'Hs_m': float(Hs_offshore),
                    'Tp_s': float(Tp_offshore),
                    'direction_deg': float(swell_dir_coming_from),
                    'Hs_swell_m': float(wave_forecast.get('Hs_swell', Hs_offshore)),
                    'Hs_wind_m': float(wave_forecast.get('Hs_wind', 0.0)),
                    'travel_time_hours': float(wave_forecast.get('travel_time_hours', 0.0)),
                    'Hs_raw_before_k_site': float(Hs_offshore_raw),
                    'k_site_correction': float(Hs_offshore / Hs_offshore_raw) if Hs_offshore_raw > 0 else 1.0
                },
                'breaking': {
                    'height_m': float(Hb_surf),  # Store surf height, not Hs
                    'height_hs_m': float(Hb),  # Also store Hs for reference
                    'depth_m': float(h_break),
                    'distance_from_shore_m': float(x_break),
                    'angle_deg': float(theta_break_deg),
                    'type': str(breaker_type)
                },
                'iribarren_number': float(Xi),
                'shoaling_path': ensure_json_serializable(shoaling_path),
                'shoaling_path_surf': ensure_json_serializable([
                    {**p, 'H': p['H'] / 1.6, 'H_hs': p['H']} for p in shoaling_path
                ]),  # Convert to surf height for graph
                'propagation': {
                    'decay_factor': float(wave_forecast.get('decay_factor', 1.0)),
                    'wind_wave_contribution_pct': float(100.0 * wave_forecast.get('Hs_wind', 0.0)**2 / (Hs_offshore**2 + wave_forecast.get('Hs_wind', 0.0)**2)) if Hs_offshore > 0 else 0.0
                },
                'scoring_breakdown': {
                    'base_score': float(quality_result.get('base_score', 0.0)),
                    'penalty_multiplier': float(quality_result.get('penalty_multiplier', 1.0)),
                    'penalized_score': float(quality_result.get('penalized_score', 0.0)),
                    'breaker_multiplier': float(quality_result.get('breaker_multiplier', 1.0)),
                    'trend_adjustment': float(surf_score_adjusted - surf_score_base),
                    'final_score': float(surf_score_adjusted)
                }
            }
        }
        
        forecasts.append(forecast_entry)
        
        # Automatically store model prediction for learning system
        try:
            # Prepare data for storage
            offshore_data = {
                'Hs': float(Hs_offshore),
                'Tp': float(Tp_offshore),
                'direction': float(swell_dir_coming_from)
            }
            
            local_data = {
                'wind_speed': float(wind_speed),
                'wind_dir': float(wind_dir),
                'tide': float(tide_level)
            }
            
            model_prediction = {
                'Hb': float(Hb),
                'theta_break': float(theta_break_deg),
                'breaker_type': str(breaker_type),
                'surf_score': float(quality_result['surf_score'])
            }
            
            # Store without human rating (can be added later via API)
            storage.store_observation(
                timestamp=forecast_time,
                offshore_data=offshore_data,
                local_data=local_data,
                model_prediction=model_prediction,
                human_rating=None,
                tags=None
            )
        except Exception as e:
            # Don't fail forecast if storage fails
            logger.warning(f"Failed to store observation for {forecast_time}: {e}")
    
    return forecasts


@app.route('/', methods=['GET'])
def root():
    """Root endpoint - redirects to frontend."""
    return jsonify({
        'message': 'Belmar Surf Forecast API',
        'frontend': 'http://localhost:3000',
        'endpoints': {
            'health': '/health',
            'forecast': '/forecast',
            'forecast_physics': '/forecast/physics'
        },
        'note': 'Access the web interface at http://localhost:3000'
    }), 200


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat()
    })


@app.route('/climatology', methods=['GET'])
def get_climatology():
    """
    Get climatology data (monthly statistics).
    
    Returns:
    --------
    JSON with monthly statistics and current month expectations
    """
    try:
        # Load all observations
        now = datetime.now()
        start_date = now - timedelta(days=365)  # Last year
        observations = storage.load_observations(start_date, now)
        
        # Calculate monthly statistics
        monthly_stats = climatology.calculate_monthly_statistics(observations)
        
        # Save for future use
        climatology.save_climatology(monthly_stats)
        
        # Get current month expectations
        current_month = now.month
        expectations = climatology.get_seasonal_expectations(current_month)
        
        return jsonify({
            'monthly_statistics': monthly_stats,
            'current_month': current_month,
            'current_expectations': expectations,
            'observation_count': len(observations)
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting climatology: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/calibration/status', methods=['GET'])
def calibration_status():
    """
    Get calibration status and data.
    
    Returns:
    --------
    JSON with K_site values, observation counts, and calibration quality
    """
    try:
        # Load calibration data
        k_site_dict, tide_prefs, wind_prefs, bar_state_index = calibration.load_calibration_data()
        
        # Get observation count
        obs_count = storage.get_observation_count()
        rated_count = len(storage.get_observations_with_ratings())
        
        # Calculate calibration quality
        quality = 'none'
        if rated_count >= 50:
            quality = 'good'
        elif rated_count >= 20:
            quality = 'fair'
        elif rated_count >= 5:
            quality = 'poor'
        
        return jsonify({
            'k_site_factors': k_site_dict,
            'tide_preferences': tide_prefs,
            'wind_preferences': wind_prefs,
            'bar_state_index': float(bar_state_index),
            'observations': {
                'total': obs_count,
                'with_ratings': rated_count
            },
            'calibration_quality': quality,
            'last_updated': datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting calibration status: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/observations', methods=['POST'])
def add_observation():
    """
    Add human observation/rating for a specific timestamp.
    
    Request body (JSON):
    {
        "timestamp": "2025-12-05T12:00:00",
        "rating": 7.5,
        "tags": ["barreling", "clean"]
    }
    
    Returns:
    --------
    JSON with success status
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
        
        timestamp_str = data.get('timestamp')
        rating = data.get('rating')
        tags = data.get('tags', [])
        
        if not timestamp_str:
            return jsonify({'error': 'timestamp is required'}), 400
        
        if rating is None:
            return jsonify({'error': 'rating is required'}), 400
        
        # Validate rating
        try:
            rating = float(rating)
            if rating < 0 or rating > 10:
                return jsonify({'error': 'rating must be between 0 and 10'}), 400
        except (ValueError, TypeError):
            return jsonify({'error': 'rating must be a number'}), 400
        
        # Parse timestamp
        try:
            obs_time = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        except ValueError:
            return jsonify({'error': 'Invalid timestamp format. Use ISO format: YYYY-MM-DDTHH:MM:SS'}), 400
        
        # Load existing observation for this timestamp
        # Find observation file for this date
        date_str = obs_time.strftime('%Y-%m-%d')
        file_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            'data', 'observations', f"{date_str}.json"
        )
        
        if not os.path.exists(file_path):
            return jsonify({'error': f'No forecast data found for timestamp {timestamp_str}'}), 404
        
        # Load observations
        try:
            with open(file_path, 'r') as f:
                observations = json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            return jsonify({'error': f'Failed to load observations: {e}'}), 500
        
        # Find matching observation (within 1 hour window)
        found = False
        for obs in observations:
            obs_time_existing = datetime.fromisoformat(obs['timestamp'].replace('Z', '+00:00'))
            time_diff = abs((obs_time - obs_time_existing).total_seconds())
            
            if time_diff < 3600:  # Within 1 hour
                # Update observation with human rating
                obs['observation'] = {
                    'rating': float(rating),
                    'tags': tags if isinstance(tags, list) else []
                }
                found = True
                break
        
        if not found:
            return jsonify({'error': f'No forecast data found within 1 hour of {timestamp_str}'}), 404
        
        # Save updated observations
        try:
            with open(file_path, 'w') as f:
                json.dump(observations, f, indent=2)
        except IOError as e:
            return jsonify({'error': f'Failed to save observation: {e}'}), 500
        
        return jsonify({
            'success': True,
            'message': 'Observation added successfully',
            'timestamp': obs_time.isoformat(),
            'rating': float(rating),
            'tags': tags
        }), 200
        
    except Exception as e:
        logger.error(f"Error adding observation: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/forecast', methods=['GET'])
def get_forecast():
    """
    Main forecast endpoint.
    
    Returns surf forecast for next 72 hours (default) or specified hours.
    
    Query parameters:
    - hours: Number of hours to forecast (default 72)
    
    Returns:
    --------
    JSON with forecast array
    """
    # Input validation
    hours_str = request.args.get('hours', '72')
    try:
        hours = int(hours_str)
        hours = max(1, min(hours, 168))  # Limit to 1 week
    except ValueError:
        return jsonify({
            'error': 'Invalid hours parameter',
            'message': 'hours must be an integer',
            'timestamp': datetime.now().isoformat()
        }), 400
    
    logger.info(f"Computing forecast for {hours} hours...")
    
    try:
        forecasts = compute_forecast(hours)
        
        # Find best time windows
        best_windows = rec_module.find_best_time_windows(forecasts, window_hours=3)
        
        # Ensure all data is JSON serializable
        response_data = {
            'location': '16th Ave, Belmar, NJ',
            'coordinates': {
                'lat': float(config.LATITUDE),
                'lon': float(config.LONGITUDE)
            },
            'buoy_station': str(config.BUOY_STATION),
            'forecast_hours': int(hours),
            'forecast': ensure_json_serializable(forecasts),
            'best_time_windows': ensure_json_serializable(best_windows),
            'timestamp': datetime.now().isoformat()
        }
        
        return jsonify(response_data)
    except Exception as e:
        logger.error(f"Error computing forecast: {e}", exc_info=True)
        return jsonify({
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500


@app.route('/forecast/physics', methods=['GET'])
def get_forecast_physics():
    """
    Detailed physics view endpoint.
    
    Returns forecast with all intermediate physics calculations.
    """
    # Input validation
    hours_str = request.args.get('hours', '72')
    try:
        hours = int(hours_str)
        hours = max(1, min(hours, 168))  # Limit to 1 week
    except ValueError:
        return jsonify({
            'error': 'Invalid hours parameter',
            'message': 'hours must be an integer',
            'timestamp': datetime.now().isoformat()
        }), 400
    
    logger.info(f"Computing detailed physics forecast for {hours} hours...")
    
    try:
        forecasts = compute_forecast(hours)
        
        # Add more detailed physics for first forecast entry
        if len(forecasts) > 0:
            # Use data already computed in compute_forecast() - no need to fetch again
            first_forecast = forecasts[0]
            
            # Extract values from already-computed forecast
            Hs_offshore = first_forecast['physics']['offshore']['Hs_m']
            Tp_offshore = first_forecast['physics']['offshore']['Tp_s']
            physics_detail = {
                'shoaling_path': [],
                'spectral_moments': {
                    'note': 'Would require spectral data from buoy'
                },
                'energy_flux': {
                    'offshore': float(dispersion.energy_flux(
                        Hs_offshore,
                        Tp_offshore,
                        config.BUOY_DEPTH,
                        theta=0.0
                    )),
                    'breaking': float(dispersion.energy_flux(
                        first_forecast['breaking_wave_height_m'],
                        Tp_offshore,
                        first_forecast['physics']['breaking']['depth_m'],
                        theta=np.deg2rad(first_forecast['physics']['breaking']['angle_deg'])
                    ))
                }
            }
            
            first_forecast['physics']['detailed'] = ensure_json_serializable(physics_detail)
        
        response_data = {
            'location': '16th Ave, Belmar, NJ',
            'forecast_hours': int(hours),
            'forecast': ensure_json_serializable(forecasts),
            'timestamp': datetime.now().isoformat()
        }
        
        return jsonify(response_data)
    except Exception as e:
        logger.error(f"Error computing physics forecast: {e}", exc_info=True)
        return jsonify({
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500


# Production error handlers
@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors."""
    logger.warning(f"404 error: {request.url}")
    return jsonify({
        'error': 'Not found',
        'message': 'The requested resource was not found.',
        'timestamp': datetime.now().isoformat()
    }), 404

@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors."""
    logger.error(f"500 error: {error}", exc_info=True)
    if is_production:
        # Don't expose error details in production
        return jsonify({
            'error': 'Internal server error',
            'message': 'An error occurred processing your request.',
            'timestamp': datetime.now().isoformat()
        }), 500
    else:
        # In development, show error details
        return jsonify({
            'error': str(error),
            'timestamp': datetime.now().isoformat()
        }), 500

@app.errorhandler(Exception)
def handle_exception(e):
    """Handle all unhandled exceptions."""
    logger.error(f"Unhandled exception: {e}", exc_info=True)
    if is_production:
        return jsonify({
            'error': 'Internal server error',
            'message': 'An unexpected error occurred.',
            'timestamp': datetime.now().isoformat()
        }), 500
    else:
        return jsonify({
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500


if __name__ == '__main__':
    # Only run development server when executed directly (not via WSGI)
    import socket
    
    # Find an available port starting from 5002
    def find_free_port(start_port=5002):
        for port in range(start_port, start_port + 100):
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                try:
                    s.bind(('localhost', port))
                    return port
                except OSError:
                    continue
        return 5002  # Fallback
    
    # Use environment variable or find free port
    if 'PORT' in os.environ:
        port = int(os.environ.get('PORT'))
        print(f"Using specified port: {port}")
    else:
        port = find_free_port()
        print(f"* Auto-selected available port: {port}")
    
    print(f"* API will be available at: http://localhost:{port}")
    print(f"* Endpoints:")
    print(f"  - GET http://localhost:{port}/forecast")
    print(f"  - GET http://localhost:{port}/forecast/physics")
    print(f"  - GET http://localhost:{port}/health")
    print("")
    
    # Write port to config file for frontend
    config_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'config')
    os.makedirs(config_dir, exist_ok=True)
    port_config_path = os.path.join(config_dir, 'port.json')
    with open(port_config_path, 'w') as f:
        json.dump({'port': port}, f)
    print(f"* Port configuration written to {port_config_path}")
    print("")
    
    # Development server only
    app.run(debug=not is_production, use_reloader=False, host='0.0.0.0', port=port)
