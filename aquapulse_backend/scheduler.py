"""
AquaPulse Scheduled Report & Alert System
Sends daily pond health reports at scheduled times (8 AM, 2 PM, 8 PM)
"""

import schedule
import time
import threading
from datetime import datetime
from sms_notification_service import send_sms, generate_daily_report_message

# ==================== SCHEDULED TASKS ====================

def get_latest_pond_data(db):
    """
    Fetch latest sensor reading from database
    
    Args:
        db: Firestore database adapter
    
    Returns:
        dict with latest reading or None
    """
    try:
        latest = db.readings.find_one(
            sort=[("timestamp", -1)]
        )
        
        if latest:
            return {
                "ph": latest.get("ph", 0),
                "tds": latest.get("tds", 0),
                "turbidity": latest.get("turbidity", 0),
                "temperature": latest.get("temperature", 25),
                "device_id": latest.get("device_id"),
                "timestamp": latest.get("timestamp")
            }
        return None
    
    except Exception as e:
        print(f"❌ Error fetching pond data: {e}")
        return None

def check_and_alert_pond_status(db, always_send=False):
    """
    Check pond status and send DAILY REPORT SMS (not just alerts)
    
    Args:
        db: Firestore database adapter
        always_send: Always send report (default True for scheduled reports)
    """
    
    print(f"\n{'='*60}")
    print(f"📍 Daily Report Check: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}")
    
    # Get latest data
    pond_data = get_latest_pond_data(db)
    
    if not pond_data:
        print("❌ No pond data found in database")
        return
    
    print(f"✅ Latest Reading:")
    print(f"   Device: {pond_data['device_id']}")
    print(f"   pH: {pond_data['ph']:.2f}")
    print(f"   TDS: {pond_data['tds']} ppm")
    print(f"   Turbidity: {pond_data['turbidity']:.2f} NTU")
    print(f"   Temperature: {pond_data['temperature']:.2f}°C")
    print(f"   Time: {pond_data['timestamp']}")
    
    # Determine time of day for report
    hour = datetime.now().hour
    if 8 <= hour < 12:
        time_of_day = "Morning"
    elif 12 <= hour < 18:
        time_of_day = "Afternoon"
    else:
        time_of_day = "Evening"
    
    # Generate daily report message (professional, not alert)
    message = generate_daily_report_message(
        ph=pond_data['ph'],
        tds=pond_data['tds'],
        turbidity=pond_data['turbidity'],
        temperature=pond_data['temperature'],
        time_of_day=time_of_day
    )
    
    # Send SMS (always send for scheduled reports)
    result = send_sms(message)
    
    print(f"\n📱 Daily Report Status:")
    print(f"   Sent: {result[0]['success'] if result else False}")
    if result and result[0]['success']:
        print(f"   SID: {result[0]['message_sid']}")
    else:
        print(f"   Reason: {result[0].get('error', 'Unknown') if result else 'No result'}")
    
    print(f"{'='*60}\n")

# ==================== SCHEDULER SETUP ====================

