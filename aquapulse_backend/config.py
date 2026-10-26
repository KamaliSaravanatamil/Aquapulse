"""
AquaPulse Configuration
Environment variables and database configuration
"""

import os
from dotenv import load_dotenv

load_dotenv()

# Flask Configuration
FLASK_ENV = os.getenv("FLASK_ENV", "development")
DEBUG = FLASK_ENV == "development"
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")

# Firebase Configuration
FIREBASE_PROJECT_ID = os.getenv("FIREBASE_PROJECT_ID")

# Server Configuration
SERVER_HOST = os.getenv("SERVER_HOST", "0.0.0.0")
SERVER_PORT = int(os.getenv("SERVER_PORT", 5000))

# CORS Configuration
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*").split(",")

# Device Configuration
DEVICE_TOKEN_EXPIRY = int(os.getenv("DEVICE_TOKEN_EXPIRY", 86400 * 365))  # 1 year

# Print configuration on startup
if DEBUG:
    print("[CONFIG] Firebase project:", FIREBASE_PROJECT_ID or "Application Default")
    print("[CONFIG] Environment:", FLASK_ENV)
