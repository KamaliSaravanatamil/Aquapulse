"""
AquaPulse Authentication Module
JWT token verification and device security
"""

import jwt
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta
from functools import wraps
from flask import request, jsonify
from typing import Optional, Dict, Tuple
from config import SECRET_KEY, DEVICE_TOKEN_EXPIRY

USER_TOKEN_EXPIRY = 60 * 60 * 24


def hash_password(password: str) -> str:
    """Hash a password with a random salt using PBKDF2-HMAC-SHA256."""
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, 120_000
    )
    return f"{salt.hex()}${digest.hex()}"


def verify_password(password: str, stored_hash: str) -> bool:
    """Verify a password against a stored PBKDF2 hash."""
    try:
        salt_hex, digest_hex = stored_hash.split("$", 1)
        digest = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            bytes.fromhex(salt_hex),
            120_000,
        )
        return hmac.compare_digest(digest.hex(), digest_hex)
    except (ValueError, TypeError):
        return False


def generate_user_token(user_id: str, email: str) -> str:
    payload = {
        "sub": user_id,
        "email": email,
        "role": "user",
        "iat": datetime.utcnow(),
        "exp": datetime.utcnow() + timedelta(seconds=USER_TOKEN_EXPIRY),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")


def verify_user_token(token: str) -> Optional[Dict]:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        if payload.get("role") != "user":
            return None
        return payload
    except jwt.InvalidTokenError:
        return None

# ==================== JWT TOKEN MANAGEMENT ====================

def generate_device_token(device_id: str, expires_in: int = DEVICE_TOKEN_EXPIRY) -> str:
    """
    Generate JWT token for device
    
    Args:
        device_id: Unique device identifier
        expires_in: Token expiry time in seconds (default: 1 year)
    
    Returns:
        JWT token string
    """
    payload = {
        "device_id": device_id,
        "iat": datetime.utcnow(),
        "exp": datetime.utcnow() + timedelta(seconds=expires_in)
    }
    token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")
    return token


def verify_device_token(token: str) -> Optional[Dict]:
    """
    Verify JWT token and extract device_id
    
    Args:
        token: JWT token to verify
    
    Returns:
        Dictionary with device_id if valid, None if invalid
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        return {
            "device_id": payload.get("device_id"),
            "iat": datetime.fromtimestamp(payload.get("iat")),
            "exp": datetime.fromtimestamp(payload.get("exp"))
        }
    except jwt.ExpiredSignatureError:
        return None  # Token expired
    except jwt.InvalidTokenError:
        return None  # Invalid token


def refresh_device_token(old_token: str) -> Optional[str]:
    """
    Refresh an expired or valid token
    
    Args:
        old_token: Current JWT token
    
    Returns:
        New token if successful, None if invalid
    """
    try:
        # This allows refresh even if token is expired
        payload = jwt.decode(old_token, SECRET_KEY, algorithms=["HS256"], options={"verify_exp": False})
        device_id = payload.get("device_id")
        if device_id:
            return generate_device_token(device_id)
        return None
    except jwt.InvalidTokenError:
        return None


def token_is_valid(token: str) -> bool:
    """Quick check if token is valid"""
    return verify_device_token(token) is not None


def token_needs_refresh(token: str) -> bool:
    """Check if token is close to expiry (within 7 days)"""
    payload = verify_device_token(token)
    if not payload:
        return False
    
    exp_time = payload.get("exp")
    days_until_exp = (exp_time - datetime.utcnow()).days
    return days_until_exp <= 7


# ==================== AUTHENTICATION DECORATORS ====================

def require_valid_token(f):
    """
    Decorator to require valid device token in request
    Expects token in: Authorization header or token parameter
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = None
        
        # Try Authorization header first
        auth_header = request.headers.get("Authorization")
        if auth_header:
            try:
                token = auth_header.split(" ")[1]
            except IndexError:
                pass
        
        # Try query parameter
        if not token:
            token = request.args.get("token")
        
        # Try JSON body
        if not token and request.is_json:
            token = request.json.get("token")
        
        if not token:
            return jsonify({
                "error": "Missing authentication token",
                "hint": "Provide token in Authorization header, query param, or JSON body"
            }), 401
        
        payload = verify_device_token(token)
        if not payload:
            return jsonify({
                "error": "Invalid or expired token",
                "hint": "Request new token or refresh expired token"
            }), 401
        
        # Attach payload to request for use in handler
        request.device_info = payload
        return f(*args, **kwargs)
    
    return decorated_function


def require_registered_device(db):
    """
    Decorator to verify device is registered and active
    Must be used AFTER require_valid_token
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            device_id = request.device_info.get("device_id")
            
            # Query database for device
            device = db["devices"].find_one({
                "device_id": device_id,
                "active": True
            })
            
            if not device:
                return jsonify({
                    "error": "Device not found or inactive",
                    "device_id": device_id
                }), 403
            
            # Attach device info to request
            request.device = {
                "_id": str(device["_id"]),
                "device_id": device["device_id"],
                "device_name": device.get("device_name"),
                "location": device.get("location")
            }
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator


# ==================== ACCESS LOGGING ====================

def log_device_access(db, device_id: str, endpoint: str, method: str, 
                      status_code: int, ip_address: str = None) -> None:
    """
    Log device API access for security auditing
    
    Args:
        db: Firestore database adapter
        device_id: Device making request
        endpoint: API endpoint accessed
        method: HTTP method (GET, POST, etc)
        status_code: Response status code
        ip_address: Client IP address
    """
    try:
        access_log = {
            "device_id": device_id,
            "endpoint": endpoint,
            "method": method,
            "status_code": status_code,
            "ip_address": ip_address or request.remote_addr,
            "timestamp": datetime.utcnow()
        }
        db["device_access_logs"].insert_one(access_log)
    except Exception as e:
        print(f"⚠️  Failed to log access: {e}")


def get_device_access_logs(db, device_id: str, hours: int = 24, limit: int = 100) -> list:
    """
    Retrieve access logs for a device
    
    Args:
        db: Firestore database adapter
        device_id: Device to get logs for
        hours: Look back period
        limit: Max results
    
    Returns:
        List of access log entries
    """
    since = datetime.utcnow() - timedelta(hours=hours)
    logs = list(db["device_access_logs"].find({
        "device_id": device_id,
        "timestamp": {"$gte": since}
    }).sort("timestamp", -1).limit(limit))
    
    # Convert ObjectId and datetime to strings
    for log in logs:
        log["_id"] = str(log["_id"])
        log["timestamp"] = log["timestamp"].isoformat()
    
    return logs


def get_failed_access_attempts(db, device_id: str, hours: int = 1) -> list:
    """
    Get failed authentication attempts for a device
    
    Args:
        db: Firestore database adapter
        device_id: Device to check
        hours: Look back period
    
    Returns:
        List of failed attempts
    """
    since = datetime.utcnow() - timedelta(hours=hours)
    failed = list(db["device_access_logs"].find({
        "device_id": device_id,
        "status_code": {"$gte": 400},
        "timestamp": {"$gte": since}
    }).sort("timestamp", -1))
    
    for log in failed:
        log["_id"] = str(log["_id"])
        log["timestamp"] = log["timestamp"].isoformat()
    
    return failed


# ==================== SECURITY UTILITIES ====================

def is_device_suspicious(db, device_id: str, failed_attempts_threshold: int = 5) -> Tuple[bool, str]:
    """
    Check if device shows suspicious behavior
    (Too many failed attempts in short time)
    
    Args:
        db: Firestore database adapter
        device_id: Device to check
        failed_attempts_threshold: Max failed attempts allowed
    
    Returns:
        Tuple of (is_suspicious: bool, reason: str)
    """
    failed_attempts = get_failed_access_attempts(db, device_id, hours=1)
    
    if len(failed_attempts) >= failed_attempts_threshold:
        return True, f"Too many failed attempts ({len(failed_attempts)} in last hour)"
    
    return False, ""
