"""
Site-specific configuration for 16th Ave Belmar, NJ.

FAKE DATA WARNING:
- BUOY_DEPTH: Approximate depth, needs verification from buoy metadata
- COASTLINE_AZIMUTH: Estimated from maps, needs actual survey
- SHORE_NORMAL: Computed from coastline azimuth, needs verification
- BEACH_SLOPE: Estimated typical NJ beach slope, needs actual survey data
"""

# Buoy configuration
# FORCED TO USE 44091 - Station 44025 is down (showing MM since Nov 29)
BUOY_STATION = '44091'  # Barnegat, NJ buoy (30mi south, CURRENTLY REPORTING)
BUOY_STATION_BACKUP = '44025'  # Sandy Hook, NJ buoy (down, backup only)
# FAKE DATA: Approximate buoy depth (meters) - needs verification from NDBC metadata
BUOY_DEPTH = 28.0  # 44091 depth

# Location coordinates
LATITUDE = 40.18  # Belmar, NJ
LONGITUDE = -74.02

# Coastline orientation
# Belmar 16th Ave: Coastline runs roughly N-S with slight tilt, faces ESE
# Shore-parallel direction (degrees clockwise from true north)
COASTLINE_AZIMUTH = 0.0  # N-S orientation

# Shore-normal direction (perpendicular to coastline, pointing offshore)
# Points ESE (approximately 110-120°)
SHORE_NORMAL = 110.0  # degrees clockwise from true north (ESE)

# Beach slope for Iribarren number calculation
# Belmar 16th Ave: Steepish foreshore with close-in bar (steeper than typical)
BEACH_SLOPE_DEGREES = 6.5  # degrees (steeper than typical NJ beach)
BEACH_SLOPE_RADIANS = 6.5 * 3.141592653589793 / 180.0  # radians

# Swell window configuration
# Ideal swell directions (coming-FROM, degrees clockwise from north)
IDEAL_SWELL_DIRECTIONS = (60, 90)  # NE to E
POOR_SWELL_DIRECTIONS = (180, 225)  # S to SSW

# Wind direction configuration (coming-FROM, degrees clockwise from north)
OFFSHORE_WIND_RANGE = (260, 330)  # W-NW
ONSHORE_WIND_RANGE = (45, 135)  # E-sector

# Breaker index (gamma_b)
GAMMA_B = 0.78  # Standard value for random waves

