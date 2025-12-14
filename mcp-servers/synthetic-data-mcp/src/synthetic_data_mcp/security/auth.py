"""
Enterprise-grade authentication and authorization system.

Implements JWT-based authentication, API key management, role-based access control,
and comprehensive security features for production deployment.
"""

import hashlib
import hmac
import secrets
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple
from functools import wraps

import jwt
from cryptography.fernet import Fernet
from passlib.context import CryptContext
from pydantic import BaseModel, Field, EmailStr
from loguru import logger
import redis
from sqlalchemy import create_engine, Column, String, DateTime, Boolean, Integer, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

# Security configuration
SECRET_KEY = secrets.token_urlsafe(32)
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7
API_KEY_LENGTH = 32
MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_DURATION_MINUTES = 15

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Database setup
Base = declarative_base()
engine = create_engine("sqlite:///synthetic_auth.db")
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Redis for rate limiting and session management
redis_client = redis.Redis(host='localhost', port=6379, decode_responses=True)


class User(Base):
    """User model for authentication."""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    roles = Column(JSON, default=list)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = Column(DateTime)
    mfa_secret = Column(String)
    api_keys = Column(JSON, default=list)


class APIKey(Base):
    """API Key model for service authentication."""
    __tablename__ = "api_keys"
    
    id = Column(Integer, primary_key=True)
    key_hash = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    user_id = Column(Integer, nullable=False)
    scopes = Column(JSON, default=list)
    rate_limit = Column(Integer, default=1000)  # Requests per hour
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime)
    last_used = Column(DateTime)
    is_active = Column(Boolean, default=True)
    api_metadata = Column(JSON, default=dict)


class TokenData(BaseModel):
    """Token payload structure."""
    sub: str
    email: Optional[str] = None
    roles: List[str] = Field(default_factory=list)
    scopes: List[str] = Field(default_factory=list)
    exp: Optional[datetime] = None
    iat: Optional[datetime] = None
    jti: Optional[str] = None  # JWT ID for revocation


class LoginRequest(BaseModel):
    """Login request structure."""
    username: str
    password: str
    mfa_code: Optional[str] = None


