from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
import models, schemas, auth_utils
from database import get_db
import admin_schemas as schemas

router = APIRouter(
    prefix="/admin",
    tags=["Admin"],
    dependencies=[Depends(auth_utils.get_current_active_user)],
    responses={404: {"description": "Not found"}},
)

def verify_admin(current_user: models.User):
    # support older schema without role enum (use is_superuser) or newer with role enums/strings
    try:
        role_attr = getattr(current_user, 'role', None)
        if role_attr is not None:
            role_val = getattr(role_attr, 'value', None) or str(role_attr)
            if role_val and role_val.lower() == 'admin':
                return
        if getattr(current_user, 'is_superuser', False):
            return
    except Exception:
        pass
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Not enough permissions"
    )

def verify_admin_or_librarian(current_user: models.User):
    try:
        role_attr = getattr(current_user, 'role', None)
        if role_attr is not None:
            role_val = getattr(role_attr, 'value', None) or str(role_attr)
            if role_val and role_val.lower() in ['admin', 'librarian']:
                return
        if getattr(current_user, 'is_superuser', False):
            return
    except Exception:
        pass
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Not enough permissions"
    )

# User Management Endpoints
@router.post("/users/", response_model=schemas.UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(
    user: schemas.UserCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth_utils.get_current_active_user)
):
    verify_admin(current_user)
    
    # Check if user already exists
    db_user = db.query(models.User).filter(models.User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create new user
    hashed_password = auth_utils.get_password_hash(user.password)
    # Map role to is_superuser flag since models.User doesn't have a role column
    is_super = False
    try:
        # role may be an enum
        role_val = getattr(user.role, 'value', None) or str(user.role)
        if role_val and role_val.lower() == 'admin':
            is_super = True
    except Exception:
        is_super = False

    db_user = models.User(
        email=user.email,
        hashed_password=hashed_password,
        full_name=user.full_name,
        is_active=user.is_active,
        is_superuser=is_super,
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    # Attach dynamic attributes expected by response schema
    try:
        db_user.role = role_val if 'role_val' in locals() else ('admin' if db_user.is_superuser else 'member')
    except Exception:
        db_user.role = 'admin' if db_user.is_superuser else 'member'
    try:
        db_user.added_by = current_user.id
    except Exception:
        pass
    return db_user

@router.get("/users/", response_model=List[schemas.UserResponse])
def read_users(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth_utils.get_current_active_user)
):
    verify_admin_or_librarian(current_user)
    users = db.query(models.User).offset(skip).limit(limit).all()
    # ensure each user has a role attribute for response_model
    for u in users:
        try:
            u.role = 'admin' if getattr(u, 'is_superuser', False) else 'member'
        except Exception:
            u.role = 'admin' if getattr(u, 'is_superuser', False) else 'member'
    return users

@router.get("/users/{user_id}", response_model=schemas.UserResponse)
def read_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth_utils.get_current_active_user)
):
    verify_admin_or_librarian(current_user)
    db_user = db.query(models.User).filter(models.User.id == user_id).first()
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    try:
        db_user.role = 'admin' if getattr(db_user, 'is_superuser', False) else 'member'
    except Exception:
        db_user.role = 'admin' if getattr(db_user, 'is_superuser', False) else 'member'
    return db_user

@router.patch("/users/{user_id}", response_model=schemas.UserResponse)
def update_user(
    user_id: int,
    user: schemas.UserUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth_utils.get_current_active_user)
):
    verify_admin(current_user)
    db_user = db.query(models.User).filter(models.User.id == user_id).first()
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    
    update_data = user.dict(exclude_unset=True)
    # Handle role specially (map to is_superuser)
    if 'role' in update_data:
        try:
            role_val = getattr(update_data['role'], 'value', None) or str(update_data['role'])
            db_user.is_superuser = True if role_val and role_val.lower() == 'admin' else False
            # attach dynamic attribute for response
            db_user.role = role_val
        except Exception:
            pass
        update_data.pop('role', None)

    for key, value in update_data.items():
        # avoid setting unknown attributes like added_by on the model
        if not hasattr(db_user, key):
            try:
                setattr(db_user, key, value)
            except Exception:
                # attach as dynamic attribute
                setattr(db_user, key, value)
        else:
            setattr(db_user, key, value)

    db.commit()
    db.refresh(db_user)
    try:
        db_user.role = 'admin' if getattr(db_user, 'is_superuser', False) else 'member'
    except Exception:
        db_user.role = 'admin' if getattr(db_user, 'is_superuser', False) else 'member'
    return db_user

@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth_utils.get_current_active_user)
):
    verify_admin(current_user)
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")
        
    db_user = db.query(models.User).filter(models.User.id == user_id).first()
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    
    db.delete(db_user)
    db.commit()
    return None

# Book Management Endpoints
@router.post("/books/", response_model=schemas.BookResponse, status_code=status.HTTP_201_CREATED)
def create_book(
    book: schemas.BookCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth_utils.get_current_active_user)
):
    verify_admin_or_librarian(current_user)
    
    # Check if book with same ISBN already exists
    db_book = db.query(models.Book).filter(models.Book.isbn == book.isbn).first()
    if db_book:
        raise HTTPException(status_code=400, detail="Book with this ISBN already exists")
    
    # Create new book
    db_book = models.Book(
        **book.dict(),
        added_by=current_user.id,
        added_at=datetime.utcnow()
    )
    db.add(db_book)
    db.commit()
    db.refresh(db_book)
    return db_book

@router.get("/books/", response_model=List[schemas.BookResponse])
def read_books(
    skip: int = 0,
    limit: int = 100,
    title: Optional[str] = None,
    author: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth_utils.get_current_active_user)
):
    query = db.query(models.Book)

    if title:
        query = query.filter(models.Book.title.ilike(f"%{title}%"))
    if author:
        query = query.filter(models.Book.author.ilike(f"%{author}%"))
    if status:
        # map admin_schemas.BookStatus (lowercase) to stored current_status values (Title case)
        mapping = {
            'available': 'Available',
            'borrowed': 'Borrowed',
            'reserved': 'Reserved',
            'lost': 'Lost'
        }
        mapped = mapping.get(status.lower(), status)
        query = query.filter(models.Book.current_status == mapped)

    books = query.offset(skip).limit(limit).all()
    return books

@router.get("/books/{book_id}", response_model=schemas.BookResponse)
def read_book(
    book_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth_utils.get_current_active_user)
):
    db_book = db.query(models.Book).filter(models.Book.id == book_id).first()
    if db_book is None:
        raise HTTPException(status_code=404, detail="Book not found")
    return db_book

@router.patch("/books/{book_id}", response_model=schemas.BookResponse)
def update_book(
    book_id: int,
    book: schemas.BookUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth_utils.get_current_active_user)
):
    verify_admin_or_librarian(current_user)
    db_book = db.query(models.Book).filter(models.Book.id == book_id).first()
    if db_book is None:
        raise HTTPException(status_code=404, detail="Book not found")
    
    update_data = book.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_book, key, value)
    
    db.commit()
    db.refresh(db_book)
    return db_book

@router.delete("/books/{book_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_book(
    book_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth_utils.get_current_active_user)
):
    verify_admin_or_librarian(current_user)
    db_book = db.query(models.Book).filter(models.Book.id == book_id).first()
    if db_book is None:
        raise HTTPException(status_code=404, detail="Book not found")
    
    db.delete(db_book)
    db.commit()
    return None
