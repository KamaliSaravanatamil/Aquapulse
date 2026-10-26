"""
AquaPulse SMS Notification Service
Sends SMS alerts using Twilio when water quality issues are detected
"""

from twilio.rest import Client
from datetime import datetime
import os

# ==================== TWILIO CONFIGURATION ====================

# Get credentials from environment variables (secure method)
# Or hardcode them here for testing
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "your_account_sid_here")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "your_auth_token_here")
TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER", "+1234567890")

# Multiple phone numbers to receive alerts (comma-separated in env)
ALERT_PHONE_NUMBERS = []
phone_env = os.getenv("ALERT_PHONE_NUMBERS", "+917358417822")
if phone_env:
    ALERT_PHONE_NUMBERS = [p.strip() for p in phone_env.split(",")]

# Fallback if no env variable
if not ALERT_PHONE_NUMBERS:
    ALERT_PHONE_NUMBERS = ["+917358417822"]  # Default

# Initialize Twilio client
try:
    twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
    TWILIO_AVAILABLE = True
except Exception as e:
    print(f"⚠️  Twilio not configured: {e}")
    TWILIO_AVAILABLE = False

# ==================== SMS SENDING ====================

def send_sms(message: str, phone_numbers: list = None) -> list:
    """
    Send SMS alert to multiple recipients using Twilio
    
    Args:
        message: SMS message content (max 160 characters recommended)
        phone_numbers: List of recipient phones (if None, uses ALERT_PHONE_NUMBERS)
    
    Returns:
        List of dicts with success status for each recipient
    """
    if not TWILIO_AVAILABLE:
        return [{
            "success": False,
            "error": "Twilio not configured",
            "timestamp": datetime.now().isoformat()
        }]
    
    recipients = phone_numbers or ALERT_PHONE_NUMBERS
    results = []
    
    for recipient in recipients:
        try:
            # Send SMS
            sms = twilio_client.messages.create(
                body=message,
                from_=TWILIO_PHONE_NUMBER,
                to=recipient
            )
            
            print(f"✅ SMS sent successfully!")
            print(f"   To: {recipient}")
            print(f"   SID: {sms.sid}")
            print(f"   Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            
            results.append({
                "success": True,
                "message_sid": sms.sid,
                "phone": recipient,
                "timestamp": datetime.now().isoformat()
            })
        
        except Exception as e:
            print(f"❌ SMS to {recipient} Failed: {str(e)}")
            results.append({
                "success": False,
                "error": str(e),
                "phone": recipient,
                "timestamp": datetime.now().isoformat()
            })
    
    return results

# ==================== POND HEALTH STATUS ====================

def generate_pond_status_message(ph: float, tds: int, turbidity: float, temperature: float) -> str:
    """
    Generate pond health status SMS message
    
    Returns: SMS text (optimized for 160 char limit)
    """
    
    # Determine health status
    if 6.5 <= ph <= 8.5 and tds < 300 and turbidity < 5 and 15 <= temperature <= 30:
        status = "✅ HEALTHY"
        emoji = "🟢"
    elif 6.0 <= ph <= 9.0 and tds < 500 and turbidity < 10 and 10 <= temperature <= 35:
        status = "⚠️ WARNING"
        emoji = "🟡"
    else:
        status = "❌ CRITICAL"
        emoji = "🔴"
    
    # Create message (keep short for SMS)
    message = f"{emoji} AquaPulse: {status}\npH:{ph:.1f} TDS:{tds} Turb:{turbidity:.1f} T:{temperature:.1f}°C"
    
    return message

def generate_daily_report_message(ph: float, tds: int, turbidity: float, temperature: float, time_of_day: str = "Daily") -> str:
    """
    Generate daily pond health status report (friendly format)
    
    Args:
        ph, tds, turbidity, temperature: Sensor readings
        time_of_day: "Morning", "Afternoon", or "Evening"
    
    Returns: SMS message with daily status
    """
    
    # Determine health status
    if 6.5 <= ph <= 8.5 and tds < 300 and turbidity < 5 and 15 <= temperature <= 30:
        health = "Good"
        health_emoji = "✅"
    elif 6.0 <= ph <= 9.0 and tds < 500 and turbidity < 10 and 10 <= temperature <= 35:
        health = "Fair - Monitor"
        health_emoji = "⚠️"
    else:
        health = "Poor - Action Needed"
        health_emoji = "❌"
    
    # Create friendly report message
    time_str = f"{time_of_day} Report" if time_of_day else "Daily Report"
    message = f"""🌊 AquaPulse {time_str}

Pond Health: {health_emoji} {health}

📊 Current Status:
pH: {ph:.1f}
TDS: {tds} ppm
Turbidity: {turbidity:.1f} NTU
Temp: {temperature:.1f}°C

✅ All readings monitored. Stay updated!"""
    
    return message

# ==================== DETAILED STATUS REPORT ====================

def generate_detailed_report(ph: float, tds: int, turbidity: float, temperature: float) -> str:
    """
    Generate detailed pond health report
    Can be sent via email or logged
    """
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    report = f"""
╔════════════════════════════════════╗
║   🌊 AquaPulse Pond Status Report   ║
╚════════════════════════════════════╝

📅 Time: {timestamp}

📊 CURRENT READINGS:
   pH Level:        {ph:.2f}
   TDS:             {tds} ppm
   Turbidity:       {turbidity:.2f} NTU
   Temperature:     {temperature:.2f}°C

✅ SAFE RANGES:
   pH:              6.5 - 8.5
   TDS:             < 300 ppm
   Turbidity:       < 5 NTU
   Temperature:     15 - 30°C

⚠️  WARNINGS if exceeded
❌ CRITICAL if way out of range

Generated by AquaPulse IoT System
"""
    
    return report

# ==================== ALERT DECISION ENGINE ====================

def should_send_alert(ph: float, tds: int, turbidity: float, temperature: float) -> tuple:
    """
    Determine if alert should be sent
    
    Returns: (should_alert: bool, alert_level: str, message: str)
    """
    
    issues = []
    alert_level = "NORMAL"
    
    # Check pH
    if ph < 6.0 or ph > 9.0:
        issues.append(f"pH CRITICAL: {ph}")
        alert_level = "CRITICAL"
    elif ph < 6.5 or ph > 8.5:
        issues.append(f"pH WARNING: {ph}")
        if alert_level == "NORMAL":
            alert_level = "WARNING"
    
    # Check TDS
    if tds >= 500:
        issues.append(f"TDS CRITICAL: {tds} ppm")
        alert_level = "CRITICAL"
    elif tds >= 300:
        issues.append(f"TDS WARNING: {tds} ppm")
        if alert_level == "NORMAL":
            alert_level = "WARNING"
    
    # Check Turbidity
    if turbidity >= 10:
        issues.append(f"Turbidity CRITICAL: {turbidity}")
        alert_level = "CRITICAL"
    elif turbidity >= 5:
        issues.append(f"Turbidity WARNING: {turbidity}")
        if alert_level == "NORMAL":
            alert_level = "WARNING"
    
    # Check Temperature
    if temperature < 10 or temperature > 35:
        issues.append(f"Temp CRITICAL: {temperature}°C")
        alert_level = "CRITICAL"
    elif temperature < 15 or temperature > 30:
        issues.append(f"Temp WARNING: {temperature}°C")
        if alert_level == "NORMAL":
            alert_level = "WARNING"
    
    should_alert = len(issues) > 0
    
    if should_alert:
        message = f"🌊 AquaPulse {alert_level}: " + " | ".join(issues[:2])  # Keep SMS short
    else:
        message = "🌊 AquaPulse: Pond health is GOOD ✅"
    
    return should_alert, alert_level, message

# ==================== MAIN ALERT FUNCTION ====================

def send_pond_status_sms(ph: float, tds: int, turbidity: float, temperature: float, 
                         phone_numbers: list = None, always_send: bool = False) -> dict:
    """
    Main function to send pond status SMS to multiple recipients
    
    Args:
        ph, tds, turbidity, temperature: Current sensor readings
        phone_numbers: List of recipients (optional)
        always_send: If True, send regardless of issues
    
    Returns:
        Result dict with status
    """
    
    should_send, alert_level, message = should_send_alert(ph, tds, turbidity, temperature)
    
    # Send if there are issues OR if always_send is True
    if should_send or always_send:
        results = send_sms(message, phone_numbers)
        return {
            "success": all(r["success"] for r in results),
            "sent_to": [r.get("phone", "unknown") for r in results],
            "results": results,
            "alert_level": alert_level,
            "reading": {
                "ph": ph,
                "tds": tds,
                "turbidity": turbidity,
                "temperature": temperature
            },
            "timestamp": datetime.now().isoformat()
        }
    else:
        return {
            "success": False,
            "reason": "No alert needed - pond is healthy",
            "alert_level": "NORMAL",
            "timestamp": datetime.now().isoformat()
        }

# ==================== TEST FUNCTION ====================

def test_sms_service():
    """Test SMS service with sample data"""
    print("\n" + "="*50)
    print("🧪 AquaPulse SMS Service Test")
    print("="*50)
    
    # Test data
    test_readings = [
        {"name": "HEALTHY", "ph": 7.2, "tds": 250, "turbidity": 2.5, "temp": 25},
        {"name": "WARNING", "ph": 6.2, "tds": 350, "turbidity": 8, "temp": 28},
        {"name": "CRITICAL", "ph": 5.5, "tds": 600, "turbidity": 15, "temp": 40},
    ]
    
    for test in test_readings:
        print(f"\n📊 Test Case: {test['name']}")
        print(f"   pH: {test['ph']}, TDS: {test['tds']}, Turbidity: {test['turbidity']}, Temp: {test['temp']}")
        
        should_send, level, msg = should_send_alert(test['ph'], test['tds'], test['turbidity'], test['temp'])
        print(f"   Should Send: {should_send}")
        print(f"   Alert Level: {level}")
        print(f"   Message: {msg}")
    
    print("\n" + "="*50)
    print("✅ SMS Service test complete!")
    print("="*50 + "\n")

# ==================== EXAMPLE USAGE ====================

if __name__ == "__main__":
    # Test SMS service
    test_sms_service()
    
    # Uncomment to send actual SMS (requires valid Twilio credentials)
    # result = send_pond_status_sms(ph=6.2, tds=350, turbidity=8, temperature=28)
    # print("\nSMS Result:", result)
