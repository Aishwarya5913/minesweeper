"""
api/index.py
============
Vercel Serverless Function entry point.
Exposes the Flask app for Vercel's Python runtime.
"""

import sys
import os

# Add root project directory to sys.path so sibling modules can be imported
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from app import app

# Vercel looks for the WSGI application variable named 'app'
# This allows Vercel to route all /api/* requests to Flask
