#!/usr/bin/env python
"""
AquaPulse Alert Configuration
Edit this file to configure your SMS alerts
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# ==================== TWILIO CONFIGURATION ====================

TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "your_account_sid_here")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "your_auth_token_here")
TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER", "+1234567890")

# ==================== ALERT RECIPIENTS ====================

# Get multiple phone numbers from environment (comma-separated)
ALERT_PHONE_NUMBERS_STR = os.getenv("ALERT_PHONE_NUMBERS", "+91XXXXXXXXXX")

# Parse comma-separated phone numbers into a list
ALERT_PHONE_NUMBERS = [
    p.strip() for p in ALERT_PHONE_NUMBERS_STR.split(",")
    if p.strip()
]

# ==================== SCHEDULER CONFIGURATION ====================

# Alert check times (24-hour format, HH:MM)
ALERT_TIMES = [
    os.getenv("ALERT_TIME_1", "08:00"),  # Morning
    os.getenv("ALERT_TIME_2", "14:00"),  # Afternoon
    os.getenv("ALERT_TIME_3", "20:00"),  # Evening
]

# ==================== WATER QUALITY THRESHOLDS ====================

THRESHOLDS = {
    # Safe ranges (normal operation, no alert)
    "ph_min": float(os.getenv("PH_MIN", "6.5")),
    "ph_max": float(os.getenv("PH_MAX", "8.5")),
    "tds_normal": int(os.getenv("TDS_MAX", "300")),
    "turbidity_normal": float(os.getenv("TURBIDITY_MAX", "5")),
    "temp_min": int(os.getenv("TEMP_MIN", "15")),
    "temp_max": int(os.getenv("TEMP_MAX", "30")),
    
    # Warning ranges
    "ph_critical_min": float(os.getenv("PH_CRITICAL_MIN", "6.0")),
    "ph_critical_max": float(os.getenv("PH_CRITICAL_MAX", "9.0")),
    "tds_warning": int(os.getenv("TDS_WARNING", "500")),
    "turbidity_warning": float(os.getenv("TURBIDITY_WARNING", "10")),
    "temp_critical_min": int(os.getenv("TEMP_CRITICAL_MIN", "10")),
    "temp_critical_max": int(os.getenv("TEMP_CRITICAL_MAX", "35")),
}

# ==================== DISPLAY CONFIGURATION ====================

print("\n" + "="*60)
print("🌊 AquaPulse Alert Configuration")
print("="*60)

print(f"\n📱 Phone Numbers for Alerts:")
for i, phone in enumerate(ALERT_PHONE_NUMBERS, 1):
    print(f"   {i}. {phone}")

print(f"\n⏰ Alert Check Times:")
for time in ALERT_TIMES:
    print(f"   • {time}")

print(f"\n📊 Water Quality Thresholds:")
print(f"   Safe Range:")
print(f"      pH: {THRESHOLDS['ph_min']} - {THRESHOLDS['ph_max']}")
print(f"      TDS: < {THRESHOLDS['tds_normal']} ppm")
print(f"      Turbidity: < {THRESHOLDS['turbidity_normal']} NTU")
print(f"      Temperature: {THRESHOLDS['temp_min']} - {THRESHOLDS['temp_max']}°C")

print(f"\n   Warning Range:")
print(f"      pH: {THRESHOLDS['ph_critical_min']} - {THRESHOLDS['ph_critical_max']}")
print(f"      TDS: < {THRESHOLDS['tds_warning']} ppm")
print(f"      Turbidity: < {THRESHOLDS['turbidity_warning']} NTU")
print(f"      Temperature: {THRESHOLDS['temp_critical_min']} - {THRESHOLDS['temp_critical_max']}°C")

print("\n" + "="*60 + "\n")

if __name__ == "__main__":
    print("✅ Alert configuration loaded successfully")
    print(f"   SMS Enabled: {bool(TWILIO_ACCOUNT_SID != 'your_account_sid_here')}")
    print(f"   Recipients: {len(ALERT_PHONE_NUMBERS)}")
