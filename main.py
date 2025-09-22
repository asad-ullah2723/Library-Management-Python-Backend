import uvicorn
from datetime import date, datetime
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from schemas import BookCreate, BookOut
from schemas import BookStatusUpdate, BulkBookStatusUpdate
from crud import add_book, delete_book, search_books, get_books, get_book_by_id, update_book, get_books_filtered, books_stats
from schemas import MemberCreate, MemberOut, MemberUpdate
from crud import add_member, get_members, get_member_by_id, update_member, delete_member
from schemas import StaffCreate, StaffOut, StaffUpdate
from crud import add_staff, get_staff, get_staff_by_id, update_staff, delete_staff
from crud import add_transaction, get_transaction_by_id, list_transactions, update_transaction, delete_transaction
from schemas import TransactionCreate, TransactionOut
from crud import add_reservation, get_reservation_by_id, list_reservations, update_reservation, delete_reservation
from schemas import ReservationCreate, ReservationOut
from crud import add_fine, get_fine_by_id, list_fines, update_fine, delete_fine
from schemas import FineCreate, FineOut
from crud import log_auth_event, get_auth_logs, daily_issued_returned, monthly_activity, most_borrowed_books, inactive_members, fine_collection_report
from schemas import AuthLogOut, DailyIssuedReturned, MonthlyActivity, MostBorrowedItem, InactiveMember, FineCollection
from database import get_db, engine, Base
import models  # ensure models are imported so tables are registered
from auth import router as auth_router
import auth_utils


# Initialize FastAPI app with debug mode
app = FastAPI(debug=True)

# Configure CORS as the first middleware
origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=600
)

# Add middleware to log all requests for debugging
@app.middleware("http")
async def log_requests(request, call_next):
    print(f"Incoming request: {request.method} {request.url}")
    print(f"Headers: {request.headers}")
    response = await call_next(request)
    print(f"Response status: {response.status_code}")
    return response
# Include auth router
app.include_router(auth_router)

@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)
    # Create a default admin user if not exists
    db = next(get_db())
    admin_email = "admin@example.com"
    admin_password = "admin123"
    admin_user = db.query(models.User).filter(models.User.email == admin_email).first()
    if not admin_user:
        hashed_password = auth_utils.get_password_hash(admin_password)
        admin_user = models.User(
            email=admin_email,
            hashed_password=hashed_password,
            full_name="Admin User",
            is_superuser=True,
            created_at=datetime.utcnow()
        )
        db.add(admin_user)
        db.commit()
        print(f"Created default admin user with email: {admin_email} and password: {admin_password}")
    db.close()

@app.get("/books/", response_model=List[BookOut])
def list_books(
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    search: Optional[str] = None,
    new_arrivals_since: Optional[date] = None,
    db: Session = Depends(get_db),
    _admin: models.User = Depends(auth_utils.get_admin_user),
):
    """
    Retrieve all books with pagination.
    - **skip**: Number of records to skip (for pagination)
    - **limit**: Maximum number of records to return (for pagination)
    """
    books = get_books_filtered(db, skip=skip, limit=limit, status=status, search=search, new_arrivals_since=new_arrivals_since)
    return books


@app.get("/books/stats")
def books_inventory_stats(new_arrivals_days: int = 30, db: Session = Depends(get_db), _admin: models.User = Depends(auth_utils.get_admin_user)):
    """Return inventory aggregated statistics for dashboard."""
    try:
        s = books_stats(db, new_arrivals_days)
        return s
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
def health(db: Session = Depends(get_db)):
    """Basic health check endpoint. Returns DB connectivity and basic counts."""
    try:
        # quick DB check
        # using raw SQL to ensure connection is valid
        db.execute("SELECT 1")
        # get a few useful counts
        total = db.query(models.Book).count()
        members = db.query(models.Member).count()
        return {"status": "ok", "database": "connected", "total_books": total, "total_members": members}
    except Exception as e:
        return {"status": "error", "database": "disconnected", "detail": str(e)}

