#!/usr/bin/env python
"""
Direct Twilio Test - Bypasses Flask to test SMS directly
"""

from twilio.rest import Client
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get credentials
ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_PHONE = os.getenv("TWILIO_PHONE_NUMBER")
YOUR_PHONE = os.getenv("ALERT_PHONE_NUMBERS")

print("\n" + "="*60)
print("🧪 DIRECT TWILIO TEST")
print("="*60)

print("\n📋 Configuration:")
print(f"   Account SID: {ACCOUNT_SID[:20]}...")
print(f"   Auth Token: {'*' * 10}")
print(f"   Twilio Phone: {TWILIO_PHONE}")
print(f"   Your Phone: {YOUR_PHONE}")

# Validate credentials
if not all([ACCOUNT_SID, AUTH_TOKEN, TWILIO_PHONE, YOUR_PHONE]):
    print("\n❌ ERROR: Missing credentials in .env file!")
    print("   Make sure .env has all 4 variables")
    exit(1)

# Initialize Twilio client
try:
    client = Client(ACCOUNT_SID, AUTH_TOKEN)
    print("\n✅ Twilio client initialized")
except Exception as e:
    print(f"\n❌ Twilio client error: {e}")
    exit(1)

# Send test SMS
try:
    print("\n📤 Sending test SMS...")
    message = client.messages.create(
        body="🌊 AquaPulse Test: System is working! ✅",
        from_=TWILIO_PHONE,
        to=YOUR_PHONE
    )
    
    print(f"✅ SMS SENT SUCCESSFULLY!")
    print(f"   SID: {message.sid}")
    print(f"   Status: {message.status}")
    print(f"   From: {message.from_}")
    print(f"   To: {message.to}")
    print(f"\n📱 Check your phone in 1-2 seconds!")
    
except Exception as e:
    print(f"\n❌ SMS FAILED: {str(e)}")
    print(f"\nTroubleshooting:")
    print(f"   1. Is your phone number verified in Twilio?")
    print(f"   2. Do you have enough trial credits ($14.35)?")
    print(f"   3. Are credentials correct?")

print("\n" + "="*60 + "\n")
