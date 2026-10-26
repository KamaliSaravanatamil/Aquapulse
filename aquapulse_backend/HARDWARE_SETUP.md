# Hardware Setup Guide - AquaPulse ESP32

## Part 1: Upload Firmware to ESP32

### Prerequisites
- ESP32 development board
- USB cable (USB-A to Micro-USB)
- Arduino IDE installed on your computer

### Step 1: Install Arduino IDE
Download from: https://www.arduino.cc/en/software

### Step 2: Add ESP32 Board Support
1. Open Arduino IDE
2. Go to: **File → Preferences**
3. In "Additional Boards Manager URLs", paste:
   ```
   https://dl.espressif.com/dl/package_esp32_index.json
   ```
4. Click OK
5. Go to: **Tools → Board → Board Manager**
6. Search for: `ESP32`
7. Click **Install** (by Espressif Systems)

### Step 3: Install Required Libraries
In Arduino IDE, go to: **Sketch → Include Library → Manage Libraries**

Search and install these libraries:
1. **WiFi** (built-in, no install needed)
2. **HTTPClient** (built-in, no install needed)
3. **ArduinoJson** - by Benoit Blanchon
4. **Wire** (built-in for I2C)
5. **LiquidCrystal_I2C** - by Frank de Brabander

### Step 4: Select ESP32 Board
1. Go to: **Tools → Board**
2. Select: **ESP32 → ESP32 Dev Module**

### Step 5: Select COM Port
1. Connect ESP32 to your computer with USB cable
2. Go to: **Tools → Port**
3. Select the COM port (usually COM3, COM4, COM5, etc.)

### Step 6: Open and Configure Firmware
1. Open file: `ESP32_AquaPulse_HTTP_ONLY.ino`
2. **Modify these lines** (around lines 20-30):
   ```cpp
   const char* SSID = "JAI-GANESH_5G";           // Your WiFi SSID
   const char* PASSWORD = "Jaideepa@06";          // Your WiFi Password
   const char* SERVER_IP = "192.168.29.158";      // Your backend server IP
   const int SERVER_PORT = 5000;                  // Flask server port
   ```

### Step 7: Upload Firmware
1. Click the **Upload** button (arrow icon)
   - OR go to: **Sketch → Upload**
