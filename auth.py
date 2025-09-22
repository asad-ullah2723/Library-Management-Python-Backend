from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from jose import JWTError, jwt
import models, schemas, auth_schemas, auth_utils, crud
from database import get_db

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.get('/public-key')
def public_key():
    """Return public PEM key when RS256 is enabled. Returns 404 when asymmetric signing is not enabled."""
    pk = auth_utils.get_public_key()
    if not pk:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Public key not available")
    return {"public_key": pk}


@router.get('/debug')
def debug_token(current_user: models.User = Depends(auth_utils.get_admin_user), token: str = Depends(auth_utils.oauth2_scheme)):
    """Admin-only: return decoded token payload and current_user info for debugging."""
    from jose import JWTError, jwt
    try:
        verify_key = auth_utils.get_public_key() if auth_utils.is_rs256_enabled() else auth_utils.SECRET_KEY
        payload = jwt.decode(token, verify_key, algorithms=[auth_utils.ALGORITHM])
    except JWTError as e:
        return {"error": str(e)}
    return {"payload": payload, "current_user": {"id": getattr(current_user, 'id', None), "email": getattr(current_user, 'email', None), "is_superuser": getattr(current_user, 'is_superuser', False)}}

@router.post("/register", response_model=auth_schemas.UserInDB)
def register(user: auth_schemas.UserCreate, db: Session = Depends(get_db)):
    # Check if user already exists
    db_user = db.query(models.User).filter(models.User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create new user
    hashed_password = auth_utils.get_password_hash(user.password)
    db_user = models.User(
        email=user.email,
        hashed_password=hashed_password,
        full_name=user.full_name,
        created_at=datetime.utcnow()
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

class LoginRequest(auth_schemas.UserLogin):
    pass

@router.post("/login", response_model=auth_schemas.Token)
async def login(request: Request, login_data: LoginRequest, db: Session = Depends(get_db)):
    # capture remote IP (best-effort)
    client_ip = None
    try:
        client_ip = request.client.host
    except Exception:
        client_ip = request.headers.get("x-forwarded-for") or request.client

    print(f"Login attempt for email: {login_data.email}")

    # Authenticate user
    user = db.query(models.User).filter(models.User.email == login_data.email).first()
    if not user:
        print("User not found")
        # log failed login
        try:
            crud.log_auth_event(user_id=None, email=login_data.email, event="login_failed", role=None, ip_address=client_ip, db=db)
        except Exception:
            pass
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not auth_utils.verify_password(login_data.password, user.hashed_password):
        print("Invalid password")
        # log failed login with known user id
        try:
            crud.log_auth_event(user_id=user.id, email=user.email, event="login_failed", role=None, ip_address=client_ip, db=db)
        except Exception:
            pass
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Determine role string: prefer user.role (enum) if available, else fall back to is_superuser flag
    role_str = None
    try:
        # If models.User has a role enum attribute
        role_attr = getattr(user, 'role', None)
        if role_attr is not None:
            # If it's an enum, use .value, otherwise str()
            role_str = getattr(role_attr, 'value', None) or str(role_attr)
    except Exception:
        role_str = None

    if not role_str:
        # Fall back to is_superuser boolean (older schema) or default to 'member'
        try:
            role_str = 'admin' if getattr(user, 'is_superuser', False) else 'member'
        except Exception:
            role_str = 'member'

    # Create access token including role/scopes
    access_token_expires = timedelta(minutes=auth_utils.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth_utils.create_access_token(
        data={"sub": user.email, "role": role_str},
        expires_delta=access_token_expires
    )

    # log successful login
    try:
        crud.log_auth_event(user_id=user.id, email=user.email, event="login_success", role=role_str, ip_address=client_ip, db=db)
    except Exception:
        pass

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user_id": user.id,
        "email": user.email,
        "role": role_str
    }

@router.post("/forgot-password")
async def forgot_password(email: str, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == email).first()
    if not user:
        # Don't reveal that the user doesn't exist
        return {"message": "If your email is registered, you will receive a password reset link"}
    
    # Generate reset token (in a real app, this would be a secure random token)
    reset_token = auth_utils.create_access_token(
        data={"sub": user.email}, 
        expires_delta=timedelta(hours=1)  # 1 hour expiration
    )
    
    # In a real app, send an email with the reset link
    # For now, we'll just return the token (don't do this in production!)
    reset_link = f"http://localhost:8000/auth/reset-password?token={reset_token}"
    print(f"Reset link for {user.email}: {reset_link}")
    
    return {"message": "Password reset link sent to your email"}

@router.post("/reset-password")
async def reset_password(
    token: str, 
    new_password: str,
    db: Session = Depends(get_db)
):
    try:
        # Verify token
        payload = jwt.decode(token, auth_utils.SECRET_KEY, algorithms=[auth_utils.ALGORITHM])
        email = payload.get("sub")
        if not email:
            raise HTTPException(status_code=400, detail="Invalid token")
        
        # Update user password
        user = db.query(models.User).filter(models.User.email == email).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        user.hashed_password = auth_utils.get_password_hash(new_password)
        db.commit()
        
        return {"message": "Password updated successfully"}
        
    except JWTError:
        raise HTTPException(status_code=400, detail="Invalid or expired token")

@router.get("/me")
async def read_users_me(current_user: models.User = Depends(auth_utils.get_current_active_user)):
    # Compute role string similarly to the login endpoint
    role_str = None
    try:
        role_attr = getattr(current_user, 'role', None)
        if role_attr is not None:
            role_str = getattr(role_attr, 'value', None) or str(role_attr)
    except Exception:
        role_str = None

    if not role_str:
        try:
            role_str = 'admin' if getattr(current_user, 'is_superuser', False) else 'member'
        except Exception:
            role_str = 'member'

    # Build response dict (include commonly used fields and the computed role)
    resp = {
        'id': getattr(current_user, 'id', None),
        'email': getattr(current_user, 'email', None),
        'full_name': getattr(current_user, 'full_name', None),
        'is_active': getattr(current_user, 'is_active', None),
        'is_superuser': getattr(current_user, 'is_superuser', False),
        'created_at': getattr(current_user, 'created_at', None),
        'role': role_str,
    }
    return resp

@router.post("/logout")
async def logout():
    # In a real app, you might want to invalidate the token
    return {"message": "Successfully logged out"}
