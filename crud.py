from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from models import Book
from schemas import BookCreate
from typing import List, Optional
from sqlalchemy.orm import Session
from models import Book, Member, Staff
import models
from schemas import (
    BookCreate,
    MemberCreate,
    MemberUpdate,
    StaffCreate,
    StaffUpdate,
)
from datetime import date, timedelta

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
        image_url=getattr(book_data, 'image_url', None),
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


def get_books_filtered(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    search: Optional[str] = None,
    new_arrivals_since: Optional[date] = None,
):
    """
    Return books with optional status/search filters.
    status values (frontend-friendly): available, borrowed, reserved, damaged, lost, removed, new-arrivals
    """
    query = db.query(Book)

    # map friendly status to current_status field
    if status:
        s = status.lower()
        if s == "available":
            query = query.filter(Book.current_status == "Available")
        elif s == "borrowed" or s == "issued":
            query = query.filter(Book.current_status.in_(["Issued", "Borrowed"]))
        elif s == "reserved":
            query = query.filter(Book.current_status == "Reserved")
        elif s == "damaged":
            query = query.filter(Book.current_status == "Damaged")
        elif s == "lost":
            query = query.filter(Book.current_status == "Lost")
        elif s == "removed":
            # assume removed is represented by current_status == 'Removed'
            query = query.filter(Book.current_status == "Removed")
        elif s == "new-arrivals":
            # handled below via new_arrivals_since; if not provided, default to 30 days
            pass

    if search:
        like = f"%{search}%"
        query = query.filter(
            (Book.title.ilike(like))
            | (Book.author.ilike(like))
            | (Book.isbn.ilike(like))
            | (Book.accession_number.ilike(like))
        )

    if status and status.lower() == "new-arrivals":
        if not new_arrivals_since:
            new_arrivals_since = date.today() - timedelta(days=30)
        query = query.filter(Book.date_of_purchase >= new_arrivals_since)
    elif new_arrivals_since:
        query = query.filter(Book.date_of_purchase >= new_arrivals_since)

    return query.offset(skip).limit(limit).all()


def books_stats(db: Session, new_arrivals_days: int = 30) -> dict:
    """Return aggregated book counts for inventory dashboard."""
    stats = {}
    stats['total'] = db.query(Book).count()
    stats['available'] = db.query(Book).filter(Book.current_status == 'Available').count()
    # treat Issued/Borrowed as borrowed
    stats['borrowed'] = db.query(Book).filter(Book.current_status.in_(['Issued', 'Borrowed'])).count()
    stats['damaged'] = db.query(Book).filter(Book.current_status == 'Damaged').count()
    stats['lost'] = db.query(Book).filter(Book.current_status == 'Lost').count()
    stats['removed'] = db.query(Book).filter(Book.current_status == 'Removed').count()
    since = date.today() - timedelta(days=new_arrivals_days)
    stats['new_arrivals'] = db.query(Book).filter(Book.date_of_purchase >= since).count()
    return stats


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


def set_book_status(book_id: int, status: str, note: Optional[str], db: Session) -> Optional[Book]:
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        return None
    book.current_status = status
    # optionally store note in shelf_number or elsewhere; here we ignore it or extend model later
    db.add(book)
    db.commit()
    db.refresh(book)
    return book


def bulk_update_book_status(book_ids: List[int], status: str, note: Optional[str], db: Session) -> int:
    """Update multiple books' status. Returns number of rows updated."""
    q = db.query(Book).filter(Book.id.in_(book_ids))
    count = q.count()
    q.update({"current_status": status}, synchronize_session=False)
    db.commit()
    return count


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


def list_transactions_for_member(member_id: int, db: Session, skip: int = 0, limit: int = 100) -> List[Txn]:
    """Return transactions belonging to a specific member."""
    return db.query(Txn).filter(Txn.member_id == member_id).offset(skip).limit(limit).all()


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


def list_reservations_for_member(member_id: int, db: Session, skip: int = 0, limit: int = 100) -> List[Resv]:
    """Return reservations belonging to a specific member."""
    return db.query(Resv).filter(Resv.member_id == member_id).offset(skip).limit(limit).all()


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


# --- Fine CRUD ---
from models import Fine

def add_fine(fine_data, db: Session) -> Fine:
    exists = db.query(Fine).filter(Fine.fine_id == fine_data.fine_id).first()
    if exists:
        raise ValueError("Fine with this fine_id already exists.")
    new_fine = Fine(
        fine_id=fine_data.fine_id,
        member_id=fine_data.member_id,
        amount=fine_data.amount,
        reason=fine_data.reason,
        payment_status=fine_data.payment_status,
        payment_date=fine_data.payment_date,
    )
    db.add(new_fine)
    try:
        db.commit()
    except IntegrityError as e:
        db.rollback()
        msg = str(e.orig) if getattr(e, 'orig', None) else str(e)
        raise ValueError(msg)
    db.refresh(new_fine)
    return new_fine


def get_fine_by_id(fine_id: int, db: Session) -> Optional[Fine]:
    return db.query(Fine).filter(Fine.id == fine_id).first()


def list_fines(db: Session, skip: int = 0, limit: int = 100) -> List[Fine]:
    return db.query(Fine).offset(skip).limit(limit).all()


def list_fines_for_member(member_id: int, db: Session, skip: int = 0, limit: int = 100) -> List[Fine]:
    """Return fines belonging to a specific member."""
    return db.query(Fine).filter(Fine.member_id == member_id).offset(skip).limit(limit).all()


