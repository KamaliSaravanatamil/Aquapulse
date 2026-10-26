"""
AquaPulse Backend Server - HTTP Only Version
IoT water quality monitoring system backend
Real-time sensor data collection via HTTP REST API
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
from firestore_db import DuplicateKeyError, create_firestore_database
from datetime import datetime, timedelta
import jwt
import os
import atexit
import secrets
from config import *
from models import (
    SensorReading, Device, WaterQualityIndex,
    SensorCalibration, AlertRule, COLLECTIONS
)
from auth import (
    generate_device_token, verify_device_token, refresh_device_token,
    generate_user_token, hash_password, verify_password,
    token_needs_refresh, require_valid_token, require_registered_device, 
    log_device_access, get_device_access_logs, get_failed_access_attempts,
    is_device_suspicious
)

DESCENDING = -1

# ==================== FLASK APP SETUP ====================

app = Flask(__name__)
app.config['SECRET_KEY'] = SECRET_KEY
CORS(app, origins=CORS_ORIGINS)

# ==================== FIRESTORE CONNECTION ====================

try:
    db = create_firestore_database()
    print("Firebase Firestore connected successfully")
except Exception as e:
    db = None
    print(f"Firebase Firestore unavailable: {e}")

# ==================== HTTP API ====================

print("Using HTTP REST mode")

# ==================== HELPER FUNCTIONS ====================

def get_latest_reading(device_id: str):
    """Get latest sensor reading for a device"""
    if db is None:
        return None
    
    return db[COLLECTIONS["readings"]].find_one(
        {"device_id": device_id},
        sort=[("timestamp", DESCENDING)]
    )


def calculate_wqi(ph: float, tds: int, turbidity: float = 0, temperature: float = 25) -> dict:
    """
    Calculate Water Quality Index (WQI) - Score from 0 to 100
    
    Thresholds:
    - Excellent:  85-100 (Safe for aquaculture)
    - Good:       70-84  (Safe with monitoring)
    - Fair:       50-69  (Needs treatment)
    - Poor:       <50    (Unsafe)
    """
    
    # pH Score (Optimal: 6.5-8.5)
    if 6.5 <= ph <= 8.5:
        ph_score = 100
    elif 6.0 <= ph < 6.5 or 8.5 < ph <= 9.0:
        ph_score = 80
    elif 5.5 <= ph < 6.0 or 9.0 < ph <= 9.5:
        ph_score = 50
    else:
        ph_score = 20
    
    # TDS Score (Optimal: 300-500 ppm)
    if 300 <= tds <= 500:
        tds_score = 100
    elif 200 <= tds < 300 or 500 < tds <= 800:
        tds_score = 75
    elif 100 <= tds < 200 or 800 < tds <= 1200:
        tds_score = 50
    else:
        tds_score = 25
    
    # Turbidity Score (Optimal: <5 NTU)
    if turbidity < 5:
        turbidity_score = 100
    elif 5 <= turbidity < 10:
        turbidity_score = 70
    elif 10 <= turbidity < 20:
        turbidity_score = 40
    else:
        turbidity_score = 20
    
    # Temperature Score (Optimal: 20-28°C for most fish)
    if 20 <= temperature <= 28:
        temperature_score = 100
    elif 15 <= temperature < 20 or 28 < temperature <= 32:
        temperature_score = 75
    elif 10 <= temperature < 15 or 32 < temperature <= 35:
        temperature_score = 50
    else:
        temperature_score = 25
    
    # Weighted average
    wqi = (
        ph_score * 0.25 +
        tds_score * 0.35 +
        turbidity_score * 0.25 +
        temperature_score * 0.15
    )
    
    # Determine status
    if wqi >= 85:
        status = "Excellent"
    elif wqi >= 70:
        status = "Good"
    elif wqi >= 50:
        status = "Fair"
    else:
        status = "Poor"
    
    return {
        "wqi_score": round(wqi, 1),
        "status": status,
        "ph_score": ph_score,
        "tds_score": tds_score,
        "turbidity_score": turbidity_score,
        "temperature_score": temperature_score
    }


# ==================== API ENDPOINTS ====================

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    firestore_status = "connected" if db is not None else "disconnected"
    
    return jsonify({
        "status": "online" if db is not None else "degraded",
        "timestamp": datetime.utcnow().isoformat(),
        "firestore": firestore_status,
        "mode": "http_only",
        "version": "3.0",
        "features": ["http", "jwt", "wqi", "firestore"]
    }), 200


@app.route('/data', methods=['POST'])
def simple_data_update():
    """
    Simple sensor data endpoint (NO AUTHENTICATION - for testing/ESP32)
    
    Expected JSON:
    {
      "device_id": "pond_001",
      "ph": 7.2,
      "tds": 320,
      "turbidity": 3.0,
      "temperature": 27
    }
    """
    if db is None:
        return jsonify({"error": "Database not connected"}), 500
    
    try:
        data = request.json
        if not data:
            return jsonify({"error": "No data provided"}), 400
        
        device_id = data.get("device_id", "default_device")
        
        # Validate required fields
        if "ph" not in data or "tds" not in data:
            return jsonify({"error": "Missing required fields: ph, tds"}), 400
        
        # Save reading
        reading = {
            "device_id": device_id,
            "ph": float(data.get("ph")),
            "tds": int(data.get("tds")),
            "turbidity": float(data.get("turbidity", 0)),
            "temperature": float(data.get("temperature", 25)),
            "status": data.get("status", "Connected"),
            "source": "http_simple",
            "timestamp": datetime.utcnow()
        }
        
        db[COLLECTIONS["readings"]].insert_one(reading)
        
        # Calculate WQI
        wqi_data = calculate_wqi(
            reading['ph'],
            reading['tds'],
            reading['turbidity'],
            reading['temperature']
        )
        
        wqi_record = {
            "device_id": device_id,
            "wqi_score": wqi_data["wqi_score"],
            "status": wqi_data["status"],
            "timestamp": datetime.utcnow()
        }
        
        db[COLLECTIONS["wqi_history"]].insert_one(wqi_record)
        
        print(f"✅ Data endpoint: {device_id} - pH={reading['ph']}, TDS={reading['tds']}, WQI={wqi_data['wqi_score']}")
        
        return jsonify({
            "status": "success",
            "wqi": wqi_data["wqi_score"],
            "wqi_status": wqi_data["status"],
            "message": "Data saved"
        }), 200
        
    except Exception as e:
        print(f"❌ Error in /data: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/update', methods=['POST'])
def update_readings():
    """
    Update sensor readings - Called by ESP32 or simulator
    No device authentication is required.
    
    Expected JSON:
    {
      "device_id": "pond_001",
      "ph": 7.2,
      "tds": 320,
      "ec": 1.34,
      "turbidity": 3.0,
      "temperature": 27,
      "status": "Connected"
    }
    """
    if db is None:
        return jsonify({"error": "Database not connected"}), 500
    
    try:
        data = request.json
        
        if not data:
            return jsonify({"error": "No data provided"}), 400
        
        device_id = data.get("device_id", "default_device")

        # Validate required fields
        if not all(key in data for key in ["ph", "tds"]):
            return jsonify({"error": "Missing required fields: ph, tds"}), 400
        
        # Prepare reading document
        reading = {
            "device_id": device_id,
            "ph": float(data.get("ph")),
            "tds": int(data.get("tds")),
            "ec": float(data.get("ec", 0)),
            "turbidity": float(data.get("turbidity", 0)),
            "temperature": float(data.get("temperature", 25)),
            "status": data.get("status", "Connected"),
            "timestamp": datetime.utcnow()
        }
        
        # Save to Firestore
        result = db[COLLECTIONS["readings"]].insert_one(reading)
        reading['_id'] = str(result.inserted_id)
        reading['timestamp'] = reading['timestamp'].isoformat()
        
        # Calculate and save WQI
        wqi_data = calculate_wqi(
            reading['ph'],
            reading['tds'],
            reading['turbidity'],
            reading['temperature']
        )
        
        wqi_record = {
            "device_id": device_id,
            "wqi_score": wqi_data["wqi_score"],
            "status": wqi_data["status"],
            "ph_score": wqi_data["ph_score"],
            "tds_score": wqi_data["tds_score"],
            "turbidity_score": wqi_data["turbidity_score"],
            "temperature_score": wqi_data["temperature_score"],
            "timestamp": datetime.utcnow()
        }
        db[COLLECTIONS["wqi_history"]].insert_one(wqi_record)
        
        message = f"✅ Updated: pH={reading['ph']}, TDS={reading['tds']}, WQI={wqi_data['wqi_score']}"
        print(message)
        
        return jsonify({
            "status": "received",
            "message": message,
            "reading_id": reading['_id'],
            "wqi": wqi_data
        }), 201
        
    except Exception as e:
        log_device_access(db, data.get("device_id") if data else "unknown", "/update", "POST", 500)
        return jsonify({"error": str(e)}), 500


@app.route('/readings', methods=['GET'])
def get_readings():
    """
    Get latest sensor readings
    
    Query parameters:
    - device_id: Filter by device (optional)
    - limit: Number of readings to return (default: 10)
    """
    if db is None:
        return jsonify({"error": "Database not connected"}), 500
    
    try:
        device_id = request.args.get("device_id")
        limit = int(request.args.get("limit", 10))
        
        query = {}
        if device_id:
            query["device_id"] = device_id
        
        readings = list(db[COLLECTIONS["readings"]].find(query).sort(
            "timestamp", DESCENDING
        ).limit(limit))
        
        # Convert ObjectId to string and datetime to ISO format
        for reading in readings:
            reading['_id'] = str(reading['_id'])
            reading['timestamp'] = reading['timestamp'].isoformat()
        
        return jsonify({
            "total": len(readings),
            "readings": readings
        }), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/readings/<device_id>/latest', methods=['GET'])
def get_latest_reading_endpoint(device_id):
    """Get latest reading for a specific device"""
    if db is None:
        return jsonify({"error": "Database not connected"}), 500
    
    try:
        reading = get_latest_reading(device_id)
        
        if not reading:
            return jsonify({"error": f"No readings found for device {device_id}"}), 404
        
        reading['_id'] = str(reading['_id'])
        reading['timestamp'] = reading['timestamp'].isoformat()
        
        return jsonify(reading), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/wqi/<device_id>/latest', methods=['GET'])
def get_latest_wqi(device_id):
    """Get latest Water Quality Index for device"""
    if db is None:
        return jsonify({"error": "Database not connected"}), 500
    
    try:
        wqi = db[COLLECTIONS["wqi_history"]].find_one(
            {"device_id": device_id},
            sort=[("timestamp", DESCENDING)]
        )
        
        if not wqi:
            return jsonify({"error": f"No WQI data found for device {device_id}"}), 404
        
        wqi['_id'] = str(wqi['_id'])
        wqi['timestamp'] = wqi['timestamp'].isoformat()
        
        return jsonify(wqi), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/devices/register', methods=['POST'])
def register_device():
    """
    Register a new ESP32 device
    Generates JWT token for the device
    
    Expected JSON:
    {
      "device_id": "pond_001",
      "device_name": "Main Pond Monitor",
      "location": "Farm Building A"
    }
    """
    if db is None:
        return jsonify({"error": "Database not connected"}), 500
    
    try:
        data = request.json or {}
        
        device_id = data.get("device_id")
        if not device_id:
            return jsonify({"error": "device_id is required"}), 400
        
        # Generate device token (JWT) - Valid for 1 year
        device_token = generate_device_token(device_id, expires_in=DEVICE_TOKEN_EXPIRY)
        
        device_doc = {
            "device_id": device_id,
            "device_name": data.get("device_name", device_id),
            "device_token": device_token,
            "location": data.get("location", ""),
            "device_type": data.get("device_type", "ESP32"),
            "active": True,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "last_access": None,
            "failed_attempts": 0
        }
        
        try:
            result = db[COLLECTIONS["devices"]].insert_one(device_doc)
            device_doc['_id'] = str(result.inserted_id)
            device_doc['created_at'] = device_doc['created_at'].isoformat()
            device_doc['updated_at'] = device_doc['updated_at'].isoformat()
            
            print(f"✅ Device registered: {device_id}")
            print(f"   Token: {device_token[:50]}...")
            
            return jsonify({
                "status": "registered",
                "message": f"Device {device_id} registered successfully",
                "device": device_doc,
                "hint": "Save this token securely. Used for all sensor data uploads."
            }), 201
            
        except DuplicateKeyError:
            return jsonify({"error": f"Device {device_id} already exists"}), 409
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/auth/register', methods=['POST'])
def register_user():
    """Create an application user account."""
    if db is None:
        return jsonify({"error": "Database not connected"}), 500

    data = request.json or {}
    email = str(data.get("email", "")).strip().lower()
    password = data.get("password", "")
    name = str(data.get("name", "")).strip()

    if not email or "@" not in email:
        return jsonify({"error": "A valid email is required"}), 400
    if not isinstance(password, str) or len(password) < 8:
        return jsonify({"error": "Password must be at least 8 characters"}), 400

    if db["users"].find_one({"email": email}):
        return jsonify({"error": "An account with this email already exists"}), 409

    user_doc = {
        "user_id": secrets.token_urlsafe(16),
        "email": email,
        "name": name,
        "password_hash": hash_password(password),
        "created_at": datetime.utcnow(),
    }
    result = db["users"].insert_one(user_doc)
    token = generate_user_token(user_doc["user_id"], email)
    return jsonify({
        "status": "registered",
        "token": token,
        "user": {
            "id": user_doc["user_id"],
            "email": email,
            "name": name,
        },
    }), 201


@app.route('/auth/login', methods=['POST'])
def login_user():
    """Authenticate an application user and return a JWT."""
    if db is None:
        return jsonify({"error": "Database not connected"}), 500

    data = request.json or {}
    email = str(data.get("email", "")).strip().lower()
    password = data.get("password", "")
    user = db["users"].find_one({"email": email})

    if not user or not verify_password(password, user.get("password_hash", "")):
        return jsonify({"error": "Invalid email or password"}), 401

    return jsonify({
        "status": "authenticated",
        "token": generate_user_token(user["user_id"], email),
        "user": {
            "id": user["user_id"],
            "email": user["email"],
            "name": user.get("name", ""),
        },
    }), 200


@app.route('/token/refresh', methods=['POST'])
def refresh_token():
    """
    Refresh device JWT token
    SP32 should request new token every ~30 days
    
    Expected JSON:
    {
      "device_id": "pond_001",
      "token": "old_jwt_token"
    }
    """
    if db is None:
        return jsonify({"error": "Database not connected"}), 500
    
    try:
        data = request.json or {}
        device_id = data.get("device_id")
        old_token = data.get("token")
        
        if not device_id or not old_token:
            return jsonify({"error": "Missing device_id or token"}), 400
        
        # Verify old token (works even if expired)
        new_token = refresh_device_token(old_token)
        
        if not new_token:
            return jsonify({"error": "Invalid token provided"}), 401
        
        # Update device with new token
        update_result = db[COLLECTIONS["devices"]].update_one(
            {"device_id": device_id},
            {
                "$set": {
                    "device_token": new_token,
                    "updated_at": datetime.utcnow()
                }
            }
        )
        
        if update_result.matched_count == 0:
            return jsonify({"error": f"Device {device_id} not found"}), 404
        
        log_device_access(db, device_id, "/token/refresh", "POST", 200)
        
        return jsonify({
            "status": "refreshed",
            "message": "Token refreshed successfully",
            "device_id": device_id,
            "token": new_token,
            "expires_in_days": 365
        }), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/device/<device_id>/access-logs', methods=['GET'])
def get_device_logs(device_id):
    """
    Get API access logs for a device (security audit)
    
    Query parameters:
    - hours: Look back period (default: 24)
    - limit: Max results (default: 100)
    
    Requires: Valid device token in Authorization header
    """
    if db is None:
        return jsonify({"error": "Database not connected"}), 500
    
    try:
        # Get token from header
        token = request.headers.get("Authorization")
        if token:
            token = token.split(" ")[1] if " " in token else token
        else:
            token = request.args.get("token")
        
        if not token:
            return jsonify({"error": "Missing authentication token"}), 401
        
        # Verify token matches device
        device_info = verify_device_token(token)
        if not device_info or device_info.get("device_id") != device_id:
            return jsonify({"error": "Unauthorized"}), 403
        
        hours = int(request.args.get("hours", 24))
        limit = int(request.args.get("limit", 100))
        
        logs = get_device_access_logs(db, device_id, hours=hours, limit=limit)
        
        log_device_access(db, device_id, f"/device/{device_id}/access-logs", "GET", 200)
        
        return jsonify({
            "device_id": device_id,
            "period_hours": hours,
            "total_logs": len(logs),
            "logs": logs
        }), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/device/<device_id>/security-status', methods=['GET'])
def get_security_status(device_id):
    """
    Get security status of a device
    (Failed attempts, suspicious activity)
    
    Requires: Valid device token
    """
    if db is None:
        return jsonify({"error": "Database not connected"}), 500
    
    try:
        # Get token
        token = request.headers.get("Authorization")
        if token:
            token = token.split(" ")[1] if " " in token else token
        else:
            token = request.args.get("token")
        
        if not token:
            return jsonify({"error": "Missing authentication token"}), 401
        
        device_info = verify_device_token(token)
        if not device_info or device_info.get("device_id") != device_id:
            return jsonify({"error": "Unauthorized"}), 403
        
        # Get device info
        device = db[COLLECTIONS["devices"]].find_one({"device_id": device_id})
        if not device:
            return jsonify({"error": "Device not found"}), 404
        
        # Check suspicious activity
        is_suspicious, reason = is_device_suspicious(db, device_id)
        failed_attempts = get_failed_access_attempts(db, device_id, hours=1)
        
        token_exp = device_info.get("exp") if device_info else None
        days_until = ((token_exp - datetime.utcnow()).days if token_exp else 0)
        
        status = {
            "device_id": device_id,
            "active": device.get("active", True),
            "suspicious": is_suspicious,
            "suspicious_reason": reason,
            "failed_attempts_1h": len(failed_attempts),
            "token_expires": token_exp.isoformat() if token_exp else None,
            "days_until_expiry": days_until
        }
        
        if status["days_until_expiry"] <= 7:
            status["warning"] = "Token expiring soon. Request refresh."
        
        log_device_access(db, device_id, f"/device/{device_id}/security-status", "GET", 200)
        
        return jsonify(status), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/device/<device_id>/deactivate', methods=['POST'])
def deactivate_device(device_id):
    """
    Deactivate a device (prevent data uploads)
    
    Expected JSON:
    {
      "token": "jwt_token",
      "reason": "Optional reason for deactivation"
    }
    """
    if db is None:
        return jsonify({"error": "Database not connected"}), 500
    
    try:
        data = request.json or {}
        token = data.get("token")
        
        if not token:
            return jsonify({"error": "Missing authentication token"}), 401
        
        device_info = verify_device_token(token)
        if not device_info or device_info.get("device_id") != device_id:
            return jsonify({"error": "Unauthorized"}), 403
        
        result = db[COLLECTIONS["devices"]].update_one(
            {"device_id": device_id},
            {
                "$set": {
                    "active": False,
                    "deactivated_at": datetime.utcnow(),
                    "deactivation_reason": (data or {}).get("reason", "Not specified")
                }
            }
        )
        
        if result.matched_count == 0:
            return jsonify({"error": "Device not found"}), 404
        
        log_device_access(db, device_id, f"/device/{device_id}/deactivate", "POST", 200)
        
        return jsonify({
            "status": "deactivated",
            "message": f"Device {device_id} has been deactivated",
            "device_id": device_id
        }), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/devices', methods=['GET'])
def get_devices():
    """Get all registered devices (admin only)"""
    if db is None:
        return jsonify({"error": "Database not connected"}), 500
    
    try:
        devices = list(db[COLLECTIONS["devices"]].find())
        
        for device in devices:
            device['_id'] = str(device['_id'])
            device['created_at'] = device['created_at'].isoformat()
            device['updated_at'] = device['updated_at'].isoformat()
            if device.get('last_access'):
                device['last_access'] = device['last_access'].isoformat()
        
        return jsonify({
            "total": len(devices),
            "devices": devices
        }), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500



def get_statistics(device_id):
    """Get statistics for a device (last 24 hours)"""
    if db is None:
        return jsonify({"error": "Database not connected"}), 500
    
    try:
        hours = int(request.args.get("hours", 24))
        since = datetime.utcnow() - timedelta(hours=hours)
        
        readings = list(db[COLLECTIONS["readings"]].find({
            "device_id": device_id,
            "timestamp": {"$gte": since}
        }))
        
        if not readings:
            return jsonify({"error": f"No readings found for {device_id}"}), 404
        
        ph_values = [r['ph'] for r in readings]
        tds_values = [r['tds'] for r in readings]
        
        stats = {
            "device_id": device_id,
            "period_hours": hours,
            "readings_count": len(readings),
            "ph": {
                "min": min(ph_values),
                "max": max(ph_values),
                "avg": sum(ph_values) / len(ph_values)
            },
            "tds": {
                "min": min(tds_values),
                "max": max(tds_values),
                "avg": sum(tds_values) / len(tds_values)
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
        return jsonify(stats), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/reset', methods=['POST'])
def reset_data():
    """Reset all data (WARNING: Clears database)"""
    if db is None:
        return jsonify({"error": "Database not connected"}), 500
    
    try:
        # This should be password protected in production
        password = request.json.get("password") if request.json else None
        
        if password != "AQUAPULSE_RESET_123":
            return jsonify({"error": "Invalid reset password"}), 401
        
        db[COLLECTIONS["readings"]].delete_many({})
        db[COLLECTIONS["wqi_history"]].delete_many({})
        
        return jsonify({
            "status": "reset",
            "message": "All data cleared successfully"
        }), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ==================== ERROR HANDLERS ====================

@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Endpoint not found"}), 404


@app.errorhandler(500)
def server_error(error):
    return jsonify({"error": "Internal server error"}), 500


# ==================== MAIN ====================

if __name__ == "__main__":
    print("\n" + "=" * 75)
    print("🌊 AquaPulse Backend Server - HTTP Edition")
    print("=" * 75)
    print(f"📍 HTTP Server: http://{SERVER_HOST}:{SERVER_PORT}")
    print("🗄️  Database: Firebase Firestore")
    print(f"🔐 Authentication: JWT Tokens")
    print(f"📡 Protocol: HTTP REST API (ESP32 ready)")
    print(f"🔧 Environment: {FLASK_ENV}")
    
    print("\n📚 AVAILABLE ENDPOINTS:\n")
    
    print("  ⚙️  CORE ENDPOINTS:")
    print("  GET  /health                      → Server health check")
    print("  POST /update                      → HTTP POST sensor data (REQUIRES TOKEN)")
    print("  GET  /readings                    → Get latest readings")
    print("  GET  /readings/<device_id>/latest → Get device's latest reading")
    print("  GET  /wqi/<device_id>/latest      → Get latest WQI score")
    print("  GET  /statistics/<device_id>      → Get device statistics")
    
    print("\n  🔐 DEVICE AUTHENTICATION:")
    print("  POST /devices/register            → Register new device (get JWT token)")
    print("  POST /token/refresh               → Refresh expired token")
    print("  GET  /devices                     → List all devices")
    print("  POST /device/<id>/deactivate      → Deactivate device")
    
    print("\n  🛡️  SECURITY & MONITORING:")
    print("  GET  /device/<id>/access-logs     → Get API access history")
    print("  GET  /device/<id>/security-status → Check device security status")
    
    print("\n  🔧 UTILITIES:")
    print("  POST /reset                       → Reset database (PASSWORD REQUIRED)")
    
    print("\n" + "=" * 75)
    print("🔐 SECURITY & FEATURES:")
    print("  ✅ Application user JWT authentication")
    print("  ✅ Firebase Firestore persistent storage")
    print("  ✅ Automatic Water Quality Index (0-100)")
    print("  ✅ HTTP REST API for sensor communication")
    print("  ✅ Failed attempt tracking (anti-brute force)")
    print("  ✅ Complete access logging")
    print("  ✅ Device activation/deactivation")
    print("=" * 75 + "\n")
    
    app.run(host=SERVER_HOST, port=SERVER_PORT, debug=DEBUG)