2. Wait for upload to complete (you'll see "Done uploading" message)

### Step 8: Monitor Serial Output
1. Go to: **Tools → Serial Monitor**
2. Set baud rate to: **115200**
3. You should see:
   ```
   Starting ESP32 Sensor System...
   Connecting to WiFi: JAI-GANESH_5G
   WiFi Connected!
   IP: 192.168.29.XXX
   LCD Initialized
   Testing LCD display...
   Starting sensor readings...
   ```

---

## Part 2: Wire 4 Sensors to ESP32

### Sensor Pinout on ESP32

| Sensor | Purpose | GPIO Pin | ADC Channel |
|--------|---------|----------|-------------|
| Sensor 1 | pH | GPIO 34 | ADC1_6 |
| Sensor 2 | TDS | GPIO 35 | ADC1_7 |
| Sensor 3 | Turbidity | GPIO 32 | ADC1_4 |
| Sensor 4 | Temperature | GPIO 33 | ADC1_5 |

### Wiring Instructions

**For each analog sensor:**

1. **Sensor Signal Wire** → ESP32 GPIO pin (see table above)
2. **Sensor GND (Black)** → ESP32 GND
3. **Sensor VCC (Red)** → ESP32 3.3V or 5V (check your sensor specs)

### Example: pH Sensor Connection
```
pH Sensor "A0" Pin ──→ ESP32 GPIO 34
pH Sensor "GND" Pin ──→ ESP32 GND
pH Sensor "VCC" Pin ──→ ESP32 5V
```

### Important Notes
- **Use 3.3V logic** - ESP32 is NOT 5V tolerant
- If sensors use 5V, use a **voltage divider** circuit
- Keep wires short to reduce noise
- If readings are unstable, add a **100nF capacitor** near each sensor

---

## Part 3: Connect I2C LCD Display

### Display Specifications
- **Type:** 16x2 I2C LCD
- **Address:** 0x27 (default)
- **Protocol:** I2C (2-wire)

### LCD Pinout

| Pin | Function |
|-----|----------|
| VCC | Power (5V) |
| GND | Ground |
| SDA | I2C Data |
| SCL | I2C Clock |

### Wiring on ESP32

```
LCD VCC ──→ ESP32 5V
LCD GND ──→ ESP32 GND
LCD SDA ──→ ESP32 GPIO 21
LCD SCL ──→ ESP32 GPIO 22
```

### Verify I2C Address
1. Open Serial Monitor in Arduino IDE
2. Upload this quick test code:
   ```cpp
   #include <Wire.h>
   
   void setup() {
     Serial.begin(115200);
     Wire.begin(21, 22);
     
     for(byte i = 8; i < 120; i++) {
       Wire.beginTransmission(i);
       if (Wire.endTransmission() == 0) {
         Serial.print("Device found at 0x");
         Serial.println(i, HEX);
       }
     }
   }
   
   void loop() {}
   ```
3. If you see `Device found at 0x27` → Address is correct
4. If different, update line 45 in `ESP32_AquaPulse_HTTP_ONLY.ino`:
   ```cpp
   LiquidCrystal_I2C lcd(0x27, 16, 2);  // Change 0x27 to your address
   ```

---

## Part 4: Complete Hardware Wiring Diagram

```
ESP32 DevKit
┌─────────────────────────────────┐
│         GND  GND  GND  GND      │
│         VCC  5V   3.3V          │
│                                 │
│  GPIO34 ──┬──────→ pH Sensor    │
│  GPIO35 ──┼──────→ TDS Sensor   │
│  GPIO32 ──┼──────→ Turbidity    │
│  GPIO33 ──┴──────→ Temperature  │
│                                 │
│  GPIO21 (SDA) ──→ LCD SDA       │
│  GPIO22 (SCL) ──→ LCD SCL       │
│  5V ──→ LCD VCC                 │
│  GND ──→ LCD GND                │
└─────────────────────────────────┘

16x2 I2C LCD
┌──────────────────────┐
│ Sensor Readings v3.0 │
│ pH: 7.2 T: 25.5°C   │
└──────────────────────┘
(Display rotates every 1 second)
```

---

## Part 5: Test Hardware

### Step 1: Check Serial Monitor
After uploading firmware, open Serial Monitor (115200 baud) and verify:
- WiFi connection status
- LCD initialization
- Sensor readings every 3 seconds
- JSON data being formatted

**Expected output:**
```
Starting ESP32 Sensor System...
Connecting to WiFi: JAI-GANESH_5G
WiFi Connected!
IP: 192.168.29.123
LCD Initialized
Testing LCD display...
Reading 1 - pH: 7.23, TDS: 245, Turbidity: 3.2, Temp: 25.1
Posting to: http://192.168.29.158:5000/data
HTTP Response: 200 OK
```

### Step 2: Monitor Backend
In your backend PowerShell window (where Flask is running), you should see:
```
192.168.29.123 - - [16/Mar/2026 08:35:12] "POST /data HTTP/1.1" 200 -
192.168.29.123 - - [16/Mar/2026 08:35:15] "POST /data HTTP/1.1" 200 -
192.168.29.123 - - [16/Mar/2026 08:35:18] "POST /data HTTP/1.1" 200 -
```

### Step 3: Check Readings Endpoint
Run in your testing window:
```powershell
curl http://192.168.29.158:5000/readings
```

You should see real sensor data now!

### Step 4: View LCD Display
The 16x2 LCD on your ESP32 will show:
```
Line 1: Current reading (pH, TDS, Turbidity, or Temp)
Line 2: Value and unit
```
Display auto-rotates every 1 second.

---

## Troubleshooting

### Issue: ESP32 not connecting to WiFi
- Verify SSID and password are correct
- Check WiFi network is 2.4 GHz (ESP32 doesn't support 5 GHz)
- Look for error messages in Serial Monitor

### Issue: Sensors reading 0 or very high values
- Check wiring connections
- Verify GPIO pins are correct
- Test with multimeter to check sensor output
- Try different ADC pins if one fails

### Issue: LCD not displaying anything
- Verify I2C address (0x27 or other)
- Check SDA (GPIO 21) and SCL (GPIO 22) connections
- Try LCD test scan code (shown above)
- Increase I2C clock speed if needed

### Issue: Data not reaching backend
- Verify backend is running: `curl http://192.168.29.158:5000/health`
- Check server IP in firmware matches your PC IP
- Verify ESP32 and PC are on same WiFi network
- Check firewall isn't blocking port 5000

### Issue: LCD showing but no sensor readings
- Verify ADC pins are connected correctly
- Add delay in loop (code already has 3 second delays)
- Check Serial Monitor for ADC values
- Ensure sensors have power (VCC connection)

---

## Final Checklist

Before declaring hardware setup complete:

- ✅ Firmware uploaded to ESP32
- ✅ ESP32 connects to WiFi (check Serial Monitor)
- ✅ LCD displays properly (shows rotating readings)
- ✅ Sensor data appears in Serial Monitor
- ✅ Backend receives POST requests (check Flask logs)
- ✅ `/readings` endpoint returns real data
- ✅ ESP32 IP appears in backend logs

Once all checkboxes pass, your hardware is fully integrated! 🎉

---

## Quick Reference: Key Settings

**Backend Server:**
- IP: 192.168.29.158
- Port: 5000
- Endpoint: http://192.168.29.158:5000/data

**ESP32 WiFi:**
- SSID: JAI-GANESH_5G
- Password: Jaideepa@06

**GPIO Pins:**
- pH: 34, TDS: 35, Turbidity: 32, Temperature: 33
- I2C SDA: 21, SCL: 22

**I2C LCD:**
- Address: 0x27
- Pins: SDA=21, SCL=22

