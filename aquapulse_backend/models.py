"""
AquaPulse Database Models
Firestore collection schemas and helper functions
"""

from datetime import datetime
from typing import Dict, Optional, List
from pydantic import BaseModel, Field

# ==================== DATA MODELS (Pydantic) ====================

class SensorReading(BaseModel):
    """Sensor reading from ESP32 or test simulator"""
    device_id: str
    ph: float
    tds: int
    ec: Optional[float] = None
    turbidity: Optional[float] = None
    temperature: Optional[float] = None
    status: str = "Connected"
    timestamp: Optional[datetime] = Field(default_factory=datetime.utcnow)

    class Config:
        json_schema_extra = {
            "example": {
                "device_id": "pond_001",
                "ph": 7.2,
                "tds": 320,
                "ec": 1.34,
                "turbidity": 3.0,
                "temperature": 27,
                "status": "Connected"
            }
        }


class Device(BaseModel):
    """IoT Device (ESP32)"""
    device_id: str
    device_name: str
    device_token: str
    location: Optional[str] = None
    device_type: str = "ESP32"
    active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_schema_extra = {
            "example": {
                "device_id": "pond_001",
                "device_name": "Main Pond Monitor",
                "device_token": "jwt_token_here",
                "location": "Farm Building A",
                "device_type": "ESP32",
                "active": True
            }
        }


class WaterQualityIndex(BaseModel):
    """Water Quality Index calculation result"""
    device_id: str
    wqi_score: float
    status: str  # "Excellent", "Good", "Fair", "Poor"
    ph_score: float
    tds_score: float
    turbidity_score: float
    temperature_score: float
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    recommendations: List[str] = []

    class Config:
        json_schema_extra = {
            "example": {
                "device_id": "pond_001",
                "wqi_score": 85.3,
                "status": "Excellent",
                "ph_score": 90.0,
                "tds_score": 85.0,
                "turbidity_score": 80.0,
                "temperature_score": 85.0,
                "recommendations": ["pH is within optimal range", "Water clarity is good"]
            }
        }


class SensorCalibration(BaseModel):
    """Sensor calibration settings"""
    device_id: str
    ph_offset: float = 0.0
    ph_scale: float = 1.0
    tds_scale: float = 1.0
    turbidity_scale: float = 1.0
    temperature_offset: float = 0.0
    calibration_date: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_schema_extra = {
            "example": {
                "device_id": "pond_001",
                "ph_offset": 0.1,
                "ph_scale": 0.99,
                "tds_scale": 1.05,
                "turbidity_scale": 1.0,
                "temperature_offset": -0.5
            }
        }


class AlertRule(BaseModel):
    """Alert rule for triggering notifications"""
    device_id: str
    alert_type: str  # "ph_high", "ph_low", "tds_high", "temp_critical"
    threshold_value: float
    enabled: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_schema_extra = {
            "example": {
                "device_id": "pond_001",
                "alert_type": "ph_high",
                "threshold_value": 8.5,
                "enabled": True
            }
        }


# ==================== FIRESTORE COLLECTION NAMES ====================

COLLECTIONS = {
    "readings": "readings",
    "devices": "devices",
    "wqi_history": "wqi_history",
    "calibrations": "calibrations",
    "alert_rules": "alert_rules",
}

