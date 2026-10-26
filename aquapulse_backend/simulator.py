"""AquaPulse sensor simulator for the unauthenticated ESP32 upload endpoint."""

import requests
import time
import random
import json

# ==================== CONFIGURATION ====================

BASE_URL = "http://localhost:5000"
DEVICE_ID = "pond_001"

print("=" * 70)
print("🌊 AquaPulse Sensor Simulator")
print("=" * 70)
print(f"📍 Backend: {BASE_URL}")
print(f"📱 Device ID: {DEVICE_ID}")

# ==================== SIMULATE SENSOR DATA ====================

print("\n🌊 Sending simulated sensor data...\n")

# Simulate realistic water parameter variations
ph_value = 7.0
tds_value = 200
turbidity_value = 3
temperature_value = 27

try:
    iteration = 0
    while True:
        # Simulate realistic water parameter changes
        ph_value += random.uniform(-0.2, 0.2)
        tds_value += random.randint(-10, 10)
        turbidity_value += random.uniform(-0.5, 0.5)
        temperature_value += random.uniform(-0.3, 0.3)
        
        # Keep within realistic ranges
        ph_value = max(6.0, min(9.0, ph_value))
        tds_value = max(100, min(500, tds_value))
        turbidity_value = max(0, min(20, turbidity_value))
        temperature_value = max(15, min(35, temperature_value))
        
        # Prepare data for the open ESP32 upload endpoint
        data = {
            "device_id": DEVICE_ID,
            "ph": round(ph_value, 2),
            "tds": int(tds_value),
            "turbidity": round(turbidity_value, 2),
            "temperature": int(temperature_value),
            "status": "Connected"
        }
        
        # Send to backend
        try:
            response = requests.post(
                f"{BASE_URL}/update",
                json=data,
                timeout=5
            )
            
            if response.status_code == 201:
                result = response.json()
                wqi = result.get("wqi", {})
                
                # Color-coded output based on WQI status
                status = wqi.get("status", "Unknown")
                if status == "Excellent":
                    status_emoji = "✅"
                elif status == "Good":
                    status_emoji = "🟢"
                elif status == "Fair":
                    status_emoji = "🟡"
                else:
                    status_emoji = "🔴"
                
                print(f"[{iteration:04d}] {status_emoji} pH={data['ph']}, TDS={data['tds']}, Turbidity={data['turbidity']:.1f}, Temp={data['temperature']}°C → WQI: {wqi.get('wqi_score', 0)} ({status})")
                iteration += 1
                    
            else:
                print(f"❌ Error ({response.status_code}): {response.json().get('error')}")
        
        except requests.exceptions.RequestException as e:
            print(f"❌ Request failed: {e}")
        
        # Wait 3 seconds before next update (matches Flutter refresh rate)
        time.sleep(3)
        
except KeyboardInterrupt:
    print("\n\n👋 Simulator stopped")
    print(f"📊 Total readings sent: {iteration}")
    print("📝 Data stored in Firebase Firestore")
    print("\n📡 Upload Summary:")
    print(f"  ✅ Device ID: {DEVICE_ID}")
    print(f"  ✅ Sensor readings sent without device authentication")
    print("=" * 70)
    
except Exception as e:
    print(f"\n❌ Error: {e}")
