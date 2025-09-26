from datetime import datetime, timedelta
from typing import Optional, List

from fastapi import Depends, HTTPException, status, Security
from fastapi.security import OAuth2PasswordBearer, SecurityScopes
from jose import JWTError, jwt
import os
import logging
try:
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.backends import default_backend
    _HAS_CRYPTO = True
except Exception:
    _HAS_CRYPTO = False
from passlib.context import CryptContext
from pydantic import ValidationError
from sqlalchemy.orm import Session

import models
import auth_schemas
from database import get_db

# to get a string like this run:
# openssl rand -hex 32
# By default we use HS256 with a shared secret (suitable for local/dev).
# For stronger JWS (asymmetric) support, place RSA keys under `keys/private.pem` and `keys/public.pem`
DEFAULT_SECRET = "09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7"
DEFAULT_ALGORITHM = "HS256"

# Attempt to load RSA keys for RS256 (JWS). If present, we'll prefer RS256.
KEY_DIR = os.path.join(os.path.dirname(__file__), "keys")
PRIVATE_KEY_PATH = os.path.join(KEY_DIR, "private.pem")
PUBLIC_KEY_PATH = os.path.join(KEY_DIR, "public.pem")

_USE_RS256 = False
_PRIVATE_KEY = None
_PUBLIC_KEY = None
if os.path.exists(PRIVATE_KEY_PATH) and os.path.exists(PUBLIC_KEY_PATH) and _HAS_CRYPTO:
    try:
        with open(PRIVATE_KEY_PATH, 'rb') as f:
            private_bytes = f.read()
        with open(PUBLIC_KEY_PATH, 'rb') as f:
            public_bytes = f.read()

        # Validate keys by attempting to load them. This raises on invalid keys.
        try:
            serialization.load_pem_private_key(private_bytes, password=None, backend=default_backend())
            serialization.load_pem_public_key(public_bytes, backend=default_backend())
        except Exception as e:
            logging.warning("RSA key files found but failed to parse: %s. Falling back to HS256.", e)
            _USE_RS256 = False
            ALGORITHM = DEFAULT_ALGORITHM
            SECRET_KEY = DEFAULT_SECRET
        else:
            _PRIVATE_KEY = private_bytes.decode('utf-8')
            _PUBLIC_KEY = public_bytes.decode('utf-8')
            _USE_RS256 = True
            ALGORITHM = 'RS256'
            SECRET_KEY = _PRIVATE_KEY
    except Exception as e:
        logging.warning("Error reading RSA keys: %s. Falling back to HS256.", e)
        _USE_RS256 = False
        ALGORITHM = DEFAULT_ALGORITHM
        SECRET_KEY = DEFAULT_SECRET
else:
    if os.path.exists(PRIVATE_KEY_PATH) or os.path.exists(PUBLIC_KEY_PATH):
        logging.warning("RSA key files found but cryptography isn't available; falling back to HS256.")
    ALGORITHM = DEFAULT_ALGORITHM
    SECRET_KEY = DEFAULT_SECRET
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="auth/login",
    scopes={
        "admin": "Admin operations",
        "librarian": "Librarian operations",
        "member": "Member operations"
    },
    # Do not automatically return a 401 when no token is provided.
    # This allows creating optional authentication dependencies for public endpoints.
    auto_error=False,
)


def is_rs256_enabled() -> bool:
    """Return True if RS256/JWS signing is enabled and keys loaded."""
    return bool(_USE_RS256 and _PUBLIC_KEY and _PRIVATE_KEY)


