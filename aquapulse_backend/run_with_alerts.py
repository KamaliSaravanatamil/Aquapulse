#!/usr/bin/env python
"""
AquaPulse Backend with SMS Alerts Enabled
Run this instead of server.py to get full alert functionality
"""

import sys
import os
from dotenv import load_dotenv

# Load .env file FIRST before anything else
load_dotenv()

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import Flask app
from server import app, db

# Import alert system
from alert_integration import setup_alert_system
from alert_config import ALERT_PHONE_NUMBERS

def main():
    """Main entry point with alerts"""
    
    print("\n" + "="*70)
    print("🌊 AquaPulse Backend Server - SMS Alerts Edition")
    print("="*70)
    
    print("\n📋 Configuration:")
    print(f"   Host: 0.0.0.0")
    print(f"   Port: 5000")
    print(f"   Database: Firebase Firestore")
    
    print(f"\n📱 SMS Alert System:")
    print(f"   Status: ✅ ENABLED")
    print(f"   Recipients: {len(ALERT_PHONE_NUMBERS)} phone(s)")
    for i, phone in enumerate(ALERT_PHONE_NUMBERS, 1):
        print(f"      {i}. {phone}")
    
    print(f"\n⏰ Scheduled Checks:")
    print(f"   08:00 - Morning check")
    print(f"   14:00 - Afternoon check")
    print(f"   20:00 - Evening check")
    
    print(f"\n📊 API Endpoints:")
    print(f"   GET  /api/alerts/latest - Latest alert")
    print(f"   GET  /api/alerts/history - Alert history")
    print(f"   POST /api/alerts/test - Send test alert")
    print(f"   GET  /api/alerts/settings - Alert settings")
    print(f"   POST /api/alerts/settings - Update settings")
    
    # Initialize alert system
    print(f"\n🚀 Initializing alert system...")
    try:
        scheduler = setup_alert_system(
            app=app,
            db=db,
            phone_numbers=ALERT_PHONE_NUMBERS
        )
        print("✅ Alert system initialized successfully!")
    except Exception as e:
        print(f"⚠️  Warning: Could not initialize alerts: {e}")
        print("   Server will continue without SMS alerts")
        scheduler = None
    
    print("\n" + "="*70)
    print("🌐 Starting Flask Server...")
    print("="*70 + "\n")
    
    # Start Flask app
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=False,  # Important: debug=False for scheduler to work
        use_reloader=False  # Important: disable reloader for scheduler
    )

if __name__ == "__main__":
    main()
