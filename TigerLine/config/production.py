"""
Production configuration for PythonAnywhere deployment.

This file contains production-specific settings that differ from development.
"""

import os

# Detect if running on PythonAnywhere
is_pythonanywhere = 'PYTHONANYWHERE_DOMAIN' in os.environ or 'USERNAME' in os.environ

if is_pythonanywhere:
    # PythonAnywhere path structure
    username = os.environ.get('USERNAME', 'username')
    PROJECT_ROOT = f'/home/{username}/TigerLine'
else:
    # Local development - use current directory
    PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Data directories
DATA_DIR = os.path.join(PROJECT_ROOT, 'data')
OBSERVATIONS_DIR = os.path.join(DATA_DIR, 'observations')
CALIBRATION_DIR = os.path.join(DATA_DIR, 'calibration')
CLIMATOLOGY_DIR = os.path.join(DATA_DIR, 'climatology')
CACHE_DIR = os.path.join(PROJECT_ROOT, 'config', 'cache')
LOGS_DIR = os.path.join(PROJECT_ROOT, 'logs')

# API Keys (from environment variables)
OPENWEATHERMAP_API_KEY = os.environ.get('OPENWEATHERMAP_API_KEY', '')

# CORS settings
ALLOWED_ORIGINS = os.environ.get('ALLOWED_ORIGINS', '*').split(',')
# If PythonAnywhere, allow the domain
if is_pythonanywhere:
    username = os.environ.get('USERNAME', 'username')
    pythonanywhere_domain = f'https://{username}.pythonanywhere.com'
    if '*' not in ALLOWED_ORIGINS:
        ALLOWED_ORIGINS.append(pythonanywhere_domain)

# Logging configuration
LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
LOG_FILE = os.path.join(LOGS_DIR, 'app.log')

# Flask configuration
FLASK_ENV = 'production' if is_pythonanywhere else 'development'
DEBUG = not is_pythonanywhere

# Cache settings
CACHE_TTL = int(os.environ.get('CACHE_TTL', '300'))  # 5 minutes default

# Ensure all directories exist
def ensure_directories():
    """Create all necessary directories if they don't exist."""
    directories = [
        DATA_DIR,
        OBSERVATIONS_DIR,
        CALIBRATION_DIR,
        CLIMATOLOGY_DIR,
        CACHE_DIR,
        LOGS_DIR
    ]
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        # Set permissions (readable/writable by owner, readable by group/others)
        os.chmod(directory, 0o755)

# Initialize directories on import
ensure_directories()

