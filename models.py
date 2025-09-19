from sqlalchemy import Column, Integer, String, Float, Date, Boolean
from datetime import datetime, date
from database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String)
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    created_at = Column(Date, default=datetime.utcnow)
    reset_password_token = Column(String, nullable=True)
    reset_password_expires = Column(Date, nullable=True)


class Book(Base):
    __tablename__ = "books"

    id = Column(Integer, primary_key=True, index=True)
    # accession_number / book id (optional alternative identifier)
    accession_number = Column(String, unique=True, index=True, nullable=True)
    title = Column(String, nullable=False, index=True)
    author = Column(String, nullable=False, index=True)
    publisher = Column(String, nullable=True)
    edition = Column(String, nullable=True)
    isbn = Column(String, unique=True, index=True, nullable=True)
    genre = Column(String, nullable=True)
    language = Column(String, nullable=True)
    pages = Column(Integer, nullable=True)
    price = Column(Float, nullable=True)
    date_of_purchase = Column(Date, nullable=True)
    published_date = Column(Date, default=date.today)
    current_status = Column(String, default="Available")  # Available / Issued / Reserved / Lost / Damaged
    shelf_number = Column(String, nullable=True)
    owner_id = Column(Integer, index=True)


class Member(Base):
    __tablename__ = "members"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String, nullable=False, index=True)
    contact_number = Column(String, nullable=True)
    email = Column(String, unique=True, index=True, nullable=True)
    address = Column(String, nullable=True)
    membership_type = Column(String, nullable=True)  # e.g., Student, Teacher, Staff, Public
    start_date = Column(Date, nullable=True)
    expiry_date = Column(Date, nullable=True)
    fine_dues = Column(Float, default=0.0)
    borrowing_history = Column(String, nullable=True)  # store as JSON string (simple approach)
    created_at = Column(Date, default=datetime.utcnow)


class Staff(Base):
    __tablename__ = "staff"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    role = Column(String, nullable=True)  # Librarian, Assistant, Administrator, etc.
    contact_info = Column(String, nullable=True)
    shift_timings = Column(String, nullable=True)  # store as text like "09:00-17:00" or JSON
    assigned_responsibilities = Column(String, nullable=True)  # JSON string or comma-separated
    created_at = Column(Date, default=datetime.utcnow)


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    transaction_id = Column(String, unique=True, index=True, nullable=False)
    member_id = Column(Integer, index=True, nullable=False)
    book_id = Column(Integer, index=True, nullable=False)
    issue_date = Column(Date, nullable=False)
    due_date = Column(Date, nullable=False)
    return_date = Column(Date, nullable=True)
    fine_details = Column(String, nullable=True)  # JSON string or text describing fines
    renewal_count = Column(Integer, default=0)
    created_at = Column(Date, default=datetime.utcnow)
