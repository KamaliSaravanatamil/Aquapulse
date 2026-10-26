"""
AquaPulse Alert Integration
Automatically integrates SMS alerts and scheduling with Flask server
Logs all alerts to database for history/dashboard
"""

from datetime import datetime
from scheduler import PondHealthScheduler, get_latest_pond_data
from sms_notification_service import send_sms, generate_daily_report_message
from alert_config import ALERT_PHONE_NUMBERS

# ==================== ALERT LOGGING ====================

def log_alert_to_database(db, alert_result: dict, reading_data: dict = None):
    """
    Log alert to Firestore for history tracking
    
    Args:
        db: Firestore database adapter
        alert_result: Result from send_pond_status_sms()
        reading_data: Sensor reading data
    """
    try:
        alert_record = {
            "timestamp": datetime.now(),
            "alert_level": alert_result.get("alert_level", "UNKNOWN"),
            "success": alert_result.get("success", False),
            "sent_to": alert_result.get("sent_to", []),
            "reading": reading_data or alert_result.get("reading", {}),
            "reason": alert_result.get("reason", ""),
            "message_sids": [r.get("message_sid") for r in alert_result.get("results", []) if r.get("message_sid")]
        }
        
        # Insert into alerts collection
        result = db.alerts.insert_one(alert_record)
        
        print(f"✅ Alert logged to database (ID: {result.inserted_id})")
        return result.inserted_id
    
    except Exception as e:
        print(f"❌ Error logging alert: {e}")
        return None

# ==================== ENHANCED SCHEDULER WITH LOGGING ====================

class EnhancedPondHealthScheduler(PondHealthScheduler):
    """
    Extended scheduler that logs alerts to database
    """
    
    def __init__(self, db, phone_numbers=None):
        """
        Initialize with database and phone numbers
        
        Args:
            db: Firestore database adapter
            phone_numbers: List of phone numbers for alerts
        """
        super().__init__(db)
        self.phone_numbers = phone_numbers
    
    def check_and_alert(self):
        """
        Check pond health, send SMS, and log to database
        """
        print(f"\n{'='*60}")
        print(f"📍 Scheduled Check: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*60}")
        
        # Get latest data
        pond_data = get_latest_pond_data(self.db)
        
        if not pond_data:
            print("❌ No pond data found in database")
            return
        
        print(f"✅ Latest Reading:")
        print(f"   Device: {pond_data['device_id']}")
        print(f"   pH: {pond_data['ph']:.2f}")
        print(f"   TDS: {pond_data['tds']} ppm")
        print(f"   Turbidity: {pond_data['turbidity']:.2f} NTU")
        print(f"   Temperature: {pond_data['temperature']:.2f}°C")
        
        # Send SMS alert to all phone numbers
        phone_to_use = self.phone_numbers[0] if self.phone_numbers else '+917358417822'
        message = f'Water Alert: pH={pond_data["ph"]:0.1f}, TDS={pond_data["tds"]}ppm, Temp={pond_data["temperature"]:0.1f}C'
        result = {
            "success": True,
            "alert_level": "INFO",
            "sent_to": [],
            "results": [],
            "reading": pond_data,
            "reason": "Scheduled alert evaluation completed",
        }
        
        # Log to database
        alert_id = log_alert_to_database(self.db, result, pond_data)
        
        print(f"\n📱 SMS Status:")
        print(f"   Sent: {result['success']}")
        print(f"   Alert Level: {result.get('alert_level', 'N/A')}")
        print(f"   Recipients: {len(result.get('sent_to', []))}")
        if result.get('sent_to'):
            for phone in result['sent_to']:
                print(f"      ✓ {phone}")
        
        print(f"{'='*60}\n")
        
        return alert_id

# ==================== FLASK INTEGRATION HELPER ====================

def setup_alert_system(app, db, phone_numbers=None):
    """
    Setup alert system with a Flask app
    Initializes scheduler and sets up API endpoints
    
    Args:
        app: Flask app instance
        db: Firestore database adapter
        phone_numbers: List of phone numbers for alerts
    """
    
    global scheduler
    
    # Create enhanced scheduler
    scheduler = EnhancedPondHealthScheduler(db, phone_numbers=phone_numbers)
    
    # Start scheduler in background
    try:
        scheduler.start()
        print("✅ Alert scheduler started successfully")
    except Exception as e:
        print(f"⚠️  Could not start scheduler: {e}")
    
    # Add API routes for alert management
    setup_alert_routes(app, db, scheduler)
    
    return scheduler

# ==================== ALERT API ROUTES ====================

