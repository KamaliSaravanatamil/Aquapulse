#!/usr/bin/env python
"""
Simple SMS Endpoint - Direct Approach
Just sends SMS without complex logic
"""

from flask import Flask, jsonify, request
from flask_cors import CORS
from dotenv import load_dotenv
import os
from twilio.rest import Client

# Load environment
load_dotenv()

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Get Twilio credentials
ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_PHONE = os.getenv("TWILIO_PHONE_NUMBER")
YOUR_PHONE = os.getenv("ALERT_PHONE_NUMBERS")

# Initialize Twilio
client = Client(ACCOUNT_SID, AUTH_TOKEN)

# In-memory storage for latest readings
latest_readings = {
    "device_id": "pond_001",
    "ph": 7.0,
    "tds": 0,
    "turbidity": 0,
    "temperature": 25.0,
    "source": "esp32_hardware",
    "timestamp": None
}

@app.route('/test', methods=['GET', 'POST', 'OPTIONS'])
def test_connection():
    """Test endpoint to verify phone connectivity"""
    if request.method == 'OPTIONS':
        return '', 204
    
    return jsonify({
        "success": True,
        "message": "✅ Phone can reach backend!",
        "server_ip": "192.168.29.158",
        "endpoint": "/send-sms-direct available"
    }), 200

@app.route('/sms-test', methods=['GET', 'POST', 'OPTIONS'])
def sms_test():
    """Direct SMS test endpoint - sends SMS and returns result"""
    if request.method == 'OPTIONS':
        return '', 204
    
    try:
        sms_body = "🌊 AquaPulse Test SMS - Direct from phone!"
        
        print(f"📱 Testing SMS: {sms_body}")
        message = client.messages.create(
            body=sms_body,
            from_=TWILIO_PHONE,
            to=YOUR_PHONE
        )
        
        print(f"✅ Test SMS Sent! SID: {message.sid}, Status: {message.status}")
        
        return jsonify({
            "success": True,
            "message": "✅ Test SMS Sent!",
            "message_sid": message.sid,
            "status": message.status,
            "sent_to": YOUR_PHONE
        }), 200
    
    except Exception as e:
        print(f"❌ SMS Test Error: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/data', methods=['POST', 'OPTIONS'])
def receive_sensor_data():
    """Receive sensor data from ESP32 and store it"""
    
    # Handle CORS preflight
    if request.method == 'OPTIONS':
        return '', 204
    
    try:
        data = request.json
        
        # Update latest readings
        global latest_readings
        latest_readings = {
            "device_id": data.get("device_id", "pond_001"),
            "ph": float(data.get("ph", 0)),
            "tds": int(data.get("tds", 0)),
            "turbidity": float(data.get("turbidity", 0)),
            "temperature": float(data.get("temperature", 0)),
            "source": "esp32_hardware",
            "timestamp": data.get("timestamp")
        }
        
        print(f"✅ ESP32 Data Received: pH={latest_readings['ph']}, TDS={latest_readings['tds']}, Temp={latest_readings['temperature']}°C")
        
        return jsonify({
            "success": True,
            "message": "Data received and stored",
            "readings": latest_readings
        }), 200
    
    except Exception as e:
        print(f"❌ Error receiving data: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/readings', methods=['GET'])
def get_readings():
    """Get latest sensor readings for Flutter app"""
    try:
        return jsonify({
            "readings": [latest_readings]
        }), 200
    except Exception as e:
        return jsonify({
            "error": str(e)
        }), 500

@app.route('/send-sms-direct', methods=['POST', 'OPTIONS'])
def send_sms_direct():
    """Send SMS with actual live sensor data"""
    
    # Handle CORS preflight
    if request.method == 'OPTIONS':
        return '', 204
    
    try:
        # Use actual sensor data from latest_readings
        ph = latest_readings.get("ph", 7.0)
        tds = latest_readings.get("tds", 0)
        temp = latest_readings.get("temperature", 25.0)
        turbidity = latest_readings.get("turbidity", 0)
        
        # Determine water health status
        if 6.5 <= ph <= 8.0 and tds < 500 and turbidity < 10:
            health_status = "✅ Excellent"
        elif 6.0 <= ph <= 8.5 and tds < 1000 and turbidity < 20:
            health_status = "✅ Good"
        else:
            health_status = "⚠️ Check Required"
        
        # Create SMS message with live data - SIMPLIFIED for instant delivery
        sms_body = f"AquaPulse: pH {ph:.1f} | TDS {tds} ppm | Temp {temp:.1f}C | Status: OK"
        
        message = client.messages.create(
            body=sms_body,
            from_=TWILIO_PHONE,
            to=YOUR_PHONE
        )
        
        print(f"📱 SMS Sent with live data: pH={ph}, TDS={tds}, Temp={temp}°C")
        
        return jsonify({
            "success": True,
            "message_sid": message.sid,
            "status": message.status,
            "sent_to": YOUR_PHONE,
            "data": {
                "ph": ph,
                "tds": tds,
                "temperature": temp,
                "turbidity": turbidity
            }
        })
    
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

if __name__ == '__main__':
    print(f"\n{'='*60}")
    print("📱 Simple SMS Direct Server (CORS Enabled)")
    print(f"{'='*60}")
    print(f"\nTest with:")
    print(f"  curl -X POST http://192.168.29.158:5000/send-sms-direct")
    print(f"\nOr PowerShell:")
    print(f"  Invoke-WebRequest -Uri 'http://192.168.29.158:5000/send-sms-direct' -Method POST")
    print(f"\nFlutter/Browser:")
    print(f"  Click SMS button in app (CORS enabled)")
    print(f"\n{'='*60}\n")
    
    app.run(host='0.0.0.0', port=5000, debug=False)