class PondHealthScheduler:
    """
    Manages scheduled pond health checks and SMS alerts
    """
    
    def __init__(self, db):
        """
        Initialize scheduler
        
        Args:
            db: Firestore database adapter
        """
        self.db = db
        self.scheduler_thread = None
        self.is_running = False
    
    def schedule_checks(self):
        """Schedule pond health checks at specific times"""
        
        # Schedule 3 times daily
        schedule.every().day.at("08:00").do(check_and_alert_pond_status, db=self.db)
        schedule.every().day.at("14:00").do(check_and_alert_pond_status, db=self.db)
        schedule.every().day.at("20:00").do(check_and_alert_pond_status, db=self.db)
        
        print("\n📅 Scheduled SMS Alerts:")
        print("   ⏰ 08:00 AM - Morning Check")
        print("   ⏰ 02:00 PM - Afternoon Check")
        print("   ⏰ 08:00 PM - Evening Check")
        print()
    
    def run_scheduler(self):
        """Run scheduler in background thread"""
        
        print("🚀 Starting Pond Health Scheduler...")
        self.schedule_checks()
        
        while self.is_running:
            schedule.run_pending()
            time.sleep(60)  # Check every minute
    
    def start(self):
        """Start scheduler in background"""
        
        if self.is_running:
            print("⚠️  Scheduler already running")
            return
        
        self.is_running = True
        self.scheduler_thread = threading.Thread(
            target=self.run_scheduler,
            daemon=True
        )
        self.scheduler_thread.start()
        print("✅ Scheduler started (running in background)")
    
    def stop(self):
        """Stop scheduler"""
        
        if not self.is_running:
            print("⚠️  Scheduler not running")
            return
        
        self.is_running = False
        if self.scheduler_thread:
            self.scheduler_thread.join(timeout=5)
        
        schedule.clear()
        print("✅ Scheduler stopped")
    
    def test_immediate_check(self, always_send=True):
        """
        Run a test check immediately (useful for testing)
        
        Args:
            always_send: If True, send SMS even if pond is healthy
        """
        print("🧪 Running immediate test check...")
        check_and_alert_pond_status(self.db, always_send=always_send)

# ==================== SIMPLE INTERVAL SCHEDULER ====================

class SimpleIntervalScheduler:
    """
    Simple alternative: check every X minutes
    Useful if you don't need exact time scheduling
    """
    
    def __init__(self, db, interval_minutes=30):
        """
        Initialize with check interval
        
        Args:
            db: Firestore database adapter
            interval_minutes: How often to check (e.g., 30 for every 30 min)
        """
        self.db = db
        self.interval_minutes = interval_minutes
        self.scheduler_thread = None
        self.is_running = False
    
    def run_interval_scheduler(self):
        """Run scheduler with fixed intervals"""
        
        print(f"\n🚀 Starting Interval Scheduler (every {self.interval_minutes} minutes)...")
        
        while self.is_running:
            check_and_alert_pond_status(self.db, always_send=False)
            time.sleep(self.interval_minutes * 60)
    
    def start(self):
        """Start interval scheduler"""
        
        if self.is_running:
            print("⚠️  Scheduler already running")
            return
        
        self.is_running = True
        self.scheduler_thread = threading.Thread(
            target=self.run_interval_scheduler,
            daemon=True
        )
        self.scheduler_thread.start()
        print(f"✅ Interval scheduler started (checks every {self.interval_minutes} minutes)")
    
    def stop(self):
        """Stop scheduler"""
        
        self.is_running = False
        if self.scheduler_thread:
            self.scheduler_thread.join(timeout=5)
        print("✅ Interval scheduler stopped")

# ==================== TESTING ====================

def test_scheduler_dry_run(db):
    """Test scheduler without sending real SMS"""
    
    print("\n" + "="*60)
    print("🧪 Scheduler DRY RUN (no SMS sent)")
    print("="*60)
    
    pond_data = get_latest_pond_data(db)
    
    if pond_data:
        print(f"\n✅ Database connected, latest reading found:")
        print(f"   pH: {pond_data['ph']}, TDS: {pond_data['tds']}")
        print(f"   Turbidity: {pond_data['turbidity']}, Temp: {pond_data['temperature']}")
        print("\n📊 Alert Decision Logic:")
        print("   - If any parameter out of range → ALERT (SMS sent)")
        print("   - All parameters OK → No SMS")
        print("\n✅ Scheduler is ready to run!")
    else:
        print("❌ No data in database yet")
        print("   Wait for ESP32 to send first reading, then try again")
    
    print("="*60 + "\n")

if __name__ == "__main__":
    # This file is normally imported, not run directly
    # But you can add test code here
    print("ℹ️  This module should be imported by your Flask server")
    print("   Example: from scheduler import PondHealthScheduler")