@app.post("/books/", response_model=BookOut)
def create_book(book: BookCreate, db: Session = Depends(get_db), _admin: models.User = Depends(auth_utils.get_admin_user)):
    try:
        return add_book(book, db)
    except Exception as e:
        # Log and convert to HTTP error so clients see a concise message
        import traceback
        print("Error creating book:", e)
        traceback.print_exc()
        raise HTTPException(status_code=400, detail=str(e))

@app.delete("/books/{book_id}")
def remove_book(book_id: int, db: Session = Depends(get_db), _admin: models.User = Depends(auth_utils.get_admin_user)):
    ok = delete_book(book_id, db)
    if not ok:
        raise HTTPException(status_code=404, detail="Book not found")
    return {"detail": "Book deleted"}

@app.get("/books/search", response_model=List[BookOut])
def search(
    title: Optional[str] = None,
    author: Optional[str] = None,
    isbn: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    published_after: Optional[date] = None,
    published_before: Optional[date] = None,
    db: Session = Depends(get_db),
    _admin: models.User = Depends(auth_utils.get_admin_user),
):
    try:
        print("Searching books with params:", {
            "title": title,
            "author": author,
            "isbn": isbn,
            "min_price": min_price,
            "max_price": max_price,
            "published_after": published_after,
            "published_before": published_before
        })
        result = search_books(
            title=title,
            author=author,
            isbn=isbn,
            min_price=min_price,
            max_price=max_price,
            published_after=published_after,
            published_before=published_before,
            db=db
        )
        print(f"Found {len(result)} books")
        return result
    except Exception as e:
        print(f"Error in search: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/books/{book_id}", response_model=BookOut)
def retrieve_book(book_id: int, db: Session = Depends(get_db), _admin: models.User = Depends(auth_utils.get_admin_user)):
    b = get_book_by_id(book_id, db)
    if not b:
        raise HTTPException(status_code=404, detail="Book not found")
    return b


@app.put("/books/{book_id}", response_model=BookOut)
def modify_book(book_id: int, book: BookCreate, db: Session = Depends(get_db), _admin: models.User = Depends(auth_utils.get_admin_user)):
    updated = update_book(book_id, book, db)
    if not updated:
        raise HTTPException(status_code=404, detail="Book not found")
    return updated


@app.patch("/books/{book_id}/status", response_model=BookOut)
def update_book_status(book_id: int, payload: BookStatusUpdate, db: Session = Depends(get_db), _admin: models.User = Depends(auth_utils.get_admin_user)):
    updated = set_book_status(book_id, payload.status, payload.note, db)
    if not updated:
        raise HTTPException(status_code=404, detail="Book not found")
    return updated


@app.post("/books/status/bulk")
def bulk_status_update(payload: BulkBookStatusUpdate, db: Session = Depends(get_db), _admin: models.User = Depends(auth_utils.get_admin_user)):
    count = bulk_update_book_status(payload.book_ids, payload.status, payload.note, db)
    return {"updated": count}


@app.get("/members/", response_model=List[MemberOut])
def list_members(skip: int = 0, limit: int = 100, db: Session = Depends(get_db), _admin: models.User = Depends(auth_utils.get_admin_user)):
    """List members with pagination"""
    return get_members(db, skip=skip, limit=limit)


@app.post("/members/", response_model=MemberOut)
def create_member(member: MemberCreate, db: Session = Depends(get_db), _admin: models.User = Depends(auth_utils.get_admin_user)):
    return add_member(member, db)


@app.get("/members/{member_id}", response_model=MemberOut)
def retrieve_member(member_id: int, db: Session = Depends(get_db), _admin: models.User = Depends(auth_utils.get_admin_user)):
    m = get_member_by_id(member_id, db)
    if not m:
        raise HTTPException(status_code=404, detail="Member not found")
    return m


@app.put("/members/{member_id}", response_model=MemberOut)
def modify_member(member_id: int, member: MemberUpdate, db: Session = Depends(get_db), _admin: models.User = Depends(auth_utils.get_admin_user)):
    updated = update_member(member_id, member, db)
    if not updated:
        raise HTTPException(status_code=404, detail="Member not found")
    return updated


@app.delete("/members/{member_id}")
def remove_member(member_id: int, db: Session = Depends(get_db), _admin: models.User = Depends(auth_utils.get_admin_user)):
    ok = delete_member(member_id, db)
    if not ok:
        raise HTTPException(status_code=404, detail="Member not found")
    return {"detail": "Member deleted"}


