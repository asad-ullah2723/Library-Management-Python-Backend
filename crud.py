from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from models import Book
from schemas import BookCreate
from typing import List, Optional
from sqlalchemy.orm import Session
from models import Book, Member, Staff
from schemas import (
    BookCreate,
    MemberCreate,
    MemberUpdate,
    StaffCreate,
    StaffUpdate,
)
from datetime import date

# --- Book CRUD ---
def add_book(book_data: BookCreate, db: Session) -> Book:
    # Guard against duplicates before hitting DB constraints
    if getattr(book_data, "isbn", None):
        exists = db.query(Book).filter(Book.isbn == book_data.isbn).first()
        if exists:
            raise ValueError("A book with this ISBN already exists.")
    if getattr(book_data, "accession_number", None):
        exists = db.query(Book).filter(Book.accession_number == book_data.accession_number).first()
        if exists:
            raise ValueError("A book with this accession number already exists.")

    new_book = Book(
        accession_number=book_data.accession_number,
        title=book_data.title,
        author=book_data.author,
        publisher=book_data.publisher,
        edition=book_data.edition,
        isbn=book_data.isbn,
        genre=book_data.genre,
        language=book_data.language,
        pages=book_data.pages,
        price=book_data.price,
        date_of_purchase=book_data.date_of_purchase,
        published_date=book_data.published_date or date.today(),
        current_status=book_data.current_status or "Available",
        shelf_number=book_data.shelf_number,
    )
    db.add(new_book)
    try:
        db.commit()
    except IntegrityError as e:
        db.rollback()
        # Convert DB error to clear message for API layer
        msg = str(e.orig) if getattr(e, 'orig', None) else str(e)
        raise ValueError(msg)
    db.refresh(new_book)
    return new_book


def delete_book(book_id: int, db: Session) -> bool:
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        return False
    db.delete(book)
    db.commit()
    return True


def get_books(db: Session, skip: int = 0, limit: int = 100) -> List[Book]:
    return db.query(Book).offset(skip).limit(limit).all()


def get_book_by_id(book_id: int, db: Session) -> Optional[Book]:
    return db.query(Book).filter(Book.id == book_id).first()


def update_book(book_id: int, book_data: BookCreate, db: Session) -> Optional[Book]:
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        return None
    # If changing identifiers, ensure uniqueness
    if getattr(book_data, "isbn", None) and book_data.isbn != book.isbn:
        exists = db.query(Book).filter(Book.isbn == book_data.isbn).first()
        if exists:
            raise ValueError("A book with this ISBN already exists.")
    if getattr(book_data, "accession_number", None) and book_data.accession_number != book.accession_number:
        exists = db.query(Book).filter(Book.accession_number == book_data.accession_number).first()
        if exists:
            raise ValueError("A book with this accession number already exists.")

    # map all fields from BookCreate if present
    data = book_data.__dict__
    for key, value in data.items():
        if value is not None:
            setattr(book, key, value)
    db.add(book)
    try:
        db.commit()
    except IntegrityError as e:
        db.rollback()
        msg = str(e.orig) if getattr(e, 'orig', None) else str(e)
        raise ValueError(msg)
    db.refresh(book)
    return book


def search_books(
    title: Optional[str] = None,
    author: Optional[str] = None,
    isbn: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    published_after: Optional[date] = None,
    published_before: Optional[date] = None,
    db: Session = None,
) -> List[Book]:
    query = db.query(Book)
    if title:
        query = query.filter(Book.title.ilike(f"%{title}%"))
    if author:
        query = query.filter(Book.author.ilike(f"%{author}%"))
    if isbn:
        query = query.filter(Book.isbn.ilike(f"%{isbn}%"))
    if min_price is not None:
        query = query.filter(Book.price >= min_price)
    if max_price is not None:
        query = query.filter(Book.price <= max_price)
    if published_after:
        query = query.filter(Book.published_date >= published_after)
    if published_before:
        query = query.filter(Book.published_date <= published_before)
    return query.all()


# --- Member CRUD ---
def add_member(member_data: MemberCreate, db: Session) -> Member:
    new_member = Member(
        full_name=member_data.full_name,
        contact_number=member_data.contact_number,
        email=member_data.email,
        address=member_data.address,
        membership_type=member_data.membership_type,
        start_date=member_data.start_date,
        expiry_date=member_data.expiry_date,
        fine_dues=member_data.fine_dues or 0.0,
        borrowing_history=member_data.borrowing_history,
    )
    db.add(new_member)
    db.commit()
    db.refresh(new_member)
    return new_member


def get_members(db: Session, skip: int = 0, limit: int = 100) -> List[Member]:
    return db.query(Member).offset(skip).limit(limit).all()


def get_member_by_id(member_id: int, db: Session) -> Optional[Member]:
    return db.query(Member).filter(Member.id == member_id).first()


def update_member(member_id: int, member_data: MemberUpdate, db: Session) -> Optional[Member]:
    member = db.query(Member).filter(Member.id == member_id).first()
    if not member:
        return None
    data = member_data.__dict__
    for key, value in data.items():
        if value is not None:
            setattr(member, key, value)
    db.add(member)
    db.commit()
    db.refresh(member)
    return member


def delete_member(member_id: int, db: Session) -> bool:
    member = db.query(Member).filter(Member.id == member_id).first()
    if not member:
        return False
    db.delete(member)
    db.commit()
    return True