class TokenResponse(BaseModel):
    """Token response structure."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class AuthService:
    """Core authentication service."""
    
    def __init__(self, db: Session):
        self.db = db
        self.fernet = Fernet(Fernet.generate_key())
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify password against hash."""
        return pwd_context.verify(plain_password, hashed_password)
    
    def hash_password(self, password: str) -> str:
        """Hash password using bcrypt."""
        return pwd_context.hash(password)
    
    def create_access_token(
        self,
        data: dict,
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """Create JWT access token."""
        to_encode = data.copy()
        
        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        
        to_encode.update({
            "exp": expire,
            "iat": datetime.now(timezone.utc),
            "jti": secrets.token_urlsafe(16)
        })
        
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt
    
    def create_refresh_token(self, user_id: str) -> str:
        """Create refresh token."""
        data = {
            "sub": user_id,
            "type": "refresh",
            "jti": secrets.token_urlsafe(16)
        }
        
        expire = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
        data["exp"] = expire
        
        encoded_jwt = jwt.encode(data, SECRET_KEY, algorithm=ALGORITHM)
        
        # Store in Redis for revocation capability
        redis_client.setex(
            f"refresh_token:{data['jti']}",
            int(timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS).total_seconds()),
            user_id
        )
        
        return encoded_jwt
    
    def verify_token(self, token: str) -> Optional[TokenData]:
        """Verify and decode JWT token."""
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            
            # Check if token is revoked
            jti = payload.get("jti")
            if jti and redis_client.get(f"revoked_token:{jti}"):
                return None
            
            return TokenData(**payload)
        
        except jwt.ExpiredSignatureError:
            logger.warning("Token expired")
            return None
        except jwt.JWTError as e:
            logger.error(f"JWT verification failed: {e}")
            return None
    
    def revoke_token(self, token: str) -> bool:
        """Revoke a token by adding to blacklist."""
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            jti = payload.get("jti")
            
            if jti:
                # Calculate remaining TTL
                exp = payload.get("exp")
                if exp:
                    ttl = exp - time.time()
                    if ttl > 0:
                        redis_client.setex(f"revoked_token:{jti}", int(ttl), "1")
                        return True
            
            return False
        except Exception as e:
            logger.error(f"Token revocation failed: {e}")
            return False
    
    def authenticate_user(
        self,
        username: str,
        password: str,
        mfa_code: Optional[str] = None
    ) -> Optional[User]:
        """Authenticate user with credentials."""
        # Check rate limiting
        attempts_key = f"login_attempts:{username}"
        attempts = redis_client.get(attempts_key)
        
        if attempts and int(attempts) >= MAX_LOGIN_ATTEMPTS:
            logger.warning(f"User {username} locked out due to too many attempts")
            return None
        
        # Get user from database
        user = self.db.query(User).filter(
            (User.username == username) | (User.email == username)
        ).first()
        
        if not user or not self.verify_password(password, user.hashed_password):
            # Increment failed attempts
            redis_client.incr(attempts_key)
            redis_client.expire(attempts_key, LOCKOUT_DURATION_MINUTES * 60)
            return None
        
        # Verify MFA if enabled
        if user.mfa_secret and not self.verify_mfa(user.mfa_secret, mfa_code):
            return None
        
        # Clear failed attempts
        redis_client.delete(attempts_key)
        
        # Update last login
        user.last_login = datetime.utcnow()
        self.db.commit()
        
        return user
    
    def create_api_key(
        self,
        user_id: int,
        name: str,
        scopes: List[str] = None,
        expires_in_days: Optional[int] = None
    ) -> str:
        """Create API key for service authentication."""
        # Generate secure random key
        api_key = secrets.token_urlsafe(API_KEY_LENGTH)
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        
        # Calculate expiration
        expires_at = None
        if expires_in_days:
            expires_at = datetime.utcnow() + timedelta(days=expires_in_days)
        
        # Store in database
        db_key = APIKey(
            key_hash=key_hash,
            name=name,
            user_id=user_id,
            scopes=scopes or [],
            expires_at=expires_at
        )
        
        self.db.add(db_key)
        self.db.commit()
        
        logger.info(f"API key created for user {user_id}: {name}")
        
        return api_key
    
    def verify_api_key(self, api_key: str) -> Optional[APIKey]:
        """Verify API key and check rate limits."""
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        
        # Get key from database
        db_key = self.db.query(APIKey).filter(
            APIKey.key_hash == key_hash,
            APIKey.is_active == True
        ).first()
        
        if not db_key:
            return None
        
        # Check expiration
        if db_key.expires_at and db_key.expires_at < datetime.utcnow():
            return None
        
        # Check rate limiting
        rate_key = f"api_rate:{key_hash}"
        current_count = redis_client.incr(rate_key)
        
        if current_count == 1:
            redis_client.expire(rate_key, 3600)  # 1 hour window
        
        if current_count > db_key.rate_limit:
            logger.warning(f"Rate limit exceeded for API key: {db_key.name}")
            return None
        
        # Update last used
        db_key.last_used = datetime.utcnow()
        self.db.commit()
        
        return db_key
    
    def verify_mfa(self, secret: str, code: str) -> bool:
        """Verify TOTP MFA code."""
        import pyotp
        
        if not code:
            return False
        
        totp = pyotp.TOTP(secret)
        return totp.verify(code, valid_window=1)
    
    def generate_mfa_secret(self) -> str:
        """Generate MFA secret for user."""
        import pyotp
        return pyotp.random_base32()


