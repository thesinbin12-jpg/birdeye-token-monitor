# Vercel entry point - re-export from api/index.py
import sys
import os

# Add project root to path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Import and re-export the Flask app from api/index.py
from api.index import app

# Export for Vercel
__all__ = ['app']