def get_public_key() -> Optional[str]:
    """Return the public PEM if available, else None."""
    return _PUBLIC_KEY

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against a hash."""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Generate a password hash."""
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token with user data and expiration."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "scopes": [data.get("role", "member")]})
    # If using RS256, pass the private key for signing; for HS256 pass the secret
    sign_key = _PRIVATE_KEY if _USE_RS256 else SECRET_KEY
    encoded_jwt = jwt.encode(to_encode, sign_key, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(
    security_scopes: SecurityScopes,
    token: Optional[str] = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> models.User:
    """Get the current user from the JWT token and validate scopes."""
    if security_scopes.scopes:
        authenticate_value = f'Bearer scope="{security_scopes.scope_str}"'
    else:
        authenticate_value = "Bearer"
    
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": authenticate_value},
    )
    
    try:
        # If no token was provided, oauth2_scheme returns None when auto_error=False
        if not token:
            raise credentials_exception
        # For RS256 we must verify with the public key
        verify_key = _PUBLIC_KEY if _USE_RS256 else SECRET_KEY
        payload = jwt.decode(token, verify_key, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
        
        # Get user scopes from token or default to member
        token_scopes = payload.get("scopes", ["member"])
        token_data = {"sub": email, "scopes": token_scopes}
        
    except (JWTError, ValidationError):
        raise credentials_exception
    
    user = db.query(models.User).filter(models.User.email == email).first()
    if user is None:
        raise credentials_exception
    
    # Check if user has required scopes
    if security_scopes.scopes:
        for scope in security_scopes.scopes:
            if scope not in token_scopes:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Not enough permissions",
                    headers={"WWW-Authenticate": authenticate_value},
                )
    
    return user


async def get_optional_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> Optional[models.User]:
    """Attempt to get current user from token. Return None if no token provided.

    Raises 401/403 if a token is provided but invalid or user not found.
    """
    if not token:
        return None
    # Reuse existing logic from get_current_user but without SecurityScopes handling
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        verify_key = _PUBLIC_KEY if _USE_RS256 else SECRET_KEY
        payload = jwt.decode(token, verify_key, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except (JWTError, ValidationError):
        raise credentials_exception

    user = db.query(models.User).filter(models.User.email == email).first()
    if user is None:
        raise credentials_exception
    return user

async def get_current_active_user(
    current_user: models.User = Security(get_current_user, scopes=[])
) -> models.User:
    """Get the current active user."""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    return current_user

def get_admin_user(
    current_user: models.User = Security(get_current_user, scopes=["admin"])
) -> models.User:
    """Get the current user if they are an admin."""
    # Support both newer `role` attribute (enum/string) and older `is_superuser` flag
    try:
        role_attr = getattr(current_user, 'role', None)
        if role_attr is not None:
            role_val = getattr(role_attr, 'value', None) or str(role_attr)
            if role_val and role_val.lower() == 'admin':
                return current_user
        # fallback to is_superuser boolean
        if getattr(current_user, 'is_superuser', False):
            return current_user
    except Exception:
        pass
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Not enough permissions"
    )

def get_librarian_user(
    current_user: models.User = Security(get_current_user, scopes=[]),
    token: Optional[str] = Security(oauth2_scheme, scopes=[]),
) -> models.User:
    """Get the current user if they are a librarian or admin.

    This accepts tokens that include either the 'librarian' or 'admin' scope (logical OR).
    We don't ask Security to enforce scopes because Security with multiple scopes requires
    all scopes to be present. Instead we decode the token ourselves here (if present)
    and accept the user if either scope is present, or if the DB user has role/is_superuser.
    """
    # Try to accept based on token scopes first (if token provided)
    try:
        if token:
            verify_key = _PUBLIC_KEY if _USE_RS256 else SECRET_KEY
            payload = jwt.decode(token, verify_key, algorithms=[ALGORITHM])
            token_scopes = payload.get("scopes", [])
            if isinstance(token_scopes, str):
                token_scopes = [token_scopes]
            for s in token_scopes:
                if s and s.lower() in ["librarian", "admin"]:
                    return current_user
    except Exception:
        # ignore token decode errors here; we'll validate via DB attributes below
        pass

    # Fallback: check stored user attributes
    try:
        role_attr = getattr(current_user, 'role', None)
        if role_attr is not None:
            role_val = getattr(role_attr, 'value', None) or str(role_attr)
            if role_val and role_val.lower() in ['librarian', 'admin']:
                return current_user
        if getattr(current_user, 'is_superuser', False):
            return current_user
    except Exception:
        pass

    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")
