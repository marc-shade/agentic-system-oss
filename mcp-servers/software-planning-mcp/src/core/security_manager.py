import os
import json
import bcrypt
import jwt
import asyncio
from enum import Enum
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from loguru import logger

class UserRole(Enum):
    """User role definitions."""
    ADMIN = "admin"
    MANAGER = "manager"
    DEVELOPER = "developer"
    VIEWER = "viewer"

class SecurityManager:
    """
    Manages security aspects of the Software Planning MCP.
    Handles authentication, authorization, and security policies.
    """
    
    def __init__(self):
        self.security_dir = Path(os.path.expanduser("~/.mcp/security"))
        self.security_dir.mkdir(parents=True, exist_ok=True)
        self.users_file = self.security_dir / "users.json"
        self.roles_file = self.security_dir / "roles.json"
        self.policies_file = self.security_dir / "policies.json"
        
        # Initialize security files
        self._initialize_security_files()
        
        # Load security data
        self.users = self._load_users()
        self.roles = self._load_roles()
        self.policies = self._load_policies()
        
        # JWT settings
        self.jwt_secret = os.environ.get("MCP_JWT_SECRET", "your-secret-key")
        self.jwt_algorithm = "HS256"
        self.jwt_expiry = timedelta(hours=24)
        
        # Active sessions
        self.active_sessions: Dict[str, Dict[str, Any]] = {}
    
    def _initialize_security_files(self):
        """Initialize security files with default values."""
        if not self.users_file.exists():
            with open(self.users_file, "w") as f:
                json.dump({"users": []}, f, indent=2)
        
        if not self.roles_file.exists():
            with open(self.roles_file, "w") as f:
                json.dump({
                    "roles": {
                        "admin": {"permissions": ["*"]},
                        "manager": {"permissions": [
                            "read:*",
                            "write:projects",
                            "write:workflows",
                            "manage:teams"
                        ]},
                        "developer": {"permissions": [
                            "read:*",
                            "write:code",
                            "write:docs"
                        ]},
                        "viewer": {"permissions": ["read:*"]}
                    }
                }, f, indent=2)
        
        if not self.policies_file.exists():
            with open(self.policies_file, "w") as f:
                json.dump({
                    "password_policy": {
                        "min_length": 8,
                        "require_uppercase": True,
                        "require_lowercase": True,
                        "require_numbers": True,
                        "require_special": True
                    },
                    "session_policy": {
                        "max_sessions": 5,
                        "session_timeout": 24,  # hours
                        "require_2fa": False
                    },
                    "api_policy": {
                        "rate_limit": 100,  # requests per minute
                        "require_https": True,
                        "allowed_origins": ["*"]
                    }
                }, f, indent=2)
    
    def _load_users(self) -> Dict[str, Any]:
        """Load user data."""
        try:
            with open(self.users_file, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Failed to load users: {e}")
            return {"users": []}
    
    def _load_roles(self) -> Dict[str, Any]:
        """Load role definitions."""
        try:
            with open(self.roles_file, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Failed to load roles: {e}")
            return {"roles": {}}
    
    def _load_policies(self) -> Dict[str, Any]:
        """Load security policies."""
        try:
            with open(self.policies_file, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Failed to load policies: {e}")
            return {}
    
    def _save_users(self):
        """Save user data."""
        try:
            with open(self.users_file, "w") as f:
                json.dump(self.users, f, indent=2)
        except IOError as e:
            logger.error(f"Failed to save users: {e}")
    
    def _save_roles(self):
        """Save role definitions."""
        try:
            with open(self.roles_file, "w") as f:
                json.dump(self.roles, f, indent=2)
        except IOError as e:
            logger.error(f"Failed to save roles: {e}")
    
    def _save_policies(self):
        """Save security policies."""
        try:
            with open(self.policies_file, "w") as f:
                json.dump(self.policies, f, indent=2)
        except IOError as e:
            logger.error(f"Failed to save policies: {e}")
    
    def _validate_password(self, password: str) -> bool:
        """
        Validate password against password policy.
        
        Args:
            password: Password to validate
            
        Returns:
            True if password meets policy requirements
        """
        policy = self.policies.get("password_policy", {})
        
        if len(password) < policy.get("min_length", 8):
            return False
        
        if policy.get("require_uppercase") and not any(c.isupper() for c in password):
            return False
        
        if policy.get("require_lowercase") and not any(c.islower() for c in password):
            return False
        
        if policy.get("require_numbers") and not any(c.isdigit() for c in password):
            return False
        
        if policy.get("require_special") and not any(not c.isalnum() for c in password):
            return False
        
        return True
    
    def _hash_password(self, password: str) -> bytes:
        """Hash password using bcrypt."""
        return bcrypt.hashpw(password.encode(), bcrypt.gensalt())
    
    def _verify_password(self, password: str, hashed: bytes) -> bool:
        """Verify password against hash."""
        return bcrypt.checkpw(password.encode(), hashed)
    
    def _generate_token(self, user_id: str, role: str) -> str:
        """Generate JWT token."""
        payload = {
            "user_id": user_id,
            "role": role,
            "exp": datetime.utcnow() + self.jwt_expiry
        }
        return jwt.encode(payload, self.jwt_secret, algorithm=self.jwt_algorithm)
    
    def _verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify JWT token."""
        try:
            return jwt.decode(token, self.jwt_secret, algorithms=[self.jwt_algorithm])
        except jwt.InvalidTokenError:
            return None
    
    async def create_user(
        self,
        username: str,
        password: str,
        role: str,
        email: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a new user.
        
        Args:
            username: Username
            password: Password
            role: User role
            email: Optional email address
            
        Returns:
            User information
        """
        # Check if username exists
        if any(u["username"] == username for u in self.users["users"]):
            raise ValueError(f"Username '{username}' already exists")
        
        # Validate role
        if role not in self.roles["roles"]:
            raise ValueError(f"Invalid role: {role}")
        
        # Validate password
        if not self._validate_password(password):
            raise ValueError("Password does not meet policy requirements")
        
        # Create user
        user = {
            "id": str(len(self.users["users"]) + 1),
            "username": username,
            "password": self._hash_password(password).decode(),
            "role": role,
            "email": email,
            "created_at": datetime.now().isoformat(),
            "last_login": None,
            "active": True
        }
        
        self.users["users"].append(user)
        self._save_users()
        
        # Remove password from response
        user_info = user.copy()
        user_info.pop("password")
        
        logger.info(f"Created user: {username}")
        return user_info
    
    async def authenticate(
        self,
        username: str,
        password: str
    ) -> Dict[str, Any]:
        """
        Authenticate a user.
        
        Args:
            username: Username
            password: Password
            
        Returns:
            Authentication result with token
        """
        # Find user
        user = None
        for u in self.users["users"]:
            if u["username"] == username:
                user = u
                break
        
        if not user:
            raise ValueError("Invalid credentials")
        
        # Verify password
        if not self._verify_password(password, user["password"].encode()):
            raise ValueError("Invalid credentials")
        
        # Check if user is active
        if not user["active"]:
            raise ValueError("Account is inactive")
        
        # Generate token
        token = self._generate_token(user["id"], user["role"])
        
        # Update last login
        user["last_login"] = datetime.now().isoformat()
        self._save_users()
        
        # Create session
        session = {
            "user_id": user["id"],
            "token": token,
            "created_at": datetime.now().isoformat(),
            "expires_at": (datetime.now() + self.jwt_expiry).isoformat()
        }
        
        self.active_sessions[token] = session
        
        # Clean up expired sessions
        await self._cleanup_sessions()
        
        return {
            "token": token,
            "user": {
                "id": user["id"],
                "username": user["username"],
                "role": user["role"],
                "email": user["email"]
            }
        }
    
    async def authorize(
        self,
        token: str,
        required_permission: str
    ) -> bool:
        """
        Check if a token has the required permission.
        
        Args:
            token: JWT token
            required_permission: Required permission
            
        Returns:
            True if authorized
        """
        # Verify token
        payload = self._verify_token(token)
        if not payload:
            return False
        
        # Check if session exists
        if token not in self.active_sessions:
            return False
        
        # Get role permissions
        role = payload["role"]
        role_info = self.roles["roles"].get(role)
        if not role_info:
            return False
        
        permissions = role_info["permissions"]
        
        # Check permissions
        if "*" in permissions:
            return True
        
        if required_permission in permissions:
            return True
        
        # Check wildcard permissions
        resource_type = required_permission.split(":")[0]
        if f"{resource_type}:*" in permissions:
            return True
        
        return False
    
    async def _cleanup_sessions(self):
        """Clean up expired sessions."""
        current_time = datetime.now()
        expired_tokens = []
        
        for token, session in self.active_sessions.items():
            expires_at = datetime.fromisoformat(session["expires_at"])
            if current_time > expires_at:
                expired_tokens.append(token)
        
        for token in expired_tokens:
            self.active_sessions.pop(token)
    
    async def logout(self, token: str):
        """
        Log out a user session.
        
        Args:
            token: JWT token
        """
        self.active_sessions.pop(token, None)
    
    async def update_user(
        self,
        user_id: str,
        updates: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Update user information.
        
        Args:
            user_id: User ID
            updates: Updates to apply
            
        Returns:
            Updated user information
        """
        # Find user
        user = None
        for u in self.users["users"]:
            if u["id"] == user_id:
                user = u
                break
        
        if not user:
            raise ValueError(f"User '{user_id}' not found")
        
        # Apply updates
        for key, value in updates.items():
            if key == "password":
                if not self._validate_password(value):
                    raise ValueError("Password does not meet policy requirements")
                user[key] = self._hash_password(value).decode()
            elif key in ["username", "email", "role", "active"]:
                user[key] = value
        
        self._save_users()
        
        # Remove password from response
        user_info = user.copy()
        user_info.pop("password")
        
        return user_info
    
    async def update_role(
        self,
        role_name: str,
        permissions: List[str]
    ) -> Dict[str, Any]:
        """
        Update role permissions.
        
        Args:
            role_name: Role name
            permissions: New permissions
            
        Returns:
            Updated role information
        """
        if role_name not in self.roles["roles"]:
            raise ValueError(f"Role '{role_name}' not found")
        
        self.roles["roles"][role_name]["permissions"] = permissions
        self._save_roles()
        
        return {
            "name": role_name,
            "permissions": permissions
        }
    
    async def update_policy(
        self,
        policy_type: str,
        settings: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Update security policy settings.
        
        Args:
            policy_type: Type of policy
            settings: New settings
            
        Returns:
            Updated policy settings
        """
        if policy_type not in ["password_policy", "session_policy", "api_policy"]:
            raise ValueError(f"Invalid policy type: {policy_type}")
        
        self.policies[policy_type].update(settings)
        self._save_policies()
        
        return {
            "type": policy_type,
            "settings": self.policies[policy_type]
        }
    
    def get_tools(self) -> List[Dict[str, Any]]:
        """Get tools for security management."""
        return [
            {
                "name": "create_user",
                "description": "Create a new user",
                "parameters": [
                    {
                        "name": "username",
                        "description": "Username",
                        "type": "string",
                        "required": True,
                    },
                    {
                        "name": "password",
                        "description": "Password",
                        "type": "string",
                        "required": True,
                    },
                    {
                        "name": "role",
                        "description": "User role",
                        "type": "string",
                        "required": True,
                    },
                    {
                        "name": "email",
                        "description": "Optional email address",
                        "type": "string",
                        "required": False,
                    }
                ],
                "handler": self.tool_create_user,
            },
            {
                "name": "authenticate",
                "description": "Authenticate a user",
                "parameters": [
                    {
                        "name": "username",
                        "description": "Username",
                        "type": "string",
                        "required": True,
                    },
                    {
                        "name": "password",
                        "description": "Password",
                        "type": "string",
                        "required": True,
                    }
                ],
                "handler": self.tool_authenticate,
            },
            {
                "name": "authorize",
                "description": "Check if a token has the required permission",
                "parameters": [
                    {
                        "name": "token",
                        "description": "JWT token",
                        "type": "string",
                        "required": True,
                    },
                    {
                        "name": "required_permission",
                        "description": "Required permission",
                        "type": "string",
                        "required": True,
                    }
                ],
                "handler": self.tool_authorize,
            },
            {
                "name": "update_user",
                "description": "Update user information",
                "parameters": [
                    {
                        "name": "user_id",
                        "description": "User ID",
                        "type": "string",
                        "required": True,
                    },
                    {
                        "name": "updates",
                        "description": "Updates to apply",
                        "type": "object",
                        "required": True,
                    }
                ],
                "handler": self.tool_update_user,
            },
            {
                "name": "update_role",
                "description": "Update role permissions",
                "parameters": [
                    {
                        "name": "role_name",
                        "description": "Role name",
                        "type": "string",
                        "required": True,
                    },
                    {
                        "name": "permissions",
                        "description": "New permissions",
                        "type": "array",
                        "items": {"type": "string"},
                        "required": True,
                    }
                ],
                "handler": self.tool_update_role,
            },
            {
                "name": "update_policy",
                "description": "Update security policy settings",
                "parameters": [
                    {
                        "name": "policy_type",
                        "description": "Type of policy",
                        "type": "string",
                        "required": True,
                    },
                    {
                        "name": "settings",
                        "description": "New settings",
                        "type": "object",
                        "required": True,
                    }
                ],
                "handler": self.tool_update_policy,
            },
        ]
    
    async def tool_create_user(
        self,
        username: str,
        password: str,
        role: str,
        email: Optional[str] = None
    ) -> Dict[str, Any]:
        """Tool handler for creating a user."""
        try:
            user = await self.create_user(username, password, role, email)
            return {
                "user": user,
                "message": f"Created user '{username}'"
            }
        except ValueError as e:
            return {"error": str(e)}
    
    async def tool_authenticate(
        self,
        username: str,
        password: str
    ) -> Dict[str, Any]:
        """Tool handler for authenticating a user."""
        try:
            result = await self.authenticate(username, password)
            return {
                "result": result,
                "message": f"Authenticated user '{username}'"
            }
        except ValueError as e:
            return {"error": str(e)}
    
    async def tool_authorize(
        self,
        token: str,
        required_permission: str
    ) -> Dict[str, Any]:
        """Tool handler for authorizing a request."""
        try:
            authorized = await self.authorize(token, required_permission)
            return {
                "authorized": authorized,
                "message": "Authorization check completed"
            }
        except Exception as e:
            return {"error": str(e)}
    
    async def tool_update_user(
        self,
        user_id: str,
        updates: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Tool handler for updating a user."""
        try:
            user = await self.update_user(user_id, updates)
            return {
                "user": user,
                "message": f"Updated user {user_id}"
            }
        except ValueError as e:
            return {"error": str(e)}
    
    async def tool_update_role(
        self,
        role_name: str,
        permissions: List[str]
    ) -> Dict[str, Any]:
        """Tool handler for updating a role."""
        try:
            role = await self.update_role(role_name, permissions)
            return {
                "role": role,
                "message": f"Updated role '{role_name}'"
            }
        except ValueError as e:
            return {"error": str(e)}
    
    async def tool_update_policy(
        self,
        policy_type: str,
        settings: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Tool handler for updating a policy."""
        try:
            policy = await self.update_policy(policy_type, settings)
            return {
                "policy": policy,
                "message": f"Updated {policy_type}"
            }
        except ValueError as e:
            return {"error": str(e)}
