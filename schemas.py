from datetime import date
from pydantic import BaseModel, ConfigDict, Field
from typing import Optional

class BookCreate(BaseModel):
    accession_number: Optional[str] = Field(None, max_length=100)
    title: str = Field(..., min_length=1, max_length=200)
    author: str = Field(..., min_length=1, max_length=200)
    publisher: Optional[str] = Field(None, max_length=200)
    edition: Optional[str] = Field(None, max_length=100)
    isbn: Optional[str] = Field(None, min_length=1, max_length=50)
    genre: Optional[str] = Field(None, max_length=100)
    language: Optional[str] = Field(None, max_length=50)
    pages: Optional[int] = Field(None, gt=0)
    price: Optional[float] = Field(None, gt=0, description="Price must be greater than 0")
    date_of_purchase: Optional[date] = None
    published_date: Optional[date] = None
    current_status: Optional[str] = Field(None, max_length=50)
    shelf_number: Optional[str] = Field(None, max_length=100)

class BookOut(BookCreate):
    id: int
    model_config = ConfigDict(from_attributes=True)


class MemberBase(BaseModel):
    full_name: str = Field(..., min_length=1, max_length=200)
    contact_number: Optional[str] = Field(None, max_length=50)
    email: Optional[str] = Field(None, max_length=100)
    address: Optional[str] = None
    membership_type: Optional[str] = Field(None, max_length=50)
    start_date: Optional[date] = None
    expiry_date: Optional[date] = None
    fine_dues: Optional[float] = 0.0
    borrowing_history: Optional[str] = None  # JSON string of borrowing records


class MemberCreate(MemberBase):
    pass


class MemberUpdate(MemberBase):
    # all fields optional for updates
    full_name: Optional[str] = None


class MemberOut(MemberBase):
    id: int
    created_at: Optional[date] = None
    model_config = ConfigDict(from_attributes=True)


class StaffBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    role: Optional[str] = None
    contact_info: Optional[str] = None
    shift_timings: Optional[str] = None
    assigned_responsibilities: Optional[str] = None


class StaffCreate(StaffBase):
    pass


class StaffUpdate(BaseModel):
    name: Optional[str] = None
    role: Optional[str] = None
    contact_info: Optional[str] = None
    shift_timings: Optional[str] = None
    assigned_responsibilities: Optional[str] = None


class StaffOut(StaffBase):
    id: int
    created_at: Optional[date] = None
    model_config = ConfigDict(from_attributes=True)


class TransactionBase(BaseModel):
    transaction_id: str
    member_id: int
    book_id: int
    issue_date: date
    due_date: date
    return_date: Optional[date] = None
    fine_details: Optional[str] = None
    renewal_count: Optional[int] = 0


class TransactionCreate(TransactionBase):
    pass


class TransactionOut(TransactionBase):
    id: int
    created_at: Optional[date] = None
    model_config = ConfigDict(from_attributes=True)