from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from jose import JWTError, jwt
import models, schemas, auth_schemas, auth_utils
from database import get_db

router = APIRouter(prefix="/auth", tags=["Authentication"])

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
async def login(login_data: LoginRequest, db: Session = Depends(get_db)):
    print(f"Login attempt for email: {login_data.email}")
    
    # Authenticate user
    user = db.query(models.User).filter(models.User.email == login_data.email).first()
    if not user:
        print("User not found")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not auth_utils.verify_password(login_data.password, user.hashed_password):
        print("Invalid password")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Generate access token
    access_token_expires = timedelta(minutes=auth_utils.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth_utils.create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    
    response_data = {
        "access_token": access_token, 
        "token_type": "bearer",
        "user_id": user.id,
        "email": user.email
    }
    print(f"Login successful for user: {user.email}")
    print(f"Response data: {response_data}")
    
    return response_data

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

@router.get("/me", response_model=auth_schemas.UserInDB)
async def read_users_me(current_user: models.User = Depends(auth_utils.get_current_active_user)):
    return current_user

@router.post("/logout")
async def logout():
    # In a real app, you might want to invalidate the token
    return {"message": "Successfully logged out"}
