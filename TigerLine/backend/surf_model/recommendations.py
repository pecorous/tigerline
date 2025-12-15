"""
Surf condition recommendations and descriptors.

Provides:
- Condition descriptors (glassy, mushy, choppy, etc.)
- Best time windows
- Skill level indicators
- Actionable recommendations
"""


def get_condition_descriptor(surf_score, wind_type, wind_speed_ms, period_s, wave_height_ft):
    """
    Generate a descriptive condition summary.
    
    Parameters:
    -----------
    surf_score : float
        Surf score (0-10)
    wind_type : str
        'offshore', 'cross', or 'onshore'
    wind_speed_ms : float
        Wind speed (m/s)
    period_s : float
        Wave period (s)
    wave_height_ft : float
        Wave height (ft)
        
    Returns:
    --------
    str
        Condition descriptor
    """
    descriptors = []
    
    # Wind condition
    if wind_type == 'offshore':
        if wind_speed_ms < 3.0:
            descriptors.append("glassy")
        elif wind_speed_ms < 6.0:
            descriptors.append("clean")
        else:
            descriptors.append("offshore")
    elif wind_type == 'onshore':
        if wind_speed_ms < 5.0:
            descriptors.append("mushy")
        else:
            descriptors.append("choppy")
    else:  # cross
        if wind_speed_ms < 4.0:
            descriptors.append("sideshore")
        else:
            descriptors.append("cross-shore")
    
    # Wave quality
    if period_s < 7.0:
        descriptors.append("weak")
    elif period_s > 12.0:
        descriptors.append("powerful")
    
    # Wave size
    if wave_height_ft < 2.0:
        descriptors.append("small")
    elif wave_height_ft <= 4.0:
        descriptors.append("waist to shoulder high")
    elif wave_height_ft <= 6.0:
        descriptors.append("head high")
    elif wave_height_ft <= 8.0:
        descriptors.append("overhead")
    else:
        descriptors.append("large")
    
    # Overall quality - updated to match stricter scoring
    if surf_score >= 8.0:
        quality = "excellent"
    elif surf_score >= 6.0:
        quality = "good"
    elif surf_score >= 4.0:
        quality = "fair"
    elif surf_score >= 2.0:
        quality = "poor"
    elif surf_score >= 1.0:
        quality = "very poor"
    else:
        quality = "unrideable"
    
    descriptor = ", ".join(descriptors)
    
    # Special case: Unrideable conditions
    if surf_score < 1.0 or (wave_height_ft < 2.5 and wind_type == 'onshore'):
        return "Unrideable conditions"
    
    return f"{quality.capitalize()} conditions: {descriptor}"


def get_skill_level_indicator(surf_score, wave_height_ft, wind_speed_ms, wind_type):
    """
    Determine if conditions are suitable for different skill levels.
    
    Parameters:
    -----------
    surf_score : float
        Surf score (0-10)
    wave_height_ft : float
        Wave height (ft)
    wind_speed_ms : float
        Wind speed (m/s)
    wind_type : str
        Wind type
        
    Returns:
    --------
    dict with keys:
        beginner : bool
            Suitable for beginners
        intermediate : bool
            Suitable for intermediate
        advanced : bool
            Suitable for advanced
        recommended : str
            Recommended skill level
    """
    beginner_ok = (
        wave_height_ft >= 1.0 and
        wave_height_ft <= 4.0 and
        wind_speed_ms < 8.0 and
        surf_score >= 3.0
    )
    
    intermediate_ok = (
        wave_height_ft >= 2.0 and
        wave_height_ft <= 8.0 and
        wind_speed_ms < 12.0 and
        surf_score >= 4.0
    )
    
    advanced_ok = (
        wave_height_ft >= 3.0 and
        surf_score >= 5.0
    )
    
    if beginner_ok and surf_score >= 5.0:
        recommended = "beginner"
    elif intermediate_ok and surf_score >= 6.0:
        recommended = "intermediate"
    elif advanced_ok:
        recommended = "advanced"
    else:
        recommended = "not recommended"
    
    return {
        'beginner': bool(beginner_ok),  # Ensure Python bool, not numpy bool_
        'intermediate': bool(intermediate_ok),
        'advanced': bool(advanced_ok),
        'recommended': recommended
    }


