"""
Board recommendation system based on wave conditions and skill level.

Provides surfboard recommendations based on:
- Wave height (ft)
- Wave period (s)
- Wind conditions
- Surfer skill level
"""


def recommend_board(wave_height_ft, period_s, wind_type, wind_speed_ms, skill_level='intermediate'):
    """
    Recommend surfboard type and size based on conditions.
    
    Parameters:
    -----------
    wave_height_ft : float
        Breaking wave height in feet
    period_s : float
        Wave period in seconds
    wind_type : str
        'offshore', 'cross', or 'onshore'
    wind_speed_ms : float
        Wind speed in m/s
    skill_level : str
        'beginner', 'intermediate', or 'advanced'
        
    Returns:
    --------
    dict with keys:
        primary : str
            Primary board recommendation
        alternatives : list of str
            Alternative board options
        reasoning : str
            Explanation of recommendation
        size_range : str
            Recommended size range
    """
    skill_level = skill_level.lower()
    
    # Adjust for period: short period = need more volume
    if period_s < 8.0:
        volume_adjustment = "longer"  # Need more volume for weak waves
    elif period_s > 12.0:
        volume_adjustment = "shorter"  # Can go shorter with more power
    else:
        volume_adjustment = "standard"
    
    # Adjust for wind: onshore = need more volume to paddle through chop
    if wind_type == 'onshore' and wind_speed_ms > 5.0:
        wind_adjustment = "longer"  # Need more paddle power
    else:
        wind_adjustment = None
    
    if skill_level == 'beginner':
        return _recommend_beginner(wave_height_ft, period_s, volume_adjustment, wind_adjustment)
    elif skill_level == 'advanced':
        return _recommend_advanced(wave_height_ft, period_s, volume_adjustment, wind_adjustment)
    else:  # intermediate
        return _recommend_intermediate(wave_height_ft, period_s, volume_adjustment, wind_adjustment)


def _recommend_beginner(wave_height_ft, period_s, volume_adj, wind_adj):
    """Recommend board for beginner surfers."""
    if wave_height_ft < 1.0:
        return {
            'primary': 'Not recommended - waves too small',
            'alternatives': [],
            'reasoning': 'Waves are too small for learning. Wait for better conditions.',
            'size_range': 'N/A'
        }
    elif wave_height_ft <= 2.0:
        size = "9'0\" - 10'0\"" if volume_adj == "longer" else "8'6\" - 9'6\""
        return {
            'primary': 'Foam Board / Soft Top',
            'alternatives': ['Longboard (9\'+)'],
            'reasoning': 'Small waves require maximum stability and paddle power. Foam boards are safest for learning.',
            'size_range': size
        }
    elif wave_height_ft <= 3.0:
        size = "9'0\" - 9'6\"" if volume_adj == "longer" else "8'6\" - 9'0\""
        return {
            'primary': 'Longboard',
            'alternatives': ['Foam Board', 'Funboard (8\'+)'],
            'reasoning': 'Knee to waist high waves. Longboard provides stability and easy paddling.',
            'size_range': size
        }
    elif wave_height_ft <= 4.0:
        return {
            'primary': 'Longboard (8\'6\" - 9\'0\")',
            'alternatives': ['Funboard (8\'+)'],
            'reasoning': 'Shoulder high waves. Longboard still recommended for beginners. Consider funboard if comfortable.',
            'size_range': '8\'6\" - 9\'0\"'
        }
    else:
        return {
            'primary': 'Not recommended for beginners',
            'alternatives': [],
            'reasoning': 'Waves are too large for beginner surfers. Wait for smaller conditions or take lessons.',
            'size_range': 'N/A'
        }