@app.get("/staff/", response_model=List[StaffOut])
def list_staff(skip: int = 0, limit: int = 100, db: Session = Depends(get_db), _admin: models.User = Depends(auth_utils.get_admin_user)):
    return get_staff(db, skip=skip, limit=limit)


@app.post("/staff/", response_model=StaffOut)
def create_staff(staff: StaffCreate, db: Session = Depends(get_db), _admin: models.User = Depends(auth_utils.get_admin_user)):
    return add_staff(staff, db)


@app.get("/staff/{staff_id}", response_model=StaffOut)
def retrieve_staff(staff_id: int, db: Session = Depends(get_db), _admin: models.User = Depends(auth_utils.get_admin_user)):
    s = get_staff_by_id(staff_id, db)
    if not s:
        raise HTTPException(status_code=404, detail="Staff not found")
    return s


@app.put("/staff/{staff_id}", response_model=StaffOut)
def modify_staff(staff_id: int, staff: StaffUpdate, db: Session = Depends(get_db), _admin: models.User = Depends(auth_utils.get_admin_user)):
    updated = update_staff(staff_id, staff, db)
    if not updated:
        raise HTTPException(status_code=404, detail="Staff not found")
    return updated


@app.delete("/staff/{staff_id}")
def remove_staff(staff_id: int, db: Session = Depends(get_db), _admin: models.User = Depends(auth_utils.get_admin_user)):
    ok = delete_staff(staff_id, db)
    if not ok:
        raise HTTPException(status_code=404, detail="Staff not found")
    return {"detail": "Staff deleted"}


# Transactions endpoints
@app.get("/transactions/", response_model=List[TransactionOut])
def list_txns(skip: int = 0, limit: int = 100, db: Session = Depends(get_db), _admin: models.User = Depends(auth_utils.get_admin_user)):
    return list_transactions(db, skip=skip, limit=limit)


@app.post("/transactions/", response_model=TransactionOut)
def create_txn(txn: TransactionCreate, db: Session = Depends(get_db), _admin: models.User = Depends(auth_utils.get_admin_user)):
    try:
        return add_transaction(txn, db)
    except Exception as e:
        import traceback
        print("Error creating transaction:", e)
        traceback.print_exc()
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/transactions/{txn_id}", response_model=TransactionOut)
def retrieve_txn(txn_id: int, db: Session = Depends(get_db), _admin: models.User = Depends(auth_utils.get_admin_user)):
    t = get_transaction_by_id(txn_id, db)
    if not t:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return t


@app.put("/transactions/{txn_id}", response_model=TransactionOut)
def modify_txn(txn_id: int, txn: TransactionCreate, db: Session = Depends(get_db), _admin: models.User = Depends(auth_utils.get_admin_user)):
    updated = update_transaction(txn_id, txn, db)
    if not updated:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return updated


@app.delete("/transactions/{txn_id}")
def remove_txn(txn_id: int, db: Session = Depends(get_db), _admin: models.User = Depends(auth_utils.get_admin_user)):
    ok = delete_transaction(txn_id, db)
    if not ok:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return {"detail": "Transaction deleted"}


# Reservations endpoints
@app.get("/reservations/", response_model=List[ReservationOut])
def list_resv(skip: int = 0, limit: int = 100, db: Session = Depends(get_db), _admin: models.User = Depends(auth_utils.get_admin_user)):
    return list_reservations(db, skip=skip, limit=limit)


@app.post("/reservations/", response_model=ReservationOut)
def create_resv(resv: ReservationCreate, db: Session = Depends(get_db), _admin: models.User = Depends(auth_utils.get_admin_user)):
    try:
        return add_reservation(resv, db)
    except Exception as e:
        import traceback
        print("Error creating reservation:", e)
        traceback.print_exc()
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/reservations/{resv_id}", response_model=ReservationOut)
def retrieve_resv(resv_id: int, db: Session = Depends(get_db), _admin: models.User = Depends(auth_utils.get_admin_user)):
    r = get_reservation_by_id(resv_id, db)
    if not r:
        raise HTTPException(status_code=404, detail="Reservation not found")
    return r