def update_fine(fine_id: int, fine_data, db: Session) -> Optional[Fine]:
    f = db.query(Fine).filter(Fine.id == fine_id).first()
    if not f:
        return None
    data = fine_data.__dict__
    for key, value in data.items():
        if value is not None:
            setattr(f, key, value)
    db.add(f)
    try:
        db.commit()
    except IntegrityError as e:
        db.rollback()
        msg = str(e.orig) if getattr(e, 'orig', None) else str(e)
        raise ValueError(msg)
    db.refresh(f)
    return f


def delete_fine(fine_id: int, db: Session) -> bool:
    f = db.query(Fine).filter(Fine.id == fine_id).first()
    if not f:
        return False
    db.delete(f)
    db.commit()
    return True


# --- Auth Logs & Reports ---
from models import AuthLog
from sqlalchemy import func

def log_auth_event(user_id: Optional[int], email: Optional[str], event: str, role: Optional[str], ip_address: Optional[str], db: Session):
    entry = AuthLog(user_id=user_id, email=email, event=event, role=role, ip_address=ip_address)
    db.add(entry)
    db.commit()


def get_auth_logs(db: Session, skip: int = 0, limit: int = 100):
    return db.query(AuthLog).order_by(AuthLog.timestamp.desc()).offset(skip).limit(limit).all()


def daily_issued_returned(db: Session, days: int = 30):
    # Count transactions where issue_date / return_date fall within last `days`
    since = date.today() - timedelta(days=days)
    issued_q = db.query(func.date(models.Transaction.issue_date).label('d'), func.count().label('issued')).filter(models.Transaction.issue_date >= since).group_by(func.date(models.Transaction.issue_date)).subquery()
    returned_q = db.query(func.date(models.Transaction.return_date).label('d'), func.count().label('returned')).filter(models.Transaction.return_date >= since).group_by(func.date(models.Transaction.return_date)).subquery()
    # left join issued and returned dates
    q = db.query(func.coalesce(issued_q.c.d, returned_q.c.d).label('date'), func.coalesce(issued_q.c.issued, 0).label('issued'), func.coalesce(returned_q.c.returned, 0).label('returned')).outerjoin(returned_q, issued_q.c.d == returned_q.c.d)
    results = []
    for r in q.all():
        results.append({'date': r.date, 'issued': r.issued, 'returned': r.returned})
    return results


def monthly_activity(db: Session, months: int = 6):
    # aggregate by month for last `months`
    # Note: this is a simple aggregation and assumes PostgreSQL date functions; it should work via SQLAlchemy func
    results = []
    # use Transaction.issue_date / return_date
    # For brevity, return empty list if Transaction model or table missing
    try:
        issued = db.query(func.to_char(models.Transaction.issue_date, 'YYYY-MM').label('month'), func.count().label('issued')).group_by(func.to_char(models.Transaction.issue_date, 'YYYY-MM')).order_by(func.to_char(models.Transaction.issue_date, 'YYYY-MM').desc()).limit(months).all()
        returned = db.query(func.to_char(models.Transaction.return_date, 'YYYY-MM').label('month'), func.count().label('returned')).group_by(func.to_char(models.Transaction.return_date, 'YYYY-MM')).order_by(func.to_char(models.Transaction.return_date, 'YYYY-MM').desc()).limit(months).all()
        # merge
        issued_map = {r.month: r.issued for r in issued}
        returned_map = {r.month: r.returned for r in returned}
        months_keys = sorted(set(list(issued_map.keys()) + list(returned_map.keys())), reverse=True)[:months]
        for m in months_keys:
            results.append({'month': m, 'issued': issued_map.get(m, 0), 'returned': returned_map.get(m, 0)})
    except Exception:
        return []
    return results


def most_borrowed_books(db: Session, limit: int = 10):
    # Count transactions by book_id
    q = db.query(models.Transaction.book_id, func.count().label('borrow_count')).group_by(models.Transaction.book_id).order_by(func.count().desc()).limit(limit).all()
    results = []
    for r in q:
        book = db.query(Book).filter(Book.id == r.book_id).first()
        results.append({'book_id': r.book_id, 'title': getattr(book, 'title', None), 'borrow_count': r.borrow_count})
    return results


def inactive_members(db: Session, months: int = 6):
    # Members with no transactions in the last `months`
    since = date.today() - timedelta(days=30*months)
    active_member_ids = db.query(models.Transaction.member_id).filter(models.Transaction.issue_date >= since).distinct()
    q = db.query(Member).filter(~Member.id.in_(active_member_ids)).all()
    results = []
    for m in q:
        # last_activity is out of scope; set None or last transaction date if available
        last_txn = db.query(models.Transaction).filter(models.Transaction.member_id == m.id).order_by(models.Transaction.issue_date.desc()).first()
        last_activity = getattr(last_txn, 'issue_date', None)
        results.append({'member_id': m.id, 'full_name': m.full_name, 'last_activity': last_activity})
    return results


def fine_collection_report(db: Session, days: int = 30):
    since = date.today() - timedelta(days=days)
    q = db.query(func.date(Fine.payment_date).label('date'), func.sum(Fine.amount).label('collected')).filter(Fine.payment_date != None).filter(Fine.payment_date >= since).group_by(func.date(Fine.payment_date)).all()
    results = []
    for r in q:
        results.append({'date': r.date, 'collected_amount': float(r.collected)})
    return results