def _recommend_intermediate(wave_height_ft, period_s, volume_adj, wind_adj):
    """Recommend board for intermediate surfers."""
    if wave_height_ft < 1.0:
        return {
            'primary': 'Longboard (9\'+)',
            'alternatives': ['Foam Board'],
            'reasoning': 'Very small waves. Longboard maximizes wave catching ability.',
            'size_range': '9\'0\" - 10\'0\"'
        }
    elif wave_height_ft <= 2.0:
        if volume_adj == "longer":
            primary = 'Longboard (8\'6\" - 9\'6\")'
            alt = ['Funboard (7\'6\" - 8\'6\")']
            size = '8\'6\" - 9\'6\"'
        else:
            primary = 'Funboard (7\'6\" - 8\'6\")'
            alt = ['Longboard (8\'6\" - 9\'6\")', 'Mid-length (7\' - 8\')']
            size = '7\'6\" - 8\'6\"'
        return {
            'primary': primary,
            'alternatives': alt,
            'reasoning': 'Small waves. Funboard or longboard provides good paddle power and wave catching.',
            'size_range': size
        }
    elif wave_height_ft <= 3.0:
        if volume_adj == "longer":
            primary = 'Funboard (7\' - 8\')'
            alt = ['Mid-length (7\' - 8\')', 'Longboard (8\'6\"+)']
            size = '7\'0\" - 8\'0\"'
        else:
            primary = 'Mid-length (7\' - 8\')'
            alt = ['Funboard (7\' - 8\')', 'Shortboard (6\'6\" - 7\')']
            size = '7\'0\" - 8\'0\"'
        return {
            'primary': primary,
            'alternatives': alt,
            'reasoning': 'Waist to shoulder high. Mid-length or funboard ideal for intermediate surfers.',
            'size_range': size
        }
    elif wave_height_ft <= 4.0:
        if volume_adj == "longer":
            primary = 'Mid-length (7\' - 7\'6\")'
            alt = ['Shortboard (6\'6\" - 7\')', 'Funboard (7\'+)']
            size = '7\'0\" - 7\'6\"'
        else:
            primary = 'Shortboard (6\'6\" - 7\')'
            alt = ['Mid-length (7\' - 7\'6\")']
            size = '6\'6\" - 7\'0\"'
        return {
            'primary': primary,
            'alternatives': alt,
            'reasoning': 'Shoulder to head high. Shortboard or mid-length depending on comfort level.',
            'size_range': size
        }
    elif wave_height_ft <= 6.0:
        primary = 'Shortboard (6\'6\" - 7\')'
        alt = ['Mid-length (7\')']
        return {
            'primary': primary,
            'alternatives': alt,
            'reasoning': 'Head high waves. Standard shortboard size works well.',
            'size_range': '6\'6\" - 7\'0\"'
        }
    elif wave_height_ft <= 8.0:
        return {
            'primary': 'Step-up (6\'8\" - 7\'2\")',
            'alternatives': ['Performance Shortboard (6\'6\" - 7\')'],
            'reasoning': 'Overhead waves. Step-up provides more paddle power and stability.',
            'size_range': '6\'8\" - 7\'2\"'
        }
    else:
        return {
            'primary': 'Step-up / Gun (7\'+)',
            'alternatives': [],
            'reasoning': 'Large waves. Step-up or gun recommended for safety and performance.',
            'size_range': '7\'0\" - 8\'0\"'
        }


def _recommend_advanced(wave_height_ft, period_s, volume_adj, wind_adj):
    """Recommend board for advanced surfers."""
    if wave_height_ft < 2.0:
        if volume_adj == "longer":
            primary = 'Longboard (9\'+)'
            alt = ['Mid-length (7\'6\" - 8\'6\")', 'Groveler (5\'10\" - 6\'4\")']
            size = '9\'0\" - 10\'0\"'
        else:
            primary = 'Groveler (5\'10\" - 6\'4\")'
            alt = ['Mid-length (7\' - 8\')', 'Longboard (9\'+)']
            size = '5\'10\" - 6\'4\"'
        return {
            'primary': primary,
            'alternatives': alt,
            'reasoning': 'Small waves. Groveler or longboard depending on preference.',
            'size_range': size
        }
    elif wave_height_ft <= 3.0:
        if volume_adj == "longer":
            primary = 'Mid-length (7\' - 8\')'
            alt = ['Groveler (5\'10\" - 6\'4\")', 'Performance Shortboard (6\' - 6\'6\")']
            size = '7\'0\" - 8\'0\"'
        else:
            primary = 'Performance Shortboard (6\' - 6\'6\")'
            alt = ['Groveler (5\'10\" - 6\'4\")', 'Mid-length (7\' - 8\')']
            size = '6\'0\" - 6\'6\"'
        return {
            'primary': primary,
            'alternatives': alt,
            'reasoning': 'Waist to shoulder high. Performance shortboard or groveler for maneuverability.',
            'size_range': size
        }
    elif wave_height_ft <= 5.0:
        primary = 'Performance Shortboard (5\'10\" - 6\'6\")'
        alt = ['Step-up (6\'6\" - 7\')']
        return {
            'primary': primary,
            'alternatives': alt,
            'reasoning': 'Shoulder to head high. Performance shortboard ideal for advanced surfers.',
            'size_range': '5\'10\" - 6\'6\"'
        }
    elif wave_height_ft <= 8.0:
        primary = 'Performance Shortboard (6\' - 6\'8\")'
        alt = ['Step-up (6\'8\" - 7\'2\")']
        return {
            'primary': primary,
            'alternatives': alt,
            'reasoning': 'Head to overhead. Performance board or step-up depending on conditions.',
            'size_range': '6\'0\" - 6\'8\"'
        }
    elif wave_height_ft <= 12.0:
        return {
            'primary': 'Step-up / Gun (6\'8\" - 7\'6\")',
            'alternatives': [],
            'reasoning': 'Large waves. Step-up or gun provides paddle power and control.',
            'size_range': '6\'8\" - 7\'6\"'
        }
    else:
        return {
            'primary': 'Gun / Big Wave Board (7\'6\"+)',
            'alternatives': [],
            'reasoning': 'Very large waves. Gun or big wave board essential for safety.',
            'size_range': '7\'6\" - 9\'0\"'
        }