class RoleBasedAccessControl:
    """Role-based access control system."""
    
    # Define role permissions
    PERMISSIONS = {
        "admin": ["*"],  # Full access
        "developer": [
            "generate:read", "generate:write",
            "validate:read", "validate:write",
            "audit:read"
        ],
        "analyst": [
            "generate:read",
            "validate:read",
            "audit:read"
        ],
        "viewer": [
            "generate:read",
            "audit:read"
        ]
    }
    
    @classmethod
    def check_permission(
        cls,
        user_roles: List[str],
        required_permission: str
    ) -> bool:
        """Check if user roles have required permission."""
        for role in user_roles:
            permissions = cls.PERMISSIONS.get(role, [])
            
            # Check for wildcard or specific permission
            if "*" in permissions or required_permission in permissions:
                return True
            
            # Check for partial match (e.g., "generate:*" matches "generate:read")
            resource = required_permission.split(":")[0]
            if f"{resource}:*" in permissions:
                return True
        
        return False
    
    @classmethod
    def require_permission(cls, permission: str):
        """Decorator to require specific permission."""
        def decorator(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                # Extract user from request context
                request = kwargs.get('request')
                if not request or not hasattr(request, 'user'):
                    raise PermissionError("Authentication required")
                
                user = request.user
                if not cls.check_permission(user.roles, permission):
                    raise PermissionError(f"Permission denied: {permission}")
                
                return await func(*args, **kwargs)
            return wrapper
        return decorator


class SecurityMiddleware:
    """Security middleware for request processing."""
    
    def __init__(self, auth_service: AuthService):
        self.auth_service = auth_service
    
    async def __call__(self, request, call_next):
        """Process security checks for each request."""
        
        # Extract token from headers
        auth_header = request.headers.get("Authorization")
        api_key = request.headers.get("X-API-Key")
        
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
            token_data = self.auth_service.verify_token(token)
            
            if token_data:
                request.state.user = token_data
                request.state.auth_type = "jwt"
        
        elif api_key:
            key_data = self.auth_service.verify_api_key(api_key)
            
            if key_data:
                request.state.api_key = key_data
                request.state.auth_type = "api_key"
        
        # Add security headers
        response = await call_next(request)
        
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Content-Security-Policy"] = "default-src 'self'"
        
        return response


class DataEncryption:
    """Data encryption service for sensitive information."""
    
    def __init__(self, key: Optional[bytes] = None):
        if key:
            self.fernet = Fernet(key)
        else:
            self.fernet = Fernet(Fernet.generate_key())
    
    def encrypt(self, data: str) -> str:
        """Encrypt string data."""
        return self.fernet.encrypt(data.encode()).decode()
    
    def decrypt(self, encrypted_data: str) -> str:
        """Decrypt string data."""
        return self.fernet.decrypt(encrypted_data.encode()).decode()
    
    def encrypt_dict(self, data: Dict[str, Any]) -> str:
        """Encrypt dictionary data."""
        import json
        json_str = json.dumps(data)
        return self.encrypt(json_str)
    
    def decrypt_dict(self, encrypted_data: str) -> Dict[str, Any]:
        """Decrypt dictionary data."""
        import json
        json_str = self.decrypt(encrypted_data)
        return json.loads(json_str)


class AuditLogger:
    """Security audit logging."""
    
    @staticmethod
    def log_authentication(
        user_id: str,
        success: bool,
        ip_address: str,
        user_agent: str
    ):
        """Log authentication attempts."""
        event = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": "authentication",
            "user_id": user_id,
            "success": success,
            "ip_address": ip_address,
            "user_agent": user_agent
        }
        
        # Log to security audit trail
        logger.info(f"AUTH_AUDIT: {event}")
        
        # Store in database for compliance
        redis_client.lpush("security_audit_log", str(event))
        redis_client.ltrim("security_audit_log", 0, 10000)  # Keep last 10k events
    
    @staticmethod
    def log_api_access(
        api_key_id: str,
        endpoint: str,
        method: str,
        ip_address: str
    ):
        """Log API access."""
        event = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": "api_access",
            "api_key_id": api_key_id,
            "endpoint": endpoint,
            "method": method,
            "ip_address": ip_address
        }
        
        logger.info(f"API_AUDIT: {event}")
        redis_client.lpush("api_audit_log", str(event))
    
    @staticmethod
    def log_data_access(
        user_id: str,
        resource: str,
        action: str,
        data_classification: str
    ):
        """Log data access for compliance."""
        event = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": "data_access",
            "user_id": user_id,
            "resource": resource,
            "action": action,
            "data_classification": data_classification
        }
        
        logger.info(f"DATA_AUDIT: {event}")
        redis_client.lpush("data_audit_log", str(event))


# Initialize database tables
Base.metadata.create_all(bind=engine)