def find_best_time_windows(forecasts, window_hours=3):
    """
    Find best time windows for surfing sessions.
    
    Parameters:
    -----------
    forecasts : list of dict
        List of forecast entries with 'surf_score' and 'timestamp'
    window_hours : int
        Duration of session window in hours
        
    Returns:
    --------
    list of dict
        Best time windows with start, end, average score, and reasoning
    """
    if len(forecasts) < window_hours:
        return []
    
    windows = []
    
    for i in range(len(forecasts) - window_hours + 1):
        window_forecasts = forecasts[i:i + window_hours]
        scores = [f['surf_score'] for f in window_forecasts]
        avg_score = sum(scores) / len(scores)
        min_score = min(scores)
        max_score = max(scores)
        
        # Get conditions for reasoning
        first = window_forecasts[0]
        wind_type = first.get('wind', {}).get('type', 'unknown')
        wind_speed = first.get('wind', {}).get('speed_ms', 0)
        wave_height = first.get('breaking_wave_height_ft', 0)
        
        windows.append({
            'start_time': window_forecasts[0]['timestamp'],
            'end_time': window_forecasts[-1]['timestamp'],
            'average_score': float(avg_score),  # Ensure Python float
            'min_score': float(min_score),
            'max_score': float(max_score),
            'score_range': float(max_score - min_score),
            'wind_type': str(wind_type),
            'wind_speed_ms': float(wind_speed),
            'wave_height_ft': float(wave_height)
        })
    
    # Sort by average score descending, then by start time ascending
    windows.sort(key=lambda x: (-x['average_score'], x['start_time']))
    
    # Return top 3 windows by score, but they'll be ordered chronologically within same score
    return windows[:3]


def generate_recommendation_text(forecast_entry):
    """
    Generate actionable recommendation text for a forecast entry.
    
    Parameters:
    -----------
    forecast_entry : dict
        Single forecast entry
        
    Returns:
    --------
    str
        Recommendation text
    """
    score = forecast_entry.get('surf_score', 0)
    wave_height = forecast_entry.get('breaking_wave_height_ft', 0)
    period = forecast_entry.get('period_s', 0)
    wind = forecast_entry.get('wind', {})
    wind_type = wind.get('type', 'unknown')
    wind_speed = wind.get('speed_ms', 0)
    tide = forecast_entry.get('tide', {})
    tide_level = tide.get('level_ft', 0)
    
    recommendations = []
    
    # Unrideable conditions
    if score < 1.0 or (wave_height < 2.5 and wind_type == 'onshore'):
        return "Conditions are unrideable. Waves too small and/or onshore wind."
    
    if wave_height < 2.0:
        return "Waves are essentially flat (< 2 ft). Not recommended."
    
    if wave_height < 2.5 and wind_type == 'onshore':
        return "Small waves with onshore wind. Conditions are poor."
    
    # Overall assessment
    if score >= 8.0:
        recommendations.append("Excellent conditions! Great day to surf.")
    elif score >= 6.0:
        recommendations.append("Good conditions. Worth checking out.")
    elif score >= 4.0:
        recommendations.append("Fair conditions. May be worth it if you're local.")
    elif score >= 2.0:
        recommendations.append("Poor conditions. Consider waiting for better waves.")
    else:
        recommendations.append("Very poor conditions. Not recommended - probably not worth it.")
    
    # Wave-specific advice
    if wave_height < 2.5:
        recommendations.append("Very small waves - essentially unrideable.")
    elif wave_height <= 3.0:
        recommendations.append("Small waves - only worth it with perfect conditions (offshore wind, good period).")
    elif wave_height <= 4.0:
        recommendations.append("Small to medium waves - bring a longboard or foam board.")
    elif wave_height > 8.0:
        recommendations.append("Large waves - experienced surfers only.")
    
    # Period advice
    if period < 7.0:
        recommendations.append("Short period waves will be weak and mushy.")
    elif period > 12.0:
        recommendations.append("Long period groundswell - powerful waves expected.")
    
    # Wind advice
    if wind_type == 'offshore' and wind_speed < 5.0:
        recommendations.append("Light offshore winds - clean conditions.")
    elif wind_type == 'onshore':
        if wind_speed < 5.0:
            recommendations.append("⚠️ Onshore wind - conditions will be mushy/choppy.")
        else:
            recommendations.append("⚠️ Strong onshore wind - ruining wave quality.")
    elif wind_type == 'cross':
        recommendations.append("Cross-shore winds - conditions may be affected.")
    
    # Tide advice
    if abs(tide_level) < 0.5:
        recommendations.append("Mid-tide conditions.")
    elif tide_level > 1.0:
        recommendations.append("High tide - may affect wave quality.")
    elif tide_level < -1.0:
        recommendations.append("Low tide - check sandbar exposure.")
    
    return " ".join(recommendations)