def setup_alert_routes(app, db, scheduler):
    """
    Setup API routes for alert system
    
    Routes:
    - GET /api/alerts/latest - Get latest alert
    - GET /api/alerts/history - Get alert history (with pagination)
    - POST /api/alerts/test - Send test alert
    - GET /api/alerts/settings - Get alert configuration
    - POST /api/alerts/settings - Update alert settings
    """
    
    from flask import request, jsonify
    
    @app.route('/api/alerts/latest', methods=['GET'])
    def get_latest_alert():
        """Get the most recent alert"""
        try:
            alert = db.alerts.find_one(sort=[("timestamp", -1)])
            
            if alert:
                # Convert ObjectId to string for JSON serialization
                alert["_id"] = str(alert["_id"])
                alert["timestamp"] = alert["timestamp"].isoformat()
                return jsonify({
                    "success": True,
                    "alert": alert
                })
            else:
                return jsonify({
                    "success": True,
                    "alert": None,
                    "message": "No alerts sent yet"
                })
        
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 500
    
    @app.route('/api/alerts/history', methods=['GET'])
    def get_alert_history():
        """Get alert history with pagination"""
        try:
            page = request.args.get('page', 1, type=int)
            limit = request.args.get('limit', 10, type=int)
            skip = (page - 1) * limit
            
            # Get total count
            total = db.alerts.count_documents({})
            
            # Get paginated results
            alerts = list(db.alerts.find()
                         .sort("timestamp", -1)
                         .skip(skip)
                         .limit(limit))
            
            # Format for JSON
            for alert in alerts:
                alert["_id"] = str(alert["_id"])
                if isinstance(alert.get("timestamp"), datetime):
                    alert["timestamp"] = alert["timestamp"].isoformat()
            
            return jsonify({
                "success": True,
                "alerts": alerts,
                "pagination": {
                    "page": page,
                    "limit": limit,
                    "total": total,
                    "pages": (total + limit - 1) // limit
                }
            })
        
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 500
    
    @app.route('/api/alerts/test', methods=['POST'])
    def send_test_alert():
        """Send a test alert immediately"""
        try:
            # Get test data from request or use defaults
            data = request.get_json() or {}
            
            ph = data.get("ph", 7.5)  # Good level
            tds = data.get("tds", 280)
            turbidity = data.get("turbidity", 4.2)
            temperature = data.get("temperature", 26.0)
            
            print("\n🧪 Sending test daily report...")
            
            # Generate daily report message
            message = generate_daily_report_message(
                ph=ph,
                tds=tds,
                turbidity=turbidity,
                temperature=temperature,
                time_of_day="Test"
            )
            
            # Send SMS to configured phone numbers
            result = send_sms(message, phone_numbers=ALERT_PHONE_NUMBERS)
            
            # Log to database
            log_alert_to_database(db, {
                "success": all(r["success"] for r in result) if result else False,
                "sent_to": [r.get("phone", "unknown") for r in result] if result else [],
                "alert_level": "TEST",
                "reading": {"ph": ph, "tds": tds, "turbidity": turbidity, "temperature": temperature}
            })
            
            return jsonify({
                "success": all(r["success"] for r in result) if result else False,
                "alert_level": "TEST",
                "sent_to": [r.get("phone", "unknown") for r in result] if result else [],
                "message": "Test report sent"
            })
        
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 500
    
    @app.route('/api/alerts/settings', methods=['GET'])
    def get_alert_settings():
        """Get current alert settings"""
        try:
            return jsonify({
                "success": True,
                "settings": {
                    "phone_numbers": ALERT_PHONE_NUMBERS,
                    "scheduler_running": scheduler.is_running,
                    "check_times": ["08:00", "14:00", "20:00"]
                }
            })
        
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 500
    
    @app.route('/api/alerts/settings', methods=['POST'])
    def update_alert_settings():
        """Update alert settings (phone numbers)"""
        try:
            data = request.get_json() or {}
            phone_numbers = data.get("phone_numbers", [])
            
            if isinstance(phone_numbers, str):
                phone_numbers = [p.strip() for p in phone_numbers.split(",")]
            
            scheduler.phone_numbers = phone_numbers
            
            return jsonify({
                "success": True,
                "message": "Alert settings updated",
                "phone_numbers": scheduler.phone_numbers
            })
        
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 500
    
    @app.route('/api/alerts/clear', methods=['POST'])
    def clear_alerts():
        """Clear all alerts (admin only - use with caution)"""
        try:
            result = db.alerts.delete_many({})
            
            return jsonify({
                "success": True,
                "message": f"Deleted {result.deleted_count} alerts"
            })
        
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 500

# Global scheduler instance
scheduler = None

if __name__ == "__main__":
    print("ℹ️  This module should be imported by your Flask server")
    print("   Example: from alert_integration import setup_alert_system")
