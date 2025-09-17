from pydantic import BaseModel, EmailStr, Field
from datetime import date, datetime
from typing import List, Optional
from enum import Enum

class UserRole(str, Enum):
    ADMIN = "admin"
    LIBRARIAN = "librarian"
    MEMBER = "member"

class BookStatus(str, Enum):
    AVAILABLE = "available"
    BORROWED = "borrowed"
    RESERVED = "reserved"
    LOST = "lost"

# User Management Schemas
class UserCreate(BaseModel):
    email: EmailStr
    full_name: str
    password: str = Field(..., min_length=8)
    role: UserRole = UserRole.MEMBER
    is_active: bool = True

class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None

class UserResponse(BaseModel):
    id: int
    email: EmailStr
    full_name: str
    role: UserRole
    is_active: bool
    created_at: datetime
    added_by: Optional[int] = None

    class Config:
        from_attributes = True

# Book Management Schemas
class BookBase(BaseModel):
    title: str
    author: str
    isbn: str
    description: Optional[str] = None
    price: Optional[float] = None
    published_date: Optional[date] = None
    status: BookStatus = BookStatus.AVAILABLE

class BookCreate(BookBase):
    pass

class BookUpdate(BaseModel):
    title: Optional[str] = None
    author: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    published_date: Optional[date] = None
    status: Optional[BookStatus] = None

class BookResponse(BookBase):
    id: int
    added_by: int
    added_at: datetime

    class Config:
        from_attributes = True

# Response Models
class PaginatedResponse(BaseModel):
    total: int
    page: int
    per_page: int
    items: List[dict]

class ErrorResponse(BaseModel):
    detail: str
