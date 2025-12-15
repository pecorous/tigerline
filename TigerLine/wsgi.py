"""
WSGI entry point for PythonAnywhere deployment.

This file is used by PythonAnywhere to serve the Flask application.
PythonAnywhere looks for a variable named 'application' in this file.
"""

import sys
import os

# Detect if running on PythonAnywhere
# PythonAnywhere sets USERNAME environment variable
is_pythonanywhere = 'PYTHONANYWHERE_DOMAIN' in os.environ or 'USERNAME' in os.environ

if is_pythonanywhere:
    # PythonAnywhere path structure
    # Get username from environment or use default
    username = os.environ.get('USERNAME', 'username')
    path = f'/home/{username}/TigerLine'
else:
    # Local development - use current directory
    path = os.path.dirname(os.path.abspath(__file__))

# Add project directory to path
if path not in sys.path:
    sys.path.insert(0, path)

# Set environment variables
os.environ['FLASK_APP'] = 'backend.api.server'
os.environ['FLASK_ENV'] = 'production' if is_pythonanywhere else 'development'

# Import Flask app
from backend.api.server import app

# PythonAnywhere looks for 'application'
application = app

# For local testing
if __name__ == '__main__':
    app.run(debug=not is_pythonanywhere)