# --- Staff CRUD ---
def add_staff(staff_data: StaffCreate, db: Session) -> Staff:
    new_staff = Staff(
        name=staff_data.name,
        role=staff_data.role,
        contact_info=staff_data.contact_info,
        shift_timings=staff_data.shift_timings,
        assigned_responsibilities=staff_data.assigned_responsibilities,
    )
    db.add(new_staff)
    db.commit()
    db.refresh(new_staff)
    return new_staff


def get_staff(db: Session, skip: int = 0, limit: int = 100) -> List[Staff]:
    return db.query(Staff).offset(skip).limit(limit).all()


def get_staff_by_id(staff_id: int, db: Session) -> Optional[Staff]:
    return db.query(Staff).filter(Staff.id == staff_id).first()


def update_staff(staff_id: int, staff_data: StaffUpdate, db: Session) -> Optional[Staff]:
    staff = db.query(Staff).filter(Staff.id == staff_id).first()
    if not staff:
        return None
    data = staff_data.__dict__
    for key, value in data.items():
        if value is not None:
            setattr(staff, key, value)
    db.add(staff)
    db.commit()
    db.refresh(staff)
    return staff


def delete_staff(staff_id: int, db: Session) -> bool:
    staff = db.query(Staff).filter(Staff.id == staff_id).first()
    if not staff:
        return False
    db.delete(staff)
    db.commit()
    return True


# --- Transaction CRUD ---
from models import Transaction as Txn

def add_transaction(txn_data, db: Session) -> Txn:
    # ensure uniqueness of transaction_id
    exists = db.query(Txn).filter(Txn.transaction_id == txn_data.transaction_id).first()
    if exists:
        raise ValueError("Transaction with this transaction_id already exists.")
    new_txn = Txn(
        transaction_id=txn_data.transaction_id,
        member_id=txn_data.member_id,
        book_id=txn_data.book_id,
        issue_date=txn_data.issue_date,
        due_date=txn_data.due_date,
        return_date=txn_data.return_date,
        fine_details=txn_data.fine_details,
        renewal_count=txn_data.renewal_count,
    )
    db.add(new_txn)
    try:
        db.commit()
    except IntegrityError as e:
        db.rollback()
        msg = str(e.orig) if getattr(e, 'orig', None) else str(e)
        raise ValueError(msg)
    db.refresh(new_txn)
    return new_txn


def get_transaction_by_id(txn_id: int, db: Session) -> Optional[Txn]:
    return db.query(Txn).filter(Txn.id == txn_id).first()


def list_transactions(db: Session, skip: int = 0, limit: int = 100) -> List[Txn]:
    return db.query(Txn).offset(skip).limit(limit).all()


def update_transaction(txn_id: int, txn_data, db: Session) -> Optional[Txn]:
    txn = db.query(Txn).filter(Txn.id == txn_id).first()
    if not txn:
        return None
    data = txn_data.__dict__
    for key, value in data.items():
        if value is not None:
            setattr(txn, key, value)
    db.add(txn)
    try:
        db.commit()
    except IntegrityError as e:
        db.rollback()
        msg = str(e.orig) if getattr(e, 'orig', None) else str(e)
        raise ValueError(msg)
    db.refresh(txn)
    return txn


def delete_transaction(txn_id: int, db: Session) -> bool:
    txn = db.query(Txn).filter(Txn.id == txn_id).first()
    if not txn:
        return False
    db.delete(txn)
    db.commit()
    return True


# --- Reservation CRUD ---
from models import Reservation as Resv

def add_reservation(resv_data, db: Session) -> Resv:
    # ensure uniqueness of reservation_id
    exists = db.query(Resv).filter(Resv.reservation_id == resv_data.reservation_id).first()
    if exists:
        raise ValueError("Reservation with this reservation_id already exists.")
    new_resv = Resv(
        reservation_id=resv_data.reservation_id,
        book_id=resv_data.book_id,
        member_id=resv_data.member_id,
        reservation_date=resv_data.reservation_date,
        status=resv_data.status,
    )
    db.add(new_resv)
    try:
        db.commit()
    except IntegrityError as e:
        db.rollback()
        msg = str(e.orig) if getattr(e, 'orig', None) else str(e)
        raise ValueError(msg)
    db.refresh(new_resv)
    return new_resv


def get_reservation_by_id(resv_id: int, db: Session) -> Optional[Resv]:
    return db.query(Resv).filter(Resv.id == resv_id).first()


def list_reservations(db: Session, skip: int = 0, limit: int = 100) -> List[Resv]:
    return db.query(Resv).offset(skip).limit(limit).all()


def update_reservation(resv_id: int, resv_data, db: Session) -> Optional[Resv]:
    resv = db.query(Resv).filter(Resv.id == resv_id).first()
    if not resv:
        return None
    data = resv_data.__dict__
    for key, value in data.items():
        if value is not None:
            setattr(resv, key, value)
    db.add(resv)
    try:
        db.commit()
    except IntegrityError as e:
        db.rollback()
        msg = str(e.orig) if getattr(e, 'orig', None) else str(e)
        raise ValueError(msg)
    db.refresh(resv)
    return resv


def delete_reservation(resv_id: int, db: Session) -> bool:
    resv = db.query(Resv).filter(Resv.id == resv_id).first()
    if not resv:
        return False
    db.delete(resv)
    db.commit()
    return True
