"""
WSGI config for CorporateDock project (cPanel/Passenger compatible).

This module contains the WSGI application used by cPanel's Passenger WSGI.
It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/wsgi/
"""

import sys
import os
from pathlib import Path

# ===========================================================================
# cPanel Passenger Configuration
# ===========================================================================

# Determine the Python interpreter path from virtual environment
# Adjust this path based on your cPanel setup
INTERP = os.path.join(os.environ.get('HOME', ''), 'CorporateDock', 'venv', 'bin', 'python')

# Check if we're using the correct Python interpreter
if sys.executable != INTERP:
    os.execl(INTERP, INTERP, *sys.argv)

# ===========================================================================
# Add project directory to Python path
# ===========================================================================

# Get the project root directory
project_root = os.path.join(os.environ.get('HOME', ''), 'CorporateDock')
sys.path.insert(0, project_root)

# Add the project settings directory to path
sys.path.insert(0, os.path.join(project_root, 'CorporateDock_project'))

# ===========================================================================
# Load environment variables from .env file
# ===========================================================================

from dotenv import load_dotenv
env_path = os.path.join(project_root, '.env')
load_dotenv(env_path)

# ===========================================================================
# Configure Django settings
# ===========================================================================

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'yallamotor_project.settings')

# ===========================================================================
# Get the WSGI application
# ===========================================================================

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