@app.put("/reservations/{resv_id}", response_model=ReservationOut)
def modify_resv(resv_id: int, resv: ReservationCreate, db: Session = Depends(get_db), _admin: models.User = Depends(auth_utils.get_admin_user)):
    updated = update_reservation(resv_id, resv, db)
    if not updated:
        raise HTTPException(status_code=404, detail="Reservation not found")
    return updated


@app.delete("/reservations/{resv_id}")
def remove_resv(resv_id: int, db: Session = Depends(get_db), _admin: models.User = Depends(auth_utils.get_admin_user)):
    ok = delete_reservation(resv_id, db)
    if not ok:
        raise HTTPException(status_code=404, detail="Reservation not found")
    return {"detail": "Reservation deleted"}


# Fines endpoints
@app.get("/fines/", response_model=List[FineOut])
def list_fines_endpoint(skip: int = 0, limit: int = 100, db: Session = Depends(get_db), _admin: models.User = Depends(auth_utils.get_admin_user)):
    return list_fines(db, skip=skip, limit=limit)


@app.post("/fines/", response_model=FineOut)
def create_fine(fine: FineCreate, db: Session = Depends(get_db), _admin: models.User = Depends(auth_utils.get_admin_user)):
    try:
        return add_fine(fine, db)
    except Exception as e:
        import traceback
        print("Error creating fine:", e)
        traceback.print_exc()
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/fines/{fine_id}", response_model=FineOut)
def retrieve_fine(fine_id: int, db: Session = Depends(get_db), _admin: models.User = Depends(auth_utils.get_admin_user)):
    f = get_fine_by_id(fine_id, db)
    if not f:
        raise HTTPException(status_code=404, detail="Fine not found")
    return f


@app.put("/fines/{fine_id}", response_model=FineOut)
def modify_fine(fine_id: int, fine: FineCreate, db: Session = Depends(get_db), _admin: models.User = Depends(auth_utils.get_admin_user)):
    updated = update_fine(fine_id, fine, db)
    if not updated:
        raise HTTPException(status_code=404, detail="Fine not found")
    return updated


@app.delete("/fines/{fine_id}")
def remove_fine(fine_id: int, db: Session = Depends(get_db), _admin: models.User = Depends(auth_utils.get_admin_user)):
    ok = delete_fine(fine_id, db)
    if not ok:
        raise HTTPException(status_code=404, detail="Fine not found")
    return {"detail": "Fine deleted"}


# Auth logs
@app.get("/auth/logs", response_model=List[AuthLogOut])
def list_auth_logs(skip: int = 0, limit: int = 100, db: Session = Depends(get_db), _admin: models.User = Depends(auth_utils.get_admin_user)):
    return get_auth_logs(db, skip=skip, limit=limit)


# Reports
@app.get("/reports/daily-activity", response_model=List[DailyIssuedReturned])
def report_daily_activity(days: int = 30, db: Session = Depends(get_db), _admin: models.User = Depends(auth_utils.get_admin_user)):
    return daily_issued_returned(db, days)


@app.get("/reports/monthly-activity", response_model=List[MonthlyActivity])
def report_monthly_activity(months: int = 6, db: Session = Depends(get_db), _admin: models.User = Depends(auth_utils.get_admin_user)):
    return monthly_activity(db, months)


@app.get("/reports/most-borrowed", response_model=List[MostBorrowedItem])
def report_most_borrowed(limit: int = 10, db: Session = Depends(get_db), _admin: models.User = Depends(auth_utils.get_admin_user)):
    return most_borrowed_books(db, limit)


@app.get("/reports/inactive-members", response_model=List[InactiveMember])
def report_inactive_members(months: int = 6, db: Session = Depends(get_db), _admin: models.User = Depends(auth_utils.get_admin_user)):
    return inactive_members(db, months)


@app.get("/reports/fine-collection", response_model=List[FineCollection])
def report_fine_collection(days: int = 30, db: Session = Depends(get_db), _admin: models.User = Depends(auth_utils.get_admin_user)):
    return fine_collection_report(db, days)

# Add this to run the application directly
if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=9000,
        reload=True
    )

#ddsdsf